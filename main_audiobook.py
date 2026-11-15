"""Analyse manuscripts, then render human-approved audiobook orientations."""

import argparse
from pathlib import Path
import re
import shutil
import sys

import ollama

from diarizer import check_model
from orientation import analyse_chapter, atomic_json, read_orientation
from qwen_renderer import Engine, ensure_profiles, instruction, load_profiles, render_book

ROOT = Path(__file__).resolve().parent
BOOKS = {
    "1": "Livre I - L_éveil",
    "2": "Livre II - La Traque",
    "3": "Livre III - L’Héritage",
}
CHAPTER = re.compile(r"^(?:CHAPITRE )?(\d+) - .+\.md$")


def chapter_paths(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise ValueError(f"Dossier de livre introuvable : {directory}")
    numbered: list[tuple[int, Path]] = []
    for path in directory.glob("*.md"):
        match = CHAPTER.fullmatch(path.name)
        if not match:
            raise ValueError(f"Nom de chapitre non reconnu : {path}")
        numbered.append((int(match.group(1)), path))
    numbered.sort(key=lambda item: item[0])
    if not numbered:
        raise ValueError(f"Aucun chapitre Markdown dans {directory}")
    for expected, (number, _) in enumerate(numbered, 1):
        if number != expected:
            raise ValueError(f"Numérotation incorrecte dans {directory} : chapitre {expected} attendu.")
    return [path for _, path in numbered]


def run() -> None:
    parser = argparse.ArgumentParser(description="Analyser puis générer les livres audio localement.")
    parser.add_argument("phase", choices=("analyse", "generer"), help="Phase du traitement.")
    parser.add_argument("--book", choices=tuple(BOOKS), help="Ne générer que le livre 1, 2 ou 3.")
    parser.add_argument("--model", default="qwen2.5:3b", help="Modèle Ollama d'analyse émotionnelle (défaut : qwen2.5:3b).")
    parser.add_argument("--speaker-model", default="qwen2.5:7b", help="Modèle Ollama d'attribution des locuteurs (défaut : qwen2.5:7b).")
    parser.add_argument("--approuve", action="store_true", help="Confirmer la validation humaine des orientations.")
    parser.add_argument("--auto", action="store_true", help="Générer sans validation humaine, avec avertissements.")
    args = parser.parse_args()

    selected = [(number, folder) for number, folder in BOOKS.items() if not args.book or number == args.book]
    chapters = [(number, chapter_paths(ROOT / folder)) for number, folder in selected]
    if args.phase == "analyse":
        client = ollama.Client(host="http://127.0.0.1:11434", timeout=180)
        check_model(client, args.model)
        if args.speaker_model:
            check_model(client, args.speaker_model)
        for number, paths in chapters:
            directory = ROOT / "exports" / "orientations" / f"Livre-{number}"
            for index, source in enumerate(paths, 1):
                target = directory / f"chapitre-{index:03d}.json"
                if target.exists():
                    data = read_orientation(target, source, index, allow_unknown=True)
                    print(f"Orientation conservée : {target}", flush=True)
                else:
                    print(f"Analyse du livre {number}, chapitre {index}/{len(paths)}.", flush=True)
                    data = analyse_chapter(source, index, client, args.model, args.speaker_model)
                    atomic_json(target, data)
                    print(f"Orientation créée : {target}", flush=True)
                ensure_profiles(ROOT / "exports" / "orientations" / "voix.json",
                                {s["locuteur"] for s in data["segments"]})
        print("Analyse terminée. Vérifiez et corrigez les fichiers d'orientation avant la génération.", flush=True)
        return
    if not args.approuve and not args.auto:
        raise ValueError("Validation humaine requise : relisez les orientations, puis ajoutez --approuve.")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg et ffprobe sont requis dans le PATH.")
    profiles_path = ROOT / "exports" / "orientations" / "voix.json"
    profiles = load_profiles(profiles_path)
    for number, paths in chapters:
        directory = ROOT / "exports" / "orientations" / f"Livre-{number}"
        for index, source in enumerate(paths, 1):
            data = read_orientation(directory / f"chapitre-{index:03d}.json", source, index)
            for segment in data["segments"]:
                if segment["locuteur"] not in profiles:
                    raise ValueError(f"Voix manquante pour {segment['locuteur']} dans {profiles_path}")
                instruction(segment, profiles[segment["locuteur"]])
    if args.auto:
        print("ATTENTION : génération sans validation humaine.", flush=True)
    engine = Engine()
    for number, paths in chapters:
        target = render_book(ROOT, number, paths, engine)
        print(f"Créé : {target}", flush=True)


if __name__ == "__main__":
    try:
        run()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)

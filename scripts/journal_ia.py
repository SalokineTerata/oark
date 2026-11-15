"""Journal de relais local : état, ajout et rotation sans service externe."""

import argparse
from datetime import datetime
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 16000
HEADER = "# Journal actif des IA\n\nEntrées récentes ; archives dans `archives`.\n"
BOOKS = (
    ("1", "Livre I - L_éveil"),
    ("2", "Livre II - La Traque"),
    ("3", "Livre III - L’Héritage"),
)
BOOKS_V2 = {
    "1": "livres/Livre I - L'Éveil",
    "2": "livres/Livre II - La Traque",
    "3": "livres/Livre III - L'Héritage",
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def lock(directory: Path) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    return os.open(directory / ".verrou", os.O_CREAT | os.O_EXCL | os.O_WRONLY)


def archive_path(directory: Path) -> Path:
    archive = directory / "archives"
    archive.mkdir(parents=True, exist_ok=True)
    index = 1
    while (archive / f"journal-{index:04d}.md").exists():
        index += 1
    return archive / f"journal-{index:04d}.md"


def rotate(directory: Path) -> Path | None:
    current = directory / "courant.md"
    if not current.exists() or current.read_text(encoding="utf-8") == HEADER:
        return None
    target = archive_path(directory)
    # Write the empty successor first: failure cannot lose the previous journal.
    successor = directory / ".successeur.tmp"
    atomic_write(successor, HEADER)
    try:
        os.replace(current, target)
        try:
            os.replace(successor, current)
        except OSError:
            os.replace(target, current)
            raise
    finally:
        successor.unlink(missing_ok=True)
    return target


def add_entry(directory: Path, title: str, text: str) -> Path | None:
    title = title.strip()
    text = text.strip()
    if not title or not text or "\n" in title or "\r" in title:
        raise ValueError("Titre sur une seule ligne et contenu non vides requis.")
    entry = f"\n## {datetime.now().astimezone().isoformat(timespec='seconds')} — {title}\n\n{text}\n"
    if len((HEADER + entry).encode("utf-8")) > MAX_BYTES:
        raise ValueError(f"Entrée trop longue pour un journal de {MAX_BYTES} octets ; résumez-la.")
    fd = lock(directory)
    try:
        current = directory / "courant.md"
        content = current.read_text(encoding="utf-8") if current.exists() else HEADER
        archived = None
        if len((content + entry).encode("utf-8")) > MAX_BYTES:
            archived = rotate(directory)
            content = HEADER
        atomic_write(current, content + entry)
        return archived
    finally:
        os.close(fd)
        (directory / ".verrou").unlink()


def status(root: Path) -> str:
    lines = [f"Projet : {root}"]
    for number, folder in BOOKS:
        v2_source = root / BOOKS_V2[number]
        source = v2_source if v2_source.is_dir() else root / folder
        chapters = len(list(source.glob("*.md"))) if source.is_dir() else 0
        pivots = root / "exports" / "orientations" / f"Livre-{number}"
        orientations = len(list(pivots.glob("chapitre-*.json"))) if pivots.is_dir() else 0
        audio = root / "exports" / f"Livre-{number}_Audiobook.mp3"
        result = f"{audio.stat().st_size} octets (non vérifié)" if audio.is_file() else "absent"
        lines.append(f"Livre {number} : {chapters} sources, {orientations} orientations, audio {result}")
    journal = root / "journal_ia"
    archives = journal / "archives"
    lines.append(f"Archives du journal : {len(list(archives.glob('journal-*.md'))) if archives.is_dir() else 0}")
    lines.append("Un fichier audio existant ne prouve pas sa qualité ni sa complétude.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Racine du projet (défaut : ce projet).")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("etat", help="Inventaire local, sans démarrer de service.")
    commands.add_parser("lire", help="Afficher le journal actif.")
    commands.add_parser("rotation", help="Archiver le journal actif non vide.")
    add = commands.add_parser("ajouter", help="Ajouter une entrée et effectuer la rotation si nécessaire.")
    add.add_argument("--titre", required=True)
    source = add.add_mutually_exclusive_group(required=True)
    source.add_argument("--texte")
    source.add_argument("--fichier", type=Path, help="Fichier UTF-8 contenant l'entrée.")
    args = parser.parse_args()
    root = args.root.resolve()
    directory = root / "journal_ia"
    if args.command == "etat":
        print(status(root))
    elif args.command == "lire":
        current = directory / "courant.md"
        print(current.read_text(encoding="utf-8") if current.exists() else "Journal actif absent.")
    elif args.command == "ajouter":
        text = args.fichier.read_text(encoding="utf-8-sig") if args.fichier else args.texte
        archived = add_entry(directory, args.titre, text)
        print(f"Entrée ajoutée : {directory / 'courant.md'}")
        if archived:
            print(f"Archive créée : {archived}")
    else:
        fd = lock(directory)
        try:
            archived = rotate(directory)
            print(f"Archive créée : {archived}" if archived else "Aucune entrée à archiver.")
        finally:
            os.close(fd)
            (directory / ".verrou").unlink()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build EPUB3 books for the Oark V2 trilogy in exports-v2/ using Pandoc."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parent.parent
EXPORTS_V2 = ROOT / "exports-v2"
BOOKS = (
    ("I", "Livre I - L'Éveil", "Oark - Livre I - L'Éveil.epub", "Oark — Livre I : L’Éveil"),
    ("II", "Livre II - La Traque", "Oark - Livre II - La Traque.epub", "Oark — Livre II : La Traque"),
    ("III", "Livre III - L'Héritage", "Oark - Livre III - L'Héritage.epub", "Oark — Livre III : L’Héritage"),
)
FILENAME = re.compile(r"^CHAPITRE (\d+) - .+\.md$")
HEADING = re.compile(r"^# CHAPITRE (\d+) : .+$", re.IGNORECASE)


def find_pandoc() -> Path:
    configured = os.environ.get("PANDOC")
    if configured:
        candidate = Path(configured)
        if candidate.is_file():
            return candidate
    resolved = shutil.which("pandoc")
    if resolved:
        return Path(resolved)
    fallback = Path(os.environ.get("LOCALAPPDATA", "")) / "Pandoc" / "pandoc.exe"
    if fallback.is_file():
        return fallback
    raise RuntimeError("Pandoc introuvable. Installez-le ou définissez PANDOC.")


def discover_book(folder_name: str) -> list[tuple[int, Path, str]]:
    directory = EXPORTS_V2 / folder_name
    if not directory.is_dir():
        raise RuntimeError(f"Dossier introuvable : {directory}")
    sources: list[tuple[int, Path]] = []
    for path in directory.glob("*.md"):
        match = FILENAME.fullmatch(path.name)
        if not match:
            raise RuntimeError(f"Nom de chapitre non reconnu : {path}")
        sources.append((int(match.group(1)), path))
    sources.sort(key=lambda item: item[0])
    if not sources:
        raise RuntimeError(f"Aucun chapitre trouvé dans {directory}")

    chapters: list[tuple[int, Path, str]] = []
    for expected, (number, source) in enumerate(sources, 1):
        if number != expected:
            raise RuntimeError(f"Numérotation non continue dans {directory} : chapitre {expected} attendu, trouvé {number}.")
        text = source.read_text(encoding="utf-8-sig")
        first_line = text.splitlines()[0].rstrip("\r") if text.splitlines() else ""
        heading = HEADING.fullmatch(first_line)
        if not heading or int(heading.group(1)) != number:
            raise RuntimeError(f"Titre H1 inattendu dans {source} : {first_line!r}")
        chapters.append((number, source, text.strip()))
    return chapters


def verify_epub(epub_path: Path, expected_chapters: int) -> dict[str, int]:
    if not epub_path.is_file() or epub_path.stat().st_size == 0:
        raise RuntimeError(f"Fichier EPUB invalide ou vide : {epub_path}")
    with zipfile.ZipFile(epub_path, "r") as zf:
        names = zf.namelist()
        if "META-INF/container.xml" not in names:
            raise RuntimeError(f"EPUB invalide (META-INF/container.xml manquant) : {epub_path}")
        chapter_xhtml = [n for n in names if re.search(r"ch\d+\.xhtml$", n)]
        if len(chapter_xhtml) != expected_chapters:
            raise RuntimeError(
                f"Nombre de chapitres XHTML inattendu dans {epub_path.name} : "
                f"{len(chapter_xhtml)} trouvés, {expected_chapters} attendus."
            )
        media_files = [n for n in names if n.startswith("EPUB/media/")]
    return {
        "size_kb": round(epub_path.stat().st_size / 1024),
        "chapters_xhtml": len(chapter_xhtml),
        "images": len(media_files),
    }


def run() -> None:
    parser = argparse.ArgumentParser(description="Construire les EPUB3 de la trilogie V2 dans exports-v2/.")
    parser.add_argument("--book", choices=("I", "II", "III"), help="Ne construire qu'un seul livre.")
    args = parser.parse_args()

    pandoc = find_pandoc()
    base_css = ROOT / "scripts" / "book_style.css"
    if not base_css.is_file():
        raise RuntimeError(f"Feuille de style introuvable : {base_css}")

    selected = [b for b in BOOKS if not args.book or b[0] == args.book]
    prepared = [(b, discover_book(b[1])) for b in selected]

    # Temp dir strictly on D: (never C:)
    with tempfile.TemporaryDirectory(prefix="oark-v2-epub-", dir=EXPORTS_V2) as workdir:
        work = Path(workdir)
        css_v2 = work / "book_style_v2.css"
        css_v2.write_text(
            base_css.read_text(encoding="utf-8")
            + "\nblockquote {\n"
            + "  margin: 0.8em 1.2em 1.4em;\n"
            + "  padding-left: 0.9em;\n"
            + "  border-left: 2px solid #999;\n"
            + "  font-style: italic;\n"
            + "  font-size: 0.92em;\n"
            + "  color: #444;\n"
            + "}\n",
            encoding="utf-8",
        )

        for (roman, _, filename, title), chapters in prepared:
            md_path = work / f"oark-v2-livre-{roman.lower()}.md"
            epub_tmp = work / filename
            target = EXPORTS_V2 / filename
            combined_md = "\n\n".join(c[2] for c in chapters) + "\n"
            combined_md = combined_md.replace("](../illustrations/", "](illustrations/")
            md_path.write_text(combined_md, encoding="utf-8", newline="\n")

            subprocess.run(
                [
                    str(pandoc),
                    str(md_path),
                    "--from=markdown",
                    "--to=epub3",
                    "--standalone",
                    "--toc",
                    "--toc-depth=1",
                    "--resource-path", str(EXPORTS_V2),
                    "--metadata", f"title={title}",
                    "--metadata", "lang=fr",
                    "--css", str(css_v2),
                    "--output", str(epub_tmp),
                ],
                check=True,
                cwd=EXPORTS_V2,
            )
            shutil.copyfile(epub_tmp, target)
            stats = verify_epub(target, len(chapters))
            print(
                f"OK : {target.name} | {len(chapters)} chapitres | "
                f"{stats['chapters_xhtml']} sections XHTML | {stats['size_kb']} Ko",
                flush=True,
            )


if __name__ == "__main__":
    try:
        run()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)

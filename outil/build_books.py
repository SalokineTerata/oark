#!/usr/bin/env python3
"""Build illustrated Oark books with Pandoc and Microsoft Edge."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
BOOKS = (
    ("I", "Livre I - L_éveil", "Oark - Livre I - L'Éveil.pdf", "Oark — Livre I : L’Éveil"),
    ("II", "Livre II - La Traque", "Oark - Livre II - La Traque.pdf", "Oark — Livre II : La Traque"),
    ("III", "Livre III - L’Héritage", "Oark - Livre III - L'Héritage.pdf", "Oark — Livre III : L’Héritage"),
)
FILENAME = re.compile(r"^(?:CHAPITRE )?(\d+) - .+\.md$")
HEADING = re.compile(r"^# Chapitre (\d+) — .+$")
PDF_DATE = re.compile(rb"/(CreationDate|ModDate) \(D:\d{14}[+-]\d{2}'\d{2}'\)")
FIXED_DATE = b"D:20000101000000+00'00'"


def executable(env_name: str, name: str, fallbacks: list[Path]) -> Path:
    configured = os.environ.get(env_name)
    if configured:
        candidate = Path(configured)
        if not candidate.is_file():
            raise RuntimeError(f"{env_name} ne désigne pas un fichier : {candidate}")
        return candidate
    resolved = shutil.which(name)
    if resolved:
        return Path(resolved)
    for candidate in fallbacks:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"{name} introuvable. Installez-le ou définissez {env_name}.")


def discover_book(book: tuple[str, str, str, str]) -> list[tuple[Path, Path, str]]:
    roman, folder, _, _ = book
    directory = ROOT / folder
    if not directory.is_dir():
        raise RuntimeError(f"Dossier du livre introuvable : {directory}")
    sources = []
    for path in directory.glob("*.md"):
        match = FILENAME.fullmatch(path.name)
        if not match:
            raise RuntimeError(f"Nom de chapitre non reconnu : {path}")
        sources.append((int(match.group(1)), path))
    sources.sort(key=lambda item: item[0])
    if not sources:
        raise RuntimeError(f"Aucun chapitre trouvé dans {directory}")
    entries = []
    for expected, (number, source) in enumerate(sources, 1):
        if number != expected:
            raise RuntimeError(f"Numérotation non continue dans {directory} : chapitre {expected} attendu.")
        text = source.read_text(encoding="utf-8-sig")
        first, separator, body = text.partition("\n")
        heading = HEADING.fullmatch(first.rstrip("\r"))
        if not separator or not heading or int(heading.group(1)) != number:
            raise RuntimeError(f"Titre incorrect dans {source}")
        image = ROOT / "illustrations" / f"livre-{roman.lower()}" / f"{number:03d}.png"
        if not image.is_file():
            raise RuntimeError(f"Illustration manquante pour {source.name} : {image}")
        with image.open("rb") as stream:
            if stream.read(8) != b"\x89PNG\r\n\x1a\n":
                raise RuntimeError(f"Illustration PNG invalide : {image}")
        markdown = first.rstrip("\r") + "\n\n![](<" + image.resolve().as_uri() + ">){.chapter-illustration}\n\n" + body.lstrip("\r\n")
        entries.append((source, image, markdown))
    return entries


def normalize_pdf(data: bytes) -> bytes:
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
        raise RuntimeError("Le navigateur n'a pas produit un PDF complet.")
    matches = PDF_DATE.findall(data)
    if sorted(matches) != [b"CreationDate", b"ModDate"]:
        raise RuntimeError("Métadonnées PDF inattendues : impossible de garantir une sortie déterministe.")
    normalized = PDF_DATE.sub(lambda match: b"/" + match.group(1) + b" (" + FIXED_DATE + b")", data)
    if len(normalized) != len(data):
        raise RuntimeError("La normalisation des métadonnées a modifié la taille du PDF.")
    return normalized


def run() -> None:
    parser = argparse.ArgumentParser(description="Reconstruire les trois livres illustrés.")
    parser.add_argument("--book", choices=("I", "II", "III"), help="Ne construire qu'un livre.")
    parser.add_argument("--format", choices=("pdf", "epub"), default="pdf", help="Format de sortie.")
    args = parser.parse_args()
    localappdata = Path(os.environ.get("LOCALAPPDATA", ""))
    pandoc = executable("PANDOC", "pandoc", [localappdata / "Pandoc" / "pandoc.exe"])
    edge = None
    if args.format == "pdf":
        edge = executable(
            "EDGE",
            "msedge",
            [
                Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            ],
        )
    style = ROOT / "scripts" / "book_style.css"
    if not style.is_file():
        raise RuntimeError(f"Feuille de style introuvable : {style}")
    books = [book for book in BOOKS if not args.book or book[0] == args.book]
    prepared = [(book, discover_book(book)) for book in books]
    with tempfile.TemporaryDirectory(prefix="oark-books-") as workdir:
        work = Path(workdir)
        outputs = []
        for book, entries in prepared:
            roman, _, name, title = book
            print(f"Livre {roman} : {len(entries)} chapitres.", flush=True)
            md = work / f"livre-{roman.lower()}.md"
            markdown = [entry[2].rstrip() for entry in entries]
            if args.format == "epub":
                markdown = [
                    text.replace(image.resolve().as_uri(), image.relative_to(ROOT).as_posix())
                    for text, (_, image, _) in zip(markdown, entries)
                ]
            md.write_text("\n\n".join(markdown) + "\n", encoding="utf-8", newline="\n")
            if args.format == "epub":
                epub = work / f"livre-{roman.lower()}.epub"
                subprocess.run(
                    [
                        str(pandoc), str(md), "--from=markdown", "--to=epub3", "--standalone",
                        "--toc", "--toc-depth=1", "--metadata", f"title={title}", "--metadata", "lang=fr",
                        "--css", str(style), "--resource-path", str(ROOT), "--output", str(epub),
                    ],
                    check=True,
                    cwd=ROOT,
                )
                if not epub.is_file():
                    raise RuntimeError(f"Pandoc n'a pas produit l'EPUB du livre {roman}.")
                target = ROOT / "exports" / Path(name).with_suffix(".epub").name
                outputs.append((epub, target))
                continue
            html = work / f"livre-{roman.lower()}.html"
            pdf = work / f"livre-{roman.lower()}.pdf"
            subprocess.run(
                [
                    str(pandoc), str(md), "--from=markdown", "--to=html5", "--standalone",
                    "--toc", "--toc-depth=1", "--metadata", f"title={title}", "--metadata", "lang=fr",
                    "--css", style.resolve().as_uri(), "--output", str(html),
                ],
                check=True,
                cwd=ROOT,
            )
            assert edge is not None
            result = subprocess.run(
                [
                    str(edge), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--disable-background-networking", "--disable-extensions",
                    f"--user-data-dir={work / ('edge-' + roman.lower())}",
                    f"--print-to-pdf={pdf}", html.resolve().as_uri(),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            if result.returncode or not pdf.is_file():
                raise RuntimeError(f"Échec du navigateur pour le livre {roman} :\n{result.stderr[-4000:]}")
            pdf.write_bytes(normalize_pdf(pdf.read_bytes()))
            outputs.append((pdf, ROOT / "exports" / name))
        for source, target in outputs:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            print(f"Créé : {target}", flush=True)


if __name__ == "__main__":
    try:
        run()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)

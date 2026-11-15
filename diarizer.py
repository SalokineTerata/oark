"""Split Markdown into spoken blocks and identify speakers using local Ollama."""

from pathlib import Path
import re
from typing import Iterable

import httpx
import ollama
from tqdm import tqdm

SYSTEM_PROMPT = "Tu es un assistant qui analyse un texte littéraire. Identifie qui parle. Réponds UNIQUEMENT par l'un de ces mots-clés : [NARRATEUR], [KODA], [BORRAS], [VANE], [JARO]. Si c'est de la description, c'est [NARRATEUR]."
SPEAKERS = {"[NARRATEUR]", "[KODA]", "[BORRAS]", "[VANE]", "[JARO]"}


def markdown_blocks(text: str) -> list[str]:
    """Keep chapter headings, paragraphs and dialogue turns in reading order."""
    blocks: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            block = " ".join(paragraph).strip()
            block = re.sub(r"!\[([^\]]*)\]\([^)]*\)", "", block)
            block = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", block)
            block = re.sub(r"^#{1,6}\s+", "", block)
            block = re.sub(r"(\*\*|__|\*|_)(.*?)\1", r"\2", block)
            block = block.strip()
            if block and not re.fullmatch(r"[-*_ ]{3,}", block):
                blocks.append(block)
            paragraph.clear()

    for line in text.splitlines():
        line = line.strip()
        if not line:
            flush()
        elif line.startswith("—"):
            flush()
            paragraph.append(line)
            flush()
        elif line.startswith("#"):
            flush()
            paragraph.append(line)
            flush()
        else:
            # Some paragraphs place a dialogue turn after a narrative sentence.
            parts = re.split(r"(?<=[.!?])\s+(?=—\s)", line, maxsplit=1)
            paragraph.append(parts[0])
            if len(parts) == 2:
                flush()
                paragraph.append(parts[1])
                flush()
    flush()
    return blocks


def read_markdown(paths: Iterable[Path]) -> list[str]:
    blocks: list[str] = []
    for path in paths:
        blocks.extend(markdown_blocks(path.read_text(encoding="utf-8-sig")))
    if not blocks:
        raise ValueError("Aucun texte à lire dans les chapitres.")
    return blocks


def check_model(client: ollama.Client, model: str) -> None:
    try:
        client.show(model)
    except (ollama.ResponseError, ConnectionError, httpx.RequestError) as exc:
        raise RuntimeError(
            f"Ollama ou le modèle '{model}' est inaccessible. Démarrez Ollama sur "
            f"127.0.0.1:11434 et installez le modèle avec « ollama pull {model} » : {exc}"
        ) from exc


def diarize(blocks: list[str], client: ollama.Client, model: str) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    for index, block in enumerate(tqdm(blocks, desc="Diarisation", unit="bloc")):
        before = blocks[index - 1] if index else "(début du livre)"
        after = blocks[index + 1] if index + 1 < len(blocks) else "(fin du livre)"
        prompt = (
            "Identifie uniquement le locuteur du BLOC CIBLE. Les blocs voisins servent "
            "de contexte, pas de réponse.\n"
            f"BLOC PRÉCÉDENT :\n{before}\n\nBLOC CIBLE :\n{block}\n\nBLOC SUIVANT :\n{after}"
        )
        try:
            response = client.chat(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": prompt}],
                options={"temperature": 0},
            )
        except (ollama.ResponseError, ConnectionError, httpx.RequestError) as exc:
            raise RuntimeError(f"Échec Ollama au bloc {index + 1} : {exc}") from exc
        speaker = (response.message.content or "").strip().upper()
        if speaker not in SPEAKERS:
            raise ValueError(f"Réponse Ollama invalide au bloc {index + 1} : {speaker!r}")
        segments.append((speaker, block))
    return segments

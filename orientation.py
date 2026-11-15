"""Editable, chapter-level orientation documents for the local audio pipeline."""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

import httpx
import ollama
from tqdm import tqdm

from diarizer import markdown_blocks
from speakers import OTHER, explicit_speaker, resolve_chapter

EMOTIONS = (
    "neutre", "interet", "joie", "plaisir", "amour", "admiration", "soulagement",
    "fierte", "espoir", "compassion", "tristesse", "peur", "colere", "degout",
    "mepris", "honte", "culpabilite", "regret", "deception", "inquietude",
    "surprise", "confusion", "ennui",
)
INTENTIONS = (
    "narrer", "informer", "questionner", "repondre", "ordonner", "rassurer",
    "persuader", "avertir", "menacer", "protester", "plaisanter", "hesiter",
    "confier", "saluer", "remercier", "autre",
)
VOCALISATIONS = ("parole", "chuchotement", "cri", "rire", "sanglot", "soupir")
FIABILITE = ("explicite", "deduit", "incertain")
VERSION = 1

INCISION = re.compile(
    r"^(?P<dialogue>—.*?[.!?,…])\s+"
    r"(?P<narration>(?:dit|demanda|répondit|reprit|lança|murmura|ordonna|ajouta|"
    r"souffla|cria|affirma|répliqua|chuchota|rétorqua|interrogea)"
    r"(?:[-\s])[^.!?]*[.!?])(?:\s+(?P<suite>.+))?$",
    re.IGNORECASE,
)


def split_blocks(blocks: list[str]) -> list[tuple[str, str, int | None]]:
    """Split unambiguous dialogue attributions from the spoken line."""
    result: list[tuple[str, str, int | None]] = []
    for block in blocks:
        match = INCISION.fullmatch(block) if block.startswith("—") else None
        if match:
            dialogue_index = len(result)
            result.append((match["dialogue"], "dialogue", None))
            result.append((match["narration"], "narration", None))
            if match["suite"]:
                result.append((match["suite"], "dialogue", dialogue_index))
        else:
            result.append((block, "dialogue" if block.startswith("—") else "narration", None))
    return result


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyse_chapter(path: Path, number: int, client: ollama.Client, model: str, speaker_model: str | None = None) -> dict:
    blocks = split_blocks(markdown_blocks(path.read_text(encoding="utf-8-sig")))
    if not blocks or not blocks[0][0].lower().startswith(f"chapitre {number} "):
        raise ValueError(f"Titre du chapitre {number} invalide : {path}")
    explicit = {}
    for i, (text, kind, continuation) in enumerate(blocks[:-1]):
        if kind == "dialogue" and continuation is None and blocks[i + 1][1] == "narration":
            who = explicit_speaker(blocks[i + 1][0])
            if who:
                explicit[i] = who
    attribution = resolve_chapter(blocks, explicit, client, speaker_model or model)
    annotated = []
    for start in tqdm(range(0, len(blocks), 4), desc=f"Analyse chapitre {number}", unit="lot"):
        ids = list(range(start, min(start + 4, len(blocks))))
        context = range(max(0, start - 8), min(len(blocks), start + 7))
        properties = {
            "locuteur": {"type": "string"},
            "fiabilite_locuteur": {"type": "string", "enum": list(FIABILITE)},
            "emotion": {"type": "string", "enum": list(EMOTIONS)},
            "valence": {"type": "number", "minimum": -1, "maximum": 1},
            "activation": {"type": "number", "minimum": 0, "maximum": 1},
            "dominance": {"type": "number", "minimum": 0, "maximum": 1},
            "intensite": {"type": "number", "minimum": 0, "maximum": 1},
            "intention": {"type": "string", "enum": list(INTENTIONS)},
            "vocalisation": {"type": "string", "enum": list(VOCALISATIONS)},
        }
        schema = {
            "type": "object",
            "properties": {
                str(i): {"type": "object", "properties": properties,
                         "required": list(properties), "additionalProperties": False}
                for i in ids
            },
            "required": [str(i) for i in ids],
            "additionalProperties": False,
        }
        prompt = (
            "Analyse littéraire en français. Identifie le locuteur et propose une orientation "
            "de jeu à partir du texte : valence de -1 à 1, activation, dominance et intensité "
            "de 0 à 1. Les indications sont hypothétiques et seront vérifiées par un humain. "
            "Le titre et les descriptions sont NARRATEUR. Pour une réplique marquée dialogue, "
            "détermine qui parle sans confondre le locuteur avec le destinataire ; si incertain, "
            "utilise INCONNU. Indique si l'attribution est explicite, deduite ou incertaine ; "
            "une simple alternance ne rend pas une attribution explicite. "
            "Bricole et ÉCHO sont deux personnages distincts : nomme-les BRICOLE et ECHO. "
            "Vocalisation parole sauf si le texte indique explicitement autre chose. "
            f"Réponds au format demandé pour les seuls numéros {ids}.\n"
            + "\n".join(f"{i} [{blocks[i][1]}]: {blocks[i][0]}" for i in context)
        )
        for attempt in range(3):
            try:
                response = client.chat(
                    model=model, messages=[{"role": "user", "content": prompt}], format=schema,
                    options={"temperature": 0.1 * attempt, "num_ctx": 4096, "num_predict": 2000},
                )
                result = json.loads(response.message.content or "")
                break
            except json.JSONDecodeError as exc:
                if attempt == 2:
                    raise RuntimeError(f"Analyse échouée pour {path.name}, bloc {start + 1} après 3 essais : {exc}") from exc
                tqdm.write(f"Réponse JSON invalide pour {path.name}, bloc {start + 1} ; nouvel essai.")
            except (ollama.ResponseError, ConnectionError, httpx.RequestError) as exc:
                raise RuntimeError(f"Analyse échouée pour {path.name}, bloc {start + 1} : {exc}") from exc
        if not isinstance(result, dict):
            raise ValueError(f"Réponse d'analyse invalide dans {path.name}, bloc {start + 1}.")
        for i in ids:
            data = result.get(str(i))
            if not isinstance(data, dict):
                raise ValueError(f"Analyse manquante pour le bloc {i + 1} de {path.name}.")
            speaker = data.get("locuteur")
            if not isinstance(speaker, str) or not speaker.strip():
                raise ValueError(f"Locuteur invalide pour le bloc {i + 1} de {path.name}.")
            text, kind, continuation = blocks[i]
            reliability = data.get("fiabilite_locuteur")
            if i == 0 or kind == "narration":
                speaker = "NARRATEUR"
            else:
                who, role, reliability = attribution[i]
                speaker = (role or "VOIX") if who == OTHER else who
            segment = {
                "id": i + 1,
                "type": "chapitre" if i == 0 else kind,
                "texte": text,
                "locuteur": speaker.strip().upper(),
                "fiabilite_locuteur": "explicite" if i == 0 or kind == "narration" else reliability,
                "emotion": data.get("emotion"),
                "valence": data.get("valence"),
                "activation": data.get("activation"),
                "dominance": data.get("dominance"),
                "intensite": data.get("intensite"),
                "intention": data.get("intention"),
                "vocalisation": data.get("vocalisation"),
            }
            validate_segment(segment, allow_unknown=True)
            annotated.append(segment)
    return {
        "version": VERSION,
        "chapitre": number,
        "source": path.name,
        "sha256_source": source_hash(path),
        "modele_analyse": model,
        "segments": annotated,
    }


def validate_segment(segment: dict, allow_unknown: bool = False) -> None:
    if not isinstance(segment, dict):
        raise ValueError("Un segment doit être un objet JSON.")
    for field in ("texte", "locuteur"):
        if not isinstance(segment.get(field), str) or not segment[field].strip():
            raise ValueError(f"Champ {field} vide ou invalide.")
    if not allow_unknown and segment["locuteur"].strip().upper() == "INCONNU":
        raise ValueError("Locuteur INCONNU : corrigez-le dans le fichier d'orientation.")
    if segment.get("type") not in ("chapitre", "narration", "dialogue"):
        raise ValueError("Type de segment invalide.")
    for field, low, high in (("valence", -1, 1), ("activation", 0, 1),
                             ("dominance", 0, 1), ("intensite", 0, 1)):
        value = segment.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{field} doit être un nombre entre {low} et {high}.")
    for field, values in (("emotion", EMOTIONS), ("intention", INTENTIONS),
                          ("vocalisation", VOCALISATIONS), ("fiabilite_locuteur", FIABILITE)):
        if segment.get(field) not in values:
            raise ValueError(f"{field} invalide : {segment.get(field)!r}")


def read_orientation(path: Path, source: Path, chapter: int, allow_unknown: bool = False) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != VERSION or data.get("chapitre") != chapter:
        raise ValueError(f"Version ou numéro de chapitre invalide : {path}")
    if data.get("source") != source.name or data.get("sha256_source") != source_hash(source):
        raise ValueError(f"Source modifiée depuis l'analyse : {source}. Régénérez l'orientation.")
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError(f"Aucun segment dans {path}")
    for expected, segment in enumerate(segments, 1):
        validate_segment(segment, allow_unknown=allow_unknown)
        if type(segment.get("id")) is not int or segment["id"] != expected:
            raise ValueError(f"Numérotation des segments incorrecte dans {path}.")
    if segments[0]["type"] != "chapitre":
        raise ValueError(f"Annonce du chapitre manquante dans {path}.")
    return data

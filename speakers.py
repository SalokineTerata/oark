"""Speaker attribution for dialogue lines: explicit attributions first, then a constrained local LLM."""

import json
import re
import unicodedata

import httpx
import ollama

# Canonical speaker -> spellings used in the manuscripts.
CAST = {
    "KODA": ("Koda",),
    "BORRAS": ("Borras",),
    "JARO": ("Jaro",),
    "BRICOLE": ("Bricole",),
    "ECHO": ("Écho", "ÉCHO", "Echo", "ECHO"),
    "LYSS": ("Lyss",),
    "ARLET": ("Arlet",),
    "VANE": ("Vane",),
    "NARA": ("Nara",),
    "SELI": ("Seli",),
    "ILYAN": ("Ilyan",),
    "SAÏR": ("Saïr",),
    "MÈRE": ("Mère",),
}
SPEECH_VERBS = (
    "dit", "demanda", "répondit", "reprit", "lança", "murmura", "ordonna", "ajouta", "souffla", "cria",
    "affirma", "répliqua", "chuchota", "rétorqua", "interrogea", "annonça", "déclara", "expliqua",
    "siffla", "gronda", "grogna", "lâcha", "conclut", "proposa", "insista", "précisa",
)
NAME = re.compile(
    r"(?<!\w)(" + "|".join(re.escape(s) for spellings in CAST.values() for s in spellings) + r")(?!\w)"
)
SPELLING = {s: canonical for canonical, spellings in CAST.items() for s in spellings}
ATTRIBUTION = re.compile(
    r"^(?:" + "|".join(SPEECH_VERBS) + r")(?:-t)?[- ](?P<who>[^\s,.;:!?]+)", re.IGNORECASE
)
OTHER = "AUTRE"


def present_cast(text: str) -> list[str]:
    found = {SPELLING[m.group(1)] for m in NAME.finditer(text)}
    return [name for name in CAST if name in found]


def explicit_speaker(narration: str) -> str | None:
    """Return the canonical speaker named right after a speech verb, if any."""
    match = ATTRIBUTION.match(narration.strip())
    if not match:
        return None
    return SPELLING.get(match.group("who"))


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def resolve_line(
    blocks: list[tuple[str, str, int | None]], labels: dict[int, str], index: int,
    cast: list[str], client: ollama.Client, model: str, excluded: set[str],
) -> tuple[str, str]:
    """Return (speaker, role). The role is only meaningful for AUTRE."""
    allowed = [name for name in cast if name not in excluded] + [OTHER]
    schema = {
        "type": "object",
        "properties": {"locuteur": {"type": "string", "enum": allowed}, "role": {"type": "string"}},
        "required": ["locuteur", "role"], "additionalProperties": False,
    }
    lines = []
    for i in range(max(0, index - 10), min(len(blocks), index + 3)):
        text, kind, _ = blocks[i]
        if i == index:
            lines.append(f">>> RÉPLIQUE À ATTRIBUER : {text}")
        elif kind == "dialogue":
            lines.append(f"[{labels.get(i, '?')}] {text}")
        else:
            lines.append(f"(narration) {text}")
    prompt = (
        "Tu identifies qui prononce une réplique dans un roman de science-fiction en français. "
        f"Personnages possibles : {', '.join(cast)}, ou {OTHER} pour un personnage secondaire "
        "(précise alors son rôle en un mot dans « role »). "
        "Règles : le locuteur n'est jamais la personne à qui l'on s'adresse ; un nom cité dans la "
        "réplique désigne en général son destinataire ; dans un échange sans narration entre les "
        "répliques, les deux interlocuteurs alternent ; le contexte de narration proche indique "
        "souvent qui prend la parole. Réponds uniquement en JSON.\n\n" + "\n".join(lines)
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = client.chat(
                model=model, messages=[{"role": "user", "content": prompt}], format=schema,
                options={"temperature": 0.2 * attempt, "num_ctx": 4096, "num_predict": 120},
            )
            data = json.loads(response.message.content or "")
            speaker = data["locuteur"]
            role = str(data.get("role", "")).strip()
            break
        except (ollama.ResponseError, ConnectionError, httpx.RequestError, json.JSONDecodeError, KeyError) as exc:
            last_error = exc
    else:
        raise RuntimeError(f"Attribution impossible au bloc {index + 1} : {last_error}") from last_error
    if speaker not in allowed:
        raise ValueError(f"Locuteur hors liste au bloc {index + 1} : {speaker!r}")
    return speaker, role


def alternate(blocks, labels: dict[int, str], index: int) -> tuple[str, str] | None:
    """Two-party exchange: the speaker is the one before the previous speaker."""
    def previous_dialogue(start: int, window: int) -> int | None:
        for i in range(start - 1, max(-1, start - 1 - window), -1):
            if blocks[i][1] == "dialogue":
                return i
        return None

    last = previous_dialogue(index, 2)
    if last is None or last not in labels:
        return None
    before = previous_dialogue(last, 2)
    if before is None or before not in labels or labels[before] == labels[last]:
        return None
    if labels[before] not in CAST:
        return None
    return labels[before], ""


def resolve_chapter(
    blocks: list[tuple[str, str, int | None]], explicit: dict[int, str],
    client: ollama.Client, model: str, progress=None,
) -> dict[int, tuple[str, str, str]]:
    """Map each dialogue block index to (speaker, role, reliability)."""
    cast = present_cast(" ".join(text for text, _, _ in blocks))
    labels: dict[int, str] = {}
    result: dict[int, tuple[str, str, str]] = {}
    for index, (text, kind, continuation) in enumerate(blocks):
        if kind != "dialogue":
            continue
        if continuation is not None:
            result[index] = (*result[continuation][:2], result[continuation][2])
        elif index in explicit:
            result[index] = (explicit[index], "", "explicite")
        else:
            excluded = set()
            previous = index - 1
            if previous in result and blocks[previous][1] == "dialogue" and previous in labels:
                excluded.add(labels[previous])
            speaker, role = alternate(blocks, labels, index) or resolve_line(
                blocks, labels, index, cast, client, model, excluded)
            result[index] = (speaker, role, "deduit")
        speaker, role, _ = result[index]
        labels[index] = role.upper() if speaker == OTHER and role else speaker
        if progress:
            progress()
    return result

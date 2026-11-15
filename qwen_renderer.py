"""Expressive local rendering with Qwen3-TTS CustomVoice, resumable chapter by chapter."""

import hashlib
import json
import os
from pathlib import Path
import re
import zlib

import numpy as np
from pydub import AudioSegment
from tqdm import tqdm

from assembler import assemble
from orientation import atomic_json, read_orientation

RENDER_VERSION = "qwen-v1"
MODEL_DIR = Path(__file__).resolve().parent / "models" / "Qwen3-TTS-1.7B-CustomVoice-fp16"
SAMPLE_RATE = 24000
BATCH = 8
MAX_CHARS = 240

# Native timbres of the model (Chinese, English, Japanese, Korean speakers reading French).
DEFAULT_TIMBRES = {
    "NARRATEUR": "uncle_fu", "KODA": "ono_anna", "BORRAS": "dylan", "JARO": "ryan",
    "BRICOLE": "aiden", "ECHO": "eric", "LYSS": "sohee", "MÈRE": "vivian",
    "VANE": "ryan", "ARLET": "dylan", "NARA": "vivian", "SELI": "vivian",
    "ILYAN": "dylan", "SAÏR": "aiden",
}
SECONDARY_TIMBRES = ("ryan", "vivian", "aiden", "dylan", "sohee")
TIMBRES = {"aiden", "dylan", "eric", "ono_anna", "ryan", "serena", "sohee", "uncle_fu", "vivian"}
DEFAULT_CHARACTER = {
    "NARRATEUR": "a calm, deep, warm storyteller voice",
    "KODA": "a determined young woman",
    "BORRAS": "a gruff, tired man",
    "JARO": "a bold man",
    "BRICOLE": "a quick, curious, youthful voice",
    "ECHO": "a calm, slightly artificial, precise voice",
    "LYSS": "a sharp, guarded woman",
    "MÈRE": "a mature, caring woman",
    "VANE": "a hard, authoritative man",
    "ARLET": "a deep, steady older man",
    "NARA": "a soft-spoken woman",
    "SELI": "a light, nervous voice",
    "ILYAN": "a deep, measured man",
    "SAÏR": "a young, tense man",
}
EMOTION = {
    "neutre": "neutral", "interet": "curious", "joie": "joyful", "plaisir": "pleased", "amour": "tender",
    "admiration": "admiring", "soulagement": "relieved", "fierte": "proud", "espoir": "hopeful",
    "compassion": "compassionate", "tristesse": "sad", "peur": "frightened", "colere": "angry",
    "degout": "disgusted", "mepris": "contemptuous", "honte": "ashamed", "culpabilite": "guilty",
    "regret": "regretful", "deception": "disappointed", "inquietude": "anxious",
    "surprise": "surprised", "confusion": "confused", "ennui": "bored",
}
INTENTION = {
    "questionner": "asking a question", "ordonner": "giving an order", "rassurer": "reassuring",
    "persuader": "persuading", "avertir": "warning", "menacer": "threatening",
    "protester": "protesting", "plaisanter": "joking", "hesiter": "hesitating",
    "confier": "confiding quietly", "saluer": "greeting", "remercier": "thanking",
}
VOCALISATION = {
    "chuchotement": "whispering softly", "cri": "shouting loudly", "rire": "laughing while speaking",
    "sanglot": "voice breaking, sobbing between words", "soupir": "sighing wearily while speaking",
}


def load_profiles(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Le fichier des voix doit être un objet JSON : {path}")
    for speaker, profile in data.items():
        if not isinstance(speaker, str) or not speaker or speaker != speaker.strip().upper():
            raise ValueError(f"Nom de locuteur invalide dans {path} : {speaker!r}")
        if not isinstance(profile, dict) or profile.get("timbre") not in TIMBRES or not isinstance(profile.get("caractere"), str):
            raise ValueError(f"Profil vocal invalide pour {speaker} dans {path} (timbre parmi {sorted(TIMBRES)}).")
    return data


def ensure_profiles(path: Path, speakers: set[str]) -> None:
    profiles = load_profiles(path)
    for speaker in sorted(speakers - profiles.keys() - {"INCONNU"}):
        if speaker in DEFAULT_TIMBRES:
            timbre, character = DEFAULT_TIMBRES[speaker], DEFAULT_CHARACTER[speaker]
        else:
            timbre = SECONDARY_TIMBRES[zlib.crc32(speaker.encode("utf-8")) % len(SECONDARY_TIMBRES)]
            character = f"a secondary character: {speaker.lower()}"
        profiles[speaker] = {"timbre": timbre, "caractere": character}
    atomic_json(path, profiles)


def instruction(segment: dict, profile: dict) -> str:
    """Turn the editable orientation into a natural-language delivery instruction."""
    if segment["type"] == "chapitre":
        return "Speak French with a calm, deep, warm storyteller voice. Announce the chapter title slowly and solemnly."
    level = segment["intensite"]
    degree = "slightly" if level < 0.35 else "clearly" if level < 0.7 else "intensely"
    parts = [f"Speak French with {profile['caractere']}."]
    if segment["type"] == "narration":
        parts.append("Narrate in a measured, literary tone.")
    emotion = EMOTION[segment["emotion"]]
    if emotion != "neutral":
        parts.append(f"The tone is {degree} {emotion}.")
    if segment["activation"] >= 0.7:
        parts.append("Fast, energetic pace.")
    elif segment["activation"] <= 0.3:
        parts.append("Slow, low-energy pace.")
    if segment["intention"] in INTENTION:
        parts.append(f"The speaker is {INTENTION[segment['intention']]}.")
    if segment["vocalisation"] in VOCALISATION:
        parts.append(f"Delivery: {VOCALISATION[segment['vocalisation']]}.")
    return " ".join(parts)


def split_text(text: str, limit: int = MAX_CHARS) -> list[str]:
    """Cut long text at sentence ends so each piece stays well within the model's stable range."""
    if len(text) <= limit:
        return [text]
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?…])\s+", text):
        while len(sentence) > limit:
            if current:
                pieces.append(current)
                current = ""
            boundary = sentence.rfind(" ", 0, limit + 1)
            if boundary <= 0:
                raise ValueError(f"Mot trop long pour la synthèse : {sentence[:limit]!r}")
            pieces.append(sentence[:boundary])
            sentence = sentence[boundary:].lstrip()
        if current and len(current) + len(sentence) + 1 > limit:
            pieces.append(current)
            current = ""
        current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


class Engine:
    def __init__(self) -> None:
        import torch
        from qwen_tts import Qwen3TTSModel

        if not MODEL_DIR.is_dir():
            raise RuntimeError(f"Modèle Qwen3-TTS manquant : {MODEL_DIR}")
        if not torch.cuda.is_available():
            raise RuntimeError("GPU CUDA indisponible : le rendu Qwen3-TTS serait impraticable.")
        self.torch = torch
        self.model = Qwen3TTSModel.from_pretrained(str(MODEL_DIR), device_map="cuda:0", dtype=torch.float16)

    def speak(self, jobs: list[tuple[str, str, str]]) -> list[np.ndarray]:
        """jobs: (text, timbre, instruction). Returns mono float arrays at SAMPLE_RATE."""
        results: list[np.ndarray | None] = [None] * len(jobs)
        order = sorted(range(len(jobs)), key=lambda i: len(jobs[i][0]))
        for start in range(0, len(order), BATCH):
            group = order[start:start + BATCH]
            for attempt in range(3):
                pending = [i for i in group if results[i] is None]
                if not pending:
                    break
                self.torch.manual_seed(1234 + attempt)
                longest = max(len(jobs[i][0]) for i in pending)
                wavs, rate = self.model.generate_custom_voice(
                    text=[jobs[i][0] for i in pending], language=["French"] * len(pending),
                    speaker=[jobs[i][1] for i in pending], instruct=[jobs[i][2] for i in pending],
                    max_new_tokens=int(longest * 1.6) + 60,
                )
                if rate != SAMPLE_RATE:
                    raise RuntimeError(f"Fréquence inattendue : {rate}")
                for i, wav in zip(pending, wavs):
                    seconds = len(wav) / rate
                    chars = len(jobs[i][0])
                    if 0.035 * chars <= seconds <= 0.2 * chars + 3:
                        results[i] = np.asarray(wav, dtype=np.float32)
            self.torch.cuda.empty_cache()
        missing = [i for i, wav in enumerate(results) if wav is None]
        if missing:
            raise RuntimeError(f"Audio de durée aberrante après 3 essais pour : {jobs[missing[0]][0][:80]!r}")
        return results  # type: ignore[return-value]


def pause_ms(previous: dict | None, current: dict) -> int:
    if previous is None:
        return 0
    if previous["type"] == "chapitre":
        return 1000
    return 450 if previous["type"] != current["type"] else 250


def render_chapter(segments: list[dict], profiles: dict[str, dict], engine: Engine, target: Path) -> None:
    jobs, owners = [], []
    for index, segment in enumerate(segments):
        profile = profiles[segment["locuteur"]]
        for piece in split_text(segment["texte"]):
            jobs.append((piece, profile["timbre"], instruction(segment, profile)))
            owners.append(index)
    audio = engine.speak(jobs)
    track = AudioSegment.empty()
    previous = None
    for index, segment in enumerate(segments):
        pieces = [audio[j] for j, owner in enumerate(owners) if owner == index]
        gap = np.zeros(int(SAMPLE_RATE * 0.12), dtype=np.float32)
        wave = np.concatenate([np.concatenate([p, gap]) for p in pieces])
        pcm = (np.clip(wave, -1, 1) * 32767).astype(np.int16)
        clip = AudioSegment(pcm.tobytes(), frame_rate=SAMPLE_RATE, sample_width=2, channels=1)
        track += AudioSegment.silent(pause_ms(previous, segment), frame_rate=SAMPLE_RATE) + clip
        previous = segment
    if len(track) < 500:
        raise RuntimeError("Le chapitre audio est vide.")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp.mp3")
    with track.export(temporary, format="mp3", bitrate="64k"):
        pass
    os.replace(temporary, target)


def validate(path: Path, source: Path, index: int, profiles: dict[str, dict]) -> dict:
    data = read_orientation(path, source, index)
    for segment in data["segments"]:
        if segment["locuteur"] not in profiles:
            raise ValueError(f"Voix manquante pour {segment['locuteur']}")
        instruction(segment, profiles[segment["locuteur"]])
    return data


def render_book(root: Path, number: str, paths: list[Path], engine: Engine | None = None) -> Path:
    directory = root / "exports" / "orientations" / f"Livre-{number}"
    profiles = load_profiles(root / "exports" / "orientations" / "voix.json")
    documents = [validate(directory / f"chapitre-{i:03d}.json", source, i, profiles)
                 for i, source in enumerate(paths, 1)]
    cache = root / "exports" / "temp_audio" / f"qwen-livre-{number}"
    cache.mkdir(parents=True, exist_ok=True)
    chapters = []
    for index, data in enumerate(tqdm(documents, desc=f"Livre {number}", unit="chapitre"), 1):
        key = json.dumps([RENDER_VERSION, data, profiles], ensure_ascii=False, sort_keys=True).encode("utf-8")
        chapter = cache / f"chapitre-{index:03d}-{hashlib.sha256(key).hexdigest()}.mp3"
        chapters.append(chapter)
        if chapter.is_file() and chapter.stat().st_size:
            print(f"Livre {number}, chapitre {index} : reprise du fichier existant.", flush=True)
            continue
        engine = engine or Engine()
        print(f"Livre {number}, chapitre {index}/{len(paths)} : {data['segments'][0]['texte']}", flush=True)
        render_chapter(data["segments"], profiles, engine, chapter)
    target = root / "exports" / f"Livre-{number}_Audiobook.mp3"
    assemble(chapters, target, silence_ms=1200)
    return target

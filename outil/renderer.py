"""Render approved orientation documents using an offline Piper voice model."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import onnxruntime
from piper import PiperVoice, SynthesisConfig
from piper.config import PiperConfig
from pydub import AudioSegment
from tqdm import tqdm

from assembler import assemble
from orientation import atomic_json, read_orientation

VOICE_NAME = "fr_FR-mls-medium"
SPEAKER_COUNT = 125
RENDER_VERSION = "orientation-v1"


def load_profiles(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Le fichier des voix doit être un objet JSON : {path}")
    used = set()
    for speaker, speaker_id in data.items():
        if not isinstance(speaker, str) or not speaker.strip() or speaker != speaker.strip().upper():
            raise ValueError(f"Nom de locuteur invalide dans {path} : {speaker!r}")
        if isinstance(speaker_id, bool) or not isinstance(speaker_id, int) or not 0 <= speaker_id < SPEAKER_COUNT:
            raise ValueError(f"Identifiant vocal invalide pour {speaker} dans {path}.")
        if speaker_id in used:
            raise ValueError(f"La voix {speaker_id} est attribuée à plusieurs locuteurs dans {path}.")
        used.add(speaker_id)
    return data


def ensure_profiles(path: Path, speakers: set[str]) -> None:
    profiles = load_profiles(path)
    used = set(profiles.values())
    for speaker in sorted(speakers - profiles.keys() - {"INCONNU"}):
        available = next((i for i in range(SPEAKER_COUNT) if i not in used), None)
        if available is None:
            raise ValueError(f"Plus de {SPEAKER_COUNT} locuteurs distincts : choisissez d'autres modèles vocaux.")
        profiles[speaker] = available
        used.add(available)
    atomic_json(path, profiles)


def load_voice(directory: Path) -> PiperVoice:
    model = directory / f"{VOICE_NAME}.onnx"
    config = directory / f"{VOICE_NAME}.onnx.json"
    if not model.is_file() or not config.is_file():
        raise RuntimeError(f"Modèle Piper manquant : {model} ou {config}")
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = onnxruntime.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
    return PiperVoice(session=session, config=PiperConfig.from_dict(json.loads(config.read_text(encoding="utf-8"))),
                      download_dir=directory)


def prosody(segment: dict) -> tuple[float, float, float]:
    intensity = segment["intensite"]
    activation = segment["activation"]
    dominance = segment["dominance"]
    valence = segment["valence"]
    rate = 1 + (activation - 0.5) * 0.32 * intensity
    semitones = (0.8 * valence + 0.9 * (activation - 0.5) + 0.4 * (dominance - 0.5)) * intensity
    gain = (activation - 0.5) * 6 * intensity + (dominance - 0.5) * 2 * intensity
    if segment["emotion"] in ("tristesse", "regret", "deception"):
        rate *= 1 - 0.06 * intensity
        semitones -= 0.3 * intensity
    elif segment["emotion"] in ("joie", "colere", "surprise"):
        rate *= 1 + 0.04 * intensity
        semitones += 0.3 * intensity
    if segment["intention"] == "questionner":
        semitones += 0.3 * intensity
    elif segment["intention"] == "hesiter":
        rate *= 1 - 0.08 * intensity
    if segment["type"] == "narration":
        rate *= 0.95
        gain -= 0.5
    if segment["vocalisation"] == "chuchotement":
        gain -= 4
        rate *= 0.9
    elif segment["vocalisation"] == "cri":
        gain += 3
        rate *= 1.05
    elif segment["vocalisation"] != "parole":
        raise ValueError(f"Vocalisation non prise en charge par Piper : {segment['vocalisation']}")
    return rate, 2 ** (semitones / 12), gain


def synthesize_chapter(segments: list[dict], profiles: dict[str, int], voice: PiperVoice, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="audio-", dir=target.parent) as temp:
        output = Path(temp) / "chapter.mp3"
        errors = Path(temp) / "ffmpeg.log"
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "s16le", "-ar", "22050", "-ac", "1", "-i", "pipe:0",
            "-codec:a", "libmp3lame", "-b:a", "64k", str(output),
        ]
        with errors.open("w+", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
            assert process.stdin is not None
            try:
                for index, segment in enumerate(tqdm(segments, desc="Synthèse locale", unit="segment")):
                    rate, pitch, gain = prosody(segment)
                    if index:
                        pause = 750 if index == 1 else 200
                        process.stdin.write(b"\0\0" * (22050 * pause // 1000))
                    found = False
                    config = SynthesisConfig(speaker_id=profiles[segment["locuteur"]], length_scale=pitch / rate)
                    for chunk in voice.synthesize(segment["texte"], syn_config=config):
                        found = True
                        audio = AudioSegment(chunk.audio_int16_bytes, frame_rate=chunk.sample_rate,
                                             sample_width=2, channels=1)
                        audio = audio._spawn(audio.raw_data, overrides={"frame_rate": round(chunk.sample_rate * pitch)})
                        process.stdin.write(audio.set_frame_rate(22050).normalize(headroom=6).apply_gain(gain).raw_data)
                    if not found:
                        raise RuntimeError(f"Aucun audio pour le segment {index + 1}.")
                process.stdin.close()
                code = process.wait()
            except BaseException:
                try:
                    process.stdin.close()
                except OSError:
                    pass
                if process.poll() is None:
                    process.terminate()
                process.wait()
                raise
            if code:
                log.seek(0)
                raise RuntimeError(f"Échec FFmpeg : {log.read()}")
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("Le chapitre audio est vide.")
        os.replace(output, target)


def render_book(root: Path, number: str, paths: list[Path], voice: PiperVoice, automatic: bool = False) -> Path:
    directory = root / "exports-audiobook" / "orientations" / f"Livre-{number}"
    profiles_path = root / "voix" / "voix.json"
    profiles = load_profiles(profiles_path)
    documents = []
    for index, source in enumerate(paths, 1):
        path = directory / f"chapitre-{index:03d}.json"
        data = read_orientation(path, source, index)
        for segment in data["segments"]:
            if segment["locuteur"] not in profiles:
                raise ValueError(f"Voix manquante pour {segment['locuteur']} dans {profiles_path}")
            prosody(segment)
        documents.append(data)
    cache = root / "exports-audiobook" / "temp_audio" / f"orientation-livre-{number}"
    cache.mkdir(parents=True, exist_ok=True)
    chapters = []
    for index, data in enumerate(documents, 1):
        key = json.dumps([RENDER_VERSION, data, profiles, automatic], ensure_ascii=False, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(key).hexdigest()
        chapter = cache / f"chapitre-{index:03d}-{digest}.mp3"
        chapters.append(chapter)
        if chapter.is_file() and chapter.stat().st_size:
            print(f"Livre {number}, chapitre {index} : reprise du fichier existant.", flush=True)
            continue
        print(f"Livre {number}, chapitre {index}/{len(paths)} : {data['segments'][0]['texte']}", flush=True)
        synthesize_chapter(data["segments"], profiles, voice, chapter)
    target = root / "exports-audiobook" / f"Livre-{number}_Audiobook.mp3"
    assemble(chapters, target, silence_ms=1200)
    for chapter in chapters:
        chapter.unlink()
    return target

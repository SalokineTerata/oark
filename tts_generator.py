"""Generate one French speech MP3 per diarized segment."""

import asyncio
from pathlib import Path

import aiohttp
import edge_tts
from edge_tts.exceptions import EdgeTTSException
from tqdm import tqdm

VOICES = {
    "[NARRATEUR]": "fr-FR-HenriNeural",
    "[KODA]": "fr-FR-DeniseNeural",
    "[BORRAS]": "fr-FR-RemyMultilingualNeural",
    "[VANE]": "fr-CA-AntoineNeural",
    "[JARO]": "fr-CH-FabriceNeural",
}


async def check_voices() -> None:
    async def probe(voice: str) -> bool:
        audio_received = False
        async for chunk in edge_tts.Communicate("Test.", voice).stream():
            if chunk["type"] == "audio" and chunk["data"]:
                audio_received = True
        return audio_received

    for voice in tqdm(VOICES.values(), desc="Vérification des voix", unit="voix"):
        for attempt in range(3):
            try:
                if not await asyncio.wait_for(probe(voice), timeout=30):
                    raise RuntimeError(f"Aucun audio reçu pour la voix {voice}.")
                break
            except (aiohttp.ClientError, OSError, asyncio.TimeoutError, EdgeTTSException) as exc:
                if attempt == 2:
                    raise RuntimeError(f"Voix Edge TTS inaccessible ({voice}) : {exc}") from exc
                tqdm.write(f"Voix {voice} inaccessible, nouvelle tentative : {exc}")
                await asyncio.sleep(2 ** attempt)


async def generate_audio(segments: list[tuple[str, str]], directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for index, (speaker, text) in enumerate(tqdm(segments, desc="Synthèse vocale", unit="segment"), 1):
        if speaker not in VOICES:
            raise ValueError(f"Locuteur inconnu au segment {index} : {speaker}")
        path = directory / f"{index:04d}_{speaker.strip('[]')}.mp3"
        for attempt in range(3):
            try:
                await edge_tts.Communicate(text, VOICES[speaker]).save(str(path))
                break
            except (aiohttp.ClientError, OSError, asyncio.TimeoutError, EdgeTTSException) as exc:
                if attempt == 2:
                    raise RuntimeError(f"Échec Edge TTS au segment {index} ({speaker}) : {exc}") from exc
                tqdm.write(f"Échec Edge TTS au segment {index}, nouvelle tentative : {exc}")
                await asyncio.sleep(2 ** attempt)
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Fichier audio vide pour le segment {index} : {path}")
        files.append(path)
    if not files:
        raise ValueError("Aucun segment audio à générer.")
    return files

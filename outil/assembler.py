"""Assemble speech segments without holding an entire audiobook in memory."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from tqdm import tqdm


def assemble(files: list[Path], target: Path, silence_ms: int = 200) -> None:
    if not files:
        raise ValueError("Aucun fichier audio à assembler.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg est introuvable. Installez-le et ajoutez-le au PATH.")
    target.parent.mkdir(parents=True, exist_ok=True)
    silence = AudioSegment.silent(duration=silence_ms, frame_rate=24000).set_channels(1).set_sample_width(2)
    with tempfile.TemporaryDirectory(prefix="oark-assembly-", dir=target.parent) as temp:
        output = Path(temp) / "audiobook.mp3"
        errors = Path(temp) / "ffmpeg.log"
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "pipe:0",
            "-codec:a", "libmp3lame", "-b:a", "64k", "-f", "mp3", str(output),
        ]
        with errors.open("w+", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
            assert process.stdin is not None
            try:
                for index, path in enumerate(tqdm(files, desc="Assemblage", unit="segment")):
                    try:
                        audio = AudioSegment.from_mp3(path).set_frame_rate(24000).set_channels(1).set_sample_width(2)
                    except CouldntDecodeError as exc:
                        raise RuntimeError(f"Impossible de décoder le segment {path} : {exc}") from exc
                    if index:
                        process.stdin.write(silence.raw_data)
                    process.stdin.write(audio.raw_data)
                process.stdin.close()
                returncode = process.wait()
            except BrokenPipeError as exc:
                try:
                    process.stdin.close()
                except OSError:
                    pass
                process.wait()
                log.seek(0)
                raise RuntimeError(f"Échec FFmpeg pendant l'assemblage : {log.read()}") from exc
            except BaseException:
                try:
                    process.stdin.close()
                except OSError:
                    pass
                if process.poll() is None:
                    process.terminate()
                process.wait()
                raise
            if returncode:
                log.seek(0)
                raise RuntimeError(f"Échec FFmpeg (code {returncode}) : {log.read()}")
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("FFmpeg n'a pas produit de livre audio.")
        os.replace(output, target)

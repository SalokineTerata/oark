"""Download the local TTS models into D:\\dev\\Oark-Copilot\\models, retrying on network errors."""

from pathlib import Path
import sys
import time

from huggingface_hub import snapshot_download

MODELS = {
    "Qwen3-TTS-12Hz-1.7B-CustomVoice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen3-TTS-Tokenizer-12Hz": "Qwen/Qwen3-TTS-Tokenizer-12Hz",
}


def main() -> None:
    root = Path(__file__).resolve().parent / "models"
    names = sys.argv[1:] or list(MODELS)
    for name in names:
        for attempt in range(1, 61):
            try:
                snapshot_download(MODELS[name], local_dir=root / name, max_workers=2)
                print(f"OK {name}", flush=True)
                break
            except Exception as exc:  # network interruptions are expected
                print(f"{name} tentative {attempt} : {type(exc).__name__}", flush=True)
                time.sleep(5)
        else:
            raise SystemExit(f"Téléchargement impossible : {name}")


if __name__ == "__main__":
    main()

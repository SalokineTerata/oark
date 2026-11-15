#!/usr/bin/env python3
"""Generate V2 charcoal-and-pastel illustrations via local ComfyUI with strict GPU thermal guard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
V2_ILLUST = ROOT / "exports-v2" / "illustrations"
MANIFEST = V2_ILLUST / "manifest_v2.json"
BOOK_FOLDERS = {"I": "livre-i", "II": "livre-ii", "III": "livre-iii"}
MAX_GPU_TEMP_C = 85
COOLDOWN_TARGET_C = 79


def get_gpu_temp() -> int:
    out = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
        text=True,
        timeout=5,
    ).strip()
    return int(out.splitlines()[0].strip())


def ensure_thermal_margin() -> None:
    temp = get_gpu_temp()
    if temp < MAX_GPU_TEMP_C:
        return
    print(f"[THERMAL GUARD] GPU à {temp} °C (>= {MAX_GPU_TEMP_C} °C). Pause refroidissement jusqu'à <= {COOLDOWN_TARGET_C} °C...", flush=True)
    waited = 0
    while waited < 180:
        time.sleep(5)
        waited += 5
        temp = get_gpu_temp()
        if temp <= COOLDOWN_TARGET_C:
            print(f"[THERMAL GUARD] GPU refroidi à {temp} °C. Reprise.", flush=True)
            return
    raise RuntimeError(f"Arrêt de sécurité thermique : GPU resté à {temp} °C après 180 s.")


def request_json(url: str, data: dict | None = None) -> dict:
    payload = None if data is None else json.dumps(data).encode("utf-8")
    headers = {} if payload is None else {"Content-Type": "application/json"}
    with urlopen(Request(url, data=payload, headers=headers), timeout=30) as response:
        return json.load(response)


def wait_for_server(server: str, timeout_s: int = 60) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            request_json(server + "/system_stats")
            return
        except Exception:
            time.sleep(1.5)
    raise RuntimeError(f"Serveur ComfyUI injoignable sur {server} après {timeout_s} s.")


def workflow(model: str, prompt: str, negative: str, seed: int) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "DreamShaper_8_pruned.safetensors"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": negative}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 512, "batch_size": 1}},
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "seed": seed,
                "steps": 18,
                "cfg": 7.0,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
            },
        },
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "oark_v2", "images": ["7", 0]}},
    }


def valid_png(data: bytes) -> bool:
    return (
        len(data) >= 24
        and data[:8] == b"\x89PNG\r\n\x1a\n"
        and data[12:16] == b"IHDR"
        and struct.unpack(">II", data[16:24]) == (768, 512)
        and b"IEND" in data[-16:]
    )


def generate_one(server: str, model: str, prompt: str, negative: str, seed: int) -> bytes:
    ensure_thermal_margin()
    resp = request_json(server + "/prompt", {"prompt": workflow(model, prompt, negative, seed)})
    prompt_id = resp["prompt_id"]
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        history = request_json(server + "/history/" + prompt_id)
        if prompt_id in history:
            result = history[prompt_id]
            status = result.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"Erreur ComfyUI : {status.get('messages')}")
            img = result["outputs"]["8"]["images"][0]
            q = urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")})
            with urlopen(server + "/view?" + q, timeout=30) as r:
                data = r.read()
            if not valid_png(data):
                raise RuntimeError("PNG invalide renvoyé par ComfyUI.")
            return data
        time.sleep(0.8)
    raise RuntimeError(f"Timeout ComfyUI pour {prompt_id}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--book", choices=("I", "II", "III"))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    wait_for_server(args.server)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    model = manifest["model"]
    style = manifest["style"]
    negative = manifest["negative"]

    done = 0
    for idx, item in enumerate(manifest["illustrations"], 1):
        if args.book and item["book"] != args.book:
            continue
        folder = V2_ILLUST / BOOK_FOLDERS[item["book"]]
        folder.mkdir(parents=True, exist_ok=True)
        out_png = folder / f"{item['id']}.png"
        out_jpg = folder / f"{item['id']}.jpg"
        if out_png.exists() or out_jpg.exists():
            continue
        full_prompt = (
            f"{item['prompt']}, "
            f"(charcoal sketch and soft pastel illustration:1.2), "
            f"expressive hand-drawn strokes, textured paper grain, "
            f"restrained palette of ochre, slate blue, charcoal grey and muted amber"
        )
        seed = 202600 + idx
        data = generate_one(args.server, model, full_prompt, negative, seed)
        out_png.write_bytes(data)
        done += 1
        temp = get_gpu_temp()
        print(f"[{done}] Livre {item['book']} {item['id']}.png généré (GPU: {temp} °C)", flush=True)
        time.sleep(3.5)  # thermal breath between renders
        if args.limit and done >= args.limit:
            break

    print(f"Terminé : {done} illustrations générées.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)

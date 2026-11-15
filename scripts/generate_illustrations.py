#!/usr/bin/env python3
"""Generate chapter illustrations using a local ComfyUI server."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "illustrations" / "manifest.json"
NEGATIVE = (
    "text, letters, watermark, logo, caption, speech bubble, comic panel, "
    "flag, national flag, insignia, patches, astronaut, NASA, "
    "extra limbs, malformed hands, blurry, low quality"
)


def request_json(url: str, data: dict | None = None) -> dict:
    payload = None if data is None else json.dumps(data).encode("utf-8")
    headers = {} if payload is None else {"Content-Type": "application/json"}
    with urlopen(Request(url, data=payload, headers=headers), timeout=30) as response:
        return json.load(response)


def workflow(model: str, prompt: str, seed: int, negative: str = NEGATIVE) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model}},
        "2": {"class_type": "ModelSamplingDiscrete", "inputs": {
            "model": ["1", 0], "sampling": "lcm", "zsnr": False,
        }},
        "3": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["1", 1], "text": prompt,
        }},
        "4": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["1", 1], "text": negative,
        }},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "width": 768, "height": 512, "batch_size": 1,
        }},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "seed": seed, "steps": 6, "cfg": 1.8,
            "sampler_name": "lcm", "scheduler": "normal", "denoise": 1.0,
            "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
        }},
        "7": {"class_type": "VAEDecode", "inputs": {
            "samples": ["6", 0], "vae": ["1", 2],
        }},
        "8": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": "oark", "images": ["7", 0],
        }},
    }


def valid_png(data: bytes) -> bool:
    return (
        len(data) >= 24
        and data[:8] == b"\x89PNG\r\n\x1a\n"
        and data[12:16] == b"IHDR"
        and struct.unpack(">II", data[16:24]) == (768, 512)
        and b"IEND" in data[-16:]
    )


def generate(server: str, model: str, entry: dict) -> bytes:
    response = request_json(server + "/prompt", {
        "prompt": workflow(model, entry["prompt"], entry["seed"], entry.get("negative", NEGATIVE)),
    })
    prompt_id = response.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI a refusé la génération : {response}")
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        history = request_json(server + "/history/" + prompt_id)
        if prompt_id in history:
            result = history[prompt_id]
            status = result.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"Échec ComfyUI pour {prompt_id} : {status.get('messages')}")
            images = result.get("outputs", {}).get("8", {}).get("images", [])
            if len(images) != 1:
                raise RuntimeError(f"ComfyUI n'a pas produit exactement une image : {result}")
            image = images[0]
            query = urlencode({
                "filename": image["filename"],
                "subfolder": image.get("subfolder", ""),
                "type": image.get("type", "output"),
            })
            with urlopen(server + "/view?" + query, timeout=30) as response:
                data = response.read()
            if not valid_png(data):
                raise RuntimeError("ComfyUI a renvoyé un PNG incomplet ou de dimensions incorrectes.")
            return data
        time.sleep(2)
    raise RuntimeError(f"Délai dépassé pour la génération ComfyUI {prompt_id}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Générer les illustrations avec ComfyUI.")
    parser.add_argument("--server", default="http://127.0.0.1:8188", help="Adresse du serveur local ComfyUI.")
    parser.add_argument("--book", choices=("I", "II", "III"), help="Ne traiter qu'un livre.")
    parser.add_argument("--chapter", type=int, help="Ne traiter qu'un chapitre (nécessite --book).")
    parser.add_argument("--force", action="store_true", help="Régénérer les images déjà présentes.")
    args = parser.parse_args()
    if args.chapter is not None and (not args.book or args.chapter < 1):
        parser.error("--chapter exige --book et un numéro positif.")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    model = manifest["model"]
    entries = []
    for book, scenes in manifest["books"].items():
        for number, item in enumerate(scenes, 1):
            if (args.book and book != args.book) or (args.chapter is not None and number != args.chapter):
                continue
            if isinstance(item, str):
                scene = item
                seed = manifest["seed_bases"][book] + number
                negative = NEGATIVE
            elif isinstance(item, dict):
                scene = item["scene"]
                seed = item["seed"]
                negative = item.get("negative", NEGATIVE)
            else:
                raise ValueError(f"Scène invalide : livre {book}, chapitre {number}.")
            if (not isinstance(scene, str) or not scene.strip() or type(seed) is not int
                    or seed < 0 or not isinstance(negative, str) or not negative.strip()):
                raise ValueError(f"Scène ou graine invalide : livre {book}, chapitre {number}.")
            entries.append({
                "book": book,
                "chapter": number,
                "seed": seed,
                "prompt": scene + " " + manifest["style"],
                "negative": negative,
            })
    if not entries:
        raise RuntimeError("Aucun chapitre correspondant dans le manifeste.")
    server = args.server.rstrip("/")
    info = request_json(server + "/object_info/CheckpointLoaderSimple")
    models = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    if model not in models:
        raise RuntimeError(f"Modèle absent des checkpoints ComfyUI : {model}")

    for entry in entries:
        target = ROOT / "illustrations" / f"livre-{entry['book'].lower()}" / f"{entry['chapter']:03d}.png"
        if target.exists() and not args.force:
            if not valid_png(target.read_bytes()):
                raise RuntimeError(f"Image existante invalide : {target} (utiliser --force).")
            print(f"Conservée : {target}", flush=True)
            continue
        print(f"Génération : livre {entry['book']}, chapitre {entry['chapter']}...", flush=True)
        data = generate(server, model, entry)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".png.part")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        print(f"Créée : {target}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, OSError, RuntimeError, KeyError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)

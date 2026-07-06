"""Generate 'voice of the model' narration audio from a narration script.

THE voice is fixed: River (ElevenLabs voice_id SAz9YHcvj6GT2YYXdXww) — never
change it; it is the brand's audio identity (docs/growth/BRAND.md).

Usage:
    python scripts/generate_narration.py docs/growth/posts/<post>-narration.txt

Writes the MP3 next to the assets and copies it to Desktop/SecondBounce_Brand
for Aaron to attach in the Substack editor (+ menu -> Audio).
"""

import os
import shutil
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

VOICE_ID = "SAz9YHcvj6GT2YYXdXww"  # River — the fixed voice of the model
MODEL_ID = "eleven_multilingual_v2"
# style kept at 0.0: higher values make the voice add stray words (a phantom
# trailing "The" appeared on a 2026-07-06 close). Verify with STT after gen.
SETTINGS = {"stability": 0.6, "similarity_boost": 0.75, "style": 0.0}


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY missing from .env")

    src = Path(sys.argv[1])
    text = src.read_text(encoding="utf-8")
    name = src.stem.replace("-narration", "") + "-voice-of-the-model.mp3"
    out = root / "docs/growth/posts/assets" / name

    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        "?output_format=mp3_44100_128",
        headers={"xi-api-key": key},
        json={"text": text, "model_id": MODEL_ID, "voice_settings": SETTINGS},
        timeout=300,
    )
    r.raise_for_status()
    out.write_bytes(r.content)

    desktop = Path.home() / "Desktop" / "SecondBounce_Brand"
    if desktop.exists():
        shutil.copy(out, desktop / name)
    print(f"narration saved: {out.name} ({len(r.content)//1024} KB, "
          f"~{len(text)} credits used)")


if __name__ == "__main__":
    main()

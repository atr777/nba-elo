"""Transcribe a generated narration and diff it against the script it came from.

generate_narration.py has said "verify with STT after gen" since a phantom trailing
"The" turned up on a 2026-07-06 close, but nothing did the verifying. This does.
Voice models drop and invent words, and the failure lands in a published MP3 where
nobody re-reads it.

    python scripts/verify_narration.py docs/growth/posts/<post>-narration.txt

Compares the transcript to the source and reports the differences, with extra
attention to the LAST few words, which is where the artefact appeared.
"""

import difflib
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
MODEL = "scribe_v1"


def normalise(text: str) -> list[str]:
    """Compare meaning, not punctuation. The narration script spells numbers out, so
    a transcript saying "657" where the script says "six hundred and fifty-seven" is
    a real difference worth seeing, not noise to be smoothed away."""
    text = text.lower().replace("-", " ")
    return re.findall(r"[a-z0-9']+", text)


def main() -> None:
    load_dotenv(ROOT / ".env")
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY missing from .env")

    src = Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"no such narration script: {src}")
    mp3 = (ROOT / "docs/growth/posts/assets"
           / (src.stem.replace("-narration", "") + "-voice-of-the-model.mp3"))
    if not mp3.exists():
        sys.exit(f"no audio to verify at {mp3}; run generate_narration.py first")

    print(f"transcribing {mp3.name} ({mp3.stat().st_size // 1024}KB)...")
    with mp3.open("rb") as fh:
        r = requests.post(STT_URL, headers={"xi-api-key": key},
                          files={"file": (mp3.name, fh, "audio/mpeg")},
                          data={"model_id": MODEL}, timeout=600)
    if r.status_code >= 400:
        sys.exit(f"STT failed HTTP {r.status_code}: {r.text[:300]}")
    heard = (r.json() or {}).get("text", "")
    if not heard:
        sys.exit("STT returned no text")

    want, got = normalise(src.read_text(encoding="utf-8")), normalise(heard)
    sm = difflib.SequenceMatcher(None, want, got)
    print(f"script {len(want)} words, heard {len(got)} words, "
          f"similarity {sm.ratio() * 100:.2f}%")

    diffs = [(tag, want[i1:i2], got[j1:j2])
             for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]
    if not diffs:
        print("EXACT MATCH. Nothing added, nothing dropped.")
    else:
        print(f"\n{len(diffs)} difference(s):")
        for tag, a, b in diffs[:25]:
            print(f"  {tag:9s} script={' '.join(a)[:60]!r} heard={' '.join(b)[:60]!r}")

    # The tail, checked explicitly: that is where the known artefact appeared.
    print(f"\nlast 8 words of script: {' '.join(want[-8:])}")
    print(f"last 8 words heard    : {' '.join(got[-8:])}")
    if got[-8:] != want[-8:]:
        print("WARNING: the ending does not match. Listen to the last few seconds "
              "before this ships.")


if __name__ == "__main__":
    main()

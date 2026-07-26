"""THE RECEIPT: the house visual format for Substack Notes (chosen by Aaron,
2026-07-26, from three candidates in generate_note_mockups.py).

A thermal-receipt slip in monospace on torn paper, 1080x1350 (4:5 portrait, the
format the feed rewards). BRAND.md calls the receipt our one ownable signature; this
renders it literally instead of as a one-line stamp.

Every number is READ FROM THE HONEST LOG, never passed in by hand, so a receipt
cannot drift from what the audit would reproduce (non-negotiable #1 in CLAUDE.md).

    python scripts/generate_receipt_note.py season       # season summary
    python scripts/generate_receipt_note.py calibration  # stated vs actual
    python scripts/generate_receipt_note.py --list

Output: docs/growth/posts/assets/receipts/receipt_<type>_<YYYYMMDD>.png

USE IT SPARINGLY. Aaron's rule, 2026-07-26: not every note gets an image, or the
feed looks automated. The receipt is for notes that make a claim needing proof; the
observational and human notes stay text-only. See docs/growth/ENGAGEMENT_PLAYBOOK.md.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
LOG_CSV = ROOT / "data/exports/prediction_tracking_honest.csv"
OUT_DIR = ROOT / "docs/growth/posts/assets/receipts"

W, H = 1080, 1350
NAVY_DEEP = (8, 12, 20)
PAPER = (253, 253, 254)
INK = (24, 33, 48)
RECEIPT_GRAY = (137, 135, 129)

FONTS = "C:/Windows/Fonts/"
WIDTH_CHARS = 34  # rules sized to the slip; keep row text under this


def mono(sz, bold=False):
    return ImageFont.truetype(FONTS + ("consolab.ttf" if bold else "consola.ttf"), sz)


def sans(sz):
    return ImageFont.truetype(FONTS + "segoeui.ttf", sz)


# --------------------------------------------------------------------- data
def load_stats() -> dict:
    """Everything a receipt can print, derived from the pre-game log only."""
    if not LOG_CSV.exists():
        sys.exit(f"missing {LOG_CSV}")
    d = pd.read_csv(LOG_CSV).dropna(subset=["correct"])
    n = len(d)
    correct = int(d["correct"].sum())
    buckets = []
    if "confidence" in d.columns:
        cuts = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]
        for lo, hi in cuts:
            sub = d[(d["confidence"] > lo) & (d["confidence"] <= hi)]
            if len(sub) >= 25:  # ignore buckets too small to mean anything
                buckets.append((f"{int(lo*100)}-{int(hi*100) if hi<=1 else 100}%",
                                100 * sub["correct"].mean(), len(sub)))
    season = "2025-26"
    if "date" in d.columns and len(d):
        yr = int(str(d["date"].max())[:4])
        season = f"{yr-1}-{str(yr)[-2:]}"
    return {"n": n, "correct": correct, "wrong": n - correct,
            "accuracy": 100 * correct / n if n else 0.0,
            "buckets": buckets, "season": season}


# ------------------------------------------------------------------ render
def render(blocks: list, out: Path) -> Path:
    """blocks is a list of tuples, so any receipt can be composed without touching
    the drawing code:
        ("title", text) ("sub", text) ("rule", "=" or "-") ("head", text)
        ("row", label, value) ("bigrow", label, value) ("line", text) ("gap", px)
    """
    img = Image.new("RGB", (W, H), NAVY_DEEP)
    d = ImageDraw.Draw(img)
    pad, top, bot = 90, 70, 70
    d.rectangle([pad, top, W - pad, H - bot], fill=PAPER)

    step = 26  # torn edges
    for x in range(pad, W - pad, step):
        d.polygon([(x, top), (x + step / 2, top + 15), (x + step, top)], fill=NAVY_DEEP)
        d.polygon([(x, H - bot), (x + step / 2, H - bot - 15), (x + step, H - bot)],
                  fill=NAVY_DEEP)

    x0 = pad + 58
    inner = W - 2 * pad - 116
    y = top + 78

    def centre(text, font, fill):
        nonlocal y
        w = d.textbbox((0, 0), text, font=font)[2]
        d.text(((W - w) / 2, y), text, font=font, fill=fill)

    for b in blocks:
        kind = b[0]
        if kind == "title":
            centre(b[1], mono(40, True), INK); y += 58
        elif kind == "sub":
            centre(b[1], mono(24), RECEIPT_GRAY); y += 62
        elif kind == "head":
            centre(b[1], mono(26, True), INK); y += 52
        elif kind == "rule":
            d.text((x0, y), b[1] * WIDTH_CHARS, font=mono(24),
                   fill=INK if b[1] == "=" else RECEIPT_GRAY)
            y += 46
        elif kind in ("row", "bigrow"):
            f = mono(30, kind == "bigrow")
            d.text((x0, y), b[1], font=f, fill=INK)
            vw = d.textbbox((0, 0), b[2], font=f)[2]
            d.text((x0 + inner - vw, y), b[2], font=f, fill=INK)
            y += 46
        elif kind == "line":
            d.text((x0, y), b[1], font=mono(28), fill=INK); y += 42
        elif kind == "gap":
            y += b[1]

    d.text((x0, H - bot - 132), "=" * WIDTH_CHARS, font=mono(24), fill=INK)
    for i, txt in enumerate(("VERIFIED WALK-FORWARD", f"{date.today():%m/%d/%Y}")):
        w = d.textbbox((0, 0), txt, font=mono(24))[2]
        d.text(((W - w) / 2, H - bot - 88 + i * 36), txt,
               font=mono(24), fill=RECEIPT_GRAY)
    u = "secondbounce.substack.com"
    uw = d.textbbox((0, 0), u, font=sans(24))[2]
    d.text(((W - uw) / 2, H - bot + 22), u, font=sans(24), fill=RECEIPT_GRAY)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


# ------------------------------------------------------------------- types
def season_receipt(s: dict) -> list:
    return [
        ("title", "SECOND BOUNCE"), ("sub", "PREDICTION RECEIPT"),
        ("rule", "="), ("head", f"{s['season']} SEASON"),
        ("row", "GAMES CALLED", f"{s['n']}"),
        ("row", "CORRECT", f"{s['correct']}"),
        ("row", "WRONG", f"{s['wrong']}"),
        ("gap", 6), ("bigrow", "ACCURACY", f"{s['accuracy']:.2f}%"),
        ("gap", 10), ("rule", "-"),
        ("line", "EVERY PICK LOGGED"), ("line", "BEFORE TIP-OFF."),
        ("line", "GRADED AFTER THE FINAL."), ("line", "NEVER RECOMPUTED."),
        ("gap", 8), ("rule", "-"),
        ("line", "NO PICK DELETED."), ("line", "NO NUMBER REVISED"),
        ("line", "AFTER THE FACT."),
    ]


def calibration_receipt(s: dict) -> list:
    blocks = [
        ("title", "SECOND BOUNCE"), ("sub", "CALIBRATION RECEIPT"),
        ("rule", "="), ("head", "WHAT WE SAID VS"), ("head", "WHAT HAPPENED"),
        ("gap", 6),
    ]
    # sample size goes inline: on its own row it orphans and eats the slip's height
    for label, won, n in s["buckets"]:
        blocks.append(("row", f" SAID {label} ({n})", f"WON {won:.1f}%"))
    blocks += [
        ("gap", 8), ("rule", "-"),
        ("bigrow", "ALL GAMES", f"{s['accuracy']:.2f}%"),
        ("row", "SAMPLE", f"{s['n']}"),
        ("gap", 8), ("rule", "-"),
        ("line", "CONFIDENCE IS A CLAIM."), ("line", "THIS IS THE CHECK."),
    ]
    return blocks


TYPES = {"season": season_receipt, "calibration": calibration_receipt}


def main() -> None:
    p = argparse.ArgumentParser(description="Render a receipt note image")
    p.add_argument("type", nargs="?", default="season", choices=sorted(TYPES))
    p.add_argument("--list", action="store_true", help="list receipt types")
    p.add_argument("--out", help="explicit output path")
    a = p.parse_args()
    if a.list:
        print("types:", ", ".join(sorted(TYPES)))
        return
    s = load_stats()
    out = Path(a.out) if a.out else OUT_DIR / f"receipt_{a.type}_{date.today():%Y%m%d}.png"
    render(TYPES[a.type](s), out)
    print(f"wrote {out}")
    print(f"  from {s['n']} graded games, accuracy {s['accuracy']:.2f}%")


if __name__ == "__main__":
    main()

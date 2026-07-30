"""Hero image for the correction essay: the withdrawn number struck out beside the
one that survived.

Uses the brand's receipt motif (docs/growth/BRAND.md) in a landscape crop, because a
Substack header wants wide and our receipt notes are portrait for the feed.

Both figures are READ, one from the archived leaky log and one from the honest log,
so the image cannot drift from the essay or from config/metrics.yaml.

    python scripts/generate_correction_hero.py
"""

import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
LEAKY = ROOT / "data/exports/prediction_tracking_vps_final.csv"
HONEST = ROOT / "data/exports/prediction_tracking_honest.csv"
OUT = ROOT / "docs/growth/posts/assets/correction_hero.png"

W, H = 1456, 720   # ~2:1, a Substack header crop
OBSIDIAN = "#0f1011"
CLOUD = "#f5f5f7"
ASH = "#9f9fa0"
GRID = "#2e2e2e"
IRIS = "#847dff"
EMBER = "#d95926"

# Same cross-platform resolution as generate_og_card.py: this may be run on the PC
# or, one day, from the VPS.
FONT_CANDIDATES = {
    "mono": ["C:/Windows/Fonts/consola.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"],
    "mono_bold": ["C:/Windows/Fonts/consolab.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"],
    "serif_bold": ["C:/Windows/Fonts/georgiab.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"],
    "sans": ["C:/Windows/Fonts/segoeui.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def _font(role, sz):
    for p in FONT_CANDIDATES[role]:
        if Path(p).exists():
            return ImageFont.truetype(p, sz)
    sys.exit(f"no font for {role}")


def figures():
    def acc(p):
        if not p.exists():
            sys.exit(f"missing {p}")
        d = pd.read_csv(p).dropna(subset=["correct"])
        return 100 * d["correct"].mean(), int(d["correct"].sum()), len(d)
    leaked, leaked_n, n1 = acc(LEAKY)
    honest, honest_n, n2 = acc(HONEST)
    assert n1 == n2, f"the two logs cover different samples: {n1} vs {n2}"
    return leaked, leaked_n, honest, honest_n, n1


def main() -> None:
    leaked, leaked_n, honest, honest_n, n = figures()

    img = Image.new("RGB", (W, H), OBSIDIAN)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 6], fill=IRIS)

    d.text((84, 74), "THE CORRECTION", font=_font("mono_bold", 30), fill=ASH)
    d.text((84, 128), f"Same model. Same {n} games.",
           font=_font("sans", 40), fill=CLOUD)

    # Left: what we published, struck through.
    lx, ly = 84, 236
    d.text((lx, ly), f"{leaked:.1f}%", font=_font("serif_bold", 150), fill=EMBER)
    box = d.textbbox((lx, ly), f"{leaked:.1f}%", font=_font("serif_bold", 150))
    strike_y = (box[1] + box[3]) // 2 + 6
    d.line([lx - 8, strike_y, box[2] + 8, strike_y], fill=EMBER, width=7)
    d.text((lx, box[3] + 18), "as published", font=_font("sans", 31), fill=EMBER)
    d.text((lx, box[3] + 60), f"{leaked_n} correct", font=_font("mono", 26), fill=ASH)

    # Right: what survived.
    rx = 700
    d.text((rx, ly), f"{honest:.1f}%", font=_font("serif_bold", 150), fill=CLOUD)
    rbox = d.textbbox((rx, ly), f"{honest:.1f}%", font=_font("serif_bold", 150))
    d.text((rx, rbox[3] + 18), "after a walk-forward audit",
           font=_font("sans", 31), fill=IRIS)
    d.text((rx, rbox[3] + 60), f"{honest_n} correct", font=_font("mono", 26), fill=ASH)

    # The arrow, sitting in the gutter between the two numbers.
    ay = (ly + rbox[3]) // 2
    d.line([box[2] + 52, ay, rx - 52, ay], fill=GRID, width=5)
    d.polygon([(rx - 52, ay), (rx - 78, ay - 17), (rx - 78, ay + 17)], fill=GRID)

    # Receipt strip: the finding, in the house monospace.
    sy = H - 160
    d.rectangle([84, sy, W - 84, sy + 74], outline=GRID, width=2)
    d.text((112, sy + 24),
           f"[ {leaked_n - honest_n} wins that were not there ]",
           font=_font("mono_bold", 30), fill=IRIS)

    d.text((84, H - 56),
           "We found it in our own tracker, and cut our own number.",
           font=_font("sans", 28), fill=ASH)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}  {W}x{H}  "
          f"{OUT.stat().st_size / 1024:.0f}KB  ({leaked:.2f}% -> {honest:.2f}%)")


if __name__ == "__main__":
    main()

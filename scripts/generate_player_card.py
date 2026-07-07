"""Signature player card: NBA.com headshot, duotone brand treatment, grain,
receipt overlay. One card per post, for the post's subject only (BRAND.md).

Usage:
    python scripts/generate_player_card.py <nba_player_id> "Name" <rating> "kicker line" [out.png]
    e.g. python scripts/generate_player_card.py 203507 "Giannis Antetokounmpo" 2280 "THE HEADLINE MOVE"
"""

import io
import sys
from datetime import date

import numpy as np
import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

ASSETS = "docs/growth/posts/assets"
F = "C:/Windows/Fonts/"

# Origin palette (names kept; values shifted to obsidian/cyan/ember)
NAVY = (15, 16, 17)        # obsidian canvas + duotone shadows
CARD_EDGE = (26, 26, 28)
BLUE = (0, 179, 221)       # cyan data-signal: duotone mids + rating number
PALE = (200, 240, 250)     # pale cyan: duotone highlights
TEXT = (245, 245, 247)     # cloud
MUTED = (159, 159, 160)    # ash
ORANGE = (215, 78, 9)      # ember accent (kicker)

HEADSHOT_URL = "https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png"


def duotone_grain(img: Image.Image) -> Image.Image:
    """Map a headshot to the brand duotone (navy -> blue -> pale) + film grain."""
    rgba = img.convert("RGBA")
    alpha = np.array(rgba.split()[3], dtype=np.uint8)
    gray = np.array(rgba.convert("L"), dtype=np.float32) / 255.0

    # film grain before mapping so it tints with the duotone
    rng = np.random.default_rng(27)
    gray = np.clip(gray + rng.normal(0, 0.045, gray.shape), 0, 1)

    # two-segment duotone ramp: shadows->navy, mids->blue, highlights->pale
    lo, hi = np.array(NAVY, float), np.array(BLUE, float)
    top = np.array(PALE, float)
    t = gray[..., None]
    out = np.where(t < 0.55,
                   lo + (hi - lo) * (t / 0.55),
                   hi + (top - hi) * ((t - 0.55) / 0.45))
    out = out.astype(np.uint8)
    res = np.dstack([out, alpha])
    return Image.fromarray(res, "RGBA")


def receipt_line() -> str:
    t = pd.read_csv("data/exports/prediction_tracking_honest.csv")
    acc = t["correct"].astype(bool).mean() * 100
    return (f"[ {acc:.1f}% · {len(t)} games · as of "
            f"{date.today().strftime('%m/%d/%Y')} ]")


def build(pid: str, name: str, rating: str, kicker: str, out: str):
    r = requests.get(HEADSHOT_URL.format(pid=pid), timeout=30)
    r.raise_for_status()
    head = Image.open(io.BytesIO(r.content))
    head = duotone_grain(head)

    W, H = 1456, 780
    card = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(card)

    # right panel wash behind the player
    d.rectangle([W - 660, 0, W, H], fill=(12, 18, 30))
    # headshot, anchored bottom-right
    hw = 640
    hh = int(hw * head.height / head.width)
    head = head.resize((hw, hh))
    card.paste(head, (W - hw - 20, H - hh), head)

    # baseline the player "stands" on
    d.rectangle([W - 660, H - 8, W, H], fill=BLUE)

    f_kick = ImageFont.truetype(F + "seguibl.ttf", 30)
    f_name = ImageFont.truetype(F + "seguibl.ttf", 86)
    f_num = ImageFont.truetype(F + "seguibl.ttf", 168)
    f_lab = ImageFont.truetype(F + "segoeuib.ttf", 28)
    f_small = ImageFont.truetype(F + "segoeui.ttf", 24)

    x = 84
    d.text((x, 72), kicker.upper(), font=f_kick, fill=ORANGE)
    # wrap name onto two lines if long; all caps for weight
    name_u = name.upper()
    parts = name_u.split(" ", 1)
    if d.textlength(name_u, font=f_name) > 680 and len(parts) == 2:
        d.text((x, 128), parts[0], font=f_name, fill=TEXT)
        d.text((x, 232), parts[1], font=f_name, fill=TEXT)
        ny = 372
    else:
        d.text((x, 128), name_u, font=f_name, fill=TEXT)
        ny = 268
    d.text((x - 6, ny), f"{int(rating):,}", font=f_num, fill=BLUE)
    d.text((x, ny + 200), "MODEL RATING · 1500 = LEAGUE AVERAGE",
           font=f_lab, fill=MUTED)

    d.text((x, H - 44), "secondbounce.substack.com", font=f_small, fill=MUTED)

    card.save(out)
    print("saved:", out)


if __name__ == "__main__":
    pid, name, rating = sys.argv[1], sys.argv[2], sys.argv[3]
    kicker = sys.argv[4] if len(sys.argv) > 4 else "SECOND BOUNCE"
    out = sys.argv[5] if len(sys.argv) > 5 else f"{ASSETS}/card_{pid}.png"
    build(pid, name, rating, kicker, out)

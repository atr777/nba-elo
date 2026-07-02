"""Generate Second Bounce brand assets (BRAND.md v1 system).

Outputs to docs/growth/posts/assets/:
- logo_substack.png   circle-cropped glowing ball (publication avatar)
- footer_banner.png   light post footer: ball + wordmark + bounce arcs + receipt
- x_header.png        1500x500 dark header for the X profile

The receipt stamp is computed from the honest tracking CSV, never hand-typed.
"""

from datetime import date

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ASSETS = "docs/growth/posts/assets"

# palette (BRAND.md)
NAVY = (15, 22, 35)
PAPER = (253, 253, 254)
BLUE_DARK_SURFACE = (75, 139, 244)   # signal blue on dark
BLUE_LIGHT_SURFACE = (42, 120, 214)  # signal blue on light
INK = (24, 33, 48)
TEXT_DARK = (232, 236, 244)
SECONDARY = (110, 118, 130)
MUTED_DARK = (100, 116, 139)
RECEIPT_GRAY = (137, 135, 129)

F = "C:/Windows/Fonts/"


def receipt_line() -> str:
    t = pd.read_csv("data/exports/prediction_tracking_honest.csv")
    acc = t["correct"].astype(bool).mean() * 100
    stamp = date.today().strftime("%m/%d/%Y")
    return (f"[ {acc:.1f}% · {len(t)} games · as of {stamp} · "
            f"verified walk-forward ]")


def bounce_arcs(draw, x, y, total_w, color, width=3):
    """Two diminishing arcs under the wordmark: the physics of the name."""
    w1 = int(total_w * 0.62)
    w2 = int(total_w * 0.30)
    h1 = int(w1 * 0.10)
    h2 = int(w2 * 0.10)
    draw.arc([x, y - h1, x + w1, y + h1], start=180, end=360,
             fill=color, width=width)
    x2 = x + w1 + int(total_w * 0.04)
    draw.arc([x2, y - h2, x2 + w2, y + h2], start=180, end=360,
             fill=color, width=width)


# ---------------------------------------------------------------- ball logo
src = Image.open(f"{ASSETS}/logo_site.png").convert("RGBA")
cx, cy, r = 512, 495, 420
crop = src.crop((cx - r, cy - r, cx + r, cy + r)).resize((1024, 1024))
mask = Image.new("L", (1024, 1024), 0)
ImageDraw.Draw(mask).ellipse([0, 0, 1024, 1024], fill=255)
ball_full = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
ball_full.paste(crop, (0, 0), mask)
ball_full.save(f"{ASSETS}/logo_substack.png")

RECEIPT = receipt_line()

# ------------------------------------------------------------ footer banner
W, H = 1456, 420
banner = Image.new("RGB", (W, H), PAPER)
pattern = Image.open(f"{ASSETS}/pattern.png").convert("RGBA")
tile = pattern.resize((380, 380))
tile.putalpha(tile.split()[3].point(lambda a: int(a * 0.03)))
for x in range(0, W, 380):
    for y in range(0, H, 380):
        banner.paste(tile, (x, y), tile)

draw = ImageDraw.Draw(banner)
draw.rectangle([0, 0, W, 5], fill=(183, 208, 250))

ball = ball_full.resize((124, 124))
banner.paste(ball, (80, 92), ball)

f_brand = ImageFont.truetype(F + "segoeuib.ttf", 70)
f_tag = ImageFont.truetype(F + "segoeui.ttf", 31)
f_mono = ImageFont.truetype(F + "consola.ttf", 26)

tx = 80 + 124 + 34
draw.text((tx, 98), "SECOND BOUNCE", font=f_brand, fill=INK)
prefix_w = draw.textlength("SECOND ", font=f_brand)
bounce_w = draw.textlength("BOUNCE", font=f_brand)
bounce_arcs(draw, tx + prefix_w, 207, bounce_w, BLUE_LIGHT_SURFACE)
draw.text((tx + 4, 246), "NBA predictions that show their work",
          font=f_tag, fill=SECONDARY)

draw.text((84, 330), RECEIPT, font=f_mono, fill=RECEIPT_GRAY)
draw.text((W - 80, H - 56), "secondbounce.substack.com",
          font=ImageFont.truetype(F + "segoeui.ttf", 26),
          fill=RECEIPT_GRAY, anchor="ra")
banner.save(f"{ASSETS}/footer_banner.png")

# ---------------------------------------------------------------- X header
XW, XH = 1500, 500
hdr = Image.new("RGB", (XW, XH), NAVY)
tile2 = pattern.resize((500, 500))
tile2.putalpha(tile2.split()[3].point(lambda a: int(a * 0.06)))
for x in range(0, XW, 500):
    for y in range(0, XH, 500):
        hdr.paste(tile2, (x, y), tile2)
d2 = ImageDraw.Draw(hdr)
d2.rectangle([0, 0, XW, 6], fill=BLUE_DARK_SURFACE)

ball2 = ball_full.resize((190, 190))
hdr.paste(ball2, (110, 140), ball2)

f_brand2 = ImageFont.truetype(F + "segoeuib.ttf", 88)
tx2 = 110 + 190 + 48
d2.text((tx2, 140), "SECOND BOUNCE", font=f_brand2, fill=TEXT_DARK)
prefix2 = d2.textlength("SECOND ", font=f_brand2)
bounce2 = d2.textlength("BOUNCE", font=f_brand2)
bounce_arcs(d2, tx2 + prefix2, 263, bounce2, BLUE_DARK_SURFACE, width=4)
d2.text((tx2 + 5, 310), "NBA predictions that show their work",
        font=ImageFont.truetype(F + "segoeui.ttf", 38), fill=MUTED_DARK)
d2.text((tx2 + 5, 396), RECEIPT,
        font=ImageFont.truetype(F + "consola.ttf", 30), fill=(148, 163, 184))
hdr.save(f"{ASSETS}/x_header.png")

print("done:", RECEIPT)

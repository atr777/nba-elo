"""Origin-aesthetic brand assets: a Substack header banner and a post footer
banner that match the live site (obsidian canvas, cream serif wordmark, warm
ember accent, mono receipt). Uses the hero ball + our logo.
"""

from datetime import date

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ASSETS = "docs/growth/posts/assets"
F = "C:/Windows/Fonts/"

OBSIDIAN = (15, 16, 17)
CLOUD = (245, 245, 247)
ASH = (159, 159, 160)
EMBER = (215, 78, 9)      # burnt orange, our warm accent (matches tile)

serif = lambda s: ImageFont.truetype(F + "georgiab.ttf", s)   # DM-Serif stand-in
sans = lambda s: ImageFont.truetype(F + "segoeui.ttf", s)
mono = lambda s: ImageFont.truetype(F + "consola.ttf", s)


def receipt_line():
    t = pd.read_csv("data/exports/prediction_tracking_honest.csv")
    acc = t["correct"].astype(bool).mean() * 100
    return (f"[ {acc:.1f}% · {len(t)} games · as of "
            f"{date.today().strftime('%m/%d/%Y')} · verified walk-forward ]")


def ball_faded(target_h):
    """Hero ball scaled to height, with a left-edge fade into obsidian."""
    ball = Image.open(f"{ASSETS}/hero_ball.png").convert("RGB")
    r = target_h / ball.height
    ball = ball.resize((int(ball.width * r), target_h))
    fade = Image.new("L", ball.size, 255)
    fd = ImageDraw.Draw(fade)
    fw = int(ball.width * 0.45)
    for x in range(fw):
        fd.line([(x, 0), (x, ball.height)], fill=int(255 * (x / fw)))
    out = Image.new("RGB", ball.size, OBSIDIAN)
    out.paste(ball, (0, 0), fade)
    return out


def substack_header(path):
    W, H = 1600, 500
    img = Image.new("RGB", (W, H), OBSIDIAN)
    ball = ball_faded(H)
    img.paste(ball, (W - ball.width, 0))
    d = ImageDraw.Draw(img)
    x = 96
    d.text((x, 150), "Second Bounce", font=serif(96), fill=CLOUD)
    d.line([(x + 4, 268), (x + 250, 268)], fill=EMBER, width=2)
    d.text((x + 4, 288), "NBA PREDICTIONS THAT SHOW THEIR WORK",
           font=sans(26), fill=ASH)
    d.text((x + 4, 340), receipt_line(), font=mono(23), fill=(120, 120, 122))
    img.save(path)


def footer_banner(path):
    W, H = 1456, 420
    img = Image.new("RGB", (W, H), OBSIDIAN)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 4], fill=EMBER)
    ball = Image.open(f"{ASSETS}/logo_substack.png").convert("RGBA").resize((118, 118))
    img.paste(ball, (84, 92), ball)
    x = 84 + 118 + 34
    d.text((x, 96), "Second Bounce", font=serif(74), fill=CLOUD)
    d.text((x + 4, 196), "NBA predictions that show their work",
           font=sans(30), fill=ASH)
    d.text((84, 322), receipt_line(), font=mono(24), fill=(120, 120, 122))
    d.text((W - 84, H - 54), "secondbounce.substack.com", font=sans(25),
           fill=ASH, anchor="ra")
    img.save(path)


if __name__ == "__main__":
    substack_header(f"{ASSETS}/substack_header.png")
    footer_banner(f"{ASSETS}/footer_banner_origin.png")
    print("done: substack_header.png, footer_banner_origin.png")

"""Creative-direction mockups for visual Substack Notes. Generates three candidate
formats so Aaron can pick one to standardise on.

All are 1080x1350 (4:5 portrait), which is the format the feed rewards: it occupies
roughly 25% more mobile screen than a square and materially outperforms landscape.
Every chart we already own is landscape, because it was built for the newsletter.

    python scripts/generate_note_mockups.py

Writes docs/growth/posts/assets/mockups/note_direction_[a|b|c].png
Numbers come from the honest 657-game log and the preseason overlay. Nothing here is
invented; if a figure changes, regenerate rather than editing the image.
"""

from pathlib import Path
from datetime import date

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/growth/posts/assets/mockups"
W, H = 1080, 1350

# docs/growth/BRAND.md
NAVY = (15, 22, 35)
NAVY_DEEP = (8, 12, 20)
PAPER = (253, 253, 254)
BLUE_DARK = (75, 139, 244)
BLUE_LIGHT = (42, 120, 214)
ORANGE = (248, 161, 0)
INK = (24, 33, 48)
RECEIPT = (137, 135, 129)

F = "C:/Windows/Fonts/"
def mono(sz, bold=False):
    return ImageFont.truetype(F + ("consolab.ttf" if bold else "consola.ttf"), sz)
def sans(sz, bold=False):
    return ImageFont.truetype(F + ("segoeuib.ttf" if bold else "segoeui.ttf"), sz)

STAMP = f"[ 70.6% . 657 games . as of {date.today():%m/%d/%Y} . verified walk-forward ]"


def center(d, y, text, font, fill, width=W):
    w = d.textbbox((0, 0), text, font=font)[2]
    d.text(((width - w) / 2, y), text, font=font, fill=fill)


# ---------------------------------------------------------------- Direction A
def direction_a():
    """THE RECEIPT. The brand's own motif made literal: a thermal receipt of the
    season. Monospace on paper, torn top and bottom edge. Most ownable of the three
    because nobody else in NBA media is shaped like this."""
    img = Image.new("RGB", (W, H), NAVY_DEEP)
    d = ImageDraw.Draw(img)

    # paper slip inset on the navy field
    pad, top, bot = 90, 70, 70
    d.rectangle([pad, top, W - pad, H - bot], fill=PAPER)

    # torn edges: notch triangles along top and bottom of the slip
    step = 26
    for x in range(pad, W - pad, step):
        d.polygon([(x, top), (x + step / 2, top + 15), (x + step, top)], fill=NAVY_DEEP)
        d.polygon([(x, H - bot), (x + step / 2, H - bot - 15), (x + step, H - bot)],
                  fill=NAVY_DEEP)

    x0 = pad + 58
    inner = W - 2 * pad - 116
    y = top + 78

    center(d, y, "SECOND BOUNCE", mono(40, True), INK); y += 58
    center(d, y, "PREDICTION RECEIPT", mono(24), RECEIPT); y += 62
    d.text((x0, y), "=" * 34, font=mono(24), fill=INK); y += 46

    def row(label, value, bold=False, color=INK):
        nonlocal y
        f = mono(30, bold)
        d.text((x0, y), label, font=f, fill=color)
        vw = d.textbbox((0, 0), value, font=f)[2]
        d.text((x0 + inner - vw, y), value, font=f, fill=color)
        y += 46

    center(d, y, "2025-26 SEASON", mono(28, True), INK); y += 56
    row("GAMES CALLED", "657")
    row("CORRECT", "464")
    row("WRONG", "193")
    y += 6
    row("ACCURACY", "70.62%", bold=True)
    y += 10
    d.text((x0, y), "-" * 34, font=mono(24), fill=RECEIPT); y += 46

    center(d, y, "STATED VS ACTUAL", mono(26, True), INK); y += 52
    for said, won in [("80-90%", "79.6%"), ("70-80%", "73.2%"),
                      ("60-70%", "69.7%"), ("50-60%", "60.0%")]:
        row(f"  SAID {said}", f"WON {won}")
    y += 8
    d.text((x0, y), "-" * 34, font=mono(24), fill=RECEIPT); y += 46

    for line in ["EVERY PICK LOGGED", "BEFORE TIP-OFF.",
                 "GRADED AFTER THE FINAL.", "NEVER RECOMPUTED."]:
        d.text((x0, y), line, font=mono(28), fill=INK); y += 42
    y += 12
    d.text((x0, y), "=" * 34, font=mono(24), fill=INK); y += 44
    center(d, y, "VERIFIED WALK-FORWARD", mono(24), RECEIPT); y += 36
    center(d, y, f"{date.today():%m/%d/%Y}", mono(24), RECEIPT)

    center(d, H - bot + 22, "secondbounce.substack.com", sans(24), RECEIPT)
    p = OUT / "note_direction_a.png"
    img.save(p); return p


# ---------------------------------------------------------------- Direction B
def direction_b():
    """THE BIG NUMBER. One figure at hero scale on night navy, one sentence of
    context, the receipt stamp. Fastest possible read on a phone; scales to any
    stat, so it is the easiest to automate daily in season."""
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)

    # a single orange rule as the only ornament: orange marks the model's claim
    d.rectangle([0, 0, W, 12], fill=ORANGE)

    d.text((80, 150), "WHEN THE MODEL SAID", font=sans(38, True), fill=BLUE_DARK)
    d.text((80, 205), "80 TO 90 PERCENT", font=sans(38, True), fill=BLUE_DARK)

    # hero number
    d.text((66, 330), "79.6%", font=sans(250, True), fill=PAPER)

    d.text((80, 640), "is what it actually won.", font=sans(52), fill=PAPER)

    body = ["Not what it promised. What it did,", "across 201 games, each one logged",
            "before tip-off and graded after", "the final."]
    y = 760
    for line in body:
        d.text((80, y), line, font=sans(40), fill=(178, 190, 208)); y += 58

    d.text((80, 1030), "Calibration is the part", font=sans(40, True), fill=ORANGE)
    d.text((80, 1082), "everyone skips.", font=sans(40, True), fill=ORANGE)

    d.line([80, 1180, W - 80, 1180], fill=(46, 58, 78), width=2)
    d.text((80, 1210), STAMP, font=mono(23), fill=RECEIPT)
    d.text((80, 1252), "secondbounce.substack.com", font=sans(26), fill=(120, 134, 154))

    p = OUT / "note_direction_b.png"
    img.save(p); return p


# ---------------------------------------------------------------- Direction C
def direction_c():
    """THE PROOF. A portrait chart that argues one point: stated confidence tracks
    reality. Most informative and most defensible, and it reuses the chart pipeline,
    but it asks the reader to study it, which is a lot to ask in a feed."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    d.text((72, 84), "We say it, then we", font=sans(58, True), fill=INK)
    d.text((72, 152), "prove it", font=sans(58, True), fill=INK)
    d.text((72, 246), "Stated confidence against what actually", font=sans(32), fill=(85, 96, 111))
    d.text((72, 288), "happened, 657 games, 2025-26.", font=sans(32), fill=(85, 96, 111))

    # grouped bars: stated midpoint vs actual
    buckets = [("50-60%", 55.0, 60.0, 195), ("60-70%", 65.0, 69.7, 119),
               ("70-80%", 75.0, 73.2, 142), ("80-90%", 85.0, 79.6, 201)]
    x0, y0 = 130, 420
    row_h, bar_h, scale = 200, 58, 8.4

    for i, (label, said, won, n) in enumerate(buckets):
        ytop = y0 + i * row_h
        d.text((72, ytop - 46), f"model said {label}", font=sans(30, True), fill=INK)
        d.text((W - 72 - d.textbbox((0,0), f"n={n}", font=sans(26))[2], ytop - 42),
               f"n={n}", font=sans(26), fill=RECEIPT)
        # stated (light blue) then actual (orange = the model's claim being tested)
        d.rectangle([x0, ytop, x0 + said * scale, ytop + bar_h - 20], fill=(168, 198, 239))
        d.text((x0 + said * scale + 14, ytop - 2), f"{said:.0f}", font=sans(26), fill=(110, 128, 152))
        d.rectangle([x0, ytop + bar_h - 6, x0 + won * scale, ytop + 2 * bar_h - 26], fill=BLUE_LIGHT)
        d.text((x0 + won * scale + 14, ytop + bar_h - 8), f"{won:.1f}", font=sans(28, True), fill=INK)

    # legend on its own line, stamp beneath it: at this width they collide otherwise
    lg = 1218
    d.rectangle([72, lg, 106, lg + 20], fill=(168, 198, 239))
    d.text((118, lg - 6), "stated", font=sans(26), fill=(85, 96, 111))
    d.rectangle([230, lg, 264, lg + 20], fill=BLUE_LIGHT)
    d.text((276, lg - 6), "actually won", font=sans(26), fill=(85, 96, 111))
    d.line([72, 1268, W - 72, 1268], fill=(231, 233, 238), width=2)
    d.text((72, 1288), STAMP, font=mono(21), fill=RECEIPT)

    p = OUT / "note_direction_c.png"
    img.save(p); return p


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (direction_a, direction_b, direction_c):
        print("wrote", fn())

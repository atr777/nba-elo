"""Generate branded assets for Substack.

1. logo_substack.png: the site's glowing-ball logo circle-cropped for use as
   the Substack publication logo/avatar (1024x1024, transparent corners).
2. footer_banner.png: light, airy post footer with the ball mark in the header
   row (v3: lighter + translucent feel, Aaron 2026-07-01).
"""

from PIL import Image, ImageDraw, ImageFont

ASSETS = "docs/growth/posts/assets"

# ---------------------------------------------------- substack logo (circle)
src = Image.open(f"{ASSETS}/logo_site.png").convert("RGBA")
# ball sits centered around (512, 490); crop a circle that keeps its glow
cx, cy, r = 512, 495, 420
box = (cx - r, cy - r, cx + r, cy + r)
crop = src.crop(box).resize((1024, 1024))
mask = Image.new("L", (1024, 1024), 0)
ImageDraw.Draw(mask).ellipse([0, 0, 1024, 1024], fill=255)
logo = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
logo.paste(crop, (0, 0), mask)
logo.save(f"{ASSETS}/logo_substack.png")

# ------------------------------------------------------------- footer banner
BG = (253, 253, 254)
ACCENT_SOFT = (183, 208, 250)   # accent blue washed onto white
STAT = (28, 92, 171)
INK = (24, 33, 48)
SECONDARY = (110, 118, 130)
MUTED = (160, 165, 173)

W, H = 1456, 420
banner = Image.new("RGB", (W, H), BG)

# whisper-faint basketball pattern
pattern = Image.open(f"{ASSETS}/pattern.png").convert("RGBA")
tile = pattern.resize((380, 380))
alpha = tile.split()[3].point(lambda a: int(a * 0.03))
tile.putalpha(alpha)
for x in range(0, W, 380):
    for y in range(0, H, 380):
        banner.paste(tile, (x, y), tile)

draw = ImageDraw.Draw(banner)
draw.rectangle([0, 0, W, 5], fill=ACCENT_SOFT)

# ball mark, small circle in the header row
ball = logo.resize((124, 124))
banner.paste(ball, (80, 96), ball)

f_brand = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 70)
f_tag = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 32)
f_stat = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 33)
f_small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 26)

tx = 80 + 124 + 34
draw.text((tx, 102), "SECOND BOUNCE", font=f_brand, fill=INK)
draw.text((tx + 4, 198), "NBA predictions, powered by ELO", font=f_tag,
          fill=SECONDARY)

y = 302
draw.text((84, y), "70.6% season accuracy", font=f_stat, fill=STAT)
w1 = draw.textlength("70.6% season accuracy", font=f_stat)
draw.text((84 + w1 + 22, y + 3), "tracked in public, every game",
          font=f_small, fill=SECONDARY)

draw.text((W - 80, H - 56), "secondbounce.substack.com", font=f_small,
          fill=MUTED, anchor="ra")

banner.save(f"{ASSETS}/footer_banner.png")
print("done: logo_substack.png, footer_banner.png")

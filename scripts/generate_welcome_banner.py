"""Compact welcome banner for the Substack welcome email."""

from PIL import Image, ImageDraw, ImageFont

ASSETS = "docs/growth/posts/assets"
F = "C:/Windows/Fonts/"
PAPER = (253, 253, 254)
INK = (24, 33, 48)
BLUE = (42, 120, 214)
SECONDARY = (110, 118, 130)
ACCENT_SOFT = (183, 208, 250)

W, H = 1456, 300
img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W, 5], fill=ACCENT_SOFT)

ball = Image.open(f"{ASSETS}/logo_substack.png").convert("RGBA").resize((150, 150))
img.paste(ball, (84, 75), ball)

f_kick = ImageFont.truetype(F + "seguibl.ttf", 26)
f_main = ImageFont.truetype(F + "seguibl.ttf", 64)
f_tag = ImageFont.truetype(F + "segoeui.ttf", 30)

x = 84 + 150 + 44
d.text((x, 70), "WELCOME TO", font=f_kick, fill=BLUE)
d.text((x, 108), "SECOND BOUNCE", font=f_main, fill=INK)
# bounce arcs under "BOUNCE"
prefix = d.textlength("SECOND ", font=f_main)
bw = d.textlength("BOUNCE", font=f_main)
bx = x + prefix
w1, w2 = int(bw * 0.62), int(bw * 0.30)
h1, h2 = int(w1 * 0.10), int(w2 * 0.10)
y = 198
d.arc([bx, y - h1, bx + w1, y + h1], 180, 360, fill=BLUE, width=3)
x2 = bx + w1 + int(bw * 0.04)
d.arc([x2, y - h2, x2 + w2, y + h2], 180, 360, fill=BLUE, width=3)
d.text((x, 218), "NBA predictions that show their work", font=f_tag,
       fill=SECONDARY)

img.save(f"{ASSETS}/welcome_banner.png")
print("done: welcome_banner.png")

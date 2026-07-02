"""Season-moments ribbon: a filmstrip of five receipts for the recap post.

Team logos from the ESPN CDN (same source the live site uses).
Output: docs/growth/posts/assets/moments_ribbon.png (1456x340).
"""

from PIL import Image, ImageDraw, ImageFont

ASSETS = "docs/growth/posts/assets"
F = "C:/Windows/Fonts/"

STRIP = (8, 12, 20)
CARD = (15, 22, 35)
TEXT = (232, 236, 244)
MUTED = (100, 116, 139)
BLUE = (75, 139, 244)
GREEN = (16, 185, 129)
RED = (239, 68, 68)
HOLE = (24, 32, 48)

W, H = 1456, 340
img = Image.new("RGB", (W, H), STRIP)
d = ImageDraw.Draw(img)

# film sprocket holes
for y in (14, H - 26):
    for x in range(24, W - 20, 52):
        d.rounded_rectangle([x, y, x + 26, y + 12], radius=4, fill=HOLE)

f_label = ImageFont.truetype(F + "segoeuib.ttf", 19)
f_big = ImageFont.truetype(F + "segoeuib.ttf", 56)
f_mid = ImageFont.truetype(F + "segoeuib.ttf", 40)
f_sub = ImageFont.truetype(F + "segoeui.ttf", 19)
f_stamp = ImageFont.truetype(F + "segoeuib.ttf", 21)


def logo(name, size):
    im = Image.open(f"{ASSETS}/logos/{name}.png").convert("RGBA")
    return im.resize((size, size))


def card(x, w=262):
    d.rounded_rectangle([x, 46, x + w, H - 46], radius=12, fill=CARD)
    return x, x + w


def stamp(cx, y, text, color):
    tw = d.textlength(text, font=f_stamp)
    d.rounded_rectangle([cx - tw / 2 - 12, y, cx + tw / 2 + 12, y + 32],
                        radius=6, outline=color, width=2)
    d.text((cx, y + 4), text, font=f_stamp, fill=color, anchor="ma")


def center(x0, x1):
    return (x0 + x1) / 2


pad = 22
xs = [pad + i * (262 + 27) for i in range(5)]

# 1. the streak
x0, x1 = card(xs[0]); c = center(x0, x1)
d.text((c, 66), "THE STREAK", font=f_label, fill=MUTED, anchor="ma")
d.text((c, 104), "20", font=f_big, fill=TEXT, anchor="ma")
d.text((c, 178), "straight correct picks\nat the March peak", font=f_sub,
       fill=MUTED, anchor="ma", align="center")
stamp(c, 238, "CORRECT", GREEN)

# 2. the run
x0, x1 = card(xs[1]); c = center(x0, x1)
d.text((c, 66), "THE RUN", font=f_label, fill=MUTED, anchor="ma")
d.text((c, 104), "16 / 20", font=f_big, fill=TEXT, anchor="ma")
d.text((c, 178), "tracked playoff games\ncalled correctly", font=f_sub,
       fill=MUTED, anchor="ma", align="center")
stamp(c, 238, "80%", GREEN)

# 3. the humbling (BOS-PHI twice)
x0, x1 = card(xs[2]); c = center(x0, x1)
d.text((c, 66), "THE HUMBLING", font=f_label, fill=MUTED, anchor="ma")
img.paste(logo("bos", 74), (int(c) - 88, 96), logo("bos", 74))
img.paste(logo("phi", 74), (int(c) + 14, 96), logo("phi", 74))
d.text((c, 182), "90% on Boston at home,\ntwice. Lost twice.", font=f_sub,
       fill=MUTED, anchor="ma", align="center")
stamp(c, 238, "MISS x2", RED)

# 4. the blowout (OKC-PHX)
x0, x1 = card(xs[3]); c = center(x0, x1)
d.text((c, 66), "THE BLOWOUT", font=f_label, fill=MUTED, anchor="ma")
img.paste(logo("okc", 74), (int(c) - 88, 96), logo("okc", 74))
img.paste(logo("phx", 74), (int(c) + 14, 96), logo("phx", 74))
d.text((c, 182), "90% on the Thunder.\nSuns won by 32.", font=f_sub,
       fill=MUTED, anchor="ma", align="center")
stamp(c, 238, "MISS", RED)

# 5. the audit
x0, x1 = card(xs[4]); c = center(x0, x1)
d.text((c, 66), "THE AUDIT", font=f_label, fill=MUTED, anchor="ma")
d.text((c, 112), "73.5 → 70.6", font=f_mid, fill=TEXT, anchor="ma")
d.text((c, 178), "we caught our tracker\nflattering the model", font=f_sub,
       fill=MUTED, anchor="ma", align="center")
stamp(c, 238, "CORRECTED", BLUE)

img.save(f"{ASSETS}/moments_ribbon.png")
print("done: moments_ribbon.png")

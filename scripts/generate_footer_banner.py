"""Generate the branded footer banner used at the bottom of every Substack post.

Matches the Second Bounce site: dark navy surface, faint basketball pattern,
blue accent. Output: docs/growth/posts/assets/footer_banner.png (1456px wide).
"""

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

BG = (15, 22, 35)        # site --surface #0f1623
ACCENT = (75, 139, 244)  # site --accent #4b8bf4
PICK = (248, 161, 0)     # site --pick #f8a100
TEXT = (232, 236, 244)   # site --text #e8ecf4
MUTED = (100, 116, 139)  # site --muted #64748b

W, H = 1456, 420
banner = Image.new("RGB", (W, H), BG)

# faint tiled basketball pattern, like the site header
pattern = Image.open("docs/growth/posts/assets/pattern.png").convert("RGBA")
tile = pattern.resize((380, 380))
tile = ImageEnhance.Brightness(tile).enhance(1.0)
alpha = tile.split()[3].point(lambda a: int(a * 0.10))
tile.putalpha(alpha)
for x in range(0, W, 380):
    for y in range(0, H, 380):
        banner.paste(tile, (x, y), tile)

draw = ImageDraw.Draw(banner)

# top accent bar
draw.rectangle([0, 0, W, 6], fill=ACCENT)

f_brand = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 76)
f_tag = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 34)
f_stat = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 34)
f_small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 27)

draw.text((80, 92), "SECOND BOUNCE", font=f_brand, fill=TEXT)
draw.text((84, 196), "NBA predictions, powered by ELO", font=f_tag, fill=MUTED)

# stat line with accent dot separators
y = 292
draw.text((84, y), "73.5% season accuracy", font=f_stat, fill=PICK)
w1 = draw.textlength("73.5% season accuracy", font=f_stat)
draw.text((84 + w1 + 24, y + 2), "tracked in public, every game",
          font=f_small, fill=TEXT)

draw.text((W - 80, H - 62), "secondbounce.substack.com", font=f_small,
          fill=MUTED, anchor="ra")

banner.save("docs/growth/posts/assets/footer_banner.png")
print("done: footer_banner.png")

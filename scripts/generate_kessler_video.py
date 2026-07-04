"""Build the 'Kessler Tax' voice-of-the-model video for X (1080x1080).

Reuses the LeBron video pipeline: River narration + the existing music bed
(lebron_bed.mp3) + brand slides + bundled ffmpeg. Every number is reproducible
from player_ratings_bpm_adjusted.csv (raw 1699 / adjusted 1529).
"""

import os
import re
import subprocess
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import imageio_ffmpeg
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

from generate_player_card import duotone_grain

ASSETS = Path("docs/growth/posts/assets")
F = "C:/Windows/Fonts/"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

NAVY = (10, 15, 26)
BLUE = (75, 139, 244)
ORANGE = (248, 161, 0)
TEXT = (236, 240, 247)
MUTED = (110, 125, 148)
RED = (239, 90, 90)

W = H = 1080
KESSLER_ID = "1631117"

NARRATION = (
    "This is the voice of the model. The Lakers just paid Walker Kessler a "
    "hundred and thirty million dollars. His box score rates him sixteen "
    "ninety nine, a fringe star. I rate him fifteen twenty nine. A hundred "
    "and seventy point haircut. Why? Box scores flatter rim protectors. "
    "Blocks, rebounds, and low turnovers look better than they actually "
    "play. It is the same discount I put on Rudy Gobert and every rim "
    "protector in the league, and last season the adjusted numbers predicted "
    "games better than the raw ones. The market priced the highlight reel. I "
    "priced the wins. One of us is wrong, and we will find out by June. "
    "Second Bounce. The receipts are public."
)

BALL = Image.open(ASSETS / "logo_substack.png").convert("RGBA")


def font(name, size):
    return ImageFont.truetype(F + name, size)


def base():
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=BLUE)
    return img, d


def kicker(d, text, color=ORANGE, y=90):
    d.text((80, y), text, font=font("seguibl.ttf", 34), fill=color)


def footer(img, d, url=True):
    img.paste(BALL.resize((52, 52)), (80, H - 102), BALL.resize((52, 52)))
    d.text((148, H - 92), "SECOND BOUNCE", font=font("seguibl.ttf", 36),
           fill=TEXT)
    if url:
        d.text((W - 80, H - 84), "secondbounce.substack.com",
               font=font("segoeui.ttf", 28), fill=MUTED, anchor="ra")


def slide1():
    img, d = base()
    try:
        r = requests.get(
            f"https://cdn.nba.com/headshots/nba/latest/1040x760/{KESSLER_ID}.png",
            timeout=30)
        r.raise_for_status()
        head = duotone_grain(Image.open(BytesIO(r.content)))
        hw = 640
        head = head.resize((hw, int(hw * head.height / head.width)))
        img.paste(head, (W - hw + 40, H - head.height), head)
    except Exception as e:
        print("headshot failed, text-only hook:", e)
    kicker(d, "THE VOICE OF THE MODEL")
    d.text((80, 175), "THE $130M", font=font("seguibl.ttf", 118), fill=TEXT)
    d.text((80, 305), "DISAGREEMENT", font=font("seguibl.ttf", 96), fill=TEXT)
    d.text((80, 445), "The market and the model do not\nagree on Walker Kessler.",
           font=font("segoeui.ttf", 44), fill=MUTED)
    footer(img, d, url=False)
    return img


def slide2():
    img, d = base()
    kicker(d, "THE MARKET SAYS", color=MUTED)
    d.text((80, 210), "1,699", font=font("seguibl.ttf", 290), fill=TEXT)
    d.text((86, 540), "RAW BOX-SCORE RATING", font=font("seguibl.ttf", 46),
           fill=MUTED)
    d.text((86, 616), "$130 million, four years", font=font("segoeui.ttf", 46),
           fill=ORANGE)
    footer(img, d)
    return img


def slide3():
    img, d = base()
    kicker(d, "THE MODEL SAYS")
    d.text((80, 210), "1,529", font=font("seguibl.ttf", 290), fill=BLUE)
    d.text((86, 540), "ADJUSTED RATING", font=font("seguibl.ttf", 46),
           fill=TEXT)
    d.text((86, 616), "a 170-point haircut", font=font("segoeui.ttf", 46),
           fill=RED)
    footer(img, d)
    return img


def slide4():
    img, d = base()
    kicker(d, "WHY THE HAIRCUT")
    lines = [
        "Box scores flatter rim protectors.",
        "Blocks, rebounds, low turnovers look",
        "better than they actually play.",
        "",
        "Same discount we carry on Gobert.",
        "Last season, adjusted beat raw.",
    ]
    y = 230
    for ln in lines:
        d.text((80, y), ln, font=font("segoeuib.ttf", 52),
               fill=TEXT if ln and not ln.startswith("Same") else MUTED)
        y += 88 if ln else 44
    footer(img, d)
    return img


def slide5():
    img, d = base()
    img.paste(BALL.resize((220, 220)), (W // 2 - 110, 110),
              BALL.resize((220, 220)))
    f96 = font("seguibl.ttf", 96)
    d.text((W // 2, 380), "SECOND BOUNCE", font=f96, fill=TEXT, anchor="ma")
    total_w = d.textlength("SECOND BOUNCE", font=f96)
    bw = d.textlength("BOUNCE", font=f96)
    x0 = W // 2 - total_w / 2 + d.textlength("SECOND ", font=f96)
    w1, w2 = int(bw * 0.62), int(bw * 0.30)
    h1, h2 = int(w1 * 0.10), int(w2 * 0.10)
    y = 520
    d.arc([x0, y - h1, x0 + w1, y + h1], 180, 360, fill=BLUE, width=5)
    x2 = x0 + w1 + int(bw * 0.04)
    d.arc([x2, y - h2, x2 + w2, y + h2], 180, 360, fill=BLUE, width=5)
    d.text((W // 2, 590), "We'll find out by June.",
           font=font("segoeui.ttf", 46), fill=MUTED, anchor="ma")
    d.text((W // 2, 700), "[ 70.6% · 657 games · verified walk-forward ]",
           font=font("consola.ttf", 34), fill=MUTED, anchor="ma")
    d.text((W // 2, 810), "secondbounce.substack.com",
           font=font("segoeuib.ttf", 40), fill=BLUE, anchor="ma")
    return img


def audio_duration(path):
    p = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True,
                       text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    return (float(m.group(1)) * 3600 + float(m.group(2)) * 60
            + float(m.group(3)))


def main():
    load_dotenv(".env")
    nar = ASSETS / "kessler_narration.mp3"
    r = requests.post(
        "https://api.elevenlabs.io/v1/text-to-speech/SAz9YHcvj6GT2YYXdXww"
        "?output_format=mp3_44100_128",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        json={"text": NARRATION, "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75,
                                 "style": 0.25}},
        timeout=300)
    r.raise_for_status()
    nar.write_bytes(r.content)
    dur = audio_duration(nar)
    print(f"narration: {dur:.1f}s")

    slides = [slide1(), slide2(), slide3(), slide4(), slide5()]
    weights = [0.17, 0.17, 0.17, 0.28, 0.21]
    total = dur + 2.0
    lines = []
    for i, (img, wgt) in enumerate(zip(slides, weights)):
        p = ASSETS / f"_kv_slide{i}.png"
        img.save(p)
        lines.append(f"file '{p.resolve()}'\nduration {total * wgt:.2f}")
    lines.append(f"file '{(ASSETS / '_kv_slide4.png').resolve()}'")
    concat = ASSETS / "_kv_list.txt"
    concat.write_text("\n".join(lines), encoding="utf-8")

    out = ASSETS / "kessler_tax.mp4"
    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
           "-i", str(nar), "-i", str(ASSETS / "lebron_bed.mp3"),
           "-filter_complex",
           f"[1:a]adelay=800|800[nar];"
           f"[2:a]volume=0.18,afade=t=out:st={total-3:.1f}:d=3[bed];"
           f"[nar][bed]amix=inputs=2:duration=longest:dropout_transition=3[a]",
           "-map", "0:v", "-map", "[a]", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "160k", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-1200:])
        sys.exit(1)
    for f in ASSETS.glob("_kv_*"):
        f.unlink()
    print(f"video: {out} ({out.stat().st_size // 1024} KB, {total:.1f}s)")


if __name__ == "__main__":
    main()

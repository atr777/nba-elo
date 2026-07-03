"""Build the LeBron $3.9M 'voice of the model' video for X (1080x1080).

Narration: River TTS. Music: ElevenLabs bed (lebron_bed.mp3, pre-generated).
Slides: brand-styled PIL frames. Assembly: bundled ffmpeg.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import imageio_ffmpeg
import pandas as pd
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_player_card import duotone_grain  # noqa: E402

ASSETS = Path("docs/growth/posts/assets")
F = "C:/Windows/Fonts/"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

NAVY = (10, 15, 26)
BLUE = (75, 139, 244)
ORANGE = (248, 161, 0)
TEXT = (236, 240, 247)
MUTED = (110, 125, 148)

NARRATION = (
    "This is the voice of the model. LeBron James is reportedly willing to "
    "sign for three point nine million dollars. In my system, he rates "
    "nineteen forty seven. An average NBA player rates fifteen hundred. That "
    "is the largest free value in basketball, and whoever captures it moves "
    "my forecast overnight. The suitors: Golden State. Denver. Philadelphia. "
    "Cleveland. I don't do narratives. I do numbers. And the numbers say the "
    "next contender might cost the league minimum. Second Bounce. The "
    "receipts are public."
)

W = H = 1080


def font(name, size):
    return ImageFont.truetype(F + name, size)


def base():
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=BLUE)
    return img, d


def kicker(d, text, y=90):
    d.text((80, y), text, font=font("seguibl.ttf", 34), fill=ORANGE)


BALL = Image.open(ASSETS / "logo_substack.png").convert("RGBA")


def footer(img, d, url=True):
    ball = BALL.resize((52, 52))
    img.paste(ball, (80, H - 102), ball)
    d.text((148, H - 92), "SECOND BOUNCE", font=font("seguibl.ttf", 36),
           fill=TEXT)
    if url:
        d.text((W - 80, H - 84), "secondbounce.substack.com",
               font=font("segoeui.ttf", 28), fill=MUTED, anchor="ra")


def slide1():
    img, d = base()
    r = requests.get(
        "https://cdn.nba.com/headshots/nba/latest/1040x760/2544.png",
        timeout=30)
    head = duotone_grain(Image.open(__import__("io").BytesIO(r.content)))
    hw = 700
    head = head.resize((hw, int(hw * head.height / head.width)))
    img.paste(head, (W - hw + 60, H - head.height), head)
    kicker(d, "THE VOICE OF THE MODEL")
    d.text((80, 170), "THE $3.9M", font=font("seguibl.ttf", 120), fill=TEXT)
    d.text((80, 300), "QUESTION", font=font("seguibl.ttf", 120), fill=TEXT)
    d.text((80, 470), "LeBron is reportedly willing\nto sign for the minimum.",
           font=font("segoeui.ttf", 44), fill=MUTED)
    footer(img, d, url=False)
    return img


def slide2():
    img, d = base()
    kicker(d, "WHAT THE MARKET WOULD GET")
    d.text((80, 200), "1,947", font=font("seguibl.ttf", 300), fill=BLUE)
    d.text((86, 540), "LEBRON JAMES, AGE 41", font=font("seguibl.ttf", 48),
           fill=TEXT)
    d.text((86, 620), "1,500 = average NBA player",
           font=font("segoeui.ttf", 42), fill=MUTED)
    footer(img, d)
    return img


def slide3():
    img, d = base()
    kicker(d, "THE VALUE GAP")
    # two bars: average player vs LeBron, price tags attached
    d.text((80, 200), "AVERAGE PLAYER", font=font("segoeuib.ttf", 36),
           fill=MUTED)
    d.rectangle([80, 250, 80 + 500, 320], fill=(38, 50, 72))
    d.text((80 + 510, 262), "1,500", font=font("seguibl.ttf", 40), fill=MUTED)
    d.text((80, 400), "LEBRON AT THE MINIMUM", font=font("segoeuib.ttf", 36),
           fill=TEXT)
    d.rectangle([80, 450, 80 + 810, 520], fill=BLUE)
    d.text((80 + 820, 462), "1,947", font=font("seguibl.ttf", 40), fill=BLUE)
    d.text((80, 620), "The largest free value in basketball.",
           font=font("segoeui.ttf", 46), fill=TEXT)
    footer(img, d)
    return img


def slide4():
    img, d = base()
    kicker(d, "THE SUITORS")
    th = pd.read_csv("data/exports/team_elo_history_phase_1_6.csv")
    latest = th.sort_values("date").groupby("team_name").last().reset_index()

    def elo(frag):
        m = latest[latest.team_name.str.contains(frag, case=False)]
        return int(round(m.rating_after.iloc[-1])) if len(m) else None

    teams = [("gs", "Golden State", elo("Warriors")),
             ("den", "Denver", elo("Nuggets")),
             ("phi", "Philadelphia", elo("76ers")),
             ("cle", "Cleveland", elo("Cavaliers"))]
    y = 220
    for abbr, name, rating in teams:
        p = ASSETS / "logos" / f"{abbr}.png"
        if not p.exists():
            r = requests.get(
                f"https://a.espncdn.com/i/teamlogos/nba/500/{abbr}.png",
                timeout=30)
            p.write_bytes(r.content)
        logo = Image.open(p).convert("RGBA").resize((120, 120))
        img.paste(logo, (80, y), logo)
        d.text((230, y + 18), name, font=font("seguibl.ttf", 52), fill=TEXT)
        d.text((W - 80, y + 22), f"{rating:,}" if rating else "—",
               font=font("seguibl.ttf", 52), fill=BLUE, anchor="ra")
        y += 170
    d.text((80, y + 10), "Team rating today. Add him and watch it move.",
           font=font("segoeui.ttf", 40), fill=MUTED)
    footer(img, d)
    return img


def slide5():
    img, d = base()
    ball = BALL.resize((220, 220))
    img.paste(ball, (W // 2 - 110, 110), ball)
    d.text((W // 2, 380), "SECOND BOUNCE", font=font("seguibl.ttf", 96),
           fill=TEXT, anchor="ma")
    # bounce arcs, anchored under "BOUNCE"
    f96 = font("seguibl.ttf", 96)
    total_w = d.textlength("SECOND BOUNCE", font=f96)
    bw = d.textlength("BOUNCE", font=f96)
    x0 = W // 2 - total_w / 2 + d.textlength("SECOND ", font=f96)
    w1, w2 = int(bw * 0.62), int(bw * 0.30)
    h1, h2 = int(w1 * 0.10), int(w2 * 0.10)
    y = 520
    d.arc([x0, y - h1, x0 + w1, y + h1], 180, 360, fill=BLUE, width=5)
    x2 = x0 + w1 + int(bw * 0.04)
    d.arc([x2, y - h2, x2 + w2, y + h2], 180, 360, fill=BLUE, width=5)
    d.text((W // 2, 590), "NBA predictions that show their work",
           font=font("segoeui.ttf", 44), fill=MUTED, anchor="ma")
    d.text((W // 2, 700), "[ 70.6% · 657 games · verified walk-forward ]",
           font=font("consola.ttf", 36), fill=MUTED, anchor="ma")
    d.text((W // 2, 810), "secondbounce.substack.com",
           font=font("segoeuib.ttf", 40), fill=BLUE, anchor="ma")
    return img


def audio_duration(path):
    p = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True,
                       text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    hh, mm, ss = float(m.group(1)), float(m.group(2)), float(m.group(3))
    return hh * 3600 + mm * 60 + ss


def main():
    load_dotenv(".env")
    # narration
    nar = ASSETS / "lebron_39m_narration.mp3"
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
    weights = [0.16, 0.18, 0.20, 0.26, 0.20]
    total = dur + 2.0
    lines = []
    for i, (img, wgt) in enumerate(zip(slides, weights)):
        p = ASSETS / f"_vid_slide{i}.png"
        img.save(p)
        lines.append(f"file '{p.resolve()}'\nduration {total * wgt:.2f}")
    lines.append(f"file '{(ASSETS / '_vid_slide4.png').resolve()}'")
    concat = ASSETS / "_vid_list.txt"
    concat.write_text("\n".join(lines), encoding="utf-8")

    out = ASSETS / "lebron_39m.mp4"
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
    print(f"video: {out} ({out.stat().st_size // 1024} KB, {total:.1f}s)")


if __name__ == "__main__":
    main()

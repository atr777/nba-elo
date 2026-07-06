"""LeBron-to-Cleveland decision video (creative build for X, 1080x1080).

Elevated beyond the standard slideshow:
- River narration, per-slide-synced (audio welded to visuals)
- ElevenLabs cinematic building bed (cle_bed.mp3) + crowd-roar SFX at the reveal
- Ken Burns motion on every slide (each clip = its own narration segment, so
  sync holds) + fade from/to black
Roster verified 2026-07-06 (Harden in via Garland trade; Garland gone).
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
WINE = (134, 32, 52)  # Cleveland wine, a nod without leaving the palette
TEXT = (236, 240, 247)
MUTED = (110, 125, 148)
W = H = 1080

SEG_TEXTS = [
    "This is the voice of the model. LeBron James is going home to Cleveland. "
    "For the third time.",
    "He signs for the minimum. In my system he rates nineteen forty seven. One "
    "of the great bargains I have ever priced.",
    "And the roster is loaded. James Harden, twenty one thirty six. Evan "
    "Mobley, eighteen ninety six. Donovan Mitchell, eighteen sixty five. "
    "Cleveland already rated sixteen thirty seven, a contender.",
    "So this is the most top-heavy roster I have ever been asked to rate. The "
    "talent is not the question. Harden, Mitchell, and now LeBron. Three men "
    "who have spent their careers with the ball in their hands. And one ball "
    "to share.",
    "The ceiling is a championship. The math is a puzzle. And I will be "
    "watching every possession. Second Bounce. The receipts are public.",
]

BALL = Image.open(ASSETS / "logo_substack.png").convert("RGBA")


def font(n, s):
    return ImageFont.truetype(F + n, s)


def base():
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=BLUE)
    return img, d


def footer(img, d, url=True):
    img.paste(BALL.resize((48, 48)), (78, H - 96), BALL.resize((48, 48)))
    d.text((140, H - 88), "SECOND BOUNCE", font=font("seguibl.ttf", 32),
           fill=TEXT)
    if url:
        d.text((W - 78, H - 82), "secondbounce.substack.com",
               font=font("segoeui.ttf", 26), fill=MUTED, anchor="ra")


def slide1():
    img, d = base()
    r = requests.get(
        "https://cdn.nba.com/headshots/nba/latest/1040x760/2544.png", timeout=30)
    head = duotone_grain(Image.open(BytesIO(r.content)))
    hw = 660
    head = head.resize((hw, int(hw * head.height / head.width)))
    img.paste(head, (W - hw + 40, H - head.height), head)
    d.text((78, 88), "THE VOICE OF THE MODEL", font=font("seguibl.ttf", 30),
           fill=ORANGE)
    d.text((74, 150), "HOME.", font=font("seguibl.ttf", 150), fill=TEXT)
    d.text((74, 300), "AGAIN.", font=font("seguibl.ttf", 150), fill=BLUE)
    d.text((80, 495), "LeBron returns to Cleveland\nfor the third time.",
           font=font("segoeui.ttf", 42), fill=MUTED)
    footer(img, d, url=False)
    return img


def slide2():
    img, d = base()
    d.text((78, 120), "WHAT CLEVELAND GETS", font=font("seguibl.ttf", 30),
           fill=ORANGE)
    d.text((70, 210), "1,947", font=font("seguibl.ttf", 300), fill=BLUE)
    d.text((80, 560), "LEBRON JAMES, FOR THE MINIMUM",
           font=font("seguibl.ttf", 44), fill=TEXT)
    d.text((80, 632), "1500 = league average", font=font("segoeui.ttf", 40),
           fill=MUTED)
    footer(img, d)
    return img


def slide3():
    img, d = base()
    d.text((78, 96), "THE ROSTER HE JOINS", font=font("seguibl.ttf", 30),
           fill=ORANGE)
    rows = [("James Harden", "2,136"), ("Evan Mobley", "1,896"),
            ("Donovan Mitchell", "1,865"), ("Jarrett Allen", "1,831")]
    y = 210
    for name, val in rows:
        d.text((80, y), name, font=font("seguibl.ttf", 52), fill=TEXT)
        d.text((W - 80, y + 4), val, font=font("seguibl.ttf", 52), fill=BLUE,
               anchor="ra")
        y += 96
    d.text((80, y + 20), "Team rating 1,637 — a contender before he arrived.",
           font=font("segoeui.ttf", 38), fill=MUTED)
    footer(img, d)
    return img


def slide4():
    img, d = base()
    d.text((78, 150), "THE VERDICT", font=font("seguibl.ttf", 30), fill=ORANGE)
    d.text((74, 240), "THREE", font=font("seguibl.ttf", 128), fill=TEXT)
    d.text((74, 372), "CREATORS.", font=font("seguibl.ttf", 128), fill=TEXT)
    d.text((74, 520), "ONE BALL.", font=font("seguibl.ttf", 128), fill=BLUE)
    d.text((80, 700), "The talent isn't the question. The touches are.",
           font=font("segoeui.ttf", 40), fill=MUTED)
    footer(img, d)
    return img


def slide5():
    img, d = base()
    img.paste(BALL.resize((210, 210)), (W // 2 - 105, 120),
              BALL.resize((210, 210)))
    f96 = font("seguibl.ttf", 92)
    d.text((W // 2, 380), "SECOND BOUNCE", font=f96, fill=TEXT, anchor="ma")
    tw = d.textlength("SECOND BOUNCE", font=f96)
    bw = d.textlength("BOUNCE", font=f96)
    x0 = W // 2 - tw / 2 + d.textlength("SECOND ", font=f96)
    w1, w2 = int(bw * 0.62), int(bw * 0.30)
    yy = 505
    d.arc([x0, yy - int(w1 * 0.1), x0 + w1, yy + int(w1 * 0.1)], 180, 360,
          fill=BLUE, width=5)
    x2 = x0 + w1 + int(bw * 0.04)
    d.arc([x2, yy - int(w2 * 0.1), x2 + w2, yy + int(w2 * 0.1)], 180, 360,
          fill=BLUE, width=5)
    d.text((W // 2, 575), "We'll find out, game by game.",
           font=font("segoeui.ttf", 44), fill=MUTED, anchor="ma")
    d.text((W // 2, 690), "[ 70.6% · 657 games · verified walk-forward ]",
           font=font("consola.ttf", 34), fill=MUTED, anchor="ma")
    d.text((W // 2, 800), "secondbounce.substack.com",
           font=font("segoeuib.ttf", 40), fill=BLUE, anchor="ma")
    return img


def dur(path):
    p = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    return float(m[1]) * 3600 + float(m[2]) * 60 + float(m[3])


def main():
    load_dotenv(".env")
    key = os.environ["ELEVENLABS_API_KEY"]

    segs, durs = [], []
    for i, text in enumerate(SEG_TEXTS):
        p = ASSETS / f"_cseg{i}.mp3"
        r = requests.post(
            "https://api.elevenlabs.io/v1/text-to-speech/SAz9YHcvj6GT2YYXdXww"
            "?output_format=mp3_44100_128", headers={"xi-api-key": key},
            json={"text": text, "model_id": "eleven_multilingual_v2",
                  "voice_settings": {"stability": 0.5, "similarity_boost": 0.75,
                                     "style": 0.3}}, timeout=300)
        r.raise_for_status()
        p.write_bytes(r.content)
        segs.append(p)
        durs.append(dur(p))
        print(f"seg{i}: {durs[-1]:.1f}s")

    LEAD = 0.6
    slides = [slide1(), slide2(), slide3(), slide4(), slide5()]
    disp = [durs[0] + LEAD] + durs[1:]
    total = LEAD + sum(durs)

    # Ken Burns clip per slide (each clip == its narration segment -> sync holds)
    clips = []
    for i, (img, dd) in enumerate(zip(slides, disp)):
        sp = ASSETS / f"_cslide{i}.png"
        img.save(sp)
        cp = ASSETS / f"_cclip{i}.mp4"
        frames = max(2, round(dd * 30))
        zdir = "zoom+0.00035" if i % 2 == 0 else "zoom+0.0006"
        subprocess.run([FFMPEG, "-y", "-loop", "1", "-i", str(sp),
                        "-vf", f"scale=1350:1350,zoompan=z='min({zdir},1.12)'"
                        f":d={frames}:s=1080x1080:fps=30",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        str(cp)], capture_output=True, text=True)
        clips.append(cp)

    listf = ASSETS / "_cclips.txt"
    listf.write_text("\n".join(f"file '{c.resolve()}'" for c in clips),
                     encoding="utf-8")
    silent = ASSETS / "_csilent.mp4"
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i",
                    str(listf), "-c", "copy", str(silent)],
                   capture_output=True, text=True)

    out = ASSETS / "lebron_cleveland_decision.mp4"
    ms = int(LEAD * 1000)
    cmd = [FFMPEG, "-y", "-i", str(silent)]
    for s in segs:
        cmd += ["-i", str(s)]
    cmd += ["-i", str(ASSETS / "cle_bed.mp3"), "-i", str(ASSETS / "cle_crowd.mp3")]
    nlab = "".join(f"[{k}:a]" for k in range(1, 6))
    cmd += ["-filter_complex",
            f"[0:v]fade=t=in:st=0:d=0.7,fade=t=out:st={total-0.8:.1f}:d=0.8[v];"
            f"{nlab}concat=n=5:v=0:a=1,adelay={ms}|{ms}[nar];"
            f"[6:a]volume=0.2,afade=t=in:st=0:d=1,afade=t=out:st={total-3:.1f}:d=3[bed];"
            f"[7:a]adelay={ms}|{ms},volume=0.42,afade=t=out:st=4.5:d=1.5[sfx];"
            f"[nar][bed][sfx]amix=inputs=3:duration=longest:dropout_transition=2[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "160k", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-1800:])
        sys.exit(1)
    for f in list(ASSETS.glob("_cseg*")) + list(ASSETS.glob("_cslide*")) + \
            list(ASSETS.glob("_cclip*")) + [listf, silent]:
        f.unlink()
    print(f"video: {out} ({out.stat().st_size // 1024} KB, {total:.1f}s)")


if __name__ == "__main__":
    main()

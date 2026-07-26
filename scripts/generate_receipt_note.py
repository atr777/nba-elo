"""THE RECEIPT: the house visual format for Substack Notes (chosen by Aaron,
2026-07-26, from three candidates in generate_note_mockups.py).

A photographed-looking thermal receipt: textured paper, cross fold, perforated rules,
barcode, scalloped bottom edge. 1080x1350 (4:5 portrait, the format the feed rewards).
BRAND.md calls the receipt our one ownable signature; this renders it literally
instead of as a one-line stamp.

Every number is READ FROM THE HONEST LOG, never passed in by hand, so a receipt
cannot drift from what the audit would reproduce (non-negotiable #1 in CLAUDE.md).

    python scripts/generate_receipt_note.py season       # season summary
    python scripts/generate_receipt_note.py calibration  # stated vs actual
    python scripts/generate_receipt_note.py nightly      # one night's graded slate
    python scripts/generate_receipt_note.py nightly --date 20260510
    python scripts/generate_receipt_note.py --list

Output: docs/growth/posts/assets/receipts/receipt_<type>_<YYYYMMDD>.png

USE IT SPARINGLY. Aaron's rule, 2026-07-26: not every note gets an image, or the
feed looks automated. Target roughly one in three; the receipt is for notes making a
claim that wants proof. See docs/growth/ENGAGEMENT_PLAYBOOK.md.
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
LOG_CSV = ROOT / "data/exports/prediction_tracking_honest.csv"
OUT_DIR = ROOT / "docs/growth/posts/assets/receipts"

W, H = 1080, 1350
NAVY_DEEP = (8, 12, 20)
INK = (24, 33, 48)
RECEIPT_GRAY = (137, 135, 129)

# The slip is inset on the navy field. Its LENGTH adapts to the content, because a
# real till roll is as long as what was printed on it: a two-game night on a
# full-height slip leaves an obviously fake blank tail.
PAD, TOP = 90, 62
SLIP_MIN_H, SLIP_MAX_H = 620, H - 62 - 96
FOOTER_H = 210

FONTS = "C:/Windows/Fonts/"
WIDTH_CHARS = 34

TEAM_ABBREVS = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL',
    'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL',
    'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP',
    'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL',
    'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR',
    'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR',
    'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS',
}


def mono(sz, bold=False):
    return ImageFont.truetype(FONTS + ("consolab.ttf" if bold else "consola.ttf"), sz)


def sans(sz):
    return ImageFont.truetype(FONTS + "segoeui.ttf", sz)


def abbr(name: str) -> str:
    return TEAM_ABBREVS.get(str(name), str(name)[:3].upper())


# ------------------------------------------------------------------ texture
def paper(w: int, h: int, seed: int = 7, strength: float = 1.0) -> Image.Image:
    """Thermal-paper stock: soft cloudy mottling, a cross fold, fine grain.

    Built from low-resolution noise upscaled smoothly (that is what gives the broad
    cloudy variation of real paper, rather than uniform static), then a little
    high-frequency grain on top, then fold seams.

    RESTORED 2026-07-26 at Aaron's request. A heavier, photoreal version (uneven
    lighting, antisymmetric fold shading, corner vignette) was tried and rejected as
    too dirty; this quieter stock is the house look. `strength` scales every
    amplitude, so it can still be nudged from the CLI without another rewrite.
    """
    rng = np.random.default_rng(seed)
    s = strength

    # broad mottling: 16x20 noise stretched to full size
    low = rng.normal(0, 1, (20, 16))
    mottle = np.array(Image.fromarray(
        ((low - low.min()) / np.ptp(low) * 255).astype(np.uint8)
    ).resize((w, h), Image.BICUBIC), dtype=np.float32)
    mottle = (mottle - mottle.mean()) / 255.0 * 13.0 * s  # +-13 levels, subtle

    grain = rng.normal(0, 2.1 * s, (h, w))

    base = 250.0 + mottle + grain
    # very slightly cool paper, like the reference photo
    arr = np.stack([base - 1.0, base - 0.4, base], axis=2)

    # cross fold: one horizontal seam, one vertical, each a dark line with a
    # lighter lift beside it, blurred. Real folds catch light on one side.
    fold_y, fold_x = int(h * 0.47), int(w * 0.52)
    seam = np.zeros((h, w), dtype=np.float32)
    for off, val in ((-2, 5.0), (-1, 3.0), (0, -7.0), (1, -3.0), (2, 3.5)):
        val *= s
        yy, xx = fold_y + off, fold_x + off
        if 0 <= yy < h:
            seam[yy, :] += val
        if 0 <= xx < w:
            seam[:, xx] += val
    seam = np.array(Image.fromarray(
        np.clip(seam + 128, 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(1.6)), dtype=np.float32) - 128.0
    arr += seam[:, :, None]

    # a couple of faint diagonal creases so it does not read as a flat gradient
    for (x0, y0, x1, y1) in ((int(w * .1), int(h * .22), int(w * .95), int(h * .30)),
                             (int(w * .05), int(h * .70), int(w * .9), int(h * .62))):
        cre = Image.new("L", (w, h), 128)
        ImageDraw.Draw(cre).line([x0, y0, x1, y1], fill=121, width=3)
        arr += (np.array(cre.filter(ImageFilter.GaussianBlur(3.0)),
                         dtype=np.float32) - 128.0)[:, :, None] * 0.9 * s

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def barcode(d: ImageDraw.ImageDraw, cx: int, y: int, seed_text: str,
            h_px: int = 62, target_w: int = 330) -> None:
    """Decorative barcode, deterministic from seed_text so the same receipt always
    renders identically. Not a real symbology and never presented as scannable."""
    rng = np.random.default_rng(abs(hash(seed_text)) % (2**32))
    widths = rng.choice([2, 2, 3, 4, 6], size=90)
    total = 0
    bars = []
    for i, bw in enumerate(widths):
        if total + bw > target_w:
            break
        bars.append((total, int(bw), i % 2 == 0))
        total += int(bw) + 2
    x0 = cx - total // 2
    for off, bw, dark in bars:
        if dark:
            d.rectangle([x0 + off, y, x0 + off + bw, y + h_px], fill=(18, 20, 26))


def dashed(d: ImageDraw.ImageDraw, x0: int, x1: int, y: int,
           dash: int = 9, gap: int = 7, w: int = 3, fill=(60, 68, 82)) -> None:
    x = x0
    while x < x1:
        d.line([x, y, min(x + dash, x1), y], fill=fill, width=w)
        x += dash + gap


def scallop(img: Image.Image, slip, bg=NAVY_DEEP, r: int = 22) -> None:
    """Wavy bottom edge, like a torn-off till roll.

    Carves background-coloured semicircles UP into the paper; the paper left between
    them forms the downward lobes. PIL angles run clockwise from 3 o'clock with y
    increasing downward, so the upper half of the bounding box is start=180 end=360.
    Using 0..180 draws the lower half, which lands below the slip and is invisible.
    """
    d = ImageDraw.Draw(img)
    x0, _, x1, y = slip
    x = x0 - r  # start half a lobe early so the left corner is not a flat stub
    while x < x1:
        d.pieslice([x, y - r, x + 2 * r, y + r], start=180, end=360, fill=bg)
        x += 2 * r


# --------------------------------------------------------------------- data
def load_stats() -> dict:
    if not LOG_CSV.exists():
        sys.exit(f"missing {LOG_CSV}")
    d = pd.read_csv(LOG_CSV).dropna(subset=["correct"])
    n = len(d)
    correct = int(d["correct"].sum())
    buckets = []
    if "confidence" in d.columns:
        for lo, hi in [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]:
            sub = d[(d["confidence"] > lo) & (d["confidence"] <= hi)]
            if len(sub) >= 25:
                buckets.append((f"{int(lo*100)}-{min(int(hi*100),100)}%",
                                100 * sub["correct"].mean(), len(sub)))
    season = "2025-26"
    if "date" in d.columns and n:
        yr = int(str(d["date"].max())[:4])
        season = f"{yr-1}-{str(yr)[-2:]}"
    return {"n": n, "correct": correct, "wrong": n - correct,
            "accuracy": 100 * correct / n if n else 0.0,
            "buckets": buckets, "season": season, "df": d}


def load_night(target: str | None) -> dict:
    """One night's graded slate. Defaults to the most recent date in the log, which
    in the offseason is the last game played rather than today."""
    s = load_stats()
    d = s["df"]
    if "date" not in d.columns:
        sys.exit("log has no date column")
    day = str(target) if target else str(int(d["date"].max()))
    night = d[d["date"].astype(str) == day].copy()
    if night.empty:
        sys.exit(f"no graded games on {day} (latest is {int(d['date'].max())})")
    night = night.sort_values("confidence", ascending=False)
    rows = []
    for _, g in night.iterrows():
        pick = abbr(g["home_team_name"]) if g["predicted_winner"] == "home" \
            else abbr(g["away_team_name"])
        rows.append({
            "matchup": f"{abbr(g['away_team_name'])} @ {abbr(g['home_team_name'])}",
            "pick": pick, "conf": 100 * float(g["confidence"]),
            "hit": bool(g["correct"]),
        })
    hits = sum(r["hit"] for r in rows)
    return {"day": day, "rows": rows, "hits": hits, "n": len(rows),
            "pretty": datetime.strptime(day, "%Y%m%d").strftime("%m/%d/%Y")}


# ------------------------------------------------------------------ render
def _emit(blocks, d, x0, x1, y, centre=None, pitch: int = 38) -> int:
    """Lay the blocks out and return the final y. With d=None it measures only, which
    is how the slip length is chosen before any paper is drawn."""
    inner = x1 - x0
    for b in blocks:
        kind = b[0]
        if kind == "title":
            if d: centre(b[1], mono(40, True), INK, y)
            y += 56
        elif kind == "sub":
            if d: centre(b[1], mono(24), RECEIPT_GRAY, y)
            y += 54
        elif kind == "head":
            if d: centre(b[1], mono(26, True), INK, y)
            y += 46
        elif kind == "rule":
            if d:
                if b[1] == "=":
                    d.line([x0, y + 6, x1, y + 6], fill=INK, width=3)
                    d.line([x0, y + 14, x1, y + 14], fill=INK, width=3)
                else:
                    dashed(d, x0, x1, y + 10)
            y += 36
        elif kind in ("row", "bigrow", "smallrow"):
            if d:
                f = mono({"row": 30, "bigrow": 30, "smallrow": 26}[kind],
                         kind == "bigrow")
                d.text((x0, y), b[1], font=f, fill=INK)
                vw = d.textbbox((0, 0), b[2], font=f)[2]
                d.text((x0 + inner - vw, y), b[2], font=f, fill=INK)
            y += 46 if kind != "smallrow" else pitch
        elif kind == "line":
            if d: d.text((x0, y), b[1], font=mono(28), fill=INK)
            y += 42
        elif kind == "gap":
            y += b[1]
    return y


def _fit(blocks: list, x0: int, x1: int):
    """Return (blocks, pitch, content_h) that fits inside SLIP_MAX_H."""
    for pitch in (38, 34, 30):
        trial = list(blocks)
        while True:
            h = _emit(trial, None, x0, x1, 0, pitch=pitch) + 40
            if TOP + h + FOOTER_H <= SLIP_MAX_H:
                return trial, pitch, h
            drop = next((i for i in range(len(trial) - 1, -1, -1)
                         if trial[i][0] == "line"), None)
            if drop is None:
                break          # nothing decorative left; try a tighter pitch
            trial.pop(drop)
    return blocks, 30, _emit(blocks, None, x0, x1, 0, pitch=30) + 40


def render(blocks: list, out: Path, barcode_seed: str = "",
           texture: float = 1.0) -> Path:
    x0, x1 = PAD + 58, W - PAD - 58

    # pass 1: measure and make it FIT. A 15-game slate overruns the slip, so tighten
    # the row pitch first, then sacrifice the closing slogan lines. Never drop a game:
    # the itemised picks ARE the receipt, the tagline is decoration.
    blocks, pitch, content_h = _fit(blocks, x0, x1)
    slip_h = max(SLIP_MIN_H, min(SLIP_MAX_H, TOP + content_h + FOOTER_H))
    # centre a short slip rather than pinning it to the top, so a light slate does not
    # leave the whole lower half of the frame empty
    slip_top = max(40, (H - slip_h - 56) // 2)
    slip = (PAD, slip_top, W - PAD, slip_top + slip_h)

    img = Image.new("RGB", (W, H), NAVY_DEEP)
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rectangle([slip[0] + 6, slip[1] + 10, slip[2] + 6, slip[3] + 12],
                                fill=120)
    img.paste(Image.new("RGB", (W, H), (0, 0, 0)),
              (0, 0), sh.filter(ImageFilter.GaussianBlur(18)))
    img.paste(paper(slip[2] - slip[0], slip[3] - slip[1], strength=texture),
              (slip[0], slip[1]))

    d = ImageDraw.Draw(img)

    def centre(text, font, fill, yy):
        w = d.textbbox((0, 0), text, font=font)[2]
        d.text(((W - w) / 2, yy), text, font=font, fill=fill)

    y = slip[1] + 30
    dashed(d, x0, x1, y + 4)  # perforation under the top edge, as in the reference
    _emit(blocks, d, x0, x1, y + 40, centre, pitch=pitch)

    fy = slip[3] - FOOTER_H + 20
    dashed(d, x0, x1, fy)
    for i, txt in enumerate(("VERIFIED WALK-FORWARD", f"{date.today():%m/%d/%Y}")):
        w = d.textbbox((0, 0), txt, font=mono(23))[2]
        d.text(((W - w) / 2, fy + 20 + i * 32), txt, font=mono(23), fill=RECEIPT_GRAY)
    barcode(d, W // 2, fy + 96, barcode_seed or str(date.today()))

    scallop(img, slip)
    u = "secondbounce.substack.com"
    uw = d.textbbox((0, 0), u, font=sans(24))[2]
    d.text(((W - uw) / 2, slip[3] + 34), u, font=sans(24), fill=(96, 106, 124))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


# ------------------------------------------------------------------- types
def season_receipt(s: dict) -> list:
    return [
        ("title", "SECOND BOUNCE"), ("sub", "PREDICTION RECEIPT"),
        ("rule", "="), ("head", f"{s['season']} SEASON"), ("gap", 4),
        ("row", "GAMES CALLED", f"{s['n']}"),
        ("row", "CORRECT", f"{s['correct']}"),
        ("row", "WRONG", f"{s['wrong']}"),
        ("gap", 4), ("bigrow", "ACCURACY", f"{s['accuracy']:.2f}%"),
        ("gap", 6), ("rule", "-"),
        ("line", "EVERY PICK LOGGED"), ("line", "BEFORE TIP-OFF."),
        ("line", "GRADED AFTER THE FINAL."), ("line", "NEVER RECOMPUTED."),
        ("gap", 6), ("rule", "-"),
        ("line", "NO PICK DELETED."), ("line", "NO NUMBER REVISED"),
        ("line", "AFTER THE FACT."),
    ]


def calibration_receipt(s: dict) -> list:
    blocks = [("title", "SECOND BOUNCE"), ("sub", "CALIBRATION RECEIPT"),
              ("rule", "="), ("head", "WHAT WE SAID VS"), ("head", "WHAT HAPPENED"),
              ("gap", 4)]
    for label, won, n in s["buckets"]:
        blocks.append(("row", f" SAID {label} ({n})", f"WON {won:.1f}%"))
    blocks += [("gap", 6), ("rule", "-"),
               ("bigrow", "ALL GAMES", f"{s['accuracy']:.2f}%"),
               ("row", "SAMPLE", f"{s['n']}"),
               ("gap", 6), ("rule", "-"),
               ("line", "CONFIDENCE IS A CLAIM."), ("line", "THIS IS THE CHECK.")]
    return blocks


def nightly_receipt(nt: dict) -> list:
    """One night, itemised like a till roll. The in-season workhorse: every graded
    pick with the confidence we stated before tip, and whether it landed."""
    blocks = [("title", "SECOND BOUNCE"), ("sub", "NIGHTLY RECEIPT"),
              ("rule", "="), ("head", nt["pretty"]), ("gap", 4)]
    for r in nt["rows"]:
        blocks.append(("smallrow", f" {r['matchup']}",
                       f"{r['pick']} {r['conf']:.0f}%  {'HIT' if r['hit'] else 'MISS'}"))
    pct = 100 * nt["hits"] / nt["n"]
    blocks += [("gap", 6), ("rule", "-"),
               ("bigrow", "TONIGHT", f"{nt['hits']} OF {nt['n']}"),
               ("row", "", f"{pct:.0f}%"),
               ("gap", 6), ("rule", "-"),
               ("line", "PICKS LOGGED BEFORE TIP."), ("line", "MISSES PRINTED TOO.")]
    return blocks


TYPES = {"season": season_receipt, "calibration": calibration_receipt,
         "nightly": nightly_receipt}


def main() -> None:
    p = argparse.ArgumentParser(description="Render a receipt note image")
    p.add_argument("type", nargs="?", default="season", choices=sorted(TYPES))
    p.add_argument("--date", help="nightly only: YYYYMMDD (default: latest in log)")
    p.add_argument("--list", action="store_true")
    p.add_argument("--out")
    p.add_argument("--texture", type=float, default=1.0,
                   help="paper texture strength (0 = flat, 1 = default, 1.6 = heavy)")
    a = p.parse_args()
    if a.list:
        print("types:", ", ".join(sorted(TYPES)))
        return

    if a.type == "nightly":
        nt = load_night(a.date)
        blocks, seed, stamp = nightly_receipt(nt), f"night{nt['day']}", nt["day"]
        note = f"{nt['hits']} of {nt['n']} on {nt['pretty']}"
    else:
        s = load_stats()
        blocks = TYPES[a.type](s)
        seed = f"{a.type}{s['n']}"
        stamp = f"{date.today():%Y%m%d}"
        note = f"{s['n']} graded games, accuracy {s['accuracy']:.2f}%"

    out = Path(a.out) if a.out else OUT_DIR / f"receipt_{a.type}_{stamp}.png"
    render(blocks, out, barcode_seed=seed, texture=a.texture)
    print(f"wrote {out}\n  from {note}")


if __name__ == "__main__":
    main()

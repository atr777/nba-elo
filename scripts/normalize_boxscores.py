"""Canonicalize player_boxscores_all.csv so the player-ELO engine can read all of it.

The box-score file was written by two different scrapers over the years and they
disagree on three columns. The engine understands only the older dialect, so
every game written by the newer scraper is silently dropped: `process_game` finds
no player with numeric minutes, logs "No active players found", and moves on.
That is why player ratings froze at 2025-11-23 while the file itself held games
through 2026-03-08.

Dialect differences:

  column      old (engine understands)   new (silently dropped)
  ---------   ------------------------   ----------------------
  minutes     "38.0"                     "19:16"   (MM:SS)
  team_id     1..30  (our DB ids)        1610612737 (NBA ids)
  team_name   "Atlanta Hawks"            "ATL"

This script rewrites the new dialect into the old one, in place, after taking a
backup. It is idempotent: rows already in the old dialect are untouched, so it is
safe to run repeatedly (and safe to run after every future scrape).

Rows for non-NBA teams (All-Star squads, Guangzhou Loong-Lions, Hapoel Jerusalem)
are left alone; downstream code filters on team_id <= 30.

    python scripts/normalize_boxscores.py [--dry-run]
"""

import shutil
import sys
import unicodedata
from pathlib import Path

import pandas as pd

BOX = Path("data/raw/player_boxscores_all.csv")
BACKUP = Path("data/raw/player_boxscores_all.csv.bak")

NBA_TO_DB = {
    1610612737: (1, "Atlanta Hawks"), 1610612738: (2, "Boston Celtics"),
    1610612751: (17, "Brooklyn Nets"), 1610612766: (30, "Charlotte Hornets"),
    1610612741: (4, "Chicago Bulls"), 1610612739: (5, "Cleveland Cavaliers"),
    1610612742: (6, "Dallas Mavericks"), 1610612743: (7, "Denver Nuggets"),
    1610612765: (8, "Detroit Pistons"), 1610612744: (9, "Golden State Warriors"),
    1610612745: (10, "Houston Rockets"), 1610612754: (11, "Indiana Pacers"),
    1610612746: (12, "LA Clippers"), 1610612747: (13, "Los Angeles Lakers"),
    1610612763: (29, "Memphis Grizzlies"), 1610612748: (14, "Miami Heat"),
    1610612749: (15, "Milwaukee Bucks"), 1610612750: (16, "Minnesota Timberwolves"),
    1610612740: (3, "New Orleans Pelicans"), 1610612752: (18, "New York Knicks"),
    1610612760: (25, "Oklahoma City Thunder"), 1610612753: (19, "Orlando Magic"),
    1610612755: (20, "Philadelphia 76ers"), 1610612756: (21, "Phoenix Suns"),
    1610612757: (22, "Portland Trail Blazers"), 1610612758: (23, "Sacramento Kings"),
    1610612759: (24, "San Antonio Spurs"), 1610612761: (28, "Toronto Raptors"),
    1610612762: (26, "Utah Jazz"), 1610612764: (27, "Washington Wizards"),
}


def parse_minutes(v):
    """'19:16' -> 19.27 ; '38.0' -> 38.0 ; '' / NaN -> NaN. Never raises."""
    if pd.isna(v):
        return pd.NA
    s = str(v).strip()
    if not s:
        return pd.NA
    if ":" in s:
        try:
            mm, ss = s.split(":")[:2]
            return round(int(mm) + int(ss) / 60.0, 2)
        except (ValueError, TypeError):
            return pd.NA
    try:
        return float(s)
    except ValueError:
        return pd.NA


def norm_name(s):
    if not isinstance(s, str):
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", s)
                if not unicodedata.combining(c))
    return s.lower().strip()


def canonicalize_player_ids(df):
    """One player, one player_id.

    The file mixes THREE player-id spaces: legacy ids, NBA ids (203507 = Giannis)
    and ESPN ids (3032977 = the same Giannis). The rating engine keys on
    player_id, so a single player accumulated two separate rating entities: the
    real Giannis (882 games, 2024) and a phantom (11 games, 1506). Downstream
    lookups build dict(name -> rating), so last-write-wins could return the
    phantom, and Miami showed a NEGATIVE roster delta after adding him.

    Collapse every id space onto the id that carries the most rows for that name.
    Names are already the join key used by the ratings file and the roster
    mapping, so this does not introduce a new source of ambiguity.
    """
    key = df.player_name.map(norm_name)
    counts = df.assign(_k=key).groupby(["_k", "player_id"]).size()
    canonical = counts.groupby(level=0).idxmax().map(lambda t: t[1])
    multi = counts.groupby(level=0).size()
    n_multi = int((multi > 1).sum())
    remapped = df.player_id.values != key.map(canonical).values
    df["player_id"] = key.map(canonical).values
    print(f"canonicalized player ids: {n_multi:,} names had >1 id; "
          f"{int(remapped.sum()):,} rows remapped")
    return df


def main():
    dry = "--dry-run" in sys.argv
    df = pd.read_csv(BOX, low_memory=False)
    print(f"read {len(df):,} rows, {df.game_id.nunique():,} games")

    is_new = df.team_id > 1_000_000
    n_new = int(is_new.sum())
    print(f"rows in the new dialect: {n_new:,} ({df.loc[is_new, 'game_id'].nunique():,} games)")

    before = pd.to_numeric(df.minutes, errors="coerce").notna().sum()

    if n_new:
        # minutes: MM:SS -> float (applied to every row; old rows are already numeric)
        df["minutes"] = df.minutes.map(parse_minutes)

        # team_id / team_name: NBA ids -> our DB ids + full names
        mapped = df.loc[is_new, "team_id"].map(NBA_TO_DB)
        known = mapped.notna()
        df.loc[is_new & known, "team_name"] = [v[1] for v in mapped[known]]
        df.loc[is_new & known, "team_id"] = [v[0] for v in mapped[known]]
        print(f"remapped {int(known.sum()):,} rows to DB team ids "
              f"({int((~known).sum()):,} non-NBA rows left alone)")

        after = pd.to_numeric(df.minutes, errors="coerce").notna().sum()
        print(f"rows with numeric minutes: {before:,} -> {after:,}  (+{after-before:,})")

    # Always run: id spaces mix even when the dialect is already canonical.
    df = canonicalize_player_ids(df)

    if dry:
        print("\n--dry-run: nothing written.")
        return

    if not BACKUP.exists():
        shutil.copy2(BOX, BACKUP)
        print(f"backup written to {BACKUP}")
    df.to_csv(BOX, index=False)
    print(f"wrote {BOX}")


if __name__ == "__main__":
    main()

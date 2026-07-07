"""Roster Phase A: refresh player_team_mapping.csv from the NBA API, then apply
manual overrides for announced-but-not-yet-official moves.

The old mapping went stale (Kuminga on Atlanta, Naz Reid/AD on wrong teams),
which is why the roster-accuracy rule bans naming a player's team without
verification. This rebuilds it nightly from the source of truth
(commonteamroster) and layers a human-maintained overrides file on top for the
free-agency window, where signings lag their agreements.

Run on the VPS (nba_api installed there). Safe by design: if the API returns
too few players (blocked / mid-transaction), it ABORTS and keeps the existing
mapping rather than overwriting it with garbage.

    python scripts/refresh_roster_mapping.py
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

MAPPING_FILE = Path("data/exports/player_team_mapping.csv")
OVERRIDES_FILE = Path("data/manual/roster_overrides.csv")
MIN_PLAYERS = 350   # 30 teams x ~14; below this we assume a bad pull and abort

# NBA API team id (1610612XXX) -> our internal DB id (1-30) + full name
NBA_TEAMS = {
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


def log(m):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}")


def season_str(start):
    return f"{start}-{str(start + 1)[-2:]}"


def current_season_start():
    """League year flips July 1: from July 2026 the current season is 2026-27."""
    n = datetime.now()
    return n.year if n.month >= 7 else n.year - 1


def _fetch_season(commonteamroster, season):
    log(f"Fetching {season} rosters for {len(NBA_TEAMS)} teams...")
    rows, failed = [], 0
    for nba_id, (db_id, name) in NBA_TEAMS.items():
        try:
            df = commonteamroster.CommonTeamRoster(
                team_id=nba_id, season=season, timeout=30).get_data_frames()[0]
            for _, p in df.iterrows():
                rows.append({
                    "player_id": p["PLAYER_ID"], "player_name": p["PLAYER"],
                    "team_id": db_id, "team_name": name,
                    "position": p.get("POSITION", ""),
                })
            time.sleep(0.6)
        except Exception as e:
            failed += 1
            log(f"  WARN team {name}: {e}")
            time.sleep(1.0)
    log(f"  {season}: fetched {len(rows)} players ({failed} teams failed)")
    return rows


def fetch_rosters():
    """Prefer the current league-year rosters; if the API hasn't populated them
    yet (early offseason), fall back to the prior season so we still get a full,
    if slightly stale, set that the overrides layer then corrects."""
    from nba_api.stats.endpoints import commonteamroster
    start = current_season_start()
    for s in (season_str(start), season_str(start - 1)):
        rows = _fetch_season(commonteamroster, s)
        if len(rows) >= MIN_PLAYERS:
            log(f"Using {s} rosters ({len(rows)} players)")
            return pd.DataFrame(rows)
        log(f"  {s} too sparse ({len(rows)}); trying older season")
    return pd.DataFrame(rows)


def apply_overrides(df):
    if not OVERRIDES_FILE.exists():
        return df
    ov = pd.read_csv(OVERRIDES_FILE)
    df["_k"] = df["player_name"].str.lower().str.strip()
    applied = 0
    for _, o in ov.iterrows():
        key = str(o["player_name"]).lower().strip()
        mask = df["_k"] == key
        if mask.any():
            df.loc[mask, "team_name"] = o["team_name"]
            if pd.notna(o.get("team_id")):
                df.loc[mask, "team_id"] = int(o["team_id"])
        else:
            df = pd.concat([df, pd.DataFrame([{
                "player_id": "", "player_name": o["player_name"],
                "team_id": int(o["team_id"]) if pd.notna(o.get("team_id")) else "",
                "team_name": o["team_name"], "position": "", "_k": key,
            }])], ignore_index=True)
        applied += 1
    df = df.drop(columns="_k")
    log(f"Applied {applied} manual overrides")
    return df


def main():
    df = fetch_rosters()
    if len(df) < MIN_PLAYERS:
        log(f"ABORT: only {len(df)} players (< {MIN_PLAYERS}). Keeping existing "
            f"mapping to avoid overwriting with a bad pull.")
        sys.exit(1)
    df = apply_overrides(df)
    df = df.drop_duplicates(subset=["player_name"], keep="last")
    df.to_csv(MAPPING_FILE, index=False)
    log(f"Wrote {len(df)} player-team rows to {MAPPING_FILE}")


if __name__ == "__main__":
    main()

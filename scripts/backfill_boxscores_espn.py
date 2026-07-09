"""Backfill missing player box scores via a (date + team pair) -> ESPN event id crosswalk.

Why a crosswalk is needed. `nba_box_scraper.py` fetches ESPN's summary endpoint
with `event=<game_id>`, so it only works when our game_id IS an ESPN event id.
For 2025-26 our games file stores NBA ids (`22500058`, playoffs `42500223`), so
every request 404s: the earlier "backfill" completed, added zero games, and wrote
749 ids to failed_game_ids.txt. A game_id set-difference cannot fix this because
the two files do not share an id space.

What this does instead:
  1. Find completed games that have no box-score rows.
  2. For each distinct DATE, pull ESPN's scoreboard once and index its events by
     (home team name, away team name). ESPN's displayName matches our team names
     exactly for all 30 franchises (verified).
  3. Fetch each box score by its ESPN event id, then RE-STAMP every row with OUR
     game_id, so player_elo_engine can join it to the games file.
  4. Append to player_boxscores_all.csv (never overwrites existing games).

Afterwards run: normalize_boxscores.py -> calculate_bpm.py -> player_elo_engine.py

    python scripts/backfill_boxscores_espn.py --since 2025-10-01 [--dry-run] [--limit N]
"""

import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nba_box_scraper import NBABoxScraper

GAMES = "data/raw/nba_games_all.csv"
BOX = "data/raw/player_boxscores_all.csv"
SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"


# Our games file and ESPN disagree on exactly one franchise.
ALIASES = {
    "Los Angeles Clippers": "LA Clippers",
    "LA Clippers": "LA Clippers",
}


def canon(name):
    return ALIASES.get(name, name)


def scoreboard_for(date_int, session, retries=3):
    """For one YYYYMMDD date, return (by_teams, by_score) indexes of ESPN events.

    by_teams : {(canon home, canon away): event_id}
    by_score : {(home_score, away_score): [event_id, ...]}  -- fallback only, and
               only trusted when the score pair is unique on that date.
    """
    for attempt in range(retries):
        try:
            r = session.get(SCOREBOARD, params={"dates": str(date_int)}, timeout=25)
            if r.status_code != 200:
                time.sleep(2 ** attempt)
                continue
            by_teams, by_score = {}, defaultdict(list)
            for e in r.json().get("events", []):
                comp = e["competitions"][0]
                home = away = hs = as_ = None
                for t in comp["competitors"]:
                    if t["homeAway"] == "home":
                        home, hs = t["team"]["displayName"], t.get("score")
                    else:
                        away, as_ = t["team"]["displayName"], t.get("score")
                if home and away:
                    by_teams[(canon(home), canon(away))] = e["id"]
                    try:
                        by_score[(int(hs), int(as_))].append(e["id"])
                    except (TypeError, ValueError):
                        pass
            return by_teams, by_score
        except requests.RequestException:
            time.sleep(2 ** attempt)
    return {}, {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None,
                    help="only backfill games on/after this date "
                         "(default: Oct 1 of the current league year)")
    ap.add_argument("--dry-run", action="store_true", help="resolve the crosswalk, scrape nothing")
    ap.add_argument("--limit", type=int, default=0, help="cap games scraped (smoke test)")
    ap.add_argument("--rate-limit", type=float, default=0.4)
    args = ap.parse_args()

    if args.since is None:
        from datetime import datetime
        now = datetime.now()
        args.since = f"{now.year if now.month >= 10 else now.year - 1}-10-01"
    since = int(args.since.replace("-", ""))
    games = pd.read_csv(GAMES)
    played = games[(games.home_score > 0) | (games.away_score > 0)]
    have = set(pd.read_csv(BOX, usecols=["game_id"], low_memory=False).game_id.unique())

    missing = played[(~played.game_id.isin(have)) & (played.date >= since)].sort_values("date")
    print(f"completed games missing box scores on/after {args.since}: {len(missing)}")
    if missing.empty:
        print("nothing to do.")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    # ---- build the crosswalk, one scoreboard call per date ----
    by_date = defaultdict(list)
    for _, g in missing.iterrows():
        by_date[int(g.date)].append(g)

    resolved, unresolved = [], []
    by_score_hits = 0
    print(f"resolving {len(by_date)} dates against the ESPN scoreboard...")
    for i, (date_int, rows) in enumerate(sorted(by_date.items()), 1):
        by_teams, by_score = scoreboard_for(date_int, session)
        for g in rows:
            eid = by_teams.get((canon(g.home_team_name), canon(g.away_team_name)))
            if not eid:
                # fallback: unique score pair on this date is unambiguous
                cands = by_score.get((int(g.home_score), int(g.away_score)), [])
                if len(cands) == 1:
                    eid = cands[0]
                    by_score_hits += 1
            (resolved if eid else unresolved).append((g.game_id, eid, date_int))
        if i % 20 == 0:
            print(f"  {i}/{len(by_date)} dates  resolved={len(resolved)} unresolved={len(unresolved)}")
        time.sleep(0.15)
    if by_score_hits:
        print(f"  ({by_score_hits} resolved via unique score-pair fallback)")

    print(f"\ncrosswalk: {len(resolved)} resolved, {len(unresolved)} unresolved "
          f"({len(resolved)/max(1,len(resolved)+len(unresolved))*100:.1f}%)")
    if unresolved[:3]:
        print("  sample unresolved:", unresolved[:3])
    if args.dry_run:
        print("\n--dry-run: nothing scraped.")
        return
    if not resolved:
        print("nothing resolved; aborting rather than writing an empty backfill.")
        sys.exit(1)

    if args.limit:
        resolved = resolved[: args.limit]
        print(f"--limit: scraping only {len(resolved)} games")

    # ---- fetch by ESPN id, re-stamp with OUR game_id ----
    scraper = NBABoxScraper(rate_limit_delay=args.rate_limit, retry_attempts=3, workers=1)
    rows, failed = [], []
    for i, (our_id, espn_id, date_int) in enumerate(resolved, 1):
        players = scraper.fetch_boxscore(espn_id)
        if not players:
            failed.append((our_id, espn_id))
            continue
        for p in players:
            p["game_id"] = our_id          # key to OUR games file, not ESPN's
            rows.append(p)
        if i % 25 == 0:
            print(f"  scraped {i}/{len(resolved)}  rows={len(rows)}  failed={len(failed)}")
        time.sleep(args.rate_limit)

    print(f"\nscraped {len(resolved)-len(failed)} games, {len(rows):,} player rows, {len(failed)} failed")
    if not rows:
        print("no rows; nothing written.")
        sys.exit(1)

    new = pd.DataFrame(rows)
    old = pd.read_csv(BOX, low_memory=False)
    new = new.reindex(columns=old.columns)          # align schema, drop extras
    combined = pd.concat([old, new], ignore_index=True)
    combined = combined.drop_duplicates(subset=["game_id", "player_id"], keep="first")
    combined.to_csv(BOX, index=False)
    print(f"wrote {BOX}: {len(old):,} -> {len(combined):,} rows, "
          f"{old.game_id.nunique():,} -> {combined.game_id.nunique():,} games")
    print("\nnext: normalize_boxscores.py -> calculate_bpm.py -> player_elo_engine.py")


if __name__ == "__main__":
    main()

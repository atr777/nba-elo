"""Are the sources we depend on still answering? Run before opening night, and
whenever ingestion looks quiet.

WHY THIS EXISTS. The NBA CDN schedule endpoint started returning 403 on 2026-07-09.
It was noticed only because someone happened to look, it sat broken for three weeks,
and it was the fallback for the pipeline that produces the entire product. In the
offseason nothing breaks visibly: no games means no gap means no alarm. The first
night it would have mattered was opening night.

A dead dependency should not need a human to remember to check it.

    python scripts/check_data_sources.py          # exit 1 if a REQUIRED source is down
    python scripts/check_data_sources.py --quiet  # only print problems

Exit code is 0 when every required source answers, 1 otherwise, so this can gate a
pipeline or a pre-season checklist.
"""

import argparse
import sys
from datetime import date, timedelta

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; SecondBounce/1.0)"}
# A date with a full slate, used for the checks that need real content back. Kept in
# the past on purpose: "yesterday" is empty all summer and would report a false down.
KNOWN_SLATE = "20260410"


def check_nba_api_games():
    """PRIMARY ingestion. If this is down and stays down, nothing else matters."""
    from nba_api.stats.endpoints import leaguegamefinder

    df = leaguegamefinder.LeagueGameFinder(
        season_nullable="2025-26", league_id_nullable="00", timeout=45
    ).get_data_frames()[0]
    return len(df) > 0, f"{len(df)} rows, latest {df.GAME_DATE.max()}"


def check_nba_api_scoreboard():
    from nba_api.stats.endpoints import scoreboardv2

    d = scoreboardv2.ScoreboardV2(game_date="2026-04-10", timeout=45).get_data_frames()[0]
    return len(d) > 0, f"{len(d)} games"


def check_espn_scoreboard():
    """FALLBACK ingestion, and independent of the NBA. Both legs being NBA-owned is
    what made the 2026-07 outage take out the whole chain at once."""
    r = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
        params={"dates": KNOWN_SLATE}, headers=UA, timeout=30)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    n = len(r.json().get("events") or [])
    return n > 0, f"{n} events on {KNOWN_SLATE}"


def check_espn_boxscore():
    """Used by backfill_boxscores_espn.py, which owns player box-score coverage."""
    r = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary",
        params={"event": "401812736"}, headers=UA, timeout=30)
    return r.status_code == 200, f"HTTP {r.status_code}"


def check_nba_cdn_schedule():
    """DEAD as of 2026-07-09, kept as a probe rather than deleted. If it ever comes
    back that is worth knowing, and a green line here is a reminder that a second
    NBA-owned source is not a real second source."""
    r = requests.get(
        "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
        headers=UA, timeout=25)
    return r.status_code == 200, f"HTTP {r.status_code} (403 expected since 2026-07-09)"


def check_nba_cdn_headshots():
    """Same host, different path, and this one still works. Worth separating: the
    block is path-scoped, not a whole-CDN ban, and the site's player cards use it."""
    r = requests.get("https://cdn.nba.com/headshots/nba/latest/1040x760/2544.png",
                     headers=UA, timeout=25)
    return r.status_code == 200, f"HTTP {r.status_code}"


# required=True means a failure exits non-zero. The CDN schedule probe is not
# required: it is known dead and we no longer depend on it.
CHECKS = [
    ("nba_api games (PRIMARY ingest)", check_nba_api_games, True),
    ("nba_api scoreboard", check_nba_api_scoreboard, True),
    ("ESPN scoreboard (FALLBACK ingest)", check_espn_scoreboard, True),
    ("ESPN boxscore summary", check_espn_boxscore, True),
    ("NBA CDN headshots (player cards)", check_nba_cdn_headshots, False),
    ("NBA CDN schedule (retired)", check_nba_cdn_schedule, False),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true", help="only print problems")
    a = ap.parse_args()

    failures = []
    for label, fn, required in CHECKS:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {str(e)[:70]}"
        tag = "ok  " if ok else ("DOWN" if required else "down")
        if not ok and required:
            failures.append(label)
        if not a.quiet or not ok:
            req = "" if required else "  (not required)"
            print(f"  [{tag}] {label:36s} {detail}{req}")

    if failures:
        print(f"\n{len(failures)} REQUIRED source(s) down: {', '.join(failures)}")
        print("Ingestion is at risk. Both legs must not be NBA-owned; if the ESPN "
              "line is the one that broke, find a third source before the season.")
        sys.exit(1)
    if not a.quiet:
        print("\nAll required sources answering.")


if __name__ == "__main__":
    main()

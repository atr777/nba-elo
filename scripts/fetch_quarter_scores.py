"""
fetch_quarter_scores.py
-----------------------
Fetches quarter-level line scores for NBA games using BoxScoreSummaryV3
and writes them to data/raw/nba_quarter_scores.csv.

IMPORTANT NOTE ON GAME IDs
--------------------------
nba_games_all.csv stores game_ids that are a mix of sources:
  - Pre-2020 games: NBA API-style IDs (e.g. 21031001 -> '0021031001', prefix '002')
  - 2020+ games: ESPN-style IDs (e.g. 401266805, prefix '040')

BoxScoreSummaryV3 only accepts real NBA API game IDs (prefix '002' for regular
season, '004' for playoffs). We therefore use leaguegamefinder to resolve the
correct NBA API game ID for each season/date range, then fetch quarter scores
using those IDs. The output CSV stores the NBA API game_id alongside the
original ESPN-style game_id from nba_games_all.csv so the analyst can join on
date + teams if needed.

Output CSV schema:
    nba_game_id, home_q1, home_q2, home_q3, home_q4, home_ot,
    away_q1, away_q2, away_q3, away_q4, away_ot,
    game_date, home_team_abbr, away_team_abbr

home_ot / away_ot = total_score - (q1+q2+q3+q4) for each team.
For regulation games these will be 0.

BoxScoreSummaryV3 line_score columns (confirmed 2026-03-25):
    gameId, teamId, teamCity, teamName, teamTricode, teamSlug,
    teamWins, teamLosses, period1Score, period2Score, period3Score,
    period4Score, score

No per-OT columns exist in V3 line_score; home_ot/away_ot are derived as
    score - (period1Score + period2Score + period3Score + period4Score)

Usage:
    # Default: 2020-21 through 2024-25 regular season, incremental
    python scripts/fetch_quarter_scores.py

    # Test with first N games only (always fetches oldest games first)
    python scripts/fetch_quarter_scores.py --sample 20

    # All seasons back to 2000-01
    python scripts/fetch_quarter_scores.py --all

    # Include playoffs
    python scripts/fetch_quarter_scores.py --include-playoffs

    # Specific season (e.g. 2022-23)
    python scripts/fetch_quarter_scores.py --season 2022-23

Rate limit: 0.6s between requests (NBA API ban threshold is ~30 req/min).
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths — all absolute so this script can be called from any cwd
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
OUTPUT_CSV = RAW_DIR / "nba_quarter_scores.csv"
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

RATE_LIMIT_DELAY = 1.5  # seconds between API calls

# Seasons to fetch by default (2020-21 through current)
DEFAULT_SEASONS = [
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
]

ALL_SEASONS = [
    "2000-01", "2001-02", "2002-03", "2003-04", "2004-05",
    "2005-06", "2006-07", "2007-08", "2008-09", "2009-10",
    "2010-11", "2011-12", "2012-13", "2013-14", "2014-15",
    "2015-16", "2016-17", "2017-18", "2018-19", "2019-20",
    "2020-21", "2021-22", "2022-23", "2023-24", "2024-25",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step 1: Resolve NBA API game IDs via leaguegamefinder
# ---------------------------------------------------------------------------

def fetch_nba_api_game_ids(seasons: list[str], include_playoffs: bool = False) -> pd.DataFrame:
    """Use leaguegamefinder to get all NBA API game IDs for the given seasons.

    Returns a DataFrame with columns:
        nba_game_id (str, 10-digit zero-padded),
        game_date (str YYYY-MM-DD),
        home_team_abbr (str),
        away_team_abbr (str),
        season (str)

    Sorted ascending by game_date so --sample N always grabs oldest games.
    """
    from nba_api.stats.endpoints import leaguegamefinder

    season_types = ["Regular Season"]
    if include_playoffs:
        season_types.append("Playoffs")

    all_rows: list[dict] = []

    for season in seasons:
        for stype in season_types:
            log.info("Fetching game list: season=%s  type=%s", season, stype)
            try:
                gf = leaguegamefinder.LeagueGameFinder(
                    season_nullable=season,
                    league_id_nullable="00",
                    season_type_nullable=stype,
                )
                df = gf.get_data_frames()[0]
                time.sleep(RATE_LIMIT_DELAY)
            except Exception as exc:
                log.warning("leaguegamefinder failed for %s %s: %s", season, stype, exc)
                time.sleep(2.0)
                continue

            if df.empty:
                log.info("  No games returned for %s %s", season, stype)
                continue

            log.info("  Got %d team-game rows for %s %s", len(df), season, stype)

            # leaguegamefinder returns one row per team per game.
            # We need home vs away. MATCHUP format: "ATL vs. BOS" (home) or "ATL @ BOS" (away).
            # Group by GAME_ID and resolve home/away.
            df["nba_game_id"] = df["GAME_ID"].astype(str).str.zfill(10)
            df["is_home"] = ~df["MATCHUP"].str.contains("@")
            df["game_date"] = pd.to_datetime(df["GAME_DATE"]).dt.strftime("%Y-%m-%d")

            # Extract abbreviation from MATCHUP: "ATL vs. BOS" -> "ATL"
            df["team_abbr"] = df["MATCHUP"].str.split(r"\s+(?:vs\.|@)\s+").str[0].str.strip()

            for gid, grp in df.groupby("nba_game_id"):
                home_rows = grp[grp["is_home"]]
                away_rows = grp[~grp["is_home"]]

                if home_rows.empty or away_rows.empty:
                    # Some playoff/play-in games may only have one row; skip
                    continue

                home_abbr = home_rows.iloc[0]["team_abbr"]
                away_abbr = away_rows.iloc[0]["team_abbr"]
                game_date = grp.iloc[0]["game_date"]

                all_rows.append({
                    "nba_game_id": gid,
                    "game_date": game_date,
                    "home_team_abbr": home_abbr,
                    "away_team_abbr": away_abbr,
                    "season": season,
                })

    result = pd.DataFrame(all_rows).drop_duplicates(subset=["nba_game_id"])

    # Sort ascending by date so --sample N always grabs the oldest games first.
    # This keeps the sample in pre-2025 territory where V3 has complete data.
    if not result.empty:
        result = result.sort_values("game_date", ascending=True).reset_index(drop=True)

    log.info("Total unique NBA API game IDs resolved: %d", len(result))
    return result


# ---------------------------------------------------------------------------
# Step 2: Fetch quarter scores for a single NBA API game ID
# ---------------------------------------------------------------------------

def fetch_line_score(nba_game_id: str) -> dict | None:
    """Call BoxScoreSummaryV3 and parse the line_score dataset.

    Returns a dict with keys matching the output schema, or None on failure.
    Only returns a dict when ALL eight quarter values (home/away Q1-Q4) are
    non-null integers > 0.  Games that return empty data are skipped entirely
    so no blank rows are written to the output CSV.

    V3 line_score columns (confirmed 2026-03-25):
        gameId, teamId, teamCity, teamName, teamTricode, teamSlug,
        teamWins, teamLosses, period1Score, period2Score, period3Score,
        period4Score, score

    OT is derived as: score - (period1Score + period2Score + period3Score + period4Score)
    """
    from nba_api.stats.endpoints import boxscoresummaryv3

    try:
        b = boxscoresummaryv3.BoxScoreSummaryV3(game_id=nba_game_id)
        ls = b.line_score.get_data_frame()
    except Exception as exc:
        log.warning("game %s  fetch failed: %s", nba_game_id, exc)
        return None

    if ls is None or ls.empty:
        log.warning("game %s  empty line_score returned", nba_game_id)
        return None

    if len(ls) < 2:
        log.warning("game %s  only %d team rows in line_score", nba_game_id, len(ls))
        return None

    # V3 does not have a GAME_SEQUENCE column.  Row 0 is the visiting team and
    # row 1 is the home team based on NBA API convention for V3, but leaguegamefinder
    # already resolved home/away for us.  Use game_summary to look up team tricodes
    # against the home_team_abbr we already know — but since we pass that info in
    # from the game_index, we rely on the row order here: row 0 = away, row 1 = home.
    # Confirmed via manual spot-check on game 0022401001 (MIN home vs NOP away).
    away_row = ls.iloc[0]
    home_row = ls.iloc[1]

    def q(row, period: int):
        """Return the integer score for the given period, or None if missing/zero-fill."""
        col = f"period{period}Score"
        v = row.get(col, None)
        if v is None or not pd.notna(v):
            return None
        return int(v)

    home_q1 = q(home_row, 1)
    home_q2 = q(home_row, 2)
    home_q3 = q(home_row, 3)
    home_q4 = q(home_row, 4)
    away_q1 = q(away_row, 1)
    away_q2 = q(away_row, 2)
    away_q3 = q(away_row, 3)
    away_q4 = q(away_row, 4)

    # Data integrity gate: skip games where any quarter value is missing or zero.
    # A real NBA quarter cannot be 0 points; that indicates incomplete data from the API.
    quarter_vals = [home_q1, home_q2, home_q3, home_q4, away_q1, away_q2, away_q3, away_q4]
    if any(v is None or v <= 0 for v in quarter_vals):
        log.warning(
            "game %s  incomplete quarter data — skipping (quarters: H %s/%s/%s/%s  A %s/%s/%s/%s)",
            nba_game_id, home_q1, home_q2, home_q3, home_q4,
            away_q1, away_q2, away_q3, away_q4,
        )
        return None

    # OT = total score minus regulation quarters.  V3 has no per-OT columns.
    home_total = row_int(home_row, "score")
    away_total = row_int(away_row, "score")
    home_ot = max(0, home_total - (home_q1 + home_q2 + home_q3 + home_q4)) if home_total else 0
    away_ot = max(0, away_total - (away_q1 + away_q2 + away_q3 + away_q4)) if away_total else 0

    # Pull game_date and team abbreviations from the line score itself.
    # V3 uses 'teamTricode' instead of 'TEAM_ABBREVIATION'.
    # game_date is not in V3 line_score; it will be filled in from the game_index
    # by the caller, so we store an empty string here as a placeholder.
    home_abbr = str(home_row.get("teamTricode", ""))
    away_abbr = str(away_row.get("teamTricode", ""))

    return {
        "nba_game_id": nba_game_id,
        "home_q1": home_q1,
        "home_q2": home_q2,
        "home_q3": home_q3,
        "home_q4": home_q4,
        "home_ot": home_ot,
        "away_q1": away_q1,
        "away_q2": away_q2,
        "away_q3": away_q3,
        "away_q4": away_q4,
        "away_ot": away_ot,
        "game_date": "",       # filled in from game_index below
        "home_team_abbr": home_abbr,
        "away_team_abbr": away_abbr,
    }


def row_int(row, col: str) -> int:
    v = row.get(col, 0)
    return int(v) if pd.notna(v) else 0


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

OUTPUT_COLUMNS = [
    "nba_game_id",
    "home_q1", "home_q2", "home_q3", "home_q4", "home_ot",
    "away_q1", "away_q2", "away_q3", "away_q4", "away_ot",
    "game_date", "home_team_abbr", "away_team_abbr",
]


def append_to_csv(rows: list[dict], path: Path) -> None:
    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    write_header = not path.exists()
    df.to_csv(path, mode="a", header=write_header, index=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch NBA quarter-level scores")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        metavar="N",
        help="Only fetch the first N games (oldest first, for testing)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all seasons back to 2000-01 (default: 2020-21 onwards)",
    )
    parser.add_argument(
        "--include-playoffs",
        action="store_true",
        help="Include playoff games (default: regular season only)",
    )
    parser.add_argument(
        "--season",
        type=str,
        default=None,
        metavar="YYYY-YY",
        help="Fetch a single season only (e.g. 2022-23)",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # 1. Determine which seasons to cover
    # ------------------------------------------------------------------
    if args.season:
        seasons = [args.season]
    elif args.all:
        seasons = ALL_SEASONS
    else:
        seasons = DEFAULT_SEASONS

    log.info("Target seasons: %s", seasons)

    # ------------------------------------------------------------------
    # 2. Resolve NBA API game IDs via leaguegamefinder (sorted oldest-first)
    # ------------------------------------------------------------------
    game_index = fetch_nba_api_game_ids(seasons, include_playoffs=args.include_playoffs)

    if game_index.empty:
        log.error("No game IDs resolved — aborting.")
        return

    # ------------------------------------------------------------------
    # 3. Incremental — skip game_ids already in the output file
    # ------------------------------------------------------------------
    already_fetched: set[str] = set()
    if OUTPUT_CSV.exists():
        existing = pd.read_csv(OUTPUT_CSV, dtype={"nba_game_id": str})
        already_fetched = set(existing["nba_game_id"].str.zfill(10))
        log.info(
            "Existing %s has %d rows — will skip those game_ids",
            OUTPUT_CSV.name,
            len(existing),
        )

    pending_df = game_index[~game_index["nba_game_id"].isin(already_fetched)]

    log.info(
        "Total games in index: %d  |  Already fetched: %d  |  To fetch: %d",
        len(game_index),
        len(already_fetched),
        len(pending_df),
    )

    if pending_df.empty:
        log.info("Nothing to fetch — output is already up to date.")
        return

    # Apply --sample limit AFTER incremental filter.
    # game_index is already sorted oldest-first, so head(N) = oldest N games.
    if args.sample:
        pending_df = pending_df.head(args.sample)
        log.info("--sample %d: limited to %d games", args.sample, len(pending_df))

    # Build a lookup: nba_game_id -> game_date/home_team_abbr/away_team_abbr
    # so the fetch loop can fill in fields that V3 line_score no longer carries.
    index_lookup = pending_df.set_index("nba_game_id")[
        ["game_date", "home_team_abbr", "away_team_abbr"]
    ].to_dict("index")

    pending_ids = pending_df["nba_game_id"].tolist()

    # ------------------------------------------------------------------
    # 4. Fetch loop
    # ------------------------------------------------------------------
    new_rows: list[dict] = []
    errors: list[str] = []
    skipped: list[str] = []

    for i, gid in enumerate(pending_ids, start=1):
        if i % 50 == 0 or i == 1:
            log.info("Progress: %d / %d  (errors so far: %d)", i, len(pending_ids), len(errors))

        row = fetch_line_score(gid)

        if row is not None:
            # Fill in game_date and team abbreviations from the index if the
            # line_score returned empty strings (V3 dropped GAME_DATE_EST).
            meta = index_lookup.get(gid, {})
            if not row["game_date"] and meta.get("game_date"):
                row["game_date"] = meta["game_date"]
            if not row["home_team_abbr"] and meta.get("home_team_abbr"):
                row["home_team_abbr"] = meta["home_team_abbr"]
            if not row["away_team_abbr"] and meta.get("away_team_abbr"):
                row["away_team_abbr"] = meta["away_team_abbr"]
            new_rows.append(row)
        else:
            # fetch_line_score already logged the reason.
            # Distinguish hard errors (exception) from soft skips (incomplete data)
            # by checking whether a warning was already issued; for simplicity we
            # bucket both into errors — no blank row is ever written.
            errors.append(gid)

        # Checkpoint every 100 rows so a crash doesn't lose progress
        if new_rows and len(new_rows) % 100 == 0:
            append_to_csv(new_rows, OUTPUT_CSV)
            log.info("Checkpoint: flushed %d rows to %s", len(new_rows), OUTPUT_CSV.name)
            new_rows = []

        time.sleep(RATE_LIMIT_DELAY)

    # Final flush
    if new_rows:
        append_to_csv(new_rows, OUTPUT_CSV)

    # ------------------------------------------------------------------
    # 5. Summary
    # ------------------------------------------------------------------
    success_count = len(pending_ids) - len(errors)
    log.info("Done. Fetched %d new rows. Skipped/errored on %d game_ids.", success_count, len(errors))
    if errors:
        log.warning("Failed/skipped game_ids (first 20): %s", errors[:20])
        if len(errors) > 20:
            log.warning("  ... and %d more", len(errors) - 20)

    if OUTPUT_CSV.exists():
        final = pd.read_csv(OUTPUT_CSV, dtype={"nba_game_id": str})
        log.info("Output file now has %d rows — %s", len(final), OUTPUT_CSV)


if __name__ == "__main__":
    main()

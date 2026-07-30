"""Second-source game ingestion, for when the NBA API comes up empty.

REPLACES scripts/fetch_missing_from_cdn.py, which is dead. That script read
cdn.nba.com/static/json/staticData/scheduleLeagueV2.json, and as of 2026-07-09 that
path answers 403 from Akamai's edge. Re-checked 2026-07-30 from Aaron's PC AND from
the VPS, with browser User-Agent, Referer and Origin: every combination 403s, and so
do the sibling paths (scheduleLeagueV2_1.json, liveData/scoreboard). It is not a
User-Agent problem and not geo-blocking. The path is simply closed to us.

WHY ESPN, beyond it working. The old arrangement was not really a fallback: primary
was stats.nba.com and fallback was cdn.nba.com, both NBA-owned, so one decision on
their side removed both legs at once. Which is exactly what happened. ESPN is an
independent source, and this repo already depends on it for box-score backfill and
injuries, so it is a proven path rather than a new one.

    python scripts/fetch_missing_games_fallback.py --start 2026-10-21 --end 2026-10-28
    python scripts/fetch_missing_games_fallback.py --start ... --end ... --dry-run

DEDUP IS ON (date, home_team_id, away_team_id), NOT on game_id. This matters more
than anything else here. ESPN does not know NBA game ids, so rows written by this
script carry an id of the form `20261021_1_2`. If dedup keyed on that, the same game
could later arrive from the NBA API as `0022600001` and be appended a SECOND time,
double-counting a result in the ELO history. Two such duplicate pairs already exist
in the file from 2002 and 2003 under legacy ids, which is what that failure looks
like. The triple is the real identity of a game in this project: it is what
track_predictions_pregame keys on and what the leakage audit rebuilds.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import requests

from src.scrapers.nba_api_data_fetcher import NBA_API_TO_DB_ID

GAMES_PATH = 'data/raw/nba_games_all.csv'
SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'

# ESPN agrees with the NBA on 29 of 30 display names. The exception is the Clippers,
# the same single quirk backfill_boxscores_espn.py documents.
ESPN_NAME_ALIASES = {'LA Clippers': 'Los Angeles Clippers'}

# ESPN status -> whether the game is final. Anything else (scheduled, in progress,
# postponed, canceled) is not a result and must not be written.
FINAL_STATES = {'STATUS_FINAL'}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start', required=True, help='Start date YYYY-MM-DD')
    p.add_argument('--end', required=True, help='End date YYYY-MM-DD (inclusive)')
    p.add_argument('--dry-run', action='store_true', help='Report without writing')
    return p.parse_args()


def team_lookup():
    """{full team name: our 1-30 id}, DERIVED rather than hand-typed.

    Built by joining nba_api's static team table to NBA_API_TO_DB_ID, the map that
    already governs this translation. Typing a fourth name-to-id table by hand is how
    this project ended up with several disagreeing id spaces.
    """
    from nba_api.stats.static import teams as nba_teams
    by_nba_id = {t['id']: t['full_name'] for t in nba_teams.get_teams()}
    out = {}
    for nba_id, db_id in NBA_API_TO_DB_ID.items():
        name = by_nba_id.get(nba_id)
        if name:
            out[name] = db_id
    if len(out) != 30:
        sys.exit(f"team lookup built {len(out)} entries, expected 30; refusing to run")
    return out


def fetch_day(date_obj, session):
    """Completed games for one date, as rows in nba_games_all.csv's shape."""
    r = session.get(SCOREBOARD, params={'dates': date_obj.strftime('%Y%m%d')},
                    timeout=30)
    r.raise_for_status()
    return r.json().get('events', []) or []


def rows_for(events, names, date_obj):
    date_int = int(date_obj.strftime('%Y%m%d'))
    rows, skipped = [], []
    for ev in events:
        comps = (ev.get('competitions') or [{}])[0]
        state = ((comps.get('status') or {}).get('type') or {}).get('name', '')
        if state not in FINAL_STATES:
            skipped.append(f"{ev.get('name', '?')}: {state}")
            continue

        side = {}
        for c in comps.get('competitors') or []:
            raw = (c.get('team') or {}).get('displayName', '')
            side[c.get('homeAway')] = (ESPN_NAME_ALIASES.get(raw, raw), c.get('score'))
        if 'home' not in side or 'away' not in side:
            skipped.append(f"{ev.get('name', '?')}: missing a side")
            continue

        (home_name, home_score), (away_name, away_score) = side['home'], side['away']
        home_id, away_id = names.get(home_name), names.get(away_name)
        if home_id is None or away_id is None:
            # Loud, not skipped quietly: an unmapped name means an alias broke, and
            # silently dropping games is how a gap goes unnoticed for months.
            sys.exit(f"unmapped team name from ESPN: "
                     f"{home_name if home_id is None else away_name!r}. "
                     f"Add it to ESPN_NAME_ALIASES.")
        try:
            hs, as_ = int(home_score), int(away_score)
        except (TypeError, ValueError):
            skipped.append(f"{home_name} v {away_name}: unreadable score")
            continue
        if hs == 0 and as_ == 0:
            skipped.append(f"{home_name} v {away_name}: final but 0-0")
            continue

        # Playoff games matter for the record and are typed differently upstream.
        season_type = 'playoffs' if (ev.get('season') or {}).get('slug') == 'post-season' \
            else 'regular'

        rows.append({
            'game_id': f"{date_int}_{home_id}_{away_id}",
            'date': date_int,
            'home_team_id': home_id,
            'home_team_name': home_name,
            'away_team_id': away_id,
            'away_team_name': away_name,
            'home_score': hs,
            'away_score': as_,
            'winner_team_id': float(home_id if hs > as_ else away_id),
            'season_type': season_type,
        })
    return rows, skipped


def main():
    args = parse_args()
    start = datetime.strptime(args.start, '%Y-%m-%d').date()
    end = datetime.strptime(args.end, '%Y-%m-%d').date()
    if end < start:
        sys.exit("--end is before --start")

    print("=" * 70)
    print(f" Fallback ingestion via ESPN: {start} -> {end}")
    print("=" * 70)

    names = team_lookup()
    existing = pd.read_csv(GAMES_PATH)
    print(f"[CSV] {len(existing)} existing games, latest {existing['date'].max()}")

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; SecondBounce/1.0)'})

    fetched, skipped_all = [], []
    day = start
    while day <= end:
        try:
            events = fetch_day(day, session)
        except Exception as e:
            print(f"[WARN] {day}: {type(e).__name__}: {str(e)[:90]}")
            day += timedelta(days=1)
            continue
        rows, skipped = rows_for(events, names, day)
        fetched.extend(rows)
        skipped_all.extend(skipped)
        if rows:
            print(f"[ESPN] {day}: {len(rows)} final game(s)")
        day += timedelta(days=1)

    if skipped_all:
        print(f"[SKIP] {len(skipped_all)} non-final or unusable entries "
              f"(first few: {skipped_all[:3]})")

    if not fetched:
        print("[OK] Nothing final in that range. Nothing to add.")
        return

    new = pd.DataFrame(fetched)

    # THE DEDUP THAT MATTERS. See the module docstring: game_id is not a reliable
    # identity across sources, the (date, home, away) triple is.
    def triple(df):
        return (df['date'].astype(str) + '_' + df['home_team_id'].astype(str)
                + '_' + df['away_team_id'].astype(str))

    have = set(triple(existing))
    new['_t'] = triple(new)
    dupes_within = int(new['_t'].duplicated().sum())
    new = new[~new['_t'].duplicated()]
    truly_new = new[~new['_t'].isin(have)].drop(columns='_t')
    already = len(new) - len(truly_new)

    print(f"[DEDUP] {len(fetched)} fetched, {dupes_within} duplicated inside the pull, "
          f"{already} already present, {len(truly_new)} new")

    if truly_new.empty:
        print("[OK] Everything fetched is already in the database.")
        return

    if args.dry_run:
        print("\n[DRY RUN] would add:")
        print(truly_new[['date', 'home_team_name', 'away_team_name',
                         'home_score', 'away_score', 'season_type']].to_string(index=False))
        return

    updated = pd.concat([existing, truly_new], ignore_index=True).sort_values('date')
    updated = updated.reset_index(drop=True)

    # Post-write invariants. This file feeds every rating we publish, so an append
    # that breaks it should stop here rather than surface as a strange rating later.
    #
    # The duplicate check is RELATIVE, not an absolute count. This repo already
    # carries two duplicate triples from 2002 and 2003 under legacy ids, and the
    # local and VPS copies of this file differ (the local one is gitignored and goes
    # stale), so any hardcoded number would fire spuriously on one machine or the
    # other. What must hold is that this append introduces none.
    dupes_before = len(existing) - triple(existing).nunique()
    dupes_after = len(updated) - triple(updated).nunique()
    assert len(updated) == len(existing) + len(truly_new), "row count mismatch"
    assert dupes_after == dupes_before, (
        f"this append introduced {dupes_after - dupes_before} duplicate "
        f"(date,home,away) triple(s). Refusing to write: a double-counted result "
        f"corrupts every rating after it."
    )
    updated.to_csv(GAMES_PATH, index=False)

    print(f"\n[OK] Added {len(truly_new)}. Total {len(updated)}, "
          f"range {updated['date'].min()} -> {updated['date'].max()}")


if __name__ == '__main__':
    main()

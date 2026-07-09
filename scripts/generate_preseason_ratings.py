"""Roster-delta preseason team ratings for the upcoming season.

This is the capability the offseason has been missing. Until now every public
number we could publish was "where a team FINISHED," because the team ELO carried
into a new season is just last season's rating reverted toward the mean. It has
no idea Giannis changed conferences.

    preseason(T) = 0.75 * elo_end(last season) + 0.25 * 1500 + K * delta(T)

delta(T) prices the roster CHANGE in player-rating points:

    delta(T) = talent(who is on T now) - talent(who played for T last season)

Both sides are valued with the SAME prices (player ratings as of the end of last
season) so the delta measures personnel change, not rating drift. Deltas are
centered to zero-sum across the 30 teams, because ELO is a relative scale: the
league cannot get better by everyone signing someone.

Design notes, each of which was a bug first:
  * Weights are MINUTES PER GAME, not total minutes. The current season's box
    score history is partial, so total minutes are not comparable across seasons;
    mpg is scale free.
  * A player is a ROOKIE if we have no rating for him, NOT if he has no minutes
    last season. Otherwise a rated star who missed the sampled games (Jalen
    Williams, Tyler Herro) gets priced as a 1450 rookie and craters his team.
  * Talent is measured over the top-10 rotation by expected minutes, so deep
    bench and two-way names cannot drag the mean.

Unlike the backtest (which proxied the opening roster from early box scores) this
uses the REAL current roster from data/exports/player_team_mapping.csv, refreshed
nightly from the NBA API plus data/manual/roster_overrides.csv. Every input is
known today, so there is no leakage.

K=0.8 was selected out-of-sample (expanding window, 13 held-out seasons; it won
every window). Evidence: docs/research/2026-07-09-roster-delta.md

    python scripts/generate_preseason_ratings.py
"""

import sys
import logging
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

import pandas as pd

from src.features.roster_delta import compute_upcoming_delta

K = 0.8
ROOKIE_RATING = 1450.0     # a rookie is a below-average NBA player, on average
ROOKIE_MPG = 12.0          # and plays bench minutes
MAX_MPG = 38.0
ROTATION = 10              # talent is the quality of your rotation
BASE = 1500.0
REVERSION = 0.75
OUT = Path("data/exports/preseason_ratings.csv")


def norm(s):
    if not isinstance(s, str):
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", s)
                if not unicodedata.combining(c))
    return s.lower().strip()


def main():
    hist = pd.read_csv("data/exports/team_elo_history_phase_1_6.csv")
    hist = hist[hist.team_id <= 30]
    last = hist.sort_values("date").groupby("team_id").last().reset_index()
    end_elo = dict(zip(last.team_id, last.rating_after))
    team_name = dict(zip(last.team_id, last.team_name))

    ph = pd.read_csv("data/exports/player_elo_history_bpm.csv",
                     usecols=["date", "player_name", "team_id", "minutes"])
    ph = ph[ph.team_id <= 30].copy()
    y = ph.date.astype(str).str[:4].astype(int)
    m = ph.date.astype(str).str[4:6].astype(int)
    ph["season"] = y.where(m >= 10, y - 1)
    ph["minutes"] = pd.to_numeric(ph.minutes, errors="coerce").fillna(0.0)
    ph["key"] = ph.player_name.map(norm)
    ls = int(ph.season.max())          # last completed/sampled season

    def mpg_table(df, by):
        g = df.groupby(by).minutes.agg(["sum", "size"])
        return (g["sum"] / g["size"]).clip(upper=MAX_MPG)

    cur = ph[ph.season == ls]
    prev = ph[ph.season == ls - 1]
    mpg_cur = mpg_table(cur, "key").to_dict()          # league-wide, last season
    mpg_prev = mpg_table(prev, "key").to_dict()        # fallback if unsampled
    mpg_team = mpg_table(cur, ["team_id", "key"])      # for the old roster

    pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
    pr["key"] = pr.player_name.map(norm)
    rating = dict(zip(pr.key, pr.rating))

    pm = pd.read_csv("data/exports/player_team_mapping.csv")
    pm = pm[pm.team_id.between(1, 30)].copy()
    pm["key"] = pm.player_name.map(norm)

    # ONE definition of the delta, shared with the engine (src/features/roster_delta.py)
    upcoming, deltas = compute_upcoming_delta(".")
    rookie_counts = {
        t: sum(1 for k in pm[pm.team_id == t].key if k not in rating)
        for t in sorted(end_elo)
    }

    rows = []
    for team_id in sorted(end_elo):
        if team_id not in deltas:
            continue
        rows.append({
            "team_id": team_id, "team_name": team_name[team_id],
            "finished": round(end_elo[team_id], 1),
            "reverted": round(REVERSION * end_elo[team_id] + (1 - REVERSION) * BASE, 1),
            "delta": round(deltas[team_id], 1),
            "rookies": rookie_counts[team_id],
        })

    df = pd.DataFrame(rows)
    df["preseason"] = (df.reverted + K * df.delta).round(1)
    df["elo_change"] = (df.preseason - df.finished).round(1)
    df = df.sort_values("preseason", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", df.index + 1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    print(f"PRESEASON RATINGS for {ls+1}-{str(ls+2)[-2:]}  (K={K}, "
          f"zero-sum delta mean={df.delta.mean():.1f})\n")
    print(df[["rank", "team_name", "finished", "delta", "preseason",
              "elo_change", "rookies"]].to_string(index=False))
    print(f"\nWrote {OUT}")

    mv = df.sort_values("delta")
    print("\nBiggest roster UPGRADES (delta, player-rating pts):")
    for _, r in mv.tail(4)[::-1].iterrows():
        print(f"  {r.team_name:24s} {r.delta:+7.1f}   {r.finished:.0f} -> {r.preseason:.0f}")
    print("Biggest roster DOWNGRADES:")
    for _, r in mv.head(4).iterrows():
        print(f"  {r.team_name:24s} {r.delta:+7.1f}   {r.finished:.0f} -> {r.preseason:.0f}")


if __name__ == "__main__":
    main()

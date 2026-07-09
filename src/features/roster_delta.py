"""Roster-delta preseason ratings.

The team ELO carried into a new season is just last season's rating reverted
toward the mean. It has no idea Giannis changed conferences. This module prices
the roster CHANGE in player-rating points:

    delta(T, S) = talent(roster of T in season S)
                - talent(roster of T in season S-1)

`talent()` is the minutes-per-game-weighted mean player rating of the top-10
rotation, on the 1500-centered player-rating scale. The engine converts it to
team-ELO points with a scalar K. K = 0 exactly reproduces the old behaviour.

Why it is leak-free: BOTH sides are valued with the same vintage, namely each
player's rating and role AS OF THE END OF SEASON S-1. Nothing about how season S
actually unfolded enters the valuation. The only season-S information used is
roster MEMBERSHIP, which is public at preseason -- that is the whole point of a
preseason rating.

Definitions (each of these was a bug first; see docs/research/2026-07-09-roster-delta.md):

  * A ROOKIE is a player with NO KNOWN RATING before season S. It is NOT "a player
    with no minutes last season": a rated star who missed all of S-1 (a torn
    Achilles) must keep his rating, not get priced as a 1450 rookie.
  * As-of rating and role are the player's MOST RECENT known values from any
    season before S, not strictly season S-1, for the same reason.
  * Weights are MINUTES PER GAME, not total minutes. Box-score coverage of the
    current season is partial, so totals are not comparable across seasons.
  * talent() is measured over the top-10 rotation, so deep bench and two-way
    names cannot drag the mean.
  * Deltas are CENTERED to zero-sum across the 30 teams. ELO is a relative scale;
    the league cannot improve by everyone signing someone. Uncentered deltas
    carry a negative mean and would deflate every team, every season.

Data source: `data/exports/player_elo_history_bpm.csv` (DB team_ids, dates,
minutes, per-game `rating_after`). `rating_after` is RAW, so the deployed
position OFFSETS (additive, ELO points) are re-applied here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

HISTORY = "data/exports/player_elo_history_bpm.csv"

# Approximate the opening-night roster by who appears in a team's first N games.
# N=1 is the conservative choice: it peeks least into the season being predicted.
OPENING_GAMES = 1

ROOKIE_RATING = 1450.0     # a rookie is a below-average NBA player, on average
ROOKIE_MPG = 12.0          # and plays bench minutes
MAX_MPG = 38.0
ROTATION = 10              # talent is the quality of your rotation

REAL_TEAMS = set(range(1, 31))   # exclude All-Star / exhibition team ids

PRIORS_FILE = "config/rookie_priors.json"
DRAFT_FILE = "data/raw/draft_history.csv"


def load_rookie_priors(root: Path | str = "."):
    """(rating_of_pick, mpg_of_pick, picks_by_name) or None if not fitted.

    A flat rookie prior misprices the two things that actually vary with draft
    position. Minutes vary enormously (a top-3 pick plays ~27 mpg, a late second
    ~9), while the end-of-rookie-season RATING barely moves and in fact runs
    backwards, because our player ELO moves in proportion to minutes played. So
    the prior mostly needs to get the role weight right.

    Curves are fitted on rookie seasons <= 2012 (scripts/fit_rookie_priors.py) so
    they cannot leak into the 2013-2025 validation window.
    """
    import json
    import math

    root = Path(root)
    pf, df = root / PRIORS_FILE, root / DRAFT_FILE
    if not pf.exists() or not df.exists():
        return None
    p = json.loads(pf.read_text())

    def rating_of(pick):
        return p["rating"]["intercept"] + p["rating"]["log_pick_coef"] * math.log(max(1, pick))

    def mpg_of(pick):
        v = p["mpg"]["intercept"] + p["mpg"]["log_pick_coef"] * math.log(max(1, pick))
        return min(MAX_MPG, max(3.0, v))

    d = pd.read_csv(df, usecols=["PLAYER_NAME", "OVERALL_PICK"])
    picks = {}
    for n, pk in zip(d.PLAYER_NAME, d.OVERALL_PICK):
        k = _norm(n)
        if k and k not in picks and pd.notna(pk):
            picks[k] = int(pk)
    return rating_of, mpg_of, picks, p["undrafted"]


def _position_offsets() -> Dict[str, float]:
    """Deployed player-rating definition: rim protectors docked, ADDITIVE ELO pts.

    The shot-creator boost was removed 2026-07-09 (unvalidated; it multiplied a
    1500-anchored scale and put Harden 3rd in the league). See player_elo_engine.
    """
    from src.engines.player_elo_engine import POSITION_OFFSETS
    return POSITION_OFFSETS


def load_history(root: Path | str = ".") -> pd.DataFrame:
    h = pd.read_csv(
        Path(root) / HISTORY,
        usecols=["game_id", "date", "player_id", "player_name", "team_id",
                 "minutes", "rating_after"],
    )
    h = h[h.team_id.isin(REAL_TEAMS)].copy()
    y = h.date.astype(str).str[:4].astype(int)
    m = h.date.astype(str).str[4:6].astype(int)
    h["season"] = y.where(m >= 10, y - 1)
    h["minutes"] = pd.to_numeric(h.minutes, errors="coerce").fillna(0.0)
    return h


def talent(pairs) -> float | None:
    """mpg-weighted mean rating over the top-ROTATION players by minutes."""
    pairs = sorted((p for p in pairs if p[1] > 0), key=lambda x: -x[1])[:ROTATION]
    den = sum(w for _, w in pairs)
    return sum(r * w for r, w in pairs) / den if den > 0 else None


def compute_deltas(root: Path | str = ".",
                   rookie_rating: float = ROOKIE_RATING,
                   rookie_mpg: float = ROOKIE_MPG,
                   center: bool = True,
                   opening_games: int = OPENING_GAMES,
                   draft_priors: bool = False,
                   ) -> Dict[Tuple[int, int], float]:
    """delta[(season, team_id)] in player-rating points. Positive = roster upgraded.

    draft_priors=True prices each rookie by his draft position instead of a flat
    (1450, 12 mpg). Validated separately; see docs/research.
    """
    priors = load_rookie_priors(root) if draft_priors else None
    h = load_history(root)
    id_to_key = dict(zip(h.player_id, h.player_name.map(_norm)))

    def rookie_prior(pid):
        """(rating, mpg) for a player with no rating history."""
        if not priors:
            return rookie_rating, rookie_mpg
        rating_of, mpg_of, picks, und = priors
        pick = picks.get(id_to_key.get(pid, ""))
        if pick is None:
            return und["rating"], und["mpg"]
        return rating_of(pick), mpg_of(pick)

    off = _position_offsets()
    h = h.sort_values("date")

    # end-of-season, position-adjusted rating per (season, player)
    last = h.groupby(["season", "player_id"]).tail(1)
    names = last.player_name.str.lower().str.strip()
    adj = last.rating_after.values + names.map(lambda n: off.get(n, 0.0)).values
    end_rating = dict(zip(zip(last.season, last.player_id), adj))

    # minutes per game, league-wide and per team
    g = h.groupby(["season", "player_id"]).minutes.agg(["sum", "size"])
    mpg = (g["sum"] / g["size"]).clip(upper=MAX_MPG).to_dict()
    gt = h.groupby(["season", "team_id", "player_id"]).minutes.agg(["sum", "size"])
    mpg_team = (gt["sum"] / gt["size"]).clip(upper=MAX_MPG).to_dict()

    full_roster: Dict[Tuple[int, int], set] = {}
    for (season, team, pid) in mpg_team:
        full_roster.setdefault((season, team), set()).add(pid)

    opening: Dict[Tuple[int, int], set] = {}
    for (season, team), grp in h.groupby(["season", "team_id"]):
        first = set(grp.drop_duplicates("game_id").sort_values("date").game_id.head(opening_games))
        opening[(season, team)] = set(grp[grp.game_id.isin(first)].player_id.unique())

    seasons = sorted(h.season.unique())
    deltas: Dict[Tuple[int, int], float] = {}

    # as-of state: most recent known rating / role STRICTLY BEFORE the season we price
    latest_rating: Dict[int, float] = {}
    latest_mpg: Dict[int, float] = {}

    for s in seasons:
        if latest_rating:                       # need history to price against
            for team in sorted(REAL_TEAMS):
                new_roster = opening.get((s, team))
                old_roster = full_roster.get((s - 1, team))
                if not new_roster or not old_roster:
                    continue

                new_pairs = []
                for p in new_roster:
                    r = latest_rating.get(p)
                    if r is None:               # never rated before => rookie
                        new_pairs.append(rookie_prior(p))
                    else:
                        new_pairs.append((r, latest_mpg.get(p) or rookie_mpg))

                old_pairs = [(latest_rating[p], mpg_team[(s - 1, team, p)])
                             for p in old_roster
                             if p in latest_rating and (s - 1, team, p) in mpg_team]

                t_new, t_old = talent(new_pairs), talent(old_pairs)
                if t_new is not None and t_old is not None:
                    deltas[(s, team)] = t_new - t_old

        # only now absorb season s, so season s+1 is priced with info through s
        for (ss, pid), r in end_rating.items():
            if ss == s:
                latest_rating[pid] = r
        for (ss, pid), v in mpg.items():
            if ss == s:
                latest_mpg[pid] = v

    if center:
        for s in seasons:
            keys = [k for k in deltas if k[0] == s]
            if keys:
                mean = sum(deltas[k] for k in keys) / len(keys)
                for k in keys:
                    deltas[k] -= mean

    return deltas


def compute_upcoming_delta(root: Path | str = ".",
                           rookie_rating: float = ROOKIE_RATING,
                           rookie_mpg: float = ROOKIE_MPG,
                           center: bool = True):
    """Delta for the season that has not started yet.

    The backtest has to guess the opening roster from early box scores. Here we
    do not guess: the roster comes from data/exports/player_team_mapping.csv,
    refreshed nightly from the NBA API plus data/manual/roster_overrides.csv. Every
    input is known today, so there is no leakage of any kind.

    Returns (upcoming_season, {team_id: delta}).
    """
    root = Path(root)
    h = load_history(root)
    ls = int(h.season.max())                 # last season we have box scores for
    upcoming = ls + 1

    g = h.groupby(["season", "player_id"]).minutes.agg(["sum", "size"])
    mpg = (g["sum"] / g["size"]).clip(upper=MAX_MPG)
    gt = h.groupby(["season", "team_id", "player_id"]).minutes.agg(["sum", "size"])
    mpg_team = (gt["sum"] / gt["size"]).clip(upper=MAX_MPG)

    # most recent known role for each player (last season, else the one before)
    mpg_cur = mpg.xs(ls, level="season").to_dict() if ls in mpg.index.get_level_values(0) else {}
    mpg_prev = mpg.xs(ls - 1, level="season").to_dict() if (ls - 1) in mpg.index.get_level_values(0) else {}

    name_by_id = dict(zip(h.player_id, h.player_name.map(_norm)))
    id_by_name = {v: k for k, v in name_by_id.items()}

    pr = pd.read_csv(root / "data/exports/player_ratings_bpm_adjusted.csv")
    rating = {_norm(n): r for n, r in zip(pr.player_name, pr.rating)}

    pm = pd.read_csv(root / "data/exports/player_team_mapping.csv")
    pm = pm[pm.team_id.between(1, 30)].copy()
    pm["key"] = pm.player_name.map(_norm)

    deltas = {}
    for team_id in sorted(REAL_TEAMS):
        new_pairs = []
        for k in pm[pm.team_id == team_id].key:
            r = rating.get(k)
            if r is None:                       # never rated => rookie
                new_pairs.append((rookie_rating, rookie_mpg))
                continue
            pid = id_by_name.get(k)
            w = (mpg_cur.get(pid) or mpg_prev.get(pid) or rookie_mpg) if pid else rookie_mpg
            new_pairs.append((r, w))

        try:
            old = mpg_team.xs((ls, team_id), level=("season", "team_id"))
        except KeyError:
            continue
        old_pairs = []
        for pid, w in old.items():
            r = rating.get(name_by_id.get(pid, ""))
            if r is not None:
                old_pairs.append((r, w))

        t_new, t_old = talent(new_pairs), talent(old_pairs)
        if t_new is not None and t_old is not None:
            deltas[team_id] = t_new - t_old

    if center and deltas:
        mean = sum(deltas.values()) / len(deltas)
        deltas = {t: v - mean for t, v in deltas.items()}
    return upcoming, deltas


def _norm(s):
    import unicodedata
    if not isinstance(s, str):
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s.lower().strip()


if __name__ == "__main__":
    import sys
    d = compute_deltas(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(f"computed {len(d)} (season, team) deltas")
    for s in sorted({k[0] for k in d})[-2:]:
        row = sorted(((v, t) for (ss, t), v in d.items() if ss == s), reverse=True)
        print(f"\nseason {s}: top/bottom 3 (player-rating pts)")
        for v, t in row[:3] + row[-3:]:
            print(f"   team {t:2d}  {v:+7.1f}")

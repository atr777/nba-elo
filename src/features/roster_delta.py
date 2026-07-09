"""Roster-delta preseason ratings.

The team ELO carried into a new season is just last season's rating reverted
toward the mean. It has no idea Giannis changed conferences. This module prices
the roster CHANGE in player-rating points so the engine can start a season from
"who is actually here" rather than "who was here last April."

Core idea, and the reason it is leak-free:

    delta(T, S) = talent(roster of T in season S)
                - talent(roster of T in season S-1)

BOTH sides are valued with the SAME vintage: player ratings as of the END of
season S-1, and minutes played during season S-1. Nothing from season S enters
the valuation. The only season-S information used is roster MEMBERSHIP, which is
public at preseason (that is the whole point of a preseason rating).

talent() is a minutes-weighted mean player rating, so it is on the 1500-centered
player-rating scale. The engine converts it to team-ELO points with a single
scalar K, swept and validated separately. K = 0 exactly reproduces the current
behaviour.

Rookies have no prior rating and no prior minutes, so they enter at a configurable
prior (rating and minutes). Their prior is what makes a "roster-delta" preseason
rating possible for a team that just drafted its franchise player.

Data source is `data/exports/player_elo_history_bpm.csv`, which already carries
DB team_ids, dates, minutes, and per-game `rating_after` (RAW: the position
multipliers are applied on export, so we re-apply them here to match the
deployed definition of a player rating).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

HISTORY = "data/exports/player_elo_history_bpm.csv"

# Approximate the opening-night roster by who appears in a team's first N games.
OPENING_GAMES = 10

# Rookie priors (a rookie is a player with no minutes in season S-1).
ROOKIE_RATING = 1450.0     # below the 1500 average; swept in validation
ROOKIE_MINUTES = 900.0     # ~ a rotation player's season, so they carry real weight

REAL_TEAMS = set(range(1, 31))   # exclude All-Star / exhibition team ids


def _position_multipliers() -> Dict[str, float]:
    """Deployed player-rating definition: rim protectors docked, creators boosted."""
    from src.engines.player_elo_engine import POSITION_MULTIPLIERS
    return POSITION_MULTIPLIERS


def load_history(root: Path | str = ".") -> pd.DataFrame:
    h = pd.read_csv(
        Path(root) / HISTORY,
        usecols=["game_id", "date", "player_id", "player_name", "team_id",
                 "minutes", "rating_after"],
    )
    h = h[h.team_id.isin(REAL_TEAMS)].copy()
    y = h.date.astype(str).str[:4].astype(int)
    m = h.date.astype(str).str[4:6].astype(int)
    h["season"] = y.where(m >= 10, y - 1)      # NBA season starts in October
    h["minutes"] = pd.to_numeric(h.minutes, errors="coerce").fillna(0.0)
    return h


def build_tables(h: pd.DataFrame, opening_games: int = OPENING_GAMES):
    """Returns (end_rating, team_minutes, player_minutes, opening_roster).

    end_rating[(season, player_id)]     -> position-adjusted rating at season end
    team_minutes[(season, team, pid)]   -> minutes that player logged FOR that team
    player_minutes[(season, pid)]       -> total minutes league-wide
    opening_roster[(season, team)]      -> set of player_ids in the team's first N games
    """
    mult = _position_multipliers()

    # ---- end-of-season rating per player (last game of that season) ----
    h = h.sort_values("date")
    last = h.groupby(["season", "player_id"]).tail(1)
    names = last.player_name.str.lower().str.strip()
    adj = last.rating_after.values * names.map(lambda n: mult.get(n, 1.0)).values
    end_rating = dict(zip(zip(last.season, last.player_id), adj))

    # ---- minutes ----
    tm = h.groupby(["season", "team_id", "player_id"]).minutes.sum()
    team_minutes = tm.to_dict()
    pm = h.groupby(["season", "player_id"]).minutes.sum()
    player_minutes = pm.to_dict()

    # full roster per (season, team), prebuilt so we never rescan team_minutes
    full_roster: Dict[Tuple[int, int], set] = {}
    for (season, team, pid), mins in team_minutes.items():
        if mins > 0:
            full_roster.setdefault((season, team), set()).add(pid)

    # ---- opening roster: players in the team's first OPENING_GAMES games ----
    opening: Dict[Tuple[int, int], set] = {}
    for (season, team), grp in h.groupby(["season", "team_id"]):
        order = grp.drop_duplicates("game_id").sort_values("date").game_id
        first = set(order.head(opening_games))
        opening[(season, team)] = set(grp[grp.game_id.isin(first)].player_id.unique())
    return end_rating, team_minutes, player_minutes, opening, full_roster


def _talent(players, weight_of, rating_of) -> float | None:
    """Minutes-weighted mean player rating. None when the roster carries no weight."""
    num = den = 0.0
    for p in players:
        w = weight_of(p)
        r = rating_of(p)
        if w <= 0 or r is None:
            continue
        num += w * r
        den += w
    return num / den if den > 0 else None


def compute_deltas(root: Path | str = ".",
                   rookie_rating: float = ROOKIE_RATING,
                   rookie_minutes: float = ROOKIE_MINUTES,
                   center: bool = True,
                   opening_games: int = OPENING_GAMES,
                   ) -> Dict[Tuple[int, int], float]:
    """delta[(season, team_id)] in player-rating points. Positive = roster upgraded.

    Uses ONLY season S-1 ratings and minutes to price both rosters, so the value
    of the change cannot be contaminated by how season S actually went.

    center=True subtracts each season's league mean, making the adjustment
    zero-sum. ELO is a relative scale: talent cannot be created league-wide by
    everyone signing someone. Without centering, the raw deltas carry a negative
    mean (rookies enter below 1500, opening rosters carry fringe players) and
    would silently deflate every team's rating each season.
    """
    h = load_history(root)
    end_rating, team_minutes, player_minutes, opening, full_roster = build_tables(h, opening_games)

    seasons = sorted(h.season.unique())
    season_set = set(seasons)
    deltas: Dict[Tuple[int, int], float] = {}

    for s in seasons[1:]:                      # need a prior season to price with
        prev = s - 1
        if prev not in season_set:
            continue
        for team in sorted(REAL_TEAMS):
            new_roster = opening.get((s, team))
            old_roster = full_roster.get((prev, team))
            if not new_roster or not old_roster:
                continue

            # a rookie (for season s) logged no minutes anywhere in season prev
            rookies = {p for p in new_roster
                       if player_minutes.get((prev, p), 0.0) <= 0}

            def rating_new(p, _r=rookies):
                if p in _r:
                    return rookie_rating
                return end_rating.get((prev, p))

            def weight_new(p, _r=rookies):
                if p in _r:
                    return rookie_minutes
                return player_minutes.get((prev, p), 0.0)

            t_new = _talent(new_roster, weight_new, rating_new)
            t_old = _talent(old_roster,
                            lambda p, _t=team: team_minutes.get((prev, _t, p), 0.0),
                            lambda p: end_rating.get((prev, p)))
            if t_new is None or t_old is None:
                continue
            deltas[(s, team)] = t_new - t_old

    if center:
        for s in seasons:
            keys = [k for k in deltas if k[0] == s]
            if not keys:
                continue
            mean = sum(deltas[k] for k in keys) / len(keys)
            for k in keys:
                deltas[k] -= mean

    return deltas


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    d = compute_deltas(root)
    print(f"computed {len(d)} (season, team) deltas")
    for s in sorted({k[0] for k in d})[-3:]:
        row = sorted(((v, t) for (ss, t), v in d.items() if ss == s), reverse=True)
        print(f"\nseason {s}: biggest upgrades / downgrades (player-rating pts)")
        for v, t in row[:3]:
            print(f"   team {t:2d}  {v:+7.1f}")
        for v, t in row[-3:]:
            print(f"   team {t:2d}  {v:+7.1f}")

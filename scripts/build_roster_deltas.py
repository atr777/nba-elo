"""Write data/exports/roster_deltas.csv, the file the engine reads at a season
boundary to nudge each team by K * (roster-talent change).

Two sources, one definition (src/features/roster_delta.py):
  * historical seasons, from box-score opening rosters (research + reproducibility)
  * the UPCOMING season, from the real NBA-API roster mapping (no leakage at all)

Regenerate whenever the roster mapping changes materially (trades, signings) or
after a box-score backfill. The engine only applies rows at or after
`roster_delta.start_season` in config/settings.yaml.

    python scripts/build_roster_deltas.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

import pandas as pd

from src.features.roster_delta import compute_deltas, compute_upcoming_delta

OUT = Path("data/exports/roster_deltas.csv")


def main():
    hist = compute_deltas(".")
    upcoming_season, upcoming = compute_upcoming_delta(".")

    names = pd.read_csv("data/raw/nba_games_all_vps.csv",
                        usecols=["home_team_id", "home_team_name"]).drop_duplicates()
    nm = dict(zip(names.home_team_id, names.home_team_name))

    rows = [{"season": s, "team_id": t, "team_name": nm.get(t, ""),
             "delta": round(v, 2), "source": "history"}
            for (s, t), v in sorted(hist.items())]
    rows += [{"season": upcoming_season, "team_id": t, "team_name": nm.get(t, ""),
              "delta": round(v, 2), "source": "roster_mapping"}
             for t, v in sorted(upcoming.items())]

    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df)} rows to {OUT}")
    print(f"  historical seasons: {df[df.source=='history'].season.nunique()}")
    print(f"  upcoming season   : {upcoming_season} "
          f"({(df.source=='roster_mapping').sum()} teams, from the live roster mapping)")

    up = df[df.season == upcoming_season].sort_values("delta")
    print(f"\n{upcoming_season}-{str(upcoming_season+1)[-2:]} biggest roster swings "
          f"(player-rating pts, zero-sum):")
    for _, r in up.tail(4)[::-1].iterrows():
        print(f"  UP   {r.team_name:24s} {r.delta:+7.1f}")
    for _, r in up.head(4).iterrows():
        print(f"  DOWN {r.team_name:24s} {r.delta:+7.1f}")


def load_roster_deltas(path=OUT):
    """{(season, team_id): delta}. Returns {} if the file is absent."""
    p = Path(path)
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    return {(int(s), int(t)): float(d)
            for s, t, d in zip(df.season, df.team_id, df.delta)}


if __name__ == "__main__":
    main()

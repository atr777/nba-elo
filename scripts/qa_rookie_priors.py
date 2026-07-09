"""Does pricing rookies by draft position beat the flat (1450, 12 mpg) prior?

Held to the same bar as everything else:
  * the curves were fitted on rookie seasons <= 2012 only, so the evaluation
    window (2013-2025) never informed them;
  * K is held at its validated 0.8 for BOTH arms, so the only thing that differs
    is the rookie prior;
  * every held-out season is scored out of sample, pooled, then compared PAIRED
    on the identical games (McNemar on accuracy flips, 10k paired bootstrap on
    the per-game squared-error difference).

If Brier does not improve out of sample, the prior does not ship.

    python scripts/qa_rookie_priors.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

import numpy as np
import pandas as pd
from scipy import stats

from src.engines.team_elo_engine import TeamELOEngine
from src.features.roster_delta import compute_deltas

K = 0.8
FIRST_SCORED = 2013          # first held-out season (curves fitted <= 2012)

games = pd.read_csv("data/raw/nba_games_all.csv")
games = games[(games.home_score > 0) | (games.away_score > 0)].sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.apply(lambda d: d.year if d.month >= 10 else d.year - 1)
RNG = np.random.default_rng(20260709)
N_BOOT = 10000


def run(deltas):
    e = TeamELOEngine(k_factor=20, home_advantage=60, use_mov=True,
                      use_enhanced_features=True, use_top_player_concentration=False,
                      player_ratings=pr, player_team_mapping=pm)
    e.reset_ratings()
    e.rest_tracker.b2b_penalty = 46
    e.rest_tracker.one_day_penalty = 0
    cur, rows = None, []
    for idx, g in games.iterrows():
        s = seasons.iloc[idx]
        if cur is not None and s != cur:
            e._apply_season_reversion(reversion_factor=0.75)
            for team, rating in list(e.current_ratings.items()):
                d = deltas.get((s, team))
                if d is not None:
                    e.current_ratings[team] = rating + K * d
        cur = s
        if s >= FIRST_SCORED:
            try:
                p = e.predict_game(g["home_team_id"], g["away_team_id"], game_date=g["date"])
                rows.append((s, g["game_id"], p["home_win_probability"],
                             1 if int(g["home_score"]) > int(g["away_score"]) else 0))
            except Exception:
                pass
        e.process_game(g.to_dict())
    return pd.DataFrame(rows, columns=["season", "game_id", "p", "y"]).set_index("game_id")


print("computing deltas (flat prior vs draft-position prior)...")
d_flat = compute_deltas(".", draft_priors=False)
d_draft = compute_deltas(".", draft_priors=True)
changed = sum(1 for k in d_flat if abs(d_flat[k] - d_draft.get(k, 0)) > 1e-9)
print(f"  {len(d_flat)} deltas, {changed} differ between the two priors\n")

A = run(d_flat)
B = run(d_draft)
j = A.join(B, lsuffix="_a", rsuffix="_b", how="inner")
assert (j.y_a == j.y_b).all()
y = j.y_a.values.astype(float)
pa, pb = j.p_a.values, j.p_b.values
ca = (pa >= 0.5) == (y == 1)
cb = (pb >= 0.5) == (y == 1)

a_only = int((ca & ~cb).sum())
b_only = int((~ca & cb).sum())
n_disc = a_only + b_only
p_mc = stats.binomtest(b_only, n_disc, 0.5).pvalue if n_disc else 1.0

se_a, se_b = (pa - y) ** 2, (pb - y) ** 2
d = se_a - se_b                       # > 0 means the draft prior is better
idx = RNG.integers(0, len(d), size=(N_BOOT, len(d)))
boot = d[idx].mean(axis=1)
lo, hi = np.percentile(boot, [2.5, 97.5])
p_boot = 2 * min((boot <= 0).mean(), (boot >= 0).mean())

print(f"=== OUT OF SAMPLE, seasons {FIRST_SCORED}-{int(seasons.max())} "
      f"({len(y)} paired games, K={K} for both) ===")
print(f"  accuracy   flat {ca.mean()*100:.2f}%  ->  draft {cb.mean()*100:.2f}%   "
      f"({cb.sum()-ca.sum():+d} games)")
print(f"  McNemar    draft-right={b_only}, flat-right={a_only}   p={p_mc:.4f}"
      f"   {'SIGNIFICANT' if p_mc < 0.05 else 'not significant'}")
print(f"  brier      {se_a.mean():.5f} -> {se_b.mean():.5f}   (diff {d.mean():+.6f})")
print(f"  boot 95%CI [{lo:+.6f}, {hi:+.6f}]  p={p_boot:.4f}"
      f"   {'SIGNIFICANT' if p_boot < 0.05 else 'not significant'}")

print("\nper-season held-out brier (flat -> draft):")
for s in sorted(j.season_a.unique()):
    sub = j[j.season_a == s]
    ba = ((sub.p_a - sub.y_a) ** 2).mean()
    bb = ((sub.p_b - sub.y_b) ** 2).mean()
    print(f"  {int(s)}-{int(s)+1}  {ba:.4f} -> {bb:.4f}  {'+' if bb < ba else '-'}")

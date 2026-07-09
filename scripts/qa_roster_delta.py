"""QA gate for roster-delta. Two things the sweep alone cannot tell us:

1. K was chosen by looking at 2024-25 and 2025-26, the same seasons we report on.
   That is selection on the test set. Here K is chosen on TRAINING seasons only
   (2012-2023) and then applied cold to the two eval seasons.

2. Is the eval-season gain real, or a handful of coin flips? Every K predicts the
   same games, so we compare PAIRED: McNemar exact on the correctness flips, and
   a 10k paired bootstrap on the per-game squared-error difference.

    python scripts/qa_roster_delta.py
"""

import sys
import logging
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

import numpy as np
import pandas as pd
from scipy import stats

from src.engines.team_elo_engine import TeamELOEngine
from src.features.roster_delta import compute_deltas

games = pd.read_csv("data/raw/nba_games_all_vps.csv")
games = games[(games.home_score.astype(int) > 0) | (games.away_score.astype(int) > 0)]
games = games.sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.apply(lambda d: d.year if d.month >= 10 else d.year - 1)

TRAIN = set(range(2012, 2024))     # 2012-13 .. 2023-24
EVAL = {2024, 2025}
DELTAS = compute_deltas(".")
RNG = np.random.default_rng(20260709)
N_BOOT = 10000


def run(K, keep):
    e = TeamELOEngine(k_factor=20, home_advantage=60, use_mov=True,
                      use_enhanced_features=True, use_top_player_concentration=False,
                      player_ratings=pr, player_team_mapping=pm)
    e.reset_ratings()
    e.rest_tracker.b2b_penalty = 46
    e.rest_tracker.one_day_penalty = 0
    cur = None
    rows = []
    for idx, g in games.iterrows():
        s = seasons.iloc[idx]
        if cur is not None and s != cur:
            e._apply_season_reversion(reversion_factor=0.75)
            if K != 0.0:
                for team, rating in list(e.current_ratings.items()):
                    d = DELTAS.get((s, team))
                    if d is not None:
                        e.current_ratings[team] = rating + K * d
        cur = s
        if s in keep:
            try:
                p = e.predict_game(g["home_team_id"], g["away_team_id"], game_date=g["date"])
                rows.append((g["game_id"], p["home_win_probability"],
                             1 if int(g["home_score"]) > int(g["away_score"]) else 0))
            except Exception:
                pass
        e.process_game(g.to_dict())
    d = pd.DataFrame(rows, columns=["game_id", "p", "y"]).set_index("game_id")
    return d


# ---------------- Phase 1: pick K on TRAINING seasons only ----------------
print("PHASE 1 - choose K on training seasons 2012-13..2023-24 (eval seasons untouched)\n")
GRID = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.80]
print(f"{'K':>5} {'train acc':>10} {'train brier':>12} {'n':>7}")
train_res = {}
for K in GRID:
    d = run(K, TRAIN)
    acc = ((d.p >= 0.5) == (d.y == 1)).mean()
    br = ((d.p - d.y) ** 2).mean()
    train_res[K] = (acc, br)
    print(f"{K:>5.2f} {acc*100:>9.2f}% {br:>12.4f} {len(d):>7d}")

K_acc = max(GRID, key=lambda k: train_res[k][0])
K_bri = min(GRID, key=lambda k: train_res[k][1])
print(f"\ntraining picks: best accuracy K={K_acc}   best brier K={K_bri}")
K_STAR = K_bri     # Brier is the finer-grained, lower-variance criterion
print(f"-> committing to K* = {K_STAR} (chosen WITHOUT seeing eval seasons)\n")

# ---------------- Phase 2: cold test on eval seasons, paired ----------------
print(f"PHASE 2 - apply K*={K_STAR} cold to 2024-25 and 2025-26, paired vs K=0\n")
b = run(0.0, EVAL)
c = run(K_STAR, EVAL)
j = b.join(c, lsuffix="_b", rsuffix="_c", how="inner")
assert (j.y_b == j.y_c).all()
y = j.y_b.values
pb, pc = j.p_b.values, j.p_c.values
cb = (pb >= 0.5) == (y == 1)
cc = (pc >= 0.5) == (y == 1)

b_only = int((cb & ~cc).sum())
c_only = int((~cb & cc).sum())
n_disc = b_only + c_only
p_mc = stats.binomtest(c_only, n_disc, 0.5).pvalue if n_disc else 1.0

se_b, se_c = (pb - y) ** 2, (pc - y) ** 2
d = se_b - se_c                       # >0 means roster-delta is better
obs = d.mean()
idx = RNG.integers(0, len(d), size=(N_BOOT, len(d)))
boot = d[idx].mean(axis=1)
lo, hi = np.percentile(boot, [2.5, 97.5])
p_boot = 2 * min((boot <= 0).mean(), (boot >= 0).mean())

print(f"paired games: {len(y)}")
print(f"  accuracy   {cb.mean()*100:.2f}%  ->  {cc.mean()*100:.2f}%   ({cc.sum()-cb.sum():+d} games)")
print(f"  McNemar    delta-only-right={c_only}, base-only-right={b_only}   p={p_mc:.4f}"
      f"   {'SIGNIFICANT' if p_mc < 0.05 else 'not significant'}")
print(f"  brier      {se_b.mean():.5f} -> {se_c.mean():.5f}   (diff {obs:+.6f})")
print(f"  boot 95%CI [{lo:+.6f}, {hi:+.6f}]  p={p_boot:.4f}"
      f"   {'SIGNIFICANT' if p_boot < 0.05 else 'not significant'}")

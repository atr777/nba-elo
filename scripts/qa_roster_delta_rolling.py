"""Rolling out-of-sample QA for roster-delta. The strongest test we can run.

Phase-1/Phase-2 with a single split gave only 2,679 held-out games, too few to
resolve a Brier change of ~0.0006. Here we do expanding-window selection:

    for each season S:
        pick K* by minimizing Brier on every season BEFORE S
        score season S using K*        <- truly out of sample

Pool every held-out season's predictions and compare, paired, against K=0 on the
exact same games. This yields ~13 seasons of honest out-of-sample games instead
of 2, and it never lets a season inform its own K.

Efficiency: one full walk-forward pass per K value gives predictions for ALL
seasons at once, so rolling selection is pure bookkeeping afterwards.

    python scripts/qa_roster_delta_rolling.py
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

games = pd.read_csv("data/raw/nba_games_all_vps.csv")
games = games[(games.home_score.astype(int) > 0) | (games.away_score.astype(int) > 0)]
games = games.sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.apply(lambda d: d.year if d.month >= 10 else d.year - 1)

FIRST_SCORED = 2005      # collect preds from here on
FIRST_EVAL = 2013        # need some training history before the first held-out season
GRID = [0.0, 0.4, 0.8, 1.0, 1.2, 1.6]
OPENING = 1   # conservative: minimal peek into the predicted season
DELTAS = compute_deltas(".", opening_games=OPENING)
RNG = np.random.default_rng(20260709)
N_BOOT = 10000


def run(K):
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
        if s >= FIRST_SCORED:
            try:
                p = e.predict_game(g["home_team_id"], g["away_team_id"], game_date=g["date"])
                rows.append((s, g["game_id"], p["home_win_probability"],
                             1 if int(g["home_score"]) > int(g["away_score"]) else 0))
            except Exception:
                pass
        e.process_game(g.to_dict())
    return pd.DataFrame(rows, columns=["season", "game_id", "p", "y"])


print(f"opening_games={OPENING} (conservative). one pass per K, {len(GRID)} values ...")
P = {}
for K in GRID:
    P[K] = run(K).set_index("game_id")
    print(f"  K={K:<4} done ({len(P[K])} scored games)")

allseasons = sorted(P[0.0].season.unique())
evals = [s for s in allseasons if s >= FIRST_EVAL]

chosen, held_b, held_c = {}, [], []
for S in evals:
    # choose K on everything strictly before S
    best, bestbr = 0.0, None
    for K in GRID:
        tr = P[K][P[K].season < S]
        if len(tr) == 0:
            continue
        br = ((tr.p - tr.y) ** 2).mean()
        if bestbr is None or br < bestbr:
            bestbr, best = br, K
    chosen[S] = best
    b = P[0.0][P[0.0].season == S]
    c = P[best][P[best].season == S]
    j = b.join(c, lsuffix="_b", rsuffix="_c", how="inner")
    held_b.append(j[["p_b", "y_b"]].rename(columns={"p_b": "p", "y_b": "y"}))
    held_c.append(j[["p_c", "y_c"]].rename(columns={"p_c": "p", "y_c": "y"}))

print("\nK chosen per held-out season (from prior seasons only):")
print("  " + "  ".join(f"{s}:{chosen[s]}" for s in evals))

B = pd.concat(held_b); C = pd.concat(held_c)
y = B.y.values.astype(float)
pb, pc = B.p.values, C.p.values
cb = (pb >= 0.5) == (y == 1)
cc = (pc >= 0.5) == (y == 1)

b_only = int((cb & ~cc).sum()); c_only = int((~cb & cc).sum())
n_disc = b_only + c_only
p_mc = stats.binomtest(c_only, n_disc, 0.5).pvalue if n_disc else 1.0

se_b, se_c = (pb - y) ** 2, (pc - y) ** 2
d = se_b - se_c
idx = RNG.integers(0, len(d), size=(N_BOOT, len(d)))
boot = d[idx].mean(axis=1)
lo, hi = np.percentile(boot, [2.5, 97.5])
p_boot = 2 * min((boot <= 0).mean(), (boot >= 0).mean())

print(f"\n=== POOLED OUT-OF-SAMPLE ({len(y)} games, seasons {evals[0]}-{evals[-1]}) ===")
print(f"  accuracy   {cb.mean()*100:.2f}%  ->  {cc.mean()*100:.2f}%   ({cc.sum()-cb.sum():+d} games)")
print(f"  McNemar    delta-right={c_only}, base-right={b_only}   p={p_mc:.4f}"
      f"   {'SIGNIFICANT' if p_mc < 0.05 else 'not significant'}")
print(f"  brier      {se_b.mean():.5f} -> {se_c.mean():.5f}   (diff {d.mean():+.6f})")
print(f"  boot 95%CI [{lo:+.6f}, {hi:+.6f}]  p={p_boot:.4f}"
      f"   {'SIGNIFICANT' if p_boot < 0.05 else 'not significant'}")

print("\nper-season held-out brier (base -> roster-delta):")
for S, bb, cc_ in zip(evals, held_b, held_c):
    sb = ((bb.p - bb.y) ** 2).mean(); sc = ((cc_.p - cc_.y) ** 2).mean()
    mark = "+" if sc < sb else "-"
    print(f"  {S}-{S+1}  K={chosen[S]:<4} {sb:.4f} -> {sc:.4f}  {mark}")


# ---- SOP gate: the two named seasons, before vs after, at each season's chosen K ----
print("\n=== SOP GATE: 2024-25 and 2025-26, accuracy AND brier ===")
for S in (2024, 2025):
    K = chosen[S]
    b = P[0.0][P[0.0].season == S]; c = P[K][P[K].season == S]
    j = b.join(c, lsuffix="_b", rsuffix="_c", how="inner")
    yy = j.y_b.values
    ab = ((j.p_b >= 0.5) == (yy == 1)).mean(); ac = ((j.p_c >= 0.5) == (yy == 1)).mean()
    bb = ((j.p_b - yy) ** 2).mean(); bc = ((j.p_c - yy) ** 2).mean()
    ok = (ac >= ab) and (bc <= bb)
    print(f"  {S}-{S+1} (K={K}, n={len(j)}): acc {ab*100:.2f}% -> {ac*100:.2f}%   "
          f"brier {bb:.4f} -> {bc:.4f}   {'PASS' if ok else 'FAIL'}")

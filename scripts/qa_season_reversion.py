"""Rolling out-of-sample QA for the season-reversion factor.

Origin: Aaron asked whether coaching effectiveness could be measured. The cheap
falsification (excess team-season residual sd = 0.0000 against binomial noise)
says no persistent coaching alpha exists. But the same diagnostic surfaced a real
defect: residuals are NEGATIVELY autocorrelated season to season (r = -0.106,
p = 0.0038, shuffled-label placebo at 0). Teams that beat their rating miss it the
next year, which is what you see when an ELO carries too much of last season
forward. The deployed reversion is 0.75 and has never been swept.

Protocol, identical to the roster-delta K validation so the two are comparable:
  * one walk-forward pass per candidate value;
  * for each held-out season, pick the factor that minimizes Brier on every
    season BEFORE it (never on the season being scored);
  * pool all held-out predictions and compare PAIRED against the deployed 0.75 on
    the identical games (McNemar exact on flips, 10k paired bootstrap on Brier).

Finally report the SOP gate on 2024-25 and 2025-26: accuracy AND Brier.

    python scripts/qa_season_reversion.py
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

DEPLOYED = 0.75
GRID = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.75]
FIRST_SCORED = 2005
FIRST_EVAL = 2013
RNG = np.random.default_rng(20260709)
N_BOOT = 10000

games = pd.read_csv("data/raw/nba_games_all.csv")
games = games[(games.home_score > 0) | (games.away_score > 0)].sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.dt.year.where(dates.dt.month >= 10, dates.dt.year - 1)


def run(rev):
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
            e._apply_season_reversion(reversion_factor=rev)
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


print(f"one walk-forward pass per reversion value ({len(GRID)} values)...")
P = {r: run(r) for r in GRID}
for r in GRID:
    print(f"  {r} done")

evals = [s for s in sorted(P[DEPLOYED].season.unique()) if s >= FIRST_EVAL]
chosen, A, B = {}, [], []
for S in evals:
    best, bb = DEPLOYED, None
    for r in GRID:
        tr = P[r][P[r].season < S]
        if len(tr) == 0:
            continue
        br = ((tr.p - tr.y) ** 2).mean()
        if bb is None or br < bb:
            bb, best = br, r
    chosen[S] = best
    a = P[DEPLOYED][P[DEPLOYED].season == S]
    b = P[best][P[best].season == S]
    j = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
    A.append(j[["p_a", "y_a"]].values)
    B.append(j[["p_b", "y_b"]].values)

print("\nreversion chosen per held-out season (from prior seasons only):")
print("  " + "  ".join(f"{s}:{chosen[s]}" for s in evals))

A = np.vstack(A); B = np.vstack(B)
y = A[:, 1]
pa, pb = A[:, 0], B[:, 0]
ca = (pa >= 0.5) == (y == 1)
cb = (pb >= 0.5) == (y == 1)
a_only = int((ca & ~cb).sum()); b_only = int((~ca & cb).sum())
n_disc = a_only + b_only
p_mc = stats.binomtest(b_only, n_disc, 0.5).pvalue if n_disc else 1.0

se_a, se_b = (pa - y) ** 2, (pb - y) ** 2
d = se_a - se_b
idx = RNG.integers(0, len(d), size=(N_BOOT, len(d)))
boot = d[idx].mean(axis=1)
lo, hi = np.percentile(boot, [2.5, 97.5])
p_boot = 2 * min((boot <= 0).mean(), (boot >= 0).mean())

print(f"\n=== POOLED OUT-OF-SAMPLE ({len(y)} games, {evals[0]}-{evals[-1]}) ===")
print(f"  accuracy   {DEPLOYED}: {ca.mean()*100:.2f}%  ->  swept: {cb.mean()*100:.2f}%   ({cb.sum()-ca.sum():+d} games)")
print(f"  McNemar    swept-right={b_only}, deployed-right={a_only}   p={p_mc:.4f}"
      f"   {'SIGNIFICANT' if p_mc < 0.05 else 'not significant'}")
print(f"  brier      {se_a.mean():.5f} -> {se_b.mean():.5f}   (diff {d.mean():+.6f})")
print(f"  boot 95%CI [{lo:+.6f}, {hi:+.6f}]  p={p_boot:.4f}"
      f"   {'SIGNIFICANT' if p_boot < 0.05 else 'not significant'}")

print("\n=== SOP GATE: 2024-25 and 2025-26, accuracy AND brier ===")
for S in (2024, 2025):
    if S not in chosen:
        continue
    r = chosen[S]
    a = P[DEPLOYED][P[DEPLOYED].season == S]
    b = P[r][P[r].season == S]
    j = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
    yy = j.y_a.values
    aa = ((j.p_a >= 0.5) == (yy == 1)).mean(); ab = ((j.p_b >= 0.5) == (yy == 1)).mean()
    ba = ((j.p_a - yy) ** 2).mean(); bb2 = ((j.p_b - yy) ** 2).mean()
    ok = (ab >= aa) and (bb2 <= ba)
    print(f"  {S}-{S+1} (rev={r}, n={len(j)}): acc {aa*100:.2f}% -> {ab*100:.2f}%   "
          f"brier {ba:.5f} -> {bb2:.5f}   {'PASS' if ok else 'FAIL'}")

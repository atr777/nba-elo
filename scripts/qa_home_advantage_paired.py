"""QA gate for the home_advantage sweep: is any candidate REALLY better than the
deployed HA=60, or is the sweep just reading noise?

The sweep's marginal accuracies differ by ~0.2pp on 2,679 games, which is well
inside the ~0.9pp standard error of a single accuracy estimate. But every config
predicts the SAME games, so a paired comparison is far more powerful than
comparing marginals:

  - accuracy   -> McNemar exact test on the games whose correctness FLIPS
  - brier      -> paired bootstrap CI on the per-game squared-error difference

Walk-forward contract is identical to validate_config_2seasons.py.

    python scripts/qa_home_advantage_paired.py
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

games = pd.read_csv("data/raw/nba_games_all_vps.csv")
games = games[
    (games.home_score.astype(int) > 0) | (games.away_score.astype(int) > 0)
].sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.apply(lambda d: d.year if d.month >= 10 else d.year - 1)
EVAL = {2024, 2025}

BASELINE = 60
CANDIDATES = [45, 50, 55]
RNG = np.random.default_rng(20260708)
N_BOOT = 10000


def run(home_advantage):
    e = TeamELOEngine(
        k_factor=20, home_advantage=home_advantage, use_mov=True,
        use_enhanced_features=True, use_top_player_concentration=False,
        player_ratings=pr, player_team_mapping=pm,
    )
    e.reset_ratings()
    e.rest_tracker.b2b_penalty = 46
    e.rest_tracker.one_day_penalty = 0
    cur = None
    keys, preds, acts = [], [], []
    for idx, g in games.iterrows():
        s = seasons.iloc[idx]
        if cur is not None and s != cur:
            e._apply_season_reversion(reversion_factor=0.75)
        cur = s
        if s in EVAL:
            try:
                p = e.predict_game(g["home_team_id"], g["away_team_id"],
                                   game_date=g["date"])
                keys.append(idx)
                preds.append(p["home_win_probability"])
                acts.append(1 if int(g["home_score"]) > int(g["away_score"]) else 0)
            except Exception:
                pass
        e.process_game(g.to_dict())
    return pd.DataFrame({"idx": keys, "p": preds, "y": acts}).set_index("idx")


print(f"Running baseline HA={BASELINE} and candidates {CANDIDATES} ...\n")
base = run(BASELINE)

for ha in CANDIDATES:
    cand = run(ha)
    # align on the exact same games
    j = base.join(cand, lsuffix="_b", rsuffix="_c", how="inner")
    assert (j.y_b == j.y_c).all(), "outcome mismatch after join"
    y = j.y_b.values
    pb, pc = j.p_b.values, j.p_c.values
    cb = (pb >= 0.5) == (y == 1)
    cc = (pc >= 0.5) == (y == 1)

    # McNemar: discordant pairs only
    b_only = int((cb & ~cc).sum())   # baseline right, candidate wrong
    c_only = int((~cb & cc).sum())   # candidate right, baseline wrong
    n_disc = b_only + c_only
    if n_disc > 0:
        # exact binomial two-sided
        p_mcnemar = stats.binomtest(c_only, n_disc, 0.5).pvalue
    else:
        p_mcnemar = 1.0

    # Paired bootstrap on Brier difference (baseline - candidate; >0 = candidate better)
    se_b = (pb - y) ** 2
    se_c = (pc - y) ** 2
    d = se_b - se_c
    obs = d.mean()
    idx = RNG.integers(0, len(d), size=(N_BOOT, len(d)))
    boot = d[idx].mean(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    p_boot = 2 * min((boot <= 0).mean(), (boot >= 0).mean())

    print(f"=== HA={ha} vs HA={BASELINE} (n={len(y)} paired games) ===")
    print(f"  accuracy   {cb.mean()*100:.2f}% -> {cc.mean()*100:.2f}%  "
          f"({cc.sum()-cb.sum():+d} games)")
    print(f"  McNemar    flips: candidate-only-right={c_only}, baseline-only-right={b_only}"
          f"  p={p_mcnemar:.3f}")
    print(f"  brier      {se_b.mean():.5f} -> {se_c.mean():.5f}  (diff {obs:+.6f})")
    print(f"  boot 95%CI [{lo:+.6f}, {hi:+.6f}]  p={p_boot:.3f}"
          f"   {'SIGNIFICANT' if p_boot < 0.05 else 'not significant'}")
    print(f"  home bias  {pb.mean()-y.mean():+.4f} -> {pc.mean()-y.mean():+.4f}")
    print()

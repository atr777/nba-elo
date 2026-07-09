"""SOP sweep: home_advantage, walk-forward on 2024-25 AND 2025-26.

Motivated by the 2026-07-08 diagnostic: over 657 tracked games the model's mean
predicted home probability was 0.5945 against an actual 0.5830 home-win rate,
suggesting home_advantage=60 is too generous. This sweeps the parameter and
reports accuracy AND Brier per season (the SOP gate), plus the home-bias number
that motivated the change.

Every game is predicted BEFORE its result is processed (same walk-forward
contract as validate_config_2seasons.py). Everything except home_advantage is
held at the deployed config: k=20, MOV on, enhanced features on, b2b penalty 46,
one-day penalty 0, top-player concentration OFF.

With concentration OFF the player ratings/mapping never enter the backtest, so
the (now 2026-27) roster mapping cannot contaminate historical seasons.

    python scripts/sweep_home_advantage.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

import pandas as pd

from src.engines.team_elo_engine import TeamELOEngine

games = pd.read_csv("data/raw/nba_games_all_vps.csv")
games = games[
    (games.home_score.astype(int) > 0) | (games.away_score.astype(int) > 0)
].sort_values("date").reset_index(drop=True)
pr = pd.read_csv("data/exports/player_ratings_bpm_adjusted.csv")
pm = pd.read_csv("data/exports/player_team_mapping.csv")
dates = pd.to_datetime(games.date.astype(str), format="%Y%m%d")
seasons = dates.apply(lambda d: d.year if d.month >= 10 else d.year - 1)
EVAL_SEASONS = {2024, 2025}

SWEEP = [20, 30, 40, 45, 50, 55, 60, 65, 70, 80]


def run(home_advantage):
    """Walk-forward both eval seasons at one home_advantage. Returns per-season
    [hits, n, brier_sum, pred_home_prob_sum, actual_home_wins]."""
    e = TeamELOEngine(
        k_factor=20, home_advantage=home_advantage, use_mov=True,
        use_enhanced_features=True, use_top_player_concentration=False,
        player_ratings=pr, player_team_mapping=pm,
    )
    e.reset_ratings()
    e.rest_tracker.b2b_penalty = 46
    e.rest_tracker.one_day_penalty = 0
    cur = None
    stats = {s: [0, 0, 0.0, 0.0, 0] for s in EVAL_SEASONS}
    for idx, g in games.iterrows():
        s = seasons.iloc[idx]
        if cur is not None and s != cur:
            e._apply_season_reversion(reversion_factor=0.75)
        cur = s
        if s in EVAL_SEASONS:
            try:
                p = e.predict_game(g["home_team_id"], g["away_team_id"],
                                   game_date=g["date"])
                ph = p["home_win_probability"]
                act = 1 if int(g["home_score"]) > int(g["away_score"]) else 0
                st = stats[s]
                st[0] += (ph >= 0.5) == bool(act)
                st[1] += 1
                st[2] += (ph - act) ** 2
                st[3] += ph
                st[4] += act
            except Exception:
                pass
        e.process_game(g.to_dict())
    return stats


print(f"{'HA':>4} | {'2024-25 acc':>11} {'brier':>7} | {'2025-26 acc':>11} {'brier':>7} "
      f"| {'pooled acc':>10} {'brier':>7} | {'bias (pred-act)':>15}")
print("-" * 96)

rows = []
for ha in SWEEP:
    st = run(ha)
    h = sum(st[s][0] for s in EVAL_SEASONS)
    n = sum(st[s][1] for s in EVAL_SEASONS)
    b = sum(st[s][2] for s in EVAL_SEASONS)
    predsum = sum(st[s][3] for s in EVAL_SEASONS)
    actsum = sum(st[s][4] for s in EVAL_SEASONS)
    a24, n24, b24 = st[2024][0] / st[2024][1], st[2024][1], st[2024][2] / st[2024][1]
    a25, n25, b25 = st[2025][0] / st[2025][1], st[2025][1], st[2025][2] / st[2025][1]
    bias = predsum / n - actsum / n
    rows.append((ha, a24, b24, a25, b25, h / n, b / n, bias))
    print(f"{ha:>4} | {a24*100:>10.2f}% {b24:>7.4f} | {a25*100:>10.2f}% {b25:>7.4f} "
          f"| {h/n*100:>9.2f}% {b/n:>7.4f} | {bias:>+15.4f}")

print()
best_acc = max(rows, key=lambda r: r[5])
best_bri = min(rows, key=lambda r: r[6])
least_bias = min(rows, key=lambda r: abs(r[7]))
print(f"best pooled accuracy : HA={best_acc[0]}  ({best_acc[5]*100:.2f}%)")
print(f"best pooled brier    : HA={best_bri[0]}  ({best_bri[6]:.4f})")
print(f"least home bias      : HA={least_bias[0]}  ({least_bias[7]:+.4f})")
print()
print("SOP gate: a change ships only if it does not hurt accuracy OR brier on "
      "EITHER season versus HA=60 (deployed).")

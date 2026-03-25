# QA Report — 2026-03-25 — Sprint 2: Score Prediction

## Result: PASS (with one WARNING)

---

## Checks Run

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1a | config/score_model.yaml exists | PASS | File present and readable |
| 1b | intercept plausible (1–5) | PASS | 2.8437 — within range |
| 1c | coefficient plausible (0.02–0.06) | PASS | 0.034507 — within range |
| 1d | league_avg_ppg plausible (112–118) | PASS | 114.15 — within range |
| 2 | elo_diff_to_expected_margin() exists in elo_math.py | PASS | Lines 37–49, correct signature and formula |
| 3a | predicted_home_score in result dict | PASS | Line 898 |
| 3b | predicted_away_score in result dict | PASS | Line 899 |
| 3c | predicted_margin in result dict | PASS | Line 900 |
| 3d | Win probability logic untouched | PASS | calculate_expected_score not called directly in predictor; no changes to win prob path detected |
| 4 | score-projection block in export_github_pages.py | PASS | Line 550: `<div class="score-projection">` with predicted_away_score / predicted_home_score |
| 5a | Smoke test runs without error | WARNING | See below — HybridTeamPlayerPredictor class does not exist; predict_game_hybrid is a module-level function requiring 3 DataFrames |
| 5b | predicted_home_score present and in range (70–150) | PASS | 117 — valid |
| 5c | predicted_away_score present and in range (70–150) | PASS | 111 — valid |
| 5d | predicted_margin present | PASS | 6.0 |
| 5e | home_win_probability present | PASS | 0.6277 |
| 6 | Win probability in expected range (0.45–0.75) | PASS | 0.6277 — within range |

---

## Issues Found

### WARNING — Smoke Test Invocation Signature (Severity: Low)

The smoke test command in the sprint spec called `HybridTeamPlayerPredictor()` as a class, but `predict_game_hybrid` is a module-level function, not a class. The function also requires three DataFrames (`team_ratings`, `player_ratings`, `player_team_mapping`) as positional arguments — it cannot be called with team IDs alone.

This is not a code defect. The Sprint 2 implementation is correct. The issue is that the recommended smoke test invocation in the sprint spec will always fail with an `ImportError` / `TypeError` if run verbatim. Any downstream script, newsletter export, or documentation that references `HybridTeamPlayerPredictor` as a class name needs to be updated to use the function directly with loaded DataFrames.

Recommended fix: Update the sprint spec and any caller examples to match the actual interface:

```python
from src.predictors.hybrid_team_player import predict_game_hybrid
result = predict_game_hybrid(home_team_id, away_team_id, team_ratings, player_ratings, player_team_mapping)
```

---

## Score Model Parameters (Reproduced for Record)

```
intercept:      2.8437
coefficient:    0.034507
league_avg_ppg: 114.15
train_r2:       0.1527   (acceptable for margin prediction — noisy task)
holdout_r2:     0.1702
holdout_mae:    11.31 pts
```

The holdout R² is slightly higher than train R², which is unusual but not alarming at this scale (29k train / 2.3k holdout). It does not indicate data leakage given the margin prediction task is inherently noisy. No action required.

---

## Smoke Test Output (BOS ID=2 vs MIA ID=14)

```
home_score:  117
away_score:  111
margin:      6.0
home_prob:   0.6277
```

All four fields present. Scores in 70–150 range. Margin consistent with score split. Win probability in valid range.

---

## Recommendation

PROCEED to newsletter generation / GitHub Pages export.

The WARNING (invocation signature mismatch in the spec) is cosmetic — the production code is correct. Flag to the Analyst to update any documentation or example scripts that reference `HybridTeamPlayerPredictor` as a class.

# Model Gains: Audit, Ablations, and Decisions

**Date:** 2026-07-01 | **Author:** Claude (full project handoff) | **Status:** Decisions taken, implementation scheduled

## 1. The tracking audit (headline finding)

`auto_track_predictions.py` predicted completed games retroactively using ratings
computed from ALL completed games, including the game being predicted. The game's
own result leaked into its "prediction."

**Measured with a strict walk-forward replay of the identical production config
on the identical 657 games:**

| Record | Accuracy |
|---|---|
| Published (leaked) | 73.52% |
| Honest walk-forward | **70.62%** |
| Picks that differ | 11.7% of games |

**Decisions taken (2026-07-01):**
- Historical record corrected everywhere: recap post, footer banner, and the live
  site's `prediction_tracking.csv` (VPS backup kept at
  `prediction_tracking_LEAKED_BACKUP_20260701.csv`). The public number is 70.62%.
- The correction is disclosed openly in the launch post (transparency is the brand).
- `auto_track_predictions.py` must be rebuilt to snapshot predictions BEFORE games
  (log at prediction time, reconcile results later). Scheduled: July engineering
  block, alongside the roster Phase A work. Until then, no games are being played,
  so nothing regresses.
- Walk-forward replay (`scripts/audit_tracking_leakage.py` +
  `scripts/ablation_honest_2025_26.py`) is now the standard validation harness.
  No model change ships without it.

A second, related defect: the retro-tracked games gave BOTH teams a 0-days-rest
penalty (their "last game" was the game itself), so rest penalties cancelled to
zero in every tracked prediction, and the tracking flags (`home_back_to_back`
etc.) are hardcoded `False` placeholders.

## 2. Honest feature ablations (657 games, 2025-26)

| Variant | Accuracy | Delta vs baseline |
|---|---|---|
| Production config (all features) | 70.62% | — |
| No rest penalties | 69.86% | rest is worth +0.76pp |
| B2B penalty only (drop -15 one-day penalty) | 70.78% | one-day penalty HURTS -0.16pp |
| No form factor | 70.17% | form is worth +0.45pp |
| No top-player concentration | 71.23% | concentration HURTS -0.61pp |
| No season reversion | 70.47% | reversion worth +0.15pp |

**Combined candidate configs (accuracy + Brier):**

| Config | Accuracy | Brier |
|---|---|---|
| Production (b2b46, 1day15, conc on) | 70.62% | 0.2046 |
| **b2b46, no 1-day, conc off** | **71.39%** | **0.1977** |
| b2b60, no 1-day, conc off | 71.23% | 0.1974 |
| b2b30, no 1-day, conc off | 71.08% | 0.1977 |

**Decision:** New production config for 2026-27 = **b2b penalty 46, one-day
penalty 0, top-player concentration OFF.** +0.77pp accuracy and better
probability quality on the honest replay. Caveat: 657 games means ~5 games of
noise on that delta; confidence comes from accuracy AND Brier agreeing, both
sub-changes helping independently, and a plausible mechanism (concentration
double-counts player strength that the player layer already carries; supporting
evidence: picks flipped against the raw ELO favorite ran 49.5% — coin flip).

## 3. Calibration defect (honest data)

| Stated confidence | Games | Actual win rate |
|---|---|---|
| 50-60% | 195 | 60.0% |
| 60-70% | 119 | 69.7% |
| 70-80% | 142 | 73.2% |
| 80-90% | 117 | 78.6% |
| 90%+ | 84 | 81.0% |

Under-confident at the bottom, over-confident at the top. **Decision:** fit a
probability recalibration layer (Platt scaling / logistic on the ELO-implied
prob, fit on multi-season walk-forward output, validated out-of-sample) before
opening night. This won't change many picks but fixes the stated probabilities,
which is what premium subscribers actually consume.

## 4. Priority queue for the offseason (ranked by expected value)

1. **Tracking integrity rebuild** (log-at-prediction-time) — trust is the
   product; mandatory before first 2026-27 game.
2. **Ship the new feature config** (+0.77pp measured) — one-line changes plus
   walk-forward re-validation.
3. **Roster handling Phase A** (nightly mapping refresh, overrides file) — fixes
   trades; design in `2026-07-01-roster-handling-design.md`.
4. **Probability recalibration** — fixes the top-bucket overconfidence.
5. **Roster-delta preseason adjustment + rookie priors (Phase B)** — targets
   October accuracy, powers the free-agency and preseason content series.
6. Close-game work (58.3% honest) — hardest, highest ceiling; revisit after 1–5.

## 5. What did NOT survive scrutiny

- The "close game accuracy 61%" and "86% high-confidence" numbers in older docs
  were leakage artifacts. Honest: 58.3% close, 77.6% high-confidence.
- "No season reset" in CLAUDE.md is stale: 75/25 reversion exists in
  `compute_season_elo` and works (+0.15pp).
- The drift-alert threshold bug (alerting at ≥ 0) was already fixed upstream;
  the May 11 report shows healthy thresholds (≥ 3).

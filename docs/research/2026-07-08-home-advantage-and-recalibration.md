# Home advantage + probability recalibration: no change ships

**Date:** 2026-07-08
**Decision:** **Keep `home_advantage = 60`. Do not add a calibration layer.**
Both were investigated, both failed their evidence gate. Queue item #2
("probability recalibration") is closed as *no action*.

## Why we looked

Over the 657 tracked games of 2025-26, the model's mean predicted home
probability was **0.5945** against an actual home-win rate of **0.5830**, a
+1.15pp home bias. The folded confidence buckets also looked overconfident at the
top (90%+ picks won 81%). Both suggested a cheap win.

## Finding 1: the recalibration premise does not survive out-of-sample

Unfolded (home prob vs home win), the error is not a single temperature:

| predicted home prob | n | actual | gap |
|---|---|---|---|
| 0.30-0.40 | 80 | 0.300 | -0.047 |
| 0.50-0.60 | 134 | 0.612 | **+0.070** |
| 0.80-1.00 | 190 | 0.795 | **-0.077** |

The 0.80+ overconfidence and the 0.50-0.60 *under*confidence cancel, so a global
Platt scaling buys 0.3% of Brier even fit in-sample.

Fit honestly (chronological split, train on the first 394 tracked games, test on
the last 263), **both calibrators made Brier worse**:

| method | Brier | LogLoss | Accuracy |
|---|---|---|---|
| raw | **0.1782** | 0.5362 | 0.7643 |
| Platt | 0.1853 | 0.5546 | 0.7643 |
| isotonic | 0.1821 | 0.5487 | 0.7643 |

Cause: the model sharpened across the season (61% Nov-Dec, 77% Mar, 80%
playoffs). A calibrator fit on the weak early stretch over-shrinks the strong
late one. Much of the apparent miscalibration is non-stationarity.

Note the accuracy column: **identical for all three.** Any monotonic probability
map preserves which side of 0.5 a pick lands on. Recalibration can never improve
the 70.6%; it can only make the published confidence numbers honest. Never
promise accuracy gains from it in content.

## Finding 2: home_advantage is already at a flat optimum

Walk-forward sweep on **both** seasons (`scripts/sweep_home_advantage.py`),
everything else at the deployed config (k=20, MOV on, enhanced on, b2b 46,
one-day 0, concentration off):

| HA | 2024-25 acc / brier | 2025-26 acc / brier | pooled acc / brier | bias |
|---|---|---|---|---|
| 40 | 66.79% / 0.2134 | 68.09% / 0.2090 | 67.45% / 0.2112 | -0.0112 |
| 45 | 66.79% / 0.2133 | 68.24% / 0.2089 | **67.53%** / 0.2111 | -0.0070 |
| 50 | 66.87% / 0.2133 | 68.09% / 0.2090 | 67.49% / 0.2111 | -0.0028 |
| 55 | 66.94% / 0.2132 | 67.87% / 0.2089 | 67.41% / **0.2110** | +0.0011 |
| **60 (deployed)** | 66.87% / 0.2133 | 67.80% / 0.2089 | 67.34% / 0.2111 | +0.0048 |
| 65 | 66.64% / 0.2133 | 68.24% / 0.2089 | 67.45% / 0.2111 | +0.0086 |

Pooled accuracy spans 0.3pp across the whole range and pooled Brier is flat to
the 4th decimal. The 2025-26 column is non-monotonic (HA=45 and HA=65 both give
68.24%), the signature of noise.

**Validity check:** the bias column moves monotonically from -0.0298 (HA=20) to
+0.0189 (HA=80), which proves the parameter really does flow into the prediction.
The flat accuracy/Brier is a property of the model, not a wiring bug.

## Finding 3: the paired test kills it

Every config predicts the same games, so a paired test is far more powerful than
comparing marginals (`scripts/qa_home_advantage_paired.py`, n=2,679 paired games,
McNemar exact on flips + 10k paired bootstrap on Brier):

| candidate | acc delta | McNemar p | Brier delta | boot 95% CI | p |
|---|---|---|---|---|---|
| HA=45 | +5 games | 0.597 | +0.000015 | [-0.000532, +0.000579] | 0.950 |
| HA=50 | +4 games | 0.627 | -0.000008 | [-0.000374, +0.000360] | 0.959 |
| HA=55 | +2 games | 0.815 | +0.000092 | [-0.000094, +0.000277] | 0.340 |

Not one is significant on either metric. Every bootstrap CI straddles zero.

Critically, **the motivating bias does not replicate.** On the full walk-forward
the HA=60 bias is only **+0.0048**, not the +0.0115 seen on the 657-game tracked
subset. The tracked-subset bias was largely sample noise. The hypothesis that
motivated this sweep was not supported.

## Decision

**No model change.** `home_advantage` stays at 60. HA=55 would zero the residual
bias, but it produces no measurable accuracy or Brier improvement (p=0.340,
2 games out of 2,679), and changing a production parameter for a statistically
indistinguishable result is churn. The SOP gate requires evidence of improvement,
not merely "not worse."

## What this means for the queue

The model's scalar parameters are tuned. Further fiddling is reading noise. The
remaining leverage is **capability we do not have**, not tuning we have not done:

- We still cannot produce a **roster-adjusted preseason rating**. Every public
  number we publish this offseason has to be hedged as "where they finished,"
  never a 2026-27 forecast. That blocks the September 30-teams-in-30-days series
  and it is the thing content actually needs.
- Rookies have no rating at all (Summer League opened 2026-07-09 with us unable
  to say anything about the No. 1 pick).

Promoting roster-delta preseason ratings + rookie priors to the top of the queue.

# Roster-delta preseason ratings

**Date:** 2026-07-09
**Status:** **Capability SHIPPED** (`scripts/generate_preseason_ratings.py`).
**Live-engine integration: NOT enabled. Needs Aaron's sign-off** (it fails the
letter of our own SOP gate, on two games).

## What it is

The team ELO carried into a new season is last season's rating reverted 75/25
toward the mean. It has no idea Giannis changed conferences. This adds one term:

    preseason(T) = 0.75*elo_end(S-1) + 0.25*1500 + K * delta(T)

    delta(T) = talent(who is on T now) - talent(who played for T last season)

`talent()` is the minutes-per-game-weighted mean player rating of the top-10
rotation. Both rosters are priced with the **same vintage** (player ratings as of
the end of S-1), so the delta measures personnel change, not rating drift.
Deltas are **centered to zero-sum** across the 30 teams: ELO is a relative scale,
and the league cannot improve by everyone signing someone. Without centering the
raw deltas carry a negative mean and silently deflate the whole league each year.

Code: `src/features/roster_delta.py` (backtest) and
`scripts/generate_preseason_ratings.py` (production).

## Validation

Every game predicted before its result is processed, same contract as
`validate_config_2seasons.py`. `K=0` reproduces the deployed baseline exactly
(66.87% / 0.2133 and 67.80% / 0.2089), which is the correctness check.

**Selection was done honestly.** A naive sweep on the two eval seasons peaked at
K=0.4 and "improved everything." But choosing K on the seasons you report is
selection on the test set, the same trap that killed the recalibration idea. So K
is chosen by **expanding window**: for each held-out season, K minimizes Brier on
every *prior* season only. It selected **K=0.8 in all 13 windows** (very stable).

**Pooled out-of-sample, 16,080 games, seasons 2013-14 .. 2025-26:**

| metric | baseline | roster-delta | test |
|---|---|---|---|
| Brier | 0.21643 | **0.21583** | boot 95% CI [+0.00014, +0.00108], **p=0.0090** |
| accuracy | 65.37% | 65.47% (+16 games) | McNemar p=0.4805, n.s. |

10 of 13 held-out seasons improved Brier.

**Leakage check.** The backtest must proxy the opening roster from early box
scores, which peeks at injuries in the games it then predicts. The gain grows
with the peek window (N=1: +0.00061, N=5: +0.00083, N=10: +0.00088, N=20:
+0.00106), so some of it *is* leakage. But at **N=1** (minimum peek) the gain is
still +0.00061 and still significant. The signal is personnel, not leakage. All
numbers above are reported at the conservative N=1. **Production has no leak at
all**: the roster comes from the NBA API in July.

**K is not at a boundary.** Training Brier bottoms at K≈1.2 (0.21290) and
degrades on both sides (K=1.6: 0.21320, K=2.0: 0.21378). A genuine interior
optimum, unlike the home-advantage sweep which was flat.

## The SOP gate result (read this before enabling)

| season | accuracy | Brier | verdict |
|---|---|---|---|
| 2024-25 | 66.87% -> 67.02% | 0.2133 -> 0.2132 | PASS |
| 2025-26 | 67.80% -> **67.65%** | 0.2089 -> 0.2087 | **FAIL** (accuracy) |

The failure is **two games out of 1,357**. Pooled over 16,080 out-of-sample games
the accuracy difference is not significant in either direction (p=0.48). This is
the same lesson recalibration taught us: a rating change that improves
probability quality does not necessarily flip picks, and accuracy is a coarse,
high-variance metric.

**But we do not quietly reinterpret our own bright line.** The honest statement:
roster-delta significantly improves probability quality (Brier) and leaves
accuracy statistically unchanged. Enabling it in the live engine is a judgement
call about whether a significant Brier gain justifies a change that cannot
promise an accuracy gain.

Recommendation: **enable at the 2026-27 season boundary with K=0.8.** The feature
only acts at a season boundary, so there is no urgency and no in-season risk.
Note that our public credential is accuracy (70.6%), and this will not move it.

## What shipped today

`data/exports/preseason_ratings.csv`, the first 2026-27 preseason table we can
publish. It reproduces the offseason from first principles, with nothing
hand-coded:

| team | delta | finished -> preseason |
|---|---|---|
| Washington Wizards | +114.4 | 1234 -> 1392 |
| Boston Celtics | +90.3 | 1673 -> 1702 |
| Indiana Pacers | +75.7 | 1312 -> 1420 |
| Miami Heat | +61.9 | 1506 -> 1554 |
| Portland Trail Blazers | +61.6 | 1492 -> 1543 |
| ... | | |
| Los Angeles Lakers | -65.4 | 1591 -> 1516 |
| Memphis Grizzlies | -70.8 | 1372 -> 1348 |
| Milwaukee Bucks | -96.0 | 1402 -> 1350 |
| LA Clippers | -163.1 | 1556 -> 1412 |

Clippers lose Kawhi, Milwaukee loses Giannis, Miami gains him, Memphis loses Ja,
Washington adds Anthony Davis and Deandre Ayton, Boston gets Tatum back, Indiana
gets Haliburton back. OKC stays first.

Preseason ratings are **compressed toward 1500 by the 75/25 reversion**, so nearly
every good team's number falls versus where it finished. That is uncertainty, not
a prediction that they got worse. Content must say so.

## Bugs found and fixed while building (do not reintroduce)

1. **Rookie test on minutes, not rating.** A rated star who missed the sampled
   games (Jalen Williams, Tyler Herro) was priced as a 1450 rookie. It dropped OKC
   136 points and made them look like they collapsed. A rookie is a player with
   **no rating**, full stop.
2. **Unrated fringe players carried rookie weight**, so two-way names
   (Thanasis/Alex Antetokounmpo) dominated a team's mean.
3. **Total minutes as weights** mixed a partial current season (max ~650 min) with
   a full prior one (~3,500). Use minutes per game; it is scale free.
4. **Uncentered deltas** would have deflated all 30 teams every season.

## Next

- Rookie priors are a single constant (1450). Draft position is the obvious
  refinement and it matters for the September series (Dybantsa, Peterson).
- Enable in the live engine at the October boundary, pending sign-off.

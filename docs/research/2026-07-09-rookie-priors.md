# Rookie priors by draft position: fitted, validated, NOT shipped

**Date:** 2026-07-09
**Decision:** **Keep the flat rookie prior (1450 rating, 12 mpg).** Draft-position
priors are fitted and available behind `compute_deltas(draft_priors=True)`, but
they are **disabled by default** because they do not improve prediction out of
sample. Do not enable without new evidence.

## Why we looked

`roster_delta` prices a player with no NBA history at a flat (1450, 12 mpg). Both
numbers are wrong on their face:

- 1450 sits below the actual rookie mean end-of-season rating (**1479.5**).
- Draft position clearly carries information about **minutes**.

## What the data actually says (and it is not what you would guess)

Rookie outcomes by draft slot, from our own history (n=1,142 rookie seasons):

| pick | n | end-of-rookie rating | mpg |
|---|---|---|---|
| 1-3 | 69 | 1,466.7 | 27.3 |
| 4-10 | 171 | 1,460.2 | 23.0 |
| 11-20 | 233 | 1,478.6 | 15.9 |
| 21-30 | 215 | 1,481.8 | 14.2 |
| 31-45 | 275 | 1,485.3 | 12.2 |
| 46-61 | 179 | 1,492.7 | 9.3 |

**Later picks finish their rookie year rated HIGHER.** Not because they are
better. Our player ELO moves in proportion to minutes played, so a lottery pick
logging 27 mpg of below-average rookie basketball falls further than a bench guy
logging 9. The real draft signal is minutes, not rating.

## The fit

`scripts/fit_rookie_priors.py`, on rookie seasons **2001-2012 only**, so the
2013-2025 validation window cannot inform the curve:

    rating = 1450.3 + 9.21 * ln(pick)
    mpg    =   31.62 - 5.55 * ln(pick)
    undrafted: rating 1488.5, mpg 10.7

It generalizes well to the held-out rookies:

| pick | predicted rating / mpg | held-out actual |
|---|---|---|
| 1 | 1450.3 / 31.6 | 1470.5 / 27.8 (n=36) |
| 10 | 1471.5 / 18.8 | 1470.6 / 20.5 (n=62) |
| 30 | 1481.6 / 12.7 | 1484.4 / 12.9 (n=56) |
| 45 | 1485.4 / 10.5 | 1485.5 / 10.8 (n=45) |

So the curve is right. It just does not matter.

## Validation: a clean null

`scripts/qa_rookie_priors.py`. K held at its validated 0.8 for **both** arms, so
the only difference is the rookie prior. Every held-out season scored out of
sample, pooled, compared paired on identical games.

**Seasons 2013-14 .. 2025-26, 15,861 paired games:**

| metric | flat prior | draft prior | test |
|---|---|---|---|
| Brier | 0.21625 | 0.21624 | boot 95% CI [-0.000062, +0.000091], **p=0.72** |
| accuracy | 65.38% | 65.37% (-1 game) | McNemar **p=1.000** |

Six of thirteen seasons improved. That is a coin flip.

## Why it is null (the mechanism, not a shrug)

All 733 deltas change, so the feature is wired correctly. But switching priors
moves a team's delta by **1.56 player-rating points on average** (max 12.9)
against a delta spread of **37 points (1 sd)**. After K=0.8 that is roughly one
ELO point.

Two reasons it cannot matter:

1. **A rookie is replacement level.** At 1450-1490 he is worth about what the
   1500-ish rotation player he displaces is worth. Getting his minutes right
   moves a minutes-weighted rotation mean almost not at all.
2. **Deltas are zero-sum by construction.** Any level shift common to all 30
   teams (and every team drafts) is centered straight back out. Only the
   *differential* between teams survives, and that is small.

## Decision

Keep the flat prior. `draft_priors=True` stays available and tested, defaulted
off. Fitted coefficients live in `config/rookie_priors.json`.

We will not chase this further. Note the pattern: this is the fourth consecutive
attempt to improve prediction (recalibration, home advantage, injury-awareness,
rookie priors) that came back null or unfalsifiable. The model's remaining error
is not in its priors.

## What this IS good for: content

The September 30-teams-in-30-days series does not need a rookie rating; it needs
an honest answer to "what does your model think of Dybantsa?" The answer is now
*earned* rather than evasive: **we fitted draft position properly, tested it, and
it did not change a single prediction.** That is a better post than a fake number.

Caveat for that series: the 2026 draft is **not in `nba_api` yet**
(`drafthistory` ends at 2025), so Dybantsa's and Peterson's picks must come from
news at write time.

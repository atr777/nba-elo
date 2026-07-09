# Coaching effectiveness: no alpha. But the question found a real bug.

**Date:** 2026-07-09 (Aaron's question, from a soccer modeller: can we measure
coaching via after-timeout points, timeout efficacy, time management?)
**Answer:** No, and we can prove it cheaply without scraping a single play-by-play.
**But:** the diagnostic surfaced the largest prediction improvement we have found.
**Decision required from Aaron.** Nothing shipped.

## 1. There is no coaching alpha to find

Coaching can only improve *prediction* if teams systematically beat or miss what
their rating predicts, and if that residual persists. Team ELO already absorbs
coaching: a well-coached team wins, so its rating rises. An after-timeout
efficiency *level* is collinear with the rating itself.

Walk-forward, deployed config, residual = mean(actual win - predicted win prob)
per team-season, 776 team-seasons, 2000-2025:

| quantity | value |
|---|---|
| sd of team-season residuals | 0.0511 (4.2 wins per 82) |
| sd expected from coin-flip noise alone | 0.0552 |
| **excess ("true" team-level) sd** | **0.0000** |

The observed spread is entirely consistent with binomial noise. **There is no room
left for a persistent coaching skill to live in.** A perfect after-timeout metric
would be explaining randomness. This does not say coaching does not matter; it
says its effect is already *inside* the rating.

Do not scrape play-by-play for this.

## 2. What the diagnostic did find

Residuals are **negatively** autocorrelated season to season:

    corr(resid_S, resid_S+1) = -0.106, p = 0.0038, n = 746 team-season pairs
    placebo (team labels shuffled within season): mean r = +0.002, 95% [-0.069, +0.071]

Teams that beat their rating one year *miss* it the next. That is not skill
persisting; it is the signature of an ELO that carries **too much** of last season
forward. The season-reversion factor is 0.75, and it had never been swept.

## 3. Sweeping season reversion

`scripts/sweep_season_reversion.py`, then `scripts/qa_season_reversion.py` using
the exact protocol from the roster-delta validation: expanding-window selection
(each held-out season's factor chosen only from seasons before it), pooled paired
comparison against the deployed value.

Selection landed on **0.45 in 12 of 13 windows** (0.40 once). Deployed 0.75 is the
**worst value in the grid** on training Brier.

**Pooled out-of-sample, 15,861 games, seasons 2013-14 .. 2025-26:**

| metric | rev 0.75 (deployed) | rev 0.45 | test |
|---|---|---|---|
| Brier | 0.21696 | **0.21576** | boot 95% CI [+0.00064, +0.00178], **p = 0.0000** |
| accuracy | 65.24% | 65.31% (+11 games) | McNemar p = 0.68, n.s. |

That Brier gain is **~2x roster-delta's** and ~20x the rookie prior. It is the
largest effect we have measured.

**Mechanism check.** At rev 0.45 the residual autocorrelation that motivated the
sweep collapses to **-0.058 (p = 0.11)**, no longer significant. The defect the
diagnostic identified is the defect the parameter fixes.

## 4. The uncomfortable part: roster-delta is largely subsumed

Reversion and roster-delta both correct a stale rating at the season boundary.
K = 0.8 was validated *at reversion 0.75*. Re-testing jointly (pooled OOS, 2013-2025):

| config | Brier | accuracy |
|---|---|---|
| deployed (rev .75, K=0) | 0.21696 | 65.24% |
| roster-delta only (rev .75, K=.8) | 0.21625 | 65.38% |
| **reversion only (rev .45, K=0)** | **0.21572** | 65.33% |
| both (rev .45, K=.8) | 0.21542 | 65.30% |

Paired bootstrap:

- rev .45 alone **vs deployed**: +0.001241, **p = 0.0000 (significant)**
- rev .45 + K=.8 **vs rev .45 alone**: +0.000297, **p = 0.272 (not significant)**

**Once reversion is set correctly, roster-delta adds nothing measurable.** It was
mostly a proxy for "revert more." Roster-delta remains the only way to *publish* a
2026-27 preseason table (it prices named players, which a scalar cannot), but its
value to the live engine is now in doubt.

## 5. The SOP gate

| season | accuracy | Brier | verdict |
|---|---|---|---|
| 2024-25 | 66.87% -> 66.34% | 0.21330 -> 0.21195 | **FAIL** (accuracy) |
| 2025-26 | 66.52% -> 66.43% | 0.21494 -> 0.21274 | **FAIL** (accuracy) |

Brier improves on both. Accuracy falls on both, by 7 games and 1 game
respectively. Pooled over 15,861 out-of-sample games the accuracy difference is
**not significant in either direction** (p = 0.68), so these are noise. But the
bright line says a change ships only if it hurts neither metric on either season,
and by that line this fails.

Note the recurring shape: **every rating-quality improvement we find shows up in
Brier and not in accuracy.** Accuracy only moves when a pick flips across 0.5.

## 6. Decision required

Nothing is shipped. Three coherent options:

1. **Ship reversion 0.45, disable roster-delta in the engine.** Simplest model,
   largest and most significant Brier gain, accuracy statistically unchanged.
   Keep `generate_preseason_ratings.py` for content. Fails the accuracy bright line.
2. **Keep 0.75 + roster-delta** (today's state). Defensible: nothing has beaten
   the accuracy gate, and accuracy is our public credential.
3. **Ship reversion 0.45 AND keep roster-delta at K=0.8.** Best raw Brier, but the
   increment over option 1 is not significant, so it buys complexity for noise.

Reminder for content either way: this will **not** move the 70.6%. That record is
logged pre-game and never recomputed. A reversion change alters future predictions
and the displayed team ratings, not the credential.

## 7. Loose end

The one coaching variant not ruled out is a **coach CHANGE** effect (a new head
coach makes the carried-over rating stale), which is the exact analogue of
roster-delta. Given that reversion subsumed roster-delta, a coach-change term
would very likely be subsumed too. Testable cheaply with `nba_api` coach data if
Aaron wants it closed formally.

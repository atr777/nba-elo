# Second Bounce: Season Operations SOP

**Version 1.0 — 2026-07-01.** The standing operating procedure for running this
project accurately and profitably. Owned by Claude, approved by Aaron.

## Prime directives

1. **Never publish a number that wouldn't survive an audit.** Every accuracy
   claim traces to walk-forward, pre-game predictions. The harness is
   `scripts/audit_tracking_leakage.py`; if a stat can't be reproduced by it,
   it doesn't ship.
2. **No model change without a before/after walk-forward comparison** (accuracy
   AND Brier) on at least one full season, ideally two.
3. **Predictions are logged when made, graded when played.** Never recomputed
   after the fact.
4. **Aaron publishes, Claude drafts.** Nothing goes public (posts, tweets, site
   copy changes beyond automated daily updates) without Aaron pressing the button.
5. **No em dashes. Every post carries at least one data graphic.**

## Daily loop (in season; automated on VPS, 5x daily)

| Step | What | Gate |
|---|---|---|
| 1 | Data pull (games, injuries, rosters) | Freshness check: newest game ≤ 24h old |
| 2 | Ratings update + today's predictions | Predictions logged to pending file BEFORE tip-off |
| 3 | Yesterday's results reconciled against pending log | Accuracy tally updates only from pre-game snapshots |
| 4 | Site regenerated + pushed | Stat block matches tracking CSV |
| 5 | Drift check (`detect_model_drift.py`) | ALERT → investigate before next content goes out |

Manual daily (5 min, Claude): skim `DRIFT_STATUS.md`, skim the site, queue the
daily X graphic if in season.

## Weekly loop (in season)

- **Accuracy receipt post** (free tier + X thread): last week's record from the
  honest log, one graphic, wins AND misses. This is the growth engine; never skip.
- Check subscriber metrics: total, weekly growth, open rate.
- Backup: pull `prediction_tracking.csv` from VPS to local.

## Monthly loop

- Player ELO calibration review (existing scheduled task).
- Calibration bucket check on season-to-date honest data: any bucket off by
  more than 5pp on 50+ games → recalibration investigation.
- VPS health: disk, cron log tail, billing status (auto-renew ON as of Jul 2026).

## Change management

- Feature/parameter changes: branch → walk-forward on 2024-25 AND 2025-26 →
  decision doc entry (docs/research/) → deploy to VPS → verify next morning's
  run. Never deploy on a game day within 2 hours of first tip.
- Every deploy is a git commit pulled by the VPS's own update step; no manual
  file edits on the server (the one exception, corrected tracking history, is
  backed up as `prediction_tracking_LEAKED_BACKUP_20260701.csv`).

## Revenue operations

**Model: free newsletter → premium tier at season start.** No betting content
(Aaron's standing decision, 2026-07-01).

| Phase | Trigger | Action |
|---|---|---|
| Now–Aug | — | 2 posts/week free content; X 3-4/week; grow list |
| Sept | — | Preseason series (30 teams / 30 days) |
| Opening night | — | Season launch post: full-slate picks begin, free |
| In season | — | Weekly receipt post; audience growth is the only revenue KPI |

### REVISED 2026-07-26 (Aaron's decision): stay free, pursue sponsorship

**There is no paid tier for 2026-27.** The earlier plan (activate $6/mo late Sept)
was not executable: Substack paid runs exclusively on Stripe and **Stripe does not
support Guatemala**. Rather than stand up alternative rails, Aaron chose to stay
free and monetize through brand partnerships once the audience justifies it.
Full reasoning: `docs/research/2026-07-26-strategic-competitive-monetization-review.md`.

Consequences, and they are the whole strategy now:

- **Audience size is the only metric that matters.** Sponsorship needs roughly
  5k followers/subscribers before anyone pays real money. Everything is judged
  against list growth.
- **The sponsor pool is narrower than the category's.** Sportsbooks and
  prediction markets dominate basketball-newsletter sponsorship (Kalshi sponsors
  halfpast\*noon). **The no-betting rule stands and rules them out.** Realistic
  targets: data/analytics tools, sports media apps, ticketing, apparel, DTC.
  Never take a book or a prediction-market sponsor, however good the offer.
- **No paywall means no conversion gate**, so the old 300-subscriber trigger and
  the paid-conversion KPI are retired.
- Revisit paid in 2027 if the list clears ~3k, at which point a US entity for
  Stripe becomes worth the paperwork.

**KPIs reviewed weekly:** free subs, weekly sub growth, open rate, X followers.
Growth stall = content mix problem: bias toward receipts and contrarian model
takes, away from methodology. **Subscriber count is currently unmeasured** (the
stored Substack cookie 403s on stats endpoints); fix or log it manually, because
it is now the primary business metric.

**The credential line.** Lead with auditability and calibration, not raw accuracy:
"Every pick logged before tip-off, graded after the final, never recomputed. When
the model says 80%, it wins 80%." Quote "70.6% across 657 games in 2025-26,
verified by walk-forward audit" when asked for the number, and never 73.5%. Do not
frame us as beating the market: measured 2026-07-26, we sit slightly behind Vegas
on both accuracy and Brier. See `model-tuning-exhausted` in project memory.

## Incident playbook

- **Pipeline dead** (site stale > 24h in season): SSH `nba-vps`, check
  `logs/daily_update.log`, rerun `bash /opt/nba-elo/run_daily_update.sh`.
- **Accuracy crater** (7-day < 55% on 15+ games): freeze content claims, run
  error-analysis segmentation, check data freshness first (stale rosters and
  injury data are the usual suspects), only then consider model causes.
- **Wrong number published:** correct it loudly and immediately (precedent set
  2026-07-01 with the 73.5→70.6 correction). Cover-ups kill this business;
  corrections build it.

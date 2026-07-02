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
| Sept | — | Preseason series (30 teams / 30 days); founding-member waitlist mention |
| Late Sept | List ≥ 300 | Activate paid tier: $6/mo, $50/yr, $100 founding |
| Late Sept | List < 300 | Still activate, but lead with founding tier only (scarcity framing) |
| Opening night | — | Premium launch post: full-slate picks begin |
| In season | Paid conversion < 4% after 4 weeks | Add premium-only sample posts (open one Deep Dive free per month) |

**KPIs reviewed weekly:** free subs, weekly sub growth, open rate, X followers,
(in season) paid subs + churn. Growth stall = content mix problem: bias toward
receipts and contrarian model takes, away from methodology.

**The credential line (use everywhere):** "70.6% accuracy across 657 games in
2025-26, verified by walk-forward audit, tracked in public."

## Incident playbook

- **Pipeline dead** (site stale > 24h in season): SSH `nba-vps`, check
  `logs/daily_update.log`, rerun `bash /opt/nba-elo/run_daily_update.sh`.
- **Accuracy crater** (7-day < 55% on 15+ games): freeze content claims, run
  error-analysis segmentation, check data freshness first (stale rosters and
  injury data are the usual suspects), only then consider model causes.
- **Wrong number published:** correct it loudly and immediately (precedent set
  2026-07-01 with the 73.5→70.6 correction). Cover-ups kill this business;
  corrections build it.

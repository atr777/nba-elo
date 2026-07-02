# Second Bounce — 2026-27 Launch Kit

> Created 2026-07-01 (project handoff). Goal: profitable by opening night (~Oct 21, 2026).
> Strategy: content/newsletter monetization. Funnel: **X → site → Substack free → Substack premium.**

---

## The Credential

Everything we publish leads with this, because it's true and verifiable on the site:

> **73.5% prediction accuracy across all 657 games of the 2025-26 season.**
> Open methodology, tracked publicly every day since October 2025.

Secondary proof points: 81.4% over the final stretch, fully automated daily pipeline, transparent tracking page.

---

## 1. Substack Setup (Aaron creates, ~20 minutes)

- **Publication name:** Second Bounce
- **URL:** `secondbounce.substack.com` (fallback: `secondbouncenba`)
- **Tagline:** "NBA predictions from a 73.5%-accurate ELO engine. Every game, every day, tracked in public."
- **Categories:** Sports
- **Sections to create:** "Daily Slate" (free), "The Deep Dive" (premium, activate in Sept)
- **About page:** I'll draft it once the account exists.
- Connect the same email you use for the site (athro27@gmail.com) and send me the publication URL.

**Pricing (activate late Sept, not before):** $6/mo, $50/yr, founding $100.
Free tier through the whole offseason — we're building the list, not milking it.

### What free vs premium gets (season)
| | Free | Premium |
|---|---|---|
| Daily picks (all games, confidence %) | Top 3 games | Full slate |
| Weekly accuracy report | ✅ | ✅ |
| Toss-up game breakdowns | — | ✅ |
| Player ELO movers + injury impact analysis | — | ✅ |
| Model change logs ("why we adjusted X") | — | ✅ |

The existing `export_substack_daily.py` / `export_substack_premium.py` scripts map to these tiers; I'll rework their output format once the publication exists.

---

## 2. X / Twitter (Aaron creates account)

- **Handle (in order of preference):** `@SecondBounceNBA`, `@SecondBounceELO`, `@2ndBounceNBA`
- **Name:** Second Bounce 🏀
- **Bio:** "NBA game predictions from a hybrid ELO engine. 73.5% accurate over the full 2025-26 season (657 games, tracked publicly). Daily picks in season."
- **Link:** the GitHub Pages site (later: Substack)
- **Pinned tweet (I'll finalize when account exists):** season-recap thread with the 73.5% receipt, screenshot of the tracking page, link to methodology.

**Content pillars (offseason, 3–4 posts/week):**
1. **ELO reacts to free agency** — every significant signing/trade: "What does the model say [team]'s rating looks like now?" (July is free-agency month — this is why we launch NOW)
2. **Season recap series** — best calls, worst misses, what 73.5% actually means vs coin-flip and vs experts
3. **Model transparency** — how the engine works, one concept per post (K-factor, home advantage, WElo dampening)
4. **Preseason ratings reveals** — September: one team per day, 30-day countdown to tip-off. This is the flagship growth play.

**In season:** daily slate graphic (auto-generated from the pipeline), weekly accuracy receipt post.

## 3. Discord (Aaron creates server, I design it)

Launch in **August** — after X has some followers to invite (don't open an empty room).
- **Channels:** #announcements, #daily-picks (auto-post via webhook from VPS pipeline), #model-talk, #general
- Webhook integration is a small script I'll add to the VPS cron once the server exists.

---

## 4. Offseason Calendar

| When | What | Owner |
|------|------|-------|
| **July (now)** | Substack + X accounts created | Aaron |
| July | Season recap post (free) + pinned X thread | Claude |
| July | Free-agency ELO reaction posts as signings happen | Claude |
| July | Engine: season-reset reversion (75/25), roster/mapping refresh, drift-alert bug fix | Claude |
| Aug | Discord launch; schedule-release content (hardest/easiest schedules by ELO) | Both |
| Sept | Preseason ratings reveal series (30 teams, 30 days) | Claude |
| Late Sept | Activate premium tier; founding-member offer to early list | Aaron flips switch |
| Oct | Opening-week predictions; premium launch push | Claude |

## 5. Revenue Math (sanity check)

Substack median conversion free→paid is 5–10%. At $50/yr:
- 500 free subs → ~25–50 paid → **$1,250–2,500/yr**
- 2,000 free subs → ~100–200 paid → **$5,000–10,000/yr**

Costs: VPS (~$5–7/mo, auto-renews), everything else $0. Break-even is roughly **2 paid subscribers**. The whole game is list size by opening night, which is why every July/August action above is growth, not monetization.

---

## Engine work queue (pre-season hardening, Claude)

1. **Season-reset reversion** — 75% prior + 25% mean at season rollover (without it, October accuracy will sag and damage the credential right at premium launch)
2. Offseason roster movement → refresh `player_team_mapping.csv`, handle traded players' ELO carryover
3. Fix drift-detection threshold bug (`consecutive wrong picks: 0 ≥ 0 → ALERT`)
4. Offseason mode for the site (season recap view instead of "0 games today")
5. Discord webhook + X-ready daily graphic export from the VPS pipeline

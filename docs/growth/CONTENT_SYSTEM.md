# The Content System

**v1 — 2026-07-02.** The weekly production loop for Second Bounce. Written to be
executable by ANY operator (human or any Claude model) from a cold start.
Voice/visual rules live in `BRAND.md`; this file is the assembly line.

## Content taxonomy

| Type | What | Cadence | Length | Audio |
|---|---|---|---|---|
| **Essay** | The Tuesday flagship: one idea, argued with our data | Weekly, Tuesday | 900-1,400 words | Always |
| **Reaction** | Breaking news through the model's eyes | Within 24h of big news | 500-800 words | Always |
| **Receipt** (in season) | Monday: last week's record, best call, worst miss | Weekly, Monday | 400-600 words | Optional |
| **X posts** | Chart crops, receipts, one-liners from the model | 2-3/day scheduled | — | — |
| **Notes** | Substack's social feed; growth engine | 1-3/day | 1-3 sentences | — |

The first two published pieces: season recap = launch Essay; FA day one = Reaction.

## The weekly loop

**Session A (Monday or Tuesday), Claude produces:**
1. The Tuesday Essay: draft md in `docs/growth/posts/YYYY-MM-DD-slug.md`,
   graphics via the house scripts, narration script alongside as
   `*-narration.txt`.
2. `python scripts/substack_push_draft.py <post.md> --subtitle "..."` (tags
   auto-applied).
3. `python scripts/generate_narration.py <post-narration.txt>` (MP3 lands in
   Desktop/SecondBounce_Brand).
4. The week's **bank**: `docs/growth/banks/YYYY-Wnn-bank.md` with 8-12 X posts
   (each with its image path) and 8-12 Notes.

**Aaron then (15-20 min):**
1. Review draft → attach MP3 (editor + → Audio) → Publish (7-10PM ET slot).
2. X web → schedule the bank's posts: one ~9AM ET, one-two in the 7-10PM ET
   window per day ([Buffer/Sprout data: sports peaks 7-10PM weekdays,
   3-6PM weekends]).
3. Substack app → post 1-3 Notes/day from the bank (or approve the bank for
   auto-drip once VPS Notes posting ships).

**Session B (Thursday or Friday), Claude produces:** reaction drafts for the
week's news, restocks the bank, answers/queues anything Aaron flagged.

**Breaking news exception:** speed beats polish. If Aaron opens a session
within the hour of big news, a Reaction ships same-day: card + 500 words +
narration in one pass.

## Image decision tree (per post)

1. Every post: ≥1 house-style chart (dataviz rules in BRAND.md) + footer banner
   (`generate_brand_assets.py` regenerates with live receipt).
2. Post about ONE player/team: exactly one player card
   (`generate_player_card.py <nba_id> "Name" <rating> "kicker"`). Never more.
3. Season-scale story: the moments-ribbon pattern (`generate_moments_ribbon.py`
   as template).

## The tweet formulas that fit us

- **The receipt:** screenshot-style stat + "verified walk-forward" framing.
- **The contrarian number:** model disagrees with market/discourse (Kessler
  tax). Our best viral vector.
- **The confession:** we publish our misses. Rare = powerful.
- **The chart crop:** one chart, one sentence, link.
- Always: plain claims, no hashtags, no engagement-bait questions, no em dashes.

## Standing rules

- Aaron is the only publish button. Claude never posts publicly.
- Every number in content must be reproducible from
  `data/exports/prediction_tracking_honest.csv` or the walk-forward harness.
- Narration voice is River (`SAz9YHcvj6GT2YYXdXww`), always introduced as the
  voice of the model, never a fake human.
- Credits budget: ~121k/month ElevenLabs ≈ 2h audio; a normal week uses <15 min.

## ROSTER ACCURACY (hard rule — Aaron, 2026-07-03)

`player_team_mapping.csv` is STALE (pre-free-agency). Player ratings are correct;
their TEAM assignments are NOT. **Never name a player as being on a team from the
mapping without verifying against current news.** A single wrong roster claim
(Naz Reid, Anthony Davis) destroys credibility. Until the nightly roster refresh
(Roster Phase A) ships, and during any active transaction window even after:
- Team ELO ratings are always safe to cite (team-level, not roster-dependent).
- A player's individual rating is safe to cite; WHERE they play is not.
- Roster detail in any post gets a live news verification at write/fire time,
  for that specific team, right before it goes out. No pre-built roster lists.

## The Posting Pack (end-of-day deliverable for next day)

Standard next-day handoff. Must be phone-usable and paste-able into Aaron's
private Discord with ZERO back-references ("same as before" is banned).

Format:
- Title: `SECOND BOUNCE — POSTING PACK (<date>)`.
- **Part 1: schedule table.** Columns: time (US Central, primary) + ET
  reference (CT = ET - 1h), platform (X / Substack), one-line description,
  asset filename. Audience is US, so anchor slot strategy to ET peak windows,
  then convert. Holidays: pull earlier (US evenings die on holidays).
- Under the table, **every post's exact copy in its own fenced code block** so
  each is one-tap copyable on mobile. Spell everything out; never reference an
  earlier message.
- Media reminder: the .mp4/.png assets live on the PC; tell Aaron to drop them
  into the Discord channel too (while PC is on) so his phone has them.
- **Part 2 (optional): contingency content** that fires on news (e.g. a star's
  decision). Give the frame + caption; fill verified roster detail at fire time
  per the roster-accuracy rule above.
- End with override rules (what breaking news supersedes the plan).

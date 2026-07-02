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

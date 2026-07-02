# Second Bounce Brand Book v1

**2026-07-01.** Inspired by halfpast*noon's system, built in our own voice.
Their brand is craft and culture. Ours is a machine with receipts.

## 1. What we learned from halfpast*noon (research summary)

| Element | What they do | What we take from it |
|---|---|---|
| Positioning | Anti-clickbait "social media-enabled basketball magazine," 90s-magazine soul | The *stance*: slow, real, proud of craft. Not the culture-mag identity |
| Signature motif | The asterisk (halfpast\*noon, "\*a \*creative \*space\* for\* hoops\*") and timestamp gimmick | Have ONE ownable typographic signature and repeat it everywhere |
| Palette | One accent (teal #18b79f) on black/white, never more | Discipline: our blue and orange already exist; stop there |
| Cadence | One essay every Tuesday, no exceptions; daily presence on social | The fixed weekly slot is the product. Subscribers set their clock by it |
| Voice | Expert-casual, literary titles ("A Requiem For a Beam"), witty subtitles, ~1,200-word three-act essays, stats serve narrative | Title craft and rhythm, adapted to a data-native voice |
| Revenue | Brand partnerships (Kalshi), merch, free newsletter | Partnerships become viable at ~5K followers; our paid tier remains the primary engine |

## 2. Positioning

**halfpast*noon is a love letter to basketball. Second Bounce is a lie detector for it.**

One line: *"A prediction engine that shows its work."*

The brand promise: every claim traceable, every miss published, every number
walk-forward honest. The 73.5→70.6 correction isn't an embarrassment, it's the
founding myth. Nobody else in NBA media voluntarily downgrades their own record.

## 3. The signature motif: the receipt

Their asterisk, our receipt stamp. A monospaced, timestamped accuracy line that
appears on every asset, always current, always reproducible from the public log:

```
[ 70.6% · 657 games · as of 07/01/2026 · verified walk-forward ]
```

- Rendered in monospace (Consolas/IBM Plex Mono) — the "machine voice."
- Generated programmatically from `prediction_tracking.csv`, never typed by hand.
- Appears: footer banner of every post, X bio, site footer, video end cards.
- In-season it updates daily, which quietly proves the operation is alive.

**Second signature: "the model" as a character.** The engine is referred to in
third person, with dry affection: "the model still believes in the Kings, which
is its most human quality." Human writes, machine predicts, both are named.

## 4. Visual identity

| Token | Value | Use |
|---|---|---|
| Night navy | `#0f1623` / `#080c14` | Site, dark social graphics |
| Paper | `#fdfdfe` | Newsletter surfaces, light graphics |
| Signal blue | `#4b8bf4` (dark) / `#2a78d6` (light) | The data color: charts, links, accents |
| Pick orange | `#f8a100` | The pick. Reserved for what the model chooses, nothing else |
| Ink | `#182130` | Text on light |
| Receipt gray | `#898781` | The monospace receipt stamp |

- **Logo:** the glowing glass basketball (circle crop) is the avatar everywhere.
- **Wordmark:** SECOND BOUNCE in the UI sans, with a small blue bounce arc under
  "BOUNCE" (first bounce big, second bounce smaller: the physics of the name).
- **Typography:** Inter/Segoe for everything; monospace ONLY for the receipt and
  stat callouts. No serif, no display fonts.
- **Imagery:** charts are the default imagery, always in the house style (light
  surface, signal blue, direct labels). The dataviz consistency is the aesthetic.
- **Player cards (the one exception to no-photography):** NBA.com headshots run
  through the signature treatment in `scripts/generate_player_card.py`: brand
  duotone (navy shadows, signal-blue mids, pale highlights), film grain, orange
  kicker label, hero rating, receipt stamp. Rules: **at most ONE card per post**,
  only for the post's single subject, never as decoration. The duotone is the
  signature; never use an untreated photo. (Headshots via cdn.nba.com, standard
  editorial practice for newsletters; the heavy transformation keeps it clearly
  our design language.)
- Orange is rationed: in any graphic, orange marks the model's pick and nothing
  else. Scarcity keeps it meaningful.

## 5. Voice

- Expert-casual. Assume the reader is smart, not that they know what Brier means.
- Literary titles, no colons, no numbers in titles ("The Confidence Problem",
  "What the Model Owes Utah"). Subtitles carry the hook and may use numbers.
- Stats are load-bearing but sparse: 2-4 per essay, each doing narrative work.
- We show misses with the same energy as wins. Misses are content, not damage.
- First person plural for the humans ("we"), third person for the model.
- No em dashes. No hype adjectives ("insane", "wild"). The numbers carry the drama.

## 6. Cadence (the halfpast*noon lesson, adapted)

**Offseason (now → October):**
- **Tuesday, every week: the essay.** ~1,000-1,400 words, one chart minimum.
  July slate: free-agency moves through the model's eyes, the audit story
  ("How We Caught Our Own Model Cheating" — that's a banger), engine upgrades.
- Free-agency reaction notes: short posts within 24h of major signings.
- X: 3-4/week (chart crops, receipt stamps, one-liners from the model).
- **September: the countdown.** 30 teams in 30 days, one preseason rating/day.

**In season:**
- Daily: automated picks post (site + X graphic), short.
- **Monday: the receipt.** Last week's record, best call, worst miss, one chart.
- Tuesday essay continues (analysis of what the model sees that the discourse doesn't).

## 7. Audio & video (ElevenLabs Creator, commercial license)

This is our "music curation" equivalent: a production-quality layer competitors
of our size don't have.

- **The Voice of the Model:** design ONE fixed ElevenLabs voice (calm, dry,
  slightly amused analyst) and never change it. It reads the weekly essay
  (Substack voiceover upload) and the daily line in season.
- **60-second receipts:** weekly X/IG video: house-style charts animated as
  slides, model-voice narration, ElevenLabs music bed. Fully scriptable from
  the tracking data.
- Podcast feed (Substack native) once the weekly narration is routine.
- Rule: the synthetic voice is always presented AS the model's voice, never as
  a fake human. On-brand (machine with receipts), and honest.

## 8. What we deliberately do NOT copy

- The asterisk, the lowercase wordmark, the timestamp gimmick (theirs).
- Culture/fashion/music coverage. We are the numbers desk, not the culture desk.
- Merch (revisit at 5K+ audience).
- Their monetization (partnerships-first). Ours is paid-tier-first; partnerships
  become a bonus channel once X + Substack have real reach.

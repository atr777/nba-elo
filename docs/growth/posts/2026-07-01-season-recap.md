# We Predicted Every NBA Game for a Season. Here's the Receipt.

Last October, we turned on a prediction engine and let it call every NBA game, every day, in public. No cherry-picking, no deleted posts, no "we had a feeling" hindsight. Every pick was logged with a timestamp and a confidence score before tip-off, and every result was recorded next to it — right or wrong.

The season is over. Here's how it went.

## The headline numbers

- **73.5% accuracy across 657 tracked games** (483 correct)
- When the model was confident — a win probability of 75% or higher — it went **86.1% over 273 games**
- In close matchups (teams within 30 rating points), where every game is basically a coin flip, it still hit **63.8%**
- Longest streak of consecutive correct picks: **24 games**
- It picked the underdog 90 times and was right on 60% of those calls

For context: picking the home team every night gets you roughly 55%. Most public prediction models live in the 63–67% range. 73.5% over a full season is the kind of number we'd be skeptical of too — which is exactly why the full game-by-game log is public.

## What is this thing?

Second Bounce runs on a hybrid ELO engine — the same rating framework used in chess, extended for the NBA. Every team carries a rating that rises and falls with each result, weighted by margin of victory and opponent strength. On top of that sits a player layer: individual ratings that capture what happens when a star sits, gets traded, or goes on a heater.

Each game day, the engine blends team strength, player availability, rest and travel fatigue, recent form, and home court into a single win probability for every matchup. Then it publishes the picks and lives with the consequences.

## The honest part: we got better as we went

The season wasn't one smooth 73%. It was a climb:

- **December:** 63.7% — respectable, but we knew something was off
- **January:** 60.9% — the low point. Time to dig.
- **March:** **81.2%** — after we found and fixed a bug that was silently zeroing out home-court advantage in the final output, plus a retrain of the scoring model
- **April:** **77.8%** — sustained, not a hot streak
- **Playoffs:** **80%** across 20 tracked games

(You'll also notice a tracking gap in February — our old update pipeline died and games went unlogged until the new automated system came online in mid-March. The lesson: the model was never the fragile part. The infrastructure was. That's fixed — it now runs on a server that updates itself five times a day without anyone touching it.)

We're telling you about the bug and the gap for one reason: a prediction account that never shows you its misses is a betting tout, not a model. We're the other thing.

## The misses we still think about

The model's three most confident wrong calls of the season, in all their glory:

- Gave Oklahoma City **90%** at home against Phoenix. The Suns won by 32.
- Gave Denver **90%** at home against Minnesota in April. Wolves stole it 119–114.
- Gave Detroit **90%** on the road in Utah on December 26. The Jazz — the Jazz! — won 131–129.

Basketball remains undefeated at humbling math. That's why the confidence number is on every pick: an 90% call losing isn't the model being broken, it's the 1-in-10 showing up on schedule. Over the full season, our high-confidence picks won at almost exactly the rate the probabilities promised.

## What happens now

The 2026-27 season tips off in late October. Between now and then, Second Bounce will cover:

- **Free agency, through the model's eyes** — every major signing and trade, translated into rating changes: who actually got better, and by how many points per 100
- **The offseason engine upgrades** — what we're improving after a full season of live fire, explained in plain English
- **Preseason ratings for all 30 teams** — a September countdown series, one team per day, ending at opening night

When the games start, this newsletter delivers picks every single game day — with confidence scores, and with the running accuracy tally right there in the open.

**Subscribe free and you'll have the model's read on every big offseason move before your group chat does.**

---

*Second Bounce is a fully automated NBA prediction engine with a public track record. The methodology and full prediction log live at [our tracking site](https://atr777.github.io/nba-predictions/). Follow [@SecondBounceNBA](https://x.com/SecondBounceNBA) for daily picks in season.*

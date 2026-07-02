# We Predicted Every NBA Game for a Season. Here's the Receipt.

Last October, we turned on a prediction engine and let it call every NBA game, every day, in public. No cherry-picking, no deleted posts, no "we had a feeling" hindsight. Every pick was logged with a timestamp and a confidence score before tip-off, and every result was recorded next to it, right or wrong.

The season is over. Here's how it went.

![2025-26 season: 73.5% accuracy, 483 of 657 tracked games](https://substack-post-media.s3.amazonaws.com/public/images/f5880b22-e920-49db-9bf4-2e27e4feca8c_1456x680.jpeg)

For context: picking the home team every night gets you roughly 55%. Most public prediction models live in the 63 to 67% range. A 73.5% season is the kind of number we'd be skeptical of too, which is exactly why the full game-by-game log is public.

## What is this thing?

Second Bounce runs on a hybrid ELO engine, the same rating framework used in chess, extended for the NBA. Every team carries a rating that rises and falls with each result, weighted by margin of victory and opponent strength. On top of that sits a player layer: individual ratings that capture what happens when a star sits, gets traded, or goes on a heater.

Each game day, the engine blends team strength, player availability, rest and travel fatigue, recent form, and home court into a single win probability for every matchup. Then it publishes the picks and lives with the consequences.

## The honest part: we got better as we went

The season wasn't one smooth 73%. It was a climb.

![Monthly accuracy: 64% in December, 61% in January, then 81% in March, 78% in April, 80% in the playoffs](https://substack-post-media.s3.amazonaws.com/public/images/c5ba740b-764b-4d53-bca6-744ff72061e3_1456x819.jpeg)

January was the low point, and it forced us to dig. What we found was a bug that had been silently zeroing out home-court advantage in the model's final output. We fixed it in early March, retrained the scoring model on a much bigger dataset, and the engine jumped from a low-60s predictor to a high-70s one. That level held through April and through 20 tracked playoff games.

You'll also notice the gap in February: our old update pipeline died and games went unlogged until the new automated system came online in mid-March. The lesson was that the model was never the fragile part. The infrastructure was. That's fixed. It now runs on a server that updates itself five times a day without anyone touching it.

We're telling you about the bug and the gap for one reason: a prediction account that never shows you its misses is a betting tout, not a model. We're the other thing.

## The number we're proudest of

Accuracy is nice. Calibration is what separates a real model from a guy with takes. When we attach a confidence score to a pick, that number is supposed to mean something, and over a full season it did:

![Calibration chart: at every confidence level, the actual win rate matched or beat the model's stated probability](https://substack-post-media.s3.amazonaws.com/public/images/23e456b3-469d-4dd0-baf8-7d2ced1df9b4_1456x860.jpeg)

At every single confidence level, the model delivered what it promised or better. When it said "this is basically a coin flip," it went 60%. When it said 90%+, it won 93% of the time. That's the whole product in one chart.

## The misses we still think about

The model's three most confident wrong calls of the season, in all their glory:

- Gave Oklahoma City **90%** at home against Phoenix. The Suns won by 32.
- Gave Denver **90%** at home against Minnesota in April. The Wolves stole it 119 to 114.
- Gave Detroit **90%** on the road in Utah on December 26. The Jazz, the Jazz!, won 131 to 129.

Basketball remains undefeated at humbling math. That's why the confidence number is on every pick: a 90% call losing isn't the model breaking, it's the 1-in-10 showing up on schedule.

## What happens now

The 2026-27 season tips off in late October. Between now and then, Second Bounce will cover:

- **Free agency, through the model's eyes.** Every major signing and trade, translated into rating changes: who actually got better, and by how much.
- **The offseason engine upgrades.** What we're improving after a full season of live fire, explained in plain English.
- **Preseason ratings for all 30 teams.** A September countdown series, one team per day, ending at opening night.

When the games start, this newsletter delivers picks every single game day, with confidence scores, and with the running accuracy tally right there in the open.

**Subscribe free and you'll have the model's read on every big offseason move before your group chat does.**

![Second Bounce: NBA predictions, powered by ELO](https://substack-post-media.s3.amazonaws.com/public/images/222675cb-3409-42e7-84eb-68a0c651ad89_1456x420.jpeg)

[Full prediction log and methodology](https://atr777.github.io/nba-predictions/) · [Follow @SecondBounceNBA on X](https://x.com/SecondBounceNBA)

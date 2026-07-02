# We Predicted Every NBA Game for a Season. Here's the Receipt.

Last October, we turned on a prediction engine and let it call every NBA game, every day, in public. No cherry-picking, no deleted posts, no "we had a feeling" hindsight. Every game got a pick and a confidence score, and every result was recorded next to it, right or wrong.

The season is over. Here's how it went.

![2025-26 season: 70.6% accuracy, 464 of 657 tracked games](https://substack-post-media.s3.amazonaws.com/public/images/02b93b8d-b09d-4794-8484-382f07a5b671_1456x680.jpeg)

For context: picking the home team every night gets you roughly 55%. Most public prediction models live in the 63 to 67% range. A 70.6% season clears both bars, and the full game-by-game log is public.

One more thing about that number. While preparing this recap we audited our own tracker and caught it flattering the model: a subtle data leak had inflated the record to 73.5%. We rebuilt the whole season as a strict walk-forward replay, and 70.6% is what survives. It's the only number you'll ever see us quote. A prediction outfit that quietly publishes its most flattering math is a tout. We're the other thing.

## What is this thing?

Second Bounce runs on a hybrid ELO engine, the same rating framework used in chess, extended for the NBA. Every team carries a rating that rises and falls with each result, weighted by margin of victory and opponent strength. On top of that sits a player layer: individual ratings that capture what happens when a star sits, gets traded, or goes on a heater.

Each game day, the engine blends team strength, player availability, rest and travel fatigue, recent form, and home court into a single win probability for every matchup. Then it publishes the picks and lives with the consequences.

## The honest part: we got better as we went

The season wasn't one smooth 70%. It was a climb.

![Monthly accuracy: 61% through December, 63% in January, then 77% in March, 74% in April, 80% in the playoffs](https://substack-post-media.s3.amazonaws.com/public/images/2f545e42-b11e-4e04-a487-05af3dfb970a_1456x819.jpeg)

January forced us to dig, and what we found was a bug silently zeroing out home-court advantage in the final output. We fixed it in early March and retrained the scoring model on a much bigger dataset. The engine jumped from a low-60s predictor to a mid-70s one, held that level through April, and went 16 for 20 in tracked playoff games.

You'll also notice the gap in February: our old update pipeline died and games went unlogged until the new automated system came online in mid-March. Between that and the tracking audit above, the lesson of season one was blunt: the model was never the fragile part, the bookkeeping was. Both are rebuilt.

## Do the confidence scores mean anything?

Accuracy is one thing. Calibration, whether a "75% confident" pick actually wins about 75% of the time, is what separates a model from a guy with takes. Here's ours, warts included:

![Calibration chart: actual win rate vs stated probability by confidence bucket](https://substack-post-media.s3.amazonaws.com/public/images/9321ff53-0200-4bef-a842-5697eb6ecc37_1456x860.jpeg)

The middle of the range is solid: picks in the 60 to 80% buckets delivered right around what they promised, and coin-flip games landed above promise. The flaw is at the top: picks stated at 90%+ won 81% of the time, not 90. The model knows who's better; it's still learning how sure to be. Tightening that top end is literally on our offseason engineering list, and you'll be able to check next season whether we did it.

## The season in five receipts

![Five moments: the 20-game streak, the 16/20 playoff run, the Boston-Philly humbling, the OKC blowout miss, and the audit](https://substack-post-media.s3.amazonaws.com/public/images/36503e95-bac5-4d4c-be3d-d139afe22561_1456x340.jpeg)

Basketball remains undefeated at humbling math. A 90% call losing isn't the model breaking, it's the 1-in-10 showing up on schedule (ask Denver, who the model gave 90% at home before Minnesota stole it 119 to 114). But several of those clustered at the top is exactly why "overconfident up top" is our number one calibration fix.

## What happens now

The 2026-27 season tips off in late October. Between now and then, Second Bounce will cover:

- **Free agency, through the model's eyes.** Every major signing and trade, translated into rating changes: who actually got better, and by how much.
- **The offseason engine upgrades.** We've already found real ones: our audit showed two "features" that were quietly costing accuracy, and removing them alone is worth almost a full percentage point. That story is coming in its own post.
- **Preseason ratings for all 30 teams.** A September countdown series, one team per day, ending at opening night.

When the games start, this newsletter delivers picks every single game day, with confidence scores, and with the running accuracy tally right there in the open.

**Subscribe free and you'll have the model's read on every big offseason move before your group chat does.**

![Second Bounce: NBA predictions that show their work](https://substack-post-media.s3.amazonaws.com/public/images/48f4bf14-faa4-4781-8061-93f3deaf3aa5_1456x420.jpeg)

[Full prediction log and methodology](https://atr777.github.io/nba-predictions/) · [Follow @SecondBounceNBA on X](https://x.com/SecondBounceNBA)

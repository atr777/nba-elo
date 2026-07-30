# Posting pack: the correction essay (2026-07-29)

Post: `docs/growth/posts/2026-07-29-how-we-caught-our-own-model-cheating.md`
Substack draft: id **209055629** (the earlier 209054364 was deleted, its images were
broken and its footer rendered twice).
Graphics, both already uploaded into the draft as PNG:
`posts/assets/correction_hero.png` (header) and
`posts/assets/leakage_cumulative_accuracy.png` (the two-line chart).
Narration: `posts/assets/2026-07-29-how-we-caught-our-own-model-cheating-voice-of-the-model.mp3`,
also copied to `Desktop/SecondBounce_Brand/`. STT-verified word for word, 623 of 623.
Substack URL: fill in after Aaron publishes, then update the note in the queue.

**Strategy note.** Written for engineers and analysts, not NBA fans, because at one
subscriber we have no fanbase to lose and the leakage story is the only asset we own
that travels outside basketball. Zero restacks across ten notes says broadcasting
does not work for us yet; the ask in each of these is a reply or a check, not a read.

**Aaron: post the THREAD first.** The single tweets are follow-ups for later days,
not alternatives. Space them at least a day apart.

---

## 1. The thread (main asset, post this one)

**1/**
```
We published a 73.5% NBA prediction record last season.

Then we audited our own tracker and cut it to 70.6%.

Same model. Same 657 games. The bug was in how we were measuring, and it's the kind
that passes code review.
```

**2/** + `leakage_cumulative_accuracy.png`
```
Both lines are the same 657 games.

The only difference is when the model was allowed to see each result.

They tangle early, separate around game 200, and never come back.
```

**3/**
```
Our ratings are Elo-style. Every result nudges a team's number, and a prediction
compares two numbers at a moment in time.

"Moment" is the word doing the damage.
```

**4/**
```
The old tracker walked back through the season and asked the model who'd win each
completed game.

But it asked today's ratings. Which had already absorbed the result of the game it
was asking about.

Tiny. Toward the right answer. 657 times.
```

**5/**
```
Nothing crashed. No error in any log.

The code did what it said. The arithmetic was right. The games and outcomes were
real.

The flaw isn't in a line of that function. It's in the order the lines run relative
to time.
```

**6/**
```
The detail that surprised us: the leak didn't lift everything uniformly.

48 games flipped wrong to right.
29 flipped right to wrong.

77 games moved. Net: 19 wins we hadn't earned. A leak doesn't need to be big. It
needs to be systematic.
```

**7/**
```
Fix wasn't a better audit script. It was refusing to reconstruct the past at all.

Picks are now written down before tip-off with a timestamp, graded after the final,
and never recomputed.

A prediction you can recompute later is an opinion with a date on it.
```

**8/**
```
Full write-up, including the chart and the harness we used:

[POST URL]

If you publish a forecasting record, the question worth asking isn't about your
model. It's when your predictions were written down, and who could check.
```

---

## 2. Single tweets (later days, one at a time)

**A. The general lesson, no basketball**
```
If you evaluate a forecast by reconstructing it after the fact, you're trusting
yourself to rebuild a past state of knowledge while sitting on top of the answers.

We failed that test by 19 games and 2.9 percentage points. Write predictions down
when you make them.
```

**B. The uncomfortable comparison**
```
Our honest NBA accuracy is 70.6%. Vegas closing lines land near 73%.

We're behind the market and we say so.

If a model claims to beat it comfortably, ask when its picks were logged.
```

**C. The invitation (evergreen, reusable)**
```
We cut our own published accuracy from 73.5% to 70.6% after catching a leak in our
tracker.

Every pick since is logged before tip-off, graded after, misses left in.

The log is public: atr777.github.io/nba-predictions
```

---

## 3. Substack Note (add to the queue once the post URL exists)

Attach the post as a `link:` card, not an image. Suggested text:

```
We published a 73.5% accuracy record, then audited our own tracker and cut it to
70.6%. The bug: it asked each game's outcome from ratings that had already absorbed
that outcome. 48 games flipped one way, 29 the other, net 19 wins we hadn't earned.
```

---

## Aaron's checklist

1. Read the post. It names our own error in public, so you should be comfortable
   with every line before it ships.
2. **Attach the audio.** In the Substack editor: `+` menu, then Audio, then upload
   `2026-07-29-how-we-caught-our-own-model-cheating-voice-of-the-model.mp3` from
   `Desktop/SecondBounce_Brand/`. Both images are already in the draft body.
3. Publish the Substack draft (id 209055629).
4. Paste the live URL back to me. I'll fill `[POST URL]` in tweet 8 and add the
   Note to the queue with a link card.
5. Post thread 1 on X. Best window for this audience is a weekday morning ET.
6. When someone replies with a technical question, answer it yourself rather than
   letting it sit. Replies are the only thing that has moved our numbers at all.

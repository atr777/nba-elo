# Substack profile copy: tagline and welcome email

**Why this file exists.** Checked the publication settings on 2026-07-30 and found
`welcome_email_body` **empty** and `hero_text` **empty**. So every new subscriber gets
a subject line ("Welcome to Second Bounce") and a blank email, and the landing page has
no tagline under the title. At one subscriber, the first impression is the most
expensive thing we own to waste.

Flagged by the growth case study Aaron sent, whose 15-minute profile checklist includes
a warm welcome email that links to the best past piece. See
`docs/research/2026-07-30-substack-growth-case-study.md`.

**Aaron applies these.** They are outbound copy that goes to every future subscriber,
so they are drafted here rather than set silently by me. Click-by-click is at the
bottom. No em dashes in either, per house rules.

---

## 1. Tagline (`hero_text`)

Shown under the publication name on the landing page. Keep it short; it gets truncated.

```
NBA predictions with a public track record. Every pick logged before tip-off, graded after the final, misses left in.
```

Shorter alternative if it wraps badly:

```
NBA predictions, logged before tip-off and graded in public. 70.6% across 657 games.
```

---

## 2. Welcome email

Subject is already set to "Welcome to Second Bounce" and is fine. This is the body.

```
Thanks for subscribing.

Here is what you signed up for, in one paragraph.

Second Bounce runs an ELO-style model that predicts NBA games. Every pick is
published before tip-off with a probability attached, graded after the final whistle,
and never quietly edited afterwards. Last season it called 70.6% of 657 games
correctly. That number is lower than the one we originally published, which is the
best thing about it.

If you read one thing first, read that story:

How We Caught Our Own Model Cheating
https://secondbounce.substack.com/p/how-we-caught-our-own-model-cheating

We published a 73.5% record, audited our own tracker, found it had been feeding the
model answers, and cut the number. 19 of those wins were not real. The post walks
through the bug and how we found it.

Two things you can expect. Numbers you can check, because the full game-by-game log is
public at atr777.github.io/nba-predictions. And misses reported with the same energy as
wins, because a prediction account that hides its bad nights is selling something else.

No betting picks. Not now, not later.

Aaron
Second Bounce
```

**Note on the 73.5% figure.** It appears here deliberately, the same exception the
correction essay gets in `config/metrics.yaml`. The retracted number is the subject of
the sentence, not a claim about our record. Do not reuse this phrasing anywhere the
number is not being explicitly withdrawn.

---

## Aaron: where to put these

**Tagline**
1. Go to https://secondbounce.substack.com/publish/settings
2. Under **Basics**, find the short description or tagline field under the publication
   name.
3. Paste section 1. Save.

**Welcome email**
1. Same settings page, find **Emails** in the left menu (sometimes under
   "Subscriber welcome page" / "Welcome email").
2. Paste section 2 into the body. Leave the subject as it is.
3. Make the post title a real link on the URL beneath it if the editor allows.
4. Save, then use "send test email" to yourself if the option is there. Worth doing
   once: it is the only way to see what a new subscriber actually receives.

**Also worth 2 minutes while you are in there:** the publication has no logo or cover
photo set (`logo_url` and `cover_photo_url` are both empty). We already have art that
fits: `pages/assets/og_card.png` for a cover, and the ball mark at
`docs/growth/posts/assets/logo_substack.png` for a logo.

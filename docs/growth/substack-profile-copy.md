# Substack profile: what is actually missing, and the copy for it

**Corrected 2026-07-30.** An earlier version of this file claimed four gaps: empty
tagline, empty welcome email, no logo, no cover photo. **Three of those were wrong.**

I read them from `/api/v1/publication`, where `hero_text`, `logo_url` and
`cover_photo_url` are indeed empty. But the publication runs with
**`is_personal_mode: true`**, which means it renders from Aaron's *personal profile*
fields instead. Checked against the live page: the tagline text is on it, the ball mark
appears as the logo, and a header image is present. Nothing to fix.

**Lesson for next time: verify a "missing" setting against the rendered page before
acting on it.** An empty field in one API object is not the same as a gap on the site.

---

## The one real item: the welcome email for FREE subscribers

Substack keeps **five** separate welcome emails. The one that matters for us is the
free-subscriber one, because we have no paid tier and never will
([[substack-paid-tier-blocked]]).

| Substack label | Field | Relevant to us? |
|---|---|---|
| Welcome email to **free** subscribers | `unfinished_subscription_email_content` | **YES, this one** |
| Welcome email to paid subscribers | `welcome_email_content` | No, no paid tier |
| Welcome email to founding subscribers | `founding_tier_welcome_email_content` | No |
| Welcome email to imported subscribers | `imported_welcome_email_content` | No |
| Paid expiry / renewal emails | various | No |

Note the trap: the field named `welcome_email_content`, the one you would reach for, is
the **paid** email. It would never fire. The free one is oddly named
`unfinished_subscription_email_content`.

**I could not confirm whether it currently has content.** Its value is loaded by the
editor rather than sent with the settings page, so the only way to know is to open it.
If there is already something reasonable in there, leave it.

### Direct link

```
https://secondbounce.substack.com/publish/settings/edit?title=Welcome%20email%20to%20free%20subscribers&bodyField=unfinished_subscription_email_content&titleField=unfinished_subscription_email_subject&titlePlaceholder=Email%20subject...&redirect=https%3A%2F%2Fsecondbounce.substack.com%2Fpublish%2Fsettings
```

### Subject

```
Welcome to Second Bounce
```

### Body

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

**On the 73.5% figure:** it appears deliberately, as the number being withdrawn, which
is the same exception the correction essay carries in `config/metrics.yaml`. Do not
reuse this phrasing anywhere the number is not explicitly being retracted.

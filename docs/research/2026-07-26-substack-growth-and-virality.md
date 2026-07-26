# Substack Growth and Virality: What Actually Moves the Number

**2026-07-26.** Written straight after the strategic review, which concluded that
audience size is now our only revenue metric (we stay free and pursue sponsorship,
Aaron 2026-07-26). So this document is about one question: **how does a
three-digit publication in a data niche actually grow on Substack in 2026?**

## 1. The two facts that should reshape our plan

**a) Substack's own network drives ~50% of all new subscriptions.**
Recommendations plus the app account for **half of new free subs and a quarter of
new paid subs** platform-wide, and 32 million new subscribers came from inside the
app in a single three-month stretch of 2025
([Disrupt](https://disruptmarketing.co/blog/substack-growth-monetisation-guide/),
[Substack](https://on.substack.com/cp/142007285)). Below 10k subscribers,
**recommendations, Notes engagement, and collaboration outrank everything else,
including niche choice**
([buildtolaunch](https://buildtolaunch.substack.com/p/how-to-grow-substack-from-zero-in-2026)).

We have been treating Substack as a publishing destination and X as the growth
engine. That is backwards for our size. **The growth engine is inside Substack.**

**b) The Notes feed stopped being follower-based in late 2025.**
The feed no longer prioritizes people you follow; most of what a reader sees comes
from creators they have never followed
([Escape the Cubicle](https://escapethecubicle.substack.com/p/how-i-hacked-the-new-notes-algorithm),
[Really Good Business Ideas](https://www.reallygoodbusinessideas.com/p/substack-notes-algorithm)).

This is the single most favourable structural fact available to us. **Reach is no
longer gated on follower count**, so our tiny following is not the handicap it
would be on X. A good note from a 200-subscriber publication can be shown to cold
readers. That is why Notes automation was the right thing to build first.

## 2. What the data says about virality (and why we should not chase it)

An analysis of 1.3 million notes found roughly **135 genuine viral outliers, about
one in ten thousand** ([Online Writing Club](https://www.onlinewritingclub.com/p/what-makes-a-substack-note-go-viral)).
Multiple practitioner accounts converge on the same conclusion: **steady posting
outgrew the occasional viral hit**, and creators who did not restack or interact
stalled regardless of quality.

So the honest model of growth here is not "write a banger." It is:
consistent volume × visual format × in-niche engagement × recommendations.
Virality is a bonus draw on a ticket you buy by posting.

What does correlate with performance:

| Signal | Finding | Our position |
|---|---|---|
| **Images/video** | Notes with a photo or video beat text-only, and Substack is actively pushing multimedia | **We have a chart pipeline. This is our edge.** Our current drip is text-only, which is the main gap in what I built today. |
| **Observational, specific, human** | Casual and real beats polished and comprehensive; "AI can write ten tips in seconds, your story cannot be copied" | Our model-as-character voice already fits. Avoid press-release cadence. |
| **Restacking in-niche** | Trains the algorithm on audience overlap, creating a "virtuous cycle" | **Not happening at all today.** Pure Aaron action, roughly 5 minutes a day. |
| **Consistency** | Beats experimentation every time | Our drip now enforces this mechanically. |
| **External referrers** | X and LinkedIn are the two most cited off-platform drivers | X is manual and thin. LinkedIn is untouched and is plausibly a better fit for a "we audit our own model" story than for basketball takes. |

Open rates on Substack average ~44%, about double the email industry norm, so
subscribers acquired here are worth more than a generic list.

## 3. Why this niche suits the mechanics unusually well

Most creators struggle to post visual notes daily because making a good graphic is
work. **We generate them automatically.** In season the engine produces, every
single day, without human effort:

- a slate of pre-tip predictions with stated confidence
- yesterday's graded results, right and wrong
- rating movements, streaks, upsets
- a running public accuracy figure

That is roughly 1,300 games a year of native, visual, timestamped, falsifiable
content. The "receipt" motif in BRAND.md is not just an aesthetic; it is
**inherently screenshot-shaped**, which is the format the 2026 algorithm rewards.

The structural insight: **our automation lets us execute the 2026 Notes playbook at
a volume and consistency solo creators cannot match.** That, not model accuracy, is
our realistic path to an audience. It also means the drip built today is the
highest-leverage code in the project right now.

## 4. What I would do, concretely

**Highest leverage first, and note that the top item is not code.**

1. **Get recommended by adjacent publications.** This is half of platform growth
   and we are getting none of it. Target basketball and sports-data Substacks of
   comparable or moderately larger size and offer reciprocal recommendations. The
   pitch writes itself: "we run a public, audited NBA prediction record; happy to
   recommend you." **This is relationship work only Aaron can do**, and it is
   probably worth more than every engineering item combined. 10 to 20 targeted
   asks is a realistic first pass.
2. **Restack and comment in-niche daily.** Five minutes, trains the algorithm on
   audience overlap, and the research is unanimous that skipping it stalls growth.
   Also Aaron only, since it is engagement from a human account.
3. **Add image support to the Notes drip (v2).** Endpoints are already mapped:
   `POST /api/v1/image` (upload) and `POST /api/v1/comment/attachment`, then
   reference the attachment when creating the note. This converts our chart
   pipeline into the format the algorithm favours. **This is the top code item.**
4. **In season, wire the daily receipt into the drip.** One automatic visual note
   per day: yesterday's calls, graded. This is the flywheel, and it needs no
   writing.
5. **Write the audit essay** ("How We Caught Our Own Model Cheating"). Still
   unwritten, still our most linkable asset, and exactly the kind of story-driven
   piece the platform rewards over tips.
6. **Test LinkedIn** with the methodology/self-audit angle. It is one of the two
   cited external drivers and costs one repost of each essay.
7. **Do not chase virality.** At one in ten thousand, planning for it is planning
   to be disappointed. Buy tickets by posting consistently.

## 5. What this changes about the drip I built today

- **Text-only is a real limitation**, not a cosmetic one. Item 3 above.
- **2 notes/day and 5 hours apart is a reasonable starting cadence** and sits
  inside the platform norm of 1 to 3. Worth raising once image notes work and we
  can see which formats land.
- **The queue should carry more observational notes and fewer announcements.**
  Of the 12 seeded, most are claims and stats. The research says the human,
  specific, slightly-off-angle ones travel further. Worth rebalancing when Aaron
  approves the first batch.
- **Nothing about virality justifies removing the approval gate.** Volume without
  judgement is how a numbers account becomes noise.

## 6. Uncertainties

- The deepest quantitative note analysis is paywalled; I used its free findings
  (the one-in-ten-thousand rate) and corroborated tactics across several
  practitioner sources rather than paying for one blogger's cut.
- Practitioner growth claims ("1,000 subs in 60 days") are self-reported and
  unaudited. I treat the direction as informative and the magnitudes as marketing.
- We still cannot measure our own subscriber count, so we will not be able to
  attribute any of this until that is fixed. It remains the first thing to solve.

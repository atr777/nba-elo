# Strategic Review: Position, Competitors, and the Path to Revenue

**2026-07-26.** Written at Aaron's request, roughly 12 weeks before opening night
(Oct 21, 2026). Everything here is measured from our own data or cited to a
source. Where I am uncertain I say so.

---

## 1. The headline: the revenue plan is blocked, and nobody had checked

`docs/SOP_SEASON_OPERATIONS.md` says: **"Late Sept, list >= 300: activate paid
tier: $6/mo, $50/yr, $100 founding."**

That cannot happen as written.

- Substack's paid subscriptions run **exclusively through Stripe**
  ([Substack/Stripe](https://stripe.com/en-lt/customers/substack), and Substack's
  own support docs confirm the requirement).
- **Stripe does not support businesses in Guatemala.** Verified on
  [stripe.com/global](https://stripe.com/global): in Latin America the supported
  list is **Brazil and Mexico only**. This matches the standing note in project
  memory (`user_location_guatemala.md`).

So the paid button does not exist for Aaron today. This is the single most
important item in this document, because the fix has **weeks of lead time** (a US
entity plus an EIN, if that is the route) and it now sits on the critical path.
Everything else in the monetization plan is downstream of it.

Options, roughly by speed:

| Route | Lead time | Notes |
|---|---|---|
| **PayPal Subscriptions**, off-Substack | days | PayPal Business is available in Guatemala. Fastest first dollar. Manual access control, no native paywall. |
| **Merchant of Record** (Paddle, Lemon Squeezy) | 1-3 weeks | They are the seller of record and pay out to non-Stripe countries. Verify Guatemala payout at signup. Pairs with Ghost or a gated site, not with Substack's paywall. |
| **US LLC + EIN + Stripe** (incl. Stripe Atlas) | 4-10 weeks | The only route that unlocks **native Substack paid**. EIN for a foreign owner without an SSN is the slow step. Real cost and real paperwork. |
| **Stay free, sell sponsorship** | now | The halfpast\*noon model. Realistically needs ~5k audience before anyone pays. |

**My recommendation: decouple the two jobs.** Keep Substack as the free growth
engine (it is good at that and the list is portable). Do not bet the revenue
model on Substack's paywall. If Aaron wants native Substack paid, start the US
entity **this week** or it will not be ready for October.

---

## 2. Where the engine actually stands

Measured just now from `data/exports/prediction_tracking_honest.csv` (657 graded
games, logged pre-game, never recomputed):

| Metric | Us | Reference |
|---|---|---|
| Accuracy | **70.62%** | Vegas closing lines ~**73%** |
| Brier | **0.2046** | Vegas ~**0.195** |
| Always pick home | 58.30% | our floor |
| **Pick the higher raw rating, ignore home court** | **70.78%** | **beats our full model by 1 game** |

Two things follow, and they point the same direction.

**a) We are slightly behind the market, on both metrics.** Vegas is ~73% with a
Brier near 0.195 ([benchmark](https://www.seanrmoran.com/nbaplayoffpredictor/)).
A good independent public model lands near 69% / 0.199. We are in that
respectable independent band, not ahead of the market. **We should stop leading
with the raw accuracy number**, because it invites precisely the comparison we
lose. Note also that the ex-538 modeller now blends betting-market probabilities
into his own forecast, which tells you how hard the market is to beat from
ratings alone.

**b) The extra machinery is not demonstrably buying accuracy.** A trivial
baseline (higher raw ELO wins, no home advantage, no momentum, no fatigue) scores
70.78% against our 70.62%. That difference is one game out of 657, i.e. noise, so
the honest statement is "indistinguishable," not "worse." But it is the same
verdict the research docs already reached independently: the home-advantage sweep
came back flat, recalibration failed out of sample, roster-delta was subsumed by
reversion, rookie priors were a clean null. **Parameter tuning is exhausted and
the docs prove it four separate ways.**

**What we DO have, and are not selling:** the model is **well calibrated**. When
it says 80-90% it wins 79.6%. When it says 70-80% it wins 73.2%. When it says
60-70% it wins 69.7%.

| Stated confidence | Games | Actually won |
|---|---|---|
| 50-60% | 195 | 60.0% |
| 60-70% | 119 | 69.7% |
| 70-80% | 142 | 73.2% |
| 80-90% | 201 | 79.6% |

That is a real, verifiable, and genuinely uncommon property. "When we say 80%, we
mean 80%, and here is the log" is a stronger and more defensible claim than any
accuracy percentage, and it does not lose a comparison to Vegas.

**One cosmetic problem:** the site prominently displays **55.2% on close games**.
That is barely above a coin flip and it is the second number a visitor reads. It
should be reframed (close games are near-coin-flips *for everyone*, which is
itself an honest and interesting point) or de-emphasized.

---

## 3. Where the operation actually stands

| Area | State | Read |
|---|---|---|
| Engine + data pipeline | Mature. 5x daily VPS cron, self-healing box scores, 100% ingestion, one config source of truth | **Done. Genuinely good.** |
| Track record | 657 games, honest, auditable, publicly corrected | **Our real asset** |
| Content cadence | **4 posts in 26 days**, with an 18-day gap (Jul 6 to Jul 24) vs a plan of **2/week** | **This is the problem** |
| Distribution | X manual, no Notes automation (queue #7), no custom domain | Underbuilt |
| Measurement | **Subscriber count is not tracked.** The stored Substack cookie authorizes drafts but returns 403 on stats endpoints | **The gate metric is invisible** |
| Site | Live, funnel to Substack exists, credential displayed | Fine |

The pattern is unmistakable. Sessions have gone into model micro-optimization
(which the docs now prove was a dead end) while **the two things that actually
produce revenue, publishing rhythm and audience, have slipped.** BRAND.md says it
outright: "The fixed weekly slot is the product. Subscribers set their clock by
it." We are not holding the slot.

And we cannot see the one number the paid-tier gate depends on. The 300-subscriber
trigger is currently unmeasurable, and it was an arbitrary threshold to begin with
(see the math below).

---

## 4. The competitive field

**The closest competitor is the one who does exactly our product, better
credentialed.**

- **Neil Paine** (`neilpaine.substack.com`): co-creator of 538's RAPTOR, now
  publishes an **NBA Elo forecast and player ratings** on Substack with **12,000+
  subscribers**. Same artifact, same platform, more authority, a two-year head
  start. He blends FanDuel implied probabilities into his forecast.
- **Cleaning the Glass** (Ben Falk, former Sixers/Blazers front office): premium
  subscription analytics. Wins on insider credibility.
- **Thinking Basketball** (Ben Taylor): YouTube-first, books, membership. Wins on
  production and personality.
- **Dunks & Threes** (EPM) and **Inpredictable**: free public metrics/win
  probability. They are reference utilities, not newsletters.
- **Basketball Intelligence**: paid daily curation. A different lane
  (aggregation, not modelling).
- **Prediction markets** (Kalshi, Polymarket): the reason "here are my
  probabilities" is no longer scarce on its own. Anyone can read a live market.

**The 538 vacuum is real but already occupied.** 538's predictive RAPTOR was
retired and the forecast simplified; Paine stepped directly into that space. We
are not entering an empty room.

**Where that leaves us.** We do not have the best model, the best pedigree, or
the biggest audience. What we have that none of them lead with:

1. **Pre-committed, pre-game, publicly logged picks with a graded outcome for
   every single game.** Paine forecasts seasons; we call games and keep receipts.
2. **A published self-correction** (73.5 to 70.6). Nobody in this space
   voluntarily downgrades their own record. It is the founding myth and it is
   credible precisely because it cost us something.
3. **Calibration we can prove**, per the table above.
4. **Production quality** disproportionate to our size: narration in a fixed
   voice, player cards, house-style charts.

That is a transparency-and-craft brand, not an alpha brand. The positioning in
BRAND.md ("a lie detector for basketball," "a prediction engine that shows its
work") is exactly right. The mistake would be selling **edge**, because the
numbers above say we do not have a demonstrable one.

---

## 5. The monetization math, honestly

Substack conversion benchmarks: **median ~3%**, 2-5% normal, 5-8% good, and
specialist/technical niches can reach ~8%
([1](https://www.yana-g-y.com/p/substack-free-to-paid-conversion-rate),
[2](https://www.reallygoodbusinessideas.com/p/substack-average-paid-subscriber-conversion-rate)).
Substack takes 10%, payment processing ~3%.

At the planned **$6/mo** and a 3% conversion:

| Free list | Paid subs | Gross/mo | Net/mo (approx) |
|---|---|---|---|
| 300 (the SOP gate) | 9 | $54 | ~$47 |
| 1,000 | 30 | $180 | ~$156 |
| 3,000 | 90 | $540 | ~$470 |
| 5,000 | 150 | $900 | ~$783 |
| 10,000 | 300 | $1,800 | ~$1,566 |

**The 300-subscriber gate produces roughly $47/month.** That is a tip jar, not a
business, and it is worth saying plainly because "profitable by the 2026-27
season" is the stated prime directive. To net ~$1,000/mo at $6 and 3% you need
about **6,300 free subscribers**. At **$9/mo** you need about 4,200. At $9/mo and
a 5% conversion (plausible for a specialist data niche with a strong free tier),
about **2,500**.

Three consequences:

1. **$6/mo is underpriced** for a specialist data product with daily output.
   $9/mo, $79/yr, $149 founding gets to the same revenue with a third fewer
   subscribers, and a higher price signals a serious product. Comparable
   basketball analytics subscriptions sit well above $6.
2. **The bottleneck is audience, not model quality and not even payments.**
   Payments are a hard blocker, but a solved payment stack on a 300-person list
   is still $47/mo.
3. **The Oct 2026 goal should be restated.** "Profitable" at this list size is
   not reachable by opening night. A defensible October target: **paid tier
   technically live, a real founding cohort, and first revenue**, with
   meaningful money as a 2027 goal. Better to reset the definition now than to
   hit October and call a working product a failure.

---

## 6. What I would do, in order

**This week**
1. **Decide the payment rails** (section 1). If the answer involves a US entity,
   start immediately; it is the longest lead time in the entire plan.
2. **Make subscribers visible.** Either fix the API credential or Aaron pastes
   the dashboard number weekly and I log it to a CSV so growth is trackable.
   Right now we are flying blind on our only revenue-linked KPI.
3. **Freeze model work.** Declare the engine feature-complete for 2026-27 except
   data integrity, the October roster boundary, and the CDN-fallback check
   already flagged for opening night. The docs justify this four times over;
   further tuning has negative expected value against the calendar.

**August**
4. **Hold the Tuesday slot, without exception.** It is the product. Write and
   bank posts in advance so news droughts cannot break the streak.
5. **Write "How We Caught Our Own Model Cheating."** BRAND.md flagged it as the
   banger and it is still unwritten; the correction currently exists as one
   paragraph inside the season recap. As a standalone piece it is our single best
   acquisition asset: it is the most linkable, most shareable, most
   trust-building thing we own, and no competitor can copy it.
6. **Reposition the credential** from raw accuracy to calibration plus
   auditability. Keep quoting 70.6% when asked (never 73.5%), but lead with "every
   pick logged before tip, graded after, nothing recomputed, and when we say 80%
   we win 80%."
7. **Ship Notes auto-posting** (queue #7). It is the only remaining engineering
   item that touches growth, which makes it the only one worth doing now.

**September**
8. **Batch the 30-teams-in-30-days countdown before the month starts.** It is the
   scheduled audience-builder and it must not compete with in-season reaction
   work for session time.
9. **Launch the founding tier** at the corrected price, on working rails, framed
   with scarcity rather than a subscriber threshold we cannot measure.

**Distribution, ongoing (the actual constraint)**
10. Get in front of existing audiences instead of waiting: r/nba and
    r/nbadiscussion on the corrections story, basketball analytics podcasts, and
    a citable public preseason table (that is how Paine earns inbound links).
    Nothing above matters if the list stays at three digits.

---

## 7. What I am not certain about

- **Subscriber count and open rate.** Unmeasured, so every conversion projection
  here is a model, not a forecast. Get this number first.
- **X follower count.** No API, unverifiable from here.
- **Whether Substack's newer in-app payments change the Stripe dependency** for
  an unsupported-country writer. Worth 20 minutes with Substack support before
  committing to a US entity.
- **Paine's exact pricing.** Not visible in search; his subscriber count is
  public (12k+) but the paid split is not.
- **Whether $9/mo clears in this niche.** It is a judgement call from adjacent
  products, not a tested price.

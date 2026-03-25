# Research Report — 2026-03-25

## Question / Trigger
How do leading sports prediction sites communicate expected point spread and confidence to casual fans — people who have never seen a "-6" betting line — and what specific UI patterns are worth borrowing for a dark-themed NBA prediction card?

## Current NBA_ELO State (Baseline for Comparison)

The live prediction card in `templates/predict_today.html` and the design prototype in `docs/design/quarter_preview.html` currently display:

- Row background color coded by game type (Blowout = amber, Strong Favorite = orange, Moderate Favorite = red, Slight Favorite = pink, Toss-up = cyan)
- Prediction column: `<TeamAbbr> 67.1%` — raw percentage only, no plain-English margin
- Confidence column: text label ("High", "Medium", "Low") with color class
- Type column: game category label ("Blowout", "Strong Favorite", etc.)
- Design prototype adds a quarter score grid and a `BOS -6` spread notation at the bottom

The key gap: the spread is still expressed as `BOS -6` (betting notation). There is no plain-English phrasing like "Boston expected to win by 6." The win probability percentage appears alone with no visual bar in the live table view (only in the prototype). The confidence tier labels exist but carry no icon or visual anchor.

---

## Findings

### Finding 1: FiveThirtyEight — Horizontal Split Bar as the Primary Confidence Signal

**Source:** https://projects.fivethirtyeight.com/2022-nba-predictions/ | https://fivethirtyeight.com/features/our-new-live-in-game-win-probabilities-are-here-for-the-nba-playoffs/

**Relevance:** FiveThirtyEight ran the most-cited public NBA prediction model for a decade. Their game card UI was widely praised as accessible.

**What they did:** Each pre-game card showed a horizontal bar divided into two color segments (one per team), with a percentage anchored at each end. The favored team's color filled a larger portion. No spread number appeared at all. The only text was something like "Boston: 67%" on one side, "Miami: 33%" on the other, with the bar between them making the gap immediately obvious.

**Why it works for casual fans:** The bar is a physical metaphor — the bigger side wins. A fan who has never seen a betting line immediately grasps "Boston has most of the bar." The absence of a spread number eliminates the need to explain what "-6" means. The probability percentages act as confirmation, not as the primary signal.

**Gap vs. NBA_ELO:** The live prediction table has a probability bar in the design prototype (`prob-bar-wrap` div with `prob-bar-fill`) but it is not present in the production table view — only the numeric percentage appears. The bar in the prototype also only shows one team's side, not a split showing both teams simultaneously.

**Recommendation:** Replace or augment the current single-sided bar with a split bar spanning the full card width. Left side = away team color, right side = home team color, divider at the correct probability split. No spread number needed alongside it. Estimated impact: removes the single most confusing element for new users (the "-6" notation) while keeping all the information.

---

### Finding 2: Google / Opta Pattern — "Team A is favored" + Percentage in One Plain Sentence

**Source:** https://theanalyst.com/articles/live-win-probability | https://theanalyst.com/articles/opta-football-predictions

**Relevance:** Opta Analyst (data backbone for many broadcast partners) and Google's sports results panel both use a one-sentence plain-English summary as the top-line signal before any numbers appear.

**What they do:** The primary visible text is a declarative sentence: "Boston are favored to win" or in Google's case "Boston is more likely to win this game." Below that, a percentage or bar. The spread number, if it exists at all, appears as a tertiary element in smaller type.

**Why it works for casual fans:** The sentence answers the only question a casual fan has: "who is going to win?" They do not need to decode a number first. Research from Wharton Sports Analytics confirms that win probability graphics only read as useful when the narrative framing precedes the number — without it, fans perceive the number as annoying noise.

**Gap vs. NBA_ELO:** The current card shows `<TeamAbbr> 67.1%` with no surrounding sentence. The team abbreviation plus raw probability is the entire primary signal in the Prediction column. New users with no prior context do not know if 67.1% is impressive or marginal.

**Recommendation:** Change the prediction cell to read: "Boston favored — 67%" with "favored" in normal weight and "Boston" bolded. For toss-ups: "Too close to call — 52%". This requires no additional data, only a template string change. The word "favored" gives users semantic context that the number alone lacks.

---

### Finding 3: Dimers / MyGameSim Pattern — Projected Final Score as the Confidence Anchor

**Source:** https://www.dimers.com/bet-hub/nba/schedule | https://www.mygamesim.com/nba/

**Relevance:** Dimers is currently one of the highest-traffic NBA prediction sites. Their game cards are built around the projected final score, not the win probability percentage. MyGameSim runs 10,000 game simulations and publishes a projected scoreline per team.

**What they do:** The headline element is a predicted scoreline, e.g., "MIL 108 — POR 119." Beneath it, in smaller text: "Milwaukee wins 38% of simulations." The margin (119 - 108 = 11 point gap) is immediately readable by any fan as a margin of victory, with zero betting literacy required. The spread never appears.

**Why it works for casual fans:** Every NBA fan understands final scores. A fan who sees "BOS 117 — MIA 111" instantly reads a 6-point Boston win without needing to know what "-6" means. The margin is embedded in the score itself. Dimers also explicitly notes this approach in their methodology: "from those score projections, we estimate each team's chances of winning" — the score leads, the probability follows.

**Gap vs. NBA_ELO:** The quarter score grid in the design prototype (`docs/design/quarter_preview.html`) already implements this pattern excellently — it shows quarter-by-quarter projected scores with a projected final. However, this component is in a design prototype file only and does not appear in the live production `predict_today.html` table. The live table has no projected score at all.

**Recommendation:** Bring the quarter score grid from the prototype into the live card view. It is the strongest plain-English spread communicator already built. In the meantime, even showing just "Projected: BOS 117 – MIA 111" as a single line under the matchup would move the needle significantly. The margin implied by the projected scores should replace or supplement the `BOS -6` notation in the spread line.

---

### Finding 4: Confidence Tiers with Semantic Icons — The "Lock / Fire / Coin" Convention

**Source:** https://www.actionnetwork.com/picks | https://www.cbssports.com/nba/picks/ | https://dribbble.com/tags/prediction

**Relevance:** Action Network and CBS Sports are the two most-used pick platforms by fans who self-describe as "casual bettors" and "fantasy players." Both use icon-based confidence signals independently of percentage numbers.

**What they do:** Three-tier icon system used across both platforms and most Dribbble/Behance prediction card designs:
- High confidence (75%+): lock icon or fire icon — connotes "locked in," not gamble-like
- Medium confidence (60–74%): thumbs-up or check mark — connotes "leaning"
- Toss-up (50–59%): coin or scale icon — connotes "could go either way"

The icons appear before or above the team name, and confidence percentage is secondary. CBS Sports uses a star rating (1–3 stars) as an alternative, which achieves the same effect through a universally understood rating metaphor.

**Why it works for casual fans:** Icons bypass literacy requirements entirely. A user who does not know what "67% confidence" means still understands that a fire icon next to Boston means "this pick is hot." The icon creates an emotional anchor the number does not. It also creates natural shareability — casual fans share picks by tier ("I've got two locks tonight") rather than by probability.

**Gap vs. NBA_ELO:** The current confidence column shows plain text: "High", "Medium", "Low" with color classes. There are no icons. The design prototype badges say "High Confidence" and "Medium · Tossup" in small text but also use no icons. Color alone (green/yellow) is doing all the visual work, which is known to be a weaker signal than color + icon combined (icon is legible even at small sizes and on color-blind displays).

**Recommendation:** Add a single Unicode or SVG icon before the confidence label in the table cell:
- High (75%+): a lock symbol (closed padlock) or shield — conveys certainty without implying gambling
- Medium (60–74%): a bar chart or chevron-up icon
- Toss-up (below 60%): a horizontal balance / equals sign

This is a CSS/template-only change. The lock icon in particular is a well-established pattern across the pick community and strongly associated with "sure thing" by users who have never seen a betting line.

---

### Finding 5: ESPN BPI — Color Gradient Confidence Scale Rather Than Discrete Tiers

**Source:** https://www.espn.com/nba/bpi | https://www.espn.com/nba/bpi/_/view/projections

**Relevance:** ESPN's Basketball Power Index (BPI) is the mainstream entry point for casual fans who encounter prediction systems inside the ESPN app without seeking them out. Their design priority is legibility inside an information-dense environment.

**What they do:** Rather than discrete color tiers (red/orange/yellow/cyan), ESPN BPI uses a continuous color gradient from one team color to the other along the probability bar. The percentage is shown as a number inside or beside the colored segment. The bar width proportionally represents confidence — a narrow segment for 52% looks clearly different from a wide segment for 85%. The favored team name is bolded.

Key finding from ESPN's own description: game predictions "account for opponent strength, pace of play, site, travel distance, day's rest and altitude." They surface these factors as small supporting text under the prediction, e.g., "Home court: +2.3 pts". This sub-line functions as a plain-English reason for the prediction.

**Why it works for casual fans:** A gradient bar tied to actual team colors creates a tribal/emotional connection casual fans lack with abstract colored rows. A Celtics fan immediately sees "their" green occupying most of the bar. The supporting factor text ("Home court: +2.3") reads like a human explanation, not a model output, which reduces the "black box" perception that turns casual fans off.

**Gap vs. NBA_ELO:** The current color scheme (amber/orange/red/pink/cyan) is model-centric, not team-centric. The row background changes to signal confidence tier, but the color carries no team-identity meaning. There is no supporting factor explanation beneath predictions ("Home advantage: +4 pts", "2 days' rest advantage", etc.) even though NBA_ELO computes rest, travel, and H2H factors internally.

**Recommendation (two parts):**
1. In the prediction bar, use the favored team's actual hex color (stored in `config/constants.yaml` team mappings) for the filled portion rather than a fixed accent color. This is a one-line CSS variable change per card render.
2. Add a one-line "reason" below each prediction that surfaces the top factor. The hybrid predictor already computes rest and travel deltas — surface the largest one in plain English: "Home advantage · BOS rested 2 days more." This converts a black-box number into a legible rationale.

---

## Summary Comparison Table

| Practice | State of Art | NBA_ELO Current | Delta |
|----------|-------------|-----------------|-------|
| Spread communication | "Team A expected to win by X" or projected score (Dimers, Google) | `BOS -6` betting notation | Betting jargon in UI |
| Win probability bar | Split bar, both teams shown, team colors (FiveThirtyEight, ESPN) | Single-sided bar in prototype only; not in live table | Bar missing from live view |
| Confidence signal | Icon (lock/fire/coin) + tier label + color (Action Network, CBS) | Text label + color only ("High", "Medium") | No icon anchor |
| Prediction framing | "Boston favored" sentence before the number (Opta, Google) | Raw `BOS 67.1%` — number only, no framing sentence | No plain-English sentence |
| Projected score | Scoreline as primary element, spread derived from gap (Dimers, MyGameSim) | Quarterly score grid in prototype, absent from live table | Prototype not deployed |
| Prediction rationale | Top factor surfaced in plain text ("Home court: +2.3", ESPN) | No supporting rationale displayed | Factors computed but hidden |
| Team color in UI | Team-specific colors in probability bar (ESPN, CBS) | Fixed model-tier colors (amber/orange/red/cyan) | No team identity |

---

## Recommended Next Steps

Listed in implementation order (easiest to hardest):

1. **Replace `BOS -6` notation with plain-English margin** in both the live table and the design prototype. Change spread line to "Boston by 6" or "Expected margin: 6 pts". Zero new data required. Relevant file: `templates/predict_today.html` (the spread line) and `docs/design/quarter_preview.html` (`.qscore-spread-fav` span). Owner: analyst.

2. **Add confidence icons to the confidence column** in `predict_today.html`. Lock = High, bar-chart = Medium, scale/equals = Toss-up. Can use Unicode characters (e.g., U+1F512 for lock, U+1F4CA for bar chart) or simple SVG. No backend change needed. Owner: analyst.

3. **Deploy the quarterly score grid to the live card** — the `quarter_preview.html` prototype already has the correct design. Port the `.qscore-grid` component and `.qscore-spread` line into the game row render in `loadTodaysGames()`. The projected score replaces the betting notation as the primary spread signal. Owner: analyst.

4. **Add a plain-English "reason" line** under each prediction: pull the largest contributing factor from the hybrid predictor (rest delta, home advantage, H2H) and render it as "Home advantage · 2 extra days' rest" beneath the favorite's name. Requires a small API change to expose top factor from `/api/predict/today`. Owner: data-engineer + analyst.

5. **Switch probability bar fill to team colors** using the team hex palette in `constants.yaml`. Makes the bar emotionally resonant for fans who identify with their team's colors. Owner: analyst (CSS + template).

---

## Sources Reviewed

- https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/
- https://projects.fivethirtyeight.com/2022-nba-predictions/
- https://fivethirtyeight.com/features/our-new-live-in-game-win-probabilities-are-here-for-the-nba-playoffs/
- https://www.espn.com/nba/bpi
- https://www.espn.com/nba/bpi/_/view/projections
- https://www.dimers.com/bet-hub/nba/schedule
- https://www.mygamesim.com/nba/
- https://www.actionnetwork.com/picks
- https://www.cbssports.com/nba/picks/
- https://theanalyst.com/articles/live-win-probability
- https://theanalyst.com/articles/opta-football-predictions
- https://neilpaine.substack.com/p/2024-25-nba-forecast
- https://wsb.wharton.upenn.edu/a-paradox-of-blown-leads-rethinking-win-probability-in-football/
- https://dribbble.com/tags/prediction

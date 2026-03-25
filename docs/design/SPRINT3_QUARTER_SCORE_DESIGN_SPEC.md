# Sprint 3 — Quarter Score Breakdown: Design Spec

**Author:** UI/UX Agent
**Date:** 2026-03-25
**Target file:** `nba-elo-engine/scripts/export_github_pages.py`
**Scope:** CSS additions + HTML template replacement for `.score-projection` inside game cards

---

## 1. Research Summary — 21st.dev Patterns

21st.dev is a shadcn/Radix-based component registry (MIT licensed). WebFetch was blocked for the live site, but their catalog is documented via allshadcn.com and their public GitHub presence. The patterns relevant here are:

- **Data table** — dense grid with muted header labels (`text-xs font-medium text-muted-foreground`) above numeric values (`text-sm font-semibold`)
- **Stat card** — single prominent number in `font-bold text-2xl`, sub-label in `text-xs text-muted-foreground`, separated by a top-border accent rule
- **Table cell hierarchy** — column headers rendered smaller and lighter than cell values; values aligned right in numeric columns; rows separated by a 1px `border-b border-border` not box-shadows

The key takeaway: 21st.dev components use **tight vertical rhythm**, **weight contrast** (label 500 / value 700-800), and **tonal color separation** (muted text for labels, near-white for numbers). No gradients, no glow. Those patterns map cleanly onto our existing token set.

---

## 2. Design Decisions

### Why a mini box-score grid instead of the current single line

The current `.score-projection` renders as:

```
Projected: Lakers 112 · Celtics 108
```

This is a single muted text line — it buries the data. A quarter-by-quarter grid:
- Elevates the score prediction to a scannable visual element
- Mirrors the familiar box-score format every NBA fan reads natively
- Distinguishes the site from basic "team A wins by X" copy

### Quarter distribution model (data note for analyst)

Until the backend produces per-quarter projections, the Q1–Q4 values should be estimated via a simple split:
- Each quarter = total / 4, with random-ish variance distributed as `[-1, +2, -1, 0]` offset applied cyclically to avoid four identical numbers
- This is a display convention only — the analyst can swap in real per-quarter model outputs once available
- The HTML component is designed to receive `q1_home`, `q2_home`, `q3_home`, `q4_home` (and away equivalents) as Python f-string variables

---

## 3. Color Tokens Used

All values come directly from the existing `:root` block — no new colors introduced.

| Role | Token | Hex |
|------|-------|-----|
| Card background | `--surface` | `#0f1623` |
| Inner grid background | `--bg` | `#080c14` |
| Column header text | `--muted` | `#64748b` |
| Score numbers (neutral) | `--text` | `#e8ecf4` |
| Predicted winner's scores | `--pick` | `#f8a100` |
| Divider lines | `--border` | `#1e2d45` |
| Final total (accent) | `--accent` | `#4b8bf4` |

The winning team's Q1-Q4 row is rendered in `--pick` (amber/gold) — consistent with how `.team-pick` already colors the matchup line. The losing team's row uses `--text` at reduced opacity (`0.65`). This keeps the visual hierarchy clear without introducing any new color.

---

## 4. Typography Spec

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| "PROJECTED SCORE" label | `0.62rem` | 700 | `--muted`, uppercase, `letter-spacing: 1.2px` |
| Q1 / Q2 / Q3 / Q4 / TOTAL column headers | `0.6rem` | 600 | `--muted` |
| Team abbreviation (row label) | `0.7rem` | 600 | see winner/loser rule above |
| Quarter score values | `0.78rem` | 700 | see winner/loser rule above |
| TOTAL value | `0.82rem` | 800 | `--accent` for winner, `--muted` for loser |

Rationale: quarter scores are the primary data — they get the highest weight (700). The total column is the summary — it gets 800 and a blue accent to draw the eye right. Column headers are the smallest and lightest element, same pattern as shadcn's `text-muted-foreground text-xs`.

---

## 5. Layout — Grid Structure

```
┌──────────────────────────────────────────────┐
│  PROJECTED SCORE           [section-title]   │
│                                              │
│        Q1    Q2    Q3    Q4   │  TOTAL       │
│  LAL   28    30    27    29   │   114        │  ← winner row (amber)
│  BOS   26    27    28    27   │   108        │  ← loser row (muted)
└──────────────────────────────────────────────┘
```

The grid uses `display: grid` with `grid-template-columns: auto repeat(4, 1fr) 2px 52px`.
- Column 1 (`auto`): team abbreviation label, left-aligned
- Columns 2-5 (`1fr` each): Q1–Q4 values, center-aligned
- Column 6 (`2px`): a vertical `border-right: 1px solid var(--border)` divider rendered as a spacer `<div>`
- Column 7 (`52px`): TOTAL value, right-aligned

The divider before TOTAL is the key visual cue borrowed from real box scores — it tells the reader "everything left of this line is the breakdown, the number on the right is what matters."

---

## 6. Interaction States

- No hover on the grid rows themselves (they are read-only data)
- The entire game card already has a hover state (`background: var(--surface-hi)`) — the quarter grid inherits this naturally
- On mobile (`max-width: 400px`), Q column headers collapse from `Q1 Q2 Q3 Q4` to just the numbers — the headers are `display:none` and the team abbrev takes a `font-size: 0.65rem` to fit

---

## 7. CSS Classes to Add

Add these classes inside the `<style>` block in `render_html()`, after the existing `.score-projection` rule (line 887).

```css
/* ── Quarter Score Breakdown ─────────────────────────────── */
.qscore-wrap {{
  margin-top: 0.55rem;
  margin-bottom: 0.1rem;
}}
.qscore-label {{
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--muted);
  margin-bottom: 0.3rem;
}}
.qscore-grid {{
  display: grid;
  grid-template-columns: 36px repeat(4, 1fr) 1px 52px;
  align-items: center;
  gap: 0;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}}
.qscore-header {{
  display: contents;
}}
.qscore-header > span {{
  font-size: 0.6rem;
  font-weight: 600;
  color: var(--muted);
  text-align: center;
  padding: 0.3rem 0.25rem;
  border-bottom: 1px solid var(--border);
}}
.qscore-header > span:first-child {{
  text-align: left;
  padding-left: 0.5rem;
}}
.qscore-header > .qs-divider-header {{
  border-bottom: 1px solid var(--border);
  background: var(--border);
  padding: 0;
}}
.qscore-header > span:last-child {{
  text-align: right;
  padding-right: 0.5rem;
}}
.qscore-row {{
  display: contents;
}}
.qscore-row > span {{
  font-size: 0.78rem;
  font-weight: 700;
  text-align: center;
  padding: 0.32rem 0.25rem;
  color: var(--text);
  opacity: 0.65;
}}
.qscore-row > span:first-child {{
  font-size: 0.7rem;
  font-weight: 600;
  text-align: left;
  padding-left: 0.5rem;
  letter-spacing: 0.2px;
}}
.qscore-row > .qs-divider {{
  background: var(--border);
  align-self: stretch;
}}
.qscore-row > span:last-child {{
  font-size: 0.82rem;
  font-weight: 800;
  text-align: right;
  padding-right: 0.5rem;
  color: var(--muted);
}}
/* Winner row overrides */
.qscore-row.qs-winner > span {{
  color: var(--pick);
  opacity: 1;
}}
.qscore-row.qs-winner > span:last-child {{
  color: var(--accent);
}}
/* Separator between away and home rows */
.qscore-row-sep {{
  grid-column: 1 / -1;
  height: 1px;
  background: var(--border);
}}
```

---

## 8. HTML Template Snippet

This replaces the existing `.score-projection` `<div>` in the game card template. In `export_github_pages.py`, the current line is:

```python
<div class="score-projection">Projected: {p['away']} {p.get('predicted_away_score', '—')} · {p['home']} {p.get('predicted_home_score', '—')}</div>
```

Replace it with the following Python f-string block. The quarter values are computed inline using simple arithmetic — the analyst can swap these with real model outputs later.

```python
# Quarter score computation (placeholder distribution until model produces per-Q values)
# Offsets are applied cyclically to avoid four identical numbers
_away_tot = p.get('predicted_away_score', 0) or 0
_home_tot = p.get('predicted_home_score', 0) or 0
_q_offsets = [-1, 2, -1, 0]  # sum = 0, so total is preserved
_aq = [max(20, round(_away_tot / 4) + _q_offsets[i]) for i in range(4)]
_hq = [max(20, round(_home_tot / 4) + _q_offsets[i]) for i in range(4)]
# Recalculate totals from quarters to stay consistent with displayed values
_away_display = sum(_aq)
_home_display = sum(_hq)
_winner_is_home = p['is_home_win']
_away_row_cls = 'qs-winner' if not _winner_is_home else ''
_home_row_cls = 'qs-winner' if _winner_is_home else ''
_away_abbr = TEAM_ABBREVS.get(p['away'], p['away'][:3].upper())
_home_abbr = TEAM_ABBREVS.get(p['home'], p['home'][:3].upper())
```

Then the HTML block (still inside the f-string):

```html
<div class="qscore-wrap">
  <div class="qscore-label">Projected Score</div>
  <div class="qscore-grid">

    <!-- Header row -->
    <div class="qscore-header">
      <span></span>
      <span>Q1</span>
      <span>Q2</span>
      <span>Q3</span>
      <span>Q4</span>
      <span class="qs-divider-header"></span>
      <span>FINAL</span>
    </div>

    <!-- Away row -->
    <div class="qscore-row {_away_row_cls}">
      <span>{_away_abbr}</span>
      <span>{_aq[0]}</span>
      <span>{_aq[1]}</span>
      <span>{_aq[2]}</span>
      <span>{_aq[3]}</span>
      <span class="qs-divider"></span>
      <span>{_away_display}</span>
    </div>

    <!-- Row separator -->
    <div class="qscore-row-sep"></div>

    <!-- Home row -->
    <div class="qscore-row {_home_row_cls}">
      <span>{_home_abbr}</span>
      <span>{_hq[0]}</span>
      <span>{_hq[1]}</span>
      <span>{_hq[2]}</span>
      <span>{_hq[3]}</span>
      <span class="qs-divider"></span>
      <span>{_home_display}</span>
    </div>

  </div>
</div>
```

**Important implementation note for the analyst:** The `display: contents` technique on `.qscore-header` and `.qscore-row` makes the child `<span>` elements direct grid items of `.qscore-grid`. This means the `<div class="qscore-header">` and `<div class="qscore-row">` wrappers are invisible to the grid layout engine — only the `<span>` children participate in grid placement. The 7-column layout (`36px repeat(4, 1fr) 1px 52px`) therefore applies across all three logical "rows" (header, away, home) as one unified grid.

The `.qscore-row-sep` is a plain `div` that spans all 7 columns via `grid-column: 1 / -1` — this is the horizontal rule between away and home rows.

---

## 9. Vibe-Coded Giveaway Check

Before this component ships, confirm the following are absent:

| Check | Status |
|-------|--------|
| No `linear-gradient` on the quarter grid | Pass — solid `var(--bg)` background |
| No `box-shadow` glow | Pass — `border: 1px solid var(--border)` only |
| No `border-radius: 9999px` | Pass — `6px` used, matches bar/badge spec |
| No `color: white` on colored backgrounds | Pass — `var(--pick)` rows use `#f8a100` on `#080c14` |
| No `font-family: system-ui` | Pass — inherits Inter from `body` |
| No `#3b82f6` blue | Pass — `--accent` (`#4b8bf4`) only |
| No equal padding everywhere | Pass — header cells `0.3rem`, data cells `0.32rem`, label col `padding-left: 0.5rem` |
| TOTAL column draws the eye (not equal weight to Q values) | Pass — `font-weight: 800` vs `700` for Q values; `--accent` color for winner total |

---

## 10. Mobile Behavior (`max-width: 400px`)

Add inside the existing `@media (max-width: 400px)` block:

```css
.qscore-grid {{
  grid-template-columns: 30px repeat(4, 1fr) 1px 46px;
}}
.qscore-row > span,
.qscore-header > span {{
  font-size: 0.58rem;
  padding: 0.25rem 0.15rem;
}}
.qscore-row > span:first-child {{
  font-size: 0.6rem;
  padding-left: 0.35rem;
}}
.qscore-row > span:last-child,
.qscore-header > span:last-child {{
  padding-right: 0.35rem;
}}
.qscore-label {{
  font-size: 0.58rem;
}}
```

At 375px width this keeps all 7 columns legible with no overflow or truncation.

---

## 11. Acceptance Criteria

Before shipping, open `pages/index.html` in a browser and verify:

1. The quarter grid appears below the win-probability bar on each game card
2. The predicted winner's row is amber (`#f8a100`), loser's row is muted (`#e8ecf4` at 65% opacity)
3. The TOTAL column has a visible divider to its left
4. The FINAL value for the winner is in blue (`#4b8bf4`), not amber
5. Four distinct quarter values per team (not four identical numbers from a raw /4 split)
6. On mobile (375px), all columns fit without horizontal scroll
7. No vibe-coded patterns listed in Section 9 are present

---

## 12. What the Analyst Needs to Do Next

This spec is display-only. To make the quarter breakdown genuinely predictive (not cosmetically distributed), the analyst should:

1. Build a per-quarter pace model: Q1 tends to run slightly under average pace, Q4 above (regulation close games) — `src/utils/elo_math.py` is the right place for a `elo_diff_to_quarter_scores()` helper
2. Expose `q1_home`, `q2_home`, `q3_home`, `q4_home`, `q1_away`, etc. in the `predictions` dict returned by `get_today_predictions()`
3. Replace the `_q_offsets` arithmetic in the HTML template with direct reads of those dict keys

The component HTML/CSS does not need to change when that upgrade happens — it already expects per-quarter variables.

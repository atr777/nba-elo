"""July 9 posting pack: the six reported LeBron suitors, by where each team
actually FINISHED the 2025-26 season in our team ratings.

These are finishing ratings, NOT 2026-27 forecasts (we have no roster-adjusted
preseason ratings yet), and the chart says so. Team-level numbers only, so no
roster claim is made. Deliberately does NOT put LeBron's individual rating
(1,947) on the same axis as team ratings: different populations, not comparable.

Suitor list per reporting as of 2026-07-08: GSW, MIA, CLE, PHI, MIN, DEN.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#0f1011"; INK = "#f5f5f7"; SECONDARY = "#9f9fa0"; MUTED = "#6a6b6b"
BASELINE = "#3a3d3f"; BLUE = "#00b3dd"; EMBER = "#d74e09"

plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "text.color": INK,
})
OUT = "docs/growth/posts/assets"
os.makedirs(OUT, exist_ok=True)

# (team, finishing rating, league rank of 30, is_top5)
suitors = [
    ("Cleveland",    1636, 5,  True),
    ("Denver",       1611, 7,  False),
    ("Minnesota",    1604, 8,  False),
    ("Miami",        1505, 17, False),
    ("Philadelphia", 1486, 19, False),
    ("Golden State", 1486, 20, False),
]
OKC = 1770
LEAGUE_AVG = 1500
BASE = 1440

rows = suitors[::-1]  # best at top of chart
fig, ax = plt.subplots(figsize=(7.28, 4.9), dpi=200)
fig.subplots_adjust(left=0.28, right=0.90, top=0.72, bottom=0.14)

for i, (name, val, rank, top5) in enumerate(rows):
    ax.barh(i, val - BASE, left=BASE, height=0.6,
            color=EMBER if top5 else BLUE, zorder=3)
    ax.text(val + 4, i, f"{val:,}", va="center", ha="left", fontsize=11.5,
            color=INK, fontweight="bold")

# rank rides in the tick label, so it can never collide with the team name
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([f"{r[0]}  #{r[2]}" for r in rows], fontsize=12.5, color=INK)
for tick, r in zip(ax.get_yticklabels(), rows):
    if r[3]:
        tick.set_color(EMBER); tick.set_fontweight("bold")

# the two reference lines get labels on DIFFERENT rows (top vs bottom)
ax.axvline(LEAGUE_AVG, color=BASELINE, linewidth=1, linestyle="--", zorder=2)
ax.text(LEAGUE_AVG, -0.78, "league average (1,500)", fontsize=8.5,
        color=MUTED, va="center", ha="center")
ax.axvline(OKC, color=SECONDARY, linewidth=1, zorder=2)
ax.text(OKC - 8, len(rows) - 0.35, "Oklahoma City, the league's best (1,770)",
        fontsize=8.5, color=SECONDARY, va="center", ha="right")

ax.set_xlim(BASE, 1800)
ax.set_ylim(-1.2, len(rows) - 0.1)
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(colors=MUTED, length=0)
ax.set_xticks([])

fig.text(0.045, 0.915, "THE LEBRON SWEEPSTAKES", fontsize=11, color=MUTED,
         fontweight="bold")
fig.text(0.045, 0.835, "Six teams want him. One finished in the top five.",
         fontsize=14.5, color=INK, fontweight="bold")
fig.text(0.28, 0.045, "Finishing ratings, not 2026-27 forecasts.",
         fontsize=8.5, color=MUTED)
fig.text(0.90, 0.045, "secondbounce.substack.com", fontsize=8.5, color=MUTED, ha="right")

fig.savefig(f"{OUT}/lebron_suitors_2026.png", bbox_inches=None)
plt.close(fig)
print(f"Saved {OUT}/lebron_suitors_2026.png")

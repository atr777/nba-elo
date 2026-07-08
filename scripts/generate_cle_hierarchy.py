"""One-off chart for the July 8 posting pack: Cleveland's roster by model
rating, flagging that Donovan Mitchell's new $273M extension makes him the
Cavs' third-best player in our system, behind Harden and Mobley.

Ratings are individual (roster-safe); team membership verified against the
refreshed player_team_mapping on 2026-07-07. Outputs a 1456px-wide PNG.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

SURFACE = "#0f1011"; INK = "#f5f5f7"; SECONDARY = "#9f9fa0"; MUTED = "#6a6b6b"
GRID = "#242628"; BASELINE = "#3a3d3f"; BLUE = "#00b3dd"; EMBER = "#d74e09"

plt.rcParams.update({
    "font.family": "Segoe UI",
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "text.color": INK,
})

OUT = "docs/growth/posts/assets"
os.makedirs(OUT, exist_ok=True)

# Confirmed Cleveland core, top 6 by model rating (Segoe rating file 2025-26).
players = [
    ("James Harden",     2136, False),
    ("Evan Mobley",      1896, False),
    ("Donovan Mitchell", 1864, True),   # the new $273M man
    ("Jarrett Allen",    1831, False),
    ("Larry Nance Jr.",  1576, False),
    ("Sam Merrill",      1553, False),
]
players = players[::-1]  # matplotlib draws bottom-up; we want Harden on top
names = [p[0] for p in players]
vals = [p[1] for p in players]
flags = [p[2] for p in players]
BASE = 1500  # league-average player

fig, ax = plt.subplots(figsize=(7.28, 4.9), dpi=200)
fig.subplots_adjust(left=0.30, right=0.94, top=0.74, bottom=0.12)

y = range(len(players))
for i, (name, val, flag) in enumerate(players):
    color = EMBER if flag else BLUE
    ax.barh(i, val - BASE, left=BASE, height=0.62, color=color,
            zorder=3, alpha=1.0 if flag else 0.92)
    ax.text(val + 8, i, f"{val:,}", va="center", ha="left",
            fontsize=12, color=INK, fontweight="bold")

ax.set_yticks(list(y))
ax.set_yticklabels(names, fontsize=12.5,
                   color=INK)
for tick, flag in zip(ax.get_yticklabels(), flags):
    if flag:
        tick.set_color(EMBER); tick.set_fontweight("bold")

# 1500 baseline reference
ax.axvline(BASE, color=BASELINE, linewidth=1, zorder=2)
ax.set_xlim(BASE, 2230)
for side in ("top", "right", "bottom", "left"):
    ax.spines[side].set_visible(False)
ax.tick_params(colors=MUTED, length=0)
ax.set_xticks([])

# Headline block
fig.text(0.055, 0.925, "CLEVELAND, BY MODEL RATING", fontsize=11,
         color=MUTED, fontweight="bold")
fig.text(0.055, 0.845, "The Cavs' new $273M man is our model's third-best Cavalier.",
         fontsize=14.5, color=INK, fontweight="bold")

# Mitchell annotation — Mitchell is index 3 from bottom (players reversed)
mitch_i = names.index("Donovan Mitchell")
ax.annotate("new 4-year, $273M extension",
            xy=(1864, mitch_i), xytext=(1610, mitch_i - 0.62),
            fontsize=9.5, color=EMBER, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=EMBER, lw=1))

fig.text(0.30, 0.045, "1,500 = average NBA player  ·  walk-forward verified",
         fontsize=8.5, color=MUTED)
fig.text(0.94, 0.045, "secondbounce.substack.com", fontsize=8.5,
         color=MUTED, ha="right")

fig.savefig(f"{OUT}/cle_hierarchy.png", bbox_inches=None)
plt.close(fig)
print(f"Saved {OUT}/cle_hierarchy.png")

"""This week's deals: model-adjusted rating minus raw box-score rating.
Negative = the model docks (rim protectors); positive = the model boosts
(shot creators). Diverging chart, house style."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Origin palette (dark obsidian canvas)
SURFACE = "#0f1011"
INK = "#f5f5f7"
SECONDARY = "#9f9fa0"
MUTED = "#6a6b6b"
BASELINE = "#3a3d3f"
RED = "#e5484d"
BLUE = "#00b3dd"

plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "text.color": INK,
})

# (player, delta, note) — sorted most-docked to most-boosted
rows = [
    ("Isaiah Hartenstein", -196, "3 yr / $75M · Oklahoma City"),
    ("Walker Kessler", -170, "4 yr / $130M · Lakers"),
    ("LaMelo Ball", +126, "traded to Minnesota"),
    ("James Harden", +158, "re-ups with Cleveland"),
]
rows = rows[::-1]  # most boosted at top

fig, ax = plt.subplots(figsize=(7.28, 4.8), dpi=200)
for y, (name, delta, note) in enumerate(rows):
    color = BLUE if delta > 0 else RED
    ax.barh(y, delta, height=0.5, color=color, zorder=3)
    side = -1 if delta > 0 else 1  # name/note sit on the zero side, opposite bar
    ha = "right" if delta > 0 else "left"
    ax.text(side * 12, y + 0.12, name, va="center", ha=ha, fontsize=12.5,
            color=INK, fontweight="bold")
    ax.text(side * 12, y - 0.16, note, va="center", ha=ha, fontsize=9.5,
            color=MUTED)
    tip = delta + (10 if delta > 0 else -10)
    ax.text(tip, y, f"+{delta}" if delta > 0 else f"{delta}", va="center",
            ha="left" if delta > 0 else "right", fontsize=12.5,
            color=color, fontweight="bold")

ax.axvline(0, color=BASELINE, linewidth=1.2, zorder=2)
ax.set_xlim(-340, 340)
ax.set_ylim(-1.05, len(rows) - 0.25)
ax.set_yticks([])
ax.set_xticks([])
for s in ax.spines.values():
    s.set_visible(False)
ax.text(-335, -0.75, "MODEL DOCKS  ◄", fontsize=10, color=RED,
        fontweight="bold", va="center")
ax.text(335, -0.75, "►  MODEL BOOSTS", fontsize=10, color=BLUE,
        fontweight="bold", va="center", ha="right")
fig.subplots_adjust(left=0.03, right=0.97, top=0.80, bottom=0.05)
fig.text(0.035, 0.945, "This week's deals, model vs box score",
         fontsize=15, fontweight="bold", color=INK)
fig.text(0.035, 0.862, "Model-adjusted rating minus raw box score. The market "
         "pays for what the model marks down.", fontsize=10.5, color=SECONDARY)
fig.savefig("docs/growth/posts/assets/week_divergence.png")
print("done")

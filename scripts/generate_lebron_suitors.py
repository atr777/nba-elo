"""LeBron suitors ranked by the model's team rating. Team-level only (safe:
no roster claims). Reported frontrunners highlighted."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
SECONDARY = "#52514e"
MUTED = "#898781"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"
FAINT = "#c9c8c2"

plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "text.color": INK,
})

# (team, last-season model rating, is reported frontrunner, note)
rows = [
    ("Boston", 1673, False, ""),
    ("Cleveland", 1637, True, "frontrunner"),
    ("New York", 1634, False, ""),
    ("Miami", 1505, True, "frontrunner · now has Giannis"),
    ("Golden State", 1486, True, "frontrunner"),
]
rows = rows[::-1]  # highest at top

fig, ax = plt.subplots(figsize=(7.28, 4.6), dpi=200)
for y, (team, rating, front, note) in enumerate(rows):
    color = BLUE if front else FAINT
    ax.barh(y, rating - 1400, left=1400, height=0.6, color=color, zorder=3)
    ax.text(1408, y, team, va="center", fontsize=12.5,
            color="white" if front else INK, fontweight="bold", zorder=4)
    ax.text(rating + 6, y, f"{rating:,}", va="center", fontsize=12,
            color=INK, fontweight="bold")
    if note:
        ax.text(rating + 70, y, note, va="center", fontsize=9.5, color=MUTED)

ax.axvline(1500, color=BASELINE, linewidth=1, zorder=2)
ax.text(1500, -0.55, "1500 = average team", fontsize=9, color=MUTED,
        ha="center", va="top")
ax.set_xlim(1400, 1760)
ax.set_ylim(-1.0, len(rows) - 0.2)
ax.set_yticks([])
ax.set_xticks([])
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("LeBron's suitors, by the model's rating",
             fontsize=15, fontweight="bold", loc="left", pad=14, color=INK)
ax.text(0, 1.02, "Reported frontrunners highlighted. Team rating from last "
        "season; LeBron rates 1,947.",
        transform=ax.transAxes, fontsize=10.5, color=SECONDARY)
fig.tight_layout()
fig.savefig("docs/growth/posts/assets/lebron_suitors.png")
print("done")

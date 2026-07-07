"""Generate the three graphics for the 2025-26 season recap post.

Outputs 1456px-wide PNGs (2x Substack's 728px content column) to
docs/growth/posts/assets/. Palette follows the validated dataviz reference:
single blue series on a light surface, text in ink tokens, hairline chrome.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Origin palette (dark obsidian canvas, cream text, cyan data-signal)
SURFACE = "#0f1011"
INK = "#f5f5f7"
SECONDARY = "#9f9fa0"
MUTED = "#6a6b6b"
GRID = "#242628"
BASELINE = "#3a3d3f"
BLUE = "#00b3dd"        # cyan data-signal
BLUE_LIGHT = "#4b49aa"  # deep iris (secondary marks)
GOOD = "#30a46c"

plt.rcParams.update({
    "font.family": "Segoe UI",
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": INK,
})

OUT = "docs/growth/posts/assets"
import os
os.makedirs(OUT, exist_ok=True)


def strip_axes(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.spines["bottom"].set_linewidth(1)
    ax.tick_params(colors=MUTED, length=0)


# ---------------------------------------------------------------- hero card
fig, ax = plt.subplots(figsize=(7.28, 3.4), dpi=200)
ax.axis("off")
fig.text(0.055, 0.83, "2025-26 SEASON ACCURACY", fontsize=10.5, color=MUTED,
         fontweight="bold")
fig.text(0.048, 0.40, "70.6%", fontsize=64, color=INK, fontweight="bold")
fig.text(0.055, 0.24, "464 of 657 tracked games called correctly",
         fontsize=12.5, color=SECONDARY)
for x, big, small in [
    (0.52, "77.6%", "on 75%+ confidence\npicks (259 games)"),
    (0.70, "20", "straight correct\npicks at the peak"),
    (0.845, "80%", "in the playoffs\n(20 games)"),
]:
    fig.text(x, 0.60, big, fontsize=21, color=INK, fontweight="bold")
    fig.text(x, 0.535, small, fontsize=9, color=SECONDARY, va="top")
fig.lines.append(Line2D([0.52, 0.945], [0.72, 0.72], transform=fig.transFigure,
                        color=GRID, linewidth=1))
fig.text(0.945, 0.08, "secondbounce.substack.com", fontsize=8.5, color=MUTED,
         ha="right")
fig.savefig(f"{OUT}/hero_card.png", bbox_inches=None)
plt.close(fig)

# ------------------------------------------------------- monthly accuracy
months = ["Nov-Dec", "Jan", "Feb", "Mar", "Apr", "Playoffs"]
vals = [61.1, 63.0, None, 77.4, 73.6, 80.0]
games = [162, 92, None, 239, 144, 20]

fig, ax = plt.subplots(figsize=(7.28, 4.1), dpi=200)
xs = range(len(months))
for x, v in zip(xs, vals):
    if v is None:
        ax.text(x, 30, "pipeline\noutage,\nno tracking", ha="center",
                fontsize=9, color=MUTED, style="italic")
        continue
    ax.bar(x, v, width=0.42, color=BLUE, zorder=3)
    ax.text(x, v + 2.2, f"{v:.0f}%", ha="center", fontsize=12.5,
            color=INK, fontweight="bold")
ax.axhline(50, color=BASELINE, linewidth=1, zorder=2)
ax.text(2, 52.2, "50% = coin flip", fontsize=9, color=MUTED, ha="center")
ax.set_xticks(list(xs))
ax.set_xticklabels([f"{m}\n{g} games" if g else m
                    for m, g in zip(months, games)], fontsize=10.5)
ax.set_ylim(0, 96)
ax.set_yticks([])
ax.set_xlim(-0.55, 5.55)
strip_axes(ax)
ax.set_title("The model got better as the season went on",
             fontsize=15, fontweight="bold", loc="left", pad=16, color=INK)
ax.text(0, 1.015, "Prediction accuracy by month. A home-court bug was found "
        "and fixed in early March.", transform=ax.transAxes, fontsize=10.5,
        color=SECONDARY)
fig.tight_layout()
fig.savefig(f"{OUT}/monthly_accuracy.png")
plt.close(fig)

# ----------------------------------------------------------- calibration
buckets = ["50-60%", "60-70%", "70-80%", "80-90%", "90%+"]
expected = [54.6, 65.2, 74.4, 84.8, 90.0]
actual = [60.0, 69.7, 73.2, 78.6, 81.0]
n = [195, 119, 142, 117, 84]

fig, ax = plt.subplots(figsize=(7.28, 4.3), dpi=200)
xs = range(len(buckets))
for x, e, a in zip(xs, expected, actual):
    ax.plot([x, x], [e, a], color=GRID, linewidth=2, zorder=2)
    ax.scatter([x], [e], s=90, color=BLUE_LIGHT, zorder=3)
    ax.scatter([x], [a], s=120, color=BLUE, zorder=4,
               edgecolors=SURFACE, linewidths=2)
    ax.text(x + 0.13, a - 0.4, f"{a:.0f}%", fontsize=12, color=INK,
            fontweight="bold", va="center")
ax.set_xticks(list(xs))
ax.set_xticklabels([f"{b}\n{g} games" for b, g in zip(buckets, n)],
                   fontsize=10.5)
ax.set_ylim(48, 100)
ax.set_yticks([])
ax.set_xlim(-0.5, 4.75)
strip_axes(ax)
ax.set_title("The confidence scores mean something, with one flaw",
             fontsize=15, fontweight="bold", loc="left", pad=16, color=INK)
ax.text(0, 1.015, "Stated win probability vs. reality, 657 games. Solid in "
        "the middle, overconfident up top.",
        transform=ax.transAxes, fontsize=10.5, color=SECONDARY)
legend = ax.legend(handles=[
    Line2D([], [], marker="o", linestyle="", markersize=10, color=BLUE,
           label="Actual win rate"),
    Line2D([], [], marker="o", linestyle="", markersize=8.5,
           color=BLUE_LIGHT, label="What the model promised"),
], loc="upper left", frameon=False, fontsize=10.5, labelcolor=SECONDARY,
   borderaxespad=0.1)
fig.tight_layout()
fig.savefig(f"{OUT}/calibration.png")
plt.close(fig)

print("done: hero_card.png, monthly_accuracy.png, calibration.png")

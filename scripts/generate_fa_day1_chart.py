"""Chart for the free-agency day-one post: the movers, by model rating."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
SECONDARY = "#52514e"
MUTED = "#898781"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"
BLUE_FAINT = "#9ec5f4"

plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "text.color": INK,
})

players = [
    ("Giannis Antetokounmpo", 2280, "to Miami"),
    ("LeBron James", 1947, "leaving LA, dest. TBD"),
    ("Kawhi Leonard", 1858, "back to Toronto"),
    ("Jaylen Brown", 1746, "to Philadelphia"),
    ("LaMelo Ball", 1703, "to Minnesota"),
    ("Paul George", 1699, "to Boston"),
    ("Ja Morant", 1647, "to Portland"),
    ("Norman Powell", 1541, "to Chicago"),
    ("Walker Kessler", 1529, "to the Lakers"),
    ("Andrew Wiggins", 1446, "stays in Miami"),
    ("Quentin Grimes", 1435, "to the Lakers"),
]

fig, ax = plt.subplots(figsize=(7.28, 5.6), dpi=200)
ys = range(len(players) - 1, -1, -1)
for y, (name, rating, dest) in zip(ys, players):
    ax.barh(y, rating - 1350, left=1350, height=0.55, color=BLUE, zorder=3)
    if rating >= 1650:
        ax.text(1358, y, f"{name}  ·  {dest}", va="center", fontsize=10.5,
                color="white", zorder=4, fontweight="bold")
        ax.text(rating + 12, y, f"{rating:,}", va="center", fontsize=10.5,
                color=INK, fontweight="bold")
    else:
        ax.text(rating + 12, y, f"{rating:,}  {name} · {dest}", va="center",
                fontsize=10.5, color=INK, zorder=4)

ax.axvline(1500, color=BASELINE, linewidth=1, zorder=2)
ax.text(1500, -0.55, "1500 = average NBA player", fontsize=9,
        color=MUTED, ha="center", va="top")
ax.set_xlim(1350, 2420)
ax.set_ylim(-1.1, len(players))
ax.set_yticks([])
ax.set_xticks([])
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Free agency day one: the movers, by model rating",
             fontsize=15, fontweight="bold", loc="left", pad=14, color=INK)
ax.text(0, 1.005, "Adjusted player ELO entering the offseason. Reported "
        "moves as of July 2.", transform=ax.transAxes, fontsize=10.5,
        color=SECONDARY)
fig.tight_layout()
fig.savefig("docs/growth/posts/assets/fa_day1_movers.png")
print("done")

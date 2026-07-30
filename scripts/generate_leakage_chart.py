"""Chart for the correction essay: cumulative accuracy, as-published vs walk-forward.

Both lines cover the SAME 657 games. The only difference is when the model was
allowed to see each result, which is the entire point: the gap is not a different
model or a different sample, it is one bug in the evaluation.

    python scripts/generate_leakage_chart.py

Palette: brand iris #847dff for the honest series, #d95926 for the withdrawn one.
That pair was validated with the dataviz palette checker on a dark surface and
passes all six checks (lightness band, chroma floor, CVD separation, normal-vision
floor, contrast), worst-case CVD deltaE 30.2. Do not substitute colours by eye.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEAKY = ROOT / "data/exports/prediction_tracking_vps_final.csv"
HONEST = ROOT / "data/exports/prediction_tracking_honest.csv"
OUT = ROOT / "docs/growth/posts/assets/leakage_cumulative_accuracy.png"

OBSIDIAN = "#0f1011"
CLOUD = "#f5f5f7"
ASH = "#9f9fa0"
GRID = "#2e2e2e"
IRIS = "#847dff"       # honest, the record we stand behind
EMBER = "#d95926"      # withdrawn


def _key(d):
    return (d["date"].astype(str) + "_" + d["home_team_id"].astype(str)
            + "_" + d["away_team_id"].astype(str))


def load():
    leaky = pd.read_csv(LEAKY).dropna(subset=["correct"])
    honest = pd.read_csv(HONEST).dropna(subset=["correct"])
    leaky["key"], honest["key"] = _key(leaky), _key(honest)
    # Order by the honest log's chronology and align the withdrawn file onto it, so
    # both lines advance through the season in the same order. Sorting each file
    # independently would let a tie break differently and put the two series a game
    # out of step with each other.
    honest = honest.sort_values(["date", "key"]).reset_index(drop=True)
    m = honest[["key", "date", "correct"]].merge(
        leaky[["key", "correct"]], on="key", suffixes=("_honest", "_leaky"))
    assert len(m) == len(honest) == 657, f"alignment lost: {len(m)}"
    n = range(1, len(m) + 1)
    m["cum_honest"] = 100 * m["correct_honest"].cumsum() / n
    m["cum_leaky"] = 100 * m["correct_leaky"].cumsum() / n
    return m


def main() -> None:
    m = load()

    # Start the plot at game 30. A running average over the first handful of games
    # swings between 43% and 100% purely because the denominator is tiny, which on a
    # chart reads as a real event and dwarfs the effect being shown. The full series
    # is still what the final figures are computed from; this only sets the window.
    START = 30
    v = m.iloc[START - 1:]
    x = range(START, len(m) + 1)

    fig, ax = plt.subplots(figsize=(10.5, 5.9), dpi=150)
    fig.patch.set_facecolor(OBSIDIAN)
    ax.set_facecolor(OBSIDIAN)

    ax.plot(x, v["cum_leaky"], color=EMBER, lw=2, zorder=3)
    ax.plot(x, v["cum_honest"], color=IRIS, lw=2, zorder=4)

    # Direct labels rather than relying on the legend alone: two series, both named
    # at the line end, so identity never depends on colour.
    end_leaky = v["cum_leaky"].iloc[-1]
    end_honest = v["cum_honest"].iloc[-1]
    ax.text(len(m) + 8, end_leaky, f"  as published\n  {end_leaky:.1f}%",
            color=EMBER, fontsize=11, va="center", fontweight="bold")
    ax.text(len(m) + 8, end_honest, f"  walk-forward\n  {end_honest:.1f}%",
            color=IRIS, fontsize=11, va="center", fontweight="bold")

    # Limits from the data, padded, so no part of either line is clipped.
    lo = min(v["cum_honest"].min(), v["cum_leaky"].min())
    hi = max(v["cum_honest"].max(), v["cum_leaky"].max())
    ax.set_xlim(START, len(m) * 1.20)
    ax.set_ylim(lo - 1.5, hi + 1.5)
    ax.set_xlabel("games graded, in the order they were played", color=ASH, fontsize=10.5)
    ax.set_ylabel("cumulative accuracy (%)", color=ASH, fontsize=10.5)
    ax.set_title("Same 657 games, same model, two evaluations",
                 color=CLOUD, fontsize=15.5, fontweight="bold", loc="left", pad=16)

    ax.grid(True, color=GRID, lw=0.7, alpha=0.55)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=ASH, labelsize=9.5)

    fig.text(0.008, 0.022,
             "The withdrawn line let each rating absorb a game before predicting it. "
             "Net effect: 19 wins that were not there.",
             color=ASH, fontsize=9.5)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.88, bottom=0.16)
    fig.savefig(OUT, facecolor=OBSIDIAN)
    print(f"wrote {OUT.relative_to(ROOT)}  "
          f"(final {end_leaky:.2f}% vs {end_honest:.2f}%)")


if __name__ == "__main__":
    main()

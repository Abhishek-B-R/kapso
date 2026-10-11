"""Render docs/images/relbench.png: Kapso against the official RelBench
leaderboard entries of Stanford STAR and Kumo AI, one panel per board.

    python benchmarks/relbench/figure.py docs/images/relbench.png

The numbers are the leaderboard means (star-project.stanford.edu/relbench/
leaderboard, data file leaderboard.json); the Stanford STAR and Kumo marks are
drawn as vector shapes, the Leeroo mark comes from docs/logo/logo-transparent.png.
"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.patches import FancyBboxPatch

OUT = sys.argv[1]
LEEROO_MARK = Path(__file__).resolve().parents[2] / "docs" / "logo" / "logo-transparent.png"
GREY, ORANGE, INK, MUTED = "#d4d8e0", "#F5A623", "#1a1a1a", "#555a63"
KUMO_PINK = "#E6007E"
MONO = "DejaVu Sans Mono"

PANELS = [  # title, metric, bars [(name, affiliation, mark, value, text, kind)], delta, ylim
    ("Classification", "AUROC · 12 tasks · higher is better",
     [("RT-J (fine-tuned)", "Stanford STAR", "star", 79.02, "79.0", "grey"),
      ("KumoRFM-v2", "Kumo AI", "kumo", 79.26, "79.3", "grey"),
      ("Kapso", "Leeroo", "leeroo", 81.19, "81.2", "orange")],
     "+2.4%", (76.0, 83.0)),
    ("Regression", "error (NMAE) · 9 tasks · lower is better",
     [("RT-J (fine-tuned)", "Stanford STAR", "star", 0.2711, "0.2711", "grey"),
      ("KumoRFM-v2", "Kumo AI", "kumo", 0.2847, "0.2847", "grey"),
      ("Kapso", "Leeroo", "leeroo", 0.2476, "0.2476", "orange")],
     "−8.7% error", (0.20, 0.31)),
    ("Recommendations", "MAP · 10 tasks · higher is better",
     [("ID-GNN", "Stanford STAR", "star", 9.33, "9.3", "grey"),
      ("KumoRFM-v2", "Kumo AI", "kumo", None, "no entry", "none"),
      ("Kapso", "Leeroo", "leeroo", 18.37, "18.4", "orange")],
     "+97%", (0.0, 22.5)),
]

fig = plt.figure(figsize=(19.2, 9.6), dpi=100)
fig.patch.set_facecolor("#f7f8fa")
gx, gy = np.meshgrid(np.linspace(0.01, 0.99, 56), np.linspace(0.02, 0.98, 28))
fig.add_axes([0, 0, 1, 1]).set_axis_off()
plt.scatter(gx, gy, s=2.2, color="#d9dce2", transform=fig.transFigure, zorder=0, clip_on=False)
fig.text(0.5, 0.925, "Predictive Modelling on Relational Data (RelBench)", ha="center", va="center",
         fontsize=30, fontweight="bold", color=INK)
fig.text(0.5, 0.878, "e-commerce reviews · classified ads · event recommendation · fashion retail · online Q&A · clinical trials",
         ha="center", va="center", fontsize=15, color=MUTED)

mark = Image.open(LEEROO_MARK).convert("RGBA")
raster = {"leeroo": np.asarray(mark.crop(mark.getchannel("A").getbbox()))}

def draw_mark(kind, cx, cy, size=0.052):
    """A logo tile of one size for every entry, centred at figure (cx, cy)."""
    h = size * 2  # figure is 2:1, so equal width/height in inches
    ax = fig.add_axes([cx - size / 2, cy - h / 2, size, h]); ax.set_axis_off()
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    if kind == "kumo":
        ax.add_patch(FancyBboxPatch((0.08, 0.08), 0.84, 0.84, boxstyle="round,pad=0,rounding_size=0.14",
                                    facecolor="white", edgecolor="#d9dce2", linewidth=1.0))
        ax.text(0.5, 0.47, "ku", ha="center", va="center", fontsize=23, fontweight="bold", color=KUMO_PINK)
    elif kind == "star":  # the STAR favicon, redrawn from its SVG (32-unit grid, rx 7 tile, 5-unit cells)
        u = 0.84 / 32
        ax.add_patch(FancyBboxPatch((0.08, 0.08), 0.84, 0.84, boxstyle=f"round,pad=0,rounding_size={7*u}",
                                    facecolor="#8c1515", edgecolor="none"))
        for row, y in enumerate((20, 13.5, 7)):      # svg y grows downward; axes y grows upward
            for col, x in enumerate((7, 13.5, 20)):
                solid = (row, col) in ((2, 0), (1, 1), (0, 2))   # the white diagonal
                ax.add_patch(FancyBboxPatch((0.08 + x * u, 0.08 + (32 - y - 5) * u), 5 * u, 5 * u,
                                            boxstyle=f"round,pad=0,rounding_size={u}", facecolor="white",
                                            edgecolor="none", alpha=1.0 if solid else 0.5))
    else:
        ax.imshow(raster[kind], extent=(0.1, 0.9, 0.1, 0.9), interpolation="lanczos")

lefts, width, bottom, height = [0.04, 0.375, 0.71], 0.275, 0.235, 0.50
for (title, metric, bars, delta, ylim), left in zip(PANELS, lefts):
    ax = fig.add_axes([left, bottom, width, height]); ax.set_facecolor("none")
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#c9ccd3"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_ylim(*ylim); ax.set_xlim(-0.6, 2.6); span = ylim[1] - ylim[0]
    for i, (name, aff, mark, value, text, kind) in enumerate(bars):
        if kind == "none":
            ax.bar(i, span, bottom=ylim[0], width=0.72, fill=False, edgecolor="#c9ccd3",
                   linestyle=(0, (4, 4)), linewidth=1.2)
            ax.text(i, ylim[0] + 0.5 * span, "task not\nsupported", ha="center", va="center", fontsize=13, linespacing=1.5,
                    color="#9aa0a8", style="italic")
        else:
            ax.bar(i, value - ylim[0], bottom=ylim[0], width=0.72,
                   color=ORANGE if kind == "orange" else GREY, zorder=3)
            if kind == "orange":  # value on top, the gain beneath it, as the original
                ax.text(i, value + 0.075 * span, text, ha="center", va="bottom", fontsize=20,
                        fontfamily=MONO, fontweight="bold", color=INK)
                ax.text(i, value + 0.018 * span, delta, ha="center", va="bottom", fontsize=12.5,
                        fontweight="bold", color="#e0901a")
            else:
                ax.text(i, value + 0.018 * span, text, ha="center", va="bottom", fontsize=20,
                        fontfamily=MONO, fontweight="bold", color=INK)
        cx = left + width * (i + 0.6) / 3.2
        draw_mark(mark, cx, bottom - 0.062)
        ax.text(i, -0.235, name, ha="center", va="top", fontsize=11.5, fontweight="bold", color=INK,
                transform=ax.get_xaxis_transform(), clip_on=False)
        ax.text(i, -0.295, aff, ha="center", va="top", fontsize=10.5, color=MUTED,
                transform=ax.get_xaxis_transform(), clip_on=False)
    fig.text(left + width / 2, 0.80, title, ha="center", va="center", fontsize=19, fontweight="bold", color=INK)
    fig.text(left + width / 2, 0.77, metric, ha="center", va="center", fontsize=12.5, color=MUTED)

fig.text(0.04, 0.04, "Gains calculated against the best other entry on the official RelBench leaderboard",
         ha="left", va="center", fontsize=11.5, color=MUTED)
draw_mark("leeroo", 0.915, 0.04, size=0.022)
fig.text(0.929, 0.04, "Leeroo", ha="left", va="center", fontsize=19, fontweight="bold", color=ORANGE)
fig.savefig(OUT, dpi=200, facecolor=fig.get_facecolor())
print("wrote", OUT)

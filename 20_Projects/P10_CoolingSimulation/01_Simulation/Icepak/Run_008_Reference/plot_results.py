# -*- coding: utf-8 -*-
# Run_001 figures from Export/. Static PNGs: sequential single-hue maps, one-series die profile.
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

RUN = r"C:\AnsysSim\projects\P10_CoolingSimulation\Runs\Run_008_MeshGlobal025"
EXP, FIG = os.path.join(RUN, "Export"), os.path.join(RUN, "Figure")
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE = LinearSegmentedColormap.from_list("seq_blue", ["#e6f0fb", "#7fb2ea", "#2a78d6", "#123f78"])
plt.rcParams.update({"font.family": "sans-serif", "font.size": 10, "text.color": INK,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.edgecolor": INK2, "figure.facecolor": SURF, "axes.facecolor": SURF})


def load(name):
    a = np.loadtxt(os.path.join(EXP, name + ".fld"), skiprows=2)
    xs, ys = np.unique(np.round(a[:, 0], 6)), np.unique(np.round(a[:, 1], 6))
    # the file runs x-outer, y-inner
    return xs, ys, a[:, 3].reshape(len(xs), len(ys)).T


rows = list(csv.DictReader(open(os.path.join(EXP, "object_temperatures.csv"))))
src = [r for r in rows if r["group"] in ("src_gpu", "src_base")]


def outlines(ax, sel):
    for r in sel:
        ax.add_patch(Rectangle((float(r["x"]), float(r["y"])), float(r["dx"]), float(r["dy"]),
                               fill=False, ec="#ffffff", lw=0.7, alpha=0.8))


def heat(name, title, fname, sel, size):
    xs, ys, t = load(name)
    fig, ax = plt.subplots(figsize=size, dpi=200)
    m = ax.pcolormesh(xs, ys, t, cmap=BLUE, shading="auto")
    outlines(ax, sel)
    j, i = np.unravel_index(np.argmax(t), t.shape)
    ax.plot(xs[i], ys[j], "+", color=INK, ms=9, mew=1.3)
    ax.annotate("peak %.1f °C" % t.max(), (xs[i], ys[j]), xytext=(8, 7), textcoords="offset points",
                color=INK, fontsize=9, bbox=dict(fc=SURF, ec="none", pad=1.5, alpha=0.9))
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(title, loc="left", fontsize=11)
    cb = fig.colorbar(m, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label("Temperature (°C)")
    cb.outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, fname))
    plt.close(fig)


heat("T_GPU_BEOLMXY", "GPU BEOL_MXY layer temperature (z = 0.5126 mm), heat blocks outlined",
     "20261104_HBM2p5D_MeshGlobal025_GPU_BEOLMXY_Tmap.png", [r for r in src if r["group"] == "src_gpu"], (8.2, 5.2))
heat("T_Interposer_plane", "Temperature on the z = 0.5126 mm plane: GPU and base dies, heat blocks outlined",
     "20261104_HBM2p5D_MeshGlobal025_Module_Plane_Tmap.png", src, (10, 4.4))

s = json.load(open(os.path.join(EXP, "summary.json")))["hbm_mean"]
labels = ["base"] + ["%d" % i for i in range(1, 13)]
vals = [s["base"]] + [s["D%02d" % i] for i in range(1, 13)]
fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=200)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_axisbelow(True)
ax.plot(range(13), vals, "-o", color="#2a78d6", lw=2, ms=6, label="Icepak, this run (all 4 stacks equal)")
ax.plot([0, 12], [57, 43], linestyle="none", marker="D", ms=8, mfc=SURF, mec=INK, mew=1.4,
        label="Paper, read approx. from Fig. 4c")
ax.annotate("%.1f" % vals[0], (0, vals[0]), xytext=(0, -15), textcoords="offset points", ha="center", color=INK2)
ax.annotate("%.1f" % vals[-1], (12, vals[-1]), xytext=(0, -15), textcoords="offset points", ha="center", color=INK2)
ax.annotate("~57", (0, 57), xytext=(0, 9), textcoords="offset points", ha="center", color=INK2)
ax.annotate("~43", (12, 43), xytext=(0, 9), textcoords="offset points", ha="center", color=INK2)
ax.set_xticks(range(13))
ax.set_xticklabels(labels)
ax.set_xlabel("HBM die (base, then DRAM 1 to 12)")
ax.set_ylabel("Die peak temperature (°C)")
ax.set_ylim(36, 60)
for k in ("top", "right"):
    ax.spines[k].set_visible(False)
ax.set_title("HBM die peak temperature vs paper", loc="left", fontsize=11)
ax.legend(frameon=False, loc="upper right")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "20261104_HBM2p5D_MeshGlobal025_HBM_DieProfile.png"))
plt.close(fig)
print("done")

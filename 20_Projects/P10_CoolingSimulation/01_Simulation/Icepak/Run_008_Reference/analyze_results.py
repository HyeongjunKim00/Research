# -*- coding: utf-8 -*-
# Run_001 summary numbers from Export/ (object_temperatures.csv + grid .fld files).
import csv
import json
import os

import numpy as np

RUN = r"C:\AnsysSim\projects\P10_CoolingSimulation\Runs\Run_008_MeshGlobal025"
EXP = os.path.join(RUN, "Export")
H_TOP, H_BOT, T_AMB = 30000.0, 200.0, 20.0

rows = list(csv.DictReader(open(os.path.join(EXP, "object_temperatures.csv"))))
for r in rows:
    r["Tmax"], r["Tmin"], r["P"] = float(r["Tmax_C"]), float(r["Tmin_C"]), float(r["power_W"])


def pick(f):
    return [r for r in rows if f(r)]


def ext(sel):
    return max(r["Tmax"] for r in sel), min(r["Tmin"] for r in sel)


def load(name):
    a = np.loadtxt(os.path.join(EXP, name + ".fld"), skiprows=2)
    return a


out = {}
print("total power in boxes  %.3f W" % sum(r["P"] for r in rows))
print("whole model           max %.3f  min %.3f" % ext(rows))
gpu = pick(lambda r: r["group"] in ("gpu", "src_gpu"))
print("GPU column (all)      max %.3f  min %.3f" % ext(gpu))
hot = max(gpu, key=lambda r: r["Tmax"])
print("  hottest GPU object:", hot["name"], hot["Tmax"])
for nm, sel in (("BSPDN", pick(lambda r: r["name"] == "BSPDN")),
                ("BEOL_MXY+Src", pick(lambda r: r["name"].startswith("BEOL_MXY") or r["name"].startswith("Src_GPU"))),
                ("GPU_FEOL", pick(lambda r: r["name"] == "GPU_FEOL")),
                ("BSPDN_Bond", pick(lambda r: r["name"] == "BSPDN_Bond")),
                ("GPU_Carrier", pick(lambda r: r["name"] == "GPU_Carrier")),
                ("TIM", pick(lambda r: r["name"] == "TIM")),
                ("Lid", pick(lambda r: r["name"] == "Lid")),
                ("Laminate", pick(lambda r: r["name"] == "Laminate")),
                ("Mold", pick(lambda r: r["group"] == "mold"))):
    print("  %-14s max %.3f  min %.3f" % ((nm,) + ext(sel)))
print("  GPU hotspot blocks:")
for r in pick(lambda r: r["name"].startswith("Src_GPU")):
    print("    %-14s %6.2f W  Tmax %.3f  Tmin %.3f" % (r["name"], r["P"], r["Tmax"], r["Tmin"]))

stacks = {}
for tag in ("L1", "L2", "R1", "R2"):
    base = pick(lambda r: r["name"].startswith("HBM_%s_Base" % tag) or r["name"].startswith("Src_%s_" % tag))
    d = {"base": ext(base)}
    for i in range(1, 13):
        sel = pick(lambda r: r["name"].startswith("HBM_%s_D%02d_" % (tag, i)))
        si = pick(lambda r: r["name"] == "HBM_%s_D%02d_Si" % (tag, i))
        d["D%02d" % i] = ext(sel) + ext(si)
    stacks[tag] = d
print("\nHBM die peak (degC). base = BEOL+Si+PHY/TSV blocks, Dnn = ubump+BEOL+Si of that die")
print("die    " + "".join("%8s" % t for t in stacks))
print("base   " + "".join("%8.2f" % stacks[t]["base"][0] for t in stacks))
for i in range(1, 13):
    k = "D%02d" % i
    print("%-7s" % k + "".join("%8.2f" % stacks[t][k][0] for t in stacks))
out["stacks"] = {t: {k: v[0] for k, v in stacks[t].items()} for t in stacks}

# energy balance: q = h (T - Tamb) on the two cooled faces, area weighted on a 0.5 mm grid
lid, lam = load("T_LidTop"), load("T_LamBottom")
dA = (0.5e-3) ** 2
q_top = H_TOP * np.sum(lid[:, 3] - T_AMB) * dA
q_bot = H_BOT * np.sum(lam[:, 3] - T_AMB) * dA
print("\nenergy balance: lid %.2f W + laminate %.2f W = %.2f W (in: 574.00 W)" % (q_top, q_bot, q_top + q_bot))
print("lid top surface: mean %.3f max %.3f min %.3f" % (lid[:, 3].mean(), lid[:, 3].max(), lid[:, 3].min()))
print("laminate bottom: mean %.3f max %.3f min %.3f" % (lam[:, 3].mean(), lam[:, 3].max(), lam[:, 3].min()))

g = load("T_GPU_BEOLMXY")
print("\nGPU BEOL_MXY plane: max %.3f at x=%.2f y=%.2f, min %.3f at x=%.2f y=%.2f, mean %.3f, NaNs %d"
      % (np.nanmax(g[:, 3]), g[np.nanargmax(g[:, 3]), 0], g[np.nanargmax(g[:, 3]), 1],
         np.nanmin(g[:, 3]), g[np.nanargmin(g[:, 3]), 0], g[np.nanargmin(g[:, 3]), 1],
         np.nanmean(g[:, 3]), int(np.isnan(g[:, 3]).sum())))

# comparison with the reference values given for Chen et al. (Fig. 4c read approx.)
gmax, gmin = ext(gpu)
wmax, wmin = ext(rows)
print("\nvs paper: GPU peak %.2f vs 69.1 (%+.2f degC, %+.1f%% of rise above 20)"
      % (gmax, gmax - 69.1, 100 * (gmax - 69.1) / (69.1 - 20)))
print("          map min: GPU %.2f, whole model %.2f vs 20.3" % (gmin, wmin))
avg = {k: np.mean([stacks[t][k][0] for t in stacks]) for k in stacks["L1"]}
print("          HBM base mean of 4 stacks %.2f vs ~57 (%+.2f); D12 %.2f vs ~43 (%+.2f)"
      % (avg["base"], avg["base"] - 57, avg["D12"], avg["D12"] - 43))
out.update(gpu_max=gmax, gpu_min=gmin, model_min=wmin, q_top=q_top, q_bot=q_bot, hbm_mean=avg)
json.dump(out, open(os.path.join(EXP, "summary.json"), "w"), indent=1)

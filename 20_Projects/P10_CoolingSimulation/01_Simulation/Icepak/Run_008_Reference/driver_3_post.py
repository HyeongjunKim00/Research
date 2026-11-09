# -*- coding: utf-8 -*-
# Run_001 post driver: per-object Tmax/Tmin (field calculator), temperature on grids,
# mesh statistics, solver profile, convergence.  Every step is independent.
import csv
import io
import os
import traceback

MODEL = r"C:\AnsysSim\projects\P10_CoolingSimulation\Runs\Run_008_MeshGlobal025\Model"
EXPORT = os.path.join(os.path.dirname(MODEL), "Export")
AEDT = os.path.join(MODEL, "20261104_HBM2p5D_MeshGlobal025.aedt")
GEOM = os.path.join(MODEL, "hbm_gpu_2p5d_geometry.csv")
DONE = os.path.join(EXPORT, "post_done.txt")
SOLUTION = "Setup1 : SteadyState"
QTY = "Temp"
log = []


def step(label, fn):
    try:
        r = fn()
        log.append("OK    %s  %s" % (label, "" if r is None else r))
        return r
    except Exception:
        log.append("FAIL  %s\n%s" % (label, traceback.format_exc()))
        return None


def write_log():
    fh = io.open(os.path.join(EXPORT, "post_log.txt"), "w", encoding="utf-8")
    fh.write(u"\n".join(log) + u"\n")
    fh.close()


def calc(oFR, obj, op, tmp):
    oFR.CalcStack("clear")
    oFR.EnterQty(QTY)
    oFR.EnterVol(obj)
    oFR.CalcOp(op)
    oFR.CalculatorWrite(tmp, ["Solution:=", SOLUTION], [])
    fh = open(tmp, "r")
    lines = [ln.strip() for ln in fh.readlines() if ln.strip()]
    fh.close()
    os.remove(tmp)
    oFR.CalcStack("clear")
    return float(lines[-1])


def grid(oFR, name, x0, x1, y0, y1, z, step_mm):
    path = os.path.join(EXPORT, name + ".fld")
    oFR.CalcStack("clear")
    oFR.EnterQty(QTY)
    oFR.ExportOnGrid(path,
                     ["%.6fmm" % x0, "%.6fmm" % y0, "%.6fmm" % z],
                     ["%.6fmm" % x1, "%.6fmm" % y1, "%.6fmm" % z],
                     ["%.6fmm" % step_mm, "%.6fmm" % step_mm, "%.6fmm" % step_mm],
                     SOLUTION, [],
                     ["NAME:ExportOption", "IncludePtInOutput:=", True, "RefCSName:=", "Global",
                      "PtInSI:=", False, "FieldInRefCS:=", True],
                     "Cartesian", ["0mm", "0mm", "0mm"], False)
    oFR.CalcStack("clear")
    return "%s exists=%s" % (path, os.path.exists(path))


try:
    oProject = oDesktop.OpenProject(AEDT)
    oDesign = oProject.SetActiveDesign("HBM_GPU_2p5D")
    oFR = oDesign.GetModule("FieldsReporter")

    step("mesh stats", lambda: oDesign.ExportMeshStats("Setup1", "", os.path.join(EXPORT, "mesh_stats.txt")))
    step("profile", lambda: oDesign.ExportProfile("Setup1", "", os.path.join(EXPORT, "profile.prof")))
    step("convergence", lambda: oDesign.ExportConvergence("Setup1", "", os.path.join(EXPORT, "convergence.txt")))

    fh = open(GEOM, "r")
    objs = list(csv.DictReader(fh))
    fh.close()
    tmp = os.path.join(EXPORT, "_tmp.fld")
    out = open(os.path.join(EXPORT, "object_temperatures.csv"), "w")
    out.write("name,group,x,y,z,dx,dy,dz,power_W,Tmax_C,Tmin_C\n")
    nfail = 0
    for o in objs:
        try:
            tx = calc(oFR, o["name"], "Maximum", tmp)
            tn = calc(oFR, o["name"], "Minimum", tmp)
        except Exception:
            nfail += 1
            if nfail == 1:
                log.append("FAIL first calc %s\n%s" % (o["name"], traceback.format_exc()))
            tx, tn = float("nan"), float("nan")
        out.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%.6f,%.6f\n"
                  % (o["name"], o["group"], o["x"], o["y"], o["z"], o["dx"], o["dy"], o["dz"],
                     o["power_W"], tx, tn))
        out.flush()
    out.close()
    log.append("objects %d, calc failures %d" % (len(objs), nfail))

    write_log()
    # BEOL_MXY mid-plane (GPU hotspot layer, also inside the HBM base BEOL layer)
    z_mxy = 0.511865 + 0.0014 / 2.0
    step("grid GPU", lambda: grid(oFR, "T_GPU_BEOLMXY", 17.55, 47.45, 21.55, 43.45, z_mxy, 0.1))
    step("grid module", lambda: grid(oFR, "T_Interposer_plane", 5.6, 59.4, 20.6, 44.4, z_mxy, 0.2))
    # just inside the two cooled faces, for the energy balance
    step("grid lid top", lambda: grid(oFR, "T_LidTop", 0.25, 64.75, 0.25, 64.75, 4.4449, 0.5))
    step("grid lam bottom", lambda: grid(oFR, "T_LamBottom", 0.25, 64.75, 0.25, 64.75, 0.0001, 0.5))
    fh = io.open(os.path.join(EXPORT, "post_messages.txt"), "w", encoding="utf-8")
    for m in oDesktop.GetMessages("", "", 0):
        fh.write(u"%s\n" % (m,))
    fh.close()
except Exception:
    log.append("FATAL\n" + traceback.format_exc())
finally:
    write_log()
    fh = open(DONE, "w")
    fh.write("finished\n")
    fh.close()

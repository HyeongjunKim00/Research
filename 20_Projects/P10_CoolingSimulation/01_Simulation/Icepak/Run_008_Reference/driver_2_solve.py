# -*- coding: utf-8 -*-
# Run_001 solve driver: opens the built project and solves Setup1.
import io
import os
import time
import traceback

MODEL = r"C:\AnsysSim\projects\P10_CoolingSimulation\Runs\Run_008_MeshGlobal025\Model"
EXPORT = os.path.join(os.path.dirname(MODEL), "Export")
AEDT = os.path.join(MODEL, "20261104_HBM2p5D_MeshGlobal025.aedt")
DONE = os.path.join(EXPORT, "solve_done.txt")


def dump_messages(tag):
    fh = io.open(os.path.join(EXPORT, "solve_messages_%s.txt" % tag), "w", encoding="utf-8")
    try:
        for m in oDesktop.GetMessages("", "", 0):
            fh.write(u"%s\n" % (m,))
    finally:
        fh.close()


status = "FAILED"
t0 = time.time()
try:
    oProject = oDesktop.OpenProject(AEDT)
    oDesign = oProject.SetActiveDesign("HBM_GPU_2p5D")
    oDesign.Analyze("Setup1")
    oProject.Save()
    dump_messages("ok")
    status = "OK"
except Exception:
    fh = io.open(os.path.join(EXPORT, "solve_traceback.txt"), "w", encoding="utf-8")
    fh.write(traceback.format_exc())
    fh.close()
    try:
        dump_messages("fail")
    except Exception:
        pass
finally:
    fh = open(DONE, "w")
    fh.write("%s\nwall_clock_s %.1f\n" % (status, time.time() - t0))
    fh.close()

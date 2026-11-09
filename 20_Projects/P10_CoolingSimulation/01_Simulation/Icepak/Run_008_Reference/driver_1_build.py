# -*- coding: utf-8 -*-
# Run_001 build driver: new project + Icepak design, then runs hbm_gpu_2p5d.py UNMODIFIED.
# Launched by: ansysedt.exe -ng -RunScriptAndExit driver_1_build.py
import io
import os
import traceback

MODEL = r"C:\AnsysSim\projects\P10_CoolingSimulation\Runs\Run_008_MeshGlobal025\Model"
EXPORT = os.path.join(os.path.dirname(MODEL), "Export")
AEDT = os.path.join(MODEL, "20261104_HBM2p5D_MeshGlobal025.aedt")
USER_SCRIPT = os.path.join(MODEL, "hbm_gpu_2p5d.py")
DONE = os.path.join(EXPORT, "build_done.txt")


def dump_messages(tag):
    fh = io.open(os.path.join(EXPORT, "build_messages_%s.txt" % tag), "w", encoding="utf-8")
    try:
        for m in oDesktop.GetMessages("", "", 0):
            fh.write(u"%s\n" % (m,))
    finally:
        fh.close()


status = "FAILED"
try:
    oProject = oDesktop.NewProject()
    oProject.SaveAs(AEDT, True)
    oDesign = oProject.InsertDesign("Icepak", "HBM_GPU_2p5D", "SteadyState TemperatureAndFlow", "")
    # AEDT 2026 R1 auto-creates a default Region in a new Icepak design; the user script
    # stops on any existing solid (ALLOW_OVERWRITE = False) and builds its own Region anyway.
    oDesign.SetActiveEditor("3D Modeler").Delete(["NAME:Selections", "Selections:=", "Region"])
    fh = io.open(USER_SCRIPT, "r", encoding="utf-8")
    src = fh.read()
    fh.close()
    g = {"__name__": "__main__", "__file__": USER_SCRIPT, "oDesktop": oDesktop}
    exec(compile(src, USER_SCRIPT, "exec"), g)
    oProject.Save()
    dump_messages("ok")
    status = "OK"
except Exception:
    fh = io.open(os.path.join(EXPORT, "build_traceback.txt"), "w", encoding="utf-8")
    fh.write(traceback.format_exc())
    fh.close()
    try:
        dump_messages("fail")
    except Exception:
        pass
finally:
    fh = open(DONE, "w")
    fh.write(status + "\n")
    fh.close()

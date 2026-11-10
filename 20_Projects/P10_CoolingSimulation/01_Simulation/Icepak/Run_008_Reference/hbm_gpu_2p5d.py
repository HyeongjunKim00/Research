# -*- coding: utf-8 -*-
"""
hbm_gpu_2p5d.py  -  Chen et al., "Breaking Thermal Bottleneck in 3D
                    HBM-on-GPU Integration via System-Technology
                    Co-Optimization", IEDM 2025.  **2.5D baseline (Fig. 2)**
                    를 Ansys Icepak (AEDT 2026 R1) 에 짓는다.

  AEDT  >  Automation  >  Run Script...  >  이 파일
  (빈 프로젝트에 Icepak 디자인 하나 넣어 두고 실행)

  AEDT 밖에서 python 으로 돌리면 형상만 계산해서 겹침/두께/전력을 검사하고
  단면도·평면도·발열원 배치도(SVG)와 리포트를 쓴다.

논문 그대로인 것 (출처는 각 상수 옆에: [T] Fig. 2c 표, [L] Fig. 2a 배치, [S] 본문)
  - laminate 65x65, Cu pillar, interposer 54x24, interposer BEOL
  - GPU 30x22 : uBump / BSPDN / FEOL / BEOL_MXY / BSPDN bonding / Si carrier
  - HBM 4 stacks (11x11 base die + 12 DRAM dies), GPU 양옆 2개씩,
    GPU-HBM 0.1 mm, 가장자리 0.9/1.0 mm mold
  - TIM 200 um, lid 3 mm; lid 윗면 30000 W/m2K, laminate 아랫면 200 W/m2K, 20 degC
  - 층 두께와 열전도율 (아래 예외 빼고)

논문에서 바꾼 것 (요청)
  - DRAM 단: hybrid bonding 2 um 을 없애고 microbump 15 um 을 넣음.
    늘어난 13 um 만큼 DRAM Si 를 줄임: 41 -> 28 um, top die 169 -> 156 um.
    DRAM BEOL 3 um 은 그대로.  단 높이 46 / 174 um 은 그대로라 GPU 기둥과 맞음.
    microbump 물성은 GPU-HBM uBump 와 같은 im_uBump (0.59 / 19.28).
  - 발열 (전부 실제 두께가 있는 층을 평면에서 쪼갠 Block, 시트 없음)
      GPU 배경  : BSPDN 층 전체에 균일        P_GPU * GPU_BG_FRAC
      GPU 핫스팟: BEOL_MXY 층을 쪼갠 블록 12개가 나머지를 나눠 가짐
                  2행 x [GPC, GPC, NV-HBI, GPC, GPC] 10개 (전력 비 1) +
                  양쪽 가장자리 NVLink 2개 (전력 비 0.5), Blackwell 다이어그램 배치
      base die  : base BEOL 층을 쪼갠 PHY + TSV&I/O 블록
                  (Son et al., EDAPS 2023 logic die 배치).  PHY 방향은
                  PHY_FACE: "gpu" (원래, 각 스택이 GPU 쪽) | "-y" | "+y".
      DRAM die  : Si 층 전체에 균일
      HBM 전력  : 기준 PHY 4 / TSV 2 / DRAM 2 W x 12 = 30 W 를 논문의 40 W 로
                  선형 확대 (x 4/3) -> PHY 5.333 / TSV 2.667 / DRAM 2.667 W

논문이 안 정해줘서 여기서 정한 것 (전부 상수로 노출)
  - DRAM die 크기 10.8 x 10.8 (논문 "~11", Fig. 5a 의 0.1 mm mold 테두리)
  - GPU 핫스팟 크기/간격/배경 비율 (GPU_BLOB_*, GPU_BG_FRAC): 열지도 모양만 보고
    잡은 값.  논문의 0.5 mm power map 은 비공개.
  - lid = laminate 65x65, TIM = interposer 54x24 (Fig. 2b 비율)

IronPython 2.7 (AEDT) 과 CPython 3 양쪽에서 돈다.  AddMessage 로 가는 문자열은
ASCII 만 (이 AEDT 빌드가 한글에서 예외를 던진다).
"""
import math
import os
import sys

# ==========================================================================
#  스위치
# ==========================================================================
SYMMETRY      = "none"     # "none" = 논문처럼 전체 모듈 | "quarter" = 1/4
GROUP_SOURCES = False      # False = 발열 물체마다 Block 하나
COOL_TOP      = True       # lid 윗면 Wall
LIDLESS       = False      # True = 힛스프레더 제거, HTC 를 TIM 상면에 직접 (Phase 2 lid vs lidless)
COOL_BOTTOM   = True       # laminate 아랫면 Wall (논문: 200 W/m2K 공랭)
AUTO_MESH     = True
ALLOW_OVERWRITE = False    # 디자인에 이미 solid 가 있으면 멈춘다
CLEAN_FIRST   = True
BATCH_UNDO    = True
PREFIX        = "im_"
SURFACE_MATERIAL = "Steel-oxidised-surface"

# ==========================================================================
#  치수 (mm)
# ==========================================================================
LAM_W, LAM_H = 65.0, 65.0          # [L]
INT_W, INT_H = 54.0, 24.0          # [L]
GPU_W, GPU_H = 30.0, 22.0          # [L]
BASE_W, BASE_H = 11.0, 11.0        # [L]  HBM base die
DRAM_W, DRAM_H = 10.8, 10.8        # 논문 "~11", Fig. 5(a) 0.1 mm mold 테두리
GAP_GPU_HBM  = 0.1                 # [L]
MARGIN_X     = 0.9                 # [L]  base die <-> interposer 가장자리 (x)
MARGIN_Y     = 1.0                 # [L]  (y)
HBM_ROW_GAP  = 0.0                 # 같은 열의 base die 두 장 사이 (24 = 1+11+11+1)
N_DRAM       = 12                  # [S]
LID_W, LID_H = LAM_W, LAM_H
TIM_W, TIM_H = INT_W, INT_H

#  두께 (mm)
T_LID        = 3.000     # [T]
T_TIM        = 0.200     # [T]
T_DRAM_UBUMP = 0.015     # 요청: hybrid bonding 2 um 대신 microbump 15 um
T_DRAM_SI    = 0.028     # 요청: 41 - 13
T_DRAM_TOP   = 0.156     # 요청과 같은 규칙: 169 - 13  (단 높이 유지)
T_DRAM_BEOL  = 0.003     # [T] 그대로
T_BASE_SI    = 0.050     # [T]
T_BASE_BEOL  = 0.005     # [T]
T_UBUMP      = 0.040     # [T]  GPU-HBM / HBM-interposer uBump
T_CARRIER    = 0.731235  # [T]
T_BSPDN_BOND = 0.0005    # [T]
T_BEOL_MXY   = 0.0014    # [T]
T_FEOL       = 0.00015   # [T]
T_BSPDN      = 0.001715  # [T]
T_INT_BEOL   = 0.005     # [T]
T_INT        = 0.095     # [T]
T_CUPILLAR   = 0.070     # [T]
T_LAM        = 0.300     # [T]

#  열전도율 (W/m-K)  [T]   (k_inplane, k_crossplane)
K = {
    "Lid":        (400.0,  400.0),
    "TIM":        (9.71,   9.71),
    "Si":         (140.0,  140.0),    # DRAM Si, base Si, GPU carrier, interposer
    "DRAM_BEOL":  (0.85,   0.85),
    "Base_BEOL":  (1.5,    1.5),
    "uBump":      (0.59,   19.28),    # GPU-HBM uBump; DRAM 사이 microbump 도 이것
    "BSPDN_Bond": (1.4,    1.4),
    "BEOL_MXY":   (1.5,    1.5),
    "FEOL":       (7.9,    7.9),
    "BSPDN":      (83.0,   71.0),
    "Int_BEOL":   (1.2,    1.2),
    "CuPillar":   (0.54,   13.25),
    "Laminate":   (13.0,   13.0),
    "Mold":       (3.0,    3.0),      # [S]
}

# ==========================================================================
#  전력 (W)
# ==========================================================================
P_GPU   = 414.0            # [S]  = BSPDN 배경 + BEOL_MXY 핫스팟 10개

#  HBM: 기준값 (Son et al. 그림의 PHY 4 W + TSV&I/O 2 W, DRAM 2 W x 12 = 30 W 스택당)
#  을 논문의 40 W 스택당 [S] 에 맞춰 선형으로 키운다.  배율 40/30 = 1.333.
P_HBM_REF    = 30.0
P_HBM        = 40.0                        # 스택당 목표 [S]
HBM_SCALE    = P_HBM / P_HBM_REF
P_PHY_REF, P_TSV_REF, P_DRAM_REF = 4.0, 2.0, 2.0
P_PHY   = P_PHY_REF  * HBM_SCALE           # 5.333 W  base BEOL 블록
P_TSV   = P_TSV_REF  * HBM_SCALE           # 2.667 W  base BEOL 블록
P_DRAM  = P_DRAM_REF * HBM_SCALE           # 2.667 W  DRAM die 한 장, Si 층 균일
P_BASE  = P_PHY + P_TSV                    # 8 W
assert abs(P_BASE + N_DRAM * P_DRAM - P_HBM) < 1e-9

#  base die: Son et al. logic die 배치.  base die 한 변을 1 로 본 (x0, y0, x1, y1).
#  그림에서 픽셀로 잰 값.  그림 그대로면 PHY 가 -x 쪽(왼쪽)에 있다.
PHY_RECT = (0.270, 0.161, 0.403, 0.839)    # 1.46 x 7.45 mm on 11 mm
TSV_RECT = (0.414, 0.025, 0.589, 0.975)    # 1.93 x 10.45 mm on 11 mm

#  PHY 가 어느 쪽을 보게 할지.  base die 배치 전체를 그 방향으로 돌린다.
#    "gpu" : 각 스택의 PHY 가 GPU 쪽 (왼쪽 스택 +x, 오른쪽 스택 -x)   <- 원래 설정
#    "-y"  : 네 스택 모두 아래 (AEDT Top 뷰 기준 아래, y 작은 쪽)
#    "+y"  : 네 스택 모두 위
#  모듈이 y 로 대칭이라 "-y" 와 "+y" 는 서로 거울상이고 온도 결과도 같다.
#  "-y"/"+y" 는 y 대칭을 깨므로 SYMMETRY = "quarter" 와 같이 쓸 수 없다.
PHY_FACE = "gpu"

#  GPU: 배경(BSPDN) + BEOL_MXY 층의 블록들
#    핫스팟 10개 = 2행 x [GPC, GPC, NV-HBI, GPC, GPC]  (Blackwell 다이어그램의
#    초록 GPC 와 보라 NV-HBI 를 본뜬 것).
#    edge I/O: HBM 이 GPU 좌·우(±x)에 붙으므로 GPU-측 HBM PHY 를 좌·우 edge
#    (HBM 마주보는 면)에 둔다.
#    [2026-11-10] 이전엔 NVLink 를 HBM 쪽 좌·우 edge 에 뒀는데, 논문 본문
#    "HBM interfaces block two sides of each GPU and prevent additional
#    GPU-to-GPU connections" 와 상충.  이 4-HBM 패키지는 GPU-GPU 연결이 막혀
#    NVLink 를 넣을 근거가 약하므로 **NVLink 제거**, HBM 쪽 edge 엔 (물리적으로
#    맞는) GPU-측 HBM PHY 만 둔다.  NVLink 몫은 정규화로 compute+PHY 가 흡수(총 414 W
#    불변).  발열맵은 [추론] (논문 비공개).
#    핫스팟 몫 P_GPU*(1-GPU_BG_FRAC) 를 아래 전력 비(W)로 12개가 나눠 갖는다.
GPU_BG_FRAC     = 0.5                # 414 W 중 BSPDN 층에 균일하게 까는 몫
GPU_ROWS_Y      = (0.275, 0.725)     # 행 중심, GPU 세로(22 mm)를 1 로.
                                     #  7.7 mm 두 행이 2.2 mm 씩 띄고 들어간다:
                                     #  2.2 + 7.7 + 2.2 + 7.7 + 2.2 = 22
GPU_BLOB_PITCH  = 5.0                # 이웃 핫스팟 중심 간격 (mm)
GPU_BLOB_BIG    = (4.0, 7.7)         # 가운데 NV-HBI (x, y) mm  (5 -> 4, 요청)
GPU_BLOB_SMALL  = (3.0, 7.7)         # GPC.  y 7.7 (요청)
GPU_BLOB_DENS   = (1, 1, 1.25, 1, 1) # 전력밀도 비 (한 행, 바깥 -> 가운데 -> 바깥).
                                     #  전력 = 밀도 x 면적 이라 크기를 바꿔도 밀도 비가 유지된다
GPU_PHY_SIZE    = (1.5, 17.0)        # GPU-측 HBM PHY: 좌·우 edge 세로 스트립 (x,y) mm [추론]
GPU_PHY_W       = 0.5                # PHY 전력 비: 밀도 1 인 작은 핫스팟(GPC)의 절반
GPU_EDGE_GAP    = 0.2                # edge 스트립을 GPU 가장자리에서 띄우는 양 (mm)

#  냉각  [S]
H_TOP    = 30000.0
H_BOTTOM = 200.0
T_AMB    = 20.0

#  메시
MESH_MAX     = (0.25, 0.25, 0.25)
MESH_GAP     = (0.01, 0.01, 0.0001)      # z 0.1 um: FEOL 0.15 um 이 살아야 한다
MESH_DIE_MAX = (0.5, 0.5, 0.02)          # die 영역: z 20 um -> 28 um Si 에 2셀
MESH_DIE_PAD = 0.25
MESH_RATIO   = 2
MESH_GAP_N   = 1
MESH_EDGE_N  = 1

# ==========================================================================
#  작은 도구
# ==========================================================================
def r9(v):
    return round(float(v), 9)


def mm(v):
    return "%.9gmm" % float(v)


COLORS = {
    "Lid": (170, 220, 170), "TIM": (250, 215, 160), "Si": (120, 170, 220),
    "DRAM_BEOL": (200, 190, 220), "Base_BEOL": (190, 180, 210),
    "uBump": (90, 160, 140), "BSPDN_Bond": (140, 190, 120), "BEOL_MXY": (230, 120, 140),
    "FEOL": (250, 110, 110), "BSPDN": (250, 170, 170), "Int_BEOL": (200, 200, 230),
    "CuPillar": (70, 150, 130), "Laminate": (190, 210, 140), "Mold": (215, 215, 200),
}


def material_table():
    """(name, k_inplane, k_cross, rgb)"""
    out = []
    for k in ("Lid", "TIM", "Si", "DRAM_BEOL", "Base_BEOL", "uBump",
              "BSPDN_Bond", "BEOL_MXY", "FEOL", "BSPDN", "Int_BEOL",
              "CuPillar", "Laminate", "Mold"):
        out.append((PREFIX + k, K[k][0], K[k][1], COLORS[k]))
    return out


# ==========================================================================
#  형상
# ==========================================================================
def complement(outer, holes):
    """outer 사각형에서 holes 를 뺀 나머지를 서로 안 겹치는 사각형들로."""
    x0, y0, x1, y1 = outer
    xs = sorted(set([x0, x1] + [h[0] for h in holes] + [h[2] for h in holes]))
    ys = sorted(set([y0, y1] + [h[1] for h in holes] + [h[3] for h in holes]))
    xs = [r9(v) for v in xs if x0 - 1e-9 <= v <= x1 + 1e-9]
    ys = [r9(v) for v in ys if y0 - 1e-9 <= v <= y1 + 1e-9]

    def free(i, j):
        cx = (xs[i] + xs[i + 1]) / 2.0
        cy = (ys[j] + ys[j + 1]) / 2.0
        for h in holes:
            if h[0] < cx < h[2] and h[1] < cy < h[3]:
                return False
        return True

    rects = []
    for i in range(len(xs) - 1):
        j = 0
        while j < len(ys) - 1:
            if not free(i, j):
                j += 1
                continue
            k = j
            while k < len(ys) - 1 and free(i, k):
                k += 1
            rects.append([xs[i], ys[j], xs[i + 1], ys[k]])
            j = k
    merged = True
    while merged:
        merged = False
        for a in range(len(rects)):
            for b in range(len(rects)):
                if a == b:
                    continue
                A, B = rects[a], rects[b]
                if (abs(A[1] - B[1]) < 1e-9 and abs(A[3] - B[3]) < 1e-9
                        and abs(A[2] - B[0]) < 1e-9):
                    rects[a] = [A[0], A[1], B[2], A[3]]
                    del rects[b]
                    merged = True
                    break
            if merged:
                break
    return rects


def build():
    """상자 목록과 배치 요약.  좌표계: laminate 왼쪽 아래 모서리가 (0,0,0)."""
    boxes = []

    def B(name, x, y, z, dx, dy, dz, mat, power=0.0, grp=""):
        boxes.append(dict(name=name, x=r9(x), y=r9(y), z=r9(z),
                          dx=r9(dx), dy=r9(dy), dz=r9(dz),
                          mat=PREFIX + mat, power=float(power), grp=grp))

    cx, cy = LAM_W / 2.0, LAM_H / 2.0
    L = {}

    # ---- 공통 판들 -------------------------------------------------------
    z = 0.0
    B("Laminate", 0, 0, z, LAM_W, LAM_H, T_LAM, "Laminate", grp="sub");      z += T_LAM
    xi, yi = cx - INT_W / 2.0, cy - INT_H / 2.0
    B("CuPillar",   xi, yi, z, INT_W, INT_H, T_CUPILLAR, "CuPillar", grp="sub"); z += T_CUPILLAR
    B("Interposer", xi, yi, z, INT_W, INT_H, T_INT,      "Si",       grp="sub"); z += T_INT
    B("IntBEOL",    xi, yi, z, INT_W, INT_H, T_INT_BEOL, "Int_BEOL", grp="sub"); z += T_INT_BEOL
    z_int_top = r9(z)
    L.update(xi=xi, yi=yi, z_int_top=z_int_top)

    # ---- GPU 기둥 --------------------------------------------------------
    #  배경 전력은 BSPDN 층 전체에, 핫스팟은 BEOL_MXY 층을 쪼개서 (아래 split_hosts)
    xg, yg = cx - GPU_W / 2.0, cy - GPU_H / 2.0
    zg = z_int_top
    gpu = [("GPU_uBump",    T_UBUMP,      "uBump",      0.0),
           ("BSPDN",        T_BSPDN,      "BSPDN",      P_GPU * GPU_BG_FRAC),
           ("GPU_FEOL",     T_FEOL,       "FEOL",       0.0),
           ("BEOL_MXY",     T_BEOL_MXY,   "BEOL_MXY",   0.0),
           ("BSPDN_Bond",   T_BSPDN_BOND, "BSPDN_Bond", 0.0),
           ("GPU_Carrier",  T_CARRIER,    "Si",         0.0)]
    for nm, t, mat, pw in gpu:
        B(nm, xg, yg, zg, GPU_W, GPU_H, t, mat, pw, grp="gpu")
        zg = r9(zg + t)
    z_gpu_top = zg
    L.update(xg=xg, yg=yg, z_gpu_top=z_gpu_top)

    # ---- HBM 스택 4개 ----------------------------------------------------
    x_bL = xg - GAP_GPU_HBM - BASE_W
    x_bR = xg + GPU_W + GAP_GPU_HBM
    y_b0 = cy - (2 * BASE_H + HBM_ROW_GAP) / 2.0
    y_b1 = y_b0 + BASE_H + HBM_ROW_GAP
    stacks = [("L1", x_bL, y_b0), ("L2", x_bL, y_b1),
              ("R1", x_bR, y_b0), ("R2", x_bR, y_b1)]
    L.update(x_bL=x_bL, x_bR=x_bR, y_b0=y_b0, y_b1=y_b1, stacks=stacks)

    z_base_top = None
    for tag, xb, yb in stacks:
        zh = z_int_top
        for nm, t, mat, pw in [("HBM_%s_uBump" % tag,    T_UBUMP,     "uBump",     0.0),
                               ("HBM_%s_BaseBEOL" % tag, T_BASE_BEOL, "Base_BEOL", 0.0),
                               ("HBM_%s_BaseSi" % tag,   T_BASE_SI,   "Si",        0.0)]:
            B(nm, xb, yb, zh, BASE_W, BASE_H, t, mat, pw, grp="base")
            zh = r9(zh + t)
        z_base_top = zh
        xd = xb + (BASE_W - DRAM_W) / 2.0
        yd = yb + (BASE_H - DRAM_H) / 2.0
        for i in range(1, N_DRAM + 1):
            t_si = T_DRAM_TOP if i == N_DRAM else T_DRAM_SI
            for nm, t, mat, pw in [("HBM_%s_D%02d_uBump" % (tag, i), T_DRAM_UBUMP, "uBump",     0.0),
                                   ("HBM_%s_D%02d_BEOL" % (tag, i),  T_DRAM_BEOL,  "DRAM_BEOL", 0.0),
                                   ("HBM_%s_D%02d_Si" % (tag, i),    t_si,         "Si",        P_DRAM)]:
                B(nm, xd, yd, zh, DRAM_W, DRAM_H, t, mat, pw, grp="dram")
                zh = r9(zh + t)
        L["z_hbm_top"] = zh
    L["z_base_top"] = z_base_top

    if abs(L["z_hbm_top"] - z_gpu_top) > 1e-9:
        raise ValueError("HBM top %.6f != GPU top %.6f mm: the carrier thickness "
                         "no longer matches the stack" % (L["z_hbm_top"], z_gpu_top))
    z_die_top = z_gpu_top

    # ---- mold ------------------------------------------------------------
    outer = (xi, yi, r9(xi + INT_W), r9(yi + INT_H))
    gpu_hole = (xg, yg, r9(xg + GPU_W), r9(yg + GPU_H))
    base_holes = [(xb, yb, r9(xb + BASE_W), r9(yb + BASE_H)) for _t, xb, yb in stacks]
    dram_holes = [(r9(xb + (BASE_W - DRAM_W) / 2.0), r9(yb + (BASE_H - DRAM_H) / 2.0),
                   r9(xb + (BASE_W + DRAM_W) / 2.0), r9(yb + (BASE_H + DRAM_H) / 2.0))
                  for _t, xb, yb in stacks]
    n = 0
    for (za, zb, holes) in ((z_int_top, z_base_top, [gpu_hole] + base_holes),
                            (z_base_top, z_die_top, [gpu_hole] + dram_holes)):
        for rx0, ry0, rx1, ry1 in complement(outer, holes):
            n += 1
            B("Mold_%02d" % n, rx0, ry0, za, rx1 - rx0, ry1 - ry0, zb - za, "Mold", grp="mold")

    # ---- TIM, lid ----------------------------------------------------------
    B("TIM", cx - TIM_W / 2.0, cy - TIM_H / 2.0, z_die_top, TIM_W, TIM_H, T_TIM, "TIM", grp="hs")
    z_lid = r9(z_die_top + T_TIM)
    if LIDLESS:
        z_top = z_lid                      # 힛스프레더 없음: TIM 상면이 냉각면
    else:
        B("Lid", cx - LID_W / 2.0, cy - LID_H / 2.0, z_lid, LID_W, LID_H, T_LID, "Lid", grp="hs")
        z_top = r9(z_lid + T_LID)
    L.update(z_die_top=z_die_top, z_lid=z_lid, z_top=z_top, cx=cx, cy=cy)

    # ---- 발열 블록: 층을 평면에서 쪼갠다 -------------------------------------
    srcs = sources(L)
    boxes = split_hosts(boxes, srcs)
    L["n_src"] = len(srcs)

    if SYMMETRY == "quarter":
        boxes = clip_quarter(boxes, cx, cy)
    return boxes, L


def phy_face(tag):
    """스택 tag 의 PHY 가 볼 방향: '+x' | '-x' | '+y' | '-y'."""
    if PHY_FACE == "gpu":
        return "+x" if tag.startswith("L") else "-x"     # GPU 는 L 스택의 +x 쪽
    if PHY_FACE in ("-y", "+y"):
        return PHY_FACE
    raise ValueError("PHY_FACE must be 'gpu', '-y' or '+y', not %r" % (PHY_FACE,))


def orient(rect, face):
    """Son et al. 그림(PHY 가 -x 쪽)의 상대 좌표 rect 를 face 방향으로 돌린다.
    base die 중심(0.5, 0.5) 기준 회전/반전이라 결과도 0..1 안에 있다."""
    x0, y0, x1, y1 = rect
    if face == "-x":                       # 그림 그대로
        return (x0, y0, x1, y1)
    if face == "+x":                       # 좌우 반전
        return (1.0 - x1, y0, 1.0 - x0, y1)
    if face == "-y":                       # 반시계 90도: (x, y) -> (1 - y, x)
        return (1.0 - y1, x0, 1.0 - y0, x1)
    if face == "+y":                       # 시계 90도:   (x, y) -> (y, 1 - x)
        return (y0, 1.0 - x1, y1, 1.0 - x0)
    raise ValueError("unknown face %r" % (face,))


def sources(L):
    """발열 블록 목록: dict(name, x, y, dx, dy, power, host, grp).
    z 는 host 층의 것을 그대로 쓴다 (층 두께 = 블록 두께)."""
    out = []

    def S(name, x, y, dx, dy, pw, host, grp):
        out.append(dict(name=name, x=r9(x), y=r9(y), dx=r9(dx), dy=r9(dy),
                        power=float(pw), host=host, grp=grp))

    # base die: PHY / TSV&I/O 를 base BEOL 층에, PHY_FACE 방향으로 돌려서.
    for tag, xb, yb in L["stacks"]:
        for nm, rect, pw in (("PHY", PHY_RECT, P_PHY), ("TSV", TSV_RECT, P_TSV)):
            rx0, ry0, rx1, ry1 = orient(rect, phy_face(tag))
            S("Src_%s_%s" % (tag, nm), xb + rx0 * BASE_W, yb + ry0 * BASE_H,
              (rx1 - rx0) * BASE_W, (ry1 - ry0) * BASE_H, pw, "HBM_%s_BaseBEOL" % tag, "src_base")

    # GPU: 핫스팟 2행 x 5개(compute) + HBM PHY 2개(좌·우 edge, HBM 마주봄)
    #  + NVLink 2개(위·아래 edge, HBM 없는 면), 전부 BEOL_MXY 층에.
    #  핫스팟 몫 p_hot 을 가중치로 나눈다.  compute 가중치 = 밀도비 x 면적,
    #  edge(PHY/NVLink) 가중치 = 비율 x (밀도 1 인 작은 핫스팟의 가중치).
    p_hot = P_GPU * (1.0 - GPU_BG_FRAC)
    nb = len(GPU_BLOB_DENS)
    blobs = []
    for r, yf in enumerate(GPU_ROWS_Y):
        yc = L["yg"] + yf * GPU_H
        for k, dens in enumerate(GPU_BLOB_DENS):
            off = (k - (nb - 1) / 2.0) * GPU_BLOB_PITCH
            w, h = GPU_BLOB_BIG if k == (nb - 1) // 2 else GPU_BLOB_SMALL
            xc = L["xg"] + GPU_W / 2.0 + off
            blobs.append(("Src_GPU_R%d_%d" % (r + 1, k + 1), xc - w / 2.0, yc - h / 2.0,
                          w, h, dens * w * h))
    w_small = GPU_BLOB_SMALL[0] * GPU_BLOB_SMALL[1]          # 밀도 1 x 작은 면적
    w_phy = GPU_PHY_W * w_small
    wsum = sum([b[5] for b in blobs]) + 2 * w_phy
    for nm, x, y, w, h, wt in blobs:
        S(nm, x, y, w, h, p_hot * wt / wsum, "BEOL_MXY", "src_gpu")
    # GPU-측 HBM PHY: 좌·우 edge 세로 스트립 (HBM 을 마주보는 ±x 면). NVLink 는 제거.
    pw_x, pw_y = GPU_PHY_SIZE
    yp = L["yg"] + (GPU_H - pw_y) / 2.0
    S("Src_GPU_PHY_L", L["xg"] + GPU_EDGE_GAP, yp, pw_x, pw_y,
      p_hot * w_phy / wsum, "BEOL_MXY", "src_gpu")
    S("Src_GPU_PHY_R", L["xg"] + GPU_W - GPU_EDGE_GAP - pw_x, yp, pw_x, pw_y,
      p_hot * w_phy / wsum, "BEOL_MXY", "src_gpu")
    return out


def split_hosts(boxes, srcs):
    """발열 블록이 놓일 층(host)을 평면에서 쪼갠다.  블록 자리는 그 전력을 갖는
    상자로, 나머지는 host 의 원래 전력을 면적비로 나눠 갖는 상자로."""
    by_host = {}
    for s in srcs:
        by_host.setdefault(s["host"], []).append(s)
    out = []
    for b in boxes:
        if b["name"] not in by_host:
            out.append(b)
            continue
        ss = by_host[b["name"]]
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                a, c = ss[i], ss[j]
                ox = min(a["x"] + a["dx"], c["x"] + c["dx"]) - max(a["x"], c["x"])
                oy = min(a["y"] + a["dy"], c["y"] + c["dy"]) - max(a["y"], c["y"])
                if ox > 1e-7 and oy > 1e-7:
                    raise ValueError("sources %s and %s overlap in %s by %.3f x %.3f mm"
                                     % (a["name"], c["name"], b["name"], ox, oy))
        for s in ss:
            if (s["x"] < b["x"] - 1e-7 or s["y"] < b["y"] - 1e-7
                    or s["x"] + s["dx"] > b["x"] + b["dx"] + 1e-7
                    or s["y"] + s["dy"] > b["y"] + b["dy"] + 1e-7):
                raise ValueError("source %s sticks out of %s" % (s["name"], b["name"]))
        outer = (b["x"], b["y"], r9(b["x"] + b["dx"]), r9(b["y"] + b["dy"]))
        holes = [(s["x"], s["y"], r9(s["x"] + s["dx"]), r9(s["y"] + s["dy"])) for s in ss]
        for s in ss:
            nb = dict(b)
            nb.update(name=s["name"], x=s["x"], y=s["y"], dx=s["dx"], dy=s["dy"],
                      power=s["power"], grp=s["grp"], host=b["name"])
            out.append(nb)
        rest = complement(outer, holes)
        a_rest = sum([(r[2] - r[0]) * (r[3] - r[1]) for r in rest])
        for i, (rx0, ry0, rx1, ry1) in enumerate(rest):
            nb = dict(b)
            nb.update(name="%s_%02d" % (b["name"], i + 1), x=rx0, y=ry0,
                      dx=r9(rx1 - rx0), dy=r9(ry1 - ry0),
                      power=(b["power"] * (rx1 - rx0) * (ry1 - ry0) / a_rest) if a_rest > 0 else 0.0)
            out.append(nb)
    return out


def clip_quarter(boxes, cx, cy):
    out = []
    for b in boxes:
        x0, x1 = max(b["x"], cx), b["x"] + b["dx"]
        y0, y1 = max(b["y"], cy), b["y"] + b["dy"]
        if x1 - x0 < 1e-9 or y1 - y0 < 1e-9:
            continue
        nb = dict(b)
        fx = (x1 - x0) / b["dx"]
        fy = (y1 - y0) / b["dy"]
        nb.update(x=r9(x0), y=r9(y0), dx=r9(x1 - x0), dy=r9(y1 - y0),
                  power=b["power"] * fx * fy)
        out.append(nb)
    return out


def total_power(boxes):
    return sum([b["power"] for b in boxes])


# ==========================================================================
#  검사
# ==========================================================================
def preflight(boxes, L):
    w = []
    for i in range(len(boxes)):
        a = boxes[i]
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            ox = min(a["x"] + a["dx"], b["x"] + b["dx"]) - max(a["x"], b["x"])
            oy = min(a["y"] + a["dy"], b["y"] + b["dy"]) - max(a["y"], b["y"])
            oz = min(a["z"] + a["dz"], b["z"] + b["dz"]) - max(a["z"], b["z"])
            if ox > 1e-7 and oy > 1e-7 and oz > 1e-7:
                w.append("OVERLAP %s / %s  (%.4g x %.4g x %.4g mm)"
                         % (a["name"], b["name"], ox, oy, oz))
    if SYMMETRY == "none":
        v_all = INT_W * INT_H * (L["z_die_top"] - L["z_int_top"])
        v_use = sum([b["dx"] * b["dy"] * b["dz"] for b in boxes
                     if b["grp"] in ("gpu", "base", "dram", "mold", "src_gpu", "src_base")])
        if abs(v_all - v_use) > 1e-6:
            w.append("MOLD GAP: %.6f mm3 of the interposer volume is unfilled" % (v_all - v_use))
        #  쪼갠 층이 원래 평면을 빈틈없이 덮는지
        for host, foot in (("BEOL_MXY", GPU_W * GPU_H), ("HBM_L1_BaseBEOL", BASE_W * BASE_H)):
            a = sum([b["dx"] * b["dy"] for b in boxes
                     if b.get("host") == host or b["name"].startswith(host + "_")])
            if abs(a - foot) > 1e-6:
                w.append("SPLIT %s covers %.4f of %.4f mm2" % (host, a, foot))
    want = P_GPU + 4 * P_HBM
    if SYMMETRY == "quarter":
        want /= 4.0
    got = total_power(boxes)
    if abs(want - got) > 1e-6:
        w.append("POWER %.3f W in boxes, expected %.3f W" % (got, want))
    gpu_t = (T_UBUMP + T_BSPDN + T_FEOL + T_BEOL_MXY + T_BSPDN_BOND + T_CARRIER)
    hbm_t = (T_UBUMP + T_BASE_BEOL + T_BASE_SI
             + (N_DRAM - 1) * (T_DRAM_UBUMP + T_DRAM_BEOL + T_DRAM_SI)
             + (T_DRAM_UBUMP + T_DRAM_BEOL + T_DRAM_TOP))
    if abs(gpu_t - hbm_t) > 1e-9:
        w.append("STACK HEIGHT gpu %.6f != hbm %.6f" % (gpu_t, hbm_t))
    #  PHY 가 PHY_FACE 가 정한 쪽을 보는지 (PHY 중심이 base die 중심보다 그쪽에)
    for b in boxes:
        if b["grp"] == "src_base" and b["name"].endswith("_PHY"):
            tag = b["name"].split("_")[1]
            base = [q for q in boxes if q["name"] == "HBM_%s_BaseSi" % tag]
            if not base:
                continue
            bcx = base[0]["x"] + base[0]["dx"] / 2.0
            bcy = base[0]["y"] + base[0]["dy"] / 2.0
            pcx = b["x"] + b["dx"] / 2.0
            pcy = b["y"] + b["dy"] / 2.0
            want = phy_face(tag)
            ok = {"+x": pcx > bcx, "-x": pcx < bcx,
                  "+y": pcy > bcy, "-y": pcy < bcy}[want]
            if not ok:
                w.append("PHY of %s does not face %s" % (tag, want))
    if SYMMETRY == "quarter" and PHY_FACE in ("-y", "+y"):
        w.append("PHY_FACE %s breaks the y mirror symmetry: SYMMETRY must be 'none'" % PHY_FACE)
    return w


def mesh_box(boxes, L):
    pad = MESH_DIE_PAD
    x0 = L["xi"] - pad
    y0 = L["yi"] - pad
    x1 = L["xi"] + INT_W + pad
    y1 = L["yi"] + INT_H + pad
    z0 = T_LAM + T_CUPILLAR / 2.0
    z1 = L["z_die_top"] + T_TIM / 2.0
    if SYMMETRY == "quarter":
        x0 = L["cx"] - pad
        y0 = L["cy"] - pad
    return dict(name="MeshBox_Die", x=r9(x0), y=r9(y0), z=r9(z0),
                dx=r9(x1 - x0), dy=r9(y1 - y0), dz=r9(z1 - z0), maxsize=MESH_DIE_MAX)


def mesh_estimate(boxes, L, mb):
    nx = mb["dx"] / MESH_DIE_MAX[0]
    ny = mb["dy"] / MESH_DIE_MAX[1]
    zs = sorted(set([b["z"] for b in boxes] + [b["z"] + b["dz"] for b in boxes]))
    zs = [v for v in zs if mb["z"] - 1e-9 <= v <= mb["z"] + mb["dz"] + 1e-9]
    nz = 0
    for i in range(len(zs) - 1):
        nz += max(1, int(math.ceil((zs[i + 1] - zs[i]) / MESH_DIE_MAX[2] - 1e-9)))
    return nx * ny * nz, nx, ny, nz


# ==========================================================================
#  리포트, 그림
# ==========================================================================
def stack_table(boxes):
    rows = []
    for b in sorted(boxes, key=lambda q: (q["z"], q["x"], q["y"])):
        rows.append("%-20s z %9.6f .. %9.6f (%8.6f)  xy %6.2f x %6.2f  %-14s %s"
                    % (b["name"], b["z"], b["z"] + b["dz"], b["dz"], b["dx"], b["dy"],
                       b["mat"], ("%.3f W" % b["power"]) if b["power"] > 0 else ""))
    return rows


def write_views(boxes, L, stem, outdir):
    palette = dict([(m[0], "rgb(%d,%d,%d)" % m[3]) for m in material_table()])

    def bounds(k, dk):
        return (min([b[k] for b in boxes]), max([b[k] + b[dk] for b in boxes]))

    x0, x1 = bounds("x", "dx")
    y0, y1 = bounds("y", "dy")
    z0, z1 = bounds("z", "dz")

    def nice(span):
        raw = span / 10.0
        if raw <= 0:
            return 1.0
        mag = 10.0 ** math.floor(math.log(raw) / math.log(10.0))
        for m in (1.0, 2.0, 2.5, 5.0, 10.0):
            if raw <= m * mag:
                return m * mag
        return 10.0 * mag

    def svg(fname, title, items, u0, u1, v0, v1, ul, vl, flipv, notes, outlines, marks=()):
        W, H, M = 1240.0, 760.0, 96.0
        su = (W - 2 * M - 210) / max(u1 - u0, 1e-9)
        sv = (H - 2 * M) / max(v1 - v0, 1e-9)
        PX = lambda a: M + (a - u0) * su
        PY = lambda b, db: ((H - M - (b - v0) * sv - max(db * sv, 0.6)) if flipv
                            else M + (b - v0) * sv)
        esc = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%g" height="%g" '
             'viewBox="0 0 %g %g" font-family="sans-serif">' % (W, H, W, H),
             '<rect width="%g" height="%g" fill="white"/>' % (W, H),
             '<text x="%g" y="30" font-size="17" font-weight="bold">%s</text>' % (M, esc(title))]
        du, dv = nice(u1 - u0), nice(v1 - v0)
        t = du * math.floor(u0 / du)
        while t <= u1 + 1e-9:
            if t >= u0 - 1e-9:
                o.append('<line x1="%.2f" y1="%g" x2="%.2f" y2="%g" stroke="#e8e8e8"/>'
                         % (PX(t), M, PX(t), H - M))
                o.append('<text x="%.2f" y="%g" font-size="11" fill="#555" '
                         'text-anchor="middle">%g</text>' % (PX(t), H - M + 16, t))
            t += du
        t = dv * math.floor(v0 / dv)
        while t <= v1 + 1e-9:
            if t >= v0 - 1e-9:
                o.append('<line x1="%g" y1="%.2f" x2="%g" y2="%.2f" stroke="#e8e8e8"/>'
                         % (M, PY(t, 0.0), W - M - 210, PY(t, 0.0)))
                o.append('<text x="%g" y="%.2f" font-size="11" fill="#555" '
                         'text-anchor="end">%g</text>' % (M - 8, PY(t, 0.0) + 4, t))
            t += dv
        for nm, mat, a, b, da, db in items:
            o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                     'stroke="#333" stroke-width="0.3"/>'
                     % (PX(a), PY(b, db), max(da * su, 0.6), max(db * sv, 0.6),
                        palette.get(mat, "#ccc")))
        for nm, a, b, da, db in outlines:
            o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" '
                     'stroke="#d0d" stroke-width="1.6" stroke-dasharray="6,4"/>'
                     % (PX(a), PY(b, db), max(da * su, 0.6), max(db * sv, 0.6)))
            o.append('<text x="%.2f" y="%.2f" font-size="11" fill="#d0d">%s</text>'
                     % (PX(a) + 3, PY(b, db) - 4, nm))
        #  발열 블록: 빨간 채움.  단면에서는 층이 얇아 최소 2.5 px 로 키운다
        for nm, a, b, da, db, pw in marks:
            hh = max(db * sv, 2.5)
            o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#e33" '
                     'fill-opacity="0.6" stroke="#900" stroke-width="0.8"/>'
                     % (PX(a), PY(b, db) - (hh - db * sv) / 2.0, max(da * su, 0.6), hh))
            if da * su > 26:
                o.append('<text x="%.2f" y="%.2f" font-size="9" fill="#600" '
                         'text-anchor="middle">%s %.3gW</text>'
                         % (PX(a) + da * su / 2.0, PY(b, db) + hh / 2.0 + 3 + (0 if flipv else db * sv / 2.0),
                            esc(nm.replace("Src_", "").replace("GPU_", "")), pw))
        for a, da, lbl, row in notes:
            yy = H - M + 34 + row * 22
            xa, xb = PX(a), PX(a + da)
            o.append('<line x1="%.2f" y1="%g" x2="%.2f" y2="%g" stroke="#c33" '
                     'stroke-width="1.2"/>' % (xa, yy, xb, yy))
            for e in (xa, xb):
                o.append('<line x1="%.2f" y1="%g" x2="%.2f" y2="%g" stroke="#c33" '
                         'stroke-width="1.2"/>' % (e, yy - 4, e, yy + 4))
            o.append('<text x="%.2f" y="%g" font-size="11" fill="#c33" '
                     'text-anchor="middle">%s</text>' % ((xa + xb) / 2.0, yy - 7, lbl))
        o.append('<text x="%g" y="%g" font-size="12">%s</text>' % (M, H - 14, ul))
        o.append('<text x="18" y="%g" font-size="12" transform="rotate(-90 18 %g)">%s'
                 '</text>' % (H / 2, H / 2, vl))
        o.append('<text x="%g" y="%g" font-size="10" fill="#777">horizontal %.1f px/mm, '
                 'vertical %.1f px/mm</text>' % (W - 205, H - 14, su, sv))
        yy = 52
        for n in sorted(set([i[1] for i in items])):
            th = [i[5] for i in items if i[1] == n]
            o.append('<rect x="%g" y="%g" width="11" height="11" fill="%s" stroke="#333" '
                     'stroke-width="0.3"/>' % (W - 205, yy, palette.get(n, "#ccc")))
            o.append('<text x="%g" y="%g" font-size="11">%s  %s</text>'
                     % (W - 190, yy + 10, n,
                        ("%.4g mm" % th[0]) if len(set(th)) == 1 else ""))
            yy += 16
        o.append('</svg>')
        fh = open(fname, "w")
        fh.write("\n".join(o))
        fh.close()
        return fname

    src = [b for b in boxes if b["grp"] in ("src_gpu", "src_base")]
    #  단면: GPU 위쪽 핫스팟 행의 중심을 지나는 y (위쪽 HBM 행과 PHY/TSV 도 지난다)
    ycut = L["yg"] + GPU_ROWS_Y[-1] * GPU_H
    sec = [(b["name"], b["mat"], b["x"], b["z"], b["dx"], b["dz"]) for b in boxes
           if b["y"] - 1e-9 <= ycut <= b["y"] + b["dy"] + 1e-9]
    sec_marks = [(b["name"], b["x"], b["z"], b["dx"], b["dz"], b["power"]) for b in src
                 if b["y"] - 1e-9 <= ycut <= b["y"] + b["dy"] + 1e-9]
    #  평면: DRAM 스택 중간 높이, 그 위에 발열 블록을 전부 겹쳐 (z 무관)
    zcut = (L["z_base_top"] + L["z_die_top"]) / 2.0
    top = [(b["name"], b["mat"], b["x"], b["y"], b["dx"], b["dy"]) for b in boxes
           if b["z"] - 1e-9 <= zcut <= b["z"] + b["dz"] + 1e-9]
    top_marks = [(b["name"], b["x"], b["y"], b["dx"], b["dy"], b["power"]) for b in src]
    mb = mesh_box(boxes, L)
    sec_out = [(mb["name"], mb["x"], mb["z"], mb["dx"], mb["dz"])]
    top_out = [(mb["name"], mb["x"], mb["y"], mb["dx"], mb["dy"])]
    sec_notes = [(L["x_bL"], BASE_W, "base %.1f" % BASE_W, 0),
                 (L["xg"], GPU_W, "GPU %.1f" % GPU_W, 0),
                 (L["x_bR"], BASE_W, "base %.1f" % BASE_W, 0),
                 (L["xi"], INT_W, "interposer %.1f" % INT_W, 1),
                 (L["x_bL"] + (BASE_W - DRAM_W) / 2.0, DRAM_W, "DRAM %.2f" % DRAM_W, 2)]
    top_notes = [(L["xi"], INT_W, "interposer %.1f" % INT_W, 0),
                 (L["xg"], GPU_W, "GPU %.1f" % GPU_W, 1)]
    made = []
    made.append(svg(os.path.join(outdir, stem + "_section.svg"),
                    "cross-section at y = %.2f mm (upper hotspot row / upper HBM row), "
                    "%d boxes, heat blocks in red" % (ycut, len(sec)),
                    sec, x0, x1, z0, z1, "x (mm)", "z (mm)", True, sec_notes, sec_out, sec_marks))
    made.append(svg(os.path.join(outdir, stem + "_top.svg"),
                    "plan at z = %.3f mm (mid DRAM stack) + all %d heat blocks in red"
                    % (zcut, len(src)),
                    top, x0, x1, y0, y1, "x (mm)", "y (mm)", True, top_notes, top_out, top_marks))
    #  발열원만: base BEOL 과 GPU BEOL_MXY 평면
    #  발열이 없는 층 조각은 연회색으로 눌러서 빨간 블록이 도드라지게
    palette["_bg"] = "rgb(235,235,238)"
    src_items = [(b["name"], "_bg" if b["grp"] not in ("mold",) else b["mat"],
                  b["x"], b["y"], b["dx"], b["dy"]) for b in boxes
                 if (b["name"].startswith("BEOL_MXY") or "BaseBEOL" in b["name"]
                     or b["grp"] in ("mold", "src_gpu", "src_base"))
                 and b["z"] <= L["z_base_top"] + 1e-9 and b["z"] + b["dz"] >= L["z_int_top"] - 1e-9]
    made.append(svg(os.path.join(outdir, stem + "_sources.svg"),
                    "heat blocks in BEOL_MXY: 10 hotspots + 2 NVLink (%.0f W total) + %.0f W uniform "
                    "in BSPDN; base BEOL PHY %.2f W + TSV&I/O %.2f W, PHY_FACE = %s  (+y up)"
                    % (P_GPU * (1 - GPU_BG_FRAC), P_GPU * GPU_BG_FRAC, P_PHY, P_TSV, PHY_FACE),
                    src_items, L["xi"] - 1, L["xi"] + INT_W + 1, L["yi"] - 1, L["yi"] + INT_H + 1,
                    "x (mm)", "y (mm)", True, [], [], top_marks))
    return made


def byhand_table():
    rows = []
    if COOL_TOP:
        rows.append(("Thermal > Cool_Lid",    "Heat Transfer Coeff", "%g" % H_TOP,    "w_per_m2kel"))
        rows.append(("Thermal > Cool_Lid",    "External Temperature", "%g" % T_AMB,   "cel"))
    if COOL_BOTTOM:
        rows.append(("Thermal > Cool_Bottom", "Heat Transfer Coeff", "%g" % H_BOTTOM, "w_per_m2kel"))
        rows.append(("Thermal > Cool_Bottom", "External Temperature", "%g" % T_AMB,   "cel"))
    for nm, kxy, kz, _c in material_table():
        if abs(kxy - kz) > 1e-9:
            rows.append(("Definitions > " + nm, "Thermal Conductivity",
                         "anisotropic", "X %.4g, Y %.4g, Z %.4g" % (kxy, kxy, kz)))
    return rows


def report_lines(boxes, L, warns):
    mb = mesh_box(boxes, L)
    ncell, nx, ny, nz = mesh_estimate(boxes, L, mb)
    powered = [b for b in boxes if b["power"] > 0]
    src = [b for b in boxes if b["grp"] in ("src_gpu", "src_base")]
    out = ["IEDM 2025 Chen et al. - 2.5D baseline (Fig. 2), modified DRAM stack  SYMMETRY=%s"
           % SYMMETRY,
           "=" * 70,
           "boxes %d, powered %d, total %.1f W%s"
           % (len(boxes), len(powered), total_power(boxes),
              "  (whole module %.1f W)" % (P_GPU + 4 * P_HBM) if SYMMETRY == "quarter" else ""),
           "  GPU %.0f W = %.1f W uniform in BSPDN + BEOL_MXY blocks (%.1f W): %d hotspots with "
           "power-density ratio %s per row + 2 HBM-PHY (+-x) each at %.2g x a small hotspot (NVLink removed)"
           % (P_GPU, P_GPU * GPU_BG_FRAC, P_GPU * (1 - GPU_BG_FRAC),
              len(GPU_BLOB_DENS) * len(GPU_ROWS_Y),
              ":".join(["%g" % d for d in GPU_BLOB_DENS]), GPU_PHY_W),
           "  hotspot power density: " + ", ".join(
               ["%s %.4f W/mm2" % (b["name"].replace("Src_GPU_", ""), b["power"] / (b["dx"] * b["dy"]))
                for b in src if b["name"].startswith("Src_GPU_R1")]),
           "  HBM per stack %.1f W = base BEOL blocks PHY %.3f W + TSV&I/O %.3f W, DRAM Si %.3f W x %d"
           % (P_HBM, P_PHY, P_TSV, P_DRAM, N_DRAM),
           "  (reference PHY %.0f / TSV %.0f / DRAM %.0f W x %d = %.0f W, scaled x %.4f to the paper's %.0f W)"
           % (P_PHY_REF, P_TSV_REF, P_DRAM_REF, N_DRAM, P_HBM_REF, HBM_SCALE, P_HBM),
           "",
           "DRAM stack unit (bottom to top): microbump %.0f um / BEOL %.0f um / Si %.0f um "
           "(top die Si %.0f um); no hybrid bonding"
           % (T_DRAM_UBUMP * 1e3, T_DRAM_BEOL * 1e3, T_DRAM_SI * 1e3, T_DRAM_TOP * 1e3),
           "",
           "heat blocks (each is a piece of a real layer, Block boundary with Total Power):"] + \
          ["  %-16s x %6.2f..%6.2f  y %6.2f..%6.2f  z %.6f..%.6f  %5.2f x %5.2f mm  %7.3f W  in %s"
           % (b["name"], b["x"], b["x"] + b["dx"], b["y"], b["y"] + b["dy"], b["z"], b["z"] + b["dz"],
              b["dx"], b["dy"], b["power"], b.get("host", "")) for b in src] + \
          ["",
           "plan (mm)",
           "  laminate   %.1f x %.1f" % (LAM_W, LAM_H),
           "  interposer %.1f x %.1f  at x %.2f..%.2f  y %.2f..%.2f"
           % (INT_W, INT_H, L["xi"], L["xi"] + INT_W, L["yi"], L["yi"] + INT_H),
           "  GPU        %.1f x %.1f  at x %.2f..%.2f  y %.2f..%.2f"
           % (GPU_W, GPU_H, L["xg"], L["xg"] + GPU_W, L["yg"], L["yg"] + GPU_H),
           "  base die   %.1f x %.1f  L x %.2f..%.2f  R x %.2f..%.2f   rows y %.2f..%.2f, %.2f..%.2f"
           % (BASE_W, BASE_H, L["x_bL"], L["x_bL"] + BASE_W, L["x_bR"], L["x_bR"] + BASE_W,
              L["y_b0"], L["y_b0"] + BASE_H, L["y_b1"], L["y_b1"] + BASE_H),
           "  DRAM die   %.2f x %.2f  centred on the base die (%.2f mm mold rim)"
           % (DRAM_W, DRAM_H, (BASE_W - DRAM_W) / 2.0),
           "  gaps: GPU-HBM %.2f, HBM-interposer edge x %.2f / y %.2f, row gap %.2f"
           % (GAP_GPU_HBM, MARGIN_X, MARGIN_Y, HBM_ROW_GAP),
           "  TIM %.1f x %.1f,  lid %.1f x %.1f" % (TIM_W, TIM_H, LID_W, LID_H),
           "",
           "z (mm)",
           "  interposer top %.4f,  base die top %.4f,  die top %.4f,  lid %.4f..%.4f"
           % (L["z_int_top"], L["z_base_top"], L["z_die_top"], L["z_lid"], L["z_top"]),
           "  HBM column %.4f = GPU column %.4f above the interposer BEOL"
           % (L["z_hbm_top"] - L["z_int_top"], L["z_gpu_top"] - L["z_int_top"]),
           "",
           "cooling: lid top h = %g W/m2K, laminate bottom h = %g W/m2K, ambient %g degC"
           % (H_TOP, H_BOTTOM, T_AMB),
           "  everything else adiabatic (domain boundary without a Wall)",
           "",
           "mesh: global max %s mm, min gap %s mm" % (MESH_MAX, MESH_GAP),
           "  %s x %.2f..%.2f y %.2f..%.2f z %.4f..%.4f  max %s mm"
           % (mb["name"], mb["x"], mb["x"] + mb["dx"], mb["y"], mb["y"] + mb["dy"],
              mb["z"], mb["z"] + mb["dz"], MESH_DIE_MAX),
           "  about %.2f M cells inside it (%.0f x %.0f x %d)" % (ncell / 1e6, nx, ny, nz),
           "  thinnest layer %.5g um (FEOL) -> one cell, aspect up to %.0f"
           % (T_FEOL * 1e3, MESH_DIE_MAX[0] / T_FEOL),
           ""]
    if warns:
        out += ["PRE-FLIGHT:"] + ["  " + w for w in warns] + [""]
    else:
        out += ["pre-flight: no overlaps, mold fills the interposer volume exactly, split "
                "layers cover their footprint, power and stack heights check out, PHY faces "
                "%s on all four stacks (PHY_FACE = %s)"
                % ("the GPU" if PHY_FACE == "gpu" else PHY_FACE, PHY_FACE), ""]
    out += ["TYPE THESE IN BY HAND (number left, unit from the dropdown):"]
    for w, f, v, u in byhand_table():
        out.append("  %-34s %-22s %-12s %s" % (w, f, v, u))
    out += ["", "stack (every box, bottom to top):"] + ["  " + r for r in stack_table(boxes)]
    return out


# ==========================================================================
#  AEDT
# ==========================================================================
def run_aedt():
    try:
        import ScriptEnv
        ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
    except Exception:
        pass
    oDesktop.RestoreWindow()
    oProject = oDesktop.GetActiveProject() or oDesktop.NewProject()
    try:
        oDesign = oProject.GetActiveDesign()
    except Exception:
        oDesign = None
    if oDesign is None:
        for st in ("SteadyState", ""):
            try:
                oDesign = oProject.InsertDesign("Icepak", "HBM_GPU_2p5D", st, "")
                break
            except Exception:
                oDesign = None
    if oDesign is None:
        raise Exception("Insert an Icepak design first: Project > Insert Icepak Design.")

    pname, dname = oProject.GetName(), oDesign.GetName()
    manual, loglines = [], []

    def log(m):
        try:
            m = str(m).encode("ascii", "replace")
            if not isinstance(m, str):
                m = m.decode("ascii")
        except Exception:
            m = str(m)
        loglines.append(m)
        try:
            oDesktop.AddMessage(pname, dname, 0, "[2p5d] " + m)
        except Exception:
            pass
        try:
            print(m)
        except Exception:
            pass

    def attempt(label, *fns):
        why = ""
        for f in fns:
            try:
                f()
                return True
            except Exception as e:
                why = str(e).strip().replace("\n", " ")[:300]
        manual.append(label + ("   [AEDT: %s]" % why if why else ""))
        return False

    boxes, L = build()
    warns = preflight(boxes, L)
    for w in warns:
        log("PRE-FLIGHT: " + w)
    if [w for w in warns if w.startswith(("OVERLAP", "POWER", "SPLIT", "PHY"))]:
        raise Exception("pre-flight failed; nothing was built. See the messages.")

    oEditor = oDesign.SetActiveEditor("3D Modeler")
    oDef = oProject.GetDefinitionManager()
    oBnd = oDesign.GetModule("BoundarySetup")
    try:
        oEditor.SetModelUnits(["NAME:Units Parameter", "Units:=", "mm", "Rescale:=", False])
    except Exception:
        pass

    existing = []
    for how in ("GetMatchedObjectName", "GetObjectsInGroup"):
        try:
            existing = [str(n) for n in (oEditor.GetMatchedObjectName("*")
                                         if how == "GetMatchedObjectName"
                                         else oEditor.GetObjectsInGroup("Solids"))]
            if existing:
                break
        except Exception:
            continue
    if existing and not ALLOW_OVERWRITE:
        raise Exception("This design already has %d solids (%s ...). Use a new project "
                        "or set ALLOW_OVERWRITE = True."
                        % (len(existing), ", ".join(sorted(existing)[:3])))

    undo = False
    if BATCH_UNDO:
        for c in ("StartBatchUndoBlock", "BeginUndoBlock"):
            try:
                getattr(oProject, c)("Build HBM-GPU 2.5D")
                undo = True
                break
            except Exception:
                continue

    if CLEAN_FIRST and existing:
        try:
            oEditor.Delete(["NAME:Selections", "Selections:=", ",".join(existing)])
            log("deleted %d existing solids" % len(existing))
        except Exception:
            pass

    # ---- materials --------------------------------------------------------
    nmat = 0
    for name, kxy, kz, rgb in material_table():
        try:
            if oDef.DoesMaterialExist(name):
                nmat += 1
                continue
        except Exception:
            pass
        if abs(kxy - kz) < 1e-9:
            kp = ["thermal_conductivity:=", "%.17g" % float(kxy)]
        else:
            kp = [["NAME:thermal_conductivity", "property_type:=", "AnisoProperty",
                   "unit:=", "", "component1:=", "%.17g" % float(kxy),
                   "component2:=", "%.17g" % float(kxy),
                   "component3:=", "%.17g" % float(kz)]]
        if attempt("Material %s k_xy=%g k_z=%g" % (name, kxy, kz),
                   lambda name=name, kp=kp: oDef.AddMaterial(
                       ["NAME:" + name, "CoordinateSystemType:=", "Cartesian",
                        "BulkOrSurfaceType:=", 1,
                        ["NAME:PhysicsTypes", "set:=", ["Thermal"]]] + kp +
                       ["mass_density:=", "2330", "specific_heat:=", "700"])):
            nmat += 1
    log("materials: %d / %d" % (nmat, len(material_table())))

    # ---- boxes ------------------------------------------------------------
    colors = dict([(m[0], m[3]) for m in material_table()])
    made = 0
    for b in boxes:
        rgb = (255, 40, 40) if b["grp"].startswith("src") else colors.get(b["mat"], (200, 200, 200))
        try:
            oEditor.CreateBox(
                ["NAME:BoxParameters",
                 "XPosition:=", mm(b["x"]), "YPosition:=", mm(b["y"]), "ZPosition:=", mm(b["z"]),
                 "XSize:=", mm(b["dx"]), "YSize:=", mm(b["dy"]), "ZSize:=", mm(b["dz"])],
                ["NAME:Attributes", "Name:=", b["name"], "Flags:=", "",
                 "Color:=", "(%d %d %d)" % rgb, "Transparency:=", 0.0,
                 "PartCoordinateSystem:=", "Global", "UDMId:=", "",
                 "MaterialValue:=", "\"" + b["mat"] + "\"",
                 "SurfaceMaterialValue:=", "\"" + SURFACE_MATERIAL + "\"",
                 "SolveInside:=", True, "ShellElement:=", False,
                 "ShellElementThickness:=", "0mm", "IsMaterialEditable:=", True,
                 "UseMaterialAppearance:=", False, "IsLightweight:=", False])
            made += 1
        except Exception as e:
            manual.append("Box %s @(%g,%g,%g) size(%g,%g,%g) %s   [AEDT: %s]"
                          % (b["name"], b["x"], b["y"], b["z"], b["dx"], b["dy"], b["dz"],
                             b["mat"], str(e)[:120]))
    log("boxes: %d / %d" % (made, len(boxes)))

    # ---- mesh box (non-model) ---------------------------------------------
    mb = mesh_box(boxes, L)
    try:
        if mb["name"] in [str(o) for o in oEditor.GetMatchedObjectName(mb["name"])]:
            oEditor.Delete(["NAME:Selections", "Selections:=", mb["name"]])
    except Exception:
        pass
    attempt("Non-model box %s" % mb["name"],
            lambda: oEditor.CreateBox(
                ["NAME:BoxParameters",
                 "XPosition:=", mm(mb["x"]), "YPosition:=", mm(mb["y"]), "ZPosition:=", mm(mb["z"]),
                 "XSize:=", mm(mb["dx"]), "YSize:=", mm(mb["dy"]), "ZSize:=", mm(mb["dz"])],
                ["NAME:Attributes", "Name:=", mb["name"], "Flags:=", "NonModel#",
                 "Color:=", "(255 0 255)", "Transparency:=", 0.85,
                 "PartCoordinateSystem:=", "Global", "UDMId:=", "",
                 "MaterialValue:=", "\"air\"", "SurfaceMaterialValue:=", "\"\"",
                 "SolveInside:=", True, "IsMaterialEditable:=", True,
                 "UseMaterialAppearance:=", False, "IsLightweight:=", False]))

    # ---- region ------------------------------------------------------------
    try:
        if "Region" in [str(n) for n in oEditor.GetMatchedObjectName("*")]:
            oEditor.Delete(["NAME:Selections", "Selections:=", "Region"])
    except Exception:
        pass
    attempt("Region: padding 0 on all six faces",
            lambda: oEditor.CreateRegion(
                ["NAME:RegionParameters"] +
                sum([["%sPaddingType:=" % s, "Absolute Offset", "%sPadding:=" % s, "0mm"]
                     for s in ("+X", "-X", "+Y", "-Y", "+Z", "-Z")], []),
                ["NAME:Attributes", "Name:=", "Region", "Flags:=", "Wireframe#",
                 "Color:=", "(143 175 143)", "Transparency:=", 1.0,
                 "PartCoordinateSystem:=", "Global", "UDMId:=", "",
                 "MaterialValue:=", "\"air\"", "SurfaceMaterialValue:=", "\"\"",
                 "SolveInside:=", True, "IsMaterialEditable:=", True,
                 "UseMaterialAppearance:=", False, "IsLightweight:=", False]))

    attempt("Settings > Ambient %g degC, gravity off" % T_AMB,
            lambda: oDesign.SetDesignSettings(
                ["NAME:Design Settings Data", "Perform Minimal validation:=", True,
                 "Default Fluid Material:=", "air", "Default Solid Material:=", "Al-Extruded",
                 "Default Surface Material:=", SURFACE_MATERIAL,
                 "AmbientTemperature:=", "%.17gcel" % float(T_AMB),
                 "AmbientRadiationTemperature:=", "%.17gcel" % float(T_AMB),
                 "AmbientPressure:=", "0n_per_meter_sq",
                 "Gravity Vector CS ID:=", 1, "Gravity Vector Axis:=", "Z",
                 "Gravity Direction:=", 1, "Gravity Option:=", False]))

    # ---- heat: one Block per powered object ---------------------------------
    groups = {}
    for b in boxes:
        if b["power"] <= 1e-12:
            continue
        pv = "%.17gW" % float(b["power"])
        key = pv if GROUP_SOURCES else (pv, b["name"])
        groups.setdefault(key, []).append(b["name"])
    nsrc, i = 0, 0
    for key in sorted(groups, key=lambda k: str(k)):
        objs = groups[key]
        pv = key if GROUP_SOURCES else key[0]
        i += 1
        nm = "Blk_%03d" % i
        if attempt("Block %s: %s, %s" % (nm, ",".join(objs)[:60], pv),
                   lambda nm=nm, objs=objs, pv=pv: oBnd.AssignBlockBoundary(
                       ["NAME:" + nm, "Objects:=", objs, "Block Type:=", "Solid",
                        "Use External Conditions:=", False, "Total Power:=", pv])):
            nsrc += len(objs)
    log("blocks: %d boundaries, %d objects, %.1f W" % (i, nsrc, total_power(boxes)))

    # ---- walls -------------------------------------------------------------
    def face_at_z(obj, ztarget):
        try:
            for f in [int(q) for q in oEditor.GetFaceIDs(obj)]:
                c = oEditor.GetFaceCenter(f)
                if abs(float(c[2]) - ztarget) < 1e-5:
                    return f
        except Exception:
            pass
        return None

    def wall(name, obj, ztarget, h, label):
        fid = face_at_z(obj, ztarget)
        if fid is None:
            manual.append("Select the %s face of '%s' (z = %.4f) and Assign Thermal > Wall: "
                          "h = %g w_per_m2kel, T = %g cel" % (label, obj, ztarget, h, T_AMB))
            return
        if attempt("Wall %s on %s face %d: h = %g" % (name, obj, fid, h),
                   lambda: oBnd.AssignStationaryWallBoundary(
                       ["NAME:" + name, "Faces:=", [fid],
                        "External Condition:=", "Heat Transfer Coefficient",
                        "Heat Transfer Coefficient:=", "%.17gw_per_m2kel" % float(h),
                        "External Temperature:=", "%.17gcel" % float(T_AMB),
                        "Thermal Specification:=", "Heat Transfer Coefficient",
                        "Thickness:=", "0mm", "Radiate:=", False])):
            log("wall '%s' on %s %s face: h = %g W/m2K at %g degC" % (name, obj, label, h, T_AMB))

    if COOL_TOP:
        wall("Cool_Lid", "TIM" if LIDLESS else "Lid", L["z_top"], H_TOP, "TOP")
    if COOL_BOTTOM:
        wall("Cool_Bottom", "Laminate", 0.0, H_BOTTOM, "BOTTOM")

    # ---- solution setup: conduction only ----------------------------------
    oSet = oDesign.GetModule("AnalysisSetup")
    try:
        if "Setup1" in [str(n) for n in oSet.GetSetups()]:
            oSet.DeleteSetups(["Setup1"])
    except Exception:
        pass
    args = ["NAME:Setup1"]
    for k, v in [("Enabled", True), ("Flow Regime", "Laminar"),
                 ("Include Temperature", True), ("Include Flow", False),
                 ("Include Gravity", False), ("Radiation Model", "Off"),
                 ("Convergence Criteria - Max Iterations", 300),
                 ("Convergence Criteria - Energy", "1e-12"),
                 ("Discretization Scheme - Temperature", "Second"),
                 ("Under-relaxation - Temperature", "1"),
                 ("Linear Solver Type - Temperature", "F"),
                 ("Linear Solver Termination Criterion - Temperature", "1e-06"),
                 ("Solution Initialization - Temperature", "AmbientTemp")]:
        args += [k + ":=", v]
    if attempt("Analysis > Add Solution Setup (conduction only)",
               lambda: oSet.InsertSetup("IcepakSteadyState", args)):
        log("solution setup 'Setup1' created")

    # ---- monitors ----------------------------------------------------------
    watch = ["BSPDN", "Src_GPU_R1_3", "Src_GPU_R2_3", "Lid"]
    for tag, _x, _y in L["stacks"]:
        watch += ["Src_%s_PHY" % tag, "HBM_%s_D01_Si" % tag, "HBM_%s_D%02d_Si" % (tag, N_DRAM)]
    present = set([b["name"] for b in boxes])
    watch = [w for w in watch if w in present]
    nmon = 0
    try:
        oMon = oDesign.GetModule("Monitor")
        for w in watch:
            try:
                oMon.AssignPointMonitor(["NAME:T_" + w, "Quantities:=", ["Temperature"],
                                         "Objects:=", [w]])
                nmon += 1
            except Exception:
                manual.append("Monitor > Assign Point Monitor on '%s', Temperature" % w)
    except Exception:
        pass
    log("monitors: %d / %d" % (nmon, len(watch)))

    # ---- mesh --------------------------------------------------------------
    if AUTO_MESH:
        oMesh = oDesign.GetModule("MeshRegion")

        def mesh_args(mx):
            return ["ProximitySizeFunction:=", True, "CurvatureSizeFunction:=", True,
                    "EnableTransition:=", False, "OptimizePCBMesh:=", True,
                    "Enable2DCutCell:=", False, "EnforceCutCellMeshing:=", False,
                    "Enforce2dot5DCutCell:=", False, "StairStepMeshing:=", False,
                    "MeshMethod:=", "MesherHD", "ComputeGap:=", True,
                    "MaxElementSizeX:=", mm(mx[0]), "MaxElementSizeY:=", mm(mx[1]),
                    "MaxElementSizeZ:=", mm(mx[2]),
                    "MinElementsInGap:=", "%d" % MESH_GAP_N,
                    "MinElementsOnEdge:=", "%d" % MESH_EDGE_N,
                    "MaxSizeRatio:=", "%g" % MESH_RATIO, "NoOGrids:=", False,
                    "EnableMLM:=", False, "EnforeMLMType:=", "3D", "MaxLevels:=", "0",
                    "BufferLayers:=", "0", "UniformMeshParametersType:=", "Average",
                    "2DMLMType:=", "2DMLM_None",
                    "MinGapX:=", mm(MESH_GAP[0]), "MinGapY:=", mm(MESH_GAP[1]),
                    "MinGapZ:=", mm(MESH_GAP[2]),
                    "MeshRegionResolution:=", 3, "FacetLevel:=", 3,
                    "GeometryBasedMeshing:=", True, "UserSpecifiedSettings:=", True]

        done = 0
        if attempt("Mesh > Global settings",
                   lambda: oMesh.EditGlobalMeshRegion(
                       ["NAME:Settings"] + mesh_args(MESH_MAX) + ["Objects:=", ["Region"]])):
            done += 1
        sub, reg = "SubRegion_Die", "MeshRegion_Die"
        pad = []
        for d in ("+X", "-X", "+Y", "-Y", "+Z", "-Z"):
            pad += [d + "PaddingType:=", "Percentage Offset", d + "Padding:=", "0"]
        if attempt("Mesh sub-region on %s" % mb["name"],
                   lambda: oEditor.CreateSubregion(
                       ["NAME:SubRegionParameters"] + pad
                       + [["NAME:SubRegionPartNames", mb["name"]], ["NAME:SubRegionSubmodelNames"]],
                       ["NAME:Attributes", "Name:=", sub, "Flags:=", "NonModel#Wireframe",
                        "Color:=", "(143 175 143)", "Transparency:=", 0.75,
                        "PartCoordinateSystem:=", "Global", "UDMId:=", "",
                        "MaterialValue:=", "\"air\"", "SurfaceMaterialValue:=", "\"\"",
                        "SolveInside:=", True, "IsMaterialEditable:=", True,
                        "UseMaterialAppearance:=", False, "IsLightweight:=", False])):
            tgt = sub
        else:
            tgt = mb["name"]
        if attempt("Mesh region %s on %s" % (reg, tgt),
                   lambda: oMesh.AssignMeshRegion(
                       ["NAME:" + reg, "Enable:=", True] + mesh_args(MESH_DIE_MAX)
                       + ["Objects:=", [tgt]])):
            done += 1
        log("mesh: %d / 2 assigned (global %s, die region %s mm)" % (done, MESH_MAX, MESH_DIE_MAX))

    if undo:
        for c in ("EndBatchUndoBlock", "EndUndoBlock"):
            try:
                getattr(oProject, c)()
                break
            except Exception:
                continue
    try:
        oProject.Save()
    except Exception:
        pass

    # ---- report + views ----------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = here
    for d in (here, os.path.join(os.path.expanduser("~"), "Downloads"), os.path.expanduser("~")):
        try:
            t = os.path.join(d, "_w.tmp")
            open(t, "w").close()
            os.remove(t)
            outdir = d
            break
        except Exception:
            continue
    rep = report_lines(boxes, L, warns)
    if manual:
        rep += ["", "MANUAL (AEDT refused these, do them by hand):"] + ["  " + m for m in manual]
    else:
        rep += ["", "no [MANUAL] items: every call succeeded."]
    try:
        f = open(os.path.join(outdir, "hbm_gpu_2p5d_report.txt"), "w")
        f.write("\n".join(rep) + "\n")
        f.close()
    except Exception:
        pass
    try:
        for p in write_views(boxes, L, "hbm_gpu_2p5d", outdir):
            log("view -> %s" % p)
    except Exception as e:
        log("views failed: %s" % str(e)[:100])
    log("=" * 60)
    log("DONE. %d boxes, %.1f W. report -> %s"
        % (len(boxes), total_power(boxes), os.path.join(outdir, "hbm_gpu_2p5d_report.txt")))
    for m in manual:
        log("MANUAL: " + m)
    log("type in by hand (see report): %d items" % len(byhand_table()))


def dry_run():
    boxes, L = build()
    warns = preflight(boxes, L)
    here = os.path.dirname(os.path.abspath(__file__))
    rep = report_lines(boxes, L, warns)
    f = open(os.path.join(here, "hbm_gpu_2p5d_report.txt"), "w")
    f.write("\n".join(rep) + "\n")
    f.close()
    f = open(os.path.join(here, "hbm_gpu_2p5d_geometry.csv"), "w")
    f.write("name,x,y,z,dx,dy,dz,material,power_W,group\n")
    for b in boxes:
        f.write("%s,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%s,%.9g,%s\n"
                % (b["name"], b["x"], b["y"], b["z"], b["dx"], b["dy"], b["dz"],
                   b["mat"], b["power"], b["grp"]))
    f.close()
    for p in write_views(boxes, L, "hbm_gpu_2p5d", here):
        print("view -> %s" % p)
    print("\n".join(rep[:60]))
    print("...")
    return boxes, L, warns


try:
    oDesktop  # noqa: F821  (AEDT injects this)
    IN_AEDT = True
except NameError:
    IN_AEDT = False

if IN_AEDT:
    run_aedt()
elif __name__ == "__main__":
    dry_run()

# Run_008 Reference — Icepak 배치 모델링 자료

IEDM 2025 Chen et al. 2.5D HBM-on-GPU baseline(Fig. 2)을 Ansys Icepak(AEDT 2026 R1)에서
재현한 **수렴 기준 실행(Run_008_MeshGlobal025)**의 스크립트·형상·결과 요약이다.
다른 AI/사람이 "이 시뮬이 어떻게 돌아가는지" 파악하고 이어받기 위한 공유본이다.

원본 해석 파일(`.aedt`, `.aedtresults`, `.fld` 필드)은 용량·바이너리라 공개 저장소에 올리지 않는다.
여기 있는 것은 **텍스트 산출물뿐**이다.

## 실행 방식 (headless 배치)
GUI 없이 `ansysedt.exe`에 스크립트를 넘겨 3단계로 돌린다. 각 단계는 독립이며 `Export/*_done.txt`로 완료를 표시한다.

```
ansysedt.exe -ng -RunScriptAndExit driver_1_build.py   # 형상·물성·발열원·경계·메시·셋업 생성 후 저장
ansysedt.exe -ng -RunScriptAndExit driver_2_solve.py   # Setup1 solve
ansysedt.exe -ng -RunScriptAndExit driver_3_post.py    # per-object Tmax/Tmin, 그리드 온도, 메시·수렴·프로파일 추출
```

- `-ng` = no graphics(GUI 없음). iGPU 3D 렌더 크래시를 피하는 핵심. 원격 디스플레이에서도 이 방식으로 돌린다.
- `driver_1`은 `hbm_gpu_2p5d.py`를 **수정 없이** `exec`로 실행한다. 모델 정의는 전부 그 파일 안에 있다.
- 결과 확인: 3D GUI 없이 `*_section.svg` / `*_top.svg` / `*_sources.svg`(2D 도면)와 `*_report.txt`로 구조를,
  `summary.json` / `object_temperatures.csv`로 온도를 본다.

## 파일 역할
| 파일 | 내용 |
|---|---|
| `hbm_gpu_2p5d.py` | 메인 빌드 스크립트. 형상(260 바디), 물성, 발열원 69개, 경계조건, 메시, Setup 전부 정의 |
| `driver_1_build.py` / `driver_2_solve.py` / `driver_3_post.py` | 배치 드라이버(빌드/솔브/후처리) |
| `analyze_results.py` / `plot_results.py` | 결과 집계·그림 |
| `hbm_gpu_2p5d_report.txt` | **발열원 접지 진실**: 블록별 전력 목록(260 박스, 69 파워드, 574 W) |
| `hbm_gpu_2p5d_geometry.csv` | 전 객체 좌표·크기·전력(후처리 입력) |
| `hbm_gpu_2p5d_{section,top,sources}.svg` | 2D 단면/상면/발열원 도면(구조 확인용) |
| `summary.json` / `object_temperatures.csv` | Run_008 온도 결과 |
| `Run_008_Notes.md` | 이 실행의 목적·변수·핵심 결과 |

## ⚠️ 경로 하드코딩 — 이어서 돌리려면 반드시 수정
세 드라이버와 `hbm_gpu_2p5d.py`는 절대경로가 박혀 있다:
```
MODEL = r"C:\AnsysSim\projects\P10_CoolingSimulation\Runs\Run_008_MeshGlobal025\Model"
```
다른 컴퓨터(예: 원격의 `E:\0_DSIL_Member\Hyeongjun\...`)에서 돌리려면 이 `MODEL` 경로와
`hbm_gpu_2p5d.py` 상단의 `MODEL = r"..."`을 **그 PC의 실제 작업 폴더로 바꿔야 한다.**
`.aedt` 파일명도 드라이버 안에 하드코딩돼 있으니 함께 맞춘다.

## 모델 핵심 (근거 등급은 AI_HANDOFF.md 참조)
- 발열: GPU 414 W(BSPDN 균일 207 W + BEOL 핫스팟 207 W), HBM 40 W/스택 ×4, 총 574 W.
- 경계: lid 윗면 h=30000 W/m²K(액냉 콜드플레이트), laminate 바닥 h=200, 주변 20°C, 나머지 단열, 전도 전용.
- 메시: 전역 0.25 mm + die (0.5, 0.5, 0.02) mm. 전역 0.5→0.25에서 GPU peak +0.36°C로 수렴.

## Run_008 결과 (summary.json)
- GPU peak **66.55°C** (논문 69.1°C 대비 −2.5°C), GPU min 35.54°C
- HBM base **56.20°C** (논문 대비 −0.8°C), DRAM D01..D12 55.75 → 41.87°C
- 열수지: lid 564.17 W + laminate 9.83 W = **574.00 W**, residual 2.8e-13, 약 5분 47초

자세한 상태·미완료 작업·다음 프롬프트는 저장소 루트의 `00_Rules/AI_HANDOFF.md` 참조.

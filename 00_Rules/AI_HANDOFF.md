# AI Handoff

## 현재 상태
작업 프로젝트는 `P10_CoolingSimulation` (첨단 패키징 열 시뮬레이션). IEDM 2025 Chen et al. 2.5D baseline(Fig. 2)을 Ansys Icepak(AEDT 2026 R1)에 재현하고 후속 파라미터 연구를 수행 중이다. 대용량 Ansys 원본 파일은 공개 저장소에 포함하지 않으며, 이 저장소에는 규칙·텍스트 연구 기록·공유 가능한 분석 자료만 보관한다.

## 완료 작업 (2026-11-06)
- 셋업 대조: 형상·층 두께·물성·냉각조건은 논문 Fig. 2(c)와 일치. 변경점은 DRAM 본딩(hybrid 2µm→microbump 15µm, 열적 영향 미미), 논문 비공개분 가정(GPU power map, lid·TIM 면적, DRAM 크기).
- 발열원 구조 파악: GPU 414 W = BSPDN 균일 50%(207 W) + BEOL_MXY 핫스팟 12블록 50%(207 W; GPC 16.78 W×8, NV-HBI 27.97 W×2, NVLink 8.39 W×2). HBM 40 W/스택 = base BEOL의 PHY 5.333 W + TSV&I/O 2.667 W + DRAM Si 2.667 W×12. 총량은 논문 [S], HBM 내부분배는 Son et al.(EDAPS 2023) 값을 ×1.333 선형확대 [B], GPU 공간분포는 형상 기반 가정 [추론].
- 경계조건 파악: lid 윗면 h=30000 W/m²K(액냉 콜드플레이트 수준), laminate 바닥 h=200 W/m²K, 주변 20°C, 그 외 면 단열, 전도 전용(conduction-only). 바닥은 574 W 중 ~10 W만 배출하는 부차 경로(바닥 h를 10으로 낮춰도 전체 온도 <1°C 변화로 추정).
- 메시 수렴: 전역 0.5→0.25 mm에서 GPU peak 0.36°C 변화(<0.5°C 기준)로 수렴. 거친 1 mm는 ~1.7°C 낮게 나왔음. 기준 메시 = 전역 0.25 + die (0.5, 0.5, 0.02) mm.
- 검증 결과: 수렴 메시에서 GPU peak 66.5°C(Run_008) vs 논문 69.1°C → −2.5°C. HBM base 56.2°C(−0.8°C). 열수지 574 W, residual ~1e-13.
- 민감도: GPU 배경비율 10%p당 GPU peak ~2°C(Run_003=40%, Run_005=30%); die 영역 메시 영향 ~0.1°C; DRAM 본딩 복원은 HBM base만 ~1.7°C.
- 환경 문제 규명: 이 PC(Intel UHD 730 내장그래픽, 4K, 260바디 모델)에서 AEDT **3D GUI 상호작용 시 크래시**(렉 후 종료). 라이선스 로그상 뜬 직후 재시작 반복, CHECKOUT은 정상 → 그래픽 한계일 뿐 솔브(CPU)·라이선스는 정상. 우회: 배치 실행 + 생성된 SVG/리포트로 확인. 이 때문에 원격 랩 PC로 이전함.

## 검증 완료 (2026-11-09, Phase 1 = 문헌 검증)
- 논문 원문(Dropbox `_Member/Hyeongjun/03_논문/ThermalAnalysis/Breaking_Thermal_Bottleneck...pdf`) 직접 확인 → GPU ≈32×20mm² 414W, HBM 11×11 12-Hi 40W/스택, 경계 h 30000/200·20°C, **2.5D GPU peak 69.1°C**(3D 141.7°C), 전력 공간맵은 비공개(총량만) — 전부 [A] 확정.
- 스택업 수치가 논문 Fig.2(c)와 일치(두께·k·경계·전력총량) 대조 완료.
- 수렴 메시 배경비율 민감도(원격 Run_008/009): BG50%→GPU peak **66.55°C**, BG30%→**71.08°C**. 논문 69.1°C를 브라켓, 보간 **BG≈39%**. HBM base는 배경비율 무관(56.2↔55.9).
- **결론: −2.5°C 갭은 비공개 GPU 전력맵 가정으로 전부 설명됨(구조오류 아님). 베이스라인 검증 완료**, Phase 2의 기준으로 사용.
- 원격 실행 환경: 랩 컴퓨터에서 AEDT 배치 해석을 수행한다. 실행에는 해당 컴퓨터의 대화형 데스크톱 세션이 필요하며, 원격 접속·실행 절차는 비공개 운영 메모에 둔다.

## 미완료 작업
- lidless(힛스프레더 제거) 케이스 셋업. **미결 결정**: 공정 비교를 위한 상단 냉각 경계 모델링 — (a) 양쪽에 동일 콜드플레이트 솔리드 + 그 윗면 HTC, (b) 노출면에 직접 HTC. (a) 권장(냉각 면적 교란 제거), 아직 미확정.
- lid/lidless 확정 후 **칩 크기 sweep**(지도교수 요청 결론 단계). 가설: 대형 AI 가속기에선 lidless가 냉각에 유리. **가정이 아니라 데이터로 검증할 대상.**
- 소 불일치: 논문 본문 GPU 32×20 vs 모델 30×22(Fig.2a 기준, 면적 +3%) — Phase 2 이후 민감도.
- `Research_Log.md` Phase 1 검증 기록 반영 완료(이후 계속 갱신).

## 연구 계획 순서 (형준님, 2026-11-09)
1. 기존 HBM 구조 시뮬 문헌 검증 — **완료**
2. 힛스프레더 유무(lid vs lidless) 열효율 러프 비교 (TIM·HTC 고정) — **완료**: Run_010 lidded 69.0°C(=논문 69.1 안착) vs Run_011 lidless(방식 b) 74.3°C → **Δ+5.2°C, 현 크기선 lid 유리**. 상세 `Research_Log.md` Phase 2 요약.
3. 특정 발열조건에서 힛스프레더 면적·두께의 필요 수준 ← 다음 (그래프 X축 ≥5점)
4. 국소 핫스팟/die 최고온 상승 시 힛스프레더 유효성과 쿨링 한계 제시
5. die 크기를 변수로 sweep (맨 마지막, 그래프 X축 ≥5점)

## 핵심 참고자료
- 원본 해석 파일과 대용량 solver 결과는 로컬/랩 저장 위치에 있으며 GitHub 공개 저장소에는 포함하지 않는다. 공유 가능한 텍스트 스크립트·요약 자료는 프로젝트 폴더의 안내를 참조한다.
- 구조 확인용 2D 도면: 각 Run `Model\hbm_gpu_2p5d_{section,top,sources}.svg` (3D GUI 없이 구조 확인 가능)
- 논문: Chen et al., "Breaking Thermal Bottleneck in 3D HBM-on-GPU Integration via System-Technology Co-Optimization", IEDM 2025
- HBM 전력 분배 출처: Son et al., EDAPS 2023 (logic die 전력 배치)

## 다음 AI용 프롬프트
최신 Phase 3c–3f 결과는 이 문서 하단의 2026-11-14 상태 보정과 프로젝트 `Research_Log.md`를 참조한다. 이전의 “Phase 3 시작” 지시는 오래된 내용이다.

AEDT 실행 주의: `ansysedt -ng`는 (1) **대화형 데스크톱 세션 필요**(ssh 세션0에선 공회전) (2) .bat에서 **비동기 반환**하므로 드라이버를 순차로 돌리려면 done 파일+`.aedt.lock` 해제를 기다려야 함(`run_next.ps1`에 구현). 소스 스크립트는 한글 주석 때문에 **반드시 UTF-8로 읽고 쓴다**(PowerShell `Get-Content` 기본 cp949는 파일을 깨뜨림). summary.json은 driver가 아니라 `analyze_results.py`(numpy)가 생성 — 성공 기준은 `Export\object_temperatures.csv`/`post_done.txt`로 보고, gpu_max는 그 CSV에서 group∈{gpu,src_gpu}의 Tmax 최대로 산출(=analyze 정의).

결론(lidless 유리)은 미리 단정하지 말고 **데이터로 검증**한다(칩 크기 sweep은 Phase 5). 미확인·충돌 항목은 해결된 것처럼 쓰지 말고, 조사 근거는 `Research_Log.md`에도 남긴다.

## Literature review 상태 (2026-11-12)
- 사용자가 제공한 대화 내보내기 `C:\Research\2026-11-12-132357-this-session-is-being-continued-from-a-previous-c.txt`를 문맥 자료로 읽고, lid 필요성 및 두께/폭 sweep 관련 문헌 1차 스크리닝을 진행.
- 가장 직접적인 선행연구: Wei et al. ITHERM 2019, 2.5D Si interposer test vehicle에서 lid/lidless 실험 및 lid/TIM DOE(두께/열전도율) 수행. 단 jet impingement cooling이며 footprint sweep은 확인되지 않음. 결과/한계와 인용은 `20_Projects/P10_CoolingSimulation/Research_Log.md`의 “Literature review 1차 조사” 기록.
- 더 넓은 문헌 스크리닝 미완료: Wei 원문 DOE 표 TIM 단위 재검증, Wakil·Hisada 세부 결과와 lid 치수 parameter 확인, 최신 GPU/HBM lid geometry 논문 확인 필요.
- 현시점 결론은 특정 냉각 경계에서 lidless가 우수할 수 있다는 직접 실험 근거가 존재한다는 것. 이를 콜드플레이트 GPU-HBM 일반론으로 확대하지 않는다. 이 프로젝트의 동일 coldplate/HTC 조건에서 lid 폭/두께와 lidless를 함께 sweep한 사례는 초기 검색에서 미발견이며 잠정 gap으로 관리.

## 2026-11-14 열전달 기초 학습/모델 입력 감사 착수
- 사용자는 열전달 배경지식 없이 Ansys를 진행 중이며, 교수님 피드백에 답하기 위해 IEDM 2025 Fig.2(c)의 각 layer property를 하나씩 검증하고 싶어함. 핵심 대화 원칙: 입문자에게 Fourier conduction/convection부터 직관적으로 설명하되, 수치·정의를 엄밀히 유지하고 한 번에 하나의 핵심 문제를 다룬다.
- 첫 계산은 areal thermal resistance R''=t/k와 convection 1/h 비교. TIM 200µm/k9.71 → 0.206 cm²K/W; lid 3mm/k400 →0.075 cm²K/W; HTC30,000 →0.333 cm²K/W. 이는 단순 1D 같은 면적 기준이며 패키지 전체 열저항이 아님.
- 다음 대화는 TIM k=9.71의 유효/출처/접촉저항 포함 여부 또는 HTC 경계 유효면적 정의 중 하나를 선택해 수업식으로 진행. 물성표 값 복사와 독립적 물리/실험 검증을 분리한다.

## 2026-11-14 방향 명확화: lab-owned property models
- 사용자는 추가 literature review보다 연구실 자체 측정과 모델링으로 물성별 모델을 만들고 독립적으로 엄밀 검증하고자 함. 후속 조언은 특정 한 논문 값의 plausibility 확인이 아니라 repeatable method + uncertainty + independent validation에 초점을 둘 것.
- 연구실 모델의 적절한 형태: k(T,direction), TIM joint R''(BLT, pressure, temperature, surfaces), composite layer k_eff tensor, boundary HTC(flow/T/location)로 분해. scalar k 하나를 무조건 맞추지 않는다.
- 제안 시작점은 TIM/interface. ASTM D5470 variable-BLT에서 impedance 대 thickness의 slope로 apparent k, intercept로 summed contact resistance 추정. 단 이 표준의 idealized 1D results는 실제 package 전체에 직접 대입 불가; 실험 조건을 고정/기록하고 독립 TTV에서 검증해야 함. ASTM E1461 LFA는 homogeneous isotropic solid 가정 범위가 주대상이라 BEOL/BSPDN 같은 composite stack 검증과 구별.
- 중요 방지점: 하나의 TTV peak 값에 TIM k, contact R, HTC를 동시에 fitting하면 non-identifiability. 우선 coupon characterization, 그다음 TTV에서 최소 nuisance calibration, 독립 holdout 조건 blind validation.

## 2026-11-14 BEOL explicit microstructure model
- Discussed user idea to model BEOL metal and dielectric explicitly. Feasible via multiscale RVE/homogenization; do not mesh nm interconnects across full GPU package. Build a realistic RVE of Cu lines/vias and low-k dielectric, solve x/y/z heat transport to obtain orthotropic effective conductivity, then use as package-level effective layer.
- Current paper's BEOL k may already be effective. Never combine detailed Cu/dielectric geometry with same scalar homogenized k (double-counting risk). Need verify property definition/provenance before implementation.
- Bulk k at nanoscale may miss boundary resistance, grain and size effects. Relevant prior model: Chang et al., IEEE TCPMT 2025 BTE-FEM, experimental validation at two nodes. Also IEDM 2025 layer-resolved measurements report interconnect effective TC 1–2 W/mK for many layers, much less than bulk Cu; this motivates size/interface physics.
- Next design, if user wants to proceed: request/locate stack cross-section/routing density and available test structures; construct a parameterized RVE first; compare with scalar-layer baseline; validate extracted effective properties against independent characterization/TTV. Mark synthetic geometry as generic if actual GPU layout unavailable.

## 2026-11-14 rules audit 및 현재상태 보정
- 사용자가 `00_Rules` 전체를 읽고 연구 방향과 AI 협업 원칙을 지속 적용해 달라고 요청. 숙지한 기준: `AGENTS.md`는 진입점, `AI_GUIDE.md` 공통 작업 규칙, `RESEARCH_STRATEGY.md` 산출물 중심/critical path/손절 우선, `PROJECT_CONTEXT.md` 사용자 선호, `Writing_Rules.md`는 사실·출처·추론 분리와 결과 암시 금지, `File_Naming.md` 원본 보존·검증 전 Final 금지, `Folder_Structure.md` 자료의 맥락 보존. CLAUDE/GEMINI는 공통 가이드 링크만 두는 진입 파일.
- 적용 원칙: 한 번에 한 핵심 문제, 직접 1차 자료와 조건을 확인, 수치·열저항 정의가 다르면 비교 금지, 불확실성은 명시, 작업 종료 시 project log와 handoff 갱신, 논문 산출물에 안 기여하는 추가 sweep은 비판적으로 평가.
- **핸드오프의 11/09 “Phase 3 다음 시작” 내용은 오래됨.** 최신 `Research_Log.md`와 Phase3f 자료에서 확인된 실제 상태: Phase3c 현실적 grease TIM2 grid 완료(16개 중 6개 lidless 능가, 최선 4mm×65×65 71.40°C); Phase3d 고정 aspect lid footprint×thickness 30 cases 완료(Run060–089, 최선 Run089 71.56°C, 835W analytic max power); Phase3e GPU-only scaled lid 조사에서 p=0 degenerate/HBM cooling path loss가 드러나고 p≥0.6부터 정상; Phase3f power linearity check Run150/151 완료(ratio 2.000), max-power derivation 완료. 상세 값/한계는 Research_Log.md의 최신 항목 및 05_Results 파일에 있음.
- 사용자의 최신 연구 방향: literature citation plausibility checks 자체가 목적이 아님. 연구실의 실제 stack/process를 반영한 BEOL·TIM 등 layer/interface model을 구성해 독립적인 coupon/TTV 데이터로 검증하는 것이 목표 후보. 명시적 BEOL RVE→orthotropic k_eff→package model 전달은 가능하지만, 실제 layout/stack data·검증 데이터·산출물 가치/임계경로를 먼저 평가하고 착수 여부 판단. synthetic RVE는 실제 GPU 검증이라고 과장하지 않는다.

## 노트북에서 이어서 시작할 때
1. 저장소를 노트북에 복제하고 Codex에서 저장소 폴더를 연다.
2. 새 Codex 대화에서 `00_Rules`의 공통 지침과 이 파일, `20_Projects/P10_CoolingSimulation/README.md`, `Research_Log.md`를 읽도록 요청한다.
3. 대화 기록이 기기 사이에 보이지 않더라도 이 핸드오프와 연구 로그를 기준으로 이어간다. 대용량 Ansys 원본은 저장소에 없으므로 실행이 필요하면 승인된 연구실 저장 위치에서 별도로 접근한다.

## 2026-11-14 다음 작업의 구체 시작점
- 사용자가 IEDM baseline layer-by-layer 물리 모델의 근간을 묻고, 이 검증을 우선 시작하길 희망.
- 다음 시작: frozen IEDM baseline과 후속 modified model을 분리한 model-contract / layer inventory 작성. 핵심 식 steady conduction ∇·(K∇T)+q'''=0, interface ΔT=q''R'', convection q''=h(Ts−T∞), 전역 에너지수지.
- 공유 Run_008_Reference script 현재 포함 TIM2=40µm,k5.2 및 HTC@TIM2 top surface; 이를 original IEDM Fig.2(c) representation과 혼동 금지. 기존 baseline에선 DRAM microbump 변경도 발생. 검증 전 baseline config를 고정해야 함.
- 이후 layer deep dive는 ΔT budget/sensitivity와 data availability로 선택. TIM1은 현 phase result에서 GPU ΔT의 약39%로 model-based candidate, not independently validated. BEOL RVE는 별도 multiscale work package.

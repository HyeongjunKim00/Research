# AI Handoff

## 현재 상태
작업 프로젝트는 `P10_CoolingSimulation` (첨단 패키징 열 시뮬레이션). IEDM 2025 Chen et al. 2.5D baseline(Fig. 2)을 Ansys Icepak(AEDT 2026 R1)에 `hbm_gpu_2p5d.py`로 재현하고 논문값과 대조 중이다. 실제 해석 파일은 이 PC의 `C:\AnsysSim\projects\P10_CoolingSimulation\Runs\Run_001..008`에 있으며, 용량(4.8GB)·바이너리이므로 공개 저장소에 올리지 않는다. 저장소는 `origin/main`(공개) 추적, 작업 기록·규칙만 보관한다.

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
- 원격 셔틀 구축: 이 PC→랩 PC(143.248.153.132, unist) **ssh 키 접속**으로 AEDT 배치를 자동 구동. 단 AEDT는 대화형 데스크톱 세션 필요 → 실행 트리거만 사용자가 RDP에서 수동(고정 한 줄 `run_next.ps1`). 상세는 메모리 `project-remote-aedt-shuttle`.

## 미완료 작업
- lidless(힛스프레더 제거) 케이스 셋업. **미결 결정**: 공정 비교를 위한 상단 냉각 경계 모델링 — (a) 양쪽에 동일 콜드플레이트 솔리드 + 그 윗면 HTC, (b) 노출면에 직접 HTC. (a) 권장(냉각 면적 교란 제거), 아직 미확정.
- lid/lidless 확정 후 **칩 크기 sweep**(지도교수 요청 결론 단계). 가설: 대형 AI 가속기에선 lidless가 냉각에 유리. **가정이 아니라 데이터로 검증할 대상.**
- 소 불일치: 논문 본문 GPU 32×20 vs 모델 30×22(Fig.2a 기준, 면적 +3%) — Phase 2 이후 민감도.
- `Research_Log.md` Phase 1 검증 기록 반영 완료(이후 계속 갱신).

## 연구 계획 순서 (형준님, 2026-11-09)
1. 기존 HBM 구조 시뮬 문헌 검증 — **완료**
2. 힛스프레더 유무(lid vs lidless) 열효율 러프 비교 (TIM·HTC 고정) ← 다음
3. 특정 발열조건에서 힛스프레더 면적·두께의 필요 수준
4. 국소 핫스팟/die 최고온 상승 시 힛스프레더 유효성과 쿨링 한계 제시
5. die 크기를 변수로 sweep (맨 마지막, 그래프 X축 ≥5점)

## 핵심 참고자료
- 해석 파일(이 PC): `C:\AnsysSim\projects\P10_CoolingSimulation` — `Runs\Run_001..008`(각 `Model\hbm_gpu_2p5d.py`, `Model\*_report.txt`, `Export\summary.json`), `Documents\sensitivity_summary.txt`
- 구조 확인용 2D 도면: 각 Run `Model\hbm_gpu_2p5d_{section,top,sources}.svg` (3D GUI 없이 구조 확인 가능)
- 논문: Chen et al., "Breaking Thermal Bottleneck in 3D HBM-on-GPU Integration via System-Technology Co-Optimization", IEDM 2025
- HBM 전력 분배 출처: Son et al., EDAPS 2023 (logic die 전력 배치)

## 다음 AI용 프롬프트
Phase 1(문헌 검증) 완료. 다음은 **Phase 2: 힛스프레더 유무(lid vs lidless) 비교**다. 실행은 이 PC에서 ssh로 원격 랩 PC를 셔틀로 쓴다(파일·결과 자동, AEDT 실행만 사용자가 RDP에서 `run_next.ps1` 트리거 — 메모리 `project-remote-aedt-shuttle` 참조). AEDT는 **배치(`ansysedt -ng -RunScriptAndExit`)**로만 돌린다. lidless 상단 냉각 경계는 **(a) 양쪽 동일 콜드플레이트 솔리드 + 그 윗면 HTC** 권장(냉각 면적 교란 제거). TIM·HTC 고정 후 lid 유무만 비교. 결론(lidless 유리)은 미리 단정하지 말고 **데이터로 검증**한다(칩 크기 sweep은 Phase 5, 그래프 X축 ≥5점). 미확인·충돌 항목은 해결된 것처럼 쓰지 말고, 조사 근거는 `Research_Log.md`에도 남긴다.

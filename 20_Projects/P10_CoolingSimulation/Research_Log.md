# P10 Research Log

| 날짜 | 질문/변경 | 조건 및 근거 | 결과/상태 | 다음 단계 |
|---|---|---|---|---|
| 2026-11-06 | 초기 폴더 구조 설정 | 사용자가 제공한 Ansys 모델 경로 기록 | 실행 결과 미기록 | 저장소 연결 및 프로젝트 조건 확인 |
| 2026-11-09 | 논문 입력값 1차 확인 | IEDM 2025 Chen et al. 원문(Dropbox PDF) 직접 열람 | GPU ≈32×20mm² 414W, HBM 11×11 12-Hi 40W/스택, 경계 h 30000/200·20°C, 2.5D peak 69.1°C 확인 [A] | 모델 스택업과 대조 |
| 2026-11-09 | 스택업 수치 대조 | `hbm_gpu_2p5d.py` 상수 vs 논문 Fig.2(c) 표 | 층 두께·k·경계·전력총량 일치. 의도적 차이: DRAM hybrid bonding→microbump 15µm. 미해결: GPU 32×20(논문 본문) vs 30×22(모델, Fig.2a) | 검증 solve |
| 2026-11-09 | 베이스라인 논문 재현 검증 | Run_008(BG50%)·Run_009(BG30%), converged 메시 0.25mm, 원격 AEDT 배치 | GPU peak 66.55°C / 71.08°C → 논문 69.1°C를 브라켓. 보간 BG≈39%에서 69.1°C. 갭은 비공개 전력맵 가정으로 설명됨 | Phase 2 (lid vs lidless) 설계 |
| 2026-11-09 | Phase 2: lid vs lidless 러프 비교 | BG39 고정, converged, lidded(=베이스라인) vs lidless(방식 b: lid 제거·TIM 상면에 직접 HTC), 원격 배치 | Lidded GPU 69.0°C(=논문 69.1 안착) vs Lidless 74.3°C → **Δ+5.2°C**. HBM base 56.0↔56.8(+0.7). 현 칩 크기선 lid가 냉각에 유리 | Phase 3 (면적·두께 sweep) |
| 2026-11-10 | GPU 발열맵 교정: NVLink 위치 | 형준님이 모델 검토 중 발견 — NVLink를 HBM 쪽(좌·우 ±x) edge에 뒀던 게 논문 본문 "HBM blocks two sides→GPU-GPU 연결 불가"와 상충. NVLink를 HBM 없는 면(위·아래 ±y)으로 이동, HBM 쪽 edge엔 GPU-측 HBM PHY 배치 [추론] | 소스 14개 겹침0·경계이탈0 검증. peak 위치는 NV-HBI 유지. **Phase 1·2 재실행 필요**(발열맵 변경) | 재실행 후 Phase 1/2 수치 갱신 |
| 2026-11-10 | HIR 2025 Thermal 챕터 참고 추가 | HIR Ch.20 Thermal(56쪽) 발췌 [B] | h=30000→~150 W/cm², 액냉/제트/마이크로채널 구간 정합 확인. HBM 40W는 보수적(최신 60W+). GPU 국소 flux 우리 맵이 추세(>4 W/mm²)보다 완만. `References/HIR_Thermal_2025_notes.md` | Phase 3/4에 HBM 60W·Tjmax 한계선 반영 |
| 2026-11-10 | 교정맵 재검증 (NVLink 제거) | Run_012~015: BG50/30/39 lidded + BG39 lidless, converged, 원격 배치 | GPU peak 66.53/71.05/**69.01**/**74.26**°C → 구값과 ±0.03°C. 69.1 앵커·lid Δ+5.25°C 유지. **Phase 1·2 확정**. 파이프라인 개선: run_next.ps1이 런마다 geometry 재생성(유령행 제거) | Phase 3 (면적·두께 sweep) |
| 2026-11-11 | Phase 3: lid 두께 sweep | BG39 고정, lidded, 두께 0.5/1/2/4mm 신규(Run_016~019) + 앵커 Run_014(3mm)·Run_015(lidless=0mm). 모델=Phase 2와 동일(TIM2 없음, 바닥 h=200) | GPU peak: 0mm 74.26 / 0.5 71.87 / 1.0 70.81 / 2.0 69.62 / 3.0 69.01 / 4.0 68.71°C. √(두께) 수확체감, 1~2mm서 이득 대부분(2mm=84%, 3mm=95%). HBM base 두께 무관(56.2~56.5). 번들 `04_Figures/Draft/P10_Phase3_lid_thickness_sweep/` | 면적 변수 추가(2D) |
| 2026-11-11 | 모델 수정 (형준님 지시) | ① 바닥면 adiabatic(`COOL_BOTTOM=False`, 논문은 h=200) ② TIM2 추가: lid↔콜드플레이트, 두께 100µm·k=5.0 W/mK 등방 **[T, 가정값·문헌 미대조]**. HTC를 TIM2 상면으로 이동. lidless는 방식(b) 유지 | 참조 스크립트 수정·검증(dry_run). 이후 run의 새 스터디 baseline. **절대값은 Phase 1/2/3과 비교 불가** | Phase 3b 돌림 |
| 2026-11-11 | Phase 3b: 면적×두께 2D sweep | BG39, 두께{0.5,1,2,4}mm × lid footprint{54×24,58×38,61×51,65×65}mm 16run + lidless 1 (Run_020~036), 수정 모델 | **반전**: lidless(직접)=74.83°C인데 lidded 최선 4mm×65×65=74.58(−0.25, 사실상 tie), 나머지 15개 모두 lidless보다 **더 뜨거움**. TIM2 직렬저항이 lid 확산이득 상쇄. 면적 지배(첫 확장서 급락 후 포화)·두께×면적 상호작용 확인. 번들 `.../P10_Phase3b_lid_area_thickness_grid/` | TIM2 민감도 / method(a) 재확인 |
| 2026-11-11 | TIM2 값 검증 (IEEE EPS 2026) | Indium Corp "TIM Strategy for AI/HPC" [B, 원문 직접] — 솔더 k50–90·R″0.02–0.08, 액체금속 k>25·R″<0.05, 압축금속 R″0.05–0.15 K·cm²/W. NVIDIA 2025 LM 채택. `References/IEEE_EPS_2026_TIM_notes.md` | 기존 TIM2(k5/100µm·R″0.20)는 **모든 금속 TIM2보다 2.5~10배 고저항=비현실적 보수적** → Phase 3b 반전은 아티팩트 가능성 | 현실적 그리스 TIM2로 재실행 |
| 2026-11-11 | TIM2 → 고성능 그리스로 수정 | 형준님 제공 스펙: k=5.2 W/mK(TC-5888급), BLT 40µm → R″=0.077 K·cm²/W. 참조 `K['TIM2']=5.2`, `T_TIM2=0.040` | Phase 3c 재실행 준비. Run_040~055(lidded 16), lidless는 TIM2 무관이라 Run_036(74.83) 재사용. Phase 3b 그리드는 before/after용 보존 | Phase 3c 결과 회수 |
| 2026-11-11 | Phase 3c: 면적×두께 2D sweep, **현실적 그리스 TIM2** | BG39, 두께{0.5,1,2,4}mm × footprint{54×24,58×38,61×51,65×65} 16run(Run_040~055) + lidless Run_036. TIM2=40µm/k5.2(R″=0.077). 나머지 Phase 3b와 동일 | **반전 해소**: lidless=74.83°C 대비 lid가 **16중 6개서 재역전**(전부 면적≥58×38 AND 두께≥2mm). 최선 4mm×65×65=**71.40°C(−3.43)**. 54×24(오버행0)는 항상 최악(77~78, 두께 비단조). Phase 3b "lid 패배"는 보수적 TIM2 아티팩트 확정. CSV+원본 `05_Results/Phase3c_grease_TIM2/`, 번들 `04_Figures/Draft/P10_Phase3c_grease_TIM2_grid/` | TIM2 k 민감도(임계 TIM2 찾기)/method(a) 공정비교/HBM60W·Tjmax 한계선 |
| 2026-11-12 | 병목 분석 (A): GPU 핫스팟 ΔT 버짓 | Run_055(최선 lid)·Run_036(lidless) 수직 경로 층별 Tmax로 ΔT 분해 | 총 51.4°C 중 **TIM1(die↔lid)=19.8°C(39%) 최대 병목**, Lid 자체 6.1°C(12%)뿐, TIM2+대류/확산 18.5°C(36%), die 7.0°C. **개선 타깃=lid 아니라 TIM1**(R″ 0.21, TIM2의 2.7배). 번들 `04_Figures/Draft/P10_Phase3c_bottleneck_dT_budget/`. 단서: Tmax기반 근사(순수 1D 아님) | TIM1 R″ 민감도 |
| 2026-11-12 | Phase 3d: **고정 아스펙트** lid scale×두께 sweep | 면적축 재설계 — lid가 열입력 아스펙트(54:24) 유지하며 (1+p) 배율만, 모양 불변→단일 scale 변수(3b/3c의 x/y 불균일 성장 교란 제거). 라미네이트도 같이 스케일, 칩/TIM1 고정. 두께{0.25,0.5,1,2,4} × p{0,0.2,0.4,0.6,0.8,1.0} 30run(Run_060~089). 그리스 TIM2·단열·BG39 | **깨끗한 포화 확인**: p=0→0.2 급락, knee ~p=0.4(foot~76×34), 이후 평탄 — lid 더 키워도 무의미(확산길이 한계). **두께가 게이트**: 0.25mm는 크기 이득 거의 0(78.8→78.2), 4mm 최대(78.2→71.6)·포화 늦음(λ~√(k·t)). 최선 Run_089(4mm,108×48)=71.56≈3c 최선. **검증**: p=0(라미 54×24 축소)이 3c 54×24와 완전 일치 → 단열바닥서 라미 크기 열적 무관(스케일 교란 아님). **lidless(Run_036=74.83) 두께0 행으로 포함**: 얇은 lid(0.25·0.5mm)는 전 구간 lidless보다 뜨겁고, 2·4mm만 p≥0.2에서 lidless 이김(최선 −3.27°C) → lid가 이기려면 "두껍게+오버행" 둘 다 필요. p=0 두께 비단조(min 2mm): 오버행0서 두께는 die(30×22)→lid(54×24) 확산을 ~2mm까지만 돕고 이후 수직저항만↑. CSV `05_Results/Phase3d_lidscale/`, 번들 `04_Figures/Draft/P10_Phase3d_lid_scale_thickness_grid/` | TIM1 개선 정량화 / HBM60W·Tjmax 한계선 |
| 2026-11-12 | Phase 3e: **GPU-die 스케일** 스프레더 R sweep | lid·TIM1·대류패치가 전부 GPU die(30×22)에서 출발해 (1+p) 스케일(아스펙트 30:22), 라미네이트 65×65 고정. p=0을 "lid=발열원, 오버행0" 베이스라인으로 삼으려던 의도. 두께{0.25,0.5,1,2,4} × p{0~1.0} 30run(Run_090~119). 그리스 TIM2·단열·BG39 | **p=0(G00) 컬럼은 degenerate — 베이스라인 아님**: lid/TIM1/TIM2·유일 대류면이 전부 GPU 풋프린트로 축소→HBM 4스택 냉각경로 상실·단열 → HBM_base≈**405°C**가 GPU를 **≈165°C**로 역가열(두께 164.6~167.6 무관, 솔버 오류 아닌 나쁜 설계의 정확한 물리). **가설 기각**: "p=0서 0.25mm 최저"는 틀림, p=0선 두께 무의미. **HBM 냉각경로 붕괴**(HBM_base vs p): 405→213→120→65→60→59 — lid가 HBM 재커버하는 **p≥0.6(lid 48×35.2+)**부터 정상 복귀. 그 전(p=0.2)엔 4mm가 **최고온(80.9°C)**: 두꺼운 Cu가 213°C HBM열을 GPU로 더 전도. **깨끗한 영역(p≥0.6)**: 두껍고 클수록 단조↓, p=1.0서 0.25→78.18, 4mm→**71.94**(Run_119 최선; 3d 최선 71.56보다 ~0.4↑, lid가 60×44까지밖에 안 커서). **교훈**: GPU만 덮는 스프레더는 2.5D(HBM 타경로無)서 역효과 — 공유 lid는 HBM도 덮어야(3d 반대극서 재확인). CSV `05_Results/Phase3e_spreader_R/`, 번들 `04_Figures/Draft/P10_Phase3e_spreader_R_gpu_scaled/` | Phase 3f 최대전력(GPU95/HBM85) 해석 차트 |
| 2026-11-12 | U자형 검증: p=0 두께별 층별 열강하 분해 | "왜 4mm가 2mm보다 뜨거운가"를 **기존 solve의 object_temperatures.csv 층별 Tmax**로 분해(새 시뮬 없음). Phase 3d **p=0**(lid 54×24, HBM 덮임·60°C → 역가열 교란 없음) 5두께 Run_060/066/072/078/084. 수직경로 Tmax를 인접층 차분→층별 ΔT. | **U자 = 2개 상반 효과의 합, 시뮬로 증명**: ① **lid 수직 ΔT(Lid바닥−TIM2): 0.53→1.05→2.04→3.87→7.13°C** — 두께 2배마다 2배 = **t/kA 선형** 수직저항. ② **TIM2+대류 ΔT: 32.19→30.47→28.41→26.06→23.57°C** — 단조↓(두꺼울수록 확산 개선; TIM2 스팬 16.9→12.7°C로 대류면 균일화). 2→4mm: 페널티 **+3.26** > 확산이득 **−2.49** = net **+0.78** ≈ GPU peak 실측 +1.0 → **4mm가 짐**. **TIM1 ΔT ~20°C로 두께 무관·최대 병목**(기존 결론 재확인). 교차검증: p↑로 확산공간↑면 최적두께가 2mm→4mm로 밀림(p0.2서 4mm<2mm). **파이프라인 버그 발견**: `T_LidTop.fld` export z가 3mm 레퍼런스(4.4449)에 고정→두께별 lid 상면과 불일치(2mm는 공기, 4mm는 내부) → post에서 `z=lid_z+T_LID`로 수정 필요. 번들 `04_Figures/Draft/P10_Phase3d_ushape_verify_dT_2mm_vs_4mm/`·`P10_Phase3d_layer_temp_vs_thickness_p0/` | 선형성 검증(Run_150 1×/151 2×) 후 Phase 3f |
| 2026-11-12 | 선형성 검증 배치 세팅(대기) | 모델이 전도+대류·상수물성·고정 h/주변 → **선형** 가정 검증용. 동일 geometry(3mm·65×65 전면커버·BG39)에서 전력만 ×1(Run_150: GPU414/HBM40)·×2(Run_151: GPU828/HBM80). `run_linearity.ps1`, RUN_AEDT.bat 연결·원격 푸시·로컬 dry-run(2× patch exit=0, assert 통과) 완료. **사용자 RDP 트리거 대기** | 기대: `(T−20)_2× / (T−20)_1× = 2.000`(GPU·HBM 모두, 솔버 오차 내). 2.000이면 Phase 3f 최대전력(GPU95/HBM85)을 **스윕 없이 각 기존 run에서 해석 계산** 정당화. 결과 회수 후 기록 | 트리거 결과 ratio 확인 → Phase 3f 차트 |
| 2026-11-12 | 선형성 검증 **완료** + Phase 3f 최대전력 차트 | Run_150/151 회수. 선형 확정 후 Phase 3d 30run(Run_060~089)에서 **스윕 없이 해석 계산**: m_G=75/(GPU−20), m_H=65/(HBM−20), P_max=min×574W. 한계 GPU95/HBM85°C(datasheet급, 비스윕). | **선형성 [A]**: 전력 ×2에 (T−20) GPU 52.07→104.13 **ratio 2.000**, HBM 38.56→77.12 **ratio 2.000**(솔버 오차<0.01%). **Phase 3f 결과**: **30개 조합 전부 GPU-limited** — HBM(85°C)은 이 설계공간서 한 번도 병목 아님(TIM1 ~20°C 강하가 상한 지배). P_max는 GPU_peak의 단조 재스케일. 최선 **Run_089(4mm,p=1.0)=835W**(nominal 574W의 1.455×), 최악 Run_060(0.25mm,p=0)=732W(1.276×). 스프레드 ~14%. 번들 `04_Figures/Draft/P10_Phase3f_maxpower/`, CSV·선형성기록 `05_Results/Phase3f_maxpower/` | HBM을 더 뜨겁게 미는 설계(저전도 TIM1↑ 등)면 limiter 전환 가능 — 필요 시 검토. T_LidTop.fld export-z 버그는 2D 등온맵 필요 시 수정 |

---

## Phase 1 검증 요약 (2026-11-09)

**대상:** IEDM 2025 Chen et al. "Breaking Thermal Bottleneck in 3D HBM-on-GPU Integration via STCO"의 **2.5D baseline(Fig. 2)** 재현.

**논문 확인값 [A, 원문 직접]:** GPU 다이 ≈32×20mm² ≈414W, HBM 스택 ≈11×11mm² 12-Hi ≈40W/스택. 경계: lid측 콜드플레이트 HTC 30,000 W/m²K, 라미네이트측 200 W/m²K, 주변 20°C, lid·라미네이트만 대류·나머지 단열, 전도 전용. **2.5D GPU peak 69.1°C**(3D baseline은 141.7°C). GPU/HBM 전력 공간맵은 "commercial power profiles, 0.5mm 해상도"로 **비공개**(총량만 공개).

**검증 결과:**
1. **구조 정합 [A 대조]**: 모델 층 두께·열전도율·경계·전력총량이 논문 Fig.2(c)와 일치.
2. **내부검증 [A, 자체]**: 에너지수지 닫힘(입력 574W = 출력 lid 564 + laminate 10W), 메시 수렴(전역 0.5→0.25mm에서 GPU peak +0.36°C), residual ~1e-13.
3. **논문값 재현 [A, 민감도]**: GPU 배경비율(BSPDN 균일분)만 바꾼 결과 —
   - BG 50% → GPU peak **66.55°C** (논문 −2.55°C)
   - BG 30% → GPU peak **71.08°C** (논문 +1.98°C)
   - 두 값이 논문 69.1°C를 **브라켓**, 선형보간 **BG≈39%**에서 69.1°C.
   - HBM base는 배경비율에 거의 무관(56.20 ↔ 55.93°C).

**결론 [추론, 근거 위 1–3]:** 모델은 논문 2.5D 베이스라인을 구조·경계·총전력에서 정확히 재현하며, GPU peak의 −2.5°C 차이는 **비공개 GPU 전력맵 가정(배경비율)** 범위 안에서 전부 설명된다. 구조적 오류가 아님. → 베이스라인을 Phase 2(lid 유무 비교)의 신뢰 가능한 기준으로 사용.

**의도적 모델 변경(문서화):** DRAM 본딩을 논문 hybrid bonding 2µm(k4.8)에서 microbump 15µm으로 교체, DRAM Si 41→28·top 169→156µm으로 줄여 스택 높이 유지. 열영향 작음(Run_004: HBM base만 ~1.7°C).

**남은 불일치(소):** 논문 본문 GPU 32×20mm² vs 모델 30×22mm²(Fig.2a 도면 기준, 면적 +3%). Phase 2 이후 민감도로 확인 가능.

**실행 환경:** 랩 원격 PC(AEDT 2026 R1) 배치 실행(`ansysedt.exe -ng -RunScriptAndExit` build→solve→post). 결과 `Runs/Run_00X/Export/`. 상세 참고: `01_Simulation/Icepak/Run_008_Reference/`.

---

## Phase 2 요약 (2026-11-09): 힛스프레더 유무 러프 비교

**목적:** TIM·HTC·전력을 고정(콜드플레이트 h=30000, 20°C, GPU 414W@BG39, HBM 40W/스택, converged 메시)하고 **lid 유무만** 바꿔 열효율 차이를 본다.

**모델:** lidless는 방식 (b) — lid와 그 위 냉각면을 제거하고 **HTC를 TIM 상면(54×24, die+mold 상면)에 직접** 부여(`LIDLESS` 스위치). lid 제거의 "순효과"(Cu 확산 소실 + 냉각면적 65×65→54×24 축소)를 함께 반영.

**결과 (object_temperatures.csv에서 analyze_results.py 정의로 산출):**
| | GPU peak | GPU min | HBM base(4스택 평균) |
|---|---|---|---|
| Run_010 Lidded (BG39) | **69.03°C** | 34.90 | 56.05 |
| Run_011 Lidless (BG39) | **74.26°C** | 35.42 | 56.78 |
| Δ (lidless − lidded) | **+5.23** | +0.52 | +0.73 |

**결론 [추론, 근거 위 결과]:**
1. **검증 쐐기**: 보간값 BG39에서 lidded GPU peak 69.0°C가 논문 69.1°C에 정합 → Phase 1 검증을 데이터로 완결.
2. **Phase 2 답**: 현재 칩 크기(GPU 30×22mm, ~660mm²)에선 **힛스프레더가 냉각에 유리**(제거 시 GPU +5.2°C). 지도교수 가설(대형 가속기 lidless 유리)은 이 크기에선 성립하지 않으며, 역전 지점은 Phase 5 칩 크기 sweep에서 검증 대상.

**한계·주의:** (a) lidless는 방식 (b)라 확산·면적 효과가 섞임 — "확산만의 기여"는 방식 (a)로 별도 확인 필요. (b) post에서 `ExportMeshStats/ExportConvergence`는 이 AEDT 빌드에 없어 실패(결과 무관). (c) lidless의 geometry.csv에 유령 "Lid" 행(nan)이 남아 object_temperatures.csv에 nan 1행 — GPU/HBM 산출엔 영향 없음(그룹 필터), 추후 per-run geometry.csv 재생성으로 정리 예정.

> **[2026-11-10 재검증 완료] 발열맵 교정(NVLink 제거, HBM PHY 정립) 후 Run_012~015 재실행 →
> 결과가 구 베이스라인과 사실상 동일하여 Phase 1·2 결론 확정.**
> | Run | 조건 | GPU peak (신) | (구) | HBM base |
> |---|---|---|---|---|
> | 012 | BG50 lidded | 66.53 | 66.55 | 56.36 |
> | 013 | BG30 lidded | 71.05 | 71.08 | 56.16 |
> | 014 | BG39 lidded | **69.01** | 69.03 | 56.25 |
> | 015 | BG39 lidless | **74.26** | 74.26 | 57.03 |
> → BG50/BG30이 논문 69.1을 재브라켓(BG≈39 앵커 유지), lidded 69.0=논문 정합, lidless Δ**+5.25°C**.
> 전력분배가 교정 전과 동일(GPC 16.78/NV-HBI 27.97/PHY 8.39 W)하여 열결과 불변 — 교정은 발열맵
> 라벨/위치 정합성만 개선. **Phase 1·2는 더 이상 잠정값이 아님.**
> (주의: 이번 4개 run의 object_temperatures.csv는 교정 전 geometry.csv로 post돼 **유령 NVL행(nan)·
> PHY행 누락·power열 구값** — 단 Tmax/peak는 solved 실값이라 정확. 다음 run부터 run_next.ps1이
> 런마다 geometry 재생성해 자동 클린. 완전 클린 CSV가 필요하면 post-only 재실행으로 획득 가능.)

---

## Phase 3 / 3b 상세 (2026-11-11)

### Phase 3 — lid 두께 1D sweep (Phase 2 모델: TIM2 없음, 바닥 h=200)
BG39 고정, lidded. 0mm=lidless(Run_015), 3mm=Run_014 앵커 재사용.

| 두께(mm) | 0(lidless) | 0.5 | 1.0 | 2.0 | 3.0 | 4.0 |
|---|---|---|---|---|---|---|
| GPU peak(°C) | 74.26 | 71.87 | 70.81 | 69.62 | 69.01 | 68.71 |
| Δ vs lidless | — | −2.39 | −3.45 | −4.64 | −5.25 | −5.55 |

- 단조 감소·기울기 급감(−4.8→−0.3°C/mm) = √(두께) 수확체감. 전체 이득의 62%(1mm)·84%(2mm)·95%(3mm) 확보 → 열적으로 **1~2mm면 충분**, 그 이상 미미. 역전점은 4mm까지 안 나옴.
- HBM base 56.2~56.5°C로 두께 무관(lid 확산은 GPU 핫스팟 전용).

### Phase 3b — 면적×두께 2D grid (수정 모델: +TIM2 100µm/k5, 바닥 adiabatic)
BG39. lidless(직접, 방식 b) = **74.83°C** (Run_036).

**GPU peak(°C):**
| 두께＼면적 | 54×24 | 58×38 | 61×51 | 65×65 |
|---|---|---|---|---|
| 0.5mm | 85.65 | 83.82 | 83.79 | 83.79 |
| 1.0mm | 84.49 | 81.19 | 81.02 | 81.00 |
| 2.0mm | 83.71 | 78.38 | 77.79 | 77.68 |
| 4.0mm | 84.17 | 76.51 | 75.02 | **74.58** |

**결론 [추론, 위 데이터]:**
1. **힛스프레더 이득 붕괴**: 16개 lidded 중 lidless(74.83)보다 나은 건 4mm×65×65(74.58, −0.25°C) 하나뿐, 나머지 15개는 모두 더 뜨거움. Phase 3의 lid +5.25°C 이득이 **TIM2 추가만으로 ~0으로 반전**. 물리: die→TIM1→lid→TIM2→HTC 직렬저항이 lid 확산·면적 이득을 상쇄.
2. **면적 지배 + 상호작용**: 54×24→58×38 첫 확장서 급락(4mm: 84.2→76.5), 이후 포화. 작은 면적(54×24)선 두께↑ 무의미·역전(2→4mm 83.7→84.2, 직렬저항만); 큰 면적선 두께 단조 도움. → "얇은 lid는 면적 못 살림 / 두꺼운 lid라야 면적 이득" 확인.
3. HBM base: 작은 면적+두꺼운 lid서 최고(70.6°C, 열 갇힘), lidless 최저(57.8°C).

**한계·주의:**
- **TIM2 k=5.0/100µm는 가정값 [T], 특정 문헌 대조 안 함.** 결론이 이 값에 극도로 민감(반전의 주범) → TIM2 민감도(k·두께) 필수.
- lidless 방식(b) 비대칭(냉각면적 54×24) 여전 → method(a)로 재확인하면 "lid 불리" 더 뚜렷해질 것.
- 절대값은 Phase 1/2/3(TIM2 없음·h=200)과 직접 비교 불가.

---

## 참고자료 (2026-11-10 추가)
- `References/HIR_Thermal_2025_notes.md` — HIR 2025 Thermal 챕터 [B] 발췌. 핵심: ①콜드플레이트
  h=30000(≈150 W/cm²)이 액냉/제트/마이크로채널 실존 한계 구간에 정합 → 상단 경계 타당성 보강,
  ②HBM 40 W/스택은 보수적(최신 60 W+), ③우리 GPU 국소 heat flux는 업계 추세(>4 W/mm²)보다
  완만(핫스팟 보수적), ④Phase 4 한계선 후보: 핫스팟 >100°C, HBM Tjmax ~95–105°C.

## Literature review 1차 조사 (2026-11-12, 열람일)

**질문:** 열 스프레더/lid가 항상 필요한지 검증한 연구, lid 두께·너비/면적 sweep 연구가 있는가?

### 직접 관련성이 높은 자료
- Wei et al., “Thermal Analysis of Polymer 3D Printed Jet Impingement Coolers for High Performance 2.5D Si Interposer Packages,” ITHERM 2019, DOI [10.1109/ITHERM.2019.8757402](https://doi.org/10.1109/ITHERM.2019.8757402), [원문 PDF](https://s-pack.org/wp-content/uploads/2022/12/Thermal-Analysis-of-Polymer-3D-Printed-Jet-Impingement-Coolers-for-High-Performance-2.5-D-Si-Interposer-Packages.pdf). [A: 원문 직접 확인]
  - 2.5D Si 인터포저, 8×8 mm² test die 2개, lidded(0.3mm Cu lid, TIM 80µm/k=1.9)와 lidless를 제작·실험 비교. lidless 직접 제트 냉각은 TIM/lid 제거.
  - 실험에서 lidded logic의 열저항이 lidless보다 2.5–3배 높았다고 보고. 저자들은 주원인을 TIM으로 해석. 단 이는 특정 고유량 액체 제트 냉각 조건이며 보편적 결론이 아님.
  - DOE 625 cases/flow 조건: lid 두께 0.05–1mm, lid k 20–600 W/mK, TIM 두께 0.02–400 (PDF 표 단위 표기 재확인 필요; 맥락상 μm 가능성), TIM k 1–20 W/mK. width/footprint sweep은 확인되지 않음.
  - lid 두께 영향은 TIM k<4에서 거의 무시 가능; 고유량 1000ml/min에선 TIM 열저항이 10 mm²K/W 이하일 때 lidded가 lidless 성능과 동등 가능. 낮은 유량 300ml/min에선 lidless 성능을 lidded가 따라잡지 못한 조건이 있다고 보고. 강제 제트 냉각의 결과라 우리 HTC coldplate에 직접 수치 전용 금지.
- Wei et al., “Experimental and numerical investigation of direct liquid jet impinging cooling using 3D printed manifolds on lidded and lidless packages for 2.5D integrated systems,” Applied Thermal Engineering 164 (2020) 114535, DOI [10.1016/j.applthermaleng.2019.114535](https://doi.org/10.1016/j.applthermaleng.2019.114535). [A: 논문 초록 및 PDF 검색 추출 확인]
  - 동일 연구 계열의 실험/수치 비교. lidless bare-die의 inter-chip thermal coupling 4%로 낮았고, lid는 spreading을 통해 열을 옆 die로 전달하는 특성도 강조. 냉각면적·TIM 저항의 tradeoff.
- Hisada & Yamada, “Computational Analysis on Thermal Performance of 2.5D Package,” Transactions of The Japan Institute of Electronics Packaging 7(1), 114–122 (2014), DOI [10.5104/jiepeng.7.114](https://doi.org/10.5104/jiepeng.7.114). [A: 공식 초록 확인, PDF 전체 결과 미확인]
  - Si/glass interposer 및 MCM 2.5D package에서 lidless/lidded/heat-sink-on-lid 옵션, 공기유속과 logic power 변화를 CFD 분석. 현 2.5D 문맥에 직접 유용하지만 lid는 옵션 비교이지 lid footprint/thickness DOE로 확인되지는 않음.
- Wakil, “Thermal performance impacts of heat spreading lids on flip chip packages: With and without heat sinks,” Microelectronics Reliability 46 (2006), 380–385, DOI [10.1016/j.microrel.2005.01.007](https://doi.org/10.1016/j.microrel.2005.01.007). [A: publisher abstract/preview only]
  - IBM SLC flip-chip의 lidded vs bare die를 JEDEC wind tunnel 시험과 FloTHERM으로 비교. 초록은 lid 유무 이득이 airflow·package size에 의존하고, heat sink를 쓰면 interface resistance/lid design/비교 기준에 따라 lid가 더 좋거나 나쁠 수 있다고 결론. lid thickness도 다루지만 열람한 자료에서 실제 sweep 범위는 확인하지 못함.

### 인접 사례 (직접 적용 주의)
- Sturdivant, Bogdon & Chong, “Balancing Thermal and Electrical Packaging Requirements for GaN Microwave and Millimeter-Wave High Power Amplifier Modules,” JECTC 7 (2017), DOI [10.4236/jectc.2017.71001](https://doi.org/10.4236/jectc.2017.71001). [A: 공개 논문 페이지 확인]
  - GaN RF 모듈의 CuW heat spreader 두께를 수치 sweep, 열·전기 성능 tradeoff 및 최적 두께 논의. GPU 패키지와 냉각 구조가 달라 직접 비교 사례보다는 두께 최적화 방법 참고.
- Liu et al., “Optimal design analysis for thermal performance of high power 2.5D package,” Journal of Semiconductors 37 (2016), 035006, DOI [10.1088/1674-4926/37/3/035006](https://doi.org/10.1088/1674-4926/37/3/035006). [A: 공식 초록/그림목록 확인]
  - ANSYS/Icepak 2.5D 고전력 CPU. substrate k, TIM k, fin height가 중요 변수라고 보고. lid의 Γ_jC 기여 그래프는 있으나 lid 치수 sweep인지는 미확인.
- Chen et al., IEDM 2025, [DOI 10.1109/IEDM50572.2025.11353711](https://doi.org/10.1109/IEDM50572.2025.11353711). [A: 공식 초록 확인]
  - 우리 기준 논문. HBM-on-GPU의 시스템 기술 최적화와 2.5D baseline을 다루지만, 공개 초록상 lid 크기/두께 sweep은 아님.

### 현재까지의 답과 공백 가설
- lid가 항상 유리/필수라는 보편 규칙은 문헌에서도 지지되지 않는다. lid는 lateral spreading과 냉각면적 확대를 제공하지만 TIM 추가 열저항, 높아진 thermal coupling이 단점이며 냉각 경계(airflow/jet/heat sink), 접촉저항, die footprint에 따라 순위가 바뀐다.
- 2.5D package에서 lid/lidless를 비교하고 lid 두께 및 TIM 특성을 DOE한 논문은 확인했다. 다만 현 시점 1차 검색에서는 **현대 대형 GPU+HBM의 동일 coldplate/동일 HTC에서 lid의 면적(폭)과 두께를 함께 sweep하고, lidless와 교차점을 보는** 논문은 아직 찾지 못했다. 이것은 검색 범위에 한정된 잠정 공백이지 문헌 부재의 증명은 아니다.
- 우리 Phase 3d는 fixed-aspect scale sweep(0.25–4mm lid thickness × footprint scale 0–1)이며 TIM2/바닥 adiabatic 같은 경계가 기존 제트 논문과 다르다. 독창성/비교를 주장하기 전, Wei et al. DOE의 논문 표 단위와 width sweep 유무를 PDF 원문에서 재확인하고, Wakil/Hisada 원문 결과 및 2022 ITherm multi-chip lid paper를 추가 스크리닝해야 한다.


## 열전달 기초 감사 시작 (2026-11-14)

사용자 요청: IEDM 2025 Chen et al. Fig.2(c) stackup 물성을 한 항목씩 물리적으로 검증하는 학습형 협업 시작. 이 표는 모델 입력의 출처이지, 개별 물성값의 독립적인 실험 검증 그 자체는 아님. 논문 레코드/초록은 [imec publication record](https://imec-publications.be/entities/publication/30473574-9a4d-4f0c-bcc4-1b29345192bf), DOI 10.1109/IEDM50572.2025.11353711.

첫 개념 점검(표 값에서 계산, 1D 면적 열저항 R''=t/k; 대류 R''=1/h):
- TIM t=200µm, k=9.71 W/mK → R''≈2.06×10⁻⁵ m²K/W =0.206 cm²K/W.
- Cu lid t=3mm, k=400 W/mK → R''≈7.50×10⁻⁶ m²K/W =0.075 cm²K/W.
- HTC 30,000 W/m²K → 1/h≈3.33×10⁻⁵ m²K/W =0.333 cm²K/W.
이 수치는 동일한 투영면적에서의 단순 수직 1D 저항만 비교한다. 실제 모델에서는 lid의 면적확장, spreading, TIM 접촉저항, 비균일 power map이 있어 전체 Rth나 peak T를 대신하지 않는다. 따라서 첫 audit target은 TIM 및 HTC의 유효면적/인터페이스 모델, 이어서 비등방성 BSPDN·uBump 좌표 방향, 그리고 얇은 BEOL/FEOL의 유효물성 정의로 제안.

검증 용어: (1) 문헌에서 값 재현 = provenance 확인, (2) 물리적 타당성 = 재료/방향/온도 범위에 적절한지, (3) 수치 검증 = mesh/solver convergence, (4) 실험 검증 = 독립 TTV/측정과 비교. 서로 대체하지 않음. 향후 한 번에 한 물성/모델 가정만 점검하고, fact/source claim/inference를 분리.

## 방향 수정: 연구실 고유 물성 모델 (2026-11-14)

사용자 명확화: 목표는 기존 레퍼런스의 값을 더 찾아 대조하는 literature review가 아니라, 연구실 자체의 측정·모델링을 통해 각 층/계면의 물성 모델을 구성하고 독립 검증하는 것.

핵심 방법론:
- 물성표 숫자를 단일 scalar k로 취급하기보다, bulk conductivity k(T, direction), TIM joint impedance R''(BLT, pressure, temperature, surface), anisotropic homogenized layer tensor k_eff, 냉각 boundary HTC h(flow,T,location)로 나눠 구성.
- TIM 후보 첫 실험: ASTM D5470 variable-thickness method. 동일 재료·압력·표면/온도 조건에서 여러 BLT의 총 areal impedance를 측정하고 R''=t/k_app+R''_contact 양변 회귀. ASTM은 TIM성 재료의 steady-state thermal impedance 측정 표준이며, 실측 impedance를 대부분의 실제 비균일 구조에 직접 옮길 수 없다고 명시하므로 시편/접촉/압력 기록과 TTV 검증 필요. [ASTM D5470-17(2024), https://store.astm.org/standards/d5470]
- 벌크 균질 고체의 k는 LFA로 α 측정 후 k=αρCp에서 산출 가능하나, ASTM E1461은 주로 균질·등방 고체용이므로 BEOL/BSPDN/범프의 유효 tensor를 직접 재는 절차와 혼동 금지. [ASTM E1461-13(2022), https://store.astm.org/standards/e1461]
- Anisotropic/composite layers: 미세구조 기반 unit-cell/homogenization으로 k_eff tensor를 산출하고 독립 coupon 또는 package-level TTV로 확인하는 방향.
- HTC는 고체 물성이 아니라 boundary parameter. 유량/입구온도/유체 bulk temp/기준면적을 명시해 별도로 측정·식별.
- 단일 TTV의 peak temperature만으로 TIM k, interface resistance, HTC를 모두 fitting하면 비식별/보상 오차 위험. 개별 coupon characterization → TTV에서 소수 nuisance parameter 교정 → 분리된 holdout 조건에서 blind validation 권장.

초기화 우선순위: TIM/interface joint model, 이후 anisotropic BSPDN·uBump effective model, then HTC. 상용 재료의 전형값과 실험실 모델은 경쟁하는 게 아니라 scope가 다름: 모델은 시편/공정/조립압력/온도에 국한됨.

## 2026-11-14 multiscale BEOL geometry modeling discussion
- 사용자 제안: BEOL을 scalar layer로만 두지 않고 metal/dielectric 실제 미세구조를 모델링해 k_eff를 직접 도출·검증할 수 있는지 검토.
- 답: 가능하며 적절한 접근은 system GPU/package에 nm-scale metal을 전부 직접 mesh하는 것이 아니라, 실제 routing/stack geometry의 representative volume element(RVE)에서 Cu/low-k/via를 명시해 x/y/z heat flux를 풀고 orthotropic k_eff tensor를 추출한 뒤 package-scale layer로 전달하는 multiscale/homogenization. 단, nanoscale에서 bulk k 사용만 하면 metal/dielectric boundary TBR, size/grain effects를 놓칠 수 있어 필요시 BTE-FEM/modified material model.
- 선행 방법: Chang et al. 2025 IEEE TCPMT, “Thermal Modeling and Analysis of Equivalent Thermal Properties for Advanced BEOL Stacks,” DOI 10.1109/TCPMT.2025.3564833. Official imec record says BTE-FEM, metal density and BC DOE, two process-node experimental validation, realistic 12-layer/18nm-pitch BEOL application. https://imec-publications.be/entities/publication/5cb1eff7-476f-4891-9958-86296d1b6560
- Additional evidence/context: 2025 IEDM layer-resolved measurement of interconnects DOI 10.1109/IEDM50572.2025.11353753 reports effective TC of many layers ~1–2 W/mK across 28–3nm, far below bulk Cu, attributed to metal/dielectric TBR, grain boundaries/amorphous features. https://ieeexplore.ieee.org/abstract/document/11353753
- Important caution: Fig.2(c) BEOL k=1.2 W/mK may already be an effective homogenized property. Explicit geometry and same scalar k cannot be applied together; replace layer with RVE and compare extracted k_eff, avoid double-counting metal pathways. Need identify what source model intends.
- Feasible study sequence: (1) reproduce baseline scalar k layer; (2) parameterized RVE Cu line/via + dielectric; (3) solve along x/y/z with periodic/lateral BC and extract k tensor; (4) replace only one BEOL layer in package model and examine GPU/HBM impact; (5) independent measurement/coupon/TTV blind validation. Without actual routing/GDS or stack cross-section, synthetic RVE only supports generic sensitivity, not a claim about a particular commercial GPU.
- Potential original contribution is not merely explicit CAD geometry; it is exact stack-specific effective-property model, uncertainty, and package-level validation against an independent measurement.

## 2026-11-14 규칙 적용 합의 및 핸드오프 상태 점검
사용자가 `00_Rules`의 전체 문서를 학습하고 협업 내내 준수해달라고 요청. AI_GUIDE + RESEARCH_STRATEGY를 모든 다음 작업의 기준으로 함: 산출물 기여도와 성공 가능성으로 우선순위, 막다른 길은 손절/전환 선제 제안, 한 번에 하나의 핵심문제, facts/source claims/inference 분리, 재현·수치검증·실험검증을 서로 구분. AI_HANDOFF의 구식 계획을 그대로 반복하지 않도록 최신 Research_Log 및 Phase3f 결과와 대조해 11/14 handoff 보정 기록 추가.

## 2026-11-14 첫 실행 단계 합의(모델 물리 검증)
- 질문: IEDM physical model의 layer-by-layer thermal modeling 근간과 시작 순서.
- 시작 원칙: layer 값을 곧바로 하나씩 찾아 대조하거나 전부 미세구조로 모델링하지 않는다. 먼저 frozen IEDM baseline의 model contract 작성: (i) 지배방정식, (ii) 층별 representation(균질/유효/explicit), (iii) 계면 연속/접촉저항, (iv) 경계조건 및 면적, (v) 열원, (vi) 검증 가능한 관측량.
- 지배식(steady): ∇·(K∇T)+q'''=0; passive layer 내부 q'''=0; K는 필요시 tensor. 완전접합 계면은 T와 normal heat flux 연속, 유한 계면저항은 ΔT=q''R''. 대류 경계 q''=h(T_s−T∞). 전역 열수지 ΣP=ΣQ_out.
- 중요 상태 경고: 현재 공유 `Run_008_Reference/hbm_gpu_2p5d.py`는 TIM2=40µm,k=5.2를 포함하고 상단 HTC가 TIM2 면에 걸리는 구조(line 86–87,107–108,367–368,1107); 이건 원래 IEDM Fig.2(c) 표에 보이는 die–lid TIM + lid 상부 HTC baseline과 구별해야 한다. 따라서 논문 baseline을 검증할 때 TIM2 변형 및 microbump 교체 등 후속 수정과 분리된 frozen model/config를 우선 확보해야 한다.
- 추천 첫 활동: actual script를 source of truth로 baseline-vs-modified inventory 작성. 이후 민감도/ΔT budget을 근거로 deep dive 선택. 기존 Run_055 기반 bookkeeping에서 TIM1 구간이 GPU ΔT의 약 39%로 보고됐으므로 TIM1 effective joint model은 유력 첫 물성 후보이나, 이는 현 모델의 열강하 분해이지 독립 실험 검증은 아니다. BEOL explicit RVE는 scale-modeling subtask이며, 해당 layer 물성 민감도와 routing data 접근성 확인 뒤 결정.
- 단계 구분: (A) IEDM setup reproduction/verification (B) lab-specific layer constitutive model (C) heat-spreader design study. 모델 변경 없이 baseline 검증 완료 후 B/C 진행해 혼합효과 방지.

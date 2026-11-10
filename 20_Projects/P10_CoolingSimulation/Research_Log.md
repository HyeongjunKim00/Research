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

## 참고자료 (2026-11-10 추가)
- `References/HIR_Thermal_2025_notes.md` — HIR 2025 Thermal 챕터 [B] 발췌. 핵심: ①콜드플레이트
  h=30000(≈150 W/cm²)이 액냉/제트/마이크로채널 실존 한계 구간에 정합 → 상단 경계 타당성 보강,
  ②HBM 40 W/스택은 보수적(최신 60 W+), ③우리 GPU 국소 heat flux는 업계 추세(>4 W/mm²)보다
  완만(핫스팟 보수적), ④Phase 4 한계선 후보: 핫스팟 >100°C, HBM Tjmax ~95–105°C.

# Phase 2 결과: 힛스프레더 유무 (lid vs lidless)

날짜: 2026-11-09 · 실행: 랩 원격 PC(AEDT 2026 R1) 배치

## 조건 (고정)
- 콜드플레이트 HTC 30,000 W/m²K, 라미네이트 200, 주변 20°C, 전도 전용
- GPU 414 W (배경비율 **BG=0.39** = 논문 69.1°C에 맞춘 보정값), HBM 40 W/스택 ×4
- 수렴 메시(전역 0.25 mm + die 0.5/0.5/0.02 mm)
- lidless = 방식 (b): lid 제거, HTC를 TIM 상면(54×24, die+mold 상면)에 직접

## 결과 (2026-11-10 교정맵 재검증, Run_012~015)
발열맵 교정(NVLink 제거·GPU-측 HBM PHY 정립) 후 재실행. 값은 교정 전과 ±0.03°C로 동일 → 확정.

| 케이스 | GPU peak | HBM base(4스택 평균) | 폴더 |
|---|---|---|---|
| Lidded BG50 (Phase1 브라켓↓) | 66.53°C | 56.36 | `Run_012_Lidded_BG50/` |
| Lidded BG30 (Phase1 브라켓↑) | 71.05°C | 56.16 | `Run_013_Lidded_BG30/` |
| **Lidded BG39** (논문 앵커) | **69.01°C** | 56.25 | `Run_014_Lidded_BG39/` |
| **Lidless BG39** (방식 b) | **74.26°C** | 57.03 | `Run_015_Lidless_BG39/` |
| **Δ (lidless − lidded)** | **+5.25** | +0.78 | |

BG50(66.5)·BG30(71.1)이 논문 69.1°C를 재브라켓 → BG≈39% 앵커 유지. (구 Run_010/011도 폴더 보존.)

> 주의: Run_012~015 `object_temperatures.csv`는 교정 전 geometry.csv로 post돼 유령 NVL행(nan)·
> PHY행 누락·power열 구값이 섞임. **Tmax/peak/HBM base 는 solved 실값이라 정확.** 다음 run부터
> 런처가 런마다 geometry 재생성해 자동 클린(필요 시 post-only 재실행으로 완전 클린 CSV 획득).

(값은 각 폴더 `object_temperatures.csv`에서 `analyze_results.py` 정의로 산출: GPU = group∈{gpu, src_gpu}의 Tmax 최대, HBM base = 스택별 base 블록 Tmax 최대의 4스택 평균)

## 해석
1. **검증 쐐기**: lidded GPU peak 69.0°C가 논문 2.5D 값 69.1°C에 정합 → Phase 1 검증을 데이터로 완결.
2. **Phase 2 답**: 현재 칩 크기(GPU 30×22 mm, ~660 mm²)에선 **힛스프레더가 냉각에 유리**(제거 시 GPU +5.2°C). lid의 횡방향 확산(→ 넓은 65×65 콜드플레이트 면적)이 추가 TIM/lid 저항보다 이득. 지도교수 가설(대형 가속기 lidless 유리)의 **역전 지점은 Phase 5 칩 크기 sweep**에서 검증.

## 각 폴더 파일
- `object_temperatures.csv` — 객체 260개별 Tmax/Tmin/전력 (핵심 결과)
- `hbm_gpu_2p5d_report.txt` — 스택 층·물성·발열원 분해, 경계조건
- `hbm_gpu_2p5d_{section,top,sources}.svg` — 2D 단면/상면/발열원 도면
- `build_done.txt`/`solve_done.txt`/`post_log.txt` — 실행 로그 (solve OK, wall-clock 포함)

## 주의
- lidless는 방식 (b)라 "확산 소실 + 냉각면적 축소"가 섞인 **순효과** — 확산만의 기여는 방식 (a)로 별도 확인 가능.
- post의 `ExportMeshStats/ExportConvergence`는 이 AEDT 빌드에 없어 실패(결과 무관).
- lidless `object_temperatures.csv`에 유령 "Lid" 행(nan) 1개 — group 필터로 GPU/HBM 산출엔 영향 없음.
- 무거운 온도장(`*.fld`)·`*.aedtresults`는 공유 제외(원격에만 보관).

# P10 Cooling Simulation

## 목적
P10 냉각 시뮬레이션 작업, 실행 조건, 분석 및 보고서를 관리한다.

## 원본 데이터
원본 해석 파일 위치: `C:\AnsysSim\projects\P10_CoolingSimulation\Runs\Run_008_MeshGlobal025\Model`.
용량·바이너리인 `.aedt` / `.aedtresults` / `.fld` 필드는 Git에 올리지 않는다.

공유·이어받기용 **텍스트 산출물**은 `01_Simulation/Icepak/Run_008_Reference/`에 둔다
(빌드/드라이버/후처리 `.py`, 발열원 리포트, 형상 CSV, 2D SVG, 결과 요약). 실행 방식과 경로 수정 안내는
해당 폴더의 `README.md` 참조. 다른 PC에서 돌릴 땐 스크립트의 하드코딩 경로를 그 PC 기준으로 바꿔야 한다.

## 실행 기록
각 실행의 solver/version, 모델 버전, mesh 설정, 경계조건, 열부하, 수렴 기준, 출력 위치를 로그에 남긴다. 서로 다른 조건의 결과는 조건을 명시하지 않고 직접 비교하지 않는다.

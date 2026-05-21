---
name: korea-canslim
description: >
  한국식 CAN SLIM 다(多)사이클 조사 파이프라인. 코스피/코스닥 강세장 사이클을
  자동 탐지해, 특정 사이클(또는 미조사 다음 사이클)의 "사후 최대 상승 위너 ×
  폭발 직전 변수" 모델북·리포트를 *기존과 동일한 품질·방법론*으로 재현하고
  교차사이클로 한국식 CAN SLIM 근거를 누적한다. 사용자가 "다음 사이클 조사",
  "c2020-03 사이클 돌려줘", "한국식 캔슬림 강화" 등을 요청할 때 사용.
---

# 한국식 CAN SLIM 사이클 조사 스킬

오닐 "그레이트 위너 모델북"을 한국 시장에 사이클별로 재현. 모든 산출은
`my-stock/research/oneil-model-book/cycles/<cycle_id>/`, 전역 누적은
`research/oneil-model-book/{analysis_history.md,cross_cycle.md,korea_canslim.md}`.

## 불변 원칙 (절대 위반 금지)
- **환각 금지**: 미가용 변수는 추정 말고 결손 명시(`*_src`). 가용 범위(정정):
  상장일=전 사이클 / 발행주식수=2015+(data.go.kr→DART stockTotqySttus 폴백) /
  일별수급 frgn=~2010+(페이지 확대, 옛 사이클일수록 느림) / DART 재무=~2015+
  충실 / 가격·RS·M·base·돌파일=전 사이클. pre-2010~2015 잔여 결손만 명시.
- **point-in-time 유지**, **CAN SLIM 사전 적용 금지**(사후 공통점 추출만),
  **위너·pivot 정의 불변**: 지속성 필터(유지율 50% & 상승 60일↑), pivot
  되돌림 허용폭 20%, 돌파일 별도 검증.
- 사용자 룰: 데이터 재생성 테스트는 소규모(--limit) 먼저, 통과 후 전체.

## 절차

### 0. 사이클 탐지 + 통지 (착수 전 필수)
```
python scripts/oneil_model_book/detect_cycles.py
```
→ `cycles/cycles_index.json` 의 강세장 목록을 사용자에게 표로 통지.
대상 사이클 결정: 사용자가 지정한 `cycle_id`(예 c2020-03), 없으면 *미조사
사이클*(= `cycles/<id>/model_book.json` 부재) 중 데이터가 가장 충실한 최신
쪽부터. **선택한 사이클의 앵커→종료·지수 상승률·데이터 가용 한계를 먼저
사용자에게 알린 뒤** 진행(사용자 요구사항).

### 1. 소규모 검증
```
set OMB_CYCLE=<cycle_id>   (PowerShell: $env:OMB_CYCLE='<cycle_id>')
python scripts/oneil_model_book/discover_winners.py        # 위너 발굴(전 종목 스캔)
python scripts/oneil_model_book/refine_winners.py          # 지속성 필터·상위 N
python scripts/oneil_model_book/detect_pivot.py
python scripts/oneil_model_book/collect_variables.py --limit 3
```
EPS/매출(DART, 키 페일오버 자동)·발행주식수(data.go.kr)·수급(frgn) 값과
결손 사유, 소요시간 확인. 옛 사이클이면 frgn/발행주식수 결손이 정상(명시).

### 2. 전체 실행 (검증 통과 후, 백그라운드 권장)
```
python scripts/oneil_model_book/compute_rs.py        # 5y 캐시→RS, model_book 머지
python scripts/oneil_model_book/collect_variables.py # 전체 (메모이즈·페일오버 내장)
python scripts/oneil_model_book/breakout_check.py    # 돌파일 거래량·신고가
python scripts/oneil_model_book/build_report.py
python scripts/oneil_model_book/analyze_commonality.py   # _agg_N + analysis_history append
python scripts/oneil_model_book/analyze_cross_cycle.py   # cross_cycle.md 재생성
python scripts/oneil_model_book/analyze_buy_timing.py --limit 200  # 매수타이밍 시그니처
python scripts/oneil_model_book/analyze_buy_timing_control.py        # 타이밍 단독 정밀도(대조군)
python scripts/oneil_model_book/build_control_sample.py --n 100      # 비위너 대조군 표본
OMB_CYCLE=<id>-ctrl python scripts/oneil_model_book/detect_pivot.py  # (대조군: universe 캐시 복사 후)
OMB_CYCLE=<id>-ctrl python scripts/oneil_model_book/compute_rs.py
OMB_CYCLE=<id>-ctrl python scripts/oneil_model_book/collect_variables.py
python scripts/oneil_model_book/analyze_selection_lift.py            # 선별축 enrichment(위너 vs 대조군)
```
(대조군: `build_control_sample.py`로 비위너 무작위 표본 → 위너 model_book과
동일 변수 수집 → `analyze_selection_lift.py`가 축별 *변별력*(enrichment) 산출.
"위너 사후 빈도≠선별력" 교정 근거. cyclecfg 미지 OMB_CYCLE은 레거시 폴백,
`_universe_prices*.json`을 ctrl 디렉터리로 복사 후 compute_rs.)
(compute_rs 는 collect_variables 보다 먼저 실행해 rs.json 머지 후 collect 가
RS를 합치도록 — 기존 순서 유지: discover→refine→detect_pivot→collect→
compute_rs→breakout→build_report→analyze_*.)

### 3. 표본 확장
`refine_winners.py` 의 `TOP_N` 을 30→100→200… 늘리며 2단계 반복.
사이클마다 `analyze_commonality.py` 가 `[cycle_id] N=*` 스냅샷을
`analysis_history.md` 에 무손실 append.
`analyze_buy_timing.py --limit 30→100→200` 도 함께 단계 확대 — *추세확인
후보 제약*(종가>상승50일선 & >20거래일전; 제약 없으면 R이 바닥으로
degenerate→예측 불가) 하의 사후 최적진입 시그니처를 `_buytiming_N*.txt`·
`buy_timing_rows.json`·전역 `buy_timing.md` + `analysis_history.md` append.

### 4. 한국식 CAN SLIM 강화
`cross_cycle.md`(자동)의 "글자별 사이클 일관성"을 근거로
`korea_canslim.md`(큐레이션 문서)를 *사람 검토 후* 버전업(v1→v2…):
여러 사이클 반복 성립 → 신뢰도↑·컷오프 구체화, 엇갈리면 '국면 의존' 표기.
**자동 덮어쓰기 금지 — 데이터 인용으로만 갱신**.

## DART 한도 대응
`canslim_lib/fetch.py` `dart_get` 가 status 020 시 `DART_API_KEY →
DART_API_KEY2` 자동 페일오버. 두 키 모두 소진 시 중단·결손 명시(무한재시도 X).
대량 다사이클 실행은 메모이즈(collect_variables `lru_cache`)와 병행 필수.

## 산출 위치
- 사이클별: `research/oneil-model-book/cycles/<id>/`
  (winners_final·pivots·rs·breakout·model_book(.json/.csv)·REPORT.md·_agg_N*)
  + `_buytiming_N*.txt`·`buy_timing_rows.json`(매수타이밍 시그니처·원자료)
- 전역: `analysis_history.md`(스냅샷 누적), `cross_cycle.md`(사이클 비교·근거),
  `buy_timing.md`(오닐 9축×한국 best_entry 대조·한국형 매수규칙 v1·정직한
  생존자 한계, 수동 버전업), `korea_canslim.md`(기준 v1, 수동 버전업),
  `cycles/cycles_index.json`(사이클 정의)

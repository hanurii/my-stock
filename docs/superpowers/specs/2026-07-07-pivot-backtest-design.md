# SEPA 피벗 백테스트 (1개월 전 스냅샷) + 승자 특징 분석 — 설계

날짜: 2026-07-07
상태: 설계 확정 대기 (사용자 리뷰 전)
기준 브랜치: `feat/pivot-backtest` (origin/master 기준)

## 목적

**"1개월 전 시점, SEPA 정석대로 패턴 피벗 돌파에서 샀으면 +10%/-5% 승률이 어땠나"** 를 편향 없이(전 종목 point-in-time) 확인하고,
**이긴 종목들의 공통 특징**(가격대·거래량·패턴·RS 등)을 뽑아 인사이트를 얻는다. 먼 기간은 후속 과제.

## 사용자 확정 사항

- **유니버스**: 과거 그 시점에 존재한 **전 종목**(캐시 3,032). RS·트렌드 통과분만(SEPA 정석 게이트).
- **기준일 D = 2026-06-05** (오늘 2026-07-07의 1개월 전 최근 거래일). 전진 데이터 = D 이후 캐시 마지막(2026-07-06)까지 **21거래일**.
- **시뮬**: 피벗에서 매수, **+10% 목표 / −5% 손절**, 장중(고가/저가) 선착 판정. **돌파 당일 포함**.
- **같은 날 +10%·−5% 둘 다 닿음 = 일봉으론 순서 판별 불가 → `ambiguous`(예외)로 분류**, 손절 우선 안 함. 예외 목록을 사용자에게 전달 → 사용자가 분봉으로 직접 확인.
- 산출: 리포트 + JSON. 웹페이지는 범위 밖.

## 전체 파이프라인 (신규 오케스트레이터 `scripts/pivot_backtest.py`)

```
① as-of D 트렌드 스캔  — 전 종목 트렌드 템플릿(asof=D) 통과 + RS(as-of D)
        ↓ (통과분만)
② 패턴 돌파 검출        — VCP·PP·3C 검출기 replay(asof=D), 돌파일 ∈ [D-10, D] 인 최근 돌파 이벤트
        ↓ (엔트리 = 피벗, 돌파일)
③ 피벗 트레이드 시뮬     — 돌파일 포함 전진, +10%/-5% 선착 (신규 simulate_pivot_trade)
        ↓
④ 특징 태깅 + 집계       — 이벤트별 특징 → 승률 by 특징 구간
        ↓
⑤ 산출                  — pivot-backtest JSON + 리포트(.md), ambiguous 예외 목록 포함
```

**재사용**: 트렌드 asof(`evaluate_trend_template`/`evaluate_single`에 asof 존재), 패턴 검출·history replay(`vcp_history`/`power_play_history`/`cheat_history`의 `replay_*`·`find_breakout_events`), OHLCV 캐시(`ohlcv_matrix`). **신규**: as-of D RS 조립, `simulate_pivot_trade`, 특징 분석·리포트, 오케스트레이터.

## ① as-of D 트렌드 게이트

- 각 종목 시계열을 **≤ D 로 잘라** 트렌드 템플릿 8조건 평가(`evaluate_trend_template`).
- **RS as-of D**: 잘린 시계열로 종목별 252거래일(부족 시 단축) 수익률 → **D 시점 전 종목 교차 순위**로 RS 백분위 산출(기존 `_compute_rs_for_all` 로직을 asof=D 로 1회 실행). D 시점엔 데이터 ~370거래일이라 사실상 완전 RS 가용.
- 통과 기준: 기존 SEPA 트렌드 통과 + RS ≥ 80(find-trend-template 실전 기준).

## ② 패턴 돌파 검출 (통과분만)

- 통과 종목마다 VCP·PP·3C 각 검출기를 **asof=D 로 replay** → `find_breakout_events`.
- 엔트리 채택: **돌파일이 [D−10, D] 구간인 가장 최근 돌파 이벤트**(스냅샷 시점의 "신선한 돌파"). 한 종목이 여러 패턴서 잡히면 **패턴별로 각각 1엔트리**(패턴별 승률 비교 위해).
- 엔트리 레코드: `{code, name, market, pattern, breakout_date, pivot_price, rs, + 패턴 지표}`.

## ③ 피벗 트레이드 시뮬 — `simulate_pivot_trade(series, breakout_idx, pivot, target_pct=10, stop_pct=5)`

엔트리 = `pivot`. `T = pivot×1.10`, `S = pivot×0.95`. 돌파일 인덱스 `b`부터 시계열 끝까지 전진:

- **돌파 당일(i = b)**: 피벗은 아래→위로 뚫리므로 당일 저가는 매수 전 저점일 수 있음.
  - `high ≥ T` **그리고** `low ≤ S` → **ambiguous**
  - `high ≥ T` (저가 무관) → **win** (당일 급등)
  - `low ≤ S` 만 → **ambiguous** (매수 전 저점 가능, 손절로 단정 안 함)
  - 둘 다 아님 → 다음 날
- **이후(i > b)**: 보유 확정 상태.
  - `high ≥ T` 그리고 `low ≤ S` (같은 날 둘 다) → **ambiguous**
  - `high ≥ T` 만 → **win**
  - `low ≤ S` 만 → **loss**
  - 둘 다 아님 → 다음 날
- 시계열 끝(2026-07-06)까지 미결 → **unresolved** (아직 진행 중; 현재 등락률 기록).

반환: `{result: win|loss|ambiguous|unresolved, resolve_date, days_held, exit_reason, gain_at_resolve_pct, max_gain_pct, max_dd_pct}`.

> 21거래일 창이 짧아 **unresolved 상당수 예상**은 정상. 승률은 두 가지로 — (a) 결착분(win/loss)만, (b) 전체(ambiguous·unresolved 분모 포함/별도).

## ④ 특징 태깅 + 집계

이벤트별 특징:
- `pattern`(VCP/PP/3C), `market`(코스피/코스닥)
- **가격대 버킷**(피벗 기준): `<2천 / 2~5천 / 5~1만 / 1~2만 / 2~5만 / 5만+`
- **돌파일 상대거래량** = 돌파일 거래량 ÷ 직전 50일 평균 (버킷 `<1 / 1~1.5 / 1.5~2 / 2~3 / 3+`)
- **RS 버킷** (`80~89 / 90~94 / 95~100`)
- 패턴 지표: VCP 수축 횟수·베이스 깊이 / 3C 컵 깊이·선반 / PP 깃대 상승률·깃발 깊이
- `days_held`(결착 소요일)

집계: **전체 + 패턴별 + 각 특징 버킷별 승률**(결착 기준). 표본 n 병기, **격차 큰 특징 하이라이트** + **승자 프로파일**(win 이벤트의 최빈 특징 조합).

## ⑤ 산출

- `public/data/pivot-backtest-2026-06-05.json` — 파라미터·이벤트 배열(결과·특징)·집계·**ambiguous 예외 목록**.
- **리포트** `docs/research/2026-06-05-pivot-backtest.md` — 요약(전체/패턴별 승률) + 특징별 승률 표 + 인사이트 문장 + **예외 종목 목록(분봉 확인 요청)** + 한계.

## 신규/수정 파일

- `scripts/canslim_lib/pivot_backtest.py` (신규) — `simulate_pivot_trade` + as-of RS 조립 헬퍼 + 특징 태깅. **순수 로직, pytest 대상**.
- `scripts/pivot_backtest.py` (신규) — 오케스트레이터(캐시 순회·트렌드 asof·패턴 검출·시뮬·집계·JSON/리포트 저장). 옵션 `--asof 2026-06-05`.
- `tests/test_pivot_backtest.py` (신규) — `simulate_pivot_trade` 단위테스트.
- 산출물 2개(JSON·리포트).

## 테스트 (`simulate_pivot_trade`)

- 돌파 당일 +10% 급등 → win.
- 돌파 당일 저가만 −5% → ambiguous(매수 전 저점).
- 돌파 당일 고·저 둘 다 → ambiguous.
- 이후 날 고가만 +10% → win / 저가만 −5% → loss / 둘 다 → ambiguous.
- 끝까지 미결 → unresolved(+등락률).

## 실행 인프라

- 캐시(`.cache`)는 메인 워크트리에만 존재(gitignore) → 워크트리에 **정션 연결**(설정 완료). 스크립트는 워크트리에서 실행.
- 산출 JSON은 `public/data/`라 커밋·배포 대상. 리포트도 커밋.

## 정직한 한계 (리포트에 명시)

1. **전진 창 21거래일**로 짧음 → unresolved 많음. 이번은 "1개월 전 스냅샷 1건"의 탐색적 결과.
2. **단일 기준일·단일 국면** → 일반화 금지. 더 먼 기간·다중 기준일은 후속.
3. **잔존 생존자 편향**: 캐시는 2024-11 이후분 위주, 그 전 상폐주 없음.
4. **ambiguous**는 일봉 한계 → 사용자 분봉 확인 후 승/패 확정 필요.

## 범위 밖 (후속)

- 다중 기준일·장기간(다국면) 백테스트, 웹페이지 시각화, 파라미터 스윕(다른 목표/손절), ambiguous 자동 분봉 판정.

# 분봉 기반 예외(ambiguous) 판정기 설계

날짜: 2026-07-07
상태: 설계 확정 대기 (사용자 리뷰 전)
기준 브랜치: `feat/resolve-ambiguous` (origin/master 기준)

## 목적

SEPA 피벗 백테스트(`pivot-backtest-2026-04-01.json`)의 **예외(ambiguous) 50건** — 일봉으론
"돌파 당일 +10%와 −5% 중 무엇이 먼저였는지" 못 가린 건들 — 을 **과거 1분봉**으로 되짚어
승/패로 확정한다. 사용자 실전 룰(피벗 자동매수 체결 → +10%/−5% 선착 매도)과 동일하게 판정.

## 배경 (feasibility 확인됨)

- KIS `FHKST03010230`(주식일별분봉조회, `inquire-time-dailychartprice`)가 **과거 특정일 1분봉**을 준다.
  콜당 ~120봉, `FID_INPUT_HOUR_1`(end 시각)을 앞으로 당기며 **역방향 페이징**으로 09:00~15:30 전체 확보(~4~6콜/일).
  2026-03월(≈108일 전)도 정상 반환 확인. 검증된 페이징 로직: 기존 `scripts/_fetch_min_all.py`.
- 예외 50건은 **전부 돌파 당일**의 애매함(`stop_on_breakout_day`/`both_same_day(_breakout)`)이라,
  대부분 **돌파 당일 분봉만** 있으면 풀린다. 이후는 일봉 선착으로 깨끗이 이어짐.

## 핵심 규칙 (사용자 확정)

- **진입(체결) 시점** = 가격이 **피벗에 처음 닿는 분**(고가 ≥ 피벗). 자동매수 체결 = 피벗 돌파 순간.
- 진입 분부터 당일 분봉 전진 **선착**: 고가 ≥ 피벗×1.10 먼저 → **win** / 저가 ≤ 피벗×0.95 먼저 → **loss**.
  진입 **전**의 −5% 저점은 매수 전이라 **무시**(예외의 원인).
- 당일 진입 후 아무것도 안 닿으면 → 그날 보유, **이튿날부터 일봉 선착으로 재개**(추가 분봉 불필요).
  드물게 이후 날이 '같은 날 둘 다'면 그 날만 분봉 추가 판정.
- **판정 불가**(KIS 미반환/진입과 −5%가 **같은 1분봉** 내 동시) → `ambiguous` 유지(사용자 눈확인 대상).

## 사고 재발 방지 (중요)

- **공유 캐시에 정션을 걸지 않는다.** 오케스트레이터는 `.env`·`.cache` 를 **주 작업트리 절대경로**로 참조한다:
  `MAIN = C:\Users\hanul\playground\my-stock`, `.env`·`.cache/min_daily` 모두 그 아래. 이러면 어느 워크트리에서 실행해도 동일 대상이고 정션이 불필요하다.

## 구성 (3파일)

### 1) `scripts/canslim_lib/minute_bars.py` (신규)

`fetch_day_minutes(code, date, force=False) -> list[dict]` — 특정일 1분봉(오름차순 시각)을 페이징 수집.
- 캐시: `MAIN/.cache/min_daily/<code>_<YYYYMMDD>.json` (있으면 재사용, KIS 재호출 안 함 — 백업에도 포함됨).
- 반환 bar: `{"t":"HHMM", "o","h","l","c","v"}` (float). KIS 필드 `stck_cntg_hour/stck_oprc/stck_hgpr/stck_lwpr/stck_prpr/cntg_vol`.
- TR `FHKST03010230`, `end='153000'` 부터 earliest−1분으로 페이징, earliest ≤ '0900' 이면 종료(최대 ~8콜, 콜당 0.1s throttle).
- 실패(rt_cd≠0/빈 응답/타임아웃 재시도 소진) → 빈 리스트 반환(오케스트레이터가 unresolved 처리).
- 검증된 `_fetch_min_all.py` 의 `call`/`hhmm_dec`/`fetch_day` 로직을 정리·모듈화(과거 TR로 교체).

### 2) `scripts/canslim_lib/pivot_backtest.py` 에 순수 함수 추가

`resolve_minute_trade(minutes, daily, breakout_idx, pivot, target_pct=10.0, stop_pct=5.0) -> dict`
- `minutes`: 돌파 당일 1분봉 리스트(오름차순). `daily`: 전체 일봉 series(이후 날 재개용). `breakout_idx`: 일봉상 돌파일 인덱스.
- 로직:
  1. 분봉이 비었으면 → `{"result":"ambiguous","reason":"no_minute_data"}`.
  2. 진입 분 = 첫 `h ≥ pivot`. 없으면(장중 피벗 미도달, 이론상 없음) → `ambiguous`.
  3. 진입 분부터 끝까지: 같은 분에 `h≥T` **그리고** `l≤S` → `ambiguous`(reason `same_minute`);
     `h≥T` → `win`; `l≤S` → `loss`.
  4. 당일 진입 후 미결 → **이튿날 이후 일봉 "일반 보유일" 선착**으로 재개: `daily` 의 `breakout_idx+1 .. 끝`
     각 날마다 `high≥T` 그리고 `low≤S` → `ambiguous`(reason `later_day_both`, resolve_date=그 날);
     `high≥T` → `win`; `low≤S` → `loss`; 끝까지 미도달 → `unresolved`.
     (주의: `simulate_pivot_trade` 를 그대로 쓰면 돌파일 특례(손절만=ambiguous)가 이튿날에 잘못 적용되므로,
     돌파일 특례 없는 이 "일반 보유일" 선착을 별도 헬퍼 `_daily_first_touch(daily, start_idx, pivot, T, S)` 로 구현.
     같은 헬퍼를 `simulate_pivot_trade` 의 i>b 분기가 쓰도록 리팩터해 로직 1벌 유지.)
- 반환: `{result: win|loss|ambiguous, resolved_by:"minute"|"daily", entry_time, resolve_date, reason}`.
- **pytest 대상**(합성 분봉으로 진입·선착·미결→일봉재개·same_minute 검증).

### 3) `scripts/resolve_ambiguous.py` (신규 오케스트레이터)

- `--infile public/data/pivot-backtest-2026-04-01.json`(기본).
- `.env`(MAIN 절대경로) 로드 → KIS. 각 `ambiguous` 이벤트:
  `fetch_day_minutes(code, breakout_date)` → `resolve_minute_trade(...)` → 이벤트 `result` 갱신 + `minute_resolution` 기록.
- 갱신: `events` 내 해당 이벤트 result 교체, `summary`/`by_pattern`/`by_feature`/`summary_stock_level` **재집계**(기존 `tally`/`group_win_rate`), `ambiguous` 리스트는 **남은 미결만**.
- JSON 덮어쓰기 저장 + `scripts/pivot_backtest_report.py` 재실행으로 리포트 갱신(예외↓·결착↑·정직 범위 축소).
- KIS 스로틀링·진행 로그. 재사용: 다른 백테스트 JSON도 `--infile` 로.

## 데이터 흐름

```
pivot-backtest-2026-04-01.json(ambiguous 50)
   → resolve_ambiguous.py ─ fetch_day_minutes(KIS FHKST03010230, .cache/min_daily 캐시)
                          └ resolve_minute_trade(분봉 진입→선착, 미결 시 일봉 재개)
   → JSON 갱신(win/loss 확정, 미결만 ambiguous) → 리포트 재생성
```

## 테스트

- `resolve_minute_trade`(순수): ① 진입 후 당일 +10% → win ② 진입 후 −5% → loss
  ③ 진입 전 −5% 후 미도달 → 일봉 재개 결과 ④ 진입·−5% 같은 분 → ambiguous(same_minute)
  ⑤ 분봉 없음 → ambiguous(no_minute_data).
- `minute_bars`: 실 KIS 의존이라 단위테스트 대신 오케스트레이터 소규모 실호출(1~2건)로 스모크.

## 산출물

- 갱신된 `public/data/pivot-backtest-2026-04-01.json`(예외 대부분 확정) + `docs/research/2026-04-01-pivot-backtest.md`.
- `.cache/min_daily/*.json`(gitignore, 백업 포함).

## 한계

- KIS 과거 분봉 보관 한계에 걸리는 가장 오래된 소수, **같은 1분봉 내 동시** 케이스는 여전히 예외로 남김.
- 1분봉도 봉 내부 순서는 모름(고가·저가 동시 봉) — 그 경우만 same_minute 예외.

## 범위 밖

- 실시간/당일 판정, 다른 기준일 백테스트 대량 재판정, 틱 단위 정밀화.

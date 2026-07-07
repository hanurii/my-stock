# 봇 리플레이 모드 설계

날짜: 2026-07-07
상태: 설계 확정(사용자 승인) — 스펙 리뷰 대기
기준 브랜치: `feat/bot-replay` (origin/master eefed88)

## 목적

과거 특정일 D를 골라 **KIS 자동매수 봇의 실제 판정 로직**([[sepa-nextday-breakout-findings]]의 `scripts/autobuy/signals.py`)에 그날 분봉을 하루치 흘려보내, "그날 봇이 라이브로 돌았다면 낸 매수·매도"를 **봇과 동일한 로그 형식**으로 재현한다. 사용자가 "특정 날로 돌아가 실전처럼" 보고 싶어 하는 요구의 답. 실자금·실주문 없음(순수 과거 데이터 시뮬레이션).

## 범위

- 입력: **진입일 D 하나**(예: `--date 2026-04-07`). 스캔일 = 그 직전 거래일 D-1.
- 봇의 실제 함수(`evaluate_entry`·`evaluate_exit`·`is_uptrend`)를 그대로 재사용 — 리플레이용으로 판정 로직을 재구현하지 않는다.
- 청산은 **결착될 때까지 추적**(D 당일 분봉 → 이후 일봉 선착).
- 범위 밖: 여러 날짜 배치, 슬리피지·부분체결 모델, 실주문.

## 사용자 확정 결정

- 입력 = 진입일 D 하나(그날 하루 재현).
- 매수 판정 = **분 종가 기준**(그 분 종가를 현재가로 evaluate_entry). 청산 = **분 고/저 터치**(+20%/−10%).
- 청산 추적 = 결착(익절/손절)까지. D 마감까지 미청산분은 D+1부터 일봉으로 이어감.

## 구성

```
① 후보 생성 (재사용: scripts/pivot_backtest_nextday.py 로직)
   - D-1 종가로 시계열 절단 → 각 종목 evaluate_vcp/cheat/power_play 로 status=='actionable' + pivot,
     트렌드 템플릿 통과(RS≥80). 반환 [{code,name,pivot,pattern}].
   - 국면 게이트: build_ew_index + is_uptrend(D-1 기준). 하락추세면 "매매 OFF" 로그 후 종료.
② 분봉 리플레이 엔진 (신규: scripts/autobuy/replay.py)
   - 각 후보 D일 1분봉 수집(minute_bars.fetch_day_minutes(code, D), 캐시 재사용).
   - 09:00~15:30 분 단위 전진:
     · 누적거래량(그 분까지 분봉 volume 합), elapsed_frac(경과비율) 갱신.
     · 미보유 후보: 그 분 종가=현재가로 evaluate_entry(가격·피벗·누적량·avg50·elapsed_frac,
       slots_used·slots_max·held=False). 매수면 그 분 종가로 진입 기록 + 매수 로그.
       (extended면 그날 영구 스킵) 신호 초과 시 pace 높은 순.
     · 보유 종목: 그 분 high≥진입가×1.20 → 익절 / low≤진입가×0.90 → 손절(손절 우선). 매도 로그.
③ 결착 추적 (신규 얇은 헬퍼 or 재사용)
   - D 마감까지 미청산 포지션 → D+1부터 일봉(ohlcv_matrix)으로 +20/−10 선착(같은날 both면 손절 가정).
     결착 시 익절/손절 + 날짜 로그.
④ 출력
   - 봇 로그 형식 그대로: `HH:MM 매수 {code} {name} @{price} pace{x:.1f}` ·
     `HH:MM 매도 {code} 익절|손절 @{price}` · (일봉결착은 `YYYY-MM-DD 매도 ...`)
   - 요약: 감시목록 N · 매수 N · 익절 N · 손절 N · 미청산 N · 순손익(익절+20/손절-10 합산)
```

## 봇과 동일하게 지키는 규칙

`scripts/autobuy/config.CFG` 재사용: SLOTS(10)·VOL_PACE_MIN(1.5)·CHASE_MAX_PCT(3.0)·TARGET_PCT(20)·STOP_PCT(10)·MARKET_OPEN(0905)·NEW_BUY_UNTIL(1520). 신규매수는 09:05~15:20 분만, 그 뒤는 청산만. 1종목 1포지션, 추격 +3% 하드.

## 데이터·의존

- `scripts/canslim_lib/minute_bars.fetch_day_minutes(code, date)` — 과거 1분봉(캐시 `.cache/min_daily`, 정션 없이 주 작업트리 절대경로).
- `scripts/canslim_lib/ohlcv_matrix.get_series(code)` — avg50 거래량 + 일봉 결착.
- `scripts/autobuy/signals`·`watchlist`·`config` — 봇 로직 재사용.
- 캐시·후보 JSON은 주 작업트리(my-stock) 절대경로 참조(정션 금지).

## 신규 파일

- `scripts/autobuy/replay.py` — 리플레이 엔진 + 순수 핵심(`replay_day_minutes`) + CLI(`--date`, `--slots` 옵션).
- 후보 생성은 pivot_backtest_nextday의 함수를 import 하거나, 그 로직을 얇은 헬퍼로 추출해 replay·backtest 공용.

## 테스트

- **순수 핵심 `replay_day_minutes(minutes_by_code, candidates, avg50_by_code, cfg)` → 이벤트 리스트**를 합성 분봉으로 pytest: (1) 피벗 돌파+거래량 충족 분에 매수 (2) 추격 +3% 초과분 스킵 (3) 진입 후 +20% 분에 익절, −10% 분에 손절 (4) 슬롯 초과 시 pace 우선.
- 실제 판정은 검증된 봇 함수 재사용이라 얇게. KIS 분봉/후보 생성은 소규모 실호출 스모크(오케스트레이터).

## 산출물

- CLI 실행 시 콘솔에 봇-형식 로그 + 요약. 선택: `public/data/bot-replay-<date>.json`(이벤트·요약 저장).

## 한계

- **1분봉 해상도**(틱 아님) — 분 내부 순서 근사(진입=분 종가, 청산=분 고/저 터치, 같은 분 익절·손절 동시면 손절 우선).
- 바쁜 날은 후보 많아(최대 ~150) KIS 분봉 수집 수 분 소요(캐시분 빠름). 미반환 종목은 감시 제외로 로그.
- 슬리피지·부분체결 미모델(백테스트와 동일 가정). 생존편향·9개월 캐시 한계 동일.

# 거래량 매수 실시간 검증 관찰기 설계

날짜: 2026-07-08
상태: 설계 확정(사용자 승인) — 스펙 리뷰 대기
기준 브랜치: `feat/stocks-sepa-page`

## 목적

KIS 자동매수 봇([[sepa-nextday-breakout-findings]]의 `scripts/autobuy/`)이 **거래량에 따라 어떻게 매수하는지**를, 모의계좌·실주문 없이 **실시간으로 검증**한다. 봇의 실제 매수 판정 함수(`signals.evaluate_entry`)를 그대로 재사용해 "감시 후보를 지금 라이브로 판정하면 무엇을 사고 무엇을 왜 거르는지"를 후보별 상세 로그로 보여준다. 사용자 요구: *"등가중 지수(국면)에 상관없이, 거래량 1.5배 이상인 종목을 피벗 +3% 이내 가격일 때 사는 식으로 실시간 검증."*

## 범위

- 실전 봇의 판정 함수(`evaluate_entry`)를 **그대로 import** — 판정 로직 재구현 금지(보는 것 = 실전 봇 판정 보장).
- 국면(등가중 지수) 게이트는 **끈다**. 단 실전 봇이었다면 어땠을지 **참고 한 줄**로만 표시.
- 매수 판정만 관찰. 주문·잔고조회·청산감시·KILL·상태저장은 **없다**.
- 범위 밖: 실주문/모의주문, 청산·손절·익절 추적, 실전 봇 config 변경, KIS 모의투자(VTS) 연동.

## 사용자 확정 결정

- **관찰 수준** = 매 사이클 **후보별 판정 전부** 출력(매수 순간만이 아니라 거절 사유까지).
- **국면 무시** = **검증 전용 스위치**(이 관찰기에서만 국면 게이트 off). 실전 봇 `config.CFG`는 그대로 두어 실전은 여전히 국면 게이트 켜진 채 안전.
- **접근** = A안: 실전 `runner.py`를 안 건드리는 **별도 관찰 스크립트**.

## 접근 비교(채택 근거)

- **A(채택): 별도 관찰 스크립트** — 핵심 판정은 `evaluate_entry` 재사용이라 충실도 보장, 관찰 목적 출력을 깨끗이 설계, 프로덕션 봇 위험 0.
- B: `runner.py`에 `--no-regime --verbose` 플래그 — 러너의 잔고/청산/실주문 경로가 잡음, 검증 관심사를 프로덕션 핫패스에 주입. 기각.
- C: 리플레이(replay.py) 라이브화 — 리플레이는 과거일 분봉 재생용, 실시간 시세와 구조 불일치. 기각.

## 구성

### 신규 파일
- `scripts/autobuy/verify_volume.py`
  - **순수 조립 핵심** `observe_sweep(...)` — 한 사이클치 후보 판정을 이벤트/표시행 리스트로 산출(합성 입력 테스트 가능).
  - **라이브 오케스트레이터** `run(...)` — 감시목록 로드 → 반복 스윕(실시간 KIS 조회) → 출력.
  - **CLI** `main()` — `--once`, `--slots`, `--interval`.

### 재사용(실전 봇 그대로)
- `autobuy.signals.evaluate_entry` — **매수 판정의 전부**(돌파·추격+3%·거래량 pace≥1.5·슬롯·미보유).
- `autobuy.signals.is_uptrend` — 국면 **표시**용(게이트 아님).
- `autobuy.watchlist.load_actionable` — `sepa-*-candidates.json`에서 actionable+pivot 후보 로드.
- `autobuy.watchlist.build_ew_index` — 국면 참고 표시용 등가중 지수.
- `autobuy.config.CFG` — SLOTS·VOL_PACE_MIN(1.5)·CHASE_MAX_PCT(3.0)·MARKET_OPEN·NEW_BUY_UNTIL·MARKET_CLOSE·POLL_SEC.
- `canslim_lib.kis_api.fetch_quote_with_volume` — 현재가 + 당일 누적거래량.
- `canslim_lib.ohlcv_matrix.get_series` — avg50 거래량(최근 50일 평균).

## 데이터 흐름 (한 사이클)

1. 감시 후보 전체를 KIS로 조회 → `{current, acml_vol}`. 초당 ~8회 스로틀 → 후보 N개면 한 스윕 ≈ N/8초(150개면 ~19초, 실전 봇과 동일 속도).
2. 각 후보: `elapsed_frac`(09:00 기준 경과비율, 실전 `runner._elapsed_frac`과 동일식) 계산 → `evaluate_entry(current, pivot, acml_vol, avg50, elapsed_frac, slots_used=len(held_sim), slots_max, held=<이미 시뮬보유?>, vol_pace_min, chase_max_pct)` 호출 → `(ok, why)`.
3. `why=="extended"`면 그날 영구 스킵 집합에 추가(실전 봇과 동일).
4. `ok`인 후보들을 pace 높은 순 정렬, 슬롯 남는 만큼 시뮬 보유(`held_sim`)에 편입 → `★매수` 이벤트. 같은 종목은 하루 한 번만(재매수 방지, 실전 `traded_today`와 동일).
5. 후보별 표시행 + 이번 사이클 매수 이벤트를 반환.

### avg50 / elapsed_frac / pace
- avg50 = `ohlcv_matrix.get_series(code)`의 마지막 50개 volume 평균. 캐시는 전 영업일까지 → 실전 봇과 동일 입력.
- pace = `acml_vol / (avg50 * elapsed_frac)` — **표시용만**. 실제 임계 비교(≥1.5)는 `evaluate_entry` 내부에서 수행(중복 판정 안 함).

## 출력 형태

매 사이클 **블록 새로고침**:
```
=== 14:03:20 (장 경과 77%) · 슬롯 2/10 · 감시 34종목 ===
[국면 참고: 하락추세(지수<20MA) — 실전 봇이면 오늘 매매 OFF였음]
★매수 발생(2): 000660 SK하이닉스 @183500 pace2.1 · 042700 한미반도체 @...
--- 후보별 판정 ---
000660 SK하이닉스   183500 / 182000  +0.8%  pace2.1  ▷ already_held
112040 위메이드     41500 / 40000   +3.7%  pace1.8  ✗ extended
006400 삼성SDI      39900 / 41000   -2.7%   pace1.1  ✗ below_pivot
051910 LG화학       310000 / 305000 +1.6%   pace1.1  ✗ low_volume
...
```
`evaluate_entry`는 사유를 하나만 반환한다(우선순위: already_held→no_slot→below_pivot→extended→no_baseline→low_volume). 피벗 미달이면 거래량 검사 전에 `below_pivot`으로 끝나므로 한 종목에 사유는 항상 한 개. pace는 표시용으로 항상 계산해 보여준다.
- `★매수` 순간은 파일 로그 `scripts/autobuy/_run/verify_volume_<YYYYMMDD>.log` 에도 append(장 후 복기).
- 국면은 게이트가 아니라 참고 한 줄. `is_uptrend`를 스캔·표시용으로만 호출.
- 매수창(`MARKET_OPEN`~`NEW_BUY_UNTIL`) 밖이면 판정은 계속 보여주되 `★매수`는 안 냄(실전 봇과 동일: 그 시간대엔 신규매수 안 함).

## CLI

```
python -X utf8 scripts/autobuy/verify_volume.py            # 실시간 반복 관찰(장중)
python -X utf8 scripts/autobuy/verify_volume.py --once      # 한 번만 스윕하고 종료
python -X utf8 scripts/autobuy/verify_volume.py --slots 20  # 슬롯 상한 조정
python -X utf8 scripts/autobuy/verify_volume.py --interval 10  # 스윕 사이 최소 대기(초)
```
- `MARKET_CLOSE` 지나면 자동 종료. `--once`면 한 스윕 후 종료.

## 안전

- **주문 코드 자체가 없다** — 이 파일은 `kis_trade`를 import하지 않음. dryrun/live 개념조차 없어 실주문 물리적으로 불가.
- 읽기 전용: KIS는 시세 조회(`fetch_quote_with_volume`)만, 잔고/주문 TR 미사용.
- 실전 봇 `config.CFG`·`runner.py`·상태파일 무변경 → 실전 봇 동작에 영향 0.

## 테스트

순수 조립 핵심 `observe_sweep(quotes_by_code, candidates, avg50_by_code, held_sim, skip, cfg, elapsed_frac)` → (표시행 리스트, 매수 이벤트 리스트, 갱신된 held_sim/skip)를 합성 입력으로 pytest:
1. 거래량 pace<1.5 → `low_volume` 표시·미매수.
2. 가격 > 피벗×1.03 → `extended` 표시·skip 편입·미매수.
3. 돌파+pace≥1.5+슬롯여유 → `buy`·held_sim 편입.
4. 매수 신호 슬롯 초과 → pace 높은 순으로만 편입, 나머지 `no_slot`.
5. 이미 held_sim/skip/당일매수 종목 → 재판정 스킵.

실제 판정은 검증된 `evaluate_entry` 재사용이라 얇게. KIS 실호출은 소규모 스모크(`--once`)로 오케스트레이터만 확인.

## 전제 / 한계

- **전제**: 감시목록이 `sepa-*-candidates.json`(피벗)이라, 신선한 검증엔 그날 `/sepa`로 후보를 먼저 갱신하는 게 좋음(안 해도 기존 후보로 동작).
- **의미 있는 시간대**: 09:00~15:30 장중. 장외엔 누적거래량이 안 늘어 pace가 갱신 안 됨.
- **분해능**: 실시간이나 사이클 단위(한 스윕 ≈ N/8초). 초 단위 틱은 못 봄.
- dryrun 성격 — 실제 체결·슬리피지·부분체결 없음. 청산(손절/익절)은 이 도구 범위 밖(매수 판정 검증 전용).
- `_elapsed_frac`·pace 표시식이 `runner.py`와 문자 중복(변경 시 드리프트 위험) — 기존 replay.py도 동일 상황. 판정 자체는 `evaluate_entry` 재사용이라 충실도엔 영향 없음.

## 산출물

- `scripts/autobuy/verify_volume.py` + pytest.
- 콘솔 실시간 블록 + `_run/verify_volume_<날짜>.log`.

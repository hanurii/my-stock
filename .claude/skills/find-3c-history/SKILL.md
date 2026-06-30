---
name: find-3c-history
description: >
  3C(Cup-Completion Cheat) 검출기 회고·검증 도구(find-vcp-history 형제). find-3c
  후보 종목의 과거 1년을 매 거래일 as-of 로 되짚어, 기존 evaluate_cheat 가 짚어낸
  "3C→돌파" 이벤트·돌파 후 결과·종목 분류(extended/recent_breakout/re_basing/
  no_3c_found)를 sepa-3c-history.json 에 산출한다. 집계 수익률은 생존자 편향 경고와
  함께 참고용. 사용자가 "/find-3c-history", "3c 검증", "과거에 3c 했었나",
  "이 종목 3c 했었나" 등을 요청할 때 사용.
---

# find-3c-history — 3C 검출기 회고·검증

`find-3c` 후보 종목의 과거를 매 거래일 as-of 로 되짚어, 우리 검출기가 그 역사 속
"3C(컵 완성 치트) → 돌파" 시점을 짚어내는지 보여준다. 새 판정 로직 없이 **기존
`evaluate_cheat`(v2b) 재사용**. 정의: `docs/superpowers/specs/2026-06-30-find-3c-history-design.md`.

## 사전 조건
- **최신 데이터로 돌리려면 먼저 `update-data` → `find-trend-template` → `find-3c`** 실행.
- 입력 `public/data/sepa-3c-candidates.json` 존재(= find-3c 산출).

## 실행 (1줄)
```
python scripts/screen_3c_history.py
```
- 산출: `public/data/sepa-3c-history.json`
- 콘솔: 종목별 분류·최근 이벤트 표 + 집계 + 생존자 편향 딱지.

### 옵션
- `--ticker CODE` : 단일 종목 디버그(저장 안 함).
- `--codes 005930,000660` : 임의 종목.
- `--scan-days 250` : 과거 며칠을 되짚을지(거래일).
- `--confirm-lookback 5` : 돌파 직전 며칠 안에 3C 확인이 있어야 이벤트로 볼지.
- `--recent-days 10` : 최근 돌파 분류 경계.
- `--stop-pct 8` / `--target-pct 20` : good_breakout 경로 판정 손절·목표.
- 3C 임계값(`--min-shelf-days`·`--max-shelf-position`·`--min-cup-days` 등)도 노출 —
  find-3c 와 동일 검출기.

## 결과 확인
- `classification` : `re_basing`(돌파 후 2차 치트) · `recent_breakout`(최근 돌파) ·
  `extended`(예전 돌파·연장) · `no_3c_found`(이벤트 없음).
- 각 이벤트는 `date`·`confirm_date`·`pivot_price`·`cup_depth_pct`·`shelf_position_pct`·
  돌파 후 결과(gain/max_gain/drawdown/good_breakout)를 근거로 가진다.
- **결정적 검증은 이벤트 날짜를 차트로 직접 눈 대조하는 것.** 집계 수익률은
  RS 상위 승자만 본 결과라 **생존자 편향으로 과대평가**됨(보조 지표).

## 안 하는 것
- 임계값 자동 튜닝 · 실거래 신호 · 공유 파일 갱신 · 자동 commit · 캐시 광역 스캔
  (기본은 find-3c 후보 종목만). find-3c 와 **동일한 검출기**를 써야 검증 의미가 있다.

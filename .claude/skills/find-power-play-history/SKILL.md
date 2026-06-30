---
name: find-power-play-history
description: >
  파워 플레이 검출기 회고·검증 도구(find-vcp-history 형제). find-power-play 후보 종목의
  과거 1년을 매 거래일 as-of 로 되짚어, 기존 evaluate_power_play 가 짚어낸 "파워 플레이
  →돌파" 이벤트·돌파 후 결과·종목 분류(extended/recent_breakout/re_basing/
  no_power_play_found)를 sepa-power-play-history.json 에 산출한다. 집계 수익률은 생존자
  편향 경고와 함께 참고용. 사용자가 "/find-power-play-history", "파워플레이 검증",
  "과거에 이미 돌파했나", "이 종목 파워플레이 했었나" 등을 요청할 때 사용.
---

# find-power-play-history — 파워 플레이 검출기 회고·검증

`find-power-play` 후보 종목이 과거에 정말 파워 플레이→돌파를 거쳤는지 **기존
검출기를 과거에 그대로 적용**해 짚어낸다. 1순위 용도 = 검출기 검증(이벤트
날짜를 차트로 눈 대조). 정의: `docs/superpowers/specs/2026-06-30-find-power-play-history-design.md`.

## 사전 조건
- 먼저 `update-data` → `find-trend-template` → `find-power-play` 를 돌려 입력
  `public/data/sepa-power-play-candidates.json` 이 있어야 한다.

## 실행
```
python scripts/screen_power_play_history.py
```
- 산출: `public/data/sepa-power-play-history.json`
- 콘솔: 종목별 분류·최근 돌파 이벤트 + 집계(⚠️ 생존자 편향 경고).

### 옵션
- `--ticker 095610` : 단일 종목(저장 안 함).
- `--codes 005930,000660` : 임의 종목만(미지정 시 전체 후보).
- `--scan-days 250` `--confirm-lookback 5` `--recent-days 10` `--stop-pct 8` `--target-pct 20`
- 파워플레이 임계값(`--min-flagpole-gain` 등)은 find-power-play 와 동일(같은 검출기를 써야 검증 의미).

## 결과 보는 법
- `classification`: extended(이미 돌파·연장=추격 늦음) / recent_breakout(최근 돌파) /
  re_basing(돌파 후 2차 베이스) / no_power_play_found(검출 0=미스 의심 또는 패턴 없음).
- `events[].date` 를 차트로 열어 "진짜 파워 플레이 돌파였나" 눈으로 확인 = 진짜 검증.
- `events[].confirm_date`·`flagpole_gain_pct`·`flag_depth_pct` = 돌파 근거.
- 집계 수익률은 **생존자 편향으로 과대** — 보조 지표로만.

## 안 하는 것
- 새 판정 로직(기존 evaluate_power_play 재사용) · 임계값 자동 튜닝 · 실거래 신호 ·
  공유 파일 갱신 · 자동 commit.

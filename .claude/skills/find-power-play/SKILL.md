---
name: find-power-play
description: >
  SEPA 패턴 스킬(find-vcp 형제). 1단계(find-trend-template) 통과 종목의 일봉에서
  미너비니 파워 플레이(Power Play = High Tight Flag)를 탐지한다 — 8주 내 100%↑
  대량거래 폭등(깃대) + 얕고 좁은 횡보(깃발) + 돌파 전 거래량 마름. 피벗·진입상태
  (breakout/actionable/forming/failed)를 산출해 sepa-power-play-candidates.json
  에 저장한다. OHLCV 캐시만 사용, 수급·공유 파일 무접촉. 사용자가 "/find-power-play",
  "파워 플레이 찾아줘", "하이 타이트 플래그", "깃발 패턴" 등을 요청할 때 사용.
---

# find-power-play — SEPA 패턴: 파워 플레이(High Tight Flag)

`find-trend-template`(SEPA 1단계) 통과 종목에 대해 미너비니 **파워 플레이**(폭발적 깃대 +
얕은 깃발 + 돌파)를 탐지한다. find-vcp 의 형제 스킬(같은 입력, 다른 패턴).
정의·근거: `docs/superpowers/specs/2026-06-29-find-power-play-design.md`.

## 사전 조건
- **최신 데이터로 돌리려면 먼저 `update-data` → `find-trend-template`** 실행.
- 입력 `public/data/sepa-trend-candidates.json` 존재(= find-trend-template 산출).

## 실행 (1줄)
```
python scripts/screen_power_play.py
```
- 산출: `public/data/sepa-power-play-candidates.json`
- 콘솔: 상태 분포 + entry_ready 종목 표(깃대 상승률·기간, 깃발 깊이·길이, 피벗).

### 옵션
- `--ticker CODE` : 단일 종목 디버그(저장 안 함).
- `--min-flagpole-gain 100` / `--max-flagpole-days 40` : 깃대(8주 내 100%↑) 튜닝.
- `--pole-vol-mult 1.5` / `--max-pre-pole-gain 30` : 대량거래·조용한 출발 튜닝.
- `--min-flag-days 8` / `--max-flag-days 30` / `--max-flag-depth 20` : 깃발 튜닝
  (저가주는 `--max-flag-depth 25`).
- `--min-flag-pullback 3` : 깃발 최소 눌림폭(%) — 깃발 천장 대비 최소 되돌림.
- `--out PATH` : 출력 경로 변경.

## 결과 확인
- `pattern_count` : 파워 플레이 6조건 성립 종목 수(100% 깃대라 희귀한 게 정상).
- `status_distribution` : breakout(돌파) · actionable(피벗 근접+거래량 마름) ·
  forming(형성 중) · failed(깃발 붕괴).
- `entry_ready` 종목이 다음 단계(리스크·진입) 후보.
- 불성립 종목도 `reason`과 함께 전부 포함(환각 방지·디버그).

## 안 하는 것
- VCP 베이스 탐지(그건 find-vcp) · 전 종목 스캔(트렌드 통과 종목만) ·
  공유 파일 갱신 · 수급 신호 · 자동 commit.
- 타이트(tightness)는 합격 게이트가 아님 — 보고용 지표(책: 조정 ≤10%면 이미
  타이트). 핵심 게이트는 깃대(100%/8주·대량거래·조용) + 깃발(6주↓·≤20%·거래량 마름).

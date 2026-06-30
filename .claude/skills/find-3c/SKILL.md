---
name: find-3c
description: >
  SEPA 패턴 스킬(find-vcp·find-power-play 형제). 1단계(find-trend-template) 통과
  종목의 일봉에서 미너비니 3C(Cup-Completion Cheat = 컵 완성 치트)를 탐지한다 —
  하락→바닥→반등 도중 컵 하단/중단에 생긴 좁은 선반을, 옛 고점 한참 아래에서
  거래량과 함께 돌파하는 조기 매수점. 컵 깊이·선반 위치·피벗·진입상태
  (breakout/actionable/forming/failed)를 산출해 sepa-3c-candidates.json 에
  저장한다. OHLCV 캐시만 사용, 수급·공유 파일 무접촉. 사용자가 "/find-3c",
  "3c 찾아줘", "컵 치트", "Cup-Completion Cheat" 등을 요청할 때 사용.
---

# find-3c — SEPA 패턴: 3C(Cup-Completion Cheat)

`find-trend-template`(SEPA 1단계) 통과 종목에 대해 미너비니 **3C(컵 완성 치트)**
를 탐지한다. find-vcp·find-power-play 의 형제 스킬(같은 입력, 다른 패턴).
정의·근거: `docs/superpowers/specs/2026-06-30-find-3c-design.md`.

## 사전 조건
- **최신 데이터로 돌리려면 먼저 `update-data` → `find-trend-template`** 실행.
- 입력 `public/data/sepa-trend-candidates.json` 존재(= find-trend-template 산출).

## 실행 (1줄)
```
python scripts/screen_3c.py
```
- 산출: `public/data/sepa-3c-candidates.json`
- 콘솔: 상태 분포 + entry_ready 종목 표(컵 깊이·기간, 선반 깊이·위치, 피벗).

### 옵션
- `--ticker CODE` : 단일 종목 디버그(저장 안 함).
- `--min-cup-depth 12` / `--max-cup-depth 50` : 컵 깊이 밴드(%).
- `--min-cup-days 35` : 컵 최소 베이스 기간(거래일, 7주).
- `--min-shelf-pullback 3` : 선반 피벗 확인용 최소 눌림(%).
- `--min-shelf-days 5` / `--max-shelf-days 25` : 선반 길이(거래일).
- `--max-shelf-depth 12` : 선반 최대 조정폭(%) — 타이트.
- `--max-shelf-position 66` : 선반이 컵 깊이의 몇 % 높이까지 허용(하단/중단=66,
  low cheat만=33).
- `--breakout-vol-mult 1.4` / `--near-pivot-pct 5` : 돌파/근접 판정 임계값.
- `--lookback-days 250` : 탐색 되돌아보는 기간(거래일).
- `--out PATH` : 출력 경로 변경.

## 결과 확인
- `pattern_count` : 3C 게이트 성립 종목 수.
- `status_distribution` : breakout(돌파) · actionable(피벗 근접+거래량 마름) ·
  forming(형성 중) · failed(선반 붕괴).
- `entry_ready` 종목이 다음 단계(리스크·진입) 후보.
- 불성립 종목도 `reason`과 함께 전부 포함(환각 방지·디버그).
- `status` 는 패턴 성립 여부와 무관하게 가격 위치(돌파/근접/형성/붕괴)로
  결정된다. 따라서 `pattern_detected=false` 인 종목도 breakout/actionable 로
  표시될 수 있으며, '살 자리(entry_ready)' 는 패턴까지 성립한 종목에만 부여된다
  (요약의 breakout·actionable 개수 ≠ entry_ready).

## 현재 한계 (v2a)
- 앵커링은 **v2a("왼쪽 테두리=옛 peak=lookback 최고가" 먼저)** 로 수정되어
  `shelf_position_pct ≤ 100%` 가 구조적으로 보장되고, 신고가 종목은
  `no_overhead_cup` 으로 정직하게 걸러진다. v1의 >100% 쓰레기 값은 사라졌다
  (정의: `docs/superpowers/specs/2026-06-30-find-3c-v2-anchoring-design.md`).
- 다만 게이트(컵 깊이 12~50%/35거래일, 선반 위치 ≤66% 등)는 아직 strict 라
  트렌드 통과 종목 중 3C 후보가 매우 적다. **2026-06-30 70종목 풀런: `pattern_count=0`**
  (주된 거절: `cup_too_short` 35·`no_overhead_cup` 19 — 입력이 신고가 부근이라 옛
  peak가 최근 → 컵이 짧거나 없음 / `shelf_too_loose`·`shelf_too_short`·
  `volume_not_drying` 등 ~16종목은 컵은 성립, 선반·거래량에서 탈락).
- **책 3C 예시로 게이트를 보정하는 작업이 후속(Phase 2)** 이다
  (v2a spec §8). 즉 현 v2a의 가치는 "산출 정상화"이며, "충분히 잡는" 검출기로
  만드는 건 다음 단계다.

## 안 하는 것
- VCP 베이스 탐지(find-vcp) · 파워 플레이(find-power-play) · 전 종목 스캔(트렌드
  통과 종목만) · 공유 파일 갱신 · 수급 신호 · 자동 commit.
- 치트의 핵심(옛 고점 한참 아래 조기 진입)은 **선반 위치 게이트**(컵 하단/중단,
  ≤66%)로 구현된다 — 선반이 컵 윗부분이면 일반 컵앤핸들이지 치트가 아니다.

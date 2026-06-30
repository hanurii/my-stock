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

## 현재 한계 / 적용 범위 (v2b)
- 앵커링(v2a)은 "왼쪽 테두리=옛 peak 먼저"라 `shelf_position_pct ≤ 100%` 보장,
  신고가 종목은 `no_overhead_cup` 으로 정직하게 걸러진다.
- 게이트는 미너비니 책 3C 예시 **NU·GOOG·CRUS** 실데이터로 보정됨
  (`min_shelf_days` 2·`max_shelf_position` 90·`min_cup_days` 25). 셋 다 컵·치트
  피벗을 정확히 짚으며 NU·GOOG는 패턴 성립으로 검증(`tests/test_cheat_oracle.py`).
  근거: `docs/superpowers/specs/2026-06-30-find-3c-v2b-gate-tuning-design.md`.
- **현재 한국 트렌드 통과 라이브 = `pattern_count` 0(또는 극소수).** 버그가 아니라
  **입력 집단 특성**이다: 트렌드 통과 종목은 *조정 없이 오른 신고가 부근 모멘텀
  리더*라, "옛 고점에서 조정 후 회복 중"인 3C와 구조적으로 반대다(대부분
  `no_overhead_cup`·`cup_too_short`).
- **한국 3C는 과거 조정·상승장 초입 종목에 있으며**, 이를 발굴하는 건
  `find-3c-history`(과거 매 거래일 as-of 회고, 후속)의 몫이다.

## 안 하는 것
- VCP 베이스 탐지(find-vcp) · 파워 플레이(find-power-play) · 전 종목 스캔(트렌드
  통과 종목만) · 공유 파일 갱신 · 수급 신호 · 자동 commit.
- 치트의 핵심(옛 고점 한참 아래 조기 진입)은 **선반 위치 게이트**(컵 하단/중단,
  ≤66%)로 구현된다 — 선반이 컵 윗부분이면 일반 컵앤핸들이지 치트가 아니다.

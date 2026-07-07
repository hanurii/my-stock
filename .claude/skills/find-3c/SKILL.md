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

## 다음 단계 (티어 추이 스냅샷)
- 티어 추이 스냅샷(`public/data/sepa-tier-history.json`, 최근 3일)은 이제 **`/sepa`
  오케스트레이터가 마지막 스텝으로 소유**한다(모든 형제 패턴이 끝난 뒤 1회 실행 →
  '추이' 컬럼 마지막 점이 본문 티어와 항상 일치, 병렬 경합 없음). find-3c 안에서
  자체적으로 스냅샷을 찍지 않는다(병렬 실행 중 다른 형제 파일 쓰기와 경합·낡은
  스냅샷 방지).
  → `/stocks/sepa` 페이지의 각 패턴 테이블 '추이' 컬럼(어제→오늘 티어, 🆕 신규)이 이 파일로 계산된다.
- **find-3c 를 단독 실행**해 추이까지 갱신하려면(오케스트레이터 없이) 형제 패턴
  파일이 최신인 상태에서 **`python scripts/snapshot_sepa.py`** 를 직접 실행한다.
  후보 파일의 `status`를 그대로 복사(재분류 없음)하므로, 어느 패턴이든 재생성한
  직후 이 명령을 돌리면 그 asof 스냅샷이 현재 상태로 덮어써진다.
- `status` 는 패턴 성립 여부와 무관하게 가격 위치(돌파/근접/형성/붕괴)로
  결정된다. 따라서 `pattern_detected=false` 인 종목도 breakout/actionable 로
  표시될 수 있으며, '살 자리(entry_ready)' 는 패턴까지 성립한 종목에만 부여된다
  (요약의 breakout·actionable 개수 ≠ entry_ready).

## 현재 한계 / 적용 범위 (v2c)
- 앵커링(v2a)은 "왼쪽 테두리=옛 peak 먼저"라 `shelf_position_pct ≤ 100%` 보장,
  신고가 종목은 `no_overhead_cup` 으로 정직하게 걸러진다.
- 게이트는 미너비니 책 3C 예시 **8종(NU·GOOG·JBLU·AAPL·CRUS·브이엠·두산)** 실데이터로
  보정됨 — 핵심값 `min_shelf_days` 2·`max_shelf_position` 90·**`min_cup_days` 17**·
  **`min_shelf_position` 25**. 8종 모두 컵·치트 피벗을 정확히 짚으며 NU·GOOG·JBLU·
  AAPL·브이엠·두산은 패턴 성립으로 검증(`tests/test_cheat_oracle.py`). 근거:
  `docs/superpowers/specs/2026-06-30-find-3c-v2c-gate-refinement-design.md`.
- **`min_shelf_position`(25)** 게이트는 바닥 직후 V자 반등(선반 위치<25%)을
  치트로 오인하는 걸 막는다(`shelf_too_low_in_cup`).
- **의도적 미검출:** 진양폴리류(선반 깊이 ~20%로 느슨 + 위치 ~98%로 거의 핸들)는
  "타이트한 치트 선반" 기준 밖이라 잡지 않는다(품질 우선).
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

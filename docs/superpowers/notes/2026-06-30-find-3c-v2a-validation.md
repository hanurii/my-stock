# find-3c v2a 앵커링 — 라이브·실예시 검증 노트 (2026-06-30)

Phase 1(최근 컵 앵커링) 구현 후 라이브 풀런 검증. 계획:
`docs/superpowers/plans/2026-06-30-find-3c-v2-anchoring.md`.

## 1. 라이브 풀런 (입력 70종목, sepa-trend-candidates.json all_pass)

```
[3C 요약] 입력 70종목 | 패턴 0 | 진입가능 0 |
          breakout 4 · actionable 7 · forming 33 · failed 26
```

v1 대비 분포가 건강해졌다(v1: failed 66 / 대부분 붕괴). 위치 지표가 정상화되며
forming·actionable이 다수로 돌아옴.

## 2. 산출 정상화 불변식 (성공 기준)

- **`shelf_position_pct > 100` : 0건** (v1은 사실상 전 종목 >100, 관측 271·1428·2577%).
  최대 위치 = **98.9%** (≤100 구조적 보장 확인).
- 입력 70 == 출력 candidates 70 (누락 없음).
- 모든 비패턴 행에 `reason` 존재.

→ **v2a는 산출을 정상화했다(성공 기준 충족).** `shelf_position`이 의미 있는 값이
되고 분포가 쓰레기가 아니다.

## 3. reason 분포 (왜 아직 패턴 0인가)

```
cup_too_short      35   ← 옛 peak가 최근(베이스<35d). 트렌드 통과=신고가 부근 다수
no_overhead_cup    19   ← 신고가/무조정(옛 peak 아래 회복 구조 없음) — 정직한 거절
shelf_too_loose     7   ┐
shelf_too_short     5   ├ 컵(깊이+기간) 통과, 선반/거래량에서 막힘
volume_not_drying   2   │  = "진짜 치트에 가장 근접" 후보군(~16종목)
cup_too_deep        2   ┘
```

- **패턴 0은 앵커링 문제가 아니라 strict 게이트** 때문이다(계획대로). 두 갈래:
  1. `cup_too_short`(35)·`no_overhead_cup`(19) = 트렌드 통과 종목이 신고가 부근이라
     옛 peak가 최근 → 컵이 짧거나 없음. **입력 집단 특성**(Phase 2에서 입력 재고 또는
     min_cup_days 재검토 대상).
  2. `shelf_too_*`·`volume_not_drying`·`cup_too_deep`(~16) = 컵은 잡혔는데 선반/거래량
     게이트에서 탈락. **게이트 soft화 후보**(Phase 2 책 오라클 대조 핵심 대상).

## 4. 실예시 spot-check — 012510 (대동전자)

캐시(최근 ~1.5년)에서 "최근 조정형" 1종목으로 v2a 앵커 현실 동작 확인:

```
left_rim_date : 2026-06-01   (옛 peak)
cup_low_date  : 2026-06-11   (바닥)
shelf_high_date: 2026-06-12  (선반 고점=피벗)
cup_depth_pct : 23.72        cup_base_days: 19
shelf_position_pct: 4.05     shelf_depth_pct: 1.08   shelf_length_days: 11
pivot_price   : 120503       pct_to_pivot: 0.42      volume_dryup_ratio: 0.123
status: actionable           reason: cup_too_short   pattern_detected: False
```

- **시간순 정합:** `left_rim(06-01) ≤ cup_low(06-11) ≤ shelf_high(06-12)` ✓.
- 앵커가 "옛 고점 → 하락(23.7%) → 회복 선반(위치 4%·타이트 1%)"을 정상적으로 짚는다.
- 단 cup_base_days=19 < 35 → `cup_too_short`. 정점이 너무 최근이라 "컵"이 ~3주짜리
  짧은 구조. min_cup_days=35의 strict 거절(Phase 2 검토 대상).

> 더 오래된 책 예시(과거 데이터)는 캐시에 없어 Phase 2에서 FDR로 받아 as-of 검증.

## 5. 결론

- **v2a 앵커링 성공:** `shelf_position ≤ 100%` 보장, 분포 정상화, 기하 시간순 정합.
- **패턴 0은 strict 게이트의 결과**(앵커링 아님). 두 축으로 Phase 2에서 다룸:
  ① 입력 집단(신고가 다수) ↔ min_cup_days, ② 선반/거래량 게이트 soft화.
- Phase 2(책 오라클 대조)의 1차 검토 대상 = `shelf_too_*`/`volume_not_drying`/
  `cup_too_deep`로 떨어진 ~16종목(컵은 성립, 선반/거래량에서 탈락).

# find-3c v2a — 최근 컵 앵커링 재설계 (설계 spec)

작성일 2026-06-30 · 상태: 설계 승인됨(개념), 구현 계획 대기
선행: `2026-06-30-find-3c-design.md`(v1). 이 문서는 v1의 §4.2 앵커링만 교체한다.

## 0. 이 문서의 범위 (큰 그림 속 위치)

find-3c를 "실제로 동작하고 책 예시로 검증된" 검출기로 끌어올리는 **하이브리드
계획(C안)의 Phase 1**이다. 전체 단계:

- **Phase 1 (이 문서) — 최근 컵 앵커링 수정.** v1이 라이브 70종목에서 패턴 0개를
  내는 명백한 버그(앵커링)를 고쳐 산출을 정상화한다.
- **Phase 2 (별도 spec) — 오라클 검증 + 게이트 튜닝.** 책 3C 예시(사용자 제공
  1~2 + 직접 조사분)를 FDR 과거 데이터로 as-of 대조해 놓침·약점을 찾고 필요한
  게이트만 soft화(power-play 방법론).
- **Phase 3 (별도 spec) — find-3c-history 스킬.** `find-vcp-history` 미러.

이 문서는 **Phase 1만** 다룬다. 게이트 임계값 변경·history는 후속.

## 1. 문제 (v1이 왜 0개를 내는가)

v1 `find_cheat_shelf`는 **컵 바닥을 lookback 전체 최저점으로 먼저 앵커**했다.
입력이 트렌드 통과 종목(=52주 신고가 부근, 상승 추세)이라 그 최저점은 보통
오래전 52주 저점이고, "왼쪽 테두리"는 그 저점 *이전*의 고점이 된다. 종목은 이미
그 고점을 넘어 신고가를 만들었으므로 **선반 고점 > 왼쪽 테두리** →
`shelf_position_pct`가 100%를 크게 초과(2026-06-30 관측: 271%·1428%·2577%)하고
컵 회복 전제가 깨진다. 70종목 전부 불성립(`pattern_count=0`).

근본 원인: **앵커 순서가 거꾸로다.** 치트는 "옛 고점에서 떨어져 컵을 만들고 그
고점 *아래*에서 회복 중"인 구조다. 따라서 **옛 고점(peak)을 먼저 앵커**해야 한다.

## 2. 수정 (v2a 앵커링) — `find_cheat_shelf` 재정의

> 핵심 아이디어: **왼쪽 테두리 = 옛 peak(lookback 최고가)** 를 먼저 잡고, 그
> *이후*의 하락·회복에서 컵 바닥과 선반을 찾는다. 이러면 선반 고점이 옛 peak를
> 넘을 수 없어 `shelf_position ≤ 100%`가 **구조적으로 보장**된다.

`find_cheat_shelf(highs, lows, min_shelf_pullback) -> dict`:

1. **왼쪽 테두리(left_rim_high) = lookback 구간 최고 고가**(`argmax(highs)`).
   `left_rim_idx`, `left_rim_high`. (종목이 떨어지기 시작한 옛 peak.)
2. **컵 바닥(cup_low) = `left_rim_idx` *이후* 구간 `[left_rim_idx, n−1]` 의 최저
   저점**(`argmin(lows)`). `cup_low_idx`, `cup_low`. (peak에서 떨어진 바닥.)
3. **치트 선반 고점(shelf_high) = 피벗** = `cup_low` *이후*(회복, `[cup_low_idx+1,
   n−1]`)에서 **"뒤에 눌림이 확인된 가장 높은 고점"**.
   - 피벗 후보 = `i ∈ [cup_low_idx+1, n−2]` 중
     `min(이후 저가들) ≤ highs[i] × (1 − min_shelf_pullback/100)`. 후보 중 가장
     높은 고가가 `shelf_high`(돌파 봉 자신 제외 — v1과 동일 트릭). 후보 없으면
     회복 구간 최고 고가로 폴백(보통 선반 길이 게이트에서 걸러짐).
   - **`shelf_high ≤ left_rim_high` 가 1번 정의상 보장된다**(left_rim이 전체 최고).

→ 인덱스 순서 `left_rim_idx ≤ cup_low_idx < shelf_high_idx ≤ n−1` 보장.

### 2.1 퇴화(신고가) 처리 — 새 reason `no_overhead_cup`

- **`left_rim_idx ≥ n − 1 − min_shelf_days`** 이면(옛 peak가 너무 최근 = peak 뒤로
  컵+선반이 들어설 자리가 없음 = 사실상 신고가/조정 없음) → 컵이 없다고 보고
  **sentinel** 반환, `evaluate_cheat`가 `reason="no_overhead_cup"` 로 거절.
- 그 외 `cup_low_idx == n−1`(회복 구간 비어 있음) 등 퇴화도 `no_overhead_cup`.
- 이 게이트는 "트렌드 통과 종목 중 신고가라 옛 고점 아래 회복 구조가 없는" 다수를
  **정직하게** 걸러낸다(치트는 최근 조정 후 회복 중인 소수에서만 성립).

## 3. v1에서 그대로 유지하는 것 (변경 없음)

- **게이트·임계값**(컵 깊이 12~50%·기간 35d, 선반 길이 5~25d·깊이 12%·위치 66%,
  거래량 마름 ≤1.0) — Phase 1은 임계값을 **건드리지 않는다**. 게이트 튜닝은 Phase 2.
- **거래량 구간**(§v1 4.5): `rally_vol_avg = vols[cup_low_idx:shelf_high_idx+1]`
  평균(폴백 `vols[left_rim_idx:shelf_high_idx+1]`). `rally_vol_ratio`(보고용) =
  `rally_vol_avg / 왼쪽 하락 구간 vols[left_rim_idx:cup_low_idx+1] 평균`. 정의 동일.
- **피벗·상태·entry_ready**(§v1 4.6) 규칙 동일.
- **CLI 인자·출력 스키마**(§v1 5·6) 동일. `min_shelf_pullback` 등 모든 인자 유지.
- **불변 원칙**(공유 파일 무접촉·컷오프 금지·종목별 reason·자동 commit 안 함) 동일.

## 4. reason 목록 변경

기존 목록(§v1 5)에 **`no_overhead_cup` 추가**. 게이트 판정 순서(첫 불충족이
reason)에서 `no_overhead_cup`은 **컵 깊이 게이트보다 앞**(앵커 자체가 없으면 깊이
계산이 무의미)에 온다:

```
no_data → base_too_short → no_overhead_cup → cup_too_shallow → cup_too_deep →
cup_too_short → shelf_too_short → shelf_too_long → shelf_too_loose →
shelf_too_high_in_cup → volume_not_drying
```

구현상 `no_overhead_cup`은 `find_cheat_shelf`가 sentinel을 주는 경우
`evaluate_cheat` 진입부에서 곧장 거절(깊이/선반 계산 전).

## 5. 정합성 보장 (v2a의 핵심 성질)

- **`shelf_position_pct ≤ 100%` 구조적 보장** — left_rim이 전체 최고이므로 선반은
  그 위로 못 간다. v1의 >100% 쓰레기 값이 사라진다.
- 신고가 종목 → `no_overhead_cup`(정직한 거절). 최근 12~50% 조정 후 회복 중 +
  하단/중단 좁은 선반 종목만 후보.
- Phase 1 단독으로 `pattern_count`가 반드시 0보다 커진다고 **보장하지는 않는다**
  (게이트가 여전히 strict). 목표는 "산출을 정상화(위치 지표가 의미 있고, 분포가
  쓰레기 아님)"이며, 게이트가 너무 빡빡해 진짜 치트를 놓치면 그건 Phase 2에서
  오라클로 푼다. **Phase 1 성공 기준은 "0개"가 아니라 "정상 산출"이다.**

## 6. 검증 계획

### 6.1 단위 테스트(합성 시계열) — `tests/test_cheat.py` 갱신
v1 테스트는 v2a 앵커링에 맞게 **재작성**한다(앵커 순서가 바뀌므로 기존 합성
데이터의 기대 인덱스/지표가 달라짐). 커버:
1. 깔끔한 v2a 3C(옛 peak 100 → 30% 하락 바닥 70 → 회복 중 하단/중단 좁은 선반
   85) → `find_cheat_shelf`가 left_rim=100·cup_low=70·shelf=85, `shelf_position≈50%`,
   `pattern_detected=True`.
2. 신고가(최고가가 마지막 봉 부근) → `no_overhead_cup`.
3. 컵 얕음(<12%) → `cup_too_shallow`.
4. 컵 깊음(>50%) → `cup_too_deep`.
5. 베이스 짧음(<35d) → `cup_too_short`.
6. 선반 컵 상단(위치>66%) → `shelf_too_high_in_cup`.
7. 선반 느슨(>12%) → `shelf_too_loose`.
8. 피벗 돌파 + 대량거래 → `status=breakout`; 비패턴 돌파 → `entry_ready=False`.
9. **위치 ≤100% 불변식**: 무작위/실제형 시계열에서 `shelf_position_pct`가 항상
   ≤100(+부동소수 여유) 임을 단언하는 테스트 1개 추가.

### 6.2 라이브 재실행 (산출 정상화 확인)
`python scripts/screen_3c.py` → `sepa-3c-candidates.json` 재생성. 확인:
- 모든 성립/근접 종목의 `shelf_position_pct ≤ 100`.
- 상태 분포가 "전부 failed"가 아니라 합리적으로 퍼짐(no_overhead_cup·forming·
  cup_*·shelf_* 등). 패턴 개수는 0이어도 무방(Phase 2에서 판단).
- 입력 all_pass 수 == 출력 candidates 수(누락 없음), 모든 비패턴에 reason.

### 6.3 실제 사례 1개 대조 (오라클 맛보기)
- **첫 구현 task로, 대표 3C 사례 1개를 조사·FDR(`fdr.DataReader`)로 받아** as-of
  슬라이스에 `evaluate_cheat`를 돌려 left_rim·cup_low·선반·위치가 차트와 맞는지
  육안 대조. (전체 오라클 검증은 Phase 2.) 데이터 출처·방법은
  power-play 선례(메모리 [[price-financial-data-sources]]) 따름.

## 7. 영향 받는 파일

- `scripts/canslim_lib/cheat.py` — `find_cheat_shelf` 본문 교체(시그니처·반환 키
  동일), `evaluate_cheat` 진입부에 `no_overhead_cup` 분기 추가, `DEFAULT_PARAMS`
  변경 없음.
- `tests/test_cheat.py` — v2a 앵커링에 맞게 재작성 + 위치 불변식 테스트.
- `docs/superpowers/specs/2026-06-30-find-3c-design.md` — §4.2 앵커링을 v2a로
  갱신(또는 "v2a 문서로 대체됨" 포인터). 출력 스키마·게이트는 그대로라 §4.2와
  reason 목록(§5)만 손댄다(doc-logic sync).
- `.claude/skills/find-3c/SKILL.md` — "현재 한계(v1)" 노트를 v2a 반영해 갱신(앵커링
  수정으로 위치 지표 정상화; 게이트 튜닝은 후속).
- **`screen_3c.py` 변경 없음**(앵커링은 부품 내부; CLI·스키마 불변).

## 8. 미해결/후속 (Phase 2·3)

- **게이트 soft화(Phase 2):** v2a로도 진짜 치트를 놓치면(strict 깊이/기간/위치),
  책 오라클 대조로 어떤 게이트를 점수화/완화할지 결정. power-play 교훈(strict
  100%/8주가 틀렸듯, 여기 컵 12~50%/35d·위치 66%도 재검토 대상).
- **find-3c-history(Phase 3):** 과거 as-of 회고.
- **입력 집단 재고(후속):** 트렌드 통과 종목은 신고가 다수라 치트 후보가 적다.
  3C를 더 넓은 유니버스에서 찾을지는 Phase 2 결과 보고 판단.

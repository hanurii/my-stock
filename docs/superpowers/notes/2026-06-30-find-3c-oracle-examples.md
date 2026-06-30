# find-3c 오라클 — 대표 3C(Cup Completion Cheat) 사례 조사·검증 (2026-06-30)

Phase 2(오라클 검증 + 게이트 튜닝)의 ground truth. 책/자료에서 대표 3C 사례를
조사하고, 데이터로 검증 가능한 것을 우리 v2a 검출기에 대조한 기록.

## 0. 용어 확정
- **"3C" = "3-C" = Cup Completion Cheat** (복수 출처 일치). 미너비니
  『Trade Like a Stock Market Wizard』·『Think & Trade Like a Champion』의 치트 진입.
- 치트는 컵앤핸들의 핸들보다 **이른** 매수점. 컵을 3등분해 **low cheat(하단 1/3)·
  medium(중단)·high cheat(상단=거의 핸들)** 로 나눔. "low cheat = 하단 1/3~1/2".

## 1. 대표 사례

### ★ NU (Nu Holdings, NYSE) — 2023-10-18 (데이터 검증 완료)
복수 튜토리얼이 동일하게 인용하는 완전 명세 사례:
- 치트 범위(선반) ≈ **$7.69–8.02**, 매수 stop-buy **$8.03**(limit 8.08), 손절 **$7.67**(선반 저점 바로 아래).
- FDR 실데이터 확인: 10-16~18 좁은 횡보(고가 8.02/7.99/7.95), **10-19 $8.03 돌파**
  (종가 8.23) + **거래량 60.1M 폭발**(직전 ~20–30M). 교과서적 치트 돌파.
- **위치:** 컵 왼쪽테두리 ≈$8.29(07-13), 바닥 ≈$6.61(08-18), 선반 $8.02 →
  컵의 **약 84%**(상단). = 사실상 high/completion cheat(low cheat 아님).

### GOOGL (Alphabet) — IPO 직후 2004 (미검증, Phase 2 후보)
- IPO 후 15~20% 조정 → **low cheat(하단 1/3)** → "핸들 없이 바로 상승".
- 날짜 미상(2004 하반기). FDR로 2004 데이터 확인 필요.

### FRSH·COKE·NUE (setupfactory 차트 예시), MCK·RPRX·RSG (ChartMill)
- 차트만 제시·날짜/가격 미상. Phase 2에서 데이터로 시점 특정 필요(우선순위 낮음).

## 2. ★ v2a 검출기 × NU as-of 대조 (핵심 결과)

NU 데이터를 2023-10-18 이전으로 슬라이스해 `evaluate_cheat` 실행:

| as-of | status | reason | pivot | 비고 |
|---|---|---|---|---|
| 2023-10-18 | **actionable** | shelf_too_short | **8.02** | 피벗이 문서 $8.03과 일치 |
| 2023-10-19 | **breakout** | shelf_too_short | 8.02 | 돌파 정확 포착 |

- 앵커: left_rim 2023-07-13, cup_low 2023-08-18, shelf_high 2023-10-16,
  cup_depth **20.3%**, cup_base_days **68**, shelf_position **83.9%**,
  shelf_depth **4.2%**, shelf_length **2일**, dryup 0.90.
- **기하·피벗·상태 전이는 완벽**(피벗 $8.02 = 문서 $8.03, actionable→breakout 정확).
- **그러나 패턴 거절**: `shelf_too_short`(선반 2일 < `min_shelf_days`=5). 길이가
  통과했어도 `shelf_too_high_in_cup`(위치 83.9% > `max_shelf_position`=66)에 걸림.

## 3. 게이트에 주는 교훈 (Phase 2 핵심)

1. **`min_shelf_days=5` 가 너무 빡빡함 (명백).** 미너비니 치트의 "멈춤(pause)"은
   짧다 — NU는 2~3일. 진짜 치트를 이 게이트가 막는다. **하향(예: 2~3) 1순위 후보.**
2. **`max_shelf_position=66` = 정의 문제 (사용자 결정 필요).**
   - low cheat = 하단 1/3~1/2(≤50%). NU "completion cheat" = 84%(상단).
   - 사용자는 앞서 "하단/중단만(≤66%)"을 선택 → NU 같은 **상단/완성 치트는 의도적
     배제**. 즉 우리 게이트는 "low/medium cheat" 정의엔 정합적이고, NU는 "범위 밖"일
     수 있음.
   - **결정 필요:** (a) low/medium만(현 ≤66 유지, NU는 오라클에서 제외하고 진짜
     low cheat 예시로 검증) vs (b) 완성 치트까지 포함(≤66 완화/철폐).
3. 거래량 마름(dryup 0.90)·컵 깊이(20%)·기간(68d)·선반 깊이(4%)는 NU에서 전부
   합리적 — 이 게이트들은 잘 작동.

## 4. 결론·다음
- v2a 앵커링은 **실제 3C(NU)에서 컵·피벗을 정확히 짚는다**(앵커링 재설계 성공의
  실증). 막는 건 **선반 길이·위치 게이트**다.
- Phase 2 1순위: `min_shelf_days` 하향. 그 다음 `max_shelf_position` 은 사용자
  정의 결정(low/medium만 vs 완성치트 포함) 후 조정.
- 사용자 제공 책 예시 1~2개(특히 진짜 low cheat) + GOOGL/기타로 오라클 보강.

## 출처
- ChartMill — Mark Minervini's Cheat Entries (개요).
- financialtechwiz / setupfactory / IBD Live(lilys.ai) — NU·GOOGL·FRSH·COKE·NUE 언급.
- 데이터: FinanceDataReader `fdr.DataReader('NU', ...)`.

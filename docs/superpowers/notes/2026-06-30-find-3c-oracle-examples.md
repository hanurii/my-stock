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

### ★ GOOG (Alphabet) — 2004-11~12 (데이터 검증 완료, v2a가 검출 성공)
- FDR `GOOG`(2004 IPO~) 분할조정 데이터로 as-of 스윕. 우리 v2a 검출기가 **진짜
  3C를 pattern_detected=True 로 검출**:
  - 컵: left_rim 2004-11-03 → cup_low 2004-11-22 → shelf 2004-11-30,
    **cup_depth 19.99%**(="15~20% 조정" 내러티브 일치), **shelf_position 53.8%
    (low/middle cheat)**, shelf_depth 7.94%, shelf_len 17~20일, dryup 0.56→0.38.
  - 2004-12-23·12-29 **pattern_detected=True**(reason=None). status=forming인 건
    12-20경 이미 피벗(4.56)을 넘어 actionable/breakout 창을 지났기 때문.
- **의의:** v2a 앵커링·게이트가 **실제 low/middle cheat 를 정상 검출**함을 실증.
  NU(짧은 선반·상단)와 달리 GOOG는 긴 선반(17일)·하단중단이라 현 게이트로도 통과.
  → 검출기는 근본적으로 동작한다. 막히는 건 (a)짧은 선반(NU 2일<5) (b)상단 위치
  (NU 84%>66) (c)미성숙/신고가(cup_too_short·no_overhead_cup, 트렌드 입력 다수).

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
   - **사용자 결정(2026-06-30): (b) 완성 치트까지 포함.** → Phase 2에서
     `max_shelf_position` 을 ~90~95(또는 철폐)로 완화. v2a 앵커링상 선반은 항상 옛
     고점 아래(위치 <100%)라 "옛 고점 아래 조기 진입" 본질은 유지된다. NU(84%)가
     성립하도록 + `min_shelf_days` 도 2~3으로 하향. 단, 라이브 70종목에 거짓양성이
     쏟아지지 않는지 함께 확인(과완화 방지).
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

## 5. 오라클 8종 종합 (v2c 보정 근거, 2026-06-30)

미너비니 3C 책 예시를 저자 피벗 시점 as-of 로 대조. 검출기는 **거의 항상 컵·피벗을
정확히 짚으며**, 막던 건 게이트였다:

| 종목 | 저자 피벗 | 위치% | 컵깊이% | 컵기간 | v2b | v2c |
|---|---|---|---|---|---|---|
| NU | 2023-10-18 | 84 | 20 | 68 | ✅ | ✅ |
| GOOG | 2004-12-23 | 54 | 20 | 35 | ✅ | ✅ |
| JBLU | 2014-11-03 | 68 | 27 | ~50 | ✅ | ✅ |
| AAPL | 2004-08-12 | 90 | 16 | ~35 | ✅ | ✅ |
| CRUS | 2010-02-25 | 58 | 23 | 33 | ✅(borderline) | ✅ |
| 브이엠 089970 | 2021-03-19 | 49 | 17 | ~20 | ❌ cup_too_short | **✅** |
| 두산 000150 | 2021-07-02 | 34 | 20 | ~17 | ❌ cup_too_short | **✅** |
| 진양폴리 010640 | 2021-12-08 | 98 | 35 | 길음 | ❌ shelf_too_loose | ❌(의도적 미검출) |
| 휴마나 HUM | 1978-03 | — | — | — | 데이터 없음(FDR 1981~) | — |

**v2c 보정:** `min_cup_days` 25→17(브이엠·두산), 신규 `min_shelf_position`=25(V자 반등
거부). 결과: 오라클 7/8 통과(진양폴리만 의도적 보류), **라이브 pattern 0 유지**, history
위치<25 V자 이벤트 24→0. 진양폴리(느슨·완성 치트)는 별도 후속.

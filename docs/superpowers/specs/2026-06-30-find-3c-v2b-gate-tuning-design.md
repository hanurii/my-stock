# find-3c v2b — 오라클 기반 게이트 보정 + 검증 하니스 (설계 spec)

작성일 2026-06-30 · 상태: 설계 승인됨, 구현 계획 대기
선행: v1(`...-find-3c-design.md`), v2a 앵커링(`...-find-3c-v2-anchoring-design.md`).

## 0. 위치 (하이브리드 계획의 Phase 2)

- Phase 1(v2a): 앵커링 수정 → 산출 정상화(완료).
- **Phase 2(이 문서): 책 오라클로 게이트를 보정**하고, 그 보정을 **재현 가능한
  pytest 하니스**로 고정한다.
- Phase 3(별도): find-3c-history.

## 1. 오라클 (검증된 실제 3C 사례)

세 사례를 FDR 실데이터로 as-of 대조 검증함(상세: `docs/superpowers/notes/
2026-06-30-find-3c-oracle-examples.md`). v2a 검출기는 셋 다 **컵·피벗·치트 위치를
정확히 짚는다**(앵커링 성공). 막던 것은 게이트:

| 사례 | 치트일 | 유형 | 선반길이 | 위치 | 컵기간 | 피벗(=문서) | v2a 기본(5/66) |
|---|---|---|---|---|---|---|---|
| NU (NYSE) | 2023-10-18 | 완성/상단 | 2일 | 84% | 68d | $8.02(=$8.03) | shelf_too_short |
| GOOG | 2004-12-23 | low/middle | 17일 | 54% | 35d | 4.56 | ✅ pattern |
| CRUS | 2010-02-25~ | middle | 1~4일 | 62% | 33d | 7.41 | cup_too_short→volume |

## 2. 게이트 보정 (이 spec의 핵심 변경)

`canslim_lib/cheat.py` 의 `DEFAULT_PARAMS` 3개 값만 변경한다. 게이트 *로직*·앵커링·
출력 스키마·상태 규칙은 불변.

| 파라미터 | v2a | v2b | 근거 |
|---|---|---|---|
| `min_shelf_days` | 5 | **2** | 치트 "멈춤"은 짧다(NU 2일, CRUS 1~4일). |
| `max_shelf_position` | 66 | **90** | 완성 치트 포함(사용자 결정). NU 84%. v2a상 선반은 항상 옛 고점 아래(<100%)라 "옛 고점 아래 조기 진입" 본질 유지. |
| `min_cup_days` | 35 | **25** | 치트는 컵 *완성 전* 일찍 발동(CRUS 컵 33d). 오닐 7주는 완성 컵 기준. |

### 2.1 보정 후 오라클 결과(목표 — 실험으로 확인됨)
- **NU 2023-10-18 → `pattern_detected=True`, status=actionable**(피벗 8.02). 10-19 breakout.
- **GOOG 2004-12-23 → `pattern_detected=True`**(보정 전부터 통과, 회귀 없음 확인).
- **CRUS** → 컵(rim 2010-01-12·low 2010-02-05·depth ~23%)·피벗 7.41·치트일 actionable
  을 **정확히 위치**. 단 `pattern_detected` 는 borderline(선반 다중터치로 측정
  선반길이가 짧아지고 돌파일 거래량 확장으로 `volume_not_drying`). → §6 후속.

### 2.2 과완화 방지 (필수 불변식)
- 보정값(2/90/25)으로 **라이브 70종목(sepa-trend-candidates.json all_pass) 재실행 시
  `pattern_count` 가 폭증하지 않아야** 한다(실험값: 여전히 0 — 거짓양성 없음).
  근거: 한국 거절 주류는 `cup_too_short`/`no_overhead_cup`(컵 문제)라 선반·위치
  완화로 거의 변하지 않음. **구현 후 실측해 폭증(예: >10) 시 보정값 재검토.**

## 3. 오라클 검증 하니스 (재현 가능)

**문제:** FDR는 네트워크 의존이라 pytest에서 직접 호출하면 불안정(오프라인·차단).
**해결:** 오라클 3종의 FDR 데이터를 **고정 fixture(JSON)로 1회 덤프해 커밋**하고,
pytest는 그 fixture를 읽어 `evaluate_cheat` 를 as-of로 돌려 단언한다.

### 3.1 fixture 생성(1회용 스크립트, 산출물만 커밋)
- `scripts/_dump_oracle_fixtures.py`(개발 보조; 네트워크 사용) — `fdr.DataReader`
  로 아래를 받아 `tests/fixtures/oracle/{TICKER}.json` 으로 저장:
  - NU: 2023-01-01 ~ 2023-10-25
  - GOOG: 2004-08-19 ~ 2005-01-05
  - CRUS: 2009-06-01 ~ 2010-03-10
  - 형식: `{"ticker","rows":[{"date","open","high","low","close","volume"}, ...]}`.
- fixture JSON 은 커밋(테스트 재현용). 덤프 스크립트는 `_` 접두(임시 보조) 관례.

### 3.2 pytest 하니스 — `tests/test_cheat_oracle.py`
- 헬퍼 `load_asof(ticker, date) -> series_dict`(fixture에서 date 이하 슬라이스).
- 단언:
  - `test_oracle_nu_actionable_at_cheat`: NU as-of 2023-10-18 → `pattern_detected
    is True`, `status == "actionable"`, `7.8 <= pivot_price <= 8.2`.
  - `test_oracle_nu_breakout_next_day`: NU as-of 2023-10-19 → `status == "breakout"`.
  - `test_oracle_goog_pattern`: GOOG as-of 2004-12-23 → `pattern_detected is True`,
    `shelf_position_pct <= 66`(low/middle).
  - `test_oracle_crus_locates_cheat`: CRUS as-of 2010-02-25 → `left_rim_date ==
    "2010-01-12"`, `cup_low_date == "2010-02-05"`, `20 <= cup_depth_pct <= 27`,
    `7.2 <= pivot_price <= 7.6`, `status in ("actionable","forming","breakout")`.
    (= 치트를 정확히 위치. pattern_detected 는 단언하지 않음 — §6 후속.)

## 4. 영향 받는 기존 단위 테스트 (`tests/test_cheat.py`)

기본값이 바뀌므로 **기본값에 의존하던 거절 테스트의 합성 데이터를 새 임계값에
맞게 조정**한다(게이트 *로직*은 그대로라 데이터만 수정):
- `test_default_params_*`: `min_shelf_days==2`, `max_shelf_position==90`,
  `min_cup_days==25` 로 단언 갱신.
- `test_evaluate_rejects_shelf_too_high_in_cup`: 선반 위치를 **>90%** 로 만들어
  트립(기존 84%는 이제 통과). 또는 `max_shelf_position=66` 을 명시 param 으로 넘겨
  로직만 검증(권장: 명시 param 으로 디커플).
- `test_evaluate_rejects_short_cup_base`: 기대 reason 이 새 `min_cup_days=25` 기준
  (base<25)이 되도록 데이터/assert 조정.
- shelf 길이 의존 테스트(`shelf_too_short` 등): `min_shelf_days=2` 기준(선반<2)으로
  조정. `_clean_3c_v2` 가 여전히 `pattern_detected=True` 인지 확인.
- 위치 불변식 테스트(`shelf_position ≤ 100`)는 영향 없음.

> 원칙: 게이트 **로직** 테스트는 가능하면 **명시 param** 을 넘겨 기본값 변경과
> 독립시키고, 기본값 자체는 `test_default_params_*` 에서만 단언한다(향후 보정에
> 강건).

## 5. 정직한 문서화 (doc-logic sync)

- **v2b spec(이 문서)** + 검증 노트 갱신.
- `find-3c/SKILL.md` "현재 한계" 절: 게이트는 책 오라클(NU·GOOG·CRUS)로 보정됨,
  **현재 한국 트렌드 통과 라이브 = ~0(입력 집단 특성: 조정 없이 오른 모멘텀 리더
  엔 3C 부재)**, **한국 3C는 과거 조정·상승장 초입에 있으며 `find-3c-history`(Phase 3)
  가 되짚어 찾는다** 고 명시.
- v1·v2a spec 의 게이트 기본값 언급에 v2b 갱신 포인터.

## 6. 미해결/후속

- **선반 측정 정교화(CRUS strict miss):** 다중 터치 횡보에서 선반 천장이 최근
  동일고점으로 계속 리셋돼 측정 선반길이가 짧아지는 문제. 선반을 "최근 동일고점
  군집 전체"로 잡거나 dryup 기준 구간을 재정의하는 건 별도(이 spec 범위 밖).
- **입력 집단(Phase 3로 흡수):** 한국 3C는 라이브(신고가 리더)가 아니라 과거
  조정 종목에 있음 → find-3c-history 가 과거 as-of 회고로 발굴. 별도 spec.
- 임계값(2/90/25)은 3사례 기반 추정 — 사례 누적 시 재보정.

## 7. 불변 원칙 (기존 SEPA 스킬과 동일)
- 공유 파일 무접촉·컷오프 금지·종목별 reason·자동 commit 안 함.
- 콘솔 수치 그대로 보고, 추측 금지.

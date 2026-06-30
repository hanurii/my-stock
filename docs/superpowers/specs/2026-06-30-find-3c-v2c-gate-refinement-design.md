# find-3c v2c — 오라클 확장 기반 게이트 재보정 (설계 spec)

작성일 2026-06-30 · 상태: 설계 승인됨, 구현 계획 대기
선행: v2b 게이트 보정(`...-find-3c-v2b-gate-tuning-design.md`).

## 0. 위치
하이브리드 계획의 게이트 재보정 2차. v2b(NU·GOOG·CRUS 3종 오라클)에서 오라클을
**8종**으로 확장하며 드러난 두 가지 체계적 약점을 고친다.

## 1. 확장된 오라클 (데이터 검증)
미너비니 3C 책 예시를 FDR 실데이터로 as-of 대조(상세: `docs/superpowers/notes/
2026-06-30-find-3c-oracle-examples.md`). 저자 피벗 시점에서 우리 검출기가 컵·피벗을
정확히 짚는지 + 게이트 통과 여부:

| 종목 | 저자 피벗 | 위치% | 컵깊이% | 컵기간(거래일) | v2b | 막은 게이트 |
|---|---|---|---|---|---|---|
| NU | 2023-10-18 | 84 | 20 | 68 | ✅ | — |
| GOOG | 2004-12-23 | 54 | 20 | 35 | ✅ | — |
| JBLU | 2014-11-03 | 68 | 27 | ~50 | ✅ | — |
| AAPL | 2004-08-12 | 90 | 16 | ~35 | ✅ | — |
| CRUS | 2010-02-25 | 58 | 23 | 33 | ✅(borderline) | — |
| **브이엠** | 2021-03-19 | 49 | 17 | **~20** | ❌ | `cup_too_short` |
| **두산** | 2021-07-02 | 34 | 20 | **~17** | ❌ | `cup_too_short` |
| 진양폴리 | 2021-12-08 | 98 | 35 | 길음 | ❌ | `shelf_too_loose`(선반깊이20%) |

(휴마나 HUM 1978: 데이터 없음(FDR 1981~)으로 검증 불가, 개념 참고만.)

## 2. 두 가지 체계적 약점 → 보정

### 2.1 `min_cup_days` 25 → 17 (지배적 블로커)
치트는 컵 *완성 전* 일찍 발동한다. 최근 고점에서 ~17~20거래일밖에 안 된 짧은
컵에서 터지는 게 정상(브이엠 20·두산 17·CRUS 33). v2b의 25는 브이엠·두산 같은
진짜 치트를 막았다. **17로 낮추면 둘 다 통과하고, 라이브 70종목 `pattern_count`는
여전히 0(과완화 없음 — 실측 확인됨).**

### 2.2 신규 게이트 `min_shelf_position`(기본 25) — V자 반등 거부
v2a에서 NU(짧은 2일 선반)를 잡으려 `min_shelf_days`를 2로 낮춘 부작용으로,
**바닥 친 직후 1~2일 반등**을 치트 선반으로 오인하는 거짓양성이 생겼다(137080:
−36% 급락 후 위치 18%의 즉시 반등 → pattern_detected=True).
- 진짜 치트는 선반이 회복의 **중간 이상**에 있다(오라클 위치 34~98%, 137080만 18%).
- **게이트:** `shelf_position_pct ≥ min_shelf_position`(기본 25). 미만이면
  reason **`shelf_too_low_in_cup`**.
- **검증:** history 110이벤트 중 위치<25인 24건(바닥 반등)이 걸러지고, 진짜 치트
  (≥34%)는 전부 유지. 오라클 8종 모두 위치≥34라 영향 없음.

### 2.3 잡지 못하는 케이스 (의도적 보류)
- **진양폴리**: 선반 깊이 **20%**(느슨, 우리 타이트 기준 ≤12 밖) + 위치 98%(거의
  핸들). 잡으려면 `max_shelf_depth`(12→~20)·`max_shelf_position`(90→~99)을 크게
  풀어야 해 품질 저하·거짓양성 위험 → **보류·문서화**. v2c는 진양폴리를 잡지
  않는다(오라클 테스트에서 "거부됨"으로 단언해 정직하게 고정).

## 3. 변경 사항 (정확히)

### 3.1 `canslim_lib/cheat.py`
- `DEFAULT_PARAMS`: `min_cup_days` 25→**17**, 신규 `min_shelf_position`: **25.0** 추가.
- `evaluate_cheat` 게이트 체인에 `shelf_too_low_in_cup` 추가. 새 순서(첫 불충족이 reason):
  ```
  ... shelf_too_loose → shelf_too_low_in_cup → shelf_too_high_in_cup → volume_not_drying
  ```
  즉 선반 깊이(loose) 다음, 위치 하한(too_low) → 위치 상한(too_high) 순.
  구현: `cond_shelf_pos_lo = shelf_position >= p["min_shelf_position"]`,
  `cond_shelf_pos_hi = shelf_position <= p["max_shelf_position"]`(기존).
- 다른 게이트 로직·앵커링·상태·스키마 불변.

### 3.2 CLI 노출
- `screen_3c.py`·`screen_3c_history.py`에 `--min-shelf-position`(default
  DEFAULT_PARAMS) 추가, params dict에 포함. `min_cup_days` 기본은 자동 반영(17).

### 3.3 오라클 하니스 확장 (`tests/`)
- 신규 fixture(커밋): JBLU·AAPL·089970(브이엠)·000150(두산)·010640(진양폴리).
  덤프는 기존 `scripts/_dump_oracle_fixtures.py`에 항목 추가.
- `tests/test_cheat_oracle.py`에 단언 추가:
  - `JBLU @2014-11-03`, `AAPL @2004-08-12`, `브이엠 @2021-03-19`, `두산 @2021-07-02`
    → `pattern_detected is True` + 피벗 범위·위치 범위.
  - `진양폴리 @2021-12-08` → `pattern_detected is False`(알려진 미스, reason
    `shelf_too_loose`로 단언 — 정직 고정).
  - (137080은 캐시 종목이라 fixture 불필요; V자 거부는 단위 테스트로 §3.4.)

### 3.4 단위 테스트 (`tests/test_cheat.py`)
- `test_default_params_*`: `min_cup_days==17`, `min_shelf_position==25.0` 단언 추가.
- `test_evaluate_rejects_short_cup_base`: cup_base<17 이 되도록 데이터 조정(현 18<25
  였던 것 → <17 로). 또는 명시 param 으로 디커플.
- **신규** `test_evaluate_rejects_low_shelf`: 선반 위치<25(바닥 직후 반등) 합성
  시계열 → reason `shelf_too_low_in_cup`.
- 기존 게이트-로직 테스트는 명시 param 으로 기본값 변경과 독립(원칙 유지).

## 4. 과완화 방지 (필수 불변식)
- v2c 보정값으로 라이브 70종목 `pattern_count` 폭증 없음(실측 기대 0; min_cup_days=17
  단독에서 0 확인됨, min_shelf_position은 더 엄격해지는 방향이라 늘 0 유지).
- history 재실행: V자(위치<25) 이벤트가 줄고(≈24건 감소) 진짜 치트 이벤트는 유지.

## 5. 정직한 문서화 (doc-logic sync)
- v2c spec(이 문서) + 오라클 노트 갱신(8종 표·결론).
- `find-3c/SKILL.md`·`find-3c-history/SKILL.md`: 게이트 기본값(min_cup_days 17·
  min_shelf_position 25) + "진양폴리류(느슨·높은 선반)는 의도적 미검출" 명시.
- v1/v2a/v2b spec 게이트 언급에 v2c 포인터(각 1줄).

## 6. 미해결/후속
- **진양폴리류(느슨·완성 치트)**: 별도 "high/loose cheat" 변형으로 다룰지는 후속 결정.
- **NU 데이터 재현 주의**: 신선 FDR 풀과 커밋 fixture가 미세하게 다를 수 있음(배당
  조정 변동). 오라클 테스트는 **커밋 fixture가 기준**(재현성).
- 임계값(17/25)은 8종 기반 — 사례 누적 시 재보정.
- 선반 측정 정교화(CRUS 다중터치)·캐시 광역 스캔은 여전히 후속(v2b §6).

## 7. 불변 원칙
- 공유 파일 무접촉·컷오프 금지·종목별 reason·자동 commit 안 함. 동일 검출기 사용.

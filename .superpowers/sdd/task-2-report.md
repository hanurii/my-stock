# Task 2 Report: evaluate_vcp 코일 피벗·코일 게이트 전환

## Status: DONE

## Files Changed

- `scripts/canslim_lib/vcp.py` — 3군데 수정
- `tests/test_vcp.py` — `_vcp_series()` + positive 테스트 + extended 회귀 2건 수정

---

## TDD Evidence

### RED (positive test failure before vcp.py changes)

```
FAILED tests/test_vcp.py::test_evaluate_vcp_recognizes_and_breaks_out
  assert 100.0 == 96.0
  (기존 코드는 수축 천장 100.0을 피벗으로 반환; 코일 고점 96.0이어야 함)
```

### GREEN (positive test after 3 edits to vcp.py)

```
tests/test_vcp.py::test_evaluate_vcp_recognizes_and_breaks_out PASSED
  pivot_price=96.0, status=breakout, entry_ready=True
```

### Extended regression BEFORE volume-profile fix

```
FAILED tests/test_vcp.py::test_evaluate_vcp_extended_not_breakout
  AssertionError: status=breakout, pivot=95.0
  (r2_ext vol=300 → 마른 코일 오탐 → breakout 잘못 분류)

FAILED tests/test_vcp.py::test_evaluate_vcp_above_ceiling_extended_not_breakout
  AssertionError: status=breakout, pivot=107.5
  (extended vol=500 → 마른 코일 오탐 → breakout 잘못 분류)
```

### Extended regression AFTER volume-profile fix (1500 = 안 마름)

```
tests/test_vcp.py::test_evaluate_vcp_extended_not_breakout PASSED
tests/test_vcp.py::test_evaluate_vcp_above_ceiling_extended_not_breakout PASSED
```

### Full regression

```
19 passed in 0.04s
```

---

## Changes Made

### scripts/canslim_lib/vcp.py

**Edit 1 (Step 3): 피벗 산출 블록 교체**

- 구: `ceiling_seg = closes[bs:last_lo_idx+1]` → `pivot = max(ceiling_seg)` (ZigZag 수축 천장)
- 신: `ma50 = volume_ma(vols, 50)` → `coil = detect_final_coil(...)` → `pivot = coil["pivot"] if coil else None`
- 코일은 현재(돌파) 바 직전 구간만 스캔 → 피벗이 고정 저항선으로 기능

**Edit 2 (Step 4): base 채움부 중복 계산 제거 + 코일 진단 필드 추가**

- `bv`, `base_ma50`, 두 번째 `ma50` 계산 제거 (ma50은 Edit 1에서 이미 계산)
- 가산 3키: `coil_len`, `coil_dry_mean`, `coil_range_pct` (기존 13키 불변)

**Edit 3 (Step 5): 인식 게이트 교체**

- 구: `cond_dry = dry_min <= p["dry_max"]` (베이스 우측 1/3 단일바 최솟값 기준)
- 신: `cond_coil = coil is not None` (최종 타이트 코일 존재 여부)
- 실패 reason: `"volume_not_drying"` → `"no_tight_coil"`

### tests/test_vcp.py

**`_vcp_series()` 교체**: 코일 기반 픽스처로 전환
- c1+r1+c2 수축 연쇄 유지 (ZigZag 인식용)
- r2(회복)→coil(6봉, 94.5~96, 범위 1.56%)→bo(99) 구조
- r2+coil 거래량 300 (마름), bo 거래량 6000 (터짐)

**`test_evaluate_vcp_recognizes_and_breaks_out`**: `pivot_price == 96.0` 단언 추가

**`test_evaluate_vcp_extended_not_breakout`**: `vols` r2_ext 구간 300→1500
- 연장 회복 구간은 거래량 동반(비마름) → coil=None → reason=no_tight_coil → not breakout

**`test_evaluate_vcp_above_ceiling_extended_not_breakout`**: `vols` extended 구간 500→1500
- 천장 위 연장 구간도 거래량 동반 → coil=None → not breakout

---

## Self-Review Findings

1. **기존 13키 완전 유지**: vcp_detected, num_contractions, contractions, base_length_days, base_depth_pct, pivot_price, pct_to_pivot, volume_dryup_ratio, tightness_pct, status, swings, reason, entry_ready 모두 보존. 가산 3키(coil_len/coil_dry_mean/coil_range_pct) 추가.

2. **dry_max 유지**: DEFAULT_PARAMS에서 제거하지 않음(brief 제약 준수). 인식 게이트에서는 더 이상 사용되지 않지만 파라미터로 보존.

3. **no unrelated test changes**: extended 2건 외 다른 테스트 코드는 일절 수정 없음. `test_evaluate_vcp_short_base_rejected`는 `reason in ("base_too_short", "no_contraction_chain")` OR 집합 단언이라 `no_tight_coil` 영향 없음.

4. **`volume_dryup_ratio` 키**: `_mean(vols[-5:]) / ma50[-1]`로 계산 — `ma50`을 Edit 1에서 이미 선언하므로 하위 코드가 정상 참조함.

5. **코일 없을 때 `pivot=None`**: `_is_breakout`은 `pivot is None` → `return False` 처리가 있어 안전.

6. **Task 1 `detect_final_coil` 위치**: same module → 추가 import 불필요 (확인 완료).

---

## Commit

- SHA: (see git log after commit)
- Message: `feat(vcp): evaluate_vcp 피벗·인식을 최종 타이트 코일 기반으로 전환`

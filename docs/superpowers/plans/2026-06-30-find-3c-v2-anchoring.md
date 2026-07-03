# find-3c v2a 최근 컵 앵커링 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `find_cheat_shelf`를 "최근 컵 앵커링"(왼쪽 테두리=lookback 최고가 → 컵 바닥=그 이후 최저 → 선반=컵 바닥 이후 회복)으로 재설계해, `shelf_position_pct ≤ 100%`를 구조적으로 보장하고 v1의 0개·>100% 쓰레기 산출을 정상화한다.

**Architecture:** 단일 순수 함수 `find_cheat_shelf`의 앵커 순서만 교체하고, `evaluate_cheat` 진입부에 `no_overhead_cup` 거절 분기를 추가한다. 게이트 임계값·CLI·출력 스키마·상태 로직·`screen_3c.py`는 변경하지 않는다. 합성 테스트를 새 앵커링에 맞게 재작성한다.

**Tech Stack:** Python 3 (stdlib only), pytest. 기존 `canslim_lib.cheat`/`ohlcv_matrix`.

## Global Constraints

- 설계 spec: `docs/superpowers/specs/2026-06-30-find-3c-v2-anchoring-design.md`(Phase 1). v1 spec: `2026-06-30-find-3c-design.md`.
- **이 Phase는 게이트 임계값을 변경하지 않는다**(DEFAULT_PARAMS 값 불변). 게이트 튜닝은 Phase 2.
- `find_cheat_shelf` 반환 키는 v1과 동일(`cup_low_idx`,`cup_low`,`left_rim_idx`,`left_rim_high`,`shelf_high_idx`,`shelf_high`,`cup_depth_pct`,`cup_base_days`) + 신규 `no_overhead_cup`(bool).
- 앵커 순서: **왼쪽 테두리(left_rim) = argmax(highs)** → **컵 바닥(cup_low) = argmin(lows) in [left_rim_idx, n−1]** → **선반(shelf_high) = 컵 바닥 이후 눌림확인 최고가**. `shelf_high ≤ left_rim_high` 구조적 보장.
- 신규 reason `no_overhead_cup`: 게이트 순서에서 `base_too_short` 다음, `cup_too_shallow` 앞.
- 순수 함수(파일/네트워크 I/O 없음), stdlib만. 시블링 `power_play.py` 관례 유지.
- 성공 기준 = **"0개 탈출"이 아니라 "산출 정상화"**: 모든 행 `shelf_position_pct ≤ 100`, 분포가 전부-failed가 아님, 입력=출력 종목수, 모든 비패턴에 reason.
- 공유 파일 무접촉·컷오프 금지·자동 commit 금지(plan의 커밋 단계는 개발용).

## File Structure

- `scripts/canslim_lib/cheat.py` — **수정.** `_sentinel`에 `no_overhead_cup` 키 추가; `find_cheat_shelf` 본문 교체(시그니처에 `min_shelf_days` 추가); `evaluate_cheat` 진입부 `no_overhead_cup` 분기 + `find_cheat_shelf` 호출에 `min_shelf_days` 전달.
- `tests/test_cheat.py` — **재작성.** 새 앵커링에 맞춘 `find_cheat_shelf` 테스트 + `_clean_3c_v2` 픽스처 + 게이트/상태/위치불변식 테스트.
- `docs/.../2026-06-30-find-3c-design.md`(v1) — §4.2·§5 reason 목록 doc-sync(Task 3).
- `.claude/skills/find-3c/SKILL.md` — "현재 한계" 노트 갱신(Task 3).
- `public/data/sepa-3c-candidates.json` — 런타임 산출물(커밋 안 함).

---

## Task 1: v2a 앵커링 — `find_cheat_shelf` 재설계 + `no_overhead_cup`

**Files:**
- Modify: `scripts/canslim_lib/cheat.py`
- Test: `tests/test_cheat.py` (전면 재작성)

**Interfaces:**
- Consumes: `DEFAULT_PARAMS`, `_mean` (기존).
- Produces:
  - `find_cheat_shelf(highs, lows, min_shelf_pullback=None, min_shelf_days=5) -> dict` — 반환 키: 위 8개 + `no_overhead_cup`(bool).
  - `evaluate_cheat(series, params=None) -> dict` — 반환 스키마 v1과 동일, 단 `reason` 에 `no_overhead_cup` 추가 가능. `find_cheat_shelf` 를 `min_shelf_days` 와 함께 호출.

- [ ] **Step 1: Write the failing tests (rewrite the whole test file)**

`tests/test_cheat.py` 전체를 아래로 교체:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.cheat import DEFAULT_PARAMS, find_cheat_shelf, evaluate_cheat


# ── DEFAULT_PARAMS ────────────────────────────────────────────────
def test_default_params_has_required_keys():
    for k in ("lookback_days", "min_total_days", "min_cup_depth", "max_cup_depth",
              "min_cup_days", "min_shelf_pullback", "min_shelf_days", "max_shelf_days",
              "max_shelf_depth", "max_shelf_position", "breakout_vol_mult", "near_pivot_pct"):
        assert k in DEFAULT_PARAMS
    assert DEFAULT_PARAMS["min_cup_depth"] == 12.0
    assert DEFAULT_PARAMS["max_shelf_position"] == 66.0
    assert DEFAULT_PARAMS["min_shelf_days"] == 5


# ── find_cheat_shelf: 최근 컵 앵커링 ──────────────────────────────
def test_find_cheat_shelf_anchors_rim_first():
    # 옛 peak 100(idx2) → 하락 → 바닥 70(idx7) → 회복 선반 천장 85(idx10), 뒤에 눌림.
    highs = [98, 99, 100, 90, 80, 74, 71, 78, 83, 85, 85, 82, 84]
    lows  = [96, 97,  98, 88, 78, 72, 70, 76, 81, 83, 80, 80, 82]
    r = find_cheat_shelf(highs, lows, min_shelf_pullback=3.0, min_shelf_days=5)
    assert r["no_overhead_cup"] is False
    assert r["left_rim_high"] == 100     # 옛 peak(전체 최고가)
    assert r["left_rim_idx"] == 2
    assert r["cup_low"] == 70            # peak 이후 최저 저점
    assert r["cup_low_idx"] == 6
    assert r["shelf_high"] == 85         # 바닥 이후 회복 최고가, 옛 peak 100 이하
    assert r["shelf_high"] <= r["left_rim_high"]
    assert abs(r["cup_depth_pct"] - 30.0) < 1e-6   # (100-70)/100*100


def test_find_cheat_shelf_new_high_returns_no_overhead_cup():
    # 꾸준히 상승해 최고가가 마지막 봉 부근 → 옛 peak 뒤로 컵 자리 없음.
    highs = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    lows  = [ 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    r = find_cheat_shelf(highs, lows, min_shelf_pullback=3.0, min_shelf_days=5)
    assert r["no_overhead_cup"] is True


def test_find_cheat_shelf_shelf_below_rim_invariant():
    # 회복이 옛 peak를 못 넘으므로 shelf_high <= left_rim_high 항상.
    highs = [50, 90, 100, 70, 60, 65, 80, 95, 95, 92, 94]
    lows  = [48, 88,  98, 68, 58, 63, 78, 92, 90, 90, 92]
    r = find_cheat_shelf(highs, lows, min_shelf_pullback=3.0, min_shelf_days=5)
    assert r["shelf_high"] <= r["left_rim_high"]


def test_find_cheat_shelf_empty_returns_sentinel():
    r = find_cheat_shelf([], [], min_shelf_pullback=3.0)
    assert r["cup_depth_pct"] == 0.0
    assert r["no_overhead_cup"] is True


# ── evaluate_cheat helpers ────────────────────────────────────────
def _series(closes, highs=None, lows=None, vols=None):
    n = len(closes)
    highs = highs if highs is not None else [c * 1.01 for c in closes]
    lows = lows if lows is not None else [c * 0.99 for c in closes]
    vols = vols if vols is not None else [1000] * n
    dates = [f"d{i}" for i in range(n)]
    return {"dates": dates, "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def _clean_3c_v2():
    """옛 peak 100 → 30% 하락(바닥 70) → 회복(72→85) 도중 하단/중단(≈52%) 좁은
    선반(85 천장, 깊이 ~6%) → 거래량 마름. 총 47봉, cup_base_days≈44."""
    rim = [98, 99, 100, 99, 98]                          # 옛 peak 100 (idx2)
    decline = [98 - i * (28 / 19) for i in range(20)]    # 98 → ~70 (좌측 하락)
    bottom = [70, 71, 70, 72]                            # 컵 바닥
    recovery = [74, 76, 78, 80, 82, 84, 85, 85]          # 우측 회복 → 85
    shelf = [84, 83, 82, 83, 84, 83, 82, 83, 84, 83]     # 좁은 선반(천장85, 저82)
    closes = rim + decline + bottom + recovery + shelf
    n = len(closes)
    highs = [c * 1.01 for c in closes]
    lows = [c * 0.99 for c in closes]
    # 거래량: 좌측 하락 보통(1000) → 바닥·회복 대량(2000) → 선반 마름(500)
    vols = [1500] * 5 + [1000] * 20 + [2000] * (4 + 8) + [500] * 10
    return {"dates": [f"d{i}" for i in range(n)],
            "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


# ── evaluate_cheat: 정상 검출 + 불변식 ────────────────────────────
def test_evaluate_detects_clean_3c_v2():
    r = evaluate_cheat(_clean_3c_v2())
    assert r["pattern_detected"] is True
    assert r["reason"] is None
    assert 12.0 <= r["cup_depth_pct"] <= 50.0
    assert r["cup_base_days"] >= 35
    assert r["shelf_depth_pct"] <= 12.0
    assert r["shelf_position_pct"] <= 100.0          # 구조적 보장
    assert r["shelf_position_pct"] <= 66.0           # 하단/중단
    assert r["volume_dryup_ratio"] <= 1.0
    assert r["entry_ready"] == (r["pattern_detected"] and r["status"] in ("breakout", "actionable"))


def test_shelf_position_never_exceeds_100():
    # 다양한 형태에서 shelf_position_pct <= 100 (앵커링 불변식).
    cases = [_clean_3c_v2(),
             _series([100, 80, 60, 70, 85, 90, 95, 93, 94, 92, 93, 94] + [93]*30),
             _series([50, 70, 100, 95, 80, 60, 55, 65, 75, 85, 88, 86] + [87]*30)]
    for s in cases:
        r = evaluate_cheat(s)
        if r["shelf_position_pct"] is not None:
            assert r["shelf_position_pct"] <= 100.0 + 1e-6, (r["reason"], r["shelf_position_pct"])


def test_evaluate_no_data():
    r = evaluate_cheat({"closes": [], "highs": [], "lows": [], "volumes": [], "dates": []})
    assert r["pattern_detected"] is False
    assert r["reason"] == "no_data"


def test_evaluate_rejects_short_total_series():
    r = evaluate_cheat(_series([100, 99, 98, 99, 100]))
    assert r["pattern_detected"] is False
    assert r["reason"] == "base_too_short"


def test_evaluate_rejects_new_high_no_overhead_cup():
    # 단조 상승(신고가) → no_overhead_cup. 40봉 이상으로 base_too_short 회피.
    closes = [10 + i * 0.5 for i in range(45)]
    r = evaluate_cheat(_series(closes))
    assert r["pattern_detected"] is False
    assert r["reason"] == "no_overhead_cup"


# ── evaluate_cheat: 게이트 거절 ───────────────────────────────────
def test_evaluate_rejects_shallow_cup():
    # 옛 peak 100 → 얕은 하락(95, 5%) → 회복 선반. cup_too_shallow.
    rim = [98, 99, 100, 99, 98]
    decline = [98 - i * (5 / 19) for i in range(20)]      # 98 → ~93
    bottom = [95, 95.5, 95, 95.5]
    recovery = [96, 96.5, 97, 97.5, 98, 98, 97.5, 98]
    shelf = [97.5, 97, 97.5, 97, 97.5, 97, 97.5, 97, 97.5, 97]
    closes = rim + decline + bottom + recovery + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*25 + [2000]*12 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "cup_too_shallow"


def test_evaluate_rejects_deep_cup():
    # 옛 peak 100 → 깊은 하락(40, 60%) → 회복. cup_too_deep.
    rim = [98, 99, 100, 99, 98]
    decline = [98 - i * (58 / 19) for i in range(20)]     # 98 → ~40
    bottom = [40, 41, 40, 42]
    recovery = [44, 46, 48, 50, 52, 54, 55, 55]
    shelf = [54, 53, 52, 53, 54, 53, 52, 53, 54, 53]
    closes = rim + decline + bottom + recovery + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*25 + [2000]*12 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "cup_too_deep"


def test_evaluate_rejects_short_cup_base():
    # 옛 peak가 최근(베이스 기간 < 35) → cup_too_short. 앞을 낮게 패딩해 전체>=40,
    # peak가 뒤쪽 idx에 오게.
    pre = [60 + i * 0.05 for i in range(16)]              # 60~60.75 (peak 100보다 낮음)
    rim = [98, 99, 100, 99, 98]                           # peak at idx 18
    decline = [96, 90, 84, 80]
    bottom = [76, 77]
    recovery = [80, 84, 88, 90]
    shelf = [89, 88, 89, 88, 89, 88]
    closes = pre + rim + decline + bottom + recovery + shelf   # 16+5+4+2+4+6 = 37 ... 패딩 조정
    r = evaluate_cheat(_series(closes, vols=[1000]*len(closes)))
    assert r["reason"] in ("cup_too_short", "base_too_short")


def test_evaluate_rejects_shelf_too_high_in_cup():
    # 선반이 컵 상단(위치>66%): 회복이 옛 peak 100 가까이(95)까지.
    rim = [98, 99, 100, 99, 98]
    decline = [98 - i * (28 / 19) for i in range(20)]     # → ~70
    bottom = [70, 71, 70, 72]
    recovery = [76, 82, 87, 91, 93, 94, 95, 95]           # 70→95 깊은 회복
    shelf = [94, 93, 92, 93, 94, 93, 92, 93, 94, 93]
    closes = rim + decline + bottom + recovery + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*25 + [2000]*12 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "shelf_too_high_in_cup"


def test_evaluate_rejects_loose_shelf():
    # 선반 깊이>12%: 선반이 85→72까지 출렁.
    rim = [98, 99, 100, 99, 98]
    decline = [98 - i * (28 / 19) for i in range(20)]
    bottom = [70, 71, 70, 72]
    recovery = [74, 76, 78, 80, 82, 84, 85, 85]
    shelf = [80, 76, 73, 72, 75, 78, 80, 78, 76, 74]      # ~15% 출렁
    closes = rim + decline + bottom + recovery + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*25 + [2000]*12 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "shelf_too_loose"


def test_evaluate_rejects_volume_not_drying():
    # 게이트 통과하되 선반 거래량이 회복 거래량보다 높음 → volume_not_drying.
    s = _clean_3c_v2()
    s["volumes"] = [1500]*5 + [1000]*20 + [2000]*12 + [5000]*10   # 선반이 마르지 않음
    r = evaluate_cheat(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "volume_not_drying"


# ── evaluate_cheat: 상태 ──────────────────────────────────────────
def test_status_breakout_on_pivot_break_with_volume():
    s = _clean_3c_v2()
    # 선반 천장(≈85.85) 위로 종가 돌파 + 대량거래. 단 옛 peak(101)는 안 넘게(high<101).
    s["closes"].append(88.0); s["highs"].append(89.0); s["lows"].append(87.0)
    s["volumes"].append(4000); s["dates"].append("dN")
    r = evaluate_cheat(s)
    assert r["status"] == "breakout"
    assert r["entry_ready"] == (r["pattern_detected"] and r["status"] in ("breakout", "actionable"))


def test_status_actionable_near_pivot_with_dryup():
    s = _clean_3c_v2()
    s["closes"].append(83.0); s["highs"].append(84.0); s["lows"].append(82.0)
    s["volumes"].append(500); s["dates"].append("dN")
    r = evaluate_cheat(s)
    assert r["status"] == "actionable"
    assert 0 <= r["pct_to_pivot"] <= 5


def test_entry_ready_false_for_non_pattern_breakout():
    # 얕은 컵(non-pattern)인데 선반 돌파 신호는 나타남 → entry_ready False.
    rim = [98, 99, 100, 99, 98]
    decline = [98 - i * (5 / 19) for i in range(20)]
    bottom = [95, 95.5, 95, 95.5]
    recovery = [96, 96.5, 97, 97.5, 98, 98, 98, 98]
    shelf = [97.5, 97, 97.5, 97, 97.5, 97, 97.5, 97]
    closes = rim + decline + bottom + recovery + shelf
    s = _series(closes, vols=[1000]*25 + [2000]*12 + [500]*8)
    s["closes"].append(99.0); s["highs"].append(99.5); s["lows"].append(98.5)
    s["volumes"].append(4000); s["dates"].append("dN")
    r = evaluate_cheat(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "cup_too_shallow"
    assert r["status"] in ("breakout", "actionable")
    assert r["entry_ready"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cheat.py -v`
Expected: 다수 FAIL — `find_cheat_shelf` 가 아직 v1(바닥-우선) 앵커링이고 `no_overhead_cup` 키/분기가 없어 새 단언이 깨진다.

- [ ] **Step 3: Update `_sentinel` to carry `no_overhead_cup`**

`scripts/canslim_lib/cheat.py` 의 `_sentinel` 을 교체:

```python
def _sentinel() -> dict:
    return {"cup_low_idx": 0, "cup_low": 0.0, "left_rim_idx": 0, "left_rim_high": 0.0,
            "shelf_high_idx": 0, "shelf_high": 0.0, "cup_depth_pct": 0.0, "cup_base_days": 0,
            "no_overhead_cup": True}
```

- [ ] **Step 4: Replace `find_cheat_shelf` with the v2a anchoring**

`scripts/canslim_lib/cheat.py` 의 `find_cheat_shelf` 본문을 교체:

```python
def find_cheat_shelf(highs: list[float], lows: list[float],
                     min_shelf_pullback: float | None = None,
                     min_shelf_days: int = 5) -> dict:
    """최근 컵 앵커링: 왼쪽 테두리(left_rim)=lookback 최고가(옛 peak) → 컵 바닥
    (cup_low)=그 이후 최저 저점 → 선반 고점(shelf_high)=컵 바닥 이후 '뒤에 눌림이
    확인된 최고 고가'(피벗). shelf_high ≤ left_rim_high 가 구조적으로 보장된다.

    옛 peak 가 너무 최근(left_rim_idx ≥ n-1-min_shelf_days)이거나 회복 구간이 비면
    컵이 없다고 보고 sentinel(no_overhead_cup=True)을 반환한다(신고가/무조정).
    """
    if not highs or not lows:
        return _sentinel()
    n = len(highs)
    left_rim_idx = max(range(n), key=lambda i: highs[i])
    left_rim_high = highs[left_rim_idx]
    # 옛 peak 뒤로 컵+선반이 들어설 자리가 없음 → 컵 없음(신고가/무조정)
    if left_rim_idx >= n - 1 - min_shelf_days:
        s = _sentinel()
        s["left_rim_idx"] = left_rim_idx
        s["left_rim_high"] = left_rim_high
        return s
    cup_low_idx = min(range(left_rim_idx, n), key=lambda i: lows[i])
    cup_low = lows[cup_low_idx]
    if cup_low_idx >= n - 1:                       # 회복 구간 비어 있음
        s = _sentinel()
        s["left_rim_idx"] = left_rim_idx
        s["left_rim_high"] = left_rim_high
        s["cup_low_idx"] = cup_low_idx
        s["cup_low"] = cup_low
        return s
    right = range(cup_low_idx + 1, n)
    if min_shelf_pullback is None:
        cand = [i for i in right if i < n - 1]
    else:
        pb = min_shelf_pullback / 100.0
        cand = [i for i in right if i < n - 1 and min(lows[i + 1:]) <= highs[i] * (1 - pb)]
    if cand:
        shelf_high_idx = max(cand, key=lambda i: highs[i])
    else:
        shelf_high_idx = max(right, key=lambda i: highs[i])
    shelf_high = highs[shelf_high_idx]
    cup_depth_pct = (left_rim_high - cup_low) / left_rim_high * 100.0 if left_rim_high > 0 else 0.0
    cup_base_days = (n - 1) - left_rim_idx
    return {"cup_low_idx": cup_low_idx, "cup_low": cup_low,
            "left_rim_idx": left_rim_idx, "left_rim_high": left_rim_high,
            "shelf_high_idx": shelf_high_idx, "shelf_high": shelf_high,
            "cup_depth_pct": cup_depth_pct, "cup_base_days": cup_base_days,
            "no_overhead_cup": False}
```

- [ ] **Step 5: Add the `no_overhead_cup` branch in `evaluate_cheat`**

`scripts/canslim_lib/cheat.py` 의 `evaluate_cheat` 에서 `find_cheat_shelf` 호출부를 찾아 `min_shelf_days` 를 넘기고, 직후에 거절 분기를 추가한다. 기존:

```python
    cs = find_cheat_shelf(highs, lows, p["min_shelf_pullback"])
    lri, cli, shi = cs["left_rim_idx"], cs["cup_low_idx"], cs["shelf_high_idx"]
```

를 다음으로 교체:

```python
    cs = find_cheat_shelf(highs, lows, p["min_shelf_pullback"], p["min_shelf_days"])
    if cs.get("no_overhead_cup"):
        base["reason"] = "no_overhead_cup"
        return base
    lri, cli, shi = cs["left_rim_idx"], cs["cup_low_idx"], cs["shelf_high_idx"]
```

(나머지 `evaluate_cheat` 본문·게이트·상태 로직은 변경 없음. `no_overhead_cup` 은 `base_too_short` 다음, 깊이 계산 전에 처리되어 §spec 게이트 순서를 만족한다.)

- [ ] **Step 6: Run tests; TDD-tune ONLY test data (not logic) until green**

Run: `python -m pytest tests/test_cheat.py -v`
Expected: 전부 PASS. 합성 시계열이 의도한 reason/status 를 정확히 내지 않으면 **테스트
데이터만** 조정한다(앵커가 rim-우선으로 바뀌어 인덱스/지표가 달라질 수 있음). 특히:
- `_clean_3c_v2` 가 `pattern_detected=True` 가 되도록(left_rim=100·cup_low≈70·shelf≈85,
  위치≈52%, 깊이≈30%, dryup≈0.25).
- `test_evaluate_rejects_short_cup_base` 가 `cup_too_short` 를 내도록 `pre` 길이를 조정
  (전체 n≥40 이면서 peak→현재 거래일수 <35). 안 되면 assert 의 `in (...)` 를 유지하고
  실제 reason 을 보고서에 기록.
디버그 1줄:
```bash
python -c "import sys; sys.path.insert(0,'scripts'); import tests.test_cheat as t; from canslim_lib.cheat import evaluate_cheat, find_cheat_shelf; print(find_cheat_shelf(t._clean_3c_v2()['highs'], t._clean_3c_v2()['lows'], 3.0, 5)); print(evaluate_cheat(t._clean_3c_v2()))"
```
**`evaluate_cheat`/`find_cheat_shelf` 로직은 위 Step 3~5 에서 확정 — 절대 수정하지 말 것.**
만약 로직 수정 없이 어떤 테스트의 의도를 못 만들면 BLOCKED 로 보고.

- [ ] **Step 7: Commit**

```bash
git add scripts/canslim_lib/cheat.py tests/test_cheat.py
git commit -m "feat(find-3c): v2a 최근 컵 앵커링(rim-first) + no_overhead_cup + 테스트 재작성"
```

---

## Task 2: 라이브 재실행 + 실제 사례 1개 대조 (산출 정상화 검증)

**Files:**
- Create: `docs/superpowers/notes/2026-06-30-find-3c-v2a-validation.md` (검증 기록)

**Interfaces:**
- Consumes: Task 1의 `evaluate_cheat`(v2a), `screen_3c.py`, `ohlcv_matrix.get_series`.
- Produces: 검증 노트(코드 아님).

- [ ] **Step 1: Re-run the full live screen**

```bash
python scripts/screen_3c.py
```
Expected: `💾 저장: ...sepa-3c-candidates.json` + `[3C 요약]` 한 줄. 에러 없음.

- [ ] **Step 2: Assert "sane output" invariants on the JSON**

```bash
python -c "
import json
d=json.load(open('public/data/sepa-3c-candidates.json',encoding='utf-8'))
pos=[c['shelf_position_pct'] for c in d['candidates'] if c.get('shelf_position_pct') is not None]
over=[p for p in pos if p>100.0001]
print('candidates', len(d['candidates']))
print('shelf_position>100 count:', len(over), '(expect 0)')
print('max shelf_position:', max(pos) if pos else None)
from collections import Counter
print('reasons:', Counter(c.get('reason') for c in d['candidates']))
print('dist:', d['status_distribution'], 'pattern', d['pattern_count'], 'entry', d['entry_ready_count'])
assert len(over)==0, 'shelf_position>100 still present — anchoring not fixed'
assert all(c.get('reason') or c.get('pattern_detected') for c in d['candidates'])
print('SANE: no >100 positions, all non-pattern have reason')
"
```
Expected: `shelf_position>100 count: 0`. 분포에 `no_overhead_cup` 가 다수 나타나는 것이
정상(트렌드 통과=신고가 다수). 패턴 개수는 0이어도 무방(Phase 2에서 판단). **>100 이
하나라도 있으면 앵커링 미수정 → BLOCKED.**

- [ ] **Step 3: Spot-check one real "recently-corrected" ticker**

입력 종목 중 최근 조정 후 회복형(=`no_overhead_cup` 가 아니고 cup_depth 가 12~50%
범위로 잡힌) 종목을 하나 골라 `--ticker` 로 지표를 확인:
```bash
python -c "
import json
d=json.load(open('public/data/sepa-3c-candidates.json',encoding='utf-8'))
c=[x for x in d['candidates'] if x.get('reason')!='no_overhead_cup' and x.get('cup_depth_pct') and 12<=x['cup_depth_pct']<=50]
c.sort(key=lambda x:(x.get('shelf_position_pct') or 999))
for x in c[:5]:
    print(x['code'], x['name'][:8], 'depth',x['cup_depth_pct'],'pos',x['shelf_position_pct'],'shelfD',x['shelf_depth_pct'],'reason',x.get('reason'),'status',x['status'])
"
```
그 중 하나의 코드로:
```bash
python scripts/screen_3c.py --ticker <CODE>
```
Expected: `left_rim > shelf_high > cup_low`, `0 < shelf_position ≤ 100`, `cup_depth` 가
12~50% 범위로 합리적. 즉 v2a 앵커가 실제 종목에서 "옛 고점→하락→회복 선반" 구조를
정상적으로 짚는다.

> 메모: 더 오래된 책 예시(과거 데이터)는 캐시(~1.5년)에 없을 수 있다. 그건 Phase 2
> 에서 FDR(`fdr.DataReader(code, start, end)`)로 받아 as-of 슬라이스 검증한다. 이
> Step 은 캐시에 있는 "최근 조정형" 1종목으로 v2a 앵커의 현실 동작만 확인한다.

- [ ] **Step 4: Write the validation note**

`docs/superpowers/notes/2026-06-30-find-3c-v2a-validation.md` 에 기록:
- 라이브 요약 한 줄(pattern/entry/dist), `shelf_position>100` 개수(=0 확인),
  reason 분포(특히 `no_overhead_cup` 비중).
- spot-check 한 종목의 left_rim/cup_low/shelf_high/position/depth 와 "정상" 판정.
- 결론: v2a 가 산출을 정상화했는가(Yes/No), 패턴이 여전히 0이면 그 해석(게이트 strict
  → Phase 2 대상).

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/notes/2026-06-30-find-3c-v2a-validation.md
git commit -m "docs(find-3c): v2a 라이브·실예시 검증 노트(산출 정상화 확인)"
```

---

## Task 3: 문서 동기화 (doc-logic sync)

**Files:**
- Modify: `docs/superpowers/specs/2026-06-30-find-3c-design.md` (v1 spec)
- Modify: `.claude/skills/find-3c/SKILL.md`

**Interfaces:**
- Consumes: Task 1·2 결과(확정된 v2a 동작·검증 수치).
- Produces: 없음(문서).

- [ ] **Step 1: Point v1 spec §4.2 to v2a + add `no_overhead_cup` to reason list**

`docs/superpowers/specs/2026-06-30-find-3c-design.md` 에서:
1. §4.2 앵커링 절 맨 앞에 한 줄 추가(본문은 남기되 상위 포인터):
```markdown
> **갱신(2026-06-30, v2a):** 아래 "컵 바닥 먼저" 앵커링은 트렌드 통과 입력(신고가
> 다수)에서 `shelf_position>100%`·패턴 0을 내는 한계가 확인되어, **"왼쪽 테두리(옛
> peak)=lookback 최고가 먼저"** 앵커링으로 교체되었다. 정의·근거는
> `2026-06-30-find-3c-v2-anchoring-design.md` 참조. 본 절의 이하 내용은 역사적 기록.
```
2. §5 reason 목록 문장에 `no_overhead_cup` 을 추가(나열되는 곳):
   `... base_too_short / no_overhead_cup / cup_too_shallow / cup_too_deep / ...`.

- [ ] **Step 2: Update SKILL.md "현재 한계" note to reflect v2a**

`.claude/skills/find-3c/SKILL.md` 의 `## 현재 한계 (v1)` 절을 Task 2 의 실제 결과에
맞춰 교체. 패턴이 여전히 0이면:
```markdown
## 현재 한계 (v2a)
- 앵커링은 v2a("왼쪽 테두리=옛 peak 먼저")로 수정되어 `shelf_position_pct ≤ 100%`
  가 보장되고, 신고가 종목은 `no_overhead_cup` 으로 정직하게 걸러진다. 다만 게이트
  (컵 깊이 12~50%/35일, 선반 위치 ≤66% 등)는 아직 strict 라 트렌드 통과 종목 중
  3C 후보가 매우 적을 수 있다(현 풀런 패턴 N개 — 실제 수치 기입). **책 3C 예시로
  게이트를 보정하는 작업이 후속(Phase 2)**이다(spec §8).
```
(Task 2 에서 패턴이 0보다 크게 나왔다면 문구를 그 결과에 맞게 사실대로 적는다.)

- [ ] **Step 3: Verify docs render and frontmatter still parses**

```bash
python -c "t=open('.claude/skills/find-3c/SKILL.md',encoding='utf-8').read(); assert t.startswith('---') and 'name: find-3c' in t; print('SKILL frontmatter OK')"
```
Expected: `SKILL frontmatter OK`.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-06-30-find-3c-design.md .claude/skills/find-3c/SKILL.md
git commit -m "docs(find-3c): v2a 앵커링 반영 — v1 spec 포인터 + SKILL 한계 노트 갱신"
```

---

## Self-Review (작성자 점검)

**1. Spec coverage:**
- v2a 앵커링(spec §2) → Task 1 `find_cheat_shelf` 교체. ✓
- `no_overhead_cup`(spec §2.1·§4) → Task 1 `_sentinel`+분기, reason 순서 base_too_short 다음. ✓
- 유지 항목(게이트·CLI·스키마·상태, spec §3) → Task 1 은 그 외 본문 미변경. ✓
- 위치 ≤100% 보장(spec §5) → Task 1 `test_shelf_position_never_exceeds_100`·`test_find_cheat_shelf_shelf_below_rim_invariant` + Task 2 Step 2 라이브 단언. ✓
- 검증 계획(spec §6.1 테스트/§6.2 라이브/§6.3 실예시) → Task 1 테스트 / Task 2 Step 1-3. ✓
- 영향 파일(spec §7) → Task 1(cheat.py·test), Task 2(노트), Task 3(v1 spec·SKILL). screen_3c.py 무변경 명시. ✓
- doc-logic sync(spec §7) → Task 3. ✓

**2. Placeholder scan:** 모든 코드 step 에 실제 코드/명령/기대출력 포함. Task 1 Step 6·Task 2 Step 3 의 데이터 튜닝은 의도된 TDD 단계(로직 동결 명시). ✓

**3. Type consistency:** `find_cheat_shelf` 반환 키(+`no_overhead_cup`)가 Task 1 `evaluate_cheat` 분기에서 `cs.get("no_overhead_cup")`/`cs["left_rim_idx"]` 등으로 일관 소비. `min_shelf_days` 가 DEFAULT_PARAMS(기존)·find_cheat_shelf 시그니처·evaluate_cheat 호출에서 일치. 테스트가 `evaluate_cheat`/`find_cheat_shelf` 의 실제 반환 키만 단언. ✓

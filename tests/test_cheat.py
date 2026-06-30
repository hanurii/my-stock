import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.cheat import DEFAULT_PARAMS, find_cheat_shelf, evaluate_cheat


# ── DEFAULT_PARAMS ────────────────────────────────────────────────
def test_default_params_has_required_keys():
    for k in ("lookback_days", "min_total_days", "min_cup_depth", "max_cup_depth",
              "min_cup_days", "min_shelf_pullback", "min_shelf_days", "max_shelf_days",
              "max_shelf_depth", "min_shelf_position", "max_shelf_position",
              "breakout_vol_mult", "near_pivot_pct"):
        assert k in DEFAULT_PARAMS
    assert DEFAULT_PARAMS["min_cup_depth"] == 12.0
    assert DEFAULT_PARAMS["max_shelf_position"] == 90.0
    assert DEFAULT_PARAMS["min_shelf_days"] == 2
    assert DEFAULT_PARAMS["min_cup_days"] == 17
    assert DEFAULT_PARAMS["min_shelf_position"] == 25.0


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
    # 앞을 길게(낮게) 패딩해 n>=40 이면서, 옛 peak(global max)를 뒤쪽에 둬
    # cup_base_days = (n-1) - left_rim_idx < 25 → cup_too_short.
    pre = [60 + i * 0.02 for i in range(22)]      # 60~60.42, 22봉(peak보다 낮음)
    rim = [98, 99, 100, 99, 98]                   # peak(global max) at idx 24
    decline = [96, 90, 84, 80]
    bottom = [76, 77]
    recovery = [80, 84, 88, 90]
    shelf = [89, 88, 89, 88, 89, 88]
    closes = pre + rim + decline + bottom + recovery + shelf  # 22+5+4+2+4+6 = 43
    r = evaluate_cheat(_series(closes, vols=[1000]*len(closes)), {"min_cup_days": 25})
    # left_rim_idx=24, n=43 → cup_base_days=18 < 25
    assert r["pattern_detected"] is False
    assert r["reason"] == "cup_too_short"


def test_evaluate_rejects_shelf_too_high_in_cup():
    # 선반이 컵 상단(위치>66%): 회복이 옛 peak 100 가까이(95)까지.
    rim = [98, 99, 100, 99, 98]
    decline = [98 - i * (28 / 19) for i in range(20)]     # → ~70
    bottom = [70, 71, 70, 72]
    recovery = [76, 82, 87, 91, 93, 94, 95, 95]           # 70→95 깊은 회복
    shelf = [94, 93, 92, 93, 94, 93, 92, 93, 94, 93]
    closes = rim + decline + bottom + recovery + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*25 + [2000]*12 + [500]*10),
                       {"max_shelf_position": 66})
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


def test_evaluate_rejects_low_shelf():
    # 옛 peak 100 → 가파른 하락 바닥 60(컵40%) → 바닥 직후 64 부근 즉시 반등(위치~10%).
    rim = [98, 99, 100, 99, 98]
    decline = [98 - i * (38 / 19) for i in range(20)]     # 98 → ~60
    bottom = [60, 61, 60, 61, 60]                          # 5봉(n=40 확보)
    shelf = [64, 63, 64, 63, 64, 63, 64, 63, 64, 63]      # 바닥 바로 위 64(위치 ~10%)
    closes = rim + decline + bottom + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*25 + [2000]*5 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "shelf_too_low_in_cup"


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

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.cheat import DEFAULT_PARAMS, find_cheat_shelf, evaluate_cheat


def test_default_params_has_required_keys():
    for k in ("lookback_days", "min_total_days", "min_cup_depth", "max_cup_depth",
              "min_cup_days", "min_shelf_pullback", "min_shelf_days", "max_shelf_days",
              "max_shelf_depth", "max_shelf_position", "breakout_vol_mult", "near_pivot_pct"):
        assert k in DEFAULT_PARAMS
    assert DEFAULT_PARAMS["min_cup_depth"] == 12.0
    assert DEFAULT_PARAMS["max_shelf_position"] == 66.0


def test_find_cheat_shelf_anchors_bottom_first():
    # 왼쪽 테두리 100(idx0) → 바닥 70(idx4) → 우측 반등 후 선반 천장 85(idx8),
    # 선반 천장 뒤로 80까지 눌림(>3%) 확인. 피벗은 옛 고점 100이 아니라 85.
    highs = [100, 92, 84, 76, 71, 78, 83, 85, 85, 82, 84]
    lows  = [ 98, 90, 82, 74, 70, 76, 81, 83, 80, 80, 82]
    r = find_cheat_shelf(highs, lows, min_shelf_pullback=3.0)
    assert r["cup_low"] == 70
    assert r["cup_low_idx"] == 4
    assert r["left_rim_high"] == 100
    assert r["left_rim_idx"] == 0
    assert r["shelf_high"] == 85          # 옛 고점 100이 아님(바닥 이후 우측에서만)
    assert r["shelf_high_idx"] in (7, 8)  # 85를 찍은 봉
    assert abs(r["cup_depth_pct"] - 30.0) < 1e-6   # (100-70)/100*100
    assert r["cup_base_days"] == (len(highs) - 1) - 0


def test_find_cheat_shelf_excludes_fresh_breakout_bar():
    # 마지막 바가 우측 신고가 90으로 돌파. 피벗은 돌파봉(90)이 아니라 선반 천장 85.
    highs = [100, 92, 84, 76, 71, 78, 83, 85, 84, 83, 90]
    lows  = [ 98, 90, 82, 74, 70, 76, 81, 83, 80, 81, 88]
    r = find_cheat_shelf(highs, lows, min_shelf_pullback=3.0)
    assert r["shelf_high"] == 85
    assert r["shelf_high_idx"] == 7


def test_find_cheat_shelf_empty_returns_sentinel():
    r = find_cheat_shelf([], [], min_shelf_pullback=3.0)
    assert r["cup_depth_pct"] == 0.0
    assert r["cup_base_days"] == 0


def _series(closes, highs=None, lows=None, vols=None):
    n = len(closes)
    highs = highs if highs is not None else [c * 1.01 for c in closes]
    lows = lows if lows is not None else [c * 0.99 for c in closes]
    vols = vols if vols is not None else [1000] * n
    dates = [f"d{i}" for i in range(n)]
    return {"dates": dates, "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def _clean_3c():
    """왼쪽 하락(100→70, 30%) → 바닥 다지기 → 우측 반등(72→85) → 하단/중단(50%)
    위치의 좁은 선반(85, 깊이 ~6%) → 거래량 마름. 총 44봉."""
    decline = [100 - i * (30 / 21) for i in range(22)]       # 100→~70, 22봉
    bottom = [70, 71, 70, 72]                                # 바닥 4봉
    rally = [74, 76, 78, 80, 82, 84, 85, 85]                 # 72→85 반등 8봉
    shelf = [84, 83, 82, 83, 84, 83, 82, 83, 84, 83]         # 85천장 대비 ~6% 좁은 선반 10봉
    closes = decline + bottom + rally + shelf
    n = len(closes)                                          # 44
    highs = [c * 1.01 for c in closes]
    lows = [c * 0.99 for c in closes]
    # 선반 천장(idx≈28, 85)이 우측 최고가가 되도록, 그리고 그 뒤로 눌림이 있도록
    # highs/lows 는 위 close 비율로 충분(선반에서 82까지 눌림 = 85*0.99=84.15 위지만
    # close 82*0.99=81.18 로 85*0.99=84.15 대비 >3% 눌림 충족).
    # 거래량: 좌측 하락 보통(1000) → 바닥+우측 반등 대량(2000) → 선반 마름(500)
    vols = [1000] * 22 + [2000] * (4 + 8) + [500] * 10
    return {"dates": [f"d{i}" for i in range(n)],
            "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def test_evaluate_detects_clean_3c():
    r = evaluate_cheat(_clean_3c())
    assert r["pattern_detected"] is True
    assert r["reason"] is None
    assert 12.0 <= r["cup_depth_pct"] <= 50.0
    assert r["cup_base_days"] >= 35
    assert r["shelf_depth_pct"] <= 12.0
    assert r["shelf_position_pct"] <= 66.0
    assert r["volume_dryup_ratio"] <= 1.0
    assert r["pivot_price"] is not None
    assert r["entry_ready"] == (r["pattern_detected"] and r["status"] in ("breakout", "actionable"))


def test_evaluate_no_data():
    r = evaluate_cheat({"closes": [], "highs": [], "lows": [], "volumes": [], "dates": []})
    assert r["pattern_detected"] is False
    assert r["reason"] == "no_data"


def test_evaluate_rejects_short_total_series():
    r = evaluate_cheat(_series([100, 99, 98, 99, 100]))
    assert r["pattern_detected"] is False
    assert r["reason"] == "base_too_short"


def test_evaluate_rejects_shallow_cup():
    # 컵 깊이 ~5% (<12%) → cup_too_shallow. 좌측 100→95 만 하락.
    decline = [100 - i * (5 / 21) for i in range(22)]        # 100→~95
    bottom = [95, 95.5, 95, 95.5]
    rally = [96, 96.5, 97, 97.5, 98, 98, 97.5, 98]
    shelf = [97.5, 97, 97.5, 97, 97.5, 97, 97.5, 97, 97.5, 97]
    closes = decline + bottom + rally + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*22 + [2000]*12 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "cup_too_shallow"


def test_evaluate_rejects_deep_cup():
    # 컵 깊이 ~60% (>50%) → cup_too_deep. 좌측 100→40 하락.
    decline = [100 - i * (60 / 21) for i in range(22)]       # 100→~40
    bottom = [40, 41, 40, 42]
    rally = [44, 46, 48, 50, 52, 54, 55, 55]
    shelf = [54, 53, 52, 53, 54, 53, 52, 53, 54, 53]
    closes = decline + bottom + rally + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*22 + [2000]*12 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "cup_too_deep"


def test_evaluate_rejects_short_cup_base():
    # 베이스 기간 < 35봉(V자). 전체 30봉, 좌측 짧은 하락.
    decline = [100 - i * (30 / 9) for i in range(10)]        # 100→~70, 10봉
    bottom = [70, 72]
    rally = [74, 78, 82, 85]
    shelf = [84, 83, 82, 83, 84, 83, 82, 84]                 # 8봉
    closes = decline + bottom + rally + shelf                # 24봉 < min_total? -> 길이 보장 위해 패딩
    # min_total_days(40) 미만이면 base_too_short 가 먼저 뜨므로, 좌측을 늘려
    # 전체>=40 이되 베이스 기간(좌측테두리→현재)만 짧게 만들 수 없음(테두리=idx0).
    # 대신 lookback 으로 앞을 잘라 베이스를 짧게: 좌측에 '더 높은 옛 고점'을 두지
    # 않고 전체를 41봉으로 만들되 cup_base_days = n-1-left_rim_idx 를 <35 로:
    # left_rim_idx 를 뒤로 밀려면 좌측 초반이 테두리보다 낮아야 한다.
    # pre 값이 cup 바닥(70)보다 높고 왼쪽 테두리(100)보다 낮아야 cup 앵커가 올바른 위치를 잡는다.
    # pre=60 계열이면 pre 자체가 최저점이 돼 cup 이 엉뚱하게 잡힘 → 75 계열 16봉으로 조정.
    # n=40(>=min_total_days), left_rim_idx=16, cup_base_days=(39-16)=23 < 35 → cup_too_short.
    pre = [75 + i * 0.1 for i in range(16)]                  # 75~76.5, 바닥(70)↑ · 테두리(100)↓
    closes = pre + decline + bottom + rally + shelf          # 16+24=40
    r = evaluate_cheat(_series(closes, vols=[1000]*(len(closes))))
    assert r["reason"] == "cup_too_short"


def test_evaluate_rejects_loose_shelf():
    # 선반 깊이 >12% → shelf_too_loose. 우측 선반을 85→72(~15%)까지 출렁이게.
    decline = [100 - i * (30 / 21) for i in range(22)]
    bottom = [70, 71, 70, 72]
    rally = [74, 76, 78, 80, 82, 84, 85, 85]
    shelf = [80, 76, 73, 72, 75, 78, 80, 78, 76, 74]        # 85 대비 ~15% 출렁
    closes = decline + bottom + rally + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*22 + [2000]*12 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "shelf_too_loose"


def test_evaluate_rejects_shelf_too_high_in_cup():
    # 선반이 컵 상단(위치 >66%) → shelf_too_high_in_cup.
    # 컵 100→70(깊이30), 선반 천장이 95 (위치=(95-70)/30=83%).
    decline = [100 - i * (30 / 21) for i in range(22)]
    bottom = [70, 71, 70, 72]
    rally = [76, 82, 87, 91, 93, 94, 95, 95]                # 72→95 깊은 회복
    shelf = [94, 93, 92, 93, 94, 93, 92, 93, 94, 93]        # 95 천장 좁은 선반
    closes = decline + bottom + rally + shelf
    r = evaluate_cheat(_series(closes, vols=[1000]*22 + [2000]*12 + [500]*10))
    assert r["pattern_detected"] is False
    assert r["reason"] == "shelf_too_high_in_cup"


def test_status_breakout_on_pivot_break_with_volume():
    s = _clean_3c()
    # 선반 천장(≈85.85=85*1.01) 위로 종가 돌파 + 대량거래 1봉 추가.
    # 새 봉 high(88)는 우측 신고가지만 마지막 봉이라 피벗 후보에서 제외된다.
    s["closes"].append(87.0)
    s["highs"].append(88.0)
    s["lows"].append(86.0)
    s["volumes"].append(4000)   # rally 평균(≈1923)의 1.4배(=2692) 이상
    s["dates"].append("dN")
    r = evaluate_cheat(s)
    assert r["status"] == "breakout"
    assert r["entry_ready"] == (r["pattern_detected"] and r["status"] in ("breakout", "actionable"))


def test_status_actionable_near_pivot_with_dryup():
    s = _clean_3c()
    # 종가가 피벗(≈85.85) 0~5% 아래 + 거래량 마름 유지
    s["closes"].append(83.0)    # (85.85-83)/85.85 ≈ 3.3%
    s["highs"].append(84.0)
    s["lows"].append(82.0)
    s["volumes"].append(500)
    s["dates"].append("dN")
    r = evaluate_cheat(s)
    assert r["status"] == "actionable"
    assert 0 <= r["pct_to_pivot"] <= 5


def test_status_failed_on_shelf_breakdown():
    s = _clean_3c()
    # 선반 영역(82~85) 아래 대폭 이탈 → shelf_depth>12% 로 failed.
    # low=70.5 는 cup_low(69.3)보다 높아 컵 앵커를 유지하면서 선반 깊이를 ~18%로 확대.
    # (원 brief 의 low=69.0 은 cup_low=69.3 보다 낮아 컵 구조가 무너져서 조정)
    s["closes"].append(73.0)
    s["highs"].append(74.0)
    s["lows"].append(70.5)
    s["volumes"].append(1500)
    s["dates"].append("dN")
    r = evaluate_cheat(s)
    assert r["status"] == "failed"


def test_entry_ready_false_for_non_pattern_breakout():
    # 컵 너무 얕음(non-pattern)이지만 돌파 신호가 나타나면 entry_ready=False.
    decline = [100 - i * (5 / 21) for i in range(22)]       # 깊이 ~5%
    bottom = [95, 95.5, 95, 95.5]
    rally = [96, 96.5, 97, 97.5, 98, 98, 98, 98]
    shelf = [97.5, 97, 97.5, 97, 97.5, 97, 97.5, 97]
    closes = decline + bottom + rally + shelf
    s = _series(closes, vols=[1000]*22 + [2000]*12 + [500]*8)
    s["closes"].append(99.0)
    s["highs"].append(100.0)
    s["lows"].append(98.0)
    s["volumes"].append(4000)
    s["dates"].append("dN")
    r = evaluate_cheat(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "cup_too_shallow"
    assert r["entry_ready"] is False

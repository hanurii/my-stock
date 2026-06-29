import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.power_play import DEFAULT_PARAMS, find_flagpole, evaluate_power_play


def test_default_params_has_required_keys():
    for k in ("lookback_days", "min_flagpole_gain", "max_flagpole_days",
              "pole_vol_mult", "quiet_window", "max_pre_pole_gain",
              "min_flag_days", "max_flag_days", "max_flag_depth",
              "breakout_vol_mult", "near_pivot_pct", "min_total_days"):
        assert k in DEFAULT_PARAMS
    assert DEFAULT_PARAMS["min_flagpole_gain"] == 100.0
    assert DEFAULT_PARAMS["max_flagpole_days"] == 40


def test_find_flagpole_detects_doubling():
    # 저점 50에서 시작해 110까지(+120%) 오른 뒤, 100 근처 고점이 인덱스 5
    highs = [52, 70, 90, 105, 110, 111, 108, 106, 104]
    lows  = [50, 66, 86, 100, 105, 106, 100, 98, 96]
    fp = find_flagpole(highs, lows, max_flagpole_days=40)
    # 구간 최고 고가는 인덱스 5(111)
    assert fp["flag_high_idx"] == 5
    assert fp["flag_high"] == 111
    # 깃대 시작 저점은 50(인덱스 0)
    assert fp["pole_start_low"] == 50
    assert fp["pole_start_idx"] == 0
    # (111-50)/50*100 = 122%
    assert abs(fp["flagpole_gain_pct"] - 122.0) < 1e-6
    assert fp["flagpole_days"] == 5


def test_find_flagpole_respects_window_cap():
    # 아주 오래된 저점(인덱스0=10)은 40일 경계 밖이면 무시되고,
    # 경계 안 최저점만 깃대 시작으로 잡힌다.
    highs = [12] + [40]*45 + [80]   # 고점은 마지막(인덱스46)
    lows  = [10] + [38]*45 + [70]
    fp = find_flagpole(highs, lows, max_flagpole_days=40)
    assert fp["flag_high_idx"] == 46
    # 경계 = 46-40 = 6 이후의 최저 저점(38), 10이 아님
    assert fp["pole_start_low"] == 38
    assert fp["flagpole_days"] <= 40


def test_find_flagpole_single_element_returns_sentinel():
    fp = find_flagpole([100.0], [90.0], max_flagpole_days=40)
    assert fp["flagpole_gain_pct"] == 0.0
    assert fp["flagpole_days"] == 0
    assert fp["flag_high_idx"] == 0


def test_find_flagpole_empty_returns_sentinel():
    fp = find_flagpole([], [], max_flagpole_days=40)
    assert fp["flagpole_gain_pct"] == 0.0


def _series(closes, highs=None, lows=None, vols=None):
    n = len(closes)
    highs = highs if highs is not None else [c * 1.01 for c in closes]
    lows = lows if lows is not None else [c * 0.99 for c in closes]
    vols = vols if vols is not None else [1000] * n
    dates = [f"2026-01-{i+1:03d}" for i in range(n)]
    return {"dates": dates, "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def _clean_htf():
    """조용(20일 저변동) → 8주 내 +120% 깃대(대량거래) → 좁고 얕은 깃발(~10%)."""
    quiet = [50 + (i % 2) for i in range(20)]          # 50~51 횡보(조용)
    pole = [52, 58, 66, 75, 85, 95, 104, 110]          # 50→110 (+120%), 8일
    flag = [108, 106, 105, 104, 103, 105, 106, 107, 106, 105]  # 고점110 대비 ~5.5% 얕은 깃발
    closes = quiet + pole + flag
    highs = [c * 1.01 for c in closes]
    lows = [c * 0.99 for c in closes]
    # 거래량: 조용 낮음(800) → 깃대 대량(3000) → 깃발 마름(500)
    vols = [800]*len(quiet) + [3000]*len(pole) + [500]*len(flag)
    return {"dates": [f"d{i}" for i in range(len(closes))],
            "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def test_evaluate_detects_clean_htf():
    r = evaluate_power_play(_clean_htf())
    assert r["pattern_detected"] is True
    assert r["reason"] is None
    assert r["flagpole_gain_pct"] >= 100.0
    assert r["flag_depth_pct"] <= 20.0
    assert r["flagpole_vol_ratio"] >= 1.5
    assert r["pivot_price"] is not None
    assert r["entry_ready"] == (r["pattern_detected"] and r["status"] in ("breakout", "actionable"))


def test_evaluate_rejects_short_total_series():
    r = evaluate_power_play(_series([100, 101, 99, 102, 100]))
    assert r["pattern_detected"] is False
    assert r["reason"] == "base_too_short"


def test_evaluate_rejects_weak_flagpole_gain():
    # 깃대 상승률만 죽인다: 깃대를 +30%짜리로 교체(저점50→고점65)
    quiet = [50 + (i % 2) for i in range(20)]
    pole = [52, 55, 58, 60, 62, 63, 64, 65]
    flag = [64, 63, 62, 63, 64, 63, 62, 63, 64, 63]
    closes = quiet + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [500]*10)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "pole_gain_too_small"


def test_evaluate_rejects_weak_pole_volume():
    s = _clean_htf()
    # 깃대 거래량을 조용 구간과 동일하게(800) → 대량거래 조건 실패
    s["volumes"] = [800]*20 + [800]*8 + [500]*10
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "pole_volume_weak"


def test_evaluate_rejects_not_quiet_before_pole():
    # 폭등 직전 20일이 이미 +50% 상승(말기 베이스) → not_quiet_before_pole
    pre = [50 + i*1.3 for i in range(20)]   # 50→약74.7 (+49%)
    pole = [76, 84, 92, 100, 110, 120, 130, 150]   # 74.7→150 추가 폭등
    flag = [148, 146, 145, 144, 145, 146, 147, 146, 145, 144]
    closes = pre + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [500]*10)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "not_quiet_before_pole"


def test_evaluate_rejects_deep_flag():
    s = _clean_htf()
    # 깃발 저점을 깊게: 110고점 대비 -30% (77)까지 빠짐
    quiet = [50 + (i % 2) for i in range(20)]
    pole = [52, 58, 66, 75, 85, 95, 104, 110]
    flag = [105, 98, 90, 82, 77, 80, 85, 88, 90, 92]   # 깊은 조정 ~30%
    closes = quiet + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [500]*10)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "flag_too_deep"


def test_evaluate_rejects_too_long_flag():
    s = _clean_htf()
    quiet = [50 + (i % 2) for i in range(20)]
    pole = [52, 58, 66, 75, 85, 95, 104, 110]
    flag = [106]*35   # 6주(30일) 초과 횡보
    closes = quiet + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [500]*35)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "flag_too_long"


def test_evaluate_no_data():
    r = evaluate_power_play({"closes": [], "highs": [], "lows": [], "volumes": [], "dates": []})
    assert r["pattern_detected"] is False
    assert r["reason"] == "no_data"


def test_evaluate_rejects_short_flag():
    # gain/pole-volume/quiet 모두 통과, flag가 3일로 min_flag_days(8) 미달
    quiet = [50 + (i % 2) for i in range(20)]  # 50~51 횡보(조용)
    pole = [52, 58, 66, 75, 85, 95, 104, 110]  # +120% 깃대
    flag = [108, 106, 105]                       # 3일 → flag_too_short
    closes = quiet + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [500]*3)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "flag_too_short"


def test_evaluate_rejects_volume_not_drying():
    # gain/pole-volume/quiet/flag-length/flag-depth 모두 통과,
    # 깃발 최근 5일 거래량이 깃대 거래량보다 높아 volume_not_drying
    quiet = [50 + (i % 2) for i in range(20)]  # 50~51 횡보(조용)
    pole = [52, 58, 66, 75, 85, 95, 104, 110]  # +120% 깃대, 거래량 3000
    flag = [108] * 8                             # 8일 깃발, 깊이 ~2.8%, 거래량 5000
    closes = quiet + pole + flag
    s = _series(closes, vols=[800]*20 + [3000]*8 + [5000]*8)
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
    assert r["reason"] == "volume_not_drying"


def test_status_breakout_on_pivot_break_with_volume():
    s = _clean_htf()
    # 피벗(=기존 깃발 최고가 111.1) 위로 종가 돌파 + 대량거래 1일 추가.
    # evaluate_power_play의 pivot_price = max(highs) 이므로, 이 바의 high를
    # 기존 최고가(111.1)보다 낮게(111.0) 설정해 피벗이 이동하지 않도록 한다.
    # close > high 는 합성 테스트 데이터에서만 허용되는 의도적 값이다.
    s["closes"].append(112.0)   # 기존 pivot 111.1 초과
    s["highs"].append(111.0)    # 111.1보다 낮아야 기존 pole-top이 pivot 유지
    s["lows"].append(110.0)
    s["volumes"].append(6000)   # pole 평균(3000)의 1.4배(=4200) 이상
    s["dates"].append("dN")
    r = evaluate_power_play(s)
    assert r["status"] == "breakout"
    assert r["entry_ready"] == (r["pattern_detected"] and r["status"] in ("breakout", "actionable"))


def test_status_failed_on_flag_breakdown():
    s = _clean_htf()
    # 깃발 저점을 깊게 깨고 종가가 그 아래로 → failed
    s["closes"].append(70.0)
    s["highs"].append(72.0)
    s["lows"].append(69.0)
    s["volumes"].append(2000)
    s["dates"].append("dN")
    r = evaluate_power_play(s)
    assert r["status"] == "failed"


def test_status_actionable_near_pivot_with_dryup():
    s = _clean_htf()
    # 마지막 종가가 피벗(110) 0~5% 아래 + 거래량 마름 유지
    s["closes"].append(107.0)   # (110-107)/110 = 2.7%
    s["highs"].append(108.0)
    s["lows"].append(106.0)
    s["volumes"].append(500)
    s["dates"].append("dN")
    r = evaluate_power_play(s)
    assert r["status"] == "actionable"
    assert 0 <= r["pct_to_pivot"] <= 5

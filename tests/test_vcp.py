import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp import zigzag, find_contractions, evaluate_vcp


def test_zigzag_picks_alternating_pivots_from_peak():
    # 100에서 시작(고점) → 80(-20%)으로 하락 → 92(+15%)로 반등 → 85로 마감
    values = [100, 95, 88, 80, 84, 90, 92, 88, 85]
    piv = zigzag(values, pct=8.0)
    kinds = [k for _, _, k in piv]
    # 시작 고점, 저점, 고점 ... 교대
    assert kinds[0] == "high"
    assert piv[0][1] == 100
    # 80 저점이 잡혀야
    assert any(abs(p - 80) < 1e-9 and k == "low" for _, p, k in piv)
    # 교대성: 같은 종류 연속 없음
    assert all(kinds[i] != kinds[i+1] for i in range(len(kinds)-1))


def test_zigzag_ignores_subthreshold_noise():
    # 100 -> 97(-3%, 임계 미만) -> 101 : 잡음이라 중간 저점 안 잡힘
    values = [100, 97, 101, 99, 103]
    piv = zigzag(values, pct=8.0)
    lows = [p for _, p, k in piv if k == "low"]
    assert 97 not in lows


def test_find_contractions_high_to_low_depths():
    pivots = [
        (0, 100.0, "high"), (5, 75.0, "low"),
        (10, 90.0, "high"), (15, 78.0, "low"),
        (20, 86.0, "high"), (25, 80.0, "low"),
    ]
    depths = find_contractions(pivots)
    # (100-75)/100=25, (90-78)/90=13.33, (86-80)/86=6.98
    assert len(depths) == 3
    assert abs(depths[0] - 25.0) < 1e-6
    assert abs(depths[1] - 13.3333) < 1e-3
    assert abs(depths[2] - 6.9767) < 1e-3


def test_find_contractions_empty_when_no_pairs():
    assert find_contractions([(0, 100.0, "high")]) == []


# ---------------------------------------------------------------------------
# Task 3: evaluate_vcp tests
# ---------------------------------------------------------------------------

def _series_from_closes(closes):
    # highs/lows = 종가 ±0.5%, volumes 균일(거래량 마름 테스트는 개별 지정)
    highs = [c * 1.005 for c in closes]
    lows = [c * 0.995 for c in closes]
    vols = [1000] * len(closes)
    dates = [f"2026-01-{i+1:02d}" for i in range(len(closes))]
    return {"dates": dates, "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def _vcp_closes():
    # 고점100 → -25% → 회복 → -13% → 회복 → -7% (수축 수렴) → 피벗 근처
    seg = []
    seg += [100, 92, 84, 78, 75]          # -25%
    seg += [80, 86, 90]                    # 회복
    seg += [88, 84, 80, 78.3]              # -13% (90->78.3)
    seg += [82, 86, 88]                    # 회복
    seg += [87, 85, 83, 80.8]              # -8.18% (88->80.8, crosses 8% zigzag threshold)
    seg += [84, 86]                        # 피벗(88) 향해 접근
    return seg


def test_evaluate_vcp_detects_contracting_base():
    s = _series_from_closes(_vcp_closes())
    # 거래량 마름: 후반 1/3 거래량을 낮춤
    third = len(s["volumes"]) // 3
    s["volumes"] = [1500]*third + [1000]*third + [600]*(len(s["volumes"])-2*third)
    r = evaluate_vcp(s)
    assert r["vcp_detected"] is True
    assert 2 <= r["num_contractions"] <= 6
    # 수축이 대체로 얕아지는 수열
    assert r["contractions"][0] > r["contractions"][-1]
    assert r["pivot_price"] is not None


def test_evaluate_vcp_rejects_short_base():
    s = _series_from_closes([100, 98, 99, 97, 98])  # 5일 < min_base_days
    r = evaluate_vcp(s)
    assert r["vcp_detected"] is False
    assert r["reason"] == "base_too_short"


def test_evaluate_vcp_breakout_status():
    closes = _vcp_closes() + [89.0]   # 피벗(88) 위로 돌파
    s = _series_from_closes(closes)
    s["volumes"][-1] = 5000           # 돌파 거래량 급증
    r = evaluate_vcp(s)
    assert r["status"] == "breakout"

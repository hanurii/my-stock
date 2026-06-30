import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp import zigzag, find_contractions, evaluate_vcp, volume_ma, adaptive_zigzag, find_contraction_chain, _is_breakout


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


def test_volume_ma_trailing():
    assert volume_ma([10, 20, 30, 40, 50], window=3) == [10, 15, 20, 30, 40]


def test_adaptive_zigzag_catches_tight_swings_that_fixed8_misses():
    # 타이트 시계열(스윙 ~4%): 고정 8%는 수축을 못 잡고, 적응형은 잡는다
    closes = [100, 104, 100, 96, 100, 104, 100, 96, 100, 104]
    fixed = [k for _, _, k in zigzag(closes, 8.0)]
    # 시계열 평균 일간등락 ~4% → k=1.0이면 임계 ~4%(타이트 수축 포착).
    # (브리프 k=2.0은 임계 ~8%로 고정과 같아져 적응 우위를 못 보이므로 k=1.0 사용.)
    adapt = [k for _, _, k in adaptive_zigzag(closes, k=1.0)]
    # 고정 8%는 교대 스윙이 거의 없음(시작/끝 정도), 적응형은 더 많은 교대 스윙
    assert adapt.count("high") + adapt.count("low") > fixed.count("high") + fixed.count("low")


# ---------------------------------------------------------------------------
# Task 4: evaluate_vcp tests (adaptive_zigzag + find_contraction_chain + 50선 거래량 + _is_breakout)
# ---------------------------------------------------------------------------

def _vcp_series():
    """VCP: 2수축 수렴 베이스(25%→15%) + 우측 거래량 마름 + 피벗(92) 첫돌파 마지막 바.

    적응형 zigzag(k=4.0) 기본값 기준 임계≈12.2% → 수축1(25%)·수축2(15%) 모두 포착.
    베이스 우측 1/3 거래량 / MA50 최솟값 ≈ 0.35 < dry_max(0.7) 조건 충족.
    돌파 바: 93(종가) > 92(피벗), opens[-1]=91.5 양봉, vol=6000 ≥ MA50×1.4.
    """
    c1 = [100.0, 96.0, 91.0, 86.0, 82.0, 78.0, 75.5, 75.0]   # 수축1: 100→75 = -25%
    r1 = [78.0, 81.0, 84.0, 87.0, 89.0, 91.0, 92.0]            # 회복: →92(피벗)
    c2 = [90.0, 87.0, 84.0, 81.0, 79.0, 78.5, 78.2]            # 수축2: 92→78.2 ≈ -15%
    r2 = [81.0, 84.0, 87.0, 90.0, 91.5]                         # 회복: 피벗(92) 아래
    bo = [93.0]                                                   # 돌파 바: 92 첫돌파

    closes = c1 + r1 + c2 + r2 + bo   # 총 28 봉
    n = len(closes)
    opens = [c * 0.99 for c in closes]
    opens[-1] = 91.5                   # 돌파 바 시가: 피벗 아래 → 양봉 확인
    highs = [c * 1.01 for c in closes]
    lows = [c * 0.99 for c in closes]
    # 거래량: 초반 1200 → 회복1 800 → 수축2 600 → 우측(r2) 300(마름) → 돌파 6000
    vols = ([1200] * len(c1) + [800] * len(r1) + [600] * len(c2)
            + [300] * len(r2) + [6000] * len(bo))
    assert len(vols) == n
    dates = [f"2026-01-{i+1:02d}" for i in range(n)]
    return {"dates": dates, "closes": closes, "opens": opens,
            "highs": highs, "lows": lows, "volumes": vols}


def test_evaluate_vcp_recognizes_and_breaks_out():
    r = evaluate_vcp(_vcp_series())
    assert r["vcp_detected"] is True
    assert r["pivot_price"] is not None
    assert r["status"] == "breakout"
    assert r["entry_ready"] is True


def test_evaluate_vcp_short_base_rejected():
    s = {"dates": ["d"]*5, "closes": [100, 99, 100, 98, 99], "opens": [100]*5,
         "highs": [101]*5, "lows": [98]*5, "volumes": [1]*5}
    r = evaluate_vcp(s)
    assert r["vcp_detected"] is False
    assert r["reason"] in ("base_too_short", "no_contraction_chain")


def test_find_contraction_chain_pivot_is_last_high_and_shrinks():
    # 수축 깊이 25% → 13% → 7% (수렴), 마지막 수축 고점=피벗
    swings = [
        (0, 100.0, "high"), (5, 75.0, "low"),
        (10, 90.0, "high"), (15, 78.3, "low"),
        (20, 88.0, "high"), (25, 81.8, "low"),
    ]
    r = find_contraction_chain(swings, tol=1.15)
    assert r["count"] == 3
    assert r["base_start"] == 0          # 첫 수축 고점 인덱스
    assert r["pivot"] == 88.0            # 마지막 수축 고점 = 최소저항선
    assert r["depths"][0] > r["depths"][-1]


def test_find_contraction_chain_none_without_pairs():
    assert find_contraction_chain([(0, 100.0, "high")], tol=1.15) is None


# ---------------------------------------------------------------------------
# Task 3: _is_breakout tests
# ---------------------------------------------------------------------------

def test_is_breakout_clean_true():
    closes = [95.0, 104.0]; opens = [96.0, 100.0]; vols = [100.0, 300.0]; ma50 = [150.0, 150.0]
    p = {"breakout_vol_mult": 1.4, "near_pivot_pct": 5.0}
    # 전일95≤100, 당일104>100(첫돌파), 양봉(104>100), vol300≥150×1.4=210, 연장4%≤5
    assert _is_breakout(closes, opens, vols, ma50, pivot=100.0, p=p) is True


def test_is_breakout_quiet_volume_false():
    closes = [95.0, 104.0]; opens = [96.0, 100.0]; vols = [100.0, 120.0]; ma50 = [150.0, 150.0]
    p = {"breakout_vol_mult": 1.4, "near_pivot_pct": 5.0}
    # 거래량 120 < 210 → 조용한 돌파라 False
    assert _is_breakout(closes, opens, vols, ma50, pivot=100.0, p=p) is False


def test_is_breakout_extended_false():
    closes = [108.0, 120.0]; opens = [107.0, 109.0]; vols = [100.0, 300.0]; ma50 = [150.0, 150.0]
    p = {"breakout_vol_mult": 1.4, "near_pivot_pct": 5.0}
    # 전일108>100이라 첫돌파 아님(이미 위) → False
    assert _is_breakout(closes, opens, vols, ma50, pivot=100.0, p=p) is False

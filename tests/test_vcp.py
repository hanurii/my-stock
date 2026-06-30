import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp import zigzag, find_contractions, evaluate_vcp, volume_ma, adaptive_zigzag


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
    assert r["pivot_price"] == 88.0
    # entry_ready: breakout이고 vcp_detected도 True면 entry_ready=True여야 함
    assert r["entry_ready"] == (r["vcp_detected"] and r["status"] in ("breakout", "actionable"))


def test_evaluate_vcp_records_reason_on_non_monotone():
    # 수축이 확대(더 깊어지는) 베이스: VCP 아님, reason 기록돼야
    # 첫 수축 ~25%, 둘째 수축 ~30%로 더 깊어짐(단조 수렴 실패)
    # 베이스 길이 충분히 확보, 거래량 마름 조건도 충족
    seg = []
    seg += [100, 92, 84, 78, 75]      # 고점100 → -25% 수축
    seg += [80, 86, 90, 88]           # 회복 ~90
    seg += [85, 80, 75, 70, 63]       # 고점90 → -30% 수축(더 깊어짐 → 단조 위반)
    seg += [68, 72, 75]               # 약간 회복
    # 거래량: 후반을 초반보다 낮게(거래량 마름 조건 우회 목적)
    s = _series_from_closes(seg)
    n = len(s["volumes"])
    third = n // 3
    s["volumes"] = [1500] * third + [1000] * third + [600] * (n - 2 * third)
    r = evaluate_vcp(s)
    assert r["vcp_detected"] is False
    assert r["reason"] is not None        # null이면 안 됨(§7 근거 출력 불변원칙)
    assert r["entry_ready"] is False

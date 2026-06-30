import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp import (
    zigzag, find_contractions, evaluate_vcp, volume_ma,
    adaptive_zigzag, find_contraction_chain, _is_breakout, detect_final_coil,
)


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
    """VCP: 2수축 수렴(25%→15%) + 돌파 직전 '타이트+마른 코일'(94.5~96, 피벗 96) + 첫돌파 바.

    인식: 적응형 ZigZag로 수축1(100→75=-25%)·수축2(92→78.2≈-15%) 포착(count2·net 수렴).
    피벗 = detect_final_coil 의 코일 고점 = 96(돌파 바 직전 타이트 구간 종가 최고치).
    돌파 바: 99(종가) > 96(피벗) 첫돌파, opens[-1]=95(<피벗, 양봉·근접), vol=6000 ≥ MA50×1.4.
    코일·r2 거래량은 마름(300) → coil_dry_mean ≪ 0.9.
    """
    c1   = [100.0, 96.0, 91.0, 86.0, 82.0, 78.0, 75.5, 75.0]   # 수축1: 100→75 = -25% (천장 100)
    r1   = [78.0, 81.0, 84.0, 87.0, 89.0, 91.0, 92.0]           # 회복 →92
    c2   = [90.0, 87.0, 84.0, 81.0, 79.0, 78.5, 78.2]           # 수축2: 92→78.2 ≈ -15%
    r2   = [82.0, 87.0, 92.0, 95.0]                              # 회복: 코일 레벨로 복귀
    coil = [95.5, 94.5, 95.0, 96.0, 95.5, 96.0]                 # 타이트 코일: 범위 1.56%, 고점=피벗 96
    bo   = [99.0]                                                # 돌파 바: 96 첫돌파

    closes = c1 + r1 + c2 + r2 + coil + bo
    n = len(closes)
    opens = [c * 0.99 for c in closes]
    opens[-1] = 95.0                  # 돌파 바 시가: 피벗(96) 아래 → 양봉·근접 확인
    highs = [c * 1.01 for c in closes]
    lows = [c * 0.99 for c in closes]
    # 거래량: 초반/회복 정상 → r2+coil 마름(300) → 돌파 6000
    vols = ([1200] * len(c1) + [800] * len(r1) + [600] * len(c2)
            + [300] * (len(r2) + len(coil)) + [6000] * len(bo))
    assert len(vols) == n
    dates = [f"2026-01-{i+1:02d}" for i in range(n)]
    return {"dates": dates, "closes": closes, "opens": opens,
            "highs": highs, "lows": lows, "volumes": vols}


def test_evaluate_vcp_recognizes_and_breaks_out():
    r = evaluate_vcp(_vcp_series())
    assert r["vcp_detected"] is True
    assert r["pivot_price"] == 96.0          # 피벗 = 최종 타이트 코일 고점
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


# ---------------------------------------------------------------------------
# Task-5 fix regression: 첫돌파 가드 복원 (안정 피벗 = 수축 고점)
# ---------------------------------------------------------------------------

def test_evaluate_vcp_extended_not_breakout():
    """베이스 천장(100) 미회복 연장 구간 → 첫돌파 가드 → status != breakout.

    PRODUCTION 경로(evaluate_vcp) 직접 구동 테스트.
    피벗 = 횡보 천장 = max(closes[base_start:-1]) = 100 (수축1 고점 = 베이스 최고가, 안정 레벨).
    회복이 수축2 고점(92)은 넘어 96까지 올라왔지만 베이스 천장(100)은 아직 못 넘은 상태.
    closes[-2]=95 < 100(천장) 이고 closes[-1]=96 < 100 → 첫돌파 조건 False → breakout 아님.
    러닝맥스(pivot=max(closes[last_lo:-1])=95) 코드에서는 closes[-2]=95<=95가 항상 참이라
    breakout으로 잘못 분류됨 — 이 테스트가 그 회귀를 고정한다.
    # (코일 로직) 연장 회복 구간은 거래량을 동반(안 마름)하므로 detect_final_coil=None
    # → 인식 실패(reason=no_tight_coil) → breakout 아님. '마른 코일 부재'가 가드.
    """
    c1 = [100.0, 96.0, 91.0, 86.0, 82.0, 78.0, 75.5, 75.0]   # 수축1: 100→75 = -25% (천장=100)
    r1 = [78.0, 81.0, 84.0, 87.0, 89.0, 91.0, 92.0]            # 회복: →92
    c2 = [90.0, 87.0, 84.0, 81.0, 79.0, 78.5, 78.2]            # 수축2: 92→78.2 ≈ -15%
    # 회복이 수축2 고점(92)은 넘었지만 베이스 천장(100)은 아직 못 넘은 '연장' 구간.
    # pivot=천장=100, closes[-1]=96 < 100 → 첫돌파 아님.
    r2_ext = [81.0, 84.0, 87.0, 90.0, 92.5, 94.0, 95.0, 96.0]
    closes = c1 + r1 + c2 + r2_ext
    n = len(closes)
    opens = [c * 0.99 for c in closes]
    highs = [c * 1.01 for c in closes]
    lows  = [c * 0.99 for c in closes]
    # 마지막 바 거래량 6000(터짐) — volume 조건이 통과해도 첫돌파 가드가 막아야 함
    vols  = ([1200] * len(c1) + [800] * len(r1) + [600] * len(c2)
             + [1500] * (len(r2_ext) - 1) + [6000])
    assert len(vols) == n
    dates = [f"2026-01-{i+1:02d}" for i in range(n)]
    series = {"dates": dates, "closes": closes, "opens": opens,
              "highs": highs, "lows": lows, "volumes": vols}
    r = evaluate_vcp(series)
    # 수축 고점(92) 위 전일 종가(95) → 첫돌파 아님 → breakout 금지
    assert r["status"] != "breakout", (
        f"연장 종목이 breakout으로 잘못 분류됨: status={r['status']}, pivot={r['pivot_price']}"
    )


# ---------------------------------------------------------------------------
# Task-6 fix regression: 수축 구간 천장 고정 (above-ceiling 연장 오탐 차단)
# ---------------------------------------------------------------------------

def test_evaluate_vcp_above_ceiling_extended_not_breakout():
    """수축 구간 천장(100) 위로 수일간 연장된 종목 → 첫돌파 가드 → status != breakout.

    수정된 피벗: ceiling_seg = closes[bs:last_lo_idx+1] = 수축 구간만.
    수축 구간 최고가 = 100(c1 시작 종가) → 피벗 = 100(고정).

    천장 위 연장 구간(extended: 101.5→107.5)이 포함된 후 마지막 바가 신고가(109, 대량거래)여도:
      closes[-2] = 107.5 > pivot(100) → 첫돌파 조건(closes[i-1]<=pivot) False → NOT breakout.

    구 코드(ceiling_seg=closes[bs:n-1]): max(0..107.5) = 107.5 → pivot 107.5.
      closes[-2] = 107.5 ≤ 107.5 항상 참(no-op) → breakout 오탐.
    이 테스트가 그 회귀를 고정한다(above-ceiling guard).
    # (코일 로직) 천장 위 연장은 거래량 동반(안 마름) → detect_final_coil=None
    # → 인식 실패 → breakout/entry_ready 아님.
    """
    c1 = [100.0, 96.0, 91.0, 86.0, 82.0, 78.0, 75.5, 75.0]   # 수축1: 100→75 = -25%
    r1 = [78.0, 81.0, 84.0, 87.0, 89.0, 91.0, 92.0]            # 회복: →92
    c2 = [90.0, 87.0, 84.0, 81.0, 79.0, 78.5, 78.2]            # 수축2: 92→78.2 ≈ -15%
    r2 = [81.0, 84.0, 87.0, 90.0, 91.5]                         # 회복: 천장 아래
    # 천장(100) 위 수일 연장: 수축 구간 피벗(100)을 이미 넘어 며칠 경과
    extended = [101.5, 103.0, 104.5, 106.0, 107.5]
    bo_ext = [109.0]                                             # 신고가 + 대량거래

    closes = c1 + r1 + c2 + r2 + extended + bo_ext
    n = len(closes)
    opens = [c * 0.99 for c in closes]
    opens[-1] = 108.0   # 시가도 천장 위 (near_pivot 도 실패하지만 첫돌파 가드가 1차)
    highs = [c * 1.01 for c in closes]
    lows  = [c * 0.99 for c in closes]
    vols  = ([1200] * len(c1) + [800] * len(r1) + [600] * len(c2)
             + [300] * len(r2) + [1500] * len(extended) + [6000] * len(bo_ext))
    assert len(vols) == n
    dates = [f"2026-01-{i+1:02d}" for i in range(n)]
    series = {"dates": dates, "closes": closes, "opens": opens,
              "highs": highs, "lows": lows, "volumes": vols}
    r = evaluate_vcp(series)
    assert r["status"] != "breakout", (
        f"천장 위 연장 종목이 breakout으로 오탐: status={r['status']}, pivot={r['pivot_price']}"
    )
    assert r["entry_ready"] is False, (
        f"천장 위 연장 종목이 entry_ready=True: pivot={r['pivot_price']}"
    )


# ---------------------------------------------------------------------------
# Task 1: detect_final_coil 단위 테스트
# ---------------------------------------------------------------------------

# DEFAULT 코일 파라미터(테스트 고정값) — 함수에 명시 전달해 결합도 낮춤
_CP = {"coil_tight_pct": 12.0, "coil_min_days": 3, "coil_max_days": 25, "coil_dry_max": 0.9}


def test_detect_final_coil_tight_and_dry_returns_pivot():
    # 마지막 6봉이 타이트 코일(94.5~96, 범위 1.56%), 거래량 마름(300 vs ma50 1000=0.3).
    # 이전 구간은 변동폭 큼(70~96) → 코일 경계가 거기서 끊김. 현재(돌파) 바 = 인덱스 -1.
    closes = [70, 78, 85, 90,  95.5, 94.5, 95.0, 96.0, 95.5, 96.0,  99.0]
    vols   = [900, 900, 900, 900,  300, 300, 300, 300, 300, 300,  6000]
    ma50   = [1000] * len(closes)
    highs  = [c * 1.01 for c in closes]
    lows   = [c * 0.99 for c in closes]
    b1 = len(closes) - 1
    coil = detect_final_coil(highs, lows, closes, vols, ma50, b1, _CP)
    assert coil is not None
    assert coil["pivot"] == 96.0            # 코일 내 종가 최고치 = 저항 천장
    assert coil["coil_end"] == b1 - 1       # 현재(돌파) 바는 코일에서 제외
    assert coil["coil_len"] >= 3
    assert coil["coil_dry_mean"] <= 0.9


def test_detect_final_coil_wide_range_returns_none():
    # 직전 구간이 계속 넓게 움직임(타이트 코일 없음) → None.
    closes = [70, 80, 72, 85, 75, 90, 78, 95, 80, 99]
    vols   = [300] * len(closes)
    ma50   = [1000] * len(closes)
    highs  = [c * 1.01 for c in closes]
    lows   = [c * 0.99 for c in closes]
    coil = detect_final_coil(highs, lows, closes, vols, ma50, len(closes) - 1, _CP)
    assert coil is None


def test_detect_final_coil_not_dry_returns_none():
    # 가격은 타이트하지만 거래량이 안 마름(1500 vs ma50 1000 = 1.5 > 0.9) → None.
    closes = [70, 78, 85, 90,  95.5, 94.5, 95.0, 96.0, 95.5, 96.0,  99.0]
    vols   = [900, 900, 900, 900,  1500, 1500, 1500, 1500, 1500, 1500,  6000]
    ma50   = [1000] * len(closes)
    highs  = [c * 1.01 for c in closes]
    lows   = [c * 0.99 for c in closes]
    coil = detect_final_coil(highs, lows, closes, vols, ma50, len(closes) - 1, _CP)
    assert coil is None


def test_detect_final_coil_too_short_returns_none():
    # 타이트+마른 구간이 2봉뿐(coil_min_days=3 미만) → None.
    closes = [70, 80, 60, 84,  95.5, 96.0,  99.0]   # 직전 95.5,96 두 봉만 타이트, 84는 범위 12.5%로 break
    vols   = [300] * len(closes)
    ma50   = [1000] * len(closes)
    highs  = [c * 1.01 for c in closes]
    lows   = [c * 0.99 for c in closes]
    coil = detect_final_coil(highs, lows, closes, vols, ma50, len(closes) - 1, _CP)
    assert coil is None

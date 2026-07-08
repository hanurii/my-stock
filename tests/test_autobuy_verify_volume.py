import sys, pathlib, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.verify_volume import observe_sweep, _elapsed_frac

CFG = {"SLOTS": 10, "VOL_PACE_MIN": 1.5, "CHASE_MAX_PCT": 3.0}

def _cand(code, name="종목", pivot=1000.0):
    return {"code": code, "name": name, "pivot": pivot, "pattern": "VCP"}

def _q(current, acml):
    return {"current": current, "acml_vol": acml}

def test_elapsed_frac():
    d = datetime.datetime
    assert _elapsed_frac(d(2026, 7, 8, 9, 0, 0)) <= 1e-5 + 1e-6      # 개장≈0
    assert abs(_elapsed_frac(d(2026, 7, 8, 15, 30, 0)) - 1.0) < 1e-9  # 마감=1.0
    assert 0.2 < _elapsed_frac(d(2026, 7, 8, 10, 20, 0)) < 0.25       # 10:20≈0.205

def test_buy_on_pivot_cross_with_volume():
    # 피벗1000, avg50=1000, ef=0.1 → pace=acml/(1000*0.1). acml=300 → pace 3.0≥1.5, 가격1010(+1%,+3%이내) → 매수
    cands = [_cand("A")]
    held, skip = set(), set()
    rows, buys = observe_sweep({"A": _q(1010, 300)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1)
    assert len(buys) == 1 and buys[0]["code"] == "A"
    assert "A" in held
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "buy"

def test_low_volume_no_buy():
    cands = [_cand("A")]
    held, skip = set(), set()
    rows, buys = observe_sweep({"A": _q(1010, 50)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1)  # pace 0.5
    assert buys == [] and "A" not in held
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "low_volume"

def test_extended_over_3pct_added_to_skip():
    cands = [_cand("A")]
    held, skip = set(), set()
    rows, buys = observe_sweep({"A": _q(1040, 500)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1)  # +4%
    assert buys == [] and "A" in skip
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "extended"

def test_extended_skip_is_sticky_next_sweep():
    # 한 번 extended로 skip되면, 다음 스윕에 가격이 +3% 이내로 돌아와도 계속 extended 표시·미매수
    cands = [_cand("A")]
    held, skip = set(), set()
    observe_sweep({"A": _q(1040, 500)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1)   # skip 편입
    rows, buys = observe_sweep({"A": _q(1010, 500)}, cands, {"A": 1000.0}, held, skip, CFG, 0.2)
    assert buys == []
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "extended"

def test_below_pivot():
    cands = [_cand("A")]
    rows, buys = observe_sweep({"A": _q(970, 500)}, cands, {"A": 1000.0}, set(), set(), CFG, 0.1)  # -3%
    assert buys == []
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "below_pivot"

def test_already_held_skipped():
    cands = [_cand("A")]
    held = {"A"}
    rows, buys = observe_sweep({"A": _q(1010, 300)}, cands, {"A": 1000.0}, held, set(), CFG, 0.1)
    assert buys == []
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "already_held"

def test_no_quote_row():
    cands = [_cand("A")]
    rows, buys = observe_sweep({}, cands, {"A": 1000.0}, set(), set(), CFG, 0.1)  # 조회 실패
    assert buys == []
    r = [r for r in rows if r["code"] == "A"][0]
    assert r["why"] == "no_quote" and r["price"] is None

def test_slot_limit_pace_priority():
    cfg = {**CFG, "SLOTS": 1}
    cands = [_cand("A"), _cand("B")]
    held, skip = set(), set()
    # A pace=acml/(1000*0.1): acml 200 → 2.0. B acml 600 → 6.0(우선). 둘 다 +1%
    rows, buys = observe_sweep({"A": _q(1010, 200), "B": _q(1010, 600)}, cands,
                               {"A": 1000.0, "B": 1000.0}, held, skip, cfg, 0.1)
    assert len(buys) == 1 and buys[0]["code"] == "B"      # pace 높은 B만
    assert held == {"B"}
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "no_slot"

def test_outside_buy_window_no_commit():
    # in_buy_window=False면 판정은 보이되 실제 매수(held 편입)는 안 함
    cands = [_cand("A")]
    held, skip = set(), set()
    rows, buys = observe_sweep({"A": _q(1010, 300)}, cands, {"A": 1000.0}, held, skip, CFG, 0.1,
                               in_buy_window=False)
    assert buys == [] and "A" not in held
    assert [r for r in rows if r["code"] == "A"][0]["why"] == "buy"   # 조건은 충족(창밖이라 미체결)

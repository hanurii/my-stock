import sys, pathlib, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.verify_volume import observe_sweep, _elapsed_frac, _in_buy_window

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

from autobuy.verify_volume import _fmt_block

def test_fmt_block_sections_and_pace_filter():
    rows = [
        {"code": "000660", "name": "SK하이닉스", "price": 183500, "pivot": 182000,
         "pct": 0.82, "pace": 2.13, "why": "buy"},
        {"code": "042700", "name": "한미반도체", "price": 41500, "pivot": 40000,
         "pct": 3.75, "pace": 1.8, "why": "extended"},                      # 익스텐디드 → 별도 섹션
        {"code": "005930", "name": "삼성전자", "price": 70000, "pivot": 71000,
         "pct": -1.4, "pace": 0.5, "why": "below_pivot"},                   # pace<0.8 → 숨김
        {"code": "006400", "name": "삼성SDI", "price": None, "pivot": 41000,
         "pct": None, "pace": None, "why": "no_quote"},                     # 조회실패 → 숨김
    ]
    buys = [{"code": "000660", "name": "SK하이닉스", "price": 183500, "pace": 2.1}]
    out = _fmt_block("14:03:20", 0.77, 1, 10, 4, "하락추세(지수<20MA)", rows, buys, True)
    assert "14:03:20" in out and "1/10" in out and "하락추세" in out
    assert "★매수" in out and "000660" in out            # 매수 발생
    assert "익스텐디드" in out and "한미반도체" in out    # 익스텐디드 별도 분류
    assert "삼성전자" not in out                          # pace<0.8 숨김
    assert "삼성SDI" not in out                           # 조회실패 숨김
    assert "2종목 숨김" in out                            # 숨김 개수 요약

def test_fmt_block_outside_window_marks_header():
    out = _fmt_block("15:25:00", 0.99, 0, 10, 0, "상승추세", [], [], False)
    assert "매수창" in out               # 창 밖 표기

def test_in_buy_window_upper_bound_exclusive():
    cfg = {"MARKET_OPEN": "0905", "NEW_BUY_UNTIL": "1520"}
    assert _in_buy_window("0905", cfg) is True      # 하한 포함
    assert _in_buy_window("1519", cfg) is True
    assert _in_buy_window("1520", cfg) is False      # 상한 배타 — 실전 봇과 동일
    assert _in_buy_window("0904", cfg) is False      # 개장 전

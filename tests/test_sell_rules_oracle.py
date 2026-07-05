"""실데이터 오라클 회귀 — 미너비니 책 예시로 규칙③·⑥ 보정 검증.
픽스처: Tiingo 상폐주 일봉 슬라이스(tests/fixtures/oracle_*.json)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib.sell_rules import evaluate_holding

FIX = Path(__file__).resolve().parent / "fixtures"


def _load(name):
    return json.loads((FIX / f"oracle_{name}.json").read_text(encoding="utf-8"))


def test_wage_lower_lows_and_breakout_failure():
    # WAGE: 03-18 극저거래량 돌파(피벗≈63) → 03-25~27 거래량 붙은 저점경신 + 붕괴
    s = _load("wage")
    r = evaluate_holding(s, "2014-03-18", 63.68, -20.0, pivot_price=63.0)
    assert r["breakout_date_estimated"] is False
    assert r["rules"][2]["status"] == "violation"   # consecutive_lower_lows
    assert r["rules"][5]["status"] == "violation"   # breakout_failure(거래량 동반)
    assert r["rules"][0]["status"] == "violation"   # low_volume_breakout(0.45배)


def test_outr_breakout_failure_volume_asymmetry():
    # OUTR: 03-04 돌파(피벗≈72.7) → 03-06·07 대량거래 반전(비대칭)
    s = _load("outr")
    r = evaluate_holding(s, "2014-03-04", 73.06, -20.0, pivot_price=72.73)
    assert r["breakout_date_estimated"] is False
    assert r["rules"][5]["status"] == "violation"   # breakout_failure
    assert "거래량 동반" in r["rules"][5]["detail"]


def test_mvp_real_winner_qualifies():
    # 실데이터 확신 테스트 — 국내 종목 실 돌파 후 15일 창이 M·V·P 전부 충족하는지.
    # 없으면 skip(합성 테스트 Task 3이 정확성 게이트, 이 테스트는 확신 보강용).
    p = FIX / "oracle_mvp_winner.json"
    if not p.exists():
        import pytest
        pytest.skip("MVP winner fixture 미생성(캐시 부재) — 합성 테스트로 커버")
    from canslim_lib.sell_rules import evaluate_mvp
    d = json.loads(p.read_text(encoding="utf-8"))
    r = evaluate_mvp(d, d["bi_in_fixture"])
    assert r["status"] == "yes"
    assert r["m"]["ok"] and r["v"]["ok"] and r["p"]["ok"]

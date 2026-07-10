import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib import liveness


def _series(vols, dates=None):
    n = len(vols)
    dates = dates or [f"2026-07-{i+1:02d}" for i in range(n)]
    return {"dates": dates, "volumes": vols, "closes": [100.0] * n}


def test_is_halted_recent_zero_volume():
    # 최근 5일 연속 거래량 0 → 거래정지
    assert liveness.is_halted(_series([10, 20, 0, 0, 0, 0, 0])) is True


def test_active_stock_not_halted():
    assert liveness.is_halted(_series([10, 0, 20, 0, 30, 0, 40])) is False


def test_too_short_series_not_halted():
    # 데이터가 days 미만이면 판정 불가 → False
    assert liveness.is_halted(_series([0, 0])) is False


def test_none_series_not_halted():
    assert liveness.is_halted(None) is False


def test_asof_truncates_before_judging():
    # asof 이후는 얼어붙었지만, asof 시점엔 활발히 거래 → 정지 아님
    s = _series([50, 60, 70, 40, 80, 0, 0, 0, 0, 0])
    assert liveness.is_halted(s, asof="2026-07-05") is False


def test_load_excluded_codes_object_and_string(tmp_path):
    p = tmp_path / "excluded.json"
    p.write_text(json.dumps({"codes": [{"code": "057050"}, "12510"]}),
                 encoding="utf-8")
    codes = liveness.load_excluded_codes(p)
    assert codes == {"057050", "012510"}  # zfill 6자리 정규화


def test_load_excluded_missing_file_is_empty(tmp_path):
    assert liveness.load_excluded_codes(tmp_path / "nope.json") == set()


def test_filter_live_universe_drops_halted_and_excluded():
    universe = [
        {"code": "000001", "name": "활성"},
        {"code": "000002", "name": "정지"},
        {"code": "057050", "name": "수동제외"},
    ]
    series = {
        "000001": _series([10, 20, 30, 40, 50, 60]),
        "000002": _series([10, 0, 0, 0, 0, 0]),
        "057050": _series([10, 20, 30, 40, 50, 60]),  # 거래는 있으나 수동 제외
    }
    kept, dropped = liveness.filter_live_universe(
        universe, lambda c: series.get(c), excluded={"057050"})
    assert [k["code"] for k in kept] == ["000001"]
    reasons = {d["code"]: d["reason"] for d in dropped}
    assert reasons == {"000002": "halted", "057050": "excluded"}

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib import us_matrix
import us_loader


def test_trim_keeps_last_n_bars():
    s = {"dates": [f"2026-01-{i:02d}" for i in range(1, 21)],
         "opens": list(range(20)), "highs": list(range(20)),
         "lows": list(range(20)), "closes": list(range(20)),
         "volumes": list(range(20))}
    out = us_matrix.trim_series(s, 5)
    assert out["dates"] == ["2026-01-16", "2026-01-17", "2026-01-18",
                            "2026-01-19", "2026-01-20"]
    assert out["closes"] == [15, 16, 17, 18, 19]
    assert len(out["timestamps"]) == 5


def test_trim_keeps_short_series_whole():
    s = {"dates": ["2026-01-01", "2026-01-02"], "opens": [1, 2], "highs": [1, 2],
         "lows": [1, 2], "closes": [1, 2], "volumes": [1, 2]}
    out = us_matrix.trim_series(s, 310)
    assert len(out["dates"]) == 2


def test_get_series_returns_none_for_unknown(tmp_path):
    p = tmp_path / "base.json"
    p.write_text('{"asof":"2026-09-09","trim":310,"series":{}}', encoding="utf-8")
    us_matrix.load_base(p)
    assert us_matrix.get_series("NOSUCH") is None


def test_get_series_has_all_consumer_keys(tmp_path):
    p = tmp_path / "base.json"
    s = {"dates": ["2026-09-08", "2026-09-09"], "opens": [1.0, 2.0],
         "highs": [1.0, 2.0], "lows": [1.0, 2.0], "closes": [1.0, 2.0],
         "volumes": [10.0, 20.0], "timestamps": [1, 2]}
    p.write_text(json.dumps({"asof": "2026-09-09", "trim": 310,
                             "series": {"AAPL": s}}), encoding="utf-8")
    us_matrix.load_base(p)
    got = us_matrix.get_series("AAPL")
    for k in ("dates", "opens", "highs", "lows", "closes", "volumes", "timestamps"):
        assert k in got, f"소비자가 읽는 키 {k} 가 없다"


def test_get_series_returns_none_if_file_missing(tmp_path, monkeypatch):
    # _BASE를 None으로 리셋하고, 존재하지 않는 경로를 BASE_PATH로 설정한 후
    # get_series를 부르면 FileNotFoundError가 처리되어 None을 반환
    # ★ TAIL_PATH 도 함께 막는다 — get_series 의 게으른 로드가 load_latest() 라
    #   합본이 «실제로» 있으면 그것을 읽어 이 시험이 실제 디스크 상태에 기댄다.
    nonexistent = tmp_path / "subdir" / "missing.json"
    monkeypatch.setattr(us_matrix, "BASE_PATH", nonexistent)
    monkeypatch.setattr(us_matrix, "TAIL_PATH", tmp_path / "subdir" / "no-tail.json")
    us_matrix._BASE = None
    result = us_matrix.get_series("DUMMY")
    assert result is None


def _block_batch(monkeypatch):
    """묶음 길을 막아 «따로 묻는» 길만 남긴다 (2026-09-11).

    check_splits 가 종목마다 따로 묻던 것을 `yf.download(..., actions=True)`
    묶음으로 바뀌었다. 아래 시험들은 «묶음이 못 본 종목을 다시 묻는» 자리의
    계약을 본다 — 묶음을 안 막으면 진짜 야후에 나간다.
    묶음 길 자체는 tests/test_us_seam_check_splits.py 가 본다.
    """
    import us_seam

    def boom(*a, **k):
        raise RuntimeError("묶음 길은 이 시험에서 막았다")

    monkeypatch.setattr(us_seam.yf, "download", boom)


def test_check_splits_empty_window_returns_empty(monkeypatch):
    import us_seam

    class FakeTicker:
        def __init__(self, code): pass
        @property
        def splits(self):
            import pandas as pd
            return pd.Series(dtype=float)

    _block_batch(monkeypatch)
    monkeypatch.setattr(us_seam.yf, "Ticker", FakeTicker)
    got = us_seam.check_splits(["AAPL"], "2026-09-09", "2026-09-10")
    assert got == {"splits": [], "failed": []}


def test_check_splits_finds_one(monkeypatch):
    import us_seam
    import pandas as pd

    class FakeTicker:
        def __init__(self, code): pass
        @property
        def splits(self):
            return pd.Series([2.0], index=pd.to_datetime(["2026-09-10"]))

    _block_batch(monkeypatch)
    monkeypatch.setattr(us_seam.yf, "Ticker", FakeTicker)
    got = us_seam.check_splits(["APH"], "2026-09-09", "2026-09-11")
    assert got == {"splits": [{"code": "APH", "date": "2026-09-10", "ratio": 2.0}], "failed": []}


def test_check_splits_includes_until_boundary(monkeypatch):
    """닫힌 구간이다(2026-09-11 수정): until 당일 분할도 잡혀야 한다.

    fetch_tail 은 end 없이 오늘(=until) 봉까지 붙이므로, until 당일 분할을
    검사에서 빼면 검사 없이 그대로 붙는 「관문이 자기가 지키는 자료보다
    좁다」 결함이 된다. 예전 이름은 test_check_splits_excludes_until_boundary
    였고 반열린 구간([since, until))을 검증했다 — 그 동작 자체가 결함이었다.
    """
    import us_seam
    import pandas as pd

    class FakeTicker:
        def __init__(self, code): pass
        @property
        def splits(self):
            return pd.Series([2.0], index=pd.to_datetime(["2026-09-11"]))

    _block_batch(monkeypatch)
    monkeypatch.setattr(us_seam.yf, "Ticker", FakeTicker)
    got = us_seam.check_splits(["APH"], "2026-09-09", "2026-09-11")
    assert got == {"splits": [{"code": "APH", "date": "2026-09-11", "ratio": 2.0}], "failed": []}


def test_check_splits_includes_since_boundary(monkeypatch):
    import us_seam
    import pandas as pd

    class FakeTicker:
        def __init__(self, code): pass
        @property
        def splits(self):
            return pd.Series([2.0], index=pd.to_datetime(["2026-09-09"]))

    _block_batch(monkeypatch)
    monkeypatch.setattr(us_seam.yf, "Ticker", FakeTicker)
    got = us_seam.check_splits(["APH"], "2026-09-09", "2026-09-11")
    assert got == {"splits": [{"code": "APH", "date": "2026-09-09", "ratio": 2.0}], "failed": []}


def test_check_splits_handles_exception(monkeypatch):
    import us_seam

    class FakeTickerWithException:
        def __init__(self, code):
            self.code = code

        @property
        def splits(self):
            raise RuntimeError(f"네트워크 오류: {self.code}")

    _block_batch(monkeypatch)
    monkeypatch.setattr(us_seam.yf, "Ticker", FakeTickerWithException)
    got = us_seam.check_splits(["FAIL", "ALSO_FAIL"], "2026-09-09", "2026-09-11")
    assert got == {"splits": [], "failed": ["FAIL", "ALSO_FAIL"]}


def test_attach_appends_and_keeps_base_on_overlap():
    import us_seam
    base = {"series": {"AAPL": {
        "dates": ["2026-09-08", "2026-09-09"], "opens": [1.0, 2.0],
        "highs": [1.0, 2.0], "lows": [1.0, 2.0], "closes": [1.0, 2.0],
        "volumes": [10.0, 20.0], "timestamps": [1, 2]}}}
    tail = {"AAPL": {
        "dates": ["2026-09-09", "2026-09-10"], "opens": [99.0, 3.0],
        "highs": [99.0, 3.0], "lows": [99.0, 3.0], "closes": [99.0, 3.0],
        "volumes": [99.0, 30.0]}}
    got = us_seam.attach(base, tail)["series"]["AAPL"]
    assert got["dates"] == ["2026-09-08", "2026-09-09", "2026-09-10"]
    assert got["closes"] == [1.0, 2.0, 3.0], "겹친 날은 뼈대가 남아야 한다"
    assert len(got["timestamps"]) == 3


def test_attach_code_missing_from_tail_keeps_base_series():
    import us_seam
    base = {"series": {"AAPL": {
        "dates": ["2026-09-08"], "opens": [1.0], "highs": [1.0], "lows": [1.0],
        "closes": [1.0], "volumes": [10.0], "timestamps": [1]}}}
    got = us_seam.attach(base, {})["series"]["AAPL"]
    assert got["dates"] == ["2026-09-08"]


def test_attach_rejects_fetch_tail_return_passed_unwrapped():
    # attach(base, fetch_tail(...)) 를 unwrap 없이 그대로 부르면 tail 의 키가
    # "series"/"failed" 뿐이라 모든 종목이 falsy 로 떨어져 «조용히» base 를
    # 그대로 돌려줄 뻔했다(검토에서 재현됨). 이제는 시끄럽게 막혀야 한다.
    import us_seam
    import pytest

    base = {"series": {"AAPL": {
        "dates": ["2026-09-09"], "opens": [1.0], "highs": [1.0], "lows": [1.0],
        "closes": [1.0], "volumes": [10.0], "timestamps": [1]}}}
    fetch_tail_return = {"series": {"AAPL": {
        "dates": ["2026-09-10"], "opens": [3.0], "highs": [3.0], "lows": [3.0],
        "closes": [3.0], "volumes": [30.0]}}, "failed": []}

    with pytest.raises(ValueError):
        us_seam.attach(base, fetch_tail_return)


def test_attach_no_new_dates_keeps_base_asof():
    import us_seam
    base = {"asof": "2026-09-09", "series": {"AAPL": {
        "dates": ["2026-09-09"], "opens": [1.0], "highs": [1.0], "lows": [1.0],
        "closes": [1.0], "volumes": [10.0], "timestamps": [1]}}}
    tail = {"AAPL": {
        "dates": ["2026-09-09"], "opens": [99.0], "highs": [99.0],
        "lows": [99.0], "closes": [99.0], "volumes": [99.0]}}
    got = us_seam.attach(base, tail)
    assert got["asof"] == "2026-09-09"
    assert got["series"]["AAPL"]["closes"] == [1.0], "겹친 날은 뼈대가 남아야 한다"


def _mk(dates, closes):
    return {"dates": list(dates), "opens": list(closes), "highs": list(closes),
            "lows": list(closes), "closes": list(closes),
            "volumes": [10.0] * len(dates)}


def _mk_base(dates, closes):
    s = _mk(dates, closes)
    s["timestamps"] = list(range(len(dates)))
    return s


def test_attach_drops_tail_bar_inside_base_window_missing_from_base():
    """뼈대 마지막 날보다 «앞선» 꼬리 봉은 뼈대에 없어도 «버린다» (2026-09-11).

    실측: 야후가 since 앞 봉을 준다(CYCN 이 since=09-09 에 09-08 봉을 냈다).
    종전 코드는 그것을 «끝»에 덧붙여 날짜가 ['09-05','09-09','09-08','09-10']
    이 됐다. 뼈대 기간 안은 Sharadar 가 정본이고 그 구멍은 «있는 채»로
    27.4해 백테스트가 돌았으므로 다른 벤더 값으로 메우지 않는다.
    """
    import us_seam
    base = {"series": {"AAPL": _mk_base(["2026-09-05", "2026-09-09"],
                                        [1.0, 2.0])}}
    tail = {"AAPL": _mk(["2026-09-08", "2026-09-10"], [99.0, 3.0])}
    out = us_seam.attach(base, tail)
    got = out["series"]["AAPL"]
    assert got["dates"] == ["2026-09-05", "2026-09-09", "2026-09-10"]
    assert got["closes"] == [1.0, 2.0, 3.0], "구멍을 야후 값으로 메우지 않는다"
    assert got["dates"] == sorted(got["dates"]), "오름차순이어야 한다"
    assert out["asof"] == "2026-09-10"
    rep = out["tail_dropped"]
    assert rep["n_bars"] == 1 and rep["n_codes"] == 1
    assert rep["codes"] == {"AAPL": ["2026-09-08"]}
    assert rep["n_overlap"] == 0


def test_attach_overlap_is_counted_apart_from_holes():
    """겹침(뼈대에 «있는» 날)과 구멍(뼈대에 «없는» 날)은 «다른» 수다."""
    import us_seam
    base = {"series": {"AAPL": _mk_base(["2026-09-08", "2026-09-09"],
                                        [1.0, 2.0])}}
    tail = {"AAPL": _mk(["2026-09-09", "2026-09-10"], [99.0, 3.0])}
    out = us_seam.attach(base, tail)
    assert out["series"]["AAPL"]["closes"] == [1.0, 2.0, 3.0]
    rep = out["tail_dropped"]
    assert rep["n_overlap"] == 1, "겹친 날 하나"
    assert rep["n_bars"] == 0 and rep["codes"] == {}, "구멍은 없다"


def test_attach_raises_when_a_returned_series_is_not_ascending():
    """꼬리를 «안» 받은 계열도 본다 — 「어느 길로 왔나」에 기대지 않는다."""
    import us_seam
    import pytest
    base = {"series": {"AAPL": _mk_base(["2026-09-09", "2026-09-08"],
                                        [1.0, 2.0])}}
    with pytest.raises(ValueError) as e:
        us_seam.attach(base, {})
    assert "오름차순" in str(e.value) and "AAPL" in str(e.value)


def test_attach_sorts_unordered_future_tail_bars():
    import us_seam
    base = {"series": {"AAPL": _mk_base(["2026-09-09"], [1.0])}}
    tail = {"AAPL": _mk(["2026-09-11", "2026-09-10"], [4.0, 3.0])}
    got = us_seam.attach(base, tail)["series"]["AAPL"]
    assert got["dates"] == ["2026-09-09", "2026-09-10", "2026-09-11"]
    assert got["closes"] == [1.0, 3.0, 4.0]
    assert got["timestamps"] == sorted(got["timestamps"])


def test_attach_raises_on_duplicate_tail_dates():
    import us_seam
    import pytest
    base = {"series": {"AAPL": _mk_base(["2026-09-09"], [1.0])}}
    tail = {"AAPL": _mk(["2026-09-10", "2026-09-10"], [3.0, 3.5])}
    with pytest.raises(ValueError) as e:
        us_seam.attach(base, tail)
    assert "오름차순" in str(e.value)


def test_attach_empty_base_series_takes_whole_tail():
    import us_seam
    base = {"series": {"AAPL": _mk_base([], [])}}
    tail = {"AAPL": _mk(["2026-09-09", "2026-09-10"], [1.0, 2.0])}
    got = us_seam.attach(base, tail)["series"]["AAPL"]
    assert got["dates"] == ["2026-09-09", "2026-09-10"]


def test_fetch_tail_empty_codes_returns_empty():
    import us_seam
    assert us_seam.fetch_tail([], "2026-09-09") == {"series": {}, "failed": []}


def test_fetch_tail_download_exception_fails_all_codes(monkeypatch):
    import us_seam

    def boom(*a, **k):
        raise RuntimeError("네트워크 오류")

    monkeypatch.setattr(us_seam.yf, "download", boom)
    got = us_seam.fetch_tail(["AAPL", "MSFT"], "2026-09-09")
    assert got == {"series": {}, "failed": ["AAPL", "MSFT"]}


def test_fetch_tail_single_ticker_flat_columns(monkeypatch):
    # 종목이 하나면 yf.download 표가 멀티인덱스가 아니라 필드 열 하나짜리다.
    import us_seam
    import pandas as pd

    idx = pd.to_datetime(["2026-09-09", "2026-09-10"])
    df = pd.DataFrame({
        "Open": [1.0, 2.0], "High": [1.5, 2.5], "Low": [0.5, 1.5],
        "Close": [1.2, 2.2], "Volume": [100.0, 200.0],
    }, index=idx)

    monkeypatch.setattr(us_seam.yf, "download", lambda *a, **k: df)
    got = us_seam.fetch_tail(["AAPL"], "2026-09-09")
    assert got["failed"] == []
    assert got["series"]["AAPL"]["dates"] == ["2026-09-09", "2026-09-10"]
    assert got["series"]["AAPL"]["closes"] == [1.2, 2.2]


def test_fetch_tail_multi_ticker_multiindex_columns(monkeypatch):
    # 종목이 여럿이면 열이 (종목, 필드) 멀티인덱스다 — df[code] 로 뗀다.
    import us_seam
    import pandas as pd

    idx = pd.to_datetime(["2026-09-09", "2026-09-10"])
    cols = pd.MultiIndex.from_product(
        [["AAPL", "MSFT"], ["Open", "High", "Low", "Close", "Volume"]])
    data = [[1.0, 1.5, 0.5, 1.2, 100.0, 10.0, 10.5, 9.5, 10.2, 1000.0],
            [2.0, 2.5, 1.5, 2.2, 200.0, 11.0, 11.5, 10.5, 11.2, 1100.0]]
    df = pd.DataFrame(data, index=idx, columns=cols)

    monkeypatch.setattr(us_seam.yf, "download", lambda *a, **k: df)
    got = us_seam.fetch_tail(["AAPL", "MSFT"], "2026-09-09")
    assert got["failed"] == []
    assert got["series"]["AAPL"]["closes"] == [1.2, 2.2]
    assert got["series"]["MSFT"]["closes"] == [10.2, 11.2]


def test_fetch_tail_missing_code_column_is_failed_not_swallowed(monkeypatch):
    # 멀티인덱스 표에 한 종목의 열이 아예 없으면(예: 야후가 그 종목을 못 찾음)
    # df[code] 가 예외를 내고, 그 종목만 failed 에 실려야 한다(조용히 넘어가지 않는다).
    import us_seam
    import pandas as pd

    idx = pd.to_datetime(["2026-09-09", "2026-09-10"])
    cols = pd.MultiIndex.from_product(
        [["AAPL"], ["Open", "High", "Low", "Close", "Volume"]])
    data = [[1.0, 1.5, 0.5, 1.2, 100.0], [2.0, 2.5, 1.5, 2.2, 200.0]]
    df = pd.DataFrame(data, index=idx, columns=cols)

    monkeypatch.setattr(us_seam.yf, "download", lambda *a, **k: df)
    got = us_seam.fetch_tail(["AAPL", "NOSUCH"], "2026-09-09")
    assert got["series"]["AAPL"]["closes"] == [1.2, 2.2]
    assert got["failed"] == ["NOSUCH"], "받지 못한 종목은 failed 에 실려야 한다"


def test_fetch_tail_empty_data_not_counted_as_failed(monkeypatch):
    # 새 거래일이 없어 표가 비면(예: since 가 최근 영업일 바로 다음날) 실패가
    # 아니다 — series 에도 failed 에도 안 실린다.
    import us_seam
    import pandas as pd

    idx = pd.to_datetime(["2026-09-09"])
    cols = pd.MultiIndex.from_product(
        [["AAPL"], ["Open", "High", "Low", "Close", "Volume"]])
    df = pd.DataFrame([[float("nan")] * 5], index=idx, columns=cols)

    monkeypatch.setattr(us_seam.yf, "download", lambda *a, **k: df)
    got = us_seam.fetch_tail(["AAPL"], "2026-09-09")
    assert got == {"series": {}, "failed": []}


# ── load_latest: 합본(tail)이 있으면 «그것»을 읽어야 한다 ──────────────────
# 🔴 2026-09-11 발견: /update-data-us 는 꼬리를 붙인 합본을 tail.json 에 쓰는데
#    저장소 전체에서 그것을 «읽는» 자리가 0개였다. 소비자가 base.json 을 읽으면
#    자료를 갱신해도 결과가 안 바뀐다 — 예외도 경고도 없는 조용한 실패다.
#    시험이 없으면 다음 사람이 load_base 로 되돌린다.

def _mini(dates, closes):
    n = len(dates)
    return {"dates": list(dates), "opens": list(closes), "highs": list(closes),
            "lows": list(closes), "closes": list(closes),
            "volumes": [10.0] * n, "timestamps": list(range(n))}


def _write(p, asof, closes, dates):
    import json
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"asof": asof, "trim": 310,
                             "series": {"AAPL": _mini(dates, closes)}}),
                 encoding="utf-8")


def test_load_latest_prefers_tail_when_present(tmp_path, monkeypatch):
    base_p, tail_p = tmp_path / "base.json", tmp_path / "tail.json"
    _write(base_p, "2026-09-09", [1.0], ["2026-09-09"])
    _write(tail_p, "2026-09-10", [1.0, 2.0], ["2026-09-09", "2026-09-10"])
    monkeypatch.setattr(us_matrix, "BASE_PATH", base_p)
    monkeypatch.setattr(us_matrix, "TAIL_PATH", tail_p)
    us_matrix._BASE = None

    data, src = us_matrix.load_latest()
    assert src == tail_p, "합본이 있으면 합본을 읽어야 한다"
    assert data["asof"] == "2026-09-10"
    # get_series 도 같은 자료를 봐야 한다(전역 캐시가 합본으로 채워졌는가)
    assert us_matrix.get_series("AAPL")["closes"] == [1.0, 2.0]


def test_load_latest_falls_back_to_base_when_no_tail(tmp_path, monkeypatch):
    base_p, tail_p = tmp_path / "base.json", tmp_path / "nope.json"
    _write(base_p, "2026-09-09", [1.0], ["2026-09-09"])
    monkeypatch.setattr(us_matrix, "BASE_PATH", base_p)
    monkeypatch.setattr(us_matrix, "TAIL_PATH", tail_p)
    us_matrix._BASE = None

    data, src = us_matrix.load_latest()
    assert src == base_p, "합본이 없으면 뼈대로 떨어져야 한다"
    assert data["asof"] == "2026-09-09"


def test_get_series_lazy_load_prefers_tail(tmp_path, monkeypatch):
    """게으른 자동 로드도 «합본»을 골라야 한다.

    🔴 2026-09-11: get_series 는 _BASE 가 비었을 때 load_base() 를 불렀다.
       load_base 는 뼈대만 읽으므로 소비자가 load_latest() 를 «먼저» 부르지
       않으면 예외도 경고도 없이 옛 자료로 돈다. 1단계 각본은 우연히
       load_latest() 를 먼저 불러 맞고 있었다 — «계약»이 아니라 «순서»였다.
       이 시험이 그 순서 의존을 계약으로 바꾼다.
    """
    base_p, tail_p = tmp_path / "base.json", tmp_path / "tail.json"
    _write(base_p, "2026-09-09", [1.0], ["2026-09-09"])
    _write(tail_p, "2026-09-10", [1.0, 2.0], ["2026-09-09", "2026-09-10"])
    monkeypatch.setattr(us_matrix, "BASE_PATH", base_p)
    monkeypatch.setattr(us_matrix, "TAIL_PATH", tail_p)
    us_matrix._BASE = None

    # load_latest() 를 «부르지 않고» 바로 get_series 를 부른다
    got = us_matrix.get_series("AAPL")
    assert got is not None
    assert got["closes"] == [1.0, 2.0], "게으른 로드가 뼈대를 읽었다(합본을 놓쳤다)"


def test_tail_path_has_one_source_of_truth():
    # us_seam 이 경로를 «다시 적으면» 자가 둘이 되어 한쪽만 고치는 사고가 난다.
    import us_seam
    assert us_seam.TAIL_PATH is us_matrix.TAIL_PATH, (
        "TAIL_PATH 정본은 us_matrix 다 — us_seam 은 가져다 써야 한다")


# ── 「마지막 봉 = 기준일」 관문 (하네스 :355 와 같은 자리) ─────────────────
# 오늘 자료로는 0건이지만, 꼬리가 한 번이라도 돌면 「표가 빈 종목은 실패가 아니다」
# (us_seam.fetch_tail) 라 그 종목엔 옛 뼈대가 남고 종목마다 마지막 날이 달라진다.
# 그때 이 관문이 없으면 하네스가 버리는 종목이 8관문에도 RS 비교풀에도 들어간다.

def test_stale_last_bar_is_excluded(tmp_path, monkeypatch):
    import json
    import screen_trend_template_us as scr

    p = tmp_path / "base.json"
    fresh = [f"2026-{m:02d}-{d:02d}" for m in (1, 2, 3, 4, 5, 6, 7, 8, 9)
             for d in range(1, 29)][:250]
    stale = fresh[:-1]
    p.write_text(json.dumps({"asof": fresh[-1], "trim": 310, "series": {
        "FRESH": _mini(fresh, [1.0] * len(fresh)),
        "STALE": _mini(stale, [1.0] * len(stale)),
    }}), encoding="utf-8")
    monkeypatch.setattr(us_matrix, "BASE_PATH", p)
    us_matrix.load_base(p)

    asof = fresh[-1]
    ok = scr.collect_one({"code": "FRESH", "name": "f", "market": "NASDAQ"}, asof)
    bad = scr.collect_one({"code": "STALE", "name": "s", "market": "NASDAQ"}, asof)
    assert ok["ok"] is True and ok["reason_code"] is None
    assert bad["ok"] is False, "마지막 봉이 기준일보다 이르면 떨어져야 한다"
    assert bad["reason_code"] == "stale"


def test_resolve_trading_day_backs_off_to_last_session():
    import screen_trend_template_us as scr
    base = {"series": {us_loader.REF: _mini(
        ["2026-09-08", "2026-09-09"], [1.0, 2.0])}}
    # 거래일을 그대로 주면 안 움직인다
    assert scr.resolve_trading_day(base, "2026-09-09") == ("2026-09-09", False)
    # 주말/휴장일을 주면 직전 거래일로 내려간다 — 안 그러면 전 종목이 stale 로
    # 떨어져 «조용히» 후보 0 이 된다
    assert scr.resolve_trading_day(base, "2026-09-12") == ("2026-09-09", True)

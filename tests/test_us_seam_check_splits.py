"""분할 검사를 «묶어» 부르는 길 시험 (2026-09-11).

무엇이 바뀌었나: `check_splits` 가 종목마다 `yf.Ticker(c).splits` 를 따로
부르던 것을 `yf.download(..., actions=True)` 묶음으로 바꿨다. 계약은 그대로다 —
`check_splits(codes, since, until) -> {"splits": [...], "failed": [...]}`,
창은 닫힌 구간.

🔴 여기서 지켜야 하는 것은 «속도»가 아니라 `failed` 의 «뜻»이다.
  `failed` 는 「분할 없음」이 아니라 「못 봤음」이다. 묶음으로 바꾸면 이 자리가
  제일 깨지기 쉬워서, 세 갈래를 각각 시험한다:
    ① 묶음 «전체» 실패            -> 그 묶음의 모든 종목을 따로 다시 묻는다
    ② 그 종목 열이 없다 / 분할 열이 없다 / 봉이 없다(전부 NaN)
                                  -> 그 종목만 따로 다시 묻는다
    ③ 열은 받았는데 분할 값이 0 뿐 -> «분할 없음»(정상). 다시 묻지 않는다
  그리고 «따로 물어서도» 못 보면(예외) 그때야 `failed` 다.

⛔ 가짜는 «바깥 세상 표기»에 못 박는다. 야후는 자기 표기(`BRK-B`)로 열을 주지
  «되물은 대로» 주지 않는다. 받은 인자를 그대로 돌려주는 가짜를 쓰면 왕복
  시험이 항등식이 되어 «질 수가 없다».
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import us_seam  # noqa: E402

SINCE, UNTIL = "2026-09-09", "2026-09-11"

# 야후가 actions=True 로 줄 때 실제로 오는 필드(실측 2026-09-11).
FIELDS = ["Open", "High", "Low", "Close", "Adj Close", "Volume",
          "Dividends", "Stock Splits"]


def _frame(dates, per_symbol):
    """`yf.download(actions=True, group_by="ticker")` 가 내는 모양을 만든다.

    per_symbol: {야후심볼: {"fields": [...], "splits": [값 또는 None, ...]}}
      · "fields" 를 안 주면 FIELDS 전부(분할 열 포함)
      · "splits" 의 None 은 NaN(그 날 이 종목 봉이 «없다»)이고 0.0 은 봉은
        있는데 분할이 «없다»는 뜻이다 — 야후는 union 색인을 쓴다(실측).
    """
    cols, data = [], {}
    for sym, spec in per_symbol.items():
        fields = spec.get("fields", FIELDS)
        for f in fields:
            cols.append((sym, f))
            if f == "Stock Splits":
                vals = spec.get("splits", [0.0] * len(dates))
                data[(sym, f)] = [np.nan if v is None else float(v) for v in vals]
            else:
                data[(sym, f)] = [1.0] * len(dates)
    idx = pd.to_datetime(dates)
    return pd.DataFrame(data, index=idx,
                        columns=pd.MultiIndex.from_tuples(cols))


class _NoTicker:
    """따로 묻는 길이 «안» 불렸어야 하는 시험에 쓴다."""

    def __init__(self, symbol):
        raise AssertionError("따로 묻지 말았어야 한다: %s" % symbol)


# ── ③ 열은 받았고 분할 값이 0 뿐 = 분할 없음(정상) ─────────────────────────

def test_zero_split_column_is_not_failed(monkeypatch):
    def fake_download(codes, **kw):
        return _frame([SINCE, "2026-09-10"],
                      {"AAPL": {"splits": [0.0, 0.0]},
                       "MSFT": {"splits": [0.0, 0.0]}})

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", _NoTicker)
    got = us_seam.check_splits(["AAPL", "MSFT"], SINCE, UNTIL)
    assert got == {"splits": [], "failed": []}


def test_batch_finds_split_and_reports_sharadar_symbol(monkeypatch):
    # 야후는 «자기» 표기로 열을 준다 — 되물은 대로가 아니다.
    def fake_download(codes, **kw):
        return _frame([SINCE, "2026-09-10"],
                      {"BRK-B": {"splits": [0.0, 2.0]},
                       "AAPL": {"splits": [0.0, 0.0]}})

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", _NoTicker)
    got = us_seam.check_splits(["BRK.B", "AAPL"], SINCE, UNTIL)
    assert got == {"splits": [{"code": "BRK.B", "date": "2026-09-10",
                               "ratio": 2.0}], "failed": []}


def test_batch_asks_yahoo_spelling(monkeypatch):
    asked = {}

    def fake_download(codes, **kw):
        asked["codes"] = list(codes)
        return _frame([SINCE], {"BRK-B": {"splits": [0.0]},
                                "AAPL": {"splits": [0.0]}})

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", _NoTicker)
    us_seam.check_splits(["BRK.B", "AAPL"], SINCE, UNTIL)
    assert asked["codes"] == ["BRK-B", "AAPL"], "야후에는 대시로 물어야 한다"


def test_window_is_closed_and_excludes_outside(monkeypatch):
    dates = ["2026-09-08", SINCE, "2026-09-10", UNTIL, "2026-09-12"]

    def fake_download(codes, **kw):
        return _frame(dates, {"A": {"splits": [3.0, 2.0, 0.0, 5.0, 7.0]}})

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", _NoTicker)
    got = us_seam.check_splits(["A"], SINCE, UNTIL)
    assert [(s["date"], s["ratio"]) for s in got["splits"]] == [
        (SINCE, 2.0), (UNTIL, 5.0)], "창 밖(09-08·09-12)은 안 잡는다"


def test_single_code_frame_without_multiindex(monkeypatch):
    # 종목이 하나면 야후가 멀티인덱스가 «아닌» 표를 줄 수 있다.
    def fake_download(codes, **kw):
        idx = pd.to_datetime([SINCE])
        return pd.DataFrame([[1.0] * 7 + [2.0]], index=idx, columns=FIELDS)

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", _NoTicker)
    got = us_seam.check_splits(["A"], SINCE, UNTIL)
    assert got["splits"] == [{"code": "A", "date": SINCE, "ratio": 2.0}]


# ── ② 묶음은 됐는데 그 종목을 «못 봤다» -> 따로 다시 묻는다 ────────────────

def _fallback_ticker(found: dict, boom: set = frozenset()):
    """따로 묻는 길의 가짜. found = {야후심볼: (날짜, 배수)}."""

    class _T:
        asked: list = []

        def __init__(self, symbol):
            _T.asked.append(symbol)
            if symbol in boom:
                raise RuntimeError("야후 못 붙음: %s" % symbol)
            self._symbol = symbol

        @property
        def splits(self):
            hit = found.get(self._symbol)
            if hit is None:
                return pd.Series(dtype=float)
            d, r = hit
            return pd.Series([r], index=pd.to_datetime([d]))

    _T.asked = []
    return _T


@pytest.mark.parametrize("spec,label", [
    ({"fields": [f for f in FIELDS if f != "Stock Splits"]}, "분할 열이 없다"),
    ({"splits": [None, None]}, "봉이 하나도 없다(전부 NaN)"),
])
def test_seen_but_unusable_column_is_asked_again(monkeypatch, spec, label):
    def fake_download(codes, **kw):
        return _frame([SINCE, "2026-09-10"],
                      {"A": dict(spec), "B": {"splits": [0.0, 0.0]}})

    fake = _fallback_ticker({"A": ("2026-09-10", 0.5)})
    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", fake)
    got = us_seam.check_splits(["A", "B"], SINCE, UNTIL)
    assert fake.asked == ["A"], "못 본 종목만 다시 묻는다 (%s)" % label
    assert got == {"splits": [{"code": "A", "date": "2026-09-10",
                               "ratio": 0.5}], "failed": []}


def test_missing_ticker_column_is_asked_again(monkeypatch):
    # 묶음 표에 그 종목 열이 «아예» 없다 — 「분할 없음」으로 읽으면 안 된다.
    def fake_download(codes, **kw):
        return _frame([SINCE], {"B": {"splits": [0.0]}})

    fake = _fallback_ticker({"A": (SINCE, 2.0)})
    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", fake)
    got = us_seam.check_splits(["A", "B"], SINCE, UNTIL)
    assert fake.asked == ["A"]
    assert got == {"splits": [{"code": "A", "date": SINCE, "ratio": 2.0}],
                   "failed": []}


def test_unseen_with_no_data_anywhere_is_not_failed(monkeypatch):
    # 상장폐지 종목: 묶음도 못 보고 따로 물어도 빈 답이다. 예외는 «안» 났으므로
    # 종전 길과 똑같이 「분할 없음」이다 — failed 가 아니다.
    # (여기가 무너지면 4,648종목의 약 10%가 날마다 failed 로 들어와
    #  갱신이 영구히 멈춘다 — 실측 2026-09-11 표본 503종목에서 9.9%.)
    def fake_download(codes, **kw):
        return _frame([SINCE], {"B": {"splits": [0.0]}})

    fake = _fallback_ticker({})
    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", fake)
    got = us_seam.check_splits(["A", "B"], SINCE, UNTIL)
    assert fake.asked == ["A"]
    assert got == {"splits": [], "failed": []}


# ── ① 묶음 «전체» 실패 ────────────────────────────────────────────────────

@pytest.mark.parametrize("maker,label", [
    (lambda: (_ for _ in ()).throw(RuntimeError("야후 못 붙음")), "예외"),
    (lambda: pd.DataFrame(), "빈 표"),
])
def test_whole_batch_failure_asks_every_code_again(monkeypatch, maker, label):
    def fake_download(codes, **kw):
        return maker()

    fake = _fallback_ticker({"A": (SINCE, 2.0)}, boom={"B"})
    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", fake)
    got = us_seam.check_splits(["A", "B"], SINCE, UNTIL)
    assert fake.asked == ["A", "B"], "묶음 전체가 죽으면 모두 다시 묻는다 (%s)" % label
    assert got["splits"] == [{"code": "A", "date": SINCE, "ratio": 2.0}]
    assert got["failed"] == ["B"], "따로 물어서도 못 본 것만 failed 다"


def test_failed_is_only_when_individual_ask_also_fails(monkeypatch):
    def fake_download(codes, **kw):
        raise RuntimeError("야후 못 붙음")

    fake = _fallback_ticker({}, boom={"A", "B"})
    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", fake)
    got = us_seam.check_splits(["A", "B"], SINCE, UNTIL)
    assert got == {"splits": [], "failed": ["A", "B"]}


# ── 묶음으로 «실제로» 쪼개서 부르는가 ─────────────────────────────────────

def test_codes_are_sent_in_batches(monkeypatch):
    n = us_seam.SPLIT_BATCH * 2 + 3
    codes = ["C%04d" % i for i in range(n)]
    sizes = []

    def fake_download(asked, **kw):
        sizes.append(len(asked))
        return _frame([SINCE], {c: {"splits": [0.0]} for c in asked})

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    monkeypatch.setattr(us_seam.yf, "Ticker", _NoTicker)
    got = us_seam.check_splits(codes, SINCE, UNTIL)
    assert sizes == [us_seam.SPLIT_BATCH, us_seam.SPLIT_BATCH, 3], (
        "종목마다 따로 부르지 않고 SPLIT_BATCH 씩 묶어 불러야 한다")
    assert got == {"splits": [], "failed": []}


def test_empty_codes_makes_no_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("부르지 말았어야 한다")

    monkeypatch.setattr(us_seam.yf, "download", boom)
    monkeypatch.setattr(us_seam.yf, "Ticker", _NoTicker)
    assert us_seam.check_splits([], SINCE, UNTIL) == {"splits": [], "failed": []}

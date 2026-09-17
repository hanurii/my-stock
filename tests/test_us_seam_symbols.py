"""야후 심볼 표기 왕복 시험 (2026-09-11 최종 검토 2번).

무엇을 막나: Sharadar 는 점(`BRK.B`), 야후는 대시(`BRK-B`)를 쓴다. 야후는
모르는 심볼에 예외를 내지 않고 «빈 표»를 주는데, `fetch_tail` 의 계약이
「표가 빈 종목은 실패가 아니다」라서 그 빈 표가 `failed` 에 «안» 들어간다.
결과: 그 종목들은 날마다 경고 없이 옛 뼈대로 남는다(영구 stale).
뼈대 4,648종목 중 다섯이 이 길로 샜다 — BF.B·BRK.B·CRD.A·LGF.B·MOG.A.

⛔ 뼈대·산출물의 표기는 «바꾸지 않는다». 바꾸는 것은 「야후에 물을 때」뿐이고,
  받은 것은 «원래» 심볼을 키로 담아야 한다. 아래 시험이 그 왕복을 본다.

⛔ 시험이 실제로 깨지는지 확인한 것(무력화): `to_yahoo_symbol` 을
  `return code`(그대로 돌려주기)로 바꾸면 여덟이 깨진다(실측 2026-09-11,
  11개 중 8개 실패) — test_yahoo_symbol_converts_dot 다섯 갈래 ·
  test_fetch_tail_asks_yahoo_spelling ·
  test_fetch_tail_stores_under_sharadar_symbol ·
  test_check_splits_asks_yahoo_and_reports_sharadar.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import us_seam  # noqa: E402


# ── 변환 자체 ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sharadar,yahoo", [
    ("BRK.B", "BRK-B"),
    ("BF.B", "BF-B"),
    ("CRD.A", "CRD-A"),
    ("LGF.B", "LGF-B"),
    ("MOG.A", "MOG-A"),
    ("AAPL", "AAPL"),        # 점이 없으면 그대로다
])
def test_yahoo_symbol_converts_dot(sharadar, yahoo):
    assert us_seam.to_yahoo_symbol(sharadar) == yahoo


# ── fetch_tail 왕복 ───────────────────────────────────────────────────────

def _frame(symbols, dates):
    """yf.download 가 여럿일 때 내는 모양(열이 (종목, 필드) 멀티인덱스)."""
    cols = pd.MultiIndex.from_product(
        [symbols, ["Open", "High", "Low", "Close", "Volume"]])
    idx = pd.to_datetime(dates)
    data = [[1.0] * len(cols) for _ in dates]
    return pd.DataFrame(data, index=idx, columns=cols)


def test_fetch_tail_asks_yahoo_spelling(monkeypatch):
    asked = {}

    def fake_download(codes, **kw):
        asked["codes"] = list(codes)
        return _frame(list(codes), ["2026-09-10"])

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    us_seam.fetch_tail(["BRK.B", "AAPL"], since="2026-09-09")
    assert asked["codes"] == ["BRK-B", "AAPL"], "야후에는 대시로 물어야 한다"


def test_fetch_tail_stores_under_sharadar_symbol(monkeypatch):
    # 야후는 «자기» 표기로 열을 준다 — 무엇을 물었든 BRK-B 다. 되묻는 값을
    # 그대로 되돌려 주는 가짜를 쓰면 이 시험이 «질 수가 없어» 왕복을 못 잰다.
    def fake_download(codes, **kw):
        return _frame(["BRK-B", "AAPL"], ["2026-09-10"])

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    out = us_seam.fetch_tail(["BRK.B", "AAPL"], since="2026-09-09")
    assert set(out["series"]) == {"BRK.B", "AAPL"}, (
        "받은 것은 «원래» 심볼로 되돌려 담아야 한다 — 뼈대 표기가 정본이다")
    assert out["failed"] == []
    assert out["series"]["BRK.B"]["dates"] == ["2026-09-10"]


def test_fetch_tail_single_code_still_works(monkeypatch):
    # 종목이 하나면 yf.download 의 열이 멀티인덱스가 아니다 — 그 갈래도 왕복해야 한다.
    def fake_download(codes, **kw):
        idx = pd.to_datetime(["2026-09-10"])
        return pd.DataFrame([[1.0] * 5], index=idx,
                            columns=["Open", "High", "Low", "Close", "Volume"])

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    out = us_seam.fetch_tail(["BRK.B"], since="2026-09-09")
    assert list(out["series"]) == ["BRK.B"]


# ── check_splits 왕복 ─────────────────────────────────────────────────────

class _FakeTicker:
    asked: list = []

    def __init__(self, symbol):
        _FakeTicker.asked.append(symbol)
        self._symbol = symbol

    @property
    def splits(self):
        idx = pd.to_datetime(["2026-09-10"])
        return pd.Series([2.0], index=idx)


def _actions_frame(symbols, dates, splits):
    """`yf.download(actions=True, group_by="ticker")` 모양.

    ⛔ 심볼을 «못 박아» 넘긴다 — 되물은 대로 돌려주는 가짜를 쓰면 왕복 시험이
      항등식이 되어 «질 수가 없다». 야후는 «자기» 표기로 열을 준다.
    """
    fields = ["Open", "High", "Low", "Close", "Adj Close", "Volume",
              "Dividends", "Stock Splits"]
    cols = pd.MultiIndex.from_product([symbols, fields])
    data = {}
    for sym in symbols:
        for f in fields:
            data[(sym, f)] = (list(splits[sym]) if f == "Stock Splits"
                              else [1.0] * len(dates))
    return pd.DataFrame(data, index=pd.to_datetime(dates), columns=cols)


def test_check_splits_batch_asks_yahoo_and_reports_sharadar(monkeypatch):
    """묶음 길의 왕복 — 대시로 «묻고», 점으로 «담는다»."""
    asked = {}

    def fake_download(codes, **kw):
        asked["codes"] = list(codes)
        # 야후는 «자기» 표기로 준다. 무엇을 물었든 BRK-B 다.
        return _actions_frame(["BRK-B", "AAPL"], ["2026-09-10"],
                              {"BRK-B": [2.0], "AAPL": [0.0]})

    monkeypatch.setattr(us_seam.yf, "download", fake_download)
    r = us_seam.check_splits(["BRK.B", "AAPL"], since="2026-09-09",
                             until="2026-09-11")
    assert asked["codes"] == ["BRK-B", "AAPL"], "야후에는 대시로 물어야 한다"
    assert [s["code"] for s in r["splits"]] == ["BRK.B"], (
        "찾은 분할은 «원래» 심볼로 보고해야 한다 — 뼈대가 그 이름을 쓴다")
    assert r["failed"] == []


def test_check_splits_asks_yahoo_and_reports_sharadar(monkeypatch):
    """따로 묻는 길(묶음이 못 본 종목)의 왕복."""
    _FakeTicker.asked = []

    def no_batch(*a, **k):
        raise RuntimeError("묶음 길은 이 시험에서 막았다")

    monkeypatch.setattr(us_seam.yf, "download", no_batch)
    monkeypatch.setattr(us_seam.yf, "Ticker", _FakeTicker)
    r = us_seam.check_splits(["BRK.B"], since="2026-09-09", until="2026-09-11")
    assert _FakeTicker.asked == ["BRK-B"], "야후에는 대시로 물어야 한다"
    assert [s["code"] for s in r["splits"]] == ["BRK.B"], (
        "찾은 분할은 «원래» 심볼로 보고해야 한다 — 뼈대가 그 이름을 쓴다")
    assert r["failed"] == []


def test_check_splits_failure_is_reported_with_sharadar_symbol(monkeypatch):
    def no_batch(*a, **k):
        raise RuntimeError("묶음 길은 이 시험에서 막았다")

    def boom(symbol):
        raise RuntimeError("야후 못 붙음")

    monkeypatch.setattr(us_seam.yf, "download", no_batch)
    monkeypatch.setattr(us_seam.yf, "Ticker", boom)
    r = us_seam.check_splits(["BRK.B"], since="2026-09-09", until="2026-09-11")
    assert r["failed"] == ["BRK.B"]

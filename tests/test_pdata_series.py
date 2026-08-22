# -*- coding: utf-8 -*-
"""pdata 원본(비수정) → 수정주가 시계열 변환 검증.

pdata 는 비수정주가라 액면분할·병합이 나면 과거가 통째로 어긋난다.
fltRt(등락률) 연쇄로 수정 지수를 만들고, 그 지수에 맞춰 시·고·저와
거래량을 환산한다. 거래량은 거래대금(trPrc) ÷ 수정가로 되돌린다
(거래대금은 분할에 불변이라 이게 유일하게 안전한 경로).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.pdata_series import build_series  # noqa: E402


def rec(clpr, fltRt, mkp=None, hipr=None, lopr=None, trqu=1000.0, trPrc=None,
        name="테스트", mkt="KOSPI"):
    mkp = clpr if mkp is None else mkp
    hipr = clpr if hipr is None else hipr
    lopr = clpr if lopr is None else lopr
    trPrc = clpr * trqu if trPrc is None else trPrc
    return {"itmsNm": name, "mrktCtg": mkt, "clpr": clpr, "fltRt": fltRt,
            "mkp": mkp, "hipr": hipr, "lopr": lopr, "trqu": trqu, "trPrc": trPrc}


class TestNoCorporateAction:
    """기준가 변경이 없으면 원본 그대로여야 한다."""

    def test_closes_match_raw_when_no_split(self):
        days = {"2024-01-02": {"A": rec(1000.0, 0.0)},
                "2024-01-03": {"A": rec(1100.0, 10.0)},
                "2024-01-04": {"A": rec(1210.0, 10.0)}}
        s = build_series(days)["A"]
        assert s["dates"] == ["2024-01-02", "2024-01-03", "2024-01-04"]
        assert s["closes"] == pytest.approx([1000.0, 1100.0, 1210.0], rel=1e-9)

    def test_ohlc_preserved(self):
        days = {"2024-01-02": {"A": rec(1000.0, 0.0, mkp=990.0, hipr=1020.0, lopr=980.0)}}
        s = build_series(days)["A"]
        assert s["opens"][0] == pytest.approx(990.0)
        assert s["highs"][0] == pytest.approx(1020.0)
        assert s["lows"][0] == pytest.approx(980.0)


class TestSplitAdjustment:
    """액면분할: 가격이 1/2 되고 등락률은 0 → 과거를 1/2 로 환산해야 한다."""

    def test_past_closes_halved_on_2for1_split(self):
        days = {"2024-01-02": {"A": rec(1000.0, 0.0)},
                "2024-01-03": {"A": rec(1100.0, 10.0)},
                # 분할일: 실제 주가는 550 이지만 등락률은 0%
                "2024-01-04": {"A": rec(550.0, 0.0)}}
        s = build_series(days)["A"]
        # 마지막 실제가(550)에 맞춰 과거가 절반으로 환산돼야 한다
        assert s["closes"] == pytest.approx([500.0, 550.0, 550.0], rel=1e-9)

    def test_daily_returns_survive_split(self):
        days = {"2024-01-02": {"A": rec(1000.0, 0.0)},
                "2024-01-03": {"A": rec(1100.0, 10.0)},
                "2024-01-04": {"A": rec(550.0, 0.0)},
                "2024-01-05": {"A": rec(605.0, 10.0)}}
        c = build_series(days)["A"]["closes"]
        rets = [c[i] / c[i - 1] - 1 for i in range(1, len(c))]
        assert rets == pytest.approx([0.10, 0.0, 0.10], abs=1e-9)

    def test_intraday_shape_preserved_through_split(self):
        """분할 전날의 고가/종가 비율은 환산 후에도 같아야 한다."""
        days = {"2024-01-02": {"A": rec(1000.0, 0.0, hipr=1050.0, lopr=950.0)},
                "2024-01-03": {"A": rec(500.0, 0.0)}}
        s = build_series(days)["A"]
        assert s["highs"][0] / s["closes"][0] == pytest.approx(1.05)
        assert s["lows"][0] / s["closes"][0] == pytest.approx(0.95)


class TestVolume:
    """거래량은 거래대금 ÷ 수정가 — 분할이 나도 거래대금은 불변이라 안전하다."""

    def test_volume_from_turnover(self):
        days = {"2024-01-02": {"A": rec(1000.0, 0.0, trqu=500.0, trPrc=500_000.0)}}
        s = build_series(days)["A"]
        assert s["volumes"][0] == pytest.approx(500.0)

    def test_volume_rescaled_after_split(self):
        """분할 전 거래량은 환산가 기준으로 2배가 돼야 비교가 성립한다."""
        days = {"2024-01-02": {"A": rec(1000.0, 0.0, trqu=500.0, trPrc=500_000.0)},
                "2024-01-03": {"A": rec(500.0, 0.0, trqu=1000.0, trPrc=500_000.0)}}
        s = build_series(days)["A"]
        # 환산 후 첫날 가격은 500 → 거래대금 50만 ÷ 500 = 1000주
        assert s["volumes"] == pytest.approx([1000.0, 1000.0], rel=1e-9)


class TestFilters:
    def test_konex_and_foreign_excluded(self):
        days = {"2024-01-02": {"A": rec(1000.0, 0.0),
                               "B": rec(1000.0, 0.0, mkt="KONEX"),
                               "900100": rec(1000.0, 0.0, name="외국법인")}}
        out = build_series(days)
        assert "A" in out and "B" not in out

    def test_missing_day_is_skipped_not_interpolated(self):
        """중간에 거래정지로 빠진 날은 배열에 넣지 않는다(길이 = 등장일 수)."""
        days = {"2024-01-02": {"A": rec(1000.0, 0.0)},
                "2024-01-03": {"B": rec(2000.0, 0.0)},
                "2024-01-04": {"A": rec(1100.0, 10.0)}}
        s = build_series(days)["A"]
        assert s["dates"] == ["2024-01-02", "2024-01-04"]
        assert len(s["closes"]) == 2

    def test_bad_fltRt_does_not_corrupt_chain(self):
        """등락률이 없거나 말이 안 되면 종가비로 대체한다."""
        days = {"2024-01-02": {"A": rec(1000.0, 0.0)},
                "2024-01-03": {"A": rec(1100.0, None)}}
        s = build_series(days)["A"]
        assert s["closes"] == pytest.approx([1000.0, 1100.0], rel=1e-9)


class TestScale:
    def test_last_close_equals_raw_last_close(self):
        """환산 기준점은 마지막 실제 종가 — 최신 가격이 진짜 값이어야 한다."""
        days = {"2024-01-02": {"A": rec(1000.0, 0.0)},
                "2024-01-03": {"A": rec(550.0, 0.0)}}
        s = build_series(days)["A"]
        assert s["closes"][-1] == pytest.approx(550.0)


class TestStreaming:
    """1,628일치를 한꺼번에 메모리에 올리지 않고 하루씩 흘려보낼 수 있어야 한다."""

    def test_accepts_iterator_of_pairs(self):
        pairs = iter([("2024-01-02", {"A": rec(1000.0, 0.0)}),
                      ("2024-01-03", {"A": rec(1100.0, 10.0)})])
        s = build_series(pairs)["A"]
        assert s["closes"] == pytest.approx([1000.0, 1100.0], rel=1e-9)

    def test_iterator_and_dict_agree(self):
        days = {"2024-01-02": {"A": rec(1000.0, 0.0)},
                "2024-01-03": {"A": rec(550.0, 0.0)},
                "2024-01-04": {"A": rec(605.0, 10.0)}}
        a = build_series(days)["A"]
        b = build_series(iter(sorted(days.items())))["A"]
        assert a["closes"] == pytest.approx(b["closes"], rel=1e-12)
        assert a["volumes"] == pytest.approx(b["volumes"], rel=1e-12)

"""유니버스가 «스냅샷 뒤» 기준일에도 살아 있는가 (2026-09-11 최종 검토 1번).

무엇을 막나: 상장 판정이 얼린 Sharadar `lastpricedate` 를 «상한»으로 쓰면,
꼬리를 한 번이라도 붙여 기준일이 스냅샷 뒤로 가는 순간 «전 종목»이 미상장으로
읽혀 유니버스가 0 이 된다. 예외도 경고도 없이 「통과 0」으로 정상 종료한다.

이 시험 파일이 «없어서» 그 구멍이 살았다 — 지금까지의 모든 실행과 시험이
기준일 = 뼈대 기준일 = 스냅샷 날짜에서 돌았고, 그때는 술어가 통과했다.
그래서 여기 시험은 전부 «스냅샷 다음 날»을 판으로 쓴다.

⛔ 시험이 실제로 깨지는지 확인한 것(무력화):
  `is_listed_on` 의 「스냅샷 때 살아 있었다 -> 상한 없음」 줄을 지우고
  하네스 술어(`firstpricedate <= asof <= lastpricedate`)로 되돌리면
  아래 셋이 깨진다 — test_live_ticker_survives_day_after_snapshot ·
  test_universe_survives_day_after_snapshot ·
  test_zero_universe_is_reported_as_breakage(간접). 실측 2026-09-11.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import screen_trend_template_us as scr  # noqa: E402

SNAPSHOT = "2026-09-09"
NEXT_DAY = "2026-09-10"


def _meta():
    """얼린 메타의 최소판. 살아 있는 둘 + 스냅샷 «전»에 끊긴 진짜 상장폐지 하나."""
    return {
        # 스냅샷 때 거래 중이었다 -> lastpricedate 가 스냅샷과 같다
        "LIVE": {"firstpricedate": "2020-01-02", "lastpricedate": SNAPSHOT,
                 "name": "살아 있음", "exchange": "NASDAQ"},
        "LIVE2": {"firstpricedate": "2020-01-02", "lastpricedate": SNAPSHOT,
                  "name": "살아 있음 둘", "exchange": "NYSE"},
        # 스냅샷 «전»에 이미 끊겼다 -> 진짜 상장폐지
        "DEAD": {"firstpricedate": "2020-01-02", "lastpricedate": "2026-08-20",
                 "name": "상장폐지", "exchange": "NASDAQ"},
        # 스냅샷 뒤에 상장했다면 하한에 걸려야 한다(기준일보다 늦은 상장)
        "FUTURE": {"firstpricedate": "2026-12-01", "lastpricedate": SNAPSHOT,
                   "name": "아직 상장 전", "exchange": "NASDAQ"},
    }


def _base(codes):
    return {"asof": SNAPSHOT, "trim": 310,
            "series": {c: {"dates": [SNAPSHOT], "closes": [1.0]} for c in codes}}


# ── 스냅샷 날짜를 «유도»하는가 ────────────────────────────────────────────

def test_snapshot_date_is_derived_from_metadata():
    # 손으로 적으면 뼈대를 다시 만드는 날 자가 둘이 된다.
    assert scr.sharadar_snapshot_date(_meta()) == SNAPSHOT


def test_snapshot_date_moves_when_metadata_moves():
    m = _meta()
    m["LIVE"]["lastpricedate"] = "2026-10-31"
    assert scr.sharadar_snapshot_date(m) == "2026-10-31"


# ── 술어 자체 ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("asof", [SNAPSHOT, NEXT_DAY, "2026-12-31"])
def test_live_ticker_survives_day_after_snapshot(asof):
    # 🔴 이것이 1번 결함의 본체다. 하네스 술어를 그대로 쓰면 NEXT_DAY 에서 거짓이 된다.
    assert scr.is_listed_on(_meta()["LIVE"], asof, SNAPSHOT) is True


@pytest.mark.parametrize("asof,expect", [
    ("2026-08-19", True),    # 끊기기 «전» — 그날은 상장 중이었다
    ("2026-08-20", True),    # 마지막 날 당일
    ("2026-08-21", False),   # 그 뒤 — 빠져야 한다
    (NEXT_DAY, False),       # 스냅샷 다음 날에도 여전히 빠져야 한다
])
def test_really_delisted_ticker_still_drops_out(asof, expect):
    # 얼린 날짜를 상한으로 «안» 쓴다고 해서 진짜 상장폐지까지 되살리면 안 된다.
    assert scr.is_listed_on(_meta()["DEAD"], asof, SNAPSHOT) is expect


def test_first_price_date_still_bounds_from_below():
    assert scr.is_listed_on(_meta()["FUTURE"], NEXT_DAY, SNAPSHOT) is False


# ── 유니버스 조립 ─────────────────────────────────────────────────────────

def test_universe_survives_day_after_snapshot(monkeypatch):
    monkeypatch.setattr(scr.us_loader, "load_tickers", lambda v: _meta())
    base = _base(["LIVE", "LIVE2", "DEAD", "FUTURE"])
    u, meta_n, ceiling, snap = scr.build_universe(base, NEXT_DAY)
    assert snap == SNAPSHOT
    assert meta_n == 4
    assert ceiling == 4, "모집단은 «날짜 술어를 걸기 전» 수여야 한다"
    assert [s["code"] for s in u] == ["LIVE", "LIVE2"]


def test_universe_at_snapshot_date_is_unchanged(monkeypatch):
    # 고친 술어가 «오늘» 판을 흔들면 안 된다 — 302 가 나온 그 판이다.
    monkeypatch.setattr(scr.us_loader, "load_tickers", lambda v: _meta())
    base = _base(["LIVE", "LIVE2", "DEAD", "FUTURE"])
    u, _, _, _ = scr.build_universe(base, SNAPSHOT)
    assert [s["code"] for s in u] == ["LIVE", "LIVE2"]


def test_ceiling_counts_only_codes_that_have_bars(monkeypatch):
    monkeypatch.setattr(scr.us_loader, "load_tickers", lambda v: _meta())
    base = _base(["LIVE"])                      # 뼈대에 하나뿐
    u, meta_n, ceiling, _ = scr.build_universe(base, NEXT_DAY)
    assert meta_n == 4 and ceiling == 1 and len(u) == 1


# ── 「0」을 조용히 정상으로 읽지 않는가 ───────────────────────────────────

def test_zero_universe_is_reported_as_breakage():
    r = scr.universe_collapse_reason(0, 4648)
    assert r is not None and "고장" in r


def test_shrunken_universe_is_reported():
    assert scr.universe_collapse_reason(100, 4648) is not None


def test_empty_denominator_is_reported():
    assert scr.universe_collapse_reason(0, 0) is not None


def test_healthy_universe_is_not_reported():
    # 실측 2026-09-09: 4,053 / 4,648 = 87.2%
    assert scr.universe_collapse_reason(4053, 4648) is None


def test_threshold_is_not_an_identity():
    # 분모가 «술어를 통과한 것»이면 비가 언제나 1 이라 이 관문이 질 수가 없다.
    # 분자만 줄여도 걸리는지 본다.
    assert scr.universe_collapse_reason(2325, 4648) is None      # 50.02%
    assert scr.universe_collapse_reason(2323, 4648) is not None  # 49.98%

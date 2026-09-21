"""장전 브리핑의 «순수 로직» 시험.

시세 조회는 안 건드린다(그건 야후 상태에 달렸다). 여기서 지키려는 것은 셋:
  ① 초과수익을 «반드시» 빼는가 — 안 빼면 아홉 섹터가 같은 말을 한다
  ② 못 받은 티커를 «조용히» 평균에 섞지 않는가
  ③ 섹터 태그 없는 감시 종목을 «버리지» 않는가
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_morning_brief import (  # noqa: E402
    basket_return, excess, pct, rank_to_key, sector_rows, theme_overlay, watch_by_bucket,
)


# ── pct ──────────────────────────────────────────────────────

def test_pct_기본():
    assert pct(100.0, 105.0) == pytest.approx(5.0)
    assert pct(100.0, 95.0) == pytest.approx(-5.0)


@pytest.mark.parametrize("prev,cur", [(None, 100.0), (100.0, None), (0.0, 100.0), (None, None)])
def test_pct_못구하면_None(prev, cur):
    assert pct(prev, cur) is None


# ── basket_return ────────────────────────────────────────────

def test_바스켓은_동일가중():
    r = basket_return(["A", "B"], {"A": 10.0, "B": 0.0})
    assert r["ret"] == pytest.approx(5.0)
    assert r["n"] == 2


def test_못받은_티커는_평균에_안_섞인다():
    """3개 중 1개만 받았으면 그 «하나»의 값이지 3으로 나눈 값이 아니다."""
    r = basket_return(["A", "B", "C"], {"A": 9.0, "B": None, "C": None})
    assert r["ret"] == pytest.approx(9.0)
    assert r["n"] == 1
    assert r["missing"] == ["B", "C"]


def test_전부_못받으면_None이고_숨기지_않는다():
    r = basket_return(["A", "B"], {"A": None, "B": None})
    assert r["ret"] is None
    assert r["n"] == 0
    assert r["missing"] == ["A", "B"]


def test_빈_바스켓은_None():
    """조선·백화점처럼 «프록시가 없는» 섹터. 0.0 으로 채우면 「안 움직였다」로 읽힌다."""
    r = basket_return([], {"A": 5.0})
    assert r["ret"] is None
    assert r["n"] == 0


# ── excess ───────────────────────────────────────────────────

def test_초과수익은_기준지수를_뺀다():
    assert excess(5.0, 2.0) == pytest.approx(3.0)


def test_장이_통째로_오르면_초과는_0():
    """이게 이 도구의 존재 이유다 — 「장이 올랐다」를 섹터 신호로 읽지 않는다."""
    assert excess(2.0, 2.0) == pytest.approx(0.0)


def test_섹터가_장보다_덜_오르면_음수():
    assert excess(1.0, 3.0) == pytest.approx(-2.0)


@pytest.mark.parametrize("b,m", [(None, 1.0), (1.0, None), (None, None)])
def test_초과수익도_못구하면_None(b, m):
    assert excess(b, m) is None


# ── rank → key ───────────────────────────────────────────────

def test_rank_를_키로_바꾼다():
    s = [{"rank": 1, "key": "hbm_backend"}, {"rank": 2, "key": "semiconductor"}]
    assert rank_to_key(s) == {1: "hbm_backend", 2: "semiconductor"}


# ── watch_by_sector ──────────────────────────────────────────

def test_감시종목이_업종별로_묶인다():
    watch = [{"code": "001", "name": "가"}, {"code": "002", "name": "나"}]
    a = {"001": {"bucket": "semiconductor"}, "002": {"bucket": "battery"}}
    out = watch_by_bucket(a, watch)
    assert [r["name"] for r in out["semiconductor"]] == ["가"]
    assert [r["name"] for r in out["battery"]] == ["나"]


def test_업종_안_붙은_종목은_버리지_않고_미분류로():
    """sector-map 은 전 종목을 덮으므로 여기로 새면 «그게 관측»이다. 조용히 버리면 안 보인다."""
    watch = [{"code": "001", "name": "가"}, {"code": "999", "name": "샌것"}]
    out = watch_by_bucket({"001": {"bucket": "semiconductor"}}, watch)
    assert [r["name"] for r in out["_미분류"]] == ["샌것"]


def test_배정에_bucket_키가_없으면_미분류():
    out = watch_by_bucket({"001": {}}, [{"code": "001", "name": "가"}])
    assert "_미분류" in out


# ── theme_overlay (테마 축 — «일부»에만 붙는다) ───────────────

_R2K = {1: "hbm_backend", 2: "semiconductor"}


def test_테마는_붙은_종목만_모은다():
    watch = [{"code": "001", "name": "가"}, {"code": "999", "name": "무테마"}]
    assert theme_overlay({"001": {"rank": 1}}, _R2K, watch) == {"hbm_backend": ["가"]}


def test_테마가_하나도_없어도_안_터진다():
    assert theme_overlay({}, _R2K, [{"code": "001", "name": "가"}]) == {}


# ── sector_rows ──────────────────────────────────────────────

_BUCKETS = {
    "semiconductor": {"label": "반도체", "proxy": ["A"]},
    "battery": {"label": "이차전지", "proxy": ["B"]},
    "shipbuilding": {"label": "조선", "proxy": []},
}


def test_초과수익_내림차순으로_정렬된다():
    rows = sector_rows(_BUCKETS, {"A": 1.0, "B": 9.0}, 0.0, {})
    assert [r["key"] for r in rows][:2] == ["battery", "semiconductor"]


def test_미국대응_없는_묶음은_맨_뒤로():
    rows = sector_rows(_BUCKETS, {"A": -9.0, "B": -9.0}, 0.0, {})
    assert rows[-1]["key"] == "shipbuilding"
    assert rows[-1]["has_proxy"] is False


def test_초과수익이_기준지수를_실제로_뺀다():
    """바스켓 +3, 기준 +3 이면 초과는 0 이어야 한다. 3 이 나오면 뺄셈이 빠진 것이다."""
    rows = sector_rows(_BUCKETS, {"A": 3.0, "B": 3.0}, 3.0, {})
    for r in rows:
        if r["has_proxy"]:
            assert r["excess"] == pytest.approx(0.0)


def test_감시종목이_묶음행에_붙는다():
    by = {"semiconductor": [{"code": "001", "name": "가", "status": "breakout",
                             "pivot_price": 100.0, "pattern": "VCP"}]}
    rows = sector_rows(_BUCKETS, {"A": 1.0, "B": 0.0}, 0.0, by)
    sem = next(r for r in rows if r["key"] == "semiconductor")
    assert sem["watch"][0]["name"] == "가"
    assert sem["watch"][0]["pivot_price"] == 100.0


def test_감시종목_없는_묶음도_남는다():
    """오늘 후보에 없다고 그 섹터가 안 움직인 것은 아니다. 내일 들어올 수 있다."""
    rows = sector_rows(_BUCKETS, {"A": 1.0, "B": 2.0}, 0.0, {})
    assert len(rows) == 3
    assert all(r["watch"] == [] for r in rows)

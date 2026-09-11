"""이음매 분할 보정 시험.

가격 자료를 «조용히» 망가뜨릴 수 있는 자리라서 인공 자료로 알려진 답을 만든다.
검사하는 것 일곱:
  1. 알려진 분할(2대1 · 3대1 · 1대10 병합)에서 가격과 거래량이 «둘 다» 맞는가
  2. 거래대금(가격 곱하기 거래량)이 보존되는가
  3. 여러 분할이 곱해지는가
  4. 멱등성 — 보정한 결과를 다시 넣어도 또 보정되지 않는가
  5. 기준일 당일 분할의 두 갈래(이미 반영됨 / 안 됨)가 갈리는가
  6. 확인에 실패하면 멈추는가(그 종목이 자료에서 빠지는가)
  7. 입력 뼈대 dict 를 건드리지 않는가(정본은 얼려 있어야 한다)

★ 배수 규약: 야후의 ratio 는 「주식 수 배수」다. 2대1 분할이면 2.0, 1대10
  병합이면 0.1. 분할 전 봉은 가격을 ratio 로 «나누고» 거래량에 ratio 를 «곱한다».
"""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import us_seam  # noqa: E402


def _series(dates, closes, volumes):
    """가격 네 필드를 같은 값으로 채운 인공 계열(고가·저가·시가도 함께 검사하려고)."""
    return {"dates": list(dates),
            "opens": [c * 0.99 for c in closes],
            "highs": [c * 1.01 for c in closes],
            "lows": [c * 0.98 for c in closes],
            "closes": list(closes),
            "volumes": list(volumes),
            "timestamps": list(range(len(dates)))}


def _base(code, dates, closes, volumes, asof=None):
    return {"asof": asof or dates[-1], "trim": 310,
            "series": {code: _series(dates, closes, volumes)}}


def _tail(code, dates, closes, volumes):
    s = _series(dates, closes, volumes)
    s.pop("timestamps")
    return {code: s}


# ── 1. 알려진 분할 셋 — 가격과 거래량 둘 다 ────────────────────────────────

@pytest.mark.parametrize("ratio,label", [
    (2.0, "2대1 액면분할"),
    (3.0, "3대1 액면분할"),
    (0.1, "1대10 주식병합"),
])
def test_known_split_fixes_price_and_volume(ratio, label):
    # 뼈대는 분할 «전» 기준(100달러·1,000주), 꼬리는 분할 «후» 기준.
    base = _base("X", ["2026-09-08", "2026-09-09"], [100.0, 100.0],
                 [1000.0, 1000.0])
    tail = _tail("X", ["2026-09-09", "2026-09-10"],
                 [100.0 / ratio, 100.0 / ratio],
                 [1000.0 * ratio, 1000.0 * ratio])
    splits = [{"code": "X", "date": "2026-09-10", "ratio": ratio}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)

    assert [r["code"] for r in rep["adjusted"]] == ["X"], label
    assert rep["blocked"] == [] and rep["unchanged"] == []
    s = out["series"]["X"]
    for c in s["closes"]:
        assert c == pytest.approx(100.0 / ratio), f"{label}: 가격은 배수로 나눈다"
    for v in s["volumes"]:
        assert v == pytest.approx(1000.0 * ratio), f"{label}: 거래량은 배수로 곱한다"
    # 시가·고가·저가도 같이 옮겨져야 한다(종가만 고치면 봉이 찌그러진다)
    assert s["opens"][0] == pytest.approx(99.0 / ratio)
    assert s["highs"][0] == pytest.approx(101.0 / ratio)
    assert s["lows"][0] == pytest.approx(98.0 / ratio)


# ── 2. 거래대금 보존 — 유동성 관문이 멀쩡한 종목을 떨어뜨리지 않는 근거 ────

@pytest.mark.parametrize("ratio", [2.0, 3.0, 0.1])
def test_turnover_is_preserved(ratio):
    base = _base("X", ["2026-09-08", "2026-09-09"], [100.0, 120.0],
                 [1000.0, 2500.0])
    before = [c * v for c, v in zip(base["series"]["X"]["closes"],
                                    base["series"]["X"]["volumes"])]
    tail = _tail("X", ["2026-09-09"], [120.0 / ratio], [2500.0 * ratio])
    splits = [{"code": "X", "date": "2026-09-10", "ratio": ratio}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert rep["adjusted"], "보정이 일어나야 이 시험이 뜻이 있다"
    s = out["series"]["X"]
    after = [c * v for c, v in zip(s["closes"], s["volumes"])]
    for a, b in zip(after, before):
        assert a == pytest.approx(b), "거래대금이 보존돼야 한다"


# ── 3. 여러 분할은 곱해진다 ────────────────────────────────────────────────

def test_multiple_splits_multiply():
    base = _base("X", ["2026-09-08", "2026-09-09"], [60.0, 60.0],
                 [1000.0, 1000.0])
    # 2배 그리고 3배 = 6배. 가격 60 -> 10, 거래량 1,000 -> 6,000.
    tail = _tail("X", ["2026-09-09"], [10.0], [6000.0])
    splits = [{"code": "X", "date": "2026-09-10", "ratio": 2.0},
              {"code": "X", "date": "2026-09-12", "ratio": 3.0}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert rep["adjusted"][0]["ratio"] == pytest.approx(6.0)
    s = out["series"]["X"]
    assert s["closes"] == pytest.approx([10.0, 10.0])
    assert s["volumes"] == pytest.approx([6000.0, 6000.0])


# ── 4. 멱등성 — 보정 결과를 다시 넣어도 또 먹지 않는다 ─────────────────────

def test_feeding_output_back_never_applies_the_split_twice():
    """보정한 결과를 다시 넣어도 보정이 «두 번» 먹지 않는다.

    실제 파이프라인에서는 늘 얼린 뼈대를 다시 읽으므로 이런 일이 없어야 하지만,
    누가 합본을 뼈대 자리에 넣으면 값이 조용히 망가진다. 그래서 그때는 조용히
    넘어가지 않고 «멈춘다» — 분할일이 마지막 봉보다 뒤인데 관측비가 1 이면
    「이미 반영됐다」와 「둘 다 아직 안 했다」를 가를 수가 없기 때문이다.
    """
    base = _base("X", ["2026-09-08", "2026-09-09"], [100.0, 100.0],
                 [1000.0, 1000.0])
    tail = _tail("X", ["2026-09-09", "2026-09-10"], [50.0, 51.0],
                 [2000.0, 2100.0])
    splits = [{"code": "X", "date": "2026-09-10", "ratio": 2.0}]

    once, rep1 = us_seam.adjust_base_for_splits(base, splits, tail)
    twice, rep2 = us_seam.adjust_base_for_splits(once, splits, tail)

    assert rep1["adjusted"] and not rep1["unchanged"]
    assert rep2["adjusted"] == [], "두 번째에 또 보정하면 안 된다"
    assert len(rep2["blocked"]) == 1
    assert "X" not in twice["series"]
    # 첫 번째 결과 자체는 그대로다(두 번째가 값을 또 건드리지 않았다)
    assert once["series"]["X"]["closes"] == pytest.approx([50.0, 50.0])


def test_same_input_twice_gives_same_output():
    base = _base("X", ["2026-09-08", "2026-09-09"], [100.0, 100.0],
                 [1000.0, 1000.0])
    tail = _tail("X", ["2026-09-09"], [50.0], [2000.0])
    splits = [{"code": "X", "date": "2026-09-10", "ratio": 2.0}]
    a, _ = us_seam.adjust_base_for_splits(base, splits, tail)
    b, _ = us_seam.adjust_base_for_splits(base, splits, tail)
    assert a["series"]["X"]["closes"] == pytest.approx(b["series"]["X"]["closes"])


# ── 5. 기준일 당일 분할 — 두 갈래가 갈리는가 ───────────────────────────────

def test_split_on_asof_already_reflected_is_left_alone():
    """뼈대가 이미 분할을 반영한 경우. 또 보정하면 두 번 먹는다.

    1대10 병합이 기준일 당일에 났고 Sharadar 가 이미 과거를 환산해 뒀다.
    기준일 봉은 «분할 후» 시세이고 야후도 같은 값이라 관측비가 1 이다.
    """
    base = _base("PH", ["2026-09-04", "2026-09-09"], [1.477, 1.62],
                 [211000.0, 535000.0])
    tail = _tail("PH", ["2026-09-09", "2026-09-10"], [1.62, 1.85],
                 [745600.0, 3337000.0])
    splits = [{"code": "PH", "date": "2026-09-09", "ratio": 0.1}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert [r["code"] for r in rep["unchanged"]] == ["PH"]
    assert rep["adjusted"] == [] and rep["blocked"] == []
    assert out["series"]["PH"]["closes"] == pytest.approx([1.477, 1.62]), \
        "이미 반영된 뼈대는 손대면 안 된다"
    assert out["series"]["PH"]["volumes"] == pytest.approx([211000.0, 535000.0])


def test_split_on_asof_not_yet_reflected_is_adjusted():
    """같은 날 분할인데 뼈대가 «아직» 반영 안 한 경우 — 보정해야 한다.

    분할일이 뼈대 마지막 날보다 «뒤»이고 야후는 이미 환산했다.
    관측비가 분할비율과 같게 나와 「뼈대가 분할 전」으로 갈린다(실제 LFT 모양).
    """
    base = _base("LF", ["2026-09-08", "2026-09-09"], [0.695, 0.692],
                 [139000.0, 138000.0])
    tail = _tail("LF", ["2026-09-09", "2026-09-10"], [6.92, 6.83],
                 [13800.0, 20200.0])
    splits = [{"code": "LF", "date": "2026-09-10", "ratio": 0.1}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert [r["code"] for r in rep["adjusted"]] == ["LF"]
    s = out["series"]["LF"]
    assert s["closes"] == pytest.approx([6.95, 6.92])
    assert s["volumes"] == pytest.approx([13900.0, 13800.0])


def test_bar_on_split_day_is_not_touched():
    """분할일 «당일» 봉은 이미 분할 후 가격이라 건드리면 안 된다."""
    base = _base("X", ["2026-09-08", "2026-09-09"], [100.0, 50.0],
                 [1000.0, 2000.0])
    tail = _tail("X", ["2026-09-09"], [50.0], [2000.0])
    splits = [{"code": "X", "date": "2026-09-09", "ratio": 2.0}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    # 관측비 50/50 = 1 이라 「이미 반영됐다」로 갈린다 — 손대지 않는다.
    assert [r["code"] for r in rep["unchanged"]] == ["X"]
    assert out["series"]["X"]["closes"] == pytest.approx([100.0, 50.0])


def test_factor_per_bar_only_counts_later_splits():
    dates = ["2026-09-08", "2026-09-09", "2026-09-10"]
    sp = [{"code": "X", "date": "2026-09-09", "ratio": 2.0},
          {"code": "X", "date": "2026-09-11", "ratio": 3.0}]
    assert us_seam._factor_per_bar(dates, sp) == pytest.approx([6.0, 3.0, 3.0])


# ── 6. 확인에 실패하면 멈춘다(그 종목이 자료에서 빠진다) ───────────────────

def test_unknown_ratio_blocks_and_drops_the_code():
    base = _base("X", ["2026-09-08", "2026-09-09"], [100.0, 100.0],
                 [1000.0, 1000.0])
    # 관측비 100/73 = 1.37 — 분할비율(2.0)도 1 도 아니다.
    tail = _tail("X", ["2026-09-09"], [73.0], [1000.0])
    splits = [{"code": "X", "date": "2026-09-10", "ratio": 2.0}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert [r["code"] for r in rep["blocked"]] == ["X"]
    assert "X" not in out["series"], "멈춘 종목은 합본에서 빠져야 한다"


def test_no_overlapping_bar_blocks():
    """뼈대 마지막 날이 꼬리에 없으면 견줄 수가 없다 — 멈춘다."""
    base = _base("CY", ["2026-09-07", "2026-09-08"], [26.0, 23.94],
                 [14900.0, 8900.0], asof="2026-09-09")
    tail = {}          # 야후에 그 날 봉이 아예 없다
    splits = [{"code": "CY", "date": "2026-09-09", "ratio": 1.0 / 7.0}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert len(rep["blocked"]) == 1
    assert "잴 수가 없다" in rep["blocked"][0]["reason"]
    assert "CY" not in out["series"]


def test_split_after_last_bar_with_ratio_one_blocks():
    """실제 CYCN 모양 — 「관측비 1」이 「이미 반영됐다」가 «아닌» 경우.

    기준일 당일 1대7 병합인데 뼈대 마지막 봉은 그 하루 앞이고, 야후도 아직
    환산을 안 해서 두 자료가 그 봉에서 같다. 이대로 「이미 반영됐다」로 넘기면
    야후가 분할 후 봉을 내놓는 날 7배 가짜 계단이 조용히 붙는다.
    """
    base = _base("CY", ["2026-09-04", "2026-09-08"], [29.75, 23.94],
                 [14900.0, 8900.0], asof="2026-09-09")
    tail = _tail("CY", ["2026-09-08"], [23.52], [62228.0])
    splits = [{"code": "CY", "date": "2026-09-09", "ratio": 1.0 / 7.0}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert rep["unchanged"] == [], "「이미 반영됐다」로 새면 안 된다"
    assert len(rep["blocked"]) == 1
    assert "야후도 아직 환산을 안 했다" in rep["blocked"][0]["reason"]
    assert "CY" not in out["series"]


def test_seam_recheck_blocks_when_adjustment_cannot_close_the_gap():
    """보정 «뒤» 확인이 실제로 질 수 있다는 증거.

    분할일이 뼈대 마지막 날과 «같으면» 마지막 봉은 보정 대상이 아니다. 그런데
    관측비가 분할비율과 같게 나오면 분류는 「보정」으로 가고, 보정해도 이음매가
    안 닫힌다 — 그때 조용히 넘기지 않고 멈춰야 한다.
    """
    base = _base("X", ["2026-09-08", "2026-09-09"], [100.0, 100.0],
                 [1000.0, 1000.0])
    tail = _tail("X", ["2026-09-09"], [50.0], [1000.0])   # 관측비 2.0 = 분할비율
    splits = [{"code": "X", "date": "2026-09-09", "ratio": 2.0}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert len(rep["blocked"]) == 1
    assert "이음매가 안 맞는다" in rep["blocked"][0]["reason"]
    assert "X" not in out["series"]


def test_ratio_outside_bounds_blocks():
    base = _base("X", ["2026-09-09"], [100.0], [1000.0])
    tail = _tail("X", ["2026-09-09"], [100.0], [1000.0])
    splits = [{"code": "X", "date": "2026-09-10", "ratio": 1000.0}]
    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert len(rep["blocked"]) == 1
    assert "X" not in out["series"]


def test_code_missing_from_base_blocks():
    base = _base("X", ["2026-09-09"], [100.0], [1000.0])
    tail = _tail("Y", ["2026-09-09"], [50.0], [2000.0])
    splits = [{"code": "Y", "date": "2026-09-10", "ratio": 2.0}]
    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert [r["code"] for r in rep["blocked"]] == ["Y"]
    assert "X" in out["series"], "관계없는 종목은 그대로 있어야 한다"


# ── 7. 뼈대 정본은 얼려 있어야 한다 ───────────────────────────────────────

def test_input_base_is_not_mutated():
    base = _base("X", ["2026-09-08", "2026-09-09"], [100.0, 100.0],
                 [1000.0, 1000.0])
    snapshot = copy.deepcopy(base)
    tail = _tail("X", ["2026-09-09"], [50.0], [2000.0])
    splits = [{"code": "X", "date": "2026-09-10", "ratio": 2.0}]

    us_seam.adjust_base_for_splits(base, splits, tail)
    assert base == snapshot, "입력 뼈대 dict 를 건드리면 안 된다(정본은 얼림)"


def test_no_splits_returns_everything_unchanged():
    base = _base("X", ["2026-09-08", "2026-09-09"], [100.0, 100.0],
                 [1000.0, 1000.0])
    out, rep = us_seam.adjust_base_for_splits(base, [], {})
    assert rep == {"adjusted": [], "unchanged": [], "blocked": []}
    assert out["series"]["X"]["closes"] == pytest.approx([100.0, 100.0])
    assert out["asof"] == base["asof"]


# ── 보고가 실제로 무엇을 고쳤는지 말하는가 ────────────────────────────────

def test_report_names_what_changed_and_what_failed():
    base = {"asof": "2026-09-09", "trim": 310, "series": {
        "A": _series(["2026-09-08", "2026-09-09"], [100.0, 100.0],
                     [1000.0, 1000.0]),
        "B": _series(["2026-09-08", "2026-09-09"], [1.477, 1.62],
                     [211000.0, 535000.0]),
        "C": _series(["2026-09-08", "2026-09-09"], [100.0, 100.0],
                     [1000.0, 1000.0])}}
    tail = {"A": _series(["2026-09-09"], [50.0], [2000.0]),
            "B": _series(["2026-09-09"], [1.62], [745600.0]),
            "C": _series(["2026-09-09"], [73.0], [1000.0])}
    for v in tail.values():
        v.pop("timestamps")
    splits = [{"code": "A", "date": "2026-09-10", "ratio": 2.0},
              {"code": "B", "date": "2026-09-09", "ratio": 0.1},
              {"code": "C", "date": "2026-09-10", "ratio": 2.0}]

    out, rep = us_seam.adjust_base_for_splits(base, splits, tail)
    assert [r["code"] for r in rep["adjusted"]] == ["A"]
    assert [r["code"] for r in rep["unchanged"]] == ["B"]
    assert [r["code"] for r in rep["blocked"]] == ["C"]
    text = us_seam.format_split_report(rep)
    assert "보정 1" in text and "그대로 1" in text and "멈춤 1" in text
    assert "[보정] A" in text and "[그대로] B" in text and "[멈춤] C" in text

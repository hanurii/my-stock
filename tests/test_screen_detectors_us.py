"""미국 SEPA 2단계 공용 각본(screen_detectors_us.py) 시험.

여기서 재는 것은 «검출기»가 아니라 «검출기에 무엇을 먹이는가»다.
검출기 판정은 한국 모듈의 시험이 이미 덮는다 — 같은 모듈을 그대로 쓴다.

🔴 _cut 은 오늘 자료로는 «한 번도 안 도는» 갈래다(시세 최신일 = 1단계 기준일).
   1단계를 --asof 로 과거에 돌린 날에만 돈다. 그런 갈래야말로 시험이 없으면
   틀린 채로 몇 달을 산다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import screen_detectors_us as sd  # noqa: E402


def _series(dates):
    n = len(dates)
    return {"dates": list(dates),
            "opens": [float(i) for i in range(n)],
            "highs": [float(i) for i in range(n)],
            "lows": [float(i) for i in range(n)],
            "closes": [float(i) for i in range(n)],
            "volumes": [float(i) for i in range(n)],
            "timestamps": list(range(n))}


DATES = ["2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10"]


def test_cut_truncates_every_axis_to_the_same_length():
    """축을 따로 자르면 «어긋난» 계열이 조용히 생긴다 — 길이가 다 같아야 한다."""
    out = sd._cut(_series(DATES), "2026-09-08")
    assert out["dates"] == ["2026-09-07", "2026-09-08"]
    lengths = {k: len(v) for k, v in out.items() if isinstance(v, list)}
    assert set(lengths.values()) == {2}, f"축 길이가 어긋났다: {lengths}"


def test_cut_keeps_the_asof_bar_itself():
    """asof «당일» 봉은 남긴다 — 1단계가 그 봉으로 판정했기 때문이다."""
    out = sd._cut(_series(DATES), "2026-09-09")
    assert out["dates"][-1] == "2026-09-09"


def test_cut_is_noop_when_asof_is_at_or_after_the_last_bar():
    s = _series(DATES)
    assert sd._cut(s, "2026-09-10") is s
    assert sd._cut(s, "2026-12-31") is s
    assert sd._cut(s, None) is s


def test_cut_does_not_mutate_the_input():
    """us_matrix 의 전역 캐시를 그대로 넘기므로 «제자리»에서 자르면 안 된다.

    한 종목을 자른 결과가 캐시에 남으면 다음 종류(--kind)를 돌릴 때 «더 짧은»
    계열을 보게 된다 — 값도 아니고 순서도 아닌, 아무 데도 안 찍히는 차이다.
    """
    s = _series(DATES)
    sd._cut(s, "2026-09-08")
    assert s["dates"] == DATES
    assert len(s["closes"]) == 4


def test_empty_result_shape_comes_from_the_module_not_a_copy():
    """「시세 없음」 레코드의 «모양»을 손으로 베끼지 않았는가.

    각본은 fn({}) 을 불러 빈 결과를 만든다. 그래야 검출기가 필드를 늘릴 때
    빈 레코드도 같이 따라간다(한국 각본은 EMPTY 를 손으로 적어 두어 갈라질 수 있다).
    """
    for kind, (fn, defaults, detected_key, _label) in sd.EVALS.items():
        r = fn({})
        assert isinstance(r, dict), kind
        assert r.get("status") in ("breakout", "actionable", "forming", "failed"), kind
        assert detected_key in r, f"{kind}: 검출 여부 키 {detected_key} 가 없다"
        assert r[detected_key] is False, kind
        assert r.get("entry_ready") is False, kind
        assert isinstance(defaults, dict) and defaults, kind


def test_kinds_and_output_paths_line_up():
    """--kind 셋 · 산출 경로 셋 · 접두는 반드시 sepa-us- (한국 파일과 이름이 닮았다).

    🔴 ipo 는 «없다». 사용자 결정 2026-09-11 — 27.4년 하네스가 ipo_track 을 한 번도
       안 돌려서 미국에서 잰 적이 없다. 되살리려면 «먼저» 하네스로 재야 한다.
       이 시험이 「조용히 다시 생기는 것」을 막는다.
    """
    assert sd.KINDS == ["3c", "power-play", "vcp"]
    assert set(sd.OUT) == set(sd.KINDS)
    assert set(sd.EVALS) == set(sd.KINDS), "셋 다 계열을 받는 검출기여야 한다"
    assert "ipo" not in sd.KINDS and not hasattr(sd, "run_ipo")
    for kind, p in sd.OUT.items():
        assert p.name == f"sepa-us-{kind}-candidates.json"
        assert p.parent.name == "data"


def test_no_params_are_passed_to_the_detectors():
    """얼린 값 우회 금지 — 각본이 검출기에 params 를 넘기면 안 된다.

    글자로 본다. 「안 넘긴다」는 주석이 아니라 «파일»이 근거여야 한다.
    주석·docstring 은 빼고 «도는 코드»만 본다 — 머리글이 검출기 서명을 적어 두었다.
    """
    import ast
    src = (Path(sd.__file__)).read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    named = {ast.unparse(n.func) for n in calls}
    for bad in ("vcp.evaluate_vcp", "power_play.evaluate_power_play",
                "cheat.evaluate_cheat", "ipo_track.evaluate_ipo_track"):
        # EVALS 표에 «이름»으로만 들어가야 한다 — 호출 자리가 있으면 안 된다.
        assert bad not in named, f"검출기를 직접 호출한다: {bad}"
    # 실제 호출은 fn(s) / fn({}) 둘뿐이고 둘 다 인자가 «하나»다(params 없음).
    fn_calls = [n for n in calls if ast.unparse(n.func) == "fn"]
    assert fn_calls, "fn(...) 호출이 없다"
    for n in fn_calls:
        assert len(n.args) == 1 and not n.keywords, (
            f"fn 에 인자가 둘 이상이다: {ast.unparse(n)}")
    # 금지는 «구조»로 — 안 쓸 것은 import 조차 안 한다.
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[-1] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported |= {a.name for a in n.names}
    assert "ipo_track" not in imported, "ipo_track 을 import 조차 하지 않는다"
    assert not hasattr(sd, "ipo_track")
    # 한국 쪽은 «그대로»여야 한다 — 미국에서 뺀 것이 한국을 건드리면 안 된다.
    assert (Path(sd.__file__).parent / "screen_ipo_track.py").exists()
    assert (Path(sd.__file__).parent / "canslim_lib" / "ipo_track.py").exists()


# ──────────────────────────────────────────────────────────────────────
# run_detector 를 «실제로» 부르는 시험
#
# 🔴 왜 있나: 2026-09-11 검토에서 «돌연변이»로 드러났다 — 술어와 기준일 관문을
#    «둘 다 무력화해도» 시험 7개가 전부 통과했다. 시험이 「도우미」에만 붙고
#    «고친 줄»에는 안 붙어 있었다. 아래 시험은 고친 줄을 «무력화하면 깨지도록»
#    짰고, 실제로 깨지는지 하나씩 확인했다(보고서에 표로 남김).
# ──────────────────────────────────────────────────────────────────────
import json                                                    # noqa: E402
import pytest                                                  # noqa: E402
from canslim_lib import us_matrix                              # noqa: E402

D5 = ["2026-09-03", "2026-09-04", "2026-09-07", "2026-09-08", "2026-09-09"]


def _rec(code, **kw):
    r = {"code": code, "name": code, "market": "NYSE", "current_price": 10.0,
         "rs": 90, "turnover_eok": 100.0, "all_pass": False}
    r.update(kw)
    return r


class _Spy:
    """검출기 자리에 끼우는 첩자 — «무엇을 먹였는지»와 «무엇을 돌려줄지»를 잡는다."""

    def __init__(self, results=None):
        self.seen = {}          # code -> 넘어온 series
        self.order = []
        self.results = results or {}
        self._code = None

    def feed(self, code):
        self._code = code

    def __call__(self, series):
        self.order.append(self._code)
        self.seen[self._code] = series
        if not series:                      # fn({}) — «빈» 결과
            return {"vcp_detected": False, "status": "forming",
                    "entry_ready": False, "pivot_price": None,
                    "pct_to_pivot": None, "reason": "no_data"}
        return dict(self.results.get(self._code, {
            "vcp_detected": False, "status": "forming", "entry_ready": False,
            "pivot_price": None, "pct_to_pivot": None}))


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """stage1 파일·시세·검출기를 전부 가짜로 갈아 끼우고 run_detector 를 돌린다."""
    spy = _Spy()

    def setup(records, series_by_code, asof="2026-09-09", results=None):
        spy.results = results or {}
        in_path = tmp_path / "stage1.json"
        in_path.write_text(json.dumps({
            "asof": asof, "all_pass_count": sum(1 for r in records if r["all_pass"]),
            "candidates": records}), encoding="utf-8")
        out_path = tmp_path / "out.json"
        monkeypatch.setattr(sd, "IN_PATH", in_path)
        monkeypatch.setattr(sd, "OUT", {**sd.OUT, "vcp": out_path})
        monkeypatch.setattr(us_matrix, "load_latest",
                            lambda: ({"asof": asof}, us_matrix.BASE_PATH))

        def fake_get_series(code):
            spy.feed(code)
            s = series_by_code.get(code)
            return dict(s) if s else None
        monkeypatch.setattr(us_matrix, "get_series", fake_get_series)
        monkeypatch.setattr(sd, "EVALS", {**sd.EVALS,
                                          "vcp": (spy, {"x": 1}, "vcp_detected", "VCP")})
        sd.run_detector("vcp")
        return json.loads(out_path.read_text(encoding="utf-8")), spy

    return setup


def _series(dates):
    n = len(dates)
    return {"dates": list(dates), "opens": [1.0] * n, "highs": [1.0] * n,
            "lows": [1.0] * n, "closes": [1.0] * n, "volumes": [1.0] * n,
            "timestamps": list(range(n))}


def test_run_detector_takes_all_pass_only_not_gate_near(harness):
    """A — 술어가 하네스(GATE_NEAR_ALLOW=set())보다 «넓으면» 깨진다.

    무력화 시험: 술어를 `all_pass or gate_near` 로 되돌리면 GN 이 들어와 깨진다.
    """
    recs = [_rec("PASS", all_pass=True),
            _rec("FAIL"),
            _rec("GN", gate_near=True, gate_near_reasons=["1"])]
    series = {c: _series(D5) for c in ("PASS", "FAIL", "GN")}
    out, _ = harness(recs, series)
    codes = [x["code"] for x in out["candidates"]]
    assert codes == ["PASS"], f"관문 통과만 들어와야 한다: {codes}"
    assert out["input_n"] == 1
    assert out["stage1_gate_near_n"] == 1, "임박 수는 «세어서 찍되» 넣지 않는다"


def test_run_detector_cuts_series_to_stage1_asof(harness):
    """B/③ — asof 자르기가 «run_detector 안에서» 실제로 걸리는가.

    무력화 시험: `s = _cut(s, asof)` 를 지우면 첩자가 5봉을 보게 되어 깨진다.
    """
    recs = [_rec("A", all_pass=True)]
    out, spy = harness(recs, {"A": _series(D5)}, asof="2026-09-07")
    fed = spy.seen["A"]
    assert fed["dates"] == ["2026-09-03", "2026-09-04", "2026-09-07"], fed["dates"]
    assert len(fed["closes"]) == 3, "축이 어긋났다"
    assert out["candidates"][0].get("data_note") is None


def test_run_detector_marks_stale_when_last_bar_predates_asof(harness):
    """기준일 관문 — 마지막 봉이 기준일보다 «과거»면 평가하지 않는다.

    무력화 시험: `if not dates or dates[-1] != asof:` 를 지우면 첩자가 진짜
    계열을 받게 되어 깨진다.
    """
    recs = [_rec("OLD", all_pass=True)]
    out, spy = harness(recs, {"OLD": _series(D5[:2])}, asof="2026-09-09")
    assert out["stale_bar_n"] == 1
    assert out["candidates"][0]["data_note"].startswith("stale:")
    assert spy.seen["OLD"] == {}, "기준일이 어긋난 종목은 «빈» 것으로 평가해야 한다"


def test_run_detector_entry_count_is_actionable_only(harness):
    """B — 진입 수는 하네스 정의(actionable)만 센다. breakout 은 따로.

    무력화 시험: `status in HARNESS_ENTRY_STATUSES` 를
    `in ("breakout","actionable")` 로 넓히면 3이 되어 깨진다.
    """
    recs = [_rec(c, all_pass=True) for c in ("ACT", "BRK", "FORM")]
    series = {c: _series(D5) for c in ("ACT", "BRK", "FORM")}
    results = {
        "ACT": {"vcp_detected": True, "status": "actionable", "entry_ready": True,
                "pivot_price": 10.0, "pct_to_pivot": 1.0},
        "BRK": {"vcp_detected": True, "status": "breakout", "entry_ready": True,
                "pivot_price": 9.0, "pct_to_pivot": -1.0},
        "FORM": {"vcp_detected": True, "status": "forming", "entry_ready": False,
                 "pivot_price": 11.0, "pct_to_pivot": 9.0},
    }
    out, _ = harness(recs, series, results=results)
    assert out["entry_ready_count"] == 1, "진입은 actionable 하나뿐이어야 한다"
    assert out["already_breakout_count"] == 1
    assert out["module_entry_ready_count"] == 2, "모듈 자는 둘을 합친 값"
    assert out["entry_ready_count"] + out["already_breakout_count"] == \
        out["module_entry_ready_count"]
    assert "actionable" in out["entry_definition"]
    assert "backtest_volatility_pilot_us.py" in out["entry_definition"]


def test_run_detector_entry_requires_a_pivot_price(harness):
    """하네스 :288 의 «셋째» 조건 — 피벗이 없으면 진입이 아니다.

    무력화 시험: `and x.get("pivot_price")` 를 지우면 1이 되어 깨진다.
    """
    recs = [_rec("NOPIV", all_pass=True)]
    out, _ = harness(recs, {"NOPIV": _series(D5)}, results={
        "NOPIV": {"vcp_detected": True, "status": "actionable",
                  "entry_ready": True, "pivot_price": None, "pct_to_pivot": None}})
    assert out["entry_ready_count"] == 0, "피벗 없는 종목은 주문을 걸 수 없다"


def test_harness_constants_are_read_not_transcribed():
    """A·B 의 두 값은 하네스에서 «읽어» 온 것이어야 한다(자가 둘이면 안 된다)."""
    import backtest_volatility_pilot_us as H
    assert sd.HARNESS_ENTRY_STATUSES == frozenset(H.ENTRY_STATUSES)
    assert sd.HARNESS_GATE_NEAR_ALLOW == frozenset(H.GATE_NEAR_ALLOW)
    # 글자 검색이 아니라 «대입 오른쪽»을 본다 — 주석은 하네스 줄을 그대로 인용한다.
    import ast
    tree = ast.parse((Path(sd.__file__)).read_text(encoding="utf-8"))
    rhs = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and                 isinstance(n.targets[0], ast.Name):
            rhs[n.targets[0].id] = ast.unparse(n.value)
    assert rhs["HARNESS_ENTRY_STATUSES"] == "frozenset(_harness.ENTRY_STATUSES)",         f"베껴 적었다: {rhs['HARNESS_ENTRY_STATUSES']}"
    assert rhs["HARNESS_GATE_NEAR_ALLOW"] == "frozenset(_harness.GATE_NEAR_ALLOW)",         f"베껴 적었다: {rhs['HARNESS_GATE_NEAR_ALLOW']}"

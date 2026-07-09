import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.watchlist import load_actionable, load_watchlist_broad, build_ew_index

def test_load_actionable(tmp_path):
    f = tmp_path / "sepa-vcp-candidates.json"
    f.write_text(json.dumps({"candidates": [
        {"code": "005930", "name": "삼성전자", "status": "actionable", "entry_ready": True, "pivot_price": 70000.0},
        {"code": "000660", "name": "SK", "status": "forming", "entry_ready": False, "pivot_price": 50000.0},   # 제외(forming)
        {"code": "005930", "name": "삼성전자", "status": "actionable", "entry_ready": True, "pivot_price": 70000.0},  # 중복
    ]}, ensure_ascii=False), encoding="utf-8")
    out = load_actionable([str(f)])
    assert len(out) == 1 and out[0]["code"] == "005930" and out[0]["pivot"] == 70000.0

def test_load_actionable_excludes_pattern_not_detected(tmp_path):
    # status=='actionable'이라도 entry_ready(=패턴 확정)가 아니면 제외.
    # 검출기는 가격이 피벗 5% 이내 + 거래량 마름이면 패턴 미검출이어도 status=actionable을 찍는다.
    # 봇 감시목록은 페이지 🟢진입임박(detected && actionable)과 동일하게 entry_ready를 요구해야 한다.
    f = tmp_path / "sepa-vcp-candidates.json"
    f.write_text(json.dumps({"candidates": [
        {"code": "005680", "name": "삼영전자", "status": "actionable", "entry_ready": False, "pivot_price": 16169.59},  # 제외(미검출)
        {"code": "049430", "name": "코메론", "status": "actionable", "pivot_price": 20798.77},  # 제외(entry_ready 부재)
        {"code": "111111", "name": "진짜", "status": "actionable", "entry_ready": True, "pivot_price": 1000.0},  # 유지
    ]}, ensure_ascii=False), encoding="utf-8")
    out = load_actionable([str(f)])
    assert [c["code"] for c in out] == ["111111"]

def test_build_ew_index():
    # 두 종목 상승 → 지수 상승
    series = {"A": {"dates": ["d1","d2","d3"], "closes": [100,110,121]},
              "B": {"dates": ["d1","d2","d3"], "closes": [50,55,60.5]}}
    idx = build_ew_index(lambda c: series.get(c), ["A","B"])
    assert len(idx) == 3 and idx[-1] > idx[0]


def _write(tmp_path, name, candidates):
    p = tmp_path / name
    p.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
    return str(p)


def test_broad_includes_actionable_and_forming(tmp_path):
    vcp = _write(tmp_path, "sepa-vcp-candidates.json", [
        {"code": "A", "name": "에이", "status": "actionable", "pivot_price": 100.0},
        {"code": "B", "name": "비", "status": "forming", "pivot_price": 200.0},
    ])
    codes = {r["code"] for r in load_watchlist_broad([vcp])}
    assert codes == {"A", "B"}


def test_broad_excludes_breakout_failed_and_no_pivot(tmp_path):
    vcp = _write(tmp_path, "sepa-vcp-candidates.json", [
        {"code": "A", "name": "에이", "status": "breakout", "pivot_price": 100.0},
        {"code": "B", "name": "비", "status": "failed", "pivot_price": 200.0},
        {"code": "C", "name": "씨", "status": "forming", "pivot_price": None},
    ])
    assert load_watchlist_broad([vcp]) == []


def test_broad_dedup_priority_vcp_over_3c_over_pp(tmp_path):
    vcp = _write(tmp_path, "sepa-vcp-candidates.json", [
        {"code": "A", "name": "에이", "status": "forming", "pivot_price": 100.0}])
    c3 = _write(tmp_path, "sepa-3c-candidates.json", [
        {"code": "A", "name": "에이", "status": "actionable", "pivot_price": 111.0},
        {"code": "B", "name": "비", "status": "forming", "pivot_price": 222.0}])
    pp = _write(tmp_path, "sepa-power-play-candidates.json", [
        {"code": "B", "name": "비", "status": "forming", "pivot_price": 999.0}])
    out = {r["code"]: r for r in load_watchlist_broad([vcp, c3, pp])}
    assert out["A"]["pattern"] == "VCP" and out["A"]["pivot"] == 100.0
    assert out["B"]["pattern"] == "3C" and out["B"]["pivot"] == 222.0


def test_broad_priority_independent_of_path_order(tmp_path):
    vcp = _write(tmp_path, "sepa-vcp-candidates.json", [
        {"code": "A", "name": "에이", "status": "forming", "pivot_price": 100.0}])
    c3 = _write(tmp_path, "sepa-3c-candidates.json", [
        {"code": "A", "name": "에이", "status": "actionable", "pivot_price": 111.0}])
    # 3C를 먼저 넘겨도 VCP가 이겨야 함
    out = {r["code"]: r for r in load_watchlist_broad([c3, vcp])}
    assert out["A"]["pattern"] == "VCP"

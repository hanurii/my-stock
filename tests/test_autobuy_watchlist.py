import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.watchlist import load_actionable, build_ew_index

def test_load_actionable(tmp_path):
    f = tmp_path / "sepa-vcp-candidates.json"
    f.write_text(json.dumps({"candidates": [
        {"code": "005930", "name": "삼성전자", "status": "actionable", "pivot_price": 70000.0},
        {"code": "000660", "name": "SK", "status": "forming", "pivot_price": 50000.0},   # 제외
        {"code": "005930", "name": "삼성전자", "status": "actionable", "pivot_price": 70000.0},  # 중복
    ]}, ensure_ascii=False), encoding="utf-8")
    out = load_actionable([str(f)])
    assert len(out) == 1 and out[0]["code"] == "005930" and out[0]["pivot"] == 70000.0

def test_build_ew_index():
    # 두 종목 상승 → 지수 상승
    series = {"A": {"dates": ["d1","d2","d3"], "closes": [100,110,121]},
              "B": {"dates": ["d1","d2","d3"], "closes": [50,55,60.5]}}
    idx = build_ew_index(lambda c: series.get(c), ["A","B"])
    assert len(idx) == 3 and idx[-1] > idx[0]

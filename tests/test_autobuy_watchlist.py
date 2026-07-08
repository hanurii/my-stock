import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.watchlist import load_actionable, build_ew_index

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

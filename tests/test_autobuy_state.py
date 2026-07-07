import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy import state

def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_PATH", tmp_path / "positions.json")
    state.save([{"code": "005930", "entry_price": 70000.0}])
    assert state.load()[0]["code"] == "005930"

def test_kill_switch(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "KILL_PATH", tmp_path / "KILL")
    assert state.kill_switch_on() is False
    (tmp_path / "KILL").write_text("stop")
    assert state.kill_switch_on() is True

def test_state_save_is_atomic_no_leftover_tmp(tmp_path, monkeypatch):
    """save() 는 임시파일→os.replace 이며, 정상 종료 후 tmp 파일이 남지 않아야 한다."""
    monkeypatch.setattr(state, "STATE_PATH", tmp_path / "positions.json")
    state.save([{"code": "005930", "entry_price": 70000.0}])
    state.save([{"code": "005930", "entry_price": 71000.0}])  # 덮어쓰기도 원자적으로 재검증
    assert state.load() == [{"code": "005930", "entry_price": 71000.0}]
    assert not (tmp_path / "positions.json.tmp").exists()
    assert (tmp_path / "positions.json").exists()

def test_traded_today_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "_DIR", tmp_path)
    monkeypatch.setattr(state, "_today_str", lambda: "20260707")
    assert state.load_traded_today() == set()
    state.add_traded_today("005930")
    state.add_traded_today("000660")
    assert state.load_traded_today() == {"005930", "000660"}
    # 파일이 날짜로 도장 찍혀 있는지, 그리고 tmp 잔여물이 없는지
    assert (tmp_path / "traded_20260707.json").exists()
    assert not (tmp_path / "traded_20260707.json.tmp").exists()

def test_traded_today_survives_explicit_date_and_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "_DIR", tmp_path)
    state.add_traded_today("005930", "20260101")
    # "재시작" 시나리오: 같은 날짜 문자열을 다시 넘겨 이전 상태를 그대로 읽어옴
    assert state.load_traded_today("20260101") == {"005930"}
    # 다른 날짜는 별개 파일 → 비어있음
    assert state.load_traded_today("20260102") == set()

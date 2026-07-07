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

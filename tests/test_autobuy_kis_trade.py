import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy import kis_trade

def test_dryrun_buy_no_network():
    r = kis_trade.place_buy_1share("005930", mode="dryrun")
    assert r["mode"] == "dryrun" and r["code"] == "005930" and r["qty"] == 1 and r["ok"] is True

def test_dryrun_sell_no_network():
    r = kis_trade.place_sell_1share("005930", mode="dryrun")
    assert r["mode"] == "dryrun" and r["qty"] == 1 and r["ok"] is True

def test_order_live_no_keys_returns_no_token_without_raising(monkeypatch):
    """KIS_APP_KEY/SECRET 자체가 없으면 get_access_token()이 None을 반환 — 네트워크 호출 없이 ok=False."""
    for k in ("KIS_ACCOUNT", "KIS_APP_KEY", "KIS_APP_SECRET"):
        monkeypatch.delenv(k, raising=False)
    r = kis_trade._order("005930", "buy", "live")
    assert r["ok"] is False
    assert r.get("error") == "no_token"

def test_order_live_missing_account_env_does_not_raise(monkeypatch):
    """토큰은 있는데(가짜) KIS_ACCOUNT 등이 없으면 os.environ[...] 이 KeyError를 내는데,
    _order 는 이를 밖으로 새지 않게 감싸서 ok=False dict 로 돌려줘야 한다(크래시 금지)."""
    monkeypatch.setattr(kis_trade.kis_api, "get_access_token", lambda: "faketoken")
    for k in ("KIS_ACCOUNT", "KIS_APP_KEY", "KIS_APP_SECRET"):
        monkeypatch.delenv(k, raising=False)
    r = kis_trade._order("005930", "buy", "live")
    assert r["ok"] is False
    assert "error" in r
    assert r["mode"] == "live" and r["code"] == "005930"

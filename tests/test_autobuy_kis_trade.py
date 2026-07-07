import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy import kis_trade

def test_dryrun_buy_no_network():
    r = kis_trade.place_buy_1share("005930", mode="dryrun")
    assert r["mode"] == "dryrun" and r["code"] == "005930" and r["qty"] == 1 and r["ok"] is True

def test_dryrun_sell_no_network():
    r = kis_trade.place_sell_1share("005930", mode="dryrun")
    assert r["mode"] == "dryrun" and r["qty"] == 1 and r["ok"] is True

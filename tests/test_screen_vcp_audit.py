import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import canslim_lib.vcp_audit as va
import screen_vcp_audit as scr


def test_example_base_ends_at_end_not_breakout(monkeypatch, tmp_path):
    dates = ["2019-01-01", "2019-02-01", "2019-03-15", "2019-03-20", "2019-04-30"]
    series = {"dates": dates, "opens": [1]*5, "highs": [1]*5, "lows": [1]*5,
              "closes": [1]*5, "volumes": [1]*5}
    monkeypatch.setattr(va, "load_series", lambda *a, **k: series)
    captured = {}
    def fake_item(s, b0, b1, params, meta):
        captured["b0"], captured["b1"] = b0, b1
        return {"code": meta["code"], "source": meta["source"], "axes": {}}
    monkeypatch.setattr(va, "audit_item", fake_item)

    ex_file = tmp_path / "vcp_examples.json"
    ex_file.write_text(json.dumps({"examples": [
        {"code": "111111", "start": "2019-02-01", "end": "2019-03-15", "breakout_date": "2019-03-20"}]}),
        encoding="utf-8")
    monkeypatch.setattr(scr, "EXAMPLES", ex_file)
    monkeypatch.setattr(scr, "OUT_PATH", tmp_path / "out.json")
    monkeypatch.setattr(scr, "ROOT", tmp_path)

    args = argparse.Namespace(no_examples=False, no_detector=True, min_advance=25.0, dry_max=0.7,
                              breakout_vol=1.4, near=5.0, mono_tol=1.15, vol_ma_window=50, zigzag_pct=8.0)
    scr.run(args)

    assert captured["b1"] == 2                      # end 2019-03-15 = index 2
    assert dates[captured["b1"]] == "2019-03-15"    # NOT breakout_date(index 3)

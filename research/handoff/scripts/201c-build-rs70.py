# -*- coding: utf-8 -*-
r"""201c — **`rs_min = 70` 경로를 «해»마다 «만든다»** · 두뇌 승인 2026-09-06

  ✅ **비용 관문 «통과»**(두뇌 조건 ①):
     🔎 `201b` — 한 해(2020) **422.7 초(7.0 분)** · `--emit-paths` 덧비용 **+1%**(측정)
     ⇒ **28 해 ≈ 199 분 (3.3 시간)**  <  **반나절(6 시간)**  ⇒ **✅ 돌린다**

  ⛔ **«덮어쓰지» 않는다** — 정본 `.cache/bt5y/sub/uspath_*.json`(rs 80)은 **«손대지» «않는다**.
     새 자리: **`D:/stock-data/uspath-rs70/`**

  ✅ **이어 돌릴 수 «있다»** — «이미» 만든 해는 «건너뛴다**.

  🚨 **설정이 «같은지»는 «수»로 «확인»했다**(`201b` 뒤):
     `skipped.halted` **4,597** · `skipped.low_turnover` **187,440** — **rs80 정본과 «정확히» 같다**
     ⇒ ★ **«유니버스»와 «자료»가 «같다** ⇒ **rs80 정본을 「① 팔」로 «쓸 수» 있다**

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/201c-build-rs70.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[2]
SCR = ROOT / "scripts"
DST = Path("D:/stock-data/uspath-rs70")
CANON = ROOT / ".cache" / "bt5y" / "sub"
YEARS = tuple(range(1999, 2027))
RS = 70


def main():
    P = print
    DST.mkdir(parents=True, exist_ok=True)
    P("=" * 96)
    P("201c — `rs_min = %d` 경로 만들기 · %d~%d (%d 해)" % (RS, YEARS[0], YEARS[-1], len(YEARS)))
    P("=" * 96)
    P("자리: %s   ⛔ 정본(%s)은 «손대지» 않는다" % (DST, CANON), flush=True)
    P("")

    sys.path.insert(0, str(SCR))
    t_all = time.time()
    done, made = [], []
    for y in YEARS:
        out = DST / ("uspath_%d.json" % y)
        if out.exists() and out.stat().st_size > 1000:
            try:
                p = json.loads(out.read_text(encoding="utf-8"))["params"]
                if p.get("rs_min") == RS:
                    P("  ♻️ %d — «이미» 있다 (진입 %s)" % (y, format(p.get("n_trades") or 0, ",")),
                      flush=True)
                    done.append(y)
                    continue
            except Exception:
                pass
        spec = _u.spec_from_file_location("up%d" % y, SCR / "backtest_volatility_pilot_us.py")
        mod = _u.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.RS_MIN = RS
        argv = ["backtest_volatility_pilot_us.py", "--market", "us",
                "--start", "%d-01-01" % y, "--end", "%d-12-31" % y,
                "--warm-days", "700", "--emit-paths", "--out", str(out)]
        old, t0 = sys.argv, time.time()
        try:
            sys.argv = argv
            mod.main()
        except Exception as e:                      # noqa: BLE001
            P("  🚨 %d 실패 — %s" % (y, e), flush=True)
            sys.argv = old
            continue
        finally:
            sys.argv = old
        el = time.time() - t0
        try:
            p = json.loads(out.read_text(encoding="utf-8"))["params"]
            n = p.get("n_trades")
        except Exception:
            n = None
        P("  ✅ %d 끝 — 진입 %s · %.0f 초 · %.0f MB (누적 %.0f 분)"
          % (y, format(n or 0, ","), el, out.stat().st_size / 1e6,
             (time.time() - t_all) / 60.0), flush=True)
        made.append(y)

    P("")
    P("=" * 96)
    P("끝 — 새로 만든 해 **%d** · 이미 있던 해 **%d** · 총 **%.0f 분**"
      % (len(made), len(done), (time.time() - t_all) / 60.0))
    P("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

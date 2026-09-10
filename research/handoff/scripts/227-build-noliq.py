# -*- coding: utf-8 -*-
r"""227a — **유동성 문턱 «없는» 경로를 «해»마다 «만든다»** · 🔴 사용자 결정 2026-09-07

  ⛔ **정본 `.cache/bt5y/sub/` 는 «손대지» «않는다**. 새 자리: **`D:/stock-data/uspath-noliq/`**
  ✅ **이어 돌릴 수 «있다»** — «이미» 만든 해는 «건너뛴다**.
  📁 **두뇌가 «몇 해»를 «셀» 수 있는 자리**:
       `ls -1 D:/stock-data/uspath-noliq/uspath_*.json | wc -l`   (28 이 «끝»)

  🚨 **사전등록은 `results/227-PRE.md` 에 «먼저» 박았다**(값 보기 «전»).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/227-build-noliq.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import re as _re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[2]
SCR = ROOT / "scripts"
DST = Path("D:/stock-data/uspath-noliq")
CANON = ROOT / ".cache" / "bt5y" / "sub"
YEARS = tuple(range(1999, 2027))
TURN = 0.0                      # Ⓧ — 유동성 «무관»


def main():
    # 🚨 `--year YYYY` — **«한» 해만** 돈다. «배경»이 «1분» 만에 죽어(4/4) **«전경»으로 «해»마다** 돌리려는 것.
    years = YEARS
    if "--year" in sys.argv:
        years = (int(sys.argv[sys.argv.index("--year") + 1]),)
    DST.mkdir(parents=True, exist_ok=True)
    P("=" * 96)
    P("227a — 유동성 문턱 «없는»(MIN_TURNOVER_EOK = %.1f) 경로 · %d~%d (%d 해)"
      % (TURN, years[0], years[-1], len(years)))
    P("=" * 96)
    P("자리: %s   ⛔ 정본(%s)은 «손대지» 않는다" % (DST, CANON), flush=True)
    P("")

    sys.path.insert(0, str(SCR))
    t_all = time.time()
    done, made = [], []
    for y in years:
        out = DST / ("uspath_%d.json" % y)
        if out.exists() and out.stat().st_size > 1000:
            # 🚨 «앞» 4KB «만» 읽는다 — 파일이 **63MB** 라 «전체» 파싱하면
            #    재개가 «21해 × 63MB» 를 «매번» 훑어 «느리다**(2026-09-07 실측: 44초에 2009 까지)
            try:
                head = out.open(encoding="utf-8").read(4096)
                m = _re.search(r'"min_turnover_eok"\s*:\s*([0-9.]+)', head)
                if m and float(m.group(1)) == TURN:
                    P("  ♻️ %d — «이미» 있다 (%.0f MB)" % (y, out.stat().st_size / 1e6), flush=True)
                    done.append(y)
                    continue
            except Exception:                       # noqa: BLE001
                pass
        spec = _u.spec_from_file_location("up%d" % y, SCR / "backtest_volatility_pilot_us.py")
        mod = _u.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.MIN_TURNOVER_EOK = TURN                 # ⟵ **«이것» «하나»만 바꾼다**
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
        except Exception:                           # noqa: BLE001
            n = None
        P("  ✅ %d 끝 — 진입 %s · %.0f 초 · %.0f MB (누적 %.0f 분)"
          % (y, format(n or 0, ","), el, out.stat().st_size / 1e6,
             (time.time() - t_all) / 60.0), flush=True)
        made.append(y)

    P("")
    P("=" * 96)
    P("끝 — 새로 만든 해 **%d** · 이미 있던 해 **%d** · **총 %.1f 분**(실측)"
      % (len(made), len(done), (time.time() - t_all) / 60.0))
    P("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

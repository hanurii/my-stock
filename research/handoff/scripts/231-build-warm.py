# -*- coding: utf-8 -*-
r"""231a — **`pre_*`(진입 «전» 창)를 «붙인» 경로를 «만든다»** · 🔴 사용자 결정 2026-09-08

  🚨 **왜** — `mk:65` [Ⓜ] 「돌파 «이후» 주가가 **«처음»/«두» 번째**로 **20일 «또는» 50일** 이평까지
     «후퇴»할 때 산다」를 «재려면» — **진입 «전» 20~50봉**이 «있어야» 이평이 «선다**.
     🔎 지금 경로엔 **`pre_*` 가 «없다**(`pilot_us.py:248` `EMIT_WARMUP = False` · 실측 확인).

  ⛔ **정본 `.cache/bt5y/sub/` 와 `uspath-noliq/` 를 «건드리지» 않는다** — **«새» 자리**:
       **`D:/stock-data/uspath-warm2/`**
  ✅ **이어 돌릴 수 «있다»** — «이미» 만든 해는 **«앞» 4KB «만»** 읽어 «건너뛴다**.
  ✅ **`--year YYYY`** — **«한» 해만**. **«전경»으로 «시작**한다
     (🔎 「처음부터 «배경»으로 «띄운» 것은 **4/4 «죽었고**」 · 「«전경»으로 «시작**해 «배경»으로
      «옮겨진» 것은 **«살았다**」 — 2026-09-07 관측).

  💾 **디스크**: D: 남은 **370 GB**(확인함) · 지금 경로 «한» 벌이 **~2 GB** ⇒ **`pre_*` 가 몇 배여도 «충분**.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/231-build-warm.py --year 1999
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
DST = Path("D:/stock-data/uspath-warm2")
YEARS = tuple(range(1999, 2027))


def main():
    years = YEARS
    if "--year" in sys.argv:
        years = (int(sys.argv[sys.argv.index("--year") + 1]),)
    DST.mkdir(parents=True, exist_ok=True)
    P("=" * 96)
    P("231a — **`pre_*` 를 «붙인»** 경로 · %d~%d (%d 해)" % (years[0], years[-1], len(years)))
    P("=" * 96)
    P("자리: %s   ⛔ 정본·noliq 은 «손대지» 않는다" % DST, flush=True)
    P("")

    sys.path.insert(0, str(SCR))
    t_all = time.time()
    done, made = [], []
    for y in years:
        out = DST / ("uspath_%d.json" % y)
        if out.exists() and out.stat().st_size > 1000:
            try:
                head = out.open(encoding="utf-8").read(4096)
                if _re.search(r'"warmup_bars"', head):
                    P("  ♻️ %d — «이미» 있다 (%.0f MB)" % (y, out.stat().st_size / 1e6), flush=True)
                    done.append(y)
                    continue
            except Exception:                       # noqa: BLE001
                pass
        spec = _u.spec_from_file_location("up%d" % y, SCR / "backtest_volatility_pilot_us.py")
        mod = _u.module_from_spec(spec)
        spec.loader.exec_module(mod)
        argv = ["backtest_volatility_pilot_us.py", "--market", "us",
                "--start", "%d-01-01" % y, "--end", "%d-12-31" % y,
                "--warm-days", "700", "--emit-paths", "--emit-warmup",
                "--out", str(out)]
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
            n, wb = p.get("n_trades"), p.get("warmup_bars")
        except Exception:                           # noqa: BLE001
            n, wb = None, None
        P("  ✅ %d 끝 — 진입 %s · warmup %s · %.0f 초 · %.0f MB (누적 %.0f 분)"
          % (y, format(n or 0, ","), wb, el, out.stat().st_size / 1e6,
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

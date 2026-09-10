# -*- coding: utf-8 -*-
r"""201b — **«한계» 비용을 «잰다»** · 두뇌 조건 ① · 2026-09-06

  🚨 **왜** — `201` 이 낸 「27.4년 ≈ 1,178분」은 **«과대**였다(«내»가 스스로 정정).
     한 달 창의 «대부분»이 **Sharadar 적재(709일)**이고 — **스캔일이 «늘어도» 그 적재는 «한 번»**이다.

  ✅ **재는 법** — **«한 해»**(2020)를 `rs_min = 70` 으로 «한 번» 돌리고 **«시간»**을 잰다.
     ⇒ ★ **«기존» `uspath_*.json` 이 «이미» `rs_min = 80` 판**이므로(params 확인) —
       **«새로» 돌릴 것은 «70» 쪽 «하나»뿐**이다 ⇒ **비용이 «절반»**이다.

  ⛔ **두뇌 조건**: 「**반나절 «넘으면» «멈추고» «다시» 묻는다**」
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
OUT = Path(r"C:/Users/hanul/AppData/Local/Temp/claude"
           r"/C--Users-hanul-playground-my-stock"
           r"/f3bf3bbc-f87a-4400-9119-515eaefcdd0d/scratchpad/201b-year70.json")
YEARS_TOTAL = 27          # 1999~2026 · `91` 사다리와 «같은» 범위


def main():
    P = print
    P("=" * 104)
    P("201b — **«한계» 비용을 «잰다»** · 한 해(2020) × `rs_min = 70`")
    P("=" * 104)
    P("")
    P("> 조사 세션 · `scripts/201b-cost-probe.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("```")
    P("✅ **«새로» 돌릴 것은 «70» 쪽 «하나»뿐**이다 —")
    P("   `uspath_*.json` 의 `params.rs_min` 이 **80** 이므로 **«80» 판은 «이미» 있다**")
    P("⛔ 두뇌 조건: **「반나절 «넘으면» «멈추고» «다시» 묻는다」**")
    P("```", flush=True)
    P("")

    sys.path.insert(0, str(SCR))
    spec = _u.spec_from_file_location("uspilot70y", SCR / "backtest_volatility_pilot_us.py")
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.RS_MIN = 70
    argv = ["backtest_volatility_pilot_us.py", "--market", "us",
            "--start", "2020-01-01", "--end", "2020-12-31",
            "--warm-days", "700", "--out", str(OUT)]
    old, t0 = sys.argv, time.time()
    try:
        sys.argv = argv
        mod.main()
    finally:
        sys.argv = old
    el = time.time() - t0
    d = json.loads(OUT.read_text(encoding="utf-8"))
    p = d.get("params", {})

    P("")
    P("=" * 104)
    P("## ⇒ **잰 것**")
    P("=" * 104)
    P("")
    P("```")
    P("한 해(2020) · rs_min **%s** · 스캔일 **%s** · 진입 **%s**"
      % (p.get("rs_min"), format(p.get("n_scan_dates") or 0, ","),
         format(p.get("n_trades") or 0, ",")))
    P("**걸린 시간 = %.1f 초 (%.1f 분)**" % (el, el / 60.0))
    P("")
    tot_min = el * YEARS_TOTAL / 60.0
    P("## ⇒ **27 해 어림 = %.0f 분 (%.1f 시간)**" % (tot_min, tot_min / 60.0))
    P("   ⟵  `한 해 %.1f초 × %d해`" % (el, YEARS_TOTAL))
    P("")
    P("⚠️ **선형 어림**이다 — 해마다 유니버스 크기가 «다르다**(2020 은 «큰» 편)")
    P("```")
    P("")
    half = 6 * 60.0
    P("```")
    if tot_min > half:
        P("## 🔴 **「반나절(6시간)」을 «넘는다** ⇒ **«멈추고» «다시» 묻는다**(두뇌 조건 ①)")
    else:
        P("## ✅ **「반나절(6시간)」 «아래»다** ⇒ **«돌려도» 된다**")
    P("   기준 **%.0f 분** vs 어림 **%.0f 분**" % (half, tot_min))
    P("```")
    P("")
    P("```")
    P("## ⚠️ **이 어림이 «못» 하는 것**")
    P("   ⛔ **2020 «한» 해**다 — 유니버스가 «작은» 해는 «빠르고» «큰» 해는 «느리다**")
    P("   ⛔ **`rs_min=80` 쪽을 «다시» 돌리는 비용은 «안» 넣었다**(«기존» 파일을 «쓴다»는 «가정»)")
    P("     ⇒ 🚨 그 «가정»이 «깨지면**(설정이 «달라졌으면») **비용이 «두 배»**다")
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
r"""94v — 검증 세션(`51cbc329`)이 요구한 둘. **서술 · 예산 0 · 판정에 안 씀.**

① **보유일 — «떨어질 수 있는» 검사**
   칸이 5로 같고 노출이 맞았으면 **슬롯-일 총량이 같다** → `체결 ≈ 슬롯일총량 ÷ 평균보유일`.
   ```
   448 / 542 = 0.827  →  처리 쪽 보유가 **17% 짧아야** 한다
   ```
   **비가 0.83 근처면 항등식이 성립한 것**이고, **크게 어긋나면 노출·칸 말고 «다른 게» 움직인 것**이다.
   🚨 지금은 「그럴 것이다」이고 찍으면 「그렇다」가 된다.

② **MAE — 「손절을 넓히면 살아나나」를 «창을 안 태우고» 반쯤 답한다**
   ```
   −8% 에서 털린 뒤 «회복»하는가?   →  넓히면 값을 한다  (물어볼 값어치 있음)
   내리 꽂는가?                     →  넓혀도 소용없다   (물어볼 값어치 없음)
   ```
   🚨 **판정에 안 쓴다.** 이건 「새 창을 태울 값어치가 있는 물음인가」를 정하는 데만 쓴다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("m94", HERE / "94-roe-realized.py")
m94 = _u.module_from_spec(_s)
_s.loader.exec_module(m94)
m92, r91 = m94.m92, m94.r91


def main() -> int:
    print("=" * 100, flush=True)
    print("94v — ① 보유일(항등식 검사)  ② MAE(손절 넓히기가 물어볼 값어치가 있나)", flush=True)
    print("       **서술 · 예산 0 · 판정에 안 씀**", flush=True)
    print("=" * 100, flush=True)

    fund = json.loads(m92.FUND.read_text(encoding="utf-8"))["by"]
    rowsP, _a, _b = m92.build(tuple(range(1999, 2013)), *m92.PICK, fund)
    _cuts, _nc, fq = m92.cells_for(rowsP, "roe")
    ev, tagged, _m = m94.build_events(fund, fq, 0)

    # 거래별 보유일 · 결과 · 전체경로 MFE
    info = {}
    for t in ev:
        k = (t["scan_date"], t["code"], t.get("pattern", ""))
        mk = t["masks"][()]
        rd = mk.get("resolve_date") or t["entry_date"]
        hold = m92._ord(rd) - m92._ord(t["entry_date"])
        info[k] = {"hold": hold, "res": mk.get("result"), "roe1": t["_roe1"]}

    # 경로에서 «전체» MFE 와 MAE 를 다시 뽑는다 (결착 «뒤»까지 포함)
    for y in m94.YEARS:
        f = m92.SUB / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        for p in json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]:
            k = (p["scan_date"], p["code"], p.get("pattern", ""))
            if k not in info:
                continue
            epx = p.get("entry_price")
            hs, ls = p.get("h") or [], p.get("l") or []
            if not epx or not hs:
                continue
            info[k]["mfe"] = (max(hs) / epx - 1) * 100
            info[k]["mae"] = (min(ls) / epx - 1) * 100 if ls else None

    # ── ① 보유일 ───────────────────────────────────────────────────────
    print("\n① 팔별 «체결된 거래»의 보유일 중앙  (seed 0~11 · 서술이라 12판이면 충분)", flush=True)
    ctl = m94.run(ev, None, 12)
    trt = m94.run(ev, m94.prio, 12)

    def hold_med(res):
        ks = [k for k, kind, *_ in res["fill_log"] if kind == "pilot"]
        hs = [info[k]["hold"] for k in ks if k in info]
        return (st.median(hs) if hs else float("nan"), len(ks),
                st.mean(hs) if hs else float("nan"))

    hc = [hold_med(x) for x in ctl]
    ht = [hold_med(x) for x in trt]
    mc, mt = st.median(x[0] for x in hc), st.median(x[0] for x in ht)
    nc_, nt_ = st.median(x[1] for x in hc), st.median(x[1] for x in ht)
    ac, at = st.median(x[2] for x in hc), st.median(x[2] for x in ht)
    print("   대조  보유 중앙 %5.1f일 · **평균 %5.2f일** · 체결 %6.1f건" % (mc, ac, nc_), flush=True)
    print("   처리  보유 중앙 %5.1f일 · **평균 %5.2f일** · 체결 %6.1f건" % (mt, at, nt_), flush=True)
    print("   보유 비(중앙) %.3f · **보유 비(평균) %.3f** · 체결 비(대조/처리) %.3f"
          % (mt / mc if mc else float("nan"), at / ac if ac else float("nan"),
             nc_ / nt_ if nt_ else float("nan")), flush=True)
    print("      🚨 항등식은 «평균» 보유일에 걸린다(총 슬롯일 = 체결 x 평균보유). 중앙값은 근사다.",
          flush=True)
    print("   -> 두 비가 비슷하면 **항등식 성립**(자본이 같은데 회전만 빨라진 것).", flush=True)
    print("      크게 어긋나면 노출·칸 말고 «다른 게» 움직인 것이다.", flush=True)

    # ── ② MAE ─────────────────────────────────────────────────────────
    print("\n② 「−8% 에서 털린 뒤 회복하는가」 — 손절 넓히기가 물어볼 값어치가 있나", flush=True)
    for gname, want in (("roe 1분위", True), ("나머지", False)):
        g = [v for v in info.values() if v["roe1"] == want and "mfe" in v]
        st_ = [v for v in g if v["res"] == "loss"]
        if not st_:
            continue
        rec20 = sum(1 for v in st_ if v["mfe"] >= 20.0)
        rec100 = sum(1 for v in st_ if v["mfe"] >= 100.0)
        maes = sorted(v["mae"] for v in st_ if v["mae"] is not None)
        print("\n   **%s**  거래 %s · 그중 손절 %s (%.1f%%)"
              % (gname, "{:,}".format(len(g)), "{:,}".format(len(st_)),
                 100.0 * len(st_) / len(g)), flush=True)
        print("      손절된 것 중 «나중에» +20%% 까지 간 것  **%.1f%%** (%s건)"
              % (100.0 * rec20 / len(st_), "{:,}".format(rec20)), flush=True)
        print("      손절된 것 중 «나중에» 2배까지 간 것    **%.1f%%** (%s건)"
              % (100.0 * rec100 / len(st_), "{:,}".format(rec100)), flush=True)
        if maes:
            n = len(maes)
            print("      바닥(MAE) 중앙 %.1f%% · P25 %.1f%% · P10 %.1f%%"
                  % (maes[n // 2], maes[n // 4], maes[n // 10]), flush=True)
    print("\n   읽는 법: 「손절 뒤 +20% 도달」이 두 무리에서 «비슷»하면 손절폭을 넓혀도", flush=True)
    print("           roe 1분위만 특별히 살아나지 않는다 → **새 창을 태울 값어치가 없다.**", flush=True)
    print("           roe 1분위가 «훨씬» 높으면 그때는 물어볼 값어치가 있다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

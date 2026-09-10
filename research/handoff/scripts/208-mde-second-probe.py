# -*- coding: utf-8 -*-
r"""208 — **「§G 를 «푸는» 판이 «가능»한가」를 «MDE»로 «먼저» 잰다 · «둘째» 판** · 2026-09-07

  🚨 **왜** — `201d` 가 «자기» 자료로 **MDE = 9.040%p**(Δ 1.23 의 **7.35배**)를 냈다.
     가설: 「§G 항목은 «대부분» «유니버스/관문»을 바꾸는 판이라 MDE 도 «비슷»할 것」.
     ⛔ **그건 «단가» 옮기기(유형 68)** — 그래서 **«둘째» 판을 «하나» 더 «재서» 확인한다**.

  🔴 **두뇌가 고른 손잡이(「200일선 관문 빼기」)는 «못» 쓴다 — 「유니버스만 바꾸면」이 «틀렸다»**:
     🔎 `backtest_volatility_pilot_us.py:374` `evaluate_trend_template(...)` — **«스캔» 때 걸린다**
     ⇒ 빼려면 **28해 경로를 «다시» 만들어야** 한다(`201c` = **216분**) ⇒ **「제일 싼 것」이 «아니다**

  ✅ **대신 고른 손잡이 — «진짜» 제일 싼 것**: 사다리 칸 **② → 0**(섹터 관문 «빼기»)
     🔎 `91-us-out-of-sample.py:95` **`LO, HI = 0.10, 0.30`** — **임의값**이고
        **§G 에 «등재»조차 «안» 돼 있다**(`190` grep 0줄)
     ⇒ **«있는» 경로를 «그대로»** 쓴다 ⇒ build_pairs 1회 + 부트스트랩 ≈ **2.5분**

  ⛔⛔ **이 판은 «효과»를 «안» 본다** — **SD · MDE · N «만»** 찍는다.
     **점추정·CI·중앙·백분위를 «계산»조차 «하지» 않는다**(금지를 «구조»로).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/208-mde-second-probe.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
f92a = r102.f92a
pt = r91.pt

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NBOOT = 2000
SEED = 208208
YRS = 27.4
BLOCKS = ((20, 40), (80, 80))
BMIN, BMAX = BLOCKS[0]
DELTA = 1.23
MDE_K = 2.8016
MDE_201D = 9.040          # `201d` 가 «자기» 자료로 낸 값(옮긴 «단가»가 «아니라» «비교 대상»)
MDE_188 = 1.793           # `188` 최소

SYM_SAME = ("**MDE 가 `201d`(9.040)와 «비슷»하면** → **가설이 «한» 번 «버텼다»** "
            "(⛔ **「증명」이 «아니다»** — «두» 판은 «두» 판이다)")
SYM_DIFF = ("**MDE 가 «다르면»** → **「MDE 는 판마다 «다르다»」**이고 "
            "— **§G 를 «싸잡아» «닫을» 수 «없다»**")


def draw(n, rnd):
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(BMIN, BMAX)
        a = rnd.randint(0, n - 1)
        LL = min(L, n - tot)
        for j in range(LL):
            out.append((a + j) % n)
        tot += LL
    return out


def ann(tot_pct):
    v = 1.0 + tot_pct / 100.0
    if v <= 1e-9:
        return -100.0
    return (v ** (1.0 / YRS) - 1.0) * 100.0


def boot_eq(by_pos, n_pos, slots=SLOTS):
    """23c:46-66 «그대로»."""
    eq, held = 1.0, []
    for p in range(n_pos):
        if held:
            keep_ = []
            for h in held:
                if h[0] < p:
                    eq += h[1] * h[2] / 100
                else:
                    keep_.append(h)
            held = keep_
        free = slots - len(held)
        cc = by_pos.get(p)
        if free > 0 and cc:
            wgt = eq / slots
            for rel, nt, _k in cc[:free]:
                held.append([p + rel, wgt, nt])
    for h in held:
        eq += h[1] * h[2] / 100
    return (eq - 1.0) * 100.0


def build(rung):
    """rung 0 = 섹터 관문 «없음» · rung 2 = 현행 정본(주도섹터 + 침투율 밴드)."""
    (by0, _by1, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        return None
    src = by0 if rung == 0 else by2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    out = []
    for y in sorted(src):
        open_until = {}
        for p in src[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None
                          or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is False:
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 half=HALF, shares=(1.0,), add_stop="floor_entry")
            cd = p["code"]
            if cd in open_until and p["entry_date"] <= open_until[cd]:
                continue
            r = t["masks"][()]
            open_until[cd] = r["resolve_date"] or p["entry_date"]
            epx = t["entry_px"]
            net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                      for _d, fr, px in r["exits"])
            d, rd = p["d"], r["resolve_date"]
            hold = d.index(rd) if (rd and rd in d) else len(d) - 1
            out.append((t["entry_date"], max(1, hold), net))
    return out


def main():
    global BMIN, BMAX
    P("# 208 — **MDE «둘째» 판**(효과는 «안» 본다)")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/208-mde-second-probe.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("---")
    P("")
    P("# 0. **사전등록** — «둘 다» «미리»(관문 ①)")
    P("")
    P(F3)
    P("✅ " + SYM_SAME)
    P("🔴 " + SYM_DIFF)
    P("")
    P("⛔⛔ **이 판은 «효과»를 «안» 본다** — **SD · MDE · N «만»** 찍는다")
    P("   ⇒ 🚨 **점추정·CI·중앙·백분위를 «계산»조차 «하지» 않는다**(금지를 «구조»로)")
    P("⛔ **「가설이 «버티면» §G 를 «닫는다»」로 «가지» 않는다** — **«두» 판은 «두» 판**이다(관문 ④)")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 1. **손잡이를 «고른» 까닭 — «비용»으로**(관문 ③)")
    P("")
    P(F3)
    P("🔴 **두뇌가 고른 「200일선 관문 «빼기»」는 «못» 쓴다**")
    P("   🔎 " + BQ + "backtest_volatility_pilot_us.py:374" + BQ
      + " — " + BQ + "evaluate_trend_template(t['closes'], rs=rsv, rs_min=RS_MIN)" + BQ)
    P("     ⇒ **«스캔» 때 걸린다** ⇒ 빼려면 **28해 경로를 «다시»**(= " + BQ + "201c" + BQ
      + " **216분**)")
    P("   ⇒ ⛔ 「유니버스만 «바꾸면» 된다」가 **«틀렸다** — **「제일 «싼» 것」이 «아니다**")
    P("")
    P("✅ **대신 — 사다리 칸 ② → 0**(섹터 관문 «빼기»)")
    P("   🔎 " + BQ + "91-us-out-of-sample.py:95" + BQ + " **" + BQ + "LO, HI = 0.10, 0.30" + BQ
      + "** — **임의값**")
    P("   🚨 그리고 **§G 에 «등재»조차 «안» 돼 있다** — " + BQ
      + "grep '사다리|LO|침투|by2' 190-what-is-closed.md" + BQ + " → **0 줄**")
    P("     ⇒ ★ **`204` 가 «안» 본 파일이다** — 그 목록(`_gates.py`·`slot_sim*`·`screen_*`·`autobuy/*`)")
    P("       에 " + BQ + "91-us-out-of-sample.py" + BQ + " 는 **«들어 있지도» «않았다**")
    P("   ⇒ ✅ **«있는» 경로를 «그대로» 쓴다** ⇒ build 2회 + 부트스트랩 ≈ **2~3분**")
    P("")
    P("⚠️ **한정** — 칸 0 은 " + BQ + "lvl1" + BQ + "(주도섹터)와 " + BQ + "lvl2" + BQ
      + "(침투율 밴드)를 **«한꺼번에»** 뺀다")
    P("   ⇒ **「어느 쪽이 얼마」는 «못» 가른다. 이 판은 «SD 의 «크기»»만 보므로 «상관»없다**")
    P(F3)
    P("", flush=True)

    CA = Path(str(r91.OUT / "208-arms.json"))
    if CA.exists():
        built = {k: [tuple(x) for x in v]
                 for k, v in json.loads(CA.read_text(encoding="utf-8")).items()}
    else:
        a2 = build(2)
        if a2 is None:
            P("🚨 **멈춘다** — 경로 «없음»")
            return 2
        a0 = build(0)
        built = {"①": a2, "Ⓖ": a0}
        CA.write_text(json.dumps({k: [list(x) for x in v] for k, v in built.items()}),
                      encoding="utf-8")

    all_d = sorted({d for lst in built.values() for d, _h, _n in lst})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)
    idx_at = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            idx_at[k][pos[d]].append(j)

    P("---")
    P("")
    P("# 2. **자료**")
    P("")
    P(F3)
    P("   **날짜 자리 수 = %s**   ⟵  " % format(n_pos, ",")
      + BQ + "len(sorted(set(entry_dates)))" + BQ)
    P("   **① 사다리 ② (현행 정본) 거래 = %s**" % format(len(built["①"]), ","))
    P("   **Ⓖ 사다리 0 (섹터 관문 «없음») 거래 = %s**" % format(len(built["Ⓖ"]), ","))
    P(F3)
    P("", flush=True)

    P("---")
    P("")
    P("# 3. ★★ **잰 것 — SD · MDE · N «만»**")
    P("")
    P("| 블록 | **SD** | **MDE**(2.8016×SD) | MDE ÷ Δ | " + BQ + "201d" + BQ + " MDE 대비 |")
    P("|---|---:|---:|---:|---:|")
    rows = []
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        BMIN, BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        diffs = []
        for bi in range(NBOOT):
            order = draw(n_pos, rnd)
            eqs = {}
            for k, lst in built.items():
                bp = defaultdict(list)
                ia = idx_at[k]
                for newp, oldp in enumerate(order):
                    for j in ia.get(oldp, ()):
                        _d, h, nt = lst[j]
                        bp[newp].append((h, nt, 0))
                eqs[k] = ann(boot_eq(bp, n_pos))
            diffs.append(eqs["Ⓖ"] - eqs["①"])
            if (bi + 1) % 400 == 0:
                P("  [블록 %d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        sd = st.stdev(diffs)
        mde = MDE_K * sd
        rows.append((bmn, bmx, sd, mde))
        P("| **%d~%d** | %.3f | **%.3f%%p** | **%.2f 배** | %.2f 배 |"
          % (bmn, bmx, sd, mde, mde / DELTA, mde / MDE_201D))
    P("")
    P(F3)
    P("   Δ = **%.2f%%p** · " % DELTA + BQ + "188" + BQ + " 최소 MDE = **%.3f%%p** · "
      % MDE_188 + BQ + "201d" + BQ + " MDE = **%.3f%%p**" % MDE_201D)
    P(F3)
    P("")
    P("---")
    P("")

    # ── 대칭 판정 ────────────────────────────────────────────────────
    m0 = rows[0][3]
    ratio = m0 / MDE_201D
    near = 0.5 <= ratio <= 2.0
    P("# 4. **대칭 판정**")
    P("")
    P(F3)
    P("✅ " + SYM_SAME)
    P("🔴 " + SYM_DIFF)
    P("")
    P("   **이 판 MDE(블록 20~40) = %.3f%%p** · " % m0
      + BQ + "201d" + BQ + " **%.3f%%p** ⇒ **%.2f 배**" % (MDE_201D, ratio))
    P("   판정 자(«미리» 박음): **0.5 ~ 2.0 배면 「비슷」**")
    P("")
    if near:
        P("## ⇒ **✅ 쪽 — 가설이 «한» 번 «버텼다**")
        P("   ⛔ **「증명」이 «아니다** — **«두» 판은 «두» 판**이다(관문 ④)")
    else:
        P("## ⇒ **🔴 쪽 — 「MDE 는 판마다 «다르다»」**")
        P("   ⇒ **§G 를 «싸잡아» «닫을» 수 «없다** — 판마다 «따로» 재야 한다")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 관문 ─────────────────────────────────────────────────────────
    src = Path(__file__).read_text(encoding="utf-8")
    # 🚨 금지 낱말을 «소스»에 «통째로» 적으면 — 검사가 «자기 자신»을 잡는다(㊁ 의 «반대» 얼굴).
    #    그래서 **«조각»으로 적고 «런타임»에 «잇는다**  ⇒ 소스엔 «온전한» 낱말이 «없다**.
    ban = ("med" + "ian", "st." + "mean", "percen" + "tile", "ob" + "sd",
           "sorted(" + "diffs", "quan" + "tile", "int(NB" + "OOT")
    hits = [b for b in ban if b in src]
    P("# 5. **관문 넷**")
    P("")
    ok = [
        ("① 대칭 «둘 다» «미리» 인쇄", bool(SYM_SAME) and bool(SYM_DIFF)),
        ("② **「효과를 «안» 봤다」를 «출력»으로** — 각본에 금지 낱말 **%d** 개 %s"
         % (len(hits), ("(" + ", ".join(hits) + ")") if hits else "(중앙·평균·백분위·점추정 — «일곱» 낱말)"),
         not hits),
        ("③ 「«고른» 까닭」을 **«비용»**으로 적었다(216분 vs 2~3분)", True),
        ("④ 「가설이 버티면 §G 를 «닫는다»」로 «가지» 않았다 — 위 §4 가 «명시»", True),
    ]
    P(F3)
    for nm, v in ok:
        P("%s %s" % ("✅" if v else "🚨", nm))
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⇒ **한 문장**")
    P("")
    P("> ## **이 판의 MDE 는 %.3f%%p — Δ(%.2f)의 %.2f 배이고 " % (m0, DELTA, m0 / DELTA)
      + BQ + "201d" + BQ + " 의 %.2f 배다.**" % ratio)
    P("> ## **그리고 «효과»는 «보지» «않았다» — «볼» «필요»가 «없었다».**")
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

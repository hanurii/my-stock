# -*- coding: utf-8 -*-
r"""229 — **ROE 문턱 15%** · 🔴 사용자 결정 「ART 를 «그대로»」 2026-09-07

  🔎 v2:42 [미너비니] 「**15-17퍼센트 «또는» 그 «이상**»의 ROE를 가진 주식이 «일반적»으로 «더» 좋습니다」
  ⇒ ✅ **문턱 = 15**(**«범위»의 «아래»끝**) — ⛔ 17 은 «위»끝이다.

  ✅ **관문 ③ «확인»함** — 정본 캐시(`92-fund-pit.json`)에 **ARQ·ART 가 «둘 다»** 있고
     **ART 의 `roe` 가 89.4%** 다. ⇒ **캐시를 «다시» 만들지 «않고** `f92a` 도 **«안» 고친다**.
     이 판 «안»에서 `rec["ART"]` 를 **«직접»** 읽는다.

  ✅ **단위 «확인»함**(«추측» «아님») — ART `roe` 중앙 **+0.0650** · P75 **+0.1530** ⇒ **«비율»**
     ⇒ 문턱은 **0.15**.

  ⛔ **사전등록은 `results/229-PRE.md` 에 «먼저» 박았다**(값 보기 «전»).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/229-roe-threshold.py
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
m220 = _load("m220", "220-fa-four.py")
f92a = r102.f92a
pt = r91.pt

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NBOOT, SEED = 2000, 229229
BLOCKS = ((20, 40), (80, 80))
DELTA, MDE_K = 1.23, 2.8016
ROE_MIN = 0.15                 # ✅ «비율» — 단위를 «찍어» 확인함(중앙 0.0650 · P75 0.1530)

PRE_UP = "**Ⓡ 가 «위»로 갈라지면** → 「**ROE 15% 문턱이 «일한다**」 ⇒ **원전 쪽이 «맞다**"
PRE_DN = "**Ⓡ 가 «아래»로 갈라지면** → 「**ROE 문턱이 «해»다**」"
PRE_NO = ("**«못» 가리면** → 「**«넣어도» «못» 가린다**」 ⇒ **펀더 «남은» 셋이 «0» 이 된다**")


def c(s):
    return BQ + s + BQ


def build():
    """`220` 과 **«한 글자»도 «다르지» 않은** 구성 + **ART roe** «하나»만 «더» 붙인다."""
    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        return None, None
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    recs = []
    n_roe_none = 0
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            rec = fund.get(p["code"]) or {}
            arq = rec.get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            if a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX:
                continue
            fl = m220._flags(arq, arq.index(a), ix)
            if fl is None or fl["base2"] is not True:      # ① 현행 관문 «통과»분만
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 half=HALF, shares=(1.0,), add_stop="floor_entry")
            cd = p["code"]
            if cd in open_until and p["entry_date"] <= open_until[cd]:
                continue
            r = t["masks"][()]
            open_until[cd] = r["resolve_date"] or p["entry_date"]
            epx = t["entry_px"]
            net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2)) for _d, fr, px in r["exits"])
            d, rd = p["d"], r["resolve_date"]
            hold = d.index(rd) if (rd and rd in d) else len(d) - 1
            # ── ART 의 roe 를 **진입일 «전»** 것으로 붙인다(룩어헤드 «없음») ──
            art = rec.get("ART") or []
            ar = f92a.asof(art, p["entry_date"]) if art else None
            roe = None
            if ar is not None and (r102._ord(p["entry_date"]) - r102._ord(ar[0])
                                   <= r102.STALE_MAX):
                roe = ar[ix["roe"]]
            if roe is None:
                n_roe_none += 1
            recs.append({"d": t["entry_date"], "h": max(1, hold), "n": net, "roe": roe})
    return recs, n_roe_none


def main():          # noqa: C901
    P("# 229 — **ROE 문턱 15%**")
    P("")
    P("> 조사 세션 · " + c("research/handoff/scripts/229-roe-threshold.py")
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **사전등록은 " + c("results/229-PRE.md") + " 에 «먼저» 박았다**")
    P("")
    P("---")
    P("")
    P("# 0. **사전등록**(«그대로» 옮긴다)")
    P("")
    P(F3)
    P("① " + PRE_UP)
    P("② " + PRE_DN)
    P("③ " + PRE_NO)
    P("")
    P("**문턱 = 15** — v2:42 「**15-17퍼센트 «또는» 그 «이상**»」의 **«아래»끝**. ⛔ 17 은 «위»끝이다")
    P("")
    P("✅ **관문 ③ «확인»함**: 정본 캐시에 **ARQ 682,278 · ART 689,005 행**이 «둘 다» 있고 "
      "**ART `roe` 89.4%** ⇒ **캐시 «재생성» «없음** · " + c("f92a") + " **«안» 고침**")
    P("✅ **단위 «확인»함**(«추측» «아님»): ART `roe` **중앙 +0.0650 · P75 +0.1530** ⇒ **«비율»** "
      "⇒ 문턱 **0.15**")
    P("")
    P("**«예상»**: **Ⓥ 무리** ⇒ MDE «작을» 것(견줌 `220`~`223` **3.3~4.7배** · `228` 4.13배) "
      "⛔ **«수»로 «옮기지» 않는다**")
    P(F3)
    P("")
    P("---")
    P("")

    CA = Path(str(r91.OUT / "229-recs.json"))
    if CA.exists():
        d_ = json.loads(CA.read_text(encoding="utf-8"))
        recs, n_none = d_["recs"], d_["n_none"]
    else:
        P("(자료를 «짓는» 중 — ART roe 를 «붙인다» …)", flush=True)
        recs, n_none = build()
        if recs is None:
            P("🚨 **멈춘다** — 경로 «없음»")
            return 2
        CA.write_text(json.dumps({"recs": recs, "n_none": n_none}), encoding="utf-8")

    base = [(z["d"], z["h"], z["n"]) for z in recs]
    hi_roe = [(z["d"], z["h"], z["n"]) for z in recs
              if z["roe"] is not None and z["roe"] >= ROE_MIN]
    lo_roe = sum(1 for z in recs if z["roe"] is not None and z["roe"] < ROE_MIN)

    P("# 1. **팔 크기와 «양성» 대조**(«먼저» 찍는다)")
    P("")
    P(F3)
    P("   **① 현행 거래 = %s**" % format(len(base), ","))
    P("   **Ⓡ ROE ≥ 0.15 거래 = %s**" % format(len(hi_roe), ","))
    P("   («나머지» — ROE < 0.15 **%s** · ROE **«없음»** %s)"
      % (format(lo_roe, ","), format(n_none, ",")))
    P("")
    P("   **★ ① «에만» 있는 거래 = %s**" % format(len(base) - len(hi_roe), ","))
    P("   **★ Ⓡ «에만» 있는 거래 = 0**  ⟵ **Ⓡ 는 ① 의 «부분집합»**이다")
    P("")
    P("✅ **Ⓡ ⊂ ①**(«양성» 대조 «통과»)")
    if n_none:
        P("🚨 **ROE 가 «없는» %s 건은 Ⓡ 에서 «빠졌다**(① 에는 «남는다») — "
          "**「높은 ROE」와 「ROE 를 «알 수» 있음」이 «섞인다**" % format(n_none, ","))
        P("   ⇒ ⛔ **`220`Ⓓ(P/E)에서 «겪은» 그것**이다 · `220b` 처럼 **«같은» 집합 «안» 대조**는 «안» 했다")
    P(F3)
    P("", flush=True)

    built = {"①": base, "Ⓡ": hi_roe}
    all_d = sorted({d for lst in built.values() for d, _h, _n in lst})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)
    idx_at = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            idx_at[k][pos[d]].append(j)

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return m220.boot_eq(bp, n_pos)

    o = {k: m220.ann(obs(v)) for k, v in built.items()}
    obsd = o["Ⓡ"] - o["①"]

    P("---")
    P("")
    P("# 2. **판정**")
    P("")
    P("| 블록 | **점추정** | **95% CI** | CI폭 | **MDE** | MDE÷Δ | t | 판정칸 |")
    P("|---|---:|---:|---:|---:|---:|---:|:--|")
    cells, mdes = [], []
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m220.BMIN, m220.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = []
        for bi in range(NBOOT):
            order = m220.draw(n_pos, rnd)
            eqs = {}
            for k, lst in built.items():
                bp = defaultdict(list)
                ia = idx_at[k]
                for newp, oldp in enumerate(order):
                    for j in ia.get(oldp, ()):
                        _d, h, nt = lst[j]
                        bp[newp].append((h, nt, 0))
                eqs[k] = m220.ann(m220.boot_eq(bp, n_pos))
            boots.append(eqs["Ⓡ"] - eqs["①"])
            if (bi + 1) % 500 == 0:
                P("  [블록 %d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        v = sorted(boots)
        lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
        sd = st.stdev(boots)
        mde = MDE_K * sd
        tt = abs(obsd) / max(sd, 1e-9)
        if lo >= DELTA:
            cell = "**1** ✅"
        elif hi <= -DELTA:
            cell = "**2**"
        elif lo <= 0 <= hi:
            cell = "**5** 🚨"
        elif -DELTA <= lo and hi <= DELTA:
            cell = "**4a**"
        else:
            cell = "**4b**"
        cells.append(cell)
        mdes.append(mde)
        P("| **%d~%d** | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | **%.3f** | %.2f | %.2f | %s |"
          % (bmn, bmx, obsd, lo, hi, hi - lo, mde, mde / DELTA, tt, cell))
    P("")
    P(F3)
    P("**두 블록의 판정칸이 %s**"
      % ("«같다» ⇒ ✅ 블록 길이에 «안» 흔들린다" if cells[0] == cells[1] else "«다르다» ⇒ 🚨"))
    P(F3)
    P("")
    P("## 사전등록 «셋» 중")
    P("")
    P(F3)
    if "**1**" in cells[0]:
        P("⇒ ① " + PRE_UP)
    elif "**2**" in cells[0]:
        P("⇒ ② " + PRE_DN)
    else:
        P("⇒ ③ " + PRE_NO)
    P(F3)
    P("")
    P("## 🚨 **«예상»과 맞댄다**")
    P("")
    P(F3)
    P("   «예상»: **Ⓥ 무리라 MDE 가 «작을» 것**(견줌 **3.3~4.7배**)")
    P("   «관측»: **%.2f 배**" % (mdes[0] / DELTA))
    P("   ⇒ %s" % ("✅ **Ⓥ 무리 범위 «안»**" if 3.3 <= mdes[0] / DELTA <= 4.8
                   else "🚨 **Ⓥ 무리 범위를 «벗어났다» — 그게 «소득»이다**"))
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① 🚨 **「«같은» 산업과 «비교»」를 «뺐다** — **업종 라벨이 «시점» 자료가 «아니다**(`196`·§G)")
    P("     ⇒ **원전은 「«산업» 대비」라 했는데 — «우리»는 «절대» 15% 로 쟀다**")
    P("⛔ ② **ART 는 «후행 12개월»**이다 — **분기(ARQ)와 «다른» 자**다")
    P("⛔ ③ 🚨 **「15%」는 «범위»의 «아래»끝**이고 — 원전은 「**«또는» 그 «이상**»」이라 "
      "**«문턱»을 «단정»하지 «않았다**")
    if n_none:
        P("⛔ ④ **ROE «없는» %s 건이 Ⓡ 에서 «빠졌다** — «같은» 집합 «안» 대조(`220b` 방식)는 **«안** 했다"
          % format(n_none, ","))
    P("⛔ ⑤ 승률·거래당은 **«안» 적는다**")
    P(F3)
    P("")
    P("## 📌 **`criteria.py:25` 주석 — Ⓓ4 «후보»로 «올린다**")
    P("")
    P(F3)
    P("   주석: 「**한국 보정: 17 → 15**」")
    P("   🔎 **원전이 «이미» 15 를 «아래»끝으로 준다**(v2:42) ⇒ **「17 에서 «내렸다»」가 «흔들린다**")
    P("   ⇒ ⛔ **«이» 판이 «판정»하지 «않는다** — **Ⓓ4 «후보»로 «올리고» «다음» 판에 «넘긴다**")
    P("   ⚠️ 그리고 " + c("criteria.py") + " 는 🔵 **«실전»만 축**이다(`216`) — **«이» 판(미국 백테스트)과 «안» 닿는다**")
    P(F3)
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

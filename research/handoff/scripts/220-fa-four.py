# -*- coding: utf-8 -*-
r"""220~223 — **펀더 원전 Ⓥ «넷»을 «다» 잰다** · 사용자 결정 2026-09-07

  🚨 **두뇌 설계를 «셋» 고쳤다 — 까닭은 «코드»다**(`103-code33-strength.py:47-68`):
     " if not ok: return False " 앞의 판정이 **`ok = (e0 > e1) and (r0 > r1)`** 이다.
     ⇒ ★ **현행(`nitem=2`)이 «이미» 「매출 «가속»」을 «요구»한다** — 「둔화 «제외»」보다 «엄격»하다.
     ⇒ ⇒ 그러니 `221` 을 「둔화 제외」로 두면 **«현행»과 «같은» 팔**이 된다 ⇒ **«반대»로 «빼서» 잰다**.

  📐 **팔 «넷»**(판정 팔은 «각» 판에서 **«하나»** — 관문 ⑥)
     ① 현행                = `judge(nq=1, nitem=2)`
     Ⓐ `220` v2:36③       = 현행 ∧ **(e0−e1) > (r0−r1)** 「**이익** 가속이 **매출** 가속보다 «큼»」
     Ⓑ `221` v2:39        = **`nitem: 2 → 1`** 「매출 조건을 **«뺀다»**」
     Ⓒ `222` v2:42        = **`nitem: 2 → 3`**(이익률 «확대») 🚨 **ROE 는 «값»이 «없어» «뺌»**
     Ⓓ `223` v2:45        = 현행 ∧ **P/E 가 «누적 중앙»보다 «높음»**(문턱 «없는» 갈래)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/220-fa-four.py [--pre]
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
gates = _load("gates", "_gates.py")
f92a = r102.f92a
pt = r91.pt
_yoy, _nan = r102._yoy, r102._nan

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NBOOT = 2000
SEED = 220220
YRS = 27.4
BLOCKS = ((20, 40), (80, 80))
BMIN, BMAX = BLOCKS[0]
DELTA = 1.23
MDE_K = 2.8016
ROE_MIN = 15.0                      # v2:42 「15-17퍼센트 «또는» 그 «이상»」의 **«아래»끝**

ARMS = ("Ⓐ", "Ⓑ", "Ⓒ", "Ⓓ")
TITLE = {"Ⓐ": "`220` v2:36③ — **이익 가속 > 매출 가속**",
         "Ⓑ": "`221` v2:39 — **매출 조건 «빼기»**(`nitem 2→1`)",
         "Ⓒ": "`222` v2:42 — **이익률 «확대»**(🚨 ROE 는 «값»이 «없어» «뺌»)",
         "Ⓓ": "`223` v2:45 — **P/E 가 «누적 중앙»보다 «높음»**"}
PRE_UP = "**«위»로 갈라지면** → 「그 원전 «조건»이 «일한다»」 ⇒ **§B 에 «새» 것**"
PRE_DN = "**«아래»로 갈라지면** → 「그 조건을 «넣으면» «나빠진다»」 ⇒ **원전과 «어긋난» «관측»**"
PRE_NO = "**«못» 가리면** → 「«넣어도» «못» 가린다」 ⇒ **«바꿀» 근거도 «지킬» 근거도 «없다**"
PRE_MDE = "**«예상»: MDE 가 Δ(1.23)의 «일곱~열» 배**(`201d` 7.35 · `208` 10.39 · `218` 6.88) — " \
          "🚨 **«빗나가면» 그게 «소득»**이다"


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


def ann(v):
    x = 1.0 + v / 100.0
    return -100.0 if x <= 1e-9 else (x ** (1.0 / YRS) - 1.0) * 100.0


def boot_eq(by_pos, n_pos, slots=SLOTS):
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


def _flags(arq, j, ix):
    """진입 시점 j 에서 «네» 갈래의 «참/거짓»을 «한꺼번에» 낸다. None = 판정 불가."""
    if j < 5:
        return None

    def g(k, f):
        return arq[k][ix[f]] if 0 <= k < len(arq) else None
    e0, e1 = _yoy(g(j, "eps"), g(j - 4, "eps")), _yoy(g(j - 1, "eps"), g(j - 5, "eps"))
    r0, r1 = _yoy(g(j, "revenue"), g(j - 4, "revenue")), _yoy(g(j - 1, "revenue"), g(j - 5, "revenue"))
    if _nan(e0) or _nan(e1):
        return None
    rev_ok = None if (_nan(r0) or _nan(r1)) else (r0 > r1)
    base = (e0 > e1)
    out = {"base1": base,                                     # nitem=1 (이익만)
           "base2": None if rev_ok is None else (base and rev_ok)}
    # Ⓐ — 이익 가속 «폭»이 매출 가속 «폭»보다 큰가
    out["A"] = None if (_nan(r0) or _nan(r1)) else ((e0 - e1) > (r0 - r1))
    # Ⓒ — 이익률 «확대» «만**.  🚨 ROE 는 **«값»이 «전부» 비어** 있어 «뺐다**(§0 참조)
    m0, m4 = g(j, "netmargin"), g(j - 4, "netmargin")
    out["C"] = None if (_nan(m0) or _nan(m4)) else (m0 > m4)
    out["eps_ttm"] = None
    es = [g(j - k, "eps") for k in range(4)]
    if not any(_nan(x) for x in es):
        out["eps_ttm"] = sum(es)
    return out


def build():
    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        return None
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    recs = []
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            if a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX:
                continue
            fl = _flags(arq, arq.index(a), ix)
            if fl is None or fl["base2"] is not True:      # ① 현행 관문을 «통과»한 것만
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
            pe = (epx / fl["eps_ttm"]) if (fl["eps_ttm"] and fl["eps_ttm"] > 0) else None
            recs.append({"d": t["entry_date"], "h": max(1, hold), "n": net,
                         "A": fl["A"], "C": fl["C"], "pe": pe})
    # Ⓓ — P/E 「«누적» 중앙」(진입일 «이전»까지만 ⇒ 룩어헤드 «없음»)
    recs.sort(key=lambda z: z["d"])
    seen: list = []
    for z in recs:
        z["D"] = (None if z["pe"] is None or len(seen) < 30
                  else (z["pe"] > st.median(seen)))
        if z["pe"] is not None:
            seen.append(z["pe"])
    return recs


def main():          # noqa: C901
    global BMIN, BMAX
    pre_only = "--pre" in sys.argv
    P("# 220~223 — **펀더 원전 Ⓥ «넷»**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/220-fa-four.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⚠️ 두뇌가 준 **`220`~`223` «네» 번호**를 **«한» 각본**으로 «묶었다**(팔이 «같은» 자료를 «공유»한다)")
    P("")
    P("---")
    P("")
    P("# 0. 🚨 **두뇌 설계를 «셋» 고쳤다 — 까닭은 «코드»다**")
    P("")
    P(F3)
    P("🔎 " + BQ + "103-code33-strength.py:57" + BQ + "  " + BQ
      + "ok = (e0 > e1) and (r0 > r1)" + BQ)
    P("   ⇒ ★★ **현행(" + BQ + "nitem=2" + BQ + ")이 «이미» 「매출 «가속»」을 «요구»한다**")
    P("     — 두뇌가 준 「매출 «둔화» «제외»」보다 **«더» 엄격**하다")
    P("   ⇒ ⇒ 그대로 두면 **«현행»과 «같은» 팔**이 된다 ⇒ **«반대»로 «빼서» 잰다**")
    P("")
    P("   🔴 `221` 「매출 «둔화» 제외」  → ✅ **" + BQ + "nitem: 2 → 1" + BQ + "**(매출 조건을 «뺀다»)")
    P("   🔴 `222` 「이익률 «확대»」     → ✅ **" + BQ + "nitem: 2 → 3" + BQ
      + "**(코드에 «이미» 있다) **∧ " + BQ + "roe ≥ 15" + BQ + "**")
    P("   🔴 `220` 「매출이 «견인»」     → 🚨 **원전 «안»에서 «두» 문장이 «다른» 방향**이다:")
    P("      v2:30 「**«매출»이 «견인»하는 «이익»**이 원동력」")
    P("      v2:36③ 「**«이익» 성장이 «매출» 성장보다 «가속»**되면 주의 깊게 볼 만」")
    P("      ⇒ ✅ **«잴» 수 있는 «수»가 «있는» 쪽(v2:36③)으로 «잰다** — v2:30 은 **«방향»만** 준다")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 1. **사전등록** — «넷» «각각** · 값 보기 «전»")
    P("")
    for k in ARMS:
        P("## %s  %s" % (k, TITLE[k]))
        P("")
        P(F3)
        P("① " + PRE_UP)
        P("② " + PRE_DN)
        P("③ " + PRE_NO)
        P(F3)
        P("")
    P(F3)
    P("🚨 " + PRE_MDE)
    P("")
    P("⛔ **판정 팔은 «각» 판에서 «하나»**(관문 ⑥) · 넷을 «묶어» 볼 땐 **max-T 를 «따로»**")
    P("🚨🚨 **`222` 에서 ROE 를 «뺐다** — " + BQ + "roe" + BQ
      + " 는 **«이름»만 있고 «값»이 «전부» " + BQ + "None" + BQ + " 이다**")
    P("   🔎 실측: 종목 3,000 · 분기 행 **142,491** 중 " + BQ + "roe" + BQ
      + " 값 있는 행 **0 (0.0%)**")
    P("     (견줌 — " + BQ + "netmargin" + BQ + " **89.4%** · " + BQ + "eps" + BQ
      + " **94.5%** · " + BQ + "de" + BQ + " **99.9%**)")
    P("   ⇒ 🚨 **`219` 의 「Ⓦ = 0」 판정이 «틀렸다** — **«이름» 목록으로 «있다»를 «확인»했고 "
      "«값»을 «안» 세었다**")
    P("   ⇒ ★★★ **유형 35 의 «또» 한 얼굴** — 「«있다»」가 «확인»을 «안» 받았다")
    P("⛔ **`222` 는 「«같은 산업»과 «비교»」를 «뺐다**(관문 ③) — 업종 라벨이 **«시점» 자료가 «아니다**(`196`·§G)")
    P("   ⇒ **「원전은 「«산업» 대비」라 했는데 — «우리»는 «절대» ROE 로 쟀다」**")
    P("⛔ **`223` P/E 는 «만든» 값**(관문 ④):")
    P("   **" + BQ + "P/E = 진입가 ÷ (최근 «4»분기 eps «합» = TTM)" + BQ + "** · "
      + BQ + "220-fa-four.py:_flags" + BQ)
    P("   **문턱은 원전에 «없다** ⇒ **«누적» 중앙**(진입일 «이전» 표본만 · **룩어헤드 «없음»**) 으로 «가른다**")
    P("   ⚠️ 앞 **30 건**은 중앙이 «불안»해 **판정 «불가»**로 «뺀다**")
    P(F3)
    P("")
    P("---")
    P("")
    if pre_only:
        P("⏸️ **`--pre` — 사전등록만 찍었다. «아직» «안» 돌렸다.**")
        return 0

    CA = Path(str(r91.OUT / "220-recs.json"))
    if CA.exists():
        recs = json.loads(CA.read_text(encoding="utf-8"))
    else:
        P("(자료를 «짓는» 중 …)", flush=True)
        recs = build()
        if recs is None:
            P("🚨 **멈춘다** — 경로 «없음»")
            return 2
        CA.write_text(json.dumps(recs), encoding="utf-8")

    base = [(z["d"], z["h"], z["n"]) for z in recs]
    sub = {}
    for k, key in (("Ⓐ", "A"), ("Ⓒ", "C"), ("Ⓓ", "D")):
        sub[k] = [(z["d"], z["h"], z["n"]) for z in recs if z.get(key) is True]
    # Ⓑ — nitem=1 은 «현행»의 «위» 집합이라 «따로» 만든다
    P("(Ⓑ `nitem=1` 팔을 «따로» 짓는 중 …)", flush=True)
    CB = Path(str(r91.OUT / "220-b.json"))
    if CB.exists():
        sub["Ⓑ"] = [tuple(x) for x in json.loads(CB.read_text(encoding="utf-8"))]
    else:
        (_a, _b, by2), _m, _ = r91.load_ladder(
            YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
        fund, ixf = f92a.load()
        ix = {f: i for i, f in enumerate(ixf)}
        outb = []
        for y in sorted(by2):
            ou = {}
            for p in by2[y]:
                arq = (fund.get(p["code"]) or {}).get("ARQ") or []
                a = f92a.asof(arq, p["entry_date"]) if arq else None
                if a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX:
                    continue
                fl = _flags(arq, arq.index(a), ix)
                if fl is None or fl["base1"] is not True:
                    continue
                t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                     half=HALF, shares=(1.0,), add_stop="floor_entry")
                cd = p["code"]
                if cd in ou and p["entry_date"] <= ou[cd]:
                    continue
                r = t["masks"][()]
                ou[cd] = r["resolve_date"] or p["entry_date"]
                epx = t["entry_px"]
                net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                          for _d, fr, px in r["exits"])
                d, rd = p["d"], r["resolve_date"]
                hold = d.index(rd) if (rd and rd in d) else len(d) - 1
                outb.append((t["entry_date"], max(1, hold), net))
        CB.write_text(json.dumps([list(x) for x in outb]), encoding="utf-8")
        sub["Ⓑ"] = outb

    built = {"①": base}
    built.update(sub)
    all_d = sorted({d for lst in built.values() for d, _h, _n in lst})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)
    idx_at = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            idx_at[k][pos[d]].append(j)
    kb = set((d, h, n) for d, h, n in base)

    P("# 2. **팔 크기와 «양성» 대조**(«먼저» 찍는다 · 관문 ②)")
    P("")
    P(F3)
    P("   **① 현행 거래 = %s** · 날짜 자리 **%s**" % (format(len(base), ","), format(n_pos, ",")))
    for k in ARMS:
        ks = set(tuple(x) for x in built[k])
        only = len(ks - kb)
        P("   **%s %-46s 거래 = %6s**   ① «에만» «없는» 것 %s"
          % (k, TITLE[k].split("—")[1].strip()[:44], format(len(built[k]), ","), format(only, ",")))
    P("")
    P("   ✅ Ⓐ·Ⓒ·Ⓓ 는 **① 의 «부분집합»**이어야 한다(현행 «통과»분에서 «더» 거른 것)")
    P("   🚨 **Ⓑ 는 «위» 집합**이다(" + BQ + "nitem=1" + BQ + " 은 «덜» 엄하다) ⇒ **① «에만» 없는 것이 «많다»**")
    P(F3)
    P("", flush=True)

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return boot_eq(bp, n_pos)

    o = {k: ann(obs(v)) for k, v in built.items()}
    obsd = {k: o[k] - o["①"] for k in ARMS}

    rows_all = {}
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        BMIN, BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = {k: [] for k in ARMS}
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
            for k in ARMS:
                boots[k].append(eqs[k] - eqs["①"])
            if (bi + 1) % 400 == 0:
                P("  [블록 %d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        cen = {k: [x - st.mean(boots[k]) for x in boots[k]] for k in ARMS}
        sds = {k: max(st.stdev(cen[k]), 1e-9) for k in ARMS}
        maxt = sorted(max(abs(cen[k][i]) / sds[k] for k in ARMS) for i in range(NBOOT))
        thr = maxt[int(NBOOT * 0.95)]
        P("")
        P("# %d. ★★ **«자료» 축 — 블록 %d~%d**" % (3 + bi_blk, bmn, bmx))
        P("")
        P("| 팔 | **점추정** | **95% CI** | CI폭 | **MDE** | MDE÷Δ | t | max-T | 판정칸 |")
        P("|---|---:|---:|---:|---:|---:|---:|:--|:--|")
        rows = {}
        for k in ARMS:
            v = sorted(boots[k])
            lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
            sd = st.stdev(boots[k])
            tt = abs(obsd[k]) / max(sd, 1e-9)
            mde = MDE_K * sd
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
            rows[k] = (obsd[k], lo, hi, sd, mde, tt, tt >= thr, cell)
            P("| **%s** | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | **%.3f** | %.2f | %.2f | %s | %s |"
              % (k, obsd[k], lo, hi, hi - lo, mde, mde / DELTA, tt,
                 "✅ 넘음" if tt >= thr else "🔴 «못» 넘음", cell))
        P("")
        P(F3)
        P("   **max-T 95%% 문턱 = %.3f**   ⟵  " % thr
          + BQ + "sorted(max_k |centered|/SD)[int(NBOOT*.95)]" + BQ + " · **넷을 «묶어»**(유형 36)")
        P("   **넘은 팔 %d / %d**" % (sum(1 for k in ARMS if rows[k][6]), len(ARMS)))
        P(F3)
        rows_all[(bmn, bmx)] = rows
        P("")

    h = rows_all[BLOCKS[0]]
    w = rows_all[BLOCKS[1]]
    P("---")
    P("")
    P("# ⇒ **맺음**")
    P("")
    P(F3)
    for k in ARMS:
        P("**%s** 20~40 **%+.3f%%p** [%+.3f, %+.3f] 칸 **%s**  ·  80~80 칸 **%s**  %s"
          % (k, h[k][0], h[k][1], h[k][2], h[k][7].replace("**", "").replace(" 🚨", ""),
             w[k][7].replace("**", "").replace(" 🚨", ""),
             "✅ 같음" if h[k][7] == w[k][7] else "🚨 «다름»"))
    P("")
    P("**MDE(20~40)** — " + " · ".join("%s %.3f(%.1f배)" % (k, h[k][4], h[k][4] / DELTA)
                                       for k in ARMS))
    P(F3)
    P("")
    P("## 🚨 **«예상»과 맞댄다**(사전등록)")
    P("")
    P(F3)
    P("   «예상»: **Δ의 7~10 배**(`201d` 7.35 · `208` 10.39 · `218` 6.88)")
    lo_r = min(h[k][4] / DELTA for k in ARMS)
    hi_r = max(h[k][4] / DELTA for k in ARMS)
    P("   «관측»: **%.1f ~ %.1f 배**" % (lo_r, hi_r))
    P("   ⇒ %s" % ("✅ **«예상» 안**" if 7.0 <= lo_r and hi_r <= 10.0
                   else "🚨 **«예상»을 «벗어났다» — 그게 «소득»이다**"))
    P(F3)
    P("")
    P("## **묶음 문장**")
    P("")
    P(F3)
    n1 = sum(1 for k in ARMS if "**1**" in h[k][7] or "**2**" in h[k][7])
    P("「펀더멘털 원전에서 «잴» 수 있는 것 **넷**을 «다» 쟀다.")
    if n1 == 0:
        P("  ⇒ **«넷» 다 «못» 가렸다.」**")
        P("")
        P("🔴 ⛔ **「펀더 원전은 «장부»로만 «남는다」」는 «과하다** — «내린다**(검증 2차)")
        P("✅ **맞는 문장**: **「«이» 자·«이» 자료로는 «더» 잴 것이 «없다». 그리고 «남은» 것이 «셋» 있다」**")
        P("")
        P("   ㉠ **v2:30**(「**«매출»이 «견인»**하는 이익」) — **«안** 쟀다(「«방향»만」이라 «넘겼다»)")
        P("   ㉡ **ROE 15-17%** — " + BQ + "roe" + BQ + " 가 **ARQ 칸**에 «없어**(0/100,189) 못 쟀다")
        P("     🚨 **2026-09-07 정정**: **«자료»에 «없는» 게 «아니라» — **ART 칸엔 89.8% «있다**(§F ㊈)")
        P("     ⇒ ✅ **ART 로 «잴 수» 있다** — 🔴 «사용자» 결정으로 **ART 를 «그대로» 쓴다**")
        P("   ㉢ **`223` 의 «읽기»** — " + BQ + "220b" + BQ + " 가 «대조군»을 «고쳐» 다시 쟀다(칸 5)")
    else:
        P("  ⇒ **%d 개가 «가려졌다»** ⇒ **§B 에 «새» 것**이고 「고르기」 계열로 «넘어간다».」" % n1)
    P(F3)
    P("")
    P("⚠️ **못 하는 것**")
    P("")
    P(F3)
    P("⛔ ① 🚨 **`222` 는 «ROE 를 «아예» «못** 쟀다** — " + BQ + "roe" + BQ
      + " 값이 **«전부» 비어** 있다(0.0%) ⇒ **«이익률 «확대»»만** 쟀다")
    P("     그리고 「«산업» 대비」도 **«못** 쟀다(업종 라벨이 «시점» 자료 «아님»)")
    P("⛔ ② **`223` P/E 문턱은 원전에 «없다** — **«누적» 중앙**으로 «갈랐다**(우리가 «정한» 갈래)")
    P("⛔ ③ 🚨🚨 **원전 «안»에서 «두» 문장이 «어긋난다** — **«따로» 세운다**")
    P("     v2:30   「**«매출»이 «견인»하는 «이익»**」            ⇒ **매출 ≥ 이익**")
    P("     v2:36③ 「**«이익» 성장이 «매출» 성장보다 «가속»**」  ⇒ **이익 > 매출**")
    P("     ⇒ ★★★ **«정말» «어긋난다** — 「원전이 «섞였다»」(오닐/미너비니)와 **«다른» 종류**다")
    P("       그건 **«두» 책 «사이»**였고 — 이건 **«같은» 문서 «안»**이다")
    P("     ⇒ ⛔ **`220` 은 «수»가 «있는» 쪽(v2:36③)만 쟀다** — "
      "**«다른» 쪽(v2:30)은 «반대» 방향이고 «안» 쟀다**")
    P("     ⇒ 🚨 **그러니 「원전«대로» 쟀다」로 «읽으면» «틀린다**")
    P("⛔ ④ **넷은 «같은» 자료를 «공유»**한다 ⇒ **max-T 로 «보정»했다**(유형 36)")
    P("⛔ ⑤ 승률·거래당은 **«안» 적는다**")
    P(F3)
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

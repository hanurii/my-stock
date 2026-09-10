# -*- coding: utf-8 -*-
r"""227b — **유동성 문턱을 «빼면» 어떻게 되나 — 판정** · 🔴 사용자 결정 2026-09-07

  ⛔ **사전등록은 `results/227-PRE.md` 에 «먼저» 박았다**(경로를 «만들기» «전»).
     ① Ⓧ 가 «위» → 「문턱을 «빼면» «낫다」 ⇒ 문턱이 «해»를 끼치고 있었다
     ② Ⓧ 가 «아래» → 「문턱이 «일한다」 ⇒ «지킬» 근거가 «생긴다»
     ③ «못» 가림 → §B⑮ 가 「«안» 쟀다」→「봤는데 «못» 가렸다」

  📐 **팔 «둘»** — ① 현행(`.cache/bt5y/sub/` · 5.0억원 = $384,615/일)
                 Ⓧ 문턱 «없음»(`D:/stock-data/uspath-noliq/` · 0.0)
     ⛔ **그 «밖»은 «한 글자»도 «안» 바꾼다**(청산·슬롯·검출기·펀더 관문·사다리 칸·RS 80).

  ⛔ **판정 팔 «하나»**(Ⓧ − ①) · 승률·거래당 «안» 적음.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/227b-noliq-judge.py
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

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NBOOT, SEED, YRS = 2000, 227227, 27.4
BLOCKS = ((20, 40), (80, 80))
BMIN, BMAX = BLOCKS[0]
DELTA, MDE_K = 1.23, 2.8016
NOLIQ = Path("D:/stock-data/uspath-noliq")
CANON = r91.SUB

A_UP = "**Ⓧ 가 «위»로 갈라지면** → 「**문턱을 «빼면» «낫다**」 ⇒ **문턱이 «해»를 끼치고 있었다**"
A_DN = "**Ⓧ 가 «아래»로 갈라지면** → 「**문턱이 «일한다**」 ⇒ **«지킬» 근거가 «생긴다**"
A_NO = ("**«못» 가리면** → 「**«빼도» «넣어도» «못» 가린다**」 ⇒ "
        "**§B⑮ 가 「«안» 쟀다」에서 「봤는데 «못» 가렸다」로 «바뀐다**")


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


def build(sub_dir):
    """`201d`·`218` 과 **«한 글자»도 «다르지» 않은** 구성 — 경로 «자리»만 바꾼다."""
    old = r91.SUB
    r91.SUB = sub_dir
    try:
        (_a, _b, by2), missing, _ = r91.load_ladder(
            YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    finally:
        r91.SUB = old
    if missing:
        return None, missing
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    out, keys = [], set()
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
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
            net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2)) for _d, fr, px in r["exits"])
            d, rd = p["d"], r["resolve_date"]
            hold = d.index(rd) if (rd and rd in d) else len(d) - 1
            out.append((t["entry_date"], max(1, hold), net))
            keys.add((t["entry_date"], p["code"], p["pattern"]))
    return out, keys


def main():          # noqa: C901
    global BMIN, BMAX
    n_have = len(list(NOLIQ.glob("uspath_*.json")))
    P("# 227b — **유동성 문턱을 «빼면» 어떻게 되나**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/227b-noliq-judge.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **사전등록은 " + BQ + "results/227-PRE.md" + BQ + " 에 «먼저» 박았다**(경로 «만들기» «전»)")
    P("")
    P("---")
    P("")
    P("# 0. **사전등록**(«그대로» 옮긴다)")
    P("")
    P(F3)
    P("① " + A_UP)
    P("② " + A_DN)
    P("③ " + A_NO)
    P("")
    P("«예상»: **Ⓤ 무리**(«유니버스» «자체»를 바꾼다) ⇒ **MDE 가 «클» 것** "
      "⛔ 「7~10배」를 «수»로 «옮기지» 않는다 · ✅ **«빗나가면» 그게 «소득»**")
    P("")
    P("⛔ **«이겨도» «못» 쓰는 것**: Ⓧ 가 «나아도» 「**«백테스트» 유니버스**를 넓히라」이지")
    P("   **「문턱을 «없애라»」가 «아니다** — **「«살» 수 «있나»」를 «안** 쟀다")
    P(F3)
    P("")
    P("---")
    P("")
    if n_have < len(YEARS):
        P("🚨 **멈춘다** — 경로가 **%d / %d** 해뿐이다(`227a` 가 «아직» 안 끝났다)"
          % (n_have, len(YEARS)))
        return 3

    CA = Path(str(r91.OUT / "227-arms.json"))
    if CA.exists():
        d_ = json.loads(CA.read_text(encoding="utf-8"))
        built = {k: [tuple(x) for x in v] for k, v in d_["arms"].items()}
        meta = d_["meta"]
    else:
        P("(① 현행 팔을 «짓는» 중 …)", flush=True)
        a1, k1 = build(CANON)
        if a1 is None:
            P("🚨 **멈춘다** — ① 경로 «없음» %s" % k1)
            return 2
        P("(Ⓧ 문턱 «없는» 팔을 «짓는» 중 …)", flush=True)
        ax, kx = build(NOLIQ)
        if ax is None:
            P("🚨 **멈춘다** — Ⓧ 경로 «없음» %s" % kx)
            return 2
        meta = {"n1": len(a1), "nx": len(ax),
                "only1": len(k1 - kx), "onlyx": len(kx - k1)}
        built = {"①": a1, "Ⓧ": ax}
        CA.write_text(json.dumps({"arms": {k: [list(x) for x in v] for k, v in built.items()},
                                  "meta": meta}), encoding="utf-8")

    P("# 1. **팔 크기와 «양성» 대조**(«먼저» 찍는다)")
    P("")
    P(F3)
    P("   **① 현행(5.0억원 = $384,615/일) 거래 = %s**" % format(meta["n1"], ","))
    P("   **Ⓧ 문턱 «없음»(0.0)        거래 = %s**" % format(meta["nx"], ","))
    P("")
    P("   **★ ① «에만» 있는 거래 = %s**" % format(meta["only1"], ","))
    P("   **★ Ⓧ «에만» 있는 거래 = %s**" % format(meta["onlyx"], ","))
    P("")
    if meta["only1"] == 0:
        P("✅ **① ⊂ Ⓧ** — 문턱을 «뺐더니» 거래가 **«늘기»만 했다**(«양성» 대조 «통과»)")
    else:
        P("🚨 **① «에만» 있는 거래가 %s** — " % format(meta["only1"], ",")
          + BQ + "open_until" + BQ + " «중복 제거»의 «연쇄»다(`201d`·`218` 에서 «본» 그것)")
        P("   ⇒ **«오염»이 «아니라» «처치»의 «일부»**다 — 문턱을 «빼면» 진입 «순서»가 «실제»로 바뀐다")
    P(F3)
    P("", flush=True)

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
        return boot_eq(bp, n_pos)

    o = {k: ann(obs(v)) for k, v in built.items()}
    obsd = o["Ⓧ"] - o["①"]

    P("---")
    P("")
    P("# 2. **팔의 «절대» 값**(연환산 %p · 참고)")
    P("")
    P(F3)
    P("   ①  **%+.3f%%p/해**" % o["①"])
    P("   Ⓧ  **%+.3f%%p/해**" % o["Ⓧ"])
    P("   날짜 자리 **%s**" % format(n_pos, ","))
    P(F3)
    P("")
    rows = {}
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        BMIN, BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = []
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
            boots.append(eqs["Ⓧ"] - eqs["①"])
            if (bi + 1) % 400 == 0:
                P("  [블록 %d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        v = sorted(boots)
        lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
        sd = st.stdev(boots)
        tt = abs(obsd) / max(sd, 1e-9)
        bias = st.median(boots) - obsd
        mde = MDE_K * sd
        if lo >= DELTA:
            cell = "**1** ✅"
        elif hi <= -DELTA:
            cell = "**2**"
        elif lo <= 0 <= hi:
            cell = "**5** 🚨 «못 가린다»"
        elif -DELTA <= lo and hi <= DELTA:
            cell = "**4a**"
        else:
            cell = "**4b**"
        rows[(bmn, bmx)] = (obsd, lo, hi, sd, mde, tt, bias, cell)
        P("")
        P("# %d. ★★ **«자료» 축 — 블록 %d~%d**" % (3 + bi_blk, bmn, bmx))
        P("")
        P("| 짝 | **점추정** | **95% CI** | CI폭 | **MDE** | MDE÷Δ | t | **편향** | 판정칸 |")
        P("|---|---:|---:|---:|---:|---:|---:|---:|:--|")
        P("| **Ⓧ−①** | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | **%.3f** | %.2f | %.2f | %+.3f | %s |"
          % (obsd, lo, hi, hi - lo, mde, mde / DELTA, tt, bias, cell))
        P("")
        for ln in gates.shared_axis_note(
                NBOOT, ["같은 청산 규칙(+30/−10·절반+추격)", "같은 슬롯 수(5)",
                        "같은 검출기 «집합»", "같은 사다리 칸(②)", "같은 RS 문턱(80)",
                        "같은 펀더 관문(103 · nq=1·nitem=2)"]):
            P(ln)
        P("")

    h, w = rows[BLOCKS[0]], rows[BLOCKS[1]]
    P("---")
    P("")
    P("# ⇒ **맺음**")
    P("")
    P(F3)
    P("**Ⓧ − ①**  20~40  **%+.3f%%p** [%+.3f, %+.3f]  칸 **%s**"
      % (h[0], h[1], h[2], h[7].replace("**", "").replace(" 🚨 «못 가린다»", "")))
    P("            80~80  **%+.3f%%p** [%+.3f, %+.3f]  칸 **%s**"
      % (w[0], w[1], w[2], w[7].replace("**", "").replace(" 🚨 «못 가린다»", "")))
    P("")
    P("**MDE**(20~40) = **%.3f%%p** = Δ(%.2f)의 **%.2f 배**" % (h[4], DELTA, h[4] / DELTA))
    P("   ⟵ 견줌: " + BQ + "201d" + BQ + " 7.35 · " + BQ + "208" + BQ + " 10.39 · "
      + BQ + "218" + BQ + " 6.88 (**Ⓤ 무리**) · " + BQ + "220" + BQ + "~" + BQ + "223" + BQ
      + " 3.3~4.8 (**Ⓥ 무리**)")
    P(F3)
    P("")
    P(F3)
    P("**두 블록의 판정칸이 %s**"
      % ("«같다» ⇒ ✅ 블록 길이에 «안» 흔들린다" if h[7] == w[7] else "«다르다» ⇒ 🚨 «머리»는 «넓은» 쪽"))
    P(F3)
    P("")
    P("## 사전등록 «셋» 중")
    P("")
    P(F3)
    if "**1**" in h[7]:
        P("⇒ ① " + A_UP)
    elif "**2**" in h[7]:
        P("⇒ ② " + A_DN)
    else:
        P("⇒ ③ " + A_NO)
    P(F3)
    P("")
    P("## 🚨 **«예상»과 맞댄다**")
    P("")
    P(F3)
    P("   «예상»: **Ⓤ 무리라 MDE 가 «클» 것**(⛔ 「7~10배」를 «수»로 «옮기지» 않았다)")
    P("   «관측»: **%.2f 배**" % (h[4] / DELTA))
    P("   ⇒ %s" % ("✅ **Ⓤ 무리 범위(6.88~10.39) «안»**" if 6.88 <= h[4] / DELTA <= 10.39
                   else "🚨 **Ⓤ 무리 범위를 «벗어났다» — 그게 «소득»이다**"))
    P(F3)
    P("")
    P("⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① 🚨 **「«살» 수 «있나»」를 «안** 쟀다 — **하루 거래대금이 «작은» 종목은 «실제»로 «못» 산다**")
    P("     ⇒ **「«성적»이 «어떤가」만** 쟀다. **«실행» 가능성은 «다른» 물음**이다")
    P("⛔ ② **문턱 «둘»만**(5.0 · 0.0) — **«격자»가 «아니다**(원전이 「문턱 «숫자»가 «없다」 했으므로 "
      "물음이 「«있나» «없나»」였다)")
    P("⛔ ③ **환율 «고정» 1,300원** — 27.4년 «전체»에 «한» 값(" + BQ + "us_loader.py:84" + BQ
      + ") · **«민감도»를 «돌린» 기록은 «못** 찾았다 ⇒ **§G 후보**")
    P("⛔ ④ 승률·거래당은 **«안» 적는다**")
    P(F3)
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

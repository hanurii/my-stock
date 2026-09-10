# -*- coding: utf-8 -*-
r"""218 — **펀더 관문 `nq: 1 → 4`** — 원전(Ⓜ)의 「최근 «4분기» 가속」 · 2026-09-07

  🚨 **왜** — `217` v2 `:36` **[미너비니]**
     「**최근 «4분기» 동안 «분기별» 이익 «성장 속도»가 «빨라져야»** 합니다」
     🔎 우리 백테스트 펀더 관문(`201d:133`) = `r103.judge(arq, j, ix, **1**, 2)` = **«1» 분기**
     ⇒ ★ `215` 가 좁힌 것: **「«수준» vs «가속»」이 «아니라» — 「«몇» 분기를 «보는가»」**

  ⛔ **「Ⓜ 이라서 «잰다»」가 «아니라 「Ⓜ 이고 «잴» 수 «있어서»」**다.
  ⛔ **«이겨도» «못» 쓰는 것**: `nq=4` 가 «나아도» 그건 「**«백테스트» 관문**을 바꾸라」이지
     「원전이 «옳다»」가 «아니다** — **「가속」의 «정의»가 «같은지»는 «안» 쟀다**.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/218-nq-four.py
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
NBOOT = 2000
SEED = 218218
YRS = 27.4
BLOCKS = ((20, 40), (80, 80))
BMIN, BMAX = BLOCKS[0]
DELTA = 1.23
MDE_K = 2.8016

A_UP = ("**Ⓝ 가 «위»로 갈라지면** → 「**«4분기»를 보면 «낫다**」 — 원전 쪽 «수»가 «일한다»")
A_DN = ("**Ⓝ 가 «아래»로 갈라지면** → 「**«1분기»가 «일한다**」 — 우리 «현행»이 «지킨다»")
A_NO = ("**«못» 가리면** → **「원전의 «4분기»를 «넣어도» «못» 가린다」**가 «관측»되고 "
        "— **«바꿀» 근거도 «지킬» 근거도 «없다»**")


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


def build(nq):
    """nq = «몇» 분기를 «보는가». 그 «밖»은 `201d` 와 «한 글자»도 «안» 바꾼다."""
    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        return None, None
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    out, keys, n_none = [], set(), 0
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None
                          or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, nq, 2))
            if v is None:
                n_none += 1
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
            keys.add((t["entry_date"], p["code"], p["pattern"]))
    return out, (keys, n_none)


def main():          # noqa: C901
    global BMIN, BMAX
    P("# 218 — **펀더 관문 " + BQ + "nq: 1 → 4" + BQ + "**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/218-nq-four.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("---")
    P("")
    P("# 0. **사전등록** — 값 보기 «전»에 «셋 다**")
    P("")
    P(F3)
    P("① " + A_UP)
    P("② " + A_DN)
    P("③ " + A_NO)
    P("")
    P("⛔ **「Ⓜ 이라서 «잰다»」가 «아니라 「Ⓜ 이고 «잴» 수 «있어서»」**다 — **Ⓤ 였던 여덟은 «못» 잰다**")
    P("⛔ 🚨 **«이겨도» «못» 쓰는 것**: `nq=4` 가 나아도 **「«백테스트» 관문을 바꾸라」**이지")
    P("   **「원전이 «옳다»」가 «아니다** — 원전은 「최근 4분기 «분기별» 성장 «속도»가 «빨라져야»」이고")
    P("   우리 " + BQ + "103.judge" + BQ + " 는 **「eps·revenue YoY 가 «직전»보다 «큰» 분기가 nq 개 «연속»」**이다")
    P("   ⇒ ★ **「가속」의 «정의»가 «같은지»는 «안** 쟀다")
    P("⛔ **판정 팔 «하나»**(Ⓝ − ①). **청산·슬롯·검출기·사다리 칸은 «한 글자»도 «안» 바꾼다**")
    P(F3)
    P("")
    P("---")
    P("")

    CA = Path(str(r91.OUT / "218-arms.json"))
    if CA.exists():
        d_ = json.loads(CA.read_text(encoding="utf-8"))
        built = {k: [tuple(x) for x in v] for k, v in d_["arms"].items()}
        meta = d_["meta"]
    else:
        P("(자료를 «짓는» 중 — `nq=1` …)", flush=True)
        a1, m1 = build(1)
        if a1 is None:
            P("🚨 **멈춘다** — 경로 «없음»")
            return 2
        P("(… `nq=4`)", flush=True)
        a4, m4 = build(4)
        k1, k4 = m1[0], m4[0]
        meta = {"n1": len(a1), "n4": len(a4), "none1": m1[1], "none4": m4[1],
                "only1": len(k1 - k4), "only4": len(k4 - k1)}
        built = {"①": a1, "Ⓝ": a4}
        CA.write_text(json.dumps({"arms": {k: [list(x) for x in v] for k, v in built.items()},
                                  "meta": meta}), encoding="utf-8")

    P("# 1. **팔 크기와 «양성» 대조**(«먼저» 찍는다)")
    P("")
    P(F3)
    P("   **① " + BQ + "nq=1" + BQ + "(현행) 거래 = %s**" % format(meta["n1"], ","))
    P("   **Ⓝ " + BQ + "nq=4" + BQ + "(원전)  거래 = %s**" % format(meta["n4"], ","))
    P("   판정 «불가»(" + BQ + "None" + BQ + ") — nq=1 **%s** · nq=4 **%s**"
      % (format(meta["none1"], ","), format(meta["none4"], ",")))
    P("")
    P("   **★ Ⓝ «에만» 있는 거래 = %s**" % format(meta["only4"], ","))
    P("   **★ ① «에만» 있는 거래 = %s**" % format(meta["only1"], ","))
    P("")
    if meta["only4"] == 0:
        P("✅ **Ⓝ ⊂ ①** — 관문을 **«좁혔더니»** 거래가 **«줄기»만 했다**(«양성» 대조 통과)")
    else:
        P("🚨 **Ⓝ «에만» 있는 거래가 %s** — `open_until` «연쇄»다(`201d` 에서 «본» 그것) · "
          "**«처치»의 «일부»**" % format(meta["only4"], ","))
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
    obsd = o["Ⓝ"] - o["①"]

    P("")
    P("---")
    P("")
    P("# 2. **팔의 «절대» 값**(연환산 %p · 참고)")
    P("")
    P(F3)
    P("   ①  **%+.3f%%p/해**" % o["①"])
    P("   Ⓝ  **%+.3f%%p/해**" % o["Ⓝ"])
    P("   날짜 자리 **%s**" % format(n_pos, ","))
    P(F3)
    P("")
    P("---")
    P("")

    head = wide = None
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
            boots.append(eqs["Ⓝ"] - eqs["①"])
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
        row = (bmn, bmx, obsd, lo, hi, sd, mde, tt, bias, cell)
        if bi_blk == 0:
            head = row
        else:
            wide = row
        P("")
        P("# %d. ★★ **«자료» 축 — 블록 %d~%d**" % (3 + bi_blk, bmn, bmx))
        P("")
        P("| 짝 | **점추정** | **95% CI** | CI폭 | **MDE** | t | **편향** | 판정칸 |")
        P("|---|---:|---:|---:|---:|---:|---:|:--|")
        P("| **Ⓝ−①** | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | **%.3f** | %.2f | %+.3f | %s |"
          % (obsd, lo, hi, hi - lo, mde, tt, bias, cell))
        P("")
        for ln in gates.shared_axis_note(
                NBOOT, ["같은 청산 규칙(+30/−10·절반+추격)", "같은 슬롯 수(5)",
                        "같은 검출기 «집합»", "같은 사다리 칸(②)", "같은 RS 문턱(80)"]):
            P(ln)
        P("")

    P("---")
    P("")
    P("# ⇒ **맺음**")
    P("")
    P(F3)
    P("**Ⓝ − ①**  블록 20~40  **%+.3f%%p** [%+.3f, %+.3f]  칸 **%s**"
      % (head[2], head[3], head[4], head[9].replace("**", "").replace(" 🚨 «못 가린다»", "")))
    P("            블록 80~80  **%+.3f%%p** [%+.3f, %+.3f]  칸 **%s**"
      % (wide[2], wide[3], wide[4], wide[9].replace("**", "").replace(" 🚨 «못 가린다»", "")))
    P("")
    P("**MDE**(20~40) = **%.3f%%p** · Δ = **%.2f%%p** ⇒ **%.2f 배**"
      % (head[6], DELTA, head[6] / DELTA))
    P("   ⟵ 견줌: " + BQ + "201d" + BQ + " **9.040** · " + BQ + "208" + BQ + " **12.783**")
    P(F3)
    P("")
    P(F3)
    P("**두 블록의 판정칸이 %s**"
      % ("«같다»  ⇒ ✅ 블록 길이에 «안» 흔들린다" if head[9] == wide[9]
         else "«다르다»  ⇒ 🚨 «머리»는 «넓은» 쪽"))
    P(F3)
    P("")
    P("## 사전등록 «셋» 중 «어느» 것인가")
    P("")
    P(F3)
    if "**1**" in head[9]:
        P("⇒ ① " + A_UP)
    elif "**2**" in head[9]:
        P("⇒ ② " + A_DN)
    else:
        P("⇒ ③ " + A_NO)
    P(F3)
    P("")
    P("⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **「가속」의 «정의»가 «같은지» «안** 쟀다 — 원전 「분기별 성장 «속도»가 «빨라져야»」 vs "
      + BQ + "103.judge" + BQ + " 「YoY 가 «직전»보다 «큼»이 nq «연속»」")
    P("⛔ ② **nq «둘»만**(1·4) — **격자가 «아니다** ⇒ 「2·3 은 «어떤가」」는 «못» 답한다")
    P("⛔ ③ " + BQ + "nitem" + BQ + " 은 **2 «그대로»**(eps·revenue) — 원전은 「이익」만 말한 대목도 있다")
    P("⛔ ④ **«실전» 관문(" + BQ + "criteria.py" + BQ + ")은 «안» 만졌다** — 그건 🔵 «실전»만 축이다(`216`)")
    P("⛔ ⑤ **승률·거래당은 «안» 적는다**")
    P(F3)
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

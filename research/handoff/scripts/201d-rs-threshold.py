# -*- coding: utf-8 -*-
r"""201d — **RS 문턱 80 → 70. §B⑭ 를 「안 봤다」에서 「봤는데」로 옮긴다** · 2026-09-07

  🚨 **왜** — `200` 이 찾은 것: `criteria.py:29` 의 **80** 은 «오닐» CAN SLIM 「L」이고
     `trend_template.md:9`(미너비니)는 **70** 이다 ⇒ **원전이 «섞였다»**.
     `190` §B⑭ 는 「**RS<80 을 «안» 봤다**」였다.

  📐 **팔** — `201c` 가 만든 `D:/stock-data/uspath-rs70/`(28해·rs70) vs 정본 `.cache/bt5y/sub/`(rs80).
     **청산·슬롯·검출기 집합·펀더 관문은 «한 글자»도 «안» 바꾼다.**

  ⛔ **사전등록**(값 보기 «전»):
     ② 판정 팔 = **«하나»**(Ⓡ − ①). 검출기 갈래는 **«묘사»**다
     ③ **«부호»를 «예상하지» «않는다»**
     ④ **「«못» 가려도 «수확»이 «있다»」** — §B⑭ 가 「안 봤다」→「봤는데 «못» 가렸다」로 «바뀐다»
     ⑤ 승률 인용 **«금지»**

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/201d-rs-threshold.py
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
SEED = 201201
YRS = 27.4
BLOCKS = ((20, 40), (80, 80))
BMIN, BMAX = BLOCKS[0]
DELTA = 1.23
MDE_K = 2.8016
RS70 = Path("D:/stock-data/uspath-rs70")
CANON = r91.SUB

A_UP = "**Ⓡ 가 «위»로 갈라지면** → 「문턱 80 은 «높다»」 — 원전(미너비니 70)이 «맞았다»"
A_DN = "**Ⓡ 가 «아래»로 갈라지면** → 「문턱 80 이 «일한다»」 — 오닐 쪽 값이 «지킨다»"
A_NO = ("**«못» 가리면** → §B⑭ 가 「**안 봤다**」에서 「**봤는데 «못» 가렸다**」로 «바뀐다** "
        "— 그리고 **80 을 «지킬» «근거»도 «바꿀» «근거»도 «없다**")


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


def build_pairs(sub_dir):
    """`193b` §자료 와 «같은» 구성 — 사다리 ② · 펀더 관문 · 중복 제거."""
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
    keep = {}
    for y in sorted(by2):
        keep[y] = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None
                          or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                keep[y].append(p)
    pairs = []
    for y in sorted(keep):
        open_until = {}
        for p in keep[y]:
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 half=HALF, shares=(1.0,), add_stop="floor_entry")
            cd = p["code"]
            if cd in open_until and p["entry_date"] <= open_until[cd]:
                continue
            open_until[cd] = t["masks"][()]["resolve_date"] or p["entry_date"]
            pairs.append((t, p))
    return pairs, []


def trades_of(t, p):
    r = t["masks"][()]
    epx = t["entry_px"]
    net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2)) for _d, fr, px in r["exits"])
    d, rd = p["d"], r["resolve_date"]
    hold = d.index(rd) if (rd and rd in d) else len(d) - 1
    return (t["entry_date"], max(1, hold), net)


def main():  # noqa: C901
    global BMIN, BMAX
    P("# 201d — **RS 문턱 80 → 70**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/201d-rs-threshold.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("---")
    P("")
    P("# 0. **사전등록** — 값 보기 «전»에 «셋 다» 적는다")
    P("")
    P(F3)
    P("① " + A_UP)
    P("② " + A_DN)
    P("③ " + A_NO)
    P("")
    P("⛔ **판정 팔 = «하나»**(Ⓡ − ①). 검출기 갈래(VCP·3C·PP)는 **«묘사»**다 —")
    P("   슬롯 5 를 «그 검출기»끼리만 다투므로 **«다른» 유니버스**이고 **«합»과 «더하지» 않는다**(유형 67)")
    P("⛔ **승률 인용 «금지»** — 이 판의 자는 **«연환산 계좌 %p»** «하나»다")
    P("⛔ **«이겨도» «못» 쓰는 것**: 「70 이 낫다」가 나와도 그건 **「«문턱»을 바꾸라」**이지")
    P("   **「원전이 «옳다»」가 «아니다** — `205` 가 " + BQ + "trend_template.md" + BQ
      + " 의 «충실도»를 **«아직» «못» 쟀다**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 1. 자료 ─────────────────────────────────────────────────────
    P("# 1. **자료 — 관문**")
    P("")
    CA = Path(str(r91.OUT / "201d-arms.json"))

    def cnt(label, value, how):
        P("   **%s = %s**   ⟵  " % (label, value) + BQ + how + BQ)

    # ── 관문 0 — **«후보» 수준**에서 ① ⊂ Ⓡ 인가 (갈무리) ──────────────
    CC = Path(str(r91.OUT / "201d-cand.json"))
    if CC.exists():
        cd_ = json.loads(CC.read_text(encoding="utf-8"))
    else:
        def cand(sub):
            old_ = r91.SUB
            r91.SUB = sub
            try:
                (_a, _b, by2), _m, _ = r91.load_ladder(
                    YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
            finally:
                r91.SUB = old_
            return {(q["entry_date"], q["code"], q["pattern"]) for y in by2 for q in by2[y]}
        ca, cb = cand(CANON), cand(RS70)
        cd_ = {"a": len(ca), "b": len(cb), "a_only": len(ca - cb), "b_only": len(cb - ca)}
        CC.write_text(json.dumps(cd_), encoding="utf-8")
    P(F3)
    P("## ★ **관문 0 — «후보» 수준**(사다리 ② · 펀더 관문 «전» · 중복 제거 «전»)")
    P("")
    P("   **① 후보 = %s**   ⟵  " % format(cd_["a"], ",") + BQ + "len(cand(rs80))" + BQ)
    P("   **Ⓡ 후보 = %s**   ⟵  " % format(cd_["b"], ",") + BQ + "len(cand(rs70))" + BQ)
    P("   **★ ① «에만» 있는 «후보» = %s**   ⟵  " % format(cd_["a_only"], ",")
      + BQ + "len(ca - cb)" + BQ)
    P("   **★ Ⓡ «에만» 있는 «후보» = %s**   ⟵  " % format(cd_["b_only"], ",")
      + BQ + "len(cb - ca)" + BQ)
    P("")
    if cd_["a_only"] == 0:
        P("✅ **① ⊂ Ⓡ 이 «후보» 수준에서 «완벽»하다** — 문턱을 «내렸더니» 후보가 «늘기»만 했다")
    else:
        P("🚨 **① 에만 있는 «후보»가 %s 개** — 자료가 «다르다**" % format(cd_["a_only"], ","))
    P(F3)
    P("")
    if CA.exists():
        built = {k: [tuple(x) for x in v]
                 for k, v in json.loads(CA.read_text(encoding="utf-8")).items()}
        P(F3)
        P("   (♻️ 갈무리 201d-arms.json — 팔 %d)" % len(built))
        sub_ok = cd_.get("t_only")
        if sub_ok is not None:
            P("")
            P("   **★ ① «에만» 있는 «거래» = %s**   ⟵  " % format(sub_ok, ",")
              + BQ + "201d-cand.json:t_only" + BQ)
            P("")
            P("★★ **«후보»는 0 인데 «거래»는 %s 이다 — 「① ⊂ Ⓡ 인가」에 «자»가 «둘»이었다**(유형 67)"
              % format(sub_ok, ","))
            P("   ⇒ ✅ **차이는 «자료»가 «아니라» " + BQ + "open_until" + BQ + " «중복 제거»의 «연쇄»다**")
            P("     Ⓡ 에서 «더 이른» 진입이 «같은» 종목의 자리를 잡아 — ① 의 «나중» 진입이 **«밀렸다**")
            P("   ⇒ ★ **«오염»이 «아니라» «처치»의 «일부»다** — 문턱을 «내리면» «실제로» 그렇게 된다")
            P("   ⇒ ⛔ 그러나 **「RS 가 «높은» 종목이 «낫나」의 답이 «아니다**")
            P("     — 판정이 «재는» 것은 **「문턱을 «내린» «규칙» «전체»」**다(진입 «순서» 바뀜 «포함»)")
        P(F3)
    else:
        P(F3)
        P("경로 자리 — ① " + str(CANON))
        P("           Ⓡ " + str(RS70))
        P(F3, flush=True)
        p80, m80 = build_pairs(CANON)
        if p80 is None:
            P("🚨 멈춘다 — ① 경로 없음 %s" % m80)
            return 2
        p70, m70 = build_pairs(RS70)
        if p70 is None:
            P("🚨 멈춘다 — Ⓡ 경로 없음 %s" % m70)
            return 2

        # ── 관문: ① ⊂ Ⓡ 인가 (문턱을 «내렸으니» 후보는 «늘어야» 한다) ──
        k80 = {(t["entry_date"], p["code"], p["pattern"]) for t, p in p80}
        k70 = {(t["entry_date"], p["code"], p["pattern"]) for t, p in p70}
        only80 = len(k80 - k70)
        P(F3)
        cnt("① 거래(중복 제거 «후»)", format(len(p80), ","), "len(pairs_rs80)")
        cnt("Ⓡ 거래(중복 제거 «후»)", format(len(p70), ","), "len(pairs_rs70)")
        cnt("★ ① «에만» 있는 거래", format(only80, ","), "len(k80 - k70)")
        P("")
        cd_["t_only"] = only80
        CC.write_text(json.dumps(cd_), encoding="utf-8")
        P("★★ **«후보»는 0 인데 «거래»는 %s 이다 — 「① ⊂ Ⓡ 인가」에 «자»가 «둘»이었다**(유형 67)"
          % format(only80, ","))
        P("")
        P("   ⇒ ✅ **차이는 «자료»가 «아니라» " + BQ + "open_until" + BQ + " «중복 제거»의 «연쇄»다**")
        P("     Ⓡ 에서 «더 이른» 진입이 «같은» 종목의 자리를 잡아 —")
        P("     ① 에서 잡혔을 «나중» 진입이 **«밀렸다**")
        P("   ⇒ ★ **이건 «오염»이 «아니라» «처치»의 «일부»다** — 문턱을 «내리면» «실제로» 그렇게 된다")
        P("   ⇒ ⛔ 그러나 **「RS 가 «높은» 종목이 «낫나」의 답이 «아니다**")
        P("     — 판정이 «재는» 것은 **「문턱을 «내린» «규칙» «전체»」**다(진입 «순서» 바뀜 «포함»)")
        P(F3, flush=True)

        built = {"\u2460": [trades_of(t, p) for t, p in p80],
                 "\u211d": [trades_of(t, p) for t, p in p70]}
        for pat in ("VCP", "3C", "PP"):
            built["\u2460" + pat] = [trades_of(t, p) for t, p in p80 if p["pattern"] == pat]
            built["\u211d" + pat] = [trades_of(t, p) for t, p in p70 if p["pattern"] == pat]
        CA.write_text(json.dumps({k: [list(x) for x in v] for k, v in built.items()}),
                      encoding="utf-8")
        sub_ok = only80

    all_d = sorted({d for lst in built.values() for d, _h, _n in lst})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)
    idx_at = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            idx_at[k][pos[d]].append(j)

    P("")
    P(F3)
    cnt("날짜 자리 수", format(n_pos, ","), "len(sorted(set(entry_dates)))")
    for _k in ["\u2460", "\u211d", "\u2460VCP", "\u211dVCP",
               "\u24603C", "\u211d3C", "\u2460PP", "\u211dPP"]:
        cnt("  %-6s 거래 수" % _k, format(len(built[_k]), ","), "len(built[k])")
    P(F3)
    P("")
    P("---")
    P("")

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return boot_eq(bp, n_pos)

    JUDGE = [("\u211d\u2212\u2460", "\u211d", "\u2460")]
    DESC = [("VCP", "\u211dVCP", "\u2460VCP"),
            ("3C", "\u211d3C", "\u24603C"),
            ("PP", "\u211dPP", "\u2460PP")]
    ALLP = JUDGE + DESC
    o = {k: ann(obs(v)) for k, v in built.items()}
    obsd = {nm: o[a] - o[b] for nm, a, b in ALLP}

    P("# 2. **팔의 «절대» 값**(연환산 %p · 참고)")
    P("")
    P(F3)
    for k in ["\u2460", "\u211d"]:
        P("   %-4s **%+.3f%%p/해**" % (k, o[k]))
    P(F3)
    P("")
    P("---")
    P("")

    head_rows = wide_rows = None
    thr_head = 0.0
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        BMIN, BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = {nm: [] for nm, _a, _b in ALLP}
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
            for nm, a, b in ALLP:
                boots[nm].append(eqs[a] - eqs[b])
            if (bi + 1) % 200 == 0:
                P("  [블록 %d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)

        cen = {nm: [x - st.mean(boots[nm]) for x in boots[nm]] for nm, _a, _b in JUDGE}
        maxt = sorted(max(abs(cen[nm][i]) / max(st.stdev(cen[nm]), 1e-9)
                          for nm, _a, _b in JUDGE) for i in range(NBOOT))
        thr = maxt[int(NBOOT * 0.95)]

        P("")
        P("# %d. ★★ **«자료» 축 — 블록 %d~%d**%s"
          % (3 + bi_blk, bmn, bmx,
             "(`183`~`191` 과 «같은» 설정)" if (bmn, bmx) == (20, 40)
             else "(`dataaxis.py` 의 「가장 «넓은» 걸 머리로」)"))
        P("")
        P("🚨 **«단위»는 «연환산 %%p»** · Δ = **%.2f%%p** · MDE = **%.3f × SD**" % (DELTA, MDE_K))
        P("")
        P("| 짝 | **점추정** | **95% CI** | CI폭 | **MDE** | t | 최대통계 | **편향** | 판정칸 |")
        P("|---|---:|---:|---:|---:|---:|:--|---:|:--|")
        rows_all = []
        for nm, a, b in ALLP:
            v = sorted(boots[nm])
            lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
            sd = st.stdev(boots[nm])
            tt = abs(obsd[nm]) / max(sd, 1e-9)
            med = st.median(boots[nm])
            bias = med - obsd[nm]
            mde = MDE_K * sd
            judged = (nm, a, b) in JUDGE
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
            rows_all.append((nm, obsd[nm], lo, hi, tt, tt >= thr, hi - lo, bias,
                             abs(bias) / max(sd, 1e-9), cell, judged, mde))
            P("| %s**%s** | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | %.3f | %.2f | %s | %+.3f | %s |"
              % ("" if judged else "🔎묘사 ", nm, obsd[nm], lo, hi, hi - lo, mde, tt,
                 ("✅ **산다**" if tt >= thr else "🔴 **죽는다**") if judged else "—",
                 bias, cell))
        P("")
        P(F3)
        cnt("최대통계 95% 문턱(«판정» 짝만)", "%.3f" % thr,
            "sorted(max_a |centered| / SD)[int(NBOOT*0.95)]")
        jr = [r for r in rows_all if r[10]]
        cnt("최대통계를 «넘은» «판정» 짝", "%d / %d" % (sum(1 for r in jr if r[5]), len(jr)),
            "sum(1 for r in judge_rows if r[5])")
        P(F3)
        P("")
        for ln in gates.bias_note([(r[0], r[1], r[2], r[3], r[1] + r[7],
                                    (r[3] - r[2]) / 3.92, r[5]) for r in rows_all]):
            P(ln)
        P("")
        for ln in gates.shared_axis_note(
                NBOOT, ["같은 청산 규칙(+30/−10·절반+추격)", "같은 슬롯 수(5)",
                        "같은 검출기 «집합»", "같은 펀더 관문(103)", "같은 사다리 칸(②)"]):
            P(ln)
        P("")
        P(F3)
        P("⛔ **_gates.spread_note() 는 «안» 부른다** — 그건 «씨앗» 축 P95÷P05 를 먹는데")
        P("   이 기계엔 **«씨앗» 축이 «없다»**. **«없는» 자를 «부르지» 않는다**")
        P(F3)
        P("")
        if bi_blk == 0:
            head_rows, thr_head = rows_all, thr
        else:
            wide_rows = rows_all

    # ── 맺음 ────────────────────────────────────────────────────────
    P("")
    P("---")
    P("")
    P("# ⇒ **맺음**")
    P("")
    j0 = [r for r in head_rows if r[10]][0]
    j1 = [r for r in wide_rows if r[10]][0]
    P(F3)
    P("**Ⓡ − ①**  블록 20~40  **%+.3f%%p** [%+.3f, %+.3f]  칸 **%s**  (최대통계 %s)"
      % (j0[1], j0[2], j0[3], j0[9].replace("**", "").replace(" 🚨 «못 가린다»", ""),
         "넘음" if j0[5] else "«못» 넘음"))
    P("            블록 80~80  **%+.3f%%p** [%+.3f, %+.3f]  칸 **%s**  (최대통계 %s)"
      % (j1[1], j1[2], j1[3], j1[9].replace("**", "").replace(" 🚨 «못 가린다»", ""),
         "넘음" if j1[5] else "«못» 넘음"))
    P("")
    P("**MDE**(블록 20~40) = **%.3f%%p** · `188` 최소 **1.793%%p**" % j0[11])
    P(F3)
    P("")
    same = j0[9] == j1[9]
    P(F3)
    P("**두 블록의 판정칸이 %s**" % ("«같다»  ⇒ ✅ 블록 길이에 «안» 흔들린다" if same
                                     else "«다르다»  ⇒ 🚨 블록 길이가 «판정»을 «바꾼다» — «머리»는 «넓은» 쪽"))
    P(F3)
    P("")
    P("## 사전등록 «셋» 중 «어느» 것인가")
    P("")
    P(F3)
    cell0 = j0[9]
    if "**1**" in cell0:
        P("⇒ ① " + A_UP)
    elif "**2**" in cell0:
        P("⇒ ② " + A_DN)
    else:
        P("⇒ ③ " + A_NO)
    P(F3)
    P("")
    if sub_ok is not None:
        P(F3)
        P("**양성 대조**: «후보» 수준 ① «에만» = **0** ✅ · «거래» 수준 ① «에만» = **%s**"
          % format(sub_ok, ","))
        P("   ⇒ 뒤엣것은 " + BQ + "open_until" + BQ + " 연쇄이고 **«처치»의 «일부»**다")
        P(F3)
        P("")
    P("⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **「70 이 «원전»인가」는 «안» 쟀다** — `205` §6①: trend_template.md 의 «충실도» «미측정»")
    P("⛔ ② **RS 문턱 «둘»만 봤다**(80·70). **격자가 «아니다»** — 「어느 값이 «최선»인가」는 «못» 답한다")
    P("⛔ ③ **`criteria.py:29` 의 실전 관문은 «이 판이 «안» 만진다»** — 백테스트 유니버스만 바꿨다")
    P("⛔ ④ **승률·거래당은 «안» 적는다**(사전등록 ⑤)")
    P("⛔ ⑤ 🚨🚨 **이 판은 «설계상» Δ 를 «못» 가린다** — MDE **%.3f%%p** vs Δ **%.2f%%p** = **%.2f 배**"
      % (j0[11], DELTA, j0[11] / DELTA))
    P("     ⇒ ★★ **「«못» 가렸다」는 «자료»의 답이 «아니라» «자»의 답이다**")
    P("     ⇒ 「이길 수가 «없었던» 판」 — 유형 63(「질 수가 «없었던» 판」)의 **«거울»**")
    P("     ⇒ ✅ 그래도 **§B⑭ 는 «바뀐다** — 「«안» 봤다」 → 「봤는데 **«이 자»로는** «못» 가렸다」")
    P(F3)
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

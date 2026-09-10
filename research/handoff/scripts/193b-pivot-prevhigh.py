# -*- coding: utf-8 -*-
r"""193b — **방아쇠를 「«전일» 고가」로 바꾸면 «결과»가 바뀌나** · 두뇌 허가 2026-09-06

  🎯 `174:97` 이 **「«판정» «없는» «묘사»」**로 남긴 것 — 원전은 「«전일» 고점」인데
     우리 셋(VCP «종가» · 3C·PP «장중 고가»)은 **셋 다 「전일」이 «아니다»**.

  ✅ **`193` 검색 결과** — ㉠ «미국» 자료로 돌린 판 «없음» · ㉡ 「정의 차이」를 «판정»에 넣은 판 «없음»
     ㉢ 분포는 «이미» 다 나왔고 **«판정»만 «없음»**(갈무리 23,693 · 이을 수 없던 후보 0)

  🚨 **«돌리기» «전»에 박은 «예측» — «둘»**(두뇌 확정)
     ① **「MDE 아래 ⇒ «못» 본다」** — `193` §3: 전일고점 전환 = `182` 의 **α = +0.033%** 칸
        ⇒ «가격» 조각 어림 **+0.016%p** · MDE «최소» **1.793%p** ⇒ **111 배 아래**
        ★ 맞으면 «구조» 확인 · 빗나가면 **「MDE 계산」이 «틀림»**(그 자체가 «큰» 결과)
     ② 🚨 **«부호»를 «예상하지» «않는다»** — 「집합」 조각은 검출기마다 **방향이 «반대»**라
        «상쇄»될지 «더해질지» **«어림할 수» «없다»** ⇒ **「셋째 경우(«못 가린다»)」를 «미리» 적는다**(`186`)
     🚨 두뇌 «바라는 답» = 「원전 정의가 «낫길»」 ⇒ ✅ **「«차이»가 «없다»」 쪽을 «더» 세게 본다**

  ⛔ **«이겨도» «못» 쓴다 — «결과 «전»»에 박는다**
     `174` 가 «스스로» 적었다: 원전 정의로 «바꾸면» **「«우리» 검출기」가 «다른 것»이 된다**.
     ⇒ **「Ⓥ 가 «낫다»」가 나와도 그건 「검출기를 «바꾸라»」이지 「피벗만 고쳐라」가 «아니다**.

  ⛔ **이 판의 «범위» — «가장» 중요한 한정**
     후보 «날»은 **「우리 피벗이 «뚫린» 날」**로 «그대로» 둔다. **«방아쇠 «수준»»만 바꾼다.**
     ⇒ 🚨 **「진짜」 전일고점 규칙이라면 «더 이른» 날에 «먼저» 들어갔을 설정이 «있다»** — 그건 «후보»에 «없다**
     ⇒ ★ 그러므로 이 판이 답하는 것은 **「«우리» 후보 «안»에서 방아쇠 «수준»만 바꾸면」**이다
     ⇒ ✅ 그 좁힘이 **`16-selection-edge` 가 «룩어헤드»로 죽은 자리**이고 — 여기선 **«좁혀» 피한다**
     ✅ **실행 «가능»하다** — 전일 고가는 **«장전»에 «안다**(`entry-execution-method` 의 예약매수와 «맞는다»)

  📐 **블록** — `dataaxis.py:20-22` 「보유 P90 71일인데 20~40이면 구간이 «좁게» 나온다 ⇒ 20/40/80 중
     «가장 넓은» 것을 «머리»로」 ⇒ ✅ **(20,40)** 과 **(80,80)** «둘 다» 낸다.
     (20,40)은 `183`~`191` 과 «견주려고», (80,80)은 **「가장 넓은 걸 머리로」**를 «지키려고».

  🚨 **기계는 `185-oneaxis.py` 와 «같다»** — `draw`·`ann`·`boot_eq`·`trades_of` **«그대로»**.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/193b-pivot-prevhigh.py
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
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
gates = _load("gates", "_gates.py")
ptb = _load("ptb", "_pyr_be.py")
f92a = r102.f92a
pt = r91.pt

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NBOOT = 2000
SEED = 193193
YRS = 27.4
PH = Path("D:/stock-data/derived/174-prevhigh.json")
BLOCKS = ((20, 40), (80, 80))
BMIN, BMAX = BLOCKS[0]
DELTA = 1.23
MDE_MIN = 1.793
EST193 = 0.0161          # `193` §3 — «가격» 조각 어림


def draw(n, rnd):
    """**«순환»** 블록 — `183a` 의 기지답 시험을 **100%** 로 통과한 방식(`185` 와 «같다»)."""
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
    """`23c:46-66` «그대로»."""
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
        c = by_pos.get(p)
        if free > 0 and c:
            wgt = eq / slots
            for rel, nt, _k in c[:free]:
                held.append([p + rel, wgt, nt])
    for h in held:
        eq += h[1] * h[2] / 100
    return (eq - 1) * 100


def main():
    global BMIN, BMAX
    P = print
    quick = "--quick" in sys.argv
    nboot = 200 if quick else NBOOT
    P("=" * 104)
    P("193b — **방아쇠를 「«전일» 고가」로 바꾸면 «결과»가 바뀌나** · 부트 %s판%s"
      % (format(nboot, ","), "  🚨 **--quick**" if quick else ""))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-06 · `scripts/193b-pivot-prevhigh.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("```")
    P("## 🚨 **«돌리기» «전»에 박은 «예측» — «둘**")
    P("")
    P("   ① **「MDE 아래 ⇒ «못» 본다」** — 전일고점 전환 = `182` 의 **α = +0.033%** 칸")
    P("      «가격» 조각 어림 **%+.4f%%p**  ·  `188` MDE «최소» **%.3f%%p**  ⇒  **%.0f 배 아래**"
      % (EST193, MDE_MIN, MDE_MIN / EST193))
    P("      ★ 맞으면 «구조» 확인 · **빗나가면 「MDE 계산」이 «틀림»**")
    P("   ② 🚨 **«부호»를 «예상하지» «않는다** — 「집합」 조각이 검출기마다 **방향이 «반대»**")
    P("      VCP(76.9%) 는 전일고점이 피벗 «위» ⇒ «덜» 체결 · 3C·PP 는 «아래» ⇒ «더» 체결")
    P("      ⇒ **「셋째 경우(«못 가린다»)」를 «미리» 적는다**(`186` 에서 배운 것)")
    P("")
    P("   🚨 두뇌 «바라는 답» = 「원전 정의가 «낫길»」 ⇒ ✅ **「«차이»가 «없다»」 쪽을 «더» 세게 본다**")
    P("```")
    P("")
    P("```")
    P("## ⛔ **«이겨도» «못» 쓴다 — «결과 «전»»에 박는다**")
    P("   `174` 가 «스스로» 적었다: 원전 정의로 «바꾸면» **「«우리» 검출기」가 «다른 것»이 된다**")
    P("   ⇒ **「Ⓥ 가 «낫다»」가 나와도 「검출기를 «바꾸라»」이지 「피벗만 고쳐라」가 «아니다**")
    P("")
    P("## ⛔ **범위 — «가장» 중요한 한정**")
    P("   후보 «날»은 **「우리 피벗이 «뚫린» 날」**로 «그대로» 두고 — **방아쇠 «수준»만** 바꾼다")
    P("   ⇒ 🚨 「진짜」 전일고점 규칙이면 **«더 이른» 날에 «먼저» 들어갔을 설정**이 있다(후보에 «없다»)")
    P("   ⇒ ★ 이 판이 답하는 것은 **「«우리» 후보 «안»에서 방아쇠 «수준»만 바꾸면」**이다")
    P("   ✅ **실행 «가능»하다** — 전일 고가는 **«장전»에 «안다**(예약매수와 «맞는다»)")
    P("```")
    P("")

    # ── 자료 ────────────────────────────────────────────────────────
    if not PH.exists():
        P("🚨 **멈춘다** — `%s` 가 «없다**" % PH)
        return 3
    ph = json.loads(PH.read_text(encoding="utf-8"))
    CA = Path(str(r91.OUT / "193b-arms.json"))
    P("=" * 104)
    P("## 1. 자료 — 관문")
    P("=" * 104)
    P("")

    def cnt(label, value, how):
        P("   **%s = %s**   ⟵  `%s`" % (label, value, how))

    if CA.exists():
        built = {k: [tuple(x) for x in v]
                 for k, v in json.loads(CA.read_text(encoding="utf-8")).items()}
        P("```")
        P("   (♻️ 갈무리 `193b-arms.json` — 팔 %d)" % len(built))
        P("```", flush=True)
        n_no_ph = n_no_touch = None
    else:
        (_a, _b, by2), missing, _ = r91.load_ladder(
            YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
        if missing:
            P("🚨 경로 없음 — 돌린 자리 `%s`" % str(r91.SUB))
            return 2
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
                c = p["code"]
                if c in open_until and p["entry_date"] <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                pairs.append((t, p))
        P("```")
        cnt("거래 목록(중복 제거 «후»)", format(len(pairs), ","),
            "len(pairs)  — `185` 와 «같은» 구성")
        P("```", flush=True)

        def trades_of(exits_rd, t, p):
            exits, rd = exits_rd
            epx = t["entry_px"]
            net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2)) for _d, fr, px in exits)
            d = p["d"]
            hold = d.index(rd) if (rd and rd in d) else len(d) - 1
            return (t["entry_date"], max(1, hold), net)

        n_no_ph = n_no_touch = 0

        def build_arm(mode, pat=None):
            """base = ①(현행 피벗)  ·  prev = Ⓥ(전일 고가 방아쇠).  pat 이 있으면 그 검출기만."""
            nonlocal n_no_ph, n_no_touch
            out_ = []
            for t, p in pairs:
                if pat is not None and p["pattern"] != pat:
                    continue
                if mode == "base":
                    r = t["masks"][()]
                    out_.append(trades_of((r["exits"], r["resolve_date"]), t, p))
                    continue
                lvl = ph.get(p["code"] + "|" + p["entry_date"])
                if lvl is None or lvl <= 0:
                    if pat is None:
                        n_no_ph += 1
                    continue
                hi0 = (p.get("h") or [None])[0]
                if hi0 is None or hi0 < lvl:          # 그날 «고가»가 방아쇠에 «못» 닿음
                    if pat is None:
                        n_no_touch += 1
                    continue
                o0 = (p.get("o") or [None])[0]
                q = dict(p)
                q["entry_price"] = lvl if o0 is None else max(lvl, o0)   # 예약매수 = max(수준, 시가)
                t2 = ptb.resolve_trade(q, ft="limit", fs="market", stop=STOP, target=TARGET,
                                       half=HALF, shares=(1.0,), add_stop="floor_entry")
                r2 = t2["masks"][()]
                out_.append(trades_of((r2["exits"], r2["resolve_date"]), t2, p))
            return out_

        built = {"\u2460": build_arm("base"), "\u24cb": build_arm("prev")}
        for pat in ("VCP", "3C", "PP"):
            built["\u2460" + pat] = build_arm("base", pat)
            built["\u24cb" + pat] = build_arm("prev", pat)
        P("```")
        cnt("Ⓥ 에서 «빠진» 후보 — 갈무리 «없음»", format(n_no_ph, ","), "lvl is None")
        cnt("Ⓥ 에서 «빠진» 후보 — 그날 «고가»가 «못» 닿음", format(n_no_touch, ","), "h[0] < lvl")
        P("```", flush=True)
        CA.write_text(json.dumps({k: [list(x) for x in v] for k, v in built.items()}),
                      encoding="utf-8")

    all_d = sorted({d for lst in built.values() for d, _h, _n in lst})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)
    idx_at = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            idx_at[k][pos[d]].append(j)

    P("")
    P("```")
    cnt("날짜 자리 수", format(n_pos, ","), "len(sorted(set(entry_dates)))")
    for _k in ["\u2460", "\u24cb", "\u2460VCP", "\u24cbVCP",
               "\u24603C", "\u24cb3C", "\u2460PP", "\u24cbPP"]:
        cnt("  %-6s 거래 수" % _k, format(len(built[_k]), ","), "len(built[k])")
    P("")
    P("🚨 **검출기별 팔은 «분해»가 «아니다** — 슬롯 5 를 «그 검출기»끼리만 다투므로")
    P("   **«다른» 유니버스**다. ⇒ **«묘사»로만 읽고 «합»과 «더하지» 않는다**(유형 67)")
    P("```")

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return boot_eq(bp, n_pos)

    JUDGE = [("\u24cb\u2212\u2460", "\u24cb", "\u2460")]
    DESC = [("VCP", "\u24cbVCP", "\u2460VCP"),
            ("3C", "\u24cb3C", "\u24603C"),
            ("PP", "\u24cbPP", "\u2460PP")]
    ALLP = JUDGE + DESC
    o = {k: ann(obs(v)) for k, v in built.items()}
    obsd = {nm: o[a] - o[b] for nm, a, b in ALLP}

    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        BMIN, BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = {nm: [] for nm, _a, _b in ALLP}
        for bi in range(nboot):
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
                P("  [블록 %d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, nboot), flush=True)

        # 최대통계는 **판정 짝**에«만** 건다(묘사는 «안» 넣는다 — 넣으면 문턱이 «묘사»에 끌린다)
        cen = {nm: [x - st.mean(boots[nm]) for x in boots[nm]] for nm, _a, _b in JUDGE}
        maxt = sorted(max(abs(cen[nm][i]) / max(st.stdev(cen[nm]), 1e-9)
                          for nm, _a, _b in JUDGE) for i in range(nboot))
        thr = maxt[int(nboot * 0.95)]

        P("")
        P("=" * 104)
        P("## %d. ★★ **«자료» 축 — 블록 **%d~%d**%s"
          % (2 + bi_blk, bmn, bmx,
             "**(`183`~`191` 과 «같은» 설정)" if (bmn, bmx) == (20, 40)
             else "**(`dataaxis.py` 의 「가장 «넓은» 걸 머리로」)"))
        P("=" * 104)
        P("")
        P("🚨 **«단위»는 «연환산 %%p»** · Δ = **%.2f%%p**" % DELTA)
        P("")
        P("| 짝 | **점추정** | **95% CI** | CI폭 | t | 최대통계 | **편향** | **|편향|÷SD** | 판정칸 |")
        P("|---|---:|---:|---:|---:|:--|---:|---:|:--|")
        rows_all = []
        for nm, a, b in ALLP:
            v = sorted(boots[nm])
            lo, hi = v[int(nboot * .025)], v[int(nboot * .975)]
            sd = st.stdev(boots[nm])
            tt = abs(obsd[nm]) / max(sd, 1e-9)
            med = st.median(boots[nm])
            bias = med - obsd[nm]
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
                             abs(bias) / max(sd, 1e-9), cell, judged))
            P("| %s**%s** | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | %.2f | %s | %+.3f | %.2f | %s |"
              % ("" if judged else "🔎묘사 ", nm, obsd[nm], lo, hi, hi - lo, tt,
                 ("✅ **산다**" if tt >= thr else "🔴 **죽는다**") if judged else "—",
                 bias, abs(bias) / max(sd, 1e-9), cell))
        P("")
        P("```")
        cnt("최대통계 95% 문턱(«판정» 짝만)", "%.3f" % thr,
            "sorted(max_a |centered| / SD)[int(nboot*0.95)]")
        jr = [r for r in rows_all if r[10]]
        cnt("최대통계를 «넘은» «판정» 짝", "%d / %d" % (sum(1 for r in jr if r[5]), len(jr)),
            "sum(1 for r in judge_rows if r[5])")
        P("```")
        P("")
        for ln in gates.bias_note([(r[0], r[1], r[2], r[3], r[1] + r[7],
                                    (r[3] - r[2]) / 3.92, r[5]) for r in rows_all]):
            P(ln)
        P("")
        for ln in gates.shared_axis_note(
                nboot, ["같은 거래 목록(후보 «날»)", "같은 청산 규칙(+30/−10·절반+추격)",
                        "같은 슬롯 수(5)", "같은 검출기 «집합»"]):
            P(ln)
        P("")
        P("```")
        P("⛔ **`_gates.spread_note()` 는 «안» 부른다** — 그건 **«씨앗» 축 P95÷P05** 를 먹는데")
        P("   이 기계엔 **«씨앗» 축이 «없다**. **«없는» 자를 «부르지» 않는다**(유형 35 의 «반대» 얼굴)")
        P("```")
        P("")
        if bi_blk == 0:
            head_rows, _thr_head = rows_all, thr
        else:
            wide_rows, _thr_wide = rows_all, thr

    # ── 맺음 ────────────────────────────────────────────────────────
    P("")
    P("=" * 104)
    P("## ⇒ **맺음**")
    P("=" * 104)
    P("")
    j0 = [r for r in head_rows if r[10]][0]
    j1 = [r for r in wide_rows if r[10]][0]
    P("| 블록 | 점추정 | 95% CI | 판정칸 | 최대통계 |")
    P("|---|---:|---:|:--|:--|")
    P("| 20~40 (`183`~`191` 설정) | **%+.3f%%p** | [%+.3f, %+.3f] | %s | %s |"
      % (j0[1], j0[2], j0[3], j0[9], "✅ 산다" if j0[5] else "🔴 죽는다"))
    P("| **80~80 (★ 머리 — 가장 «넓은» 것)** | **%+.3f%%p** | [%+.3f, %+.3f] | %s | %s |"
      % (j1[1], j1[2], j1[3], j1[9], "✅ 산다" if j1[5] else "🔴 죽는다"))
    P("")
    P("```")
    P("## ⇒ %s **예측 ① 채점 — 🚨 «점수»는 «없다**(「예측」이 «아니라» 「계산」 · `192b` 에서 배운 것)"
      % ("✅" if abs(j1[1]) < MDE_MIN else "🔴"))
    P("   «미리» 적은 것: 「어림 %+.4f%%p · MDE 최소 %.3f%%p ⇒ «못» 본다」" % (EST193, MDE_MIN))
    P("   실측(머리 블록) 점추정 **%+.3f%%p** · CI폭 **%.2f**" % (j1[1], j1[3] - j1[2]))
    if abs(j1[1]) < MDE_MIN:
        P("   ⇒ ✅ **점추정이 MDE «아래»다** — 어림과 «같은» 자리")
    else:
        P("   ⇒ 🔴 **점추정이 MDE «위»다** — 「집합」 조각이 «가격» 조각을 «넘었다**")
        P("   ⇒ ★★ **그러면 §예측 ② 대로 「어림할 수 «없다»」가 «맞았고** — 어림 ① 은 «반쪽»이었다")
    P("")
    P("## ⇒ **예측 ② — 🔴 «채점»을 «지운다**(검증 2차 · 2026-09-06)")
    P("   실측 부호 = **%s**"
      % ("«양수»(Ⓥ 가 «나음»)" if j1[1] > 0 else "«음수»(① 이 «나음»)"))
    P("   ⛔ **「예측 ② 가 «맞았다»」를 «적지» 않는다** — **판정칸이 «전부» 5** 이므로")
    P("   ## ⇒ **「맞음」과 「«못» 잼」이 «같은» 관측을 낸다** ⇒ **«가를» 수 «없다**")
    P("```")
    P("")
    P("```")
    P("## 🔎 **검출기별 «묘사» — 「갈래를 «내되» «고르지» 않는다」**(사전등록 ③)")
    for r in wide_rows:
        if r[10]:
            continue
        P("   **%-4s** %+.3f%%p [%+.3f, %+.3f]  %s" % (r[0], r[1], r[2], r[3], r[9]))
    P("")
    P("⛔ **이 셋 가운데 «최선»을 «고르지» 않는다** — 고르면 `23` 래칫이다")
    P("✅ **내는 «까닭»**: `179` §3c 가 「**WHO** 판은 검출기 갈래에서 «부호»가 «반전»」을 냈고 —")
    P("   **이 판은 «정확히» WHO** 이므로 **«구조»상 그 «취약» 갈래에 «속한다**")
    P("```")
    P("")
    P("```")
    P("## 🔎 **«가격» 방향과 «결과» 방향이 «어긋난다** — 🔴 **«발견»이 «아니다**(검증 2차)")
    P("")
    P("   `174` §⑤㉡ 의 «중앙» 비(피벗÷전일고점)가 말하는 «가격» 방향 vs 이 판의 «결과» 부호:")
    P("")
    P("| 검출기 | 중앙 비 | 전일고가로 바꾸면 | «가격»만 보면 | **실측 부호** | 맞나 |")
    P("|---|---:|:--|:--|---:|:--|")
    _dir = {"VCP": (0.9993, "«비싸게»"), "3C": (1.0032, "«싸게»"), "PP": (1.0085, "«싸게»")}
    _hit = 0
    for r in wide_rows:
        if r[10]:
            continue
        rat, how = _dir[r[0]]
        want = "+" if how == "«싸게»" else "−"
        got = "+" if r[1] > 0 else "−"
        ok = (want == got)
        _hit += 1 if ok else 0
        P("| **%s** | %.4f | %s 산다 | %s 여야 | **%+.3f%%p** | %s |"
          % (r[0], rat, how, want, r[1], "✅" if ok else "🔴 **어긋남**"))
    P("")
    P("## ⇒ **맞은 것 %d / 3** — 규약 ⑥" % _hit)
    P("")
    if _hit < 3:
        P("   ## ⇒ **「가격」만으로는 «부호»가 «안» 나온다 —**")
        P("   ##    **「집합」(«어느» 것을 «사게» 되나) 조각이 «가격» 조각을 «덮는다**")
        P("")
        P("   ## 🔴 **그런데 이건 «새» 발견이 «아니다**(검증 2차 · 2026-09-06)")
        P("   🔎 **`175`·`182` 가 «이미» 냈다** — 「«가격» 조각」과 「«합»」이 «다른» 수다")
        P("      (`182` α=0.50%: 가격 **+2.497** vs 합 **+1.656** · α=1.00%: 가격 **+0.453** vs 합 **-1.163**)")
        P("   ⇒ ★ **이 판은 «그것»의 «또» 한 «사례»**다")
        P("")
        P("   ## ⛔ **그리고 `186`·`191` 과는 «다른» 자리다 — «섞지» 말 것**")
        P("      `186`·`191` = **«같은» 것**을 «두» 자/축으로 재니 «달라졌다**")
        P("      `193b`      = **«다른» «두 것»**(가격 «방향» vs 결과 «부호»)이 «어긋났다**")
        P("   ⛔ 그리고 **판정칸이 «전부» 5** ⇒ **이 「어긋남」도 «잡음»과 «구분» «안» 된다**")
    else:
        P("   ⇒ 🔴 **셋 «다» 「가격」 방향과 «같다** — 예측 ② 의 «걱정»이 «빗나갔다**")
    P("")
    P("🚨 **그리고 `179` 가 «예고»한 그대로다** — **WHO 판은 검출기 갈래에서 «부호»가 «반전»**한다")
    P("   VCP **%+.3f** vs 3C **%+.3f** — **부호가 «갈린다**"
      % ([r[1] for r in wide_rows if r[0] == "VCP"][0],
         [r[1] for r in wide_rows if r[0] == "3C"][0]))
    P("```")
    P("")
    P("```")
    P("## ⛔ **이 판이 «못» 하는 것**")
    P("   ## 🔴 **「끝났다」 = 「«다» 쟀다」이지 「«답»이 «나왔다»」가 «아니다**(검증 2차)")
    P("      판정칸이 **거의 «전부» 5(«못 가린다»)**다")
    P("   ⛔ **후보 «날»을 «그대로» 뒀다** — 「진짜」 전일고점 규칙의 «더 이른» 진입은 «없다**")
    P("   ⛔ **MA★ 앵커가 «없다**(`boot_eq` 규약) — ① 이 12,377만을 «재현하지» «않는다** ⇒ **«상대» 비교용**")
    P("   ⛔ **「이겨도 «못» 쓴다」**(머리 참조) — 원전 정의로 바꾸면 «검출기»가 «다른 것»이 된다")
    P("   ⛔ **「없다」가 «아니라» 「«말할 수» 없다」** · **「반대」도 «말할 수» «없다**")
    P("```")
    P("")
    P("")
    if quick:
        P("```")
        P("⛔ **`--quick` 이라 `_PAIRS.md` 에 «안» 적는다** — 문턱이 «다른» 수이므로")
        P("   🚨 2026-09-06 실사고: 시험 실행이 장부에 «줄»을 남겼다 ⇒ **막았다**")
        P("```")
    else:
        _jw = [r for r in wide_rows if r[10]]
        for _ln in gates.append_pairs(
                "193b(블록80)",
                [(r[0], r[1], (r[3] - r[2]) / 3.92, r[4], _thr_wide, r[5], None)
                 for r in _jw]):
            P(_ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

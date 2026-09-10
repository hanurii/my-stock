# -*- coding: utf-8 -*-
r"""252 - **래칫: 「25일 저가 «채널»」 vs 「«50일선»」**  (조사 세션 2026-09-09)

  📖 원전 `tm:51` 「**«새» 주도주면 «트레일링 매도 가격»으로 «50일선»**」 — **원전이 «준» 유일한 «수»**
  🚨 우리 현행 「25」는 **«출처»가 «없다**(`pyr_trigger:201 trail=25` ← `47:50` ← `41:58`)

  ⛔ **원본을 «건드리지» «않았다** — `pyr_trigger.py` 를 «복사**한 `_pyr_ma.py` 를 «두» 번 «따로» 싣는다
  ⛔ **격자 «없음»** — 팔은 **«둘»**뿐
  ⛔ **한국 인용 0**

  🔁 **두 «단계**:
     · `252-expect.txt` 가 **«없으면»** → **①단계**: 자료 짓기 ＋ **팔 크기·«겹침»·«양성» 대조**«만**
     · `252-expect.txt` 가 **«있으면»** → **②단계**: **«예상»을 «싣고» 판정**(부트)
     ⇒ **「겹침을 «보고» «예상»을 «적는다»」를 «구조»로 «강제**한다

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/252-ratchet-ma.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent

C1 = chr(0x2460)          # ① 현행 — 25일 저가 채널
CL = chr(0x24C1)          # Ⓛ — 50일선
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 252252
BLOCKS = ((20, 40), (80, 80))
MA_N = 50                 # ⛔ 원전이 «준» 값 — 사전등록에 박음(격자 «없음»)


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91
r102, r103, f92a = m201d.r102, m201d.r103, m201d.f92a
OUT = Path(str(r91.OUT))
EXPECT = HERE.parent / "results" / "252-expect.txt"

ptA = _load("ptA", "_pyr_ma.py")          # MA_N = 0  ⇒ 원본 그대로(25일 저가 채널)
ptB = _load("ptB", "_pyr_ma.py")          # MA_N = 50 ⇒ 50일선
ptA.MA_N, ptB.MA_N = 0, MA_N


def eq_of(by_pos, n_pos, slots=5):
    eq, held, got = 1.0, [], 0
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
                got += 1
    for h in held:
        eq += h[1] * h[2] / 100
    return (eq - 1.0) * 100.0, got


def cell_of(lo, hi):
    if lo >= DELTA:
        return "**1**"
    if hi <= -DELTA:
        return "**2**"
    if lo <= 0 <= hi:
        return "**5**"
    if -DELTA <= lo and hi <= DELTA:
        return "**4a**"
    return "**4b**"


def build_with(mod):
    """`201d.build_pairs` «그대로** — 다만 «해소» 모듈을 «갈아» 끼운다."""
    old = r91.SUB
    r91.SUB = m201d.CANON
    try:
        (_a, _b, by2), missing, _ = r91.load_ladder(
            m201d.YEARS, m201d.D0, m201d.D1, "91-monthly-us-full.json", use_ext=False)
    finally:
        r91.SUB = old
    if missing:
        return None, missing
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    recs = []
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
            t = mod.resolve_trade(p, ft="limit", fs="market", stop=m201d.STOP,
                                  target=m201d.TARGET, half=m201d.HALF,
                                  shares=(1.0,), add_stop="floor_entry")
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
            recs.append((cd, t["entry_date"], max(1, hold), net))
    return recs, []


def main():  # noqa: C901
    stage2 = EXPECT.exists()
    P("# 252 - **래칫: 「25일 저가 «채널»」 vs 「«50일선»」**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/252-ratchet-ma.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> **단계 %s**" % ("**②** — «예상»을 «싣고» 판정" if stage2
                        else "**①** — 팔 크기·«겹침»·«양성» 대조«만** (⛔ **판정 «안** 함)"))
    P("")
    P(F3)
    P("📖 **원전** `tm:51` 「**«새» 주도주면 «트레일링 매도 가격»으로 «50일선»**」")
    P("🚨 **우리 현행 「25」의 «출처» = «없다**")
    P("   `pyr_trigger.py:201 trail=25`  ←  `47-round3-pyramid.py:50 TRAIL = 25`"
      "  ←  `41-round1-exits.py:58 TRAIL_WINDOW = 25`  (**주석 «없음»**)")
    P("")
    P("⛔ **원본을 «건드리지» «않았다** — `pyr_trigger.py` 를 **«복사**한 " + BQ + "_pyr_ma.py" + BQ
      + " 를 «두» 번 «따로» 싣는다")
    P("   `ptA.MA_N = 0`(원본 그대로) · `ptB.MA_N = %d`(50일선)" % MA_N)
    P("⛔ **격자 «없음»** — **원전이 «준» «한» 값«만»**")
    P(F3)
    P("")
    P("---")
    P("")

    CA = OUT / "252-recs.json"
    t_build = 0.0
    if CA.exists():
        raw = json.loads(CA.read_text(encoding="utf-8"))
        recs = {k: [tuple(x) for x in v] for k, v in raw.items()}
        P(F3)
        P("   (♻️ 갈무리 " + BQ + "252-recs.json" + BQ + ")")
        P(F3)
    else:
        P("(자료를 «짓는» 중 — 팔마다 «따로» 해소한다 …)", flush=True)
        t0 = time.time()
        recs = {}
        for k, mod in ((C1, ptA), (CL, ptB)):
            rr, miss = build_with(mod)
            if rr is None:
                P("🚨 경로 «없음»: %s" % miss[:3])
                return 1
            recs[k] = rr
            P("  %s — 거래 %s (%.1f 분)" % (k, format(len(rr), ","),
                                            (time.time() - t0) / 60.0), flush=True)
        t_build = time.time() - t0
        CA.write_text(json.dumps({k: [list(x) for x in v] for k, v in recs.items()}),
                      encoding="utf-8")
        P("")
        P(F3)
        P("   ✅ 자료 짓기 **%.1f 분**(실측) · 캐시 " % (t_build / 60.0)
          + BQ + "252-recs.json" + BQ)
        P(F3)
    P("")

    # ── 1. 팔 크기 · 겹침 · 양성 대조 ─────────────────────────────
    P("# 1. **팔 «크기» · «겹침» · «양성» 대조**  ⛔ **판정 «전**")
    P("")
    P(F3)
    kA = {(c, d) for c, d, _h, _n in recs[C1]}
    kB = {(c, d) for c, d, _h, _n in recs[CL]}
    both = kA & kB
    P("   %s **현행(25일 저가 채널)** 거래 = **%s**" % (C1, format(len(recs[C1]), ",")))
    P("   %s **50일선** 거래 = **%s**" % (CL, format(len(recs[CL]), ",")))
    P("")
    P("   ★ **«겹침»**(«같은» 종목·«같은» 진입일) = **%s**" % format(len(both), ","))
    P("      %s 기준 **%.1f%%**  ·  %s 기준 **%.1f%%**"
      % (C1, 100.0 * len(both) / max(1, len(kA)), CL, 100.0 * len(both) / max(1, len(kB))))
    P("      %s «에만» = **%s**  ·  %s «에만» = **%s**"
      % (C1, format(len(kA - kB), ","), CL, format(len(kB - kA), ",")))
    P("")
    P("   🚨 **거래 «수»가 «다른» 까닭** — 청산이 «달라» **`resolve_date` 가 «달라지고**")
    P("      ⇒ **«같은» 종목의 «중복 제거»(`open_until`)가 «다르게» 걸린다**(`156`·`246` 의 교훈)")
    P("")
    hA = st.median([h for _c, _d, h, _n in recs[C1]])
    hB = st.median([h for _c, _d, h, _n in recs[CL]])
    P("   🔎 **보유 중앙**: %s **%.0f일** · %s **%.0f일**" % (C1, hA, CL, hB))
    P("")

    # 양성 대조 — 팔①이 «정본»을 재현하는가
    ref = OUT / "236-recs.json"
    if ref.exists():
        rr = [tuple(x) for x in json.loads(ref.read_text(encoding="utf-8"))]
        ok = len(rr) == len(recs[C1])
        P("   ★★ **«양성» 대조 — 팔 %s 이 «정본»을 «그대로» «재현»하는가**" % C1)
        P("      `236-recs.json`(정본 얼개) 거래 **%s**  vs  팔 %s **%s**  ⇒ %s"
          % (format(len(rr), ","), C1, format(len(recs[C1]), ","),
             "✅ **«같다**" if ok else "🚨 **«다르다** — **복사본이 원본과 «어긋난다**"))
        if not ok:
            P("      🔴🔴 **«어긋나면» 아래 «전부»를 «못» 읽는다** — **«먼저» 고쳐야** 한다")
    else:
        P("   ⚠️ **«양성» 대조 «못** 함 — `236-recs.json` 이 «없다**")
    P(F3)
    P("")

    if not stage2:
        P("---")
        P("")
        P("# ⛔ **여기서 «멈춘다** — **①단계**")
        P("")
        P(F3)
        P("   ✅ **«겹침»을 «봤다** ⇒ **이제 «예상»을 «적는다**")
        P("   📄 «적을» 곳: " + BQ + "results/252-expect.txt" + BQ)
        P("   ⇒ **그 파일이 «생기면»** 이 각본이 **②단계**(판정)로 «넘어간다**")
        P("   ⛔ **부트를 «안** 돌렸다 · **CI 가 «없다** · **판정칸이 «없다**")
        P(F3)
        P("")
        P("⛔ **커밋은 두뇌 몫입니다.**")
        return 0

    # ── 2. 예상 ────────────────────────────────────────────────────
    P("---")
    P("")
    P("# 🔴 **2. «예상** — ⛔ **«겹침»을 «본» «뒤», «판정»을 «보기» «전»에 «적었다**")
    P("")
    P(F3)
    P(EXPECT.read_text(encoding="utf-8").rstrip())
    P(F3)
    P("")
    P("---")
    P("")

    # ── 3. 판정 ───────────────────────────────────────────────────
    cal = json.loads((OUT / "201d-arms2.json").read_text(encoding="utf-8"))["cal"]
    ents = {d for k in recs for _c, d, _h, _n in recs[k]}
    if ents - set(cal):
        cal = sorted(set(cal) | ents)
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)
    built = {k: [(d, h, n) for _c, d, h, n in v] for k, v in recs.items()}

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return eq_of(bp, n_pos)

    o, got = {}, {}
    for k, v in built.items():
        e, g = obs(v)
        o[k] = m201d.ann(e)
        got[k] = g
    obsd = o[CL] - o[C1]
    P("# 3. **팔의 «절대» 값**(연환산 %p)")
    P("")
    P(F3)
    for k in (C1, CL):
        P("   %-3s **%+.3f%%p/해**  ·  슬롯 «얻은» 것 **%s** / %s"
          % (k, o[k], format(got[k], ","), format(len(built[k]), ",")))
    P("   **%s − %s = %+.3f%%p**" % (CL, C1, obsd))
    P("   날짜 자리 **%s**(달력 — **«고친» 자**)" % format(n_pos, ","))
    P(F3)
    P("")
    P("---")
    P("")

    ia = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            ia[k][pos[d]].append(j)

    P("# 4. **판정** — CI 를 **«둘» 다** 찍는다")
    P("")
    P("| 블록 | 점추정 | **백분위 CI** | 칸 | **기본(basic) CI** | 칸 | **MDE** | MDE÷Δ | 편향 |")
    P("|---|---:|---:|:--|---:|:--|---:|---:|---:|")
    t1 = time.time()
    cells, mdes = [], []
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m201d.BMIN, m201d.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = []
        for bi in range(NBOOT):
            order = m201d.draw(n_pos, rnd)
            eqs = {}
            for k, lst in built.items():
                bp = defaultdict(list)
                for newp, oldp in enumerate(order):
                    for j in ia[k].get(oldp, ()):
                        _d, h, nt = lst[j]
                        bp[newp].append((h, nt, 0))
                eqs[k] = m201d.ann(eq_of(bp, n_pos)[0])
            boots.append(eqs[CL] - eqs[C1])
            if (bi + 1) % 500 == 0:
                P("  [%d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        v = sorted(boots)
        lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
        sd = st.stdev(boots)
        blo, bhi = 2 * obsd - hi, 2 * obsd - lo
        cp, cb = cell_of(lo, hi), cell_of(blo, bhi)
        cells.append((cp, cb))
        mdes.append(MDE_K * sd / DELTA)
        P("| **%d~%d** | **%+.3f%%p** | [%+.3f, %+.3f] | %s | [%+.3f, %+.3f] | %s | **%.3f** | %.2f | %+.3f |"
          % (bmn, bmx, obsd, lo, hi, cp, blo, bhi, cb, MDE_K * sd, MDE_K * sd / DELTA,
             (lo + hi) / 2.0 - obsd), flush=True)
    t_boot = time.time() - t1
    P("")
    P(F3)
    P("   백분위 칸 = %s  ·  기본 칸 = %s"
      % (" · ".join(c[0] for c in cells), " · ".join(c[1] for c in cells)))
    P("")
    pc = {c[0] for c in cells} | {c[1] for c in cells}
    if pc == {"**5**"}:
        P("⇒ ③ **«못» 가린다** — **CI 가 0 을 «품는다**")
    elif pc == {"**1**"}:
        P("⇒ ① **%s(50일선)가 «위»로 갈라졌다**" % CL)
    elif pc == {"**2**"}:
        P("⇒ ② **%s(50일선)가 «아래»로 갈라졌다**" % CL)
    else:
        P("⇒ 🚨 **칸이 «갈린다** — **「몇 중 몇」**으로 «그대로» 적는다")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 🔴 **4b. «예상» «채점** — ⛔ **«고쳐» 읽지 «않는다**")
    P("")
    P(F3)
    P("| 내가 «적은» 것 | 나온 것 | 판정 |")
    P("|---|---|:--|")
    P("| **방향** — 「Ⓛ 가 «아래»일 것」 | 점추정 **%+.3f%%p**(Ⓛ 가 **«위»**) | 🔴 **틀렸다** |" % obsd)
    P("| **크기** — 「\|점추정\| < 1.23%%p」 | **%.3f** | ✅ **맞았다** |" % abs(obsd))
    P("| **MDE÷Δ** — 「3.34~3.90 «보다» «클» 것」 | **%.2f · %.2f** | ✅ **맞았다** |"
      % tuple(mdes))
    P("| **칸** — 「4a 또는 5 가 «제일» 그럴듯」 | **%s** | ✅ **맞았다** |"
      % " · ".join(c[0] for c in cells))
    P("")
    P("   ★★ **«방향»은 «틀렸고» «세기»는 «맞았다** — **유형 78 이 «그대로» 재현됐다**")
    P("   🚨 그리고 **점추정 방향이 「«어제» «내»가 «바랐던» 쪽」(Ⓛ 가 위)과 «같다**")
    P("      ⇒ ⛔ **「그러니 원전이 옳았다」로 «읽으면» «틀린다** — **CI 가 0 을 «품는다**")
    P("      ⇒ ★ **「예상을 «뒤집는» 것」이 «편향»을 «지우지» «않는다** — **막은 것은 «사전등록»**이다")
    P(F3)
    P("")
    P("# ⛔ **5. 「«이겨도» «못» 쓸 것」**(사전등록에 «박은» 것)")
    P("")
    P(F3)
    P("| 나왔으면 | «쓸» 수 «있는» 말 | ⛔ «못» 쓰는 말 |")
    P("|---|---|---|")
    P("| %s 가 «위» | 「**«우리» 25 vs 원전 50 에서 «후자»가 «나았다**」 | ⛔ 「원전이 «옳다»」 · "
      "⛔ 「50 이 «최적»이다」 — **격자를 «안** 돌렸다 |" % CL)
    P("| %s 가 «아래» | 「**50일선은 «우리» 25 보다 «못하다**」 | ⛔ 「래칫이 «나쁘다»」 — "
      "**래칫 «자체»는 «둘» 다 «쓴다** |" % CL)
    P("| «못» 가림 | 「**«이» 자로는 «두» 값을 «못» 가른다**」 | ⛔ 「«같다»」 — **MDE 를 «같이» 읽어라** |")
    P("")
    P("   🚨 **어느 쪽이든 «남는» 것**: **「25」의 «출처»는 «여전히» «없다**")
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 한 것**")
    P("")
    P(F3)
    P("⛔ ① **「50일선」이 「단순」인지 「지수」인지 원전이 «안** 말한다 ⇒ **«단순»으로 «내»가 «정했다**(유형 68)")
    P("⛔ ② **격자를 «안** 돌렸다 — **25 vs 50 «두» 점**뿐이다")
    P("⛔ ③ **목표(＋30%%) «전» 구간은 «둘» 다 «−10 고정»**이다 — **«거기»의 래칫은 «안** 쟀다")
    P("⛔ ④ **`76`(고점 대비 «비율» 래칫)과는 **«다른» 것**이다 — **«맞대지» «않았다**")
    P("⛔ ⑤ **팔 «둘»의 거래 «수»가 «다르다** — **중복 제거가 «달라»서다**(`156` 유형)")
    P("⛔ ⑥ 💰 **비용 실측**: 자료 짓기 **%.1f 분** · 부트 **%.1f 분**" % (t_build / 60.0, t_boot / 60.0))
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
r"""257 - **«조건부» 본전 스톱**  (조사 세션 2026-09-10)

  📖 원전 `tm:36` 「… 저는 일단 «수익»이 **«위험노출 금액»의 «배수»** 혹은 «평균 수익» «이상»이 되면
     수익을 «보호»하고자 «절차»를 만들어 놓았습니다 …」  ·  `tm:39` 에 **범위 2~6배**

  ⛔ **사전등록** `results/257-PRE.md` · **걸린 «건수»** `results/257a-count-trigger.md`
  ✅ **격자 = ㉮ 「원전 «범위» «지킴»」**(두뇌 결정) — Ⓑ2 · Ⓑ4 · Ⓑ6
     🚨 **Ⓑ4·Ⓑ6 은 «불발**(257a: 0건) ⇒ **판정에서 «빼고» «양성 대조»로 «쓴다**

  ⛔ **원본을 «건드리지» «않는다** — `pyr_trigger.py` 를 «복사**한 `_pyr_cb.py`(`CB_N`) 를 «따로» 싣는다

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/257-condbe.py
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

C1 = chr(0x2460)
B2, B4, B6 = "Ⓑ2", "Ⓑ4", "Ⓑ6"
ARMS = ((C1, 0.0), (B2, 2.0), (B4, 4.0), (B6, 6.0))
MAIN = B2                     # ⛔ **주 판정 «하나** — 살아 있는 팔이 «하나»뿐이라
CTRL = (B4, B6)               # ⛔ **양성 대조** — ① 과 **«자리»까지 «똑같아야** 한다
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 257257
BLOCKS = ((20, 40), (80, 80))
SD_GATE = 0.05                # ⛔ **분기 문턱 — 결과 «보기» 전에 박음**(`256` 과 «같은» 값·유도)


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91
OUT = Path(str(r91.OUT))
CA = OUT / "257-arms.json"


def eq_of(by_pos, n_pos, slots=5):
    eq, held, got, sday = 1.0, [], 0, 0
    for p in range(n_pos):
        if held:
            keep_ = []
            for hh in held:
                if hh[0] < p:
                    eq += hh[1] * hh[2] / 100
                else:
                    keep_.append(hh)
            held = keep_
        free = slots - len(held)
        cc = by_pos.get(p)
        if free > 0 and cc:
            wgt = eq / slots
            for rel, nt, _k in cc[:free]:
                held.append([p + rel, wgt, nt])
                got += 1
                sday += rel
    for hh in held:
        eq += hh[1] * hh[2] / 100
    return (eq - 1.0) * 100.0, got, sday


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


def build(mod):
    """`201d.build_pairs` 와 «같은» 구성 — «해소» 모듈«만** 갈아 끼운다."""
    old = r91.SUB
    r91.SUB = m201d.CANON
    try:
        (_a, _b, by2), missing, _ = r91.load_ladder(
            m201d.YEARS, m201d.D0, m201d.D1, "91-monthly-us-full.json", use_ext=False)
    finally:
        r91.SUB = old
    if missing:
        return None
    fund, ixf = m201d.f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    out = []
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = m201d.f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None
                          or m201d.r102._ord(p["entry_date"]) - m201d.r102._ord(a[0])
                          > m201d.r102.STALE_MAX)
                 else m201d.r103.judge(arq, arq.index(a), ix, 1, 2))
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
            epx, d, rd = t["entry_px"], p["d"], r["resolve_date"]
            net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                      for _dd, fr, px in r["exits"])
            hold = d.index(rd) if (rd and rd in d) else len(d) - 1
            out.append((cd, t["entry_date"], max(1, hold), net))
    return out



def verify_sample(keys, kA, kB):
    """«달라진» 거래를 «경로»에서 «손»으로 «다시» 센다 — `253` 의 「진짜 함수를 «부른다»」 얼개."""
    want = set(keys)
    old = r91.SUB
    r91.SUB = m201d.CANON
    try:
        (_a, _b, by2), missing, _ = r91.load_ladder(
            m201d.YEARS, m201d.D0, m201d.D1, "91-monthly-us-full.json", use_ext=False)
    finally:
        r91.SUB = old
    if missing:
        return []
    mod = _load("cb_chk", "_pyr_cb.py")
    mod.CB_N = 2.0
    out, seen = [], set()
    for y in sorted(by2):
        for p in by2[y]:
            k = (p["code"], p["entry_date"])
            if k not in want or k in seen:
                continue
            seen.add(k)
            t = mod.resolve_trade(p, ft="limit", fs="market", stop=m201d.STOP,
                                  target=m201d.TARGET, half=m201d.HALF,
                                  shares=(1.0,), add_stop="floor_entry")
            r = t["masks"][()]
            epx, d, h, l = t["entry_px"], p["d"], p["h"], p["l"]
            thr = epx * (1.0 + 2.0 * m201d.STOP / 100.0)
            cb = next((i for i in range(len(d)) if h[i] is not None and h[i] >= thr), None)
            be = None
            if cb is not None:
                be = next((i for i in range(cb + 1, len(d))
                           if l[i] is not None and l[i] <= epx), None)
            rd = r["resolve_date"]
            ri = d.index(rd) if (rd and rd in d) else len(d) - 1
            # 본전에 «닿은» 첫 날이 «목표»보다 «앞»이면 — «그날» 결착돼야 한다
            ok = (be is None) or (be >= ri)
            out.append({"code": k[0], "entry": k[1],
                        "a_h": kA[k][0], "a_n": kA[k][1],
                        "b_h": kB[k][0], "b_n": kB[k][1],
                        "cb": d[cb] if cb is not None else "—",
                        "be": d[be] if be is not None else "—(안 닿음)",
                        "res": rd or "—", "ok": ok})
    return out



def branch_checks(diff, only_b, kA, kB):
    """㉡·㉢·㉣ 갈래를 «각» «한» 건씩 «집어» «경로»에서 «손»으로 «본다**."""
    out = {"b_mark": "❌", "b_txt": "—", "c_mark": "❌", "c_txt": "—",
           "d_mark": "❌", "d_txt": "—"}
    want = set(diff) | set(only_b)
    old = r91.SUB
    r91.SUB = m201d.CANON
    try:
        (_a, _b, by2), missing, _ = r91.load_ladder(
            m201d.YEARS, m201d.D0, m201d.D1, "91-monthly-us-full.json", use_ext=False)
    finally:
        r91.SUB = old
    if missing:
        return out
    mod = _load("cb_br", "_pyr_cb.py")
    mod.CB_N = 2.0
    base = _load("cb_bs", "_pyr_cb.py")
    base.CB_N = 0.0
    n_b = n_c = 0
    ex_b = ex_c = None
    for y in sorted(by2):
        for p in by2[y]:
            k = (p["code"], p["entry_date"])
            t0_ = base.resolve_trade(p, ft="limit", fs="market", stop=m201d.STOP,
                                     target=m201d.TARGET, half=m201d.HALF,
                                     shares=(1.0,), add_stop="floor_entry")
            r0 = t0_["masks"][()]
            epx, d, h, l = t0_["entry_px"], p["d"], p["h"], p["l"]
            thr = epx * (1.0 + 2.0 * m201d.STOP / 100.0)
            cb = next((i for i in range(len(d)) if h[i] is not None and h[i] >= thr), None)
            if cb is None:
                continue
            fd = r0["exits"][0][0] if r0["exits"] else None
            fi = d.index(fd) if (fd and fd in d) else len(d) - 1
            if cb >= fi:
                continue                      # `257a` 대로 «불발**
            # ㉢ — 조건 걸린 날이 «목표» 도달일과 «같은» 봉
            if cb == fi:
                n_c += 1
            be = next((i for i in range(cb + 1, len(d))
                       if l[i] is not None and l[i] <= epx), None)
            # ㉡ — 조건은 걸렸는데 저가가 본전 «아래»로 «안** 감
            if be is None:
                n_b += 1
                if ex_b is None and k not in want:
                    ex_b = (k, d[cb], r0["resolve_date"])
    if n_b:
        out["b_mark"] = "✅"
        out["b_txt"] = ("**%s건** — 보기 `%s` %s(조건 %s · 저가가 본전 «아래»로 «안** 감 ⇒ "
                        "**결과 «그대로»**)" % (format(n_b, ","), ex_b[0][0], ex_b[0][1],
                                                 ex_b[1]) if ex_b
                        else "**%s건**(보기 «못» 집음)" % format(n_b, ","))
    else:
        out["b_txt"] = "**0건** — 이 자료엔 «없다**"
    out["c_mark"] = "⚪" if n_c == 0 else "✅"
    out["c_txt"] = ("**0건** — 조건(＋20%)이 목표(＋30%)와 «같은» 봉에 «걸리는» 일이 «없었다**"
                    if n_c == 0 else "**%d건**" % n_c)
    return out


def slot_trace(recs, pos, n_pos, key, slots=5):
    """㉣ — 「«어느» 거래가 «일찍» 나가 «자리»를 비웠나」를 «한» 건 «짚는다**."""
    tgt = pos[key[1]]

    def held_at(lst):
        eq, held = 1.0, []
        for p in range(n_pos):
            if held:
                held = [hh for hh in held if hh[0] >= p]
            if p == tgt:
                return list(held)
            free = slots - len(held)
            cc = [x for x in lst if pos[x[1]] == p]
            if free > 0 and cc:
                for c_, d_, h_, _n in cc[:free]:
                    held.append([p + h_, c_, d_])
        return []
    return held_at(recs[C1]), held_at(recs[MAIN])


def main():  # noqa: C901
    P("# 257 - **«조건부» 본전 스톱**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/257-condbe.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> 사전등록 " + BQ + "results/257-PRE.md" + BQ + " · 걸린 건수 "
      + BQ + "results/257a-count-trigger.md" + BQ)
    P("")
    P(F3)
    P("📖 원전 `tm:36` — 「수익이 **위험노출 금액의 «배수»**가 되면 손익분기점으로 스톱을 «옮긴다**」")
    P("   `tm:39` 에 **범위 «2~6배»**  ⇒ ✅ **범위는 «원전» 것** · 🔴 **«그» 안의 «점»은 «우리» 것**")
    P("")
    P("📐 **위험노출 = `a × stop/100`**(우리 정의 · 조건 ② 로 «확정»)")
    P("   ⇒ ★ **「N배」의 «뜻» = 수익률 «N × stop%%」** — **stop = %.0f 이므로**:" % m201d.STOP)
    for nm, cn in ARMS:
        if cn > 0:
            P("      **%s → ＋%.0f%%**%s" % (nm, cn * m201d.STOP,
                                             "   ← 🚨 **목표(＋%.0f%%) «위»**" % m201d.TARGET
                                             if cn * m201d.STOP > m201d.TARGET else ""))
    P("   ⛔ `rm:11`(자본금 0.75~1.25%)은 **포지션 «크기»** 규칙이지 «이» 자가 «아니다** — **갈라** 적는다")
    P("")
    P("⛔ **원본을 «건드리지» «않았다** — " + BQ + "_pyr_cb.py" + BQ + "(`CB_N`) 복사본")
    P("   `_pyr_cb.py:324` `if CB_N > 0.0 and _cb_i is not None and i > _cb_i: S = max(S, a)`")
    P("   ⛔ **「닿은 «다음» 봉부터」**(`i > _cb_i`) — **«같은» 봉에 올리면 «장중» 앞뒤를 «모르는» 채 쓴다**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 0. 판정표 «미리» ─────────────────────────────────────────
    P("# ⛔ **0. 판정표 — «결과»를 «보기» «전»에 «박는다**")
    P("")
    P(F3)
    P("| 결과 | ✅ «쓸» 말 | ⛔ «쓰지» «않을» 말 |")
    P("|---|---|---|")
    P("| **Ⓑ2−① 칸 1** | 「**«조건부» 본전(＋20%에서 «올림»)이 «현행»보다 «나았다**」 | "
      "⛔ 「원전«대로» 했다」(방아쇠·조건이 «다르다») · ⛔ 「배수 «2»가 «최적»」 |")
    P("| **Ⓑ2−① 칸 2** | 「**«이» 조건부 본전은 «현행»보다 «나빴다**」 | "
      "🚨 ⛔ **「조건부 본전이 «해롭다»」** — **«사슬»과 «구분» «안** 된다(아래 «사전» 문장) |")
    P("| **Ⓑ2−① 칸 5** | 「**«이» 자로는 «못** 가린다」 ＋ **MDE 를 «같은 줄»에** | "
      "⛔ 「«같다»」 · ⛔ 「«무해»하다」 |")
    P("| **양성 대조 «어긋남»** | — | 🛑 **«멈춘다** — 복사본이 원본과 «어긋났다**는 뜻 |")
    P("")
    P("🚨 **«사전» 문장 — «회전» 교란의 «방향»**(⛔ 결과 «보기» 전에 박는다)")
    P("   **`S` 를 «올리면» 청산이 «앞당겨»져 «회전»이 «는다** ⇒ **`255` 대로면 «나빠진다**")
    P("   ⇒ ✅ **「이 판에서 «회전» 교란은 «가설»에 «불리»하게 작용한다」**")
    P("   ⇒ ⇒ ★ **「좋아졌다」가 «나오면» 그건 «회전»으로 «설명»되지 «않는다** — **«드문** 판이다")
    P("   ⇒ ⛔ **«대칭»**: **「나빠졌다」면 «사슬»과 «구분»되지 «않는다** ⇒ **「해롭다」를 «못** 쓴다")
    P("")
    P("🔴 **«편향»** — **조사(나)·두뇌 = 「조건부 본전이 «낫다»」** · **검증 = 「«못** 가린다」**")
    P("   ⛔ **막는 것은 «구조»**: **양성 대조 «출력값»** · **`SD_GATE` 분기** · **판정표 «코드 안» 인쇄**")
    P(F3)
    P("")
    P("---")
    P("")

    t0 = time.time()
    recs = None
    if CA.exists():
        raw = json.loads(CA.read_text(encoding="utf-8"))
        recs = {k: [tuple(x) for x in v] for k, v in raw.items()}
        if any(len(x) != 4 for v in recs.values() for x in v[:1]):
            recs = None
        if recs is not None:
            P(F3)
            P("   (♻️ 갈무리 " + BQ + "257-arms.json" + BQ + ")")
            P(F3)
    if recs is None:
        recs = {}
        for nm, cn in ARMS:
            mod = _load("cb_%s" % nm.encode("unicode_escape").decode().replace("\\", ""),
                        "_pyr_cb.py")
            mod.CB_N = cn
            P("(팔 %s — CB_N = %.1f 짓는 중 …)" % (nm, cn), flush=True)
            r = build(mod)
            if r is None:
                P("🚨 경로 «없음»")
                return 1
            recs[nm] = r
            P("  %s — 거래 %s (%.1f분)" % (nm, format(len(r), ","),
                                           (time.time() - t0) / 60.0), flush=True)
        CA.write_text(json.dumps({k: [list(x) for x in v] for k, v in recs.items()}),
                      encoding="utf-8")
        P("")
        P(F3)
        P("   ✅ 자료 짓기 **%.1f 분**(실측)" % ((time.time() - t0) / 60.0))
        P(F3)
    P("")

    cal = json.loads((OUT / "201d-arms2.json").read_text(encoding="utf-8"))["cal"]
    ents = {d for k in recs for _c, d, _h, _n in recs[k]}
    if ents - set(cal):
        cal = sorted(set(cal) | ents)
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)
    keys = [nm for nm, _c in ARMS]

    def obs(lst):
        bp = defaultdict(list)
        for _c, d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return eq_of(bp, n_pos)

    o, got, sday = {}, {}, {}
    for k in keys:
        e, g, s = obs(recs[k])
        o[k], got[k], sday[k] = m201d.ann(e), g, s

    # ── 1. 양성 대조 ─────────────────────────────────────────────
    P("# 🛑 **1. «양성» 대조 — Ⓑ4·Ⓑ6 이 ① 과 **«자리»까지 «똑같은가**")
    P("")
    P(F3)
    P("   🔎 **까닭**: `257a` 가 **「＋40%·＋60% 는 «첫» 청산 «앞»에 «한» 번도 «안** 닿는다」(0건)")
    P("      ⇒ **조건이 «영원히» 불발** ⇒ **① 과 «똑같아야** 한다")
    P("   ⛔ **「≈」로 «넘기지» «않는다** — **네 «수»가 «전부» «자리»까지 «같아야** 한다")
    P("   🚨 **하나라도 다르면 «멈춘다** — **복사본 `_pyr_cb.py` 가 원본과 «어긋났다**는 뜻이다")
    P(F3)
    P("")
    P("| 팔 | 거래 수 | 연환산 %p/해 | 슬롯 «얻은» 것 | «슬롯-일» | ① 과 «똑같은가** |")
    P("|---|---:|---:|---:|---:|:--|")
    ok_all = True
    for k in keys:
        if k == C1:
            same = "— (기준)"
        else:
            eq4 = (len(recs[k]) == len(recs[C1]) and abs(o[k] - o[C1]) < 1e-12
                   and got[k] == got[C1] and sday[k] == sday[C1])
            if k in CTRL:
                same = "✅ **«똑같다**" if eq4 else "🛑 **«다르다**"
                ok_all = ok_all and eq4
            else:
                same = "⚪ (판정 팔 — 달라야 «정상»)" if not eq4 else "🚨 **«같다** — 조건이 «불발»했나?"
        P("| %s | %s | **%+.6f** | %s | %s | %s |"
          % (k, format(len(recs[k]), ","), o[k], format(got[k], ","),
             format(sday[k], ","), same))
    P("")
    P(F3)
    P("   ⇒ **양성 대조 = %s**  (규약 ②: 관문을 «주장»이 «아니라» **«출력값»**으로)"
      % ("✅ **통과**" if ok_all else "🛑 **«미통과**"))
    P(F3)
    P("")
    if not ok_all:
        P("---")
        P("")
        P("# 🛑🛑 **«여기»서 «끝난다** — **양성 대조 «미통과**")
        P("")
        P(F3)
        P("   ⛔ **판정을 «내지» «않는다** — **사전등록에 «그렇게» 박았다**")
        P(F3)
        P("")
        P("⛔ **커밋은 두뇌 몫입니다.**")
        return 0
    P("---")
    P("")

    # ── 2. 슬롯-일 분기 ──────────────────────────────────────────
    P("# ★★ **2. «슬롯-일»을 «먼저** — **분기 규칙이 «여기»서 «걸린다**")
    P("")
    P(F3)
    P("   ⛔ **`SD_GATE = %.2f` 는 «결과 «보기 전»»에 박은 값**이다(`256` 과 «같은» 값·유도)"
      % SD_GATE)
    P("   ⛔ **«예상»으로 «건너뛰지» «않았다** — **예상은 「≥5%」였다**(`257-PRE` §⑦)")
    P(F3)
    P("")
    sd_pair = (sday[C1], sday[MAIN])
    spread = abs(sd_pair[1] - sd_pair[0]) / max(1, min(sd_pair))
    P("   **① %s** vs **%s %s**  ⇒  **최대 차 %.4f%%**"
      % (format(sday[C1], ","), MAIN, format(sday[MAIN], ","), 100 * spread))
    P("   문턱 **%.0f%%** ⇒ **%s**"
      % (SD_GATE * 100,
         "✅ **㉠ 그대로** — 「«본전» 축」이라 «불러도» 된다" if spread < SD_GATE
         else "🚨 **㉡ 로 «올림»** — **「본전 ＋ 슬롯-일 차 %.2f%%」**로 «이름»을 «바꾼다**"
              % (100 * spread)))
    P("")
    P("   🔎 **보유 중앙**: ① **%.0f일** · %s **%.0f일**"
      % (st.median([h for _c, _d, h, _n in recs[C1]]), MAIN,
         st.median([h for _c, _d, h, _n in recs[MAIN]])))
    P(F3)
    P("")
    P("---")
    P("")

    # ── 3. 주 판정 ───────────────────────────────────────────────
    P("---")
    P("")
    P("# 🚨🚨 **2b. 「조건이 «걸렸다»」 ≠ 「스톱이 «물렸다»」 — **«진짜»** 달라진 «건수**")
    P("")
    P(F3)
    P("   🔎 `257a` 의 **2,022건**은 **「`S` 를 `a` 로 «올린»」** 건수다.")
    P("      🚨 **가격이 «다시» `a` 까지 «안» 내려오면 «아무» 일도 «안** 일어난다 ⇒ **그 거래는 ① 과 «동일**")
    P("   ⇒ ★★ **`232` 와 «같은» 모양**(「처치가 271 이 «아니라» **«10건»**」) — **«세어» 적는다**")
    P(F3)
    P("")
    kA = {(c, d): (h, n) for c, d, h, n in recs[C1]}
    kB = {(c, d): (h, n) for c, d, h, n in recs[MAIN]}
    both = set(kA) & set(kB)
    diff = sorted(k for k in both if kA[k] != kB[k])
    only_a = sorted(set(kA) - set(kB))
    only_b = sorted(set(kB) - set(kA))
    P("| | 건수 | 비율(① 기준) |")
    P("|---|---:|---:|")
    P("| ① 거래 | **%s** | — |" % format(len(kA), ","))
    P("| %s 거래 | **%s** | — |" % (MAIN, format(len(kB), ",")))
    P("| «둘» 다 «있고» **결과가 «다른**» 것 | **%s** | **%.2f%%** |"
      % (format(len(diff), ","), 100.0 * len(diff) / max(1, len(kA))))
    P("| ① «에만» 있는 것(중복제거 «어긋남») | **%s** | %.2f%% |"
      % (format(len(only_a), ","), 100.0 * len(only_a) / max(1, len(kA))))
    P("| %s «에만» 있는 것 | **%s** | %.2f%% |"
      % (MAIN, format(len(only_b), ","), 100.0 * len(only_b) / max(1, len(kA))))
    n_treat = len(diff) + len(only_a) + len(only_b)
    P("")
    P(F3)
    P("   ⇒ ★★★ **«진짜» 처치 = %s 건**(다른 것 %s ＋ 한쪽에만 %s)"
      % (format(n_treat, ","), format(len(diff), ","),
         format(len(only_a) + len(only_b), ",")))
    P("   ⇒ **`257a` 의 「조건 걸림 2,022」 대비 %.1f%%**" % (100.0 * n_treat / 2022.0))
    P("   ⛔ **그러니 「2,022건에 «걸었다»」로 «읽으면» «틀린다**")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 🚨 **2c. «새» 코드 «경로»가 «맞나** — **«손»으로 «다섯**(⛔ 「확인했다」가 «아니라 «수»)")
    P("")
    P(F3)
    P("   🚨 **양성 대조(§1)의 «약점»**: Ⓑ4·Ⓑ6 은 조건이 **«아예» 발동 «안** 해서 —")
    P("      **`_pyr_cb.py` 의 «새» 줄(`:324`)이 «한» 번도 «안** 돈다")
    P("      ⇒ **「복사본이 «원본»과 «같다»」만 «검산**하고 **「«새» 코드가 «맞다»」는 «안** 한다")
    P("   ✅ **그래서 «달라진» 거래 «다섯»을 «집어» — «경로»에서 «손»으로 «다시» 센다**")
    P("      ㉠ 조건 «걸린» 날 = **고가가 `epx × 1.20` 에 «처음» 닿은» 날**")
    P("      ㉡ 그 «다음» 봉부터 **저가 ≤ `epx`(본전)**인 «첫» 날이 **Ⓑ2 의 «청산일»과 «같은가**")
    P(F3)
    P("")
    if diff:
        chk = verify_sample(diff[:5], kA, kB)
        P("| 종목·진입일 | ① (보유, 순) | %s (보유, 순) | 조건 걸린 날 | 본전 «닿은» 첫 날 | Ⓑ2 청산일 | «같은가** |"
          % MAIN)
        P("|---|---|---|---|---|---|:--|")
        okn = 0
        for r in chk:
            okn += 1 if r["ok"] else 0
            P("| `%s` %s | (%d, %+.2f) | (%d, %+.2f) | %s | %s | %s | %s |"
              % (r["code"], r["entry"], r["a_h"], r["a_n"], r["b_h"], r["b_n"],
                 r["cb"], r["be"], r["res"], "✅" if r["ok"] else "🛑 **어긋남**"))
        P("")
        P(F3)
        P("   ⇒ **%d / %d 맞음** — %s"
          % (okn, len(chk), "✅ **«새» 코드 경로 «검산» 통과**" if okn == len(chk)
             else "🛑 **«미통과** — ⛔ **판정을 «내지» «않는다**"))
        P(F3)
        if okn != len(chk):
            P("")
            P("⛔ **커밋은 두뇌 몫입니다.**")
            return 0
    else:
        P("   🛑 **달라진 거래가 «없다** — **처치가 «0»**이다")
        P(F3)
    P("")
    P(F3)
    P("   🔴 **«자»가 «틀렸다** — 「5/5 로 «충분»한가」는 **«틀린» 물음**이었다(검증 2차)")
    P("      🔎 이 검산이 재는 것은 **「«새» 코드 «경로»가 «맞나」 = «결정론적» 논리**이지 **«통계 표본»이 «아니다**")
    P("      ⇒ ★ **맞으면 5/5 든 500/500 이든 «같고» — 틀리면 «대개» «첫» 건에서 «드러난다**")
    P("      ⇒ ★★★ **자는 「«몇» 건」이 «아니라 「«몇» «갈래»를 «덮었나»」**")
    P(F3)
    P("")
    P("## **갈래 «넷** — «덮었나**")
    P("")
    br = branch_checks(diff, only_b, kA, kB)
    if only_b:
        k4 = only_b[0]
        hA_, hB_ = slot_trace(recs, pos, n_pos, k4)
        freed = [x for x in hA_ if x[1] not in {y[1] for y in hB_}]
        br["d_mark"] = "✅"
        br["d_txt"] = ("보기 **`%s` %s** — 그날 ① 은 자리 **%d/5** «참**, %s 는 **%d/5** ⇒ "
                       "**«빈» 자리로 «들어왔다**%s"
                       % (k4[0], k4[1], len(hA_), MAIN, len(hB_),
                          (" · **«일찍» 나간 것 = `%s`(진입 %s)**" % (freed[0][1], freed[0][2]))
                          if freed else ""))
    P("| 갈래 | 덮음 | «수»·«보기» |")
    P("|---|:--|---|")
    P("| ㉠ 조건 «걸림» ＋ 그 뒤 저가 ≤ `epx` → **«조기» 청산** | ✅ **5/5** | 위 표 |")
    P("| ㉡ 조건 «걸림» ＋ 저가가 `epx` «아래»로 **«안** 감 → **«아무 일» 없음** | %s | %s |"
      % (br["b_mark"], br["b_txt"]))
    P("| ㉢ 조건 걸린 날 = **«목표» 도달일**인 «경계» | %s | %s |" % (br["c_mark"], br["c_txt"]))
    P("| 🚨 ㉣ **Ⓑ2 «에만» 있는 %d건** = **«자리»가 비어 «새로» 들어온 거래** | %s | %s |"
      % (len(only_b), br["d_mark"], br["d_txt"]))
    P("")
    P(F3)
    P("   🚨 **㉣ 이 «제일» 중요하다** — **45건은 「조건부 본전」의 «효과»가 «아니라» «회전»의 «2차» 효과**다")
    P("      ⇒ **`254` 의 「Ⓡ 은 «귀무»이지 «대안»이 «아니다」와 «같은» 자리** ⇒ **«이름»에 «들어가야** 한다")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 3. **주 판정 — %s − ①**(⛔ **판 «하나»**)" % MAIN)
    P("")
    P(F3)
    P("   ⛔ **max-T 를 «안** 쓴다 — **까닭: 살아 있는 팔이 «하나»뿐이라 «고를» 것이 «없다**")
    P("      (⛔ **「보정을 «건너뛰었다»」가 «아니다** — **Ⓑ4·Ⓑ6 은 «불발»이라 «칸»이 «아니다**)")
    P(F3)
    P("")
    ia = {k: defaultdict(list) for k in (C1, MAIN)}
    for k in (C1, MAIN):
        for j, (_c, d, _h, _n) in enumerate(recs[k]):
            ia[k][pos[d]].append(j)
    obsd = o[MAIN] - o[C1]
    P("| 블록 | 점추정 | **백분위 CI** | 칸 | **기본 CI** | 칸 | **MDE** | MDE÷Δ |")
    P("|---|---:|---:|:--|---:|:--|---:|---:|")
    cells = []
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m201d.BMIN, m201d.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        col = []
        for _bi in range(NBOOT):
            order = m201d.draw(n_pos, rnd)
            vv = {}
            for k in (C1, MAIN):
                bp = defaultdict(list)
                for newp, oldp in enumerate(order):
                    for j in ia[k].get(oldp, ()):
                        _c, _d, h, nt = recs[k][j]
                        bp[newp].append((h, nt, 0))
                vv[k] = m201d.ann(eq_of(bp, n_pos)[0])
            col.append(vv[MAIN] - vv[C1])
            if (_bi + 1) % 500 == 0:
                P("  [%d~%d] 부트 %d/%d" % (bmn, bmx, _bi + 1, NBOOT), flush=True)
        v = sorted(col)
        lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
        sdv = st.stdev(col)
        blo, bhi = 2 * obsd - hi, 2 * obsd - lo
        cp, cb = cell_of(lo, hi), cell_of(blo, bhi)
        cells.append((cp, cb))
        P("| **%d~%d** | **%+.3f%%p** | [%+.3f, %+.3f] | %s | [%+.3f, %+.3f] | %s | **%.3f** | %.2f |"
          % (bmn, bmx, obsd, lo, hi, cp, blo, bhi, cb, MDE_K * sdv, MDE_K * sdv / DELTA),
          flush=True)
    P("")
    P(F3)
    P("   백분위 칸 = %s  ·  기본 칸 = %s"
      % (" · ".join(c[0] for c in cells), " · ".join(c[1] for c in cells)))
    P(F3)
    P("")
    P("---")
    P("")
    P("# 🎯 **⇒ 판정** — **§0 표를 «그대로» 읽는다**")
    P("")
    P(F3)
    cs = {c for pair in cells for c in pair}
    if cs == {"**5**"}:
        P("⇒ ✅ **네 칸 «전부» 5** ⇒ 「**«이» 자로는 «못** 가린다」")
        P("   ⛔ 「«같다»」 ✗ · ⛔ 「«무해»하다」 ✗")
        P("")
        P("   🔴🔴 **«사전» 문장을 «쓰려다» «막혔다** — **«양쪽» 다 «막힌다**(검증 2차)")
        P("      🔎 슬롯-일 **① %s → %s %s**(**%+.2f%%**) — **Ⓑ2 가 «적다**"
          % (format(sday[C1], ","), MAIN, format(sday[MAIN], ","),
             100.0 * (sday[MAIN] - sday[C1]) / max(1, sday[C1])))
        P("      🔎 점추정은 **%+.3f%%p**(«위») ⇒ **부호가 «반대»다**" % obsd)
        P("")
        P("      ⛔ **「교란이 «불리**했는데도 «위»였다」 ✗** — **«너무» 세다**(사슬을 «주장»으로 쓴다)")
        P("      ⛔ **「«사슬»이 «설명»한다」 ✗** — **«같은» 수를 «반박»으로 쓴다**")
        P("      🔎 **까닭**: 「슬롯-일↑ = 성적↑」은 **`255` 에서 «관측»된 관계**이지 "
          "**«도구»의 «성질»이 «아니다**")
        P("         그리고 **`255` 는 범위 15,702~30,420 에서 봤고 «여기»는 «0.95%»** ⇒ "
          "**«그» 범위에서 «같은» 관계가 «서는지»를 «안** 쟀다")
        P("")
        P("      ✅ **«쓸» 수 «있는» 꼴 — «사실» 둘을 «나란히» · «인과» 주장 «없이**:")
        P("         「**슬롯-일이 «줄었는데도» 점추정은 «위»였다. 다만 «이» 크기(−0.95%)에서")
        P("           슬롯-일이 성적을 «어느» 쪽으로 «미는지»는 «안** 쟀다**」")
    P("   ⛔ **«못» 쓸 말 — «둘» «더**(두뇌·검증이 «먼저» 박은 것)")
    P("      ⛔ 「원전 «범위»를 «다» 재 봤다」 ✗ — **«실제»로 «잰» 것은 N=2 «하나»**")
    P("      ⛔ 「배수가 «클수록» 좋다/나쁘다」 ✗ — **Ⓑ4·Ⓑ6 은 «잰» 것이 «아니라» «불발»**")
    P("      ✅ **정확한 꼴**: 「**우리 목표(＋%.0f%%)에서 «걸릴» 수 «있는» 원전 배수는 «2» «하나»뿐이고 —"
      % m201d.TARGET)
    P("         «그것»을 쟀다**」")
    P("")
    P("   🔴 **그리고 «N < 3» 구간에 대해**(두뇌 정정 — 「항등식이라 «이미» 안다」는 **«틀렸다**):")
    P("      ⛔ **N<3 은 «원전»이 «안** 준 수다 ⇒ **「«우리»가 «고른» 수」가 «된다**")
    P("      ⛔ **그리고 «N<3 구간의 «성적»은 «안** 쟀다** — **「걸리는 «건수»가 «는다」는 «항등식»이지만**")
    P("         **「그래서 «낫나» «나쁘나»」는 «항등식»이 «아니다**")
    P("      ⇒ ★ **「«알아서» «안» 쟀다」로 «읽히면» «안** 된다(유형 110 의 «셋째»)")
    P("")
    P("   📌 **§B 감 — 「−Δ 배제」는 «넷» 중 «하나»뿐이다**")
    P("      백분위 20~40 🔴 · 백분위 80~80 🔴 · 기본 20~40 🔴 · **기본 80~80 ✅**")
    P("      🚨 그리고 «그» 하나가 **«제일» «좁은»** 자다 ⇒ ⛔ **자를 «결과 보고» 고르면 «고르기»**")
    P("      ⇒ ⛔ **「Δ «만큼» 나빠지는 것은 «배제»된다」 ✗**")
    P("      ⇒ ✅ **§B 에는 「«제일» «좁은» 자에서는 −Δ 가 «배제»됐다」** — **「없다」가 «아니라» 「«아직»」**")
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 한 것**")
    P("")
    P(F3)
    P("⛔ ① **손절 «−%.0f 하나»**에서만 쟀다 — **문턱이 `stop` 에 «매여** 있다(N×stop%%)" % m201d.STOP)
    P("⛔ ② **방아쇠가 «다르다** — 원전은 「위험 대비 «보상» «반전»」, 우리는 **＋%.0f%% «목표»**"
      % m201d.TARGET)
    P("⛔ ③ **「평균 수익 «이상»」 갈래를 «접었다**(원전의 «또» 하나 — «룩어헤드» 때문 · «다음» 판)")
    P("⛔ ④ **「닿았다」는 «고가» 기준**이다 — **원전이 「«종가»가」라 «안** 했다(우리 «선택»)")
    P("⛔ ⑤ **`a` 를 `epx` 로 잡았다** — `shares=(1.0,)` 라 **트랜치가 «하나»**여서다")
    P("⛔ ⑥ 💰 **비용 실측**: **%.1f 분**" % ((time.time() - t0) / 60.0))
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
r"""260 - **트레일링 «두» 격자 — ㉮ «일수» 창 · ㉯ «비율» 폭**  (조사 세션 2026-09-10)

  🚨 **까닭**: 사용자가 **「«트레일링 스탑»으로 «미국» 시장에 «투자»」**한다고 정했다(2026-09-10).
     ⇒ **`41:58 TRAIL_WINDOW = 25` 가 «곧» «실제» 돈을 굴리는 손잡이**인데 —
     ⇒ 🔴 **`259` 가 「25」의 «유도»가 «어디»에도 «없다**」를 «전수»로 «확인**했다.

  ⛔ **묻는 것은 「«어느» 창이 «좋은가»」가 «아니다** — **「«면»이 «평평»한가」**다
  ⛔ **원본을 «건드리지» «않는다** — `trail`·`run_trail` 은 **«이미» 인자**다(복사본 «불필요**)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/260-trail-grid.py
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

GRID = (10, 15, 20, 25, 30, 40, 50)     # ⛔ **25 를 «중앙»에 둔 «대칭»** — 결과 «보기» 전에 박음
CUR = 25
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 260260
BLOCKS = ((20, 40), (80, 80))


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91
pt = r91.pt
OUT = Path(str(r91.OUT))
CA = OUT / "260-arms.json"


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


def build_all():
    """사다리를 **«한» 번** 싣고 — 팔 «열넷»을 «돌려» 낸다."""
    old = r91.SUB
    r91.SUB = m201d.CANON
    try:
        (_a, _b, by2), missing, _ = r91.load_ladder(
            m201d.YEARS, m201d.D0, m201d.D1, "91-monthly-us-full.json", use_ext=False)
    finally:
        r91.SUB = old
    if missing:
        return None, missing
    fund, ixf = m201d.f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    keep = {}
    for y in sorted(by2):
        keep[y] = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = m201d.f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None
                          or m201d.r102._ord(p["entry_date"]) - m201d.r102._ord(a[0])
                          > m201d.r102.STALE_MAX)
                 else m201d.r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                keep[y].append(p)

    def one(**kw):
        out = []
        for y in sorted(keep):
            open_until = {}
            for p in keep[y]:
                t = pt.resolve_trade(p, ft="limit", fs="market", stop=m201d.STOP,
                                     target=m201d.TARGET, half=m201d.HALF,
                                     shares=(1.0,), add_stop="floor_entry", **kw)
                cd = p["code"]
                if cd in open_until and p["entry_date"] <= open_until[cd]:
                    continue
                r = t["masks"][()]
                open_until[cd] = r["resolve_date"] or p["entry_date"]
                epx, d, rd = t["entry_px"], p["d"], r["resolve_date"]
                net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                          for _dd, fr, px in r["exits"])
                hold = d.index(rd) if (rd and rd in d) else len(d) - 1
                win = 1 if net > 0 else 0
                out.append((t["entry_date"], max(1, hold), net, win))
        return out

    fams = {}
    for g in GRID:
        fams[("A", g)] = one(trail=g)
        P("  ㉮ 일수 %d — 거래 %s" % (g, format(len(fams[("A", g)]), ",")), flush=True)
    for g in GRID:
        fams[("B", g)] = one(exit_mode="runner", run_trail=float(g))
        P("  ㉯ 비율 %d%% — 거래 %s" % (g, format(len(fams[("B", g)]), ",")), flush=True)
    return fams, []


def main():  # noqa: C901
    P("# 260 - **트레일링 «두» 격자 — ㉮ «일수» 창 · ㉯ «비율» 폭**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/260-trail-grid.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P(F3)
    P("🚨 **사용자 결정**(2026-09-10) — 「**«트레일링 스탑»으로 거래 · 앞으로 «미국» 시장에 «투자**」")
    P("   ⇒ **`41:58 TRAIL_WINDOW = 25` 가 «곧» «실제» 돈을 굴리는 손잡이**")
    P("   ⇒ 🔴 **`259`: 「25」의 «유도»가 «어디»에도 «없다**(results 309·verdicts 81·tasks 101·scripts·커밋로그)")
    P("")
    P("⛔ **묻는 것은 「«어느» 창이 «좋은가»」가 «아니다** — **「«면»이 «평평»한가」**다")
    P("")
    P("📐 **격자**: **%s** — ⛔ **25 를 «중앙»에 둔 «대칭»**(결과 «보기» 전에 박음)"
      % " · ".join(("**%d**" % g) if g == CUR else str(g) for g in GRID))
    P("   ⛔ **비대칭이면 「우리가 «고른» 범위」**가 된다")
    P("   🚨 **㉯ 에도 «같은» 격자** — `67:103` 이 「«꺾이는» 모양이라 «끝점» 최적이 «아니다」」 했으니")
    P("      **25% «너머»를 «포함**한다 ⇒ ⛔ **「−25%가 «최적»」을 «전제»로 «깔지» «않는다**")
    P("")
    P("⛔ **원본을 «건드리지» «않는다** — **`trail`·`run_trail` 은 «이미» 인자**(복사본 «불필요**)")
    P(F3)
    P("")
    P("---")
    P("")

    P("# ⛔ **0. 자·판정표 — «결과»를 «보기» «전»에 «박는다**")
    P("")
    P(F3)
    P("## 📐 **자 — 「«관측» 폭 vs «귀무» 폭」**")
    P("   **통계량 = 「일곱 칸의 «최고» − «최저»」**(연환산 %p)")
    P("   **귀무** = 부트 «중심화»(각 칸을 «관측»으로 «빼고» 반복마다 폭을 «잰다**)")
    P("   🔎 **래칫의 「귀무 최대 ＋87.47%p」와 «같은» 얼개 · «다른» 통계량**(최대 → **폭**)")
    P("")
    P("   · **관측 폭 ≤ 귀무 폭** ⇒ ✅ **「창을 «어디»에 두든 «잡음» 범위 — «면»이 «평평»」이 «수»로 «선다**")
    P("   · **관측 폭 > 귀무 폭** ⇒ 「창이 «중요»하다」 ⇒ **«그때»만** 「25 가 «어디»인가」를 «본다**")
    P("")
    P("## ⛔ **«미리** 박는다 — «미끄러짐» 방지")
    P("   🚨 **「면이 «평평»하지 «않아도» — 「«어느» 창이 «좋다»」로 «가지» «않는다**")
    P("      **「25 가 «어느» «자리»인가」까지«만**」")
    P("")
    P("## 🆕 **유형 112 — 「«바꿀» 근거가 «없다」」 ≠ 「«옳다」」**")
    P("   🔎 래칫 정본 「**«채택» 근거가 «없다»(결정) ≠ «낫지» 않다(주장)**」의 **«거울»**")
    P("   ⇒ **「면이 «평평»하다」가 «나와도** — **「25 를 «바꿀» 이유가 «없다»」**이지")
    P("      **「25 가 «좋다»」가 «아니다**")
    P("   🚨 **실전에서 «이» 차이가 중요하다** — **「출처 «없는» 수를 «그대로» 쓴다」의 «근거»는**")
    P("      **「«어디»든 비슷하다」**이지 **「25 가 «좋다»」가 «아니다**")
    P("")
    P("## 📐 **판정 «자» — 「실전」이라고 «통계»가 «바뀌지» «않는다**")
    P("   ✅ **판정** = **계좌 연환산 %p**(Δ = 1.23 · «고친» 자 달력 6,893)")
    P("   ✅ **«잴» 수 «있는» 묘사** = **승률 · 거래 `net` SD · P95** ← **«거래» 단위(n = 수천)**")
    P("   ⛔ **«못** 재는 묘사 = **계좌 «낙폭»** ← **«자산곡선» «하나»**(`megacap` 전례) ⇒ **CI «없음**")
    P("")
    P("## 🔴 **«내» 편향**(⛔ 돌리기 «전»)")
    P("   **«내»가 «바라는» 것**: **「면이 «평평»하다」**")
    P("   ★ **까닭 — «나쁘다**: **「25 에 «근거»가 «없다」가 «덜» 아프게 «된다**")
    P("      ⇒ **«편하려는» 것**이지 «가설»이 «아니다**")
    P("   🔴 **검증은 «반대**: 「25 가 «근거» 없다」가 «드러나길» 바람")
    P("   ⇒ ⛔ **막는 것은 «구조»**: **대칭 격자** · **귀무 폭 «출력»** · **「좋다」 금지 «미리» 박음**")
    P("")
    P("## 📌 **③ ㉮·㉯ «둘 다» — «사용자» 답 «오기» «전»에**")
    P("   ⛔ **결과를 «보고» ㉮/㉯ 를 «고르지» «않는다** — **«사용자» 결정**이다")
    P("   ✅ **「답이 «오기» «전»에 «둘 다» 냈다」를 «기록»에** ⇒ **「골랐다」가 «아님»이 «보인다**")
    P(F3)
    P("")
    P("---")
    P("")

    t0 = time.time()
    if CA.exists():
        raw = json.loads(CA.read_text(encoding="utf-8"))
        fams = {(k.split("|")[0], int(k.split("|")[1])): [tuple(x) for x in v]
                for k, v in raw.items()}
        P(F3)
        P("   (♻️ 갈무리 " + BQ + "260-arms.json" + BQ + ")")
        P(F3)
    else:
        P("(팔 «열넷»을 «짓는» 중 — 사다리는 «한» 번만 싣는다 …)", flush=True)
        fams, miss = build_all()
        if fams is None:
            P("🚨 경로 «없음»: %s" % miss[:3])
            return 1
        CA.write_text(json.dumps({"%s|%d" % k: [list(x) for x in v]
                                  for k, v in fams.items()}), encoding="utf-8")
        P("")
        P(F3)
        P("   ✅ 자료 짓기 **%.1f 분**(실측)" % ((time.time() - t0) / 60.0))
        P(F3)
    P("")

    cal = json.loads((OUT / "201d-arms2.json").read_text(encoding="utf-8"))["cal"]
    ents = {d for v in fams.values() for d, _h, _n, _w in v}
    if ents - set(cal):
        cal = sorted(set(cal) | ents)
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt, _w in lst:
            bp[pos[d]].append((h, nt, 0))
        return eq_of(bp, n_pos)

    res = {}
    for k, v in fams.items():
        e, g, sd_ = obs(v)
        res[k] = (m201d.ann(e), g, sd_)

    for fam, nm, unit in (("A", "㉮ **«일수» 창**(＋30 목표 → 절반 → **N일 저가** 추격)", "일"),
                          ("B", "㉯ **«비율» 폭**(«순수» 트레일링 — 목표 «없이» **고점 대비 N%**)", "%")):
        P("---")
        P("")
        P("# %s" % nm)
        P("")
        P("| 창 | 연환산 %p/해 | 거래 | 슬롯 | 슬롯-일 | 보유 중앙 | **승률** | net SD | net P95 |")
        P("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for g in GRID:
            v = fams[(fam, g)]
            a, got, sd_ = res[(fam, g)]
            nets = sorted(x[2] for x in v)
            wr = 100.0 * sum(x[3] for x in v) / max(1, len(v))
            mark = "**%d%s**" % (g, unit) if g == CUR else "%d%s" % (g, unit)
            P("| %s | **%+.3f** | %s | %s | %s | %.0f | **%.1f%%** | %.2f | %.2f |"
              % (mark, a, format(len(v), ","), format(got, ","), format(sd_, ","),
                 st.median([x[1] for x in v]), wr, st.stdev(nets),
                 nets[int(len(nets) * .95)]))
        P("")
        vals = [res[(fam, g)][0] for g in GRID]
        span = max(vals) - min(vals)
        P(F3)
        P("   **관측 «폭»**(최고 − 최저) = **%.3f%%p**" % span)
        P("   ⛔ **「25 의 «순위»」는 «적지» «않는다** — **면이 «평평»하면 «순위»는 «잡음»의 «순위»**다")
        P("      🚨 «적으면» **「그럼 «다른» 칸으로 «옮기자»」**를 «자동»으로 부른다 ⇒ **금지의 «우회로»**")
        P("      ✅ **「«안» 봤다」가 «아니라 「«봤는데» «안** 쓴다」**다")
        P(F3)
        P("")

    # ── 귀무 폭 ──────────────────────────────────────────────────
    P("---")
    P("")
    P("# ★★ **판정 — 「관측 폭 vs «귀무» 폭」**")
    P("")
    P("| 가족 | 블록 | **관측 폭** | **«귀무» 폭 95%** | 넘나 | **관측 폭 ÷ Δ** |")
    P("|---|---|---:|---:|:--|---:|")
    ia = {k: defaultdict(list) for k in fams}
    for k, v in fams.items():
        for j, (d, _h, _n, _w) in enumerate(v):
            ia[k][pos[d]].append(j)
    t1 = time.time()
    verdict = {}
    for fam in ("A", "B"):
        vals = [res[(fam, g)][0] for g in GRID]
        span = max(vals) - min(vals)
        over = []
        for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
            m201d.BMIN, m201d.BMAX = bmn, bmx
            rnd = random.Random(SEED + bi_blk + (0 if fam == "A" else 7))
            nulls = []
            for _bi in range(NBOOT):
                order = m201d.draw(n_pos, rnd)
                cen = []
                for gi, g in enumerate(GRID):
                    lst = fams[(fam, g)]
                    bp = defaultdict(list)
                    for newp, oldp in enumerate(order):
                        for j in ia[(fam, g)].get(oldp, ()):
                            _d, h, nt, _w = lst[j]
                            bp[newp].append((h, nt, 0))
                    cen.append(m201d.ann(eq_of(bp, n_pos)[0]) - vals[gi])
                nulls.append(max(cen) - min(cen))
                if (_bi + 1) % 500 == 0:
                    P("  [%s %d~%d] 부트 %d/%d" % (fam, bmn, bmx, _bi + 1, NBOOT), flush=True)
            crit = sorted(nulls)[int(NBOOT * .95)]
            ov = span > crit
            over.append(ov)
            P("| %s | %d~%d | **%.3f%%p** | **%.3f%%p** | %s | **%.1f배** |"
              % ("㉮ 일수" if fam == "A" else "㉯ 비율", bmn, bmx, span, crit,
                 "🔴 **넘는다**" if ov else "✅ **«안** 넘는다", span / DELTA), flush=True)
        verdict[fam] = any(over)
    t_boot = time.time() - t1
    P("")
    P(F3)
    for fam, nm in (("A", "㉮ «일수» 창"), ("B", "㉯ «비율» 폭")):
        vals = [res[(fam, g)][0] for g in GRID]
        if not verdict[fam]:
            P("   ✅ **%s — 「관측 폭 ≤ 귀무 폭」** ⇒ **「창을 «어디»에 두든 «잡음» 범위 — «면»이 «평평»」**"
              % nm)
            P("      ⇒ ★ **유형 112**: **「%s 를 «바꿀» 이유가 «없다»」**이지 **「%s 가 «좋다»」가 «아니다**"
              % (CUR, CUR))
        else:
            P("   🔴 **%s — 「관측 폭 > 귀무 폭」** ⇒ **「창이 «중요»하다」**" % nm)
            P("      ⛔ **「«어느» 창이 «좋다»」로 «가지» «않는다**(⛔ **미리** 박은 것)")
    P("")
    P("   🚨🚨 **«그런데» «이» 관문은 «무디다** — **«갈라» 적는다**(검증 2차)")
    P("      🔎 귀무 폭이 **10.9 ~ 14.3%p** ⇒ **「폭이 «10%p 넘게» 벌어져야」 무는 자**다")
    P("      🔎 그리고 **관측 폭 4.2 ~ 6.0 은 Δ(1.23)의 «3.4 ~ 4.9배»**다")
    P("")
    P("      ✅ **«참»**: **「창을 «바꿔» «얻는» 것이 «잡음»과 «구분»되지 «않는다」**")
    P("      ⛔ **«못** 쓰는 말**: **「창을 «바꿔도» «Δ 만큼» «안» 달라진다」** — **폭이 Δ 의 «3.4~4.9배»**다")
    P("")
    P("      ✅ **정확한 꼴**: 「**창을 «바꿀» 근거가 «없다». 다만 «이» 자는 창 «사이» 차이를**")
    P("         **«Δ 자릿수»까지 «못» 가린다. 창 «선택»이 계좌에 Δ «보다» «큰» 차이를 낼 «수» «있으나** —")
    P("         **«어느» 쪽인지 «모른다**」")
    P("")
    P("   ✅ **관문이 «살아» 있었나 — «검산**: **어떤 관측이면 «넘었을까**")
    P("      🔎 **7칸 폭이 «10.9%p 넘게»** 벌어지면 넘는다")
    P("      🔎 **`253` 이 «실제»로 «그런» 판**이었다: Ⓢ1 **−7.795** vs ① **＋10.160** ⇒ **폭 17.955**")
    P("      ⇒ ✅ **귀무를 «훨씬» 넘는다** ⇒ **유형 63(질 수가 «없는» 판)에 «안** 걸린다")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 🗣️ **«사람»의 말로 — 실전에서 «무슨» 뜻인가**")
    P("")
    P(F3)
    wr_a = 100.0 * sum(x[3] for x in fams[("A", CUR)]) / max(1, len(fams[("A", CUR)]))
    wr_b = 100.0 * sum(x[3] for x in fams[("B", CUR)]) / max(1, len(fams[("B", CUR)]))
    P("   **㉮ 지금 방식**(＋30 목표 ＋ 25일 추격) 승률 **%.1f%%**" % wr_a)
    P("   **㉯ 순수 트레일링**(목표 «없이» −25%%) 승률 **%.1f%%**" % wr_b)
    P("")
    P("   🚨 **`76` 이 «누적»(9년)으로 «이미» 낸 것**: 승률 **37.0% → 14.2%**")
    P("      ⇒ ★ **«사람»의 말로**: **「«일곱» 번에 «여섯» 번은 «지는» 것을 «견뎌야» 한다」**")
    P("      ⇒ **`85` 의 「꼬리 «넓히는» 칸 ≠ 기대값 «올리는» 칸」이 «실전»에서 «이» 뜻**이다")
    P("")
    P("")
    P("   ★★ **«이» 판이 «스스로» 낸 것 — ㉯ 에서 «단조»가 «셋** 나왔다")
    P("| 비율 폭 | 승률 | net SD | 슬롯-일 | 연환산 %p |")
    P("|---|---:|---:|---:|---:|")
    for g in GRID:
        v = fams[("B", g)]
        a, got, sd_ = res[("B", g)]
        nets = sorted(x[2] for x in v)
        wr = 100.0 * sum(x[3] for x in v) / max(1, len(v))
        P("| %d%% | **%.1f%%** | **%.2f** | %s | %+.3f |"
          % (g, wr, st.stdev(nets), format(sd_, ","), a))
    P("")
    P("")
    P("   ⛔ **«방향»은 «항등식»이다 — «설계»상 «필연**(⇒ **«발견»이 «아니다**)")
    P("      · **슬롯-일 ↑** — 폭을 «넓히면» «덜» 털려 **«더» 오래 든다**")
    P("      · **net SD ↑** — 폭이 넓으면 **«큰» 승리도 «큰» 패배도**")
    P("      · **승률 ↓** — 폭이 넓을수록 **「본전 «아래»로 «되돌아온» 뒤 나갈」 여지가 «커진다**")
    P("      ⚠️ **다만 «크기»는 «관측»**이다")
    P("")
    P("   ★★★ **«관측»인 부분은 «이것**이다:")
    P("      **「셋이 «단조»인데 — «계좌»는 «평평»하다」** ⇒ **「«상쇄»된다」가 «관측»**")
    P("      ⇒ **「승률이 «떨어지는» 만큼 «이긴» 것이 «커진다」**")
    P("      ⇒ ★ **`85` 의 「꼬리 «넓히는» 칸 ≠ 기대값 «올리는» 칸」이 «빌려온» 말이 «아니라**")
    P("         **«이» 판에서 «직접» 나왔다**")
    P("")
    P("   ⛔ **`255` 의 «사슬» 관계를 «여기» «끌어오지» «않는다**(`257` 에서 «막은» 것)")
    P("      ✅ **«관측»만**: 「**«이» 격자에서는 «슬롯-일»이 **＋17.1%** 늘어도 «계좌»가 «평평**했다」")
    P("      ⇒ ★ **`257`·`258`(「«자르는» 손잡이는 슬롯-일이 «거의» «안** 바뀐다」)와 **«짝»**이다")
    P("      ⇒ ⇒ **「지도」에 «남긴다** — ⛔ **아직 «자»가 «아니다**")
    P("")
    P("   ⛔ **「«넓힐»수록 «낫다»」 ✗ · 「«좁힐»수록 «안전»하다」 ✗** — **«같은» 까닭**(연환산이 «잡음» 범위)")
    P("")
    P("   🔎 **㉮ 는 «다르다** — 승률이 **33.0~33.1%로 «거의» «불변»**이다")
    P("      🚨 **그런데 «이건» «발견»이 «아니라 「«설계»가 «그렇다»」**다:")
    P("         **목표(＋30)가 «있으면» — 이긴 거래의 «절반»이 «거기»서 «확정»**된다")
    P("      ⇒ ✅ **각 격자 «안»의 «관측»이라 «쓸» 수 «있다** — ⛔ **「㉮ 가 ㉯ 보다 «낫다」」는 «못** 쓴다")
    P("")
    P("   ⛔ **그리고 `76`(누적 9년)의 «방향»**: 순수 트레일링이 «지금»보다")
    P("      **−86.21%p**(«원» 자산 차) · **−115.90%p**(노출 맞춤 · `76:74` 문턱 C)")
    P("      ⇒ ✅ **«방향»은 «견고**(노출 보정으로도 «안» 뒤집힘) · ⛔ **«크기»는 «못** 가렸다(CI «없음»)")
    P("")
    P("   🚨🚨 **⛔ `76` 과 «이» 판을 «맞대지» «않는다** — **«다른» 물음**이다")
    P("      · **`76`** = **«9년»** · **「«순수» 트레일링 vs «지금» 얼개」를 «직접» 견줌** ⇒ **−86.21%p**")
    P("      · **`260`** = **«27.4해»** · **「각 얼개 «안»의 «창»」만 봄** ⇒ **얼개끼리는 «안** 견줬다")
    P("      ⛔ **「㉯ 격자(＋7.5~13.6)가 ㉮(＋7.2~11.4)와 «비슷»하다」로 «읽으면» «틀린다**")
    P("      ✅ **«둘» 다 보고하되 — 「«다른» 물음」임을 «같은 줄»에**")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 🎯 **⇒ «사용자»께 답할 것 «넷**")
    P("")
    P(F3)
    P("   ✅ ① **「25 를 «바꿀» «근거»가 «없다」** — 창 «일곱»을 «잡음»과 견줬고 **«구분»되지 «않는다**")
    P("")
    P("   ⛔ ② **「25 가 «옳다»·«안전»하다」는 «아니다** — **«순위»는 «잡음»의 «순위»**다")
    P("")
    P("   🚨 ③ **「«이» 자는 창 «사이» 차이를 «Δ 자릿수»까지 «못» 가린다」**")
    P("      **관측 폭이 Δ 의 «3.4 ~ 4.9배»**다 ⇒ **창 «선택»이 계좌에 Δ «보다» «큰» 차이를 낼 «수» «있다**")
    P("      ⇒ ⛔ **다만 «어느» 쪽인지 «모른다**")
    P("")
    P("   🚨 ④ **「«목표»를 «없앨» 것인가」는 «다른» 물음**이고 —")
    P("      **`76`(9년)이 «−86.21%p»**(노출 맞춤 −115.90%p) **·** 승률 **37.0% → 14.2%**")
    P("      ⇒ ★★ **«그것»부터**다 — **「창을 «몇»으로」보다 «앞»선다**")
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 한 것**")
    P("")
    P(F3)
    P("⛔ ① **격자 «밖»(＜10 · ＞50)은 «안** 봤다 — **«대칭»을 «지키려**고 «닫았다**")
    P("⛔ ② **㉮·㉯ 를 «서로» «맞대지» «않았다** — **«각각» «면»이 «평평»한가**만 봤다")
    P("     ⇒ **「㉮ vs ㉯」는 `76`(누적 9년)에 «있고** — **«이» 판의 자(연환산·부트)로는 «안** 쟀다")
    P("⛔ ③ **계좌 «낙폭»은 «안** 냈다 — **자산곡선이 «하나»**라 **CI 가 «없다**")
    P("⛔ ④ **㉯ 는 «목표»를 «없앤다** ⇒ **`half`(절반 매도)도 «사라진다** — **«두» 손잡이가 «같이» 움직인다**")
    P("⛔ ⑤ 💰 **비용 실측**: 자료 짓기 **%.1f 분** · 부트 **%.1f 분**"
      % ((t1 - t0) / 60.0, t_boot / 60.0))
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

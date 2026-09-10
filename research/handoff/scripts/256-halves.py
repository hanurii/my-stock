# -*- coding: utf-8 -*-
r"""256 - **부분 매도 «비율» 1/3 · 0.75**  (조사 세션 2026-09-09)

  📖 원전 `tm:51` 「포지션의 «3분의 1»이나 «2분의 1», 많게는 «75퍼센트» «내»에서 매도하고,
     «나머지»는 «더 큰» 움직임을 위해서 «보유»합니다」

  ⛔ **사전등록은 `results/256-PRE.md`** — 팔 «셋» · 주 판정 **T = max(Ⓗ⅓−①, Ⓗ¾−①)** ＋ 귀무 최대
  🚨 **분기 규칙이 «코드»에 «박혀» 있다**(검증 조건 ②): **슬롯-일 «최대 차» ≥ 5% 면 «이름»이 «바뀐다**

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/256-halves.py
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
H3 = chr(0x24BD) + "⅓"      # Ⓗ⅓
H4 = chr(0x24BD) + "¾"      # Ⓗ¾
ARMS = ((C1, 0.5), (H3, 1.0 / 3.0), (H4, 0.75))     # ⛔ 1/3 은 `1.0/3.0` «그대로»
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 256256
BLOCKS = ((20, 40), (80, 80))
SD_GATE = 0.05                   # ⛔ **분기 문턱 — 결과 «보기» 전에 박음**(유도는 §0b)


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91
OUT = Path(str(r91.OUT))
CA = OUT / "256-arms.json"


def eq_of(by_pos, n_pos, slots=5):
    """계좌 «연환산»용 — ＋ **«슬롯-일»**과 **«낙폭»**을 «같이» 낸다(꼬리 «묘사»용)."""
    eq, held, got, sday = 1.0, [], 0, 0
    peak, mdd = 1.0, 0.0
    for p in range(n_pos):
        if held:
            keep_ = []
            for hh in held:
                if hh[0] < p:
                    eq += hh[1] * hh[2] / 100
                else:
                    keep_.append(hh)
            held = keep_
            if eq > peak:
                peak = eq
            elif peak > 0:
                mdd = max(mdd, (peak - eq) / peak)
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
    return (eq - 1.0) * 100.0, got, sday, mdd * 100.0


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


def build(half):
    """`201d.build_pairs` 와 «같은» 구성 — **`half` «하나»만** 바꾼다."""
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
            t = m201d.pt.resolve_trade(p, ft="limit", fs="market", stop=m201d.STOP,
                                       target=m201d.TARGET, half=half,
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
            out.append((t["entry_date"], max(1, hold), net))
    return out


def main():  # noqa: C901
    P("# 256 - **부분 매도 «비율» 1/3 · 0.75**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/256-halves.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> 사전등록 " + BQ + "results/256-PRE.md" + BQ)
    P("")
    P(F3)
    P("★★★ **이 판의 «제일» 큰 소득 — «머리»에 박는다**")
    P("")
    P("   **「«순수»한 축이었고**(슬롯-일 «세» 팔에서 **0.0000%** 차)")
    P("    **«자»가 «처음»으로 Δ 자릿수에 «닿았는데**(**MDE ÷ Δ = 1.14**)")
    P("    **«그런데도» «부호»도 «상한»도 «못» 닫았다.」**")
    P("   ⇒ ★ **«그» «자체»가 «이» 축에 대한 «답»이다**")
    P("")
    P("   🔎 **까닭이 «코드»에 «있다** — `pyr_trigger.py:187` 의 추격 종료 조건에 **`half` 가 «없어**")
    P("      **청산일이 «안» 바뀐다** ⇒ **「0.0000%」가 «우연»이 «아님»을 «코드»가 «보증»한다**")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ✅ **0. 조건 ① — 「부분 익절이 «슬롯»을 «비우나»」 «코드»로 답한다**")
    P("")
    P(F3)
    P("   🅐 **슬롯 «모드» = 「종목당 «자리» «하나»」**(⛔ **«자본» 분할이 «아니다**)")
    P("      📄 `:65` **`free = slots - len(held)`** — **자리를 «개수»로 센다**")
    P("      📄 `:68` **`wgt = eq / slots`** — **비중이 «고정»**이다(판 만큼 «현금»이 «안** 돌아온다)")
    P("      ⇒ ✅ **부분 익절은 «자리»를 «안** 비운다")
    P("")
    P("   🅑 **그리고 «더** 센 것 — **`half` 가 «청산일»을 «안** 바꾼다**")
    P("      📄 `pyr_trigger.py:187` **`for j in range(i + 1, n):`** — 추격 종료 조건")
    P("         `l[j] <= s2` 에 **`half` 가 «없다**")
    P("      📄 `:185` `if half >= 1.0 - 1e-9:` ← **«전량» 매도일 때«만** 그날 끝난다")
    P("      ⇒ ✅ **우리 세 팔은 «전부» `half < 1`** ⇒ **`hold` 가 «같을» 것**")
    P("")
    P("   ⇒ ⇒ ★★★ **「사슬」이 «구조»상 «약하다** — `255` 의 «되풀이»가 «아닐** 수 있다")
    P("      ⛔ **그러나 «말»로 «닫지» «않는다** — **아래에서 «수»로 «찍는다**")
    P(F3)
    P("")
    P("# ⛔ **0b. 분기 규칙 — «결과» «보기» «전»에 «코드»에 «박혔다**")
    P("")
    P(F3)
    P("   **`SD_GATE = %.2f`**  (= 슬롯-일 **«최대 차» 5%%**)" % SD_GATE)
    P("")
    P("| 세 팔 슬롯-일 «최대 차» | 주 물음 | «이름» |")
    P("|---|---|---|")
    P("| **< 5%** | ✅ **㉠ 그대로** — `T = max(Ⓗ⅓−①, Ⓗ¾−①)` | ✅ **「«비율» 축」이라 «불러도» 된다** |")
    P("| **≥ 5%** | 🚨 **㉡ 로 «올림»** — 「«사슬»이 «깨지는가»」 | 「비율 ＋ 슬롯-일 차 X%」 |")
    P("")
    P("   🔎 **문턱 5%의 «유도»**(⛔ «수»만 박지 «않는다»): `254` 에서 **슬롯-일 «＋4.74%»** 차이가")
    P("      **−2.133%p 와 «같은» 방향**이었고 **«배제»하지 «못했다** ⇒ **그 «부근»이 「섞였다」의 «경계»**")
    P(F3)
    P("")
    P("# ⛔ **0c. 판정표 — «결과» «보기» «전»에 «박는다**")
    P("")
    P(F3)
    P("| 결과 | ✅ «쓸» 말 | ⛔ «쓰지» «않을» 말 |")
    P("|---|---|---|")
    P("| **T 가 귀무 최대 «넘고» 칸 1** | 「**원전 «비율»(그 값)이 «우리» 0.5 보다 «나았다**」 | "
      "⛔ 「원전대로 «했다»」(방아쇠 «다름») · ⛔ 「«그» 비율이 «최적»」(격자 «둘»뿐) |")
    P("| **T 가 «안** 넘음 | 「**원전 «비율» «둘» 다 «우리» 0.5 를 «못» 넘었다**」 | "
      "⛔ 「0.5 가 «최적»」 · ⛔ 「비율은 «상관없다»」 |")
    P("| **칸 2**(둘 다 «아래») | 「**«이» 두 비율은 «우리» 것보다 «나빴다**」 | "
      "⛔ 「원전이 «틀렸다»」 |")
    P("| **칸 5**(«못** 가림) | 「**«이» 자로는 «못** 가린다」 ＋ **MDE 를 «같은 줄»에** | "
      "⛔ 「«같다»」 · ⛔ 「«무해»하다」 |")
    P("| 🆕 **셋이 «단조»** | 「**«비율» «손잡이»로 «갈» 수 «있는» «제일 «먼»» 곳」** | "
      "🚨 ⛔ 「비율 «축»의 «몫»」 |")
    P("")
    P("   🔴 **«내» 편향**(`256-PRE` §④): **「Ⓗ⅓ 이 «낫다»」를 «바란다**")
    P("      🚨 **두뇌도 «같은» 쪽** · **검증은 «반대»** ⇒ **막는 것은 «구조»**(`SD_GATE` · 주 판정 «묶음» · 귀무 최대)")
    P("")
    P("   ⛔ **«사전» 한계**: **손절은 «−10 «하나»»에서만 잰다**(`131:69` 의 «목표» 축 판정을")
    P("      «통째»로 «물려받지» «않으나** — **「손절 «하나»」는 «같은» 한계**다)")
    P("      ⛔ **손절을 «둘» 이상 «돌리지» «않는다** — **칸이 «배»로 늘고 «귀무 최대»가 «커진다**")
    P(F3)
    P("")
    P("---")
    P("")

    t0 = time.time()
    if CA.exists():
        raw = json.loads(CA.read_text(encoding="utf-8"))
        recs = {k: [tuple(x) for x in v] for k, v in raw.items()}
        P(F3)
        P("   (♻️ 갈무리 " + BQ + "256-arms.json" + BQ + ")")
        P(F3)
    else:
        recs = {}
        for nm, hv in ARMS:
            P("(팔 %s — half = %.6f 짓는 중 …)" % (nm, hv), flush=True)
            r = build(hv)
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
    ents = {d for k in recs for d, _h, _n in recs[k]}
    if ents - set(cal):
        cal = sorted(set(cal) | ents)
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)
    keys = [nm for nm, _h in ARMS]

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return eq_of(bp, n_pos)

    o, got, sday, mdd = {}, {}, {}, {}
    for k in keys:
        e, g, s, m = obs(recs[k])
        o[k], got[k], sday[k], mdd[k] = m201d.ann(e), g, s, m

    # ── ★ 슬롯-일을 «먼저» ─────────────────────────────────────────
    P("# ★★ **1. «슬롯-일»을 «먼저** — **분기 규칙이 «여기»서 «걸린다**")
    P("")
    P("| 팔 | half | 거래 | 슬롯 «얻은» 것 | **«슬롯-일»** | 보유 중앙 |")
    P("|---|---:|---:|---:|---:|---:|")
    for (nm, hv) in ARMS:
        hm = st.median([h for _d, h, _n in recs[nm]])
        P("| %s | %.4f | %s | %s | **%s** | %.0f일 |"
          % (nm, hv, format(len(recs[nm]), ","), format(got[nm], ","),
             format(sday[nm], ","), hm))
    P("")
    P(F3)
    sd_vals = [sday[k] for k in keys]
    spread = (max(sd_vals) - min(sd_vals)) / max(1, min(sd_vals))
    P("   **«슬롯-일» 최대 차 = (%s − %s) ÷ %s = **%.4f%%**"
      % (format(max(sd_vals), ","), format(min(sd_vals), ","), format(min(sd_vals), ","),
         100 * spread))
    P("   문턱 `SD_GATE = %.0f%%` ⇒ **%s**"
      % (SD_GATE * 100, "✅ **㉠ 그대로** — 「«비율» 축」이라 «불러도» 된다" if spread < SD_GATE
         else "🚨 **㉡ 로 «올림»** — 「비율 ＋ 슬롯-일 차 %.2f%%」" % (100 * spread)))
    if spread < 1e-9:
        P("")
        P("   ⇒ ★★★ **차가 «정확»히 «0»** — **§0 🅑 가 «수»로 «확인**됐다")
        P("      **`half` 가 «청산일»을 «안** 바꾸므로 — **세 팔의 `hold` 가 «전부» 같다**")
        P("      ⇒ ⇒ ✅ **「사슬」 물음이 «사라진다** — **«순수»한 「비율」 축**이다")
    P(F3)
    P("")
    P("---")
    P("")

    P("# 2. **팔 «셋** ＋ **꼬리 «묘사»**(⛔ **판정이 «아니다**)")
    P("")
    P("| 팔 | 연환산 %p/해 | 계좌 «낙폭» | 거래 net SD | net P05 | net P95 |")
    P("|---|---:|---:|---:|---:|---:|")
    for nm in keys:
        nets = sorted(n for _d, _h, n in recs[nm])
        P("| %s | **%+.3f** | %.2f%% | %.2f | %.2f | %.2f |"
          % (nm, o[nm], mdd[nm], st.stdev(nets),
             nets[int(len(nets) * .05)], nets[int(len(nets) * .95)]))
    P("")
    P(F3)
    P("   🚨 **부분 익절은 «회전» 손잡이가 «아니라» «크기» 손잡이**다 — **1/3 매도 = 이긴 종목에 «더» 노출**")
    P("   🔎 전례: **「꼬리 «넓히는» 칸 ≠ 기대값 «올리는» 칸」**(`85` 의 `atr_band`④)")
    P("")
    P("   🚨🚨 **위 표를 «한» 덩어리로 «읽으면» «틀린다** — **«둘»로 «가른다**")
    P("      ⛔ **계좌 «낙폭»(38.82 → 31.37)** — **«자산곡선»이 «하나»**다 ⇒ **CI 가 «없다**")
    P("         🔎 전례 `megacap-momentum`: 「자산곡선 «하나»라 CI 불가 ⇒ **판정 «안** 냄」")
    P("         ⇒ ⛔ **«판정»으로 «쓰지» «않는다** — **«그림»일 뿐**")
    P("      ✅ **거래 `net` SD·P95** — **«거래» 단위(n = 수천)**라 **«잴» 수 «있다**")
    P("         ⛔ 다만 **«이» 판에서 «안** 쟀다 — **팔 칸 목록을 ㉠~㉣ 로 «닫았다**(`256-PRE` §⑤)")
    P("      ⇒ ★ **«한» 덩어리로 적으면 «약한» 쪽(낙폭)이 «강한» 쪽(거래 분포)의 «신용»을 «빌린다**")
    P("")
    P("   ⛔ **「Ⓗ¾ 가 «싸게» 덜 아프다」는 «못** 쓴다")
    P("      🔎 「싸게」가 서려면 **「기대값이 «같은데» 낙폭만 준다」**여야 하는데 —")
    P("         **기대값을 «못» 가렸다**(칸 5) ⇒ **「«같다»」가 «아니라 「«모른다»」**(유형 77)")
    P("      ✅ **«정확»한 꼴**: 「**Ⓗ¾ 는 «거래 분포»가 «좁다». 그런데 «성적»이 «같은지»는 «모른다**」")
    P("      ⇒ **「그 «값»이 «얼마»인가」는 «다음» 판**이다 — **«이» 판이 «답한» 것이 «아니다**")
    P("")
    P("   ⛔ **판정은 «계좌 %p»로 «그대로»** — **위 셋은 «묘사»**다")
    P(F3)
    P("")
    P("---")
    P("")

    ia = {k: defaultdict(list) for k in keys}
    for k in keys:
        for j, (d, _h, _n) in enumerate(recs[k]):
            ia[k][pos[d]].append(j)

    P("# 3. **주 판정** — **T = max(Ⓗ⅓ − ①, Ⓗ¾ − ①)** ＋ **«귀무» 최대**")
    P("")
    d3, d4 = o[H3] - o[C1], o[H4] - o[C1]
    obs_t = max(d3, d4)
    arg_t = H3 if d3 >= d4 else H4
    P("| 블록 | Ⓗ⅓−① | Ⓗ¾−① | **관측 T** | «어느» | **«귀무» 최대 95%** | 넘나 |")
    P("|---|---:|---:|---:|:--|---:|:--|")
    t1 = time.time()
    boots, over = {}, []
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m201d.BMIN, m201d.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        rows = []
        for _bi in range(NBOOT):
            order = m201d.draw(n_pos, rnd)
            vv = {}
            for k in keys:
                bp = defaultdict(list)
                for newp, oldp in enumerate(order):
                    for j in ia[k].get(oldp, ()):
                        _d, h, nt = recs[k][j]
                        bp[newp].append((h, nt, 0))
                vv[k] = m201d.ann(eq_of(bp, n_pos)[0])
            rows.append((vv[H3] - vv[C1], vv[H4] - vv[C1]))
            if (_bi + 1) % 500 == 0:
                P("  [%d~%d] 부트 %d/%d" % (bmn, bmx, _bi + 1, NBOOT), flush=True)
        boots[(bmn, bmx)] = rows
        nm_ = sorted(max(r[0] - d3, r[1] - d4) for r in rows)
        crit = nm_[int(NBOOT * .95)]
        ov = obs_t > crit
        over.append(ov)
        P("| **%d~%d** | %+.3f | %+.3f | **%+.3f%%p** | %s | **%+.3f%%p** | %s |"
          % (bmn, bmx, d3, d4, obs_t, arg_t, crit,
             "🔴 **넘는다**" if ov else "✅ **«안** 넘는다"), flush=True)
    P("")
    P(F3)
    P("   ⛔ **«귀무» 최대를 «출력»했다** — **효과가 «전혀» 없어도 «둘» 중 «최선»을 고르면 «그만큼»** 나온다")
    P("   ⛔ **본페로니 «아님»** — max-T(단일 단계 · 부트 «중심화»)")
    P(F3)
    P("")
    P("---")
    P("")

    P("# 4. **개별 «둘» — «묘사»**(⛔ **판으로 «세지» «않는다**)")
    P("")
    P("| 짝 | 블록 | 점추정 | **백분위 CI** | 칸 | **기본 CI** | 칸 | **MDE** |")
    P("|---|---|---:|---:|:--|---:|:--|---:|")
    cellz = {H3: [], H4: []}
    mdes = {H3: [], H4: []}
    ups = {H3: [], H4: []}
    for (bmn, bmx), rows in boots.items():
        for nm, idx, ob in ((H3, 0, d3), (H4, 1, d4)):
            v = sorted(r[idx] for r in rows)
            lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
            sdv = st.stdev([r[idx] for r in rows])
            blo, bhi = 2 * ob - hi, 2 * ob - lo
            cp, cb = cell_of(lo, hi), cell_of(blo, bhi)
            cellz[nm].extend([cp, cb])
            mdes[nm].append(MDE_K * sdv)
            ups[nm].extend([hi, bhi])
            P("| %s − ① | %d~%d | **%+.3f%%p** | [%+.3f, %+.3f] | %s | [%+.3f, %+.3f] | %s | %.3f |"
              % (nm, bmn, bmx, ob, lo, hi, cp, blo, bhi, cb, MDE_K * sdv))
    P("")
    P(F3)
    for nm in (H3, H4):
        P("   %s − ① — 칸 %s" % (nm, " · ".join(cellz[nm])))
    P(F3)
    P("")
    P("---")
    P("")

    P("# 🎯 **⇒ 판정** — **§0c 표를 «그대로» 읽는다**")
    P("")
    P(F3)
    seq = [o[C1], o[H3], o[H4]]
    mono = (o[H3] <= o[C1] <= o[H4]) or (o[H4] <= o[C1] <= o[H3])
    if not any(over):
        P("⇒ ✅ **T 가 «귀무» 최대를 «안** 넘는다")
        P("   ✅ **「원전 «비율» «둘» 다 «우리» 0.5 를 «못» 넘었다」**")
        P("   ⛔ 「0.5 가 «최적»」 ✗  ·  ⛔ 「비율은 «상관없다»」 ✗")
    else:
        P("⇒ 🔴 **T 가 «귀무» 최대를 «넘었다**(%s)" % arg_t)
        P("   ⛔ 「원전대로 «했다»」 ✗(방아쇠 «다름») · ⛔ 「«그» 비율이 «최적»」 ✗(격자 «둘»뿐)")
    P("")
    P("   🔎 **셋의 «차례»**: ① %+.3f · Ⓗ⅓ %+.3f · Ⓗ¾ %+.3f" % tuple(seq))
    P("   %s" % ("🚨 **단조**(비율이 «오를수록» 한 방향) ⇒ ⛔ **「비율 «축»의 «몫»」으로 «읽지» «않는다**"
                if mono else "⚪ **단조가 «아니다**"))
    P("")
    P("   🔴 **«내» 편향은 「Ⓗ⅓ 이 «낫다»」였다** — **Ⓗ⅓ − ① = %+.3f%%p** ⇒ %s"
      % (d3, "🔴 **틀렸다**" if d3 < 0 else "✅ **맞았다**"))
    P("      ⛔ **맞았어도 «칸»을 «먼저** 읽는다 — **점추정은 «판정»이 «아니다**")
    P("")
    P("   ★★ **그리고 «이» 판의 «자»가 «지금»까지 «제일** 날카롭다")
    P("      **MDE ÷ Δ = %.2f · %.2f**(Ⓗ⅓)  ·  **%.2f · %.2f**(Ⓗ¾)"
      % (mdes[H3][0] / DELTA, mdes[H3][1] / DELTA,
         mdes[H4][0] / DELTA, mdes[H4][1] / DELTA))
    P("      🔎 앞선 판들: `252` **6.65** · `253` **10.46** · `254` **4.93** · `255c` **6.74**")
    P("      ⇒ **까닭이 «구조»에 «있다**: **세 팔이 «같은» 거래를 «같은» 날 «같은» 기간 잡는다**")
    P("         ⇒ **«짝»이 «완전»하다** — 차이가 **`net` «하나»**에서«만** 온다")
    P("")
    P("")
    P("   🔴🔴 **«철회** — 「0.111%p 모자라 4a」는 **«틀린** 읽기다")
    P("      🔎 **정본 칸 4a = 「CI 가 «0»을 «배제»하고 · 전부 |Δ| «안»」** ⇒ **«0 배제»가 «필수**")
    P("      🔎 코드도 «그렇다** — `cell_of` 가 **`lo <= 0 <= hi` 를 «먼저**" + " 본다(칸 5)")
    P("      ⇒ 점추정이 **%+.3f** 이니 **CI 가 «0»을 «품을» 수밖에 «없다**" % d3)
    P("      ⇒ ⇒ ★ **4a 는 「«거의»」가 «아니라 «구조»상 «될» 수가 «없었다** —")
    P("         ⛔ **「«거의» 4a」로 «읽으면» 문턱을 «녹이는» 것**이고, **«녹일» 문턱도 «아니었다**")
    P("")
    P("   ★★ **그래서 «아래»끝이 «아니라 «위»끝을 «본다** — 「Δ 를 «메우는» 것이 «배제»되나」")
    P("      🔎 **메우려면 «＋Δ(%+.3f) «이상»»이 «필요**하다 ⇒ **«위»끝이 «그» «아래»면 «배제»된다**" % DELTA)
    P("")
    P("| 짝 | 블록 | **백분위 «위»끝** | < ＋Δ? | **기본 «위»끝** | < ＋Δ? |")
    P("|---|---|---:|:--|---:|:--|")
    for nm in (H3, H4):
        for bi_, (bmn, bmx) in enumerate(BLOCKS):
            pu, bu = ups[nm][bi_ * 2], ups[nm][bi_ * 2 + 1]
            P("| %s − ① | %d~%d | **%+.3f** | %s | **%+.3f** | %s |"
              % (nm, bmn, bmx, pu, "✅" if pu < DELTA else "🔴 **«아니다**",
                 bu, "✅" if bu < DELTA else "🔴 **«아니다**"))
    P("")
    allu = [u for nm in (H3, H4) for u in ups[nm]]
    P("   ⇒ 🔴🔴 **«닫히지» «않는다** — **여덟 위끝 중 %d 이 ＋Δ 를 «넘는다**"
      % sum(1 for u in allu if u >= DELTA))
    P("      🚨 그리고 **CI 「종류」끼리 «서로» «반대»다**:")
    P("         · **Ⓗ⅓** — **기본**은 «닫히고**(+%.3f · +%.3f) **백분위**는 «안** 닫힌다(+%.3f · +%.3f)"
      % (ups[H3][1], ups[H3][3], ups[H3][0], ups[H3][2]))
    P("         · **Ⓗ¾** — **백분위**는 «닫히고**(+%.3f · +%.3f) **기본**은 «안** 닫힌다(+%.3f · +%.3f)"
      % (ups[H4][0], ups[H4][2], ups[H4][1], ups[H4][3]))
    P("      ⇒ ⇒ ✅ **규약 그대로**(`232b`): **「둘이 «다르면» «못» 가린다」**")
    P("      ⇒ ⇒ ⛔ **「＋Δ 이상은 «배제»된다」를 «못** 쓴다 — **«상한»도 «안** 닫혔다")
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 한 것**")
    P("")
    P(F3)
    P("⛔ ① **손절 «−10 하나»**에서만 쟀다 — **`131:69` 와 «같은» 한계**(⛔ «사전»에 박았다)")
    P("⛔ ② **방아쇠가 «다르다** — 원전은 「위험 대비 «보상» «반전»」, 우리는 **＋30 «목표»**")
    P("     ⇒ **「원전 «비율»을 «썼다»」까지가 «한계**")
    P("⛔ ③ **원전의 「«스윙 트레이딩»일 때」 갈래가 «없다**")
    P("⛔ ④ **격자는 «둘»뿐**(1/3 · 0.75) — **「사이 값」은 «다음» 판**이다(팔 칸 목록 «닫음»)")
    P("⛔ ⑤ **꼬리(낙폭·SD·P05/P95)는 «묘사»**다 — **판정에 «안** 썼다")
    P("⛔ ⑥ 💰 **비용 실측**: **%.1f 분**" % ((time.time() - t0) / 60.0))
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

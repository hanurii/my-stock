# -*- coding: utf-8 -*-
r"""231b — **`mk:65` 「20/50일 이평 «풀백» 매수」 — 판정** · 🔴 사용자 결정 2026-09-08

  ⛔ **사전등록은 `results/231-PRE.md` 에 «먼저» 박았다**(경로가 «도는» 동안).
     ① Ⓟ 가 «위» → 「풀백 매수가 «일한다」  ② «아래» → 「풀백 매수가 «해»다」
     ③ «못» 가림 → §B 가 「«안» 쟀다」→「봤는데 «못» 가렸다」

  📐 **팔** — ① 돌파«만»  vs  Ⓟ 돌파 **＋** 풀백(**«더하는» 쪽**)

  🚨 **«우리»가 «정한» 것 «넷»**(원전에 «없다» — `231-PRE.md` §1):
     ㉢ 「후퇴」 = **저가 ≤ SMA ∧ 직전 저가 > SMA**(= «닿는» 첫 봉)
     ㉤ 「«다시» 상승」 = **그날 종가 > 시가**(양봉)
     ㉦ 체결가 = **그날 «종가»**
     ㉧ 기한 = 돌파 «후» **60 봉** 안

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/231b-pullback-judge.py
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
NBOOT, SEED = 2000, 231231
BLOCKS = ((20, 40), (80, 80))
DELTA, MDE_K = 1.23, 2.8016
WARM = Path("D:/stock-data/uspath-warm2")

MAS = (20, 50)          # ㉡ 원전: 「20일 «또는» 50일」
MAX_TOUCH = 2           # ㉣ 원전: 「«처음» 또는 «두» 번째」
HORIZON = 60            # ㉧ 🔴 «우리»가 «정한» 것
PRE_UP = "**Ⓟ 가 «위»로 갈라지면** → 「**풀백 매수가 «일한다**」 ⇒ **원전 쪽이 «맞다**"
PRE_DN = "**Ⓟ 가 «아래»로 갈라지면** → 「**풀백 매수가 «해»다**」 ⇒ **돌파만 사는 «지금»이 «낫다**"
PRE_NO = ("**«못» 가리면** → 「**«넣어도» «못» 가린다**」 ⇒ "
          "**§B 가 「«안» 쟀다」에서 「봤는데 «못» 가렸다」로 «바뀐다**")


def c(s):
    return BQ + s + BQ


def _sma(seq, n, i):
    """seq[i] 를 «끝»으로 하는 n 봉 단순이동평균. 모자라거나 None 이 있으면 None."""
    if i + 1 < n:
        return None
    w = seq[i + 1 - n:i + 1]
    if any(x is None for x in w):
        return None
    return sum(w) / n


def pullbacks(p):
    """돌파 «뒤» 풀백 진입 «후보»를 «최대» MAX_TOUCH 개 낸다.

    ㉢ 「후퇴」 = 저가 ≤ SMA ∧ «직전» 봉 저가 > SMA   (🔴 «우리» 정의)
    ㉤ 「«다시» 상승」 = 그날 종가 > 시가              (🔴 «우리» 정의)
    ㉦ 체결가 = 그날 «종가»                            (🔴 «우리» 정의)
    ㉧ 기한 = 돌파 «후» HORIZON 봉                     (🔴 «우리» 정의)
    """
    pc, po, ph, pl = p.get("pre_c"), p.get("pre_o"), p.get("pre_h"), p.get("pre_l")
    if not pc or not p.get("c"):
        return []
    C = list(pc) + list(p["c"])
    O = list(po or []) + list(p["o"])
    L = list(pl or []) + list(p["l"])
    D = list(p.get("pre_d") or []) + list(p["d"])
    k0 = len(pc)                     # 진입(돌파)일의 «자리»
    out, touched = [], 0
    for i in range(k0 + 1, min(k0 + 1 + HORIZON, len(C))):
        if C[i] is None or O[i] is None or L[i] is None:
            continue
        hit = False
        for n in MAS:
            s0, s1 = _sma(C, n, i), _sma(C, n, i - 1)
            if s0 is None or s1 is None or L[i - 1] is None:
                continue
            if L[i] <= s0 and L[i - 1] > s1:        # ㉢ «닿는» 첫 봉
                hit = True
                break
        if not hit:
            continue
        touched += 1
        if touched > MAX_TOUCH:                     # ㉣ «처음»/«두» 번째만
            break
        if C[i] > O[i]:                             # ㉤ «다시» 상승(양봉)
            out.append((D[i], i - k0, round(C[i], 4)))   # (날짜, 진입 «뒤» 몇 봉, 종가)
    return out


def build():
    """① 돌파«만» · Ⓟ 돌파 ＋ 풀백. `227b`·`229` 와 **«한 글자»도 «다르지» 않은** 얼개."""
    old = r91.SUB
    r91.SUB = WARM
    try:
        (_a, _b, by2), missing, _ = r91.load_ladder(
            YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    finally:
        r91.SUB = old
    if missing:
        return None, None, None
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    base, extra = [], []
    n_pb_raw = 0
    for y in sorted(by2):
        open_until = {}
        cand = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None
                          or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is False:
                continue
            cand.append(p)
        # ── ① 돌파 진입 ──
        for p in cand:
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
            base.append((t["entry_date"], max(1, hold), net))
        # ── Ⓟ 의 «덧붙는» 풀백 진입 ──
        ou2 = dict(open_until)
        for p in cand:
            pbs = pullbacks(p)
            n_pb_raw += len(pbs)
            for pdate, off, px in pbs:
                cd = p["code"]
                if cd in ou2 and pdate <= ou2[cd]:
                    continue
                q = dict(p)
                q["d"] = p["d"][off:]
                q["o"] = p["o"][off:]
                q["h"] = p["h"][off:]
                q["l"] = p["l"][off:]
                q["c"] = p["c"][off:]
                q["entry_date"] = pdate
                q["entry_price"] = px
                q["pivot"] = px
                if len(q["d"]) < 2:
                    continue
                t2 = pt.resolve_trade(q, ft="limit", fs="market", stop=STOP, target=TARGET,
                                      half=HALF, shares=(1.0,), add_stop="floor_entry")
                r2 = t2["masks"][()]
                ou2[cd] = r2["resolve_date"] or pdate
                epx = t2["entry_px"]
                net = sum(fr * r91.sl.net(round(x / epx * 100 - 100, 2))
                          for _d, fr, x in r2["exits"])
                rd2 = r2["resolve_date"]
                hold = q["d"].index(rd2) if (rd2 and rd2 in q["d"]) else len(q["d"]) - 1
                extra.append((pdate, max(1, hold), net))
    return base, extra, n_pb_raw


def main():          # noqa: C901
    n_have = len(list(WARM.glob("uspath_*.json")))
    P("# 231b — **20/50일 이평 «풀백» 매수**")
    P("")
    P("> 조사 세션 · " + c("research/handoff/scripts/231b-pullback-judge.py")
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **사전등록은 " + c("results/231-PRE.md") + " 에 «먼저» 박았다**")
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
    P("**팔** ① 돌파«만»  vs  Ⓟ 돌파 **＋** 풀백(**«더하는» 쪽** — 원전이 `mk:53`·`mk:65` 로 **«둘» 다** 말함)")
    P("")
    P("🚨 **«우리»가 «정한» 것 «넷»**(원전에 **«없다**):")
    P("   ㉢ 「후퇴」 = **저가 ≤ SMA ∧ «직전» 저가 > SMA**   ㉤ 「«다시» 상승」 = **종가 > 시가**")
    P("   ㉦ 체결가 = **그날 «종가»**                          ㉧ 기한 = 돌파 «후» **%d 봉**" % HORIZON)
    P("   ⇒ ⛔ **판정이 «어느» 쪽이든 「원전 «그대로» 쟀다」로 «읽으면» «틀린다**")
    P("")
    P("**«예상»**: **Ⓤ 무리**(«유니버스»가 «커진다») — 견줌 Ⓤ **6.88~10.39배** · Ⓥ **3.3~4.8배** "
      "⛔ **«수»로 «옮기지» 않는다**")
    P(F3)
    P("")
    P("---")
    P("")
    if n_have < len(YEARS):
        P("🚨 **멈춘다** — 경로가 **%d / %d** 해뿐이다(`231a` 가 «아직» 안 끝났다)"
          % (n_have, len(YEARS)))
        return 3

    CA = Path(str(r91.OUT / "231-arms.json"))
    if CA.exists():
        d_ = json.loads(CA.read_text(encoding="utf-8"))
        base = [tuple(x) for x in d_["base"]]
        extra = [tuple(x) for x in d_["extra"]]
        n_raw = d_["n_raw"]
    else:
        P("(자료를 «짓는» 중 — 풀백을 «찾는다** …)", flush=True)
        base, extra, n_raw = build()
        if base is None:
            P("🚨 **멈춘다** — 경로 «없음»")
            return 2
        CA.write_text(json.dumps({"base": [list(x) for x in base],
                                  "extra": [list(x) for x in extra],
                                  "n_raw": n_raw}), encoding="utf-8")

    built = {"①": base, "Ⓟ": base + extra}
    P("# 1. **팔 크기와 «양성» 대조**(«먼저» 찍는다)")
    P("")
    P(F3)
    P("   **① 돌파«만» 거래 = %s**" % format(len(base), ","))
    P("   **Ⓟ 돌파 ＋ 풀백 거래 = %s**  (덧붙은 풀백 **%s**)"
      % (format(len(built["Ⓟ"]), ","), format(len(extra), ",")))
    P("   («찾은» 풀백 «후보» «전부» = %s · " % format(n_raw, ",")
      + c("open_until") + " 으로 **%s 가 «막혔다**)" % format(n_raw - len(extra), ","))
    P("")
    P("   **★ ① «에만» 있는 거래 = 0**  ⟵ **Ⓟ 는 ① 을 «품는다**(«더하는» 쪽)")
    P("   **★ Ⓟ «에만» 있는 거래 = %s**" % format(len(extra), ","))
    P("")
    P("✅ **① ⊂ Ⓟ**(«양성» 대조 «통과») — **«구성»상 «그렇다**")
    P("🚨 그리고 " + c("open_until") + " 이 **풀백 %s 개를 «막았다**"
      % format(n_raw - len(extra), ","))
    P("   ⇒ **«오염»이 «아니라» «처치»의 «일부»**다(`201d`·`218`·`227b` 에서 «본» 그것)")
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
        return m220.boot_eq(bp, n_pos)

    o = {k: m220.ann(obs(v)) for k, v in built.items()}
    obsd = o["Ⓟ"] - o["①"]

    P("---")
    P("")
    P("# 2. **팔의 «절대» 값**(연환산 %p · 참고)")
    P("")
    P(F3)
    P("   ①  **%+.3f%%p/해**" % o["①"])
    P("   Ⓟ  **%+.3f%%p/해**" % o["Ⓟ"])
    P("   날짜 자리 **%s**" % format(n_pos, ","))
    P(F3)
    P("")
    P("---")
    P("")
    P("# 3. **판정**")
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
            boots.append(eqs["Ⓟ"] - eqs["①"])
            if (bi + 1) % 400 == 0:
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
    P("   «예상»: **Ⓤ 무리**(유니버스가 «커짐») — 견줌 **6.88~10.39배**")
    P("   «관측»: **%.2f 배**" % (mdes[0] / DELTA))
    P("   ⇒ %s" % ("✅ **Ⓤ 무리 범위 «안»**" if 6.88 <= mdes[0] / DELTA <= 10.39
                   else ("🚨 **Ⓤ 범위를 «벗어났다» — 그게 «소득»이다** "
                         "(Ⓥ 범위 3.3~4.8 %s)"
                         % ("«안»" if 3.3 <= mdes[0] / DELTA <= 4.8 else "«밖»"))))
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① 🚨 **«우리»가 «정한» 것이 «넷**이다(㉢ 후퇴 · ㉤ «다시» 상승 · ㉦ 체결가 · ㉧ 기한)")
    P("     ⇒ **「원전 «그대로» 쟀다」가 «아니다** — `231-PRE.md` §1 에 «표»로 적었다")
    P("⛔ ② **20·50일 «둘» 다 «한꺼번에»** 봤다 — 원전은 「20일 «또는» 50일」이라 **«어느» 쪽인지 «안» 말했다**")
    P("⛔ ③ **풀백을 «종가»에 샀다** — 원전은 **체결 «시점»을 «안» 말했다**"
      "(`mk:47` 은 «돌파»에 대해 「«장중»」이라 했다)")
    P("⛔ ④ " + c("open_until") + " 이 풀백 **%s 개를 «막았다** — «처치»의 «일부»이나 "
      "**「«막히지» 않았으면 «어땠나»」는 «안** 쟀다" % format(n_raw - len(extra), ","))
    P("⛔ ⑤ 승률·거래당은 **«안» 적는다**")
    P(F3)
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

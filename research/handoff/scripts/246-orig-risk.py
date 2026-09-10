# -*- coding: utf-8 -*-
r"""246 - **원전 «조합»(25% 포지션 ＋ 5% 손절 ⇒ 위험 1.25%)을 «되돌리면**  (조사 세션 2026-09-09)

  🚨 **엔진이 «다르다** — 이 판은 **`sim_lots`**(risk·cap 을 «본다»)이고
     **§B 판정은 «전부» `boot_eq`**(risk 를 «안» 본다)다 ⇒ **§B 에 «넣지» 않는다**.

  📐 팔 ① 현행  risk 0.0200 · cap 0.20 · stop 10%   ⇒ 비중 20% · 위험 2.00%
     팔 Ⓡ 원전  risk 0.0125 · cap 0.25 · stop  5%   ⇒ 비중 25% · 위험 1.25%
     🔎 `43`~`52` 가 «쓰던» 값 · `73:33` 이 「= 5칸 20%」로 «바꾼» 그 자리를 «되돌린다**
  🚨 **«둘»이 «같이» 움직인다**(risk·cap ＋ stop) — **그게 «원전»의 «조합»**이다
     ⇒ ⛔ **«어느» 것 «때문»인지는 «못» 가른다**(⇒ 한정에 적는다)

  ⛔ 격자 «없음** · 씨앗 축(`163` 꼴) · 판정 팔 «하나»(Ⓡ − ①)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/246-orig-risk.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent

C1 = chr(0x2460)
CR = chr(0x211D)
YEARS = tuple(range(1999, 2027))
D0, D1 = "1999-04-01", "2026-08-21"
TARGET, HALF, SLOTS = 30.0, 0.5, 5
N_SEED = 60
YRS = 27.4

ARMS = ((C1, 0.0200, 0.20, 10.0), (CR, 0.0125, 0.25, 5.0))


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
acc = _load("acc", "account_lib.py")
f92a = r102.f92a
pt = r91.pt
OUT = Path(str(r91.OUT))


def ann(total_pct):
    v = 1.0 + total_pct / 100.0
    return -100.0 if v <= 1e-9 else (v ** (1.0 / YRS) - 1.0) * 100.0


def main():  # noqa: C901
    P("# 246 - **원전 «조합»(25% ＋ 5% ⇒ 위험 1.25%)을 «되돌리면**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/246-orig-risk.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P(F3)
    P("🚨 **엔진이 «다르다** — 이 판은 **`sim_lots`**(risk·cap 을 «본다»)")
    P("   **§B 판정은 «전부» `boot_eq`**(`220:106` `wgt = eq/slots` — risk 를 «안» 본다)")
    P("   ⇒ ⛔ **§B 에 «넣지» «않는다** · ⛔ **§B 판정을 «바꾸지» «않는다**")
    P("")
    P("📐 **팔**")
    P("   ① 현행  risk **0.0200** · cap **0.20** · stop **10%**  ⇒ 비중 20% · **위험 2.00%**")
    P("   %s 원전  risk **0.0125** · cap **0.25** · stop **5%%**   ⇒ 비중 25%% · **위험 1.25%%**" % CR)
    P("   🔎 `43-round2-size.py:49` 등 `43`~`52` 가 «쓰던» 값 · `73:33` 이 「= 5칸 20%」로 «바꿨다**")
    P("")
    P("🚨 **«우리»가 «정한» 것 = «0»** — **네 수가 «전부» 원전/우리 코드에 «있던» 것**이다")
    P("🚨 **그러나 «둘»이 «같이» 움직인다**(risk·cap ＋ stop) — **그게 원전의 «조합»**이다")
    P("   ⇒ ⛔ **«어느» 것 «때문»인지는 «못» 가른다**")
    P("")
    P("🚨 **사전등록**(값 보기 «전»)")
    P("   ① **%s 가 «위»** → 「원전 «조합»이 «낫다」  ·  ② **%s 가 «아래»** → 「지금이 «낫다」" % (CR, CR))
    P("   ③ **«못» 가리면** → 「«되돌려도» «못» 가린다」")
    P("   ⛔ **«이겨도» «못» 쓸 것**: **「§B 판정을 «바꾼다»」 ✗** — **«엔진»이 «다르다**")
    P(F3)
    P("")
    P("---")
    P("")

    t0 = time.time()
    P("(자료를 «짓는» 중 …)", flush=True)
    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 «없음»")
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

    def build(stop):
        """손절폭마다 «따로» 해소·중복제거 — `163:132-147` «그대로»."""
        out_ = []
        for y in sorted(keep):
            open_until = {}
            for p in keep[y]:
                t = pt.resolve_trade(p, ft="limit", fs="market", stop=stop, target=TARGET,
                                     half=HALF, shares=(1.0,), add_stop="floor_entry")
                c = p["code"]
                if c in open_until and p["entry_date"] <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                t["stop_frac"] = stop / 100.0
                out_.append(t)
        return out_

    CA = OUT / "246-partial.json"
    cache = json.loads(CA.read_text(encoding="utf-8")) if CA.exists() else {}
    res, meta = {}, {}
    for nm, rk, cp, sp in ARMS:
        key = "v1|%s|r%.4f|c%.2f|s%.0f|n%d" % (nm, rk, cp, sp, N_SEED)
        if key in cache:
            res[nm] = [tuple(x) for x in cache[key]]
            meta[nm] = cache[key + "|m"]
            P("  ♻️ %s — 갈무리" % nm, flush=True)
            continue
        ev = build(sp)
        with r91.r41.Cost(*r91.COST):
            rs = [r91.sl.sim_lots(ev, seed=sd, slots=SLOTS, risk=rk, cap=cp,
                                  reserve=False, fill_rule="truncate",
                                  cash_rule="per_slot") for sd in range(N_SEED)]
        res[nm] = [acc.account(x) for x in rs]
        meta[nm] = {"nomw": st.median([x["nom_w_mean"] for x in rs]) * 100.0,
                    "expo": st.median([x["expo_mean"] for x in rs]), "n_ev": len(ev)}
        cache[key] = [list(x) for x in res[nm]]
        cache[key + "|m"] = meta[nm]
        CA.write_text(json.dumps(cache), encoding="utf-8")
        P("  %s — 거래 %s · 비중 %.1f%% · 노출 %.1f%%"
          % (nm, format(len(ev), ","), meta[nm]["nomw"], meta[nm]["expo"]), flush=True)
    el = time.time() - t0
    P("")

    P("# 1. **팔 크기 · 비중 — «양성» 대조**")
    P("")
    P(F3)
    for nm, rk, cp, sp in ARMS:
        P("   %s  거래 **%s** · **«실제» 비중 %.2f%%**(목표 %.0f%%) · 노출 %.1f%%"
          % (nm, format(meta[nm]["n_ev"], ","), meta[nm]["nomw"],
             min(rk / (sp / 100.0), cp) * 100.0, meta[nm]["expo"]))
    P("")
    ok = abs(meta[CR]["nomw"] - 25.0) < 1.5
    P("   ★ **%s 의 «실제» 비중이 «25%%» 근처인가** — %s"
      % (CR, "✅ **그렇다**" if ok else "🚨 **아니다** — **팔이 «원전»이 «아니다**"))
    P("   🚨 **거래 «수»가 «다르다** — 손절폭이 «달라» **중복 제거가 «다르게»** 걸린다(`156` 의 교훈)")
    if not ok:
        P("")
        P("   🔴🔴 **«양성» 대조가 «실패**했다 — **팔이 「원전 «조합»」을 «못» 만들었다**")
        P("      ⇒ **까닭(추정 · ⛔ «미검정»)**: 자본이 «모자라** 목표 25%를 «다» «못» 채운다")
        P("      ⇒ ⇒ ⛔ **아래 «판정»은 「원전 «조합»이 «나쁘다»」로 «읽으면» «틀린다** —")
        P("           **「«이» 팔이 «아래»였다」**까지다")
    P(F3)
    P("")
    P("---")
    P("")

    P("# 2. **판정 — 씨앗 축**(⛔ **`boot_eq` «자료» 축이 «아니다**)")
    P("")
    a1 = [ann(x[0]) for x in res[C1]]
    a2 = [ann(x[0]) for x in res[CR]]
    d = [b - a for a, b in zip(a1, a2)]
    d.sort()
    lo, hi = d[int(N_SEED * .025)], d[int(N_SEED * .975)]
    win = sum(1 for x in d if x > 0)
    P(F3)
    P("   ① 연환산 중앙 **%+.3f%%** · %s 연환산 중앙 **%+.3f%%**"
      % (st.median(a1), CR, st.median(a2)))
    P("   **%s − ① 씨앗 짝차이** — 중앙 **%+.3f%%p** · 95%% [%+.3f, %+.3f] · **이기는 판 %d / %d (%.1f%%)**"
      % (CR, st.median(d), lo, hi, win, N_SEED, 100.0 * win / N_SEED))
    P("")
    P(("   낙폭 중앙 — ① **%.2f** · %s **%.2f**   ⛔ **단위는 " + BQ + "account_lib" + BQ
       + " 의 것 «그대로»**")
      % (st.median([x[1] for x in res[C1]]), CR, st.median([x[1] for x in res[CR]])))
    P("")
    if lo > 0:
        P("⇒ ① **%s 가 «위»** — 「원전 «조합»이 «낫다」" % CR)
    elif hi < 0:
        P("⇒ ② **%s 가 «아래»** — 「지금이 «낫다」" % CR)
    else:
        P("⇒ ③ **«못» 가린다** — 「«되돌려도» «못» 가린다」")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 💰 **실측**")
    P("")
    P(F3)
    P("   **%.1f 분**  (⚠️ 어림은 「«수» 분」이었다)" % (el / 60.0))
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 하는 것**")
    P("")
    P(F3)
    P("⛔ ① 🚨 **risk·cap 과 stop 이 «같이» 움직인다** — **«어느» 것 «때문»인지 «못** 가른다")
    P("     (그게 **원전의 «조합»**이므로 «격자»로 «쪼개면» «고르기»가 된다)")
    P("⛔ ② 🚨 **엔진이 `sim_lots`** — **§B 판정(`boot_eq`)과 «섞으면» «안** 된다")
    P("⛔ ③ **씨앗 축**이다 — **«자료» 축(블록 부트)이 «아니다**")
    P("⛔ ④ **거래 «수»가 팔마다 «다르다**(손절폭이 달라 중복 제거가 «다르게» 걸린다)")
    P("⛔ ⑤ **`43`~`52` 가 «그» 값을 «쓴» 까닭은 «안** 봤다 — **`43` 이 «어디»서 «가져»왔는지 «모른다**")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

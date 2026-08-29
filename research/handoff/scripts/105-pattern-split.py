# -*- coding: utf-8 -*-
"""105 — **원전대로: 파워플레이는 실적 면제, VCP·3C 는 적용** (사전등록 `tasks/105`, 커밋 52caf7b4)

원문(조사 세션 · [1차-본인] · 독립 출처 2곳):
> "This is the **only** situation I will enter with a dearth of fundamentals. With the power play …
>  **regardless of what the current earnings and sales are showing you.**"
→ 뒤집으면 **「PP 는 면제, VCP·3C 는 적용」**이 원전 주장이 된다. 103 은 «전체»에 걸었다.

# 네 판
```
① 바탕        91 정본 (실적 조건 없음)
② 전체 적용    103 최선 칸(1분기·이익매출)을 **모든 패턴에**
③ ★ 원전대로  **PP 면제 · VCP·3C 에만**
④ 뒤집기      **PP 에만 적용 · VCP·3C 면제**   ← ③ 이 «맞는 방향»인지 가르는 대조
```
🚨 **④ 없이 ③ 을 말하지 않는다.** ③·④ 가 «둘 다» ② 보다 나으면 그건 「패턴을 가른 것」이 아니라
   **「덜 거른 것」**이 한 일이다.

# 🚨 값 보기 «전»에 적어 둔 것
   PP 는 후보의 **2.3%(574건)** 뿐이다. ③ 과 ② 의 차이는 **전체의 약 2%** 다.
   **「크게 좋아진다」가 나오면 그게 «이상한» 것이다.**
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_s)
_s.loader.exec_module(r102)
_t = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_t)
_t.loader.exec_module(r103)
r91, f92a, _ord = r102.r91, r102.f92a, r102._ord
BLOCKS, YRS, SPY = r102.BLOCKS, r102.YRS, r102.SPY_CAGR

NQ, NITEM = 1, 2                     # 103 의 «최선 칸» — 1분기 · 이익매출
A_PASS = 55.0
ARMS = ("① 바탕(조건 없음)", "② 전체 적용", "③ ★ 원전대로(PP 면제)", "④ 뒤집기(PP 에만)")


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else r91.N_SEED
    print("=" * 112, flush=True)
    print("105 — 원전대로: 파워플레이는 실적 «면제», VCP·3C 는 «적용» · 운의 번호 %d판" % n_seed,
          flush=True)
    print("=" * 112, flush=True)
    print("🚨 값 보기 «전»에 적었다: PP 는 후보의 **2.3%**뿐이라 바뀌는 건 «전체의 약 2%» 다.",
          flush=True)
    print("   **「크게 좋아진다」가 나오면 그게 «이상한» 것이다.**\n", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        r102.YEARS, r102.D0, r102.D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    assert ixf[0] == "date" and ix["eps"] == 3, ixf

    # ── 후보마다 판정 한 번 ───────────────────────────────────────────
    rec = []
    for y in sorted(by2):
        for p in by2[y]:
            r_ = fund.get(p["code"])
            arq = (r_ or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or _ord(p["entry_date"]) - _ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, NQ, NITEM))
            rec.append((y, p, p.get("pattern") or "?", v))

    def build(applies):
        """applies(pattern) 이 True 인 패턴에만 실적 조건을 건다.
        조건 = 「통과」 또는 「자료 없음」을 남긴다(103 최선 칸과 «같은» 규약)."""
        by = {}
        for y, p, pat, v in rec:
            if applies(pat) and v is False:
                continue
            by.setdefault(y, []).append(p)
        return by

    V = {ARMS[0]: build(lambda _p: False),
         ARMS[1]: build(lambda _p: True),
         ARMS[2]: build(lambda pt_: pt_ != "PP"),
         ARMS[3]: build(lambda pt_: pt_ == "PP")}

    # ── 관문 ㉔ 면제 대상이 «정확히 여집합»인가 ──────────────────────
    pats = set(x[2] for x in rec)
    on3 = {p for p in pats if p != "PP"}
    on4 = {p for p in pats if p == "PP"}
    ok24 = (on3 | on4 == pats) and not (on3 & on4)
    print("관문 ㉔ ③ 과 ④ 의 적용 패턴이 «정확히 여집합»인가 → **%s** (③ %s · ④ %s)"
          % ("통과" if ok24 else "🚨 미통과", sorted(on3), sorted(on4)), flush=True)
    if not ok24:
        return 3

    # ── 관문 ㉕ ② 가 103 의 최선 칸을 재현하는가 ────────────────────
    ev2, _x, _y = r91.replay(V[ARMS[1]])
    print("관문 ㉕ ② 의 매수 수가 103 최선 칸(6,260)과 같은가 → **%s** (%s)"
          % ("통과" if len(ev2) == 6260 else "🚨 다름", "{:,}".format(len(ev2))), flush=True)

    cnt = Counter(x[2] for x in rec)
    print("\n후보 패턴 — %s · 「조건 탈락」 %s건\n"
          % (" · ".join("%s %s(%.1f%%)" % (k, "{:,}".format(v), 100.0 * v / len(rec))
                        for k, v in cnt.most_common()),
             "{:,}".format(sum(1 for x in rec if x[3] is False))), flush=True)

    print("  %-22s %8s  %s" % ("판", "매수", "구간별 [연평균 · ②와의 차 · 200판중 이긴비율]"),
          flush=True)
    print("  " + "-" * 100, flush=True)
    res, eqs = {}, {}
    # 🚨 ② 를 «먼저» 돌린다 — 나머지가 ② 를 기준으로 짝비교하므로 순서가 중요하다
    #    (앞 판에서 바탕을 먼저 돌려 KeyError 가 났다)
    for nm in (ARMS[1],) + tuple(x for x in ARMS if x != ARMS[1]):
        ev, _x, _y = r91.replay(V[nm])
        res[nm] = {"n_entry": len(ev), "win": {}}
        eqs[nm] = {}
        for lab, a_, b_ in BLOCKS:
            e = [t for t in ev if a_ <= t["entry_date"] <= b_]
            rs = r91.sim(e, n_seed)
            eq = [x["equity_pct"] for x in rs]
            eqs[nm][lab] = eq
            med = st.median(eq)
            cg = ((1 + med / 100.0) ** (1 / YRS[lab]) - 1) * 100
            if nm == ARMS[1]:
                dif, w = 0.0, 50.0
            else:
                d = sorted(x - z for x, z in zip(eq, eqs[ARMS[1]][lab]))
                dif, w = st.median(d), 100.0 * sum(1 for v in d if v > 0) / n_seed
            res[nm]["win"][lab] = {"cagr": cg, "dif": dif, "win": w,
                                   "beat_spy": cg > SPY[lab]}
    for nm in ARMS:                       # 찍기는 «등록한 순서»로
        cells = ["%s %+.2f%%%s %+6.2f %5.1f%%"
                 % (lab.split()[0], res[nm]["win"][lab]["cagr"],
                    "✅" if res[nm]["win"][lab]["beat_spy"] else "❌",
                    res[nm]["win"][lab]["dif"], res[nm]["win"][lab]["win"])
                 for lab, _a, _b in BLOCKS]
        print("  %-22s %8s  %s"
              % (nm, "{:,}".format(res[nm]["n_entry"]), "  ".join(cells)), flush=True)

    # ── 판정 ─────────────────────────────────────────────────────────
    print("\n" + "=" * 112, flush=True)
    w3 = res[ARMS[2]]["win"]
    P = all(w3[l]["win"] > A_PASS for l in w3)
    print("  **P★** ③ 이 «세 구간 모두» ② 보다 이기는 판 > %.0f%% → %s   (%s)"
          % (A_PASS, "통과" if P else "**미통과**",
             " · ".join("%s %.1f%%" % (l.split()[0], w3[l]["win"]) for l in w3)), flush=True)

    print("  **Q★** ③ 이 ② 보다 나은 크기 > ④ 가 ② 보다 나은 크기  (**주지표**)", flush=True)
    Q = True
    for lab, _a, _b in BLOCKS:
        d3 = res[ARMS[2]]["win"][lab]["dif"]
        d4 = res[ARMS[3]]["win"][lab]["dif"]
        ok = d3 > d4
        Q = Q and ok
        print("        %-16s ③ %+7.2f%%p  vs  ④ %+7.2f%%p  →  %s"
              % (lab, d3, d4, "③ 이 낫다" if ok else "**④ 가 낫거나 같다 — 미통과**"), flush=True)
    print("        → **Q★ %s**" % ("통과" if Q else "미통과"), flush=True)

    # R — 매수 수 · S — MDE
    print("\n  **R** 매수 수 — %s"
          % (" · ".join("%s %s" % (n.split()[0], "{:,}".format(res[n]["n_entry"])) for n in ARMS)),
          flush=True)
    print("      ③−② = %+d 건 (전체의 %.2f%%)"
          % (res[ARMS[2]]["n_entry"] - res[ARMS[1]]["n_entry"],
             100.0 * abs(res[ARMS[2]]["n_entry"] - res[ARMS[1]]["n_entry"])
             / max(1, res[ARMS[1]]["n_entry"])), flush=True)
    print("  **S** MDE (③ vs ②) — %s"
          % (" · ".join("%s %.2f" % (l.split()[0],
                                     2.8 * st.pstdev([x - z for x, z in
                                                      zip(eqs[ARMS[2]][l], eqs[ARMS[1]][l])])
                                     / (n_seed ** 0.5)) for l, _a, _b in BLOCKS)), flush=True)
    print("\n  → **③(원전대로)의 답: %s**" % ("예" if (P and Q) else "**아니오**"), flush=True)

    (r91.OUT / "105-pattern-split.json").write_text(
        json.dumps({"res": res, "P": P, "Q": Q, "n_seed": n_seed},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 105-pattern-split.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

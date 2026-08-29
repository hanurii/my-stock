# -*- coding: utf-8 -*-
"""106 — **붙어 있는 두 칸이 하나씩 어긋난다. 「하나가 진짜」인가 「둘 다 잡음」인가** (②번)

103 에서 이렇게 나왔다:
```
1분기·이익매출·자료없으면그냥삼   2002~2017 **+8.38% ✅**(지수 7.04)  ·  2018~2026 +13.48% ❌(15.27)
2분기·이익매출·자료없으면그냥삼   2002~2017 +7.01% ❌(**0.03%p 차이**)  ·  2018~2026 **+15.81% ✅**
```
**두 칸이 거의 붙어 있는데 «하나씩» 어긋난다.** 이게 「둘 중 하나가 진짜」인지
**「둘 다 잡음이라 아무렇게나 갈린 것」**인지 가른다.

# 재는 것 — 셋
```
㉮ 두 칸을 «직접» 짝비교한다 (1분기 vs 2분기) — 세 구간 + MDE
   → 둘이 «서로» 구분이 안 되면, 「어느 칸이 어느 창에서 이긴다」는 말은 뜻이 없다
㉯ 연도별로 벌린다 — 차이가 «특정 해»에 몰려 있나
㉰ ★ **「둘 다 잡음」의 «귀무»를 만든다**
   같은 비율의 동전 던지기 «두 판»을 여러 번 만들어,
   「한 판은 A구간에서 이기고 다른 판은 B구간에서 이기는」 일이 **얼마나 흔한가**를 센다
   → 흔하면 103 의 «어긋남»은 볼 것이 없다
```
🚨 **기전 진단 + 귀무 계산이다. 새 문턱을 등록하지 않는다**(103 의 결과를 «읽는» 판이다).
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
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

N_NULL = 40           # ㉰ — 동전 던지기 «짝»을 몇 번 만들어 볼까


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else r91.N_SEED
    n_null = 6 if quick else N_NULL
    print("=" * 112, flush=True)
    print("106 — 붙어 있는 두 칸: 「하나가 진짜」인가 「둘 다 잡음」인가 · 운의 번호 %d판" % n_seed,
          flush=True)
    print("=" * 112, flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        r102.YEARS, r102.D0, r102.D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    assert ixf[0] == "date" and ix["eps"] == 3, ixf

    rec = []
    for y in sorted(by2):
        for p in by2[y]:
            r_ = fund.get(p["code"])
            arq = (r_ or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            if a is None or _ord(p["entry_date"]) - _ord(a[0]) > r102.STALE_MAX:
                v1 = v2 = None
            else:
                j = arq.index(a)
                v1 = r103.judge(arq, j, ix, 1, 2)
                v2 = r103.judge(arq, j, ix, 2, 2)
            rec.append((y, p, v1, v2))

    def build(which):
        by = {}
        for y, p, v1, v2 in rec:
            v = v1 if which == 1 else v2
            if v is False:
                continue
            by.setdefault(y, []).append(p)
        return by

    def measure(by, tag):
        ev, _x, _y = r91.replay(by)
        out = {"n_entry": len(ev), "eq": {}}
        for lab, a, b in BLOCKS:
            e = [t for t in ev if a <= t["entry_date"] <= b]
            out["eq"][lab] = [x["equity_pct"] for x in r91.sim(e, n_seed)]
        return out

    A = measure(build(1), "1분기")
    B = measure(build(2), "2분기")
    rA = 100.0 * A["n_entry"] / 9172.0
    print("매수 — 1분기 %s · 2분기 %s (바탕 9,172)\n"
          % ("{:,}".format(A["n_entry"]), "{:,}".format(B["n_entry"])), flush=True)

    # ── ㉮ 두 칸을 «직접» 짝비교 ─────────────────────────────────────
    print("# ㉮ **두 칸을 «직접» 견준다** (1분기 − 2분기)", flush=True)
    print("  %-16s %11s %11s %13s %9s %8s"
          % ("구간", "1분기 연평균", "2분기 연평균", "차이(자산)", "가릴크기", "이긴비율"), flush=True)
    print("  " + "-" * 76, flush=True)
    same = True
    for lab, _a, _b in BLOCKS:
        ea, eb = A["eq"][lab], B["eq"][lab]
        ca = ((1 + st.median(ea) / 100.0) ** (1 / YRS[lab]) - 1) * 100
        cb = ((1 + st.median(eb) / 100.0) ** (1 / YRS[lab]) - 1) * 100
        d = sorted(x - z for x, z in zip(ea, eb))
        med = st.median(d)
        mde = 2.8 * st.pstdev(d) / (n_seed ** 0.5)
        w = 100.0 * sum(1 for v in d if v > 0) / n_seed
        ok = abs(med) > mde
        same = same and (not ok)
        print("  %-16s %+10.2f%% %+10.2f%% %+12.2f%%p %8.2f %7.1f%% %s"
              % (lab, ca, cb, med, mde, w, "**갈린다**" if ok else "«구분 안 됨»"), flush=True)
    print("  → **두 칸이 서로 구분되는가: %s**"
          % ("아니다 — 셋 다 구분 안 됨" if same else "일부 구간에서 갈린다"), flush=True)

    # ── ㉰ ★ 「둘 다 잡음」의 귀무 ────────────────────────────────────
    print("\n# ㉰ ★ **「둘 다 잡음」이면 이런 어긋남이 얼마나 흔한가**", flush=True)
    print("     같은 비율의 «동전 던지기» 두 판을 %d 번 만들어, 103 과 같은 모양이 나오는지 센다"
          % n_null, flush=True)
    rnd = random.Random(20260829)
    KEY1, KEY2 = "2002~2017", "2018~2026"
    hit_cross = hit_any = 0
    base_ev, _x, _y = r91.replay(by2)
    for it in range(n_null):
        def pick(rate):
            by = {}
            for y, p, _v1, _v2 in rec:
                if rnd.random() < rate / 100.0:
                    by.setdefault(y, []).append(p)
            return by
        X = measure(pick(rA), "x")
        Y = measure(pick(100.0 * B["n_entry"] / 9172.0), "y")
        cx, cy = {}, {}
        for lab, _a, _b in BLOCKS:
            cx[lab] = ((1 + st.median(X["eq"][lab]) / 100.0) ** (1 / YRS[lab]) - 1) * 100
            cy[lab] = ((1 + st.median(Y["eq"][lab]) / 100.0) ** (1 / YRS[lab]) - 1) * 100
        # 103 과 같은 «모양» = 한 판은 KEY1 에서만 지수를 이기고, 다른 판은 KEY2 에서만
        a1, a2 = cx[KEY1] > SPY[KEY1], cx[KEY2] > SPY[KEY2]
        b1, b2 = cy[KEY1] > SPY[KEY1], cy[KEY2] > SPY[KEY2]
        if (a1 and not a2 and b2 and not b1) or (b1 and not b2 and a2 and not a1):
            hit_cross += 1
        if (a1 or a2 or b1 or b2):
            hit_any += 1
    print("     → **103 과 «같은 모양»(한 판은 앞 구간만, 다른 판은 뒤 구간만 이김)이 나온 횟수:"
          " %d / %d = %.0f%%**" % (hit_cross, n_null, 100.0 * hit_cross / n_null), flush=True)
    print("        (참고) 어느 한 구간이라도 지수를 이긴 판이 있던 횟수: %d / %d"
          % (hit_any, n_null), flush=True)

    print("\n" + "=" * 112, flush=True)
    print("  ★ 읽는 법", flush=True)
    print("     ㉮ 가 «구분 안 됨»이고 ㉰ 가 «흔하다»면  →  **103 의 어긋남은 볼 것이 없다**",
          flush=True)
    print("     ㉮ 가 «갈린다»면                        →  두 칸은 정말 다른 규칙이다", flush=True)
    (r91.OUT / "106-two-cells.json").write_text(
        json.dumps({"n_A": A["n_entry"], "n_B": B["n_entry"],
                    "cross": hit_cross, "n_null": n_null, "n_seed": n_seed},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 106-two-cells.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

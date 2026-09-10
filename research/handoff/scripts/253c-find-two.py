# -*- coding: utf-8 -*-
r"""253c - **어긋난 «둘»을 «집어» — «두» 번 «부른다**  (조사 세션 2026-09-09)

  🚨 **검증 싼 물음 ①** — `253a` 의 「옛 자」에서 **㉢(`consecutive_lower_lows`)이 «둘» 어긋났다**
     (151,997 / 151,999 = 99.99868%). **㉢ 은 «안» 되돌아오는 규칙**이라 —
     **그 「«정확»히 100.000%」가 (a) 승인의 «음성 대조»였다**(유형 108).

  📐 **자**: 어긋난 «그» 거래를 «집어** — **`SR.rule_consecutive_lower_lows` 를 «두» 번** 부른다.
     · **«같은» 답** ⇒ 구현 차이(부동소수 «합산 순서» 후보) ⇒ **재현성 «성립**
     · **«다른» 답** ⇒ **진짜 함수가 «비결정»** ⇒ **`jr` 재현성 «깨짐** ⇒ 🛑 **멈춤**

  ⛔ **㉢ «하나»만** 본다(싸게) · ⛔ **「무해」로 «닫지» 않는다**

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/253c-find-two.py
"""
from __future__ import annotations

import gc
import io
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "scripts"))

from canslim_lib import sell_rules as SR                       # noqa: E402

WARM = Path("D:/stock-data/uspath-warm2")
YEARS = tuple(range(1999, 2027))


def rolling_avgv(v, window=50, min_days=5):
    """`SR.avg_volume` 와 «같은» 것을 «한» 번에 — 판정일 «제외** · 거짓값 «거른다**.

    ⚠️🚨 **«확인된» 결함 — 이 함수를 «다시» «쓰는» 판은 «먼저» 이 줄을 «읽었다»고 «적어라**
       **`>=` «경계»에서 «진짜» 함수(`SR.avg_volume`)와 «갈린다**.
       까닭: 누적합 차(`ps[i]-ps[lo]`)와 직접 합산이 **«마지막» 비트**에서 다르고 —
       거래량이 **거의 «상수»**인 계열(예 `RSLS1`: 0.0 이 78 · 0.01 이 50)에서는
       **평균이 «정확»히 그 값과 «같아져»** `v >= avg` 가 **경계 «등호»**가 된다.
       실측 **2 / 151,999**(`253c-find-two.py` · `results/253c-two.json`) · 상대오차 9.637e-16.
       ⛔ **「2/152k」를 «다른» 판으로 «옮기지» 말 것**(유형 68) —
          **저유동·거래정지 «근처» 종목이 «많은» 표본에선 «그» 수가 «아니다**.
       ✅ **고치려면**: 창을 «직접» 합산(O(n×50)) ⇒ 색인 재빌드 어림 15~25분.
    """
    n = len(v)
    ps, pc = [0.0] * (n + 1), [0] * (n + 1)
    for i, x in enumerate(v):
        ok = 1 if x else 0
        ps[i + 1] = ps[i] + (x if ok else 0.0)
        pc[i + 1] = pc[i] + ok
    out = [None] * n
    for i in range(n):
        lo = max(0, i - window)
        cnt = pc[i] - pc[lo]
        if cnt >= min_days:
            out[i] = (ps[i] - ps[lo]) / cnt
    return out


def mine(l, v, av, si, n):
    """`253a.first_violations` 의 ㉢ «그대로**."""
    qrun = 0
    for i in range(si + 1, n):
        is_ll = l[i] < l[i - 1]
        qrun = qrun + 1 if (is_ll and av[i] is not None and v[i] is not None
                            and v[i] >= av[i]) else 0
        if qrun >= SR.LOWER_LOW_RUN:
            return i
    return None


def main():
    t0 = time.time()
    found = []
    tot = 0
    for y in YEARS:
        f = WARM / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        d = json.loads(io.open(f, encoding="utf-8").read())
        for r in d.get("trigger_paths") or []:
            pn = r.get("pre_n") or 0
            if not pn or not r.get("v") or not r.get("pivot"):
                continue
            tot += 1
            ll = r["pre_l"] + r["l"]
            vv = r["pre_v"] + r["v"]
            n = len(ll)
            av = rolling_avgv(vv)
            m = mine(ll, vv, av, pn, n)
            s = {"dates": r["pre_d"] + r["d"], "closes": r["pre_c"] + r["c"],
                 "highs": r["pre_h"] + r["h"], "lows": ll, "volumes": vv}
            a = SR.rule_consecutive_lower_lows(s, pn)
            if ("v" if m is not None else "n") != ("v" if a["status"] == "violation" else "n"):
                b = SR.rule_consecutive_lower_lows(s, pn)
                c = SR.rule_consecutive_lower_lows(s, pn)
                found.append({
                    "code": r["code"], "entry": r["entry_date"], "year": y, "si": pn, "n": n,
                    "mine": m, "real": a["status"], "detail": a["detail"],
                    "twice_same": (a == b == c),
                    "b": b["status"], "c": c["status"],
                })
                P("  🔴 %s %s (%d) — 내것 %s / 진짜 %s | 두 번 «같은가» %s"
                  % (r["code"], r["entry_date"], y, m, a["status"],
                     "✅" if (a == b == c) else "🚨 «다르다»"), flush=True)
        del d
        gc.collect()
        P("  %d 끝 — 누적 %s · 어긋남 %d (%.1f분)"
          % (y, format(tot, ","), len(found), (time.time() - t0) / 60.0), flush=True)
    P("")
    P("합 %.1f분 · 거래 %s · **어긋남 %d**" % ((time.time() - t0) / 60.0, format(tot, ","),
                                              len(found)))
    (HERE.parent / "results" / "253c-two.json").write_text(
        json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
    P("저장 253c-two.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

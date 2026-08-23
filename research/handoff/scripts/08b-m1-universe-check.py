# -*- coding: utf-8 -*-
"""08b — 확정 밖 95건(M1 적용 3,776키)이 주 지표를 움직이는가.

두뇌 세션 요청: "미확인으로 남기지 마세요. 95건 중 max_gain ≥ 8 인 건수와 그때의 주 지표."

08 본체는 지시서대로 **확정 3,681건**으로 돌았다. M1(매수 당일 손절 터치를 그날 종가 체결로
편입)을 적용하면 유니버스가 3,776키가 되고 95건이 더해진다. 그 95건이
`max_gain ≥ 8` 분모에 몇 건 들어가고 주 지표가 얼마나 움직이는지만 확인한다.

95건의 결과는 14번과 같은 규칙으로 정한다:
  목표 도달 = 승 · 손절 도달 = 패 · 같은날 동시 접촉 = 패(보수) · 마지막 종가 = 손익 부호(0.00%면 패)

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/08b-m1-universe-check.py
난수 seed: 블록 부트스트랩 80000 (08 본체와 동일)
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import defaultdict
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
TARGET, STOP = 20.0, 10.0
N_BOOT, BOOT_SEED = 1000, 80000
BLOCK_MIN, BLOCK_MAX = 20, 40
Z = 1.959963985


def wilson(k, n):
    p = k / n
    den = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / den
    hw = Z * sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return p * 100, (c - hw) * 100, (c + hw) * 100


def make_blocks(rnd, n_pos):
    blocks, total = [], 0
    while total < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - total)
        blocks.append((a, LL))
        total += LL
    return blocks


def boot_rate(by_pos, n_pos, seed):
    rnd = random.Random(seed)
    out = []
    for _ in range(N_BOOT):
        w = t = 0
        for a, L in make_blocks(rnd, n_pos):
            for j in range(L):
                for is_w in by_pos.get(a + j, ()):
                    t += 1
                    w += is_w
        if t:
            out.append(w / t * 100)
    s = sorted(out)
    return s[int(len(s) * 0.025)], s[int(len(s) * 0.975) - 1], st.median(s)


def main():
    ev = {}
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            ev[(e["scan_date"], e["code"], e["pattern"])] = e
    conf = {k: e for k, e in ev.items() if e["result"] in ("win", "loss")}
    extra_keys = set(ev) - set(conf)
    print("확정 %d · 확정 밖 %d" % (len(conf), len(extra_keys)), flush=True)

    # 확정 밖 95건을 경로에서 14번 규칙으로 결착시키고 max_gain 을 잰다
    extra = {}
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        for p in d["paths"]:
            k = (p["scan_date"], p["code"], p["pattern"])
            if k not in extra_keys:
                continue
            e = p["entry_price"]
            h, l, c = p["h"], p["l"], p["c"]
            n = len(c)
            T, S = e * (1 + TARGET / 100), e * (1 - STOP / 100)
            mh, ml = -1e30, 1e30
            idx, why = n - 1, "last_close"
            for i in range(n):
                if h[i] > mh:
                    mh = h[i]
                if l[i] < ml:
                    ml = l[i]
                ht, hs = mh >= T, ml <= S
                if ht and hs:
                    idx, why = i, ("both_same_day" if (h[i] >= T and l[i] <= S)
                                   else ("target" if h[i] >= T else "stop"))
                    break
                if ht:
                    idx, why = i, "target"
                    break
                if hs:
                    idx, why = i, "stop"
                    break
            gain = (c[idx] / e - 1) * 100
            mg = (max(h[:idx + 1]) / e - 1) * 100
            result = ("win" if why == "target" else
                      "loss" if why in ("stop", "both_same_day") else
                      ("win" if gain > 0 else "loss"))
            extra[k] = {"entry_date": p["entry_date"], "result": result,
                        "max_gain": mg, "reason": why,
                        "orig": p.get("orig_result")}
    print("확정 밖 결착 %d건" % len(extra), flush=True)

    ge8 = {k: v for k, v in extra.items() if v["max_gain"] >= 8}
    print("★ 95건 중 max_gain ≥ 8 인 건: **%d건** (승 %d · 패 %d)"
          % (len(ge8), sum(1 for v in ge8.values() if v["result"] == "win"),
             sum(1 for v in ge8.values() if v["result"] == "loss")), flush=True)
    for k, v in sorted(ge8.items()):
        print("   %s %s  max_gain %.2f%% · 결과 %s (%s) · 원래 %s"
              % (k[0], k[1], v["max_gain"], v["result"], v["reason"], v["orig"]),
              flush=True)

    # 주 지표 재계산
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    rows = [{"entry_date": e["entry_date"], "result": e["result"],
             "max_gain": e["max_gain_pct"]} for e in conf.values()]
    rows_all = rows + [{"entry_date": v["entry_date"], "result": v["result"],
                        "max_gain": v["max_gain"]} for v in extra.values()]
    lo_d = min(r["entry_date"] for r in rows_all)
    hi_d = max(cal)
    dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(dates)}
    n_pos = len(dates)

    out = {}
    for name, rs in (("확정 3,681 (08 본체)", rows), ("M1 3,776 (부가)", rows_all)):
        g = [r for r in rs if r["max_gain"] >= 8 and r["entry_date"] in pos_of]
        k = sum(1 for r in g if r["result"] == "win")
        pt, wlo, whi = wilson(k, len(g))
        bp = defaultdict(list)
        for r in g:
            bp[pos_of[r["entry_date"]]].append(1 if r["result"] == "win" else 0)
        blo, bhi, bmed = boot_rate(bp, n_pos, BOOT_SEED)
        out[name] = {"n": len(g), "n_win": k, "rate": pt,
                     "wilson": [wlo, whi], "boot": [blo, bhi], "boot_median": bmed}
        print("\n[%s] 분모 %d (승 %d) · %.2f%% · 부트 95%% %.2f ~ %.2f · Wilson %.2f ~ %.2f"
              % (name, len(g), k, pt, blo, bhi, wlo, whi), flush=True)

    a, b = out["확정 3,681 (08 본체)"], out["M1 3,776 (부가)"]
    print("\n★ 차이: 분모 %+d건 · 점추정 %+.2f%%p · 부트 하한 %+.2f%%p"
          % (b["n"] - a["n"], b["rate"] - a["rate"], b["boot"][0] - a["boot"][0]),
          flush=True)
    print("   판정 문턱(하한 ≥65%%) 통과 여부: 본체 %s · M1판 %s"
          % ("예" if a["boot"][0] >= 65 else "아니오",
             "예" if b["boot"][0] >= 65 else "아니오"), flush=True)

    (OUT / "08b-m1-universe-check.json").write_text(
        json.dumps({"n_extra": len(extra), "n_extra_ge8": len(ge8),
                    "extra_ge8": {"|".join(k): v for k, v in ge8.items()},
                    "compare": out}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("\n저장: .cache/bt5y/out/08b-m1-universe-check.json")


if __name__ == "__main__":
    main()

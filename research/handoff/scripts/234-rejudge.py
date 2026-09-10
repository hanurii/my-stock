# -*- coding: utf-8 -*-
r"""234 - **「자리」를 «달력»으로 «되돌려» «다시» 판정한다** (조사 세션 2026-09-08)

  ★★★ `233` 뒤 «드러난» 것: **보유(hold)는 «전»/«후» 100% «같다**(201d 13,631 행 «전부»).
      ⇒ **결함은 E3 «하나»** — 「자리」가 「진입일」이었던 것. **보유는 «처음부터» 「거래일」로 «맞았다**.
      ⇒ ⇒ **자료를 «다시» 지을 «필요»가 «없다** — **갈무리를 «그대로»** 쓰고 **자리«만»** 바꾼다.

  자리 = `201d-arms2.json` 의 **cal**(모든 거래일 6,893) — `23c:71` 모양.
  ⛔ 갈무리·원본 각본은 **«건드리지» 않는다**(읽기만).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/234-rejudge.py --run 220
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
DELTA, MDE_K = 1.23, 2.8016
BLOCKS = ((20, 40), (80, 80))


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
OUT = Path(str(r91.OUT))


def J(nm):
    return json.loads((OUT / nm).read_text(encoding="utf-8"))


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


def ann(v, yrs=27.4):
    x = 1.0 + v / 100.0
    return -100.0 if x <= 1e-9 else (x ** (1.0 / yrs) - 1.0) * 100.0


def draw(n, rnd, bmn, bmx):
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(bmn, bmx)
        a = rnd.randint(0, n - 1)
        LL = min(L, n - tot)
        for j in range(LL):
            out.append((a + j) % n)
        tot += LL
    return out


def cell_of(lo, hi):
    if lo >= DELTA:
        return "1"
    if hi <= -DELTA:
        return "2"
    if lo <= 0 <= hi:
        return "5"
    if -DELTA <= lo and hi <= DELTA:
        return "4a"
    return "4b"


# ══════════════════════════════════════════════════════════════════════════════
# 판마다 «팔»을 «갈무리»에서 «꺼내는» 법  (⛔ «새로» 짓지 «않는다»)
# ══════════════════════════════════════════════════════════════════════════════
def arms_220():
    recs = J("220-recs.json")
    base = [(z["d"], z["h"], z["n"]) for z in recs]
    out = {C1: base, chr(0x24B7): [tuple(x) for x in J("220-b.json")]}
    for k, key in ((chr(0x24B6), "A"), (chr(0x24B8), "C"), (chr(0x24B9), "D")):
        out[k] = [(z["d"], z["h"], z["n"]) for z in recs if z.get(key) is True]
    pairs = [(k, k, C1) for k in (chr(0x24B6), chr(0x24B7), chr(0x24B8), chr(0x24B9))]
    return out, pairs, 220220


def arms_229():
    d = J("229-recs.json")
    recs = d["recs"]
    base = [(z["d"], z["h"], z["n"]) for z in recs]
    hi = [(z["d"], z["h"], z["n"]) for z in recs
          if z.get("roe") is not None and z["roe"] >= 0.15]
    return {C1: base, chr(0x211D): hi}, [(chr(0x211D), chr(0x211D), C1)], 229229


def arms_228():
    recs = J("220-recs.json")
    base = [(z["d"], z["h"], z["n"]) for z in recs]
    rev = [(z["d"], z["h"], z["n"]) for z in recs if z.get("A") is False]
    return {C1: base, chr(0x24C3): rev}, [(chr(0x24C3), chr(0x24C3), C1)], 228228


def arms_220b():
    recs = J("220-recs.json")
    dp = [(z["d"], z["h"], z["n"]) for z in recs if z.get("D") is True]
    dm = [(z["d"], z["h"], z["n"]) for z in recs if z.get("D") is False]
    kp, km = chr(0x24B9) + "+", chr(0x24B9) + "-"
    return {kp: dp, km: dm}, [(kp + "-" + km, kp, km)], 220221


def arms_231b():
    d = J("231-arms.json")
    base = [tuple(x) for x in d["base"]]
    extra = [tuple(x) for x in d["extra"]]
    return {C1: base, chr(0x24C5): base + extra}, [(chr(0x24C5), chr(0x24C5), C1)], 231231


def arms_218():
    a = J("218-arms.json")["arms"]
    ks = [k for k in a if k != C1]
    return ({k: [tuple(x) for x in v] for k, v in a.items()},
            [(k, k, C1) for k in ks], 218218)


def arms_227b():
    a = J("227-arms.json")["arms"]
    ks = [k for k in a if k != C1]
    return ({k: [tuple(x) for x in v] for k, v in a.items()},
            [(k, k, C1) for k in ks], 227227)


def arms_208():
    a = J("208-arms.json")
    ks = [k for k in a if k != C1]
    return ({k: [tuple(x) for x in v] for k, v in a.items()},
            [(k, k, C1) for k in ks], 208208)



def _dictarms(nm, base_key=None, pair_fn=None, seed=0):
    a = J(nm)
    built = {k: [tuple(x) for x in v] for k, v in a.items()}
    return built, pair_fn(built), seed


def arms_183():
    a = J("183-arms.json")
    built = {k: [tuple(x) for x in v] for k, v in a.items()}
    ks = [k for k in built if not k.startswith(chr(0x24B9))]
    return built, [(k, k, chr(0x24B9) + k) for k in ks], 183183


def arms_185():
    a = J("185-arms.json")
    built = {k: [tuple(x) for x in v] for k, v in a.items()}
    S2, S1, N = chr(0x24C8) + chr(0x2033), chr(0x24C8) + chr(0x00B9), chr(0x24C3)
    pairs = [("175가격", N, S2), ("175합", N, C1), ("181c", S1, S2),
             ("181합", N, S2), ("182합", N, C1)]
    return built, [p for p in pairs if p[1] in built and p[2] in built], 185185


def arms_191():
    a = J("191-arms.json")
    built = {k: [tuple(x) for x in v] for k, v in a.items()}
    ks = [k for k in built if k.endswith("%")]
    return built, [(k, k, C1) for k in ks], 191191


def arms_193b():
    a = J("193b-arms.json")
    built = {k: [tuple(x) for x in v] for k, v in a.items()}
    V = chr(0x24CB)
    return built, [(V + "-" + C1, V, C1)], 193193


REG = {"220": (arms_220, "220-fa-four"), "229": (arms_229, "229-roe-threshold"),
       "228": (arms_228, "228-rev-leads"), "220b": (arms_220b, "220b-pe-clean"),
       "231b": (arms_231b, "231b-pullback-judge"), "218": (arms_218, "218-nq-four"),
       "227b": (arms_227b, "227b-noliq-judge"), "208": (arms_208, "208-mde-second-probe"),
       "183": (arms_183, "183-data-axis"), "185": (arms_185, "185-oneaxis"),
       "191": (arms_191, "191-alpha-data-axis"), "193b": (arms_193b, "193b-pivot-prevhigh")}

# «전» 판정칸 — `232a-bias-stamp.md` 에서 «읽은» 것(손으로 «옮김» · ⛔ 「전/후 나란히」 자리에서«만»)
BEFORE = {"220": {chr(0x24B6): "5", chr(0x24B7): "5", chr(0x24B8): "5", chr(0x24B9): "5"},
          "229": {chr(0x211D): "5"}, "228": {chr(0x24C3): "5"},
          "220b": {chr(0x24B9) + "+-" + chr(0x24B9) + "-": "5"},
          "231b": {chr(0x24C5): "5"}, "218": {chr(0x24DD): "5"},
          "227b": {chr(0x24CD): "5"}, "208": {chr(0x24BC): "-"}}


def main():  # noqa: C901
    if "--run" not in sys.argv:
        P("사용: --run {%s}" % "|".join(REG))
        return 1
    key = sys.argv[sys.argv.index("--run") + 1]
    if key not in REG:
        P("🚨 «모르는» 판: %s" % key)
        return 1
    fn, title = REG[key]
    NBOOT = 2000

    P("# 234-%s — **`%s` 를 «달력» 자리로 «다시» 판정**" % (key, title))
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/234-rejudge.py --run " + key + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ 사전등록 " + BQ + "results/233-PRE.md" + BQ + " 의 «대칭»이 **이 판에도 «걸린다**")
    P("> ★ **자료를 «다시» 짓지 «않았다** — **보유는 «전»/«후» 100% «같다**(`233` 뒤 확인)")
    P("")
    P("---")
    P("")

    cal = J("201d-arms2.json")["cal"]
    built, pairs, seed = fn()
    ents = {d for lst in built.values() for d, _h, _n in lst}
    out_of = sorted(ents - set(cal))
    P(F3)
    P("   달력(모든 거래일) **%s**" % format(len(cal), ","))
    P("   이 판의 진입일 **%s** · **달력 «밖» = %s**"
      % (format(len(ents), ","), format(len(out_of), ",")))
    if out_of:
        P("   🚨 **달력 «밖»이 «있다** — 그 날짜를 달력에 «더한다**(보기 %s)" % out_of[:3])
        cal = sorted(set(cal) | ents)
        P("   ⇒ 달력 **%s** 로 «늘림**" % format(len(cal), ","))
    else:
        P("   ✅ **«밖»이 «없다** — 달력을 «그대로» 쓴다")
    P("")
    for k, lst in built.items():
        P("   %-4s 거래 **%s**" % (k, format(len(lst), ",")))
    P(F3)
    P("")

    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)
    ia = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            ia[k][pos[d]].append(j)

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return eq_of(bp, n_pos)

    o, got = {}, {}
    for k, v in built.items():
        e, g = obs(v)
        o[k] = ann(e)
        got[k] = g
    P("# 1. **팔의 «절대» 값 · 슬롯 «얻은» 건수**")
    P("")
    P(F3)
    for k in built:
        P("   %-4s **%+8.3f%%p/해**  ·  슬롯 «얻은» 것 **%s** / %s (%.1f%%)"
          % (k, o[k], format(got[k], ","), format(len(built[k]), ","),
             100.0 * got[k] / len(built[k])))
    P(F3)
    P("")
    P("---")
    P("")

    P("# 2. ★★★ **판정 — «전» / «후**")
    P("")
    P("| 짝 | 블록 | 점추정 | 95%% CI | CI폭 | **MDE** | 편향 | **«후» 칸** | «전» 칸 | 바뀌나 |")
    P("|---|---|---:|---:|---:|---:|---:|:--|:--|:--|")
    t0 = time.time()
    changed = 0
    total = 0
    for nm, ka, kb in pairs:
        obsd = o[ka] - o[kb]
        for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
            rnd = random.Random(seed + bi_blk)
            boots = []
            for bi in range(NBOOT):
                order = draw(n_pos, rnd, bmn, bmx)
                eqs = {}
                for k in (ka, kb):
                    bp = defaultdict(list)
                    for newp, oldp in enumerate(order):
                        for j in ia[k].get(oldp, ()):
                            _d, h, nt = built[k][j]
                            bp[newp].append((h, nt, 0))
                    eqs[k] = ann(eq_of(bp, n_pos)[0])
                boots.append(eqs[ka] - eqs[kb])
                if (bi + 1) % 500 == 0:
                    P("  [%s %d~%d] %d/%d" % (nm, bmn, bmx, bi + 1, NBOOT), flush=True)
            v = sorted(boots)
            lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
            sd = st.stdev(boots)
            cell = cell_of(lo, hi)
            was = BEFORE.get(key, {}).get(nm, "?")
            ch = (cell != was) if was not in ("?", "-") else None
            total += 1
            if ch:
                changed += 1
            P("| **%s** | %d~%d | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | **%.3f** | %+.3f | **%s** | %s | %s |"
              % (nm, bmn, bmx, obsd, lo, hi, hi - lo, MDE_K * sd,
                 (lo + hi) / 2.0 - obsd, cell, was,
                 "—" if ch is None else ("🚨 **바뀜**" if ch else "같음")), flush=True)
    el = time.time() - t0
    P("")
    P(F3)
    P("   ★ **%d 행 «중» %d** 이 **판정칸이 «바뀌었다**" % (total, changed))
    P("   💰 실측 **%.1f 분**(부트«만» — 자료 짓기 **0**)" % (el / 60.0))
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **«전» 칸은 " + BQ + "232a-bias-stamp.md" + BQ + " 에서 «옮긴» 것**이다(손으로) — «검산» 필요")
    P("⛔ ② **묘사 팔은 «안** 쟀다 — **«판정» 짝«만**")
    P("⛔ ③ **달력은 " + BQ + "201d-arms2.json" + BQ + " 것**이다 — 이 판의 «자기» 경로로 «지은» 게 «아니다**")
    P("⛔ ④ **MDE·CI 인용 금지가 «산다** — 「전/후 나란히」 «자리»에서«만**")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

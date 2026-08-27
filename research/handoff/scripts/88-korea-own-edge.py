# -*- coding: utf-8 -*-
"""88 — **한국에서 «한국 것»을 찾는다**. 사전등록 `tasks/88-korea-own-edge.md` (`4a50d44d`)

```
표본 안(찾기)  2021-02-01 ~ 2023-12-31    ← 여기서만 «고른다»
표본 밖(판정)  2024-01-01 ~ 끝            ← 여기서만 «잰다» · 한 번만
```
🚨 여섯 칸은 «표본 안» 표에만 찍는다. 표본 밖에서 여섯을 보고 고르면 안 된다.
🚨 **가짜약(유형 26)을 먼저 건다** — 필터는 «덜 사는 것»이기도 하다.
🚨 지수는 «못 넘을 것»으로 미리 적었다. 묻는 것은 「선별이 전수보다 나은가」다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/88-korea-own-edge.py [--quick]
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim_frac as sf                                    # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

_s2 = _u.spec_from_file_location("r71", HERE / "71-korea-transfer.py")
r71 = _u.module_from_spec(_s2)
_s2.loader.exec_module(r71)

OUT = ROOT / ".cache" / "bt5y" / "out"
SUB = ROOT / ".cache" / "bt5y" / "sub"
COST = (0.0, 0.002)
TOPQ, LO, HI, STOP = 0.27, 0.10, 0.30, 8.0
YEARS = tuple(range(2021, 2027))
SPLIT = "2024-01-01"
N_SEED = 200
N_PLACEBO = 200


def band(ev, n):
    with r41.Cost(*COST):
        rs = [sf.sim_frac(ev, slots=5, seed=i, sizing="cash") for i in range(n)]
    return rs


def med(rs):
    return st.median(x["equity_pct"] for x in rs)


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 20 if quick else N_SEED
    n_plc = 20 if quick else N_PLACEBO
    print("=" * 96, flush=True)
    print("88 — 한국에서 «한국 것»을 찾는다 (사전등록 tasks/88 · 4a50d44d)", flush=True)
    print("=" * 96, flush=True)

    by = {}
    for y in YEARS:
        f = SUB / ("krpath_%d.json" % y)
        if not f.exists():
            print("🚨 %s 없음" % f.name)
            return 2
        by[y] = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    pack = json.loads((OUT / "71-monthly-kr.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    # 🚨 71번은 깃발을 «본문에» 만든다(재사용 함수가 없다) → **같은 코드를 그대로 옮긴다**.
    #    옮겨 적은 것이므로 관문 ⓪ 로 「71번과 같은 수가 나오는가」를 찍는다.
    months = sorted({m for d in monthly.values() for m in d})
    sec_top, in_pct = {}, {}
    for ym in months:
        base = r71.prev_ym(ym, 6)
        bysec = defaultdict(list)
        for t, d in monthly.items():
            a, b = d.get(base), d.get(ym)
            sc = sector.get(t)
            if not a or not b or a <= 0 or not sc:
                continue
            bysec[sc].append((b / a - 1, t))
        sm = {sc: st.mean(x for x, _ in l) for sc, l in bysec.items() if len(l) >= 5}
        if not sm:
            continue
        k = max(1, int(round(len(sm) * TOPQ)))
        sec_top[ym] = set(sorted(sm, key=lambda x: -sm[x])[:k])
        pct = {}
        for sc, l in bysec.items():
            l.sort(key=lambda x: -x[0])
            n = len(l)
            for i, (_r, t) in enumerate(l):
                pct[t] = i / n
        in_pct[ym] = pct
    print("관문 ⓪  업종 순위 %d개월 · 상위 %.0f%% = 중앙 **%d개 업종**  (71번과 같아야 한다)"
          % (len(sec_top), TOPQ * 100, st.median(len(v) for v in sec_top.values())),
          flush=True)

    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev0, _b = r41.replay(by, lambda p: r41.resolve_half_then_trail(p, STOP, 20.0))
    print("진입 전수 **%d건**" % len(ev0), flush=True)

    def q_of(e):
        return in_pct.get(r71.prev_ym(e["scan_date"][:7], 1), {}).get(e["code"])

    def in_top(e):
        s = sector.get(e["code"])
        if not s:
            return True
        tp = sec_top.get(r71.prev_ym(e["scan_date"][:7], 1))
        return True if tp is None else (s in tp)

    def grade(e, lo, hi):
        q = q_of(e)
        return q is None or (lo <= q < hi)

    CELLS = (
        ("① 전수(필터 없음)", lambda e: True),
        ("② 주도업종만", in_top),
        ("③ 2·3등급만", lambda e: grade(e, LO, HI)),
        ("④ 1등급만", lambda e: grade(e, 0.0, LO)),
        ("⑤ 업종 ∧ 2·3등급 (미국판)", lambda e: in_top(e) and grade(e, LO, HI)),
        ("⑥ 업종 ∧ 1등급", lambda e: in_top(e) and grade(e, 0.0, LO)),
    )

    # ── 관문 ① — 날짜로만 가른다 ────────────────────────────────────────
    ins = [e for e in ev0 if e["entry_date"] < SPLIT]
    outs = [e for e in ev0 if e["entry_date"] >= SPLIT]
    print("관문 ①  표본 안 %s ~ · **%d건**   |   표본 밖 %s ~ · **%d건**  (합 %d = 전수 %s)"
          % (min(e["entry_date"] for e in ins), len(ins), SPLIT, len(outs),
             len(ins) + len(outs), "일치" if len(ins) + len(outs) == len(ev0) else "🚨 불일치"),
          flush=True)

    # ══ 표본 «안» — 여기서만 고른다 ═════════════════════════════════════
    print("\n" + "=" * 96, flush=True)
    print("【표본 안】 2021-02 ~ 2023-12 — **여기서 «고른다»**", flush=True)
    print("=" * 96, flush=True)
    print("   %-26s %8s %8s %12s %12s" % ("칸", "진입", "비율", "자산중앙", "5% 하단"), flush=True)
    print("   " + "-" * 72, flush=True)
    IN = {}
    for nm, fn in CELLS:
        ev = [e for e in ins if fn(e)]
        if len(ev) < 100:
            print("   %-26s %8d  (표본 부족 → 건너뜀)" % (nm, len(ev)), flush=True)
            continue
        rs = band(ev, n_seed)
        eq = sorted(x["equity_pct"] for x in rs)
        IN[nm] = {"med": st.median(eq), "p5": eq[int(n_seed * .05)], "n": len(ev),
                  "frac": len(ev) / len(ins), "fn": fn}
        print("   %-26s %8d %7.1f%% %+11.2f%% %+11.2f%%"
              % (nm, len(ev), 100 * IN[nm]["frac"], IN[nm]["med"], IN[nm]["p5"]), flush=True)

    pick = max(IN, key=lambda k: IN[k]["med"])
    print("\n   ★ **표본 «안»에서 고른 칸 = `%s`**  (자산 중앙 %+.2f%%)"
          % (pick, IN[pick]["med"]), flush=True)
    print("   🚨 관문 ② — 이 선택은 «표본 안» 값으로만 했다. 표본 밖은 아직 «안 봤다».",
          flush=True)

    # ══ 표본 «밖» — 한 번만 잰다 ════════════════════════════════════════
    print("\n" + "=" * 96, flush=True)
    print("【표본 밖】 2024-01 ~ — **여기서만 «잰다» · 한 번**", flush=True)
    print("=" * 96, flush=True)
    base_out = [e for e in outs if True]
    sel_out = [e for e in outs if IN[pick]["fn"](e)]
    frac_out = len(sel_out) / len(base_out)
    rs_b = band(base_out, n_seed)
    rs_s = band(sel_out, n_seed)
    print("   전수 %d건 → 고른 칸 **%d건 (%.1f%%)**" % (len(base_out), len(sel_out),
                                                       100 * frac_out), flush=True)
    print("   %-26s %12s %12s %9s" % ("", "자산중앙", "5% 하단", "MDD"), flush=True)
    for nm, rs in (("전수(필터 없음)", rs_b), ("★ %s" % pick, rs_s)):
        eq = sorted(x["equity_pct"] for x in rs)
        print("   %-26s %+11.2f%% %+11.2f%% %8.1f%%"
              % (nm, st.median(eq), eq[int(n_seed * .05)],
                 st.median(x["mdd_pct"] for x in rs)), flush=True)

    pr = sorted(((1 + a["equity_pct"] / 100) / (1 + b["equity_pct"] / 100) - 1) * 100
                for a, b in zip(rs_s, rs_b))
    pw = 100.0 * sum(1 for x in pr if x > 0) / len(pr)
    okA = pr[len(pr) // 2] > 0 and pw > 50
    print("\n**A★** 짝지은 %d판 — 중앙 **%+.2f%%** · 5%% %+.2f%% · **이기는 판 %.1f%%** → **%s**"
          % (n_seed, pr[len(pr) // 2], pr[int(n_seed * .05)], pw,
             "통과" if okA else "미통과"), flush=True)

    # ══ 🚨 가짜약 — 「덜 사는 것」과 가르기 (유형 26) ═══════════════════
    print("\n★★ **가짜약 %d판** — «뜻 없는» 기준(종목코드 해시)으로 «같은 비율»만 남긴다"
          % n_plc, flush=True)
    rnd = random.Random(88088088)
    plc = []
    for i in range(n_plc):
        r2 = random.Random("plc%d" % i)
        keep = {c for c in {e["code"] for e in base_out}
                if random.Random("plc%d|%s" % (i, c)).random() < frac_out}
        ev = [e for e in base_out if e["code"] in keep]
        if len(ev) < 50:
            continue
        rs = band(ev, max(5, n_seed // 10))
        p2 = sorted(((1 + a["equity_pct"] / 100) / (1 + b["equity_pct"] / 100) - 1) * 100
                    for a, b in zip(rs, rs_b[:len(rs)]))
        plc.append((p2[len(p2) // 2], len(ev)))
        if i % 40 == 0:
            print("     가짜약 %d/%d" % (i, n_plc), flush=True)
    pm = sorted(x[0] for x in plc)
    nn = [x[1] for x in plc]
    print("   관문 ③ 양성 대조 — 가짜약 진입 수 중앙 **%d건** vs 고른 칸 **%d건** (비율 %.1f%%) → **%s**"
          % (st.median(nn), len(sel_out), 100 * frac_out,
             "통과" if abs(st.median(nn) - len(sel_out)) < 0.15 * len(sel_out) else "🚨 어긋남"),
          flush=True)
    print("   가짜약 짝 중앙의 분포 — 보통 **%+.2f%%** · 5%% %+.2f%% · **95%% %+.2f%%** · "
          "최소 %+.2f%% · 최대 %+.2f%%"
          % (pm[len(pm) // 2], pm[int(len(pm) * .05)], pm[int(len(pm) * .95)], pm[0], pm[-1]),
          flush=True)
    pct = 100.0 * sum(1 for x in pm if x < pr[len(pr) // 2]) / len(pm)
    _q = pct / 100.0
    se = 100.0 * math.sqrt(max(_q * (1 - _q), 1e-12) / len(pm))
    okN = pct >= 95.0
    print("   **N★** 관측 %+.2f%% = **%.1f 백분위** [몬테카를로 95%% %.1f ~ %.1f · 판수 %d] → **%s**"
          % (pr[len(pr) // 2], pct, max(0, pct - 1.96 * se), min(100, pct + 1.96 * se),
             len(pm), "통과" if okN else "미통과"), flush=True)

    # ══ 판정 ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 96, flush=True)
    print("사전등록 §3 판정", flush=True)
    print("  A★  %s  — 짝 중앙 %+.2f%% · 이기는 판 %.1f%%"
          % ("✅ 통과" if okA else "❌ 미통과", pr[len(pr) // 2], pw), flush=True)
    print("  N★  %s  — 가짜약 %.1f 백분위 (문턱 95)"
          % ("✅ 통과" if okN else "❌ 미통과", pct), flush=True)
    if okA and okN:
        print("\n  → **「한국에도 선별 우위가 있다」로 쓸 수 있다.**", flush=True)
    elif okA:
        print("\n  → 🚨 **«못 가림» — 우위는 보이나 「덜 사는 것」과 구분이 안 된다.**", flush=True)
    else:
        print("\n  → **미통과. 표본 안에서 고른 칸이 표본 밖에서 «서지 않는다».**", flush=True)
    print("  🚨 「최적 필터는 X」라고 쓰지 않는다. 여섯 중 «표본 안»에서 고른 하나를 잰 것이다.",
          flush=True)
    print("  ⚠️ 지수 비교는 문턱이 «아니다»(사전등록 §5) — 같은 창 KOSPI 는 서술로만 적는다.",
          flush=True)

    (OUT / "88-korea-own-edge.json").write_text(json.dumps(
        {"split": SPLIT, "n_ev": len(ev0), "n_in": len(ins), "n_out": len(outs),
         "in_cells": {k: {x: y for x, y in v.items() if x != "fn"} for k, v in IN.items()},
         "pick": pick, "n_sel_out": len(sel_out), "frac_out": frac_out,
         "pair_median": pr[len(pr) // 2], "pair_win": pw, "okA": okA,
         "plc_pct": pct, "plc_med": pm[len(pm) // 2], "plc_p95": pm[int(len(pm) * .95)],
         "n_plc": len(pm), "okN": okN, "n_seed": n_seed},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 88-korea-own-edge.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

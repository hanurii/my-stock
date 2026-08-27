# -*- coding: utf-8 -*-
"""88v — **표본 밖 −0.98%가 «한 번의 분할»에서 나온 값이다.** (두뇌 물음 ③)

88 은 표본 밖(2024-01 ~ 2026-08 · 1,701건)을 **한 덩어리**로 재서
「표본 안 7.5배가 표본 밖에서 전수보다 나빠졌다 = 과적합」으로 닫았다.
🚨 **그 구간이 «특이한 해»였을 가능성은 안 쟀다.**

여기서는 표본 밖을 **연도로 쪼개** 같은 짝비교를 다시 한다.
  · 세 해가 «전부» 마이너스면 → 「한 해 탓」이 아니다. 88 이 «더» 단단해진다.
  · 한 해만 크게 마이너스면 → 「과적합」이 아니라 「그 해」일 수 있다.
그리고 **표본 «안»도 같은 방식으로 연도별**로 쪼개, 7.5배가 세 해에 고른지 본다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/88v-byyear.py [N_SEED]
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r88", HERE / "88-korea-own-edge.py")
r88 = _u.module_from_spec(_s)
_s.loader.exec_module(r88)
r71, r41, sf = r88.r71, r88.r41, r88.sf

NS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200


def main() -> int:
    by = {}
    for y in r88.YEARS:
        by[y] = json.loads((r88.SUB / ("krpath_%d.json" % y)).read_text(
            encoding="utf-8"))["trigger_paths"]
    pack = json.loads((r88.OUT / "71-monthly-kr.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({m for d in monthly.values() for m in d})
    sec_top, in_pct = {}, {}
    for ym in months:
        base = r71.prev_ym(ym, 6)
        bysec = defaultdict(list)
        for tk, d in monthly.items():
            a_, b_ = d.get(base), d.get(ym)
            sc = sector.get(tk)
            if not a_ or not b_ or a_ <= 0 or not sc:
                continue
            bysec[sc].append((b_ / a_ - 1, tk))
        # 🚨 88 의 코드를 «그대로» 옮긴다 — 처음엔 median·len≥3·int() 로 «다시 만들었다가»
        #    주도업종 표본밖 중앙이 −0.98% 대신 −24.82% 로 나와 어긋났다.
        #    (88 은 mean · len≥5 · round() 다. 재구현하지 말고 베낀다.)
        sm = {sc: st.mean(x for x, _ in l) for sc, l in bysec.items() if len(l) >= 5}
        if not sm:
            continue
        k = max(1, int(round(len(sm) * r88.TOPQ)))
        sec_top[ym] = set(sorted(sm, key=lambda x: -sm[x])[:k])
        pct = {}
        for sc, l in bysec.items():
            l.sort(key=lambda x: -x[0])
            for i, (_r, tk) in enumerate(l):
                pct[tk] = i / len(l)
        in_pct[ym] = pct

    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev0, _b = r41.replay(by, lambda p: r41.resolve_half_then_trail(p, r88.STOP, 20.0))

    def in_top(e):
        s = sector.get(e["code"])
        if not s:
            return True
        tp = sec_top.get(r71.prev_ym(e["scan_date"][:7], 1))
        return True if tp is None else (s in tp)

    print("=" * 98)
    print("88v — 표본 밖을 «연도»로 쪼갠다  (진입 전수 %d · seed %d)" % (len(ev0), NS))
    print("=" * 98, flush=True)
    print("  ★ 88 은 표본 밖을 «한 덩어리»로 재서 「과적합」을 적었다.", flush=True)
    print("    세 해가 다 마이너스면 88 이 더 단단해지고, 한 해뿐이면 「그 해」일 수 있다.\n",
          flush=True)
    print("  %-12s %7s %7s %11s %11s %11s %10s"
          % ("구간", "전수 n", "주도 n", "전수 중앙", "주도 중앙", "짝 중앙", "이기는 판"),
          flush=True)
    print("  " + "-" * 78, flush=True)

    def one(lab, sub):
        a = [e for e in sub]
        b = [e for e in sub if in_top(e)]
        if len(b) < 30:
            print("  %-12s %7d %7d  (표본 부족 → 건너뜀)" % (lab, len(a), len(b)), flush=True)
            return
        ra, rb = r88.band(a, NS), r88.band(b, NS)
        ea = [x["equity_pct"] for x in ra]
        eb = [x["equity_pct"] for x in rb]
        pr = sorted(((1 + y / 100) / (1 + x / 100) - 1) * 100 for x, y in zip(ea, eb))
        pw = 100.0 * sum(1 for x in pr if x > 0) / len(pr)
        print("  %-12s %7d %7d %+10.2f%% %+10.2f%% %+10.2f%% %9.1f%%"
              % (lab, len(a), len(b), st.median(ea), st.median(eb),
                 pr[len(pr) // 2], pw), flush=True)

    ins = [e for e in ev0 if e["entry_date"] < r88.SPLIT]
    outs = [e for e in ev0 if e["entry_date"] >= r88.SPLIT]
    one("표본안 전체", ins)
    for y in ("2021", "2022", "2023"):
        one("  · %s" % y, [e for e in ins if e["entry_date"][:4] == y])
    print("  " + "-" * 78, flush=True)
    one("표본밖 전체", outs)
    for y in ("2024", "2025", "2026"):
        one("  · %s" % y, [e for e in outs if e["entry_date"][:4] == y])

    print("\n  ★ 읽는 법 — 「짝 중앙」이 표본 밖 **세 해 다** 음수면 「한 해 탓」이 아니다.", flush=True)
    print("    그리고 표본 «안» 세 해가 고르게 양수여야 「표본 안 7.5배」가 «구간 하나»가 아니다.",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

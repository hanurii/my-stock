# -*- coding: utf-8 -*-
"""130 — 「연마다 몇 개를 사고팔았나」 (사용자 질문 2026-08-30). 묘사이지 판정이 아니다."""
from __future__ import annotations
import importlib.util as _u, statistics as st, sys, json
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
def _load(m, f):
    s = _u.spec_from_file_location(m, HERE / f); x = _u.module_from_spec(s); s.loader.exec_module(x); return x
r91 = _load("r91", "91-us-out-of-sample.py"); r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py"); f92a = r102.f92a
YEARS = tuple(range(1999, 2027))
CFG = ((20.0, 10.0, "현행 +20/-10"), (25.0, 8.0, "+25/-8"), (30.0, 10.0, "+30/-10"))

def main():
    n_seed = 10
    (_a, _b, by2), missing, _ = r91.load_ladder(YEARS, "1999-04-01", "2026-08-21",
                                                "91-monthly-us-full.json", use_ext=False)
    if missing: print("경로 없음", flush=True); return 2
    fund, ixf = f92a.load(); ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False: k.append(p)
        by_f[y] = k
    out = {}
    for tg, sp, nm in CFG:
        r91.TARGET, r91.STOP = tg, sp
        ev, _b1, _b2 = r91.replay(by_f)
        rs = r91.sim(ev, n_seed)
        per, hold, res = [], [], Counter()
        for x in rs:
            cnt = Counter(f[3][:4] for f in x["fill_log"] if f[1] == "pilot")
            per.append(cnt)
            for t in ev: pass
            for d, r_, _t in x["ret_log"]:
                res["win" if r_ > 0 else "lose"] += 1
        yrs = sorted({y for c in per for y in c})
        med = {y: st.median(c.get(y, 0) for c in per) for y in yrs}
        vals = sorted(med.values())
        out[nm] = {"per_year": med, "min": vals[0], "med": vals[len(vals)//2], "max": vals[-1],
                   "avg": sum(vals)/len(vals)}
        print("\n### %s — 연마다 «산» 종목 수 (운의 번호 %d판 중앙)" % (nm, n_seed), flush=True)
        print("   평균 **%.1f개/년** · 중앙 %.0f · 가장 적은 해 **%.0f** · 가장 많은 해 **%.0f**"
              % (out[nm]["avg"], out[nm]["med"], out[nm]["min"], out[nm]["max"]), flush=True)
        line = "   "
        for y in yrs:
            line += "%s %2.0f  " % (y[2:], med[y])
            if len(line) > 96: print(line, flush=True); line = "   "
        if line.strip(): print(line, flush=True)
    (r91.OUT / "130-yearly.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("\n저장: 130-yearly.json", flush=True)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())

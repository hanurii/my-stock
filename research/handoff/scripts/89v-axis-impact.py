# -*- coding: utf-8 -*-
"""89v 부속 — **A 축에 남은 «가짜 점프»가 실제로 무는가.**

찾은 것 — `fltRt` 가 한국 일일 제한(±30%)을 **넘는 값이 724건** 있다(최대 +29,948%).
즉 **`fltRt` 는 «대체로» 조정값이지만 «항상»은 아니다.** 그러면 A 축(등락률 누적)에도
가짜 점프가 남는다 — 89 의 수정이 이 자리를 못 막았다.

그래서 «크기»를 잰다:
  ㉠ 오염된 종목이 몇 개이고, 그중 «진입이 있는» 종목은 몇 개인가
  ㉡ 진입 3,548건 중 **특징 창(진입 전 300봉) 안에** 가짜 점프가 든 건은 몇 건인가
  ㉢ 그 건들을 «빼면» 89 의 헤드라인(base_depth 1분위 +8.29%p)이 얼마나 움직이나
     → 안 움직이면 「실재하지만 안 문다」로 닫힌다. 움직이면 89 를 다시 돌려야 한다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/89v-axis-impact.py
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r89", HERE / "89-korea-entry-predictors.py")
r89 = _u.module_from_spec(_s)
_s.loader.exec_module(r89)
r85, r71, r41 = r89.r85, r89.r71, r89.r41

LIMIT = 31.0


def hr(t):
    print("\n" + "=" * 98, flush=True)
    print(t, flush=True)
    print("=" * 98, flush=True)


def main() -> int:
    by = {}
    for y in r89.YEARS:
        by[y] = json.loads((r89.SUB / ("krpath_%d.json" % y)).read_text(
            encoding="utf-8"))["trigger_paths"]
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev, _b = r41.replay(by, lambda p: r41.resolve_half_then_trail(p, r89.STOP, 20.0))
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by.values() for p in ps}
    for e in ev:
        p = pmap.get((e["scan_date"], e["code"], e.get("pattern", "")))
        if p:
            e["entry_px"] = p["entry_price"]
            e["pivot"] = p.get("pivot")
            e["atr_band"] = p.get("atr_band", "?")
    ser = r89.load_pdata()

    hr("㉠ 오염된 종목 — `fltRt` 가 ±30%% 를 넘는 날이 있는 종목")
    bad_days = {}
    for code, x in ser.items():
        idx = [i for i, v in enumerate(x["f"]) if abs(v) > LIMIT]
        if idx:
            bad_days[code] = idx
    ev_codes = {t["code"] for t in ev}
    hit = sorted(set(bad_days) & ev_codes)
    print("  pdata 종목 %d개 중 오염 **%d개** · 진입이 있는 종목 %d개 중 **%d개가 오염**"
          % (len(ser), len(bad_days), len(ev_codes), len(hit)), flush=True)
    tot = sum(len(v) for v in bad_days.values())
    print("  오염일 합 %d건 (종목당 중앙 %d건)"
          % (tot, st.median([len(v) for v in bad_days.values()]) if bad_days else 0),
          flush=True)

    hr("㉡ 진입 %d건 중 «특징 창»(진입 전 %d봉) 안에 가짜 점프가 든 건" % (len(ev), r89.MIN_PRE))
    tainted, ok_n = set(), 0
    for t in ev:
        code = t["code"]
        s = ser.get(code)
        if not s or not s["d"]:
            continue
        k = bisect.bisect_left(s["d"], t["entry_date"])
        if k < r89.MIN_PRE:
            continue
        ok_n += 1
        lo = k - r89.MIN_PRE
        for i in bad_days.get(code, ()):
            if lo <= i < k:
                tainted.add((t["scan_date"], t["code"], t.get("pattern", "")))
                break
    print("  특징이 만들어진 진입 %d건 중 **오염 %d건 (%.2f%%)**"
          % (ok_n, len(tainted), 100.0 * len(tainted) / max(1, ok_n)), flush=True)
    yr = Counter(k[0][:4] for k in tainted)
    print("  오염 진입의 연도 분포: %s" % dict(sorted(yr.items())), flush=True)

    hr("㉢ 오염된 진입을 «빼면» 헤드라인이 움직이나")
    print("  🚨 판정은 «빼기 전»이 정본이다. 여기서는 «흔들리는 폭»만 본다.\n", flush=True)
    pack = json.loads((r89.OUT / "71-monthly-kr.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({m for d in monthly.values() for m in d})
    in_pct = {}
    for ym in months:
        base = r71.prev_ym(ym, 6)
        bysec = {}
        for tk, d in monthly.items():
            a_, b_ = d.get(base), d.get(ym)
            sc = sector.get(tk)
            if not a_ or not b_ or a_ <= 0 or not sc:
                continue
            bysec.setdefault(sc, []).append((b_ / a_ - 1, tk))
        pct = {}
        for sc, l in bysec.items():
            l.sort(key=lambda x: -x[0])
            for i, (_r, tk) in enumerate(l):
                pct[tk] = i / len(l)
        in_pct[ym] = pct
    rows = r89.build_features(ev, ser, in_pct)
    r85.FEATS, r85.CAT, r85.NQ, r85.SPLIT, r85.BONF = (
        r89.FEATS, r89.CAT, r89.NQ, r89.SPLIT, r89.BONF)

    def mfe(t):
        p = pmap[(t["scan_date"], t["code"], t.get("pattern", ""))]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(t["resolve_date"]) if t.get("resolve_date") in p["d"] \
            else len(p["d"]) - 1
        return (max(p["h"][i0:i1 + 1]) / t["entry_px"] - 1) * 100

    m = {}
    for t in ev:
        k = (t["scan_date"], t["code"], t.get("pattern", ""))
        if k in rows:
            try:
                m[k] = mfe(t)
            except (KeyError, ValueError, IndexError):
                pass

    def build(drop):
        ins, outs = [], []
        for t in ev:
            k = (t["scan_date"], t["code"], t.get("pattern", ""))
            if k not in rows or k not in m:
                continue
            if drop and k in tainted:
                continue
            y = 1.0 if m[k] >= 20 else 0.0
            (ins if t["entry_date"] < r89.SPLIT else outs).append((rows[k], y))
        return ins, outs

    for lab, drop in (("빼기 «전» (89 정본)", False), ("오염 %d건 «뺀» 뒤" % len(tainted), True)):
        ins, outs = build(drop)
        bb = st.mean([y for _r, y in outs])
        best, bf = None, None
        for f in r89.FEATS:
            rr = r85.test_one(ins, outs, f, "")
            if rr and (best is None or rr[0] - bb > best):
                best, bf = rr[0] - bb, f
        print("  %-26s 표본안 %d · 표본밖 %d · 기준율 %.2f%% · 최선 `%s` **%+.2f%%p**"
              % (lab, len(ins), len(outs), bb * 100, bf, best * 100), flush=True)
    print("\n  ★ 두 줄의 차가 작으면 **「실재하지만 안 문다」**로 닫힌다.", flush=True)
    print("    크면 89 를 «오염 제거 후»로 다시 돌려야 한다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

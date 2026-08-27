# -*- coding: utf-8 -*-
"""89 — **한국에서 «진입 시점»으로 가를 수 있나**. 사전등록 `tasks/89` (`09f9e20a`)

🚨 **85번(미국)의 검정 엔진을 «그대로» 쓴다** — `test_one` · `test_fast` · `_shuf_year` ·
   `precompute` · `gate_fast` 를 import 해서 쓴다. **자료만 한국으로 간다.**
   그래야 「설계가 달라서 결과가 다르다」를 배제할 수 있다.
🚨 판수 4,000 · 연도 «안» 섞기 · 본페로니 2 를 **처음부터** 건다(유형 25).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/89-korea-entry-predictors.py [--quick]
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import json
import math
import os
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

_s2 = _u.spec_from_file_location("r71", HERE / "71-korea-transfer.py")
r71 = _u.module_from_spec(_s2)
_s2.loader.exec_module(r71)

# 🚨 미국 85번의 «엔진»을 그대로 쓴다 (BT_Y0 없이도 모듈 적재는 된다)
os.environ.setdefault("BT_Y0", "2017")
_s3 = _u.spec_from_file_location("r85", HERE / "85-entry-predictors.py")
r85 = _u.module_from_spec(_s3)
_s3.loader.exec_module(r85)

OUT = ROOT / ".cache" / "bt5y" / "out"
SUB = ROOT / ".cache" / "bt5y" / "sub"
PD = ROOT / ".cache" / "pdata"
TOPQ, STOP = 0.27, 8.0
YEARS = tuple(range(2021, 2027))
SPLIT = "2024-01-01"          # 🚨 88번과 «같은» 경계
N_NULL = 4000
NQ = 5
BONF = 2
MIN_PRE = 300                 # 진입 전 봉 수 하한
# 🚨 처음 130 으로 뒀더니 관문 ①′ 가 «구조적으로 못 타는» 자리라고 잡았다(최소 253).
#    85번에서 같은 일이 있었다(유형 24) — 「0건」이 «검사 결과»가 아니라 «검사가 없었다»는 뜻.
#    300 이면 실제로 걸린다. hi52(252일)에도 여유가 생긴다.
FEATS = ("pattern", "atr_band", "gap", "prior6m", "hi52", "base_depth",
         "ma200", "atr20", "in_pct", "logpx", "logcap", "turnover")
CAT = ("pattern", "atr_band")


# ═════════════════════════════════════════════════════════════════════════
def load_pdata():
    """일별 파일 → 종목별 시계열. 종가·고가·저가·시총·거래대금."""
    fs = sorted(PD.glob("price_*.json"))
    ser = defaultdict(lambda: {"d": [], "c": [], "h": [], "l": [], "cap": [], "trp": []})
    for f in fs:
        d = f.name[6:14]
        ds = "%s-%s-%s" % (d[:4], d[4:6], d[6:])
        try:
            rows = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for code, r in rows.items():
            try:
                c = float(r["clpr"])
                if c <= 0:
                    continue
                s = ser[code]
                s["d"].append(ds)
                s["c"].append(c)
                s["h"].append(float(r.get("hipr") or c))
                s["l"].append(float(r.get("lopr") or c))
                s["cap"].append(float(r.get("mrktTotAmt") or 0))
                s["trp"].append(float(r.get("trPrc") or 0))
            except (TypeError, ValueError, KeyError):
                continue
    print("   pdata %d일 · 종목 %d개 적재" % (len(fs), len(ser)), flush=True)
    return ser


def build_features(ev, ser, in_pct):
    rows, miss, kstat = {}, Counter(), []
    for e in ev:
        code = e["code"]
        s = ser.get(code)
        if not s or not s["d"]:
            miss["시계열 없음"] += 1
            continue
        k = bisect.bisect_left(s["d"], e["entry_date"])   # 🚨 진입일 «미포함»
        kstat.append(k)
        if k < MIN_PRE:
            miss["과거 봉 부족"] += 1
            continue
        cl, hh, ll = s["c"][:k], s["h"][:k], s["l"][:k]
        cap, trp = s["cap"][:k], s["trp"][:k]
        px = e["entry_px"] if "entry_px" in e else e.get("entry_price")
        if not px:
            miss["진입가 없음"] += 1
            continue
        w52 = max(hh[-252:]) if len(hh) >= 252 else max(hh)
        b60h, b60l = max(hh[-60:]), min(ll[-60:])
        m = min(20, len(cl) - 1)
        tr = [max(hh[i] - ll[i], abs(hh[i] - cl[i - 1]), abs(ll[i] - cl[i - 1]))
              for i in range(len(cl) - m, len(cl))]
        cp = [x for x in cap[-1:] if x > 0]
        tv = [x for x in trp[-50:] if x > 0]
        ym = r71.prev_ym(e["scan_date"][:7], 1)
        rows[(e["scan_date"], e["code"], e.get("pattern", ""))] = {
            "pattern": e.get("pattern", "?"),
            "atr_band": e.get("atr_band", "?"),
            "gap": (px / e["pivot"] - 1) if e.get("pivot") else 0.0,
            "prior6m": px / cl[-126] - 1,
            "hi52": px / w52,
            "base_depth": (b60h - b60l) / b60h if b60h else 0.0,
            "ma200": px / (sum(cl[-200:]) / len(cl[-200:])) - 1,
            "atr20": (sum(tr) / m) / px if m else float("nan"),
            "in_pct": in_pct.get(ym, {}).get(code, float("nan")),
            "logpx": math.log(max(px, 1e-6)),
            "logcap": math.log(cp[0]) if cp else float("nan"),
            "turnover": math.log(st.mean(tv)) if tv else float("nan"),
        }
    ks = sorted(kstat)
    print("   특징 만든 거래 **%d / %d** · 결측 %s" % (len(rows), len(ev), dict(miss)),
          flush=True)
    if ks:
        print("   관문 ①′ 진입 전 봉 수 — **최소 %d** · P1 %d · 중앙 %d · 문턱 %d → **%s**"
              % (ks[0], ks[len(ks) // 100], ks[len(ks) // 2], MIN_PRE,
                 "관문이 «탈 수 있는» 자리에 있다 (걸린 것 %d건)"
                 % sum(1 for x in ks if x < MIN_PRE) if ks[0] < MIN_PRE
                 else "🚨 최소 %d > 문턱 %d → «구조적으로 못 타는» 관문 (유형 24)"
                 % (ks[0], MIN_PRE)), flush=True)
    return rows


# ═════════════════════════════════════════════════════════════════════════
def run_outcome(rows, ev, ykey, name, base_thresh, n_null):
    r85.FEATS, r85.CAT, r85.NQ, r85.SPLIT, r85.BONF = FEATS, CAT, NQ, SPLIT, BONF
    ins, outs, yr_in, yr_out = [], [], [], []
    for e in ev:
        k = (e["scan_date"], e["code"], e.get("pattern", ""))
        if k not in rows:
            continue
        y, yr = ykey(e), e["entry_date"][:4]
        if e["entry_date"] < SPLIT:
            ins.append((rows[k], y)); yr_in.append(yr)
        else:
            outs.append((rows[k], y)); yr_out.append(yr)
    b_in = st.mean([y for _r, y in ins])
    b_out = st.mean([y for _r, y in outs])
    print("\n" + "─" * 96, flush=True)
    print("▶ **%s** — 표본안 %d건(기준율 %.2f%%) · 표본밖 %d건(기준율 **%.2f%%** · 사건 %d건)"
          % (name, len(ins), b_in * 100, len(outs), b_out * 100, round(b_out * len(outs))),
          flush=True)
    print("   한 건이 **%.2f%%p**" % (100.0 / max(1, len(outs))), flush=True)
    print("   %-11s %9s %10s %11s %s" % ("특징", "표본밖n", "상위분위", "기준율차", "고른 것"),
          flush=True)
    print("   " + "-" * 68, flush=True)
    res, meta = {}, {}
    for f in FEATS:
        r = r85.test_one(ins, outs, f, name)
        if r is None:
            print("   %-11s (분위·표본 부족 → 건너뜀)" % f, flush=True)
            continue
        rate, base, pick, nn, _why = r
        res[f] = rate - base
        meta[f] = pick
        print("   %-11s %9d %9.2f%% %+10.2f%%p %s"
              % (f, nn, rate * 100, (rate - base) * 100, pick), flush=True)
    if not res:
        return None
    bf = max(res, key=lambda f: res[f])
    obs = res[bf]
    print("\n   **관측 최선 = `%s`  %+.2f%%p** (등록 문턱 %+.2f%%p) · 고른 것 %s"
          % (bf, obs * 100, base_thresh * 100, meta[bf]), flush=True)

    pre = r85.precompute(ins, outs)
    if not r85.gate_fast(pre, ins, outs, name):
        return None
    import random as _rnd
    rnd = _rnd.Random(89089089)
    ys_in = [y for _r, y in ins]
    ys_out = [y for _r, y in outs]
    null = []
    for it in range(n_null):
        zi = r85._shuf_year(ys_in, yr_in, rnd, "year")
        zo = r85._shuf_year(ys_out, yr_out, rnd, "year")
        best = -9.0
        for f in pre:
            rr = r85.test_fast(pre, f, zi, zo)
            if rr:
                best = max(best, rr[0] - rr[1])
        null.append(best)
        if it % 1000 == 0:
            print("     귀무(연도 안) %d/%d" % (it, n_null), flush=True)
    a = sorted(null)
    pct = 100.0 * sum(1 for x in a if x < obs) / len(a)
    thr = 100.0 * (1 - 0.05 / BONF)
    _p = pct / 100.0
    se = 100.0 * math.sqrt(max(_p * (1 - _p), 1e-12) / len(a))
    print("   **N★ 귀무 %d회 (연도 안)** — 「%d칸 중 최선」이 우연으로: "
          "보통 %+.2f%%p · 95%% %+.2f%%p · **97.5%% %+.2f%%p** · 최대 %+.2f%%p"
          % (n_null, len(FEATS), a[len(a) // 2] * 100, a[int(len(a) * .95)] * 100,
             a[int(len(a) * .975)] * 100, a[-1] * 100), flush=True)
    okN, okA = pct >= thr, obs > base_thresh
    print("   → 관측 %+.2f%%p = **%.1f 백분위** [몬테카를로 95%% %.1f ~ %.1f] · 문턱 %.1f · "
          "**N %s** · **A %s**"
          % (obs * 100, pct, max(0, pct - 1.96 * se), min(100, pct + 1.96 * se), thr,
             "✅ 통과" if okN else "❌ 미통과", "✅ 통과" if okA else "❌ 미통과"), flush=True)
    return {"best": bf, "pick": meta[bf], "obs": obs, "pct": pct, "okN": okN, "okA": okA,
            "base_in": b_in, "base_out": b_out, "n_in": len(ins), "n_out": len(outs),
            "all": res, "meta": meta, "null_p975": a[int(len(a) * .975)]}


def main() -> int:
    quick = "--quick" in sys.argv
    n_null = 60 if quick else N_NULL
    print("=" * 96, flush=True)
    print("89 — 한국에서 «진입 시점»으로 가를 수 있나 (사전등록 tasks/89 · 09f9e20a)", flush=True)
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
    months = sorted({m for d in monthly.values() for m in d})
    in_pct = {}
    for ym in months:
        base = r71.prev_ym(ym, 6)
        bysec = defaultdict(list)
        for t, d in monthly.items():
            a_, b_ = d.get(base), d.get(ym)
            sc = sector.get(t)
            if not a_ or not b_ or a_ <= 0 or not sc:
                continue
            bysec[sc].append((b_ / a_ - 1, t))
        pct = {}
        for sc, l in bysec.items():
            l.sort(key=lambda x: -x[0])
            for i, (_r, t) in enumerate(l):
                pct[t] = i / len(l)
        in_pct[ym] = pct

    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev0, _b = r41.replay(by, lambda p: r41.resolve_half_then_trail(p, STOP, 20.0))
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by.values() for p in ps}
    for e in ev0:
        p = pmap.get((e["scan_date"], e["code"], e.get("pattern", "")))
        if p:
            e["entry_px"] = p["entry_price"]
            e["pivot"] = p.get("pivot")
            e["atr_band"] = p.get("atr_band", "?")
    print("진입 전수 **%d건** · 표본안/밖 경계 **%s** (88번과 같음)" % (len(ev0), SPLIT),
          flush=True)

    ser = load_pdata()
    rows = build_features(ev0, ser, in_pct)

    def mfe(e):
        p = pmap.get((e["scan_date"], e["code"], e.get("pattern", "")))
        if not p:
            return 0.0
        i0 = p["d"].index(e["entry_date"])
        try:
            i1 = p["d"].index(e["legs"][-1][0])
        except (KeyError, ValueError, IndexError):
            i1 = len(p["d"]) - 1
        return (max(p["h"][i0:i1 + 1]) / p["entry_price"] - 1) * 100

    M = {(e["scan_date"], e["code"], e.get("pattern", "")): mfe(e) for e in ev0}
    y20 = lambda e: 1.0 if M[(e["scan_date"], e["code"], e.get("pattern", ""))] >= 20 else 0.0
    y100 = lambda e: 1.0 if M[(e["scan_date"], e["code"], e.get("pattern", ""))] >= 100 else 0.0
    n20 = sum(y20(e) for e in ev0)
    n100 = sum(y100(e) for e in ev0)
    print("\n결과 정의 — ㉮ MFE≥+20%%: **%d건 (%.2f%%)**  ·  ㉯ MFE≥+100%%: **%d건 (%.2f%%)**"
          % (n20, 100 * n20 / len(ev0), n100, 100 * n100 / len(ev0)), flush=True)

    n_out = sum(1 for e in ev0 if e["entry_date"] >= SPLIT
                and (e["scan_date"], e["code"], e.get("pattern", "")) in rows)
    print("\n🚨 **C 판정 «먼저»** — 표본밖 %d건 · 상위 분위 ≈ %d건" % (n_out, n_out // NQ),
          flush=True)
    for nm, p0, lift in (("㉮ MFE≥20%", n20 / len(ev0), 1.18),
                         ("㉯ MFE≥100%", max(n100, 1) / len(ev0), 1.5)):
        need = r85.mde(max(1, n_out // NQ), p0, lift)
        print("   %-12s 기준율 %.2f%% · %.2f배를 가르려면 **자료 %.1f배 = %.0f년** 필요"
              % (nm, p0 * 100, lift, need, need * 5.6), flush=True)

    R = {}
    R["A"] = run_outcome(rows, ev0, y20, "㉮ 「+20% 에 닿는가」", 0.05, n_null)
    R["B"] = run_outcome(rows, ev0, y100, "㉯ 「더블(+100%) 하는가」",
                         0.5 * max(n100, 1) / len(ev0), n_null)

    print("\n" + "=" * 96, flush=True)
    print("사전등록 §4 판정", flush=True)
    for k, nm in (("A", "㉮ +20% 도달"), ("B", "㉯ 더블")):
        v = R.get(k)
        if not v:
            print("  %s — 산출 실패" % nm)
            continue
        print("  %-14s N★ %s · A★ %s   (최선 `%s` %s · %+.2f%%p · 귀무 %.1f 백분위)"
              % (nm, "✅" if v["okN"] else "❌", "✅" if v["okA"] else "❌",
                 v["best"], v["pick"], v["obs"] * 100, v["pct"]), flush=True)
    va = R.get("A")
    if va:
        p6 = va["all"].get("prior6m")
        pk = va["meta"].get("prior6m")
        print("\n**R★ 복제** — 미국 85번이 통과시킨 `prior6m` **1분위**가 한국에서도 같은 방향인가",
              flush=True)
        print("   한국 ㉮ 에서 `prior6m` 이 고른 것 = **%s** · 기준율차 %+.2f%%p → **%s**"
              % (pk, (p6 or 0) * 100,
                 "✅ 같은 방향(1분위)" if pk == "1분위" else "❌ 다른 방향"), flush=True)
    print("\n🚨 「최고의 예측 변수는 X」라고 쓰지 않는다 · 분위 «기울기»는 인용하지 않는다.",
          flush=True)

    (OUT / "89-korea-entry.json").write_text(json.dumps(
        {"split": SPLIT, "n_ev": len(ev0), "n_feat": len(rows), "n20": n20, "n100": n100,
         "res": R, "n_null": n_null}, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    print("\n저장: 89-korea-entry.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

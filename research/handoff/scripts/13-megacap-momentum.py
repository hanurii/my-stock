# -*- coding: utf-8 -*-
"""13 — 대형주 모멘텀 대조 (시점 시총판).

★ **이 과제로는 채택 판정을 내리지 않는다.** 숫자를 나란히 싣는 **대조용**이다.
   이 방식을 실제로 쓰려면 **별도 사전등록**이 필요하다.

정의(사전등록, 바꾸지 않음)
  · 유니버스: 매 교체일 시점 `market_cap_eok` **상위 30** (pdata 시점 값 — 현재 시총 금지)
  · 제외: 하네스와 같은 EXCLUDE_PATTERN + KOSPI/KOSDAQ 만(KONEX 제외)
  · 모멘텀: **252거래일 수익률**, 수정주가(01번과 같은 build_series)
  · 보유: 상위 **3종목 등금액** · 교체: **월 1회, 매월 첫 거래일 시가**
  · 비용: 매수 0.14% / 매도 0.14% + 세금 0.2% · 구간 2021-02-01 ~ 2026-08-21
  · 민감도는 **상위 5 · 분기 교체 둘만**(다중검정 억제)

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/13-megacap-momentum.py
난수 미사용.
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import slot_sim  # noqa: E402
from canslim_lib.pdata_series import build_series  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
PDATA = ROOT / ".cache" / "pdata"
START, END = "2021-02-01", "2026-08-21"
WARM = 430
TOP_UNIV = 30
MOM_DAYS = 252
FEE_BUY, FEE_SELL = 0.0014, 0.0034
EXCLUDE = re.compile(r"스팩|리츠|ETF|ETN|인프라|우$|우[A-C]$|[0-9]우[A-C]?$|리츠$")


def iter_pdata(s, e):
    a, b = s.replace("-", ""), e.replace("-", "")
    for p in sorted(PDATA.glob("price_*.json")):
        d = p.stem[6:]
        if not (a <= d <= b):
            continue
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        yield "%s-%s-%s" % (d[:4], d[4:6], d[6:]), recs


def mdd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def main():
    warm = (datetime.strptime(START, "%Y-%m-%d")
            - timedelta(days=WARM)).strftime("%Y-%m-%d")
    print("pdata 적재 %s ~ %s …" % (warm, END), flush=True)
    caps, dates_all = {}, []
    keep = set()
    for dt, recs in iter_pdata(warm, END):
        dates_all.append(dt)
        row = {}
        for c, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ"):
                continue
            nm = r.get("itmsNm") or ""
            if EXCLUDE.search(nm):
                continue
            cp = r.get("market_cap_eok")
            if cp:
                row[c] = (cp, nm)
        caps[dt] = row
        keep |= set(row)
    print("  일자 %d · 등장 종목 %d" % (len(dates_all), len(keep)), flush=True)

    print("수정주가 시계열 생성 …", flush=True)
    full = build_series((dt, {c: r for c, r in recs.items() if c in keep})
                        for dt, recs in iter_pdata(warm, END))
    print("  시계열 %d종목" % len(full), flush=True)

    cal = [d for d in dates_all if d >= START]
    idx = {c: {d: i for i, d in enumerate(s["dates"])} for c, s in full.items()}

    def px(c, d, which="closes"):
        i = idx.get(c, {}).get(d)
        return None if i is None else full[c][which][i]

    def mom(c, d):
        """d 직전 거래일 종가까지의 252거래일 수익률 (룩어헤드 없음)."""
        ds = full.get(c, {}).get("dates")
        if not ds:
            return None
        j = bisect_left(ds, d) - 1          # d **이전** 마지막 거래일
        if j < MOM_DAYS:
            return None
        a, b = full[c]["closes"][j - MOM_DAYS], full[c]["closes"][j]
        return None if not a else b / a - 1

    def run(top_n, freq):
        """freq: 'M' 월 1회 · 'Q' 분기 1회. 교체일 시가 체결."""
        rb, seen = [], set()
        for d in cal:
            k = d[:7] if freq == "M" else "%s-Q%d" % (d[:4], (int(d[5:7]) - 1) // 3)
            if k not in seen:
                seen.add(k)
                rb.append(d)
        eq, held, curve, log = 1.0, {}, [], []
        for i, d in enumerate(cal):
            if d in rb:
                # 청산 (교체일 시가)
                for c, sh in held.items():
                    o = px(c, d, "opens") or px(c, d, "closes")
                    if o is None:                      # 상장폐지 → 마지막 종가
                        ds = full[c]["dates"]
                        o = full[c]["closes"][-1]
                    eq += sh * o * (1 - FEE_SELL)      # sh = 주수
                held = {}
                # 선정 — 시점 시총 상위 30 중 252일 모멘텀 상위 N
                # ★ 시총은 **그날 종가**로 계산되는데 우리는 **그날 시가**에 산다.
                #   그대로 쓰면 하루짜리 룩어헤드다 → **직전 거래일 시총**을 쓴다.
                pi = bisect_left(dates_all, d) - 1
                row = caps.get(dates_all[pi]) if pi >= 0 else {}
                row = row or {}
                univ = sorted(row.items(), key=lambda kv: -kv[1][0])[:TOP_UNIV]
                cand = []
                for c, (cp, nm) in univ:
                    m = mom(c, d)
                    o = px(c, d, "opens") or px(c, d, "closes")
                    if m is not None and o:
                        cand.append((m, c, nm, o))
                cand.sort(reverse=True)
                pick = cand[:top_n]
                if pick:
                    w = eq / len(pick)
                    for m, c, nm, o in pick:
                        held[c] = w * (1 - FEE_BUY) / o     # 주수
                    eq = 0.0
                    log.append({"date": d, "picks": [(c, nm, round(m * 100, 1))
                                                     for m, c, nm, o in pick]})
            v = eq + sum(sh * (px(c, d) or full[c]["closes"][-1]) for c, sh in held.items())
            curve.append(v)
        # 마지막 청산
        final = eq + sum(sh * (px(c, cal[-1]) or full[c]["closes"][-1]) * (1 - FEE_SELL)
                         for c, sh in held.items())
        yearly = {}
        for y in ("2021", "2022", "2023", "2024", "2025", "2026"):
            ii = [i for i, d in enumerate(cal) if d[:4] == y]
            if ii:
                # 해의 시작값은 **직전 거래일 종가 기준 자산**이어야 복리가 맞는다.
                base = curve[ii[0] - 1] if ii[0] > 0 else 1.0
                yearly[y] = (curve[ii[-1]] / base - 1) * 100
        return {"final_pct": (final - 1) * 100, "mdd": mdd(curve),
                "yearly": yearly, "n_rebalance": len(rb), "log": log[:3],
                "curve_end": curve[-1]}

    print("\n[대형주 모멘텀]", flush=True)
    res = {"note": "이 과제로는 채택 판정을 내리지 않는다. 대조용이며 "
                   "실제로 쓰려면 별도 사전등록이 필요하다.",
           "spec": {"universe": "시점 market_cap_eok 상위 30", "mom_days": MOM_DAYS,
                    "fee_buy": FEE_BUY, "fee_sell": FEE_SELL,
                    "range": [START, END]}}
    arms = {"상위3 · 월교체": (3, "M"), "상위5 · 월교체": (5, "M"),
            "상위3 · 분기교체": (3, "Q")}
    for nm, (n, f) in arms.items():
        r = run(n, f)
        res.setdefault("arms", {})[nm] = {k: v for k, v in r.items() if k != "log"}
        res["arms"][nm]["first_picks"] = r["log"]
        print("  %-14s 최종 %+8.1f%% · 최대낙폭 %+7.1f%% · 교체 %3d회 · 연도별 %s"
              % (nm, r["final_pct"], r["mdd"], r["n_rebalance"],
                 {k: round(v, 1) for k, v in r["yearly"].items()}), flush=True)
        if r["log"]:
            print("     첫 교체 %s → %s" % (r["log"][0]["date"], r["log"][0]["picks"]),
                  flush=True)

    # ── 대조: 평균 종목(등가중 매수 후 보유) ──
    print("\n[대조]", flush=True)
    start_codes = [c for c in caps.get(cal[0], {}) if c in full]
    rets = []
    for c in start_codes:
        a = px(c, cal[0], "opens") or px(c, cal[0])
        if not a:
            continue
        b = px(c, cal[-1])
        if b is None:
            b = full[c]["closes"][-1]          # 소멸 → 마지막 종가
        rets.append((b * (1 - FEE_SELL)) / (a * (1 + FEE_BUY)) - 1)
    ew = st.mean(rets) * 100
    print("  평균 종목(등가중 매수후보유, n=%d) **%+.1f%%** · 중앙 %+.1f%%"
          % (len(rets), ew, st.median(rets) * 100), flush=True)
    res["equal_weight_buy_hold"] = {"n": len(rets), "mean_pct": ew,
                                    "median_pct": st.median(rets) * 100}

    # 코스피
    ks = None
    try:
        import FinanceDataReader as fdr
        df = fdr.DataReader("KS11", START, END)
        ks = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[0]) - 1) * 100
        print("  코스피(KS11, FDR) **%+.1f%%**" % ks, flush=True)
    except Exception as e:                                  # noqa: BLE001
        print("  ⚠ 코스피 취득 실패: %s %s" % (type(e).__name__, e), flush=True)
    res["kospi_pct"] = ks

    # SEPA 슬롯5 (새 정본)
    ev, seen = [], set()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                continue
            seen.add(k)
            ev.append({"code": e["code"], "pattern": e["pattern"],
                       "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                       "resolve_date": e["resolve_date"] or e["entry_date"],
                       "gain": e["gain_at_resolve_pct"], "result": e["result"]})
    eqs = [slot_sim.sim(ev, seed=s)["equity_pct"] for s in range(200)]
    eqs.sort()
    print("  SEPA 슬롯5(새 정본 %d건) 중앙 **%+.1f%%** · 5~95%% %+.1f ~ %+.1f"
          % (len(ev), st.median(eqs), eqs[9], eqs[189]), flush=True)
    res["sepa_slot5"] = {"n": len(ev), "median": st.median(eqs),
                         "band": [eqs[9], eqs[189]]}

    (OUT / "13-megacap-momentum.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/13-megacap-momentum.json")


if __name__ == "__main__":
    main()

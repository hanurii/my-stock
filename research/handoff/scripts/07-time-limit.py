# -*- coding: utf-8 -*-
"""07 - 시간 제한 (페이지 주장 9) — **판정이 아니라 수치 갱신**.

지시서: research/handoff/tasks/07-time-limit.md (v2)

★ 이 과제는 판정 대상이 아니다. 5렌즈를 걸지 않는다.
  9a "오래 버틴 게 이긴다" = 규칙이 아니라 산수다(−10%가 +20%보다 가까워 지는 쪽이 먼저 결판난다).
      **어떤 숫자가 나와도 유지로 승격시키지 않는다. 관찰로만 싣고 페이지 표를 교체할 수치를 낸다.**
  9b "시간 제한을 두지 마라" = 06번의 시간컷 3변형 결과를 **다시 계산하지 않고 인용**한다.

유니버스: 06번과 맞추기 위해 **M1 판(가) 3,776키**가 정본, 확정 3,681은 부가.
청산은 +20/−10 그날 종가 체결.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/07-time-limit.py
난수 미사용.
"""
from __future__ import annotations

import bisect
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
TARGET, STOP = 20.0, 10.0
NS = (5, 10, 20, 30)
PAGE = {5: 46.7, 10: 51.9, 20: 66.7, 30: 75.0}
PAGE_N = {5: 270, 10: 135, 20: 36, 30: 12}
NINE = "2025-11-26"
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]


def load():
    rows = []
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        for p in d["paths"]:
            e = p["entry_price"]
            h, l, c = p["h"], p["l"], p["c"]
            n = len(c)
            T, S = e * (1 + TARGET / 100), e * (1 - STOP / 100)
            rmax, rmin = [], []
            mh, ml = -1e30, 1e30
            for i in range(n):
                if h[i] > mh:
                    mh = h[i]
                if l[i] < ml:
                    ml = l[i]
                rmax.append(mh)
                rmin.append(-ml)
            ti = bisect.bisect_left(rmax, T)
            si = bisect.bisect_left(rmin, -S)
            ti = ti if ti < n else None
            si = si if si < n else None
            if ti is None and si is None:
                i, why = n - 1, "last_close"
            elif si is None:
                i, why = ti, "target"
            elif ti is None:
                i, why = si, "stop"
            elif ti < si:
                i, why = ti, "target"
            elif si < ti:
                i, why = si, "stop"
            else:
                i, why = ti, "both_same_day"
            g = (c[i] / e - 1) * 100
            rows.append({"code": p["code"], "entry_date": p["entry_date"],
                         "days": i, "reason": why, "gain": g,
                         "year": p["entry_date"][:4], "orig": p.get("orig_result"),
                         "result": ("win" if why == "target" else
                                    "loss" if why in ("stop", "both_same_day") else
                                    ("win" if g > 0 else "loss"))})
    return rows


def pct(xs, q):
    s = sorted(xs)
    if not s:
        return None
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def survive_table(rows, tag):
    """N거래일 시점에 아직 미결착인 건과 그중 최종 승 비율."""
    out = {}
    for N in NS:
        alive = [r for r in rows if r["days"] > N]
        segs = {}
        for sn, y0, y1 in SEGMENTS:
            v = [r for r in alive if y0 <= r["year"] <= y1]
            segs[sn] = {"n": len(v),
                        "win_pct": (sum(1 for r in v if r["result"] == "win")
                                    / len(v) * 100) if v else None}
        out[N] = {"n_alive": len(alive),
                  "win_pct": (sum(1 for r in alive if r["result"] == "win")
                              / len(alive) * 100) if alive else None,
                  "segments": segs}
        t = out[N]
        print("  %s N=%2d일 넘김 · 미결착 %4d건 · 이후 승률 %5.1f%% · %s "
              "| 페이지 %d건 %.1f%%"
              % (tag, N, t["n_alive"], t["win_pct"],
                 " ".join("%s %s" % (sn, ("n<3" if t["segments"][sn]["n"] < 3
                                          else "%.1f%%" % t["segments"][sn]["win_pct"]))
                          for sn, _, _ in SEGMENTS),
                 PAGE_N[N], PAGE[N]), flush=True)
    return out


def dist(rows, sel, name):
    v = [r["days"] for r in rows if sel(r)]
    d = {"n": len(v), "median": st.median(v), "q3": pct(v, 0.75),
         "p90": pct(v, 0.90), "max": max(v), "mean": st.mean(v)}
    print("  %-12s n=%4d · 중앙 %4.0f · Q3 %4.0f · P90 %5.1f · 최대 %4d · 평균 %5.1f"
          % (name, d["n"], d["median"], d["q3"], d["p90"], d["max"], d["mean"]), flush=True)
    return d


def main():
    allrows = load()
    conf = [r for r in allrows if r["orig"] in ("win", "loss")]
    print("정본 M1 3,776키 %d건 · 부가 확정 %d건" % (len(allrows), len(conf)), flush=True)
    res = {"n_m1": len(allrows), "n_confirmed": len(conf),
           "note": "이 과제는 판정이 아니라 수치 갱신이다. 5렌즈 미적용. "
                   "9a는 어떤 숫자가 나와도 '유지'로 승격시키지 않는다."}

    print("\n[9a-1] N거래일 넘긴 건의 이후 승률 "
          "(넘김 = 매수일을 0일차로 세어 N일차 종가에 아직 미결착)", flush=True)
    res["survive_m1"] = survive_table(allrows, "M1  ")
    res["survive_conf"] = survive_table(conf, "확정")

    print("\n[9a-2] 승자·패자 결착일수 분포 (정본 M1 3,776키)", flush=True)
    res["dist"] = {
        "winner": dist(allrows, lambda r: r["result"] == "win", "승자"),
        "loser": dist(allrows, lambda r: r["result"] == "loss", "패자"),
        "target": dist(allrows, lambda r: r["reason"] == "target", " ├ 목표도달"),
        "stop": dist(allrows, lambda r: r["reason"] in ("stop", "both_same_day"),
                     " ├ 손절"),
        "last_close": dist(allrows, lambda r: r["reason"] == "last_close",
                           " └ 미결착(마지막종가)")}

    print("\n[9a-3] 페이지의 두 숫자", flush=True)
    los = [r["days"] for r in allrows if r["result"] == "loss"]
    w15 = sum(1 for d in los if d <= 15) / len(los) * 100
    mx = max(r["days"] for r in allrows)
    mx_w = max(r["days"] for r in allrows if r["result"] == "win")
    res["page_numbers"] = {"loser_within_15d_pct": w15, "page_claim_pct": 90.0,
                           "max_days": mx, "page_max_days": 79,
                           "max_days_winner": mx_w}
    print("  '진 것의 90%%가 15일 안에 결판' → 5.6년 실측 **%.1f%%** (패자 %d건 중 %d건)"
          % (w15, len(los), sum(1 for d in los if d <= 15)), flush=True)
    print("  '최대 79거래일' → 5.6년 실측 **%d거래일** (승자 중 최대 %d거래일)"
          % (mx, mx_w), flush=True)

    print("\n[9a-4] 9개월 대조 (참고, M9-11)", flush=True)
    nine = [r for r in allrows if r["entry_date"] >= NINE]
    n9 = {}
    for N in NS:
        a = [r for r in nine if r["days"] > N]
        n9[N] = {"n_alive": len(a),
                 "win_pct": (sum(1 for r in a if r["result"] == "win")
                             / len(a) * 100) if a else None}
        print("  %s 이후 %d건 · N=%2d 넘김 %3d건 · 이후 승률 %s | 페이지 %d건 %.1f%%"
              % (NINE, len(nine), N, len(a),
                 ("—" if not a else "%.1f%%" % n9[N]["win_pct"]),
                 PAGE_N[N], PAGE[N]), flush=True)
    res["nine_month"] = {"from": NINE, "n": len(nine), "by_N": n9}

    (OUT / "07-time-limit.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/07-time-limit.json")


if __name__ == "__main__":
    main()

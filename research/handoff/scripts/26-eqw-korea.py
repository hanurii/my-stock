# -*- coding: utf-8 -*-
"""26 · **한국 «같은 유니버스 등가중» 벤치마크** (M37-A · 미국 결과를 보기 전에 산출).

사전등록한 정의 — **양 시장 동일**
----------------------------------
매 거래일 d 마다, **그날 시점 유니버스에 있고 전일 대비 수익률이 정의되는 종목**의
일간 수익률을 **단순평균**해 그날의 등가중 수익률로 삼고, 그것을 누적한다.
- 유니버스 = **하네스가 쓰는 그 유니버스**(한국: KOSPI·KOSDAQ · `EXCLUDE_PATTERN`
  (스팩·리츠·ETF·ETN·인프라·우선주) 제외 · 외국법인 `9xxxxx` 제외).
  🚨 **유동성 필터·관문 8조건은 적용하지 않는다** — 이건 시장 벤치마크지 전략이 아니다.
- 수익률은 **수정주가 기준**. 한국은 `fltRt`(등락률)를 그대로 쓴다 —
  `pdata_series.py` 가 `cumprod(1+fltRt/100)` 을 수정지수로 쓰는 바로 그 값이라
  **정의상 수정주가 일간수익률과 같다.**
- 비용 없다. 재조정은 **매일 등가중**(일별 평균의 누적).

덤: **비수정 종가비**(clpr_d/clpr_{d-1}−1)와 `fltRt` 를 대조해 한국의 기준가 변경 빈도를
    잰다 — 미국의 18.9%와 나란히 놓기 위해서다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/26-eqw-korea.py
"""
from __future__ import annotations

import json
import re
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PDATA = ROOT / ".cache" / "pdata"
OUT = ROOT / ".cache" / "bt5y" / "out"

START, END = "2021-02-01", "2026-08-21"
EXCLUDE = re.compile(r"스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|\d우$|우$|우\(전환\)|우B\(전환\)")
FOREIGN = re.compile(r"^9\d{5}$")


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def main():
    s, e = START.replace("-", ""), END.replace("-", "")
    files = sorted(p for p in PDATA.glob("price_*.json") if s <= p.stem[6:] <= e)
    print("pdata 일자 파일 %d개 (%s ~ %s)"
          % (len(files), files[0].stem[6:], files[-1].stem[6:]), flush=True)

    prev_close: dict[str, float] = {}
    days = []
    n_rebase = 0
    n_pairs = 0
    rebase_codes = set()
    for p in files:
        d = p.stem[6:]
        date = "%s-%s-%s" % (d[:4], d[4:6], d[6:])
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rets = []
        cur = {}
        for code, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ") or FOREIGN.match(code):
                continue
            name = r.get("itmsNm") or ""
            if EXCLUDE.search(name):
                continue
            c = num(r.get("clpr"))
            if not c or c <= 0:
                continue
            cur[code] = c
            f = num(r.get("fltRt"))
            pc = prev_close.get(code)
            if f is None or pc is None:
                continue                     # 신규상장 첫날·거래 공백 → 수익률 미정의
            rets.append(f / 100.0)
            n_pairs += 1
            # 기준가 변경 탐지: 비수정 종가비와 등락률이 크게 어긋나면 분할·병합·감자
            if abs((c / pc - 1) - f / 100.0) > 0.10:
                n_rebase += 1
                rebase_codes.add(code)
        prev_close = cur
        if rets:
            days.append((date, sum(rets) / len(rets), len(rets)))

    eq = 1.0
    curve = []
    for date, r, n in days:
        eq *= (1 + r)
        curve.append((date, eq, n))
    print("\n거래일 %d · 종목-일 쌍 %d" % (len(days), n_pairs), flush=True)
    print("하루 평균 편입 종목 %.0f (최소 %d · 최대 %d)"
          % (st.mean(x[2] for x in days), min(x[2] for x in days),
             max(x[2] for x in days)), flush=True)
    print("\n**한국 같은-유니버스 등가중 %s ~ %s : %+.2f%%**"
          % (curve[0][0], curve[-1][0], (eq - 1) * 100), flush=True)

    # 연도별
    print("\n연도별", flush=True)
    by_y = {}
    for date, r, n in days:
        by_y.setdefault(date[:4], []).append(r)
    for y in sorted(by_y):
        v = 1.0
        for r in by_y[y]:
            v *= (1 + r)
        print("  %s  %+8.2f%%  (%d일)" % (y, (v - 1) * 100, len(by_y[y])), flush=True)

    # 최대낙폭
    peak, mdd = 0.0, 0.0
    for _d, v, _n in curve:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    print("\n최대낙폭 **%.2f%%**" % (mdd * 100), flush=True)

    print("\n기준가 변경 탐지(비수정 종가비와 등락률이 10%%p 넘게 어긋난 날): "
          "**%d건 · %d종목**" % (n_rebase, len(rebase_codes)), flush=True)
    print("  (미국 대조: 창 안 기준가 변경 1,070 / 5,666 = 18.9%%)" % (), flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "26-eqw-korea.json").write_text(json.dumps({
        "definition": "daily equal-weight mean of fltRt over harness universe; no cost; no liquidity filter",
        "start": curve[0][0], "end": curve[-1][0],
        "total_pct": (eq - 1) * 100, "mdd_pct": mdd * 100,
        "n_days": len(days), "n_pairs": n_pairs,
        "avg_members": st.mean(x[2] for x in days),
        "by_year": {y: (lambda v: (v - 1) * 100)(
            __import__("functools").reduce(lambda a, b: a * (1 + b), by_y[y], 1.0))
            for y in sorted(by_y)},
        "rebase_events": n_rebase, "rebase_codes": len(rebase_codes),
        "curve": [[d, v] for d, v, _ in curve],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/26-eqw-korea.json", flush=True)


if __name__ == "__main__":
    main()

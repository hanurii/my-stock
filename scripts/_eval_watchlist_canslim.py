#!/usr/bin/env python3
"""저평가 성장주 워치리스트(growth-watchlist.json)를 CAN SLIM으로 평가."""

from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# .env 로드
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from canslim_lib.fetch import fetch_yahoo_chart, load_corp_code_map  # noqa: E402
from canslim_lib.criteria import CRITERIA_KEYS, evaluate_m  # noqa: E402

# screen_canslim 로직 직접 임포트 (fetch_market_state는 verbose 출력이 main 시점이라 충돌)
from canslim_lib.fetch import (  # noqa: E402
    fetch_annual,
    fetch_integration,
    fetch_majorstock_holding,
    fetch_quarter,
    fetch_yahoo_chart,
    get_row_values,
    yahoo_symbol,
)
from canslim_lib.criteria import (  # noqa: E402
    evaluate_a,
    evaluate_c,
    evaluate_i,
    evaluate_l,
    evaluate_n,
    evaluate_s,
)
from canslim_lib.score import compute_score  # noqa: E402


def collect_raw(code, name, market, corp_map):
    ig = fetch_integration(code)
    if not ig:
        return None
    market_cap = ig["market_cap_eok"]
    if market_cap < 500:
        return None
    ann = fetch_annual(code)
    qtr = fetch_quarter(code)
    annual_eps = get_row_values(ann, "EPS") if ann else []
    annual_roe = get_row_values(ann, "ROE") if ann else []
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    chart = fetch_yahoo_chart(yahoo_symbol(code, market), "1y", "1d")
    if not chart or len(chart["closes"]) < 200:
        return None
    corp_code = corp_map.get(code)
    inst = fetch_majorstock_holding(corp_code) if corp_code else None
    closes = chart["closes"]
    twelve_m = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0.0
    return dict(code=code, name=name, market=market, ig=ig, annual_eps=annual_eps,
                annual_roe=annual_roe, quarter_eps=quarter_eps, chart=chart,
                institutional=inst, twelve_m_return=twelve_m)


def evaluate(raw, kospi_closes, market_passed, universe_returns):
    ig = raw["ig"]
    chart = raw["chart"]
    inst = raw["institutional"]
    inst_pct = inst["institutional_pct"] if inst else None
    inst_trend = inst["recent_trend"] if inst else None
    results = {
        "C": evaluate_c(raw["quarter_eps"]),
        "A": evaluate_a(raw["annual_eps"], raw["annual_roe"]),
        "N": evaluate_n(chart["closes"]),
        "S": evaluate_s(chart["volumes"], ig["market_cap_eok"]),
        "L": evaluate_l(chart["closes"], kospi_closes, universe_returns),
        "I": evaluate_i(ig["foreign_ownership"], inst_pct, inst_trend),
        "M": (market_passed, "시장 추세 통과" if market_passed else "시장 추세 미통과", "(시장 판정)"),
    }
    score, passed, grade = compute_score(results)
    return dict(code=raw["code"], name=raw["name"], market=raw["market"],
                score=score, grade=grade, passed_count=passed,
                market_cap_eok=int(ig["market_cap_eok"]), per=ig["per"], pbr=ig["pbr"],
                dividend_yield=ig["dividend_yield"],
                foreign_ownership=ig["foreign_ownership"],
                institutional_pct=inst_pct, institutional_trend=inst_trend,
                twelve_m_return=round(raw["twelve_m_return"], 2),
                current_price=int(ig["price"]) if ig["price"] else int(chart["closes"][-1]),
                criteria={k: {"pass": r[0], "value": r[1], "detail": r[2]}
                          for k, r in results.items()})


def main():
    wl = json.load(open(ROOT / "public/data/growth-watchlist.json", encoding="utf-8"))
    stocks = wl["stocks"]
    print(f"📋 저평가 성장주 워치리스트: {len(stocks)}개")

    print("\n📊 KOSPI 추세 판정...")
    ks = fetch_yahoo_chart("^KS11", "1y", "1d")
    m_passed, m_value, m_detail = evaluate_m(ks["closes"])
    kospi_closes = ks["closes"]
    print(f"  → {m_value} ({'GO' if m_passed else 'STOP'})")

    print("\n📦 DART corp_code 매핑...")
    corp_map = load_corp_code_map()
    print(f"  {len(corp_map)}개 매핑")

    print(f"\n🔬 Pass 1: 데이터 수집 ({len(stocks)}종목)")
    raw_list = []
    fail = 0
    start = time.time()
    for i, s in enumerate(stocks):
        code = s.get("code")
        name = s.get("name", code)
        # market은 stocks에 없을 수 있음 — KOSPI/KOSDAQ 추정
        market = s.get("market") or s.get("exchange") or "KOSPI"
        if not code:
            continue
        try:
            raw = collect_raw(code, name, market, corp_map)
            if raw is None and market == "KOSPI":
                # KOSDAQ 재시도
                raw = collect_raw(code, name, "KOSDAQ", corp_map)
        except Exception:
            raw = None
        if raw:
            raw_list.append(raw)
        else:
            fail += 1
        if (i + 1) % 20 == 0:
            print(f"  ... {i + 1}/{len(stocks)} ({(i + 1) / (time.time() - start):.1f}/s)")
    print(f"  Pass 1 완료: 수집 {len(raw_list)}, 실패 {fail}")

    universe_returns = [r["twelve_m_return"] for r in raw_list]
    print(f"\n📈 Pass 2: 백분위 RS + 점수화 ({len(universe_returns)}개 universe)")
    results = []
    for raw in raw_list:
        try:
            r = evaluate(raw, kospi_closes, m_passed, universe_returns)
            results.append(r)
        except Exception:
            continue

    results.sort(key=lambda r: (-r["passed_count"], -r["score"], -r["market_cap_eok"]))

    grade_count = {}
    for r in results:
        grade_count[r["grade"]] = grade_count.get(r["grade"], 0) + 1
    print(f"\n📊 등급 분포: " + ", ".join(f"{g}={grade_count.get(g, 0)}" for g in "ABCD"))

    print(f"\n🏆 Top 30:")
    print(f"{'순':<3} {'등':<3} {'종목':<14} {'코드':<7} {'점수':<4} CANSLIM    {'시총(억)':<10} {'12M':<8} {'기관추세'}")
    print("-" * 100)
    for i, r in enumerate(results[:30]):
        crit = "".join("✓" if r["criteria"][k]["pass"] else "·" for k in CRITERIA_KEYS)
        trend = r.get("institutional_trend") or "—"
        print(f"{i+1:<3} [{r['grade']}] {r['name']:<14} {r['code']:<7} {r['score']:<4} {crit:<10} "
              f"{r['market_cap_eok']:>10,} {r['twelve_m_return']:>+7.1f}% {trend}")

    out_path = ROOT / "public/data/can-slim-watchlist-eval.json"
    out = {
        "evaluated_from": "growth-watchlist.json",
        "total_input": len(stocks),
        "evaluated": len(results),
        "market_status": {
            "verdict": "GO" if m_passed else "STOP",
            "value": m_value,
            "detail": m_detail,
        },
        "grade_distribution": grade_count,
        "candidates": results,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 저장: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

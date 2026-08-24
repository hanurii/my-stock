"""과거 시점(as-of) 룩어헤드-프리 단일종목 평가 (읽기 전용 분석용).

목적: 사용자가 본 트렌드 템플레이트 8조건 + CAN SLIM C·A + 코드33 점수표를
      "그때 알 수 있던 정보만"으로 재현해, 대상승 직전 시점의 매수 후보 여부를 검증.

데이터:
  - 가격(트렌드·RS·N·사후실측): research/.../c2024-12/_universe_prices_5y.json (close, 2021~2026)
  - RS 백분위: _rs_sortmap.json (날짜→정렬된 252일수익률 배열)
  - 실적(C·A): .cache/canslim_stocks/{code}.json 의 분기/연간 라벨을 as-of 한도로 캡
  - 거래량(S)·시장(M): Yahoo (as-of 로 슬라이싱)

룩어헤드 차단: 모든 가격은 ≤ as-of 거래일까지만, 분기 라벨 ≤ QUARTER_MAX, 연간 ≤ ANNUAL_MAX.
*매매 지시 아님 — 방법론 전향 검증 실험. 결손은 임퓨트 금지.*
"""
import argparse
import bisect
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path("C:/Users/hanul/playground/my-stock")
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib.trend_template import evaluate_trend_template
from canslim_lib.criteria import evaluate_c_detailed, compute_c_score, passes_c_gate
from canslim_lib.criteria_a import evaluate_a_v2
from canslim_lib.fetch import fetch_yahoo_chart, yahoo_symbol

CY = ROOT / "research" / "oneil-model-book" / "cycles" / "c2024-12"
CACHE = ROOT / ".cache" / "canslim_stocks"


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _is_accel(history):
    """마지막 3개가 a<b<c 단조 + c>0 (criteria._is_accel 동일)."""
    if not history or len(history) < 3:
        return False
    last3 = [v for _, v in history[-3:]]
    return last3[-1] > 0 and last3[0] < last3[1] < last3[2]


def filter_history(history, max_label):
    if not history:
        return []
    return [(k, v) for k, v in history if k <= max_label]


def eval_one(code, asof, U, sortmap, gk, quarter_max, annual_max):
    out = {"code": code, "asof": asof}

    # ── 가격 슬라이싱 (≤ asof) ──
    s = U.get(code)
    if not s:
        out["error"] = "5y 캐시에 없음"
        return out
    d, c = s["d"], s["c"]
    ai = bisect.bisect_right(d, asof) - 1
    closes = c[:ai + 1]
    out["asof_trading_day"] = d[ai]
    out["asof_close"] = c[ai]
    out["data_days_used"] = len(closes)

    # ── RS 백분위 (sortmap: 그 날짜의 전종목 252일수익률 분포에서 percentile) ──
    rs = None
    if len(closes) >= 253 and closes[-253] > 0:
        ret252 = closes[-1] / closes[-253] - 1.0
        out["ret_252d_pct"] = round(ret252 * 100, 1)
        ki = bisect.bisect_right(gk, asof) - 1
        if ki >= 0:
            arr = sortmap[gk[ki]]
            out["rs_date"] = gk[ki]
            if arr:
                pct = 100 * bisect.bisect_left(arr, ret252) / max(1, len(arr) - 1)
                rs = max(1, min(99, round(pct)))
    out["rs"] = rs

    # ── 트렌드 템플레이트 8조건 ──
    tt = evaluate_trend_template(closes, rs=rs, rs_min=70)
    out["trend"] = {
        "passed_count": tt["passed_count"],
        "all_pass": tt["pass"],
        "criteria": {k: {"pass": v["pass"], "detail": v["detail"]} for k, v in tt["criteria"].items()},
        "extras": tt["extras"],
    }

    # ── C·A (실적, 라벨 캡) ──
    cf = CACHE / f"{code}.json"
    if cf.exists():
        cd = json.loads(cf.read_text(encoding="utf-8"))
        q_eps = filter_history(cd.get("quarter_eps") or [], quarter_max)
        q_sales = filter_history(cd.get("quarter_sales") or [], quarter_max)
        a_eps = filter_history(cd.get("annual_eps") or [], annual_max)
        a_roe = filter_history(cd.get("annual_roe") or [], annual_max)
        out["caps"] = {
            "quarter_max": quarter_max, "annual_max": annual_max,
            "q_eps_used": q_eps[-6:], "a_eps_used": a_eps, "a_roe_used": a_roe,
        }
        if len(q_eps) >= 5:
            c_detailed = evaluate_c_detailed(q_eps, q_sales)
            c_score = compute_c_score(c_detailed)
            out["C"] = {
                "yoy_pct": c_detailed.get("yoy_pct"),
                "latest_quarter": c_detailed.get("latest_quarter"),
                "eps_accel_3q": c_detailed.get("eps_accel_3q"),
                "sales_yoy_pct": c_detailed.get("sales_yoy_pct"),
                "sales_accel_3q": c_detailed.get("sales_accel_3q"),
                "eps_yoy_history": c_detailed.get("eps_yoy_history"),
                "sales_yoy_history": c_detailed.get("sales_yoy_history"),
                "c_score": round(c_score["total"], 1),
                "c_tier": c_score["tier"],
                "passes_gate": passes_c_gate(c_detailed),
            }
            # 코드33: EPS·매출·순이익률 3분기 가속 (순이익 시계열 없으면 EPS·매출로만)
            out["code33"] = {
                "eps_accel_3q": _is_accel(c_detailed.get("eps_yoy_history")),
                "sales_accel_3q": _is_accel(c_detailed.get("sales_yoy_history")),
            }
            if len(a_eps) >= 2:
                try:
                    a_eval = evaluate_a_v2(
                        annual_eps=a_eps, annual_roe=a_roe,
                        quarterly_eps_yoy_history=c_detailed.get("eps_yoy_history", []),
                        sales_yoy_history=c_detailed.get("sales_yoy_history", []),
                        latest_quarter_yoy=c_detailed.get("yoy_pct"),
                        induty_code=None,
                        quarterly_eps_for_stability=[v for _, v in q_eps],
                        pretax_margin=None,
                    )
                    latest_roe = a_roe[-1][1] if a_roe else None
                    out["A"] = {"score": a_eval.get("score"), "grade": a_eval.get("grade"),
                                "track": a_eval.get("track"), "latest_roe": latest_roe,
                                "latest_annual": a_eps[-1][0]}
                except Exception as e:
                    out["A"] = {"error": str(e)}
        else:
            out["C"] = {"error": f"분기 {len(q_eps)}개 (<5)"}
    else:
        out["C"] = {"error": "canslim 캐시 없음"}

    # ── S (거래량) · M 은 Yahoo 별도 (네트워크) ──
    try:
        ch = fetch_yahoo_chart(yahoo_symbol(code, "KOSPI"),
                               period1=_ep("2024-06-01"), period2=_ep("2025-06-15"), interval="1d")
        if ch and ch.get("volumes"):
            ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") for t in ch["timestamps"]]
            vv = ch["volumes"]
            bi = bisect.bisect_right(ts, asof) - 1
            if bi >= 50 and len(vv) > bi:
                v50 = sum(vv[bi - 50:bi]) / 50
                v5 = sum(vv[bi - 4:bi + 1]) / 5
                out["S"] = {"vol5_over_50d_pct": round((v5 / v50 - 1) * 100, 1) if v50 else None,
                            "asof_day": ts[bi]}
    except Exception as e:
        out["S"] = {"error": str(e)}

    # ── 사후 실측 (그때 몰랐던 결과, 별도 표기) ──
    fwd_close = c[-1]
    fwd_date = d[-1]
    fwd_max = max(c[ai:])
    out["forward"] = {
        "from_close": c[ai], "from_date": d[ai],
        "to_close": fwd_close, "to_date": fwd_date,
        "return_pct": round((fwd_close / c[ai] - 1) * 100, 1),
        "max_return_pct": round((fwd_max / c[ai] - 1) * 100, 1),
        "note": "5y캐시 최신일까지. 실제 현재가는 더 최신일 수 있음.",
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", required=True)
    ap.add_argument("--codes", nargs="+", required=True)
    ap.add_argument("--quarter-max", required=True, help="공개된 마지막 분기 라벨 예 202503")
    ap.add_argument("--annual-max", required=True, help="공개된 마지막 연간 라벨 예 202412")
    args = ap.parse_args()

    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    sortmap = json.loads((CY / "_rs_sortmap.json").read_text(encoding="utf-8"))
    gk = sorted(sortmap)

    results = [eval_one(code, args.asof, U, sortmap, gk, args.quarter_max, args.annual_max)
               for code in args.codes]
    print(json.dumps({"asof": args.asof, "results": results}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

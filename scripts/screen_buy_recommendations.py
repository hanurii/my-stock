"""매수 추천 리스트 — 검출된 SEPA 후보 중 초수익 잠재력을 채점해 점수순으로 정렬.

입력: public/data/sepa-{vcp,power-play,power-play-all,3c}-candidates.json (검출된 후보만)
      + OHLCV 캐시(직전 상승폭) + 시장지수 KS11/KQ11(RS선, FDR; 없으면 RS·상승폭만으로 채점)
출력: public/data/sepa-buy-recommendations.json  (초수익 점수 내림차순)

점수 정의·검증은 canslim_lib/superperf.py 참조. 정렬=초수익 점수 순수(매수 타이밍은 배지로 표시만).
"""
from __future__ import annotations
import sys, json, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib import ohlcv_matrix, superperf
from canslim_lib.strategy_params import POSITION_KRW

DATA = ROOT / "public" / "data"
KST = timezone(timedelta(hours=9))
# (파일, 패턴표시명) — 한 종목이 여러 파일에 있으면 점수 동일하므로 검출된 것 우선 dedupe
PATTERN_FILES = [
    ("sepa-vcp-candidates.json", "VCP"),
    ("sepa-power-play-candidates.json", "파워플레이"),
    ("sepa-power-play-all-candidates.json", "파워플레이"),
    ("sepa-3c-candidates.json", "3C"),
]


def load_index():
    """시장지수 KS11(코스피)/KQ11(코스닥) → {market: {date: close}}. FDR 없거나 실패 시 None."""
    try:
        import FinanceDataReader as fdr
    except Exception:
        print("  ⚠ FinanceDataReader 없음 — RS선 요인 없이 채점(RS·상승폭만)", flush=True)
        return None
    out = {}
    for market, code in (("KOSPI", "KS11"), ("KOSDAQ", "KQ11")):
        try:
            df = fdr.DataReader(code, "2024-01-01")
            out[market] = {d.strftime("%Y-%m-%d"): float(c) for d, c in zip(df.index, df["Close"])}
        except Exception as e:
            print(f"  ⚠ 지수 {code} 수집 실패: {str(e)[:60]}", flush=True)
    return out or None


# 같은 종목이 여러 패턴에 검출되면 상태 우선순위로 하나만 남긴다(돌파>진입임박>예의주시).
_STATUS_PRI = {"breakout": 0, "actionable": 1, "forming": 2}
_BADGE = {"breakout": "🔴돌파", "actionable": "🟢진입임박", "forming": "🟡예의주시"}
_LIQ_BADGE = {"ok": "🟢", "caution": "🟡", "danger": "🔴"}

def load_demand_watch() -> dict[str, dict]:
    """기관 수요 유보 목록(sepa-demand-watchlist.json, 사용자 직접 관리).

    해당 종목은 추천에서 숨기지 않고 순위만 제외(하단 딤드) — 파일 없거나 깨져도 무시(비차단).
    """
    try:
        d = json.loads((DATA / "sepa-demand-watchlist.json").read_text(encoding="utf-8"))
        return {s["code"]: s for s in d.get("stocks", []) if s.get("code")}
    except Exception:
        return {}


def burden_band(burden_pct: float | None) -> str | None:
    """청산 부담률 N(%) → 신호등 밴드. 🟢ok <5 · 🟡caution 5~30 미만 · 🔴danger ≥30.

    경계 근거: 실측 손절 34왕복 슬리피지 — N<5%는 비용≈0, N≥30%는 실통증
    (에스에스알 32%·로스웰 72%). 경계값 자체(5.0·30.0)는 위 밴드에 붙는다.
    """
    if burden_pct is None:
        return None
    if burden_pct < 5:
        return "ok"
    if burden_pct < 30:
        return "caution"
    return "danger"


def liquidity_fields(s: dict) -> dict:
    """청산 부담 N/M: 실제 슬롯(POSITION_KRW=1,000만)으로 살 때 얼마나 쉽게 빠져나오나.

    N = burden_pct = POSITION_KRW ÷ ADV20(최근 20일 평균 거래대금) × 100.
    M = split_risk_krw = ADV20 × 5% = 분할매도 가능성이 시작되는 매수 금액(이 금액까지는 🟢).
    분모를 ADV50이 아닌 ADV20으로 쓰는 이유: 실측 손절일 거래대금 중앙값 = ADV20의 1.02배,
    ADV50은 대양금속의 최근 유동성 붕괴(11.9억→5.7억)를 가렸다.
    구 필드(adv_50d_eok·position_pct_of_adv·one_day_exit·liquidity)는 하위 호환으로 유지하되
    liquidity 밴드는 burden_pct 기준(burden_band)으로 재산정. 최소 20일은 기존과 동일.
    """
    closes, vols = s.get("closes") or [], s.get("volumes") or []
    n = min(len(closes), len(vols))
    empty = {"adv_20d_eok": None, "burden_pct": None, "split_risk_krw": None,
             "adv_50d_eok": None, "position_pct_of_adv": None, "one_day_exit": None, "liquidity": None}
    if n < 20:
        return empty
    turnover = [c * v for c, v in zip(closes[-50:], vols[-50:])]
    adv50 = sum(turnover) / len(turnover)
    t20 = turnover[-20:]
    adv20 = sum(t20) / len(t20)
    if adv20 <= 0:
        return {"adv_20d_eok": 0.0, "burden_pct": None, "split_risk_krw": 0,
                "adv_50d_eok": round(adv50 / 1e8, 2), "position_pct_of_adv": None,
                "one_day_exit": False, "liquidity": "danger"}
    burden = round(POSITION_KRW / adv20 * 100, 1)  # N(%) — UI가 이 값에서 색을 직접 유도
    return {
        "adv_20d_eok": round(adv20 / 1e8, 2),
        "burden_pct": burden,                          # N: 1,000만원 매수 시 청산 부담률
        "split_risk_krw": int(round(adv20 * 0.05)),    # M: 분할매도 가능성 시작 금액(원)
        "adv_50d_eok": round(adv50 / 1e8, 2) if adv50 > 0 else 0.0,
        "position_pct_of_adv": round(POSITION_KRW / adv50 * 100, 1) if adv50 > 0 else None,
        "one_day_exit": burden < 30,
        "liquidity": burden_band(burden),
    }


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔에서 이모지 출력 크래시 방지
    ap = argparse.ArgumentParser(description="매수 추천 리스트(초수익 잠재력 순)")
    ap.add_argument("--min-score", type=int, default=3, help="포함 최소 점수(기본 3; 0~1=엣지 없음 제외)")
    ap.add_argument("--out", default=str(DATA / "sepa-buy-recommendations.json"))
    a = ap.parse_args()

    idx = load_index()
    demand_watch = load_demand_watch()
    best: dict[str, dict] = {}
    asof = None
    for fname, pat in PATTERN_FILES:
        p = DATA / fname
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        asof = asof or d.get("asof")
        for c in d.get("candidates", []):
            det = c.get("vcp_detected")
            det = det if det is not None else c.get("pattern_detected")
            if not det:  # 페이지에 뜨는 '검출된' 후보만
                continue
            code = c["code"]
            s = ohlcv_matrix.get_series(code)
            if not s or not s.get("closes"):
                continue
            mkt = c.get("market", "KOSPI")
            f = superperf.compute_factors(s["dates"], s["closes"], s["highs"],
                                          (idx or {}).get(mkt) if idx else None)
            pts, reasons = superperf.score(c.get("rs"), f["prior_adv"], f["rs_nh_days"], f["rs_leads"])
            rec = {
                "code": code, "name": c.get("name"), "market": mkt,
                "current_price": c.get("current_price"), "rs": c.get("rs"),
                "status": c.get("status"), "pivot_price": c.get("pivot_price"),
                "pct_to_pivot": c.get("pct_to_pivot"), "entry_ready": bool(c.get("entry_ready")),
                "superperf_score": pts, "score_reasons": reasons,
                "prior_adv_pct": round(f["prior_adv"] * 100, 1) if f["prior_adv"] is not None else None,
                "dist_52wh": f["dist_52wh"], "rs_nh_days": f["rs_nh_days"], "rs_leads": f["rs_leads"],
                "pattern": pat, "gate_near": bool(c.get("gate_near")),
                "gate_near_reasons": c.get("gate_near_reasons") or [], **liquidity_fields(s),
            }
            w = demand_watch.get(code)
            if w:  # 기관 수요 유보 — 숨기지 않고 순위 제외+딤드 표시용 필드만 부착
                rec["demand_watch"] = {"reason": w.get("reason", ""), "added": w.get("added")}
            # dedupe: 같은 종목이 여러 패턴에 검출되면 상태 우선순위(돌파>진입임박>예의주시)로 하나만
            prev = best.get(code)
            if prev is None or _STATUS_PRI.get(rec["status"], 9) < _STATUS_PRI.get(prev["status"], 9):
                if prev is not None:  # 진 레코드의 관문임박 표시는 승계(패턴별로 갈릴 수 없는 종목 속성)
                    rec["gate_near"] = rec["gate_near"] or bool(prev.get("gate_near"))
                    rec["gate_near_reasons"] = rec["gate_near_reasons"] or prev.get("gate_near_reasons") or []
                best[code] = rec
            elif rec["gate_near"] and not prev.get("gate_near"):
                prev["gate_near"] = True
                prev["gate_near_reasons"] = rec["gate_near_reasons"]

    # 점수 min_score 이상 OR 오늘 진입 임박(entry_ready) — 낮은 점수라도 진입 임박이면 포함.
    rows = [r for r in best.values() if r["superperf_score"] >= a.min_score or r["entry_ready"]]
    # 기관 수요 유보 종목은 점수 무관 최하단(순위 제외·딤드) — 숨기지는 않는다(모니터링용).
    rows.sort(key=lambda r: (bool(r.get("demand_watch")), -r["superperf_score"], -(r["rs"] or 0)))

    out = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": asof,
        "min_score": a.min_score,
        "position_krw": POSITION_KRW,
        "count": len(rows),
        "candidates": rows,
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 저장: {a.out}  ({len(rows)}종목, 점수≥{a.min_score})")
    for r in rows[:15]:
        b, m = r["burden_pct"], r["split_risk_krw"]
        if b is not None:
            mstr = f"{m / 1e4:,.0f}만" if m else "0"
            liq = f"{_LIQ_BADGE.get(r['liquidity'], '·')}N{b:.1f}%·M{mstr}"
        else:
            liq = "—"
        mark = "🚫유보 " if r.get("demand_watch") else ""
        print(f"  {r['superperf_score']}점 {mark}{r['name']:<12} {r['pattern']:>5} RS{r['rs']} "
              f"직전{r['prior_adv_pct']:+.0f}% 청산부담{liq} {_BADGE.get(r['status'], r['status'])}  {'·'.join(r['score_reasons'])}")


if __name__ == "__main__":
    main()

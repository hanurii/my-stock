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


def main():
    ap = argparse.ArgumentParser(description="매수 추천 리스트(초수익 잠재력 순)")
    ap.add_argument("--min-score", type=int, default=3, help="포함 최소 점수(기본 3; 0~1=엣지 없음 제외)")
    ap.add_argument("--out", default=str(DATA / "sepa-buy-recommendations.json"))
    a = ap.parse_args()

    idx = load_index()
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
                "pattern": pat,
            }
            # dedupe: 같은 종목이 여러 패턴에 검출되면 상태 우선순위(돌파>진입임박>예의주시)로 하나만
            prev = best.get(code)
            if prev is None or _STATUS_PRI.get(rec["status"], 9) < _STATUS_PRI.get(prev["status"], 9):
                best[code] = rec

    rows = [r for r in best.values() if r["superperf_score"] >= a.min_score]
    rows.sort(key=lambda r: (-r["superperf_score"], -(r["rs"] or 0)))

    out = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": asof,
        "min_score": a.min_score,
        "count": len(rows),
        "candidates": rows,
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 저장: {a.out}  ({len(rows)}종목, 점수≥{a.min_score})")
    for r in rows[:15]:
        print(f"  {r['superperf_score']}점 {r['name']:<12} {r['pattern']:>5} RS{r['rs']} "
              f"직전{r['prior_adv_pct']:+.0f}% {_BADGE.get(r['status'], r['status'])}  {'·'.join(r['score_reasons'])}")


if __name__ == "__main__":
    main()

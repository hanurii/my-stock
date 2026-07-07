# scripts/pivot_backtest_nextday_multi.py
"""SEPA 익일 진입 백테스트 — 여러 스캔일 확장(로버스트 승률·국면 의존성).

pivot_backtest_nextday.py(단일 스캔일)를 스캔일 루프로 확장. 각 스캔일 D:
  D 마지막 날 actionable(트렌드 통과·미돌파) 후보 → 익일(D+1 거래일) 피벗 돌파분 매수
  → +10%/-5% 선착. 전 스캔일의 거래를 누적해 월별·패턴·가격대로 집계.
예외(ambiguous)는 여기선 분봉 판정 대신 [최악~최선] 범위로만(수천 건 KIS 비현실적).

실행: python scripts/pivot_backtest_nextday_multi.py [--start 2025-09-01 --end 2026-06-15 --step 5]
정션 금지 — .cache 는 주 작업트리(my-stock) 절대경로 참조.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import ohlcv_matrix  # noqa: E402
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"

from canslim_lib.trend_template import evaluate_trend_template  # noqa: E402
from canslim_lib.cheat import evaluate_cheat, DEFAULT_PARAMS as CHEAT_P  # noqa: E402
from canslim_lib.vcp import evaluate_vcp  # noqa: E402
from canslim_lib.power_play import evaluate_power_play  # noqa: E402
from canslim_lib.pivot_backtest import (  # noqa: E402
    simulate_pivot_trade, price_bucket, truncate_series, tally, group_win_rate)
from screen_trend_template import _compute_rs_for_all  # noqa: E402
from canslim_lib.pykrx_universe import fetch_universe_with_cap  # noqa: E402

KST = timezone(timedelta(hours=9))
RS_MIN = 80
REF = "005930"   # 거래일 달력 기준(삼성전자, 전기간 보유)


def _detect_actionable(st: dict, pname: str):
    """st(=asof 절단 시계열)에서 해당 패턴이 actionable 이면 (pivot) 반환, 아니면 None."""
    try:
        if pname == "VCP":
            r = evaluate_vcp(st)
        elif pname == "3C":
            r = evaluate_cheat(st, CHEAT_P)
        else:
            r = evaluate_power_play(st)
    except Exception:
        return None
    if r.get("status") == "actionable" and r.get("pivot_price"):
        return r["pivot_price"]
    return None


def run(start: str, end: str, step: int) -> dict:
    universe = fetch_universe_with_cap("ALL")
    meta = {u["code"]: u for u in universe}
    codes = sorted(meta.keys())
    full = {}
    for c in codes:
        s = ohlcv_matrix.get_series(c)
        if s and s.get("closes"):
            full[c] = s
    print(f"유니버스 {len(codes)} · 시계열 {len(full)}")

    cal = full[REF]["dates"]
    scan_dates = [d for d in cal if start <= d <= end][::step]
    print(f"스캔일 {len(scan_dates)}개 ({scan_dates[0]}~{scan_dates[-1]}, step {step})")

    events = []
    per_date = []
    open_until = {}   # code -> 직전 채택 거래의 청산일(그때까진 재매수 금지, 중복 포지션 방지)
    n_skip_overlap = 0
    for D in scan_dates:
        stD = {}
        for c, s in full.items():
            t = truncate_series(s, D)
            if len(t["closes"]) >= 200:
                stD[c] = t
        rs = _compute_rs_for_all([{"code": c, "closes": t["closes"], "ok": True}
                                  for c, t in stD.items()])
        n_cand = n_ent = 0
        for c, t in stD.items():
            rsv = (rs.get(c) or {}).get("rs")
            if not evaluate_trend_template(t["closes"], rs=rsv, rs_min=RS_MIN)["pass"]:
                continue
            for pname in ("VCP", "3C", "PP"):
                pivot = _detect_actionable(t, pname)
                if pivot is None:
                    continue
                n_cand += 1
                s = full[c]
                if D not in s["dates"]:
                    continue
                ni = s["dates"].index(D) + 1
                if ni >= len(s["dates"]):
                    continue
                hi = s["highs"][ni]
                if hi is None or hi < pivot:
                    continue        # 익일 미돌파 → 진입 안 함
                edate = s["dates"][ni]
                if c in open_until and edate <= open_until[c]:
                    n_skip_overlap += 1
                    continue        # 이미 그 종목 보유 중(청산 전) → 재매수 안 함
                sim = simulate_pivot_trade(s, ni, pivot)
                open_until[c] = sim.get("resolve_date") or edate
                n_ent += 1
                events.append({
                    "code": c, "name": meta[c].get("name", c), "market": meta[c].get("market"),
                    "pattern": pname, "scan_date": D, "entry_date": edate,
                    "resolve_date": sim.get("resolve_date"),
                    "month": edate[:7], "pivot": round(pivot, 2), "rs": rsv,
                    "price_bucket": price_bucket(pivot), "result": sim["result"],
                })
        per_date.append({"scan_date": D, "n_candidates": n_cand, "n_entered": n_ent})
        print(f"  {D}: 후보 {n_cand} · 진입 {n_ent} (누적 거래 {len(events)})", flush=True)

    forward_last = max((s["dates"][-1] for s in full.values()), default=None)
    return {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "params": {"method": "nextday_entry_multi", "start": start, "end": end, "step": step,
                   "target_pct": 10, "stop_pct": 5, "rs_min": RS_MIN,
                   "candidate_status": "actionable", "n_scan_dates": len(scan_dates),
                   "n_trades": len(events), "n_skip_overlap": n_skip_overlap,
                   "dedup": "no_overlapping_position_per_stock", "forward_last": forward_last,
                   "note": "예외는 분봉 미판정 — [worst,best] 범위. 진실은 worst 쪽에 근접(4/1 근거)."},
        "summary": tally(events),
        "by_month": group_win_rate(events, "month"),
        "by_pattern": group_win_rate(events, "pattern"),
        "by_price": group_win_rate(events, "price_bucket"),
        "per_date": per_date,
        "events": events,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-09-01")
    ap.add_argument("--end", default="2026-06-15")
    ap.add_argument("--step", type=int, default=5)
    ap.add_argument("--out", default="pivot-backtest-nextday-multi.json")
    a = ap.parse_args()
    out = run(a.start, a.end, a.step)
    p = ROOT / "public" / "data" / a.out
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    s = out["summary"]
    print("\n=== 다기간 익일 진입 요약 ===")
    print(f"스캔일 {out['params']['n_scan_dates']} · 총 거래 {s['n']}")
    print(f"승 {s['win']} · 패 {s['loss']} · 예외 {s['ambiguous']} · 미결 {s['unresolved']}")
    print(f"결착 승률 {s['win_rate_resolved']}% · 정직범위 [{s['win_rate_worst']}~{s['win_rate_best']}]")
    print("\n월별(결착승률·거래수):")
    for m, v in sorted(out["by_month"].items()):
        print(f"  {m}: {v['win_rate_resolved']}% (승{v['win']}/패{v['loss']}/예외{v['ambiguous']}, n={v['n']})")
    print("\n패턴별:", {k: (v["win_rate_resolved"], v["n"]) for k, v in out["by_pattern"].items()})
    print(f"저장 → {p}")


if __name__ == "__main__":
    main()

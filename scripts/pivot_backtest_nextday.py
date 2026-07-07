# scripts/pivot_backtest_nextday.py
"""SEPA 익일 진입 백테스트 — asof 스캔의 '진입임박(actionable)' 후보를 익일 돌파 시 매수.

기존 pivot_backtest.py(2주치 돌파 수확)와 방법론이 다르다. 사용자 실전 워크플로 재현:
- 후보 = asof(예: 4/1) **마지막 날 status=actionable**(피벗 확정·아직 미돌파)
  + 트렌드 템플릿 통과(RS≥80). 전수 파워플레이는 제외(트렌드 게이트로 자동 배제).
- 진입 = **익일(asof 다음 거래일)** 고가가 피벗 도달한 것만, 피벗가 매수(자동매수 체결 가정).
- +10%/-5% 선착 → 승/패(돌파일=진입일 특례는 simulate_pivot_trade 가 처리, 예외는 분봉 판정 대상).

실행: python scripts/pivot_backtest_nextday.py --asof 2026-04-01
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
# 캐시는 주 작업트리에만 있으므로 절대경로로 덮어씀(어느 워크트리에서 실행해도 동일 대상, 정션 불필요).
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"

from canslim_lib.trend_template import evaluate_trend_template  # noqa: E402
from canslim_lib.pivot_backtest import (  # noqa: E402
    simulate_pivot_trade, price_bucket, rel_volume, truncate_series,
    tally, group_win_rate,
)
from canslim_lib import vcp_history, power_play_history, cheat_history  # noqa: E402
from screen_trend_template import _compute_rs_for_all  # noqa: E402
from canslim_lib.pykrx_universe import fetch_universe_with_cap  # noqa: E402

KST = timezone(timedelta(hours=9))
RS_MIN = 80
SCAN_DAYS = 250
PATTERNS = [("VCP", vcp_history.replay_vcp),
            ("PP", power_play_history.replay_power_play),
            ("3C", cheat_history.replay_cheat)]


def rs_bucket(rs):
    if rs is None:
        return "미상"
    return "95~100" if rs >= 95 else "90~94" if rs >= 90 else "80~89"


def relvol_bucket(rv):
    if rv is None:
        return "미상"
    return "3+" if rv >= 3 else "2~3" if rv >= 2 else "1.5~2" if rv >= 1.5 else "1~1.5" if rv >= 1 else "<1"


def run(asof: str) -> dict:
    universe = fetch_universe_with_cap("ALL")
    meta = {u["code"]: u for u in universe}
    codes = sorted(meta.keys())
    print(f"유니버스 {len(codes)}종목 · 스캔 기준일 {asof}")

    full_by_code, stD_by_code = {}, {}
    for code in codes:
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            continue
        stD = truncate_series(s, asof)
        if len(stD["closes"]) < 200:
            continue
        full_by_code[code] = s
        stD_by_code[code] = stD
    print(f"시계열 확보 {len(full_by_code)}")

    # asof 교차 RS(단일 시점)
    rows = [{"code": c, "closes": st["closes"], "ok": True}
            for c, st in stD_by_code.items() if len(st["closes"]) >= 200]
    rs_by_code = _compute_rs_for_all(rows)
    print(f"RS 계산(asof) {len(rows)}종목")

    # 후보 = asof 마지막 날 status=actionable + 트렌드 템플릿 통과(RS≥80)
    candidates = []
    for code, stD in stD_by_code.items():
        rs = (rs_by_code.get(code) or {}).get("rs")
        if not evaluate_trend_template(stD["closes"], rs=rs, rs_min=RS_MIN)["pass"]:
            continue
        for pname, replay_fn in PATTERNS:
            replay = replay_fn(stD, SCAN_DAYS, None)
            if not replay:
                continue
            last = replay[-1]
            if last.get("status") == "actionable" and last.get("pivot_price"):
                candidates.append({"code": code, "pattern": pname,
                                   "pivot": last["pivot_price"], "rs": rs})
    print(f"진입임박(actionable·트렌드통과) 후보 {len(candidates)}")

    # 익일 진입: asof 다음 거래일 고가가 피벗 도달한 것만 매수
    events, ambiguous = [], []
    n_no_next = n_no_cross = 0
    for c in candidates:
        code, pivot = c["code"], c["pivot"]
        full = full_by_code[code]
        if asof not in full["dates"]:
            n_no_next += 1
            continue
        ni = full["dates"].index(asof) + 1
        if ni >= len(full["dates"]):
            n_no_next += 1
            continue
        entry_date = full["dates"][ni]
        hi = full["highs"][ni]
        if hi is None or hi < pivot:
            n_no_cross += 1          # 익일 미돌파 → 진입 안 함
            continue
        sim = simulate_pivot_trade(full, ni, pivot)
        rec = {
            "code": code, "name": meta[code].get("name", code),
            "market": meta[code].get("market"), "pattern": c["pattern"],
            "scan_date": asof, "entry_date": entry_date, "breakout_date": entry_date,
            "pivot": round(pivot, 2), "rs": c["rs"], "price_bucket": price_bucket(pivot),
            "rel_vol": rel_volume(full, ni), **sim,
        }
        rec["rel_vol_bucket"] = relvol_bucket(rec["rel_vol"])
        rec["rs_bucket"] = rs_bucket(c["rs"])
        events.append(rec)
        if sim["result"] == "ambiguous":
            ambiguous.append(rec)
    print(f"익일 진입 {len(events)} · 익일미돌파(진입안함) {n_no_cross} · "
          f"다음날데이터없음 {n_no_next} · ambiguous {len(ambiguous)}")

    prio = {"loss": 0, "ambiguous": 1, "win": 2, "unresolved": 3}
    by_pair = {}
    for e in events:
        k = (e["code"], e["entry_date"])
        if k not in by_pair or prio[e["result"]] < prio[by_pair[k]["result"]]:
            by_pair[k] = e
    stock_events = list(by_pair.values())

    by_feature = {k: group_win_rate(events, k)
                  for k in ("pattern", "market", "price_bucket", "rel_vol_bucket", "rs_bucket")}
    forward_last = max((s["dates"][-1] for s in full_by_code.values()), default=None)
    return {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "params": {"asof": asof, "method": "nextday_entry", "target_pct": 10, "stop_pct": 5,
                   "rs_min": RS_MIN, "candidate_status": "actionable",
                   "n_candidates": len(candidates), "n_entered": len(events),
                   "n_no_cross_nextday": n_no_cross, "forward_last": forward_last},
        "summary": tally(events),
        "summary_stock_level": tally(stock_events),
        "unique_stock_days": len(stock_events),
        "by_pattern": group_win_rate(events, "pattern"),
        "by_feature": by_feature,
        "events": events,
        "ambiguous": ambiguous,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default="2026-04-01")
    args = ap.parse_args()
    out = run(args.asof)
    p = ROOT / "public" / "data" / f"pivot-backtest-nextday-{args.asof}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    s = out["summary"]
    pr = out["params"]
    print("\n=== 익일 진입 백테스트 요약 ===")
    print(f"진입임박 후보 {pr['n_candidates']} → 익일 돌파·진입 {pr['n_entered']} "
          f"(미돌파 {pr['n_no_cross_nextday']})")
    print(f"승 {s['win']} · 패 {s['loss']} · 예외 {s['ambiguous']} · 미결 {s['unresolved']} "
          f"· 결착 승률 {s['win_rate_resolved']}% [{s['win_rate_worst']}~{s['win_rate_best']}]")
    print("패턴별:", {k: (v["win_rate_resolved"], v["win"] + v["loss"]) for k, v in out["by_pattern"].items()})
    print("가격대별:", {k: (v["win_rate_resolved"], v["win"] + v["loss"]) for k, v in out["by_feature"]["price_bucket"].items()})
    print(f"저장 → {p}")


if __name__ == "__main__":
    main()

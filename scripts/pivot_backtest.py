# scripts/pivot_backtest.py
"""SEPA 피벗 백테스트 오케스트레이터 (단일 기준일 스냅샷).
실행: python scripts/pivot_backtest.py --asof 2026-04-01
정의: docs/superpowers/specs/2026-07-07-pivot-backtest-design.md
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import ohlcv_matrix  # noqa: E402
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
ENTRY_WINDOW = 10   # 돌파일이 asof 이하 마지막 10거래일 이내
SCAN_DAYS = 250
PATTERNS = [("VCP", vcp_history.replay_vcp, vcp_history.find_breakout_events),
            ("PP", power_play_history.replay_power_play, power_play_history.find_breakout_events),
            ("3C", cheat_history.replay_cheat, cheat_history.find_breakout_events)]


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
    print(f"유니버스 {len(codes)}종목 · 기준일 {asof}")

    # 전체 시계열 + as-of D 절단(검출용) 수집
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

    # 1) 후보 돌파 검출 (as-of D 절단으로 검출 — 룩어헤드 없음). 돌파일 ∈ 마지막 10거래일.
    candidates = []
    for code, stD in stD_by_code.items():
        last10 = set(stD["dates"][-ENTRY_WINDOW:])
        for pname, replay_fn, events_fn in PATTERNS:
            for ev in events_fn(replay_fn(stD, SCAN_DAYS, None)):
                if ev["date"] in last10 and ev["pivot_price"]:
                    candidates.append({"code": code, "pattern": pname,
                                       "date": ev["date"], "pivot": ev["pivot_price"]})
    print(f"후보 돌파 {len(candidates)}")

    # 2) 돌파일별 교차 RS (as-of 그 날짜) — 후보에 등장한 날짜만
    bdates = sorted({c["date"] for c in candidates})
    rs_by_date = {}
    for bd in bdates:
        rows = []
        for code, full in full_by_code.items():
            cl = truncate_series(full, bd)["closes"]
            if len(cl) >= 200:
                rows.append({"code": code, "closes": cl, "ok": True})
        rs_by_date[bd] = _compute_rs_for_all(rows)
    print(f"돌파일 RS 계산 {len(bdates)}일")

    # 3) 돌파일 기준 트렌드 게이트 통과분만 시뮬
    events, ambiguous = [], []
    for c in candidates:
        code, bd = c["code"], c["date"]
        rs = (rs_by_date[bd].get(code) or {}).get("rs")
        st_bd = truncate_series(full_by_code[code], bd)
        if not evaluate_trend_template(st_bd["closes"], rs=rs, rs_min=RS_MIN)["pass"]:
            continue
        full = full_by_code[code]
        bi = full["dates"].index(bd)
        sim = simulate_pivot_trade(full, bi, c["pivot"])
        rec = {
            "code": code, "name": meta[code].get("name", code),
            "market": meta[code].get("market"), "pattern": c["pattern"],
            "breakout_date": bd, "pivot": round(c["pivot"], 2),
            "rs": rs, "price_bucket": price_bucket(c["pivot"]),
            "rel_vol": rel_volume(full, bi), **sim,
        }
        rec["rel_vol_bucket"] = relvol_bucket(rec["rel_vol"])
        rec["rs_bucket"] = rs_bucket(rs)
        events.append(rec)
        if sim["result"] == "ambiguous":
            ambiguous.append(rec)
    print(f"게이트 통과 엔트리 {len(events)} · ambiguous {len(ambiguous)}")

    # ③ 종목-돌파일 중복 제거 stock-level (보수적: 패<예외<승 우선순위로 1건 대표)
    prio = {"loss": 0, "ambiguous": 1, "win": 2, "unresolved": 3}
    by_pair = {}
    for e in events:
        k = (e["code"], e["breakout_date"])
        if k not in by_pair or prio[e["result"]] < prio[by_pair[k]["result"]]:
            by_pair[k] = e
    stock_events = list(by_pair.values())

    by_feature = {k: group_win_rate(events, k)
                  for k in ("pattern", "market", "price_bucket", "rel_vol_bucket", "rs_bucket")}
    forward_last = max((s["dates"][-1] for s in full_by_code.values()), default=None)
    return {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "params": {"asof": asof, "target_pct": 10, "stop_pct": 5,
                   "rs_min": RS_MIN, "entry_window": ENTRY_WINDOW,
                   "gate": "per_breakout_date", "forward_last": forward_last},
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
    p = ROOT / "public" / "data" / f"pivot-backtest-{args.asof}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"💾 저장: {p.relative_to(ROOT)}")
    s = out["summary"]
    ss = out["summary_stock_level"]
    print(f"\n총 {s['n']} · 승 {s['win']} 패 {s['loss']} 예외 {s['ambiguous']} 미결 {s['unresolved']} "
          f"· 결착승률 {s['win_rate_resolved']}% (최악 {s['win_rate_worst']}%~최선 {s['win_rate_best']}%)")
    print(f"고유 종목·돌파일 {out['unique_stock_days']} · stock-level 결착승률 {ss['win_rate_resolved']}%")


if __name__ == "__main__":
    main()

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

    # 1) as-of 시계열 수집 + RS 계산
    asof_series, rows = {}, []
    for code in codes:
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            continue
        st = truncate_series(s, asof)
        if len(st["closes"]) < 200:      # 트렌드/RS 최소 데이터
            continue
        asof_series[code] = (s, st)
        rows.append({"code": code, "closes": st["closes"], "ok": True})
    rs_map = _compute_rs_for_all(rows)   # {code: {rs, ...}}
    print(f"시계열 확보 {len(asof_series)} · RS 산출 {sum(1 for v in rs_map.values() if v.get('rs'))}")

    # 2) 트렌드 게이트 → 3) 패턴 돌파 → 4) 시뮬
    events, ambiguous = [], []
    n_pass = 0
    for code, (full, st) in asof_series.items():
        rs = (rs_map.get(code) or {}).get("rs")
        tt = evaluate_trend_template(st["closes"], rs=rs, rs_min=RS_MIN)
        if not tt["pass"]:
            continue
        n_pass += 1
        last10 = set(st["dates"][-ENTRY_WINDOW:])
        for pname, replay_fn, events_fn in PATTERNS:
            rep = replay_fn(st, SCAN_DAYS, None)
            for ev in events_fn(rep):
                if ev["date"] not in last10:
                    continue
                pivot = ev["pivot_price"]
                if not pivot:
                    continue
                bi = full["dates"].index(ev["date"])
                sim = simulate_pivot_trade(full, bi, pivot)
                rec = {
                    "code": code, "name": meta[code].get("name", code),
                    "market": meta[code].get("market"), "pattern": pname,
                    "breakout_date": ev["date"], "pivot": round(pivot, 2),
                    "rs": rs, "price_bucket": price_bucket(pivot),
                    "rel_vol": rel_volume(full, bi), **sim,
                }
                rec["rel_vol_bucket"] = relvol_bucket(rec["rel_vol"])
                rec["rs_bucket"] = rs_bucket(rs)
                events.append(rec)
                if sim["result"] == "ambiguous":
                    ambiguous.append(rec)
    print(f"트렌드 통과 {n_pass} · 엔트리 이벤트 {len(events)} · ambiguous {len(ambiguous)}")

    by_feature = {k: group_win_rate(events, k)
                  for k in ("pattern", "market", "price_bucket", "rel_vol_bucket", "rs_bucket")}
    return {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "params": {"asof": asof, "target_pct": 10, "stop_pct": 5,
                   "rs_min": RS_MIN, "entry_window": ENTRY_WINDOW,
                   "forward_last": full["dates"][-1] if asof_series else None},
        "summary": tally(events),
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
    print(f"\n총 {s['n']} · 승 {s['win']} 패 {s['loss']} 예외 {s['ambiguous']} 미결 {s['unresolved']} "
          f"· 결착승률 {s['win_rate_resolved']}%")


if __name__ == "__main__":
    main()

# scripts/screen_vcp.py
"""find-vcp — SEPA 2단계: 트렌드 통과 종목의 VCP 베이스·피벗 탐지.

입력: public/data/sepa-trend-candidates.json (all_pass 종목)
출력: public/data/sepa-vcp-candidates.json
정의: docs/superpowers/specs/2026-06-29-find-vcp-design.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import ohlcv_matrix  # noqa: E402
from canslim_lib.vcp import evaluate_vcp, DEFAULT_PARAMS  # noqa: E402

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-trend-candidates.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-vcp-candidates.json"
STATUS_ORDER = {"breakout": 0, "actionable": 1, "forming": 2, "failed": 3}


def run(args) -> None:
    in_path = Path(args.inp) if args.inp else IN_PATH
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    data = json.loads(in_path.read_text(encoding="utf-8"))
    passers = [c for c in data.get("candidates", []) if c.get("all_pass")]
    if args.ticker:
        passers = [c for c in passers if c.get("code") == args.ticker]

    params = {
        "lookback_days": args.lookback_days, "zigzag_pct": args.zigzag_pct,
        "max_final_depth": args.max_final_depth, "breakout_vol_mult": args.breakout_vol_mult,
        "near_pivot_pct": DEFAULT_PARAMS["near_pivot_pct"],
    }
    out_cands = []
    for c in passers:
        code = c["code"]
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            r = {"vcp_detected": False, "status": "forming", "reason": "no_series",
                 "num_contractions": 0, "contractions": [], "pivot_price": None,
                 "pct_to_pivot": None, "volume_dryup_ratio": None, "tightness_pct": None,
                 "base_length_days": 0, "base_depth_pct": None, "swings": []}
        else:
            r = evaluate_vcp(s, params)
        out_cands.append({
            "code": code, "name": c.get("name"), "market": c.get("market"),
            "current_price": c.get("current_price"), "rs": c.get("rs"),
            **r,
        })

    out_cands.sort(key=lambda x: (STATUS_ORDER.get(x["status"], 9),
                                  x["pct_to_pivot"] if x["pct_to_pivot"] is not None else 1e9))
    dist = {k: sum(1 for x in out_cands if x["status"] == k)
            for k in ("breakout", "actionable", "forming", "failed")}
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": data.get("asof"),
        "source": in_path.name,
        "params": params,
        "vcp_count": sum(1 for x in out_cands if x["vcp_detected"]),
        "status_distribution": dist,
        "candidates": out_cands,
    }

    if not args.ticker:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 저장: {OUT_PATH.relative_to(ROOT)}")

    print(f"\n[VCP 요약] 입력 {len(passers)}종목 | VCP {output['vcp_count']} | "
          f"breakout {dist['breakout']} · actionable {dist['actionable']} · "
          f"forming {dist['forming']} · failed {dist['failed']}")
    for x in out_cands:
        if x["status"] in ("breakout", "actionable"):
            print(f"  [{x['status']:10s}] {x['code']} {str(x['name'])[:12]:12s} "
                  f"T={x['num_contractions']} 피벗 {x['pivot_price']} "
                  f"→ {x['pct_to_pivot']}% dryup {x['volume_dryup_ratio']}")


def main():
    global OUT_PATH
    ap = argparse.ArgumentParser(description="find-vcp — VCP 베이스·피벗 탐지")
    ap.add_argument("--in", dest="inp", default=None, help=f"입력(default {IN_PATH.name})")
    ap.add_argument("--out", dest="out", default=None, help=f"출력(default {OUT_PATH.name})")
    ap.add_argument("--ticker", default=None, help="단일 종목 디버그(저장 안 함)")
    ap.add_argument("--lookback-days", type=int, default=DEFAULT_PARAMS["lookback_days"])
    ap.add_argument("--zigzag-pct", type=float, default=DEFAULT_PARAMS["zigzag_pct"])
    ap.add_argument("--max-final-depth", type=float, default=DEFAULT_PARAMS["max_final_depth"])
    ap.add_argument("--breakout-vol-mult", type=float, default=DEFAULT_PARAMS["breakout_vol_mult"])
    args = ap.parse_args()
    if args.out:
        OUT_PATH = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    run(args)


if __name__ == "__main__":
    main()

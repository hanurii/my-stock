# scripts/screen_power_play.py
"""find-power-play — SEPA 패턴: 트렌드 통과 종목의 파워 플레이(High Tight Flag) 탐지.

입력: public/data/sepa-trend-candidates.json (all_pass 종목)
출력: public/data/sepa-power-play-candidates.json
정의: docs/superpowers/specs/2026-06-29-find-power-play-design.md
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
from canslim_lib.power_play import evaluate_power_play, DEFAULT_PARAMS  # noqa: E402

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-trend-candidates.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-power-play-candidates.json"
STATUS_ORDER = {"breakout": 0, "actionable": 1, "forming": 2, "failed": 3}

EMPTY = {
    "pattern_detected": False, "entry_ready": False, "status": "forming",
    "flagpole_gain_pct": None, "flagpole_days": None, "flagpole_vol_ratio": None,
    "pre_pole_gain_pct": None, "flag_length_days": None, "flag_depth_pct": None,
    "pivot_price": None, "pct_to_pivot": None, "volume_dryup_ratio": None,
    "tightness_pct": None, "pole_start_date": None, "flag_high_date": None,
}


def run(args, out_path: Path) -> None:
    in_path = Path(args.inp) if args.inp else IN_PATH
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not in_path.exists():
        print(f"❌ 입력 파일 없음: {in_path.relative_to(ROOT)}\n"
              f"   먼저 find-trend-template 을 실행해 sepa-trend-candidates.json 을 생성하세요.")
        sys.exit(1)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    passers = [c for c in data.get("candidates", []) if c.get("all_pass")]
    if args.ticker:
        passers = [c for c in passers if c.get("code") == args.ticker]

    params = {
        "lookback_days": args.lookback_days,
        "min_flagpole_gain": args.min_flagpole_gain,
        "max_flagpole_days": args.max_flagpole_days,
        "pole_vol_mult": args.pole_vol_mult,
        "max_pre_pole_gain": args.max_pre_pole_gain,
        "min_flag_pullback": args.min_flag_pullback,
        "min_flag_days": args.min_flag_days,
        "max_flag_days": args.max_flag_days,
        "max_flag_depth": args.max_flag_depth,
        "breakout_vol_mult": args.breakout_vol_mult,
        "near_pivot_pct": args.near_pivot_pct,
        "tight_pct": args.tight_pct,
        "contraction_grace": args.contraction_grace,
    }
    out_cands = []
    for c in passers:
        code = c["code"]
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            r = {**EMPTY, "reason": "no_series"}
        else:
            try:
                r = evaluate_power_play(s, params)
            except Exception as e:  # 한 종목 오류가 전체 런을 멈추지 않게
                r = {**EMPTY, "status": "failed", "reason": f"eval_error:{type(e).__name__}"}
        out_cands.append({
            "code": code, "name": c.get("name"), "market": c.get("market"),
            "current_price": c.get("current_price"), "rs": c.get("rs"),
            **r,
        })

    out_cands.sort(key=lambda x: (
        0 if x.get("entry_ready") else 1,
        STATUS_ORDER.get(x["status"], 9),
        x["pct_to_pivot"] if x["pct_to_pivot"] is not None else 1e9,
    ))
    dist = {k: sum(1 for x in out_cands if x["status"] == k)
            for k in ("breakout", "actionable", "forming", "failed")}
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": data.get("asof"),
        "source": in_path.name,
        "params": {**DEFAULT_PARAMS, **params},
        "pattern_count": sum(1 for x in out_cands if x["pattern_detected"]),
        "entry_ready_count": sum(1 for x in out_cands if x.get("entry_ready")),
        "status_distribution": dist,
        "candidates": out_cands,
    }

    if not args.ticker:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 저장: {out_path.relative_to(ROOT)}")

    er = output["entry_ready_count"]
    print(f"\n[파워플레이 요약] 입력 {len(passers)}종목 | 패턴 {output['pattern_count']} | "
          f"진입가능(entry_ready) {er} | "
          f"breakout {dist['breakout']} · actionable {dist['actionable']} · "
          f"forming {dist['forming']} · failed {dist['failed']}")
    shown = [x for x in out_cands if x.get("entry_ready")]
    if not shown:
        print("  (진입 가능 종목 없음 — 파워플레이 성립 + 돌파/근접 동시 충족 없음)")
    for x in shown:
        print(f"  [{x['status']:10s}] {x['code']} {str(x['name'])[:12]:12s} "
              f"깃대 {x['flagpole_gain_pct']}%/{x['flagpole_days']}d "
              f"깃발 {x['flag_depth_pct']}%/{x['flag_length_days']}d "
              f"피벗 {x['pivot_price']} → {x['pct_to_pivot']}%")


def main():
    ap = argparse.ArgumentParser(description="find-power-play — 파워 플레이(High Tight Flag) 탐지")
    ap.add_argument("--in", dest="inp", default=None, help=f"입력(default {IN_PATH.name})")
    ap.add_argument("--out", dest="out", default=None, help=f"출력(default {OUT_PATH.name})")
    ap.add_argument("--ticker", default=None, help="단일 종목 디버그(저장 안 함)")
    ap.add_argument("--lookback-days", type=int, default=DEFAULT_PARAMS["lookback_days"])
    ap.add_argument("--min-flagpole-gain", type=float, default=DEFAULT_PARAMS["min_flagpole_gain"])
    ap.add_argument("--max-flagpole-days", type=int, default=DEFAULT_PARAMS["max_flagpole_days"])
    ap.add_argument("--pole-vol-mult", type=float, default=DEFAULT_PARAMS["pole_vol_mult"])
    ap.add_argument("--max-pre-pole-gain", type=float, default=DEFAULT_PARAMS["max_pre_pole_gain"])
    ap.add_argument("--min-flag-pullback", type=float, default=DEFAULT_PARAMS["min_flag_pullback"])
    ap.add_argument("--min-flag-days", type=int, default=DEFAULT_PARAMS["min_flag_days"])
    ap.add_argument("--max-flag-days", type=int, default=DEFAULT_PARAMS["max_flag_days"])
    ap.add_argument("--max-flag-depth", type=float, default=DEFAULT_PARAMS["max_flag_depth"])
    ap.add_argument("--breakout-vol-mult", type=float, default=DEFAULT_PARAMS["breakout_vol_mult"])
    ap.add_argument("--near-pivot-pct", type=float, default=DEFAULT_PARAMS["near_pivot_pct"])
    ap.add_argument("--tight-pct", type=float, default=DEFAULT_PARAMS["tight_pct"])
    ap.add_argument("--contraction-grace", type=int, default=DEFAULT_PARAMS["contraction_grace"])
    args = ap.parse_args()
    if args.out:
        out_path = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    else:
        out_path = OUT_PATH
    run(args, out_path)


if __name__ == "__main__":
    main()

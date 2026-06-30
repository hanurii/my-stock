# scripts/screen_power_play_history.py
"""find-power-play-history — 파워 플레이 검출기 회고·검증.

입력: public/data/sepa-power-play-candidates.json (기본 전체 후보)
출력: public/data/sepa-power-play-history.json
정의: docs/superpowers/specs/2026-06-30-find-power-play-history-design.md
"""
from __future__ import annotations

import argparse
import json
import statistics
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
from canslim_lib.power_play import DEFAULT_PARAMS  # noqa: E402
from canslim_lib.power_play_history import (  # noqa: E402
    replay_power_play, find_breakout_events, post_breakout_outcome, classify,
)

KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-power-play-candidates.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-power-play-history.json"
CAVEAT = ("집계 수익률은 추세 통과(RS 강세) 종목만 본 결과라 생존자 편향으로 과대평가됨. "
          "검출기 신뢰의 보조 지표일 뿐, 결정적 검증은 이벤트 날짜를 차트로 눈 대조하는 것.")
CLASS_ORDER = {"re_basing": 0, "recent_breakout": 1, "extended": 2, "no_power_play_found": 3}


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def run(args, out_path: Path) -> None:
    in_path = Path(args.inp) if args.inp else IN_PATH
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not in_path.exists():
        print(f"❌ 입력 파일 없음: {in_path.relative_to(ROOT)}\n"
              f"   먼저 find-power-play 를 실행해 sepa-power-play-candidates.json 을 생성하세요.")
        sys.exit(1)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    cands = data.get("candidates", [])
    by_code = {c["code"]: c for c in cands}

    if args.codes:
        codes = [x.strip() for x in args.codes.split(",") if x.strip()]
        filt = "codes"
    else:
        codes = [c["code"] for c in cands]
        filt = "all"

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
    }

    stocks = []
    for code in codes:
        meta = by_code.get(code, {})
        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            stocks.append({"code": code, "name": meta.get("name"), "market": meta.get("market"),
                           "rs": meta.get("rs"), "classification": "no_power_play_found",
                           "num_events": 0, "most_recent_event_date": None, "events": [],
                           "reason": "no_series"})
            continue
        rep = replay_power_play(s, args.scan_days, params)
        raw = find_breakout_events(rep, args.confirm_lookback)
        events = []
        for e in raw:
            o = post_breakout_outcome(s, e["date"], args.stop_pct, args.target_pct) or {}
            ev = {**e, **o}
            ev.pop("replay_idx", None)
            events.append(ev)
        cls = classify(raw, rep, args.recent_days)
        stocks.append({"code": code, "name": meta.get("name"), "market": meta.get("market"),
                       "rs": meta.get("rs"), "classification": cls, "num_events": len(events),
                       "most_recent_event_date": events[-1]["date"] if events else None,
                       "events": events})

    stocks.sort(key=lambda x: (CLASS_ORDER.get(x["classification"], 9), -(x.get("rs") or 0)))

    all_events = [e for st in stocks for e in st["events"]]
    summary = {
        "n_stocks": len(stocks),
        "n_with_events": sum(1 for st in stocks if st["num_events"] > 0),
        "n_no_power_play_found": sum(1 for st in stocks if st["classification"] == "no_power_play_found"),
        "total_events": len(all_events),
        "agg": {
            "median_gain_since_pct": _median([e.get("gain_since_pct") for e in all_events]),
            "median_max_gain_pct": _median([e.get("max_gain_pct") for e in all_events]),
            "good_breakout_rate": (round(sum(1 for e in all_events if e.get("good_breakout")) / len(all_events), 3)
                                   if all_events else None),
        },
    }
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": data.get("asof"), "source": in_path.name, "input_filter": filt,
        "scan_days": args.scan_days,
        "params": {**params, "confirm_lookback": args.confirm_lookback, "recent_days": args.recent_days,
                   "stop_pct": args.stop_pct, "target_pct": args.target_pct},
        "caveat": CAVEAT, "summary": summary, "stocks": stocks,
    }

    if not args.ticker:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 저장: {out_path.relative_to(ROOT)}")

    print(f"\n[PP-history] 입력 {summary['n_stocks']}종목({filt}) | "
          f"이벤트보유 {summary['n_with_events']} · 미검출 {summary['n_no_power_play_found']} | "
          f"총 이벤트 {summary['total_events']}")
    for st in stocks:
        ev = st["events"][-1] if st["events"] else None
        tail = (f"최근 {ev['date']} 피벗 {ev['pivot_price']} → 현재 {ev.get('gain_since_pct')}% "
                f"(최대 {ev.get('max_gain_pct')}%, {ev.get('days_since')}일 경과)") if ev else "-"
        print(f"  [{st['classification']:19s}] {st['code']} {str(st['name'])[:12]:12s} "
              f"RS{st.get('rs')} | {tail}")
    agg = summary["agg"]
    print(f"\n[집계·참고용] 돌파후 수익률 중앙 {agg['median_gain_since_pct']}% · "
          f"최대 중앙 {agg['median_max_gain_pct']}% · good_breakout율 {agg['good_breakout_rate']}")
    print(f"⚠️ {CAVEAT}")


def main():
    ap = argparse.ArgumentParser(description="find-power-play-history — 파워 플레이 검출기 회고·검증")
    ap.add_argument("--in", dest="inp", default=None, help=f"입력(default {IN_PATH.name})")
    ap.add_argument("--out", dest="out", default=None, help=f"출력(default {OUT_PATH.name})")
    ap.add_argument("--codes", default=None, help="임의 코드 목록 쉼표구분 (예 005930,000660)")
    ap.add_argument("--ticker", default=None, help="단일 종목 디버그(저장 안 함)")
    ap.add_argument("--scan-days", type=int, default=250)
    ap.add_argument("--confirm-lookback", type=int, default=5)
    ap.add_argument("--recent-days", type=int, default=10)
    ap.add_argument("--stop-pct", type=float, default=8.0)
    ap.add_argument("--target-pct", type=float, default=20.0)
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
    args = ap.parse_args()
    if args.ticker:
        args.codes = args.ticker
    out_path = (Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out) if args.out else OUT_PATH
    run(args, out_path)


if __name__ == "__main__":
    main()

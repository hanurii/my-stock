# scripts/resolve_ambiguous.py
"""백테스트 예외(ambiguous) 이벤트를 과거 1분봉으로 승/패 확정 → JSON 갱신 → 리포트 재생성.
실행: python scripts/resolve_ambiguous.py [--infile public/data/pivot-backtest-2026-04-01.json]
정의: docs/superpowers/specs/2026-07-07-resolve-ambiguous-minute-design.md
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# .env(주 작업트리) 로드 → KIS 인증
for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        import os
        os.environ.setdefault(k, v)

from canslim_lib import ohlcv_matrix, minute_bars  # noqa: E402
from canslim_lib.pivot_backtest import resolve_minute_trade, tally, group_win_rate  # noqa: E402

# ohlcv_matrix 의 SERIES_DIR/FOREIGN_PATH 는 자신의 __file__ 기준(=이 워크트리 루트)으로
# 계산되는데, 실제 OHLCV 시계열 캐시(.cache/ohlcv/, gitignore)는 정션 없이 주 작업트리에만
# 있다. .env/.cache/min_daily 와 동일하게 절대경로로 덮어써 워크트리에서 실행해도 주
# 작업트리의 캐시를 읽도록 한다(ohlcv_matrix.py 자체는 공유 라이브러리라 수정하지 않음).
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"

FEATURE_KEYS = ("pattern", "market", "price_bucket", "rel_vol_bucket", "rs_bucket")


def run(infile: Path) -> None:
    d = json.loads(infile.read_text(encoding="utf-8"))
    events = d["events"]
    amb = [e for e in events if e["result"] == "ambiguous"]
    print(f"예외 {len(amb)}건 분봉 판정 시작…")

    by_id = {(e["code"], e["breakout_date"], e["pattern"]): e for e in events}
    resolved = {"win": 0, "loss": 0, "stay": 0}
    for e in amb:
        s = ohlcv_matrix.get_series(e["code"])
        if not s or e["breakout_date"] not in s["dates"]:
            e["minute_resolution"] = {"result": "ambiguous", "reason": "no_daily"}
            resolved["stay"] += 1
            continue
        bi = s["dates"].index(e["breakout_date"])
        mins = minute_bars.fetch_day_minutes(e["code"], e["breakout_date"])
        r = resolve_minute_trade(mins, s, bi, e["pivot"])
        e["minute_resolution"] = r
        if r["result"] in ("win", "loss"):
            e["result"] = r["result"]
            e["resolve_date"] = r["resolve_date"]
            e["exit_reason"] = f"minute:{r['reason']}"
            resolved[r["result"]] += 1
        else:
            resolved["stay"] += 1
        print(f"  {e['code']} {e['name']} {e['breakout_date']} → {r['result']}"
              f"({r.get('reason')},{r.get('resolved_by')})")

    # 재집계
    d["summary"] = tally(events)
    d["by_pattern"] = group_win_rate(events, "pattern")
    d["by_feature"] = {k: group_win_rate(events, k) for k in FEATURE_KEYS}
    prio = {"loss": 0, "ambiguous": 1, "win": 2, "unresolved": 3}
    by_pair = {}
    for e in events:
        k = (e["code"], e["breakout_date"])
        if k not in by_pair or prio[e["result"]] < prio[by_pair[k]["result"]]:
            by_pair[k] = e
    d["summary_stock_level"] = tally(list(by_pair.values()))
    d["unique_stock_days"] = len(by_pair)
    d["ambiguous"] = [e for e in events if e["result"] == "ambiguous"]
    d["params"]["minute_resolved"] = True

    infile.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = d["summary"]
    print(f"\n분봉 확정: 승 {resolved['win']} · 패 {resolved['loss']} · 잔여예외 {resolved['stay']}")
    print(f"갱신 요약: 총 {s['n']} · 승 {s['win']} 패 {s['loss']} 예외 {s['ambiguous']} "
          f"· 결착 {s['win_rate_resolved']}% (최악 {s['win_rate_worst']}~최선 {s['win_rate_best']}%)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="public/data/pivot-backtest-2026-04-01.json")
    args = ap.parse_args()
    run(ROOT / args.infile)


if __name__ == "__main__":
    main()

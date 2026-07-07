# scripts/resolve_ambiguous_multi.py
"""익일진입 다기간 백테스트(pivot_backtest_nextday_multi)의 예외(ambiguous)를
진입일(entry_date) 분봉으로 승/패 확정. resolve_ambiguous.py 의 다기간판
(entry_date·by_month/by_pattern/by_price 집계). scale_mismatch 방어 포함.
실행: python scripts/resolve_ambiguous_multi.py --infile public/data/pivot-backtest-nextday-april-daily.json
정션 금지 — .env·.cache 는 주 작업트리(my-stock) 절대경로 참조.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)

from canslim_lib import ohlcv_matrix, minute_bars  # noqa: E402
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"
from canslim_lib.pivot_backtest import resolve_minute_trade, tally, group_win_rate  # noqa: E402


def run(infile: Path) -> None:
    d = json.loads(infile.read_text(encoding="utf-8"))
    events = d["events"]
    amb = [e for e in events if e["result"] == "ambiguous"]
    print(f"예외 {len(amb)}건 분봉 판정 시작…")
    res = {"win": 0, "loss": 0, "stay": 0}
    for e in amb:
        s = ohlcv_matrix.get_series(e["code"])
        ed = e["entry_date"]
        if not s or ed not in s["dates"]:
            e["minute_resolution"] = {"result": "ambiguous", "reason": "no_daily"}
            res["stay"] += 1
            continue
        bi = s["dates"].index(ed)
        mins = minute_bars.fetch_day_minutes(e["code"], ed)
        if mins:
            mhigh = max(m["h"] for m in mins)
            dhigh = s["highs"][bi]
            if mhigh and dhigh and abs(dhigh / mhigh - 1) > 0.03:
                e["minute_resolution"] = {"result": "ambiguous", "resolved_by": "minute",
                                          "reason": "scale_mismatch", "resolve_date": ed}
                res["stay"] += 1
                print(f"  {e['code']} {e['name']} {ed} → scale_mismatch")
                continue
        r = resolve_minute_trade(mins, s, bi, e["pivot"])
        e["minute_resolution"] = r
        if r["result"] in ("win", "loss"):
            e["result"] = r["result"]
            e["resolve_date"] = r["resolve_date"]
            e["exit_reason"] = f"minute:{r['reason']}"
            res[r["result"]] += 1
        else:
            res["stay"] += 1
        print(f"  {e['code']} {e['name']} {ed} → {r['result']}({r.get('reason')})", flush=True)

    d["summary"] = tally(events)
    d["by_month"] = group_win_rate(events, "month")
    d["by_pattern"] = group_win_rate(events, "pattern")
    d["by_price"] = group_win_rate(events, "price_bucket")
    d["params"]["minute_resolved"] = True

    infile.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = d["summary"]
    print(f"\n분봉 확정: 승 {res['win']} · 패 {res['loss']} · 잔여예외 {res['stay']}")
    print(f"갱신: 총 {s['n']} 승 {s['win']} 패 {s['loss']} 예외 {s['ambiguous']} 미결 {s['unresolved']} "
          f"· 결착 {s['win_rate_resolved']}% [{s['win_rate_worst']}~{s['win_rate_best']}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="public/data/pivot-backtest-nextday-april-daily.json")
    a = ap.parse_args()
    run(ROOT / a.infile)


if __name__ == "__main__":
    main()

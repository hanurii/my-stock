"""등가중 시장 국면 지수 → public/data/market-regime.json.
전 종목 일평균수익 누적 등가중 지수 + 20일선 + 국면(위/아래). 봇·리포트와 동일 잣대.
실행: python -X utf8 scripts/build_market_regime.py. 정션 금지 — 캐시는 주 작업트리 절대경로."""
from __future__ import annotations
import json, sys
from datetime import datetime
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
from autobuy.watchlist import build_ew_index  # noqa: E402

WINDOW = 250
MA = 20


def build():
    codes = [p.stem for p in (MAIN / ".cache" / "ohlcv" / "series").glob("*.json")]
    idx = build_ew_index(ohlcv_matrix.get_series, codes)
    all_dates = sorted({d for c in codes for d in (ohlcv_matrix.get_series(c) or {}).get("dates", [])})
    n = min(len(idx), len(all_dates))
    idx, all_dates = idx[:n], all_dates[:n]
    ma20 = [None] * n
    for i in range(n):
        if i >= MA - 1:
            ma20[i] = sum(idx[i - MA + 1:i + 1]) / MA
    start = max(0, n - WINDOW)
    base = idx[start] or 1.0
    series = []
    for i in range(start, n):
        v = idx[i] / base * 100
        m = (ma20[i] / base * 100) if ma20[i] is not None else None
        up = (v > m) if m is not None else None
        series.append({"date": all_dates[i], "index": round(v, 2),
                       "ma20": (round(m, 2) if m is not None else None), "up": up})
    last = series[-1]
    out = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "current": {"date": last["date"], "index": last["index"], "ma20": last["ma20"], "uptrend": last["up"]},
           "series": series}
    outp = ROOT / "public" / "data" / "market-regime.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"저장 {outp} · {len(series)}일 · 현재 {last['date']} 지수 {last['index']} "
          f"20MA {last['ma20']} → {'상승추세' if last['up'] else '하락추세'}")


if __name__ == "__main__":
    build()

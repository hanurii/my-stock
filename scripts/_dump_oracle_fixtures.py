"""find-3c 오라클 fixture 덤프(1회용 개발 보조). FDR로 NU·GOOG·CRUS OHLCV를 받아
tests/fixtures/oracle/{ticker}.json 으로 저장. pytest 는 이 fixture만 읽는다(네트워크 X).
"""
from __future__ import annotations
import json
from pathlib import Path
import FinanceDataReader as fdr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "oracle"
SPECS = {
    "NU":   ("2023-01-01", "2023-10-25"),
    "GOOG": ("2004-08-19", "2005-01-05"),
    "CRUS": ("2009-06-01", "2010-03-10"),
    "JBLU":   ("2013-10-01", "2014-11-07"),
    "AAPL":   ("2003-08-01", "2004-08-16"),
    "089970": ("2020-03-01", "2021-03-22"),
    "000150": ("2020-07-01", "2021-07-06"),
    "010640": ("2020-12-01", "2021-12-10"),
}


def dump(ticker: str, start: str, end: str) -> int:
    df = fdr.DataReader(ticker, start, end)
    rows = [{"date": idx.strftime("%Y-%m-%d"),
             "open": float(r["Open"]), "high": float(r["High"]),
             "low": float(r["Low"]), "close": float(r["Close"]),
             "volume": float(r["Volume"])}
            for idx, r in df.iterrows()]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{ticker}.json").write_text(
        json.dumps({"ticker": ticker, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return len(rows)


if __name__ == "__main__":
    for tk, (s, e) in SPECS.items():
        n = dump(tk, s, e)
        print(f"{tk}: {n} rows -> tests/fixtures/oracle/{tk}.json")

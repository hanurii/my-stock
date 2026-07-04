"""MIK(마이클스컴퍼니, 상폐) 일봉 → vcp_oracle_mik.json 고정 오라클 변환(일회성).

상폐 종목이라 야후/stooq/Nasdaq 무료 경로는 전멸(삭제·봇차단). Tiingo(상폐 이력
보존)에서 원시 OHLCV를 받아 검출기 로더 형식(6키)으로 저장한다. 스플릿·배당 없는
구간이라 원시가격=조정가격(미너비니 차트와 동일).

토큰은 환경변수 TIINGO_API_KEY 에서 읽는다(커밋에 비밀 미포함).
재현: `TIINGO_API_KEY=... python scripts/_build_mik_oracle.py`
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "data" / "vcp_oracle_mik.json"
START, END = "2014-06-01", "2015-06-30"


def main() -> int:
    tok = os.environ.get("TIINGO_API_KEY")
    if not tok:
        print("환경변수 TIINGO_API_KEY 필요", file=sys.stderr)
        return 2
    url = (f"https://api.tiingo.com/tiingo/daily/MIK/prices"
           f"?startDate={START}&endDate={END}&token={tok}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Accept": "application/json"})
    rows = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    rows = [r for r in rows if r.get("close") is not None]
    rows.sort(key=lambda r: r["date"])
    out = {
        "dates":   [r["date"][:10] for r in rows],
        "opens":   [float(r["open"]) for r in rows],
        "highs":   [float(r["high"]) for r in rows],
        "lows":    [float(r["low"]) for r in rows],
        "closes":  [float(r["close"]) for r in rows],
        "volumes": [int(r["volume"]) for r in rows],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} first={out['dates'][0]} last={out['dates'][-1]} "
          f"2014-11-06={'2014-11-06' in out['dates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

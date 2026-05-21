"""0단계 사전 검증 — SK하이닉스(000660) 기준.

1) fetch_yahoo_chart 다년(2y) 시세 확장이 동작하는지
2) DART 과거 분기 주당순이익 point-in-time 조회가 동작하는지

해석/판정 없음. raw 값 출력만. 수동 공시 대조용.
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # my-stock/
sys.path.insert(0, str(ROOT / "scripts"))

# .env 수동 로드 (DART_API_KEY)
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from canslim_lib.fetch import (  # noqa: E402
    fetch_yahoo_chart,
    load_corp_code_map,
    fetch_dart_quarterly_eps_history,
    fetch_dart_quarterly_sales_history,
)

KST = timezone(timedelta(hours=9))
CODE = "000660"
SYMBOL = "000660.KS"


def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, KST).strftime("%Y-%m-%d")


def test_yahoo(range_: str):
    chart = fetch_yahoo_chart(SYMBOL, range_=range_, interval="1d")
    if not chart:
        print(f"  [{range_}] FAIL: None 반환")
        return
    ts = chart["timestamps"]
    cl = chart["closes"]
    if not ts:
        print(f"  [{range_}] FAIL: 빈 데이터")
        return
    print(f"  [{range_}] OK  거래일 {len(ts)}개  "
          f"{fmt_ts(ts[0])} ~ {fmt_ts(ts[-1])}  "
          f"종가범위 {min(cl):,.0f} ~ {max(cl):,.0f}  최신종가 {cl[-1]:,.0f}")


def main():
    print("=== 1) Yahoo 다년 시세 확장 검증 (SK하이닉스 000660.KS) ===")
    for r in ("1y", "2y", "5y"):
        test_yahoo(r)

    print()
    print("=== 2) DART 과거 분기 주당순이익 point-in-time 검증 ===")
    corp_map = load_corp_code_map()
    if not corp_map:
        print("  FAIL: corp_code 맵 비어있음 (DART_API_KEY 확인)")
        return
    corp_code = corp_map.get(CODE)
    print(f"  corp_code({CODE}) = {corp_code}")
    if not corp_code:
        print("  FAIL: SK하이닉스 corp_code 미발견")
        return

    for base_year in (2025, 2024):
        eps = fetch_dart_quarterly_eps_history(corp_code, base_year)
        sales = fetch_dart_quarterly_sales_history(corp_code, base_year)
        print(f"  [base_year={base_year}] 분기 기본주당이익(원):")
        for k, v in eps:
            print(f"      {k}  EPS = {v:,.0f}")
        print(f"  [base_year={base_year}] 분기 매출액(원):")
        for k, v in sales:
            print(f"      {k}  매출 = {v:,.0f}")


if __name__ == "__main__":
    main()

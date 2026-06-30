# scripts/_gen_pp_example_fixtures.py
"""책 파워플레이 예시 5종의 OHLCV를 FDR로 1회 받아 스냅샷 픽스처로 저장.
산출 tests/fixtures/power_play_examples.json 은 커밋되어 테스트가 네트워크 없이 돈다.
재생성: python scripts/_gen_pp_example_fixtures.py
"""
from __future__ import annotations
import json
from pathlib import Path
import FinanceDataReader as fdr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "power_play_examples.json"

# (이름, 코드, fetch시작, fetch끝, 피벗(저자), 기대검출, 비고)
CASES = [
    ("케이엠더블유", "032500", "2018-12-01", "2019-07-20", "2019-07-10", True, ""),
    ("화인베스틸", "133820", "2019-11-01", "2020-06-05", "2020-05-25", True, ""),
    ("티앤엘", "340570", "2021-01-04", "2021-06-25", "2021-06-16", False, "xfail:중첩깃발 후속"),
    ("다우데이타", "032190", "2019-08-01", "2020-05-15", "2020-05-07", False, "폴시작형 의도적 미검출"),
    ("BBY", "BBY", "1997-05-01", "1997-12-15", "1997-12-01", True, "분할조정"),
]


def main():
    stocks = []
    for name, code, s, e, pivot, expect, note in CASES:
        df = fdr.DataReader(code, s, e)
        dates = [d.strftime("%Y-%m-%d") for d in df.index]
        pv = pivot if pivot in dates else next(d for d in dates if d >= pivot)
        stocks.append({
            "name": name, "code": code, "pivot_date": pv,
            "expect_detected": expect, "note": note,
            "series": {
                "dates": dates,
                "closes": [round(float(x), 3) for x in df["Close"].tolist()],
                "highs": [round(float(x), 3) for x in df["High"].tolist()],
                "lows": [round(float(x), 3) for x in df["Low"].tolist()],
                "volumes": [int(x) for x in df["Volume"].tolist()],
            },
        })
        print(f"  {name} {code}: {len(dates)}봉, 피벗 {pv}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"cases": stocks}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"저장: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

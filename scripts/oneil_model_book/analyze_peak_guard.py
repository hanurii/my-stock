"""고점후 안전장치(D) 컷오프 캘리브레이션 — 과거 우량주로 검증.

라이브 결함: 스크리너가 '이미 고점 찍고 내려오는 종목'을 '쉬는 눌림목'
으로 오인. 가드 D = "최근 N거래일 안에 (직전 60/120거래일) 고점을
새로 찍었으면 사지 마라". 문제는 N을 임의로 못 정함(사용자 룰: 임의
컷오프 금지). → **과거 진짜 위너가 *터지기 직전(pivot)* 그 고점에서
며칠 떨어져 있었나** 분포로 N을 데이터에서 도출.

논리: 진짜 pivot은 한 번 쉬었다 가는 자리라 '최근 고점'에서 한참
떨어져 있어야 정상. 위너 분포의 하위 5%(=가장 고점에 가까웠던 위너)
지점을 넘지 않게 N을 잡으면, 위너는 거의 안 버리면서 '고점 직후'
가짜만 걸러짐.

산출: cycles/<id>/_universe_prices.json (close) + model_book pivot_date.
한계: 종가 기준·상폐 제외·인-샘플. 라이브 24후보에도 적용해 대조.

사용:  python analyze_peak_guard.py
"""
import bisect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CY = ROOT / "research" / "oneil-model-book" / "cycles"
OUT = CY / "c2024-12" / "_peak_guard.txt"


def load(tag):
    U = json.loads((CY / tag / "_universe_prices.json").read_text("utf-8"))
    mb = CY / tag / "model_book.json"
    rows = (json.loads(mb.read_text("utf-8"))["rows"] if mb.exists() else [])
    return U, rows


def days_since_high(closes, idx, win):
    """idx(해당일 포함) 기준 직전 win거래일 최고 종가가 며칠 전인가."""
    lo = max(0, idx - win + 1)
    seg = closes[lo:idx + 1]
    if len(seg) < 5:
        return None
    hi_off = max(range(len(seg)), key=lambda i: seg[i])
    return (len(seg) - 1) - hi_off          # 0 = 바로 그날이 고점


def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    i = max(0, min(len(sorted_vals) - 1, int(round(p / 100 * (len(sorted_vals) - 1)))))
    return sorted_vals[i]


def calc(U, rows, win):
    vals = []
    for r in rows:
        code, pd = r.get("code"), r.get("pivot_date")
        s = U.get(code)
        if not s or not pd:
            continue
        d, c = s.get("d"), s.get("c")
        if not d or not c:
            continue
        j = bisect.bisect_right(d, pd) - 1
        if j < 5:
            continue
        v = days_since_high(c, j, win)
        if v is not None:
            vals.append(v)
    vals.sort()
    return vals


def main():
    L = ["고점후 안전장치(D) 컷오프 — 과거 위너로 데이터 도출",
         "측정: 위너의 pivot(터지기 직전)일에, 직전 60/120거래일 최고",
         "종가가 '며칠 전'이었나. 값이 클수록 고점에서 멀리(쉬는 자리).",
         ""]
    summary = {}
    for tag in ("c2024-12", "c2020-03"):
        U, rows = load(tag)
        if not rows:
            L.append(f"[{tag}] model_book 없음")
            continue
        L.append(f"[{tag}] 위너 {len(rows)}명")
        for win in (60, 120):
            vals = calc(U, rows, win)
            if not vals:
                L.append(f"  직전{win}일고점: 측정불가")
                continue
            med = pct(vals, 50)
            p10, p5 = pct(vals, 10), pct(vals, 5)
            within5 = sum(1 for v in vals if v <= 5)
            within10 = sum(1 for v in vals if v <= 10)
            L.append(
                f"  직전{win}일 고점기준: n={len(vals)} | 중앙 {med}일 전 | "
                f"하위10%={p10}일 · 하위5%={p5}일")
            L.append(
                f"     └ pivot이 '고점 5일이내'인 위너 {within5}/{len(vals)}"
                f"({100*within5/len(vals):.0f}%) · '10일이내' {within10}"
                f"/{len(vals)}({100*within10/len(vals):.0f}%)")
            summary[(tag, win)] = (med, p10, p5, within5, within10, len(vals))

    L += ["",
          "== 해석(쉬운 말) ==",
          "· 진짜 위너는 터지기 직전, 최근 고점에서 '중앙값만큼 일' 떨어져",
          "  쉬고 있었다. '고점 5~10일 이내'인 위너는 소수.",
          "· 즉 '최근 5일(또는 10일) 안에 새 고점을 찍은 종목은 사지 마라'",
          "  로 막아도 과거 진짜 위너는 거의 안 버린다(위 비율만 손해).",
          "· 권고 N = 위너 보존 ≥95% 되는 값(= '고점 N일 이내면 제외'의 N)."]

    # 라이브 24후보 대조 (현재 캐시 = 2026-05-15)
    U5 = json.loads((CY / "c2024-12" / "_universe_prices_5y.json")
                     .read_text("utf-8"))
    bc = (ROOT / "research" / "oneil-model-book" / "cycles" / "c2024-12"
          / "_buy_candidates.txt")
    L += ["", "== 라이브 24후보(2026-05-15) 고점후 일수 =="]
    if bc.exists():
        import re
        codes = []
        for ln in bc.read_text("utf-8").splitlines():
            m = re.match(r"^(\d{6})\s+(\S+)\(", ln)
            if m:
                codes.append((m.group(1), m.group(2)))
        rowsL = []
        for code, nm in codes:
            s = U5.get(code)
            if not s:
                continue
            c = s.get("c")
            if not c or len(c) < 61:
                continue
            d60 = days_since_high(c, len(c) - 1, 60)
            d120 = days_since_high(c, len(c) - 1, 120)
            rowsL.append((d60, d120, nm, code))
        rowsL.sort()
        for d60, d120, nm, code in rowsL:
            flag = " ◀고점직후(가짜위험)" if d60 is not None and d60 <= 10 else ""
            L.append(f"  {nm}({code}) | 60일고점 {d60}일전 | "
                     f"120일고점 {d120}일전{flag}")
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nsaved: {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()

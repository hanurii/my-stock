"""2단계 — 폭발 직전 시점(pivot) 식별. (규칙 v2 — 델·시스코 역산)

오닐 정의(델 1996-11 / 시스코 1990 하반기 사례에서 역산):
  폭발 직전 시점 = 주가가 "짧은 반등"이 아니라 "수개월~수년 본격·지속 대상승"으로
  전환한 출발일. 바닥이 아님. 직전 횡보를 벗어나 이후 큰 되돌림 없이 고점까지
  지속 급등하는 그 시작점.
  ※ 펀더멘털은 pivot 선정에 사용하지 않음(CAN SLIM 미적용·순환논리 회피).
    pivot 직전 2개 확정 분기 키만 기록 → 3단계에서 값 수집해 사후 확인.

규칙(명시):
  탐색 구간 = 종목 저점일 ~ 고점일.
  pivot = 다음을 모두 만족하는 "가장 이른" 날 i:
    (a) 직전 25거래일(약 5주) 최고 종가 돌파  (횡보 base 이탈)
    (b) i → 고점 경로에서 종가가 진행 최고치 대비 20% 초과 하락 없음
        (= 짧은 반등이 아닌 '지속 급등')
    (c) 고점종가 / i종가 >= 2.0  (i 이후가 대상승의 본체)
  후보 없으면 폴백: 저점 이후 향후 60거래일 수익률 최대 구간 시작일.
  base(직전 횡보) = pivot 직전, 종가가 돌파선 아래 머문 마지막 연속 구간.

pivot 직전 "확정 분기" 2개 = pivot 시점에 공시 완료됐을 직전 2개 분기
  (분기 종료 + 45일 경과를 공시 가용 시점으로 간주) → 3단계 기준.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from canslim_lib.fetch import yahoo_symbol, sleep  # noqa: E402
import cyclecfg  # noqa: E402

KST = timezone(timedelta(hours=9))
DIR = cyclecfg.DIR
SRC = DIR / "winners_final.json"
OUT = DIR / "pivots.json"
TXT = DIR / "_pivots.txt"

BREAKOUT_WIN = 25          # 약 5주 횡보 base 이탈 판정 lookback
MAX_DRAWDOWN = 0.20        # pivot→고점 경로 허용 최대 되돌림 (지속 급등)
MIN_FWD_MULT = 2.0         # pivot 이후가 대상승 본체 (>=2배)
FALLBACK_FWD = 60
DISCLOSURE_LAG_DAYS = 45   # 분기 종료 후 공시 가용 간주 시점
SPARK = "▁▂▃▄▅▆▇█"


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, KST).strftime("%Y-%m-%d")


def prior_two_quarters(date_str: str) -> list[str]:
    """pivot 시점에 공시 완료됐을 직전 2개 분기 키 (YYYYMM, 03/06/09/12).

    분기 종료 + DISCLOSURE_LAG_DAYS 경과 시점을 '공시 가용'으로 간주.
    """
    piv = datetime.strptime(date_str, "%Y-%m-%d")
    qs: list[str] = []
    y = piv.year + 1
    while len(qs) < 8 and y >= piv.year - 3:
        for qm, qd in ((12, 31), (9, 30), (6, 30), (3, 31)):
            q_end = datetime(y, qm, qd)
            available = q_end + timedelta(days=DISCLOSURE_LAG_DAYS)
            if available <= piv:
                qs.append(f"{y}{qm:02d}")
        y -= 1
    qs = sorted(set(qs), reverse=True)
    return qs[:2]  # [직전분기, 그 전분기]


def sparkline(vals: list[float], n: int = 60) -> str:
    if len(vals) > n:
        step = len(vals) / n
        vals = [vals[int(i * step)] for i in range(n)]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return SPARK[0] * len(vals)
    return "".join(SPARK[min(7, int((v - lo) / (hi - lo) * 7.999))] for v in vals)


def col_of(date_str: str, dates: list[str], width: int) -> int:
    """스파크라인 내 해당 날짜의 대략 컬럼 위치."""
    if date_str not in dates:
        # 가장 가까운 이전 날짜
        prev = [d for d in dates if d <= date_str]
        if not prev:
            return 0
        date_str = prev[-1]
    idx = dates.index(date_str)
    return min(width - 1, int(idx / max(1, len(dates) - 1) * (width - 1)))


def detect(stock: dict) -> dict:
    code, name, market = stock["code"], stock["name"], stock["market"]
    sym = yahoo_symbol(code, market)
    ch = cyclecfg.yahoo(sym)
    sleep(80)
    base = {"code": code, "name": name, "market": market,
            "trough_date": stock["trough_date"], "peak_date": stock["peak_date"]}
    if not ch or not ch.get("closes"):
        return {**base, "error": "시세조회실패"}

    ts, cl, vol = ch["timestamps"], ch["closes"], ch["volumes"]
    dates = [iso(t) for t in ts]
    n = len(cl)
    t_idx = next((i for i, d in enumerate(dates) if d >= stock["trough_date"]), 0)
    p_idx = next((i for i, d in enumerate(dates) if d >= stock["peak_date"]), n - 1)

    peak_close = cl[p_idx]

    def fwd_max_drawdown(i: int) -> float:
        """i → 고점(p_idx) 경로의 진행최고치 대비 최대 하락폭(0~1)."""
        run_max = cl[i]
        mdd = 0.0
        for k in range(i, p_idx + 1):
            if cl[k] > run_max:
                run_max = cl[k]
            dd = (run_max - cl[k]) / run_max if run_max > 0 else 0.0
            if dd > mdd:
                mdd = dd
        return mdd

    def find_pivot(max_dd: float) -> tuple[int, str]:
        # 1차: 직전 25일 돌파 + 이후 max_dd 이내 지속 급등 + 본체(>=2배)
        for i in range(max(t_idx, BREAKOUT_WIN), p_idx + 1):
            if cl[i] <= max(cl[i - BREAKOUT_WIN:i]):
                continue
            if cl[i] <= 0 or peak_close / cl[i] < MIN_FWD_MULT:
                continue
            if fwd_max_drawdown(i) <= max_dd:
                return i, "P"
        # 폴백: 저점 이후 향후 60거래일 수익률 최대 구간 시작일
        best_ret, best_i = -1.0, t_idx
        for i in range(t_idx, p_idx + 1):
            j = min(n - 1, i + FALLBACK_FWD)
            if cl[i] > 0:
                r = cl[j] / cl[i]
                if r > best_ret:
                    best_ret, best_i = r, i
        return best_i, "F"

    variants = []
    for dd in (0.12, 0.20, 0.33):
        idx, m = find_pivot(dd)
        variants.append({
            "drawdown": dd,
            "pivot_date": dates[idx],
            "pivot_close": round(cl[idx], 1),
            "method": m,
            "prior_two_quarters": prior_two_quarters(dates[idx]),
            "_idx": idx,
        })

    # 검증용 스파크라인 (저점 30거래일 전 ~ 고점). a=12% b=20% c=33%
    s0 = max(0, t_idx - 30)
    s1 = min(n, p_idx + 1)
    seg_c = cl[s0:s1]
    seg_d = dates[s0:s1]
    width = min(60, len(seg_c))
    spark = sparkline(seg_c, width)
    marks = [" "] * len(spark)
    marks[col_of(stock["trough_date"], seg_d, len(spark))] = "L"
    marks[col_of(stock["peak_date"], seg_d, len(spark))] = "H"
    for tag, var in zip("abc", variants):
        marks[col_of(var["pivot_date"], seg_d, len(spark))] = tag

    for v in variants:
        v.pop("_idx", None)
    return {
        **base,
        "variants": variants,
        "spark": spark,
        "spark_marks": "".join(marks),
    }


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    winners = d["winners"]
    out = [detect(w) for w in winners]

    DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
                               "rule": __doc__, "pivots": out},
                              ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "pivot 되돌림 허용폭 3종 비교  (스파크라인 L=저점 H=고점 / a=12% b=20% c=33%)",
        "method: P=지속급등출발점(1차규칙) F=폴백(최대가속구간)",
        "",
    ]
    for i, r in enumerate(out, 1):
        if r.get("error"):
            lines.append(f"{i:2d}. {r['name']}({r['code']}) - {r['error']}")
            continue
        lines.append(
            f"{i:2d}. {r['name']} ({r['code']}/{r['market']})  "
            f"저점 {r['trough_date']} → 고점 {r['peak_date']}"
        )
        for tag, v in zip("abc", r["variants"]):
            lines.append(
                f"    {tag}) 허용 {int(v['drawdown'] * 100):>2}% → pivot {v['pivot_date']} "
                f"@ {int(v['pivot_close']):>10,} [{v['method']}]  "
                f"직전2개분기 {'/'.join(v['prior_two_quarters'])}"
            )
        lines.append(f"    {r['spark']}")
        lines.append(f"    {r['spark_marks']}")
        lines.append("")

    # 요약: 세 허용폭별 method 분포 / pivot 일자 동일 종목 수
    def mdist(k):
        return sum(1 for r in out if not r.get("error") and r["variants"][k]["method"] == "P")
    same_all = sum(
        1 for r in out if not r.get("error")
        and len({v["pivot_date"] for v in r["variants"]}) == 1
    )
    lines.append(
        f"[요약] 1차규칙(P) 적용 수 — 12%: {mdist(0)}  20%: {mdist(1)}  33%: {mdist(2)}  "
        f"(총 {sum(1 for r in out if not r.get('error'))}종목)"
    )
    lines.append(f"[요약] 세 허용폭에서 pivot 일자가 완전히 동일한 종목: {same_all}")
    TXT.write_text("\n".join(lines), encoding="utf-8")
    print("written", OUT)


if __name__ == "__main__":
    main()

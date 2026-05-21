"""트레일링 폭 정밀 캘리브레이션 (강세장) — 보유 원칙 폭 확정용.

이전엔 −20% vs −35% 2점만 비교 → 폭 미캘리브. 여기서 −20/25/30/35/40/50%
+ 추세형(50일선·120일선 이탈) 을 인과 단일진입(저점 후 첫 종가>20일선)·
종가 기준으로 NON/MID/WIN 3단계 비교.

생존자 주의: WIN(기지 위너)은 넓을수록 무조건 좋게 나옴 → 폭 선택 판단은
*MID(+50~200%, 현실적 보유 후보)*에서, NON은 '너무 넓히면 안 됨' 견제,
WIN은 상한(생존자, 절대수치 과대)으로만 해석.

지표: 평균·중앙 실현, 승률, 포착중앙(=실현÷진입~사이클 이상수익),
최악거래. 최적폭 = MID서 포착·평균이 더 안 늘고 최악이 터지기 시작 직전.

Yahoo 종가만(빠름). 사이클내 사후·인-샘플·상폐제외·비용 미반영·강세장
한정(약세장은 정반대 — v1-e). 환각 금지.
사용: python analyze_trail_calib.py [--n 80] [--seed 7]
"""
import argparse
import bisect
import json
import random
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.fetch import yahoo_symbol  # noqa: E402

CY = cyclecfg.DIR
DIS = 0.15
WIDTHS = [20, 25, 30, 35, 40, 50]


def nidx(d, ds):
    i = bisect.bisect_right(d, ds) - 1
    return i if i >= 0 else None


def ma(c, x, w):
    return sum(c[x - w + 1:x + 1]) / w if x >= w - 1 else None


def causal_entry(c, ti, n):
    for x in range(max(ti, 20), n - 5):
        m = ma(c, x, 20)
        if m and c[x] > m:
            return x
    return None


def run(c, e, n, pol):
    end = n - 1
    peak = c[e]
    for k in range(e + 1, end + 1):
        peak = max(peak, c[k])
        if c[k] <= c[e] * (1 - DIS):              # 재해 손절 −15%(공통)
            return c[k] / c[e] - 1
        if pol.startswith("T"):
            w = int(pol[1:]) / 100
            if c[k] <= peak * (1 - w):
                return c[k] / c[e] - 1
        elif pol == "MA50":
            m = ma(c, k, 50)
            if m and k - e >= 5 and c[k] < m:
                return c[k] / c[e] - 1
        elif pol == "MA120":
            m = ma(c, k, 120)
            if m and k - e >= 5 and c[k] < m:
                return c[k] / c[e] - 1
    return c[end] / c[e] - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    winners = wf["winners"]
    wc = {x["code"] for x in winners}
    rv = json.loads((CY / "winners.json").read_text(encoding="utf-8"))["ranked_valid"]

    def ok(r):
        return (not r.get("exclude_reason") and r.get("trough_date")
                and r.get("n_days", 0) >= 60 and r.get("raw_multiple"))
    rest = [r for r in rv if r["code"] not in wc and ok(r)]
    NON = [r for r in rest if r["raw_multiple"] < 1.5]
    MID = [r for r in rest if 1.5 <= r["raw_multiple"] < 3.0]
    random.seed(args.seed)
    tiers = {"NON 안오름": random.sample(NON, min(args.n, len(NON))),
             "MID 중간★판단": random.sample(MID, min(args.n, len(MID))),
             "WIN 위너(생존자상한)": random.sample(winners, min(args.n, len(winners)))}
    POLS = [f"T{w}" for w in WIDTHS] + ["MA50", "MA120"]

    out = [f"[c2024-12·강세장] 트레일링 폭 캘리브 — 단계별 {args.n}종목 "
           f"(seed {args.seed})",
           "인과 진입=저점 후 첫 종가>20일선·종가·단일매매·재해손절 −15% 공통.",
           "포착=실현÷(진입~사이클 이상수익). ★MID에서 최적폭 판독",
           "(WIN=생존자 상한·NON=과확장 견제). 강세장 한정(약세장 정반대).",
           ""]
    for tag, lst in tiers.items():
        ser = []
        for w in lst:
            ch = cyclecfg.yahoo(yahoo_symbol(w["code"], w["market"]))
            if not ch or not ch.get("closes"):
                continue
            ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
                  for t in ch["timestamps"]]
            c = ch["closes"]
            ti = nidx(ts, w["trough_date"]) or 0
            e = causal_entry(c, ti, len(c))
            if e is None:
                continue
            ser.append((c, e, len(c), max(c[e:]) / c[e] - 1))
        out.append(f"== {tag} (종목 {len(ser)}) ==")
        out.append("정책 | 평균실현% | 중앙% | 승률 | 포착중앙 | 최악%")
        for p in POLS:
            rr, caps = [], []
            for c, e, n, emax in ser:
                g = run(c, e, n, p)
                rr.append(g * 100)
                caps.append((g / emax) if emax > 1e-9 else (1.0 if g >= 0 else 0.0))
            m = len(rr)
            out.append(
                f"{p:6s} | {round(st.mean(rr),1)}% | {round(st.median(rr),1)}% | "
                f"{round(100*sum(1 for v in rr if v>0)/m)}% | "
                f"{round(st.median(caps),2)} | {round(min(rr),1)}%")
        out.append("")
    out += ["== 읽는 법(쉽게) ==",
            "★MID: 폭을 넓힐수록 평균·포착 오르다가 *더 안 오르고* 최악이",
            "급격히 커지기 시작하는 직전 폭이 최적. WIN은 넓을수록 좋게만",
            "나옴(생존자) → 폭 선택 근거로 쓰지 말 것. NON은 넓힐수록 나빠야",
            "정상(과확장 비용 확인). MA50/120은 폭 대신 추세형 대안 비교용.",
            "== 한계 ==",
            "강세장 한정·인-샘플·사후·상폐제외·표본무작위·비용 미반영·",
            "종가·단일 인과진입(검증 5신호 아님). 약세장은 정반대(v1-e)."]
    fn = f"_trail_calib_n{args.n}s{args.seed}.txt"
    (CY / fn).write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()

"""오닐 출구·손절 규칙의 한국(신흥시장) 유효성 검증.

오닐 규칙(사용자 정리):
  +20% 수익이면 (상승 지속이라도) 매도.
  단 1~3주(≤15거래일)만에 +20%면 = 강한 추세 → 최소 8주(40거래일) 보유
  후 재판단(6개월=126거래일 변형도 산출).
  매수가 −8% 하락 전 손절.

검증: 스윙저점 매수 → 각 출구정책별 *실현수익*·승률·손절률·상승포착률
(실현/이후최대상승=얼마나 챙겼나)을 NON/중간/위너 3단계로 비교.
한국 변형: 손절폭 8/12/15/20%, 트레일링(고점서 −20%), 50일선 이탈.

시세(Yahoo close)만 사용 → 빠름. 사이클내 사후·인-샘플·상폐제외.
환각 금지·결손 비임퓨트.

사용:  python analyze_exit_rules.py [--n 60] [--seed 7]
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
FAST = 15      # ≤15거래일 +20% = 빠른 강세(8주 예외)
W8, M6 = 40, 126


def nidx(d, ds):
    i = bisect.bisect_right(d, ds) - 1
    return i if i >= 0 else None


def ma(c, x, w):
    return sum(c[x - w + 1:x + 1]) / w if x >= w - 1 else None


def sim(c, e, end, stop, mode, hold=W8):
    """매수 e → 종료 인덱스 반환. mode: 'oneil'(+20%매도·8주예외) /
    'trail'(고점서 −20%) / 'ma50'(50일선 이탈). stop=재해 손절폭(진입가 대비)."""
    rmax = c[e]
    for k in range(e + 1, end + 1):
        if c[k] > rmax:
            rmax = c[k]
        # 재해 손절 (오닐 모드는 +20% 전까지만; 트레일/ma50은 상시 보호)
        if stop is not None and c[k] <= c[e] * (1 - stop):
            if mode == "oneil":
                return k
            if mode in ("trail", "ma50"):
                return k
        if mode == "oneil":
            if c[k] >= c[e] * 1.20:
                d20 = k - e
                if d20 > FAST:
                    return k                       # 즉시 +20% 매도
                return min(end, e + hold)          # 빠름 → 8주(또는 6개월) 보유
        elif mode == "trail":
            if c[k] <= rmax * 0.80:                # 고점서 −20%
                return k
        elif mode == "ma50":
            m = ma(c, k, 50)
            if m and c[k] < m and k - e >= 5:      # 50일선 이탈(진입 5일 후부터)
                return k
    return end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    winners = wf["winners"]
    win_codes = {x["code"] for x in winners}
    rv = json.loads((CY / "winners.json").read_text(encoding="utf-8"))["ranked_valid"]

    def ok(r):
        return (not r.get("exclude_reason") and r.get("trough_date")
                and r.get("n_days", 0) >= 60 and r.get("raw_multiple"))
    rest = [r for r in rv if r["code"] not in win_codes and ok(r)]
    NON = [r for r in rest if r["raw_multiple"] < 1.5]
    MID = [r for r in rest if 1.5 <= r["raw_multiple"] < 3.0]
    random.seed(args.seed)
    tiers = {
        "NON 안오름": random.sample(NON, min(args.n, len(NON))),
        "MID 중간": random.sample(MID, min(args.n, len(MID))),
        "WIN 위너": random.sample(winners, min(args.n, len(winners))),
    }

    # 정책: (이름, mode, stop)
    POL = [
        ("오닐strict(손절8%·+20%·8주예외)", "oneil", 0.08),
        ("한국:손절12%", "oneil", 0.12),
        ("한국:손절15%", "oneil", 0.15),
        ("한국:손절20%", "oneil", 0.20),
        ("트레일링(고점-20%·재해손절15%)", "trail", 0.15),
        ("50일선이탈(재해손절15%)", "ma50", 0.15),
    ]

    out = [f"[c2024-12] 오닐 출구·손절 규칙 한국 유효성 — 단계별 {args.n}종목 "
           f"(seed {args.seed})",
           "매수=사이클저점 이후 스윙저점(±5). 실현=매수→출구 수익률. "
           "포착=실현÷이후최대상승(1.0=다 챙김, 낮으면 일찍 팜).",
           "오닐 8주예외: ≤15거래일 +20%면 40거래일 보유 후 매도.",
           ""]
    six = {}
    for tag, lst in tiers.items():
        # 종목별 시세 1회 로드
        series = []
        for w in lst:
            ch = cyclecfg.yahoo(yahoo_symbol(w["code"], w["market"]))
            if not ch or not ch.get("closes"):
                continue
            ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
                  for t in ch["timestamps"]]
            c = ch["closes"]
            ti = nidx(ts, w["trough_date"]) or 0
            series.append((c, ti))
        # 스윙저점 목록
        entries = []
        for c, ti in series:
            n = len(c)
            x = max(ti, 30)
            while x < n - 6:
                if c[x] > 0 and c[x] == min(c[max(0, x - 5):min(n, x + 6)]):
                    entries.append((c, x, n - 1))
                    x += 6
                else:
                    x += 1
        out.append(f"== {tag} (종목 {len(series)} · 매수지점 {len(entries)}) ==")
        out.append("정책 | 평균실현% | 중앙% | 승률 | 손절률 | 포착중앙")
        for name, mode, stp in POL:
            rets, caps, stopped = [], [], 0
            for c, e, end in entries:
                xi = sim(c, e, end, stp, mode)
                r = c[xi] / c[e] - 1
                rets.append(r * 100)
                emax = max(c[e:end + 1]) / c[e] - 1
                caps.append((r / emax) if emax > 1e-9 else (1.0 if r >= 0 else 0.0))
                if stp is not None and c[xi] <= c[e] * (1 - stp) + 1e-9 and r < 0:
                    stopped += 1
            n_ = len(rets)
            out.append(
                f"{name} | {round(st.mean(rets),1)}% | "
                f"{round(st.median(rets),1)}% | "
                f"{round(100*sum(1 for x in rets if x>0)/n_)}% | "
                f"{round(100*stopped/n_)}% | "
                f"{round(st.median(caps),2)}")
            if name.startswith("오닐strict"):
                # 6개월 변형 (빠른+20% → 126거래일 보유)
                r6 = []
                for c, e, end in entries:
                    xi = sim(c, e, end, 0.08, "oneil", hold=M6)
                    r6.append((c[xi] / c[e] - 1) * 100)
                six[tag] = (round(st.mean(r6), 1), round(st.median(r6), 1))
        out.append(f"  └ 오닐 6개월변형(빠른+20%→126일 보유): 평균 "
                   f"{six[tag][0]}% · 중앙 {six[tag][1]}%")
        out.append("")
    out += ["== 해석 ==",
            "한국 위너는 수백~수천% 상승 → '+20% 즉시매도'면 포착중앙이",
            "매우 낮음(다 놓침). 8주/6개월 예외·트레일·50일선이 포착을",
            "얼마나 살리나, 손절폭 넓힐수록 승률·실현이 어떻게 변하나 비교.",
            "== 한계 ==",
            "사이클내 사후·인-샘플·상폐제외·표본 무작위·거래비용 미반영.",
            "매수=스윙저점(특정 신호 아님)·시세 close only."]
    fn = f"_exit_rules_n{args.n}s{args.seed}.txt"
    (CY / fn).write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()

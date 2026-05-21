"""매도신호(①)·보유신호(②)·'-8%후 재매수'(사용자안) 통합 검증.

동일 출발점 '캠페인': 각 종목 사이클저점 후 *첫 스윙저점*에서 시작해
사이클 종료까지 정책대로 운용 → 종목당 순(누적)수익으로 정책 head-to-head.

정책:
  ONEIL      1매매: 손절−8% · +20%매도(≤15거래일 빠른상승→40거래일 보유)
  WIDE       1매매: 재해손절−15% · 트레일링(산뒤 최고점 대비 −20%)
  REBUY      손절−8% 후 *다음 스윙저점* 재매수 반복(레그별 +20%/8주), 누적
  REBUY_DISC REBUY인데 재매수는 '종가>상승 50일선'일 때만(규율 재진입)
  SELL_STRUCT 1매매: 재해−15% · 매도신호=종가<직전20일 최저(구조 이탈) [①]
  HOLD_OVL   WIDE인데 보유신호(종가>상승50일선 & 최근20일 신고가)면
             트레일링 매도 보류(좋은 신호면 안 팔기) [②]

지표(NON/MID/WIN): 종목당 순수익 평균·중앙, 승률(순>0), 최악 단일거래,
평균 거래수(마찰), 포착중앙(순÷첫진입~사이클 이상수익).

시세(Yahoo close)만. 사이클내 사후·인-샘플·상폐제외·거래비용 미반영.
환각 금지·결손 비임퓨트.  사용: python analyze_exit_signals.py [--n 60] [--seed 7]
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
FAST, W8 = 15, 40


def nidx(d, ds):
    i = bisect.bisect_right(d, ds) - 1
    return i if i >= 0 else None


def ma(c, x, w):
    return sum(c[x - w + 1:x + 1]) / w if x >= w - 1 else None


def swing_lows(c, start, n):
    out = []
    x = max(start, 30)
    while x < n - 6:
        if c[x] > 0 and c[x] == min(c[max(0, x - 5):min(n, x + 6)]):
            out.append(x)
            x += 6
        else:
            x += 1
    return out


def leg(c, e, end, stop, mode):
    """1매매 종료 인덱스. mode: oneil / trail / struct / holdovl."""
    rmax = c[e]
    for k in range(e + 1, end + 1):
        if c[k] > rmax:
            rmax = c[k]
        if stop is not None and c[k] <= c[e] * (1 - stop):
            return k                                  # 재해/손절
        if mode == "oneil":
            if c[k] >= c[e] * 1.20:
                return k if (k - e) > FAST else min(end, e + W8)
        elif mode == "trail":
            if c[k] <= rmax * 0.80:
                return k
        elif mode == "struct":
            if k - e >= 20 and c[k] < min(c[k - 20:k]):
                return k
        elif mode == "holdovl":
            if c[k] <= rmax * 0.80:
                m = ma(c, k, 50)
                mp = ma(c, k - 10, 50)
                hh = c[k] >= max(c[max(e, k - 20):k]) if k > e else False
                hold = (m and mp and c[k] > m and m > mp and hh)
                if not hold:
                    return k
    return end


def campaign(c, ti, n, policy):
    """종목 캠페인 → (순수익, 거래수, 최악단일, 첫진입idx)."""
    sl = swing_lows(c, ti, n)
    if not sl:
        return None
    e0 = sl[0]
    rets = []
    if policy in ("REBUY", "REBUY_DISC"):
        pos = e0
        idx = 0
        while pos is not None and pos < n - 6:
            x = leg(c, pos, n - 1, 0.08, "oneil")
            rets.append(c[x] / c[pos] - 1)
            nxt = [s for s in sl if s > x]
            pos = None
            for s in nxt:
                if policy == "REBUY":
                    pos = s
                    break
                m, mp = ma(c, s, 50), ma(c, s - 10, 50)
                if m and mp and c[s] > m and m > mp:     # 규율: 상승 50일선 위
                    pos = s
                    break
            idx += 1
            if idx > 30:
                break
        net = 1.0
        for r in rets:
            net *= (1 + r)
        net -= 1
    else:
        mode = {"ONEIL": "oneil", "WIDE": "trail",
                "SELL_STRUCT": "struct", "HOLD_OVL": "holdovl"}[policy]
        stp = 0.08 if policy == "ONEIL" else 0.15
        x = leg(c, e0, n - 1, stp, mode)
        rets = [c[x] / c[e0] - 1]
        net = rets[0]
    ideal = max(c[e0:]) / c[e0] - 1
    cap = (net / ideal) if ideal > 1e-9 else (1.0 if net >= 0 else 0.0)
    return net * 100, len(rets), min(rets) * 100, round(cap, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
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
             "MID 중간": random.sample(MID, min(args.n, len(MID))),
             "WIN 위너": random.sample(winners, min(args.n, len(winners)))}
    POLS = ["ONEIL", "WIDE", "REBUY", "REBUY_DISC", "SELL_STRUCT", "HOLD_OVL"]

    out = [f"[c2024-12] 매도·보유·재매수 통합 — 단계별 {args.n}종목 (seed {args.seed})",
           "동일 출발점(첫 스윙저점)→사이클끝 캠페인. 순=종목당 누적수익.",
           "포착=순÷(첫진입~사이클 이상수익). REBUY=−8%후 다음스윙저점 재매수.",
           "HOLD_OVL=좋은신호(상승50일선·신고가)면 트레일링 매도 보류.",
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
            ser.append((c, nidx(ts, w["trough_date"]) or 0, len(c)))
        out.append(f"== {tag} (종목 {len(ser)}) ==")
        out.append("정책 | 평균순% | 중앙순% | 승률 | 최악거래% | 평균거래 | 포착중앙")
        for p in POLS:
            R = [campaign(c, ti, n, p) for c, ti, n in ser]
            R = [x for x in R if x]
            if not R:
                continue
            nets = [x[0] for x in R]
            out.append(
                f"{p:11s} | {round(st.mean(nets),1)}% | "
                f"{round(st.median(nets),1)}% | "
                f"{round(100*sum(1 for v in nets if v>0)/len(nets))}% | "
                f"{round(st.median([x[2] for x in R]),1)}% | "
                f"{round(st.mean([x[1] for x in R]),1)} | "
                f"{round(st.median([x[3] for x in R]),2)}")
        out.append("")
    out += ["== 해석(쉽게) ==",
            "ONEIL=오닐그대로. WIDE=한국형(넓은손절+트레일링).",
            "REBUY=사용자안(−8% 팔고 다음 저점 재매수). REBUY_DISC=재매수를",
            "추세확인된 저점만(규율). SELL_STRUCT=매도신호 비교용(구조이탈).",
            "HOLD_OVL=보유신호 켜지면 안 팔기. 평균/중앙순수익·포착 높고",
            "최악거래 견딜만하면 우수. REBUY가 WIDE보다 못하면 '−8%후",
            "재매수'는 마찰만 큰 것(저점 재진입이 안정적이지 않다는 뜻).",
            "== 한계 ==",
            "사이클내 사후·인-샘플·상폐제외·표본무작위·거래비용/세금 미반영·",
            "매수=일반 스윙저점(검증된 5신호 아님)·close only. 방향만 참고."]
    fn = f"_exit_signals_n{args.n}s{args.seed}.txt"
    (CY / fn).write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()

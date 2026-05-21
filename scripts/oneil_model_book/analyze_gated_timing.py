"""선별게이트 적용 타이밍 — "한국식 CAN SLIM 통과 종목 중 최적 매수 타이밍".

사용자 전략 확정: 타이밍 단독(lift≈0.86x, 상승추세 아닐 때도 진입→지지부진)
지양. **선별게이트(L RS≥80 + M 상승추세)를 *먼저* 통과한 날에 한해** 타이밍
진입했을 때, 비위너 대조 정밀도·lift 가 실제로 뛰는지(생존자 편향 없이)와
게이트 통과 후 최적 타이밍 시그니처를 측정.

데이터: cycles/c2024-12/_universe_prices_5y.json(close-only, 전 종목) +
장기 지수(M). I(외인/기관)는 frgn 전종목 과중→여기선 제외(L 8x·M 1.55x 가
주동력, I는 1.4x 보조; buy_timing §8). point-in-time: L 백분위·M 국면 모두
'그날' 기준. 한계: 사이클 내 사후측정·상폐 제외·인-샘플(타이밍단독 검증과
동일 잣대 → 비교 공정).

사용:  python analyze_gated_timing.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from canslim_lib.fetch import fetch_yahoo_chart  # noqa: E402

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles" / "c2024-12"
ANCHOR = "2024-12-09"
MIN_FWD = 20
THR = [50, 100, 200]


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def sma(c, j, w):
    return sum(c[j - w + 1:j + 1]) / w if j >= w - 1 else None


def confirmed(c, d):
    if d < 60:
        return False
    m, mp = sma(c, d, 50), sma(c, d - 10, 50)
    return (m and mp and c[d] > m and m > mp and c[d] > c[d - 20])


def idx_uptrend_by_date(sym):
    ch = fetch_yahoo_chart(sym, period1=_ep("2017-01-01"),
                           period2=_ep("2026-12-31"), interval="1d")
    ts, c = (ch or {}).get("timestamps"), (ch or {}).get("closes")
    out = {}
    if not ts:
        return out
    ds = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") for t in ts]
    for i in range(200, len(c)):
        out[ds[i]] = (c[i] > sma(c, i, 50) > sma(c, i, 200) and c[i] > sma(c, i, 200))
    return out


def main():
    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    win = {x["code"] for x in wf["winners"]}
    w = json.loads((CY / "winners.json").read_text(encoding="utf-8"))
    nmkt = {r["code"]: r["market"] for r in w["ranked_valid"]}

    ks = idx_uptrend_by_date("%5EKS11")
    kq = idx_uptrend_by_date("%5EKQ11")

    # L: 주봉 그리드로 전 종목 252d수익률 80분위 임계 사전계산
    any_d = U[list(U)[0]]["d"]
    grid = list(range(252, len(any_d), 5))
    thr80 = {}
    for gi in grid:
        gd = any_d[gi]
        rr = []
        for s in U.values():
            d, c = s.get("d"), s.get("c")
            if not d or not c:
                continue
            j = gi if (gi < len(d) and d[gi] == gd) else \
                max((k for k in range(len(d)) if d[k] <= gd), default=None)
            if j is None or j < 252 or c[j - 252] <= 0:
                continue
            rr.append(c[j] / c[j - 252] - 1)
        rr.sort()
        thr80[gd] = rr[int(0.8 * (len(rr) - 1))] if rr else None

    gdates = sorted(thr80)

    def thr_at(date_str):
        cand = [x for x in gdates if x <= date_str]
        return thr80[cand[-1]] if cand else None

    valid = 0
    gated = []          # 게이트통과+추세확인 진입 종목 (code, fwd%, sig...)
    tonly = []          # 비교용: 타이밍단독(게이트 무시) 진입 fwd%
    base_movers = {t: 0 for t in THR}

    for code, s in U.items():
        d, c = s.get("d"), s.get("c")
        if not d or not c or len(c) < 300:
            continue
        ai = next((k for k in range(len(d)) if d[k] >= ANCHOR), None)
        if ai is None or len(c) - ai < 80:
            continue
        valid += 1
        ti = min(range(ai, len(c)), key=lambda k: c[k])
        if c[ti] > 0:
            bm = max(c[ti:]) / c[ti] - 1
            for t in THR:
                if bm * 100 >= t:
                    base_movers[t] += 1
        mkt = nmkt.get(code, "KOSDAQ")
        reg = ks if mkt == "KOSPI" else kq

        g_to = None     # 타이밍단독 최초
        g_gt = None     # 선별게이트 통과 후 최초
        for x in range(max(ti, 252), len(c) - MIN_FWD):
            if not confirmed(c, x):
                continue
            if g_to is None:
                g_to = x
            th = thr_at(d[x])
            r252 = c[x] / c[x - 252] - 1 if c[x - 252] > 0 else None
            L_ok = (th is not None and r252 is not None and r252 >= th)
            M_ok = reg.get(d[x], False)
            if L_ok and M_ok:
                g_gt = x
                break
        if g_to is not None:
            tonly.append((max(c[g_to:]) / c[g_to] - 1) * 100)
        if g_gt is not None:
            fwd = (max(c[g_gt:]) / c[g_gt] - 1) * 100
            hi = max(c[max(0, g_gt - 252):g_gt + 1])
            gated.append({
                "code": code, "fwd": fwd,
                "from_trough_days": g_gt - ti,
                "from_trough_pct": round((c[g_gt] / c[ti] - 1) * 100, 1),
                "pct_52w_high": round(c[g_gt] / hi * 100, 1) if hi else None,
                "is_winner": code in win})

    def pctge(xs, t):
        return 100 * sum(1 for x in xs if x >= t) / len(xs) if xs else 0

    def med(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if xs else None

    ng, fwdg = len(gated), [r["fwd"] for r in gated]
    L = [f"[c2024-12] 선별게이트(L RS≥80 + M 상승추세) 적용 타이밍 검증",
         f"전 종목 {valid} | 게이트+추세확인 진입 {ng}개 "
         f"(발동률 {round(100*ng/valid,1)}%) vs 타이밍단독 {len(tonly)}개 "
         f"({round(100*len(tonly)/valid,1)}%)",
         "정의: 사이클저점 이후, L(252d수익률 전종목 80분위↑)·M(지수 50>200·"
         "상승) 동시 충족된 *첫 추세확인일* 진입. 결과=사이클내 이후최대상승.",
         "",
         "== 정밀도(진입 종목이 큰 상승) : 게이트 vs 타이밍단독 vs 기저율 ==",
         "컷오프 | 게이트정밀 | 타이밍단독 | 기저율 | 게이트 lift",
         ]
    for t in THR:
        pg = pctge(fwdg, t)
        pt = pctge(tonly, t)
        bs = 100 * base_movers[t] / valid if valid else 0
        L.append(f"≥+{t}% | {round(pg,1)}% | {round(pt,1)}% | {round(bs,1)}% | "
                 f"{round(pg/bs,2) if bs else '-'}x")

    wn = sum(1 for r in gated if r["is_winner"])
    L += ["",
          "== 위너리스트(상위200) 대조 ==",
          f"게이트 발동 중 위너: {wn}/{ng} "
          f"({round(100*wn/ng,1) if ng else 0}%)  vs 타이밍단독 위너비중 10.2%",
          f"위너 recall: {wn}/{len(win)} ({round(100*wn/len(win),1)}%)",
          "",
          "== 게이트 통과 후 '최적 타이밍' 시그니처(중앙) ==",
          f"바닥→게이트진입 거래일 : {med([r['from_trough_days'] for r in gated])}",
          f"바닥 대비 진입가 % : {med([r['from_trough_pct'] for r in gated])}",
          f"52주고가 대비 % : {med([r['pct_52w_high'] for r in gated if r['pct_52w_high']])}",
          f"진입 후 이후최대상승 중앙 % : {round(med(fwdg) or 0,1)}",
          "",
          "== 정직한 한계 ==",
          "사이클내 사후측정·상폐제외·인-샘플(타이밍단독 검증과 동일 잣대).",
          "I(외인/기관)는 전종목 frgn 과중→미포함(L·M이 주동력, I는 보조).",
          "게이트는 '늦지만 신뢰' — 대형 경기민감주 바닥은 설계상 후행 진입.",
          ]
    block = "\n".join(L)
    (CY / "_gated_timing.txt").write_text(block, encoding="utf-8")
    print(f"gated-timing saved: {CY/'_gated_timing.txt'} "
          f"(valid {valid}, gated {ng}, winners {wn})", file=sys.stderr)


if __name__ == "__main__":
    main()

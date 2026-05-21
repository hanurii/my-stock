"""약세장(2022) vs 강세장(2025) 역검증 — 우리 신호가 강세장 전용인가?

사용자 질문: 5신호·출구 규칙이 한국 약세 구간에서도 통하나, 강세장에서만
통하나? 동일 무작위 종목 집합을 *같은 규칙*으로 두 국면에 적용해 직접 비교.
  BEAR  2022-01-01~2022-12-31 (KOSPI −24.9%, 러-우전쟁+연준급인상+물가)
  BULL  2025-01-01~2025-12-31 (현재 강세장 내)

신호(가격형 4 + RS): 거래량≤50일평균 & 종가≤52주고가88% & 50일선±10%
& RS백분위≥50.  I(외인/기관)는 네이버 frgn 깊이가 2022 미도달 → 본
역검증선 *결손(추정 안 함)·제외*, 가격/거래량/RS 4축만 비교(5축 중 4축).
클린 빠른 +20% = 도중 −10% 안 빠지고 60거래일내(창 넘어가도 인정).
출구: 인과진입(창 내 첫 종가>20일선) → WIDE(재해−15%+트레일−35%)·
ONEIL(−8%·+20%/8주) 실현수익.

Yahoo(period1 2020~, 거래량 포함)·RS캐시(`_rs_sortmap.json`,
~2022중반↑ 가용; 이전 RS 결손). 사이클 무관 절대구간·인-샘플·상폐제외·
비용 미반영. 환각 금지·결손 비임퓨트.
사용: python analyze_bear_backtest.py [--n 120] [--seed 7]
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
from canslim_lib.fetch import yahoo_symbol, fetch_yahoo_chart  # noqa: E402

CY = (Path(__file__).resolve().parents[2] / "research" / "oneil-model-book"
      / "cycles" / "c2024-12")
WIN = {"BEAR(2022)": ("2022-01-01", "2022-12-31"),
       "BULL(2025)": ("2025-01-01", "2025-12-31")}
GAIN, MAXH, DROP = 0.20, 60, 0.10


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def ma(c, x, w):
    return sum(c[x - w + 1:x + 1]) / w if x >= w - 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rv = json.loads((CY / "winners.json").read_text(encoding="utf-8"))["ranked_valid"]
    pool = [r for r in rv if not r.get("exclude_reason")]
    random.seed(args.seed)
    smp = random.sample(pool, min(args.n, len(pool)))

    sm = json.loads((CY / "_rs_sortmap.json").read_text(encoding="utf-8"))
    gdates = sorted(sm)

    def rs_pct(ret, ds):
        i = bisect.bisect_right(gdates, ds) - 1
        if i < 0:
            return None
        a = sm[gdates[i]]
        return 100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1) if a else None

    # 종목 시세 1회 로드(2020~ 전체 → 2022·2025 모두 포함)
    series = []
    for w in smp:
        ch = fetch_yahoo_chart(yahoo_symbol(w["code"], w["market"]),
                               period1=_ep("2020-01-01"),
                               period2=_ep("2026-12-31"), interval="1d")
        if not ch or not ch.get("closes"):
            continue
        ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
              for t in ch["timestamps"]]
        series.append((ts, ch["closes"], ch["volumes"]))

    def sig_test(ts, c, v, w0, w1):
        """창 내 스윙저점에 가격형 4축 신호 → 클린+20% 정밀도."""
        n = len(c)
        i0 = bisect.bisect_left(ts, w0)
        i1 = bisect.bisect_right(ts, w1) - 1
        npts = nhit = f4 = h4 = fR = hR = 0
        x = max(i0, 252, 55)
        while x <= min(i1, n - 6):
            if c[x] <= 0 or c[x] != min(c[max(0, x - 5):min(n, x + 6)]):
                x += 1
                continue
            npts += 1
            tgt, hit = c[x] * (1 + GAIN), False
            for k in range(x + 1, min(n, x + MAXH + 1)):
                if c[k] <= c[x] * (1 - DROP):
                    break
                if c[k] >= tgt:
                    hit = True
                    break
            nhit += hit
            v50 = sum(v[x - 50:x]) / 50 if x >= 50 and sum(v[x - 50:x]) else None
            hi52 = max(c[max(0, x - 252):x + 1])
            m50 = ma(c, x, 50)
            p4 = (v50 and v[x] / v50 <= 1.0 and hi52 and c[x] <= 0.88 * hi52
                  and m50 and abs(c[x] / m50 - 1) <= 0.10)
            if p4:
                f4 += 1
                h4 += hit
                rp = rs_pct(c[x] / c[x - 252] - 1, ts[x]) if c[x - 252] > 0 else None
                if rp is not None and rp >= 50:
                    fR += 1
                    hR += hit
            x += 1
        return npts, nhit, f4, h4, fR, hR

    def exit_test(ts, c, w0, w1, mode):
        n = len(c)
        i0 = bisect.bisect_left(ts, w0)
        i1 = bisect.bisect_right(ts, w1) - 1
        e = None
        for x in range(max(i0, 20), min(i1, n - 5)):
            m = ma(c, x, 20)
            if m and c[x] > m:
                e = x
                break
        if e is None:
            return None
        end = min(n - 1, e + 250)
        peak = c[e]
        for k in range(e + 1, end + 1):
            peak = max(peak, c[k])
            g = c[k] / c[e] - 1
            if mode == "ONEIL":
                if c[k] <= c[e] * 0.92:
                    return g
                if g >= 0.20:
                    return g if (k - e) > 15 else c[min(end, e + 40)] / c[e] - 1
            else:  # WIDE: 재해 −15% + 트레일 −35%
                if c[k] <= c[e] * 0.85:
                    return g
                if c[k] <= peak * 0.65:
                    return g
        return c[end] / c[e] - 1

    out = [f"[역검증] 약세장(2022) vs 강세장(2025) — 무작위 {len(series)}종목 "
           f"(seed {args.seed})",
           "동일 종목·동일 규칙을 두 국면에 적용. 신호=가격형4(거래량마름·",
           "신고가아님·50일선근처·RS≥50). I(외인기관)는 frgn 2022 미도달→",
           "결손·제외(4/5축). 클린+20%=−10%전 60거래일내.",
           ""]
    for tag, (w0, w1) in WIN.items():
        NP = NH = F4 = H4 = FR = HR = 0
        for ts, c, v in series:
            a, b, d, e, f, g = sig_test(ts, c, v, w0, w1)
            NP += a; NH += b; F4 += d; H4 += e; FR += f; HR += g
        base = 100 * NH / NP if NP else 0
        p4 = 100 * H4 / F4 if F4 else 0
        pR = 100 * HR / FR if FR else 0
        out.append(f"== {tag} ==")
        out.append(f"  스윙저점 {NP} | 기저 클린+20% {round(base,1)}%")
        out.append(f"  가격4축    발동 {F4}({round(100*F4/NP,1) if NP else 0}%) "
                   f"→ 정밀도 {round(p4,1)}% | lift {round(p4/base,2) if base else '-'}x")
        out.append(f"  +RS≥50     발동 {FR}({round(100*FR/NP,1) if NP else 0}%) "
                   f"→ 정밀도 {round(pR,1)}% | lift {round(pR/base,2) if base else '-'}x")
        for mode in ("ONEIL", "WIDE"):
            rr = [exit_test(ts, c, w0, w1, mode) for ts, c, _ in series]
            rr = [x * 100 for x in rr if x is not None]
            if rr:
                out.append(
                    f"  출구 {mode:5s}: 평균 {round(st.mean(rr),1)}% · 중앙 "
                    f"{round(st.median(rr),1)}% · 승률 "
                    f"{round(100*sum(1 for z in rr if z>0)/len(rr))}% · 최악 "
                    f"{round(min(rr),1)}% (n{len(rr)})")
        out.append("")
    out += ["== 해석(쉽게) ==",
            "강세장 대비 약세장에서 기저율·정밀도·lift·출구 실현이 얼마나",
            "무너지나. lift가 약세장서 1 미만/출구 평균 음수면 '강세장 전용'",
            "→ M(시장국면) master switch 필수 입증. lift>1 유지면 신호 자체는",
            "약세장서도 변별(단 절대 성과는 약화).",
            "== 한계 ==",
            "절대 달력구간·인-샘플·상폐제외·표본무작위·비용 미반영·I축 결손",
            "(frgn 2022 미도달)·종가·단일 인과진입. 방향 비교 목적."]
    fn = f"_bear_backtest_n{len(series)}s{args.seed}.txt"
    (CY / fn).write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()

"""신호 종목에 한국형 시스템 출구 규칙 적용 — 신호 vs 관리 가치 분리.

특정 진입일 매수했다고 보고, 세 가지로 비교:
  NAIVE   현재까지 그냥 보유 (출구 규칙 없음)
  SYSTEM  ③−15% 재해(진입대비) + ④−35% 트레일(진입후 고점대비)
          + ★약세스위치(코스피 종가<200거래일선 & 200일선 하락→전량 청산)
  ONEIL   −8% 손절 / +20% 즉시매도 (≤15거래일 빠른+20%면 40거래일 보유)
첫 발동에서 청산, 없으면 현재가(보유중) 표기. 종가만·전향·매매지시 아님.

사용: python apply_system_exit.py --asof 2026-02-26 --codes 222800,108490,...
"""
import argparse
import bisect
import json
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from canslim_lib.fetch import fetch_yahoo_chart, yahoo_symbol  # noqa: E402

CY = (Path(__file__).resolve().parents[2] / "research" / "oneil-model-book"
      / "cycles" / "c2024-12")


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def sma(c, i, w):
    return sum(c[i - w + 1:i + 1]) / w if i >= w - 1 else None


def nidx(d, ds):
    i = bisect.bisect_right(d, ds) - 1
    return i if i >= 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", required=True)
    ap.add_argument("--codes", required=True)   # 쉼표구분 6자리
    a = ap.parse_args()
    codes = [c.strip() for c in a.codes.split(",") if c.strip()]

    w = json.loads((CY / "winners.json").read_text(encoding="utf-8"))
    nmap = {r["code"]: (r["name"], r["market"]) for r in w["ranked_valid"]}

    ks = fetch_yahoo_chart("%5EKS11", period1=_ep("2024-01-01"),
                           period2=_ep("2027-01-01"), interval="1d")
    kd = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
          for t in ks["timestamps"]]
    kc = ks["closes"]

    def kbear(ds):
        j = nidx(kd, ds)
        if j is None or j < 220:
            return False
        m, mp = sma(kc, j, 200), sma(kc, j - 20, 200)
        return bool(m and mp and kc[j] < m and m < mp)

    rows = []
    for code in codes:
        name, mkt = nmap.get(code, (code, "KOSPI"))
        ch = fetch_yahoo_chart(yahoo_symbol(code, mkt),
                               period1=_ep("2024-06-01"),
                               period2=_ep("2027-01-01"), interval="1d")
        if not ch or not ch.get("closes"):
            continue
        ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
              for t in ch["timestamps"]]
        c = ch["closes"]
        ei = nidx(ts, a.asof)
        if ei is None:
            continue
        e = c[ei]
        last = c[-1]
        naive = last / e - 1

        # SYSTEM
        peak = e
        s_ret, s_why, s_dt = None, "보유중(미발동)", ts[-1]
        for k in range(ei + 1, len(c)):
            peak = max(peak, c[k])
            if c[k] <= e * 0.85:
                s_ret, s_why, s_dt = c[k]/e-1, "③−15%재해", ts[k]
                break
            if c[k] <= peak * 0.65:
                s_ret, s_why, s_dt = c[k]/e-1, "④−35%트레일", ts[k]
                break
            if kbear(ts[k]):
                s_ret, s_why, s_dt = c[k]/e-1, "★약세스위치", ts[k]
                break
        if s_ret is None:
            s_ret = naive

        # ONEIL
        o_ret, o_why, o_dt = None, "보유중", ts[-1]
        for k in range(ei + 1, len(c)):
            g = c[k]/e-1
            if c[k] <= e * 0.92:
                o_ret, o_why, o_dt = g, "−8%손절", ts[k]
                break
            if g >= 0.20:
                if (k - ei) > 15:
                    o_ret, o_why, o_dt = g, "+20%매도", ts[k]
                else:
                    j = min(len(c)-1, ei+40)
                    o_ret, o_why, o_dt = c[j]/e-1, "8주룰매도", ts[j]
                break
        if o_ret is None:
            o_ret = naive

        peakret = max(c[ei:]) / e - 1
        rows.append({
            "code": code, "name": name, "e": e, "naive": naive*100,
            "peak": peakret*100, "sys": s_ret*100, "swhy": s_why,
            "sdt": s_dt, "one": o_ret*100, "owhy": o_why})

    L = [f"[시스템 출구 적용] as-of {a.asof} 5신호 종목 — 신호 vs 관리",
         "NAIVE=그냥 보유 / SYSTEM=③−15%+④−35%트레일+★약세스위치 / "
         "ONEIL=−8%·+20%. 종가·전향·매매지시 아님.",
         "",
         "종목 | 진입가 | 기간최대% | NAIVE% | SYSTEM%(사유/일자) | ONEIL%(사유)",
         "-" * 30]
    for r in rows:
        L.append(
            f"{r['name']}({r['code']}) | {r['e']:,.0f} | "
            f"+{r['peak']:.0f}% | {r['naive']:+.1f}% | "
            f"{r['sys']:+.1f}% [{r['swhy']} {r['sdt']}] | "
            f"{r['one']:+.1f}% [{r['owhy']}]")
    if rows:
        def m(k):
            v = sorted(x[k] for x in rows)
            return v[len(v)//2], sum(v)/len(v)
        nm_, na_ = m("naive")
        sm_, sa_ = m("sys")
        om_, oa_ = m("one")
        L += ["",
              f"중앙/평균 — NAIVE {nm_:+.1f}/{na_:+.1f}% · "
              f"SYSTEM {sm_:+.1f}/{sa_:+.1f}% · ONEIL {om_:+.1f}/{oa_:+.1f}%",
              "해석: SYSTEM이 NAIVE보다 (특히 토해낸 종목서) 손실 방어·",
              "이익 보존하면 '관리의 가치' 입증. ONEIL이 가장 낮으면 +20%",
              "조기매도(사용자 습관)가 한국서 독이라는 기존 결론 재확인."]
    L += ["", "한계: 표본 5·짧은 창·생존자·종가·일별리밸런스(실제 주1회)·",
          "거래비용 무관·완전 OOS 아님. 방향 참고용, 수익 보장 아님."]
    out = (Path(__file__).resolve().parents[2] / "research"
           / "oneil-model-book" / f"_sysexit_{a.asof}.txt")
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out} ({len(rows)} stocks)", file=sys.stderr)


if __name__ == "__main__":
    main()

"""매도 후 재진입 검증 — 시스템은 별도 재진입 규칙 없음(매수규칙=재진입규칙).

쇼크/원칙 매도 후, ★코스피 강세(OFF) 상태에서 그 종목이 5신호를
*다시* 충족하는 첫 종가일 = 재진입. 비교:
  NAIVE        2/26 매수 후 안 팔고 현재까지 보유
  SELL_CASH    2/26 매수 → 매도일 청산 후 현금(재진입 안 함)
  SELL_REENTER 매도 후 5신호 재발동일 재진입 → 현재 (leg 복리)

5신호=거래량≤50일평균 & 종가≤52주고가88% & |종가/50일선−1|≤10%
& RS백분위≥50 & 외인or기관 60일 순매수>0. 종가·전향·매매지시 아님.

사용: python reentry_check.py --code 222800 --market KOSDAQ \
       --entry 2026-02-26 --exit 2026-03-04 --name 심텍
"""
import argparse
import bisect
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from canslim_lib.fetch import fetch_yahoo_chart, yahoo_symbol  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

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
    ap.add_argument("--code", required=True)
    ap.add_argument("--market", required=True)
    ap.add_argument("--entry", required=True)
    ap.add_argument("--exit", dest="exitd", required=True)
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    nm = a.name or a.code

    sm = json.loads((CY / "_rs_sortmap.json").read_text(encoding="utf-8"))
    gk = sorted(sm)

    def rs_pct(ret, ds):
        i = bisect.bisect_right(gk, ds) - 1
        if i < 0:
            return None
        arr = sm[gk[i]]
        return 100 * bisect.bisect_left(arr, ret) / max(1, len(arr) - 1) if arr else None

    ks = fetch_yahoo_chart("%5EKS11", period1=_ep("2024-01-01"),
                           period2=_ep("2027-01-01"), interval="1d")
    kd = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
          for t in ks["timestamps"]]
    kc = ks["closes"]

    def kbull(ds):
        j = nidx(kd, ds)
        if j is None or j < 220:
            return None
        m, mp = sma(kc, j, 200), sma(kc, j - 20, 200)
        return bool(m and kc[j] > m and m > mp)

    ch = fetch_yahoo_chart(yahoo_symbol(a.code, a.market),
                           period1=_ep("2024-06-01"),
                           period2=_ep("2027-01-01"), interval="1d")
    ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
          for t in ch["timestamps"]]
    c, v = ch["closes"], ch.get("volumes") or []
    try:
        fr = sorted(fetch_naver_org_flow(a.code, pages=12, sleep_ms=150),
                    key=lambda r: r["date"])
    except Exception:
        fr = []

    def i60(ds):
        sel = [r for r in fr if r["date"] <= ds][-60:]
        if len(sel) < 30:
            return None
        return (sum(r.get("fgn_net") or 0 for r in sel) > 0
                or sum(r.get("org_net") or 0 for r in sel) > 0)

    def sig5(x):
        """그날 5신호 충족? (가격4 + I). 결손 시 False."""
        if x < 252 or x >= len(c) or c[x] <= 0 or c[x - 252] <= 0:
            return False, {}
        v50 = sum(v[x - 50:x]) / 50 if x >= 50 and v and sum(v[x - 50:x]) else None
        hi = max(c[x - 252:x + 1])
        m50 = sma(c, x, 50)
        rp = rs_pct(c[x] / c[x - 252] - 1, ts[x])
        ii = i60(ts[x])
        f = {
            "quiet": bool(v50 and v[x] / v50 <= 1.0),
            "below": bool(hi and c[x] <= 0.88 * hi),
            "near50": bool(m50 and abs(c[x] / m50 - 1) <= 0.10),
            "rs": bool(rp is not None and rp >= 50),
            "I": (ii is True),
        }
        return all(f.values()), f

    ei = nidx(ts, a.entry)
    xi = nidx(ts, a.exitd)
    e, xpx = c[ei], c[xi]
    cur = c[-1]
    leg1 = xpx / e - 1
    naive = cur / e - 1

    # 재진입 = 매도 다음날 이후, ★강세 & 5신호 재충족 첫날
    ri = None
    for x in range(xi + 1, len(c)):
        if kbull(ts[x]) and sig5(x)[0]:
            ri = x
            break
    L = [f"[재진입 검증] {nm}({a.code}) — 시스템(매수규칙=재진입규칙)",
         f"매수 {a.entry} {e:,.0f} → 원칙매도 {a.exitd} {xpx:,.0f} "
         f"(leg1 {leg1*100:+.1f}%, 자본보존)",
         f"매도일 ★코스피: {'강세(OFF)' if kbull(a.exitd) else '비강세' if kbull(a.exitd) is not None else '결손'}",
         ""]
    if ri is None:
        L += ["재진입 신호: 현재까지 5신호+★강세 재충족 *없음* → "
              "시스템은 '재진입 보류, 현금 유지' (SELL_CASH 확정).",
              f"  SELL_CASH 최종 {leg1*100:+.1f}% vs NAIVE {naive*100:+.1f}%"]
    else:
        rp_ = c[ri]
        leg2 = cur / rp_ - 1
        total = (1 + leg1) * (1 + leg2) - 1
        _, fl = sig5(ri)
        peak_after = max(c[ri:]) / rp_ - 1
        L += [f"▶ 재진입 신호일: **{ts[ri]} @ {rp_:,.0f}** "
              f"(매도 후 {ri-xi}거래일 뒤)",
              f"  그날 5신호: 거래량조용={fl['quiet']} 신고가아래={fl['below']} "
              f"50일선근처={fl['near50']} RS≥50={fl['rs']} 수급매집={fl['I']}",
              f"  재진입 후 현재 {ts[-1]} {cur:,.0f} = leg2 {leg2*100:+.1f}% "
              f"(재진입후 최대 +{peak_after*100:.0f}%)",
              "",
              "== 3가지 비교 (2/26 시작) ==",
              f"  NAIVE (안 팔고 보유)         : {naive*100:+.1f}%",
              f"  SELL_CASH (팔고 현금 유지)   : {leg1*100:+.1f}%",
              f"  SELL_REENTER (팔고 재진입)   : {total*100:+.1f}% "
              f"(leg1 {leg1*100:+.0f}% × leg2 {leg2*100:+.0f}%)",
              "",
              "해석: SELL_REENTER가 NAIVE 이상이면 — '쇼크 매도(자본보존)",
              "+ 규칙 재진입'이 단순보유보다 우월 = 시스템 구멍의 해법은",
              "*매도 금지*가 아니라 *재진입 규칙 명시*였음을 입증."]
    L += ["", "한계: 단일종목·종가·전향·거래비용 무관·RS=유니버스 백분위·"
          "frgn 결손 비임퓨트. 재진입규칙=매수규칙 재적용(별도 규칙 아님)."]
    out = (Path(__file__).resolve().parents[2] / "research"
           / "oneil-model-book" / f"_reentry_{a.code}.txt")
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()

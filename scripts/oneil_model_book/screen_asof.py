"""특정 과거 시점(as-of)의 최적 신호 종목 선정 + 현재까지 전향 검증.

한국형 위너 매매 시스템 v1: as-of 날짜 기준 *그날 알 수 있던 정보만* 으로
5신호 통과 종목 선정 → as-of→현재 실제 수익률로 신호 유효성 검증.

신호(모두 as-of 시점):
  ★ 코스피 강세(종가>200거래일선 & 200일선 상승) — 아니면 시스템 OFF
  ② 5신호: 거래량≤50일평균(조용) & 종가≤52주고가88%(신고가아래) &
     |종가/50일선−1|≤10%(근처) & RS백분위≥50 & 외인or기관 60일 순매수>0
1차(전종목·close+RS캐시): RS·신고가·50일선 통과 → RS순 상위 N1
2차(상위 N1만): Yahoo 거래량 + 네이버 frgn으로 거래량·I 확정 → 최종 N

데이터: `_universe_prices_5y.json`(close)·`_rs_sortmap.json`(RS백분위)·
Yahoo(거래량·검증)·네이버 frgn. 인-샘플성·생존자·짧은 창 한계 명시.
환각 금지·결손 비임퓨트. *매매 지시 아님 — 전향 검증 실험.*

사용:  python screen_asof.py --asof 2026-02-26 --n 5
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
    ap.add_argument("--asof", required=True)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--n1", type=int, default=30)   # 1차 상위 후보
    args = ap.parse_args()
    AS = args.asof

    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    sm = json.loads((CY / "_rs_sortmap.json").read_text(encoding="utf-8"))
    gk = sorted(sm)
    w = json.loads((CY / "winners.json").read_text(encoding="utf-8"))
    nmap = {r["code"]: (r["name"], r["market"]) for r in w["ranked_valid"]}

    def rs_pct(ret, ds):
        i = bisect.bisect_right(gk, ds) - 1
        if i < 0:
            return None
        a = sm[gk[i]]
        return 100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1) if a else None

    # ★ 코스피 국면 @ as-of
    ks = fetch_yahoo_chart("%5EKS11", period1=_ep("2023-01-01"),
                           period2=_ep("2027-01-01"), interval="1d")
    bull = None
    kline = "결손"
    if ks and ks.get("closes"):
        kd = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
              for t in ks["timestamps"]]
        kc = ks["closes"]
        kj = nidx(kd, AS)
        if kj is not None and kj >= 220:
            km, kmp = sma(kc, kj, 200), sma(kc, kj - 20, 200)
            bull = (km and kc[kj] > km and km > kmp)
            kline = (f"코스피 {kd[kj]} {kc[kj]:,.0f} vs 200일선 {km:,.0f} "
                     f"→ {'강세(시스템 ON)' if bull else '비강세(시스템 OFF)'}")

    # 1차: 전종목 close+RS
    cand = []
    last_global = max(U[c0]["d"][-1] for c0 in list(U)[:1])
    for code, s in U.items():
        d, c = s.get("d"), s.get("c")
        if not d or not c:
            continue
        ai = nidx(d, AS)
        if ai is None or ai < 252 or c[ai] <= 0 or c[ai - 252] <= 0:
            continue
        hi52 = max(c[ai - 252:ai + 1])
        m50 = sma(c, ai, 50)
        if not (hi52 and m50):
            continue
        rp = rs_pct(c[ai] / c[ai - 252] - 1, d[ai])
        if rp is None or rp < 50:
            continue
        if c[ai] > 0.88 * hi52:                 # 신고가 아래
            continue
        if abs(c[ai] / m50 - 1) > 0.10:         # 50일선 근처
            continue
        cand.append((code, ai, rp, c[ai], hi52))
    cand.sort(key=lambda x: -x[2])
    short = cand[:args.n1]

    # 2차: 거래량(Yahoo) + I(frgn) 확정
    picks = []
    for code, ai, rp, cas, hi52 in short:
        name, mkt = nmap.get(code, (code, "KOSPI"))
        ch = fetch_yahoo_chart(yahoo_symbol(code, mkt),
                               period1=_ep("2024-06-01"),
                               period2=_ep("2027-01-01"), interval="1d")
        if not ch or not ch.get("closes"):
            continue
        ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
              for t in ch["timestamps"]]
        cc, vv = ch["closes"], ch.get("volumes") or []
        bi = nidx(ts, AS)
        if bi is None or bi < 50 or not vv or len(vv) <= bi:
            continue
        v50 = sum(vv[bi - 50:bi]) / 50 if sum(vv[bi - 50:bi]) else None
        quiet = bool(v50 and vv[bi] / v50 <= 1.0)
        try:
            fr = sorted(fetch_naver_org_flow(code, pages=10, sleep_ms=150),
                        key=lambda r: r["date"])
            sel = [r for r in fr if r["date"] <= AS][-60:]
            fg = sum(r.get("fgn_net") or 0 for r in sel) if len(sel) >= 30 else None
            og = sum(r.get("org_net") or 0 for r in sel) if len(sel) >= 30 else None
            iok = (fg is not None and ((fg > 0) or (og > 0)))
        except Exception:
            fg = og = None
            iok = None
        if not quiet or iok is not True:
            continue
        cur = cc[-1]
        pmax = max(cc[bi:])
        picks.append({
            "code": code, "name": name, "mkt": mkt, "rs": rp,
            "asof_close": cc[bi], "vol_ratio": round(vv[bi] / v50, 2),
            "pct_52w_high": round(cc[bi] / hi52 * 100, 1),
            "fg60": fg, "og60": og,
            "cur_date": ts[-1], "cur": cur,
            "ret_pct": round((cur / cc[bi] - 1) * 100, 1),
            "maxret_pct": round((pmax / cc[bi] - 1) * 100, 1)})
        if len(picks) >= args.n:
            break

    L = [f"[전향 검증] as-of {AS} 최적신호 종목 → 현재까지",
         f"★ {kline}",
         f"1차 통과(RS≥50·신고가아래·50일선근처) {len(cand)}개 → 2차"
         f"(거래량 조용·외인/기관 매집) 확정 상위 {len(picks)}",
         "신호=시스템 v1 ②5신호 (그날 정보만). 매매지시 아님·전향 실험.",
         ""]
    if bull is False:
        L.append("⚠ as-of 코스피 비강세 → 시스템상 매수 OFF 국면(아래는 참고).")
    L.append("종목 | RS | as-of종가 | 거래량배 | 52주고가% | 외인60 | 기관60 "
             "| 현재 | 수익% | 기간최대%")
    L.append("-" * 30)
    for p in picks:
        L.append(
            f"{p['name']}({p['code']}) | RS{p['rs']:.0f} | "
            f"{p['asof_close']:,.0f} | {p['vol_ratio']}x | "
            f"{p['pct_52w_high']}% | {p['fg60']:+,} | {p['og60']:+,} | "
            f"{p['cur']:,.0f}({p['cur_date']}) | {p['ret_pct']:+.1f}% | "
            f"+{p['maxret_pct']:.1f}%")
    if picks:
        rs_ = sorted(x["ret_pct"] for x in picks)
        L += ["",
              f"요약: 수익 중앙 {rs_[len(rs_)//2]:+.1f}% · 평균 "
              f"{sum(rs_)/len(rs_):+.1f}% · 양(+) "
              f"{sum(1 for x in rs_ if x>0)}/{len(rs_)} · 기간최대 평균 "
              f"+{sum(x['maxret_pct'] for x in picks)/len(picks):.0f}%"]
    L += ["",
          "한계: 짧은 창(~3개월)·생존자(상폐제외)·시스템이 이 사이클 포함",
          "데이터로 튜닝(완전 OOS 아님)·종가·RS=유니버스 백분위(전수)·",
          "거래비용 무관. 신호 유효성의 *방향* 참고용, 수익 보장 아님."]
    out = CY.parent.parent / f"_screen_asof_{AS}.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out} (picks {len(picks)})", file=sys.stderr)


if __name__ == "__main__":
    main()

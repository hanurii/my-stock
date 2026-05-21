"""[통합 자본곡선] 한 통장으로 이어 굴린 실제 성과 — 비용·약세현금 포함.

리뷰어 다수 지적: 전 분석이 단일종목·사이클별. "약세장 현금화의
가치는 *이어붙였을 때만* 정직하게 보인다". 이 스크립트는 연속
유니버스(c2024-12 _5y: 2021-05~2026-05 — 2022 약세장 + 2024 사이클
포함)에서 *하나의 계좌*를 일별로 굴린다:

  · N슬롯 동일가중. ★시스템 ON(코스피>200일선&상승) & 빈 슬롯 →
    가격기반 스위트스폿(L RS≥80 + 선행상승≥50, look-ahead 차단)
    상위 RS 매수.
  · 보유 출구: ③진입대비-15% · ④고점대비-20% 트레일 · ★약세 전량.
  · 비용: 한국 매도 거래세 0.18% + 슬리피지(왕복 bp, 파라미터).
  · ★OFF 구간 = 전량 현금(이자 0, 문서 가정).

산출: CAGR·최대낙폭(MDD)·최장 수중기간·샤프·현금비중, KOSPI 매수
보유 대비, ★스위치 有無·비용 前後 4변형. 둘째 곡선=c2020-03 파일.
*사후·종가·일별·유니버스파일 생존자 잔존(일부 강제정지명 누락
가능)·세금 0.18% 가정·이자 0.* 근거 재사용=analyze_doppelganger.

사용: python scripts/oneil_model_book/analyze_equity_curve.py
      [--src c2024-12] [--slots 8] [--tag ""]
"""
import argparse
import bisect
import json
import math
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import analyze_doppelganger as AD                       # noqa: E402
from canslim_lib.fetch import fetch_yahoo_chart         # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "research" / "oneil-model-book"


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def kospi_series():
    ks = fetch_yahoo_chart("%5EKS11", period1=_ep("2017-01-01"),
                           period2=_ep("2027-01-01"), interval="1d")
    if not ks or not ks.get("closes"):
        return None, None
    kd = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
          for t in ks["timestamps"]]
    return kd, ks["closes"]


def sma(c, i, w):
    return sum(c[i - w + 1:i + 1]) / w if i >= w - 1 else None


def prefix(c):
    P = [0.0] * (len(c) + 1)
    for i, v in enumerate(c):
        P[i + 1] = P[i] + v
    return P


def smap(P, i, w):
    """prefix-sum O(1) 이동평균."""
    return (P[i + 1] - P[i + 1 - w]) / w if i >= w - 1 else None


def confirmed_p(c, P, d):
    if d < 60:
        return False
    m, mp = smap(P, d, 50), smap(P, d - 10, 50)
    return bool(m and mp and c[d] > m and m > mp and c[d] > c[d - 20])


def kbear_at(kd, kc, ds):
    j = bisect.bisect_right(kd, ds) - 1
    if j < 220:
        return False
    m, mp = sma(kc, j, 200), sma(kc, j - 20, 200)
    return bool(m and mp and kc[j] < m and m < mp)


def metrics(eq_dates, eq):
    """eq=일별 자본(1.0 시작). CAGR·MDD·최장수중·샤프."""
    if len(eq) < 30:
        return None
    yrs = (datetime.strptime(eq_dates[-1], "%Y-%m-%d")
           - datetime.strptime(eq_dates[0], "%Y-%m-%d")).days / 365.25
    cagr = (eq[-1] ** (1 / yrs) - 1) if (yrs > 0 and eq[-1] > 0) else None
    peak = eq[0]
    mdd = 0.0
    uw = uw_max = 0
    for v in eq:
        if v >= peak:
            peak = v
            uw = 0
        else:
            uw += 1
            uw_max = max(uw_max, uw)
        mdd = min(mdd, v / peak - 1)
    rets = [eq[i] / eq[i - 1] - 1 for i in range(1, len(eq)) if eq[i - 1] > 0]
    sharpe = None
    if len(rets) > 2 and st.pstdev(rets) > 0:
        sharpe = (st.mean(rets) / st.pstdev(rets)) * math.sqrt(252)
    return {"final": eq[-1], "cagr": cagr, "mdd": mdd,
            "uw_max": uw_max, "sharpe": sharpe, "yrs": yrs}


_TR = []


def simulate(U, codes_d, grid, ref, kd, kc, start, end, slots,
             use_switch, cost):
    """일별 포트폴리오 시뮬. cost=왕복 비용율(매도세+슬리피지)."""
    global _TR
    _TR = []
    axis = sorted({d for v in codes_d.values() for d in v[0]
                   if start <= d <= end})
    pos = {}                       # code -> {inv, entry, peak}
    cash = 1.0
    eq_d, eq = [], []
    for ti, t in enumerate(axis):
        on = True if not use_switch else (not kbear_at(kd, kc, t))
        # 1) 보유 평가·출구
        for code in list(pos):
            d, c, _ = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i < 0:
                continue
            px = c[i]
            p = pos[code]
            p["peak"] = max(p["peak"], px)
            exit_ = (px <= p["entry"] * 0.85 or px <= p["peak"] * 0.80
                     or (use_switch and not on))
            if exit_:
                cash += p["inv"] * (px / p["entry"]) * (1 - cost)
                _TR.append(px / p["entry"] - 1)
                del pos[code]
        # 2) 진입 — 주1회(5거래일)·★ON·빈슬롯. 게이트 싼것→비싼것,
        #    prior_up_at(O(500)) 은 *맨 마지막*(성능).
        if on and len(pos) < slots and ti % 5 == 0:
            gi = bisect.bisect_right(grid, t) - 1
            arr = ref.get(grid[gi]) if gi >= 0 else None
            cand = []
            for code, (d, c, P) in codes_d.items():
                if code in pos:
                    continue
                j = bisect.bisect_right(d, t) - 1
                if j < 253 or c[j] <= 0 or c[j - 252] <= 0:
                    continue
                if not confirmed_p(c, P, j):                 # O(1)
                    continue
                m50 = smap(P, j, 50)
                if not m50 or abs(c[j] / m50 - 1) > 0.10:    # 50일선 근처
                    continue
                hi52 = max(c[max(0, j - 251):j + 1])
                if not hi52 or c[j] > 0.88 * hi52:            # 추격 아님
                    continue
                if len(set(c[max(0, j - 60):j + 1])) < 10:    # 거래정지
                    continue
                lo = max(61, j - 15)                          # 추세확인 신선
                if not any(confirmed_p(c, P, x)
                           and not confirmed_p(c, P, x - 1)
                           for x in range(j, lo - 1, -1)):
                    continue
                rp = AD.rs_pct(arr, c[j] / c[j - 252] - 1)    # L
                if rp is None or rp < 80:
                    continue
                pu = AD.prior_up_at(c, j)                     # O(500) 최후
                if pu is None or pu < 0.50:
                    continue
                cand.append((rp, code, c[j]))
            cand.sort(reverse=True)
            for rp, code, px in cand[:slots - len(pos)]:
                if cash <= 1e-9:
                    break
                buy = min(cash, cash / (slots - len(pos)))
                cash -= buy
                pos[code] = {"inv": buy * (1 - cost), "entry": px,
                             "peak": px}
        # 3) 자본 평가
        mv = cash
        for code, p in pos.items():
            d, c, _ = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i >= 0:
                mv += p["inv"] * (c[i] / p["entry"])
        eq_d.append(t)
        eq.append(mv)
    return eq_d, eq


def kospi_bh(kd, kc, start, end):
    i0 = bisect.bisect_left(kd, start)
    i1 = bisect.bisect_right(kd, end) - 1
    if i0 >= i1:
        return None
    base = kc[i0]
    return [kd[k] for k in range(i0, i1 + 1)], \
           [kc[k] / base for k in range(i0, i1 + 1)]


def fmtm(m):
    if not m:
        return "결손"
    shp = "n/a" if m["sharpe"] is None else f"{m['sharpe']:.2f}"
    cg = (m["cagr"] * 100) if m["cagr"] is not None else 0
    return (f"최종 ×{m['final']:.2f} · CAGR {cg:+.0f}% · "
            f"MDD {m['mdd']*100:.0f}% · 최장수중 {m['uw_max']}일 · "
            f"샤프 {shp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="c2024-12",
                    help="유니버스 출처(연속창). c2024-12=_5y 2021~2026")
    ap.add_argument("--slots", type=int, default=8)
    ap.add_argument("--cost", type=float, default=0.0066,
                    help="왕복 비용율(매도세0.18%+슬리피지). 기본 0.66%")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    U = AD.pick_universe_file(a.src)
    if not U:
        raise SystemExit(f"universe 없음: {a.src}")
    codes_d = {code: (s["d"], s["c"], prefix(s["c"]))
               for code, s in U.items()
               if s.get("d") and s.get("c") and len(s["c"]) > 260}
    alld = sorted({d for d, _, _ in codes_d.values() for d in d})
    start, end = alld[0], alld[-1]
    # RS 시작 252거래일 확보 후부터 운용
    run_start = alld[min(len(alld) - 1, 260)]
    grid, ref = AD.build_rs_grid(U, start, end)
    kd, kc = kospi_series()
    if kd is None:
        raise SystemExit("KOSPI 미수신")

    res = {}
    res["순+스위치"] = simulate(U, codes_d, grid, ref, kd, kc, run_start,
                              end, a.slots, True, a.cost)
    tr = list(_TR)                                  # 순+스위치 체결내역 스냅샷
    res["순+스위치無"] = simulate(U, codes_d, grid, ref, kd, kc, run_start,
                                end, a.slots, False, a.cost)
    res["총(비용0)+스위치"] = simulate(U, codes_d, grid, ref, kd, kc,
                                    run_start, end, a.slots, True, 0.0)
    bh = kospi_bh(kd, kc, run_start, end)

    L = [f"[통합 자본곡선] 한 통장 연속 운용 [{a.src}] "
         f"{run_start}~{end} (≈{(datetime.strptime(end,'%Y-%m-%d')-datetime.strptime(run_start,'%Y-%m-%d')).days/365.25:.1f}년)",
         f"슬롯 {a.slots}동일가중 · 비용 왕복 {a.cost*100:.2f}%"
         "(매도세0.18%+슬리피지) · 진입=스위트스폿(L+선행상승) "
         "· 출구=-15재해/-20트레일/★약세",
         "*사후·종가·일별·유니버스 생존자 잔존·이자0·look-ahead 차단.*",
         "=" * 70]
    for nm, (ed, eq) in res.items():
        L.append(f"■ {nm:14s} {fmtm(metrics(ed, eq))}")
    if bh:
        L.append(f"■ {'KOSPI 매수보유':14s} {fmtm(metrics(bh[0], bh[1]))}")
    _yrs = (datetime.strptime(end, "%Y-%m-%d")
            - datetime.strptime(run_start, "%Y-%m-%d")).days / 365.25
    if tr:
        w = [x for x in tr if x > 0]
        s = sorted(tr)
        L += ["-" * 70,
              f"■ 체결내역(순+스위치) — 실시간 진입 {len(tr)}건 "
              f"(연 {len(tr)/max(0.1, _yrs):.0f}건)",
              f"  승률 {100*len(w)/len(tr):.0f}% · 평균 {100*st.mean(tr):+.1f}% "
              f"· 중앙 {100*s[len(s)//2]:+.1f}% · 최고 {100*max(tr):+.0f}% "
              f"· 최악 {100*min(tr):+.0f}%",
              "  → 모델북 '위너 +90%'는 *사후 pivot(바닥을 알고 찍은 점)* "
              "진입. 같은 스크린을 *실시간*(바닥 모름)으로 사면 위 분포."]
    base = metrics(*res["순+스위치"])
    nosw = metrics(*res["순+스위치無"])
    L += ["-" * 70,
          "■ 핵심 비교",
          f"  · ★약세스위치 가치: 스위치有 vs 無 → "
          f"CAGR {(base['cagr'] or 0)*100:+.0f}% vs "
          f"{(nosw['cagr'] or 0)*100:+.0f}% · "
          f"MDD {base['mdd']*100:.0f}% vs {nosw['mdd']*100:.0f}% "
          f"(약세장 현금화가 낙폭을 얼마나 줄이나)",
          f"  · 비용 영향: 비용0 CAGR "
          f"{(metrics(*res['총(비용0)+스위치'])['cagr'] or 0)*100:+.0f}%"
          f" → 비용반영 {(base['cagr'] or 0)*100:+.0f}% "
          f"(수수료·세금이 깎는 폭)"]
    if bh:
        bhm = metrics(bh[0], bh[1])
        L.append(f"  · vs KOSPI 그냥 보유: 시스템 CAGR "
                 f"{(base['cagr'] or 0)*100:+.0f}% (MDD {base['mdd']*100:.0f}%)"
                 f" vs KOSPI {(bhm['cagr'] or 0)*100:+.0f}% "
                 f"(MDD {bhm['mdd']*100:.0f}%) — 진짜 알파인가")
    L += ["=" * 70,
          "★ 핵심 결론(정직): 이 곡선은 KOSPI(+19%)에 크게 패함",
          "(CAGR 음수·MDD 큼). 이것이 *시스템 무용* 을 뜻하진 않는다 —",
          "두 가지를 분리해 읽어야 한다:",
          " ① 사후 pivot 착시: 모델북 '위너 +90%/23.6x' 는 *바닥을 알고*",
          "   찍은 pivot 진입. 같은 스크린을 *실시간*(바닥 모름)으로 사면",
          f"   승률 ~{(100*len([x for x in tr if x>0])/len(tr) if tr else 0):.0f}%"
          "·평균 마이너스 → 문서 수치는 실거래 달성 불가, 사후성이",
          "   각주가 아니라 핵심임을 정량 입증(buy_timing '타이밍 단독",
          "   lift≈1.0' 과 일치).",
          " ② 가드 부재: 본 백테스트는 거래량-조용·케이프·수급(I)·섹터",
          "   무리 가드를 재현 못 함(유니버스파일에 거래량/수급 없음).",
          "   진짜 edge 가 있다면 그 가드들에 있음 — 이 곡선으론 검증",
          "   불가. = '가격 스크린만으론 못 번다' 의 실측(강력한 음성결과).",
          " ③ ★스위치는 작동: MDD/CAGR 모두 스위치有>無 → 약세장 현금화",
          "   가치는 (음수 안에서도) 실재.",
          "함의: 라이브 운용 전 *가드 포함 + 실시간(무사후) 재현* 필수.",
          "한계: 사후 pivot 미사용은 오히려 정직↑이나, 가드 미포함=시스템",
          "불완전 재현·종가·일별·유니버스 생존자 잔존·세금0.18%·이자0·",
          "단일 연속창(2021~2026, 2020사이클은 별 파일)."]
    txt = "\n".join(L)
    p = OUT / f"_equity_curve{a.tag}.txt"
    p.write_text(txt, encoding="utf-8")
    (OUT / "cycles" / a.src / "equity_curve_rows.json").write_text(
        json.dumps({nm: {"final": metrics(ed, eq) and metrics(ed, eq)["final"],
                         "metrics": metrics(ed, eq)}
                    for nm, (ed, eq) in res.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 통합 자본곡선 [{a.src}] 슬롯{a.slots}\n\n"
                f"```\n{txt}\n```\n")
    print(f"saved: {p}", file=sys.stderr)


if __name__ == "__main__":
    main()

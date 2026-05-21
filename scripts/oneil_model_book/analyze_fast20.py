"""빠른 +20% 상승 출발점 케이스 마이닝 — 그 순간의 공통점 찾기.

REPORT.md 위너 200 중 무작위 10종목. 각 종목에서 '짧은 시간에 +20%'
케이스를 *전부* 추출:
  케이스 = 스윙 저점 b 에서, 도중에 −10% 아래로 안 빠지고(클린) +20%
  를 MAXH(기본 60거래일) 안에 도달. b 이후 그 +20% 도달일까지 = 소요일.
각 케이스의 매수시점 b 상태를 실측:
  L  그날 RS 백분위(전종목 52주수익률, 주봉그리드)
  M  그날 시장(코스피/코스닥) 상승추세 여부
  I  b 종료 60일 외인/기관 순매수 (네이버 frgn, 동적페이지)
  C  b 시점 point-in-time 분기 EPS YoY (DART pit_qkey+yoy_pct)
  거래량  b 당일 / 직전 50일 평균 배수 (Yahoo)
  신고가  52주 고가 대비 %  · 50일선 위 %  · 저점→b 지각 · 직전 상승
한 종목 다(多) 케이스 가능 — 전부 보고. 결손은 추정 안 함.

사용:  python analyze_fast20.py [--n 10] [--seed 7] [--gain 20] [--maxh 60]
"""
import argparse
import bisect
import json
import random
import sys
from datetime import datetime, timezone, date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.fetch import (yahoo_symbol, resolve_corp_code,  # noqa: E402
                               load_corp_code_map)
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402
from analyze_gated_timing import idx_uptrend_by_date  # noqa: E402
from check_named_stocks import pit_qkey  # noqa: E402
from collect_variables import yoy_pct  # noqa: E402

CY = cyclecfg.DIR


def nidx(d, ds):
    cand = [k for k in range(len(d)) if d[k] <= ds]
    return cand[-1] if cand else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--gain", type=float, default=20.0)   # +X% 목표
    ap.add_argument("--maxh", type=int, default=60)        # 도달 허용 거래일
    ap.add_argument("--drop", type=float, default=10.0)    # 도중 허용 낙폭(클린)
    args = ap.parse_args()
    G, MAXH, DRP = args.gain / 100, args.maxh, args.drop / 100

    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    winners = wf["winners"]
    random.seed(args.seed)
    sample = random.sample(winners, min(args.n, len(winners)))
    corp_map = load_corp_code_map()

    # 주봉 그리드: 날짜별 전종목 252d수익률 정렬 → RS 백분위
    any_d = U[list(U)[0]]["d"]
    sortmap = {}
    for gi in range(252, len(any_d), 5):
        gd = any_d[gi]
        rr = []
        for s in U.values():
            d, c = s.get("d"), s.get("c")
            if not d or not c:
                continue
            j = gi if (gi < len(d) and d[gi] == gd) else nidx(d, gd)
            if j is None or j < 252 or c[j - 252] <= 0:
                continue
            rr.append(c[j] / c[j - 252] - 1)
        rr.sort()
        sortmap[gd] = rr
    gdates = sorted(sortmap)

    def rs_pct(ret, ds):
        cand = [x for x in gdates if x <= ds]
        if not cand:
            return None
        a = sortmap[cand[-1]]
        return round(100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1), 1) if a else None

    ks = idx_uptrend_by_date("%5EKS11")
    kq = idx_uptrend_by_date("%5EKQ11")
    last_cache = U[list(U)[0]]["d"][-1]

    out = [f"[c2024-12] 빠른 +{int(args.gain)}% 출발점 케이스 — 무작위 "
           f"{len(sample)}종목 (seed {args.seed})",
           f"케이스=스윙저점서 도중 −{int(args.drop)}% 안빠지고 "
           f"+{int(args.gain)}% 를 {MAXH}거래일내 도달. 매수시점 상태 실측.",
           ""]
    allcases = []

    for w in sample:
        code, name, mkt = w["code"], w["name"], w["market"]
        tro = w["trough_date"]
        ch = cyclecfg.yahoo(yahoo_symbol(code, mkt))
        if not ch or not ch.get("closes"):
            out.append(f"### {name}({code}) — 시세조회 실패\n")
            continue
        ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
              for t in ch["timestamps"]]
        c, v = ch["closes"], ch["volumes"]
        n = len(c)
        ti = nidx(ts, tro) or 0
        try:
            fr = fetch_naver_org_flow(
                code, pages=min(95, max(10, (
                    _date.fromisoformat(last_cache) - _date.fromisoformat(tro)
                ).days // 25 + 8)), sleep_ms=170)
        except Exception:
            fr = []
        fr_sorted = sorted(fr, key=lambda r: r["date"])

        cases = []
        x = max(ti, 252, 55)
        while x < n - 5:
            # 스윙 저점: ±5일 최저
            if c[x] <= 0 or c[x] != min(c[max(0, x - 5):min(n, x + 6)]):
                x += 1
                continue
            tgt, hit, bad = c[x] * (1 + G), None, False
            for k in range(x + 1, min(n, x + MAXH + 1)):
                if c[k] <= c[x] * (1 - DRP):
                    bad = True
                    break
                if c[k] >= tgt:
                    hit = k
                    break
            if not hit or bad:
                x += 1
                continue
            # 변수 실측 @ b=x
            rsret = c[x] / c[x - 252] - 1 if x >= 252 and c[x - 252] > 0 else None
            rp = rs_pct(rsret, ts[x]) if rsret is not None else None
            reg = (ks if mkt == "KOSPI" else kq).get(ts[x], False)
            v50 = sum(v[x - 50:x]) / 50 if x >= 50 and sum(v[x - 50:x]) else None
            volx = round(v[x] / v50, 2) if v50 else None
            hi52 = max(c[max(0, x - 252):x + 1])
            pct_hi = round(c[x] / hi52 * 100, 1) if hi52 else None
            ma50 = sum(c[x - 49:x + 1]) / 50 if x >= 49 else None
            abv = round((c[x] / ma50 - 1) * 100, 1) if ma50 else None
            prior = round((c[x] / min(c[max(0, x - 60):x + 1]) - 1) * 100, 1)
            fg = og = None
            sel = [r for r in fr_sorted if r["date"] <= ts[x]][-60:]
            if len(sel) >= 30:
                fg = sum(r.get("fgn_net") or 0 for r in sel)
                og = sum(r.get("org_net") or 0 for r in sel)
            cq = pit_qkey(ts[x])
            cval, csrc = (None, "qkey 실패")
            if cq:
                corp = w.get("corp_code") or resolve_corp_code(code, corp_map)[0]
                if corp:
                    cval, csrc = yoy_pct(corp, cq, "eps", code)
            cs = {"code": code, "name": name, "mkt": mkt,
                  "buy_date": ts[x], "buy_close": round(c[x], 1),
                  "days_to_gain": hit - x, "reach_date": ts[hit],
                  "run_max_pct": round((max(c[x:hit + 20 if hit + 20 < n else n])
                                        / c[x] - 1) * 100, 1),
                  "RS_pct": rp, "M_up": bool(reg),
                  "vol_vs_50d": volx, "pct_52w_high": pct_hi,
                  "above_ma50_pct": abv, "days_from_trough": x - ti,
                  "prior60_run_pct": prior,
                  "I_fgn60": fg, "I_org60": og,
                  "C_qkey": cq, "C_eps_yoy": cval, "C_src": csrc}
            cases.append(cs)
            allcases.append(cs)
            x = hit + 1                       # 같은 상승 중복 방지
        out.append(f"### {name}({code}/{mkt}) — 케이스 {len(cases)}개 "
                   f"(저점 {tro})")
        if not cases:
            out.append("  (조건 충족 케이스 없음)\n")
        for j, s in enumerate(cases, 1):
            out.append(
                f"  [{j}] 매수 {s['buy_date']} @ {s['buy_close']:,} → "
                f"+{int(args.gain)}% {s['days_to_gain']}거래일 "
                f"(이후 최대 +{s['run_max_pct']}%)")
            out.append(
                f"      RS {s['RS_pct']} | 시장 "
                f"{'상승' if s['M_up'] else '비상승'} | 거래량 "
                f"{s['vol_vs_50d']}배 | 52주고가 {s['pct_52w_high']}% | "
                f"50일선 {s['above_ma50_pct']}%")
            iv = (f"외인{s['I_fgn60']:,}/기관{s['I_org60']:,}"
                  if s['I_fgn60'] is not None else "결손")
            out.append(
                f"      저점후 {s['days_from_trough']}일 | 직전60일 "
                f"+{s['prior60_run_pct']}% | 수급60일 {iv} | "
                f"EPS({s['C_qkey']}) "
                f"{s['C_eps_yoy'] if s['C_eps_yoy'] is not None else '결손'}"
                f"{'%' if isinstance(s['C_eps_yoy'],(int,float)) else ''}")
        out.append("")

    # 공통점 요약
    A = allcases
    def med(xs):
        xs = sorted(x for x in xs if isinstance(x, (int, float)))
        return round(xs[len(xs) // 2], 1) if xs else None

    def pct(cond):
        ok = [c for c in A if cond(c) is not None]
        return (round(100 * sum(1 for c in ok if cond(c)) / len(ok)), len(ok)) if ok else (0, 0)

    if A:
        rs80 = pct(lambda c: None if c["RS_pct"] is None else c["RS_pct"] >= 80)
        rs50 = pct(lambda c: None if c["RS_pct"] is None else c["RS_pct"] >= 50)
        mup = pct(lambda c: c["M_up"])
        vol15 = pct(lambda c: None if c["vol_vs_50d"] is None else c["vol_vs_50d"] >= 1.5)
        nh = pct(lambda c: None if c["pct_52w_high"] is None else c["pct_52w_high"] >= 95)
        iok = pct(lambda c: None if c["I_fgn60"] is None
                  else (c["I_fgn60"] > 0 or c["I_org60"] > 0))
        cok = pct(lambda c: None if not isinstance(c["C_eps_yoy"], (int, float))
                  else c["C_eps_yoy"] > 0)
        out += [
            f"== 전체 케이스 {len(A)}개 공통점 ==",
            f"+{int(args.gain)}% 도달 소요(거래일) 중앙 {med([c['days_to_gain'] for c in A])} "
            f"(최소 {min(c['days_to_gain'] for c in A)}, 최대 {max(c['days_to_gain'] for c in A)})",
            f"RS≥80 {rs80[0]}% (n{rs80[1]}) | RS≥50 {rs50[0]}% | RS중앙 {med([c['RS_pct'] for c in A])}",
            f"시장 상승추세 {mup[0]}% | 거래량≥1.5배 {vol15[0]}% "
            f"(거래량배수 중앙 {med([c['vol_vs_50d'] for c in A])})",
            f"신고가권(52주고가 95%↑) {nh[0]}% (52주고가% 중앙 {med([c['pct_52w_high'] for c in A])})",
            f"수급 외인or기관 순매수 {iok[0]}% (n{iok[1]}) | "
            f"직전분기 EPS YoY>0 {cok[0]}% (n{cok[1]})",
            f"50일선 위 % 중앙 {med([c['above_ma50_pct'] for c in A])} | "
            f"저점→매수 중앙 {med([c['days_from_trough'] for c in A])}일 | "
            f"직전60일 상승 중앙 {med([c['prior60_run_pct'] for c in A])}%",
        ]
    out += ["", "한계: 무작위 10종목(위너만)·close+거래량 Yahoo·수급 네이버"
            "(결손 비임퓨트)·C DART. 사이클내 사후·인-샘플."]
    block = "\n".join(out)
    (CY / f"_fast{int(args.gain)}_cases.txt").write_text(block, encoding="utf-8")
    (CY / f"_fast{int(args.gain)}_cases.json").write_text(
        json.dumps(allcases, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved: _fast{int(args.gain)}_cases.txt ({len(A)} cases / "
          f"{len(sample)} stocks)", file=sys.stderr)


if __name__ == "__main__":
    main()

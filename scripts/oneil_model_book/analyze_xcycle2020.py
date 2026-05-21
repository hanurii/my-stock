"""2020-21 강세장(c2020-03) 아웃-오브-샘플 교차검증 — 1단계(가격·RS·출구).

c2024-12로 *찾고 검증*한 결론을 완전 홀드아웃인 c2020-03(앵커 2020-03-19
→ 2021-07-06, KOSPI +127%)에서 재현되는지 검증.
1단계(본 파일·frgn 없이): 매수 '언제'(5신호 중 가격4+RS) 정밀도·lift,
손절·매도 규칙 실현수익 — NON/MID/WIN 3단계. I(외국인)축은 2단계서
deep frgn(2019까지)로 추가.

RS: c2020-03용 캐시 없음 → 표본 N_RS종목 횡단으로 *근사* 백분위(라벨
명시). 시세=cyclecfg.yahoo(OMB_CYCLE=c2020-03 → period1≈2018-03,
period2≈2021-07, 거래량 포함). 인-샘플 아님(홀드아웃)·상폐제외·종가.
환각 금지·근사/결손 명시.

사용:  OMB_CYCLE=c2020-03 python analyze_xcycle2020.py [--nrs 400] [--nt 45]
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

DIR = cyclecfg.DIR
GAIN, MAXH, DROP = 0.20, 60, 0.10


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nrs", type=int, default=400)   # RS 근사 표본
    ap.add_argument("--nt", type=int, default=45)     # tier별 표본
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    if cyclecfg.CYCLE_ID != "c2020-03":
        print(f"경고: OMB_CYCLE!=c2020-03 (현재 {cyclecfg.CYCLE_ID})",
              file=sys.stderr)

    w = json.loads((DIR / "winners.json").read_text(encoding="utf-8"))
    rv = w["ranked_valid"]
    wf = json.loads((DIR / "winners_final.json").read_text(encoding="utf-8"))
    wc = {x["code"] for x in wf["winners"]}

    def ok(r):
        return (not r.get("exclude_reason") and r.get("trough_date")
                and r.get("n_days", 0) >= 60 and r.get("raw_multiple"))
    rest = [r for r in rv if r["code"] not in wc and ok(r)]
    NON = [r for r in rest if r["raw_multiple"] < 1.5]
    MID = [r for r in rest if 1.5 <= r["raw_multiple"] < 3.0]
    random.seed(args.seed)
    tiers = {"NON 안오름": random.sample(NON, min(args.nt, len(NON))),
             "MID 중간": random.sample(MID, min(args.nt, len(MID))),
             "WIN 위너": random.sample(wf["winners"], min(args.nt, len(wf["winners"])))}

    # RS 근사 표본 (tier 종목 포함) — 시세 1회 로드
    rs_pool = {r["code"]: r for r in rv if ok(r)}
    rs_codes = set(random.sample(list(rs_pool), min(args.nrs, len(rs_pool))))
    for t in tiers.values():
        for r in t:
            rs_codes.add(r["code"])
    SER = {}
    for code in rs_codes:
        r = rs_pool.get(code) or next((x for x in rv if x["code"] == code), None)
        if not r:
            continue
        ch = cyclecfg.yahoo(yahoo_symbol(code, r["market"]))
        if not ch or not ch.get("closes"):
            continue
        ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
              for t in ch["timestamps"]]
        SER[code] = (ts, ch["closes"], ch["volumes"], r)

    # RS 근사: 주봉 그리드, 표본 종목 252d수익률 정렬 → 백분위
    anyd = next(iter(SER.values()))[0] if SER else []
    grid = list(range(252, len(anyd), 5))
    sortmap = {}
    for gi in grid:
        gd = anyd[gi]
        arr = []
        for ts, c, _, _ in SER.values():
            j = nidx(ts, gd)
            if j is None or j < 252 or c[j - 252] <= 0:
                continue
            arr.append(c[j] / c[j - 252] - 1)
        arr.sort()
        sortmap[gd] = arr
    gd_keys = sorted(sortmap)

    def rs_pct(ret, ds):
        i = bisect.bisect_right(gd_keys, ds) - 1
        if i < 0:
            return None
        a = sortmap[gd_keys[i]]
        return 100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1) if a else None

    def sig_exit(lst):
        npts = nhit = f4 = h4 = fR = hR = 0
        oneil, wide = [], []
        for r in lst:
            S = SER.get(r["code"])
            if not S:
                continue
            ts, c, v, _ = S
            n = len(c)
            ti = nidx(ts, r["trough_date"]) or 0
            # 5신호(가격4+RS) 정밀도
            x = max(ti, 252, 55)
            while x < n - 6:
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
                v50 = sum(v[x-50:x]) / 50 if x >= 50 and sum(v[x-50:x]) else None
                hi = max(c[max(0, x-252):x+1])
                m50 = ma(c, x, 50)
                p4 = (v50 and v[x]/v50 <= 1.0 and hi and c[x] <= 0.88*hi
                      and m50 and abs(c[x]/m50-1) <= 0.10)
                if p4:
                    f4 += 1; h4 += hit
                    rp = rs_pct(c[x]/c[x-252]-1, ts[x]) if c[x-252] > 0 else None
                    if rp is not None and rp >= 50:
                        fR += 1; hR += hit
                x += 1
            # 출구: 인과진입 → ONEIL / WIDE(−15%재해+−35%트레일)
            e = causal_entry(c, ti, n)
            if e is None:
                continue
            end = n - 1
            # ONEIL
            pk = c[e]
            for k in range(e+1, end+1):
                pk = max(pk, c[k])
                g = c[k]/c[e]-1
                if c[k] <= c[e]*0.92:
                    oneil.append(g); break
                if g >= 0.20:
                    oneil.append(g if (k-e) > 15 else c[min(end, e+40)]/c[e]-1)
                    break
            else:
                oneil.append(c[end]/c[e]-1)
            # WIDE
            pk = c[e]
            for k in range(e+1, end+1):
                pk = max(pk, c[k])
                if c[k] <= c[e]*0.85 or c[k] <= pk*0.65:
                    wide.append(c[k]/c[e]-1); break
            else:
                wide.append(c[end]/c[e]-1)
        base = 100*nhit/npts if npts else 0
        p4r = 100*h4/f4 if f4 else 0
        pRr = 100*hR/fR if fR else 0
        return {
            "npts": npts, "base": base,
            "p4": p4r, "lift4": p4r/base if base else 0, "f4": f4,
            "pR": pRr, "liftR": pRr/base if base else 0, "fR": fR,
            "oneil": oneil, "wide": wide}

    out = [f"[홀드아웃] c2020-03(2020-03~2021-07, KOSPI+127%) 교차검증 1단계",
           f"(가격4신호+RS근사·출구; frgn/I축 2단계. tier {args.nt}·RS표본 "
           f"{len(SER)}·seed {args.seed})",
           "신호=거래량≤50일평균 & 종가≤52주고가88% & 50일선±10% (+RS≥50).",
           "RS=표본 횡단 *근사* 백분위. 클린+20%=−10%전 60거래일내.",
           "비교 기준(c2024-12 강세장): 가격4 lift~1.2x·+RS~1.46x / "
           "WIDE 위너 평균>>ONEIL.",
           ""]
    for tag, lst in tiers.items():
        R = sig_exit(lst)
        out.append(f"== {tag} (스윙저점 {R['npts']}, 기저 클린+20% "
                   f"{round(R['base'],1)}%) ==")
        out.append(f"  가격4축  발동 {R['f4']} → 정밀도 {round(R['p4'],1)}% "
                   f"| lift {round(R['lift4'],2)}x")
        out.append(f"  +RS≥50   발동 {R['fR']} → 정밀도 {round(R['pR'],1)}% "
                   f"| lift {round(R['liftR'],2)}x")
        for nm, arr in (("ONEIL(-8%·+20%/8주)", R["oneil"]),
                        ("WIDE(-15%재해·-35%트레일)", R["wide"])):
            if arr:
                a = [z*100 for z in arr]
                out.append(f"  출구 {nm}: 평균 {round(st.mean(a),1)}% · 중앙 "
                           f"{round(st.median(a),1)}% · 승률 "
                           f"{round(100*sum(1 for z in a if z>0)/len(a))}% · "
                           f"최악 {round(min(a),1)}% (n{len(a)})")
        out.append("")
    out += ["== 해석 ==",
            "c2024-12와 같은 방향(가격4 lift>1·+RS가 더↑·WIDE>ONEIL on 위너)",
            "이면 결론이 홀드아웃서 *재현*=심리불변/패턴반복 지지. 어긋나면",
            "c2024-12 특수(인-샘플) 의심. 절대수치는 RS근사·표본 영향.",
            "== 2020-21 vs 2024-25 (정성) ==",
            "2020-21: 코로나 폭락→제로금리·대규모 유동성/QE·동학개미 급증·",
            " 성장/언택트 주도. 2024-25: 계엄 쇼크 바닥·밸류업·금리 인하초입·",
            " 외국인/실적 주도. 둘 다 급락 후 V반등 강세장이나 동력 상이 —",
            " 신호 재현되면 *동력 무관 패턴 불변* 의 강한 증거.",
            "== 한계 ==",
            "RS=표본 횡단 근사(전수 아님)·I(외국인)축 미포함(2단계)·상폐",
            "제외·종가·단일 인과진입·비용무관. 방향 비교 목적."]
    fn = DIR / f"_xcycle2020_p1_s{args.seed}.txt"
    fn.write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()

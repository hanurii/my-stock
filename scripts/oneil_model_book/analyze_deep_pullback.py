"""'신고가 후 깊고 오래 하락한 자리(=케이프형)'서 출발한 위너가 있나?

질문: 폭발 위너 중, *직전 고점 대비 깊이(≥12%↓) 떨어지고 그 고점이
오래전(>5거래일)* 인 자리(v1.3 가드를 빠져나가는 케이프 모양)에서
출발한 사례가 있는가? 그런 모양은 함정인가, 정당한 위너 베이스인가?

방법(2 사이클·로컬·환각 없음): 각 종목 pivot(폭발 출발점)에서
 - 직전 60거래일 고점 hi60, 그 고점까지 거리(거래일) hi_age
 - pivot 가격이 hi60 대비 낙폭 drop
 - 케이프형 = drop ≤ −12% AND hi_age > 5  (깊은+오래된 고점후 하락)
 - 깊은형(strict) = drop ≤ −20%
 - 이후 성장 = pivot 이후 120거래일 내 최고종가 / pivot − 1
위너(c2024-12+c2020-03 각200)와 안오름(각500)에서:
 ① 위너 중 케이프형 빈도·이후성장(예시 종목명)
 ② 케이프형 모집단의 위너율 vs 비케이프형 → 함정이면 위너율 급락
정직: 사후·생존자(상폐 제외)·단일창·induty 무관. 방향만.
사용: python analyze_deep_pullback.py
"""
import json
import statistics as st
import sys
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
PAIRS = [("c2024-12", "c2024-12-ctrl500", "_universe_prices_5y.json", "2024-25"),
         ("c2020-03", "c2020-03-ctrl500", "_universe_prices.json", "2020-21")]


def rows(p):
    return [r for r in json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
            if not r.get("error") and r.get("pivot_date")]


def med(v):
    return st.median(v) if v else None


def shape_at(c, i0):
    """(낙폭, 고점경과거래일) at pivot. 부족하면 None."""
    if i0 < 20 or i0 >= len(c):
        return None
    seg = c[max(0, i0 - 60):i0 + 1]
    hi = max(seg)
    if hi <= 0 or c[i0] <= 0:
        return None
    hidx = max(range(i0 - len(seg) + 1, i0 + 1), key=lambda k: c[k])
    return c[i0] / hi - 1.0, i0 - hidx


def fut_gain(c, i0):
    seg = c[i0:min(i0 + 120, len(c))]
    return (max(seg) / c[i0] - 1.0) if len(seg) > 5 and c[i0] > 0 else None


def main():
    out = ["[신고가 후 깊고 오래 하락한 자리(케이프형)서 출발한 위너 검정]",
           "케이프형 = pivot가 직전60일고점 대비 ≤−12% AND 그 고점 >5거래일 전",
           "(v1.3 가드가 못 잡는 '오래된 고점+깊은 하락' 모양)",
           "=" * 64]
    allW_cape = allW_non = 0
    pool_cape_w = pool_cape_n = pool_non_w = pool_non_n = 0
    for win, ctl, pf, nm in PAIRS:
        U = json.loads((CY / win / pf).read_text(encoding="utf-8"))

        def series(code):
            s = U.get(code) or {}
            return s.get("d") or [], s.get("c") or []

        def tag(rws):
            res = []
            for r in rws:
                d, c = series(r["code"])
                if r["pivot_date"] not in d:
                    continue
                i0 = d.index(r["pivot_date"])
                sh = shape_at(c, i0)
                g = fut_gain(c, i0)
                if sh is None or g is None:
                    continue
                drop, age = sh
                cape = (drop <= -0.12 and age > 5)
                deep = (drop <= -0.20 and age > 5)
                res.append((r.get("name", r["code"]), drop, age, g, cape, deep))
            return res

        W = tag(rows(win))
        Lo = tag(rows(ctl))
        wc = [x for x in W if x[4]]
        wn = [x for x in W if not x[4]]
        out += [f"■ {nm}  (위너 {len(W)} / 안오름 {len(Lo)})",
                f"  위너 중 케이프형 {len(wc)}/{len(W)} "
                f"({100*len(wc)//max(1,len(W))}%) — 이후성장 중앙 "
                f"{(med([x[3] for x in wc]) or 0)*100:.0f}% "
                f"(비케이프형 {(med([x[3] for x in wn]) or 0)*100:.0f}%)"]
        ex = sorted(wc, key=lambda x: -x[3])[:5]
        for n, dr, ag, g, _, dp in ex:
            out.append(f"     예) {n}: 고점대비 {dr*100:+.0f}%·{ag}거래일전"
                       f"{' (깊은형≥20%↓)' if dp else ''} → 이후 +{g*100:.0f}%")
        # 케이프형 모집단의 위너율
        lc = [x for x in Lo if x[4]]
        ln = [x for x in Lo if not x[4]]
        cw, cn = len(wc), len(lc)
        nw, nn = len(wn), len(ln)
        pr_c = cw / (cw + cn) * 100 if (cw + cn) else 0
        pr_n = nw / (nw + nn) * 100 if (nw + nn) else 0
        out += [f"  케이프형 모집단 위너율 {pr_c:.0f}% (위너{cw}/안오름{cn}) "
                f"vs 비케이프형 위너율 {pr_n:.0f}% (위너{nw}/안오름{nn})",
                f"  안오름 케이프형 이후성장 중앙 "
                f"{(med([x[3] for x in lc]) or 0)*100:.0f}%", "-" * 64]
        allW_cape += len(wc)
        allW_non += len(wn)
        pool_cape_w += cw
        pool_cape_n += cn
        pool_non_w += nw
        pool_non_n += nn
    PC = pool_cape_w / (pool_cape_w + pool_cape_n) * 100 if (pool_cape_w + pool_cape_n) else 0
    PN = pool_non_w / (pool_non_w + pool_non_n) * 100 if (pool_non_w + pool_non_n) else 0
    out += [f"[종합] 위너 총 {allW_cape} 종목이 케이프형서 출발(존재함)·"
            f"비케이프형 {allW_non}",
            f"케이프형 모집단 위너율 {PC:.0f}% vs 비케이프형 {PN:.0f}%",
            "",
            "판정 가이드:",
            "- 케이프형 위너 사례가 다수·이후성장 비슷 → '깊은 눌림서도",
            "  위너 난다', 무조건 제외는 과함(케이프 살릴 여지).",
            "- 케이프형 위너율이 비케이프형보다 *크게 낮음* → 함정 성격,",
            "  v1.3 가드를 '오래된 고점+깊은 하락'까지 확장 권고.",
            "정직한 한계: 사후·생존자(상폐 제외→하락 과소)·단일 60일창·",
            "120거래일 성장창 임의·pivot=출발 프록시. 방향만, 절대수치 X."]
    fp = CY.parent / "_deep_pullback.txt"
    fp.write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fp} (capeWinRate={PC:.0f}% nonCapeWinRate={PN:.0f}% "
          f"capeWinners={allW_cape})", file=sys.stderr)


if __name__ == "__main__":
    main()

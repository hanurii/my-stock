"""신저점-케이프(현 제외 대상) 안에서 '로켓 위너' 되살리기 검정.

현 v1.3 정교화는 '케이프형 & 오늘=15일신저점'을 제외 → 한국피아이엠형
(+1211%) 로켓 ~31%도 같이 버림(트레이드오프). 질문: 이 *제외 집합*
안에서 위너(로켓) vs 안오름(자유낙하 함정)을 가르는 표식이 있나?
있으면 그 표식 충족분만 '구제(rescue)'해 트레이드오프를 깬다.

대상 = 케이프형(직전60일고점 ≤−12% & 그 고점>5거래일전) AND 오늘이
최근15일 신저점. 위너+안오름·2사이클. 표식 후보(model_book pivot값):
 RS rs_score ≥ {80,90} · 선행상승 prior_uptrend_pct ≥ {100,150}
 낙폭 구간(−12~−30 '중간' vs ≤−30 '파국') · 조합.
각 구제게이트: 로켓 회수%(제외위너 중)·함정 재유입%(제외안오름 중)·
구제집합 실현 평균/최악10%(−15손절+⑤보수). 깨끗한 분리 있으면 채택.
정직: 사후·종가·생존자·보수가정. 순위/방향만.
사용: python analyze_cape_rescue.py
"""
import json
import statistics as st
import sys
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
PAIRS = [("c2024-12", "c2024-12-ctrl500", "_universe_prices_5y.json"),
         ("c2020-03", "c2020-03-ctrl500", "_universe_prices.json")]
HOLD = 250


def rows(p):
    return [r for r in json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
            if not r.get("error") and r.get("pivot_date")]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def excluded_cape(c, i0):
    """현 규칙이 제외하는 집합인가 + 낙폭. 아니면 None."""
    if i0 < 60 or i0 >= len(c) or c[i0] <= 0:
        return None
    seg = c[i0 - 60:i0 + 1]
    hi = max(seg)
    hidx = max(range(i0 - 60, i0 + 1), key=lambda k: c[k])
    drop = c[i0] / hi - 1.0
    if not (drop <= -0.12 and (i0 - hidx) > 5):
        return None                                   # 케이프 아님
    w15 = c[i0 - 15:i0 + 1]
    if c[i0] > min(w15):
        return None                                   # 신저점 아님(이미 통과)
    return drop                                       # 제외 대상


def realized(c, i0):
    e = c[i0]
    end = min(i0 + HOLD, len(c))
    sold, rem, peak, t1, t2 = [], 1.0, e, False, False
    for k in range(i0 + 1, end):
        px = c[k]
        if px <= 0:
            continue
        if px <= e * 0.85:
            sold.append((rem, px / e - 1.0))
            rem = 0.0
            break
        peak = max(peak, px)
        if not t1 and px >= e * 1.20:
            sold.append((1 / 3, px / e - 1.0))
            rem -= 1 / 3
            t1 = True
        if not t2 and px >= e * 1.25:
            sold.append((1 / 3, px / e - 1.0))
            rem -= 1 / 3
            t2 = True
        if (t1 or t2) and rem > 0 and px <= peak * 0.95:
            sold.append((rem, px / e - 1.0))
            rem = 0.0
            break
    if rem > 0:
        sold.append((rem, c[end - 1] / e - 1.0))
    return sum(w * r for w, r in sold)


def w10(v):
    s = sorted(v)
    return st.median(s[:max(1, len(s) // 10)]) if v else None


GATES = [
    ("RS≥80", lambda f: f["rs"] is not None and f["rs"] >= 80),
    ("RS≥90", lambda f: f["rs"] is not None and f["rs"] >= 90),
    ("선행상승≥100%", lambda f: f["pu"] is not None and f["pu"] >= 100),
    ("선행상승≥150%", lambda f: f["pu"] is not None and f["pu"] >= 150),
    ("낙폭 −12~−30%(중간)", lambda f: -0.30 <= f["drop"] <= -0.12),
    ("RS≥90 & 선행상승≥100%",
     lambda f: f["rs"] is not None and f["rs"] >= 90
     and f["pu"] is not None and f["pu"] >= 100),
    ("RS≥80 & 낙폭−12~−30%",
     lambda f: f["rs"] is not None and f["rs"] >= 80
     and -0.30 <= f["drop"] <= -0.12),
]


def main():
    ex = []                          # 제외집합: (grp, feats)
    for win, ctl, pf in PAIRS:
        U = json.loads((CY / win / pf).read_text(encoding="utf-8"))
        for grp, p in (("W", win), ("L", ctl)):
            for r in rows(p):
                s = U.get(r["code"]) or {}
                d, c = s.get("d") or [], s.get("c") or []
                if r["pivot_date"] not in d:
                    continue
                i0 = d.index(r["pivot_date"])
                drop = excluded_cape(c, i0)
                if drop is None:
                    continue
                ex.append((grp, {"rs": num(r.get("rs_score")),
                                 "pu": num(r.get("prior_uptrend_pct")),
                                 "drop": drop, "ret": realized(c, i0)}))
    W = [f for g, f in ex if g == "W"]
    Lo = [f for g, f in ex if g == "L"]
    nW, nL = len(W), len(Lo)
    out = ["[신저점-케이프 구제 검정] 현 제외집합 안 로켓 살리기",
           f"제외집합: 위너(로켓) {nW} · 안오름(함정) {nL} · "
           f"기본 위너율 {100*nW//max(1,nW+nL)}%",
           f"제외집합 위너 평균실현 {sum(f['ret'] for f in W)/nW*100:+.0f}% "
           f"(이만큼이 현재 버려지는 상방)",
           "구제게이트 | 로켓회수%(제외위너중) | 함정재유입%(제외안오름중) "
           "| 구제집합 평균 | 최악10%",
           "-" * 72]
    for name, fn in GATES:
        rw = [f for f in W if fn(f)]
        rl = [f for f in Lo if fn(f)]
        rec = len(rw) / nW * 100 if nW else 0
        readm = len(rl) / nL * 100 if nL else 0
        allr = [f["ret"] for f in rw + rl]
        mean = sum(allr) / len(allr) * 100 if allr else 0
        wr = (w10(allr) or 0) * 100
        mark = " ★" if (rec >= 40 and mean > 0 and wr > -5) else ""
        out.append(f"{name:22s} | {rec:4.0f}% | {readm:4.0f}% | "
                   f"{mean:+6.1f}% | {wr:+6.1f}%{mark}")
    out += ["-" * 72,
            "판정: 로켓회수% 높고 함정재유입% 낮고 구제집합 최악10%가",
            "크게 안 나쁘면(★) → 그 게이트로 신저점-케이프 일부 구제 =",
            "트레이드오프 완화 가능. 다 회수율 낮거나 함정도 같이 들어",
            "오면(최악10% 급락) → 트레이드오프 견고(구제 어렵다, 정직).",
            "한계: 사후·종가·생존자(함정 실제 더 나쁨=구제 위험 과소)·",
            "보수가정·2사이클·rs/pu는 pivot값. 무릎/방향만."]
    fp = CY.parent / "_cape_rescue.txt"
    fp.write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fp} (제외위너 {nW} 안오름 {nL})", file=sys.stderr)


if __name__ == "__main__":
    main()

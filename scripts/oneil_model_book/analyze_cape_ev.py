"""케이프 포함/정교화/제외 — *실현 기대값* 시뮬레이션.

질문(사용자): 케이프형 제외(작은수익·손실최소)가 정말 더 이득인가?
지금까지 'lift/승률'만 봤고 +16%는 예시계산 → 실제 출구규칙 적용한
실현수익으로 못박는다.

모집단 = 위너+안오름(2 사이클). 진입 = pivot 종가(출발 프록시,
세 정책에 동일 적용이라 비교는 공정). 출구 = 우리 확정 규칙:
 ③ −15% 재해손절: 종가 ≤ 진입×0.85 → 남은 전량 그 종가 청산
 ⑤ 분기B(보수): +20%서 1/3·+25%서 1/3·잔여 1/3 고점대비 −5% 트레일
 (분기A 8주·★스위치 생략 → 위너 상방 *과소* = 보수적, 결론 강건화)
정책: A 케이프 제외 / B 전부 포함 / C 케이프는 정교화 통과만
 (정교화 = 최근15일 저점 ≥3거래일 전 AND 종가 ≥ 저점×1.03)
생존자 보정: 안오름 표본엔 상폐·대폭락 누락 → 채택 비위너에
 가상 상폐(−60%) 비율 φ∈{0,.1,.2} 더해 EV 경계.

정직: 사후·종가만(갭/장중 무시)·거래비용0·pivot=진입프록시·
2사이클·분기A/★ 생략(보수). 절대수치 아닌 정책 *순위*·방향.
사용: python analyze_cape_ev.py
"""
import json
import statistics as st
import sys
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
PAIRS = [("c2024-12", "c2024-12-ctrl500", "_universe_prices_5y.json", "2024-25"),
         ("c2020-03", "c2020-03-ctrl500", "_universe_prices.json", "2020-21")]
HOLD = 250


def rows(p):
    return [r for r in json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
            if not r.get("error") and r.get("pivot_date")]


def sma(c, i, w):
    return sum(c[i - w + 1:i + 1]) / w if i >= w - 1 else None


def setup(c, i0):
    if i0 < 60 or i0 >= len(c) or c[i0] <= 0:
        return None
    seg = c[i0 - 60:i0 + 1]
    hi = max(seg)
    hidx = max(range(i0 - 60, i0 + 1), key=lambda k: c[k])
    cape = (c[i0] / hi - 1.0 <= -0.12 and (i0 - hidx) > 5)
    w15 = c[i0 - 15:i0 + 1]
    lo = min(w15)
    lo_age = i0 - (i0 - 15 + w15.index(lo))
    refined = (lo_age >= 3 and lo > 0 and c[i0] / lo - 1.0 >= 0.03)
    return cape, refined


def realized(c, i0):
    """−15%손절 + ⑤분기B 보수 익절. 1자본, 1/3씩."""
    e = c[i0]
    end = min(i0 + HOLD, len(c))
    sold = []                       # 실현된 (비중, 수익률)
    rem = 1.0
    peak = e
    t1 = t2 = False
    for k in range(i0 + 1, end):
        px = c[k]
        if px <= 0:
            continue
        if px <= e * 0.85:                       # 재해손절: 남은 전량
            sold.append((rem, px / e - 1.0))
            rem = 0.0
            break
        peak = max(peak, px)
        if not t1 and px >= e * 1.20:            # +20% → 1/3
            sold.append((1 / 3, px / e - 1.0))
            rem -= 1 / 3
            t1 = True
        if not t2 and px >= e * 1.25:            # +25% → 1/3
            sold.append((1 / 3, px / e - 1.0))
            rem -= 1 / 3
            t2 = True
        if (t1 or t2) and rem > 0 and px <= peak * 0.95:   # 잔여 트레일
            sold.append((rem, px / e - 1.0))
            rem = 0.0
            break
    if rem > 0:                                   # 창 끝 → 마감가
        sold.append((rem, c[end - 1] / e - 1.0))
    return sum(w * r for w, r in sold)


def agg(vals):
    if not vals:
        return None
    n = len(vals)
    return {"n": n, "mean": sum(vals) / n, "med": st.median(vals),
            "win%": 100 * sum(1 for v in vals if v > 0) / n,
            "worst10%": st.median(sorted(vals)[:max(1, n // 10)])}


def main():
    # (그룹 W/L, cape, refined, 실현수익)
    rec = []
    for win, ctl, pf, _ in PAIRS:
        U = json.loads((CY / win / pf).read_text(encoding="utf-8"))
        for grp, p in (("W", win), ("L", ctl)):
            for r in rows(p):
                s = U.get(r["code"]) or {}
                d, c = s.get("d") or [], s.get("c") or []
                if r["pivot_date"] not in d:
                    continue
                i0 = d.index(r["pivot_date"])
                su = setup(c, i0)
                if su is None:
                    continue
                cape, refined = su
                rec.append((grp, cape, refined, realized(c, i0)))

    def policy(name, take):
        v = [x[3] for x in rec if take(x)]
        nonw = [x for x in rec if take(x) and x[0] == "L"]
        a = agg(v)
        line = (f"{name:18s} n={a['n']:4d} 평균 {a['mean']*100:+6.1f}% "
                f"중앙 {a['med']*100:+6.1f}% 승률 {a['win%']:4.0f}% "
                f"최악10% {a['worst10%']*100:+6.1f}%")
        # 생존자 보정: 채택 비위너의 φ배수만큼 가상상폐(−60%) 추가
        sens = []
        for phi in (0.10, 0.20):
            extra = [-0.60] * int(len(nonw) * phi)
            m = (sum(v) + sum(extra)) / (len(v) + len(extra)) if (v or extra) else 0
            sens.append(f"φ{int(phi*100)}%→평균 {m*100:+.1f}%")
        return line + "  | 생존자보정 " + " · ".join(sens)

    L = ["[케이프 EV] 포함/정교화/제외 — 실현수익(−15손절+⑤보수익절)",
         f"모집단 {len(rec)} (위너+안오름·2사이클) · 진입=pivot · 보유 {HOLD}td",
         "*사후·종가·무비용·분기A/★생략(보수)·pivot진입프록시*",
         "-" * 72,
         policy("A 케이프 제외", lambda x: not x[1]),
         policy("B 전부 포함", lambda x: True),
         policy("C 케이프=정교화만", lambda x: (not x[1]) or (x[1] and x[2])),
         "-" * 72,
         "(참고) 케이프 세부:",
         policy("  케이프 전체", lambda x: x[1]),
         policy("  케이프 정교화통과", lambda x: x[1] and x[2]),
         policy("  케이프 정교화탈락", lambda x: x[1] and not x[2]),
         "-" * 72,
         "해석: 평균/중앙 실현수익이 가장 높은 정책이 답. A(제외)가",
         "B·C보다 높으면 '케이프 빼는 게 이득' 사용자직관 지지. 낮으면",
         "기각(−15손절이 손실 막아 비대칭이 케이프 포함을 유리화).",
         "생존자보정 φ: 안 보이는 상폐를 채택비위너의 10·20%·−60%로",
         "가정해도 정책 순위가 유지되는지(강건성). 점추정 아님·경계용.",
         "한계: 분기A 8주·★스위치 생략으로 위너 상방 과소(보수)→케이프",
         "포함이 더 유리할 여지 큼. 절대수치 신뢰말고 *순위*만."]
    fp = CY.parent / "_cape_ev.txt"
    fp.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {fp} (n={len(rec)})", file=sys.stderr)


if __name__ == "__main__":
    main()

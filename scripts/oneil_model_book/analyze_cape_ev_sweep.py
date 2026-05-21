"""케이프 정교화 강도 스위프 — '상방 최대 보존 + 최악꼬리만 절단' 탐색.

사용자 의도: 큰 수익 우선, 단 그에 따르는 큰 리스크(상충)만 골라
잘라낸다. → 정교화 임계를 *느슨한 쪽부터* 훑어, 케이프 위너 보존이
높으면서 최악10% 실현이 뚜렷이 올라가는(꼬리 절단) '무릎' 설정 채택.

케이프형(직전60일고점 ≤−12% & 고점>5거래일전) 대상.
정교화 후보 = (신저점 ≥A거래일 전) AND (종가 ≥ 최근15일저점×(1+B)).
각 (A,B)에서: 통과 케이프 위너보존%·평균실현·최악10%실현,
탈락 케이프의 평균실현(버리는 게 진짜 나쁜지). 실현=−15손절+⑤보수.
정직: 사후·종가·생존자·보수가정. 순위/방향만.
사용: python analyze_cape_ev_sweep.py
"""
import json
import statistics as st
import sys
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
PAIRS = [("c2024-12", "c2024-12-ctrl500", "_universe_prices_5y.json"),
         ("c2020-03", "c2020-03-ctrl500", "_universe_prices.json")]
HOLD = 250
A_SET = [1, 2, 3]
B_SET = [0.0, 0.005, 0.01, 0.02, 0.03]


def rows(p):
    return [r for r in json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
            if not r.get("error") and r.get("pivot_date")]


def cape_feat(c, i0):
    if i0 < 60 or i0 >= len(c) or c[i0] <= 0:
        return None
    seg = c[i0 - 60:i0 + 1]
    hi = max(seg)
    hidx = max(range(i0 - 60, i0 + 1), key=lambda k: c[k])
    if not (c[i0] / hi - 1.0 <= -0.12 and (i0 - hidx) > 5):
        return None                                   # 케이프 아님
    w15 = c[i0 - 15:i0 + 1]
    lo = min(w15)
    lo_age = i0 - (i0 - 15 + w15.index(lo))
    bounce = c[i0] / lo - 1.0 if lo > 0 else -1.0
    return lo_age, bounce


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


def worst10(v):
    s = sorted(v)
    return st.median(s[:max(1, len(s) // 10)]) if v else None


def main():
    capes = []                  # (grp, lo_age, bounce, realized)
    for win, ctl, pf in PAIRS:
        U = json.loads((CY / win / pf).read_text(encoding="utf-8"))
        for grp, p in (("W", win), ("L", ctl)):
            for r in rows(p):
                s = U.get(r["code"]) or {}
                d, c = s.get("d") or [], s.get("c") or []
                if r["pivot_date"] not in d:
                    continue
                i0 = d.index(r["pivot_date"])
                cf = cape_feat(c, i0)
                if cf is None:
                    continue
                capes.append((grp, cf[0], cf[1], realized(c, i0)))
    capeW = [x for x in capes if x[0] == "W"]
    nWcape = len(capeW)
    base_w10 = worst10([x[3] for x in capes])
    L = ["[케이프 정교화 스위프] 상방보존↑ + 최악꼬리↑ 무릎 찾기",
         f"케이프 모집단 {len(capes)} (위너 {nWcape}) · 무정교화 최악10% "
         f"{base_w10*100:+.1f}%",
         "A=신저점 ≥A거래일전 · B=종가≥저점×(1+B)",
         "A  B    | 위너보존% | 통과평균 | 통과최악10% | (탈락평균) | 통과n",
         "-" * 70]
    best = None
    for A in A_SET:
        for B in B_SET:
            pas = [x for x in capes if x[1] >= A and x[2] >= B]
            rej = [x for x in capes if not (x[1] >= A and x[2] >= B)]
            pw = [x for x in pas if x[0] == "W"]
            keep = len(pw) / nWcape * 100 if nWcape else 0
            pm = sum(x[3] for x in pas) / len(pas) if pas else 0
            pw10 = worst10([x[3] for x in pas])
            rm = sum(x[3] for x in rej) / len(rej) if rej else 0
            L.append(f"{A}  {B:<5.3f}| {keep:5.0f}% | {pm*100:+6.1f}% | "
                     f"{(pw10 or 0)*100:+7.1f}% | {rm*100:+7.1f}% | {len(pas):4d}")
            # 무릎 후보: 위너보존 최대화하되 최악10%가 무정교화 대비 +8%p↑
            if pw10 is not None and pw10 - base_w10 >= 0.08:
                score = keep
                if best is None or score > best[0]:
                    best = (score, A, B, keep, pm, pw10)
    L += ["-" * 70]
    if best:
        _, A, B, keep, pm, pw10 = best
        L.append(f"★ 추천(무릎): A={A} 거래일 · B={B:.3f}({B*100:.1f}%) — "
                 f"위너보존 {keep:.0f}%·통과평균 {pm*100:+.1f}%·"
                 f"최악10% {pw10*100:+.1f}%")
        L.append("기준: 최악10%를 무정교화 대비 +8%p↑(꼬리 절단) 하는 것들 중")
        L.append("      *위너 보존 최대*(상방 우선) 설정 — 사용자 의도 그대로.")
    else:
        L.append("★ +8%p 꼬리절단 만족 설정 없음 — 임계/기준 재검토 필요")
    L += ["해석: 탈락평균이 통과평균보다 낮을수록 '버리는 게 진짜 나쁜",
          "케이프'(상방손해 적음). 한계: 사후·종가·생존자·보수(분기A/★",
          "생략)·2사이클. 절대수치 아닌 무릎/순위만."]
    fp = CY.parent / "_cape_ev_sweep.txt"
    fp.write_text("\n".join(L), encoding="utf-8")
    msg = f"saved: {fp}"
    if best:
        msg += f" (추천 A={best[1]} B={best[2]})"
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()

"""분할매수 vs 일괄매수 — 신호 진입 후 사후 수익성 비교 (c2024-12).

모집단 = 위너200 + 안오름500 (신호가 실제로 잡는 현실 혼합).
신호일 = 각 종목 pivot_date. 종가 시세 = _universe_prices_5y.json.
1 단위 자본, 동일가중. 평단=트랜치가 평균. 수익 = 평가가/평단 − 1.

전략:
 LUMP        신호일 100%
 SPLIT_D     1/3 신호일·+1·+2 거래일 (하루단위)
 SPLIT_W     1/3 신호일·+5·+10 거래일 (주단위)
 SPLIT_DIP   1/3 신호일; 이후 트랜치는 평단 대비 −DIP% 하회 시 매수,
             창 W 내 안 빠지면 창 끝에 강제 매수 ("조금 빠지면 더 산다")

평가 = 신호일+H 거래일 종가(H=60) · 그리고 [신호일,+120] 최고종가(피크).
요일별·월요일 여부도 집계(LUMP 기준 — '월요일 매수 회피' 사후 점검).

정직: 종가 only → *오전장/세션 회피는 검정 불가*(명시). 생존자(상폐
제외 → 하락 과소·분할 방어가치 과소). 단일 사이클·거래비용/세금 미반영
(분할은 수수료↑). pivot=신호 프록시·H 임의(2지표 병기).
사용: python analyze_split_vs_lump.py
"""
import json
import argparse
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
H, PEAKW, DIP, DIPW = 60, 120, 0.05, 10
U = {}                       # main()에서 사이클별 로드


def rows(p):
    return [r for r in json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
            if not r.get("error") and r.get("pivot_date") and r.get("code") in U]


def series(code):
    s = U[code]
    return s.get("d") or [], s.get("c") or []


def avg(prices):
    return sum(prices) / len(prices) if prices else None


def strat_costs(d, c, i0):
    """각 전략의 평단. 끝 인덱스 부족하면 None."""
    n = len(c)
    out = {}
    out["LUMP"] = c[i0]
    if i0 + 2 < n:
        out["SPLIT_D"] = avg([c[i0], c[i0 + 1], c[i0 + 2]])
    if i0 + 10 < n:
        out["SPLIT_W"] = avg([c[i0], c[i0 + 5], c[i0 + 10]])
    # SPLIT_DIP
    px = [c[i0]]
    cur = i0
    ok = True
    for _ in range(2):
        ac = avg(px)
        nxt = None
        for j in range(cur + 1, min(cur + 1 + DIPW, n)):
            if c[j] <= ac * (1 - DIP):
                nxt = j
                break
        if nxt is None:
            nxt = cur + DIPW
        if nxt >= n:
            ok = False
            break
        px.append(c[nxt])
        cur = nxt
    out["SPLIT_DIP"] = avg(px) if ok and len(px) == 3 else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", default="c2024-12", help="위너 사이클 디렉터리")
    ap.add_argument("--ctl", default="c2024-12-ctrl500", help="안오름 디렉터리")
    ap.add_argument("--prices", default="c2024-12/_universe_prices_5y.json",
                    help="유니버스 종가 파일(사이클 상대경로)")
    ap.add_argument("--tag", default="", help="출력 파일 태그(_split_vs_lump<tag>)")
    a = ap.parse_args()
    global U
    U = json.loads((CY / a.prices).read_text(encoding="utf-8"))
    pop = [("위너", r) for r in rows(a.win)] + \
          [("안오름", r) for r in rows(a.ctl)]
    # 전략별·그룹별 수익 누적
    res = {}      # (grp,strat,metric) -> list
    wkd = {}      # weekday -> list of LUMP H-return (전체)
    mon = {"월요일": [], "그외": []}
    for grp, r in pop:
        code = r["code"]
        d, c = series(code)
        if r["pivot_date"] not in d:
            continue
        i0 = d.index(r["pivot_date"])
        if i0 + H >= len(c) or c[i0] <= 0:
            continue
        costs = strat_costs(d, c, i0)
        evalH = c[i0 + H]
        peak = max(c[i0:min(i0 + PEAKW, len(c))])
        for sname, ac in costs.items():
            if not ac or ac <= 0:
                continue
            res.setdefault((grp, sname, "H60"), []).append(evalH / ac - 1)
            res.setdefault((grp, sname, "PEAK"), []).append(peak / ac - 1)
            res.setdefault(("혼합", sname, "H60"), []).append(evalH / ac - 1)
            res.setdefault(("혼합", sname, "PEAK"), []).append(peak / ac - 1)
        # 요일(LUMP H60)
        try:
            w = datetime.strptime(r["pivot_date"], "%Y-%m-%d").weekday()
        except ValueError:
            w = None
        if w is not None and "LUMP" in costs:
            ret = evalH / costs["LUMP"] - 1
            wkd.setdefault(w, []).append(ret)
            (mon["월요일"] if w == 0 else mon["그외"]).append(ret)

    def med(x):
        return st.median(x) if x else None

    L = [f"[분할 vs 일괄] {a.win} 위너 vs {a.ctl} 안오름 · 신호일=pivot",
         f"평가: H={H}td 종가수익 / PEAK=+{PEAKW}td내 최고. 중앙값(%).",
         "*확률·사후·종가only·생존자·무비용. 절대수치 아닌 순위.*",
         "-" * 60]
    for grp in ("위너", "안오름", "혼합"):
        L.append(f"■ {grp}")
        for sname in ("LUMP", "SPLIT_D", "SPLIT_W", "SPLIT_DIP"):
            h = res.get((grp, sname, "H60"), [])
            pk = res.get((grp, sname, "PEAK"), [])
            mh, mp = med(h), med(pk)
            L.append(f"   {sname:9s}: H60 중앙 "
                     f"{'결손' if mh is None else f'{mh*100:+.1f}%'} (n{len(h)}) | "
                     f"PEAK 중앙 {'결손' if mp is None else f'{mp*100:+.1f}%'}")
    L += ["-" * 60, "■ 요일 효과 (LUMP, H60 중앙값)"]
    days = ["월", "화", "수", "목", "금"]
    for w in range(5):
        v = wkd.get(w, [])
        L.append(f"   {days[w]}요일: {'결손' if not v else f'{med(v)*100:+.1f}%'} (n{len(v)})")
    L.append(f"   → 월요일 {med(mon['월요일'])*100:+.1f}% (n{len(mon['월요일'])}) vs "
             f"그외 {med(mon['그외'])*100:+.1f}% (n{len(mon['그외'])})")
    L += ["-" * 60,
          "해석 가이드:",
          "- '혼합'이 신호가 실제 잡는 현실 모집단의 답. 위너만 보면",
          "  주가가 오르니 LUMP가 당연히 유리(생존자 착시) — 분할의",
          "  진짜 가치는 안오름·하락 종목의 손실 완화에 있음.",
          "- SPLIT_DIP가 LUMP보다 평단 낮추면 '눌림 매수'가 사후 유효.",
          "- 월요일<그외면 '월요일 매수 회피' 사후 지지(인과 아님).",
          "정직한 한계: 종가 only → **오전장/장중 세션 회피는 본 데이터로",
          "검정 불가**(추정 안 함). 생존자(상폐 제외)로 하락·분할 방어",
          "가치 과소. 단일 사이클·거래비용/세금 미반영(분할 수수료↑).",
          "pivot=신호 프록시. H·DIP·창 파라미터 임의(민감도 차기)."]
    out = CY.parent / f"_split_vs_lump{a.tag}.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()

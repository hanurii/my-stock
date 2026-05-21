"""대체 선별게이트 검증 — '늦지 않게 켜지면서 성공확률 높은' 게이트 탐색.

목표 재정의(사용자 2026-05-17): 저점 최저가가 아니라 *성공확률 높은
종목을 정확·확실하게* 매수. → 1순위 지표 = **정밀도/lift(성공확률)** +
**진입 신뢰성**(−8% 손절 안 맞고 +50% 도달 비율). earliness/gap = 부차.

가설 3종(모두 사이클저점 이후 *첫 추세확인일* 게이트 통과 시 진입):
  T   : 타이밍 단독 (참조, 무선별)
  L80 : RS≥80 + M 상승        (§8 기준선)
  L50 : RS≥50 + M             (#2 완만한 L 밴드)
  LUP : RS 상승전환(now≥60거래일전 & ≥50) + M   (#3 L을 추세전환으로)
전 종목(2637) close-only 유니버스 → 대조군 내장. I(#1)는 별도 블록:
위너200 vs 비위너대조군100 model_book(fgn/inst_net_60d) enrichment
(pivot 시점값 — 조기 아님 캐비엇 명시), I·I+L50 동시.

한계: 사이클내 사후·상폐제외·인-샘플(앞 검증과 동일 잣대). I 블록은
pivot 시점(조기 아님) — 방향 추정용. 환각 금지·결손 명시.

사용:  python analyze_alt_gates.py
"""
import bisect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from analyze_gated_timing import idx_uptrend_by_date, confirmed  # noqa: E402

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles" / "c2024-12"
CTRL = CY.parent / "c2024-12-ctrl"
ANCHOR = "2024-12-09"
MIN_FWD = 20
THR = [50, 100, 200]


def nidx(d, ds):
    cand = [k for k in range(len(d)) if d[k] <= ds]
    return cand[-1] if cand else None


def main():
    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    win = {x["code"] for x in wf["winners"]}
    ks = idx_uptrend_by_date("%5EKS11")
    kq = idx_uptrend_by_date("%5EKQ11")
    w = json.loads((CY / "winners.json").read_text(encoding="utf-8"))
    nmkt = {r["code"]: r["market"] for r in w["ranked_valid"]}

    # 주봉 그리드: 각 날짜별 전 종목 252d수익률 *정렬배열* (백분위 산출용)
    any_d = U[list(U)[0]]["d"]
    grid = list(range(252, len(any_d), 5))
    sortmap = {}
    for gi in grid:
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
        arr = sortmap[cand[-1]]
        return 100 * bisect.bisect_left(arr, ret) / max(1, len(arr) - 1) if arr else None

    GATES = ["T", "L80", "L50", "LUP"]
    fired = {g: [] for g in GATES}      # (code, fwd_max%, reliable_bool)
    fcodes = {g: set() for g in GATES}
    earl = {g: [] for g in GATES}       # (trough→gate days, % above trough)
    valid = 0
    base_movers = {t: 0 for t in THR}

    for code, s in U.items():
        d, c = s.get("d"), s.get("c")
        if not d or not c or len(c) < 320:
            continue
        ai = next((k for k in range(len(d)) if d[k] >= ANCHOR), None)
        if ai is None or len(c) - ai < 80:
            continue
        valid += 1
        ti = min(range(ai, len(c)), key=lambda k: c[k])
        if c[ti] > 0:
            bm = max(c[ti:]) / c[ti] - 1
            for t in THR:
                if bm * 100 >= t:
                    base_movers[t] += 1
        reg = ks if nmkt.get(code, "KOSDAQ") == "KOSPI" else kq

        done = set()
        for x in range(max(ti, 312), len(c) - MIN_FWD):
            if c[x - 252] <= 0 or not confirmed(c, x):
                continue
            M_ok = bool(reg.get(d[x], False))
            rp = rs_pct(c[x] / c[x - 252] - 1, d[x])
            rp_prev = (rs_pct(c[x - 60] / c[x - 312] - 1, d[x - 60])
                       if c[x - 312] > 0 else None)
            cond = {
                "T": True,
                "L80": M_ok and rp is not None and rp >= 80,
                "L50": M_ok and rp is not None and rp >= 50,
                "LUP": (M_ok and rp is not None and rp >= 50
                        and rp_prev is not None and rp >= rp_prev),
            }
            for g in GATES:
                if g in done or not cond[g]:
                    continue
                done.add(g)
                fwd = (max(c[x:]) / c[x] - 1) * 100
                # 신뢰성: +50% 먼저 도달 vs −8% 먼저 이탈
                reliable = None
                for k in range(x + 1, len(c)):
                    if c[k] <= c[x] * 0.92:
                        reliable = False
                        break
                    if c[k] >= c[x] * 1.50:
                        reliable = True
                        break
                fired[g].append((code, fwd, reliable))
                fcodes[g].add(code)
                earl[g].append((x - ti, (c[x] / c[ti] - 1) * 100))
            if len(done) == len(GATES):
                break

    def pctge(xs, t):
        return 100 * sum(1 for x in xs if x >= t) / len(xs) if xs else 0

    def med(xs):
        xs = sorted(x for x in xs if isinstance(x, (int, float)))
        return round(xs[len(xs) // 2], 1) if xs else None

    L = [f"[c2024-12] 대체 선별게이트 — 성공확률·진입신뢰성 (전종목 {valid})",
         "목표: 저점최저가 아닌 '성공확률↑ 종목을 정확·확실히'. 1순위=정밀도/",
         "신뢰성. 진입=사이클저점후 첫 추세확인일에 게이트 통과 시.",
         "신뢰성=진입 후 −8% 손절 전에 +50% 먼저 도달한 비율.",
         "",
         "게이트 | 발동률 | 정밀@+100 | lift@100 | 신뢰성(+50先) | "
         "위너recall | 위너비중 | 저점→발동중앙(일) | 저점대비중앙%",
         "-" * 30]
    base100 = 100 * base_movers[100] / valid if valid else 0
    for g in GATES:
        fr = fired[g]
        fv = [x[1] for x in fr]
        rel = [x[2] for x in fr if x[2] is not None]
        wn = len(fcodes[g] & win)
        L.append(
            f"{g} | {round(100*len(fr)/valid,1)}% | "
            f"{round(pctge(fv,100),1)}% | "
            f"{round(pctge(fv,100)/base100,2) if base100 else '-'}x | "
            f"{round(100*sum(1 for r in rel if r)/len(rel),1) if rel else 0}% "
            f"(n{len(rel)}) | {wn}/{len(win)} | "
            f"{round(100*wn/len(fr),1) if fr else 0}% | "
            f"{med([e[0] for e in earl[g]])} | "
            f"{med([e[1] for e in earl[g]])}%")
    L += [f"(기저율 ≥+100%: {round(base100,1)}%)", ""]

    # ── #1 I 게이트: 위너200 vs 비위너대조군100 model_book (pivot 시점) ──
    def rows(p):
        f = p / "model_book.json"
        return json.loads(f.read_text(encoding="utf-8"))["rows"] if f.exists() else []
    W, C = rows(CY), rows(CTRL)
    L += ["== #1 I(외인 or 기관 60일 순매수) 변별력 — 위너 vs 비위너대조군 ==",
          f"(model_book pivot 시점값 — *조기 아님*, 방향 추정용. 위너 {len(W)} "
          f"/ 대조군 {len(C)})"]
    if W and C:
        def rate(rs, fn):
            v = [fn(r) for r in rs]
            v = [x for x in v if x is not None]
            return (sum(1 for x in v if x) / len(v) if v else None), len(v)

        def gI(r):
            fg, ins = r.get("fgn_net_60d"), r.get("inst_net_60d")
            return None if fg is None and ins is None else ((fg or 0) > 0 or (ins or 0) > 0)

        def gL50(r):
            v = r.get("rs_score")
            return (v >= 50) if isinstance(v, (int, float)) else None

        def gIL(r):
            a, b = gI(r), gL50(r)
            return None if a is None or b is None else (a and b)
        for nm, fn in (("I 단독", gI), ("L50 단독", gL50), ("I+L50", gIL)):
            pw, nw = rate(W, fn)
            pc, nc = rate(C, fn)
            if pw is None or pc is None:
                L.append(f"{nm} | 결손")
                continue
            lift = pw / pc if pc else float("inf")
            L.append(f"{nm} | 위너 {round(pw*100,1)}% vs 대조 {round(pc*100,1)}% "
                     f"| enrich {('inf' if lift==float('inf') else round(lift,2))}x "
                     f"(n {nw}/{nc})")
    L += ["",
          "== 해석 가이드 ==",
          "정밀@+100>기저(lift>1) & 신뢰성 높을수록 '성공확률+확실성' 우수.",
          "발동률 너무 높으면(≈T) 무선별. 저점대비% 작을수록 조기(부차).",
          "== 한계 ==",
          "사이클내 사후·상폐제외·인-샘플(§5/§8/§9 동일잣대). I블록은 pivot",
          "시점(조기 아님)→방향만. 결손 비임퓨트. 실거래수익 보장 아님.",
          ]
    block = "\n".join(L)
    (CY / "_alt_gates.txt").write_text(block, encoding="utf-8")
    print(f"alt-gates saved: {CY/'_alt_gates.txt'} (valid {valid})",
          file=sys.stderr)


if __name__ == "__main__":
    main()

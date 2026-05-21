"""사는 신호(#1) × 파는 기준(#2) 동시 검증 — 목표: 성공확률↑·확실성↑.

선별집합 = 사이클저점 이후 'RS 백분위≥50 + 시장 상승'(L50+M)이 켜진 종목.
 (I=외인/기관은 전종목 frgn 과중→이 실험선 제외, 한계 명시. L50 단독도
  위너 대조 2.16x 유효 — analyze_alt_gates 참조. I층은 후속 표본조사.)

#1 사는 신호(선별 켜진 뒤 첫 해당일에 진입):
  E0 추세 막 살아날 때 = 선별 켜진 그날(기준선)
  E1 눌렸다 다시 오를 때 = 선별 후 고점서 ≥10% 눌린 뒤 그 고점 회복일
  E2 50일평균선 지지 후 반등 = 50일평균 근처(±3%)서 다음날 반등·평균 위
  E3 조용하다 터질 때 = 최근 10일 변동 축소 후 10일 고점 돌파일

#2 파는 기준: 진입가 대비 −8% / −12% / −15% / −20% / 안 팜.
지표: 진입 후 *손절에 먼저 안 닿고* +50%(또는 +100%) 도달 비율(=확실성),
정밀도@+100 및 기저 대비 배수, 위너 적중, 저점→진입 지각(부차).

전 종목(대조군 내장)·close-only·사이클내 사후·인-샘플·상폐제외. 환각 금지.
사용:  python analyze_entry_stop.py
"""
import bisect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from analyze_gated_timing import idx_uptrend_by_date  # noqa: E402

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles" / "c2024-12"
ANCHOR = "2024-12-09"
STOPS = [0.08, 0.12, 0.15, 0.20, None]
TARGETS = [0.50, 1.00]


def nidx(d, ds):
    cand = [k for k in range(len(d)) if d[k] <= ds]
    return cand[-1] if cand else None


def ma(c, x, w):
    return sum(c[x - w + 1:x + 1]) / w if x >= w - 1 else None


def main():
    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    win = {x["code"] for x in wf["winners"]}
    w = json.loads((CY / "winners.json").read_text(encoding="utf-8"))
    nmkt = {r["code"]: r["market"] for r in w["ranked_valid"]}
    ks = idx_uptrend_by_date("%5EKS11")
    kq = idx_uptrend_by_date("%5EKQ11")

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
        a = sortmap[cand[-1]]
        return 100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1) if a else None

    ENTRIES = ["E0", "E1", "E2", "E3"]
    # per entry: list of (code, entry_idx, c, peak_idx_for_fwd)
    picks = {e: [] for e in ENTRIES}
    valid = 0
    base_movers = {int(t * 100): 0 for t in TARGETS}
    base_100 = 0

    for code, s in U.items():
        d, c = s.get("d"), s.get("c")
        if not d or not c or len(c) < 340:
            continue
        ai = next((k for k in range(len(d)) if d[k] >= ANCHOR), None)
        if ai is None or len(c) - ai < 80:
            continue
        valid += 1
        ti = min(range(ai, len(c)), key=lambda k: c[k])
        if c[ti] > 0:
            bm = max(c[ti:]) / c[ti] - 1
            for t in TARGETS:
                if bm >= t:
                    base_movers[int(t * 100)] += 1
            if bm >= 1.0:
                base_100 += 1
        reg = ks if nmkt.get(code, "KOSDAQ") == "KOSPI" else kq

        # 선별(L50+M) 최초 켜진 날
        sel = None
        for x in range(max(ti, 312), len(c) - 20):
            if c[x - 252] <= 0:
                continue
            if reg.get(d[x], False) and (rs_pct(c[x] / c[x - 252] - 1, d[x]) or 0) >= 50:
                sel = x
                break
        if sel is None:
            continue

        # E0 = sel 그날
        ent = {"E0": sel}
        # E1 눌림목 후 회복: sel 이후 진행고점 rp, ≥10% 눌린 뒤 rp 회복
        rp = c[sel]
        pulled = False
        for x in range(sel + 1, len(c) - 20):
            if c[x] > rp:
                rp = c[x]
            if c[x] <= rp * 0.90:
                pulled = True
            if pulled and c[x] >= rp:
                ent["E1"] = x
                break
        # E2 50일평균 지지 후 반등
        for x in range(sel + 1, len(c) - 20):
            m = ma(c, x, 50)
            if m and m * 0.97 <= c[x - 1] <= m * 1.03 and c[x] > c[x - 1] and c[x] > m:
                ent["E2"] = x
                break
        # E3 변동성 축소 후 확장
        for x in range(sel + 20, len(c) - 20):
            w10 = c[x - 10:x]
            w50 = c[x - 50:x - 10]
            if len(w10) < 10 or len(w50) < 20:
                continue
            cv10 = (max(w10) - min(w10)) / (sum(w10) / len(w10))
            cv50 = (max(w50) - min(w50)) / (sum(w50) / len(w50))
            if cv10 < 0.6 * cv50 and c[x] > max(c[x - 10:x]):
                ent["E3"] = x
                break

        for e, ei in ent.items():
            picks[e].append((code, ei, code in win,
                             (c[ei] / c[ti] - 1) * 100, ei - ti))

    def sim(code_ei, U, stop, target):
        ok = 0
        tot = 0
        for code, ei, _, _, _ in code_ei:
            c = U[code]["c"]
            tot += 1
            hit = False
            for k in range(ei + 1, len(c)):
                if stop is not None and c[k] <= c[ei] * (1 - stop):
                    break
                if c[k] >= c[ei] * (1 + target):
                    hit = True
                    break
            ok += hit
        return 100 * ok / tot if tot else 0

    def fwdmax(code_ei, U):
        v = []
        for code, ei, _, _, _ in code_ei:
            c = U[code]["c"]
            v.append((max(c[ei:]) / c[ei] - 1) * 100)
        return v

    def med(xs):
        xs = sorted(xs)
        return round(xs[len(xs) // 2], 1) if xs else None

    b100 = 100 * base_100 / valid if valid else 0
    L = [f"[c2024-12] 사는신호×파는기준 — 성공확률·확실성 (전종목 {valid})",
         "선별집합=저점후 'RS≥50 + 시장상승' 켜진 종목(I 제외-한계). 진입="
         "선별 후 각 신호 최초일. 기저율 ≥+100%: " f"{round(b100,1)}%",
         "",
         "사는신호 | 종목수 | 정밀@+100 | lift | 위너적중 | 위너비중 | "
         "저점→진입중앙(일) | 저점대비중앙%",
         "-" * 20]
    desc = {"E0": "추세 막 살아날때", "E1": "눌렸다 다시오를때",
            "E2": "50일선 지지반등", "E3": "조용하다 터질때"}
    for e in ENTRIES:
        p = picks[e]
        fv = fwdmax(p, U)
        pr = 100 * sum(1 for x in fv if x >= 100) / len(fv) if fv else 0
        wn = sum(1 for x in p if x[2])
        L.append(
            f"{e} {desc[e]} | {len(p)} | {round(pr,1)}% | "
            f"{round(pr/b100,2) if b100 else '-'}x | {wn}/{len(win)} | "
            f"{round(100*wn/len(p),1) if p else 0}% | "
            f"{med([x[4] for x in p])} | {med([x[3] for x in p])}%")
    L += ["",
          "확실성 = 진입 후 손절에 *먼저 안 닿고* 목표 도달 비율(%)",
          ""]
    for tg in TARGETS:
        L.append(f"-- 목표 +{int(tg*100)}% 까지 안 팔리고 도달 비율 --")
        L.append("사는신호 | " + " | ".join(
            (f"손절{int(s*100)}%" if s else "안팜") for s in STOPS))
        for e in ENTRIES:
            p = picks[e]
            L.append(f"{e} | " + " | ".join(
                f"{round(sim(p,U,s,tg),1)}%" for s in STOPS))
        L.append("")
    L += ["== 해석 ==",
          "정밀@+100>기저(lift>1)=성공확률↑. 확실성%↑ & 손절 넓힐수록 개선",
          "폭 크면 '진입은 됐는데 8%가 너무 빡빡'이 원인. 저점대비%는 부차.",
          "== 한계 ==",
          "I(외인/기관) 제외(전종목 frgn 과중)=L50 단독 선별(위너대조 2.16x).",
          "close-only·사이클내 사후·인-샘플·상폐제외. 실거래수익 보장 아님.",
          ]
    block = "\n".join(L)
    (CY / "_entry_stop.txt").write_text(block, encoding="utf-8")
    print(f"entry-stop saved: {CY/'_entry_stop.txt'} (valid {valid})",
          file=sys.stderr)


if __name__ == "__main__":
    main()

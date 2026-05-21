"""2020-21 교차검증 2단계 — I(외국인/기관) 선별축 홀드아웃 검증.

1단계서 매수신호 구조·출구가 c2024-12와 동형 재현 확인. 2단계는
'무엇을(선별)' = c2024-12서 I+L50(RS) enrichment 2.89x였던 게
c2020-03 홀드아웃서도 위너를 비위너서 가려내나.

위너(winners_final) vs 비위너(ranked_valid raw_multiple<1.5=깨끗한
안오름) 각 표본. 평가점 = 인과(저점 후 첫 종가>20일선). 그 시점:
  I  외인 or 기관 60일 순매수>0 (네이버 frgn deep, 2019까지 pages~95)
  L  RS 백분위≥50 (표본 횡단 근사)
  enrichment = 위너통과율 / 비위너통과율 (>1=위너 농축=선별력)

OMB_CYCLE=c2020-03. 시세 cyclecfg.yahoo. 홀드아웃·상폐제외·종가·
RS근사·표본. 환각 금지·결손 비임퓨트.
사용: OMB_CYCLE=c2020-03 python analyze_xcycle2020_p2.py [--n 60] [--seed 7]
"""
import argparse
import bisect
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.fetch import yahoo_symbol  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

DIR = cyclecfg.DIR
FRGN_PAGES = 82          # ≈ 2020까지(2020-03 진입 60일창 +여유). 1p≈20거래일.
RS_EXTRA = 80            # RS 근사 횡단 추가표본(적정선)


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
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    w = json.loads((DIR / "winners.json").read_text(encoding="utf-8"))
    rv = w["ranked_valid"]
    wf = json.loads((DIR / "winners_final.json").read_text(encoding="utf-8"))
    wins = wf["winners"]
    wc = {x["code"] for x in wins}

    def ok(r):
        return (not r.get("exclude_reason") and r.get("trough_date")
                and r.get("n_days", 0) >= 60 and r.get("raw_multiple"))
    ctrl_pool = [r for r in rv if r["code"] not in wc and ok(r)
                 and r["raw_multiple"] < 1.5]      # 깨끗한 '안 오름'
    random.seed(args.seed)
    W = random.sample(wins, min(args.n, len(wins)))
    C = random.sample(ctrl_pool, min(args.n, len(ctrl_pool)))

    # RS 근사: W∪C + 추가 표본 횡단
    extra = random.sample([r for r in rv if ok(r)],
                          min(RS_EXTRA, len(rv)))
    need = {r["code"]: r for r in (W + C + extra)}
    SER = {}
    for code, r in need.items():
        ch = cyclecfg.yahoo(yahoo_symbol(code, r["market"]))
        if not ch or not ch.get("closes"):
            continue
        ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
              for t in ch["timestamps"]]
        SER[code] = (ts, ch["closes"], r)
    anyd = next(iter(SER.values()))[0] if SER else []
    sortmap = {}
    for gi in range(252, len(anyd), 5):
        gd = anyd[gi]
        arr = []
        for ts, c, _ in SER.values():
            j = nidx(ts, gd)
            if j is None or j < 252 or c[j - 252] <= 0:
                continue
            arr.append(c[j] / c[j - 252] - 1)
        arr.sort()
        sortmap[gd] = arr
    gk = sorted(sortmap)

    def rs_pct(ret, ds):
        i = bisect.bisect_right(gk, ds) - 1
        if i < 0:
            return None
        a = sortmap[gk[i]]
        return 100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1) if a else None

    def evaluate(group):
        """각 종목 인과 평가점서 I·L·I+L 통과 여부."""
        I = L = IL = nI = nL = 0
        for r in group:
            S = SER.get(r["code"])
            if not S:
                continue
            ts, c, _ = S
            n = len(c)
            ti = nidx(ts, r["trough_date"]) or 0
            e = causal_entry(c, ti, n)
            if e is None or e < 252 or c[e - 252] <= 0:
                continue
            T = ts[e]
            rp = rs_pct(c[e] / c[e - 252] - 1, T)
            l_ok = (rp is not None and rp >= 50)
            try:
                fr = fetch_naver_org_flow(r["code"], pages=FRGN_PAGES,
                                          sleep_ms=130)
            except Exception:
                fr = []
            sel = [x for x in sorted(fr, key=lambda z: z["date"])
                   if x["date"] <= T][-60:]
            if len(sel) >= 30:
                i_ok = (sum(x.get("fgn_net") or 0 for x in sel) > 0
                        or sum(x.get("org_net") or 0 for x in sel) > 0)
                nI += 1
                I += 1 if i_ok else 0
                if l_ok is not None:
                    nL += 1
                    L += 1 if l_ok else 0
                    IL += 1 if (i_ok and l_ok) else 0
        return {"I": (I, nI), "L": (L, nL), "IL": (IL, nL)}

    ew, ec = evaluate(W), evaluate(C)
    out = [f"[홀드아웃] c2020-03 교차검증 2단계 — I(외국인/기관) 선별축",
           f"(위너 {len(W)} vs 깨끗한 비위너 {len(C)}, frgn pages {FRGN_PAGES}"
           f"≈2019, RS근사 표본 {len(SER)}, seed {args.seed})",
           "평가점=인과(저점후 첫 종가>20일선). enrichment=위너통과/비위너통과.",
           "비교(c2024-12): I 1.41x · L50 2.16x · I+L50 2.89x",
           "",
           "축 | 위너통과 | 비위너통과 | enrichment"]
    for k, nm in (("I", "I 외인or기관 60일순매수"),
                  ("L", "L RS≥50(근사)"), ("IL", "I+L 결합")):
        aw, nw = ew[k]
        ac, nc = ec[k]
        pw = aw / nw if nw else None
        pc = ac / nc if nc else None
        en = (pw / pc) if (pw is not None and pc) else None
        out.append(
            f"{nm} | {round(100*pw,1) if pw is not None else '-'}% "
            f"({aw}/{nw}) | {round(100*pc,1) if pc is not None else '-'}% "
            f"({ac}/{nc}) | "
            f"{('inf' if en==float('inf') else round(en,2)) if en is not None else '결손'}x")
    out += ["",
            "== 해석 ==",
            "enrichment>1 & c2024-12와 같은 순서(I+L>L>I 대략)면 '선별축'이",
            "홀드아웃서 재현 = 무엇을(선별) 결론도 동력 무관. 1<이면 약세.",
            "절대값은 RS근사·표본 60·평가점(pivot 아닌 인과진입) 영향.",
            "== 한계 ==",
            "RS 표본 횡단 근사·표본 60/그룹(노이즈)·평가점=인과진입(원래",
            "selection_lift는 pivot)·frgn deep 결손분 비임퓨트·상폐제외·종가."]
    fn = DIR / f"_xcycle2020_p2_s{args.seed}.txt"
    fn.write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()

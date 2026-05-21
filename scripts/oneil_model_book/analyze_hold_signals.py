"""보유 신호 재설계 — 트레일링 매도가 떠도 '아직 살아있으면' 더 들고 가기.

이전 HOLD_OVL(상승50일선+신고가 보류)는 효과 0 → 재설계. 한국 위너는
큰 흐름 중 −20~40% 흔들기 흔함 → *건강한 흔들기 vs 진짜 끝* 을 가릴
보유신호 필요. WIDE0(재해−15% + 트레일링 고점−20%) 기준, 트레일링
매도 시점에 보유신호 켜져 있으면 매도 보류(catastrophe −35% 또는
추세선 이탈 시만 매도).

정책(인과·종가·단일진입=저점후 첫 종가>20일선):
  BASE     WIDE0: 재해−15% + 트레일링 −20% (참조·현재 최선)
  TRAIL35  신호 없이 트레일링만 −35% (보유신호 vs 단순 완화 구분용)
  H_RS     트레일링 매도 시 RS백분위≥80이면 보류(끝=−35% or RS<80후 −20%)
  H_MA120  종가>상승 120일선이면 보류(끝=120일선 이탈 or −35%)
  H_FGN    외인 or 기관 60일 순매수>0이면 보류(끝=매도전환후 −20% or −35%)
  H_COMBO  (RS≥80 또는 120일선 위) 그리고 외인/기관 매집 = 강건 보유
지표(NON/MID/WIN): 평균·중앙 실현, 승률, 포착중앙(=실현÷이상수익,
보유로 더 챙기나), 최악거래(보유로 downside 터지나), 보유연장 발생률.

Yahoo 종가·네이버 frgn·RS캐시(`_rs_sortmap.json`). 사이클내 사후·인-샘플
·상폐제외·비용 미반영. 환각 금지·결손 비임퓨트.
사용: python analyze_hold_signals.py [--n 60] [--seed 7]
"""
import argparse
import bisect
import json
import random
import statistics as st
import sys
from datetime import datetime, timezone, date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.fetch import yahoo_symbol  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

CY = cyclecfg.DIR
DIS, TRAIL, CAT = 0.15, 0.20, 0.35


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

    wf = json.loads((CY / "winners_final.json").read_text(encoding="utf-8"))
    winners = wf["winners"]
    wc = {x["code"] for x in winners}
    rv = json.loads((CY / "winners.json").read_text(encoding="utf-8"))["ranked_valid"]

    def ok(r):
        return (not r.get("exclude_reason") and r.get("trough_date")
                and r.get("n_days", 0) >= 60 and r.get("raw_multiple"))
    rest = [r for r in rv if r["code"] not in wc and ok(r)]
    NON = [r for r in rest if r["raw_multiple"] < 1.5]
    MID = [r for r in rest if 1.5 <= r["raw_multiple"] < 3.0]
    random.seed(args.seed)
    tiers = {"NON 안오름": random.sample(NON, min(args.n, len(NON))),
             "MID 중간": random.sample(MID, min(args.n, len(MID))),
             "WIN 위너": random.sample(winners, min(args.n, len(winners)))}

    sm = json.loads((CY / "_rs_sortmap.json").read_text(encoding="utf-8"))
    gdates = sorted(sm)

    def rs_pct(ret, ds):
        i = bisect.bisect_right(gdates, ds) - 1
        if i < 0:
            return None
        a = sm[gdates[i]]
        return 100 * bisect.bisect_left(a, ret) / max(1, len(a) - 1) if a else None

    POLS = ["BASE", "TRAIL35", "H_RS", "H_MA120", "H_FGN", "H_COMBO"]

    def hold_ok(pol, c, ts, k, e, fmap):
        if pol == "H_RS" or pol == "H_COMBO":
            rp = (rs_pct(c[k] / c[k - 252] - 1, ts[k])
                  if k >= 252 and c[k - 252] > 0 else None)
            rs = (rp is not None and rp >= 80)
        if pol == "H_MA120" or pol == "H_COMBO":
            m, mp = ma(c, k, 120), ma(c, k - 20, 120)
            tr = (m is not None and mp is not None and c[k] > m and m > mp)
        if pol in ("H_FGN", "H_COMBO"):
            sel = [fmap[d] for d in ts[max(e, k - 60):k] if d in fmap]
            fg = (sum(a for a, _ in sel) > 0 or sum(b for _, b in sel) > 0
                  ) if len(sel) >= 30 else None
        if pol == "H_RS":
            return rs
        if pol == "H_MA120":
            return tr
        if pol == "H_FGN":
            return fg is True
        if pol == "H_COMBO":
            return (rs or tr) and (fg is True)
        return False

    def run(c, ts, e, n, pol, fmap):
        end = n - 1
        peak = c[e]
        extended = False
        for k in range(e + 1, end + 1):
            if c[k] > peak:
                peak = c[k]
            g = c[k] / c[e] - 1
            if not extended and g < 0 and c[k] <= c[e] * (1 - DIS):
                return g, False                       # 진입 재해 손절
            tr = TRAIL if pol != "TRAIL35" else CAT
            if c[k] <= peak * (1 - tr):
                if pol in ("BASE", "TRAIL35"):
                    return g, extended
                if c[k] <= peak * (1 - CAT):
                    return g, True                     # catastrophe
                if hold_ok(pol, c, ts, k, e, fmap):
                    extended = True
                    continue                           # 보유 연장
                return g, extended                     # 보유신호 꺼짐 → 매도
        return c[end] / c[e] - 1, extended

    out = [f"[c2024-12] 보유신호 재설계 — 단계별 {args.n}종목 (seed {args.seed})",
           "WIDE0(재해−15%+트레일링−20%)에서 트레일링 매도 시 보유신호 켜지면",
           "보류(catastrophe −35%/추세이탈 시만 매도). 인과·종가·단일진입.",
           "포착=실현÷(진입~사이클 이상수익). 보유연장%=보유신호로 안 판 비율.",
           ""]
    for tag, lst in tiers.items():
        ser = []
        for w in lst:
            ch = cyclecfg.yahoo(yahoo_symbol(w["code"], w["market"]))
            if not ch or not ch.get("closes"):
                continue
            ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
                  for t in ch["timestamps"]]
            c = ch["closes"]
            ti = nidx(ts, w["trough_date"]) or 0
            e = causal_entry(c, ti, len(c))
            if e is None:
                continue
            try:
                gap = (_date.fromisoformat(ts[-1])
                       - _date.fromisoformat(w["trough_date"])).days
                fr = fetch_naver_org_flow(
                    w["code"], pages=min(30, max(10, gap // 28 + 5)),
                    sleep_ms=130)
            except Exception:
                fr = []
            fmap = {r["date"]: (r.get("fgn_net") or 0, r.get("org_net") or 0)
                    for r in fr}
            ser.append((c, ts, e, len(c), fmap, max(c[e:]) / c[e] - 1))
        out.append(f"== {tag} (종목 {len(ser)}) ==")
        out.append("정책 | 평균실현% | 중앙% | 승률 | 포착중앙 | 최악% | 보유연장%")
        for p in POLS:
            rr, caps, ext = [], [], 0
            for c, ts, e, n, fmap, emax in ser:
                g, ex = run(c, ts, e, n, p, fmap)
                rr.append(g * 100)
                caps.append((g / emax) if emax > 1e-9 else (1.0 if g >= 0 else 0.0))
                ext += 1 if ex else 0
            m = len(rr)
            out.append(
                f"{p:8s} | {round(st.mean(rr),1)}% | {round(st.median(rr),1)}% | "
                f"{round(100*sum(1 for v in rr if v>0)/m)}% | "
                f"{round(st.median(caps),2)} | {round(min(rr),1)}% | "
                f"{round(100*ext/m)}%")
        out.append("")
    out += ["== 해석(쉽게) ==",
            "BASE 대비 평균·중앙·포착↑ & 최악 견딜만하면 보유신호 가치 有.",
            "TRAIL35(신호없이 그냥 −35% 완화)보다 H_*가 나아야 '신호가",
            "진짜 가치'(단순 완화로 충분하면 신호 불필요). 보유연장%는",
            "그 신호가 실제로 얼마나 개입했나.",
            "== 한계 ==",
            "사이클내 사후·인-샘플·상폐제외·표본무작위·비용 미반영·단일",
            "인과진입(검증 5신호 아님)·종가·frgn 결손 비임퓨트."]
    fn = f"_hold_signals_n{args.n}s{args.seed}.txt"
    (CY / fn).write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()

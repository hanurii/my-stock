"""한국형 매수 규칙 — 현재 시점 후보 스크리너 (검증된 선별골격+타이밍).

근거: buy_timing.md §1~8 + korea_canslim v1.1 (대조군 검증).
  선별(무엇): L(RS≥80, 변별력 8x 1순위) + M(시장 상승) + I(외인/기관 60일
              순매수). S·+K·A 는 변별력 없어 *필터로 안 씀*.
  타이밍(언제): 폭락·반등 후 짧고 얕은 base 직후, 추세확인이 *막* 된 초기
              (종가>상승50일선 & >20거래일전), 거래량 조용·신고가 한참
              아래(오닐식 거래량돌파/신고가 *기다리지 말 것*), −8% 손절.

입력: cycles/c2024-12/_universe_prices_5y.json (close-only, ~2026-05-15).
한계: 캐시 기준일 시점·close-only(거래량 미반영, 신고가거리로 대체)·
인-샘플 규칙·생존자. *추천 아님* — 규칙 충족 후보를 사용자가 차트 확인.

사용:  python screen_buy_now.py [--fresh 15] [--top 12]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts"))
import cyclecfg  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

CY = ROOT / "research" / "oneil-model-book" / "cycles" / "c2024-12"


def sma(c, j, w):
    return sum(c[j - w + 1:j + 1]) / w if j >= w - 1 else None


def confirmed(c, d):
    if d < 60:
        return False
    m, mp = sma(c, d, 50), sma(c, d - 10, 50)
    return (m is not None and mp is not None and c[d] > m and m > mp
            and c[d] > c[d - 20])


def idx_regime():
    """현재 코스피·코스닥 국면(M)."""
    out = {}
    for nm, sym in (("KOSPI", "%5EKS11"), ("KOSDAQ", "%5EKQ11")):
        ch = cyclecfg.yahoo(sym)
        c = (ch or {}).get("closes") or []
        if len(c) < 200:
            out[nm] = "?"
            continue
        px, m50, m200 = c[-1], sum(c[-50:]) / 50, sum(c[-200:]) / 200
        out[nm] = "상승추세" if (px > m50 > m200 and px > m200) else (
            "중립" if px > m200 else "하락추세")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", type=int, default=15,
                    help="추세확인 전환 후 경과 거래일 상한(조기 진입)")
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    w = json.loads((CY / "winners.json").read_text(encoding="utf-8"))
    nm = {r["code"]: (r["name"], r["market"]) for r in w["ranked_valid"]}

    # 1) RS(L): 전 종목 52주 수익률 → 백분위
    rets = {}
    for code, s in U.items():
        c = s.get("c")
        if not c or len(c) < 260 or c[-252] <= 0:
            continue
        rets[code] = c[-1] / c[-252] - 1
    order = sorted(rets, key=lambda k: rets[k])
    rspct = {code: round(100 * i / (len(order) - 1), 1)
             for i, code in enumerate(order)}

    cand = []
    for code, s in U.items():
        c = s.get("c")
        if code not in rspct or not c or len(c) < 260:
            continue
        last = len(c) - 1
        if not confirmed(c, last):
            continue                                   # 지금 추세확인 상태여야
        # 전환 신선도: confirmed False→True 마지막 전환 이후 경과
        cross = None
        for d in range(last, 60, -1):
            if confirmed(c, d) and not confirmed(c, d - 1):
                cross = d
                break
        if cross is None:
            continue
        bars_since = last - cross
        if not (0 <= bars_since <= args.fresh):
            continue                                   # *막* 전환된 초기만
        hi52 = max(c[-252:])
        pct_hi = c[-1] / hi52 * 100 if hi52 else 100
        if pct_hi > 88:
            continue                                   # 신고가 추격 아님(조용·아래)
        ext = c[-1] / sma(c, last, 50) - 1              # 50일선 위 과열도
        if ext > 0.20:
            continue                                   # 너무 늘어남=늦음
        # base 직전 폭락·반등 + 선행상승(시그니처): 최근 250봉 내 큰 낙폭 존재
        lo = min(c[-250:]) if len(c) >= 250 else min(c)
        rebound = c[-1] / lo - 1
        prior = (max(c[-500:-120]) / min(c[-500:-120]) - 1
                 if len(c) >= 500 else None)
        if rspct[code] < 80:
            continue                                   # L: RS≥80 (1순위 변별)
        cand.append({
            "code": code, "name": nm.get(code, ("?", "?"))[0],
            "market": nm.get(code, ("?", "?"))[1],
            "RS": rspct[code], "bars_since_confirm": bars_since,
            "pct_of_52w_high": round(pct_hi, 1),
            "above_50dma_pct": round(ext * 100, 1),
            "rebound_from_low_pct": round(rebound * 100, 1),
            "prior_advance_pct": round(prior * 100, 1) if prior else None,
        })

    cand.sort(key=lambda r: (-r["RS"], r["bars_since_confirm"]))
    short = cand[:args.top]

    # 2) I축(외인/기관 60일 순매수) — 후보만 조회(저비용)
    for r in short:
        try:
            rows = fetch_naver_org_flow(r["code"], pages=4, sleep_ms=200)
            fg = sum(x.get("fgn_net") or 0 for x in rows[:60])
            og = sum(x.get("org_net") or 0 for x in rows[:60])
            r["fgn_net_60d"], r["inst_net_60d"] = fg, og
            r["I_pass"] = (fg > 0) or (og > 0)
        except Exception:
            r["fgn_net_60d"] = r["inst_net_60d"] = None
            r["I_pass"] = None

    reg = idx_regime()
    L = [f"한국형 매수 후보 — 캐시기준일 {U[list(U)[0]]['d'][-1]} "
         f"(추세확인 {args.fresh}일내 신선·RS≥80·신고가 ≤88%)",
         f"시장국면 M: KOSPI {reg.get('KOSPI')} / KOSDAQ {reg.get('KOSDAQ')}",
         f"전체 추세확인+RS≥80 후보 {len(cand)}개 중 상위 {len(short)}",
         "",
         "코드 종목 시장 | RS | 확인후일 | 52주고가% | 50일선+% | "
         "저점반등% | 선행상승% | 외인60d | 기관60d | I",
         "-" * 96]
    for r in short:
        L.append(
            f"{r['code']} {r['name']}({r['market']}) | RS{r['RS']} | "
            f"{r['bars_since_confirm']}일 | {r['pct_of_52w_high']}% | "
            f"{r['above_50dma_pct']}% | {r['rebound_from_low_pct']}% | "
            f"{r['prior_advance_pct']}% | {r.get('fgn_net_60d')} | "
            f"{r.get('inst_net_60d')} | {r.get('I_pass')}")
    L += ["",
          "해석: I=True(외인 or 기관 60일 순매수)면 선별 3축(L+M+I) 충족.",
          "진입=다음 거래일 추세 유지 확인 후, −8% 손절. 신고가/거래량",
          "폭증을 기다리면 늦음(검증 §2). *추천 아님 — 차트 직접 확인.*"]
    out = CY / "_buy_candidates.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"screened: {out}  cand={len(cand)} top={len(short)} "
          f"M(KOSPI/KOSDAQ)={reg.get('KOSPI')}/{reg.get('KOSDAQ')}",
          file=sys.stderr)


if __name__ == "__main__":
    main()

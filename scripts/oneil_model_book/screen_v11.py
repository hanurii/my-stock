"""한국식 CAN SLIM 종합 스크리너 — v1.1 선별골격 + v1.3 손실회피 가드
+ #3 선행상승≥50% 제외필터 (선별+타이밍+가드+섹터무리).

순서:
 ★ 코스피 강세(종가>200거래일선 & 200일선 상승) 아니면 시스템 OFF — 추천 안 함
 1차(전종목, close+RS캐시·즉시): L RS≥80 & 신고가 한참아래(52주고가 ≤88%)
    & 50일선 근처(±10%) & 추세확인 막 켜짐(상승50일선 위·>20거래일전,
    전환 최근 ~15일내) → RS순 상위 N1
 2차(상위 N1만 실조회): Yahoo 거래량(조용 ≤1.2배·신고가 추격 아님) +
    v1.3 손실회피 가드(직전60일 고점이 최근 5일내 AND 그 고점 대비
    −12%↓ = 고점후 분산 → 제외) + **#3 선별강화: 큰 선행상승 ≥50%
    제외필터**(없으면 탈락 — 2사이클 교차, 정밀도 76→90%) + **v1.3
    정교화: 케이프형(오래된 고점·깊은 하락)은 *오늘 15일 신저점 갱신
    중*이면 제외(자유낙하 절단·위너 69% 보존), 단 선행상승 ≥100%면
    구제 통과(로켓 표식·_cape_rescue)** +
    네이버 frgn I(외인 or 기관 60일>0)
 섹터 무리 가점(검증된 보조축): 생존 후보의 업종(DART) 중 같은 업종에
    2종목 이상 몰린 섹터 = 핫섹터 → 그 종목에 ★표(가점). 임의 점수 안 만들고
    RS순 정렬 + 섹터무리 종목을 위로·표기.

*추천 아님 — 규칙 충족 후보. 확률 도구·인-샘플·종가·캐시기준일.*
사용: python screen_v11.py [--n1 30] [--fresh 15]
"""
import argparse
import bisect
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.fetch import (fetch_yahoo_chart, yahoo_symbol,  # noqa: E402
                               fetch_stock_list,
                               resolve_corp_code, load_corp_code_map)
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_variables import dart_company  # noqa: E402

CY = ROOT / "research" / "oneil-model-book" / "cycles" / "c2024-12"


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def sma(c, i, w):
    return sum(c[i - w + 1:i + 1]) / w if i >= w - 1 else None


def confirmed(c, d):
    if d < 60:
        return False
    m, mp = sma(c, d, 50), sma(c, d - 10, 50)
    return (m and mp and c[d] > m and m > mp and c[d] > c[d - 20])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n1", type=int, default=30)
    ap.add_argument("--fresh", type=int, default=15)
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()

    U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
    # 종목명/시장: 실시간 상장목록 우선(신규 IPO 포함) → winners.json 보조
    nm = {}
    try:
        for s in fetch_stock_list("KOSPI") + fetch_stock_list("KOSDAQ"):
            nm[s["code"]] = (s["name"], s["market"])
    except Exception:
        pass
    if (CY / "winners.json").exists():
        w = json.loads((CY / "winners.json").read_text(encoding="utf-8"))
        for r in w["ranked_valid"]:
            nm.setdefault(r["code"], (r["name"], r["market"]))

    # 캐시 최신일 — 이 날짜 종가 있는 종목만 스크린(구버전 자동 배제)
    latest = max((s["d"][-1] for s in U.values() if s.get("d")), default=None)

    # 즉석 RS: 동일 종료일 전종목 252일 수익률 분포(frozen sortmap 폐기)
    R_full = []
    for s in U.values():
        d, c = s.get("d"), s.get("c")
        if (d and c and d[-1] == latest and len(c) >= 253
                and c[-1] > 0 and c[-253] > 0):
            R_full.append(c[-1] / c[-253] - 1)
    R_full.sort()

    def rs_full(ret):
        return (100 * bisect.bisect_left(R_full, ret) / max(1, len(R_full) - 1)
                if R_full else None)

    def rs_short(c, win):
        """단축 RS(상장1년 미만): 보유기간 win, 전종목 동일기간·동일
        종료일 분포 백분위(compute_rs 방식, 공정 비교)."""
        if c[-1] <= 0 or c[-1 - win] <= 0:
            return None
        r = c[-1] / c[-1 - win] - 1
        ref = []
        for s in U.values():
            cc, dd = s.get("c"), s.get("d")
            if (cc and dd and dd[-1] == latest and len(cc) > win
                    and cc[-1] > 0 and cc[-1 - win] > 0):
                ref.append(cc[-1] / cc[-1 - win] - 1)
        if len(ref) < 100:
            return None
        ref.sort()
        return 100 * bisect.bisect_left(ref, r) / max(1, len(ref) - 1)

    # ★ 코스피 국면
    ks = fetch_yahoo_chart("%5EKS11", period1=_ep("2023-01-01"),
                           period2=_ep("2027-01-01"), interval="1d")
    bull, kln = None, "결손"
    if ks and ks.get("closes"):
        kc = ks["closes"]
        m2 = sma(kc, len(kc) - 1, 200)
        m2p = sma(kc, len(kc) - 21, 200)
        bull = bool(m2 and m2p and kc[-1] > m2 and m2 > m2p)
        kln = (f"코스피 {kc[-1]:,.0f} vs 200일선 {m2:,.0f} → "
               f"{'강세(시스템 ON)' if bull else '비강세(시스템 OFF)'}")

    # 1차: 전종목 close+RS (즉석). 신선도 가드 = 최신일 종가 있는 종목만.
    # 상장 ~3개월(62거래일)↑ 이면 평가 — 252일 미만은 단축 RS.
    cand = []
    for code, s in U.items():
        d, c = s.get("d"), s.get("c")
        if not d or not c or d[-1] != latest or len(c) < 62:
            continue
        li = len(c) - 1
        if c[li] <= 0 or not confirmed(c, li):
            continue
        cross = next((x for x in range(li, 60, -1)
                      if confirmed(c, x) and not confirmed(c, x - 1)), None)
        if cross is None or li - cross > a.fresh:
            continue
        hw = min(252, li)                     # 단축 시 보유 이력 내 최고가
        hi52 = max(c[li - hw:li + 1])
        m50 = sma(c, li, 50)
        if not (hi52 and m50):
            continue
        if c[li] > 0.88 * hi52 or abs(c[li] / m50 - 1) > 0.10:
            continue
        if li >= 252 and c[li - 252] > 0:
            rp, short_rs = rs_full(c[li] / c[li - 252] - 1), False
        else:
            rp, short_rs = rs_short(c, li), True
        if rp is None or rp < 80:
            continue
        cand.append((code, li, rp, c[li], hi52, short_rs))
    cand.sort(key=lambda x: -x[2])
    short = cand[:a.n1]

    corp_map = load_corp_code_map()
    picks = []
    for code, li, rp, px, hi52, short_rs in short:
        name, mkt = nm.get(code, (code, "KOSPI"))
        ch = fetch_yahoo_chart(yahoo_symbol(code, mkt),
                               period1=_ep("2024-06-01"),
                               period2=_ep("2027-01-01"), interval="1d")
        if not ch or not ch.get("closes"):
            continue
        cc, vv = ch["closes"], ch.get("volumes") or []
        if len(cc) < 60 or not vv:
            continue
        j = len(cc) - 1
        v50 = sum(vv[j - 50:j]) / 50 if j >= 50 and sum(vv[j - 50:j]) else None
        if not v50 or vv[j] / v50 > 1.2:                 # 조용(추격 아님)
            continue
        # v1.3 손실회피 가드: 직전60일 고점이 최근5일내 & 고점대비 −12%↓
        seg = cc[max(0, j - 60):j + 1]
        hi60 = max(seg)
        hidx = max(range(len(cc) - len(seg), len(cc)), key=lambda k: cc[k])
        if (len(cc) - 1 - hidx) <= 5 and cc[j] <= hi60 * 0.88:
            continue                                      # 고점후 분산 — 제외
        # #3 선별강화: L + '큰 선행상승 ≥50%' 제외필터 (2사이클 교차검증,
        # 정밀도 76→90%·lift 7.8→23.6x). 이력 부족/선행상승 부재 = 탈락
        # (안오름 1번 함정 = 선행상승 없음). korea_canslim §#3·_trap_filter*.
        st0 = max(0, j - 500)
        if j - 60 <= st0:
            continue                                      # 이력 부족 — 탈락
        loseg = cc[st0:j - 60]
        lo = min(loseg)
        lo_i = st0 + loseg.index(lo)
        hiseg = cc[lo_i:j - 20] if (j - 20) > lo_i else cc[lo_i:j]
        prior_up = (max(hiseg) / lo - 1) if lo > 0 else None
        if prior_up is None or prior_up < 0.50:
            continue                                      # 선행상승<50% 제외
        # v1.3 정교화(2026-05-18, _cape_ev_sweep): 케이프형(직전60일고점
        # 대비 ≤−12% & 그 고점 >5거래일 전)은 무조건 제외 아님(위너 55~
        # 59% 그 모양). *오늘 15일 신저점 갱신 중*이면 제외 — 자유낙하
        # 함정만 절단(최악10% 0→+15%·위너 69% 보존). 단 선행상승 ≥100%
        # = 로켓 표식(_cape_rescue: 26위너 회수·함정 7·실현평균 +35%)→
        # 신저점이어도 *구제 통과*. 트레이드오프 부분 해소.
        cape = (cc[j] <= hi60 * 0.88) and ((len(cc) - 1 - hidx) > 5)
        if cape:
            w15 = cc[max(0, j - 15):j + 1]
            if cc[j] <= min(w15) and prior_up < 1.00:     # 신저점 & 非로켓
                continue                                  # 자유낙하 — 제외
        fg5 = og5 = fg10 = og10 = fg20 = og20 = None
        try:
            fr = sorted(fetch_naver_org_flow(code, pages=6, sleep_ms=180),
                        key=lambda r: r["date"])

            def _w(n, k):
                s = fr[-n:] if len(fr) >= min(n, 5) else fr
                return sum((r.get(k) or 0) for r in s)
            f60 = fr[-60:]
            fg = sum(r.get("fgn_net") or 0 for r in f60) if len(f60) >= 30 else None
            og = sum(r.get("org_net") or 0 for r in f60) if len(f60) >= 30 else None
            fg5, fg10, fg20 = _w(5, "fgn_net"), _w(10, "fgn_net"), _w(20, "fgn_net")
            og5, og10, og20 = _w(5, "org_net"), _w(10, "org_net"), _w(20, "org_net")
        except Exception:
            fg = og = None
        if fg is None or not ((fg > 0) or (og > 0)):       # I: 매집 배경
            continue
        # 업종(DART 3자리)
        sec = None
        try:
            corp = resolve_corp_code(code, corp_map)[0]
            if corp:
                ic = (dart_company(corp) or {}).get("induty_code")
                sec = str(ic)[:3] if ic else None
        except Exception:
            pass
        picks.append({"code": code, "name": name, "mkt": mkt, "rs": rp,
                      "short_rs": short_rs,
                      "px": cc[j], "vol": round(vv[j] / v50, 2),
                      "hi52pct": round(cc[j] / hi52 * 100, 1),
                      "ma50pct": round((cc[j] / sma(cc, j, 50) - 1) * 100, 1),
                      "fg": fg, "og": og, "sec": sec,
                      "fg5": fg5, "og5": og5, "fg10": fg10, "og10": og10,
                      "fg20": fg20, "og20": og20})

    # 섹터 무리 가점: 생존 후보 중 같은 업종 2+ = 핫섹터
    from collections import Counter
    sc = Counter(p["sec"] for p in picks if p["sec"])
    for p in picks:
        p["hot"] = bool(p["sec"] and sc.get(p["sec"], 0) >= 2)
    # 정렬: 섹터무리 우선 → RS순
    picks.sort(key=lambda p: (not p["hot"], -p["rs"]))

    L = [f"[한국식 CAN SLIM 현재 후보 — v1.1 선별골격 + v1.3 손실회피 "
         f"+ #3 선행상승≥50%] (캐시기준 {latest})",
         f"★ {kln}",
         f"1차(RS≥80·신고가 ≤88%·50일선근처·추세확인 신선) {len(cand)}개 → "
         f"2차(거래량 조용·고점후분산 제외·외인/기관 매집) 생존 {len(picks)}",
         "정렬: 섹터무리(같은업종 2+ 후보=핫섹터) 우선 → RS순. "
         "*추천 아님·확률 도구·인-샘플·종가.*", ""]
    if bull is False:
        L.append("⚠ 코스피 비강세 = 시스템 OFF 국면. 아래는 *참고용*, "
                 "원칙상 신규 매수 보류·현금.")
    L.append("종목 | RS | 거래량 | 52주고가% | 50일선% | 외인60 | 기관60 | "
             "업종 | 섹터무리")
    L.append("  └ 수급추세(주): 외인 5/10/20일 · 기관 5/10/20일 "
             "(필터 아님 — 사장님 직접 판단용. ⚠=최근5일 외인·기관 둘다 순매도)")
    L.append("-" * 30)

    def _n(v):
        return f"{v:+,}" if isinstance(v, (int, float)) else "결손"
    for p in picks[:a.top]:
        warn = (isinstance(p["fg5"], (int, float)) and p["fg5"] < 0
                and isinstance(p["og5"], (int, float)) and p["og5"] < 0)
        L.append(f"{p['name']}({p['code']}) | "
                 f"RS{p['rs']:.0f}{'*' if p['short_rs'] else ''} | "
                 f"{p['vol']}배 | {p['hi52pct']}% | {p['ma50pct']:+.1f}% | "
                 f"{p['fg']:+,} | {p['og']:+,} | {p['sec']} | "
                 f"{'★핫섹터(가점)' if p['hot'] else '-'}"
                 f"{'  ⚠최근5일 외인·기관 동반매도' if warn else ''}")
        L.append(f"  └ 외인 {_n(p['fg5'])}/{_n(p['fg10'])}/{_n(p['fg20'])} · "
                 f"기관 {_n(p['og5'])}/{_n(p['og10'])}/{_n(p['og20'])}")
    if any(p["short_rs"] for p in picks[:a.top]):
        L.append("* = 단축 RS(상장 1년 미만, 전종목 동일기간 비교) — "
                 "신뢰도 낮음, 차트 특히 주의.")
    hot_secs = [s for s, n in sc.items() if n >= 2]
    L += ["",
          f"핫섹터(후보 2+ 몰림): {hot_secs or '없음'} "
          f"— 검증된 '섹터 무리'(위너는 핫섹터에 떼지어) 보조 가점.",
          "주의: 이건 *조용한 눌림목* 후보 — 신고가·거래량 폭증 추격의",
          "정반대. 사용자 SK하이닉스식 추격·강세장 위너 조기매도 습관과",
          "반대로 가야 함. 진입 후 −15% 재해선 사수·물타기 금지.",
          "한계: 확률 도구(헛신호 절반)·인-샘플·종가·캐시기준일·거래비용",
          "무관. 차트로 거래량·추세 직접 확인 후 사용자 판단."]
    out = ROOT / "research" / "oneil-model-book" / "_screen_v11_now.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out} (1차 {len(cand)} → 생존 {len(picks)}, "
          f"핫섹터 {len(hot_secs)})", file=sys.stderr)


if __name__ == "__main__":
    main()

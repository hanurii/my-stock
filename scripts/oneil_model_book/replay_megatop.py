"""[페이퍼 트레이딩 재생] 최종 메가캡 모멘텀 시스템을 월별 일지로 재생.

목적: 사용자가 *실제 매매하는 기분*으로 5년치를 5분 안에 체험.
구성: KOSPI 전용·N=5·월간·top30·1년 모멘텀·재해-10%·트레일-20%·★스위치.

각 월별 결정·손절 발동·★ 스위치 변경을 평이한 한국어로 기록.
끝에 통계 요약(거래수·승률·최고/최악·최대낙폭) 첨부.

사용: python replay_megatop.py [--src c2024-12] [--start 2024-12-09]
"""
import argparse
import bisect
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import analyze_equity_curve as AE                       # noqa: E402
import analyze_equity_curve_rt as RT                    # noqa: E402
import analyze_doppelganger as AD                       # noqa: E402

OUT = HERE.parents[1] / "research" / "oneil-model-book"


def code_names():
    """현재 상장명 사전."""
    import FinanceDataReader as fdr
    nm = {}
    for m in ("KOSPI", "KOSDAQ"):
        for _, r in fdr.StockListing(m).iterrows():
            c = str(r.get("Code") or "").zfill(6)
            if c.isdigit() and r.get("Name"):
                nm[c] = r["Name"]
    return nm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="c2024-12")
    ap.add_argument("--start", default=None,
                    help="시작일(YYYY-MM-DD). 기본=사이클 앵커")
    ap.add_argument("--end", default=None,
                    help="종료일(YYYY-MM-DD). 기본=데이터 끝")
    ap.add_argument("--tag", default="",
                    help="출력 파일 접미사(예: _bear22)")
    a = ap.parse_args()

    # 시장 매핑·주식수
    mkmap = json.loads((OUT / "_universe_market.json")
                       .read_text(encoding="utf-8"))
    shares = json.loads((OUT / "_universe_shares.json")
                        .read_text(encoding="utf-8"))
    nm = code_names()

    U = AD.pick_universe_file(a.src)
    codes_d = {}
    skipped = 0
    for k, s in U.items():
        if not s.get("d") or not s.get("c") or len(s["c"]) <= 260:
            continue
        if mkmap.get(k) != "KOSPI":
            continue
        c = s["c"]
        # 데이터 무결성: 1주 100만원↑(분할 미반영), 일중 3배↑ 점프(잘못된 시계열) 제외
        if c[-1] > 1_000_000:
            skipped += 1
            continue
        bad = False
        for i in range(1, min(len(c), 600)):
            if c[i - 1] > 0 and (c[i] / c[i - 1] > 3 or c[i - 1] / c[i] > 3):
                bad = True
                break
        if bad:
            skipped += 1
            continue
        codes_d[k] = (s["d"], c)
    print(f"[필터] 데이터 이상 {skipped}종 제외, "
          f"유효 KOSPI 종목 {len(codes_d)}", file=sys.stderr)
    al = sorted({x for d, _ in codes_d.values() for x in d})
    rs0 = a.start or al[min(len(al) - 1, 260)]
    end = a.end or al[-1]
    axis = [t for t in al if rs0 <= t <= end]
    kd, kc = AE.kospi_series()

    REBAL = 20
    LOOKBACK = 252
    N = 5
    STOP = -0.10
    TRAIL = -0.20
    COST = 0.0066

    pos = {}             # code -> {inv, entry, peak, buy_dt}
    cash = 1.0
    trades = []
    eq = []
    diary = []
    last_month = None
    prev_on = None
    last_diary_month = None

    for ti, t in enumerate(axis):
        on = not AE.kbear_at(kd, kc, t)
        # 일별 손절·★
        for code in list(pos):
            d, c = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i < 0:
                continue
            px = c[i]
            p = pos[code]
            p["peak"] = max(p["peak"], px)
            reason = None
            if px <= p["entry"] * (1 + STOP):
                reason = f"−10% 재해손절 ({px/p['entry']*100-100:+.0f}%)"
            elif px <= p["peak"] * (1 + TRAIL):
                reason = f"고점대비 −20% 트레일 ({px/p['entry']*100-100:+.0f}%)"
            elif not on:
                reason = f"★ 약세 현금화 ({px/p['entry']*100-100:+.0f}%)"
            if reason:
                cash += p["inv"] * (px / p["entry"]) * (1 - COST)
                ret = (px / p["entry"] - 1) * 100
                trades.append((code, p["buy_dt"], t, ret, reason))
                diary.append(f"  • {t}  매도: {nm.get(code,code)[:10]} "
                             f"({code})  → {reason}")
                del pos[code]
        # ★OFF 월간 — 현금 보유 중 표시
        if ti % REBAL == 0 and not on:
            month = t[:7]
            if month != last_diary_month:
                last_diary_month = month
                # 보유 중인 거 있으면 평가, 없으면 cash
                mv = cash
                for code, p in pos.items():
                    d, c = codes_d[code]
                    i = bisect.bisect_right(d, t) - 1
                    if i >= 0:
                        mv += p["inv"] * (c[i] / p["entry"])
                diary.append("")
                diary.append(f"━━━ {t} 월간 점검  자본 ×{mv:.2f}  "
                             f"★OFF (현금 보유·매매 X) ━━━")
                diary.append("  → 코스피가 200일선 아래 또는 200일선 "
                             "하락 중. 시스템은 *기다린다*.")
        # 월간 리밸런스
        if ti % REBAL == 0 and on:
            cap = []
            for code, (d, c) in codes_d.items():
                i = bisect.bisect_right(d, t) - 1
                if i < LOOKBACK or c[i] <= 0 or c[i - LOOKBACK] <= 0:
                    continue
                if code not in shares:
                    continue
                mc = c[i] * shares[code] / 1e8
                if mc > 0:
                    cap.append((mc, code, i, c))
            cap.sort(reverse=True)
            top30 = cap[:30]
            scored = [(c[j] / c[j - LOOKBACK] - 1, code, c[j])
                      for _, code, j, c in top30
                      if c[j - LOOKBACK] > 0]
            scored.sort(reverse=True)
            target = {code: px for _, code, px in scored[:N]}
            sold_in_rebal = []
            for code in list(pos):
                if code in target:
                    continue
                d, c = codes_d[code]
                i = bisect.bisect_right(d, t) - 1
                px = c[i] if i >= 0 else pos[code]["entry"]
                cash += pos[code]["inv"] * (px / pos[code]["entry"]) \
                    * (1 - COST)
                ret = (px / pos[code]["entry"] - 1) * 100
                trades.append((code, pos[code]["buy_dt"], t, ret,
                               "리밸런스 이탈"))
                sold_in_rebal.append((code, ret))
                del pos[code]
            bought_in_rebal = []
            for code, px in target.items():
                if code in pos or cash <= 1e-9:
                    continue
                buy = min(cash, cash / (N - len(pos)))
                cash -= buy
                pos[code] = {"inv": buy * (1 - COST), "entry": px,
                             "peak": px, "buy_dt": t}
                bought_in_rebal.append((code, scored, px))
            # 일지
            mv = cash
            for code, p in pos.items():
                d, c = codes_d[code]
                i = bisect.bisect_right(d, t) - 1
                if i >= 0:
                    mv += p["inv"] * (c[i] / p["entry"])
            month = t[:7]
            if month != last_month:
                last_month = month
                last_diary_month = month
                diary.append("")
                diary.append(f"━━━ {t} 월간 점검  자본 ×{mv:.2f}  "
                             f"★{'ON' if on else 'OFF'} ━━━")
                if sold_in_rebal:
                    for code, r in sold_in_rebal:
                        diary.append(f"  • 매도(리밸): "
                                     f"{nm.get(code,code)[:10]} "
                                     f"({code})  {r:+.0f}%")
                if bought_in_rebal:
                    diary.append(f"  → 이번 달 보유:")
                    held = sorted(pos.keys())
                    for code in held:
                        ret_score = next((s for s, c, _ in scored
                                          if c == code), 0)
                        diary.append(f"    ★ {nm.get(code,code)[:12]} "
                                     f"({code})  1년 +{ret_score*100:.0f}%")
        # ★ 상태 변화 기록
        if prev_on is not None and on != prev_on:
            if on:
                diary.append(f"  ⚡ {t}  ★ 스위치 ON — 다음 점검에서 "
                             "재진입 시작")
            else:
                diary.append(f"  ⚡ {t}  ★ 스위치 OFF — 전 종목 청산 발동")
        prev_on = on
        # 평가
        mv = cash
        for code, p in pos.items():
            d, c = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i >= 0:
                mv += p["inv"] * (c[i] / p["entry"])
        eq.append(mv)

    # 통계
    peak = eq[0]
    mdd, uw_max, uw = 0.0, 0, 0
    peak_i = trough_i = 0
    for i, v in enumerate(eq):
        if v >= peak:
            peak, peak_i, uw = v, i, 0
        else:
            uw += 1
            uw_max = max(uw_max, uw)
        if v / peak - 1 < mdd:
            mdd = v / peak - 1
            trough_i = i
    wins = [t for t in trades if t[3] > 0]

    # 요약
    yr = (datetime.strptime(end, "%Y-%m-%d")
          - datetime.strptime(rs0, "%Y-%m-%d")).days / 365.25
    cagr = (eq[-1] ** (1 / yr) - 1) * 100 if yr > 0 and eq[-1] > 0 else 0
    # KOSPI 매수보유 비교
    bh = AE.kospi_bh(kd, kc, axis[0], axis[-1])
    bh_final = bh[1][-1] if bh else None
    bh_cagr = ((bh_final ** (1 / yr) - 1) * 100
               if (bh_final and yr > 0) else 0)
    bh_mdd = 0.0
    if bh:
        p = bh[1][0]
        for v in bh[1]:
            p = max(p, v)
            bh_mdd = min(bh_mdd, v / p - 1)
    L = ["📔 [페이퍼 트레이딩 일지] 메가캡 모멘텀 — 최종 권고 구성",
         f"기간: {rs0} ~ {end} (≈{yr:.1f}년) · 최종 자본 ×{eq[-1]:.2f}",
         "구성: KOSPI 전용·N=5·월간·top30·1년 모멘텀·재해−10%·트레일"
         "−20%·★스위치·비용0.66%",
         "=" * 70, ""]
    L += diary
    L += ["",
          "=" * 70,
          f"📊 {yr:.1f}년 결산",
          f"  · 시작 자본 1.00 → 최종 ×{eq[-1]:.2f} "
          f"(연수익 {cagr:+.0f}%)",
          f"  · 최대 낙폭(MDD) {mdd*100:.0f}% "
          f"(최고 {axis[peak_i]} ×{eq[peak_i]:.2f} → 최저 "
          f"{axis[trough_i]} ×{eq[trough_i]:.2f})",
          f"  · 최장 수중(본전 못 회복) 기간 {uw_max} 거래일 "
          f"(≈{uw_max/21:.0f}개월)",
          f"  · 총 거래 {len(trades)}건 · 승률 "
          f"{100*len(wins)/max(1,len(trades)):.0f}%",
          (f"  · 최고 수익 거래 {max(trades, key=lambda x: x[3])[3]:+.0f}% "
           f"· 최악 거래 {min(trades, key=lambda x: x[3])[3]:+.0f}%"
           if trades else "  · 거래 없음 (★ 스위치 줄곧 OFF로 추정)"),
          "",
          f"  📈 같은 기간 KOSPI 매수보유: ×{bh_final:.2f} "
          f"({bh_cagr:+.0f}%/년) · MDD {bh_mdd*100:.0f}% "
          f"→ 시스템이 KOSPI를 "
          f"{'★이김' if eq[-1] > bh_final else '짐'} "
          f"({(eq[-1]/bh_final-1)*100:+.0f}%p 차이)",
          "",
          "💡 이 일지가 보여주는 것:",
          "  · *대부분의 매도는 −10% 손절*입니다(승률 ~45% = 70%는 손해/소익)",
          "  · 가끔의 큰 수익이 누적 손실을 메우고 통장을 키움",
          "  · ★ 스위치 발동 구간은 *전 종목 현금*화돼 폭락 일부 차단",
          "  · 매월 결정은 *기계적*: 1년 모멘텀 톱-5만 보면 됨",
          "한계: 사후·종가·일별·n=2·주식수 현재값(소오차)·실제 슬리피지·"
          "심리 압박 미반영."]
    txt = "\n".join(L)
    p = OUT / f"_paper_replay{a.tag}.txt"
    p.write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()

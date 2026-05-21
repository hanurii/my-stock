"""보유 종목 피드백 — 한국형 위너 매매 시스템 v1 / 한국식 CAN SLIM v1.1.

특정 시점 매수한 종목을 실데이터로 점검: 잘 샀나? 보유? 매도?
순서: ★마스터 스위치(코스피 국면) → ② 진입 타이밍 평가(그날) →
③/④ 손절·트레일 현 위치 → L·I·C 선별축 현재 상태 → 종합 판정.
환각 금지·결손 명시·확률 도구(수익 보장 아님).

사용: python feedback_position.py --code 000660 --market KOSPI \
       --entry 2026-05-11 --price 1924378 --shares 37
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from canslim_lib.fetch import fetch_yahoo_chart, yahoo_symbol  # noqa: E402
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def sma(c, i, w):
    return sum(c[i - w + 1:i + 1]) / w if i >= w - 1 else None


def series(sym):
    ch = fetch_yahoo_chart(sym, period1=_ep("2023-01-01"),
                           period2=_ep("2027-01-01"), interval="1d")
    if not ch or not ch.get("closes"):
        return None
    d = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
         for t in ch["timestamps"]]
    return d, ch["closes"], ch.get("volumes") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--market", required=True)
    ap.add_argument("--entry", required=True)
    ap.add_argument("--price", type=float, required=True)
    ap.add_argument("--shares", type=float, default=0)
    ap.add_argument("--sell-date", dest="sell_date", default="")
    ap.add_argument("--sell-price", dest="sell_price", type=float, default=0)
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    nm = a.name or a.code
    L = [f"[보유 피드백] {nm}({a.code}) — 시스템 v1 / CAN SLIM v1.1",
         f"매수 {a.entry} @ {a.price:,.0f} × {a.shares:.0f}주 "
         f"(투입 {a.price*a.shares:,.0f}원)", ""]

    ks = series("%5EKS11")
    st = series(yahoo_symbol(a.code, a.market))
    if not st:
        print("시세 조회 실패", file=sys.stderr)
        return
    sd, sc, sv = st

    def idx(d, ds):
        cand = [k for k in range(len(d)) if d[k] <= ds]
        return cand[-1] if cand else None

    li = len(sc) - 1
    ei = idx(sd, a.entry)
    cur = sc[li]
    pl = cur / a.price - 1

    # ★ 마스터 스위치
    L.append("== ★ 마스터 스위치 (코스피 국면) ==")
    if ks:
        kd, kc, _ = ks
        ki = len(kc) - 1
        m200 = sma(kc, ki, 200)
        m200p = sma(kc, ki - 20, 200) if ki >= 220 else None
        bear = (m200 is not None and m200p is not None
                and kc[ki] < m200 and m200 < m200p)
        L.append(f"  코스피 {kd[ki]} {kc[ki]:,.0f} | 200일선 "
                 f"{m200:,.0f} | 200일선 추세 "
                 f"{'하락' if (m200p and m200<m200p) else '상승/횡보'}")
        L.append(f"  → 약세 스위치: {'★ON = 보유 전량 현금화 신호' if bear else 'OFF (강세/중립 — 시스템 가동)'}")
    else:
        L.append("  코스피 조회 실패 — 국면 판정 결손")
        bear = None
    L.append("")

    # 현 손익·위치
    hi52 = max(sc[max(0, li - 252):li + 1])
    m50, m200s = sma(sc, li, 50), sma(sc, li, 200)
    peak_since = max(sc[ei:li + 1]) if ei is not None else cur
    L += ["== 현재 상태 ==",
          f"  현재가 {sd[li]} {cur:,.0f} | 평가손익 {pl*100:+.1f}% "
          f"({(cur-a.price)*a.shares:+,.0f}원)",
          f"  52주고가 대비 {cur/hi52*100:.1f}% | 50일선 "
          f"{(cur/m50-1)*100:+.1f}% | 200일선 "
          f"{(cur/m200s-1)*100:+.1f}%" if m50 and m200s else "  (이평 결손)",
          f"  매수후 최고 {peak_since:,.0f} → 현재 고점대비 "
          f"{(cur/peak_since-1)*100:+.1f}%",
          ""]

    # ③/④ 손절·트레일
    dis = a.price * 0.85
    trail = peak_since * 0.65
    L += ["== ③④ 손절·매도 라인 (시스템 v1) ==",
          f"  −15% 재해 손절선: {dis:,.0f} "
          f"({'현재가 이미 하회 = 청산 검토' if cur < dis else f'현재가까지 여유 {(cur/dis-1)*100:+.1f}%'})",
          f"  넓은 트레일(매수후 고점 −35%): {trail:,.0f} "
          f"({'하회 = 매도' if cur < trail else '유지 중'})",
          ""]

    # ② 진입 타이밍 평가 (그날)
    L.append(f"== ② 진입 타이밍 평가 @ {a.entry} ==")
    if ei is not None and ei >= 252:
        v50 = (sum(sv[ei - 50:ei]) / 50
               if len(sv) > ei and ei >= 50 and sum(sv[ei - 50:ei]) else None)
        ehi = max(sc[ei - 252:ei + 1])
        em50, em200 = sma(sc, ei, 50), sma(sc, ei, 200)
        r52 = (sc[ei] / sc[ei - 252] - 1) * 100 if sc[ei - 252] > 0 else None
        quiet = v50 and sv[ei] / v50 <= 1.0
        below = sc[ei] <= 0.88 * ehi
        near50 = em50 and abs(sc[ei] / em50 - 1) <= 0.10
        L.append(f"  거래량/50일 {round(sv[ei]/v50,2) if v50 else '?'}배 "
                 f"({'조용 ✅' if quiet else '많음 ✗(돌파·추격형)'})")
        L.append(f"  52주고가 대비 {round(sc[ei]/ehi*100,1)}% "
                 f"({'한참 아래 ✅' if below else '신고가 근접 ✗(추격)'})")
        L.append(f"  50일선 {round((sc[ei]/em50-1)*100,1) if em50 else '?'}% "
                 f"({'근처 ✅' if near50 else '벗어남'}) | "
                 f"52주수익(L프록시) {round(r52,0) if r52 is not None else '?'}%")
        sig = sum([bool(quiet), bool(below), bool(near50)])
        L.append(f"  → 5신호 중 가격3축 {sig}/3 충족 "
                 f"({'조용한 눌림목 재가속 부합' if sig>=2 else '⚠ 시스템 매수신호 *불일치* (조용한 눌림목 아님)'})")
    else:
        L.append("  진입일 데이터 부족(252봉 미만) — 평가 결손")
    L.append("")

    # 종료 매매 평가 (--sell-price 주어지면)
    if a.sell_price and a.sell_date:
        si = idx(sd, a.sell_date)
        L.append(f"== 🔁 종료 매매 평가 (매도 {a.sell_date} @ "
                 f"{a.sell_price:,.0f}) ==")
        if si is not None and ei is not None:
            realized = a.sell_price / a.price - 1
            held = si - ei
            pk = max(sc[ei:si + 1])
            disL = a.price * 0.85
            trL = pk * 0.65
            sys_trig = (a.sell_price <= disL or a.sell_price <= trL)
            postmax = max(sc[si:]) if si < len(sc) - 1 else sc[si]
            cont = postmax / a.sell_price - 1
            nowp = sc[li]
            # 매도일 ★스위치
            sbear = None
            if ks:
                kj = idx(kd, a.sell_date)
                if kj is not None and kj >= 220:
                    km, kmp = sma(kc, kj, 200), sma(kc, kj - 20, 200)
                    sbear = (km and kmp and kc[kj] < km and km < kmp)
            L += [
                f"  실현수익 {realized*100:+.1f}% "
                f"({(a.sell_price-a.price)*a.shares:+,.0f}원) · 보유 "
                f"{held}거래일",
                f"  매도일 ★약세스위치: "
                f"{'ON(국면상 매도 정당)' if sbear else 'OFF(강세 — 시스템은 보유 권고 국면)' if sbear is not None else '결손'}",
                f"  −15%재해선 {disL:,.0f} · 보유중 고점 {pk:,.0f} → "
                f"트레일(고점−35%) {trL:,.0f}",
                f"  매도가가 시스템 매도라인 도달? "
                f"{'예(규칙 매도)' if sys_trig else '아니오 → ④ 위반: 강세장·재해선·트레일 안 깼는데 조기 익절'}",
                f"  ▶ 매도 후 최고 {postmax:,.0f} (매도가 대비 "
                f"{cont*100:+.0f}%) · 현재 {sd[li]} {nowp:,.0f} "
                f"({(nowp/a.sell_price-1)*100:+.0f}%)",
                f"  = 기회비용: 시스템대로 보유했다면 +{cont*100:.0f}% "
                f"추가 구간을 {'포기함' if cont>0.1 else '미미'}",
            ]
        else:
            L.append("  매도일/매수일 인덱스 결손 — 평가 불가")
        L.append("")

    # I 수급 (최근 60거래일)
    L.append("== I 수급 (최근 ~60거래일, 네이버) ==")
    try:
        fr = sorted(fetch_naver_org_flow(a.code, pages=10, sleep_ms=150),
                    key=lambda r: r["date"])[-60:]
        if len(fr) >= 30:
            fg = sum(r.get("fgn_net") or 0 for r in fr)
            og = sum(r.get("org_net") or 0 for r in fr)
            L.append(f"  외국인 {fg:+,}주 | 기관 {og:+,}주 "
                     f"({'매집(상승 연료 우호)' if (fg>0 or og>0) else '순매도(연료 약화 — 주의)'})")
        else:
            L.append("  결손(frgn 60일 미도달)")
    except Exception:
        L.append("  결손(frgn 조회 실패)")
    L += ["",
          "== 종합 판정 (시스템 v1 / CAN SLIM v1.1) ==",
          "아래 원칙으로 사용자 자가판정 보조 (확정 매매지시 아님·확률 도구):",
          "1) ★약세 스위치 ON이면 — *국면 우선*: 보유 청산(현금화) 신호.",
          "2) OFF면 시스템 가동 — ②진입이 '추격형'이었어도 ③−15% 재해선",
          "   안 깨고 ④트레일 유지·★OFF면 *정상 눌림에 팔지 말고 보유*.",
          "3) ③−15% 하회 또는 ④트레일 하회 = 매도. 진입이 신고가 추격",
          "   (②불일치)이면 변동성 큼 → 비중·−15%선 엄수.",
          "4) L(52주수익 강?)·I(매집?)가 받쳐주면 보유 근거 강화, 둘 다",
          "   꺾이면 약세 스위치 전이라도 경계.",
          "한계: RS는 전수 백분위 아닌 52주수익 프록시·종가·단일조회·",
          "거래비용 무관. 시스템은 강세장 검증·약세장은 ★스위치가 방어."]
    out = (Path(__file__).resolve().parents[2] / "research"
           / "oneil-model-book" / f"_feedback_{a.code}.txt")
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()

"""약세장 감지 -> 현금화(보유 청산) 3단계 모델 검증.

목적(사용자 정정 2026-05-17): 약세장이면 들고 있던 주식을 팔아 현금으로
빼서, 모르고 들고 있다 똥값 되는 걸 피한다. 매수 중단이 아니라 *보유
청산(현금화)* 신호.

3단계 + 재진입:
  정상   : 100% 보유
  조심   : 50% 보유(절반 현금화) - 고점 꺾임 초기에 일찍
  약세   : 0% 보유(전량 현금화) - 검증된 "추세 단독"
  재진입 : 신호 정상 복귀 시 현금 재투입

약세(전량) 트리거 = 추세 단독(검증 완료):
  코스피 종가 < 200일선 AND 200일선 < 20거래일 전 200일선
조심(절반) 트리거 후보 - 각각 따로 검증, 백테스트로 택일:
  a 기울기 : 200일선 < 20거래일 전 200일선 (종가 무관, 가장 이름)
  b 깊이   : 코스피 <= 직전 252거래일 고점 x 0.90 (1년 고점 -10%)
  c 시장폭 : 유니버스 200일선 위 비율 < 0.50 (약세는 < 0.40)
  d 2of3   : a,b,c 중 2개 이상 (c는 시장폭 가용일만)

자산 시뮬(보유 자산 = 코스피 지수, 시장국면 스위치라 지수가 정직한
프록시 - 종목 선택/생존자 편향 배제):
  끝까지보유 vs 이분법(약세 전량만) vs 3단계(조심 절반+약세 전량+재진입)
  창1 BEAR  2021-07-06(고점) ~ 2023-12-31  (2022 폭락+회복)
  창2 BULL  2025-04-09(검증 바닥) ~ 2026-05-15 (~3배 상승, 헛매도 검증)

지표: 회피 폭락폭 / 최대낙폭 / 최종가치 / 헛매도(강세장 미보유%) /
재진입 지각(바닥 후 정상복귀 거래일) / 조심 선제성(고점 대비).

데이터: Yahoo ^KS11(일봉, 증권사 일봉과 대조 검증됨) + _breadth.json
(2022-03~, 2021~22초 결손=추정 안 함). 현금 이자 0(보수적). 인-샘플
단일 사이클 종가, 거래비용/세금 미반영. 환각 금지.
사용: python analyze_regime_graded.py [--seed 7] [--cash-rate 0]
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from canslim_lib.fetch import fetch_yahoo_chart  # noqa: E402

CY = (Path(__file__).resolve().parents[2] / "research" / "oneil-model-book"
      / "cycles" / "c2024-12")
PEAK = "2021-07-06"          # 2021 코스피 실제 고점(직전 강세장 종료)
BEAR_W = ("2021-07-06", "2023-12-31")
BULL_W = ("2025-04-09", "2026-05-15")   # 2025-04-09 = 검증된 관세쇼크 바닥


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def load_breadth():
    """date -> (200일선 위 비율). 캐시 우선, 없으면 유니버스로 빌드."""
    bc = CY / "_breadth.json"
    if bc.exists():
        return json.loads(bc.read_text(encoding="utf-8"))
    U = json.loads((CY / "_universe_prices_5y.json")
                   .read_text(encoding="utf-8"))
    above = {}
    for s in U.values():
        d, c = s.get("d"), s.get("c")
        if not d or not c or len(c) < 210:
            continue
        run = sum(c[0:200])
        for i in range(199, len(c)):
            if i > 199:
                run += c[i] - c[i - 200]
            r = above.setdefault(d[i], [0, 0])
            r[1] += 1
            if c[i] > run / 200:
                r[0] += 1
    br = {dt: (v[0] / v[1]) for dt, v in above.items() if v[1] >= 200}
    bc.write_text(json.dumps(br), encoding="utf-8")
    return br


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)   # 결정적(관례 유지)
    ap.add_argument("--cash-rate", type=float, default=0.0)
    args = ap.parse_args()

    ch = fetch_yahoo_chart("%5EKS11", period1=_ep("2020-01-01"),
                           period2=_ep("2026-12-31"), interval="1d")
    if not ch or not ch.get("closes"):
        print("KOSPI fetch failed", file=sys.stderr)
        return
    d = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
         for t in ch["timestamps"]]
    c = ch["closes"]
    n = len(c)
    breadth = load_breadth()

    # 일별 신호 (point-in-time: c[0..i]만 사용)
    sig = []   # i -> dict(bear, a, b, c_, d_, br_avail)
    for i in range(n):
        if i < 252:
            sig.append(None)
            continue
        ma = sum(c[i - 199:i + 1]) / 200
        ma_prev = sum(c[i - 219:i - 19]) / 200
        hi252 = max(c[i - 251:i + 1])
        slope_down = ma < ma_prev
        bear = (c[i] < ma) and slope_down            # 약세 = 추세 단독
        a = slope_down                               # 조심 a
        b = c[i] <= 0.90 * hi252                     # 조심 b
        br = breadth.get(d[i])
        c_ = (br is not None and br < 0.50)           # 조심 c
        cand = [a, b] + ([c_] if br is not None else [])
        d_ = sum(1 for x in cand if x) >= 2           # 조심 d (2of3)
        sig.append({"bear": bear, "a": a, "b": b, "c": c_, "d": d_,
                    "br_avail": br is not None})

    CAND = ("a", "b", "c", "d")
    CLABEL = {"a": "기울기(200일선 꺾임)", "b": "깊이(1년고점-10%)",
              "c": "시장폭(<50%)", "d": "2of3(a/b/c)"}

    def state_frac(i, strat, cand=None):
        """그날 목표 보유비중. buyhold=항상1, binary=약세만0,
        graded=약세0/조심0.5/정상1."""
        s = sig[i]
        if s is None:
            return 1.0
        if strat == "buyhold":
            return 1.0
        if s["bear"]:
            return 0.0
        if strat == "binary":
            return 1.0
        return 0.5 if s[cand] else 1.0              # graded

    def simulate(w0, w1, strat, cand=None):
        i0 = next((i for i in range(n) if d[i] >= w0), None)
        i1 = next((i for i in range(n - 1, -1, -1) if d[i] <= w1), None)
        if i0 is None or i1 is None or i0 > i1:
            return None
        V = 1.0
        units = V / c[i0]
        cash = 0.0
        peakV = V
        maxdd = 0.0
        reentry_lag = None
        # 바닥(창 내 코스피 최저 종가) 인덱스
        bi = min(range(i0, i1 + 1), key=lambda k: c[k])
        for i in range(i0, i1 + 1):
            V = units * c[i] + cash
            f = state_frac(i, strat, cand)
            units = f * V / c[i]
            cash = (1 - f) * V
            peakV = max(peakV, V)
            maxdd = min(maxdd, V / peakV - 1)
            if cash > 0:
                cash *= (1 + args.cash_rate / 252)
            if (reentry_lag is None and i >= bi
                    and abs(f - 1.0) < 1e-9 and strat != "buyhold"):
                reentry_lag = i - bi
        Vend = units * c[i1] + cash
        return {"Vend": Vend, "maxdd": maxdd, "reentry_lag": reentry_lag,
                "bottom": d[bi], "i0": i0, "i1": i1}

    # 조심 선제성 & 강세장 헛매도(비보유 비율)
    def cand_diag(cand):
        ip = next((i for i in range(n) if d[i] >= PEAK), None)
        first = None
        for i in range(ip, n):
            s = sig[i]
            if s and (s["bear"] or s[cand]):
                first = i
                break
        peak_lag = (first - ip) if first is not None else None
        peak_dd = (c[first] / c[ip] - 1) * 100 if first is not None else None
        b0 = next(i for i in range(n) if d[i] >= BULL_W[0])
        b1 = next(i for i in range(n - 1, -1, -1) if d[i] <= BULL_W[1])
        bd = [sig[i] for i in range(b0, b1 + 1) if sig[i]]
        nb = len(bd)
        fa_bear = 100 * sum(1 for s in bd if s["bear"]) / nb if nb else 0
        fa_caut = (100 * sum(1 for s in bd if (not s["bear"]) and s[cand])
                   / nb if nb else 0)
        return peak_lag, peak_dd, fa_bear, fa_caut, first

    out = []
    out.append("[3단계 약세 현금화 모델] 보유자산=코스피지수, "
               "현금이자 %g%%/yr" % (args.cash_rate * 100))
    out.append("약세=추세단독(종가<200일선 & 200일선하락) 전량현금화 / "
               "조심=후보별 절반현금화 / 정상복귀=재투입")
    out.append("창 BEAR %s~%s · BULL %s~%s" %
               (BEAR_W[0], BEAR_W[1], BULL_W[0], BULL_W[1]))
    out.append("")

    bh_bear = simulate(*BEAR_W, "buyhold")
    bh_bull = simulate(*BULL_W, "buyhold")
    bn_bear = simulate(*BEAR_W, "binary")
    bn_bull = simulate(*BULL_W, "binary")

    out.append("== 200일선 후행성 (사용자 지적 실측) ==")
    ip = next(i for i in range(n) if d[i] >= PEAK)
    fb = next((i for i in range(ip, n) if sig[i] and sig[i]["bear"]), None)
    out.append("2021 고점 %s 코스피 %.1f" % (d[ip], c[ip]))
    if fb is not None:
        out.append("약세(추세단독) 첫 점등 %s 코스피 %.1f = 고점대비 "
                   "%+.1f%% (%d거래일 늦음)"
                   % (d[fb], c[fb], (c[fb] / c[ip] - 1) * 100, fb - ip))
    out.append("코스피 실제 바닥 %s %.1f = 고점대비 %+.1f%% (안 팔면 여기)"
               % (bh_bear["bottom"],
                  c[next(i for i in range(n) if d[i] == bh_bear['bottom'])],
                  (min(c[bh_bear["i0"]:bh_bear["i1"] + 1]) / c[ip] - 1) * 100))
    out.append("")

    out.append("== 자산 비교 (시작가치 1.000) ==")
    out.append("전략              | BEAR 최종 | BEAR 최대낙폭 | "
               "BULL 최종 | BULL/끝까지보유")
    out.append("끝까지 보유        |   %.3f  |   %+.1f%%   |  %.3f  | "
               "%.0f%% (기준)"
               % (bh_bear["Vend"], bh_bear["maxdd"] * 100,
                  bh_bull["Vend"], 100))
    out.append("이분법(약세전량)   |   %.3f  |   %+.1f%%   |  %.3f  | %.0f%%"
               % (bn_bear["Vend"], bn_bear["maxdd"] * 100, bn_bull["Vend"],
                  100 * bn_bull["Vend"] / bh_bull["Vend"]))
    for cd in CAND:
        gb = simulate(*BEAR_W, "graded", cd)
        gl = simulate(*BULL_W, "graded", cd)
        out.append("3단계+조심%s        |   %.3f  |   %+.1f%%   |  %.3f  | "
                   "%.0f%%"
                   % (cd, gb["Vend"], gb["maxdd"] * 100, gl["Vend"],
                      100 * gl["Vend"] / bh_bull["Vend"]))
    out.append("")

    out.append("== 재진입 지각 (코스피 바닥 후 정상복귀까지 거래일) ==")
    out.append("이분법 %s거래일" % bn_bear["reentry_lag"])
    for cd in CAND:
        gb = simulate(*BEAR_W, "graded", cd)
        out.append("3단계+조심%s %s거래일" % (cd, gb["reentry_lag"]))
    out.append("")

    out.append("== 조심 후보별 진단 ==")
    out.append("후보 | 2021고점→첫점등(거래일/고점대비%) | "
               "BULL 약세% | BULL 조심%")
    for cd in CAND:
        pl, pd, fab, fac, _ = cand_diag(cd)
        out.append("%-22s | %s거래일 / %s%% | %.0f%% | %.0f%%"
                   % (CLABEL[cd],
                      pl if pl is not None else "-",
                      ("%+.1f" % pd) if pd is not None else "-",
                      fab, fac))
    out.append("")
    out.append("== 읽는 법 ==")
    out.append("좋은 모델 = BEAR 최대낙폭 작게(끝까지보유 대비 폭락 회피)")
    out.append("+ BULL 최종이 끝까지보유에 가깝게(헛매도 손실 작게)")
    out.append("+ 재진입 지각 작게. 둘 다 좋아야 채택, 한쪽만이면 보류.")
    out.append("조심 첫점등이 약세보다 이를수록(거래일 작음) 선제성 큼.")
    out.append("== 한계 (정직) ==")
    out.append("시장폭 2022-03부터(2021~22초 결손→조심c/d 그 구간 평가")
    out.append("불가, 추정 안 함). 단일 BEAR/BULL·인-샘플·종가·현금이자")
    out.append("%g·거래비용/세금 미반영·일별 리밸런스(실제 주1회 점검)."
               % args.cash_rate)
    out.append("보유자산=지수(개별종목 분산 보유 프록시). 방향만, 절대")
    out.append("수치 사이클 의존. 2018·2008 지수형 별도 차기.")

    fn = "_regime_graded_s%d.txt" % args.seed
    (CY / fn).write_text("\n".join(out), encoding="utf-8")
    print("saved: %s" % fn, file=sys.stderr)


if __name__ == "__main__":
    main()

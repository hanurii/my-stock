"""[메가캡 톱-N 집중] narrow 사이클(c2024형) 도구 시도.

KOSPI 70% = 상위 20종목 → '분산'으론 못 이김. '집중' 게임으로 전환.
매주 *시총 상위 30* 안에서 N(3,5)개만 보유. 3가지 *고르는 법*을
실시간(미래 모름)으로 동시 테스트:
  A. 252일 수익률 1등 (단순 모멘텀)
  B. 252+63+21일 합산 랭크 (다(多)타임프레임)
  C. 외인 60일 순매수 강도 (한국 특화·수급)

출구: −15% 손절·★약세현금화·주간 리밸런스. 비용 0.66% 왕복.
사후·종가·일별·생존자잔존·n=2·주식수 현재 단일값(소오차)·
B/C 는 데이터 가용 구간 한정. analyze_doppelganger/analyze_equity_curve
헬퍼 재사용.
사용: python analyze_megatop.py --src c2024-12 [--n 3]
"""
import argparse
import bisect
import json
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import analyze_equity_curve as AE                       # noqa: E402
import analyze_equity_curve_rt as RT                    # noqa: E402
import analyze_doppelganger as AD                       # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "research" / "oneil-model-book"
CY = OUT / "cycles"


def score(method, c, j, flow=None, lookback=252):
    """반환 = 점수(높을수록 좋음). 데이터 부족 → None."""
    if j < lookback or c[j - lookback] <= 0:
        return None
    r252 = c[j] / c[j - lookback] - 1
    if method == "A":
        return r252
    if method == "B":
        if j < 63 or c[j - 63] <= 0 or j < 21 or c[j - 21] <= 0:
            return None
        r63 = c[j] / c[j - 63] - 1
        r21 = c[j] / c[j - 21] - 1
        return r252 + r63 + r21                # 합산(단순·균등)
    if method == "C":
        # 외인 60일 순매수 강도 (flow 결손 = 평가 불가)
        if not flow:
            return None
        fd, fg, _og = flow
        fi = bisect.bisect_right(fd, _t_now) - 1
        if fi < 40:
            return None
        a, b = max(0, fi - 59), fi + 1
        return sum(fg[a:b])                    # 단순 합(절대치)
    return None


_t_now = None                                  # score()에서 t 전달용


def pit_mcap(c, j, shares_code):
    """점별 시총(억) = close[j] × 주식수."""
    return c[j] * shares_code / 1e8 if shares_code else 0


def run_method(src, method, n, cost,
               top_k=30, rebal_step=5, lookback=252,
               window=None, markets=None, stop_pct=-0.15,
               trail_pct=None):
    U = AD.pick_universe_file(src)
    codes_d = {k: (s["d"], s["c"]) for k, s in U.items()
               if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _ in codes_d.values() for x in d})
    start, end = al[0], al[-1]
    rs0 = al[min(len(al) - 1, 260)]
    kd, kc = AE.kospi_series()
    sh = RT.load_shares()
    fm = RT.load_flow(src) if method == "C" else {}
    mk = None
    if markets:
        mp = OUT.parent / "oneil-model-book" / "_universe_market.json"
        # OUT not defined here; resolve via path
        from pathlib import Path as _P
        mkp = _P(__file__).resolve().parents[2] / "research" \
            / "oneil-model-book" / "_universe_market.json"
        if mkp.exists():
            mp_all = json.loads(mkp.read_text(encoding="utf-8"))
            mk = {c for c, m in mp_all.items() if m in markets}
            codes_d = {k: v for k, v in codes_d.items() if k in mk}

    if window:
        wlo, whi = window
        axis = [t for t in al if max(rs0, wlo) <= t <= min(end, whi)]
    else:
        axis = [t for t in al if rs0 <= t <= end]
    pos, cash = {}, 1.0
    eq_d, eq, trades = [], [], []
    global _t_now
    for ti, t in enumerate(axis):
        on = not AE.kbear_at(kd, kc, t)
        # 매일 손절·★스위치
        for code in list(pos):
            d, c = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i < 0:
                continue
            px = c[i]
            p = pos[code]
            peak = max(p.get("peak", p["entry"]), px)
            p["peak"] = peak
            trail_hit = (trail_pct is not None
                         and px <= peak * (1 + trail_pct))
            if (px <= p["entry"] * (1 + stop_pct)
                    or trail_hit or not on):
                cash += p["inv"] * (px / p["entry"]) * (1 - cost)
                trades.append(px / p["entry"] - 1)
                del pos[code]
        # 리밸런스 주기 + ★ON
        if on and ti % rebal_step == 0:
            _t_now = t
            # 시총 상위 top_k
            cap = []
            for code, (d, c) in codes_d.items():
                j = bisect.bisect_right(d, t) - 1
                if j < lookback or c[j] <= 0:
                    continue
                mc = pit_mcap(c, j, sh.get(code, 0))
                if mc > 0:
                    cap.append((mc, code, j, c))
            cap.sort(reverse=True)
            top30 = cap[:top_k]
            # 점수
            scored = []
            for mc, code, j, c in top30:
                s = score(method, c, j, fm.get(code), lookback)
                if s is not None:
                    scored.append((s, code, c[j]))
            scored.sort(reverse=True)
            target = {code: px for _, code, px in scored[:n]}
            # 보유 외 매도
            for code in list(pos):
                if code not in target:
                    d, c = codes_d[code]
                    i = bisect.bisect_right(d, t) - 1
                    px = c[i] if i >= 0 else pos[code]["entry"]
                    cash += pos[code]["inv"] * (px / pos[code]["entry"]) \
                        * (1 - cost)
                    trades.append(px / pos[code]["entry"] - 1)
                    del pos[code]
            # 신규 매수(등가중, 잔여 슬롯)
            slot = max(1, n)
            for code, px in target.items():
                if code in pos or cash <= 1e-9:
                    continue
                buy = min(cash, cash / (slot - len(pos)))
                cash -= buy
                pos[code] = {"inv": buy * (1 - cost),
                             "entry": px, "peak": px, "buy_dt": t}
        # 자본 평가
        mv = cash
        for code, p in pos.items():
            d, c = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i >= 0:
                mv += p["inv"] * (c[i] / p["entry"])
        eq_d.append(t)
        eq.append(mv)
    return eq_d, eq, trades


def bull_chain(ed, eq, kd, kc):
    ks = [kc[max(0, bisect.bisect_right(kd, x) - 1)] for x in ed]
    bl = [RT.bull_on(kd, kc, x) for x in ed]

    def ch(s):
        v = 1.0
        for i in range(1, len(s)):
            if bl[i] and s[i - 1] > 0:
                v *= s[i] / s[i - 1]
        return v
    bd = sum(1 for i in range(1, len(bl)) if bl[i])
    yb = bd / 252

    def cg(x):
        return (x ** (1 / yb) - 1) * 100 if yb > 0 and x > 0 else 0
    return cg(ch(eq)), cg(ch(ks))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="c2024-12",
                    choices=["c2024-12", "c2020-03"])
    ap.add_argument("--cost", type=float, default=0.0066)
    a = ap.parse_args()

    kd, kc = AE.kospi_series()
    L = [f"[메가캡 톱-N 집중] [{a.src}] — 시총 상위 30 안에서 N=3,5",
         "고르는 법 A(1년1등) / B(다단계) / C(외인강도) 동시 비교.",
         "주간 리밸런스·−15%손절·★스위치·비용0.66%. 강세장 vs KOSPI.",
         "=" * 66,
         f"  {'구성':<24}| 전 ×배 | 강세장 시 vs KOSPI | 거래 | 판정"]
    rj = {}
    for n in [3, 5]:
        for m in ["A", "B", "C"]:
            ed, eq, tr = run_method(a.src, m, n, a.cost)
            mm = AE.metrics(ed, eq)
            sCg, kCg = bull_chain(ed, eq, kd, kc)
            tag = {"A": "1년1등모멘텀", "B": "다단계모멘텀",
                   "C": "외인강도"}[m]
            nm = f"{tag} N={n}"
            rj[nm] = {"final": mm["final"], "bull_sys": sCg,
                      "bull_kospi": kCg, "trades": len(tr)}
            L.append(f"  {nm:<24}| ×{mm['final']:.2f} | "
                     f"시{sCg:+5.0f}% vs K{kCg:+5.0f}% | {len(tr):3d} | "
                     f"{'승' if sCg > kCg else '패'}")
    best = max(rj.items(), key=lambda kv: kv[1]["bull_sys"])
    L += ["-" * 66,
          f"■ 최고 구성: {best[0]} — 강세장 시스템 "
          f"{best[1]['bull_sys']:+.0f}% vs KOSPI "
          f"{best[1]['bull_kospi']:+.0f}% → "
          f"{'★KOSPI 상회!' if best[1]['bull_sys'] > best[1]['bull_kospi'] else 'KOSPI 미달'}",
          "해석: 어느 *고르는 법*이 narrow 사이클(c2024형)에 통하나의",
          "  데이터 답. 메가캡 톱-N 집중이 KOSPI 상회면 = '큰 거인",
          "  중에서 1등 짚기'가 가능 = narrow 사이클용 도구 발견.",
          "  전부 미달이면 = narrow 사이클에선 그냥 KOSPI ETF 가 답.",
          "한계: 사후·종가·일별·n=2·주식수=현재단일값·B/C 데이터",
          "  결손 시 평가 불가·N=3 매우 집중(단일 종목 변동성↑)·",
          "  메가캡=효율적 시장(알파 발견 더 어려움)."]
    txt = "\n".join(L)
    tag = "" if a.src == "c2024-12" else "_c2020"
    (OUT / f"_megatop{tag}.txt").write_text(txt, encoding="utf-8")
    (CY / a.src / "megatop_rows.json").write_text(
        json.dumps(rj, ensure_ascii=False, indent=1), encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 메가캡 톱-N 집중 [{a.src}]\n\n```\n{txt}\n```\n")
    print(txt)


if __name__ == "__main__":
    main()

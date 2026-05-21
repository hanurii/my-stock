"""한국형 매수 규칙 v1 — 비위너 대조군 정밀도 검증.

buy_timing.md 의 한계("위너=생존자 표본 → 거짓양성률 미검증")를 직접 측정.
방법: c2024-12 *전 종목*(_universe_prices.json, close-only, 네트워크 불요)에
v1 트리거(추세확인: 종가>상승50일선 & >20거래일전, 사이클 저점 이후 최초
발동)를 적용 → 트리거가 발동한 모든 종목의 *이후 최대 상승* 분포로 정밀도
(=발동 종목 중 큰 상승 비율)·거짓양성·기저율 대비 lift·위너리스트 적중률
산출. 한계: 사이클 내 결과를 사후 측정(look-ahead)·상장폐지 제외(생존자).
즉 '트리거의 변별력' 측정이지 완전한 아웃오브샘플 백테스트는 아님(명시).

사용:  python analyze_buy_timing_control.py   (OMB_CYCLE 로 사이클 선택)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cyclecfg  # noqa: E402

DIR = cyclecfg.DIR
BUY_MD = cyclecfg.RESEARCH / "buy_timing.md"
MIN_FWD = 20          # 트리거 후 최소 20거래일 잔여
THR = [50, 100, 200]  # winner-grade 컷오프(%) — 위너 잔존상승 중앙 +376% 맥락


def first_trigger(c, anchor_i):
    """사이클 저점 이후 최초 추세확인일(analyze_buy_timing.confirmed 동일)."""
    n = len(c)
    ti = min(range(anchor_i, n), key=lambda k: c[k])

    def sma(j, w):
        return sum(c[j - w + 1:j + 1]) / w if j >= w - 1 else None

    for d in range(max(ti, 60), n - MIN_FWD):
        m, mp = sma(d, 50), sma(d - 10, 50)
        if m and mp and c[d] > m and m > mp and c[d] > c[d - 20]:
            return ti, d
    return ti, None


def main():
    up = DIR / "_universe_prices.json"
    if not up.exists():
        print("_universe_prices.json 없음 (compute_rs 먼저)", file=sys.stderr)
        return
    U = json.loads(up.read_text(encoding="utf-8"))
    wf = json.loads((DIR / "winners_final.json").read_text(encoding="utf-8"))
    win_codes = {w["code"] for w in wf["winners"]}
    anchor = cyclecfg.ANCHOR

    valid = 0          # 사이클 데이터 충분 종목
    triggered = []     # (code, fwd_max%, mom250) 트리거 발동 종목
    trig_codes = set()
    base_movers = {t: 0 for t in THR}   # 트리거 무관, 저점→이후최대 ≥t (기저율)

    for code, s in U.items():
        d, c = s.get("d"), s.get("c")
        if not d or not c or len(c) < 150:
            continue
        ai = next((k for k in range(len(d)) if d[k] >= anchor), None)
        if ai is None or len(c) - ai < 80:
            continue
        valid += 1
        ti, g = first_trigger(c, ai)
        # 기저율: 저점 이후 자체 최대 상승
        if c[ti] > 0:
            base_max = (max(c[ti:]) / c[ti] - 1) * 100
            for t in THR:
                if base_max >= t:
                    base_movers[t] += 1
        if g is None or c[g] <= 0:
            continue
        fwd = (max(c[g:]) / c[g] - 1) * 100
        # L축 RS 프록시: 트리거일 기준 직전 250거래일 모멘텀(횡단 백분위용 raw)
        mom = (c[g] / c[g - 250] - 1) * 100 if g >= 250 and c[g - 250] > 0 else None
        triggered.append((code, fwd, mom))
        trig_codes.add(code)

    nt = len(triggered)
    fwd_vals = sorted(x for _, x, _ in triggered)
    # L축 결합: 트리거 발동 종목 중 250일 모멘텀 상위 20%(RS≈80 프록시)
    momed = [(co, fw, mo) for co, fw, mo in triggered if mo is not None]
    momed.sort(key=lambda r: r[2], reverse=True)
    top = momed[:max(1, len(momed) // 5)]
    nL = len(top)
    fwdL = sorted(fw for _, fw, _ in top)
    trigL_codes = {co for co, _, _ in top}

    def pct_ge(t):
        return 100 * sum(1 for x in fwd_vals if x >= t) / nt if nt else 0

    def pct_geL(t):
        return 100 * sum(1 for x in fwdL if x >= t) / nL if nL else 0

    def med(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if xs else 0

    L = [f"[{cyclecfg.CYCLE_ID}] 매수규칙 v1 — 비위너 대조군 정밀도",
         f"전 종목 {valid}개(데이터 충분) 중 v1 트리거 발동 {nt}개 "
         f"(발동률 {round(100*nt/valid,1) if valid else 0}%)",
         "정의: 트리거=사이클 저점 이후 최초 '종가>상승50일선 & >20거래일전'.",
         f"  발동 종목 이후최대상승 중앙 {round(med(fwd_vals),1)}%.",
         "",
         "== 정밀도(발동 종목이 큰 상승으로 이어진 비율) vs 기저율 ==",
         "컷오프 | 정밀도(발동중) | 기저율(전종목) | lift",
         ]
    for t in THR:
        prec = pct_ge(t)
        base = 100 * base_movers[t] / valid if valid else 0
        lift = (prec / base) if base else 0
        L.append(f"≥+{t}% | {round(prec,1)}% | {round(base,1)}% | {round(lift,2)}x")

    L += ["",
          f"== v1 + L축(RS프록시: 발동 중 250일모멘텀 상위20%, n={nL}) ==",
          "컷오프 | 정밀도 | 기저율 | lift",
          ]
    for t in THR:
        precL = pct_geL(t)
        base = 100 * base_movers[t] / valid if valid else 0
        liftL = (precL / base) if base else 0
        L.append(f"≥+{t}% | {round(precL,1)}% | {round(base,1)}% | {round(liftL,2)}x")
    twL = len(trigL_codes & win_codes)
    L.append(f"RS결합 발동 중 위너비중: {twL}/{nL} "
             f"({round(100*twL/nL,1) if nL else 0}%)  "
             f"[단독 {round(100*len(trig_codes & win_codes)/nt,1) if nt else 0}% → 결합 시]")

    # 위너리스트 적중(재현·정밀)
    tw = len(trig_codes & win_codes)
    L += ["",
          "== 위너리스트(상위200) 대조 ==",
          f"트리거가 위너 포착(recall) : {tw}/{len(win_codes)} "
          f"({round(100*tw/len(win_codes),1)}%)",
          f"발동 중 위너 비중(정밀)    : {tw}/{nt} "
          f"({round(100*tw/nt,1) if nt else 0}%)  "
          f"[비위너 오발동 {nt - tw}개]",
          "",
          "== 정직한 한계 ==",
          "결과를 사이클 내 사후 측정(look-ahead)·상장폐지 종목 제외(생존자).",
          "트리거의 *변별력* 측정이지 완전 아웃오브샘플 백테스트 아님.",
          "거짓양성=발동했으나 큰 상승 미발생 비율(위 1-정밀도). v1은 여전히",
          "'예측 후보' — 진정한 OOS(미래 데이터)·거래비용 반영은 추후 과제.",
          ]
    block = "\n".join(L)
    (DIR / "_buytiming_control.txt").write_text(block, encoding="utf-8")
    print(f"control saved: {DIR}/_buytiming_control.txt  "
          f"(valid {valid}, trig {nt})", file=sys.stderr)


if __name__ == "__main__":
    main()

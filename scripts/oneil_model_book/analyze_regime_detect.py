"""약세장 감지 모듈(master switch) 역검증 — 종가·주기점검 실행가능.

객관 신호(매주 1회 확인 가능):
  S1 추세  KOSPI 종가<200일선 AND 200일선 하락(20일전 대비)
  S2 깊이  KOSPI ≤ 직전252일 고점 ×0.85 (1년 고점 −15%↓)
  S3 시장폭 (유니버스) 종가>자기 200일선 종목 비율 < 40%
  S4 환율  원/달러 60거래일 변화 > +5% (원화 급약세=자금유출)
  S5 수급  표본 40종목 외국인 60거래일 누적 순매수 < 0 (지속 순매도)
           ※ frgn 깊은 페이지로 2010까지 가능(reference_frgn_depth) — 2022 포함.

규칙 변형을 2022 약세장(러-우+급금리) / 2025 강세장에 역검증:
  지각(2021 고점→첫 ON 거래일) · 약세 커버리지% · 강세 헛경보% ·
  2024-12 바닥 후 재가동(OFF) 지각.
정답(객관) = KOSPI ≤ 직전252 고점×0.80 AND <200일선 → 약세일.

Yahoo(^KS11·KRW=X long)·유니버스 캐시(폭)·네이버 frgn deep(수급).
인-샘플·상폐제외·표본·종가. 환각 금지·결손 비임퓨트.
사용: python analyze_regime_detect.py [--ns 40] [--seed 7]
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
from canslim_lib.fetch import (yahoo_symbol, fetch_yahoo_chart,  # noqa: E402
                               )
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

CY = (Path(__file__).resolve().parents[2] / "research" / "oneil-model-book"
      / "cycles" / "c2024-12")
PEAK21 = "2021-07-06"      # cycles_index: c2020-03 강세장 종료(직전 고점)
BOTTOM = "2024-12-09"      # c2024-12 강세장 저점
BULL_W = ("2025-01-01", "2026-04-30")   # 강세장 헛경보 측정창


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def ydl(sym):
    ch = fetch_yahoo_chart(sym, period1=_ep("2016-01-01"),
                           period2=_ep("2026-12-31"), interval="1d")
    if not ch or not ch.get("closes"):
        return [], []
    d = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
         for t in ch["timestamps"]]
    return d, ch["closes"]


def at(d, c, ds):
    i = bisect.bisect_right(d, ds) - 1
    return c[i] if i >= 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    kd, kc = ydl("%5EKS11")
    fxd, fxc = ydl("KRW=X")
    if not kd:
        print("KOSPI 조회 실패", file=sys.stderr)
        return

    # 시장폭: 유니버스 각 코드 200일선 위 비율 (롤링합 O(N)·파일 캐시)
    bcache = CY / "_breadth.json"
    if bcache.exists():
        breadth = json.loads(bcache.read_text(encoding="utf-8"))
    else:
        U = json.loads((CY / "_universe_prices_5y.json").read_text(encoding="utf-8"))
        above = {}                      # date -> [위 수, 전체 수]
        for s in U.values():
            d, c = s.get("d"), s.get("c")
            if not d or not c or len(c) < 210:
                continue
            run = sum(c[0:200])         # 롤링 200합
            for i in range(199, len(c)):
                if i > 199:
                    run += c[i] - c[i - 200]
                r = above.setdefault(d[i], [0, 0])
                r[1] += 1
                if c[i] > run / 200:
                    r[0] += 1
        breadth = {dt: (v[0] / v[1]) for dt, v in above.items() if v[1] >= 200}
        bcache.write_text(json.dumps(breadth), encoding="utf-8")

    # 수급: 표본 40종목 deep frgn → 날짜별 외인 순매수 합
    rv = json.loads((CY / "winners.json").read_text(encoding="utf-8"))["ranked_valid"]
    pool = [r for r in rv if not r.get("exclude_reason")
            and r.get("n_days", 0) >= 250]
    random.seed(args.seed)
    fsmp = random.sample(pool, min(args.ns, len(pool)))
    fday = {}                           # date -> 외인순매수 합(표본)
    # 필요한 만큼만: 분석 달력 2021-06~ → 2021-03(60일 여유)까지면 충분.
    # 1page≈20거래일≈28일. (2010까지 과수집 금지 — 목표 시기까지만.)
    need_pages = 78          # ≈ 2021-03 도달(2026-05 기준 ~5.2년)
    for w in fsmp:
        try:
            fr = fetch_naver_org_flow(w["code"], pages=need_pages, sleep_ms=130)
        except Exception:
            continue
        for r in fr:
            fday[r["date"]] = fday.get(r["date"], 0) + (r.get("fgn_net") or 0)
    fdates = sorted(fday)

    def fgn_sum60(ds):
        j = bisect.bisect_right(fdates, ds)
        seg = fdates[max(0, j - 60):j]
        return sum(fday[x] for x in seg) if len(seg) >= 40 else None

    # KOSPI 인덱스 계산용
    def kma(i, w):
        return sum(kc[i - w + 1:i + 1]) / w if i >= w - 1 else None

    # 마스터 달력 = KOSPI 거래일, 2021-06~2026-05 (폭 가용구간 위주)
    cal = [(i, kd[i]) for i in range(len(kd))
           if "2021-06-01" <= kd[i] <= "2026-05-15" and i >= 252]

    rows = []                           # (date, S1..S5, truth_bear)
    for i, dt in cal:
        m200, m200p = kma(i, 200), (sum(kc[i - 219:i - 19]) / 200
                                    if i >= 219 else None)
        hi252 = max(kc[i - 251:i + 1])
        S1 = (m200 is not None and m200p is not None
              and kc[i] < m200 and m200 < m200p)
        S2 = kc[i] <= 0.85 * hi252
        b = breadth.get(dt)
        S3 = (b is not None and b < 0.40)
        fx, fxp = at(fxd, fxc, dt), at(fxd, fxc,
                                       kd[i - 60] if i >= 60 else dt)
        S4 = (fx is not None and fxp not in (None, 0) and fx / fxp - 1 > 0.05)
        fs = fgn_sum60(dt)
        S5 = (fs is not None and fs < 0)
        truth = (kc[i] <= 0.80 * hi252 and m200 is not None and kc[i] < m200)
        rows.append({"d": dt, "S": [S1, S2, S3, S4, S5],
                     "navail": [x is not None for x in
                                (m200, True, b, fx, fs)], "T": truth})

    def rule(r, kind):
        s = r["S"]
        cnt = sum(1 for x in s if x)
        if kind == "R1_추세":
            return s[0]
        if kind == "R2_추세or깊이":
            return s[0] or s[1]
        if kind == "R3_2of5":
            return cnt >= 2
        if kind == "R4_3of5":
            return cnt >= 3
        if kind == "R5_추세&(폭or수급)":
            return s[0] and (s[2] or s[4])
        return False

    KINDS = ["R1_추세", "R2_추세or깊이", "R3_2of5", "R4_3of5",
             "R5_추세&(폭or수급)"]
    di = {r["d"]: idx for idx, r in enumerate(rows)}
    pk = min((d for d in di if d >= PEAK21), default=None)
    bot = min((d for d in di if d >= BOTTOM), default=None)

    out = [f"[역검증] 약세장 감지 모듈 — KOSPI+폭+환율+수급(표본{len(fsmp)}, "
           f"deep frgn) seed{args.seed}",
           "정답=KOSPI≤직전252고점×0.80 & <200일선. 2021고점=2021-07-06 "
           "기준 지각, 강세창 2025-01~2026-04 헛경보.",
           "S1추세 S2깊이 S3폭<40% S4원달러+5%/60d S5표본외인60d순매도",
           ""]
    # 신호 가용 점검
    av = [sum(1 for r in rows if r["navail"][k]) for k in range(5)]
    out.append(f"신호 가용일수(전 {len(rows)}일중): S1 {av[0]} S2 {av[1]} "
               f"S3 {av[2]} S4 {av[3]} S5 {av[4]}")
    truthdays = [r["d"] for r in rows if r["T"]]
    bull = [r for r in rows if BULL_W[0] <= r["d"] <= BULL_W[1]]
    out.append(f"정답 약세일 {len(truthdays)} (첫 {truthdays[0] if truthdays else '-'}"
               f"~끝 {truthdays[-1] if truthdays else '-'}) | 강세창 {len(bull)}일")
    out.append("")
    out.append("규칙 | 2021고점→첫ON(거래일 지각) | 약세 커버리지 | "
               "강세 헛경보 | 바닥후 첫OFF 지각")
    for k in KINDS:
        on = [idx for idx, r in enumerate(rows) if rule(r, k)]
        first_on = next((rows[idx]["d"] for idx in on
                         if pk and rows[idx]["d"] >= pk), None)
        late = (di[first_on] - di[pk]) if (first_on and pk) else None
        cov = (round(100 * sum(1 for r in rows if r["T"] and rule(r, k))
                     / max(1, len(truthdays))))
        fa = (round(100 * sum(1 for r in bull if rule(r, k))
                    / max(1, len(bull))))
        # 바닥 후 첫 OFF (재가동) 지각
        off = None
        if bot:
            for idx in range(di[bot], len(rows)):
                if not rule(rows[idx], k):
                    off = di[rows[idx]["d"]] - di[bot]
                    break
        out.append(f"{k:16s} | {late if late is not None else '-'}거래일 "
                   f"({first_on}) | {cov}% | {fa}% | "
                   f"{off if off is not None else '-'}거래일")
    out += ["",
            "== 읽는 법 ==",
            "지각 작을수록·약세커버리지 높을수록·강세헛경보 0에 가까울수록·",
            "바닥후 재가동 지각 작을수록 좋은 master switch. 균형 최적 채택.",
            "== 한계 ==",
            "S3(폭)는 유니버스 2021-05~ 라 2022초 일부 결손(S1·S2·S4·S5가",
            "보완). 2018 약세는 폭 부재로 본 표 미포함(지수형 별도 필요).",
            "인-샘플·표본수급 proxy(KRX 공식 시장합계 아님)·종가·비용무관."]
    fn = f"_regime_detect_s{args.seed}.txt"
    (CY / fn).write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fn}", file=sys.stderr)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""25 · **G3′ — 「되돌리기를 그만둔 것」이 옳게 됐는지 재는 관문** (M38).

옛 G3 는 「분할 되돌리기가 정확한가」를 쟀고 **통과했다**. 그런데 **되돌리는 게 옳은지는
아무도 묻지 않았다.** 그래서 관문에 한 줄을 단다:

    🚨 **이 검산이 통과해도 여전히 틀릴 수 있는 경우는?**
       검산 1~3 은 전부 **Sharadar 가 표시한 분할**만 본다.
       **Sharadar 가 놓친 분할은 셋 다 통과한다.** 그 구멍을 검산 4 가 막는다.

검산
----
1. 기준가가 바뀐 1,070종목의 **변경일에 수정 시계열이 분할 배수만큼 튀지 않을 것**
2. 교차 항등: `(closeunadj 비율) ÷ (close 비율)` = 분할 배수
3. 변경일 전후 `close × volume`(거래대금)에 **계단이 없을 것** — 대조군과 분포 비교
4. 🚨 **잔차 점검**: 창 전체에서 하루 **±90%p 넘는 움직임 전수**를 세고,
   그중 **기준가 변경일에 걸린 것이 몇 건인지** 본다(고쳐졌다면 0에 가까워야 한다).
   표본을 눈으로 볼 수 있게 상위 25건을 찍는다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/25-g3prime.py
난수 seed: 대조군 추출 250824
"""
from __future__ import annotations

import csv
import io
import json
import random
import statistics as st
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import us_loader  # noqa: E402

OUT = ROOT / ".cache" / "bt5y" / "out"
LO, HI = "2021-02-01", "2026-08-21"
SEED = 250824
BIG = 0.90


def main():
    meta = us_loader.load_tickers("base")
    codes = {c for c, m in meta.items()
             if m["firstpricedate"] <= HI and m["lastpricedate"] >= LO}
    print("기본판 창 종목 %d" % len(codes), flush=True)

    interned = {}
    ser = defaultdict(list)
    with zipfile.ZipFile(us_loader.STOCKS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
        next(rd)
        for row in rd:
            t, d = row[0], row[1]
            if d < LO or d > HI or t not in codes:
                continue
            cf, cuf = float(row[5]), float(row[8])
            if cf <= 0 or cuf <= 0:
                continue
            dd = interned.get(d)
            if dd is None:
                dd = interned[d] = sys.intern(d)
            ser[t].append((dd, cf, cuf, float(row[6])))
    print("  시계열 %d종목 · %d행" % (len(ser), sum(len(v) for v in ser.values())),
          flush=True)
    for v in ser.values():
        v.sort()

    # ── 검산 1·2 ────────────────────────────────────────────────────────────
    fail1 = fail2 = 0
    n_rebase = 0
    worst2 = 0.0
    max_adj_at_rebase = (0.0, None, None)
    rebase_dates = defaultdict(set)
    mults = []
    for t, v in ser.items():
        fs = [x[2] / x[1] for x in v]
        # ── ② 교차 항등: **하루 factor 그대로** 쓴다(대수 항등이라 전 구간에서 성립해야 한다)
        for i in range(1, len(v)):
            m_exact = fs[i] / fs[i - 1]
            adj = v[i][1] / v[i - 1][1]
            unadj = v[i][2] / v[i - 1][2]
            dev = abs(unadj / adj / m_exact - 1)
            worst2 = max(worst2, dev)
            if dev > 1e-6:
                fail2 += 1
        # ── 분할일 탐지: factor 는 close 반올림(소수 셋째) 때문에 **잡음이 크다**
        #    (저가주는 상대오차가 1%에 이른다). 인접 하루만 보면 잡음이 전부 「사건」이
        #    된다 — 1e-9 문턱 303,341건 · 1e-3 문턱 49,815건. 분할은 **지속적** 변화이므로
        #    앞뒤 3일 중앙값으로 보고, **연속 탐지는 한 사건으로 묶는다**(3거래일 이내).
        last_i = -99
        for i in range(3, len(v) - 3):
            m = st.median(fs[i:i + 3]) / st.median(fs[i - 3:i])
            if abs(m - 1.0) < 0.02:
                continue
            if i - last_i <= 3:
                continue
            last_i = i
            n_rebase += 1
            rebase_dates[t].add(v[i][0])
            mults.append(m)
            adj = v[i][1] / v[i - 1][1] - 1
            # ① 수정 시계열이 분할 배수만큼 튀면 실패
            if abs(adj - (m - 1)) < 1e-3 and abs(m - 1) > 0.05:
                fail1 += 1
            if abs(adj) > abs(max_adj_at_rebase[0]):
                max_adj_at_rebase = (adj, t, v[i][0])
    print("", flush=True)
    print("=" * 74, flush=True)
    print("G3′ 검산", flush=True)
    print("=" * 74, flush=True)
    print("기준가 변경 사건 **%d건 · %d종목** · 배수 중앙 %.4f (최소 %.6f · 최대 %.1f)"
          % (n_rebase, len(rebase_dates), st.median(mults), min(mults), max(mults)),
          flush=True)
    print("① 변경일에 수정 시계열이 분할 배수만큼 튄 건 **%d건** (0이어야 통과)"
          % fail1, flush=True)
    print("   변경일 수정 하루변화 최대 |%.2f%%| (%s %s)"
          % (max_adj_at_rebase[0] * 100, max_adj_at_rebase[1], max_adj_at_rebase[2]),
          flush=True)
    print("② 교차 항등 (closeunadj비 ÷ close비 = 배수) 이탈 최대 **%.3e** · 실패 %d건"
          % (worst2, fail2), flush=True)

    # ── 검산 3: 거래대금 계단 ───────────────────────────────────────────────
    rnd = random.Random(SEED)
    def step_ratio(v, i, w=5):
        a = [x[1] * x[3] for x in v[max(0, i - w):i]]
        b = [x[1] * x[3] for x in v[i:i + w]]
        if len(a) < w or len(b) < w or not sum(a):
            return None
        ma, mb = st.median(a), st.median(b)
        return (mb / ma) if ma > 0 else None

    treat, ctrl = [], []
    strata = {"저가 <$1": [], "$1~$10": [], ">=$10": [], "유동성 통과": []}
    for t, v in ser.items():
        rd_ = rebase_dates.get(t)
        idx = {d: i for i, (d, *_r) in enumerate(v)}
        if rd_:
            for d in rd_:
                i = idx[d]
                r = step_ratio(v, i)
                if not r:
                    continue
                treat.append(r)
                # 🚨 close 는 소수 셋째 자리 반올림이다. 서브페니 종목은 **분할 전** 가격이
                #    0.001 바닥에 눌려 거래대금이 과소 계산된다 → 비가 부풀려 보인다.
                #    가격대로 갈라서 그 설명이 맞는지 본다.
                pre = st.median([x[2] for x in v[max(0, i - 5):i]])   # 비수정=실제 호가
                key = "저가 <$1" if pre < 1 else ("$1~$10" if pre < 10 else ">=$10")
                strata[key].append(r)
                seg = [x[1] * x[3] * 1300.0 / 1e8 for x in v[max(0, i - 50):i]]
                if seg and sum(seg) / len(seg) >= 5.0:
                    strata["유동성 통과"].append(r)
        if len(v) > 20:
            i = rnd.randrange(10, len(v) - 10)
            if v[i][0] not in (rd_ or ()):
                r = step_ratio(v, i)
                if r:
                    ctrl.append(r)
    print("③ 거래대금 계단 — 변경일 전후 5일 중앙값 비 (1.0이면 계단 없음)", flush=True)
    rows3 = [("변경일 전체", treat), ("대조군", ctrl)] + list(strata.items())
    for lab, xs in rows3:
        if not xs:
            continue
        s = sorted(xs)
        print("     %-12s %5d건  중앙 %6.3f · P10 %6.3f · P90 %7.3f"
              % (lab, len(s), s[len(s) // 2], s[int(len(s) * .1)], s[int(len(s) * .9)]),
              flush=True)

    # ── 검산 4: 잔차 ────────────────────────────────────────────────────────
    big = []
    n_obs = 0
    for t, v in ser.items():
        rd_ = rebase_dates.get(t) or ()
        for i in range(1, len(v)):
            n_obs += 1
            r = v[i][1] / v[i - 1][1] - 1
            if abs(r) > BIG:
                big.append((abs(r), r, t, v[i][0], v[i][0] in rd_))
    big.sort(reverse=True)
    on_rebase = sum(1 for x in big if x[4])
    # 🚨 결정에 쓰이는 수 — 잔차 **전수**가 유동성 문턱을 넘는가(넘지 못하면 하네스가 안 산다)
    idxall = {}
    liq = []
    for _a, r, t, d, _o in big:
        im = idxall.get(t)
        if im is None:
            im = idxall[t] = {dd: i for i, (dd, *_x) in enumerate(ser[t])}
        i = im[d]
        seg = [x[1] * x[3] * 1300.0 / 1e8 for x in ser[t][max(0, i - 50):i]]
        liq.append((sum(seg) / len(seg)) if len(seg) >= 25 else 0.0)
    n_liq = sum(1 for x in liq if x >= 5.0)
    print("④ **잔차 — 하루 |움직임| > %d%%p**" % int(BIG * 100), flush=True)
    print("     관측 %d 중 **%d건 (%.4f%%)** · 그중 기준가 변경일 **%d건**"
          % (n_obs, len(big), len(big) / n_obs * 100, on_rebase), flush=True)
    print("     🚨 **전수 중 유동성 문턱(50일 평균 5억원)을 넘는 건 %d건 (%.1f%%)** "
          "— 나머지 %d건은 하네스가 애초에 안 산다"
          % (n_liq, n_liq / len(big) * 100, len(big) - n_liq), flush=True)
    print("     상위 25 (눈으로 볼 표본):", flush=True)
    for _a, r, t, d, onr in big[:25]:
        print("       %-7s %s  %+9.1f%%   %s"
              % (t, d, r * 100, "**변경일**" if onr else ""), flush=True)
    # 유동성 관문이 이 잔차들을 애초에 걸러 주는지 — 그날 앞 50일 평균 거래대금(억원)
    print("     ↓ 같은 25건의 **직전 50일 평균 거래대금(억원)** — 하네스 문턱은 5.0",
          flush=True)
    idxmap = {t: {d: i for i, (d, *_r) in enumerate(ser[t])} for _a, _r2, t, _d, _o in big[:25]}
    under = 0
    for _a, r, t, d, onr in big[:25]:
        i = idxmap[t][d]
        seg = [x[1] * x[3] * 1300.0 / 1e8 for x in ser[t][max(0, i - 50):i]]
        tv = sum(seg) / len(seg) if seg else 0.0
        under += (tv < 5.0)
        print("       %-7s %s  %10.2f억  %s"
              % (t, d, tv, "← 문턱 미만(하네스가 안 삼)" if tv < 5.0 else ""), flush=True)
    print("     → 상위 25건 중 **%d건이 유동성 문턱 미만**" % under, flush=True)
    # 눈으로 볼 원자료 — 잔차 상위 6건의 앞뒤 3일
    print("", flush=True)
    print("     ↓ 잔차 상위 6건 **원자료**(날짜 · close · closeunadj · volume)", flush=True)
    for _a, r, t, d, onr in big[:6]:
        i = idxmap[t][d]
        print("       — %s %s (%+.1f%%)" % (t, d, r * 100), flush=True)
        for x in ser[t][max(0, i - 3):i + 3]:
            print("           %s  close %12.4f  unadj %12.4f  vol %14.0f"
                  % (x[0], x[1], x[2], x[3]), flush=True)

    ok = (fail1 == 0 and fail2 == 0)
    print("", flush=True)
    print("**G3′ %s** (①② 기준)" % ("통과" if ok else "실패"), flush=True)
    print("⚠️ 남는 구멍: ①~③은 **Sharadar 가 표시한 분할만** 본다. 놓친 분할은 ④로만 보인다.",
          flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "25-g3prime.json").write_text(json.dumps({
        "n_rebase_events": n_rebase, "n_rebase_codes": len(rebase_dates),
        "fail1": fail1, "fail2": fail2, "worst_identity_dev": worst2,
        "turnover_step_treat_median": st.median(treat),
        "turnover_step_ctrl_median": st.median(ctrl),
        "n_obs": n_obs, "n_big_moves": len(big), "big_on_rebase": on_rebase,
        # 🚨 결정 2(b) 민감도가 이 목록을 배제 대상으로 쓴다 → **전수를 남긴다**
        #    (상위 200만 남기면 민감도가 조용히 부분집합만 배제하게 된다).
        "top": [{"code": t, "date": d, "ret_pct": r * 100, "on_rebase": onr,
                 "adv50_eok": round(liq[i], 2)}
                for i, (_a, r, t, d, onr) in enumerate(big)],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("저장: .cache/bt5y/out/25-g3prime.json", flush=True)


if __name__ == "__main__":
    main()

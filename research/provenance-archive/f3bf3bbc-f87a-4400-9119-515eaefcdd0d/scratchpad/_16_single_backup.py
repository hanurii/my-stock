# -*- coding: utf-8 -*-
"""16 — ★ 선별력이 있는가 (이 프로젝트에서 가장 중요한 질문).

지시서: research/handoff/tasks/16-selection-edge.md + 검증 세션 사전 검토 8항목.

13개 주장은 전부 "언제 팔까·어떤 순서로 살까·언제 쉴까"였다.
**"무엇을 살까"는 고정해 놓고 한 번도 검정하지 않았다.** 이 과제가 그것을 잰다.

세 갈래 (사슬로 정의 — 대조 → 관문통과 → 우리)
  A = 우리 − 무작위          (선별 전체)
  B = 관문통과 − 관문미통과   (관문 8조건)
  C = 우리 − 관문통과        (VCP·3C·PP 검출기)
  검산: A_β = C_β + (1 − p) × B_β  (p = 관문통과율)
  **이 점검은 검산이며 불일치는 판정 사유가 아니다** — 세 비교의 표본이 다르므로
  잔차는 오류가 아니라 상호작용이다(검증 [5]).

대조군 진입 방식
  α  : E 시가 진입 (돌파 조건 없음)          — "아무 종목이나 샀으면"
  βN : `high(E) > N일 고가(D까지)` 일 때만
       `max(N일 고가, open(E))` 진입          — "돌파는 하되 우리 검출기 없이 샀으면"
       **N = 1 · 5 · 20 · 60 사다리**(검증 [2]) — 가장 엄한 N=60에서도 남으면 진짜다
  **βATR** : β1 과 같되 **우리 거래와 같은 ATR 구간**에서만 뽑는다(검증 [1], 무조건 산출)
  **우리×β1** : 우리가 고른 **같은 종목**을 전일 고가에서 사는 판(실행 가능한 분해, 부가)

자격 판정은 **D(스캔일) 시점**, 진입은 **E = D 다음 거래일** — 우리 거래와 동일.
①같은 날 ②유동성 5억 ③정지·상폐 제외 ⑦제외 패턴은 **하네스가 판정한 `eligible`을
그대로 쓰므로 정의상 일치**한다(재구현하지 않는다).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/16-selection-edge.py
난수 seed: 대조군 추첨 160000 · 블록 부트스트랩 161000
"""
from __future__ import annotations

import json
import random
import statistics as st
from bisect import bisect_left
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from math import comb, erf, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import slot_sim  # noqa: E402
from canslim_lib.pdata_series import build_series  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
PDATA = ROOT / ".cache" / "pdata"
GATE = BT / "gate"
TARGET, STOP = 20.0, 10.0
WARM_DAYS, TAIL_DAYS = 430, 300
N_REP = 200
DRAW_SEED, BOOT_SEED = 160000, 161000
N_BOOT, BLOCK_MIN, BLOCK_MAX = 1000, 20, 40
MDE_K, EQUIV = 2.80, 0.5
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
BETAS = [1, 5, 20, 60]
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]
YS = ("2021", "2022", "2023", "2024", "2025", "2026")
net = slot_sim.net


def atr_band(v):
    if v is None:
        return "미상"
    return ("①조용 <2.5%" if v < 2.5 else "②보통 2.5~4%" if v < 4
            else "③큼 4~6%" if v < 6 else "④매우큼 6%+")


def atr_pct_at(s, i, win=20):
    """하네스 atr_pct 와 같은 정의 — i 시점까지의 ATR(20) ÷ 종가 × 100."""
    h, l, c = s["highs"], s["lows"], s["closes"]
    if i < win:
        return None
    tr = []
    for j in range(i - win + 1, i + 1):
        pc = c[j - 1]
        tr.append(max(h[j] - l[j], abs(h[j] - pc), abs(l[j] - pc)))
    return (sum(tr) / win) / c[i] * 100 if c[i] else None


def resolve(s, ni, epx):
    """+20/−10 선착, 그날 종가 체결. 시계열이 끝나면 마지막 종가(소멸 포함)."""
    h, l, c = s["highs"], s["lows"], s["closes"]
    n = len(c)
    T, S = epx * (1 + TARGET / 100), epx * (1 - STOP / 100)
    for i in range(ni, n):
        ht, hs = h[i] >= T, l[i] <= S
        if ht and hs:
            return (c[i] / epx - 1) * 100, "both_same_day", i - ni
        if ht:
            return (c[i] / epx - 1) * 100, "target", i - ni
        if hs:
            return (c[i] / epx - 1) * 100, "stop", i - ni
    return (c[n - 1] / epx - 1) * 100, "last_close", n - 1 - ni


def outcome(s, di, arm):
    """D 인덱스 di 에서 팔(arm)의 진입·결착. 진입 못 하면 None.

    arm: 'alpha' | ('beta', N)
    """
    ni = di + 1
    if ni >= len(s["closes"]):
        return None
    o, h = s["opens"], s["highs"]
    if arm == "alpha":
        epx = o[ni]
        if not epx:
            return None
    else:
        N = arm[1]
        if di - N + 1 < 0:
            return None
        thr = max(h[di - N + 1:di + 1])
        if h[ni] is None or h[ni] <= thr:
            return None
        epx = max(thr, o[ni] or thr)
    g, why, days = resolve(s, ni, epx)
    return {"gain": g, "reason": why, "days": days, "entry_price": epx,
            "result": ("win" if why == "target" else
                       "loss" if why in ("stop", "both_same_day") else
                       ("win" if g > 0 else "loss"))}


def iter_pdata(start, end):
    s, e = start.replace("-", ""), end.replace("-", "")
    for p in sorted(PDATA.glob("price_*.json")):
        d = p.stem[6:]
        if not (s <= d <= e):
            continue
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        yield "%s-%s-%s" % (d[:4], d[4:6], d[6:]), recs


def _phi(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def sign_test(xs):
    n = len(xs)
    pos = sum(1 for x in xs if x > 0)
    k = min(pos, n - pos)
    if n <= 100:
        p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / (2 ** n))
        how = "이항 정확"
    else:
        z = (abs(pos - n / 2) - 0.5) / (sqrt(n) / 2)
        p = min(1.0, 2 * (1 - _phi(z)))
        how = "정규근사(연속성 보정)"
    return {"n": n, "n_pos": pos, "p": p, "how": how}


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def draw_rng(D, arm):
    """(날짜, 팔)마다 독립 난수 — 팔을 추가해도 기존 팔의 추첨이 안 바뀐다."""
    return random.Random("%d|%s|%s" % (DRAW_SEED, D, arm))


def make_blocks(rnd, n_pos):
    out, tot = [], 0
    while tot < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - tot)
        out.append((a, LL))
        tot += LL
    return out


def day_stat(pairs, dates_all, tag, seed):
    """하루 짝차이(우리 − 대조)의 평균을 1순위로, 블록 부트스트랩."""
    ds = sorted(pairs)
    diffs = [pairs[d] for d in ds]
    mean, med = st.mean(diffs), st.median(diffs)
    pos_of = {d: i for i, d in enumerate(dates_all)}
    n_pos = len(dates_all)
    rnd = random.Random(seed)
    bm, bmd = [], []
    for _ in range(N_BOOT):
        v = []
        for a, L in make_blocks(rnd, n_pos):
            for j in range(L):
                d = dates_all[a + j]
                if d in pairs:
                    v.append(pairs[d])
        if v:
            bm.append(st.mean(v))
            bmd.append(st.median(v))
    lo, hi = ci(bm)
    mlo, mhi = ci(bmd)
    sd = st.stdev(bm)
    mde = MDE_K * sd
    excl = lo > 0 or hi < 0
    within = -EQUIV <= lo and hi <= EQUIV
    label = ("효과 있음(0 제외, 양수)" if (excl and mean > 0) else
             "효과 있음(0 제외, 음수)" if excl else
             "유지(동등성)" if within else
             ("판정불가(문턱 사각지대)" if (hi - lo) <= 2 * EQUIV
              else "판정불가(검정력 부족)"))
    sg = 1 if mean > 0 else -1
    top5 = {d for d in sorted(ds, key=lambda x: abs(pairs[x]))[-5:]}
    m4 = st.mean([pairs[d] for d in ds if d not in top5])
    l2 = {y: (st.mean([pairs[d] for d in ds if d[:4] != y])
              if any(d[:4] != y for d in ds) else None) for y in YS}
    l3 = {}
    for sn, y0, y1 in SEGMENTS:
        v = [pairs[d] for d in ds if y0 <= d[:4] <= y1]
        l3[sn] = {"n": len(v), "mean": st.mean(v) if v else None}
    stt = sign_test(diffs)
    lens = {"L1": bool(stt["p"] < 0.05 and (mlo > 0 or mhi < 0) and (med > 0) == (sg > 0)),
            "L2p": all(v is not None and (v > 0) == (sg > 0) for v in l2.values()),
            "L3": all(v["mean"] is not None and (v["mean"] > 0) == (sg > 0)
                      for v in l3.values()),
            "L4": (m4 > 0) == (sg > 0)}
    r = {"tag": tag, "n_days": len(ds), "mean": mean, "ci": [lo, hi],
         "ci_width": hi - lo, "sd": sd, "MDE": mde, "median": med,
         "median_ci": [mlo, mhi], "sign": stt, "verdict_axis": label,
         "L4_top5_removed": m4, "L2p": l2, "L3": l3, "lenses": lens,
         "n_lenses": sum(lens.values())}
    print("  %-22s 날 %4d · 평균 %+7.4f%%p · 95%% %+7.4f ~ %+7.4f (폭 %6.4f) · "
          "MDE %6.4f · 중앙 %+7.4f · 렌즈 %d/4 · **%s**"
          % (tag, len(ds), mean, lo, hi, hi - lo, mde, med, sum(lens.values()), label),
          flush=True)
    return r


def main():
    print("═══ 1단계: 연도별 시계열 + 대조군 결착 ═══", flush=True)
    ARMS = ["alpha"] + [("beta", n) for n in BETAS]
    ARMN = {"alpha": "α시가"}
    for n in BETAS:
        ARMN[("beta", n)] = "β%d일고가" % n

    ours_rows = []                       # 우리 거래(정본 3,776 아님 — 확정 events 3,776키)
    day_pairs = defaultdict(dict)        # arm -> {entry_date: 하루짝차이}
    absol = defaultdict(list)            # arm -> [순수익]
    absol_meta = defaultdict(list)
    lvl = defaultdict(dict)
    diag = {"days_pool_eq_k": 0, "trades_pool_eq_k": 0, "ours_beta1_no_breakout": 0,
            "atr_band_fallback": defaultdict(int),
            "beta_pool_short": defaultdict(int), "beta_trades_short": defaultdict(int),
            "vanished": defaultdict(int), "series_missing": 0,
            "eligible_codes": 0, "series_loaded": 0}
    atr_dist = defaultdict(list)
    cap_dist = defaultdict(list)

    for y in YEARS:
        g = json.loads((GATE / ("bt_%d_gate.json" % y)).read_text(encoding="utf-8"))
        prm = g["params"]
        start, end = prm["start"], prm["end"]
        w = (datetime.strptime(start, "%Y-%m-%d")
             - timedelta(days=WARM_DAYS)).strftime("%Y-%m-%d")
        le = (datetime.strptime(end, "%Y-%m-%d")
              + timedelta(days=TAIL_DAYS)).strftime("%Y-%m-%d")
        gl = {x["scan_date"]: x for x in g["gate_log"]}
        ev_by_D = defaultdict(list)
        for e in g["events"]:
            ev_by_D[e["scan_date"]].append(e)
        need = {c for x in g["gate_log"] for c in x["eligible"]}
        print("[%d] 시계열 생성 %s ~ %s · 적격 종목 %d …" % (y, w, le, len(need)),
              flush=True)
        cap_at = {}
        full = {}

        def _it():
            for date, recs in iter_pdata(w, le):
                if date in gl:
                    cap_at[date] = {c: r.get("market_cap_eok")
                                    for c, r in recs.items() if c in need}
                yield date, {c: r for c, r in recs.items() if c in need}

        full = build_series(_it())
        diag["eligible_codes"] += len(need)
        diag["series_loaded"] += sum(1 for c in need if c in full)
        miss = len(need) - sum(1 for c in need if c in full)
        diag["series_missing"] += miss
        print("[%d]   시계열 보유 %d / %d (결측 %d)" % (y, len(full), len(need), miss),
              flush=True)

        # 날짜 → 인덱스는 종목마다 dict 를 만들면 200MB 넘게 든다. 이진탐색으로 대신한다.
        cache = {}

        def _di(s, D):
            ds = s["dates"]
            i = bisect_left(ds, D)
            return i if (i < len(ds) and ds[i] == D) else None

        def get(c, D, arm):
            k = (c, D, arm)
            if k in cache:
                return cache[k]
            s = full.get(c)
            di = None if s is None else _di(s, D)
            v = None if di is None else outcome(s, di, arm)
            cache[k] = v
            return v

        for D in sorted(ev_by_D):
            ours = ev_by_D[D]
            k = len(ours)
            E = ours[0]["entry_date"]
            pool = [c for c in gl[D]["eligible"] if c in full]
            passed = set(gl[D]["passed"])
            our_codes = {e["code"] for e in ours}
            our_net = st.mean([net(e["gain_at_resolve_pct"]) for e in ours])
            for e in ours:
                ours_rows.append({"code": e["code"], "pattern": e["pattern"],
                                  "scan_date": D, "entry_date": E,
                                  "net": net(e["gain_at_resolve_pct"]),
                                  "result": e["result"], "atr": e.get("atr_pct"),
                                  "year": E[:4]})
                atr_dist["ours"].append(e.get("atr_pct"))
                cp = cap_at.get(D, {}).get(e["code"])
                if cp:
                    cap_dist["ours"].append(cp)
            if len(pool) <= k:
                diag["days_pool_eq_k"] += 1
                diag["trades_pool_eq_k"] += k
            # C·B 용 풀 (β1 진입으로 통일)
            b1 = ("beta", 1)
            pool_pass = [c for c in pool if c in passed]
            pool_fail = [c for c in pool if c not in passed]
            for nm, pl in (("C:관문통과β1", pool_pass), ("B:관문미통과β1", pool_fail)):
                cd = [c for c in pl if get(c, D, b1) is not None]
                if len(cd) < k:
                    diag["beta_pool_short"][nm] += 1
                    diag["beta_trades_short"][nm] += k - len(cd)
                if not cd:
                    continue
                rp = []
                r0 = draw_rng(D, nm)
                for _ in range(N_REP):
                    pick = (r0.sample(cd, k) if len(cd) >= k
                            else [cd[r0.randrange(len(cd))] for _ in range(k)])
                    rp.append(st.mean([net(get(c, D, b1)["gain"]) for c in pick]))
                lvl[nm][E] = st.mean(rp)
            if E in lvl["C:관문통과β1"]:
                day_pairs["C 우리-관문통과"][E] = our_net - lvl["C:관문통과β1"][E]
                if E in lvl["B:관문미통과β1"]:
                    day_pairs["B 관문통과-미통과"][E] = (lvl["C:관문통과β1"][E]
                                                  - lvl["B:관문미통과β1"][E])
            # ── ATR 구간 맞춤 대조 (검증 [1]) — 우리 거래 한 건마다 같은 구간에서 뽑는다
            our_bands = []
            for e in ours:
                s_ = full.get(e["code"])
                di_ = _di(s_, D) if s_ else None
                av_ = atr_pct_at(s_, di_) if di_ is not None else None
                our_bands.append(atr_band(av_))
            for nm, pl in (("A ATR맞춤β1", pool), ("C ATR맞춤β1", pool_pass)):
                by_band = {}
                for c in pl:
                    if get(c, D, b1) is None:
                        continue
                    s_ = full.get(c)
                    di_ = _di(s_, D) if s_ else None
                    if di_ is None:
                        continue
                    av_ = atr_pct_at(s_, di_)
                    if av_ is None:
                        continue
                    by_band.setdefault(atr_band(av_), []).append(c)
                if not by_band:
                    continue
                order = ["①조용 <2.5%", "②보통 2.5~4%", "③큼 4~6%", "④매우큼 6%+"]
                rp = []
                r0 = draw_rng(D, nm)
                for _ in range(N_REP):
                    vv = []
                    for bd in our_bands:
                        cd = by_band.get(bd)
                        if not cd:
                            diag["atr_band_fallback"][nm] += 1
                            if bd in order:
                                j = order.index(bd)
                                for step in (1, 2, 3):
                                    for jj in (j - step, j + step):
                                        if 0 <= jj < len(order) and by_band.get(order[jj]):
                                            cd = by_band[order[jj]]
                                            break
                                    if cd:
                                        break
                            if not cd:
                                continue
                        vv.append(net(get(cd[r0.randrange(len(cd))], D, b1)["gain"]))
                    if vv:
                        rp.append(st.mean(vv))
                if rp:
                    day_pairs[nm][E] = our_net - st.mean(rp)

            # 우리 종목 x β1 문턱 (실행 가능한 분해)
            ov = []
            for e in ours:
                r = get(e["code"], D, b1)
                if r is None:
                    diag["ours_beta1_no_breakout"] += 1
                else:
                    ov.append(net(r["gain"]))
            if ov:
                day_pairs["우리종목xβ1"][E] = our_net - st.mean(ov)

            for arm in ARMS:
                if arm == "alpha":
                    cand = pool
                else:
                    cand = [c for c in pool if get(c, D, arm) is not None]
                    if len(cand) < k:
                        diag["beta_pool_short"][ARMN[arm]] += 1
                        diag["beta_trades_short"][ARMN[arm]] += k - len(cand)
                if not cand:
                    continue
                reps = []
                r0 = draw_rng(D, ARMN[arm])
                for _ in range(N_REP):
                    pick = (r0.sample(cand, k) if len(cand) >= k
                            else [cand[r0.randrange(len(cand))] for _ in range(k)])
                    vals = []
                    for c in pick:
                        r = get(c, D, arm)
                        if r is None:
                            continue
                        vals.append(net(r["gain"]))
                        if r["reason"] == "last_close" and r["days"] < 200:
                            diag["vanished"][ARMN[arm]] += 1
                    if vals:
                        reps.append(st.mean(vals))
                if reps:
                    ctrl = st.mean(reps)
                    day_pairs[ARMN[arm]][E] = our_net - ctrl
                    absol[ARMN[arm]].append(ctrl)
                # 분포 표본 — 첫 복제 한 벌만(우리와 같은 규모의 n 을 만든다)
                if arm == "alpha" or arm == ("beta", 1):
                    pk = (draw_rng(D, ARMN[arm] + "|dist").sample(cand, k)
                          if len(cand) >= k else list(cand[:k]))
                    for c in pk:
                        s = full.get(c)
                        di = _di(s, D) if s else None
                        if di is not None:
                            av = atr_pct_at(s, di)
                            if av is not None:
                                atr_dist[ARMN[arm]].append(av)
                        cp = cap_at.get(D, {}).get(c)
                        if cp:
                            cap_dist[ARMN[arm]].append(cp)
        del full, cache, cap_at
        print("[%d]   완료 · 우리 누적 %d건" % (y, len(ours_rows)), flush=True)

    res = {"n_ours": len(ours_rows), "n_rep": N_REP, "diag": dict(diag)}
    (OUT / "16-selection-edge-raw.json").write_text(
        json.dumps({"day_pairs": {k: v for k, v in day_pairs.items()},
                    "diag": {k: (dict(v) if isinstance(v, defaultdict) else v)
                             for k, v in diag.items()},
                    "ours": ours_rows,
                    "atr_ours": [x for x in atr_dist["ours"] if x is not None],
                    "cap_ours": cap_dist["ours"]},
                   ensure_ascii=False), encoding="utf-8")
    print("\n중간 저장: 16-selection-edge-raw.json", flush=True)

    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(r["entry_date"] for r in ours_rows)
    hi_d = max(r["entry_date"] for r in ours_rows)
    dates_all = [d for d in cal if lo_d <= d <= hi_d]

    print("\n═══ A — 우리 vs 무작위 (1순위: 하루 짝차이 평균, 거래당 순수익) ═══", flush=True)
    res["A"] = {}
    for arm in ARMS:
        nm = ARMN[arm]
        if day_pairs[nm]:
            res["A"][nm] = day_stat(day_pairs[nm], dates_all, "A vs " + nm,
                                    BOOT_SEED + BETAS.index(arm[1]) + 1
                                    if arm != "alpha" else BOOT_SEED)

    print("\n═══ B · C · 부가 팔 (전부 β1 진입으로 통일) ═══", flush=True)
    res["BC"] = {}
    for i, nm in enumerate(("C 우리-관문통과", "B 관문통과-미통과", "우리종목xβ1",
                           "A ATR맞춤β1", "C ATR맞춤β1")):
        if day_pairs.get(nm):
            res["BC"][nm] = day_stat(day_pairs[nm], dates_all, nm, BOOT_SEED + 50 + i)
    if "C 우리-관문통과" in res["BC"] and "B 관문통과-미통과" in res["BC"]:
        p_gate = 172764 / 2109931
        cb = res["BC"]["C 우리-관문통과"]["mean"]
        bb = res["BC"]["B 관문통과-미통과"]["mean"]
        ab = res["A"].get("β1일고가", {}).get("mean")
        rhs = cb + (1 - p_gate) * bb
        res["identity_check"] = {"p_gate": p_gate, "C": cb, "B": bb,
                                 "A_beta1": ab, "C_plus_(1-p)B": rhs,
                                 "residual": (ab - rhs) if ab is not None else None}
        print("\n  [검산] A_β1 %+.4f  vs  C %+.4f + (1-%.4f)xB %+.4f = %+.4f · 잔차 %+.4f"
              % (ab, cb, p_gate, bb, rhs, ab - rhs), flush=True)
        print("  ※ 이 점검은 **검산이며 불일치는 판정 사유가 아니다** — 세 비교의 "
              "표본이 다르므로 잔차는 오류가 아니라 상호작용이다(검증 [5]).", flush=True)

    print("\n═══ 우리 거래 절대 성적 (M1 정본 아님 — 확정 events 기준) ═══", flush=True)
    nets = [r["net"] for r in ours_rows]
    wins = sum(1 for r in ours_rows if r["result"] == "win")
    be = sum(1 for r in ours_rows if r["net"] > 0)
    # ★ 필요 본전 승률은 **비용 반영 순수익**으로 계산한다.
    #   33.33%(=10/(20+10))는 수수료·세금을 무시한 값이라 여유를 과대평가한다.
    w_net = st.mean([r["net"] for r in ours_rows if r["net"] > 0])
    l_net = st.mean([r["net"] for r in ours_rows if r["net"] <= 0])
    need_be = (-l_net) / (w_net - l_net) * 100
    need_be_naive = STOP / (TARGET + STOP) * 100
    res["ours_absolute"] = {
        "n": len(ours_rows), "win_rate": wins / len(ours_rows) * 100,
        "breakeven_rate": be / len(ours_rows) * 100,
        "required_win_rate": need_be, "required_naive": need_be_naive,
        "mean_win_net": w_net, "mean_loss_net": l_net,
        "margin": be / len(ours_rows) * 100 - need_be,
        "per_trade": st.mean(nets), "median": st.median(nets),
        "by_year": {y: st.mean([r["net"] for r in ours_rows if r["year"] == y])
                    for y in YS if any(r["year"] == y for r in ours_rows)}}
    a = res["ours_absolute"]
    print("  n %d · 승률 %.2f%% · 순수익>0 %.2f%%"
          % (a["n"], a["win_rate"], a["breakeven_rate"]), flush=True)
    print("  이긴 거래 평균 %+.3f%%p · 진 거래 평균 %+.3f%%p → **필요 본전 승률 %.2f%%** "
          "(비용 무시하면 %.2f%%)" % (w_net, l_net, need_be, need_be_naive), flush=True)
    print("  → **여유 %+.2f%%p** · 거래당 %+.4f%%p · 중앙 %+.4f"
          % (a["margin"], a["per_trade"], a["median"]), flush=True)
    print("  연도별 거래당: %s" % {k: round(v, 3) for k, v in a["by_year"].items()},
          flush=True)

    print("\n═══ 구조적 영(零)·풀 부족 (M29-3) ═══", flush=True)
    print("  적격 풀 ≤ k 라 대조가 우리와 같아지는 날 %d일 · 거래 %d건"
          % (diag["days_pool_eq_k"], diag["trades_pool_eq_k"]), flush=True)
    for nm, v in diag["beta_pool_short"].items():
        print("  %s 풀이 k보다 작은 날 %d일 · 모자란 건수 %d"
              % (nm, v, diag["beta_trades_short"][nm]), flush=True)
    print("  시계열 결측 종목 %d / 적격 %d" % (diag["series_missing"],
                                        diag["eligible_codes"]), flush=True)
    print("  대조군 소멸(마지막 종가·200일 미만) %s" % dict(diag["vanished"]), flush=True)
    print("  우리 종목이 β1(전일 고가)을 못 넘어 진입 못 한 건 %d / %d"
          % (diag["ours_beta1_no_breakout"], len(ours_rows)), flush=True)
    print("  ATR 맞춤에서 구간이 비어 인접 구간으로 물러난 횟수 %s"
          % dict(diag["atr_band_fallback"]), flush=True)

    print("\n═══ ATR 분포 (검증 [1]) ═══", flush=True)
    ao = [x for x in atr_dist["ours"] if x is not None]
    res["atr"] = {"ours": {"median": st.median(ao), "mean": st.mean(ao),
                           "bands": {b: sum(1 for x in ao if atr_band(x) == b) / len(ao) * 100
                                     for b in ("①조용 <2.5%", "②보통 2.5~4%",
                                               "③큼 4~6%", "④매우큼 6%+")}}}
    print("  우리 ATR 중앙 %.2f%% · 구간 %s"
          % (res["atr"]["ours"]["median"],
             {k: round(v, 1) for k, v in res["atr"]["ours"]["bands"].items()}), flush=True)

    for nm in ("α시가", "β1일고가"):
        v = [x for x in atr_dist[nm] if x is not None]
        if v:
            res["atr"][nm] = {"median": st.median(v), "n": len(v),
                              "bands": {b: sum(1 for x in v if atr_band(x) == b)
                                        / len(v) * 100
                                        for b in ("①조용 <2.5%", "②보통 2.5~4%",
                                                  "③큼 4~6%", "④매우큼 6%+")}}
            print("  %-8s ATR 중앙 %.2f%% (n=%d) · 구간 %s"
                  % (nm, st.median(v), len(v),
                     {k: round(x, 1) for k, x in res["atr"][nm]["bands"].items()}),
                  flush=True)

    if cap_dist["ours"]:
        co = sorted(cap_dist["ours"])
        res["cap"] = {"ours_median": st.median(co), "n": len(co)}
        print("\n═══ 시점 시총 분포 (검증 [3] · 문턱 사전 등록) ═══", flush=True)
        cut = sorted(co)[int(len(co) * 2 / 3)]
        print("  우리 중앙 %.0f억 (n=%d) · 상위3분위 경계 %.0f억"
              % (st.median(co), len(co), cut), flush=True)
        for nm in ("α시가", "β1일고가"):
            v = cap_dist.get(nm)
            if not v:
                continue
            ratio = st.median(co) / st.median(v)
            top_o = sum(1 for x in co if x >= cut) / len(co) * 100
            top_c = sum(1 for x in v if x >= cut) / len(v) * 100
            trip = ratio > 2 or ratio < 0.5 or abs(top_o - top_c) > 20
            res.setdefault("cap_cmp", {})[nm] = {
                "ctrl_median": st.median(v), "ratio": ratio,
                "top_tercile_ours": top_o, "top_tercile_ctrl": top_c,
                "triggers_matched_arm": bool(trip)}
            print("  %-8s 중앙 %.0f억 · 비율 %.2f배 · 상위3분위 우리 %.1f%% vs 대조 "
                  "%.1f%% → 맞춤 대조 문턱 %s"
                  % (nm, st.median(v), ratio, top_o, top_c,
                     "**넘음(돌려야 함)**" if trip else "안 넘음(안 돌림)"), flush=True)

    (OUT / "16-selection-edge.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/16-selection-edge.json")


if __name__ == "__main__":
    main()

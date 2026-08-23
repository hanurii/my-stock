# -*- coding: utf-8 -*-
"""04 — 초수익 잠재력 점수 (페이지 주장 6).

지시서: research/handoff/tasks/04-superperf-score.md (v2 + M9-12 + M10~M20)

**이 판정은 "+20% 도달"에 대한 것이고, RS 80 이상 후보 안에서의 이야기다.**
점수는 원래 "6개월 안에 두 배"를 맞히려고 만든 것이다.

지수 정본 (두뇌 세션 확정, M17-5 후속)
--------------------------------------
운영 코드 `screen_buy_recommendations.py` 가 **종목의 시장에 맞는 지수**를 쓴다
(`("KOSPI","KS11"), ("KOSDAQ","KQ11")`). 사용자가 실제로 본 점수를 재현해야 하므로
**정본 = 시장별 지수(KS11/KQ11, FDR)**. 부가로 `cw`(pdata 시총가중) 판을 함께 내고
**점수가 달라지는 이벤트 건수**를 센다.

판정 (M14-1 · M15 · M19-1 · M20)
--------------------------------
· 1순위 통계 = **점수 4+ 집단 − 2− 집단의 거래당 순수익 차이(%p)**. 양수면 "점수가 듣는다".
  페이지 주장은 **효과 없음**이다.
· 판정축 = 1순위 통계의 블록 부트스트랩 95% 구간(M14-1 표). 동등성 폭 **±0.5%p**.
· **렌즈는 강등만 한다.** 뒤집힌 문턱에서도 "렌즈가 적게 통과 = 효과 없음 확인"은 **폐기됨**(M20).
· 렌즈 넷: L1(같은날) · L2′(leave-one-year, entry_date) · L3(구간 5/5) · L4(집중도).
  **원형이동 순열은 폐기** — 같은날 비교라 회전에 불변이다(M11·M15).
· MDE = 2.80 × 부트스트랩 차이 SD.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/04-superperf-score.py
난수 seed: 블록 부트스트랩 40000 · 같은건수 대조 41000 · 슬롯 순서 0(부가 0~4)
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from math import comb, erf, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts"))
import slot_sim  # noqa: E402
from canslim_lib.pdata_series import build_series  # noqa: E402
from canslim_lib.superperf import compute_factors, score  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
PDATA = ROOT / ".cache" / "pdata"
WARM_DAYS = 430
CHUNK = 150                 # 한 번에 시계열을 만들 종목 수 (메모리 상한 조절)
CACHE = None                # 연도별 점수 캐시 경로 (아래 main 에서 설정)
N_BOOT = 1000
N_CTRL = 200
N_LEVEL = 200
N_PAIR = 400
BOOT_SEED, CTRL_SEED = 40000, 41000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K = 2.80
EQUIV = 0.5                 # M16-2: 04 의 동등성 폭 = 거래당 ±0.5%p
SEED5 = (0, 1, 2, 3, 4)
NINE = "2025-11-26"
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]
net = slot_sim.net


# ── 자료 ──────────────────────────────────────────────────────────────────

def load_events():
    ev, seen = [], set()
    ranges = {}
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        ranges[y] = (d["params"]["start"], d["params"]["end"])
        for e in d["events"]:
            if e["result"] not in ("win", "loss"):
                continue
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                continue
            seen.add(k)
            ev.append({"key": k, "code": e["code"], "pattern": e["pattern"],
                       "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                       "resolve_date": e["resolve_date"], "market": e.get("market"),
                       "gain": e["gain_at_resolve_pct"], "result": e["result"],
                       "rs": e.get("rs"), "year_file": y,
                       "year": e["entry_date"][:4],
                       "net": net(e["gain_at_resolve_pct"])})
    return ev, ranges


def load_indexes():
    """정본 = 시장별 지수(KS11/KQ11). 실패하면 None 을 돌려 cw 로 대체한다."""
    try:
        import FinanceDataReader as fdr
        out = {}
        for mkt, code in (("KOSPI", "KS11"), ("KOSDAQ", "KQ11")):
            df = fdr.DataReader(code, "2020-01-01", "2026-08-21")
            out[mkt] = {d.strftime("%Y-%m-%d"): float(c)
                        for d, c in zip(df.index, df["Close"])}
            print("  %s(%s) %d일 %s ~ %s" % (mkt, code, len(out[mkt]),
                                             min(out[mkt]), max(out[mkt])), flush=True)
        return out
    except Exception as e:                                   # noqa: BLE001
        print("  ⚠ FDR 취득 실패: %s %s" % (type(e).__name__, e), flush=True)
        return None


def load_cw():
    d = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))
    return dict(zip(d["dates"], d["cw"])), d


def iter_pdata(start, end, keep):
    s, e = start.replace("-", ""), end.replace("-", "")
    for p in sorted(PDATA.glob("price_*.json")):
        dd = p.stem[6:]
        if not (s <= dd <= e):
            continue
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        yield "%s-%s-%s" % (dd[:4], dd[4:6], dd[6:]), {c: r for c, r in recs.items()
                                                       if c in keep}


# ── 통계 도구 ─────────────────────────────────────────────────────────────

def _phi(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def sign_test(diffs):
    n = len(diffs)
    pos = sum(1 for x in diffs if x > 0)
    k = min(pos, n - pos)
    if n <= 100:
        p = min(1.0, 2 * sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n))
        how = "이항 정확"
    else:
        z = (abs(pos - n / 2) - 0.5) / (sqrt(n) / 2)
        p = min(1.0, 2 * (1 - _phi(z)))
        how = "정규근사(연속성 보정)"
    return {"n": n, "n_positive": pos, "mean": st.mean(diffs),
            "median": st.median(diffs), "p": p, "how": how}


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    n = len(s)
    return s[int(n * lo / 100)], s[int(n * hi / 100) - 1]


def make_blocks(rnd, n_pos):
    blocks, total = [], 0
    while total < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - total)
        blocks.append((a, LL))
        total += LL
    return blocks


def block_boot_groups(hi_by_pos, lo_by_pos, n_pos, seed, n_boot=N_BOOT):
    """복제마다 두 집단의 평균 차이(고득점 − 저득점)를 다시 계산."""
    rnd = random.Random(seed)
    out = []
    for _ in range(n_boot):
        H, L = [], []
        for a, ln in make_blocks(rnd, n_pos):
            for j in range(ln):
                H.extend(hi_by_pos.get(a + j, ()))
                L.extend(lo_by_pos.get(a + j, ()))
        if H and L:
            out.append(st.mean(H) - st.mean(L))
    return out


def summarize(rows):
    if not rows:
        return {"n": 0, "win_rate": None, "mean_net": None}
    return {"n": len(rows),
            "win_rate": sum(1 for r in rows if r["result"] == "win") / len(rows) * 100,
            "mean_net": st.mean([r["net"] for r in rows])}


def main():
    print("이벤트 적재 …", flush=True)
    ev, ranges = load_events()
    print("확정 %d건" % len(ev), flush=True)
    rs_vals = [e["rs"] for e in ev if e["rs"] is not None]
    print("RS 결측 %d · 범위 %d~%d · 80~89 %d건(%.1f%%) · 90+ %d건(%.1f%%)"
          % (len(ev) - len(rs_vals), min(rs_vals), max(rs_vals),
             sum(1 for v in rs_vals if v < 90), sum(1 for v in rs_vals if v < 90) / len(ev) * 100,
             sum(1 for v in rs_vals if v >= 90), sum(1 for v in rs_vals if v >= 90) / len(ev) * 100),
          flush=True)

    print("지수 적재 …", flush=True)
    mkt_idx = load_indexes()
    cw, reg = load_cw()
    idx_source = "시장별(KS11/KQ11)" if mkt_idx else "cw(pdata 시총가중) — FDR 실패 대체"
    print("  지수 정본: %s" % idx_source, flush=True)

    # ── M21-2 지수 무결성 점검 (정본이 KS11/KQ11 로 바뀌어 점검 대상도 바뀜) ──
    cal_win = [d for d in reg["dates"] if "2021-02-01" <= d <= "2026-08-21"]
    integ = {"calendar_days_in_window": len(cal_win)}
    if mkt_idx:
        for mkt in ("KOSPI", "KOSDAQ"):
            ks = mkt_idx[mkt]
            miss = [d for d in cal_win if d not in ks]
            integ[mkt] = {"n_days": len(ks), "first": min(ks), "last": max(ks),
                          "missing_in_window": len(miss),
                          "missing_examples": miss[:10]}
            print("  [M21-2] %s 지수 %d일 (%s ~ %s) · 창 안 결측 %d일"
                  % (mkt, len(ks), min(ks), max(ks), len(miss)), flush=True)
        # 하루 밀림 점검 — cw 등락률과의 시차 상관에서 lag 0 이 최대여야 한다
        cwmap = cw
        for mkt in ("KOSPI", "KOSDAQ"):
            ks = mkt_idx[mkt]
            ds = [d for d in cal_win if d in ks and d in cwmap]
            a = [ks[ds[i]] / ks[ds[i - 1]] - 1 for i in range(1, len(ds))]
            b = [cwmap[ds[i]] / cwmap[ds[i - 1]] - 1 for i in range(1, len(ds))]

            def _corr(x, y):
                n = len(x)
                mx, my = st.mean(x), st.mean(y)
                cv = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)
                return cv / (st.stdev(x) * st.stdev(y))

            lags = {"-1": _corr(a[1:], b[:-1]), "0": _corr(a, b), "+1": _corr(a[:-1], b[1:])}
            integ[mkt]["lag_corr_vs_cw"] = lags
            integ[mkt]["shift_ok"] = lags["0"] == max(lags.values())
            print("  [M21-2] %s 시차 상관 −1 %.4f · 0 **%.4f** · +1 %.4f → 밀림 %s"
                  % (mkt, lags["-1"], lags["0"], lags["+1"],
                     "없음" if integ[mkt]["shift_ok"] else "**의심**"), flush=True)
    res_integrity = integ

    # 지수 일치 대조 (M17-5, 기록용 — 정본이 바뀌었으므로 참고 수치)
    dates_r, cws, kss = reg["dates"], reg["cw"], reg["kospi"]
    ix = [i for i, d in enumerate(dates_r) if "2021-02-01" <= d <= "2026-08-20" and kss[i]]
    rc = [cws[ix[i]] / cws[ix[i - 1]] - 1 for i in range(1, len(ix))]
    rk = [kss[ix[i]] / kss[ix[i - 1]] - 1 for i in range(1, len(ix))]
    mc, mk = st.mean(rc), st.mean(rk)
    corr = (sum((rc[i] - mc) * (rk[i] - mk) for i in range(len(rc))) / (len(rc) - 1)
            / (st.stdev(rc) * st.stdev(rk)))
    index_check = {"corr_daily_returns": corr,
                   "cw_total_pct": (cws[ix[-1]] / cws[ix[0]] - 1) * 100,
                   "kospi_total_pct": (kss[ix[-1]] / kss[ix[0]] - 1) * 100,
                   "n_days": len(ix),
                   "note": "cw 는 KOSPI+KOSDAQ 전체 시총가중이고 코스피 지수는 KOSPI 만이라 "
                           "애초에 다른 지수다. 정본은 시장별 지수."}
    print("  [M17-5] 일별 상관 %.4f · 구간 총수익 cw %+.1f%% vs 코스피 %+.1f%%"
          % (corr, index_check["cw_total_pct"], index_check["kospi_total_pct"]), flush=True)

    # ── 점수 재산출 ──
    by_year = defaultdict(list)
    for e in ev:
        by_year[e["year_file"]].append(e)
    n_fail = 0
    # 연도별 점수를 디스크에 캐시한다 — 계산이 중간에 죽어도 이어서 돌 수 있게.
    cache_dir = OUT / "_04_score_cache"
    cache_dir.mkdir(exist_ok=True)
    for y in sorted(by_year):
        cf = cache_dir / ("scores_%d.json" % y)
        if cf.exists():
            got = json.loads(cf.read_text(encoding="utf-8"))
            idx_by_key = {tuple(k.split("|")): v for k, v in got["scores"].items()}
            for e in by_year[y]:
                v = idx_by_key.get(e["key"])
                if v:
                    e.update(v)
            n_fail += got["n_fail"]
            print("[%d] 캐시에서 적재 (%d건, 실패 %d)"
                  % (y, len(idx_by_key), got["n_fail"]), flush=True)
            continue
        start, end = ranges[y]
        warm = (datetime.strptime(start, "%Y-%m-%d")
                - timedelta(days=WARM_DAYS)).strftime("%Y-%m-%d")
        codes = sorted({e["code"] for e in by_year[y]})
        print("[%d] 시계열 %s ~ %s · 종목 %d (청크 %d) …" % (y, warm, end, len(codes), CHUNK),
              flush=True)
        for ci_ in range(0, len(codes), CHUNK):
            chunk = set(codes[ci_:ci_ + CHUNK])
            series = build_series(iter_pdata(warm, end, chunk))
            for e in by_year[y]:
                if e["code"] not in chunk:
                    continue
                s = series.get(e["code"])
                if not s:
                    continue                     # 실패는 연도 끝에서 yfail 로 한 번만 센다
                keep = sum(1 for d in s["dates"] if d <= e["scan_date"])
                if keep < 65:
                    continue
                ds, cs = s["dates"][:keep], s["closes"][:keep]
                hs = s["highs"][:keep]
                for tag, index_map in (("mkt", (mkt_idx or {}).get(e["market"]) or cw),
                                       ("cw", cw)):
                    f = compute_factors(ds, cs, hs, index_map)
                    p6, _ = score(e["rs"], f["prior_adv"], f["rs_nh_days"], f["rs_leads"])
                    p4, _ = score(None, f["prior_adv"], f["rs_nh_days"], f["rs_leads"])
                    e["score6_" + tag] = p6
                    e["score4_" + tag] = p4
                    e["factors_" + tag] = f
            del series
            print("    청크 %d~%d 완료" % (ci_ + 1, min(ci_ + CHUNK, len(codes))), flush=True)
        # 이 해의 결과를 캐시에 저장
        saved, yfail = {}, 0
        for e in by_year[y]:
            if "score6_mkt" in e:
                saved["|".join(e["key"])] = {
                    "score6_mkt": e["score6_mkt"], "score4_mkt": e["score4_mkt"],
                    "score6_cw": e["score6_cw"], "score4_cw": e["score4_cw"],
                    "factors_mkt": e["factors_mkt"], "factors_cw": e["factors_cw"]}
            else:
                yfail += 1
        cf.write_text(json.dumps({"year": y, "n_fail": yfail, "scores": saved},
                                 ensure_ascii=False), encoding="utf-8")
        n_fail += yfail
        print("[%d] 캐시 저장 %d건 (실패 %d)" % (y, len(saved), yfail), flush=True)
    print("점수 산출 실패 %d건" % n_fail, flush=True)
    ok = [e for e in ev if "score6_mkt" in e]
    print("점수 산출 성공 %d건" % len(ok), flush=True)

    # 정본 vs cw 판 점수 차이
    diff6 = sum(1 for e in ok if e["score6_mkt"] != e["score6_cw"])
    diff4 = sum(1 for e in ok if e["score4_mkt"] != e["score4_cw"])
    print("지수 선택으로 점수가 달라진 건수: 6점판 %d건(%.1f%%) · 4점판 %d건(%.1f%%)"
          % (diff6, diff6 / len(ok) * 100, diff4, diff4 / len(ok) * 100), flush=True)

    # ── M21-3 검산: 지수를 바꿔서 달라질 수 있는 요인은 rs_nh_days · rs_leads 뿐이다 ──
    #   prior_adv 는 지수를 안 쓰므로 **차이가 0이어야 한다**. 0이 아니면 구현 오류.
    fdiff = {}
    for f in ("prior_adv", "rs_nh_days", "rs_leads", "dist_52wh"):
        fdiff[f] = sum(1 for e in ok
                       if e["factors_mkt"].get(f) != e["factors_cw"].get(f))
    print("[M21-3 검산] 요인별 차이 건수 %s" % fdiff, flush=True)
    print("            prior_adv 는 지수를 안 쓰므로 **0이어야 한다** → %s"
          % ("정상" if fdiff["prior_adv"] == 0 else "**구현 오류 의심**"), flush=True)

    res = {"n_events": len(ev), "n_scored": len(ok), "n_score_fail": n_fail,
           "index_source": idx_source, "index_check": index_check,
           "index_integrity": res_integrity, "factor_diff_check": fdiff,
           "score_diff_by_index": {"score6": diff6, "score4": diff4},
           "rs": {"missing": len(ev) - len(rs_vals), "min": min(rs_vals),
                  "max": max(rs_vals),
                  "n_80_89": sum(1 for v in rs_vals if v < 90),
                  "n_90p": sum(1 for v in rs_vals if v >= 90)},
           "equiv_bound": EQUIV, "mde_k": MDE_K, "runs": {}}

    # ── 판별: 6점판(정본) · 4점판(부가) ──
    cal = reg["dates"]
    lo_d = min(e["entry_date"] for e in ok)
    hi_d = max(e["resolve_date"] for e in ok)
    all_dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(all_dates)}
    n_pos = len(all_dates)

    for tag, field, hi_cut, lo_cut in (("6점만점(정본)", "score6_mkt", 4, 2),
                                       ("4점만점·RS제거(부가)", "score4_mkt", 3, 1)):
        H = [e for e in ok if e[field] >= hi_cut]
        L = [e for e in ok if e[field] <= lo_cut]
        byday_h, byday_l = defaultdict(list), defaultdict(list)
        for e in H:
            byday_h[e["entry_date"]].append(e["net"])
        for e in L:
            byday_l[e["entry_date"]].append(e["net"])
        both = sorted(set(byday_h) & set(byday_l))
        print("\n===== %s (%d+ vs %d−) =====" % (tag, hi_cut, lo_cut), flush=True)
        print("고득점 %d건 · 저득점 %d건 · **L1 성립 날 %d일**"
              % (len(H), len(L), len(both)), flush=True)
        if not H or not L or len(both) < 30:
            print("  ⚠ 표본 하한 미달 — 자동 판정불가", flush=True)
        S = st.mean([e["net"] for e in H]) - st.mean([e["net"] for e in L])
        hb = defaultdict(list)
        lb = defaultdict(list)
        for e in H:
            hb[pos_of[e["entry_date"]]].append(e["net"])
        for e in L:
            lb[pos_of[e["entry_date"]]].append(e["net"])
        boot = block_boot_groups(hb, lb, n_pos, BOOT_SEED)
        blo, bhi = ci(boot)
        sd = st.stdev(boot)
        daily = [st.mean(byday_h[d]) - st.mean(byday_l[d]) for d in both]
        l1 = sign_test(daily)
        dboot = []
        rnd = random.Random(BOOT_SEED + 5)
        for _ in range(N_BOOT):
            acc = [daily[rnd.randrange(len(daily))] for _ in range(len(daily))]
            dboot.append(st.median(acc))
        dlo, dhi = ci(dboot)
        years = sorted({e["year"] for e in ok})
        dyr = {}
        for y in years:
            hh = [e["net"] for e in H if e["year"] != y]
            ll = [e["net"] for e in L if e["year"] != y]
            dyr[y] = st.mean(hh) - st.mean(ll) if hh and ll else None
        segs = {}
        for sn, y0, y1 in SEGMENTS:
            hh = [e["net"] for e in H if y0 <= e["year"] <= y1]
            ll = [e["net"] for e in L if y0 <= e["year"] <= y1]
            segs[sn] = {"n_hi": len(hh), "n_lo": len(ll),
                        "diff": (st.mean(hh) - st.mean(ll)) if hh and ll else None}
        # L4: S 를 가장 크게 떠받치는 5건 제거
        allv = [(e["net"], 1) for e in H] + [(e["net"], 0) for e in L]
        hs_, hn = sum(v for v, g in allv if g), sum(1 for v, g in allv if g)
        ls_, ln_ = sum(v for v, g in allv if not g), sum(1 for v, g in allv if not g)
        eff = []
        for i, (v, g) in enumerate(allv):
            s2 = ((hs_ - v) / (hn - 1) - ls_ / ln_) if g else (hs_ / hn - (ls_ - v) / (ln_ - 1))
            eff.append((s2, i))
        eff.sort()

        def _after(dset):
            a = sum(v for i, (v, g) in enumerate(allv) if g and i not in dset)
            an = sum(1 for i, (v, g) in enumerate(allv) if g and i not in dset)
            b = sum(v for i, (v, g) in enumerate(allv) if not g and i not in dset)
            bn = sum(1 for i, (v, g) in enumerate(allv) if not g and i not in dset)
            return a / an - b / bn

        # ★ M30 (정본) — |기여| 가 큰 5건, 즉 **양쪽 꼬리**를 뺀다.
        #   한쪽(가장 양수 기여)만 빼면 S 가 이미 음수일 때 부호가 뒤집힐 수 없어
        #   실패할 수 없는 검정이 된다.
        S4 = _after({i for _, i in sorted(eff, key=lambda t: -abs(t[0] - S))[:5]})
        S4_one = _after({i for _, i in eff[:5]})     # 옛 한쪽 꼬리 판 (참고)
        excl = blo > 0 or bhi < 0
        within = -EQUIV <= blo and bhi <= EQUIV
        verdict = ("폐기" if (excl and S > 0) else "폐기(반대 방향)" if excl
                   else "유지(동등성 확인)" if within else "확인 불가(검정력 부족)")
        # ★ M27 — 렌즈는 **1순위 통계 S 와 부호가 맞을 때만** 통과다.
        #   "가설 방향(양수)에 맞는가"를 물으면 판정축이 이미 재는 것을 두 번 재게 된다.
        sg = 1 if S > 0 else -1
        l1_sig = bool(l1["p"] < 0.05 and (dlo > 0 or dhi < 0))
        lens = {"L1": bool(l1_sig and (l1["median"] > 0) == (sg > 0)),
                "L2p": all(v is not None and (v > 0) == (sg > 0) for v in dyr.values()),
                "L3": all(v["diff"] is not None and (v["diff"] > 0) == (sg > 0)
                          for v in segs.values()),
                "L4": (S4 > 0) == (sg > 0)}
        print("1순위 S = %+.4f%%p · 95%% 구간 %+.4f ~ %+.4f (0 제외 %s) · ±0.5 안 %s · "
              "SD %.4f · MDE %.4f%%p → **%s**"
              % (S, blo, bhi, "예" if excl else "아니오", "예" if within else "아니오",
                 sd, MDE_K * sd, verdict), flush=True)
        print("L1 같은날: 날 %d · 양수 %d · 중앙 %+.4f · p=%.4f (%s) · 중앙 95%% %+.4f ~ %+.4f"
              % (l1["n"], l1["n_positive"], l1["median"], l1["p"], l1["how"], dlo, dhi),
              flush=True)
        print("L2′ 연도별 %s" % {y: (None if v is None else round(v, 3))
                                 for y, v in dyr.items()}, flush=True)
        print("L3 구간별 %s" % {k: (None if v["diff"] is None else round(v["diff"], 3))
                               for k, v in segs.items()}, flush=True)
        print("L4 |기여|상위5 제거(양쪽 꼬리) S %+.4f → %+.4f "
              "(참고: 한쪽 꼬리 판이면 %+.4f)" % (S, S4, S4_one), flush=True)
        print("렌즈: L1 %s · L2′ %s · L3 %s · L4 %s → %d/4"
              % (*["통과" if lens[k] else "미통과" for k in ("L1", "L2p", "L3", "L4")],
                 sum(lens.values())), flush=True)
        res["runs"][tag] = {"n_hi": len(H), "n_lo": len(L), "n_l1_days": len(both),
                            "S": S, "ci_lo": blo, "ci_hi": bhi, "excludes_zero": excl,
                            "within_equiv": within, "boot_sd": sd, "MDE": MDE_K * sd,
                            "verdict_axis": verdict, "L1": l1,
                            "L1_median_ci": [dlo, dhi], "drop_year": dyr,
                            "segments": segs, "S_drop_top5": S4,
                            "S_drop_top5_one_tail": S4_one,
                            "L4_rule": "|기여| 상위 5건 = 양쪽 꼬리 (M30)",
                            "L1_significant_only": l1_sig, "lenses": lens,
                            "n_lenses": sum(lens.values())}

    # ── 점수별 표 ──
    for field, name in (("score6_mkt", "6점만점(정본)"), ("score4_mkt", "4점만점·RS제거")):
        tbl = {}
        for sc in range(0, 7):
            g = [e for e in ok if e[field] == sc]
            if not g:
                continue
            row = summarize(g)
            row["segments"] = {sn: summarize([e for e in g if y0 <= e["year"] <= y1])
                               for sn, y0, y1 in SEGMENTS}
            nine = [e for e in g if e["scan_date"] >= NINE]
            row["nine_month"] = summarize(nine)
            tbl[sc] = row
        res["score_table_" + field] = tbl
        print("\n[%s 점수별]" % name, flush=True)
        for sc, row in sorted(tbl.items()):
            print("  %d점  n=%4d 승률 %5.1f%% 거래당 %+7.3f%% · 9개월 n=%3d 승률 %s"
                  % (sc, row["n"], row["win_rate"], row["mean_net"],
                     row["nine_month"]["n"],
                     "—" if row["nine_month"]["win_rate"] is None
                     else "%.1f%%" % row["nine_month"]["win_rate"]), flush=True)

    # ── 슬롯5 (부차) + 밴드 폭 (M18-1) ──
    print("\n[부차·슬롯5]", flush=True)
    arms = {"전부": ok,
            "점수 3+ 만": [e for e in ok if e["score6_mkt"] >= 3],
            "점수 2− 만": [e for e in ok if e["score6_mkt"] <= 2]}
    slot = {}
    for nm, tr in arms.items():
        b = slot_sim.band(tr, n_runs=N_LEVEL)
        width = b["p95"] - b["p5"]
        slot[nm] = {**b, "band_width": width, "n_trades": len(tr)}
        print("  %-10s n=%4d 중앙 %+7.1f%% · 5~95%% %+7.1f~%+7.1f (**폭 %.1f%%p**) · 체결 %.0f"
              % (nm, len(tr), b["median"], b["p5"], b["p95"], width, b["n_filled"]),
              flush=True)
    res["slot5"] = slot

    # 같은 건수 무작위 표집 대조
    n3 = len(arms["점수 3+ 만"])
    rnd = random.Random(CTRL_SEED)
    ctrl = []
    for i in range(N_CTRL):
        samp = rnd.sample(ok, n3)
        ctrl.append(slot_sim.sim(samp, seed=i)["equity_pct"])
    clo, chi = ci(ctrl)
    res["same_count_control"] = {"n": n3, "median": st.median(ctrl),
                                 "p5": clo, "p95": chi,
                                 "vs_score3plus": slot["점수 3+ 만"]["median"] - st.median(ctrl)}
    print("  같은 건수(%d) 무작위 표집 대조: 중앙 %+.1f%% (5~95%% %+.1f~%+.1f) · "
          "점수 3+ 판과의 차이 %+.1f%%p"
          % (n3, st.median(ctrl), clo, chi, res["same_count_control"]["vs_score3plus"]),
          flush=True)

    (OUT / "04-superperf-score.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/04-superperf-score.json")


if __name__ == "__main__":
    main()

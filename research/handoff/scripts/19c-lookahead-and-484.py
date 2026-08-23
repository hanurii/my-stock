# -*- coding: utf-8 -*-
"""19 · 3단계 — 룩어헤드가 이 하네스에서 얼마짜리인가 (+ 484건 계수).

★ **표만 채우고 해석을 붙이지 않는다**(M34). 목적은 오직
  "이 하네스에서 룩어헤드가 얼마짜리인지"를 재는 것뿐이다.
  원 주장(메모리의 "≥3배 85%승"·"1.5배 유일 생존") 판정은 **별도 과제**다.

★ 함께: 20번 준비용 **484건 계수 셋**(분석 없이 세기만).
  ① 결착 결과 분포와 거래당 ② 슬롯5 체결 건수(200 seed 중앙) ③ 월 분포
★ 그리고 **표본 크기별로 무엇을 물으면 가릴 수 있는지**를 수치로(설계 답변용).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/19c-lookahead-and-484.py
난수 seed: 블록 부트스트랩 192000 · 슬롯 순서 0~199
"""
from __future__ import annotations

import importlib.util
import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
MIN_DAILY = ROOT / ".cache" / "min_daily"
CONTAM = "rel_vol_entry_LOOKAHEAD_DO_NOT_FILTER"
N_BOOT, BOOT_SEED = 1000, 192000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K = 2.80
N_SEED = 200
BUCKETS = [("<1.0", None, 1.0), ("1.0~1.5", 1.0, 1.5), ("1.5~2.0", 1.5, 2.0),
           ("2.0~3.0", 2.0, 3.0), ("≥3.0", 3.0, None)]
K = (1 - 0.002034) / (1 + 0.000034)


def net(g):
    return ((1 + g / 100) * K - 1) * 100


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def make_blocks(rnd, n):
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n - L)
        LL = min(L, n - tot)
        out.append((a, LL))
        tot += LL
    return out


def boot(ha, hb, dates, seed):
    rnd = random.Random(seed)
    out = []
    for _ in range(N_BOOT):
        a, b = [], []
        for s_, L in make_blocks(rnd, len(dates)):
            for j in range(L):
                d = dates[s_ + j]
                a.extend(ha.get(d, ()))
                b.extend(hb.get(d, ()))
        if a and b:
            out.append(st.mean(a) - st.mean(b))
    return out


def bucket_of(v):
    for nm, lo, hi in BUCKETS:
        if (lo is None or v >= lo) and (hi is None or v < hi):
            return nm
    return BUCKETS[-1][0]


def main():
    feat = {(_r["scan_date"], _r["code"], _r["pattern"]): _r
            for _r in json.loads(
                (OUT / "19-volume-features.json").read_text(encoding="utf-8"))["rows"]}
    rows, seen = [], set()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen or k not in feat:
                continue
            seen.add(k)
            f = feat[k]
            rows.append({"code": e["code"], "pattern": e["pattern"],
                         "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                         "resolve_date": e["resolve_date"] or e["entry_date"],
                         "year": e["entry_date"][:4], "gain": e["gain_at_resolve_pct"],
                         "result": e["result"], "net": net(e["gain_at_resolve_pct"]),
                         "rv_1": f["rv_1"], "contam": e.get(CONTAM)})
    rows = [r for r in rows if r["rv_1"] is not None and r["contam"] is not None]
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(r["entry_date"] for r in rows)
    hi_d = max(r["entry_date"] for r in rows)
    dates = [x for x in cal if lo_d <= x <= hi_d]
    print("표본 %d건" % len(rows), flush=True)
    res = {"n": len(rows),
           "note": "3단계는 표만 채우고 해석을 붙이지 않는다(M34)."}

    print("\n═══ 3단계 · 룩어헤드 크기 — 표만 ═══", flush=True)
    print("\n  [구간 분포]", flush=True)
    dist = {}
    for nm, _, _ in BUCKETS:
        a = sum(1 for r in rows if bucket_of(r["rv_1"]) == nm)
        b = sum(1 for r in rows if bucket_of(r["contam"]) == nm)
        dist[nm] = {"clean": a, "contam": b}
        print("   %-8s 깨끗 %4d (%5.1f%%) · 오염 %4d (%5.1f%%)"
              % (nm, a, a / len(rows) * 100, b, b / len(rows) * 100), flush=True)
    res["distribution"] = dist

    def two_group(field, thr, seed):
        A = [r for r in rows if r[field] >= thr]
        B = [r for r in rows if r[field] < thr]
        ha, hb = defaultdict(list), defaultdict(list)
        for r in A:
            ha[r["entry_date"]].append(r["net"])
        for r in B:
            hb[r["entry_date"]].append(r["net"])
        diff = st.mean(r["net"] for r in A) - st.mean(r["net"] for r in B)
        bs = boot(ha, hb, dates, seed)
        lo, hi = ci(bs)
        wr = sum(1 for r in A if r["result"] == "win") / len(A) * 100
        return {"n_a": len(A), "n_b": len(B), "diff": diff, "ci": [lo, hi],
                "MDE": MDE_K * st.stdev(bs), "win_rate_a": wr,
                "excludes_zero": bool(lo > 0 or hi < 0)}

    print("\n  [≥1.5 vs <1.5 거래당 차이]", flush=True)
    t15 = {}
    for f, nm, sd_ in (("rv_1", "깨끗 rv_1", 1), ("contam", "오염 필드", 2)):
        v = two_group(f, 1.5, BOOT_SEED + sd_)
        t15[nm] = v
        print("   %-10s %4d vs %4d · 차이 **%+.4f%%p** · 95%% %+.4f ~ %+.4f · MDE %.4f · 0 %s"
              % (nm, v["n_a"], v["n_b"], v["diff"], v["ci"][0], v["ci"][1], v["MDE"],
                 "제외" if v["excludes_zero"] else "포함"), flush=True)
    print("   **차이의 차이: %+.4f%%p**" % (t15["오염 필드"]["diff"] - t15["깨끗 rv_1"]["diff"]),
          flush=True)
    res["ge1_5"] = t15

    print("\n  [≥3.0 승률]", flush=True)
    t30 = {}
    for f, nm, sd_ in (("rv_1", "깨끗 rv_1", 3), ("contam", "오염 필드", 4)):
        v = two_group(f, 3.0, BOOT_SEED + sd_)
        t30[nm] = v
        print("   %-10s n=%4d · **승률 %.2f%%** · 거래당 차이 %+.4f%%p (95%% %+.4f ~ %+.4f)"
              % (nm, v["n_a"], v["win_rate_a"], v["diff"], v["ci"][0], v["ci"][1]),
              flush=True)
    base_wr = sum(1 for r in rows if r["result"] == "win") / len(rows) * 100
    print("   (전체 승률 %.2f%%) · **승률의 차이: %+.2f%%p**"
          % (base_wr, t30["오염 필드"]["win_rate_a"] - t30["깨끗 rv_1"]["win_rate_a"]),
          flush=True)
    res["ge3_0"] = t30
    res["base_win_rate"] = base_wr

    # ── 484건 계수 (세기만) ──
    print("\n═══ 20번 준비 · 분봉 보유 484건 계수 (분석 없음) ═══", flush=True)
    have = set(p.stem for p in MIN_DAILY.iterdir())
    sub = [r for r in rows
           if "%s_%s" % (r["code"], r["entry_date"].replace("-", "")) in have]
    print("\n  ① 결착 결과 분포와 거래당", flush=True)
    cnt = Counter(r["result"] for r in sub)
    allc = Counter(r["result"] for r in rows)
    print("   484건: %s · 거래당 **%+.4f%%p** · 승률 %.2f%%"
          % (dict(cnt), st.mean(r["net"] for r in sub),
             cnt.get("win", 0) / len(sub) * 100), flush=True)
    print("   전체 %d건: %s · 거래당 %+.4f%%p · 승률 %.2f%%"
          % (len(rows), dict(allc), st.mean(r["net"] for r in rows), base_wr), flush=True)
    res["sub484"] = {"n": len(sub), "results": dict(cnt),
                     "per_trade": st.mean(r["net"] for r in sub),
                     "win_rate": cnt.get("win", 0) / len(sub) * 100,
                     "all_per_trade": st.mean(r["net"] for r in rows),
                     "all_win_rate": base_wr}

    print("\n  ② 슬롯5에서 실제 체결되는 건수 (200 seed)", flush=True)
    slot_sim.net = net
    subkeys = {(r["scan_date"], r["code"], r["pattern"]) for r in sub}
    fills = []
    for s in range(N_SEED):
        r = slot_sim.sim(rows, seed=s)
        # sim 은 체결 목록을 안 돌려주므로 같은 규약으로 다시 센다
        fills.append(r["n_filled"])
    # 체결분 중 484 부분집합이 몇 건인지 — fill_split 재사용
    spec = importlib.util.spec_from_file_location("g18", HERE / "18-slot-selection-cause.py")
    g18 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g18)
    pos_of = {d: i for i, d in enumerate(dates)}
    rows2 = [r for r in rows if r["entry_date"] in pos_of and r["resolve_date"] in pos_of]
    inter = []
    for s in range(N_SEED):
        fl, _, _ = g18.fill_split(rows2, dates, pos_of, s)
        inter.append(sum(1 for t in fl
                         if (t["scan_date"], t["code"], t["pattern"]) in subkeys))
    print("   전체 체결 중앙 %.0f건 · 그중 **분봉 보유분 중앙 %.0f건** (5~95%% %.0f~%.0f)"
          % (st.median(fills), st.median(inter), *ci(inter, 5, 95)), flush=True)
    res["sub484"]["slot5_filled_median"] = st.median(inter)
    res["sub484"]["slot5_filled_band"] = list(ci(inter, 5, 95))

    print("\n  ③ 월 분포", flush=True)
    m = Counter(r["entry_date"][:7] for r in sub)
    print("   달 수 %d · 상위 5: %s" % (len(m), m.most_common(5)), flush=True)
    print("   연도별: %s" % dict(sorted(Counter(r["year"] for r in sub).items())),
          flush=True)
    top3 = sum(c for _, c in m.most_common(3))
    print("   **상위 3개월이 %d / %d = %.1f%%**" % (top3, len(sub), top3 / len(sub) * 100),
          flush=True)
    res["sub484"]["months"] = dict(sorted(m.items()))
    res["sub484"]["top3_share"] = top3 / len(sub) * 100

    # ── 표본 크기별로 무엇을 가릴 수 있나 ──
    print("\n═══ 설계 답변용 · 표본 크기별 **가릴 수 있는 최소 크기** ═══", flush=True)
    sd = st.pstdev([r["net"] for r in rows])
    p0 = base_wr / 100
    n_slot = int(round(st.median(inter)))
    tbl = {}
    for nm, n, split in (("484건 · 절반 분할", len(sub), 0.5),
                         ("484건 · 5.5%% 분할(19번 비율)", len(sub), 0.055),
                         ("슬롯5 체결분 %d건 · 절반" % n_slot, n_slot, 0.5),
                         ("슬롯5 체결분 %d건 · 20%% 분할" % n_slot, n_slot, 0.2)):
        na = max(2, int(n * split))
        nb = n - na
        se = sd * sqrt(1 / na + 1 / nb)
        se_w = sqrt(p0 * (1 - p0) * (1 / na + 1 / nb)) * 100
        tbl[nm] = {"n_a": na, "n_b": nb, "need_per_trade": 1.96 * se,
                   "MDE_per_trade": MDE_K * se, "need_win_rate": 1.96 * se_w}
        print("  %-28s %4d vs %4d → 거래당 **%.2f%%p** 이상 · MDE %.2f%%p · "
              "승률 **%.1f%%p** 이상이어야 가린다"
              % (nm, na, nb, 1.96 * se, MDE_K * se, 1.96 * se_w), flush=True)
    res["power_table"] = tbl
    print("  (거래당 표준편차 %.2f%%p · 기저 승률 %.2f%% 기준)" % (sd, base_wr), flush=True)

    (OUT / "19c-lookahead-and-484.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/19c-lookahead-and-484.json")


if __name__ == "__main__":
    main()

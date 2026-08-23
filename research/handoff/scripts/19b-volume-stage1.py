# -*- coding: utf-8 -*-
"""19 · 1단계 — 깨끗한 거래량이 성적을 가르는가 (+ 분봉 보유 건수 계수).

지시서: research/handoff/tasks/19-volume-axis.md (M34 개정 반영)

★ 결론 첫 문단에 반드시 쓸 것 (두뇌 세션 확정)
  **`rv_1`이 재는 것은 "돌파일 거래량"이 아니라 "돌파 직전(scan_date)의 거래량"이다.**
  **메모리의 "돌파일 1.5배" 주장은 이 검정으로 확인도 반증도 되지 않는다.**
  돌파는 진입일 당일에 일어나고 그날 거래량이 곧 오염 필드이므로,
  **일봉으로는 원리상 검정할 수 없다** — 깨끗하면 돌파 전이고 돌파일이면 룩어헤드다.

★ M34 반영
  · 1.5·3.0은 **독립 검정이 아니다** → **"확인"이 아니라 "기술"**. 주지표는 **다섯 구간 단조성**.
  · 단조성은 **200건 미만 구간을 빼고** 판단하고 **뺐다는 사실을 적는다**(M34-O).
  · 조건 ③은 부호 유지가 아니라 **의존율** — 한 해를 빼서 **효과가 절반 이상 사라지는 해**가 있으면
    **결론 첫 줄에 쓴다**(M34-F·J).
  · **2021~2022 홀드아웃**을 별도로 한 번(어느 주장도 안 건드린 유일 구간).
  · `dryup`은 보조가 아니라 **`rv_1`과 나란히** 보고한다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/19b-volume-stage1.py
난수 seed: 블록 부트스트랩 190000 · 최대통계 191000
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
MIN_DAILY = ROOT / ".cache" / "min_daily"
N_BOOT, BOOT_SEED = 1000, 190000
N_MAX, MAX_SEED = 1000, 191000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K, EQUIV = 2.80, 0.5
MIN_BUCKET_FOR_MONO = 200
BUCKETS = [("<1.0", None, 1.0), ("1.0~1.5", 1.0, 1.5), ("1.5~2.0", 1.5, 2.0),
           ("2.0~3.0", 2.0, 3.0), ("≥3.0", 3.0, None)]
YS = ("2021", "2022", "2023", "2024", "2025", "2026")
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


def boot_diff(hi_by_d, lo_by_d, dates, seed):
    rnd = random.Random(seed)
    out = []
    for _ in range(N_BOOT):
        a, b = [], []
        for s_, L in make_blocks(rnd, len(dates)):
            for j in range(L):
                d = dates[s_ + j]
                a.extend(hi_by_d.get(d, ()))
                b.extend(lo_by_d.get(d, ()))
        if a and b:
            out.append(st.mean(a) - st.mean(b))
    return out


def bucket_of(v):
    for nm, lo, hi in BUCKETS:
        if (lo is None or v >= lo) and (hi is None or v < hi):
            return nm
    return BUCKETS[-1][0]


def main():
    d = json.loads((OUT / "19-volume-features.json").read_text(encoding="utf-8"))
    rows = [r for r in d["rows"] if r["rv_1"] is not None]
    for r in rows:
        r["net"] = net(r["gain"])
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(r["entry_date"] for r in rows)
    hi_d = max(r["entry_date"] for r in rows)
    dates = [x for x in cal if lo_d <= x <= hi_d]
    print("표본 %d건 · 거래일 %d · 비용 우대(왕복 0.207%%)" % (len(rows), len(dates)),
          flush=True)
    res = {"n": len(rows),
           "caveat": "rv_1 은 돌파일이 아니라 돌파 직전(scan_date)의 거래량이다."}

    # ── 1-1 구간표 (rv_1 · dryup 나란히) ──
    print("\n═══ 1-1 · 구간표 (rv_1) — 전부 싣는다 ═══", flush=True)
    tab = {}
    for nm, lo, hi in BUCKETS:
        sel = [r for r in rows if bucket_of(r["rv_1"]) == nm]
        if not sel:
            continue
        v = [r["net"] for r in sel]
        wr = sum(1 for r in sel if r["result"] == "win") / len(sel) * 100
        # 짝지은 95% — 같은 날 다른 구간과의 비교가 불가능한 칸이 많아 단순 부트스트랩
        rnd = random.Random(BOOT_SEED + len(nm))
        bs = [st.mean([v[rnd.randrange(len(v))] for _ in range(len(v))])
              for _ in range(N_BOOT)]
        blo, bhi = ci(bs)
        tab[nm] = {"n": len(sel), "win_rate": wr, "per_trade": st.mean(v),
                   "ci": [blo, bhi], "thin": len(sel) < MIN_BUCKET_FOR_MONO}
        print("  %-8s n=%4d %s 승률 %5.2f%% · 거래당 %+8.4f%%p · 95%% %+8.4f ~ %+8.4f"
              % (nm, len(sel), "⚠️얇음" if len(sel) < MIN_BUCKET_FOR_MONO else "     ",
                 wr, st.mean(v), blo, bhi), flush=True)
    res["buckets_rv1"] = tab

    print("\n═══ 1-1b · 구간표 (dryup — 수축) ═══", flush=True)
    dv = sorted(r["dryup"] for r in rows if r["dryup"] is not None)
    qs = [dv[int(len(dv) * q)] for q in (0.2, 0.4, 0.6, 0.8)]
    print("  dryup 5분위 경계: %s" % [round(x, 3) for x in qs], flush=True)
    dt = {}
    for i in range(5):
        lo = qs[i - 1] if i > 0 else -1e18
        hi = qs[i] if i < 4 else 1e18
        sel = [r for r in rows if r["dryup"] is not None and lo <= r["dryup"] < hi]
        v = [r["net"] for r in sel]
        rnd = random.Random(BOOT_SEED + 100 + i)
        bs = [st.mean([v[rnd.randrange(len(v))] for _ in range(len(v))])
              for _ in range(N_BOOT)]
        nm = "Q%d" % (i + 1)
        dt[nm] = {"n": len(sel), "range": [lo if i else None, hi if i < 4 else None],
                  "per_trade": st.mean(v), "ci": list(ci(bs)),
                  "win_rate": sum(1 for r in sel if r["result"] == "win") / len(sel) * 100}
        print("  %-4s n=%4d · 거래당 %+8.4f%%p · 95%% %+8.4f ~ %+8.4f · 승률 %5.2f%%"
              % (nm, len(sel), st.mean(v), *dt[nm]["ci"], dt[nm]["win_rate"]), flush=True)
    res["buckets_dryup"] = dt

    # ── 1-2 주검정 ──
    print("\n═══ 1-2 · 주검정 rv_1 ≥1.5 vs <1.5 — **확인이 아니라 기술**(M34) ═══",
          flush=True)
    tests = {}

    def main_test(name, pred, seed):
        A = [r for r in rows if pred(r)]
        B = [r for r in rows if not pred(r)]
        ha, hb = defaultdict(list), defaultdict(list)
        for r in A:
            ha[r["entry_date"]].append(r["net"])
        for r in B:
            hb[r["entry_date"]].append(r["net"])
        obs = st.mean(r["net"] for r in A) - st.mean(r["net"] for r in B)
        bs = boot_diff(ha, hb, dates, seed)
        lo, hi = ci(bs)
        sd = st.stdev(bs)
        tests[name] = {"n_a": len(A), "n_b": len(B), "diff": obs, "ci": [lo, hi],
                       "sd": sd, "MDE": MDE_K * sd,
                       "excludes_zero": bool(lo > 0 or hi < 0),
                       "within_equiv": bool(-EQUIV <= lo and hi <= EQUIV)}
        print("  %-16s %4d vs %4d · 차이 **%+.4f%%p** · 95%% **%+.4f ~ %+.4f** · "
              "MDE %.4f · 0 %s"
              % (name, len(A), len(B), obs, lo, hi, MDE_K * sd,
                 "제외" if tests[name]["excludes_zero"] else "**포함**"), flush=True)
        return tests[name]

    main_test("rv_1 ≥1.5", lambda r: r["rv_1"] >= 1.5, BOOT_SEED + 1)
    main_test("rv_1 ≥3.0", lambda r: r["rv_1"] >= 3.0, BOOT_SEED + 2)
    main_test("rv_5 ≥1.5", lambda r: r["rv_5"] is not None and r["rv_5"] >= 1.5,
              BOOT_SEED + 3)
    dmed = st.median(dv)
    main_test("dryup < 중앙", lambda r: r["dryup"] is not None and r["dryup"] < dmed,
              BOOT_SEED + 4)
    res["tests"] = tests

    # ── 1-3 단조성 (얇은 구간 제외) ──
    print("\n═══ 1-3 · 단조성 — **200건 미만 구간 제외**(M34-O) ═══", flush=True)
    keep = [nm for nm, _, _ in BUCKETS if nm in tab and not tab[nm]["thin"]]
    dropped = [nm for nm, _, _ in BUCKETS if nm in tab and tab[nm]["thin"]]
    seq = [tab[nm]["per_trade"] for nm in keep]
    rev = sum(1 for i in range(len(seq) - 1) if seq[i + 1] < seq[i])
    print("  판단에 쓴 구간 %s · **뺀 구간 %s**(200건 미만)" % (keep, dropped), flush=True)
    print("  순서 %s → **뒤집힘 %d / %d쌍**"
          % ([round(x, 3) for x in seq], rev, max(0, len(seq) - 1)), flush=True)
    print("  ※ 5구간 무작위 배열이면 뒤집힘 ≤2 가 **77.5%%** 확률로 나온다 — 조건 ②는 헐겁다.",
          flush=True)
    res["monotonic"] = {"kept": keep, "dropped_thin": dropped, "seq": seq,
                        "reversals": rev, "n_pairs": max(0, len(seq) - 1)}

    # ── 1-4 leave-one-year: 의존율 ──
    print("\n═══ 1-4 · leave-one-year **의존율**(M34-F·J) — 여섯 해 전부 ═══", flush=True)
    base = tests["rv_1 ≥1.5"]["diff"]
    yr = {}
    for y in YS:
        sub = [r for r in rows if r["year"] != y]
        A = [r["net"] for r in sub if r["rv_1"] >= 1.5]
        B = [r["net"] for r in sub if r["rv_1"] < 1.5]
        v = (st.mean(A) - st.mean(B)) if A and B else None
        dep = (1 - v / base) * 100 if (v is not None and base) else None
        yr[y] = {"n_a": len(A), "diff": v, "dependency_pct": dep}
        print("  %s 제거 → 차이 %+.4f%%p · **의존율 %+.1f%%** (rv_1≥1.5 표본 %d건)"
              % (y, v, dep, len(A)), flush=True)
    half = [y for y in YS if yr[y]["dependency_pct"] is not None
            and yr[y]["dependency_pct"] >= 50]
    print("  → **효과가 절반 이상 사라지는 해: %s**"
          % (", ".join(half) if half else "없음"), flush=True)
    res["leave_one_year"] = yr
    res["half_gone_years"] = half

    # ── 1-5 홀드아웃 2021~2022 ──
    print("\n═══ 1-5 · 홀드아웃 2021~2022 (어느 주장도 안 건드린 구간) ═══", flush=True)
    ho = [r for r in rows if r["year"] in ("2021", "2022")]
    hd = [x for x in dates if x[:4] in ("2021", "2022")]
    ha, hb = defaultdict(list), defaultdict(list)
    for r in ho:
        (ha if r["rv_1"] >= 1.5 else hb)[r["entry_date"]].append(r["net"])
    na = sum(len(v) for v in ha.values())
    nb = sum(len(v) for v in hb.values())
    obs = (st.mean([x for v in ha.values() for x in v])
           - st.mean([x for v in hb.values() for x in v]))
    bs = boot_diff(ha, hb, hd, BOOT_SEED + 9)
    lo, hi = ci(bs)
    print("  n=%d (≥1.5 %d · <1.5 %d) · 차이 **%+.4f%%p** · 95%% **%+.4f ~ %+.4f** · "
          "MDE %.4f · 0 %s"
          % (len(ho), na, nb, obs, lo, hi, MDE_K * st.stdev(bs),
             "제외" if (lo > 0 or hi < 0) else "**포함**"), flush=True)
    res["holdout_2021_2022"] = {"n": len(ho), "n_a": na, "n_b": nb, "diff": obs,
                                "ci": [lo, hi], "MDE": MDE_K * st.stdev(bs),
                                "excludes_zero": bool(lo > 0 or hi < 0)}

    # ── 1-6 최대통계 보정 ──
    print("\n═══ 1-6 · 최대통계 보정 (검정 총수 %d) ═══" % len(tests), flush=True)
    rnd = random.Random(MAX_SEED)
    allnet = [r["net"] for r in rows]
    null_max = []
    for _ in range(N_MAX):
        sh = allnet[:]
        rnd.shuffle(sh)
        mx = 0.0
        for nm, tv in tests.items():
            na_ = tv["n_a"]
            mx = max(mx, abs(st.mean(sh[:na_]) - st.mean(sh[na_:])))
        null_max.append(mx)
    null_max.sort()
    thr = null_max[int(N_MAX * 0.95)]
    print("  귀무 최대통계 95%% 문턱 **%.4f%%p**" % thr, flush=True)
    for nm, tv in tests.items():
        print("   %-16s |차이| %.4f → 보정 후 %s"
              % (nm, abs(tv["diff"]),
                 "**통과**" if abs(tv["diff"]) > thr else "미통과"), flush=True)
        tv["maxstat_pass"] = bool(abs(tv["diff"]) > thr)
    res["maxstat_threshold"] = thr
    res["n_tests"] = len(tests)

    # ── 분봉 보유 건수 (세기만) ──
    print("\n═══ 참고 · 진입일 분봉 보유 건수 (세기만, 분석 안 함) ═══", flush=True)
    have = set()
    if MIN_DAILY.exists():
        for p in MIN_DAILY.iterdir():
            have.add(p.stem)
    cnt = Counter()
    hit = 0
    for r in rows:
        key = r["entry_date"].replace("-", "")
        if any(key in h for h in have) or key in have:
            hit += 1
            cnt[r["year"]] += 1
    print("  `.cache/min_daily` 항목 %d개 · 진입일 분봉이 있는 거래 **%d / %d = %.1f%%**"
          % (len(have), hit, len(rows), hit / len(rows) * 100), flush=True)
    print("  연도별: %s" % dict(sorted(cnt.items())), flush=True)
    res["min_daily"] = {"n_entries": len(have), "n_trades_with_bars": hit,
                        "pct": hit / len(rows) * 100, "by_year": dict(sorted(cnt.items()))}

    (OUT / "19-volume-stage1.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/19-volume-stage1.json")


if __name__ == "__main__":
    main()

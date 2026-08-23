# -*- coding: utf-8 -*-
"""M32-2 — 대조군 추첨이 들어가는 모든 통계를 **여러 스트림을 합쳐** 다시 낸다.

지금 구간은 **추첨 스트림 하나에 조건부**인데 **추첨 자체가 잡음원**이다
(C 의 95% 상한이 스트림에 따라 −0.0045 ↔ +0.0065 를 오갔다).
→ **S = 10 스트림 × 100회**로 바꾸고, 부트스트랩 복제마다 **스트림을 먼저 하나 뽑은 뒤**
날짜 블록을 재추출한다. 그러면 구간에 **날짜 변동 + 추첨 변동**이 함께 들어간다.
**단일 스트림 값도 나란히 실어 대비를 보인다.**
"""
import pathlib

p = pathlib.Path("research/handoff/scripts/16-selection-edge.py")
t = p.read_text(encoding="utf-8")
NL = chr(92) + "n"

t = t.replace("N_REP = 200", "N_REP = 100          # M32-2: 스트림당 반복\nSTREAMS = 10         # M32-2: 추첨 스트림 수 (총 1,000회)")

t = t.replace('''def draw_rng(D, arm):
    """(날짜, 팔)마다 독립 난수 — 팔을 추가해도 기존 팔의 추첨이 안 바뀐다."""
    return random.Random("%d|%s|%s" % (DRAW_SEED, D, arm))''',
'''def draw_rng(D, arm, stream=0):
    """(날짜, 팔, 스트림)마다 독립 난수.

    팔을 추가해도 기존 팔의 추첨이 안 바뀌고, 스트림을 바꾸면 **추첨만** 달라진다.
    """
    return random.Random("%d|%s|%s|%d" % (DRAW_SEED, D, arm, stream))''')

# ── day_stat: 스트림별 dict 를 받아 단일/다중 스트림을 모두 낸다 ──
old = '''def day_stat(pairs, dates_all, tag, seed):
    """하루 짝차이(우리 − 대조)의 평균을 1순위로, 블록 부트스트랩."""
    ds = sorted(pairs)'''
new = '''def day_stat_ms(by_stream, dates_all, tag, seed):
    """M32-2 — 스트림을 합친 구간. 복제마다 스트림을 뽑고 날짜 블록을 재추출한다."""
    streams = sorted(by_stream)
    pooled = {}
    for d in by_stream[streams[0]]:
        v = [by_stream[s][d] for s in streams if d in by_stream[s]]
        if v:
            pooled[d] = st.mean(v)
    ds = sorted(pooled)
    mean, med = st.mean([pooled[d] for d in ds]), st.median([pooled[d] for d in ds])
    n_pos = len(dates_all)
    rnd = random.Random(seed)
    bm, bmd = [], []
    for _ in range(N_BOOT):
        sp = by_stream[streams[rnd.randrange(len(streams))]]
        v = []
        for a, L in make_blocks(rnd, n_pos):
            for j in range(L):
                d = dates_all[a + j]
                if d in sp:
                    v.append(sp[d])
        if v:
            bm.append(st.mean(v))
            bmd.append(st.median(v))
    lo, hi = ci(bm)
    sd = st.stdev(bm)
    # 스트림 간 변동만 따로 — 추첨이 얼마나 잡음원인지 보이기 위해
    per_stream = [st.mean([by_stream[s][d] for d in sorted(by_stream[s])])
                  for s in streams]
    return {"tag": tag, "n_days": len(ds), "mean": mean, "median": med,
            "ci": [lo, hi], "ci_width": hi - lo, "sd": sd, "MDE": MDE_K * sd,
            "median_ci": list(ci(bmd)),
            "per_stream_mean": {"min": min(per_stream), "max": max(per_stream),
                                "sd": st.stdev(per_stream), "n": len(per_stream)},
            "verdict_axis": ("효과 있음(0 제외, 양수)" if (lo > 0) else
                             "효과 있음(0 제외, 음수)" if (hi < 0) else
                             "유지(동등성)" if (-EQUIV <= lo and hi <= EQUIV) else
                             ("판정불가(문턱 사각지대)" if (hi - lo) <= 2 * EQUIV
                              else "판정불가(검정력 부족)"))}


def day_stat(pairs, dates_all, tag, seed):
    """하루 짝차이(우리 − 대조)의 평균을 1순위로, 블록 부트스트랩(단일 스트림)."""
    ds = sorted(pairs)'''
assert t.count(old) == 1
t = t.replace(old, new)

# ── 추첨 루프를 스트림 반복으로 ──
reps = [
    ("""                rp = []
                r0 = draw_rng(D, nm)
                for _ in range(N_REP):
                    pick = (r0.sample(cd, k) if len(cd) >= k
                            else [cd[r0.randrange(len(cd))] for _ in range(k)])
                    rp.append(st.mean([net(get(c, D, b1)["gain"]) for c in pick]))
                lvl[nm][E] = st.mean(rp)""",
     """                for s_ in range(STREAMS):
                    r0 = draw_rng(D, nm, s_)
                    rp = []
                    for _ in range(N_REP):
                        pick = (r0.sample(cd, k) if len(cd) >= k
                                else [cd[r0.randrange(len(cd))] for _ in range(k)])
                        rp.append(st.mean([net(get(c, D, b1)["gain"]) for c in pick]))
                    lvl_s[nm][s_][E] = st.mean(rp)
                lvl[nm][E] = st.mean([lvl_s[nm][s_][E] for s_ in range(STREAMS)])"""),
    ("""            if E in lvl["C:관문통과β1"]:
                day_pairs["C 우리-관문통과"][E] = our_net - lvl["C:관문통과β1"][E]
                if E in lvl["B:관문미통과β1"]:
                    day_pairs["B 관문통과-미통과"][E] = (lvl["C:관문통과β1"][E]
                                                  - lvl["B:관문미통과β1"][E])""",
     """            if E in lvl["C:관문통과β1"]:
                for s_ in range(STREAMS):
                    ps[("C 우리-관문통과", s_)][E] = (our_net
                                                 - lvl_s["C:관문통과β1"][s_][E])
                if E in lvl["B:관문미통과β1"]:
                    for s_ in range(STREAMS):
                        ps[("B 관문통과-미통과", s_)][E] = (
                            lvl_s["C:관문통과β1"][s_][E]
                            - lvl_s["B:관문미통과β1"][s_][E])"""),
    ("""                rp = []
                r0 = draw_rng(D, nm)
                for _ in range(N_REP):
                    vv = []
                    for bd in our_bands:""",
     """                for s_ in range(STREAMS):
                  r0 = draw_rng(D, nm, s_)
                  rp = []
                  for _ in range(N_REP):
                    vv = []
                    for bd in our_bands:"""),
    ("""                    if vv:
                        rp.append(st.mean(vv))
                if rp:
                    day_pairs[nm][E] = our_net - st.mean(rp)""",
     """                    if vv:
                        rp.append(st.mean(vv))
                  if rp:
                    ps[(nm, s_)][E] = our_net - st.mean(rp)"""),
    ("""                reps = []
                r0 = draw_rng(D, ARMN[arm])
                for _ in range(N_REP):
                    pick = (r0.sample(cand, k) if len(cand) >= k
                            else [cand[r0.randrange(len(cand))] for _ in range(k)])
                    vals = []""",
     """                for s_ in range(STREAMS):
                  r0 = draw_rng(D, ARMN[arm], s_)
                  reps = []
                  for _ in range(N_REP):
                    pick = (r0.sample(cand, k) if len(cand) >= k
                            else [cand[r0.randrange(len(cand))] for _ in range(k)])
                    vals = []"""),
    ("""                    if vals:
                        reps.append(st.mean(vals))
                if reps:
                    ctrl = st.mean(reps)
                    day_pairs[ARMN[arm]][E] = our_net - ctrl
                    absol[ARMN[arm]].append(ctrl)""",
     """                    if vals:
                        reps.append(st.mean(vals))
                  if reps:
                    ps[(ARMN[arm], s_)][E] = our_net - st.mean(reps)"""),
]
for a, b in reps:
    assert t.count(a) == 1, a[:70]
    t = t.replace(a, b)

t = t.replace("""    lvl = defaultdict(dict)""",
              """    lvl = defaultdict(dict)
    lvl_s = defaultdict(lambda: defaultdict(dict))   # 팔 -> 스트림 -> 날짜
    ps = defaultdict(dict)                           # (팔, 스트림) -> 날짜 -> 짝차이""")

# ── 출력부: 스트림 합친 값 + 단일 스트림 값 병기 ──
old_a = '''    res["A"] = {}
    for arm in ARMS:
        nm = ARMN[arm]
        if day_pairs[nm]:
            res["A"][nm] = day_stat(day_pairs[nm], dates_all, "A vs " + nm,
                                    BOOT_SEED + BETAS.index(arm[1]) + 1
                                    if arm != "alpha" else BOOT_SEED)'''
new_a = '''    res["A"] = {}

    def report(nm, tag, seed):
        by = {s_: ps[(nm, s_)] for s_ in range(STREAMS) if ps[(nm, s_)]}
        if not by:
            return None
        m = day_stat_ms(by, dates_all, tag, seed)
        one = day_stat(by[0], dates_all, tag + " (단일 스트림)", seed + 7)
        m["single_stream"] = {"mean": one["mean"], "ci": one["ci"],
                              "ci_width": one["ci_width"], "MDE": one["MDE"],
                              "verdict_axis": one["verdict_axis"]}
        m["lenses"] = one["lenses"]
        m["n_lenses"] = one["n_lenses"]
        m["L2p"], m["L3"], m["sign"] = one["L2p"], one["L3"], one["sign"]
        m["L4_top5_removed"] = one["L4_top5_removed"]
        print("  %-22s 날 %4d · 평균 %+7.4f%%p · **다중 95%% %+7.4f ~ %+7.4f** (폭 %6.4f · "
              "MDE %6.4f) · 단일 %+7.4f ~ %+7.4f (폭 %6.4f) · 스트림간 SD %.4f · "
              "렌즈 %d/4 · **%s**"
              % (tag, m["n_days"], m["mean"], m["ci"][0], m["ci"][1], m["ci_width"],
                 m["MDE"], one["ci"][0], one["ci"][1], one["ci_width"],
                 m["per_stream_mean"]["sd"], m["n_lenses"], m["verdict_axis"]),
              flush=True)
        return m

    for arm in ARMS:
        nm = ARMN[arm]
        sd_ = BOOT_SEED + (BETAS.index(arm[1]) + 1 if arm != "alpha" else 0)
        r_ = report(nm, "A vs " + nm, sd_)
        if r_:
            res["A"][nm] = r_'''
assert t.count(old_a) == 1
t = t.replace(old_a, new_a)

old_bc = '''    for i, nm in enumerate(("C 우리-관문통과", "B 관문통과-미통과", "우리종목xβ1",
                           "A ATR맞춤β1", "C ATR맞춤β1")):
        if day_pairs.get(nm):
            res["BC"][nm] = day_stat(day_pairs[nm], dates_all, nm, BOOT_SEED + 50 + i)'''
new_bc = '''    for i, nm in enumerate(("C 우리-관문통과", "B 관문통과-미통과",
                           "A ATR맞춤β1", "C ATR맞춤β1")):
        r_ = report(nm, nm, BOOT_SEED + 50 + i)
        if r_:
            res["BC"][nm] = r_
    if day_pairs.get("우리종목xβ1"):
        res["BC"]["우리종목xβ1(룩어헤드·무효)"] = day_stat(
            day_pairs["우리종목xβ1"], dates_all, "우리종목xβ1(룩어헤드·무효)",
            BOOT_SEED + 60)'''
assert t.count(old_bc) == 1
t = t.replace(old_bc, new_bc)

t = t.replace('''        ab = res["A"].get("β1일고가", {}).get("mean")''',
              '''        ab = res["A"].get("β1일고가", {}).get("mean")''')
t = t.replace('''                    "day_pairs": {k: v for k, v in day_pairs.items()},''',
              '''                    "day_pairs": {k: v for k, v in day_pairs.items()},''')
p.write_text(t, encoding="utf-8")
print("patched")

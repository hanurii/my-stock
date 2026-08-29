# -*- coding: utf-8 -*-
"""107 — **91 의 「등록된 미결」을 닫는다: ①→② 증분이 «등급이라서»인가** (⑤번)

91 사전등록 **개정 3**(값 보기 «전»에 확정해 둔 설계)을 **그대로** 쓴다. 다시 고민하지 않는다.

# 설계 (91 개정 3 원문)
```
형태 = 「각 (섹터, 달) 안에서 순위 밴드 [0.10, 0.30) 을 남긴다」   ← **그대로 둔다**
내용 = 「그 순위가 «6개월 수익률»이다」                            ← **이것만 없앤다**
→ sec_top(①)은 «원래 값으로 확정»한 뒤, **섹터 «안»에서만** 값을 섞는다
⛔ 기각된 후보: 티커 해시(구성원이 고정됨) · scan_date 해시(국면이 통째로 들고나 «새 실험»이 됨)
K = **200 고정** (순열 p 바닥 1/(K+1) ≤ 0.0056 을 넘으려면 K ≥ 178)
계산이 벅차면 **seed 를 줄이고 K 를 지킨다.** 거칠어졌으면 «거칠어졌다»고 적는다
```

# 🚨 값 보기 «전»에 등록된 양쪽 예상 (91 개정 3 그대로)
```
가짜약이 **50% 근처**  → 등급의 «내용»이 산다. 「①<② 는 등급 때문이다」를 쓸 수 있다
가짜약이 **90% 근처**  → **형태(덜어내기) 자체가 값을 낸다.** 「등급이라서」는 죽는다
                        🚨 그건 나쁜 소식이 아니라 «발견»이다
```
# 🚨 어느 쪽이 나와도 같이 적을 한 줄 (91 개정 3 그대로)
> ② 는 가짜약을 이겨도 SPY 에 진다(+3.16 vs +7.04).
> 「어느 칸이 나은가」와 「쓸 만한가」는 다른 물음이고, 가짜약은 «앞엣것만» 답한다.

🚨 **`61b` 를 «고치지 않는다»** — 43·47·48·61 이 쓴다. 변형을 이 파일에 «따로» 둔다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
r61 = r91.r61
r61b = r91.r61b

D0, D1 = "2002-01-01", "2017-08-31"        # 91 표본 밖 A — 판정이 걸린 창
YEARS = tuple(range(2002, 2018))
K = 200                                     # 91 개정 3 이 «고정»한 값
N_SEED = 40                                 # 🚨 벅차서 줄였다. K 를 지킨다(개정 3 §판수)


def flags_shuffled(mret, sector, rnd):
    """★ 91 개정 3 의 변형 — **sec_top 을 원래 값으로 확정한 뒤 «섹터 안»에서만 섞는다.**

    `61b.make_flags(shuffle_rnd=)` 는 «달 전체»에서 섞어 sec_top 까지 무너뜨린다
    → ①→② 증분을 격리 못 한다. 그래서 여기 따로 둔다. **61b 는 안 고친다.**
    """
    sec_top, in_pct = {}, {}
    for ym, v in mret.items():
        bysec = defaultdict(list)
        for t, r in v:
            bysec[sector[t]].append((r, t))
        # ① sec_top — **원래 값 그대로** (섞기 «전»에 정한다)
        smean = {s: st.mean(x for x, _ in lst) for s, lst in bysec.items() if len(lst) >= 5}
        sec_top[ym] = set(sorted(smean, key=lambda s: -smean[s])[:r61.TOP_SECTORS])
        # ② 밴드 — 섹터 «안»에서만 값을 섞는다 (형태는 그대로, 내용만 사라진다)
        pct = {}
        for s, lst in bysec.items():
            vals = [x for x, _ in lst]
            rnd.shuffle(vals)
            lst2 = [(vals[i], t) for i, (_r, t) in enumerate(lst)]
            lst2.sort(key=lambda x: -x[0])
            n = len(lst2)
            for i, (_r, t) in enumerate(lst2):
                pct[t] = i / n
        in_pct[ym] = pct
    return sec_top, in_pct


def main() -> int:
    quick = "--quick" in sys.argv
    k, n_seed = (8, 8) if quick else (K, N_SEED)
    print("=" * 106, flush=True)
    print("107 — ①→② 증분이 «등급이라서»인가 · 91 개정 3 설계 그대로 · 순열 %d판 · 운의번호 %d판"
          % (k, n_seed), flush=True)
    print("=" * 106, flush=True)
    print("🚨 값 보기 «전»에 등록된 예상: 가짜 50%% 근처 → 「등급 때문」이 산다 ·"
          " 90%% 근처 → **형태 자체가 값을 낸다**\n", flush=True)

    pack = json.loads((r91.OUT / "91-monthly-us-full.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    lo_ym = r61.prev_ym(D0[:7], 8)
    months = sorted({m for d in monthly.values() for m in d if m >= lo_ym})
    mret = r61b.month_returns(monthly, sector, months)

    # ── 원래 값 ──────────────────────────────────────────────────────
    (by0, by1, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2

    def eq_of(by):
        ev, _x, _y = r91.replay(by)
        return len(ev), [x["equity_pct"] for x in r91.sim(ev, n_seed)]

    n1, e1 = eq_of(by1)
    n2, e2 = eq_of(by2)
    real_gap = st.median(e2) - st.median(e1)
    print("원래  ① 주도업종 매수 %s · 자산중앙 %+.2f%%" % ("{:,}".format(n1), st.median(e1)),
          flush=True)
    print("      ② 조합       매수 %s · 자산중앙 %+.2f%%" % ("{:,}".format(n2), st.median(e2)),
          flush=True)
    print("      **①→② 증분 = %+.2f%%p**\n" % real_gap, flush=True)

    # ── 관문 — 가짜약이 ① 을 «안 건드리는가» ─────────────────────────
    rnd0 = random.Random(0)
    st0, _ip0 = flags_shuffled(mret, sector, rnd0)
    st_real, _ipr = r61b.make_flags(mret, sector)
    same_top = all(st0.get(m) == st_real.get(m) for m in st_real)
    print("관문 ㉗ 가짜약이 ①(주도 섹터)을 «안 건드리는가» → **%s**"
          % ("통과" if same_top else "🚨 미통과 — 멈춘다"), flush=True)
    if not same_top:
        return 3

    # ── 순열 K 판 ────────────────────────────────────────────────────
    print("\n순열 %d 판 — 섹터 «안»에서만 등급값을 섞는다 (형태는 그대로)" % k, flush=True)
    gaps, n_ent = [], []
    for i in range(k):
        rnd = random.Random(9000 + i)
        s_top, s_pct = flags_shuffled(mret, sector, rnd)
        byF = {}
        for y in sorted(by0):
            byF[y] = [p for p in by0[y]
                      if (sector.get(p["code"]) in s_top.get(p["scan_date"][:7], set()))
                      and (0.10 <= s_pct.get(p["scan_date"][:7], {}).get(p["code"], 9.9) < 0.30)]
        nF, eF = eq_of(byF)
        gaps.append(st.median(eF) - st.median(e1))
        n_ent.append(nF)
        if (i + 1) % max(1, k // 10) == 0:
            print("   %3d/%d …" % (i + 1, k), flush=True)

    # ── 🚨 발견 후 «추가»한 팔 — 개수를 «맞춘» 가짜약 ─────────────────
    #    등록판(섹터 안 섞기)은 «티커» 개수는 맞지만 **«후보(경로)» 개수가 안 맞는다**
    #    (실측 2,573 vs 원래 4,734). 우리 후보는 상위 순위에 몰려 있어서다.
    #    → 그러면 「내용만 없앤 것」이 아니라 **「덜 산 것」**이 섞인다.
    #    → **(섹터, 달)마다 원래 ② 가 남긴 «후보 수»와 «같은 수»를 무작위로** 남기는 팔을 더 둔다.
    #    🚨 이건 «등록 후»에 붙인 것이다. 그렇게 적는다.
    keepcnt = defaultdict(int)
    for y in sorted(by2):
        for q in by2[y]:
            keepcnt[(sector.get(q["code"]), q["scan_date"][:7])] += 1
    print("", flush=True)
    print("개수를 «맞춘» 가짜약 %d 판 — (섹터, 달)마다 원래 ② 와 «같은 수»를 무작위로" % k,
          flush=True)
    gaps2, n2f = [], []
    for i in range(k):
        rnd = random.Random(31000 + i)
        pool = defaultdict(list)
        for y in sorted(by0):
            for q in by0[y]:
                pool[(sector.get(q["code"]), q["scan_date"][:7])].append((y, q))
        byM = {}
        for key, lst in pool.items():
            want = keepcnt.get(key, 0)
            if want <= 0:
                continue
            rnd.shuffle(lst)
            for y, q in lst[:want]:
                byM.setdefault(y, []).append(q)
        nM, eM = eq_of(byM)
        gaps2.append(st.median(eM) - st.median(e1))
        n2f.append(nM)
        if (i + 1) % max(1, k // 5) == 0:
            print("   %3d/%d …" % (i + 1, k), flush=True)
    g2 = sorted(gaps2)
    beat2 = sum(1 for g in gaps2 if g < real_gap)
    pct2 = 100.0 * beat2 / k

    gs = sorted(gaps)
    beat = sum(1 for g in gaps if g < real_gap)
    pct = 100.0 * beat / k
    p_perm = (k - beat + 1) / (k + 1)
    print("\n" + "=" * 106, flush=True)
    print("  가짜약 매수 수 — 중앙 %s (원래 ② 는 %s)"
          % ("{:,}".format(int(st.median(n_ent))), "{:,}".format(n2)), flush=True)
    print("  가짜약 증분 — 중앙 %+.2f%%p · 하위25%% %+.2f · 상위25%% %+.2f · 최대 %+.2f"
          % (st.median(gs), gs[k // 4], gs[3 * k // 4], gs[-1]), flush=True)
    print("  **원래 ② 의 증분 %+.2f%%p 가 가짜약 %d 판 중 «상위 %.1f%%»**"
          % (real_gap, k, 100.0 - pct), flush=True)
    print("  순열 p = %.4f  (바닥 %.4f · 본페로니 문턱 0.0056)" % (p_perm, 1.0 / (k + 1)),
          flush=True)
    print("\n  → 등록된 읽는 법: **가짜약이 %.0f%% 근처**" % pct, flush=True)
    if pct >= 80:
        print("     → **형태(덜어내기) 자체가 값을 낸다. 「등급이라서」는 죽는다**", flush=True)
    elif pct <= 60:
        print("     → **등급의 «내용»이 산다. 「①<② 는 등급 때문이다」를 쓸 수 있다**", flush=True)
    else:
        print("     → **가운데다. 어느 쪽도 못 쓴다**", flush=True)
    print("\n  🚨 어느 쪽이 나와도 같이 적는다(91 개정 3):", flush=True)
    print("     **② 는 가짜약을 이겨도 SPY 에 진다(+3.16 vs +7.04).**", flush=True)
    print("     「어느 칸이 나은가」와 「쓸 만한가」는 다른 물음이고 가짜약은 «앞엣것만» 답한다.",
          flush=True)
    if n_seed < 200:
        print("\n  ⚠️ 운의 번호를 %d 판으로 «줄였다»(K 를 지키려고). 승률이 «거칠다»." % n_seed,
              flush=True)

    (r91.OUT / "107-grade-placebo.json").write_text(
        json.dumps({"real_gap": real_gap, "gaps": gaps, "pct": pct, "p_perm": p_perm,
                    "n1": n1, "n2": n2, "n_fake_med": st.median(n_ent),
                    "gaps_matched": gaps2, "pct_matched": pct2,
                    "n_matched_med": st.median(n2f),
                    "K": k, "n_seed": n_seed}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print("\n저장: 107-grade-placebo.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

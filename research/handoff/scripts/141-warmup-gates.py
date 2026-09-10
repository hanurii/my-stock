# -*- coding: utf-8 -*-
r"""141 — **웜업 재빌드 관문 넷.** 자료만 검사한다. 특징·체·성적은 «없다».

두뇌 세션 확정(2026-08-31):
```
㉠′ 옛 경로 vs 새 경로 — 공유 키가 **완전히** 같은가   ← 실패할 수 «있는» 관문
㉡′ pre_d[-1] == scan_date                            ← 「< d[0]」보다 한 칸 조인 판
㉢  len(pre_*) == 250 · 못 채운 건은 **연도별 분포**까지
㉣  키 구성이 약속대로인가 (pre_* 여섯 + v)
```
🚨 ㉠′ 가 이 작업의 전부다. **한 자리라도 다르면 되돌리고 «왜인지»부터.**

실행:
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/141-warmup-gates.py \
      --old .cache/bt5y/sub --new D:/stock-data/uspath-warm
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SHARED = ("code", "pattern", "scan_date", "entry_date",
          "pivot", "entry_price", "atr_band", "d", "o", "h", "l", "c")
NEWKEYS = ("pre_d", "pre_o", "pre_h", "pre_l", "pre_c", "pre_v", "pre_n", "v")
SNAPSHOT = "2026-09-01 재빌드 · 시세 ~2026-08-26 · 원천 Sharadar 2026-08-27 내려받음"

# 🚨 **회귀 기준선**이지 «가설 문턱»이 아니다 — 2026-09-01 에 «실측한» 값을 그대로 박는다.
#    「예외로 봐준다」가 아니라 **「분할 N건 · 자람 M건 · 그 밖 0건」**을 못박는 것이라,
#    23번째 분할이 생기면 **잡힌다**. 값을 고칠 때는 «왜 달라졌는지»를 먼저 적을 것.
#    (분할, 자람, 그 밖, 옛쪽만, 새쪽만)
# (일치, 자람, 재조정, 자람+재조정, 꼬리수정, 그 밖, 옛쪽만, 새쪽만)
A_EXPECT = (140400, 4805, 22, 2, 53, 0, 5, 19)
DEPTH_EXPECT = {0: 142653, 1: 901, 2: 4, 3: 8, 4: 18, 5: 1692, 250: 6}
# ㉦㉧ — 자료 갱신으로 «후보 수»가 달라진 해도 건수를 못박는다 {연도: (옛, 새)}
COUNT_EXPECT = {2021: (5542, 5541), 2023: (4795, 4796), 2026: (3202, 3216)}
# ㉤ — 원본 시계열의 «불연속». 전 연도 통틀어 **1건**(2005 HYDGQ, 거래정지 뒤 재개로 보임).
#     「전형」이 아니라 **「단독」**이다. 두 번째가 생기면 여기서 잡힌다.
SEAM_EXPECT = 1
# ㉦ — 배열 «순서»가 달라진 해. 후보 수가 달라진 해와 같아야 한다.
ORDER_EXPECT = {2021, 2023, 2026}

W = 400          # 🚨 250 아님 — 「베이스 65주(325봉)」는 «확인»된 원전에서 «못» 찾았다.
                 #    「200일선 4~5개월 상승(294봉)」은 trend_template.md:5 로 «있다».


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))["trigger_paths"]


def key(r):
    return (r["scan_date"], r["code"], r["pattern"])


PRICE = ("o", "h", "l", "c")
SCALAR = ("code", "pattern", "scan_date", "entry_date", "atr_band")


def _prefix(a, b):
    """a 가 b 의 «앞부분»인가."""
    return len(a) <= len(b) and list(b[:len(a)]) == list(a)


def classify(o, r):
    """짝 하나를 두 «축»으로 가른다 → (갈래, 사유, 꼬리수정 깊이)

    🚨 **문턱을 두지 않는다.** 「몇 봉까지는 봐준다」가 아니라
       **«깊이 분포를 통째로 고정»**한다 → 한 봉이라도 달라지면 잡힌다.

    축 둘 (직교한다)
    ```
    자람     옛 날짜가 새 날짜의 «앞부분»이고 새 쪽이 더 길다
    재조정   pivot·entry_price 가 «한 배수»로 어긋난다 (분할 소급 반영)
    ```
    그리고 **꼬리 수정 깊이** — 옛 스냅숏의 «마지막 몇 봉»이 사후에 고쳐져 있다.
    실측(2026-09-01): 0봉·1봉·5봉에 몰림. 수정 시작일이 **8/17·8/21** 에 몰린다
    = 옛 스냅숏의 «마지막 주»가 잠정치였다는 뜻.

    「그 밖」은 **구조가 깨진 것만** — 스칼라 불일치 · 날짜가 앞부분이 아님 · 배열 길이 모순.
    """
    for f in SCALAR:
        if o.get(f) != r.get(f):
            return "그 밖", "scalar:%s" % f, None
    if all(o.get(f) == r.get(f) for f in SHARED):
        return "일치", "", 0
    if not _prefix(o["d"], r["d"]):
        return "그 밖", "날짜가 앞부분이 아니다", None

    # 재조정 배수 — 진입 기준가에서 뽑는다 (경로 전체에 같은 배수가 걸린다)
    rr = 1.0
    if o.get("entry_price") and r.get("entry_price"):
        rr = o["entry_price"] / r["entry_price"]
    elif o.get("pivot") and r.get("pivot"):
        rr = o["pivot"] / r["pivot"]
    rescaled = abs(rr - 1.0) > 1e-6

    n = len(o["d"])
    depth = 0
    for f in PRICE:
        if len(r[f]) < n:
            return "그 밖", "가격 배열이 날짜보다 짧다", None
        for i in range(n):
            x, yv = o[f][i], r[f][i]
            if x is None or yv is None:
                if x != yv:
                    depth = max(depth, n - i)
                continue
            # 4자리 반올림 둘 → 절대 1e-4, 큰 값에선 상대 1e-4 (자료 정밀도에서 끌어온 값)
            tol = max(1e-4, 1e-4 * abs(x))
            if abs(x - rr * yv) > tol:
                depth = max(depth, n - i)
                break
    grew = len(r["d"]) > n
    lab = ("자람+재조정" if (grew and rescaled) else
           "자람" if grew else "재조정" if rescaled else "꼬리수정")
    return lab, "", depth


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default=".cache/bt5y/sub")
    ap.add_argument("--new", required=True)
    ap.add_argument("--years", default="1999-2026")
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    years = range(y0, y1 + 1)

    n_pair = n_only_old = n_only_new = 0
    a_bad = Counter()
    a_cls = Counter()
    a_depth = Counter()
    a_ex = []
    b_bad, b_ex = 0, []
    c_short, c_short_by_year, c_len = 0, Counter(), Counter()
    d_bad, d_ex = 0, []
    e_seam, e_vol, e_ex, e_seam_year = 0, 0, [], Counter()
    g_order, g_ex, g_years = 0, [], set()
    h_cnt, h_ex = 0, []
    i_cmp, i_bad, i_tot, i_ex = [0], [0], [0], []
    n_new_tot = 0

    for y in years:
        fo, fn = Path(a.old) / ("uspath_%d.json" % y), Path(a.new) / ("uspath_%d.json" % y)
        if not fn.exists():
            print("   %d년 — 새 파일 없음, 건너뜀" % y, flush=True)
            continue
        if not fo.exists():
            print("🚨 %d년 — 옛 파일이 없어 ㉠′ 를 못 건다" % y, flush=True)
            return 2
        old = {key(r): r for r in load(fo)}
        new = load(fn)
        n_new_tot += len(new)
        seen = set()
        for r in new:
            k = key(r)
            seen.add(k)
            o = old.get(k)
            if o is None:
                n_only_new += 1
                continue
            n_pair += 1
            # ── ㉠′ 공유 키 — «완전 일치» 또는 «알려진 두 모양»인가 ──────
            cls, why, dep = classify(o, r)
            a_cls[cls] += 1
            if dep is not None:
                a_depth[dep] += 1
            if cls == "그 밖":
                a_bad[why] += 1
                if len(a_ex) < 6:
                    a_ex.append((y, k, why))
            # ── ㉡′ pre_d[-1] == scan_date ──────────────────────────────
            pd = r.get("pre_d") or []
            if not pd or pd[-1] != r["scan_date"]:
                b_bad += 1
                if len(b_ex) < 5:
                    b_ex.append((k, pd[-1] if pd else None))
            # ── ㉢ 길이 ────────────────────────────────────────────────
            c_len[len(pd)] += 1
            if len(pd) < W:
                c_short += 1
                c_short_by_year[y] += 1
            # ── ㉣ 키 구성 ─────────────────────────────────────────────
            miss = [f for f in NEWKEYS if f not in r]
            if miss:
                d_bad += 1
                if len(d_ex) < 5:
                    d_ex.append((k, miss))
            else:
                n = len(pd)
                if not all(len(r[f]) == n for f in ("pre_o", "pre_h", "pre_l", "pre_c", "pre_v")):
                    d_bad += 1
                    if len(d_ex) < 5:
                        d_ex.append((k, "pre_* 길이 불일치"))
                elif len(r["v"]) != len(r["d"]):
                    d_bad += 1
                    if len(d_ex) < 5:
                        d_ex.append((k, "v 길이 != d 길이"))
            # ── ㉤ **원본 시계열의 «불연속»** 검사 ────────────────────────
            #    🚨 **이름을 고쳤다(2026-08-31).** 원래 「pre_* 와 path 의 기준가 이음매」라
            #    붙였는데 **둘은 같은 배열의 «슬라이스»라 이음매가 애초에 생길 수 없다** —
            #    그 목적으로는 «아무것도 안 하는 코드»였다. 실제로 재는 것은
            #    **원천 자료 자체의 불연속**(분할조정 사고 · 거래정지 뒤 재개 급등)이고 그건 남는다.
            #    🚨 이 관문에는 **돌연변이를 안 걸었다** — 분해능이 증명되지 않았다.
            pc, po_, ph_ = r.get("pre_c") or [], r.get("pre_o") or [], r.get("pre_h") or []
            pl_ = r.get("pre_l") or []
            if pc:
                # 진입 «전날» 봉의 고·저·종이 서로 모순 없는가 (같은 기준가에서 온 값인가)
                if not (pl_ and ph_ and pl_[-1] is not None and ph_[-1] is not None
                        and pc[-1] is not None and pl_[-1] <= pc[-1] <= ph_[-1]):
                    e_seam += 1
                    e_seam_year[y] += 1
                    if len(e_ex) < 5:
                        e_ex.append((k, "pre 고/저/종 모순"))
                else:
                    # 진입가와의 «자릿수» 검산 — 이음매가 어긋나면 배수로 튄다
                    ratio = (r["entry_price"] / pc[-1]) if pc[-1] else None
                    if ratio is not None and not (0.2 <= ratio <= 5.0):
                        e_seam += 1
                        if len(e_ex) < 5:
                            e_ex.append((k, "진입가/직전종가 = %.4f" % ratio))
                        e_seam_year[y] += 1
            pv_ = r.get("pre_v") or []
            if pv_ and any(x is not None and x < 0 for x in pv_):
                e_vol += 1
                if len(e_ex) < 5:
                    e_ex.append((k, "pre_v 에 음수"))
        # ── ㉨ `pre_*` 의 «값» 대조 ─────────────────────────────────
        #    🚨 141e 돌연변이 ②(pre_c[-1] × 1.0001)를 관문 여덟이 «못 잡았다».
        #    pre_* 는 옛 파일에 «없어서» ㉠′ 에서 빠지고 나머지는 날짜·길이만 본다
        #    = **이 재빌드의 존재 이유가 무검증이었다.**
        #
        #    같은 (종목, 날짜)가 여러 경로에 나타난다:
        #      · 어떤 경로의 «진입 후» 배열(㉠′ 로 이미 증명됨)
        #      · 다른 경로의 «진입 전» 창
        #    → **한 번이라도 겹치면 대조한다.** 겹칠 상대가 없는 봉은 «못 본다» —
        #      그래서 **덮는 비율을 «같이» 찍는다**(안 찍으면 「통과」가 무슨 뜻인지 모른다).
        obs = {}
        for x in new:                       # ① 이미 증명된 «진입 후» 값을 먼저 깐다
            cd = x["code"]
            for i, day in enumerate(x["d"]):
                obs.setdefault((cd, day), (x["o"][i], x["h"][i], x["l"][i], x["c"][i]))
        for x in new:                       # ② pre_* 를 대조하고, 없으면 새로 등록해 서로 대조되게
            cd = x["code"]
            pdd = x.get("pre_d") or []
            for i, day in enumerate(pdd):
                i_tot[0] += 1
                val = (x["pre_o"][i], x["pre_h"][i], x["pre_l"][i], x["pre_c"][i])
                k2 = (cd, day)
                if k2 in obs:
                    i_cmp[0] += 1
                    if obs[k2] != val:
                        i_bad[0] += 1
                        if len(i_ex) < 5:
                            i_ex.append((y, cd, day))
                else:
                    obs[k2] = val
        del obs

        n_only_old += sum(1 for k in old if k not in seen)
        # ── ㉦ 배열 «순서» — 옛 파일과 새 파일의 «등장 순서»가 같은가 ─────────
        #    🚨 전례: scorecard-fills.json 은 배열 «순서»가 자료였고 재정렬로 63→43 붕괴.
        #    직접 대조는 키로 «찾아» 보므로 순서를 안 본다. 여기서 따로 센다.
        ko = [key(r) for r in load(fo)]
        kn = [key(r) for r in new]
        if ko != kn:
            g_order += 1
            g_years.add(y)
            if len(g_ex) < 3:
                first = next((i for i, (a_, b_) in enumerate(zip(ko, kn)) if a_ != b_), None)
                g_ex.append((y, "길이 %d vs %d · 첫 어긋남 %s" % (len(ko), len(kn), first)))
        # ── ㉧ 연도별 후보 «수» 가 같은가 ────────────────────────────────
        if len(ko) != len(kn):
            h_cnt += 1
            h_ex.append((y, len(ko), len(kn)))
        print("   %d년 — 짝 %d · 새쪽만 %d · 옛쪽만 %d · 순서 %s · 수 %d→%d"
              % (y, len(seen & set(old)), len(seen - set(old)),
                 len(set(old) - seen), "같음" if ko == kn else "**다름**",
                 len(ko), len(kn)), flush=True)

    print("", flush=True)
    print("=" * 92, flush=True)
    print("관문 아홉 — 새 경로 %s건 · 짝지은 것 %s건"
          % ("{:,}".format(n_new_tot), "{:,}".format(n_pair)), flush=True)
    print("=" * 92, flush=True)

    ok = True
    CL = ("일치", "자람", "재조정", "자람+재조정", "꼬리수정", "그 밖")
    got = tuple(a_cls[c] for c in CL) + (n_only_old, n_only_new)
    pass_a = (got == A_EXPECT)
    ok &= pass_a
    print("㉠′ 공유 키 — %s · 옛쪽만 %d · 새쪽만 %d"
          % (" · ".join("%s %d" % (c, a_cls[c]) for c in CL), n_only_old, n_only_new),
          flush=True)
    print("    기대(회귀 기준선) — %s · 옛쪽만 %d · 새쪽만 %d"
          % (" · ".join("%s %d" % (c, v) for c, v in zip(CL, A_EXPECT[:6])),
             A_EXPECT[6], A_EXPECT[7]), flush=True)
    dep_ok = (dict(a_depth) == DEPTH_EXPECT)
    ok &= dep_ok
    print("    꼬리수정 깊이 분포 %s  (기대 %s) → %s"
          % (dict(sorted(a_depth.items())), DEPTH_EXPECT,
             "**통과**" if dep_ok else "🚨 **달라짐**"), flush=True)
    print("    자료 스냅숏: %s" % SNAPSHOT, flush=True)
    print("    자람의 «꼬리 수정 깊이» 분포(봉): %s"
          % (sorted(a_depth.items())[:10],), flush=True)
    print("    → %s" % ("**통과**" if pass_a
                        else "🚨 **미통과 — 건수가 «달라졌다». 맞추지 말고 «왜인지»부터**"),
          flush=True)
    if a_bad:
        print("    「그 밖」 사유별: %s" % dict(a_bad), flush=True)
        print("    예: %s" % (a_ex[:3],), flush=True)

    ok &= (b_bad == 0)
    print("㉡′ pre_d[-1] == scan_date — 어긋난 건 **%d** → %s"
          % (b_bad, "**통과**" if b_bad == 0 else "🚨 **미통과**"), flush=True)
    if b_ex:
        print("    예: %s" % (b_ex[:3],), flush=True)

    print("㉢ 웜업 길이 — %d봉 미만 **%d건** (%.2f%%)"
          % (W, c_short, 100 * c_short / max(1, n_pair)), flush=True)
    if c_short_by_year:
        print("    🚨 **연도별 분포** (다음 판의 표본을 정한다):", flush=True)
        for y in sorted(c_short_by_year):
            print("       %d  %5d건 / 그해 짝 대비" % (y, c_short_by_year[y]), flush=True)
    sml = sorted(c_len.items())[:5]
    print("    가장 짧은 쪽 길이 분포: %s" % (sml,), flush=True)
    print("    (㉢ 은 «세기»만 한다 — 빼나·짧은 채 두나·결측 처리하나는 «다음 판 사전등록»)",
          flush=True)

    ok &= (d_bad == 0)
    print("㉣ 키 구성(pre_* 여섯 + v · 길이 정합) — 어긋난 건 **%d** → %s"
          % (d_bad, "**통과**" if d_bad == 0 else "🚨 **미통과**"), flush=True)
    if d_ex:
        print("    예: %s" % (d_ex[:3],), flush=True)

    ok &= (e_seam == SEAM_EXPECT and e_vol == 0)
    print("ㅤ", flush=True)
    print("ㅥ **원본 시계열의 «불연속»** (이음매 아님) — 고저종 모순/자릿수 이상 **%d** · pre_v 음수 **%d** (기대 %d · 0) → %s"
          % (e_seam, e_vol, SEAM_EXPECT,
             "**통과 — 「단독」 그대로**" if (e_seam == SEAM_EXPECT and e_vol == 0)
             else "🚨 **달라짐 — «왜인지»부터**"), flush=True)
    if e_ex:
        print("    예: %s" % (e_ex[:3],), flush=True)
    if e_seam_year:
        print("    연도별: %s" % (dict(e_seam_year),), flush=True)

    ord_ok = (g_years == ORDER_EXPECT)
    ok &= ord_ok
    print("ㅦ 배열 «순서» — 어긋난 해 %s (기대 %s) → %s"
          % (sorted(g_years) or "없음", sorted(ORDER_EXPECT),
             "**통과**" if ord_ok else "🚨 **달라짐 — 순서도 자료다**"), flush=True)
    if g_ex:
        print("    예: %s" % (g_ex[:3],), flush=True)

    got_cnt = {y: (a_, b_) for y, a_, b_ in h_ex}
    cnt_ok = (got_cnt == COUNT_EXPECT)
    ok &= cnt_ok
    print("ㅧ 연도별 후보 «수» — 달라진 해 %s" % (got_cnt or "없음",), flush=True)
    print("    기대(회귀 기준선) %s → %s"
          % (COUNT_EXPECT, "**통과**" if cnt_ok else "🚨 **달라짐 — «왜인지»부터**"), flush=True)

    cov = 100.0 * i_cmp[0] / max(1, i_tot[0])
    i_ok = (i_bad[0] == 0 and i_cmp[0] > 0)
    ok &= i_ok
    print("ㅨ `pre_*` 값 대조 — pre 봉 %s개 중 **%s개(%.1f%%)**를 겹쳐서 대조 · 어긋남 **%d** → %s"
          % ("{:,}".format(i_tot[0]), "{:,}".format(i_cmp[0]), cov, i_bad[0],
             "**통과**" if i_ok else
             ("🚨 **비교 쌍이 0 — 아무것도 안 하는 관문**" if i_cmp[0] == 0
              else "🚨 **미통과 — pre_* 가 다른 경로와 안 맞는다**")), flush=True)
    print("    🚨 **덮지 못한 %.1f%%** 는 겹칠 상대가 없는 봉이다 — "
          "«한 봉만» 망가진 경우는 못 잡을 수 있다(체계적 오류는 잡는다)" % (100.0 - cov),
          flush=True)
    if i_ex:
        print("    예: %s" % (i_ex[:3],), flush=True)

    print("", flush=True)
    print("→ %s" % ("**아홉 다 통과.** 덧붙이기가 성공했다." if ok
                    else "🚨 **미통과가 있다. 재빌드 산출을 쓰지 말 것.**"), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

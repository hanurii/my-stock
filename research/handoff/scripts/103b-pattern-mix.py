# -*- coding: utf-8 -*-
"""103b — **「실적 자료가 없는 회사」가 혹시 파워플레이인가.** 사용자 가설(2026-08-29):

> 「자료 없으면 그냥 산다에서 좋았던 이유가 혹시 **파워플레이 대상 종목**이라서 그런 건가요?
>  파워플레이 패턴 만족 시 **펀더멘탈을 보지 않는다**고 미너비니가 한 걸로 기억합니다.」

103 에서 갈림이 「조건의 세기」가 아니라 **「실적 자료가 «없는» 회사를 버리느냐」**에 있었다.
사용자 가설이 맞다면 **그 「자료 없는 무리」에 파워플레이가 몰려 있어야** 한다.

# 이 판이 가르는 것 — **셋**
```
㉮ 자료 없는 무리에 파워플레이가 «몰려 있나»       패턴 분포를 양쪽에서 센다
㉯ 파워플레이가 «실제로 더 좋나»                   패턴별 매매 한 번당 성적
㉰ 자료 없는 무리가 좋은 게 «파워플레이 때문인가»   같은 패턴 «안»에서 자료 유무를 비교
                                                  ← ㉰ 가 없으면 ㉮·㉯ 는 두 사실일 뿐이다
```
🚨 **기전 진단이다. 문턱을 안 건다.** 후보 수준(칸 배정 «전»)에서 잰다.
🚨 원전 쪽(「파워플레이엔 펀더멘털을 안 본다」가 본인 말인가)은 **조사 세션이 따로 확인 중**이다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                          # noqa: E402

_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_s)
_s.loader.exec_module(r102)
r91, f92a = r102.r91, r102.f92a

_s3 = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_s3)
_s3.loader.exec_module(r103)
NQ_WIN, NITEM_WIN = 1, 2          # 103 의 «최선 칸» — 1분기 · 이익매출
_ord = r102._ord


def ret_of(p):
    t = pt.resolve_trade(p, ft="limit", fs="market", stop=r91.STOP,
                         target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
    m = t["masks"][()]
    epx = t["entry_px"]
    if not epx or not m["exits"]:
        return None
    w = sum(x[1] for x in m["exits"]) or 1.0
    return (sum(x[1] * x[2] for x in m["exits"]) / w / epx - 1.0) * 100.0


def ci(a, b, n=2000, seed=0):
    """두 무리의 «평균 차이» 구간. a − b."""
    if not a or not b:
        return (float("nan"),) * 3
    r = random.Random(seed)
    ds = sorted(sum(r.choice(a) for _ in range(len(a))) / len(a)
                - sum(r.choice(b) for _ in range(len(b))) / len(b) for _ in range(n))
    return (st.mean(a) - st.mean(b), ds[int(n * .025)], ds[int(n * .975)])


def main() -> int:
    print("=" * 104, flush=True)
    print("103b — 「실적 자료가 없는 회사」가 혹시 파워플레이인가 · **기전 진단 · 문턱 없음**",
          flush=True)
    print("=" * 104, flush=True)
    print("사용자 가설: 「자료 없으면 그냥 산다」가 좋았던 건 그 무리가 파워플레이라서 아닌가\n",
          flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        r102.YEARS, r102.D0, r102.D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2
    fund, ixf = f92a.load()

    # ── 후보마다 «자료 있나/없나» + 패턴 + 성적 ────────────────────────
    ix = {f: i for i, f in enumerate(ixf)}
    assert ixf[0] == "date" and ix["eps"] == 3, ixf
    rows = []
    for y in sorted(by2):
        for p in by2[y]:
            rec = fund.get(p["code"])
            arq = (rec or {}).get("ARQ") or []
            r = f92a.asof(arq, p["entry_date"]) if arq else None
            if r is None or _ord(p["entry_date"]) - _ord(r[0]) > r102.STALE_MAX:
                v = None
            else:
                v = r103.judge(arq, arq.index(r), ix, NQ_WIN, NITEM_WIN)
            g = {None: "자료없음", True: "조건통과", False: "조건탈락"}[v]
            z = ret_of(p)
            if z is None:
                continue
            rows.append((p.get("pattern") or "?", g, z, p["entry_date"]))

    pats = [k for k, _c in Counter(x[0] for x in rows).most_common()]
    n_all = len(rows)
    print("후보 %s · 패턴 %s\n" % ("{:,}".format(n_all), " · ".join(pats)), flush=True)

    # ── ㉮ 자료 없는 무리에 파워플레이가 몰려 있나 ─────────────────────
    cg = Counter(x[1] for x in rows)
    print("무리 나눔 — %s" % (" · ".join("%s %s(%.1f%%)" % (k, "{:,}".format(v),
                                                           100.0 * v / len(rows))
                                         for k, v in cg.most_common())), flush=True)
    print("", flush=True)
    print("# ㉮ **「조건통과」 무리 vs 「자료없음」 무리 — 패턴이 어떻게 섞여 있나**", flush=True)
    print("  %-10s %10s %10s %10s" % ("패턴", "조건통과", "자료없음", "몰림 배수"), flush=True)
    print("  " + "-" * 46, flush=True)
    hav = [x for x in rows if x[1] == "조건통과"]
    non = [x for x in rows if x[1] == "자료없음"]
    ch, cn = Counter(x[0] for x in hav), Counter(x[0] for x in non)
    for k in pats:
        ph = 100.0 * ch[k] / max(1, len(hav))
        pn = 100.0 * cn[k] / max(1, len(non))
        print("  %-10s %9.1f%% %9.1f%% %9.2f배%s"
              % (k, ph, pn, (pn / ph if ph else float("nan")),
                 "  ← 몰려 있다" if ph and pn / ph > 1.3 else ""), flush=True)
    print("  %-10s %9s %9s" % ("── 합", "{:,}".format(len(hav)), "{:,}".format(len(non))),
          flush=True)

    # ── ㉯ 패턴별 성적 ────────────────────────────────────────────────
    print("\n# ㉯ **패턴이 실제로 성적을 가르나** — 매매 한 번당", flush=True)
    print("  %-10s %8s %12s %10s" % ("패턴", "후보 수", "매매 한 번당", "이긴 비율"), flush=True)
    print("  " + "-" * 46, flush=True)
    base_all = [x[2] for x in rows]
    for k in pats:
        v = [x[2] for x in rows if x[0] == k]
        print("  %-10s %8s %+11.3f%% %9.1f%%"
              % (k, "{:,}".format(len(v)), st.mean(v),
                 100.0 * sum(1 for z in v if z > 0) / len(v)), flush=True)
    print("  %-10s %8s %+11.3f%%" % ("── 전체", "{:,}".format(n_all), st.mean(base_all)),
          flush=True)

    # ── ㉰ ★ 같은 패턴 «안»에서 자료 유무를 비교 ──────────────────────
    print("\n# ㉰ ★ **같은 패턴 «안»에서 자료 유무를 비교한다**", flush=True)
    print("     («자료 없는 게 좋은 것»이 패턴 때문인지 아닌지는 여기서만 갈린다)", flush=True)
    print("  %-10s %9s %9s %14s %-22s" %
          ("패턴", "조건통과 n", "자료없음 n", "자료없음−조건통과", "구간(95%)"), flush=True)
    print("  " + "-" * 70, flush=True)
    out = {}
    for k in pats + ["── 전체"]:
        a = [x[2] for x in rows if (k == "── 전체" or x[0] == k) and x[1] == "자료없음"]
        b = [x[2] for x in rows if (k == "── 전체" or x[0] == k) and x[1] == "조건통과"]
        if len(a) < 30 or len(b) < 30:
            print("  %-10s %9s %9s   (표본 부족)" % (k, len(b), len(a)), flush=True)
            continue
        d, lo, hi = ci(a, b, seed=hash(k) % 9999)
        out[k] = {"n_has": len(b), "n_non": len(a), "diff": d, "lo": lo, "hi": hi}
        print("  %-10s %9s %9s %+13.3f%%p [%+6.3f, %+6.3f] %s"
              % (k, "{:,}".format(len(b)), "{:,}".format(len(a)), d, lo, hi,
                 "0 배제" if not (lo <= 0 <= hi) else "**0 포함 = 못 가림**"), flush=True)

    print("\n" + "=" * 104, flush=True)
    print("  ★ 읽는 법", flush=True)
    print("     ㉮ 에서 PP 가 «몰려 있고» ㉯ 에서 PP 가 «좋고»", flush=True)
    print("     ㉰ 의 «전체»는 플러스인데 «패턴 안»에서는 0 이면  →  **사용자 가설이 맞다**", flush=True)
    print("     ㉰ 가 «패턴 안»에서도 플러스면                    →  패턴 말고 «다른 것»이다",
          flush=True)
    (r91.OUT / "103b-pattern-mix.json").write_text(
        json.dumps({"within": out,
                    "mix_has": dict(ch), "mix_non": dict(cn),
                    "by_pat": {k: st.mean([x[2] for x in rows if x[0] == k]) for k in pats}},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 103b-pattern-mix.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

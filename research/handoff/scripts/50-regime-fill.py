# -*- coding: utf-8 -*-
"""50 — **4회차의 이득이 실집행판에서 사라지는 이유**. 기전을 쓰기 «전»에 잰다.

```
관측 증분 (4a − 3a)   종가·무비용 **+13.97%p**  →  실집행·무비용 **+0.72%p**
```
**사용자가 실제로 쓸 판은 «실집행판»이다.** 4회차는 유일하게 「바탕과 무관하게 좋은」
회차인데, **그게 실전에서 사라지면 이 과제에서 살아남는 게 하나도 없다.**

측정 셋 (지시서 그대로)
-----------------------
① **국면 «켜진 날 진입» vs «꺼진 날 진입»의 갭 이격 분포** — 승·패 갈라서
   (`max(목표,시가) − 종가` / `min(선,시가) − 종가`, 진입가 대비 %p)
② **4a 가 걸러낸 방아쇠의 «종가판 성적»과 «실집행판 성적»** — 걸러낸 것이 종가판에서만 나빴나
③ **4a 와 3a 의 «청산 종류별 구성»** — 구성이 바뀌면 실집행 보정이 다르게 걸린다

⚠️ 이 문서는 **진입 집합**(open_until 통과분) 기준이다(체결 집합이 아니다). 열 이름에 박는다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/50-regime-fill.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                          # noqa: E402

_s = _u.spec_from_file_location("r48", HERE / "48-round4-regime.py")
r48 = _u.module_from_spec(_s)
_s.loader.exec_module(r48)
r47, r41 = r48.r47, r48.r41
OUT = ROOT / ".cache" / "bt5y" / "out"
ADDS = ((3.0, 0.5),)


def kind_of(e):
    """청산 종류 — 결과와 다리 수로 가른다."""
    if e["result"] == "ambiguous":
        return "예외"
    if e["result"] == "unresolved":
        return "미결"
    if e["result"] == "loss":
        return "손절"
    return "목표+추격" if len(e["exits"]) > 1 else "목표"


def per_trade(e):
    """방아쇠 하나의 순수익 — 트랜치 취득가를 반영한다(파일럿 0.5 · 증액 0.5)."""
    epx = e["entry_px"]
    lots = [(epx, 0.5)]
    if e.get("add"):
        lots.append((e["add"][1], 0.5))
    else:
        lots = [(epx, 1.0)]
    tot = sum(x[1] for x in lots)
    return sum(fr * slot_sim.net(round(px / ep * 100 - 100, 2)) * (w / tot)
               for _d, fr, px in e["exits"] for ep, w in lots)


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    eqw = json.loads((OUT / "26-eqw-us.json").read_text(encoding="utf-8"))
    flags = r48.ma_flags(eqw["curve_harness_filt"])

    def on(p):
        g = flags.get(p["scan_date"])
        return True if (g is None or g[20] is None) else g[20]

    ev = {}
    for tag, ft, fs in (("종가", "close", "close"), ("실집행", "limit", "market")):
        e, _ = r47.replay(by, ft, fs, adds=ADDS)
        ev[tag] = {(x["scan_date"], x["code"], x["pattern"]): x for x in e}
    # 🚨 **실집행 규약이 «진입 집합»까지 바꾼다.**
    #    3회차는 증액가가 «평균단가»를 올리고, 평균단가가 손절·목표 «선»을 옮긴다.
    #    → 결착일이 달라지고 → `open_until` 차단이 달라지고 → 진입 집합이 달라진다.
    #    (0~2회차에는 없던 성질이다. 거기선 선이 «진입가» 고정이었다.)
    ka, kb = set(ev["종가"]), set(ev["실집행"])
    keys = sorted(ka & kb)
    print("🚨 진입 집합 — 종가판 %d · 실집행판 %d · **공통 %d** "
          "(종가에만 %d · 실집행에만 %d)"
          % (len(ka), len(kb), len(keys), len(ka - kb), len(kb - ka)), flush=True)
    print("   → 실집행 규약이 «평균단가 → 선 → 결착일 → open_until» 을 타고 진입 집합을 바꾼다.",
          flush=True)
    print("   ⚠️ 아래는 **공통 집합**만 쓴다(짝을 지어야 이격을 잴 수 있다).", flush=True)
    onmap = {(p["scan_date"], p["code"], p["pattern"]): on(p)
             for ps in by.values() for p in ps}
    print("공통 진입 %d · 국면 켜진 것 %d (%.1f%%)"
          % (len(keys), sum(1 for k in keys if onmap[k]),
             100 * sum(1 for k in keys if onmap[k]) / len(keys)), flush=True)

    # ── ① 갭 이격 분포 (국면 × 승/패) ────────────────────────────────────
    print("", flush=True)
    print("=" * 96, flush=True)
    print("① 갭 이격 = **실집행 체결가 − 종가** (진입가 대비 %p) · **진입 집합**(open_until 통과분)", flush=True)
    print("=" * 96, flush=True)
    g = defaultdict(list)
    for k in keys:
        a, b = ev["종가"][k], ev["실집행"][k]
        if len(a["exits"]) != len(b["exits"]):
            continue
        epx = a["entry_px"]
        kd = kind_of(a)
        side = "승(목표)" if kd.startswith("목표") else ("패(손절·추격)" if kd in ("손절",) else None)
        for (da_, fa, pa), (_db, _fb, pb) in zip(a["exits"], b["exits"]):
            d = (pb - pa) / epx * 100
            if kd.startswith("목표"):
                s = "승(목표)" if (da_, fa, pa) == a["exits"][0] else "패(추격·본전)"
            elif kd == "손절":
                s = "패(손절)"
            else:
                continue
            g[(("켜짐" if onmap[k] else "꺼짐"), s)].append(d)
    print("  %-6s %-14s %8s %10s %10s %10s %10s"
          % ("국면", "쪽", "n", "중앙", "평균", "P10", "P90"), flush=True)
    res1 = {}
    for st_ in ("켜짐", "꺼짐"):
        for side in ("승(목표)", "패(추격·본전)", "패(손절)"):
            v = sorted(g.get((st_, side), []))
            if not v:
                continue
            n = len(v)
            res1["%s|%s" % (st_, side)] = {"n": n, "median": v[n // 2], "mean": st.mean(v),
                                           "p10": v[n // 10], "p90": v[9 * n // 10]}
            print("  %-6s %-14s %8d %+9.3f %+9.3f %+9.3f %+9.3f"
                  % (st_, side, n, v[n // 2], st.mean(v), v[n // 10], v[9 * n // 10]),
                  flush=True)
    print("  ⚠️ 양수 = 실집행이 «유리», 음수 = 실집행이 «불리».", flush=True)

    # ── ② 걸러낸 방아쇠의 성적 ───────────────────────────────────────────
    print("", flush=True)
    print("=" * 96, flush=True)
    print("② **걸러낸 방아쇠**(국면 꺼짐)의 성적 — 종가판 vs 실집행판 · **진입 집합**(open_until 통과분)", flush=True)
    print("=" * 96, flush=True)
    print("  %-10s %8s %14s %14s %12s" % ("무리", "n", "종가판 거래당", "실집행 거래당", "차이"),
          flush=True)
    res2 = {}
    for lab, sel in (("남긴 것(켜짐)", True), ("걸러낸 것(꺼짐)", False)):
        ks = [k for k in keys if onmap[k] == sel]
        a = st.mean(per_trade(ev["종가"][k]) for k in ks)
        b = st.mean(per_trade(ev["실집행"][k]) for k in ks)
        res2[lab] = {"n": len(ks), "close": a, "real": b, "diff": b - a}
        print("  %-10s %8d %13.4f%% %13.4f%% %11.4f%%p" % (lab, len(ks), a, b, b - a),
              flush=True)
    d = res2["남긴 것(켜짐)"], res2["걸러낸 것(꺼짐)"]
    print("  → **걸러내기의 값** — 종가판 %+.4f%%p · 실집행판 %+.4f%%p (차 %+.4f%%p)"
          % (d[0]["close"] - d[1]["close"], d[0]["real"] - d[1]["real"],
             (d[0]["real"] - d[1]["real"]) - (d[0]["close"] - d[1]["close"])), flush=True)

    # ── ③ 청산 종류별 구성 ───────────────────────────────────────────────
    print("", flush=True)
    print("=" * 96, flush=True)
    print("③ 청산 종류별 «구성» — 3a(전체) vs 4a(국면 켜진 것만) · **진입 집합**(open_until 통과분)", flush=True)
    print("=" * 96, flush=True)
    c3 = Counter(kind_of(ev["종가"][k]) for k in keys)
    c4 = Counter(kind_of(ev["종가"][k]) for k in keys if onmap[k])
    n3, n4 = sum(c3.values()), sum(c4.values())
    print("  %-12s %10s %8s %10s %8s %10s" % ("종류", "3a n", "3a %", "4a n", "4a %", "차이(%p)"),
          flush=True)
    res3 = {}
    for kd in ("목표+추격", "목표", "손절", "예외", "미결"):
        p3 = 100 * c3.get(kd, 0) / n3
        p4 = 100 * c4.get(kd, 0) / n4
        res3[kd] = {"n3": c3.get(kd, 0), "p3": p3, "n4": c4.get(kd, 0), "p4": p4}
        print("  %-12s %10d %7.2f%% %10d %7.2f%% %+9.2f"
              % (kd, c3.get(kd, 0), p3, c4.get(kd, 0), p4, p4 - p3), flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "50-regime-fill.json").write_text(
        json.dumps({"gap": res1, "filtered": res2, "kinds": res3}, ensure_ascii=False,
                   indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/50-regime-fill.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""51 — **국면 필터의 이득은 «어느 거래가 자본을 받는가»를 통해 오는가.**

왜 여기까지 왔나
----------------
50번에서 셋 다 기각됐다:
① 갭 이격은 국면 켜진 쪽이 **덜 불리**(가설과 반대) ② 걸러낸 것이 **남긴 것보다 좋음**
③ 청산 구성 **거의 불변**. **셋 다 4회차 실집행 소멸을 설명 못 한다.**
남은 통로는 하나 — **진입 집합 per-trade 는 나쁜데 «체결분» 은 −0.098 → +0.280 으로 좋다.**

세 모집단 (이 문서의 용어 — `00-summary-table.md` 정의를 따른다)
-----------------------------------------------------------------
```
① 방아쇠 전수  26,508   hi >= pivot 인 모든 종목-일 (open_until 차단 포함)
② 진입 집합    ~9,000   그중 open_until 을 통과해 «포지션이 열린» 것
③ 체결 집합    ~300     그중 슬롯/자본을 «실제로 받은» 것
```
**이 문서는 ③ 체결 집합을 잰다.** 열 이름에 박는다.

재는 것
-------
1. 국면 켜짐/꺼짐별 **체결 건수**와 **자본×시간 점유** (건수만으로는 안 보인다)
2. 켜짐/꺼짐별 **체결분 per-trade** 와 **보유일수 분포**
3. 🚨 **「걸러내지 않았다면 그 자리에 무엇이 들어왔을까」** — 4a 가 막은 진입 중
   **실제로 칸을 받았을 것**은 몇 건인가. 자본 제약이 이미 대부분을 막고 있었다면
   필터의 값은 **「나쁜 걸 걸렀다」가 아니라 「좋은 걸 «먼저» 넣었다」**이다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/51-regime-capital.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                          # noqa: E402
import slot_sim_pyr as sp                                # noqa: E402

_s = _u.spec_from_file_location("r48", HERE / "48-round4-regime.py")
r48 = _u.module_from_spec(_s)
_s.loader.exec_module(r48)
r47, r41 = r48.r47, r48.r41
OUT = ROOT / ".cache" / "bt5y" / "out"
ADDS = ((3.0, 0.5),)
N = 40
RISK, CAP, PILOT = 0.0125, 0.25, 0.5


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

    onmap = {(p["scan_date"], p["code"], p["pattern"]): on(p)
             for ps in by.values() for p in ps}
    dayidx = {}
    for ps in by.values():
        for p in ps:
            dayidx[(p["scan_date"], p["code"], p["pattern"])] = {x: i for i, x in enumerate(p["d"])}

    res = {}
    for fname, ft, fs in (("종가판", "close", "close"), ("실집행 근사판", "limit", "market")):
        e3, _ = r47.replay(by, ft, fs, adds=ADDS)
        by_r = {y: [p for p in ps if on(p)] for y, ps in by.items()}
        e4, _ = r47.replay(by_r, ft, fs, adds=ADDS)
        # 🚨 **4a 가 3a 에 «없는» 진입을 갖는다.** 국면 필터가 방아쇠를 걷어내면
        #    `open_until` 이 풀려 «막혀 있던 다른 방아쇠»가 들어온다.
        #    (필터는 «빼기»만 하는 게 아니라 «자리를 내주기»도 한다.)
        pt = {(x["scan_date"], x["code"], x["pattern"]): x for x in e3}
        for x in e4:
            pt.setdefault((x["scan_date"], x["code"], x["pattern"]), x)
        only4 = sum(1 for x in e4
                    if (x["scan_date"], x["code"], x["pattern"])
                    not in {(y["scan_date"], y["code"], y["pattern"]) for y in e3})
        print("  🚨 4a 에만 있는 진입 **%d건** — 필터가 `open_until` 을 풀어 준 몫"
              % only4, flush=True)
        print("", flush=True)
        print("#" * 92, flush=True)
        print("# %s — 진입 집합 3a %d · 4a %d" % (fname, len(e3), len(e4)), flush=True)
        print("#" * 92, flush=True)

        def ret(k):
            e = pt[k]
            lots = ([(e["entry_px"], 0.5), (e["add"][1], 0.5)] if e.get("add")
                    else [(e["entry_px"], 1.0)])
            tot = sum(x[1] for x in lots)
            return sum(fr * slot_sim.net(round(px / ep * 100 - 100, 2)) * (w / tot)
                       for _d, fr, px in e["exits"] for ep, w in lots)

        def hold(k):
            e = pt[k]
            return dayidx[k].get(e["resolve_date"], 0)

        stats = {}
        for name, ev in (("3a", e3), ("4a", e4)):
            agg = {"켜짐": {"n": [], "cw": [], "pt": [], "hd": []},
                   "꺼짐": {"n": [], "cw": [], "pt": [], "hd": []}}
            # 🚨 seed 별로 따로 모은다 — 「40 중 몇 개가 그쪽인가」를 세려면 필요하다
            per_seed = [{"켜짐": [], "꺼짐": []} for _ in range(N)]
            for s in range(N):
                r = sp.sim_pyr(ev, seed=s, risk=RISK, cap=CAP, pilot=PILOT)
                cnt = {"켜짐": 0, "꺼짐": 0}
                cw = {"켜짐": 0.0, "꺼짐": 0.0}
                for k, _lim, w1, _ed, _rd in r["fill_log"]:
                    g = "켜짐" if onmap.get(k) else "꺼짐"
                    cnt[g] += 1
                    cw[g] += w1 * max(1, hold(k))       # 자본×시간
                    agg[g]["pt"].append(ret(k))
                    agg[g]["hd"].append(hold(k))
                    per_seed[s][g].append(ret(k))
                for g in ("켜짐", "꺼짐"):
                    agg[g]["n"].append(cnt[g])
                    agg[g]["cw"].append(cw[g])
            stats[name] = agg
            if name == "3a":
                sg = [(st.mean(x["꺼짐"]) - st.mean(x["켜짐"]))
                      for x in per_seed if x["켜짐"] and x["꺼짐"]]
                nb = sum(1 for v in sg if v > 0)
                print("    🚨 **seed별 부호** — 「꺼짐이 좋다」가 **%d / %d**"
                      " · 차이 중앙 %+.4f%%p · 최소 %+.4f · 최대 %+.4f"
                      % (nb, len(sg), st.median(sg), min(sg), max(sg)), flush=True)
            tot_n = st.mean(agg["켜짐"]["n"]) + st.mean(agg["꺼짐"]["n"])
            tot_c = st.mean(agg["켜짐"]["cw"]) + st.mean(agg["꺼짐"]["cw"])
            print("", flush=True)
            print("  [%s] **체결 집합** (seed 0~%d 평균)" % (name, N - 1), flush=True)
            print("    %-6s %10s %8s %14s %8s %12s %10s"
                  % ("국면", "체결 건수", "건수 %", "자본×시간", "점유 %", "per-trade", "보유일 중앙"),
                  flush=True)
            for g in ("켜짐", "꺼짐"):
                a = agg[g]
                if not a["n"] or tot_n == 0:
                    continue
                hd = sorted(a["hd"])
                print("    %-6s %10.1f %7.1f%% %13.4f %7.1f%% %11.4f%% %9s"
                      % (g, st.mean(a["n"]), 100 * st.mean(a["n"]) / tot_n,
                         st.mean(a["cw"]), 100 * st.mean(a["cw"]) / tot_c,
                         st.mean(a["pt"]) if a["pt"] else 0.0,
                         ("%d일" % hd[len(hd) // 2]) if hd else "—"), flush=True)

        # ── ③ 「걸러내지 않았다면 그 자리에 무엇이 들어왔을까」 ──────────────
        f3 = set()
        for s in range(N):
            r = sp.sim_pyr(e3, seed=s, risk=RISK, cap=CAP, pilot=PILOT)
            f3 |= {k for k, _l, _w, _e, _r in r["fill_log"] if not onmap.get(k)}
        n_off_entry = sum(1 for k in pt if not onmap.get(k))
        print("", flush=True)
        print("  🚨 **「걸러내지 않았다면」** — 3a 에서 «국면 꺼진» 진입 %d건 중"
              % n_off_entry, flush=True)
        # 🚨 **합집합을 비율로 읽으면 안 된다.** 물음이 「한 판에서 몇 건이 자본을 받나」면
        #    분자는 «한 seed» 의 건수다. 40 seed 합집합은 「어떤 순서에서든 받을 수 있는」
        #    다른 양이다. (2026-08-25 정정 — 오늘 열두 번째 「같은 이름의 다른 양」)
        per_run = st.mean(stats["3a"]["꺼짐"]["n"])
        print("     **한 판 기준 %.1f건 / %d = %.1f%%**  ← 물음이 「한 판에서」이므로 이게 답"
              % (per_run, n_off_entry, 100 * per_run / max(1, n_off_entry)), flush=True)
        print("     (참고: seed %d개 «합집합» 은 %d건 = %.1f%% — **다른 양이다**)"
              % (N, len(f3), 100 * len(f3) / max(1, n_off_entry)), flush=True)
        print("     → %s" % ("**자본 제약이 이미 대부분을 막고 있었다** — 필터의 값은 "
                             "「나쁜 걸 걸렀다」보다 **«어느 것을 먼저 넣느냐»**에 가깝다."
                             if per_run / max(1, n_off_entry) < 0.2 else
                             "**자본 제약이 다 막고 있진 않았다** — 필터가 실제로 걸러낸 몫이 있다."),
              flush=True)
        res[fname] = {"n_entry_3a": len(e3), "n_entry_4a": len(e4),
                      "off_entry": n_off_entry, "off_filled": len(f3),
                      "stats": {k: {g: {"n": st.mean(v["n"]), "cw": st.mean(v["cw"]),
                                        "pt": (st.mean(v["pt"]) if v["pt"] else None),
                                        "hd": (st.median(v["hd"]) if v["hd"] else None)}
                                    for g, v in a.items()} for k, a in stats.items()}}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "51-regime-capital.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/51-regime-capital.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""74t — **「같은 봉에 증액과 목표가 겹치는」 봉이 몇 건인가.** 세기만 한다.

왜
--
`pyr_trigger.resolve_one` 은 한 봉 안에서 **증액을 먼저** 처리한다(47번 순서).
증액 → 평균단가 ↑ → 목표선 ↑ 이라 **그날 목표가 안 걸릴 수도 있다**.
일봉으로는 장중 선후를 알 수 없으므로 이건 **결과를 어느 쪽으로도 밀 수 있는 임의 규약**이다.
그래서 **크기**를 잰다 — 「이 꼬리는 전체의 몇 분의 몇인가」(실패유형 19′).

무엇을 「겹쳤다」로 보는가
--------------------------
증액이 **실제로 들어간** 봉 `i` 에서
```
T_before = (그 증액 «전» 평균단가) × (1 + target/100)
T_after  = (그 증액 «후» 평균단가) × (1 + target/100)
겹침      : h[i] >= T_before                     ← 목표-먼저 규약이었으면 그날 결착했을 봉
  ├ 그대로 : h[i] >= T_after                     ← 증액을 먼저 해도 그날 결착 (몫·단가만 달라짐)
  └ 미뤄짐 : h[i] <  T_after                     ← **증액이 목표선을 밀어 올려 결착이 미뤄졌다**
```
🚨 **증액이 «막힌» 트랜치(mask False)는 평균단가를 안 바꾸므로 순서가 아무 영향이 없다.**
   그래서 `sched` 가 아니라 **`lots`(실제로 산 것)** 만 센다.

🚨 이 집계는 `pyr_trigger` 를 **고치지 않고** 산출물만으로 되짚는다.
   `lots` 에 트랜치별 (날짜·가격·몫)이 다 있으므로 평균단가 진행을 그대로 재구성할 수 있다.

⚠️ 세는 것만 한다. **「그래서 어느 쪽이 옳다」는 여기서 안 쓴다.**
⚠️ 체결 규약은 74번 헤드라인인 **실집행 근사(limit/market)** 다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/74t-samebar-order.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                   # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
YEARS = tuple(range(2017, 2027))
EXT_NAME = "uspath_ext2017.json"
TARGET = 20.0
CONFIGS = (("두 단 (1/2,1/2)", (0.5, 0.5)),
           ("세 단 (1/3×3)", (1 / 3, 1 / 3, 1 / 3)))


def scan_one(p, r):
    """해결 하나에서 겹친 봉을 센다. → (겹침, 미뤄짐) 봉 수"""
    h, d = p["h"], p["d"]
    idx = {x: i for i, x in enumerate(d)}
    lots = r["lots"]
    hit = defer = 0
    for j in range(1, len(lots)):                 # 파일럿(0번)은 증액이 아니다
        dt = lots[j][0]
        i = idx.get(dt)
        if i is None or h[i] is None:
            continue
        w0 = sum(x[2] for x in lots[:j])
        w1 = sum(x[2] for x in lots[:j + 1])
        a0 = sum(px * fr for _dt, px, fr, _k in lots[:j]) / w0
        a1 = sum(px * fr for _dt, px, fr, _k in lots[:j + 1]) / w1
        if h[i] >= a0 * (1 + TARGET / 100):
            hit += 1
            if h[i] < a1 * (1 + TARGET / 100):
                defer += 1
    return hit, defer


def main() -> int:
    ef = BT / "sub" / EXT_NAME
    ext = {}
    if ef.exists():
        for q in json.loads(ef.read_text(encoding="utf-8"))["trigger_paths"]:
            ext[(q["scan_date"], q["code"], q["pattern"])] = q

    acc = {}
    for lab, shares in CONFIGS:
        acc[lab] = {"n_res": 0, "n_with_add": 0, "n_bars_add": 0,
                    "n_bars_hit": 0, "n_bars_defer": 0,
                    "n_res_hit": 0, "n_res_defer": 0,
                    "res_mix_defer": Counter(), "res_mix_all": Counter()}
    n_path = 0

    for y in YEARS:
        f = BT / "sub" / ("uspath_%d.json" % y)
        if not f.exists():
            print("🚨 uspath_%d.json 이 없다" % y, flush=True)
            return 2
        ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
        for i, p in enumerate(ps):
            q = ext.get((p["scan_date"], p["code"], p["pattern"]))
            if q is not None:
                ps[i] = q
        n_path += len(ps)
        for p in ps:
            for lab, shares in CONFIGS:
                got = pt.resolve_all_masks(p, ft="limit", fs="market", shares=shares)
                a = acc[lab]
                for _mask, r in got.items():
                    a["n_res"] += 1
                    a["res_mix_all"][r["result"]] += 1
                    n_add = len(r["lots"]) - 1
                    if n_add == 0:
                        continue
                    a["n_with_add"] += 1
                    a["n_bars_add"] += n_add
                    hit, defer = scan_one(p, r)
                    a["n_bars_hit"] += hit
                    a["n_bars_defer"] += defer
                    if hit:
                        a["n_res_hit"] += 1
                    if defer:
                        a["n_res_defer"] += 1
                        a["res_mix_defer"][r["result"]] += 1
        del ps

    print("", flush=True)
    print("경로 %d개 (%d~%d년) · 체결 규약 **실집행 근사(limit/market)** · 목표 +%.0f%%"
          % (n_path, YEARS[0], YEARS[-1], TARGET), flush=True)
    print("", flush=True)
    for lab, _shares in CONFIGS:
        a = acc[lab]
        print("─" * 88, flush=True)
        print("【%s】" % lab, flush=True)
        print("  분모 ① 해결 전수(경로 × mask 조합)          %8d" % a["n_res"], flush=True)
        print("  분모 ② 그중 «증액이 실제로 들어간» 해결      %8d  (①의 %.2f%%)"
              % (a["n_with_add"], 100 * a["n_with_add"] / max(1, a["n_res"])), flush=True)
        print("  분모 ③ 증액이 «실제로 들어간» 봉 전수        %8d" % a["n_bars_add"], flush=True)
        print("", flush=True)
        print("  겹친 봉      %7d  → ③의 **%.3f%%** · ①의 **%.4f%%**"
              % (a["n_bars_hit"], 100 * a["n_bars_hit"] / max(1, a["n_bars_add"]),
                 100 * a["n_bars_hit"] / max(1, a["n_res"])), flush=True)
        print("   ├ 그대로   %7d  (증액을 먼저 해도 그날 결착)"
              % (a["n_bars_hit"] - a["n_bars_defer"]), flush=True)
        print("   └ **미뤄짐** %5d  → ③의 **%.3f%%** · ①의 **%.4f%%**"
              % (a["n_bars_defer"], 100 * a["n_bars_defer"] / max(1, a["n_bars_add"]),
                 100 * a["n_bars_defer"] / max(1, a["n_res"])), flush=True)
        print("", flush=True)
        print("  해결 단위 — 겹친 봉이 하나라도 있는 해결 %d (①의 %.4f%%) · "
              "그중 미뤄진 해결 **%d** (①의 **%.4f%%**)"
              % (a["n_res_hit"], 100 * a["n_res_hit"] / max(1, a["n_res"]),
                 a["n_res_defer"], 100 * a["n_res_defer"] / max(1, a["n_res"])), flush=True)
        mix = a["res_mix_defer"]
        tot = sum(mix.values())
        print("  미뤄진 해결의 «결과» 구성: %s"
              % (" · ".join("%s %d(%.1f%%)" % (k, mix.get(k, 0),
                                               100 * mix.get(k, 0) / max(1, tot))
                            for k in ("win", "loss", "ambiguous", "unresolved"))
                 if tot else "—"), flush=True)
        allm = a["res_mix_all"]
        allt = sum(allm.values())
        print("  (대조) 해결 전수의 결과 구성:  %s"
              % " · ".join("%s %d(%.1f%%)" % (k, allm.get(k, 0),
                                              100 * allm.get(k, 0) / max(1, allt))
                           for k in ("win", "loss", "ambiguous", "unresolved")), flush=True)
        print("", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "74t-samebar-order.json").write_text(
        json.dumps({lab: {k: (dict(v) if isinstance(v, Counter) else v)
                          for k, v in a.items()} for lab, a in acc.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("저장: .cache/bt5y/out/74t-samebar-order.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

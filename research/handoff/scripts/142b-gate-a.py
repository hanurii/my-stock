# -*- coding: utf-8 -*-
r"""142b — **관문 ⓐ.** `detect_final_coil` 직접 호출이 `evaluate_vcp` 내부와 «같은 값»인가.

왜 필요한가
-----------
⑦(`coil_extreme_days`)은 `evaluate_vcp` 가 **반환하지 않는다** — 내부에서 계산돼 쓰이고 버려진다.
그래서 `detect_final_coil` 을 «직접» 부른다. 그러면 **인자를 잘못 맞출 위험**이 생긴다.
→ 두 경로가 «둘 다 내는» 값(coil_len·dry_mean·range_pct·min_dry)이 **완전히 같은지**로 확인한다.

🚨 이 관문이 통과해야 ⑦ 을 믿을 수 있다. 안 되면 인자가 어긋난 것이다.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))

import entry_envelope as env                                        # noqa: E402
from canslim_lib.vcp import (evaluate_vcp, detect_final_coil,        # noqa: E402
                             volume_ma, DEFAULT_PARAMS)

NEW = Path("D:/stock-data/uspath-warm/full")
KEYS = ("coil_len", "coil_dry_mean", "coil_range_pct", "coil_min_dry")


def main() -> int:
    n = same = 0
    ex = []
    for y in (2001, 2005, 2009):            # 세 해에서 뽑는다 (한 해 우연 방지)
        ps = json.loads((NEW / ("uspath_%d.json" % y)).read_text(encoding="utf-8"))
        ps = ps["trigger_paths"]
        random.Random(142).shuffle(ps)
        for rec in ps[:200]:
            if not rec.get("pre_d"):
                continue
            e = env.entry_view(rec)          # 🚨 봉투를 통과시킨다 — 실제 쓰는 길과 같게
            s = {"dates": e["pre_d"], "closes": e["pre_c"], "highs": e["pre_h"],
                 "lows": e["pre_l"], "opens": e["pre_o"], "volumes": e["pre_v"]}
            r = evaluate_vcp(s, None)
            p = DEFAULT_PARAMS
            lb = p["lookback_days"]
            cl, hi = s["closes"][-lb:], s["highs"][-lb:]
            lo, vo = s["lows"][-lb:], s["volumes"][-lb:]
            coil = detect_final_coil(hi, lo, cl, vo, volume_ma(vo, 50), len(cl) - 1, p)
            n += 1
            a = tuple(r[k] for k in KEYS)
            b = (None,) * 4 if coil is None else tuple(coil[k] for k in KEYS)
            if a == b:
                same += 1
            elif len(ex) < 3:
                ex.append((y, rec["code"], a, b))

    print("", flush=True)
    print("관문 ⓐ — 경로 **%d건** (2001·2005·2009 에서 각 200)" % n, flush=True)
    print("   `evaluate_vcp` 반환  vs  `detect_final_coil` 직접호출 — «같은 건» **%d**"
          % same, flush=True)
    ok = (same == n and n > 0)
    print("   → %s" % ("**통과**" if ok else "🚨 **미통과 — 인자가 어긋났다**"), flush=True)
    if ex:
        for e2 in ex:
            print("      예: %s" % (e2,), flush=True)
    if n == 0:
        print("   🚨 **비교한 것이 0 — 아무것도 안 하는 관문이다**", flush=True)
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
r"""142d — 「셋 다 같음」의 **기전을 «확인»한다.** 설명이 아니라.

왜
--
나는 「자람 4,805·재조정 22·꼬리수정 53 이 있었는데도 상위 5% 구성원이 0 변화
⇒ 변화가 꼬리 순위를 흔들 만큼 크지 않았다」고 **«설명»했다. 그건 «확인»이 아니다.**
그리고 오늘 **「완전 일치는 «같은 계산»의 신호」**로 이미 한 번 데였다(`_lean_load` 사고).

## 🚨 결정적 검사 — **역방향부터**
```
① 바뀐 경로들의 **r_ 가 실제로 «바뀌었는가»**
   하나도 안 바뀌었다면 그건 「변화가 작았다」가 아니라
   **«우리가 여전히 같은 걸 읽고 있다»**는 뜻이다
② 뒤 구간 대박 151건 중 **「바뀐 경로」에 해당하는 게 몇 건인가**
   0 이면 기전이 확인된다 — 바뀐 경로는 «애초에 꼬리가 아니었다»
③ 후보 «+1» 이 어느 해에서 왔는가 — 설명 없는 변화는 안 남긴다
```

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/142d-why-same.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                        # noqa: E402

OLD = ROOT / ".cache" / "bt5y" / "sub"
NEW = Path("D:/stock-data/uspath-warm/full")
FROZEN = ROOT / "research" / "handoff" / "data" / "142-labels-frozen.json"
BACK_YEARS = tuple(range(2012, 2027))
TARGET, STOP, HALF = 30.0, 10.0, 0.5


def r_of(p):
    t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                         half=HALF, shares=(1.0,), add_stop="floor_entry")
    m = t["masks"][()]
    ep = t["entry_px"]
    if not ep or not m["exits"]:
        return None
    return sum(sh * (px / ep * 100.0 - 100.0) for _d, sh, px in m["exits"])


def key(p):
    return "|".join((p["scan_date"], p["code"], p["pattern"]))


def main() -> int:
    fz = json.loads(FROZEN.read_text(encoding="utf-8"))
    win = set(fz["back"]["keys"])
    print("뒤 구간 대박 **%d건**을 들고 시작" % len(win), flush=True)

    n_pair = 0
    path_diff = 0          # 경로(배열)가 바뀐 건
    r_diff = 0             # 그중 r_ «값»이 바뀐 건
    r_diff_win = 0         # r_ 가 바뀐 «대박»
    win_in_changed = 0     # 바뀐 «경로»에 해당하는 대박
    by_year = Counter()
    only_new, only_old = [], []
    ex = []

    for y in BACK_YEARS:
        fo, fn = OLD / ("uspath_%d.json" % y), NEW / ("uspath_%d.json" % y)
        o = {key(p): p for p in json.loads(fo.read_text(encoding="utf-8"))["trigger_paths"]}
        n = {key(p): p for p in json.loads(fn.read_text(encoding="utf-8"))["trigger_paths"]}
        only_new += [(y, k) for k in n if k not in o]
        only_old += [(y, k) for k in o if k not in n]
        for k in (set(o) & set(n)):
            n_pair += 1
            a, b = o[k], n[k]
            changed = any(a.get(f) != b.get(f) for f in ("d", "o", "h", "l", "c",
                                                         "pivot", "entry_price"))
            if not changed:
                continue
            path_diff += 1
            by_year[y] += 1
            ra, rb = r_of(a), r_of(b)
            if ra is None or rb is None or abs(ra - rb) > 1e-9:
                r_diff += 1
                if k in win:
                    r_diff_win += 1
                if len(ex) < 3:
                    ex.append((y, k, ra, rb))
            if k in win:
                win_in_changed += 1
        del o, n
        print("   %d년 처리" % y, flush=True)

    print("", flush=True)
    print("=" * 92, flush=True)
    print("기전 «확인» — 뒤 구간 짝 %s건" % "{:,}".format(n_pair), flush=True)
    print("=" * 92, flush=True)
    print("① 경로(배열·기준가)가 «바뀐» 건        **%s**" % "{:,}".format(path_diff), flush=True)
    print("   그중 **r_ 값이 «실제로» 바뀐 건**    **%s**  → %s"
          % ("{:,}".format(r_diff),
             "**바뀐다 = 우리가 «다른 것»을 읽고 있다**" if r_diff > 0
             else "🚨 **하나도 안 바뀐다 — 같은 걸 읽고 있는 것 아닌가**"), flush=True)
    if ex:
        for e in ex:
            print("      예: %d %s  r_ %.4f → %.4f" % (e[0], e[1], e[2], e[3]), flush=True)
    print("", flush=True)
    print("② 대박 %d건 중 «바뀐 경로»에 해당 **%d건** · 그중 r_ 가 바뀐 것 **%d건**"
          % (len(win), win_in_changed, r_diff_win), flush=True)
    print("   → %s" % ("**0 — 바뀐 경로는 «애초에 꼬리가 아니었다». 기전 확인**"
                       if win_in_changed == 0 else
                       "**꼬리에도 변화가 닿았는데 «구성원»은 안 바뀌었다 — 그게 진짜 물음**"),
          flush=True)
    print("", flush=True)
    print("③ 후보 «새쪽만» %d건 · «옛쪽만» %d건" % (len(only_new), len(only_old)), flush=True)
    for lab, xs in (("새쪽만", only_new), ("옛쪽만", only_old)):
        if xs:
            print("   %s 연도별: %s" % (lab, dict(Counter(y for y, _k in xs))), flush=True)
            print("      예: %s" % (xs[:3],), flush=True)
    print("", flush=True)
    print("경로가 바뀐 건의 «연도별»: %s" % dict(sorted(by_year.items())), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
r"""142c — **옛 자료 라벨 vs 새 자료 라벨.** 셋으로 갈라 본다.

왜
--
「같다/다르다」 한 줄로는 «틀린 인상»을 준다. 처방이 갈리기 때문이다:
```
㉠ **K(개수)**    5% 이므로 후보 수가 같으면 대개 같다
㉡ **문턱 r_**    자람·꼬리수정이 r_ 를 바꾸므로 달라질 수 있다
㉢ **«구성원»**   몇 건이 «새로 들어오고» 몇 건이 «빠졌나»  ← 이게 「같은 실험인가」를 정한다
```
🚨 2026-09-01 사고: `_lean_load` 가 자기 `r91` 을 따로 가져서 **라벨을 «옛» 자료로 얼렸다.**
   고친 뒤 «새» 자료로 다시 얼렸고, 여기서 둘을 «직접» 대 본다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/142c-label-diff.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_s)
_s.loader.exec_module(r102)
r91, f92a = r102.r91, r102.f92a
_s3 = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_s3)
_s3.loader.exec_module(r103)

OLD = ROOT / ".cache" / "bt5y" / "sub"
NEW = Path("D:/stock-data/uspath-warm/full")
FROZEN = ROOT / "research" / "handoff" / "data" / "142-labels-frozen.json"
FRONT_END = "2011-12-31"
TOP_Q = 0.05
YEARS = tuple(range(1999, 2027))


def label(t):
    m = t["masks"][next(iter(t["masks"]))]
    return sum(sh * (px / t["entry_px"] * 100.0 - 100.0) for _d, sh, px in m["exits"])


def run(sub):
    r91.TARGET, r91.STOP, r91.HALF = 30.0, 10.0, 0.5
    import _lean_load as ll
    ll.r91.SUB = sub                       # 🚨 «이쪽»을 바꿔야 한다 (사고 재발 방지)
    assert ll.r91.SUB == sub
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    def keep_f(p):
        arq = (fund.get(p["code"]) or {}).get("ARQ") or []
        a = f92a.asof(arq, p["entry_date"]) if arq else None
        v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                      > r102.STALE_MAX)
             else r103.judge(arq, arq.index(a), ix, 1, 2))
        return v is not False

    rows = []
    for y in YEARS:
        by1, _c, _n = ll.load_combo((y,), "1999-04-01", "2026-08-21")
        byf = {y: [p for p in by1.get(y, []) if keep_f(p)]}
        for t in r91.replay(byf)[0]:
            rows.append((t["entry_date"],
                         "|".join((t["scan_date"], t["code"], t["pattern"])),
                         label(t)))
        del by1, byf
    del fund
    return rows


def split(rows):
    out = {}
    for name, sel in (("front", lambda d: d <= FRONT_END),
                      ("back", lambda d: d > FRONT_END)):
        sub = [r for r in rows if sel(r[0])]
        ys = sorted((r[2] for r in sub), reverse=True)
        k = max(1, int(round(len(ys) * TOP_Q)))
        cut = ys[k - 1]
        out[name] = {"n": len(sub), "cut": cut,
                     "keys": {r[1] for r in sub if r[2] >= cut}}
    return out


def main() -> int:
    print("옛 자료로 계산 중 …", flush=True)
    o = split(run(OLD))
    print("새 자료로 계산 중 …", flush=True)
    n = split(run(NEW))

    print("", flush=True)
    print("=" * 92, flush=True)
    print("옛 자료(.cache/bt5y/sub) vs 새 자료(uspath-warm/full) — **셋으로 갈라서**", flush=True)
    print("=" * 92, flush=True)
    for name in ("front", "back"):
        a, b = o[name], n[name]
        ins = sorted(b["keys"] - a["keys"])
        out_ = sorted(a["keys"] - b["keys"])
        print("", flush=True)
        print("[%s]" % name, flush=True)
        print("   ㉠ **K(개수)**   옛 %d  →  새 %d   %s"
              % (len(a["keys"]), len(b["keys"]),
                 "**같음**" if len(a["keys"]) == len(b["keys"]) else "🚨 **다름**"), flush=True)
        print("      (후보 수 옛 %d → 새 %d)" % (a["n"], b["n"]), flush=True)
        print("   ㉡ **문턱 r_**   옛 %+.4f%%  →  새 %+.4f%%   %s"
              % (a["cut"], b["cut"],
                 "**같음**" if abs(a["cut"] - b["cut"]) < 1e-9 else
                 "🚨 **다름** (차 %+.4f%%p)" % (b["cut"] - a["cut"])), flush=True)
        print("   ㉢ **구성원**    새로 들어옴 **%d** · 빠짐 **%d** · 겹침 %d  → %s"
              % (len(ins), len(out_), len(a["keys"] & b["keys"]),
                 "**완전히 같음**" if not ins and not out_
                 else "🚨 **바뀜 %.2f%%**" % (100.0 * len(ins) / max(1, len(b["keys"])))),
              flush=True)
        for lab, xs in (("들어옴", ins), ("빠짐", out_)):
            if xs:
                print("      %s 예: %s" % (lab, xs[:3]), flush=True)

    fz = json.loads(FROZEN.read_text(encoding="utf-8"))
    print("", flush=True)
    print("얼린 파일과 대조 — 앞 K %d(=%d) · 뒤 K %d(=%d)"
          % (fz["front"]["K"], len(n["front"]["keys"]),
             fz["back"]["K"], len(n["back"]["keys"])), flush=True)
    ok = (fz["front"]["K"] == len(n["front"]["keys"])
          and fz["back"]["K"] == len(n["back"]["keys"]))
    print("   → %s" % ("**얼린 것이 «새» 자료가 맞다**" if ok
                       else "🚨 **얼린 것과 안 맞는다**"), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

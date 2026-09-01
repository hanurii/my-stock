# -*- coding: utf-8 -*-
r"""142a — **「대박」 집합을 «얼린다».** 체를 만들기 «전»에.

왜
--
「대박 = 후보 상위 5%」의 **분모와 목록이 체보다 «뒤»에 정해지면 순환**이다.
체를 고치면 분모가 따라 움직이고, 그러면 무엇을 이겼는지 말할 수 없다.
→ **지금 파일로 고정하고 커밋한다.** 이후 어떤 체도 이 목록을 «바꾸지 않는다».

🚨 여기서 «보는» 것은 **라벨뿐**이다. 특징은 손대지 않는다.
   그리고 142 의 점수는 **적합 파라미터가 0개**라 라벨을 알아도 «맞출 것이 없다».

라벨 규약 — 139 그대로
```
r_ = Σ sh·(px/entry_px·100 − 100)   ·  TARGET 30 · STOP 10 · HALF 0.5
     ft=limit · fs=market · shares=(1.0,) · add_stop=floor_entry
```
자료: `D:/stock-data/uspath-warm/full` (141번 · 스냅숏 2026-09-01 · 시세 ~2026-08-26)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/142a-freeze-labels.py
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

NEW = Path("D:/stock-data/uspath-warm/full")
OUT = ROOT / "research" / "handoff" / "data" / "142-labels-frozen.json"
SNAPSHOT = "2026-09-01 재빌드 · 시세 ~2026-08-26 · 원천 Sharadar 2026-08-27"
TARGET, STOP, HALF = 30.0, 10.0, 0.5
TOP_Q = 0.05
FRONT_END = "2011-12-31"          # 앞/뒤 경계 (140 과 같게)
YEARS = tuple(range(1999, 2027))


def label(t):
    """139-filter-curve.py:145-149 와 «같은» 식."""
    m = t["masks"][next(iter(t["masks"]))]
    return sum(sh * (px / t["entry_px"] * 100.0 - 100.0) for _d, sh, px in m["exits"])


def main() -> int:
    r91.TARGET, r91.STOP, r91.HALF = TARGET, STOP, HALF
    # 🚨 141 의 «새» 자료를 보게 한다 — `load_combo` 는 `r91.SUB` 에서 읽는다
    r91.SUB = NEW
    import _lean_load as ll
    # 🚨🚨 `_lean_load` 는 **자기 `r91` 인스턴스를 따로 가진다**(importlib 으로 다시 exec 한다).
    #    `r102.r91.SUB` 만 바꾸면 `load_combo` 는 여전히 «옛» `.cache/bt5y/sub` 를 읽는다.
    #    2026-09-01 실사고: 그래서 라벨을 «옛 자료»로 얼렸고, 「140 과 일치」가 «자명»해져 버렸다.
    ll.r91.SUB = NEW
    assert ll.r91.SUB == NEW, ll.r91.SUB

    # 🚨 **분모는 `by_f`** — 성장 둔화 필터까지 «현행 규칙»이다 (139:102-113 과 «같은 코드»)
    #    by2 판도 «대조 기록»으로 같이 낸다 (140 과의 라벨 일치 확인용)
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    def keep_f(p):
        """139 의 by_f 규약: judge 가 False 면 «뺀다». True·None(자료없음)은 «둔다»."""
        arq = (fund.get(p["code"]) or {}).get("ARQ") or []
        a = f92a.asof(arq, p["entry_date"]) if arq else None
        v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                      > r102.STALE_MAX)
             else r103.judge(arq, arq.index(a), ix, 1, 2))
        return v is not False

    rows, rows2 = [], []
    for y in YEARS:
        f = NEW / ("uspath_%d.json" % y)
        if not f.exists():
            print("🚨 %s 없음" % f.name, flush=True)
            return 2
        # 🚨 사다리 ②(조합)를 «141 자료»에서 그대로 만든다 — 91 과 같은 거르기 코드
        by1, _c, _n = ll.load_combo((y,), "1999-04-01", "2026-08-21")
        # by2 (대조 기록)
        e2, _b, _t = r91.replay(by1)
        for tt in e2:
            rows2.append({"entry_date": tt["entry_date"], "r": label(tt)})
        # by_f (주판정 분모)
        byf = {y: [p for p in by1.get(y, []) if keep_f(p)]}
        e1, _b, _t = r91.replay(byf)
        for tt in e1:
            rows.append({"scan_date": tt["scan_date"], "code": tt["code"],
                         "pattern": tt["pattern"], "entry_date": tt["entry_date"],
                         "r": label(tt)})
        del by1, byf, e1, e2
        print("   %d년 — by_f 누적 %d · by2 누적 %d" % (y, len(rows), len(rows2)),
              flush=True)

    front = [x for x in rows if x["entry_date"] <= FRONT_END]
    back = [x for x in rows if x["entry_date"] > FRONT_END]
    pack = {"snapshot": SNAPSHOT, "label": "139 r_ = sum(sh*(px/entry_px*100-100))",
            "target": TARGET, "stop": STOP, "half": HALF, "top_q": TOP_Q,
            "front_end": FRONT_END, "n_all": len(rows), "ladder": "by_f (139:102-113)"}
    for name, sub in (("front", front), ("back", back)):
        ys = sorted((x["r"] for x in sub), reverse=True)
        k = max(1, int(round(len(ys) * TOP_Q)))
        cut = ys[k - 1]
        keys = sorted((x["scan_date"], x["code"], x["pattern"])
                      for x in sub if x["r"] >= cut)
        pack[name] = {"n": len(sub), "cut": cut, "K": len(keys),
                      "keys": ["|".join(k2) for k2 in keys]}
        print("", flush=True)
        print("[%s] 후보 **%s** · 문턱 r_ = **%+.4f%%** · 대박 **K = %d** (%.3f%%)"
              % (name, "{:,}".format(len(sub)), cut, len(keys),
                 100.0 * len(keys) / max(1, len(sub))), flush=True)

    # ── 대조 기록: by2 앞 구간이 140 과 같은가 ──────────────────────────
    f2 = [x for x in rows2 if x["entry_date"] <= FRONT_END]
    ys2 = sorted((x["r"] for x in f2), reverse=True)
    k2 = max(1, int(round(len(ys2) * TOP_Q)))
    pack["by2_front_record"] = {"n": len(f2), "cut": ys2[k2 - 1], "K": k2}
    print("", flush=True)
    print("[대조 기록 · by2 앞] 후보 **%s** · 문턱 **%+.4f%%** · K **%d**"
          % ("{:,}".format(len(f2)), ys2[k2 - 1], k2), flush=True)
    print("   (140 은 후보 4,231 · 문턱 +41.99% · K 212 — 같으면 재빌드가 앞을 안 건드린 것)",
          flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pack, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    print("", flush=True)
    print("저장: %s  (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6), flush=True)
    print("🚨 **이 목록은 이후 어떤 체도 바꾸지 않는다.**", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

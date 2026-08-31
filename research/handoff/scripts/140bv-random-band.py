# -*- coding: utf-8 -*-
"""140bv — **139 의 ② 열(「무작위 감축」)에 «구간»을 붙인다.**

🚨 왜 — `139-filter-curve.py:158` 에서:
```python
rnd = random.Random(9090)          # ← 고정 씨앗
rd  = rnd.sample([t for _r, t in score], k)   # ← 부분집합을 «한 번»만 뽑는다
...
rr = [sl.sim_lots(sub, seed=s, ...) for s in range(n_seed)]   # ← 20판은 «슬롯 추첨»만 바꾼다
```
즉 **② 열의 각 칸은 「무작위 감축」을 «한 번» 뽑은 것**이고, 20판은 그 «한» 부분집합 위에서
슬롯 추첨만 다시 돌린 값이다. **재고 싶은 축(어느 부분집합이 뽑히느냐)에서는 n = 1 이다.**

증상도 이미 보인다 — ② 열이 «단조가 아니다**:
```
남김  50%  3,688만   25%  3,557만   10%  7,715만   5%  7,129만
```
「아무렇게나 지우면 대박도 같은 비율로 사라진다」가 참이라면 **5% 가 50% 보다 두 배 좋을 수 없다.**

무엇을 하나 — **부분집합 씨앗을 R 번 바꿔** 139 의 `main()` 을 그대로 돌리고, ② 열의 «분포»를 낸다.
   ★ **139 를 베껴 쓰지 않는다** — 옮겨 적으면 내 손계산이 끼어든다(88v 에서 겪었다).
     `random` 만 갈아끼우고 «139 의 코드 그대로» 부른다.

관문(유형 24′) — **고치기 «전»이 실패해야 한다**:
   패치를 끄고 두 판 돌리면 ② 가 «완전히 같아야» 한다(씨앗 고정이므로).
   같지 않으면 내 패치가 아니라 «다른 것»이 값을 흔드는 것이고, 그러면 이 판은 못 쓴다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/140bv-random-band.py [--reps N] [--full]
"""
from __future__ import annotations

import hashlib
import importlib.util as _u
import json
import os
import random as _real_random
import shutil
import statistics as st
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REAL_OUT = ROOT / ".cache" / "bt5y" / "out"
GUARD = ("139-filter-curve.json",)


class SeedShift:
    """`random` 모듈 «대역» — `Random(s)` 의 씨앗만 옮긴다. 나머지는 그대로 넘긴다."""

    def __init__(self, shift: int):
        self.shift = shift

    def Random(self, seed=None):                       # noqa: N802  (모듈 API 를 흉내낸다)
        return _real_random.Random(seed if seed is None else seed + self.shift)

    def __getattr__(self, name):
        return getattr(_real_random, name)


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None


def link_inputs(tmp):
    """🚨 `r91.OUT` 을 임시로 돌리면 «입력»도 거기서 찾는다(596MB — 복사 못 한다).
    → **하드링크**로 채운다. 단 139 가 «쓰는» 파일은 링크하면 안 된다 —
      같은 아이노드라 `write_text` 가 «원본을 잘라낸다**."""
    n = 0
    for p in REAL_OUT.iterdir():
        if not p.is_file() or p.name in GUARD:
            continue
        try:
            os.link(p, tmp / p.name)
            n += 1
        except OSError:
            shutil.copy2(p, tmp / p.name)
            n += 1
    return n


def load139():
    s = _u.spec_from_file_location("m139", HERE / "139-filter-curve.py")
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def run_once(mod, tmp, shift, quick):
    """139 의 main() 을 «그대로» 한 번 돌리고 ② 열만 꺼낸다."""
    mod.random = SeedShift(shift)
    mod.r91.OUT = tmp
    argv = sys.argv
    sys.argv = ["139", "--quick"] if quick else ["139"]
    try:
        rc = mod.main()
    finally:
        sys.argv = argv
    if rc != 0:
        return None
    res = json.loads((tmp / "139-filter-curve.json").read_text(encoding="utf-8"))
    key = "② 예측력 0 (무작위)"
    return {k: res[k][key] for k in res}


def main() -> int:
    reps = 20
    if "--reps" in sys.argv:
        reps = int(sys.argv[sys.argv.index("--reps") + 1])
    quick = "--full" not in sys.argv

    before = {f: md5(REAL_OUT / f) for f in GUARD}
    tmp = Path(tempfile.mkdtemp(prefix="rndband_"))
    nlink = link_inputs(tmp)
    mod = load139()

    print("=" * 104, flush=True)
    print("140bv — 139 의 ② 열에 «구간»을 붙인다 (부분집합 씨앗 %d판 · %s)"
          % (reps, "quick 6슬롯" if quick else "20슬롯"), flush=True)
    print("   🚨 139 는 `random.Random(9090)` 로 부분집합을 «한 번»만 뽑는다 → 그 축에서 n=1", flush=True)
    print("   임시 OUT %s  (입력 %d장 하드링크 · 쓰는 파일 %s 는 «링크 안 함»)"
          % (tmp, nlink, GUARD[0]), flush=True)
    print("=" * 104, flush=True)

    # ── 관문(유형 24′) — 패치를 «끄면» 두 판이 «같아야» 한다
    print("\n㉠ 관문 — 패치 끄고 두 판: **같아야** 통과 (안 같으면 다른 것이 값을 흔든다)", flush=True)
    a = run_once(mod, tmp, 0, quick)
    b = run_once(mod, tmp, 0, quick)
    if a is None or b is None:
        print("🚨 139 main() 이 0 을 안 냈다 — 중단", flush=True)
        return 2
    same = all(abs(a[k]["post"] - b[k]["post"]) < 1e-6 for k in a)
    print("   %s — %s" % ("**통과**" if same else "🚨 **미통과**",
                          " · ".join("%s %.0f만" % (k, a[k]["post"]) for k in a)), flush=True)
    if not same:
        print("🚨 씨앗을 고정했는데 두 판이 다르다. 이 판은 못 쓴다.", flush=True)
        return 3

    # ── 본판 — 부분집합 씨앗을 바꾼다
    print("\n㉡ 본판 — 부분집합 씨앗 %d판" % reps, flush=True)
    rows = {}
    for r in range(reps):
        got = run_once(mod, tmp, 1000 * (r + 1), quick)
        if got is None:
            print("🚨 %d판째 실패 — 중단" % (r + 1), flush=True)
            return 4
        for k, v in got.items():
            rows.setdefault(k, []).append(v["post"])
            rows.setdefault(k + "|n", []).append(v["n"])
        print("   %2d판  %s" % (r + 1,
              " · ".join("%s %7.0f만" % (k, got[k]["post"]) for k in got)), flush=True)

    # ── 표
    base_all = rows.get("100%") or []
    print("\n" + "=" * 104, flush=True)
    print("### 140bv — ② 「무작위 감축」의 «분포» (139 는 이 중 «한 판»만 보고했다)", flush=True)
    print("  %-8s %10s %10s %10s %12s %10s %10s"
          % ("남김", "중앙", "5백분위", "95백분위", "폭", "최소", "최대"), flush=True)
    print("  " + "-" * 78, flush=True)
    for k in ("100%", "50%", "25%", "10%", "5%"):
        v = sorted(rows.get(k) or [])
        if not v:
            continue
        lo = v[max(0, int(round(0.05 * (len(v) - 1))))]
        hi = v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]
        print("  %-8s %9.0f만 %9.0f만 %9.0f만 %11.0f만 %9.0f만 %9.0f만"
              % (k, st.median(v), lo, hi, hi - lo, v[0], v[-1]), flush=True)

    # ── ★ 핵심 판정 — 139 가 적은 「−71.4%」가 «분포의 어디»인가
    if base_all:
        base = st.median(base_all)
        print("\n  ★ **139 의 「현행 대비」를 «분포»로 다시 적으면** (기준 = 100% 칸 중앙 %.0f만)"
              % base, flush=True)
        for k in ("50%", "25%", "10%", "5%"):
            v = sorted(rows.get(k) or [])
            if not v:
                continue
            pct = [100.0 * (x - base) / base for x in v]
            worse = sum(1 for x in v if x < base)
            print("     %-5s  중앙 **%+.1f%%**  5~95%% [%+.1f%% ~ %+.1f%%]  ·"
                  " 현행보다 나쁜 판 **%d/%d**  ·  139 가 보고한 값 대비"
                  % (k, st.median(pct), pct[max(0, int(round(0.05 * (len(pct) - 1))))],
                     pct[min(len(pct) - 1, int(round(0.95 * (len(pct) - 1))))],
                     worse, len(v)), flush=True)

        print("\n  ★★ **매수 수 — 「후보를 줄여도 매수는 안 준다」가 «어디까지» 참인가**", flush=True)
        for k in ("100%", "50%", "25%", "10%", "5%"):
            v = rows.get(k + "|n") or []
            if v:
                print("     %-5s  매수 중앙 **%.0f건**  [%.0f ~ %.0f]"
                      % (k, st.median(v), min(v), max(v)), flush=True)

    bad = [f for f in GUARD if md5(REAL_OUT / f) != before[f]]
    print("\n확인 — 원본 %s: %s" % (GUARD, "그대로 OK" if not bad else "🚨 바뀜 %s" % bad),
          flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

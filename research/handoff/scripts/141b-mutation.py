# -*- coding: utf-8 -*-
r"""141b — **㉥ 돌연변이 시험.** 「같다」에 값이 생기게 하는 관문.

왜
--
㉠′ 가 「어긋난 필드 0」을 내도 그게 **「정말 같아서」인지 「비교기가 둔해서」인지 못 가른다.**
그래서 **일부러 한 곳을 망가뜨리고 ㉠′ 가 «실패하는지»** 본다 — 실패해야 「통과」가 의미를 갖는다.
(실패유형 24′: 「고쳤다」의 증거는 «고치기 전 상태가 실패하는지»를 보는 것.)

🚨 **㉠′ 판정을 «읽기 전»에 이걸 먼저 돌린다.** (두뇌 세션 지시)

무엇을 망가뜨리나 — **네 자리를 «따로»** 건드려 분해능을 각각 잰다
```
① c[0]  × 1.0001      가장 작은 가격 변화   ← 두뇌 세션이 지정한 것
② pivot × 1.0001      진입 기준가
③ d[0]  하루 밀기      날짜
④ 배열 순서 뒤집기     ㉦ 가 잡아야 한다
```

실행:
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/141b-mutation.py \
      --old .cache/bt5y/sub --new D:/stock-data/uspath-warm/test430 --year 2005
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATES = HERE / "141-warmup-gates.py"


def run_gates(old, new, year):
    """141 을 그대로 돌려 (통과했나, 출력) 을 낸다."""
    p = subprocess.run(
        [sys.executable, str(GATES), "--old", str(old), "--new", str(new),
         "--years", "%d-%d" % (year, year)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    return p.returncode == 0, (p.stdout or "") + (p.stderr or "")


def mutate(src, dst, how):
    pack = json.loads(Path(src).read_text(encoding="utf-8"))
    ps = pack["trigger_paths"]
    if how == "order":
        pack["trigger_paths"] = list(reversed(ps))
    else:
        # 값이 있는 «첫» 기록 하나만 건드린다
        for r in ps:
            if how == "c0" and r.get("c") and r["c"][0] is not None:
                r["c"][0] = r["c"][0] * 1.0001
                break
            if how == "pivot" and r.get("pivot"):
                r["pivot"] = r["pivot"] * 1.0001
                break
            if how == "d0" and r.get("d"):
                r["d"][0] = "1900-01-01"
                break
    Path(dst).write_text(json.dumps(pack, ensure_ascii=False, separators=(",", ":")),
                         encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default=".cache/bt5y/sub")
    ap.add_argument("--new", required=True)
    ap.add_argument("--year", type=int, required=True)
    a = ap.parse_args()
    src = Path(a.new) / ("uspath_%d.json" % a.year)
    if not src.exists():
        print("🚨 %s 가 없다" % src, flush=True)
        return 2

    print("=" * 92, flush=True)
    print("㉥ 돌연변이 시험 — **망가뜨리면 ㉠′ 가 «실패해야» 한다** (%d년)" % a.year, flush=True)
    print("=" * 92, flush=True)

    base_ok, base_out = run_gates(a.old, a.new, a.year)
    print("  ⓪ 손 안 댄 판          → %s"
          % ("**통과**" if base_ok else "미통과"), flush=True)
    if not base_ok:
        print("     🚨 손도 안 댔는데 미통과다. 돌연변이 시험 이전에 그것부터.", flush=True)
        for ln in base_out.splitlines():
            if "미통과" in ln or "어긋난" in ln or "예:" in ln:
                print("     | %s" % ln.strip(), flush=True)

    rows = []
    tmp = Path(tempfile.mkdtemp(prefix="141b_"))
    try:
        for how, lab in (("c0", "① c[0] × 1.0001"),
                         ("pivot", "② pivot × 1.0001"),
                         ("d0", "③ d[0] 를 1900-01-01 로"),
                         ("order", "④ 배열 순서 뒤집기")):
            d = tmp / how
            d.mkdir()
            mutate(src, d / ("uspath_%d.json" % a.year), how)
            ok, out = run_gates(a.old, d, a.year)
            # 망가뜨렸으니 **실패해야** 정상이다
            good = not ok
            rows.append((lab, ok, good, out))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    allgood = True
    for lab, ok, good, out in rows:
        allgood &= good
        hit = [ln.strip() for ln in out.splitlines()
               if ("미통과" in ln and ("㉠" in ln or "㉡" in ln or "㉦" in ln or "㉧" in ln))]
        print("  %-22s → 관문 %s  %s" % (lab, "통과(=못 잡음)" if ok else "**실패(=잡았다)**",
                                        "✅" if good else "🚨 **분해능 없음**"), flush=True)
        if hit:
            print("     | %s" % hit[0], flush=True)

    print("", flush=True)
    print("→ %s" % ("**돌연변이 넷을 다 잡았다.** ㉠′ 의 「통과」는 의미가 있다."
                    if allgood else
                    "🚨 **못 잡은 돌연변이가 있다. ㉠′ 의 「통과」를 믿지 말 것.**"), flush=True)
    return 0 if (allgood and base_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""㉠ — **순환 블록 재표집으로 58·59·60·61 을 다시 돌린다.**

왜 — `dataaxis._resample` 이 계열의 양 끝을 덜 뽑는다(검증 세션 발견, 두뇌 세션 실측).
     블록 80 에서 첫날·마지막날이 가운데의 **0.013배**, 옮겨간 무게 **3.64%**.
     74번에서 12칸 중 1칸의 「0 배제」가 **뒤집혔다**.

무엇을 보나 — **A 문턱은 전부 「하나라도 0 배제인가」**이고 넷 다 **미통과(전부 0 포함)**다.
     따라서 위험은 **「0 포함이 0 배제로 뒤집혀 미통과가 통과가 되는 것」**뿐이다.
     → 순환으로 돌려 **A 칸 중 0 을 배제하는 것이 «생기는지»만** 본다.

🚨 **기존 캐시를 덮지 않는다** — 임시 `OUT` 을 만들고 필요한 입력만 복사해 넣는다.
   (58~61 은 `26-eqw-us9y.json` · `38-indices.json` · `61-monthly-us.json` 을 읽는다.)

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
      python research/handoff/scripts/74v-cyclic-recheck.py [58|59|60|61]
"""
from __future__ import annotations

import importlib.util as _u
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataaxis as da                                    # noqa: E402

REAL_OUT = ROOT / ".cache" / "bt5y" / "out"
INPUTS = ("26-eqw-us9y.json", "38-indices.json", "61-monthly-us.json")
JOBS = {"58": "58-slot-count.py", "59": "59-regime-9y.py",
        "60": "60-regime-faithful.py", "61": "61-selection-leaders.py"}


def main() -> int:
    which = [a for a in sys.argv[1:] if a in JOBS]
    if not which:
        print("쓰기: 74v-cyclic-recheck.py 58|59|60|61")
        return 2
    if not hasattr(da, "CYCLIC"):
        print("🚨 dataaxis 에 CYCLIC 이 없다 — 두뇌 세션 커밋을 먼저 받아야 한다")
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="cyc_out_"))
    for f in INPUTS:
        src = REAL_OUT / f
        if src.exists():
            shutil.copy2(src, tmp / f)
    print("=" * 92)
    print("㉠ 순환 블록 재표집 재실행 — 대상 %s" % ", ".join(which))
    print("   임시 OUT = %s  (기존 캐시는 손대지 않는다)" % tmp)
    print("   CYCLIC[0] = True")
    print("=" * 92, flush=True)

    da.CYCLIC[0] = True
    for key in which:
        fn = JOBS[key]
        print("", flush=True)
        print("#" * 92, flush=True)
        print("# %s  (순환)" % fn, flush=True)
        print("#" * 92, flush=True)
        spec = _u.spec_from_file_location("job%s" % key, HERE / fn)
        mod = _u.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # 🚨 산출 경로를 임시로 돌린다 — «불러온 뒤» 바꿔야 모듈 상수가 갈린다
        mod.OUT = tmp
        if da.CYCLIC[0] is not True:
            print("🚨 CYCLIC 이 도중에 꺼졌다 — 중단", flush=True)
            return 1
        rc = mod.main()
        print("→ %s 반환값 %s · CYCLIC=%s" % (fn, rc, da.CYCLIC[0]), flush=True)
    # 유형 22 — 「덮지 않았다」를 «상태»에서 확인한다
    print("", flush=True)
    print("확인 — 임시 OUT 에 생긴 파일: %s"
          % sorted(p.name for p in tmp.iterdir() if p.name not in INPUTS), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

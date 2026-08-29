# -*- coding: utf-8 -*-
"""104v 1단계 — **A급 셋 + 74 의 12칸을 «순환 × 스트림 200» 으로 다시 돌린다.**

고침이 «둘»이다(판정 104 §3-2):
  ㉠ `CYCLIC[0] = True`     — 모든 날이 정확히 block 번 덮인다
  ㉡ `n_stream = 200`       — 순환 «단독»은 스트림 10 과 상호작용해 중앙을 옮긴다
                              (실측: 참값 −2.25% → 순환×10 중앙 +4.77~+7.27%)

🚨 `da.N_STREAM = 200` 으로는 «안 된다» — `band_total`/`band_paired` 의 기본 인자가
   **정의 시점에 묶여** 있다. 그래서 `da.sweep` 을 «감싸서» 강제로 넣는다.
   몬테카를로 예산은 같게: 10×100 = **200×5 = 1,000 값**.

🚨 기존 캐시를 덮지 않는다 — 임시 `OUT` 을 만들고 필요한 입력만 복사한다. 끝나고 md5 로 확인.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/104v-stage1-rerun.py [75|75a|77|74]
"""
from __future__ import annotations

import hashlib
import importlib.util as _u
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataaxis as da                                    # noqa: E402

REAL_OUT = ROOT / ".cache" / "bt5y" / "out"
JOBS = {"75": "75-livermore.py", "75a": "75a-mde.py",
        "77": "77-minervini.py", "74": "74-pyramid-rebuilt.py",
        # ── 2단계 B급 — 코드는 «찍기»만 하나 결과 문서가 그 수를 «인용»한다
        "76": "76-exit-x-pyramid.py", "78": "78-source-quotes.py",
        "79": "79-stop-and-band.py", "79b": "79b-lower-band.py",
        "80b": "80b-longer-exits.py"}
INPUTS = ("26-eqw-us9y.json", "26-eqw-us.json", "38-indices.json",
          "61-monthly-us.json", "74-pyramid-rebuilt.json", "75-livermore.json")

N_STREAM, N_REP = 200, 5


def wrap_sweep():
    """`sweep` 을 감싸 «스트림 200 × 재표집 5» 를 강제한다 (예산은 그대로 1,000)."""
    orig = da.sweep

    def forced(curves_v, curves_0=None, blocks=da.BLOCKS, n_stream=None, n_rep=None):
        return orig(curves_v, curves_0, blocks, N_STREAM, N_REP)
    forced.__name__ = "sweep_forced_200x5"
    da.sweep = forced
    return orig


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None


def main() -> int:
    which = [a for a in sys.argv[1:] if a in JOBS]
    if not which:
        print("쓰기: 104v-stage1-rerun.py 75|75a|77|74")
        return 2

    before = {f: md5(REAL_OUT / f) for f in INPUTS}
    tmp = Path(tempfile.mkdtemp(prefix="cyc200_"))
    for f in INPUTS:
        src = REAL_OUT / f
        if src.exists():
            shutil.copy2(src, tmp / f)

    da.CYCLIC[0] = True
    wrap_sweep()
    print("=" * 96, flush=True)
    print("104v 1단계 — 순환 × 스트림 %d (재표집 %d · 예산 %d)"
          % (N_STREAM, N_REP, N_STREAM * N_REP), flush=True)
    print("   대상 %s · 임시 OUT %s" % (", ".join(which), tmp), flush=True)
    print("   🚨 CYCLIC=%s · sweep=%s" % (da.CYCLIC[0], da.sweep.__name__), flush=True)
    print("=" * 96, flush=True)

    for key in which:
        fn = JOBS[key]
        print("\n" + "#" * 96, flush=True)
        print("# %s  (순환 × 200)" % fn, flush=True)
        print("#" * 96, flush=True)
        spec = _u.spec_from_file_location("job%s" % key, HERE / fn)
        mod = _u.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "OUT"):
            mod.OUT = tmp
        # 🚨 관문 — 모듈이 «자기» dataaxis 를 따로 들고 있지 않은지
        mda = getattr(mod, "da", None)
        if mda is not None and (mda.CYCLIC[0] is not True
                                or getattr(mda.sweep, "__name__", "") != "sweep_forced_200x5"):
            print("🚨 모듈의 dataaxis 가 «다른 객체»다 — 패치가 안 먹었다. 중단", flush=True)
            return 1
        rc = mod.main()
        print("→ %s 반환 %s" % (fn, rc), flush=True)

    print("\n확인 — 원본 캐시 md5", flush=True)
    bad = [f for f in INPUTS if md5(REAL_OUT / f) != before[f]]
    print("   %d/%d 그대로 · %s"
          % (len(INPUTS) - len(bad), len(INPUTS), "OK" if not bad else "🚨 바뀜 %s" % bad),
          flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

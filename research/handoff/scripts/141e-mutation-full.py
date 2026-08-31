# -*- coding: utf-8 -*-
r"""141e — **㉥ 돌연변이, «전 구간» 판.**

왜 141b 를 못 쓰나
------------------
141b 는 **한 해**만 대조한다. 그런데 141 의 회귀 기준선(`A_EXPECT` 등)은 **28년 전체**의 값이라
한 해만 돌리면 **손 안 댄 판(⓪)부터 미통과**가 난다.
→ 그러면 돌연변이가 「망가뜨려서」 실패한 건지 「기준선이 안 맞아서」 실패한 건지 **못 가른다.**
   **관문이 무엇을 잡았는지 증명이 안 된다** (실패유형 24′ 그대로).

그래서 여기서는 **전 구간(1999~2026)**을 대조한다.
4.86GB 를 복사하지 않으려고 **하드링크로 그림자 디렉터리**를 만들고, 한 해만 진짜 사본으로 바꾼다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/141e-mutation-full.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GATES = HERE / "141-warmup-gates.py"
OLD = ".cache/bt5y/sub"
NEW = Path("D:/stock-data/uspath-warm/full")
YEAR = 2015                     # 돌연변이를 심을 해


def shadow(dst):
    """진짜 파일을 «하드링크»로 걸어 둔다 — 4.86GB 를 복사하지 않는다."""
    dst.mkdir(parents=True, exist_ok=True)
    for f in NEW.glob("uspath_*.json"):
        try:
            os.link(f, dst / f.name)
        except OSError:
            shutil.copy2(f, dst / f.name)
    return dst


def mutate(src, dst, how):
    pack = json.loads(Path(src).read_text(encoding="utf-8"))
    ps = pack["trigger_paths"]
    if how == "order":
        pack["trigger_paths"] = list(reversed(ps))
    else:
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
            if how == "drop1" and True:
                pack["trigger_paths"] = ps[:-1]      # 한 건 «지운다»
                break
            if how == "prev1" and r.get("pre_c") and r["pre_c"][-1] is not None:
                r["pre_c"][-1] = r["pre_c"][-1] * 1.0001   # 진입 «전» 마지막 봉
                break
    Path(dst).write_text(json.dumps(pack, ensure_ascii=False, separators=(",", ":")),
                         encoding="utf-8")


def run(newdir):
    p = subprocess.run(
        [sys.executable, str(GATES), "--old", OLD, "--new", str(newdir),
         "--years", "1999-2026"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    return p.returncode == 0, (p.stdout or "")


def main() -> int:
    print("=" * 92, flush=True)
    print("㉥ 돌연변이 — **전 구간(1999~2026)**. 「고정된 관문」이 «실패할 수 있는가»", flush=True)
    print("=" * 92, flush=True)

    ok0, out0 = run(NEW)
    print("  ⓪ 손 안 댄 판 (진짜 산출) → %s"
          % ("**통과**" if ok0 else "🚨 미통과"), flush=True)
    if not ok0:
        for ln in out0.splitlines():
            if "달라" in ln or "미통과" in ln:
                print("     | %s" % ln.strip(), flush=True)
        print("     🚨 기준선부터 안 맞는다. 돌연변이 시험 이전에 그것부터.", flush=True)
        return 2

    rows = []
    tmp = Path(tempfile.mkdtemp(prefix="141e_", dir="D:/stock-data"))
    try:
        sd = shadow(tmp / "shadow")
        src = NEW / ("uspath_%d.json" % YEAR)
        tgt = sd / ("uspath_%d.json" % YEAR)
        for how, lab in (("c0", "① c[0] × 1.0001 (진입 «후» 가격)"),
                         ("prev1", "② pre_c[-1] × 1.0001 (진입 «전» 가격)"),
                         ("pivot", "③ pivot × 1.0001"),
                         ("d0", "④ d[0] 를 1900-01-01 로"),
                         ("drop1", "⑤ 경로 한 건 «지우기»"),
                         ("order", "⑥ 배열 순서 뒤집기")):
            tgt.unlink(missing_ok=True)
            mutate(src, tgt, how)
            ok, out = run(sd)
            good = not ok
            hit = next((ln.strip() for ln in out.splitlines()
                        if "달라" in ln or "«왜인지»" in ln), "")
            rows.append((lab, ok, good, hit))
            print("  %-34s → %s  %s" % (lab, "통과(=못 잡음)" if ok else "**실패(=잡았다)**",
                                        "✅" if good else "🚨 **분해능 없음**"), flush=True)
            if hit:
                print("     | %s" % hit[:120], flush=True)
            # 다음 판을 위해 원래 파일로 되돌린다
            tgt.unlink(missing_ok=True)
            try:
                os.link(src, tgt)
            except OSError:
                shutil.copy2(src, tgt)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    allgood = all(g for _l, _o, g, _h in rows)
    print("", flush=True)
    print("→ %s" % ("**여섯을 다 잡았다.** 고정된 관문의 「통과」에 값이 있다."
                    if allgood else "🚨 **못 잡은 돌연변이가 있다. 「통과」를 믿지 말 것.**"),
          flush=True)
    return 0 if allgood else 1


if __name__ == "__main__":
    raise SystemExit(main())

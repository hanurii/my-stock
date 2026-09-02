# -*- coding: utf-8 -*-
"""_runv.py — **검사하고 «나서» 돌린다.**

★ 오늘 남은 구멍: 「관문은 «산출물»에 걸리고 «작업 도구»엔 안 걸린다」.
  판정을 «계산하는» 스크립트도, 패치 스크립트도 검사 «밖»에 있었고 둘 다 터졌다.
  이 감싸개는 «어디에 있든» 돌리기 «직전»에 검사한다 — 파일 위치에 안 기댄다.

  쓰기:  python _runv.py <스크립트.py> [인자…]

검사 셋:
  ① 서식      `_fmtcheck` — %-서식과 «맨 문자열의 %%»
  ② 컴파일    SyntaxError
  ③ 🆕 «정의 전 사용»  모듈 수준에서 «아직 안 묶인» 이름을 읽는가
       (`_fmtcheck` 가 «못» 잡아 «돌려서» 잡혔던 그 결함 — md/sdd)

⚠️ 이 감싸개의 «한계»를 먼저 적는다(유형 44·60):
  · ③은 **모듈 수준만** 본다. 함수 «안»의 정의 전 사용은 못 본다
  · ③은 **분기·반복을 안 본다** — `if` 안에서만 묶이는 이름을 «묶였다»고 본다(위음성 쪽)
  · «논리»는 아무것도 안 본다. 통과는 「이 셋으로는 안 틀렸다」일 뿐이다
"""
from __future__ import annotations

import ast
import builtins
import runpy
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def undefined_at_module_level(src: str, path: str):
    """모듈 수준에서 «묶이기 전»에 읽히는 이름들."""
    tree = ast.parse(src, filename=path)
    bound: set[str] = set(dir(builtins)) | {"__name__", "__file__", "__doc__"}
    bad: list[tuple[int, str]] = []

    def bind(node):
        for t in ast.walk(node):
            if isinstance(t, ast.Name) and isinstance(t.ctx, (ast.Store, ast.Del)):
                bound.add(t.id)
            elif isinstance(t, (ast.alias,)):
                bound.add((t.asname or t.name).split(".")[0])

    for stmt in tree.body:
        # 먼저 «읽기»를 본다 — 같은 문장 안의 묶기는 오른쪽이 먼저이므로
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for n in ast.walk(stmt):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in bound:
                    bad.append((n.lineno, n.id))
        # 그 다음 이 문장이 «묶는» 것을 등록
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(stmt.name)
        else:
            bind(stmt)
    return bad


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = Path(sys.argv[1]).resolve()
    if not target.is_file():
        print("🚨 파일 없음 — %s" % target)
        return 2
    src = target.read_text(encoding="utf-8")

    print("=" * 88)
    print("_runv — **검사하고 «나서» 돌린다** · 대상 `%s`" % target.name)
    print("=" * 88)

    fail = []

    # ① 서식
    fc = HERE / "_fmtcheck.py"
    if fc.is_file():
        r = subprocess.run([sys.executable, str(fc), str(target)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            print("  ✅ ① 서식(`_fmtcheck`)")
        else:
            print("  🚨 ① 서식 — 미통과")
            print((r.stdout or "").rstrip())
            fail.append("서식")
    else:
        print("  ⚠️ ① `_fmtcheck.py` 를 못 찾음 — **이 검사를 «안 했다»**")

    # ② 컴파일
    try:
        compile(src, str(target), "exec")
        print("  ✅ ② 컴파일")
    except SyntaxError as e:
        print("  🚨 ② 컴파일 — line %s: %s" % (e.lineno, e.msg))
        fail.append("컴파일")

    # ③ 정의 전 사용
    if "컴파일" not in fail:
        bad = undefined_at_module_level(src, str(target))
        if not bad:
            print("  ✅ ③ 정의 전 사용(모듈 수준)")
        else:
            print("  🚨 ③ **정의 전 사용** — 모듈 수준에서 «묶이기 전»에 읽는다")
            for ln, name in bad[:12]:
                print("       line %-5d `%s`" % (ln, name))
            fail.append("정의 전 사용")

    if fail:
        print("\n  ⛔ **미통과(%s) — 돌리지 «않는다»**" % " · ".join(fail))
        print("  ★ 맞추지 말고 «왜»부터. 그리고 이 검사는 «논리»를 «안» 본다")
        print("=" * 88)
        return 1

    print("\n  ▶ 검사 통과 — 돌린다")
    print("=" * 88, flush=True)
    sys.argv = sys.argv[1:]
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

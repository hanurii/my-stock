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
  · ③은 **겹문장(for/if/while/with/try) «안»의 순서를 안 본다** — 그 안의 모든 묶기를
    «먼저» 인정한다. 오탐 0 을 얻는 대신 「반복문 «안»의 정의 전 사용」은 «못» 잡는다(위음성 쪽)
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


def _stores(node):
    """이 노드가 «묶는» 이름들."""
    out = set()
    for t in ast.walk(node):
        if isinstance(t, ast.Name) and isinstance(t.ctx, (ast.Store, ast.Del)):
            out.add(t.id)
        elif isinstance(t, ast.alias):
            out.add((t.asname or t.name).split(".")[0])
        elif isinstance(t, ast.ExceptHandler) and t.name:
            out.add(t.name)
    return out


def _prebound(stmt):
    """«읽기»를 보기 «전»에 묶어야 하는 것 —
    for 목표 · with as · 내포 표현식 변수 · except as. (안 하면 «오탐»이 난다)"""
    out = set()
    for n in ast.walk(stmt):
        if isinstance(n, (ast.For, ast.AsyncFor)):
            out |= _stores(n.target)
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            out |= _stores(n.optional_vars)
        elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for g in n.generators:
                out |= _stores(g.target)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, ast.Lambda):
            out |= {a.arg for a in n.args.args + n.args.posonlyargs + n.args.kwonlyargs}
            if n.args.vararg:
                out.add(n.args.vararg.arg)
            if n.args.kwarg:
                out.add(n.args.kwarg.arg)
    return out


def undefined_at_module_level(src: str, path: str):
    """모듈 수준에서 «묶이기 전»에 읽히는 이름들.

    ⚠️ 오탐을 막으려고 for 목표 · with as · 내포 변수 · except as · lambda 인자를
       «먼저» 묶는다. 그래도 «분기 안에서만» 묶이는 이름은 «묶였다»고 본다(위음성 쪽).
    """
    tree = ast.parse(src, filename=path)
    bound = set(dir(builtins)) | {"__name__", "__file__", "__doc__", "__spec__", "__package__"}
    bad = []
    seen = set()

    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(stmt.name)
            continue
        # 🚨 «겹문장»(for/while/if/with/try)은 «안»의 순서를 이 검사가 못 따라간다.
        #    그래서 그 안의 «모든» 묶기를 «먼저» 인정한다 — 오탐을 없애는 대신
        #    「반복문 «안»의 정의 전 사용」은 «못» 잡는다(위음성 쪽. 한계에 적었다).
        COMPOUND = (ast.For, ast.AsyncFor, ast.While, ast.If, ast.With,
                    ast.AsyncWith, ast.Try, ast.Match) if hasattr(ast, "Match") else (
                    ast.For, ast.AsyncFor, ast.While, ast.If, ast.With, ast.AsyncWith, ast.Try)
        local = bound | _prebound(stmt)
        if isinstance(stmt, COMPOUND):
            local |= _stores(stmt)
        for n in ast.walk(stmt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in local:
                if (n.lineno, n.id) not in seen:
                    seen.add((n.lineno, n.id))
                    bad.append((n.lineno, n.id))
        bound |= _stores(stmt)
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

# -*- coding: utf-8 -*-
"""연구 스크립트 «저장 즉시» 검사 — PostToolUse(Edit|Write).

★ 왜 있나: `_runv.py` 가 직접 적어 둔 구멍 —
  「관문은 «산출물»에 걸리고 «작업 도구»엔 안 걸린다」.
  `_runv.py` 는 «돌릴 때» 검사한다. 이 훅은 «저장할 때» 검사한다.
  몇 시간짜리 백테스트를 돌린 «뒤에» %-서식으로 터지는 것을 앞당겨 잡는다.

검사 둘(«돌리지 않는다» — 훅이 백테스트를 돌리면 안 된다):
  ① 컴파일    SyntaxError
  ② 서식      `research/handoff/scripts/_fmtcheck.py`

⚠️ 한계:
  · `_runv.py` 의 ③ «정의 전 사용»은 «안» 한다(그건 모듈을 실제로 훑어야 한다)
  · 통과는 「이 둘로는 안 틀렸다」일 뿐이다. 논리는 아무것도 안 본다
  · 그러니 이 훅이 «`_runv.py` 를 대신하지 않는다». 돌릴 땐 그대로 `_runv.py` 를 쓴다
"""
import json
import os
import subprocess
import sys

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FMTCHECK = os.path.join(ROOT, "research", "handoff", "scripts", "_fmtcheck.py")
WATCH = ("research/handoff/scripts/", "scripts/")


def blocked(msg):
    print(json.dumps({"decision": "block", "reason": msg}, ensure_ascii=False))
    return 0


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    ti = data.get("tool_input") or {}
    tr = data.get("tool_response") or {}
    path = tr.get("filePath") or ti.get("file_path") or ""
    if not path.endswith(".py"):
        return 0
    norm = path.replace("\\", "/")
    if not any(w in norm for w in WATCH):
        return 0
    if not os.path.isfile(path):
        return 0

    # ① 컴파일 (파일을 쓰지 않는다 — __pycache__ 를 안 남긴다)
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        compile(src, path, "exec")
    except SyntaxError as e:
        return blocked(
            "🚨 저장 관문 ① 컴파일 실패 — %s\n  line %s: %s\n"
            "고치고 다시 저장해라." % (os.path.basename(path), e.lineno, e.msg))
    except Exception:
        return 0  # 못 읽으면 «막지 않는다»

    # ② 서식 (%-서식과 맨 문자열의 %%)
    if not os.path.isfile(FMTCHECK):
        return 0
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        r = subprocess.run([sys.executable, FMTCHECK, path],
                           capture_output=True, timeout=20, env=env)
    except Exception:
        return 0
    if r.returncode != 0:
        out = (r.stdout or b"").decode("utf-8", "replace").strip()
        return blocked(
            "🚨 저장 관문 ② 서식(`_fmtcheck`) 실패 — %s\n%s\n"
            "이대로 돌리면 «찍는 순간» 터진다. 고치고 다시 저장해라."
            % (os.path.basename(path), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

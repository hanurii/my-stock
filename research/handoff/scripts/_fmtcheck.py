# -*- coding: utf-8 -*-
"""🚨 133 교훈 — «파일 안의 모든» 서식 문자열을 «실제로» 찍어 본다."""
import ast, sys, re
src = open(sys.argv[1], encoding="utf-8").read()
tree = ast.parse(src)
bad = 0
for node in ast.walk(tree):
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)):
        continue
    left = node.left
    # 문자열 리터럴(암시 이어붙임 포함)만
    try:
        s = ast.literal_eval(left)
    except Exception:
        continue
    if not isinstance(s, str) or "%" not in s:
        continue
    n = len(re.findall(r"%[-+ #0]*[0-9.*]*[diouxXeEfFgGcrsa]", s))
    try:
        s % (tuple([1.0] * n) if n else ())
    except Exception as e:
        bad += 1
        print("  🚨 line %-4d %s" % (node.lineno, s[:70].replace("\n", " ")))
        print("       %r" % (e,))

# ── 🚨 유형 48 후속(검증 세션 26-09-01) — «맨» 문자열의 %% 는 «아무도 안 봤다» ──────────
#   「생성」은 «전사»를 없애지 «읽기»를 없애지 않는다. 서식이 «안» 걸린 문자열에서
#   %% 를 쓰면 그대로 새어 나간다. 위 검사는 %-BinOp 만 보므로 여기를 못 본다.
fmt_nodes = {id(n.left) for n in ast.walk(tree)
             if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod)}
# 🚨 오탐 둘 — 26-09-02 실측으로 나왔다:
#   ① 문자열 «자체»가 "%%" 인 것 = «검색어»이지 «출력»이 아니다 (이 파일 스스로가 걸렸다)
#   ② `.replace("%%", "%")` 로 «이미 우회»한 것 — 출력은 옳다 (147:285 가 그랬다)
#   ⇒ 둘을 빼지 않으면 «고칠 필요 없는 곳»을 고치게 된다
repl_args = set()
for n in ast.walk(tree):
    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "replace"):
        for a in n.args:
            repl_args.add(id(a))
        if isinstance(n.func.value, ast.Constant):
            repl_args.add(id(n.func.value))
leak = 0
for node in ast.walk(tree):
    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
        continue
    if (id(node) in fmt_nodes or id(node) in repl_args
            or node.value.strip() == "%%" or "%%" not in node.value):
        continue
    leak += 1
    print("  🚨 line %-4d 서식 «안» 걸린 문자열에 %%%% — 그대로 새어 나간다"
          % (node.lineno,))
    print("       %r" % (node.value[:70],))
print("%%%% 누출 검사 — 문제 **%d개**" % leak)
bad += leak

print("서식 검사 — 문제 **%d개**" % bad)
sys.exit(1 if bad else 0)

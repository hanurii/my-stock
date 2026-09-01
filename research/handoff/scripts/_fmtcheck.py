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
print("서식 검사 — 문제 **%d개**" % bad)
sys.exit(1 if bad else 0)

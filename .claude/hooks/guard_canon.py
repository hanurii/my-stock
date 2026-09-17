# -*- coding: utf-8 -*-
"""정본 파일 편집 관문 — PreToolUse(Edit|Write|NotebookEdit).

★ 왜 있나: 이 저장소에는 «고치면 조용히 무너지는» 파일이 있다.
  사람 주의력으로는 «모르고» 고치는 것을 못 막는다. 그래서 기계가 막는다.

  deny = 아예 막는다(사고 기록이 있는 것)
  ask  = 사용자에게 물어본다(규약이라 «알고» 고칠 수는 있는 것)

⚠️ 한계를 먼저 적는다:
  · 경로로만 판단한다. «무엇을» 바꾸는지는 안 본다
    (scorecard-fills.json 에 «끝에 append» 하는 정당한 편집도 함께 막힌다 —
     그때는 Bash 로 쓰거나 이 파일에서 잠시 빼라)
  · Bash 로 쓰는 것(`python ... > 파일`)은 «못» 막는다. Edit/Write 도구만 본다
"""
import json
import sys

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

# 관문에서 «빼는» 것 — 여러 세션이 «함께» 쓰기로 «정한» 파일.
# ★ RULES 보다 «먼저» 본다(아래 RULES 의 넓은 규칙에 걸리는 것을 되돌리는 자리라 순서가 뜻이다).
# (경로 조각, 이유)
EXEMPT = [
    ("research/handoff/verdicts/_no-cite.md",
     "인용 금지 «등재부» — 조사·검증·두뇌가 «함께» 쓴다(사용자 결정 2026-09-10).\n"
     "verdicts/ 관문의 «뜻»은 「검증 세션의 «판정문»을 남이 «덮지» 않게」이고,\n"
     "이 파일은 «판정문»이 아니라 «공용 등재부»라 그 뜻에 «안» 걸린다.\n"
     "판마다 늘어나므로 «매번» 묻는 것이 «일»만 늘렸다."),
]

# (경로 조각, 접두사인가, 판정, 이유)
RULES = [
    ("public/data/scorecard-fills.json", False, "deny",
     "이 파일은 «배열 순서 자체가 자료»다(장중 체결 순서 정본).\n"
     "2026-08-21 에 재정렬해서 정산표 왕복이 63 → 43 건으로 조용히 무너진 «실사고»가 있다.\n"
     "추가는 «끝에 append» 만(indent=1 · 키 순서 유지), 갱신 뒤 보유점검 재실행."),

    ("scripts/canslim_lib/strategy_params.py", False, "deny",
     "매매값 «정본» 파일이다 — «한국» 시장. 손익비(현재 +20/-10)·슬롯 수는\n"
     "«사용자 결정»이고 커밋 번호가 붙는다(직전: 2026-09-17, 익절 +30 → +20 되돌림).\n"
     "여기 수를 바꾸려면 «사용자에게 물어서» 결정과 근거를 받은 뒤에 바꾼다.\n"
     "⛔ 미국 판에서 나온 값을 여기 옮기지 않는다 — 한국 값은 한국 근거로 선다(헌법 §0)."),

    ("research/handoff/verdicts/", True, "ask",
     "`verdicts/` 는 «검증 세션»이 쓰는 곳이다(두뇌는 tasks/, 조사는 results/).\n"
     "지금 세션이 검증 세션이 «맞다면» 승인해라. 아니면 취소하고 파일로 넘겨라."),
]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # 입력을 못 읽으면 «막지 않는다»(관문이 작업을 세우면 안 된다)

    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path:
        return 0
    norm = path.replace("\\", "/").lower()

    for frag, reason in EXEMPT:
        if norm.endswith(frag):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "✅ 관문 «면제» — %s\n\n%s" % (frag, reason),
                }
            }, ensure_ascii=False))
            return 0

    for frag, is_prefix, decision, reason in RULES:
        f = frag.lower()
        hit = (f in norm) if is_prefix else norm.endswith(f)
        if not hit:
            continue
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": "🛑 정본 파일 — %s\n\n%s" % (frag, reason),
            }
        }, ensure_ascii=False))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

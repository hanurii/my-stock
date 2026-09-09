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

# (경로 조각, 접두사인가, 판정, 이유)
RULES = [
    ("public/data/scorecard-fills.json", False, "deny",
     "이 파일은 «배열 순서 자체가 자료»다(장중 체결 순서 정본).\n"
     "2026-08-21 에 재정렬해서 정산표 왕복이 63 → 43 건으로 조용히 무너진 «실사고»가 있다.\n"
     "추가는 «끝에 append» 만(indent=1 · 키 순서 유지), 갱신 뒤 보유점검 재실행."),

    ("scripts/canslim_lib/strategy_params.py", False, "deny",
     "매매값 «정본» 파일이다. 손익비(현재 +30/-10)·슬롯 수는 «사용자 결정»이고\n"
     "커밋 번호가 붙는다(직전: 41db459d, 2026-09-02).\n"
     "여기 수를 바꾸려면 «사용자에게 물어서» 결정과 근거 번호를 받은 뒤에 바꾼다."),

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

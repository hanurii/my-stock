# -*- coding: utf-8 -*-
"""작업 트리를 «지우는» git 명령 관문 — PreToolUse(Bash).

★ 왜 있나 (2026-09-11 실사고):
  하청이 제 시험 자국을 지우려고 `git checkout -- scripts/screen_trend_template.py` 를 돌렸다.
  그 파일에는 «남의» 미커밋 작업(주석 세 줄)이 «이미» 있었고, `git checkout --` 는
  «파일 전체»를 HEAD 로 되돌리므로 그것까지 «같이» 지웠다.
  되찾은 것은 «운»이었다 — 하청이 «우연히** `cp ... /tmp/...bak` 을 먼저 해 뒀다.
  ⇒ 운에 기대지 않게 «막는다».

★ 처방의 핵심: 「되돌리지 마라」가 아니라 **「네가 뜬 사본에서 되돌려라」**.
  자기가 만든 자국만 지우려면 `cp` 로 뜬 사본을 되쓰면 된다. 그러면 남의 것은 안 건드린다.

⚠️ 한계:
  · 글자만 본다. 변수에 담아 돌리거나(`$CMD`) 스크립트 안에 숨기면 «못» 막는다
  · 미커밋 변경이 «있는지»는 안 본다 — 깨끗한 파일을 되돌리는 «무해»한 경우도 함께 막힌다
  · «명령문의 글자»만 보므로 실제로 되돌리지 «않는» 명령도 걸린다.
    시험 각본에 그 글자를 그대로 적으면 «그 각본»이 걸린다(2026-09-11 에 실제로 걸렸다).
    ⇒ 이 훅을 «시험»할 때는 패턴 글자를 명령문에 «적지 말고» 파일에서 읽어 넘겨라.

★ 판정은 «deny» 다 (사용자 결정 2026-09-11).
  처음엔 ask 였는데 «하청»은 그 물음에 답할 수 «없어» 물음이 «전부» 사용자에게 올라갔다.
  막으려던 것은 막았지만 «비용»을 엉뚱한 사람이 냈다.
  deny 면 하청이 사람을 «안» 거치고 바로 거절을 받아 위 「사본」 길로 돌아선다.
  ⇒ 사람이 «정말» 이 명령을 써야 하면 `.claude/settings.json` 의 PreToolUse 에서
    이 훅 줄을 «잠시» 빼고 쓴 뒤 되돌린다. 「다시 묻지 않기」로 «통째로» 풀지 말 것.
"""
import json
import re
import sys

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

# (정규식, 무엇인가)
PATTERNS = [
    (r"\bgit\s+checkout\s+--\s", "git checkout -- <경로>"),
    (r"\bgit\s+restore\b(?!.*--staged)", "git restore <경로>"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\bgit\s+clean\s+-[a-z]*f", "git clean -f"),
]

REASON = (
    "🛑 작업 트리를 «지우는» git 명령 — %s\n\n"
    "이 명령은 «파일 전체»를 되돌린다. 그 파일에 «남의» 미커밋 작업이 있으면 «그것까지» 지운다.\n"
    "2026-09-11 에 실제로 그렇게 주석 세 줄이 사라졌고, 되찾은 건 «운»이었다.\n\n"
    "★ 네가 «만든» 자국만 지우려면:\n"
    "   1) 고치기 «전»에  cp <파일> <파일>.bak\n"
    "   2) 되돌릴 때     cp <파일>.bak <파일>\n"
    "   이러면 남의 미커밋 작업은 «안» 건드린다.\n\n"
    "★ 사본을 «안» 떠 뒀다면 «먼저»  git diff -- <파일>  로 «무엇이» 사라질지 보고,\n"
    "   그 내용을 어딘가에 «적어» 둔 뒤에 승인을 받아라.\n\n"
    "⛔ 이 관문은 «사람에게 묻지 않고» 막는다(deny). 위 「사본」 길로 가라.\n"
    "   그 길이 «정말» 안 되면, 부르는 쪽에 «무엇이 사라질지»를 적어 보고하고 지시를 받아라."
)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # 입력을 못 읽으면 «막지 않는다»(관문이 작업을 세우면 안 된다)

    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    for pat, label in PATTERNS:
        if re.search(pat, cmd):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": REASON % label,
                }
            }, ensure_ascii=False))
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

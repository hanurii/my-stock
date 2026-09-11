# -*- coding: utf-8 -*-
"""Sharadar 마감 알림 — SessionStart.

★ 왜 있나: Sharadar 결제가 2026-09 로 끝난다(사용자, 2026-09-10).
  10월이면 1999~2016 원가격을 «다시» 받을 길이 «영영» 없어진다.
  사용자가 「잊어버릴 수도 있다」고 하셨고 — 적어 두는 것은 «막지» 못한다.
  그래서 세션이 열릴 때마다 «기계»가 본다.

  판단은 «파일 시각»으로만 한다(zip 을 여는 것은 21초라 세션 시작에 못 쓴다).
  받으면 시각이 갱신되어 «저절로» 꺼진다.

⚠️ 한계: 「받았다」가 아니라 「파일이 «새것»이다」만 본다.
  full history 를 받았는지 «내용»은 «안» 본다.
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 자료가 C 에 안 들어가 D 로 옮겼다(2026-09-10). us_loader.py:59 와 같은 차례로 본다.
# SHARADAR_DIR 로 덮어쓸 수 있다.
_env = os.environ.get("SHARADAR_DIR")
_CANDS = ([Path(_env)] if _env else
          [Path(r"D:/stock-data/sharadar"),
           Path(__file__).resolve().parents[2] / ".cache" / "sharadar"])
LAST_MONTH = date(2026, 9, 30)      # 결제 마지막 달의 끝
NAG_FROM = date(2026, 9, 24)        # 이때부터 알린다


def newest_mtime():
    """어느 자리든 제일 새로운 stocks 파일의 날짜. 날짜 붙은 보관본도 함께 본다."""
    days = []
    for c in _CANDS:
        for p in c.glob("stocks*.csv.zip"):
            days.append(date.fromtimestamp(p.stat().st_mtime))
    return max(days) if days else None


def main():
    today = date.today()
    if today < NAG_FROM:
        return 0
    got = newest_mtime()
    if got and got >= NAG_FROM:
        return 0                     # 마감 주에 이미 받았다 — 조용히

    left = (LAST_MONTH - today).days
    if left >= 0:
        head = f"Sharadar 마지막 내려받기까지 {left}일 남았습니다 (마감 {LAST_MONTH})."
    else:
        head = f"Sharadar 결제가 {LAST_MONTH} 로 끝났습니다 ({-left}일 지남)."
    body = (
        f"{head}\n"
        f"  마지막으로 받은 날: {got or '없음'}\n"
        "  받을 것: stocks (full history 1999~) · tickers  →  .cache/sharadar/\n"
        "    시세 파일 이름을 stocks.csv.zip 으로 두면 코드가 그것을 먼저 읽습니다.\n"
        "  왜: 10월이면 1999~2016 원가격을 다시 받을 길이 없습니다.\n"
        "      그리고 뼈대가 늦게 끝날수록 야후로 이어 붙일 구간이 짧아집니다.\n"
        "      (오늘 갱신 한 번이 이음매 분할을 29개에서 1개로 줄였습니다.)"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": body,
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

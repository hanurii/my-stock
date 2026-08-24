# -*- coding: utf-8 -*-
"""자료 기준일 복원 — **「이 문서의 숫자는 어느 시점의 자료로 쟀나」**

왜 필요한가
-----------
pdata 는 **매 영업일 자란다.** 그래서 같은 스크립트를 다른 날 돌리면 마지막 해의
거래일 수와 값이 달라진다. **「기간」만 적어서는 재현이 안 된다.**
「어느 시점의 자료로 잰 기간인가」를 함께 적어야 한다.

🚨 **왜 「창 끝날짜」를 쓰면 안 되는가 — 실측으로 기각됐다**
  문서 11개가 창을 **「~ 2026-08-21」** 이라 적었다. 그런데 **2026-08-21 자료는
  2026-08-24 20:00 에야 들어왔다**(`price_20260821.json` 생성 시각).
  → **창 끝은 «명령줄에 지정한 값»이지 «자료가 거기까지 있었다»는 뜻이 아니다.**
  → 창 끝으로 라벨하면 **자료가 없던 날짜를 자료 기준일로 적게 된다.**

어떻게 복원하나
---------------
  자료 기준일 = **그 문서의 마지막 커밋 시각에 pdata 에 «이미 있던» 가장 늦은 거래일**
  - 커밋 시각: `git log -1 --format=%ad -- <파일>`
  - 있었는지: `price_YYYYMMDD.json` 의 **mtime ≤ 커밋 시각**

⚠️ **한계 둘 (숫자를 믿기 전에 읽는다)**
  1. mtime 은 **「마지막으로 손댄 시각」**이다. 실제로 1,629개 중 **97.9%가
     2026-07-07~08 에 몰려 있다**(과거 일괄 백필). 그래서 「이 날짜가 언제 처음
     생겼나」는 못 준다. **하지만 우리가 묻는 건 «앞끝»뿐이고, 앞끝 파일들은
     날마다 하나씩 붙어 진짜 시각을 갖고 있다.**
  2. 캐시를 백업에서 되살리면 mtime 이 **앞으로** 밀린다 → 앞끝을 **더 이르게**
     본다 = **보수적**이다. 틀리는 방향이 안전한 쪽이다.

★ **이번 실행이 특히 견고한 이유**: 앞끝이 **2026-08-21 16:09 부터 2026-08-24 20:00
   까지 줄곧 `2026-08-20` 이었다.** 모든 결과 문서의 커밋이 그 사이에 있다.
   → **그 안에서 언제 계산했든 답이 같다.** 상한이 아니라 **확정에 가깝다.**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/_asof_recover.py
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PDATA = ROOT / ".cache" / "pdata"
RESULTS = ROOT / "research" / "handoff" / "results"


def pdata_touches():
    """[(mtime, 'YYYYMMDD')] — pdata 각 거래일 파일을 마지막으로 손댄 시각."""
    out = []
    for f in PDATA.glob("price_*.json"):
        m = re.search(r"(\d{8})", f.name)
        if m:
            out.append((dt.datetime.fromtimestamp(f.stat().st_mtime), m.group(1)))
    out.sort()
    return out


def frontier(touches, when):
    """`when` 시점에 **이미 있던** 거래일 중 가장 늦은 것."""
    got = [d for m, d in touches if m <= when]
    return max(got) if got else None


def commit_time(p: Path):
    r = subprocess.run(["git", "log", "-1", "--format=%ad",
                        "--date=format:%Y-%m-%d %H:%M:%S", "--", str(p)],
                       capture_output=True, text=True, cwd=str(ROOT))
    s = r.stdout.strip()
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S") if s else None


def iso(d):
    return "%s-%s-%s" % (d[:4], d[4:6], d[6:]) if d else None


def main() -> int:
    t = pdata_touches()
    bulk = Counter(m.strftime("%Y-%m-%d") for m, _ in t).most_common(1)
    print("pdata %d일 · mtime 최다 몰림 %s (%d개 = %.1f%%)"
          % (len(t), bulk[0][0], bulk[0][1], 100 * bulk[0][1] / len(t)), flush=True)

    # 앞끝이 언제 어떻게 움직였는지 — 견고성의 근거
    print("\n앞끝 이동 (최근 6회)", flush=True)
    seen, moves = "", []
    for m, d in t:
        if d > seen:
            seen = d
            moves.append((m, d))
    for m, d in moves[-6:]:
        print("   %s 에 앞끝 → %s" % (m.strftime("%Y-%m-%d %H:%M"), iso(d)), flush=True)

    rows = []
    for p in sorted(RESULTS.glob("*.md")):
        c = commit_time(p)
        rows.append((p.name, c, frontier(t, c) if c else None))

    print("\n문서 %d개" % len(rows), flush=True)
    cnt = Counter(x[2] for x in rows)
    for d, n in sorted(cnt.items(), key=lambda x: (x[0] or "")):
        print("   자료 기준일 %s : %2d개" % (iso(d) or "**복원 실패**", n), flush=True)
    miss = [x[0] for x in rows if not x[2]]
    print("   **미상 %d개**%s" % (len(miss), (" — " + ", ".join(miss)) if miss else ""),
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

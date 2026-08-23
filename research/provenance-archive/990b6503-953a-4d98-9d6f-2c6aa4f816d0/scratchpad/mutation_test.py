# -*- coding: utf-8 -*-
"""Mutation test: relax/remove the season-exhaustion clause in rule 1b and
see whether the existing test suite catches it."""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\Users\hanul\playground\my-stock")
SRC = REPO / "scripts" / "screen_earnings_calendar.py"
orig = SRC.read_text(encoding="utf-8")

CLAUSE = "            and not any(s <= d <= e for d, _t, _k in events)  # \uadf8 \uc2dc\uc98c \uc2e4\uc801\uc774 \uc544\uc9c1 \uc5c6\uc74c\n"
assert CLAUSE in orig, "clause not found"

MUTANTS = {
    # Finding's stated scenario: drop the season-exhaustion condition entirely
    "M1_remove_exhaustion": orig.replace(CLAUSE, ""),
    # Kind-sensitive relaxation: only periodic reports exhaust a season, jamjeong doesn't
    "M2_only_reports_exhaust": orig.replace(
        "and not any(s <= d <= e for d, _t, _k in events)",
        "and not any(s <= d <= e for d, _t, _k in events if _k != '\uc7a0\uc815\uc2e4\uc801')",
    ),
}

results = {}
try:
    for name, mutated in MUTANTS.items():
        SRC.write_text(mutated, encoding="utf-8")
        p = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_earnings_calendar.py", "-q", "--no-header", "-x", "--tb=line"],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        tail = "\n".join(p.stdout.strip().splitlines()[-6:])
        results[name] = (p.returncode, tail)
finally:
    SRC.write_text(orig, encoding="utf-8")

# sanity: original passes
p = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_earnings_calendar.py", "-q", "--no-header", "--tb=line"],
    cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
)
results["ORIGINAL"] = (p.returncode, "\n".join(p.stdout.strip().splitlines()[-4:]))

for name, (rc, tail) in results.items():
    print("=" * 20, name, "rc =", rc)
    print(tail)
    print()

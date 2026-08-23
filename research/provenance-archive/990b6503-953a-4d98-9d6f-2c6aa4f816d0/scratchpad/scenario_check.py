# -*- coding: utf-8 -*-
"""Does M2 (jamjeong doesn't exhaust) regress the finding's scenario:
jamjeong 2026-07-28 + IR 2026-08-03, asof 2026-08-04?"""
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(r"C:\Users\hanul\playground\my-stock")
SRC = REPO / "scripts" / "screen_earnings_calendar.py"
orig = SRC.read_text(encoding="utf-8")

SNIPPET = r"""
import sys
from datetime import date
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from screen_earnings_calendar import estimate_next_earnings
JAM = "\uc5f0\uacb0\uc7ac\ubb34\uc81c\ud45c\uae30\uc900\uc601\uc5c5(\uc7a0\uc815)\uc2e4\uc801(\uacf5\uc815\uacf5\uc2dc)"
IR = "\uae30\uc5c5\uc124\uba85\ud68c(IR)\uac1c\ucd5c(\uc548\ub0b4\uacf5\uc2dc)"
filings = [
    {"date": "2025-08-04", "title": JAM},
    {"date": "2025-08-14", "title": "\ubc18\uae30\ubcf4\uace0\uc11c (2025.06)"},
    {"date": "2026-07-28", "title": JAM},
    {"date": "2026-08-03", "title": IR},
]
r = estimate_next_earnings(filings, date(2026, 8, 4))
print(r["status"], r["expected"], "|", r["basis"])
"""

def run():
    p = subprocess.run([sys.executable, "-c", SNIPPET], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return (p.stdout.strip() or p.stderr.strip().splitlines()[-1])

print("ORIGINAL:", run())
try:
    SRC.write_text(orig.replace(
        "and not any(s <= d <= e for d, _t, _k in events)",
        "and not any(s <= d <= e for d, _t, _k in events if _k != '\uc7a0\uc815\uc2e4\uc801')",
    ), encoding="utf-8")
    print("M2      :", run())
finally:
    SRC.write_text(orig, encoding="utf-8")

# -*- coding: utf-8 -*-
"""pytest plugin: seed sys.modules with a bad-guard variant of screen_earnings_calendar."""
import sys
import types
from pathlib import Path

ROOT = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(ROOT / "scripts"))

src_path = ROOT / "scripts" / "screen_earnings_calendar.py"
src = src_path.read_text(encoding="utf-8")
old = "            not (s > win[1] or e < win[0])                    # IR 창과 시즌 창이 겹치고\n"
new = "            not (s > win[1] or e < win[0]) and e >= win[1]     # BAD TIGHTENING\n"
assert old in src
bad_src = src.replace(old, new)

mod = types.ModuleType("screen_earnings_calendar")
mod.__file__ = str(src_path)
exec(compile(bad_src, str(src_path), "exec"), mod.__dict__)
sys.modules["screen_earnings_calendar"] = mod
print("[bad_seed] seeded bad-guard screen_earnings_calendar")

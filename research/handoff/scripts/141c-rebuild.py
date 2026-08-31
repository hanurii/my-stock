# -*- coding: utf-8 -*-
r"""141c — 웜업 재빌드 «몰이꾼». 해마다 짓고, 이미 있는 해는 건너뛴다.

🚨 이 파일은 **`Start-Process` 로 «분리해» 띄우기 위한 것**이다.
   도구가 붙들고 있는 백그라운드로 돌리면 긴 작업이 거둬지는 일이 있었다(3회).
   여기서는 파이썬이 자식 프로세스를 순서대로 부르고, **진행을 로그 파일에 적는다.**

재개  이미 `uspath_YYYY.json` 이 있으면 «건너뛴다». 끊겨도 진도가 남는다.
      중간 파일 `*.paths.jsonl` 은 `pathsink` 가 `open("w")` 로 열어 **덧붙기 사고가 없다**.

실행(분리):
  Start-Process python -ArgumentList "research/handoff/scripts/141c-rebuild.py" `
     -WorkingDirectory C:\Users\hanul\playground\my-stock `
     -RedirectStandardOutput ...\_141c.log -RedirectStandardError ...\_141c.err -NoNewWindow
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]   # research/handoff/scripts → 저장소 뿌리
OUT = Path("D:/stock-data/uspath-warm/full")
BUILDER = ROOT / "scripts" / "backtest_volatility_pilot_us.py"
WARM_DAYS = 700
YEARS = tuple(range(1999, 2027))


def span(y):
    s = "1999-04-01" if y == 1999 else "%d-01-01" % y
    e = "2026-08-21" if y == 2026 else "%d-12-31" % y
    return s, e


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    done, skipped, failed = [], [], []
    for y in YEARS:
        out = OUT / ("uspath_%d.json" % y)
        if out.exists():
            skipped.append(y)
            print("[%6.1f분] %d 이미 있음 — 건너뜀" % ((time.time() - t0) / 60, y), flush=True)
            continue
        s, e = span(y)
        print("[%6.1f분] %d 짓는 중 (%s ~ %s) …" % ((time.time() - t0) / 60, y, s, e),
              flush=True)
        p = subprocess.run(
            [sys.executable, str(BUILDER), "--market", "us",
             "--start", s, "--end", e, "--step", "1",
             "--emit-paths", "--emit-warmup", "--warm-days", str(WARM_DAYS),
             "--out", str(out).replace("\\", "/")],
            cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env={**__import__("os").environ,
                 "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
        tail = [ln for ln in (p.stdout or "").splitlines()
                if "저장" in ln or "개를 스트리밍" in ln]
        if p.returncode != 0 or not out.exists():
            failed.append(y)
            print("   🚨 %d 실패 (rc=%s)" % (y, p.returncode), flush=True)
            for ln in (p.stderr or "").splitlines()[-8:]:
                print("      | %s" % ln, flush=True)
        else:
            done.append(y)
            for ln in tail:
                print("      %s" % ln.strip(), flush=True)
            print("      크기 %.0f MB" % (out.stat().st_size / 1e6), flush=True)

    tot = sum(f.stat().st_size for f in OUT.glob("uspath_*.json"))
    print("", flush=True)
    print("===== 끝 (%.1f분) =====" % ((time.time() - t0) / 60), flush=True)
    print("지음 %d · 건너뜀 %d · 실패 %d %s"
          % (len(done), len(skipped), len(failed), failed or ""), flush=True)
    print("파일 %d개 · 합계 **%.2f GB**"
          % (len(list(OUT.glob("uspath_*.json"))), tot / 1e9), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

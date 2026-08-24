# -*- coding: utf-8 -*-
"""양보 감시기 — **사용자의 `SEPA-Daily` 가 우리보다 우선이다.**

여유 RAM 이 **0.5GB** 아래로 두 번 연속 내려가면 **우리 배치만** 끝내고 비켜 준다.
🚨 **SEPA 프로세스는 절대 건드리지 않는다.** 우리가 띄운 것만 이름으로 골라 죽인다.

죽이는 대상 (우리 것만)
  - `_us_paths_run.sh`            ← 다음 해를 새로 띄우지 못하게 **먼저** 죽인다
  - `25-run-guarded.py`
  - `backtest_volatility_pilot_us.py ... --emit-paths`
건드리지 않는 것
  - `ohlcv_matrix.py` · `claude` · `screen_canslim` · 그 밖 전부
  - `_after_paths_gate.sh`  ← 6/6 을 기다리는 폴링일 뿐이라 살려 둔다

죽인 뒤 **깨진 `uspath_*.json` 을 지운다**(쓰는 중에 죽으면 잘린 파일이 남고,
배치의 `skip` 이 그걸 «완성»으로 오해한다). **파일이 있다 ≠ 온전하다.**

🚨 **자기 생존 신호** (2026-08-24 추가)
  이 감시기는 **한 번 조용히 죽은 적이 있다**(cp949 인코딩). **감시기가 없는 채로
  배치가 도는 게 최악**이라 셋을 넣었다.
  1. **출력 인코딩을 코드 안에서 강제**한다 — 환경변수에 기대지 않는다.
  2. **매 점검마다 `_YIELD_HEARTBEAT.txt` 에 시각을 쓴다.** 그 파일이 멎으면 죽은 것이다.
  3. **점검 한 번이 실패해도 죽지 않는다**(점검마다 try). 죽을 땐 사유를 남긴다.
  감시기가 죽으면 **`_yield_sup.sh` 가 되살리고, 못 되살리면 우리 배치를 멈춘다.**

끝 코드: 0=우리 배치 없음(할 일 끝) · 1=양보함 · 2=치명적 오류

실행: python research/handoff/scripts/_yield_watch.py
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

# ① 환경변수에 기대지 않는다 — 여기서 강제한다
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / ".cache" / "bt5y" / "sub"
HERE = Path(__file__).resolve().parent
MARK = HERE / "_YIELDED_TO_SEPA.txt"
BEAT = HERE / "_YIELD_HEARTBEAT.txt"

FLOOR_GB = 0.50          # 두뇌 세션 지정: 감시기 문턱(0.2)이 아니라 **0.5**
NEED = 2                 # 연속 몇 번이면 양보하는가 (순간 요동 방지)
EVERY = 10               # 초

OURS = ("_us_paths_run.sh", "25-run-guarded.py", "--emit-paths",
        "39-exit-variants.py", "40-extend-cap-paths.py",
        "41-round1-exits.py", "42-checks.py")   # 관문·연장·변형도 우리 것
NEVER = ("ohlcv_matrix", "claude", "screen_canslim", "_after_paths_gate")


class _M(ctypes.Structure):
    _fields_ = ([("a", wt.DWORD), ("b", wt.DWORD)]
                + [(c, ctypes.c_ulonglong) for c in "cdefghi"])


def free_gb() -> float:
    m = _M()
    m.a = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.d / 1024 ** 3


def procs():
    """(pid, commandline) 목록. PowerShell CIM 으로 뽑는다."""
    ps = ("Get-CimInstance Win32_Process | "
          "Where-Object { $_.Name -match 'python|bash' } | "
          "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, timeout=45)
    d = json.loads(r.stdout or "[]")
    if isinstance(d, dict):
        d = [d]
    return [(x["ProcessId"], x.get("CommandLine") or "") for x in d]


def targets():
    out = []
    for pid, cl in procs():
        if any(n in cl for n in NEVER):      # 🚨 사용자 것 · 대기 폴링은 제외
            continue
        if any(o in cl for o in OURS):
            out.append((pid, cl))
    # `_us_paths_run.sh` 를 **맨 앞**으로: 다음 해를 새로 띄우기 전에 끊는다
    out.sort(key=lambda t: 0 if "_us_paths_run.sh" in t[1] else 1)
    return out


def clean_partial():
    """쓰는 중에 죽어 **잘린** json 을 지운다. **파일이 있다 ≠ 온전하다.**"""
    bad = []
    for f in sorted(SUB.glob("uspath_*.json")):
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            bad.append(f.name)
            f.unlink()
    return bad


def beat(state: str, extra: str = "") -> None:
    """② 생존 신호. **이 파일이 멎으면 감시기가 죽은 것이다.**"""
    body = ["ts=%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
            "epoch=%d" % int(time.time()),
            "pid=%d" % __import__("os").getpid(),
            "state=%s" % state, extra]
    try:
        BEAT.write_text("\n".join(body) + "\n", encoding="utf-8")
    except Exception:
        pass


def sepa_alive():
    """🚨 **«무엇에» 양보하는지 기록한다.**

    2026-08-24 21:51 에 이 감시기가 처음 발동했는데, **SEPA 는 21:30 에 이미 끝나 있었다.**
    압박은 claude 세션 셋(1.5GB)이 서로를 밀어낸 것이었다.
    **끊은 판단은 옳았지만(0.486GB) 「양보한다」는 «이유»는 그 순간 성립하지 않았다.**
    상대가 없는데 「양보」라고만 적으면 **다음 사람이 「SEPA 가 무거웠구나」로 잘못 읽는다.**
    """
    try:
        for _pid, cl in procs():
            if any(k in cl for k in ("ohlcv_matrix", "screen_canslim", "canslim_lib")):
                return True, cl[:70]
    except Exception:
        pass
    return False, ""


def top_mem(k=3):
    ps = ("Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First %d "
          "ProcessName,@{n='MB';e={[math]::Round($_.WorkingSet64/1MB)}} "
          "| ConvertTo-Json -Compress" % k)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout or "[]")
        if isinstance(d, dict):
            d = [d]
        return " · ".join("%s %dMB" % (x["ProcessName"], x["MB"]) for x in d)
    except Exception:
        return "확인 불가"


def yield_now(g: float, t) -> None:
    sepa, scl = sepa_alive()
    top = top_mem(3)
    print("\n🚨 **끊는다** — 여유 %.3f GB < %.2f GB" % (g, FLOOR_GB), flush=True)
    print("   상대: %s" % (("**SEPA 살아 있음** — " + scl) if sepa
                          else "**SEPA 없음 — 다른 압박이다**"), flush=True)
    print("   상위 점유: %s" % top, flush=True)
    for pid, cl in t:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        print("   죽임 %s · %s" % (pid, cl[:90]), flush=True)
    time.sleep(3)
    bad = clean_partial()
    done = sorted(f.stem for f in SUB.glob("uspath_*.json"))
    MARK.write_text(
        "끊은 시각: %s\n여유: %.3f GB\n상대: %s\n상위 점유: %s\n"
        "지운 잘린 파일: %s\n남은 경로: %d개 %s\n"
        "재개: bash research/handoff/scripts/_us_paths_run.sh (skip 이 이어받는다)\n"
        % (time.strftime("%Y-%m-%d %H:%M:%S"), g,
           ("SEPA 살아 있음: " + scl) if sepa else "SEPA 없음 — 다른 압박",
           top, bad or "없음", len(done), done),
        encoding="utf-8")
    print("   잘린 파일 지움: %s" % (bad or "없음"), flush=True)
    print("   남은 경로 %d개: %s" % (len(done), done), flush=True)
    print("   → SEPA 가 끝나면 `_us_paths_run.sh` 를 다시 돌리면 된다.", flush=True)
    beat("yielded", "free=%.3f" % g)


def main() -> int:
    print("양보 감시기 시작 — 문턱 %.2f GB · %d회 연속 · %d초 간격"
          % (FLOOR_GB, NEED, EVERY), flush=True)
    beat("start")
    low, errs = 0, 0
    while True:
        # ③ 점검 한 번이 실패해도 죽지 않는다
        try:
            g = free_gb()
            t = targets()
            errs = 0
        except Exception:
            errs += 1
            print("[%s] ⚠️ 점검 실패 %d회\n%s"
                  % (time.strftime("%H:%M:%S"), errs, traceback.format_exc()), flush=True)
            beat("error", "consecutive=%d" % errs)
            if errs >= 5:
                print("🚨 점검이 5회 연속 실패 — **감시기를 신뢰할 수 없다.** 끝낸다.", flush=True)
                beat("dead", "reason=probe-failed-5x")
                return 2
            time.sleep(EVERY)
            continue

        if not t:
            print("[%s] 우리 배치가 없다 — 감시 종료 (여유 %.3f GB)"
                  % (time.strftime("%H:%M:%S"), g), flush=True)
            beat("done", "free=%.3f" % g)
            return 0

        low = low + 1 if g < FLOOR_GB else 0
        print("[%s] 여유 %.3f GB · 우리 %d개 · 연속 %d/%d"
              % (time.strftime("%H:%M:%S"), g, len(t), low, NEED), flush=True)
        beat("watch", "free=%.3f ours=%d low=%d" % (g, len(t), low))

        if low >= NEED:
            yield_now(g, t)
            return 1
        time.sleep(EVERY)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        beat("dead", "reason=interrupt")
        sys.exit(2)
    except Exception:
        beat("dead", "reason=%s" % traceback.format_exc().splitlines()[-1][:120])
        traceback.print_exc()
        sys.exit(2)

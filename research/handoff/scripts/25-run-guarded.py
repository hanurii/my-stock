# -*- coding: utf-8 -*-
"""25 본실행 · **여유 RAM 감시 + peak RSS 실측** 껍데기.

왜 필요한가
-----------
안전 규약 3 — "실행 중 여유가 0.2GB 아래로 떨어지면 중단". 사람이 지켜볼 수 없으니
이 껍데기가 5초마다 재고, 걸리면 자식을 죽이고 그 사실을 로그에 남긴다.
규약 2의 적합식(0.000468 GB/종목 + 0.044)이 5,667에서 맞는지는 **자식의 peak
working set 실측**으로만 확인된다 → 끝나고 GetProcessMemoryInfo 로 읽는다.
(psutil 이 없어서 ctypes 로 직접 부른다. 자식이 끝나도 핸들이 열려 있으면 읽힌다.)

사용: python 25-run-guarded.py <로그경로> -- <실행할 명령…>
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time

FLOOR_GB = 0.20            # 규약 3
POLL_SEC = 5.0


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


def free_gb() -> float:
    m = MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 1024 ** 3


def mem_of(handle):
    c = PROCESS_MEMORY_COUNTERS()
    c.cb = ctypes.sizeof(c)
    if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(c), c.cb):
        return c.PeakWorkingSetSize / 1024 ** 3, c.WorkingSetSize / 1024 ** 3
    return None, None


def main():
    logp = sys.argv[1]
    cmd = sys.argv[sys.argv.index("--") + 1:]
    log = open(logp, "w", encoding="utf-8", buffering=1)

    def say(s):
        print(s, flush=True)
        log.write(s + "\n")

    say("시작 전 여유 %.3f GB" % free_gb())
    say("명령: %s" % " ".join(cmd))
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    h = int(p._handle)
    peak = 0.0
    minfree = free_gb()
    killed = False
    while p.poll() is None:
        time.sleep(POLL_SEC)
        f = free_gb()
        minfree = min(minfree, f)
        pk, cur = mem_of(h)
        if pk:
            peak = max(peak, pk)
        if f < FLOOR_GB:
            say("\n🚨 여유 %.3f GB < %.2f — 규약 3에 따라 **중단**한다 "
                "(자식 peak %.3f GB · 경과 %.0f초)" % (f, FLOOR_GB, peak, time.time() - t0))
            p.kill()
            killed = True
            break
    p.wait()
    pk, _ = mem_of(h)
    if pk:
        peak = max(peak, pk)
    say("\n--- 감시 결과 ---")
    say("자식 **peak working set %.3f GB**" % peak)
    say("실행 중 **최저 여유 %.3f GB**" % minfree)
    say("종료코드 %s · 경과 %.0f초 · 중단여부 %s"
        % (p.returncode, time.time() - t0, "예" if killed else "아니오"))
    log.close()
    sys.exit(1 if killed else (p.returncode or 0))


if __name__ == "__main__":
    main()

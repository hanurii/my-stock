# -*- coding: utf-8 -*-
"""자식 프로세스의 **최대 작업 집합(PeakWorkingSetSize)** 을 재는 얇은 래퍼.

psutil 없이 Windows API 로 직접 읽는다. 프로세스가 끝난 뒤에도 핸들이 살아 있으면
`GetProcessMemoryInfo` 가 최대치를 그대로 돌려주므로 **폴링이 필요 없고 정확하다**
(폴링은 봉우리를 놓칠 수 있다).

사용: python research/handoff/scripts/_peak_rss.py <라벨> -- <명령 …>
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as w
import subprocess
import sys
import time


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


def main():
    argv = sys.argv[1:]
    label = argv[0]
    cmd = argv[argv.index("--") + 1:]
    print("[peak-rss] %s\n[peak-rss] 명령: %s" % (label, " ".join(cmd)), flush=True)
    t0 = time.time()
    p = subprocess.Popen(cmd)
    rc = p.wait()
    el = time.time() - t0
    c = PROCESS_MEMORY_COUNTERS()
    c.cb = ctypes.sizeof(c)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(
        int(p._handle), ctypes.byref(c), c.cb)
    if not ok:
        print("[peak-rss] GetProcessMemoryInfo 실패 (err %d)"
              % ctypes.GetLastError(), flush=True)
        sys.exit(rc)
    print("\n[peak-rss] ===== %s =====" % label, flush=True)
    print("[peak-rss] 종료코드 %d · 소요 %.1f초" % (rc, el), flush=True)
    print("[peak-rss] **최대 작업집합(PeakWorkingSet) %.3f GB (%.0f MB)**"
          % (c.PeakWorkingSetSize / 2**30, c.PeakWorkingSetSize / 2**20), flush=True)
    print("[peak-rss] 최대 페이지파일(커밋) %.3f GB"
          % (c.PeakPagefileUsage / 2**30), flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()

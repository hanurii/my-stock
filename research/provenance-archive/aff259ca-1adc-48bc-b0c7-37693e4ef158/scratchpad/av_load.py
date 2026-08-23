# -*- coding: utf-8 -*-
"""Adversarial verify — independent raw-pdata loader (my own implementation).

Loads clpr/fltRt/trqu/mrktCtg for every day-file, aligned to the npz code order,
and caches to av_raw.npz for the check scripts.
"""
import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\hanul\playground\my-stock")
PDATA = ROOT / ".cache" / "pdata"
SP = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad")

z = np.load(SP / "passmatrix.npz", allow_pickle=False)
npz_dates = [str(d) for d in z["dates"]]
npz_codes = [str(c) for c in z["codes"]]
code_pos = {c: i for i, c in enumerate(npz_codes)}

files = sorted(PDATA.glob("price_*.json"))
my_dates = [f.stem[6:10] + "-" + f.stem[10:12] + "-" + f.stem[12:14] for f in files]
assert my_dates == npz_dates, "date grid mismatch vs npz!"
T = len(files)
N = len(npz_codes)

close = np.full((T, N), np.nan)
flt = np.full((T, N), np.nan)
vol = np.full((T, N), np.nan)
mkt = np.zeros((T, N), dtype=np.uint8)   # 1 KOSPI 2 KOSDAQ 3 other
extra_codes = set()   # codes in pdata not in npz (should be pure-KONEX drops)

MK = {"KOSPI": 1, "KOSDAQ": 2}
t0 = time.time()
for t, f in enumerate(files):
    d = json.loads(f.read_text(encoding="utf-8"))
    for code, row in d.items():
        j = code_pos.get(code)
        if j is None:
            extra_codes.add((code, row.get("mrktCtg")))
            continue
        mkt[t, j] = MK.get(row.get("mrktCtg"), 3)
        c = row.get("clpr")
        if c is not None and c > 0:
            close[t, j] = c
        fr = row.get("fltRt")
        if fr is not None and fr not in ("", "-"):
            flt[t, j] = float(fr)
        v = row.get("trqu")
        if v is not None:
            vol[t, j] = v
    if (t + 1) % 400 == 0:
        print(f"{t+1}/{T} {time.time()-t0:.0f}s", flush=True)

konex_only_extras = sum(1 for c, m in extra_codes if m == "KONEX")
print("codes in pdata but not npz:", len(extra_codes),
      "of which KONEX:", konex_only_extras)
non_konex = [(c, m) for c, m in extra_codes if m != "KONEX"]
print("non-KONEX extras (should be none):", non_konex[:10])

np.savez(SP / "av_raw.npz", close=close, flt=flt, vol=vol, mkt=mkt)
print("saved av_raw.npz", time.time() - t0)

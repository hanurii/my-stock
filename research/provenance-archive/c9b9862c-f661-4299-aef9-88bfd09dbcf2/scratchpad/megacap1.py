import json, os, glob
from datetime import datetime

PD = r"C:/Users/hanul/playground/my-stock/.cache/pdata"
files = sorted(glob.glob(os.path.join(PD, "price_*.json")))
dates = [os.path.basename(f)[6:14] for f in files]
START, END = "20251126", "20260821"
sel = [(d,f) for d,f in zip(dates,files) if START <= d <= END]
print("trading days in window:", len(sel), sel[0][0], sel[-1][0])

def load(f):
    with open(f, encoding='utf-8') as fp:
        return json.load(fp)

d0 = load(sel[0][1])
print("universe size at start:", len(d0))
# sample record
k = list(d0)[0]
print(k, json.dumps(d0[k], ensure_ascii=False))

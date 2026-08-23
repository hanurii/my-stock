# -*- coding: utf-8 -*-
"""2차 요인 추가: RS선·ATR수축·신고가돌파 여부·재진입 이력 등."""
import json, sys
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAIN = Path(r"C:\Users\hanul\playground\my-stock"); SCR = Path(sys.argv[0]).parent
sys.path.insert(0, str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"
ohlcv_matrix.FOREIGN_PATH = MAIN/".cache"/"ohlcv"/"foreign.json"
from canslim_lib.pivot_backtest import truncate_series

rows = json.loads((SCR/"events_feat2.json").read_text(encoding="utf-8"))

# ── 등가중 시장지수(캐시 전 종목 일별 수익률 평균 누적) ──────────────
import glob, os
ret_sum = defaultdict(float); ret_n = defaultdict(int)
files = sorted(glob.glob(str(ohlcv_matrix.SERIES_DIR/"*.json")))
for fp in files:
    try: s = json.loads(Path(fp).read_text(encoding="utf-8"))
    except Exception: continue
    d, c = s.get("dates") or [], s.get("closes") or []
    for i in range(1, len(c)):
        if c[i] and c[i-1] and 0.5 < c[i]/c[i-1] < 2.0:
            ret_sum[d[i]] += c[i]/c[i-1]-1; ret_n[d[i]] += 1
idx_dates = sorted(k for k in ret_sum if ret_n[k] >= 100)
idx_val = {}; v = 100.0
for d in idx_dates:
    v *= 1 + ret_sum[d]/ret_n[d]; idx_val[d] = v
print(f"등가중 지수 {len(idx_dates)}일 {idx_dates[0]}~{idx_dates[-1]}  (마지막 {idx_val[idx_dates[-1]]:.1f})")

codes = sorted({r["code"] for r in rows})
ser = {c: ohlcv_matrix.get_series(c) for c in codes}

# 종목별 과거 이벤트 이력(같은 종목 직전 거래 결과)
hist = defaultdict(list)
for r in sorted(rows, key=lambda x: x["scan_date"]):
    hist[r["code"]].append(r)

def mean(xs):
    xs=[x for x in xs if x is not None]
    return sum(xs)/len(xs) if xs else None

for r in rows:
    s = ser.get(r["code"]); D = r["scan_date"]
    if not s: continue
    t = truncate_series(s, D)
    cl,hi,lo,vo,op = t["closes"],t["highs"],t["lows"],t["volumes"],t["opens"]
    n=len(cl); px=cl[-1]
    # ATR 수축비 (ATR20 / ATR60)
    def atr(w):
        trs=[]
        for i in range(max(1,n-w), n):
            if hi[i] is None or lo[i] is None or cl[i-1] is None: continue
            trs.append(max(hi[i]-lo[i], abs(hi[i]-cl[i-1]), abs(lo[i]-cl[i-1])))
        return sum(trs)/len(trs) if len(trs)>=w*0.6 else None
    a20,a60 = atr(20), atr(60)
    r["atr_squeeze"] = round(a20/a60,3) if a20 and a60 else None
    # 거래량 마름(패턴 무관): 최근20일 평균 / 최근50일 평균
    v20,v50 = mean(vo[-20:]), mean(vo[-50:])
    r["vol_dry_20_50"] = round(v20/v50,3) if v20 and v50 else None
    # 52주 고가 이후 경과일 / 신고가 돌파 여부
    w=min(252,n); segh=hi[-w:]
    mx=max(x for x in segh if x is not None)
    r["days_since_52wh"] = (len(segh)-1) - max(i for i,x in enumerate(segh) if x==mx)
    r["pivot_above_52wh"] = 1 if r["pivot"] >= mx else 0
    r["pivot_vs_52wh_pct"] = round((r["pivot"]/mx-1)*100,2)
    # 그날 종가 위치
    if hi[-1] is not None and lo[-1] is not None and hi[-1]>lo[-1]:
        r["close_pos"] = round((px-lo[-1])/(hi[-1]-lo[-1])*100,1)
    # ret_250d
    r["ret_250d_pct"] = round((px/cl[-1-250]-1)*100,2) if n>250 and cl[-1-250] else None
    # RS선 = 종가/지수
    dts=t["dates"]
    rl=[]
    for i in range(n):
        iv=idx_val.get(dts[i])
        rl.append(cl[i]/iv if iv and cl[i] else None)
    rlw=[x for x in rl[-w:] if x is not None]
    if rlw and rl[-1]:
        r["rsline_vs_high_pct"] = round((rl[-1]/max(rlw)-1)*100,2)
        r["rsline_newhigh"] = 1 if rl[-1] >= max(rlw)*0.999 else 0
    if n>20 and rl[-1] and rl[-21]:
        r["rsline_20d_pct"] = round((rl[-1]/rl[-21]-1)*100,2)
    if n>60 and rl[-1] and rl[-61]:
        r["rsline_60d_pct"] = round((rl[-1]/rl[-61]-1)*100,2)
    # 초과수익 20일
    i0=idx_val.get(dts[-21]) if n>20 else None; i1=idx_val.get(dts[-1])
    if i0 and i1 and n>20 and cl[-21]:
        r["excess_20d_pct"] = round(((px/cl[-21])-(i1/i0))*100,2)
    # 같은 종목 직전 거래 결과
    prev=[x for x in hist[r["code"]] if x["scan_date"] < D and x["result"] in ("win","loss")]
    r["n_prior"] = len(prev)
    r["prev_loss"] = (1 if prev[-1]["result"]=="loss" else 0) if prev else None
    r["is_repeat"] = 1 if prev else 0

(SCR/"events_feat3.json").write_text(json.dumps(rows,ensure_ascii=False),encoding="utf-8")
keys=["atr_squeeze","vol_dry_20_50","days_since_52wh","pivot_above_52wh","pivot_vs_52wh_pct",
      "close_pos","ret_250d_pct","rsline_vs_high_pct","rsline_newhigh","rsline_20d_pct",
      "rsline_60d_pct","excess_20d_pct","prev_loss","is_repeat"]
for k in keys:
    print(f"  {k:<20} 결측 {sum(1 for r in rows if r.get(k) is None):>3}/{len(rows)}")
print("신고가돌파(pivot>=52wh):", sum(1 for r in rows if r.get('pivot_above_52wh')==1), "/", len(rows))
print("재진입(is_repeat):", sum(1 for r in rows if r.get('is_repeat')==1))

# -*- coding: utf-8 -*-
"""과제A 패널: 614건 × 순서규칙 키 (전부 as-of, 룩어헤드 없음)."""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
SCR = Path(__file__).resolve().parent
sys.path.insert(0, str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix, superperf
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"
ohlcv_matrix.FOREIGN_PATH = MAIN/".cache"/"ohlcv"/"foreign.json"
from canslim_lib.pivot_backtest import truncate_series

feat = json.loads((SCR.parent/"events_feat3.json").read_text(encoding="utf-8"))
full = json.loads((SCR.parent/"evfull.json").read_text(encoding="utf-8"))
idx  = json.loads((SCR/"idx.json").read_text(encoding="utf-8"))
regime = {r["date"]: r for r in json.loads((MAIN/"public/data/market-regime.json").read_text(encoding="utf-8"))["series"]}

# evfull 로 진입일 시가 확보
opn = {}
for r in full:
    s = r["ser"]; bi = r["bi_local"]
    assert s["dates"][bi] == r["entry_date"], (r["code"], r["entry_date"])
    opn[(r["code"], r["entry_date"])] = s["opens"][bi]

codes = sorted({r["code"] for r in feat})
ser = {c: ohlcv_matrix.get_series(c) for c in codes}

rows=[]
n_open_missing=0
for r in feat:
    D=r["scan_date"]; s=ser[r["code"]]
    t = truncate_series(s, D)
    f = superperf.compute_factors(t["dates"], t["closes"], t["highs"], idx)
    sc, _ = superperf.score(r["rs"], f["prior_adv"], f["rs_nh_days"], f["rs_leads"])
    o = opn.get((r["code"], r["entry_date"]))
    if o is None: n_open_missing+=1
    piv = r["pivot"]
    rec = dict(
        code=r["code"], name=r["name"], market=r["market"], pattern=r["pattern"],
        scan_date=D, entry_date=r["entry_date"], result=r["result"],
        gain=r["gain_at_resolve_pct"], pivot=piv, entry_price=r["entry_price"],
        # 순서 키
        turnover=r["turnover_eok"],        # 50일 평균 거래대금(억)
        rs=r["rs"], sp=sc,                  # 초수익 점수 0~6
        pct_to_pivot=r["pct_to_pivot"],     # 스캔일 종가→피벗 거리 % (작을수록 피벗 근접)
        atr=r["atr_pct"], dist52=r["dist_52wh_pct"],  # 0 에 가까울수록 고가 근접(음수)
        cap=r["cap_eok"], gap=r["gap_up_pct"],
        open_ratio=(o/piv if o else None),  # 진입일 시가/피벗 — 돌파순서 대리지표
        up=bool((regime.get(r["entry_date"]) or {}).get("up")),
    )
    rows.append(rec)
print("open 결측", n_open_missing)
Path(SCR/"panelA.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
from collections import Counter
print(len(rows), Counter(x["sp"] for x in rows))
print("open_ratio 분포 min/med/max",
      *(round(v,4) for v in (min(x["open_ratio"] for x in rows),
        sorted(x["open_ratio"] for x in rows)[len(rows)//2],
        max(x["open_ratio"] for x in rows))))
# gap 과의 정합성 검증
bad=[x for x in rows if x["gap"]>0 and abs((max(x["open_ratio"],1.0)-1)*100 - x["gap"])>0.02]
print("gap 정합 불일치", len(bad))

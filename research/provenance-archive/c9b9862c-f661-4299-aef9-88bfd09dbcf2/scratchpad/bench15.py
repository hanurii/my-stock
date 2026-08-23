# -*- coding: utf-8 -*-
"""병렬화 이득 실측 (종목 샤딩, Windows spawn)."""
import json, sys, time, os
from pathlib import Path
import concurrent.futures as cf
ROOT=Path(r"C:/Users/hanul/playground/my-stock")
SER=ROOT/".cache"/"ohlcv"/"series"

def work(codes):
    sys.path.insert(0,str(ROOT/"scripts"))
    from canslim_lib import vcp_history, power_play_history, cheat_history
    n=0
    for c in codes:
        try: s=json.loads((SER/f"{c}.json").read_text(encoding="utf-8"))
        except Exception: continue
        if len(s["closes"])<300: continue
        vcp_history.replay_vcp(s,150,None)
        power_play_history.replay_power_play(s,150,None)
        cheat_history.replay_cheat(s,150,None)
        n+=1
    return n

if __name__=="__main__":
    codes=[p.stem for p in sorted(SER.glob("*.json"))][:400]
    for W in (1,4,8):
        sh=[codes[i::W] for i in range(W)]
        t0=time.time()
        if W==1:
            tot=work(sh[0])
        else:
            with cf.ProcessPoolExecutor(max_workers=W) as ex:
                tot=sum(ex.map(work,sh))
        dt=time.time()-t0
        print(f"워커 {W}: {tot}종목×150일 {dt:.1f}s → {tot*150*3/dt:.0f} 검출/초  (배속 기준 {dt:.1f}s)")

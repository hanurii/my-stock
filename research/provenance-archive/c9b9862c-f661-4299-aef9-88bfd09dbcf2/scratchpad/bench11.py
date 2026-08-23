# -*- coding: utf-8 -*-
"""관문여유 점수·변동성 지표를 npz 에서 numpy 로 뽑는 비용."""
import numpy as np, time
from pathlib import Path
PM = Path(r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/aff259ca-1adc-48bc-b0c7-37693e4ef158/scratchpad/passmatrix.npz")
z=np.load(PM, allow_pickle=True)
t0=time.time(); idx=z['idx']; print("idx 로드", round(time.time()-t0,2),"s", idx.shape, idx.nbytes/1e6,"MB")
T,N=idx.shape
def rollmean(a,w):
    c=np.nancumsum(np.nan_to_num(a,nan=0.0),axis=0)
    cnt=np.cumsum(np.isfinite(a),axis=0)
    out=np.full_like(a,np.nan)
    out[w-1:]= (c[w-1:]-np.concatenate([np.zeros((1,a.shape[1])),c[:-w]]))/w
    valid=np.full(a.shape,False); valid[w-1:]=(cnt[w-1:]-np.concatenate([np.zeros((1,a.shape[1])),cnt[:-w]]))==w
    out[~valid]=np.nan
    return out
t0=time.time()
ma50=rollmean(idx,50); ma150=rollmean(idx,150); ma200=rollmean(idx,200)
print("MA 50/150/200:", round(time.time()-t0,1),"s")
t0=time.time()
# 52주 고저 (rolling max/min) — 슬라이딩 윈도우
from numpy.lib.stride_tricks import sliding_window_view
w=252
sw=sliding_window_view(idx,(w,),axis=0)
hi52=np.full_like(idx,np.nan); lo52=np.full_like(idx,np.nan)
hi52[w-1:]=np.nanmax(sw,axis=-1); lo52[w-1:]=np.nanmin(sw,axis=-1)
print("52주 고저:", round(time.time()-t0,1),"s  메모리 슬라이딩뷰 OK")
t0=time.time()
ret=np.diff(np.log(idx),axis=0)
ew=np.nanmean(ret,axis=1)          # 등가중 시장 수익
vol20=np.array([np.nanstd(ew[max(0,i-19):i+1])*np.sqrt(252)*100 for i in range(len(ew))])
print("등가중 변동성:", round(time.time()-t0,1),"s  최근값", round(vol20[-1],1),"% 연율")
q=np.nanpercentile(vol20[-300:],[25,50,75]); print("최근 300일 변동성 사분위:", np.round(q,1))

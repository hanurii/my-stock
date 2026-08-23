import sys; sys.path.insert(0,'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad')
from base import load
import numpy as np, pandas as pd
from scipy import stats as st
ev,r=load(); r=r.reset_index(drop=True)
r['wbar']=r.groupby('scan_date')['w'].transform('mean')
r['pbar']=r.groupby('scan_date')['pct_all'].transform('mean')
r['s']=((r['w']-r['wbar'])*(r['pct_all']-r['pbar'])).values
s=r['s'].values; code=r['code'].values; day=r['scan_date'].values
ucode,ci=np.unique(code,return_inverse=True); uday,di=np.unique(day,return_inverse=True)
def tstat(keep):
    ss=s[keep]; n=len(ss)
    if n<10: return np.nan
    g=np.bincount(ci[keep],ss,minlength=len(ucode))
    return ss.mean()/(np.sqrt((g**2).sum())/n)
allk=np.ones(len(s),bool)
print(f'기준 t={tstat(allk):+.3f}')
lo=[(ucode[j], (ci==j).sum(), tstat(ci!=j)) for j in range(len(ucode))]
lo=pd.DataFrame(lo,columns=['code','n','t']).sort_values('t')
nm=dict(zip(r['code'],r['name'])); lo['name']=lo['code'].map(nm)
print('종목 1개 제거 최소 t 5개:'); print(lo.head(5).to_string(index=False))
print('t<1.96 되는 종목 수:',int((lo['t']<1.96).sum()),'/',len(lo))
ld=[(uday[j],(di==j).sum(),tstat(di!=j)) for j in range(len(uday))]
ld=pd.DataFrame(ld,columns=['date','n','t']).sort_values('t')
print('날짜 1개 제거 최소 t 5개:'); print(ld.head(5).to_string(index=False))
print('t<1.96 되는 날짜 수:',int((ld['t']<1.96).sum()),'/',len(ld))
dm=r.groupby('scan_date').apply(lambda g: ((g['w']-g['w'].mean())*(g['pct_all']-g['pct_all'].mean())).mean() if len(g)>1 else np.nan, include_groups=False).dropna()
tt=dm.mean()/(dm.std(ddof=1)/np.sqrt(len(dm)))
print(f'\n날짜 동일가중 t검정: 날짜수={len(dm)} t={tt:+.2f} 단측p={1-st.t.cdf(tt,len(dm)-1):.4f}')

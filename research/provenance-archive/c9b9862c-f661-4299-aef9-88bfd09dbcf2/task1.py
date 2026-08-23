# -*- coding: utf-8 -*-
"""과제 C-1: 지금 국면 지표가 그날 승률을 얼마나 설명하나"""
import sys, json, math
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build

rows = build()
res = [r for r in rows if r['nres']>0]

W = sum(r['w'] for r in res); L = sum(r['l'] for r in res); N=W+L
p = W/N
print(f"[전체] 결착 {N}건, 승 {W}, 승률 {100*p:.1f}%")

# --- 1) 국면이 설명하는 분산 ---
def grp(sel):
    w=sum(r['w'] for r in res if sel(r)); l=sum(r['l'] for r in res if sel(r)); return w,l
wu,lu = grp(lambda r: r['up']); wd,ld = grp(lambda r: not r['up'])
pu = wu/(wu+lu); pdn = wd/(wd+ld)
var_tot = p*(1-p)
var_in = ((wu+lu)*pu*(1-pu) + (wd+ld)*pdn*(1-pdn))/N
print(f"[국면] 상승 {wu}/{wu+lu} = {100*pu:.1f}% · 조정 {wd}/{wd+ld} = {100*pdn:.1f}%")
print(f"  거래 단위 설명력 R2 = {100*(1-var_in/var_tot):.2f}%  (= 국면만 알면 승패 예측의 {100*(1-var_in/var_tot):.1f}%만 설명)")

# --- 2) 상승국면 날들 사이의 편차 (과산포) ---
def overdisp(sub, label):
    n_days = len(sub); tot = sum(r['nres'] for r in sub)
    pp = sum(r['w'] for r in sub)/tot
    # 관측 분산(거래수 가중) vs 이항 기대
    num = sum(r['nres']*(r['w']/r['nres'] - pp)**2 for r in sub)
    obs = num/tot
    exp = sum(r['nres']*pp*(1-pp)/r['nres'] for r in sub)/tot  # = pp(1-pp)*days/tot 아님
    # 정확히: E[(phat-p)^2] = p(1-p)/n_i  -> 가중평균
    exp = sum(r['nres']*(pp*(1-pp)/r['nres']) for r in sub)/tot
    # 카이제곱 과산포 검정
    chi = sum((r['w'] - r['nres']*pp)**2/(r['nres']*pp*(1-pp)) for r in sub)
    dfree = n_days-1
    print(f"[{label}] 날 {n_days}, 거래 {tot}, 승률 {100*pp:.1f}%")
    print(f"  날별 승률 분산 관측 {obs:.4f} vs 우연(이항) 기대 {exp:.4f}  → 과산포 배수 {obs/exp:.2f}")
    print(f"  카이제곱 {chi:.1f} / df {dfree}  (비 {chi/dfree:.2f})")
    return chi, dfree

allres = [r for r in res if r['nres']>=1]
overdisp(allres, "전체 146일")
up3 = [r for r in res if r['up'] and r['nres']>=3]
overdisp(up3, "상승국면 & 3건+ 진입")
up4 = [r for r in res if r['up'] and r['nres']>=4]
overdisp(up4, "상승국면 & 4건+ 진입")

# 상승국면 날의 승률 분포
import collections
def dist(sub, label):
    b = collections.Counter()
    for r in sub:
        wr = r['w']/r['nres']
        if wr==0: b['0% (전멸)']+=1
        elif wr<0.25: b['0~25%']+=1
        elif wr<0.5: b['25~50%']+=1
        elif wr<1.0: b['50~99%']+=1
        else: b['100% (전승)']+=1
    print(f"[{label}] n={len(sub)}일 " + " · ".join(f"{k} {v}일({100*v/len(sub):.0f}%)" for k,v in
          sorted(b.items(), key=lambda x:['0% (전멸)','0~25%','25~50%','50~99%','100% (전승)'].index(x[0]))))
dist(up3, "상승국면 3건+")
dist([r for r in res if not r['up'] and r['nres']>=3], "조정국면 3건+")

# 전멸 확률: 실제 vs 독립가정
for lab, sub in (("상승국면", [r for r in res if r['up'] and r['nres']>=4]),
                 ("조정국면", [r for r in res if not r['up'] and r['nres']>=4]),
                 ("전체", [r for r in res if r['nres']>=4])):
    if not sub: continue
    pp = sum(r['w'] for r in sub)/sum(r['nres'] for r in sub)
    zero = sum(1 for r in sub if r['w']==0)
    exp_zero = sum((1-pp)**r['nres'] for r in sub)
    print(f"[전멸] {lab} 4건+ 진입 {len(sub)}일: 실제 전멸 {zero}일({100*zero/len(sub):.0f}%) vs 우연이면 {exp_zero:.1f}일({100*exp_zero/len(sub):.0f}%)  승률기준 {100*pp:.1f}%")

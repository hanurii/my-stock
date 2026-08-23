# -*- coding: utf-8 -*-
import json, glob, os, collections, statistics as st
ROOT='C:/Users/hanul/playground/my-stock/'
files=sorted(glob.glob(ROOT+'.cache/pdata/price_*.json'))
files=[f for f in files if '20251126'<=os.path.basename(f)[6:14]<='20260821']
print('파일',len(files), os.path.basename(files[0]), os.path.basename(files[-1]))
dates=[os.path.basename(f)[6:14] for f in files]
# fltRt 연쇄로 종목별 누적수익 인덱스
idx=collections.defaultdict(dict)   # code -> date -> cumulative factor
name={}
for f,d in zip(files,dates):
    try: p=json.load(open(f,encoding='utf-8'))
    except Exception: continue
    for c,v in p.items():
        try: fl=float(v.get('fltRt',0) or 0)
        except Exception: fl=0.0
        idx[c][d]=fl
        name[c]=v.get('itmsNm','')
json.dump({'dates':dates},open('C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/final/_d.json','w'))

def hold_ret(code, d_from, d_to=None):
    """d_from(진입일) 종가 -> d_to 종가. d_from 당일 등락률은 제외(그날 종가에 산 것으로 간주)"""
    ds=[d for d in dates if d> d_from and (d_to is None or d<=d_to)]
    f=1.0; n=0
    for d in ds:
        fl=idx.get(code,{}).get(d)
        if fl is None: continue
        f*= (1+fl/100); n+=1
    return (f-1)*100, n

j=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
EV=j['events']
targets={'005930':'삼성전자','000660':'SK하이닉스','009150':'삼성전기','402340':'SK스퀘어','034730':'SK','028260':'삼성물산'}
print('\n=== 초대형주: 규칙대로 팔았을 때 vs 그냥 들고 있었을 때(진입일~8/20) ===')
for e in EV:
    if e['code'] in targets:
        h,_=hold_ret(e['code'], e['entry_date'].replace('-',''))
        print(f"{e['name']:<10}{e['entry_date']} {e['result']:<5} 실현 {e['gain_at_resolve_pct']:+7.2f}%   그냥보유 {h:+8.2f}%")

print('\n=== 614건 전체: 규칙 vs 진입 후 끝까지 보유 ===')
rule=[];hold=[]
for e in EV:
    if e['result'] not in('win','loss'): continue
    h,n=hold_ret(e['code'], e['entry_date'].replace('-',''))
    if n<5: continue
    rule.append(e['gain_at_resolve_pct']); hold.append(h)
print('n=%d  규칙 평균 %+.2f%% 중앙 %+.2f%% | 보유 평균 %+.2f%% 중앙 %+.2f%%'%(
    len(rule),st.mean(rule),st.median(rule),st.mean(hold),st.median(hold)))
print('보유가 더 나은 비율 %.1f%%'%(100*sum(1 for a,b in zip(rule,hold) if b>a)/len(rule)))

# -*- coding: utf-8 -*-
"""02번 — 기각을 무너뜨려 본다. 날짜 정렬을 여러 가지로 바꿔 🔴가 최악이 되는 판이 있는가."""
import json, glob, collections, statistics as st, bisect
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
ev=[]
for f in sorted(glob.glob(BT+r"\bt_*.json")):
    ev += json.load(open(f,encoding='utf-8'))['events']
seen,U=set(),[]
for e in sorted(ev,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
CONF=[e for e in U if e['result'] in ('win','loss')]
AMB=[e for e in U if e['result']=='ambiguous']
reg=json.load(open(BT+r"\regime_long.json",encoding='utf-8'))
UP={d:v for d,v in zip(reg['dates'],reg['up_ew20'])}
KS={d:v for d,v in zip(reg['dates'],reg['up_ks20'])}
nas=json.load(open(BT+r"\nasdaq.json",encoding='utf-8'))['up']
nd=sorted(nas)
def nas_prev(day, strict=True, back=0):
    i=bisect.bisect_left(nd,day) if strict else bisect.bisect_right(nd,day)
    i=i-1-back
    return nas[nd[i]] if i>=0 else None
def cells(trades, regkey='ew', regdate='scan', nasmode=('entry',True,0)):
    out=collections.defaultdict(list)
    R = UP if regkey=='ew' else KS
    for e in trades:
        r = R.get(e['scan_date'] if regdate=='scan' else e['entry_date'])
        base = e['entry_date'] if nasmode[0]=='entry' else e['scan_date']
        n = nas_prev(base, nasmode[1], nasmode[2])
        if r is None or n is None: out['결측'].append(e); continue
        out[(bool(r),bool(n))].append(e)
    return out
LBL={(True,True):'🟢둘다좋음',(True,False):'🟡상승+나스닥↓',
     (False,True):'🟡조정+나스닥↑',(False,False):'🔴둘다나쁨'}
def show(c, tag):
    rows=[]
    for k in ((True,True),(True,False),(False,True),(False,False)):
        g=c.get(k,[])
        if not g: rows.append((LBL[k],0,0,0)); continue
        n=[net(e['gain_at_resolve_pct']) for e in g]
        rows.append((LBL[k],len(g),100*sum(1 for e in g if e['result']=='win')/len(g),st.mean(n)))
    red=rows[3][3]; others=st.mean([r[3] for r in rows[:3]])
    worst=min(rows,key=lambda r:r[3])[0]
    print("\n[%s] 결측 %d" % (tag, len(c.get('결측',[]))))
    for L,n_,w,m in rows: print("   %-16s n=%4d 승률 %5.1f%% 거래당 %+7.3f%%" % (L,n_,w,m))
    print("   S = 🔴 − 나머지평균 = %+.3f%%p · 최악 칸 = %s %s"
          % (red-others, worst, "★🔴가 최악(페이지 방향)" if worst.startswith('🔴') else ""))
    return red-others, worst

show(cells(CONF), "주 판정 재현 — 국면=scan_date up_ew20 · 나스닥=entry_date 직전 미국장")
print("\n" + "="*70)
print("무너뜨리기 1 — 날짜 정렬을 여러 가지로")
show(cells(CONF, nasmode=('entry',False,0)), "나스닥: entry_date 당일 포함(<=) ← 룩어헤드 가능")
show(cells(CONF, nasmode=('entry',True,1)), "나스닥: 한 칸 더 뒤로(직전의 직전)")
show(cells(CONF, nasmode=('scan',True,0)), "나스닥: scan_date 기준 직전")
show(cells(CONF, nasmode=('scan',False,0)), "나스닥: scan_date 당일 포함(<=)")
show(cells(CONF, regdate='entry'), "국면: entry_date 기준 up_ew20")
show(cells(CONF, regkey='ks'), "국면: 코스피 20일선(up_ks20)")
print("\n" + "="*70)
print("무너뜨리기 2 — M1(매수 당일 손절 74건)을 넣으면 칸 배치가 바뀌는가")
paths={}
for y in (2021,2022,2023,2024,2025,2026):
    for p in json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))['paths']:
        paths[(p['scan_date'],p['code'],p['pattern'])]=p
AMB2=[]
for e in AMB:
    p=paths[(e['scan_date'],e['code'],e['pattern'])]
    e2=dict(e); e2['gain_at_resolve_pct']=(p['c'][0]/p['entry_price']-1)*100; e2['result']='loss'
    AMB2.append(e2)
c=cells(CONF+AMB2)
print("  ambiguous 74건의 칸 분포:", {LBL[k]: sum(1 for e in AMB2 if (bool(UP.get(e['scan_date'])), bool(nas_prev(e['entry_date']))) == k) for k in LBL})
show(c, "M1 적용판 (3,755건)")
print("\n" + "="*70)
print("무너뜨리기 3 — 9개월 구간(페이지가 만들어진 구간)")
show(cells([e for e in CONF if e['entry_date']>='2025-11-26']), "9개월 · 주 정렬")
show(cells([e for e in CONF if e['entry_date']>='2025-11-26'], nasmode=('entry',False,0)), "9개월 · 당일 포함(<=)")

print("\n" + "="*70)
print("무너뜨리기 4 — 칸별 한 해 제거 (연도 = scan_date)")
c=cells(CONF)
for k in ((True,True),(True,False),(False,True),(False,False)):
    g=c[k]; base=st.mean(net(e['gain_at_resolve_pct']) for e in g)
    row=[]
    for y in ('2021','2022','2023','2024','2025','2026'):
        sub=[e for e in g if e['scan_date'][:4]!=y]
        row.append(st.mean(net(e['gain_at_resolve_pct']) for e in sub))
    print("  %-16s 전체 %+7.3f%%  한해제거 %s  → 최악 %+.3f%% [%s] %s"
          % (LBL[k], base, " ".join("%+6.2f"%v for v in row), min(row),
             ('2021','2022','2023','2024','2025','2026')[row.index(min(row))],
             "⚠부호뒤집힘" if base>0 and min(row)<0 else ""))
print("\n무너뜨리기 5 — 조정 국면 안에서 나스닥 축의 부호가 정렬에 따라 뒤집히는가")
for tag,nm in (("주 정렬",('entry',True,0)),("한 칸 뒤",('entry',True,1)),
               ("scan 기준",('scan',True,0)),("당일포함(룩어헤드)",('entry',False,0))):
    cc=cells(CONF, nasmode=nm)
    a=st.mean(net(e['gain_at_resolve_pct']) for e in cc[(False,True)])
    b=st.mean(net(e['gain_at_resolve_pct']) for e in cc[(False,False)])
    print("  %-18s 조정+나스닥↑ %+7.3f%% vs 조정+나스닥↓ %+7.3f%%  → %s"
          % (tag,a,b,"↑가 나쁨" if a<b else "★↓가 나쁨(부호 반전)"))
cc=cells(CONF, regkey='ks')
a=st.mean(net(e['gain_at_resolve_pct']) for e in cc[(False,True)])
b=st.mean(net(e['gain_at_resolve_pct']) for e in cc[(False,False)])
print("  %-18s 조정+나스닥↑ %+7.3f%% vs 조정+나스닥↓ %+7.3f%%" % ("코스피20MA",a,b))
print("\n합산 검산: 조정 %d건 %+.3f%% · 상승 %d건 %+.3f%%"
      % (len(c[(False,True)])+len(c[(False,False)]),
         st.mean(net(e['gain_at_resolve_pct']) for e in c[(False,True)]+c[(False,False)]),
         len(c[(True,True)])+len(c[(True,False)]),
         st.mean(net(e['gain_at_resolve_pct']) for e in c[(True,True)]+c[(True,False)])))

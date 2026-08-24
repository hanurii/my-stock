# -*- coding: utf-8 -*-
import json,statistics,io,sys
alld=json.load(open('scripts/_min3_0624_for0623sig.json',encoding='utf-8'))
out=io.StringIO()
def p(*x): print(*x,file=out)
W=20; COST=0.5

def classify_entry(bars):
    """returns (branch, entry_index, entry_price, target) or None(skip)"""
    if len(bars)<3: return None
    c0=bars[0]; body=(c0['c']/c0['o']-1)*100
    if c0['c']>c0['o'] and body<3:          # A 작은양봉 → 즉시진입 목표10
        return ('A',1,bars[1]['o'],10.0)
    elif body>=3:                            # B 장대양봉 → 매수안함(스킵). 단 참고용 계산은 따로.
        return ('B',None,None,None)
    else:                                    # C 음봉 → 상쇄+거래량마름+변동성축소 대기, 목표6
        for j in range(1,W):
            if j>=len(bars): break
            x=bars[j]
            if x['c']>x['o'] and x['c']>c0['o'] and x['v']<c0['v'] and (x['h']-x['l'])<(c0['h']-c0['l']):
                return ('C',j,x['c'],6.0)
        return ('Cskip',None,None,None)

def path(bars, ei, e, target, stop):
    tp=e*(1+target/100); sl=e*(1+stop/100)
    for k in range(ei+1,len(bars)):
        x=bars[k]
        if x['l']<=sl: return stop,'손절'
        if x['h']>=tp: return target,'익절'
    return (bars[-1]['c']/e-1)*100,'종가청산'

# pre-classify
cls={nm:classify_entry(d['bars']) for nm,d in alld.items()}
nA=sum(1 for v in cls.values() if v and v[0]=='A')
nB=sum(1 for v in cls.values() if v and v[0]=='B')
nC=sum(1 for v in cls.values() if v and v[0]=='C')
nCs=sum(1 for v in cls.values() if v and v[0]=='Cskip')
p(f"분류: A(작은양봉) {nA} / B(장대양봉,매수안함) {nB} / C(음봉→진입) {nC} / C인데 조건미달 스킵 {nCs}  (총 {len(alld)})")
p("")

def runall(stop):
    rA=[];rC=[]
    for nm,d in alld.items():
        c=cls[nm]
        if not c: continue
        br,ei,e,tg=c
        if br=='A': r,_=path(d['bars'],ei,e,tg,stop); rA.append(r-COST)
        elif br=='C': r,_=path(d['bars'],ei,e,tg,stop); rC.append(r-COST)
    return rA,rC

def line(name,rets):
    if not rets: return f"  {name}: 없음"
    w=sum(1 for x in rets if x>0)
    return f"  {name}: {len(rets)}건 평균 {statistics.mean(rets):+.2f}%/건 승률 {100*w/len(rets):.0f}% 합계 {sum(rets):+.1f}%p"

p("="*72)
p("【손절선별 결과】  A=작은양봉(목표10%) · C=음봉진입(목표6%) · B는 매수 안 함")
p("  (6/23 신호 → 6/24 매매, 미래참조·선택편향 없음, 비용 0.5% 차감)")
for stop in [-2.5,-4,-6,-8]:
    rA,rC=runall(stop)
    allr=rA+rC
    w=sum(1 for x in allr if x>0)
    bе6=abs(stop)/(6+abs(stop))*100; be10=abs(stop)/(10+abs(stop))*100
    p("-"*72)
    p(f"손절 {stop:+.1f}%   (본전승률: 목표10%→{be10:.0f}%, 목표6%→{bе6:.0f}%)")
    p(line("A 작은양봉",rA))
    p(line("C 음봉진입",rC))
    p(f"  ▶ A+C 합산: {len(allr)}건 평균 {statistics.mean(allr):+.2f}%/건 승률 {100*w/len(allr):.0f}% 합계 {sum(allr):+.1f}%p")
p("="*72)

# 참고: B(장대양봉)를 만약 즉시 시초가 진입했다면 (매수 안 하길 잘했는지 확인)
p("\n[참고] B 장대양봉을 '매수 안 함'이 옳았나 — 만약 다음봉 시가 진입(목표10/손절-2.5)했다면:")
rB=[]
for nm,d in alld.items():
    if cls[nm] and cls[nm][0]=='B':
        r,_=path(d['bars'],1,d['bars'][1]['o'],10.0,-2.5); rB.append(r-COST)
if rB:
    w=sum(1 for x in rB if x>0)
    p(f"  {len(rB)}건 평균 {statistics.mean(rB):+.2f}%/건 승률 {100*w/len(rB):.0f}% → {'매수 안 한 게 이득' if statistics.mean(rB)<0 else '오히려 샀어야'}")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))

# -*- coding: utf-8 -*-
import json,glob,os,random,collections,statistics as st
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
def fee(g,slip=0.0):
    """slip: 손절 체결이 이만큼 더 밀린다(%p)."""
    if g<0: g-=slip
    return ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
def load(pat,fol='exit/'):
    ev=[]
    for f in sorted(glob.glob(B+fol+pat)):
        ev+=[e for e in json.load(open(f,encoding='utf-8'))['events'] if e['result'] in ('win','loss')]
    seen=set(); U=[]
    for e in sorted(ev,key=lambda x:(x['entry_date'],x['code'])):
        k=(e['scan_date'],e['code'],e['pattern'])
        if k not in seen: seen.add(k); U.append(e)
    return U
def sim(ev,seed,slots=5,slip=0.0):
    byday=collections.defaultdict(list)
    for e in ev: byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]; peak=1.0; mdd=0.0
    for d in sorted(set(list(byday)+[e['resolve_date'] for e in ev])):
        for rd,e,wg in [h for h in held if h[0]<=d]:
            eq+=wg*fee(e['gain_at_resolve_pct'],slip)/100
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e,eq/slots))
        peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return (eq-1)*100, mdd*100
A=load('bt_*.json',''); C=load('t30s7_*.json'); D=load('t20s7_*.json'); E=load('t30s10_*.json')

print("① 연도별 거래당 순수익 — 일관성")
print(f"{'연도':<7}{'+20/-10':>11}{'+30/-10':>11}{'+20/-7':>11}{'+30/-7':>11}")
V={'+20/-10':A,'+30/-10':E,'+20/-7':D,'+30/-7':C}
wins=collections.Counter()
for y in ('2021','2022','2023','2024','2025','2026'):
    row=f"{y:<7}"; base=None
    for k,ev in V.items():
        g=[fee(e['gain_at_resolve_pct']) for e in ev if e['scan_date'][:4]==y]
        v=st.mean(g); row+=f"{v:>+10.2f}%"
        if k=='+20/-10': base=v
        elif v>base: wins[k]+=1
    print(row)
print(f"  현행 대비 우세 연수: " + '  '.join(f"{k} {wins[k]}/6" for k in ('+30/-10','+20/-7','+30/-7')))

print("\n② 짝비교 (같은 난수 400회, 슬롯5 자산곡선)")
N=400
for lab,ev in (('+30/-10',E),('+20/-7',D),('+30/-7',C)):
    d=sorted(sim(ev,i)[0]-sim(A,i)[0] for i in range(N))
    w=sum(1 for x in d if x>0)
    print(f"  {lab}: 현행보다 나은 경우 {w}/{N} ({w/N*100:.0f}%)  차이 중앙 {d[N//2]:+.1f}%p  (5~95%: {d[N//20]:+.0f}~{d[N-N//20]:+.0f}%p)")

print("\n③ 손절 슬리피지 — 시장가 체결이 밀리면")
print(f"{'슬리피지':<10}{'+20/-10':>12}{'+30/-10':>12}{'+20/-7':>12}{'+30/-7':>12}")
for slip in (0.0,0.5,1.0,2.0):
    row=f"{slip:>+5.1f}%p   "
    for k,ev in V.items():
        r=sorted(sim(ev,i,slip=slip)[0] for i in range(100))
        row+=f"{r[50]:>+11.1f}%"
    print(row)

print("\n④ 손절 -7% 는 얼마나 자주 맞나 (손절 비율)")
for k,ev in V.items():
    l=sum(1 for e in ev if e['result']=='loss')
    print(f"  {k}: 손절 {l}/{len(ev)} = {l/len(ev)*100:.1f}%   보유일 중앙 {st.median([e['days_held'] for e in ev]):.0f}")

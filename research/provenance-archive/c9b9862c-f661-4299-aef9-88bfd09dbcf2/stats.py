# -*- coding: utf-8 -*-
import sys, json, os, collections, statistics, random, math
SCR = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"
sys.path.insert(0, SCR)
from lib import load
rows = json.load(open(os.path.join(SCR,"rows.json"), encoding="utf-8"))
sc = load("scorecard.json"); T = {(t['code'],t['open_date']):t for t in sc['trades']}

# --- 1. 손절 미준수 비용 ---
cost=0; details=[]
for t in sc['trades']:
    if t.get('stop_violation') and t.get('stop'):
        intend = 100*(t['stop']/t['avg_buy']-1)
        slip = t['gross_pct'] - intend
        notional = t['avg_buy']*t['buy_qty']
        c = notional*slip/100
        cost += c; details.append((t['name'], round(slip,2), round(c)))
print("1) 손절선 하회 체결 6건 — 의도 손절가 대비 초과 손실")
for n,s,c in sorted(details,key=lambda x:x[2]): print(f"   {n}: {s:+.2f}%p  {c:,.0f}원")
print(f"   합계 {cost:,.0f}원")
print()

# --- 2. 같은날 짝비교: 규칙밖(a+b1) vs 규칙안 ---
def sameday(flagfn, label):
    byd=collections.defaultdict(lambda: ([],[]))
    for r in rows:
        (byd[r['d']][0] if flagfn(r) else byd[r['d']][1]).append(r)
    days=[(d,a,b) for d,(a,b) in byd.items() if a and b]
    pos=neg=tie=0; diffs=[]
    for d,a,b in days:
        wa=sum(1 for x in a if x['outcome']=='win')/len(a)
        wb=sum(1 for x in b if x['outcome']=='win')/len(b)
        diffs.append(wa-wb)
        if wa>wb: pos+=1
        elif wa<wb: neg+=1
        else: tie+=1
    n=pos+neg
    p = sum(math.comb(n,k) for k in range(0,min(pos,neg)+1))/2**n*2 if n else 1.0
    p = min(1.0,p)
    print(f"2) 같은날 짝비교 [{label}]: 양쪽 다 있는 날 {len(days)}일 (동률 {tie}) "
          f"플래그쪽 승 {pos}일 · 패 {neg}일 · 부호검정 p={p:.3f} · 평균승률차 {100*statistics.mean(diffs) if diffs else 0:+.1f}%p")
    return days

sameday(lambda r: (not r['listed']) or (not r['detected']), "규칙밖(리스트없음+패턴미검출)")
sameday(lambda r: not r['entry_ready'], "entry_ready 아님")
print()

# --- 3. Fisher exact: 규칙밖 vs 규칙안 승률 ---
def fisher(a,b,c,d):
    def C(n,k): return math.comb(n,k)
    n=a+b+c+d; tot=0; obs=C(a+b,a)*C(c+d,c)/C(n,a+c)
    for i in range(0, min(a+b,a+c)+1):
        j=a+b-i; k=a+c-i; l=c+d-k
        if j<0 or k<0 or l<0: continue
        pr=C(a+b,i)*C(c+d,k)/C(n,a+c)
        if pr<=obs+1e-12: tot+=pr
    return tot
out=[r for r in rows if (not r['listed']) or (not r['detected'])]
ins=[r for r in rows if r['listed'] and r['detected']]
ow=sum(1 for r in out if r['outcome']=='win'); iw=sum(1 for r in ins if r['outcome']=='win')
print(f"3) 규칙밖 {len(out)}건 승{ow} ({100*ow/len(out):.1f}%) vs 규칙안 {len(ins)}건 승{iw} ({100*iw/len(ins):.1f}%)  Fisher p={fisher(ow,len(out)-ow,iw,len(ins)-iw):.4f}")
print(f"   손익합: 규칙밖 {sum(r['net_won'] for r in out):,.0f}원 / 규칙안 {sum(r['net_won'] for r in ins):,.0f}원")
print()

# --- 4. 8월(상승국면)만 따로: 승률은 높은데 왜 손실인가 ---
aug=[r for r in rows if r['d']>='2026-08-01']
w=[r for r in aug if r['outcome']=='win']; l=[r for r in aug if r['outcome']=='loss']
print(f"4) 8월 24건: 승 {len(w)}({100*len(w)/len(aug):.1f}%) 평균이익 {statistics.mean([x['net_pct'] for x in w]):+.2f}% / "
      f"패 {len(l)} 평균손실 {statistics.mean([x['net_pct'] for x in l]):+.2f}% → 손익비 {abs(statistics.mean([x['net_pct'] for x in w])/statistics.mean([x['net_pct'] for x in l])):.2f}")
be = -statistics.mean([x['net_pct'] for x in l])/(statistics.mean([x['net_pct'] for x in w])-statistics.mean([x['net_pct'] for x in l]))
print(f"   현재 손익비의 손익분기 승률 = {100*be:.1f}%  (실제 {100*len(w)/len(aug):.1f}%)")
print(f"   손익비 2.0(+20/-10)이면 손익분기 33.3% → 8월 41.7%면 흑자")
print()

# --- 5. 각 이탈 제거 시 손익 개선(주변효과) ---
base=sum(r['net_won'] for r in rows)
def marginal(fn,label):
    keep=[r for r in rows if not fn(r)]
    d=sum(r['net_won'] for r in keep)-base
    w=sum(1 for r in keep if r['outcome']=='win')
    print(f"   {label}: 제거 {len(rows)-len(keep)}건 → 남은 {len(keep)}건 승률 {100*w/len(keep):.1f}% 손익 {sum(r['net_won'] for r in keep):,.0f}원 (개선 {d:+,.0f}원)")
print(f"5) 이탈 유형별 제거 시 (기준 {base:,.0f}원)")
marginal(lambda r: not r['listed'], "(a) 리스트 밖")
marginal(lambda r: r['listed'] and not r['detected'], "(b1) 패턴 미검출")
marginal(lambda r: (not r['listed']) or (not r['detected']), "(a+b1) 규칙 밖 전부")
marginal(lambda r: not r['entry_ready'], "(a+b1+b2) entry_ready 아닌 것 전부")
marginal(lambda r: not r['up'], "(e) 조정국면 매수")
marginal(lambda r: (not r['up']) or (not r['detected']), "(e)+(b1) 둘 다")

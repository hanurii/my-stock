import sys, math, random, statistics as s
sys.path.insert(0,'.')
from lib import *
from collections import defaultdict
random.seed(20260822)

d, ev = load()
R = resolved(ev)

# ---------- 1) 같은날 순위 퍼센타일 (국면 오염 제거) ----------
byday=defaultdict(list)
for e in R: byday[e['scan_date']].append(e)
for dte,lst in byday.items():
    n=len(lst)
    if n<2:
        for e in lst: e['to_pct']=None
        continue
    srt=sorted(lst,key=lambda x:x['turnover_eok'])
    for i,e in enumerate(srt): e['to_pct']=i/(n-1)   # 0=그날 최저 거래대금, 1=최고

multi=[e for e in R if e.get('to_pct') is not None]
print("같은날 2건 이상인 날의 거래 수:", len(multi), " / 날 수", sum(1 for l in byday.values() if len(l)>=2))
bands=[(0,0.25,'하위25%'),(0.25,0.5,'25~50%'),(0.5,0.75,'50~75%'),(0.75,1.01,'상위25%')]
print("\n[같은날 거래대금 순위 백분위별 성적]")
for lo,hi,lab in bands:
    sub=[e for e in multi if lo<=e['to_pct']<hi]
    w,n=wr(sub); r,_=exp_ret(sub)
    print(f"  {lab:8s} n={n:3d} 승률 {w:5.1f}% 실현평균 {r:+.2f}%")

# ---------- 2) 날짜 고정 순열검정: 승자의 평균 거래대금-순위 ----------
def stat_turnover(events):
    ws=[e['to_pct'] for e in events if e['result']=='win']
    return sum(ws)/len(ws)
obs=stat_turnover(multi)
cnt=0; N=5000
daygroups=list(defaultdict(list).values())
g=defaultdict(list)
for e in multi: g[e['scan_date']].append(e)
groups=list(g.values())
for _ in range(N):
    tot=0.0; k=0
    for lst in groups:
        res=[e['result'] for e in lst]
        random.shuffle(res)
        for e,rr in zip(lst,res):
            if rr=='win': tot+=e['to_pct']; k+=1
    if tot/k >= obs: cnt+=1
p_perm=(cnt+1)/(N+1)
print(f"\n[날짜 내 결과 셔플 순열검정 5000회] 승자 평균 거래대금순위 관측 {obs:.3f} vs 귀무 0.5 → 단측 p={p_perm:.4f}")

# ---------- 3) 전후반 분할 ----------
print("\n[전후반 분할 (2026-03-25 기준)]")
for lab, sel in (("전반(~2026-03-24)", lambda e: e['scan_date']<'2026-03-25'),
                 ("후반(2026-03-25~)", lambda e: e['scan_date']>='2026-03-25')):
    sub=[e for e in multi if sel(e)]
    hi=[e for e in sub if e['to_pct']>=0.5]; lo=[e for e in sub if e['to_pct']<0.5]
    print(f"  {lab}: 상위절반 {wr(hi)} / 하위절반 {wr(lo)}")
    # 절대컷
    sub2=[e for e in R if sel(e)]
    a=[e for e in sub2 if e['turnover_eok']>=30]; b=[e for e in sub2 if e['turnover_eok']<30]
    print(f"          거래대금>=30억 {wr(a)} / <30억 {wr(b)}")

# ---------- 4) 월 층화 잔여효과 ----------
print("\n[월 층화: 월별 상위절반-하위절반 승률차]")
bym=defaultdict(list)
for e in multi: bym[e['month']].append(e)
diffs=[]
for m in sorted(bym):
    sub=bym[m]
    hi=[e for e in sub if e['to_pct']>=0.5]; lo=[e for e in sub if e['to_pct']<0.5]
    if len(hi)<5 or len(lo)<5: 
        print(f"  {m}: 표본부족 (hi{len(hi)}/lo{len(lo)})"); continue
    dw=wr(hi)[0]-wr(lo)[0]; diffs.append(dw)
    print(f"  {m}: {wr(hi)[0]:5.1f}%(n{len(hi)}) - {wr(lo)[0]:5.1f}%(n{len(lo)}) = {dw:+6.1f}%p")
print(f"  월 부호: 양수 {sum(1 for x in diffs if x>0)} / 음수 {sum(1 for x in diffs if x<0)} (중앙 {s.median(diffs):+.1f}%p)")

# ---------- 5) 종목 블록 순열검정 ----------
print("\n[종목 블록 순열검정 3000회 — 상위절반 vs 하위절반 승률차]")
hi=[e for e in multi if e['to_pct']>=0.5]; lo=[e for e in multi if e['to_pct']<0.5]
obs_d = wr(hi)[0]-wr(lo)[0]
bycode=defaultdict(list)
for e in multi: bycode[e['code']].append(e)
codes=list(bycode)
cnt=0; N=3000
for _ in range(N):
    # 종목 단위로 결과 블록을 다른 종목에 배정 (블록 구조 보존)
    blocks=[[x['result'] for x in bycode[c]] for c in codes]
    random.shuffle(blocks)
    hw=hl=lw=ll=0
    for c,blk in zip(codes,blocks):
        evs=bycode[c]
        # 길이 다를 수 있으니 순환 배정
        for i,e in enumerate(evs):
            rr=blk[i%len(blk)]
            if e['to_pct']>=0.5:
                hw+= rr=='win'; hl+= rr=='loss'
            else:
                lw+= rr=='win'; ll+= rr=='loss'
    dd=100*hw/(hw+hl)-100*lw/(lw+ll)
    if dd>=obs_d: cnt+=1
print(f"  관측 승률차 {obs_d:+.1f}%p, 순열 단측 p={(cnt+1)/(N+1):.4f}")

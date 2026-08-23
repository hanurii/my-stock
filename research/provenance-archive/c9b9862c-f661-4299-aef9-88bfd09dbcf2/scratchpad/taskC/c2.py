import json,os,collections,math
S=os.environ['SCRATCH']
rows=[r for r in json.load(open(os.path.join(S,'taskC','joinedC.json'),encoding='utf-8')) if r['outcome']]
LAB={"1":"① 150·200일선","2":"② 150>200일선","3":"③ 200일선 상승","4":"④ 50일선 정렬","5":"⑤ 50일선","6":"⑥ 52주저가","7":"⑦ 52주고가","8":"⑧ RS"}
def stats(rs):
    n=len(rs); s=sum(1 for r in rs if r['outcome']=='stop'); t=sum(1 for r in rs if r['outcome']=='target')
    o=n-s-t
    mg=[r['max_gain_pct'] for r in rs if r['max_gain_pct'] is not None]
    cr=[r['cur_ret_pct'] for r in rs if r['cur_ret_pct'] is not None]
    return dict(n=n,stop=s,target=t,open=o,stop_r=100*s/n,tgt_r=100*t/n,
                stop_r_res=100*s/(s+t) if s+t else None,
                mg=sum(mg)/len(mg) if mg else None, cr=sum(cr)/len(cr) if cr else None)
print('=== 전체 ===')
a=stats(rows); print(a)
print()
print('=== 1) tightest 조건별 코호트 (전체 추천행 %d) ==='%len(rows))
print(f"{'조건':<16}{'n':>5}{'손절':>6}{'+20%':>6}{'미결':>6}{'손절률':>8}{'+20%율':>8}{'결정론손절률':>12}{'평균MFE':>9}{'평균수익':>9}")
by=collections.defaultdict(list)
for r in rows: by[r['tightest']].append(r)
for k in '12345678':
    rs=by.get(k,[])
    if not rs: continue
    d=stats(rs)
    print(f"{LAB[k]:<16}{d['n']:>5}{d['stop']:>6}{d['target']:>6}{d['open']:>6}{d['stop_r']:>8.1f}{d['tgt_r']:>8.1f}"
          f"{(d['stop_r_res'] if d['stop_r_res'] is not None else float('nan')):>12.1f}{d['mg']:>9.1f}{d['cr']:>9.1f}")
# 종목 단위(첫 등장) 중복제거
print()
first={}
for r in sorted(rows,key=lambda x:x['date']):
    first.setdefault(r['code'],r)
u=list(first.values())
print('=== 1b) 종목 첫등장 1행만 (n=%d) ==='%len(u))
byu=collections.defaultdict(list)
for r in u: byu[r['tightest']].append(r)
for k in '12345678':
    rs=byu.get(k,[])
    if not rs: continue
    d=stats(rs)
    print(f"{LAB[k]:<16}{d['n']:>5}{d['stop']:>6}{d['target']:>6}{d['open']:>6}{d['stop_r']:>8.1f}{d['tgt_r']:>8.1f}{d['mg']:>9.1f}{d['cr']:>9.1f}")
print('전체(종목단위)',stats(u))

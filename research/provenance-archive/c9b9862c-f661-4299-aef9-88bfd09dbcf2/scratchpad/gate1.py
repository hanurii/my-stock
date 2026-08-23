# -*- coding: utf-8 -*-
"""1차 관문: 같은 스캔일 안에서만 비교 → 날짜별 부호검정."""
import json, sys, math, random
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(sys.argv[0]).parent
rows = json.loads((SCR/"events_feat.json").read_text(encoding="utf-8"))
R = [r for r in rows if r["result"] in ("win","loss")]
print(f"결착 {len(R)}건 · 고유종목 {len({r['code'] for r in R})} · 스캔일 {len({r['scan_date'] for r in R})}")

def binom_two_sided(k, n, p=0.5):
    if n == 0: return 1.0
    def pmf(i): return math.comb(n,i)*p**i*(1-p)**(n-i)
    obs = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n+1) if pmf(i) <= obs*(1+1e-9)))

def wr(g): return sum(1 for x in g if x["result"]=="win")/len(g)*100 if g else None
def ev(g):
    # +20/-10 손익비 → 승 +20, 패 -10 (실제 gain_at_resolve 사용)
    v=[x.get("gain_at_resolve_pct") for x in g if x.get("gain_at_resolve_pct") is not None]
    return sum(v)/len(v) if v else None

def same_day_median(rows_, key, min_n=2):
    """그날 중앙값으로 상/하 분할. 값이 다 같은 날은 제외."""
    byday = defaultdict(list)
    for r in rows_:
        if r.get(key) is not None:
            byday[r["scan_date"]].append(r)
    diffs, hi_all, lo_all = [], [], []
    for d, g in byday.items():
        if len(g) < min_n: continue
        vals = sorted(x[key] for x in g)
        med = vals[len(vals)//2] if len(vals)%2 else (vals[len(vals)//2-1]+vals[len(vals)//2])/2
        hi = [x for x in g if x[key] > med]; lo = [x for x in g if x[key] <= med]
        if not hi or not lo:   # 동점 처리: >중앙 / <=중앙 로 갈리지 않으면 스킵
            hi = [x for x in g if x[key] >= med]; lo = [x for x in g if x[key] < med]
        if not hi or not lo: continue
        diffs.append((d, wr(hi)-wr(lo), len(hi), len(lo)))
        hi_all += hi; lo_all += lo
    return diffs, hi_all, lo_all

def same_day_cat(rows_, key, a_pred):
    byday = defaultdict(list)
    for r in rows_:
        if r.get(key) is not None: byday[r["scan_date"]].append(r)
    diffs, hi_all, lo_all = [], [], []
    for d, g in byday.items():
        hi=[x for x in g if a_pred(x)]; lo=[x for x in g if not a_pred(x)]
        if not hi or not lo: continue
        diffs.append((d, wr(hi)-wr(lo), len(hi), len(lo)))
        hi_all+=hi; lo_all+=lo
    return diffs, hi_all, lo_all

def sign_report(diffs):
    pos=sum(1 for _,x,_,_ in diffs if x>0); neg=sum(1 for _,x,_,_ in diffs if x<0)
    tie=len(diffs)-pos-neg
    p=binom_two_sided(pos,pos+neg)
    med=sorted(x for _,x,_,_ in diffs)
    med=(med[len(med)//2] if med else 0)
    return dict(days=len(diffs), usable=pos+neg, pos=pos, neg=neg, tie=tie, p=round(p,4),
                median_diff=round(med,1))

def within_day_perm(hi_all, lo_all, n_iter=3000, seed=7):
    """같은 날 안에서 라벨을 섞는 층화 순열검정(부호검정 보완, 더 강한 검정력)."""
    rnd=random.Random(seed)
    byday=defaultdict(lambda: [[],[]])
    for x in hi_all: byday[x["scan_date"]][0].append(x)
    for x in lo_all: byday[x["scan_date"]][1].append(x)
    def stat(assign):
        h=[];l=[]
        for d,(H,L) in byday.items():
            pool=H+L; nh=len(H)
            idx=assign[d]
            h+= [pool[i] for i in idx[:nh]]; l+=[pool[i] for i in idx[nh:]]
        return wr(h)-wr(l)
    base={d: list(range(len(H)+len(L))) for d,(H,L) in byday.items()}
    obs=stat(base)
    cnt=0
    for _ in range(n_iter):
        a={}
        for d,(H,L) in byday.items():
            idx=list(range(len(H)+len(L))); rnd.shuffle(idx); a[d]=idx
        if abs(stat(a))>=abs(obs)-1e-9: cnt+=1
    return round(obs,2), round((cnt+1)/(n_iter+1),4)

CONT = ["rs","entry_price","turnover_eok","cap_eok","dist_52wh_pct","gain_52wl_pct",
        "pct_to_pivot","base_len","base_depth","ext_50ma_pct","ext_150ma_pct","ext_200ma_pct",
        "ret_5d_pct","ret_20d_pct","ret_60d_pct","ret_120d_pct","atr_pct","gap_up_pct",
        "dryup","n_contractions","tightness","coil_len","coil_dry_mean","coil_min_dry","coil_range_pct"]
res={}
print("\n=== 1차 관문: 같은날 중앙값 분할 부호검정 (전체 결착 580) ===")
print(f"{'요인':<18}{'쓸수있는날':>9}{'+':>5}{'-':>5}{'p':>8}{'중앙차':>8}{'상WR':>7}{'하WR':>7}{'n상/n하':>12}")
for k in CONT:
    diffs,hi,lo = same_day_median(R,k)
    if not diffs: continue
    s=sign_report(diffs)
    res[k]=dict(s=s, hi_wr=wr(hi), lo_wr=wr(lo), nhi=len(hi), nlo=len(lo))
    print(f"{k:<18}{s['usable']:>9}{s['pos']:>5}{s['neg']:>5}{s['p']:>8.4f}{s['median_diff']:>8.1f}"
          f"{(wr(hi) or 0):>7.1f}{(wr(lo) or 0):>7.1f}{f'{len(hi)}/{len(lo)}':>12}")

print("\n=== 범주형 ===")
cats = [("pattern_VCP","pattern",lambda x:x["pattern"]=="VCP"),
        ("market_KOSPI","market",lambda x:x["market"]=="KOSPI"),
        ("sector_tagged(룩어헤드주의)","code",lambda x:x.get("sector_short") is not None)]
for nm,key,pred in cats:
    diffs,hi,lo = same_day_cat(R,key,pred)
    if not diffs: continue
    s=sign_report(diffs)
    res[nm]=dict(s=s,hi_wr=wr(hi),lo_wr=wr(lo),nhi=len(hi),nlo=len(lo))
    print(f"{nm:<26}{s['usable']:>7}{s['pos']:>5}{s['neg']:>5}{s['p']:>8.4f}{s['median_diff']:>8.1f}"
          f"{(wr(hi) or 0):>7.1f}{(wr(lo) or 0):>7.1f}{f'{len(hi)}/{len(lo)}':>12}")

(SCR/"gate1_res.json").write_text(json.dumps(res,ensure_ascii=False,indent=1),encoding="utf-8")

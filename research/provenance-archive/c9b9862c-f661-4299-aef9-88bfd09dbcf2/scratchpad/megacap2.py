import json, os, glob

PD = r"C:/Users/hanul/playground/my-stock/.cache/pdata"
files = sorted(glob.glob(os.path.join(PD, "price_*.json")))
dates_all = [os.path.basename(f)[6:14] for f in files]
START, END = "20251126", "20260821"
sel = [(d,f) for d,f in zip(dates_all,files) if START <= d <= END]
DATES = [d for d,_ in sel]

def load(f):
    with open(f, encoding='utf-8') as fp:
        return json.load(fp)

days = []
for d,f in sel:
    days.append((d, load(f)))
print("days", len(days), days[0][0], days[-1][0])

# ---- confirm pit index cw over this window
pit = json.load(open(r'C:/Users/hanul/AppData/Local/Temp/pit_index.json', encoding='utf-8'))
pd_map = {x.replace('-',''):i for i,x in enumerate(pit['dates'])}
i0, i1 = pd_map[DATES[0]], pd_map[DATES[-1]]
print("PIT cw window ret %%: %.2f" % ((pit['cw'][i1]/pit['cw'][i0]-1)*100))
print("PIT ew window ret %%: %.2f" % ((pit['ew'][i1]/pit['ew'][i0]-1)*100))

# ---- rebuild cap-weighted index from pdata with prev-day cap weights, fltRt chain
# daily index return R_t = sum_i w_{i,t-1} * r_{i,t}, over stocks present both days
contrib = {}   # code -> linked contribution to total index return
names = {}
cum = 1.0
Rs = []
for t in range(1, len(days)):
    dprev, prev = days[t-1]
    dcur, cur = days[t]
    # weights from prev day cap
    common = [c for c in cur if c in prev]
    caps = {}
    tot = 0.0
    for c in common:
        mc = prev[c].get('market_cap_eok')
        if mc is None or mc <= 0:
            continue
        caps[c] = mc
        tot += mc
    R = 0.0
    parts = {}
    for c, mc in caps.items():
        r = cur[c].get('fltRt')
        if r is None:
            continue
        w = mc/tot
        p = w * (r/100.0)
        parts[c] = p
        R += p
    for c,p in parts.items():
        contrib[c] = contrib.get(c, 0.0) + p*cum
        names[c] = cur[c].get('itmsNm')
    cum *= (1+R)
    Rs.append(R)
print("REBUILT cap-weighted index total ret %%: %.2f" % ((cum-1)*100))
print("sum of contributions %%: %.2f" % (sum(contrib.values())*100))

json.dump({'contrib':contrib,'names':names,'total':cum-1},
          open(r'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/contrib.json','w',encoding='utf-8'), ensure_ascii=False)

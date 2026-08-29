import importlib.util as _u, random, statistics as st, sys
from pathlib import Path
HERE = Path("research/handoff/scripts").resolve(); sys.path.insert(0, str(HERE))
import pyr_trigger as pt
_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py"); r102 = _u.module_from_spec(_s); _s.loader.exec_module(r102)
_t = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py"); r103 = _u.module_from_spec(_t); _t.loader.exec_module(r103)
r91, f92a, _ord = r102.r91, r102.f92a, r102._ord
(_a,_b,by2), miss, _ = r91.load_ladder(r102.YEARS, r102.D0, r102.D1, "91-monthly-us-full.json", use_ext=False)
fund, ixf = f92a.load(); ix = {f:i for i,f in enumerate(ixf)}
G = {"조건통과": [], "조건탈락": [], "자료없음": []}
for y in sorted(by2):
    for p in by2[y]:
        rec = fund.get(p["code"]); arq = (rec or {}).get("ARQ") or []
        r = f92a.asof(arq, p["entry_date"]) if arq else None
        v = None if (r is None or _ord(p["entry_date"]) - _ord(r[0]) > r102.STALE_MAX) else r103.judge(arq, arq.index(r), ix, 1, 2)
        t = pt.resolve_trade(p, ft="limit", fs="market", stop=r91.STOP, target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
        m = t["masks"][()]; epx = t["entry_px"]
        if not epx or not m["exits"]: continue
        w = sum(x[1] for x in m["exits"]) or 1.0
        z = (sum(x[1]*x[2] for x in m["exits"])/w/epx - 1.0)*100.0
        G[{None:"자료없음", True:"조건통과", False:"조건탈락"}[v]].append(z)
print("  %-10s %9s %13s %10s" % ("무리", "후보 수", "매매 한 번당", "이긴 비율"))
print("  " + "-"*48)
for k in ("조건통과","자료없음","조건탈락"):
    v = G[k]
    print("  %-10s %9s %+12.3f%% %9.1f%%" % (k, "{:,}".format(len(v)), st.mean(v), 100.0*sum(1 for z in v if z>0)/len(v)))
alln = sum(G.values(), [])
print("  %-10s %9s %+12.3f%%" % ("── 바탕(전부)", "{:,}".format(len(alln)), st.mean(alln)))
keep = G["조건통과"] + G["자료없음"]
print()
print("  ★ 103 최선 칸 = 「조건탈락만 뺀다」 → 남는 %s건 · 매매 한 번당 %+.3f%%" % ("{:,}".format(len(keep)), st.mean(keep)))
rnd = random.Random(3)
ds = sorted(sum(rnd.choice(keep) for _ in range(len(keep)))/len(keep) - sum(rnd.choice(alln) for _ in range(len(alln)))/len(alln) for _ in range(3000))
print("     바탕과의 차 %+.3f%%p  구간 [%+.3f, %+.3f]  %s" % (st.mean(keep)-st.mean(alln), ds[75], ds[2924], "0 배제" if not (ds[75] <= 0 <= ds[2924]) else "**0 포함**"))
ds2 = sorted(sum(rnd.choice(G["조건탈락"]) for _ in range(len(G["조건탈락"])))/len(G["조건탈락"]) - sum(rnd.choice(keep) for _ in range(len(keep)))/len(keep) for _ in range(3000))
print("     ★ 「떨어진 무리」가 「남긴 무리」보다 %+.3f%%p  구간 [%+.3f, %+.3f]  %s" % (st.mean(G["조건탈락"])-st.mean(keep), ds2[75], ds2[2924], "0 배제" if not (ds2[75] <= 0 <= ds2[2924]) else "**0 포함**"))

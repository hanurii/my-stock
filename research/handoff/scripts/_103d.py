import importlib.util as _u, random, statistics as st, sys
from pathlib import Path
HERE = Path("research/handoff/scripts").resolve(); sys.path.insert(0, str(HERE))
import pyr_trigger as pt
_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py"); r102 = _u.module_from_spec(_s); _s.loader.exec_module(r102)
_t = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py"); r103 = _u.module_from_spec(_t); _t.loader.exec_module(r103)
r91, f92a, _ord = r102.r91, r102.f92a, r102._ord
(_a,_b,by2), miss, _ = r91.load_ladder(r102.YEARS, r102.D0, r102.D1, "91-monthly-us-full.json", use_ext=False)
fund, ixf = f92a.load(); ix = {f:i for i,f in enumerate(ixf)}
G = {}
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
        G.setdefault((p.get("pattern") or "?", {None:"자료없음", True:"조건통과", False:"조건탈락"}[v]), []).append(z)
def ci(a, b, sd):
    r = random.Random(sd)
    ds = sorted(sum(r.choice(a) for _ in range(len(a)))/len(a) - sum(r.choice(b) for _ in range(len(b)))/len(b) for _ in range(3000))
    return st.mean(a)-st.mean(b), ds[75], ds[2924]
print("★ 원문이 «실제로» 말하는 것: 「파워플레이면 «나쁜 실적»을 무시해도 되나」")
print("   → 같은 패턴 «안»에서 「조건탈락(성장 둔화)」 vs 「조건통과(성장 가속)」을 견준다")
print()
print("  %-6s %11s %11s %11s %15s %-24s" % ("패턴","통과 n","탈락 n","통과 평균","탈락−통과","구간(95%)"))
print("  " + "-"*84)
for k in ("VCP","3C","PP"):
    a, b = G.get((k,"조건탈락"),[]), G.get((k,"조건통과"),[])
    if len(a) < 20 or len(b) < 20:
        print("  %-6s %11s %11s   (표본 부족)" % (k, len(b), len(a))); continue
    d, lo, hi = ci(a, b, hash(k)%999)
    mark = "0 배제 → 실적이 «먹힌다»" if hi < 0 else ("**0 포함 = 못 가림**" if lo <= 0 <= hi else "0 배제")
    print("  %-6s %11s %11s %+10.3f%% %+14.3f%%p [%+6.3f,%+6.3f] %s" % (k, "{:,}".format(len(b)), "{:,}".format(len(a)), st.mean(b), d, lo, hi, mark))
print()
print("  ★ 읽는 법: VCP·3C 에서는 «탈락이 확실히 나쁜데» PP 에서는 «못 가리면»,")
print("             그게 원문(「파워플레이만은 실적을 안 본다」)과 맞는 모양이다")

import json, statistics
from collections import defaultdict
pil=json.load(open("rows_mh60.json"))
tt=[r for r in pil if r["touched"]]
up=[r for r in tt if r["tr_ret"]>r["base_ret"]+1e-9]; dn=[r for r in tt if r["tr_ret"]<r["base_ret"]-1e-9]
print("MECH: touched={} better={} avg={:+.1f}pp  worse={} avg={:+.1f}pp".format(
  len(tt), len(up), sum(r["tr_ret"]-r["base_ret"] for r in up)/len(up), len(dn), sum(r["tr_ret"]-r["base_ret"] for r in dn)/len(dn)))
loss=[r for r in pil if not r["touched"]]
ab=sum(r["base_ret"] for r in tt)/len(tt); at=sum(r["tr_ret"] for r in tt)/len(tt)
lb=sum(r["base_ret"] for r in loss)/len(loss); lt=sum(r["tr_ret"] for r in loss)/len(loss)
print("non-touch n={} identical={}  avg {:+.2f} -> {:+.2f}".format(len(loss), all(abs(r["base_ret"]-r["tr_ret"])<1e-9 for r in loss), lb, lt))
print("avg win {:+.2f} -> {:+.2f} ; avg loss {:+.2f} -> {:+.2f} ; ratio {:.2f} -> {:.2f}".format(ab,at,lb,lt,ab/abs(lb),at/abs(lt)))
srt=sorted(pil,key=lambda r:-(r["tr_ret"]-r["base_ret"]))[:10]
print("top10 contributors:", ", ".join("{}({})".format(r["code"],r["entry"][5:]) for r in srt), "unique", len({r["code"] for r in srt}))
oos=json.load(open("oos_lead.json"))
d=[r["t10"]-r["base"] for r in oos]; n=len(d)
byy=defaultdict(list)
for r in oos: byy[r["entry"][:4]].append(r["t10"]-r["base"])
print("OOS by year:", " ".join("{} {:+.2f}".format(y,sum(v)/len(v)) for y,v in sorted(byy.items())))
print("OOS all {:+.3f}pp ; median(nonzero) {:+.2f}pp".format(sum(d)/n, statistics.median([x for x in d if abs(x)>1e-9])))

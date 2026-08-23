import json, random, statistics
exec(open("t3.py",encoding="utf-8").read().split("def run(")[0])
pb,tb = slot_sim(rows,"base",slots=5,seed=1)
pt,tt = slot_sim(rows,"trail",slots=5,seed=1)
print("base: n=%d  avg ret %.2f%%  pnl %.0f만" % (len(tb), sum(x[1] for x in tb)/len(tb), pb))
print("trail: n=%d  avg ret %.2f%%  pnl %.0f만" % (len(tt), sum(x[1] for x in tt)/len(tt), pt))
from collections import Counter
print("base kinds:", Counter(x[0]["base_kind"] for x in tb))
print("trail kinds:", Counter(x[0]["tr_kind"] for x in tt))
print("전체 표본 평균 base %.2f trail %.2f" % (sum(r["base_ret"] for r in rows)/len(rows), sum(r["tr_ret"] for r in rows)/len(rows)))
# 보유일
print("base 평균보유 %.1f일, trail %.1f일" % (sum(x[0]["base_days"] for x in tb)/len(tb), sum(x[0]["tr_days"] for x in tt)/len(tt)))

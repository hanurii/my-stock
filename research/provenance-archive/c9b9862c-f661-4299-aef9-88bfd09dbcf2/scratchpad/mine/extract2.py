import subprocess, json, os, collections
REPO = r"C:\Users\hanul\playground\my-stock"
OUT = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\bydata"
os.makedirs(OUT, exist_ok=True)
revs = subprocess.run(["git","log","--format=%H","--","public/data/sepa-trend-candidates.json"],
                      capture_output=True, text=True, cwd=REPO).stdout.split()
best = {}
for r in revs:
    raw = subprocess.run(["git","show",f"{r}:public/data/sepa-trend-candidates.json"],
                         capture_output=True, cwd=REPO).stdout
    d = json.loads(raw.decode("utf-8"))
    cnt = collections.Counter(c.get("last_date") for c in d["candidates"])
    datadate = cnt.most_common(1)[0][0]
    gen = d.get("generated_at") or ""
    if datadate not in best or gen > best[datadate][0]:
        best[datadate] = (gen, r, d, d.get("asof"))
print("data dates:", len(best))
for dd,(gen,r,d,asof) in sorted(best.items()):
    idx = {c["code"]: c for c in d["candidates"]}
    json.dump({"data_date":dd,"asof":asof,"gen":gen,"rev":r,"n":len(idx),"recs":idx},
              open(os.path.join(OUT, f"{dd}.json"),"w",encoding="utf-8"), ensure_ascii=False)
    print(dd, "| asof", asof, "| gen", gen, "|", len(idx))

import subprocess, json, os, sys
OUT = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\asof"
os.makedirs(OUT, exist_ok=True)
revs = subprocess.run(["git","log","--format=%H","--","public/data/sepa-trend-candidates.json"],
                      capture_output=True, text=True, cwd=r"C:\Users\hanul\playground\my-stock").stdout.split()
best = {}
for r in revs:
    raw = subprocess.run(["git","show",f"{r}:public/data/sepa-trend-candidates.json"],
                         capture_output=True, cwd=r"C:\Users\hanul\playground\my-stock").stdout
    d = json.loads(raw.decode("utf-8"))
    asof = d.get("asof"); gen = d.get("generated_at") or ""
    key = asof
    if key not in best or gen > best[key][0]:
        best[key] = (gen, r, d)
print("dates:", len(best))
for asof,(gen,r,d) in sorted(best.items()):
    idx = {c["code"]: c for c in d["candidates"]}
    with open(os.path.join(OUT, f"{asof}.json"), "w", encoding="utf-8") as f:
        json.dump({"asof":asof,"gen":gen,"rev":r,"n":len(idx),"recs":idx}, f, ensure_ascii=False)
    print(asof, gen, r[:8], len(idx), d.get("all_pass_count"))

# -*- coding: utf-8 -*-
"""Build cache of nightly sepa-trend-candidates.json snapshots (last commit per calendar date)."""
import json, subprocess, os

SCRATCH = os.path.dirname(os.path.abspath(__file__))
REPO = r"C:/Users/hanul/playground/my-stock"
PATH = "public/data/sepa-trend-candidates.json"

out = subprocess.run(["git", "log", "--format=%H %cI", "--", PATH],
                     capture_output=True, cwd=REPO, check=True)
lines = out.stdout.decode().strip().splitlines()
# newest first; keep first seen per calendar date = last commit of that date
kept = {}
for ln in lines:
    sha, iso = ln.split()
    date = iso[:10]
    if date not in kept:
        kept[date] = (sha, iso)

snaps = []
for date in sorted(kept):
    sha, iso = kept[date]
    raw = subprocess.run(["git", "show", f"{sha}:{PATH}"], capture_output=True, cwd=REPO, check=True)
    d = json.loads(raw.stdout.decode("utf-8"))
    recs = {}
    names = {}
    for c in d["candidates"]:
        code = c["code"]
        recs[code] = [c.get("rs"), c.get("passed_count"), bool(c.get("all_pass"))]
        names[code] = c.get("name")
    snaps.append({"date": date, "sha": sha, "iso": iso, "asof": d.get("asof"),
                  "n": len(recs), "n_allpass": sum(1 for v in recs.values() if v[2]),
                  "recs": recs, "names": names})

with open(os.path.join(SCRATCH, "trend_snaps.json"), "w", encoding="utf-8") as f:
    json.dump(snaps, f, ensure_ascii=False)
print("snapshots:", len(snaps))
for s in snaps:
    print(s["date"], s["iso"][11:16], "n=", s["n"], "all_pass=", s["n_allpass"])

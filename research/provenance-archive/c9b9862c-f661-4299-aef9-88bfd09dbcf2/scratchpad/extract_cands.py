import json, subprocess, os, sys, collections
REPO = r"C:\Users\hanul\playground\my-stock"
OUT = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"

files = {
  "VCP": "public/data/sepa-vcp-candidates.json",
  "3C": "public/data/sepa-3c-candidates.json",
  "PP": "public/data/sepa-power-play-candidates.json",
}

def git(args):
    return subprocess.run(["git"]+args, cwd=REPO, capture_output=True)

snap = collections.defaultdict(dict)  # asof -> pattern -> {code: rec}
meta = collections.defaultdict(dict)  # asof -> pattern -> commit info

for pat, path in files.items():
    log = git(["log","--format=%H|%ad","--date=short","--since=2026-06-25","--reverse","--",path]).stdout.decode()
    for line in log.strip().split("\n"):
        if not line.strip(): continue
        h, cd = line.split("|")
        raw = git(["show", f"{h}:{path}"]).stdout
        try:
            d = json.loads(raw.decode("utf-8"))
        except Exception as e:
            continue
        asof = d.get("asof") or d.get("generated_at","")[:10]
        cands = d.get("candidates", [])
        m = {}
        for c in cands:
            code = c.get("code")
            m[code] = {
                "name": c.get("name"),
                "status": c.get("status"),
                "entry_ready": c.get("entry_ready"),
                "pivot": c.get("pivot_price") or c.get("pivot"),
                "price": c.get("current_price"),
                "rs": c.get("rs"),
                "pct_to_pivot": c.get("pct_to_pivot"),
                "detected": c.get("vcp_detected") if pat=="VCP" else True,
            }
        # keep the FIRST commit for a given asof (original evening run)
        if pat not in snap[asof]:
            snap[asof][pat] = m
            meta[asof][pat] = {"commit": h, "commit_date": cd, "n": len(m)}

json.dump({"snap":snap,"meta":meta}, open(os.path.join(OUT,"cand_hist.json"),"w",encoding="utf-8"), ensure_ascii=False)
print("asof dates:", sorted(snap.keys()))
for a in sorted(snap.keys()):
    print(a, {p:(meta[a][p]["commit_date"], meta[a][p]["n"]) for p in snap[a]})

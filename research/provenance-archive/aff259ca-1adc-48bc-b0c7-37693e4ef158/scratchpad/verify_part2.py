# -*- coding: utf-8 -*-
"""Part 2: corrected as-of (morning commits), backtest reproduction, hand spot-checks."""
import subprocess, json, sys, io
from collections import Counter
from math import comb

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REPO = r"C:/Users/hanul/playground/my-stock"
SCRATCH = r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/aff259ca-1adc-48bc-b0c7-37693e4ef158/scratchpad"

def fisher(a, b, c, d):
    n = a+b+c+d; r1, c1 = a+b, a+c
    den = comb(n, r1)
    def pa(x):
        if x < 0 or x > r1 or c1-x < 0 or c1-x > n-r1: return 0.0
        return comb(c1, x)*comb(n-c1, r1-x)/den
    po = pa(a); lo = max(0, r1+c1-n); hi = min(r1, c1)
    return sum(pa(x) for x in range(lo, hi+1) if pa(x) <= po*(1+1e-9))

log = subprocess.run(["git","-C",REPO,"log","--format=%H %cI","--","public/data/sepa-trend-candidates.json"],
                     capture_output=True,text=True).stdout.strip().splitlines()
commits = []  # oldest-first: (iso, sha)
for line in reversed(log):
    sha, iso = line.split()
    commits.append((iso, sha))

cache = {}
def load(sha):
    if sha not in cache:
        raw = subprocess.run(["git","-C",REPO,"show",f"{sha}:public/data/sepa-trend-candidates.json"],
                             capture_output=True).stdout
        d = json.loads(raw.decode("utf-8"))
        cache[sha] = (d.get("asof"), {c["code"]:(c.get("rs"),c.get("passed_count"),bool(c.get("all_pass"))) for c in d["candidates"]})
    return cache[sha]

# corrected as-of: for cutoff, latest commit per asof among commits < cutoff
def snap_seq(cutoff_iso):
    per_asof = {}
    for iso, sha in commits:
        if iso[:19] < cutoff_iso:
            asof, snap = load(sha)
            per_asof[asof] = snap  # later commit overwrites (commits oldest-first)
    return [per_asof[a] for a in sorted(per_asof)]

enr = json.load(open(f"{SCRATCH}/enriched_trades.json", encoding="utf-8"))["rows"]

def tenure(code, seq):
    last10 = seq[-10:]
    ts = sum(1 for s in last10 if code in s and s[code][2])
    tl = sum(1 for s in last10 if code in s and (s[code][1] or 0) >= 7)
    st = 0
    for s in reversed(seq):
        if code in s and s[code][2]: st += 1
        else: break
    return ts, tl, st, len(seq)

print("=== corrected as-of (include pre-09:00 same-day commits) ===")
rows = []
for t in enr:
    cutoff = t["open_date"] + "T09:00:00"
    seq = snap_seq(cutoff)
    ts, tl, st, np_ = tenure(t["code"], seq)
    rows.append(dict(name=t["name"], code=t["code"], od=t["open_date"], net=t["net_pct"],
                     win=t["outcome"]=="win", rs=t["displayed_rs"], ts=ts, tl=tl, st=st, np=np_))
lst = json.load(open(f"{SCRATCH}/newcomer_flag.json", encoding="utf-8"))["trades_listing"]
for r, l in zip(rows, lst):
    if r["ts"] != l["tenure10_strict"]:
        print(f"  tenure changed: {r['name']} {r['od']}: file {l['tenure10_strict']} -> corrected {r['ts']} (net {r['net']})")

def cell(rs_):
    n=len(rs_); w=sum(1 for r in rs_ if r["win"]); s=sum(r["net"] for r in rs_)
    return n, w, (100*w/n if n else 0), (s/n if n else 0), s
def show(lab, rs_):
    n,w,wr,avg,s = cell(rs_)
    print(f"  {lab:34s} n={n:3d} wins={w:2d} wr={wr:.1f}% avg={avg:.2f} sum={s:.2f}")
    return n,w

newc=[r for r in rows if r["ts"]<=2]; mid=[r for r in rows if 3<=r["ts"]<=4]; reg=[r for r in rows if r["ts"]>=5]
n1,w1=show("corrected newcomer ten<=2", newc)
show("corrected mid 3-4", mid)
n2,w2=show("corrected regular >=5", reg)
print(f"  fisher new vs reg: {fisher(w1,n1-w1,w2,n2-w2):.4f}")

prec=[r for r in rows if r["ts"]<=1 and r["rs"] is not None and r["rs"]<=84]
print("  corrected 'ten<=1 AND rs<=84' members:", [(r['name'],r['od'],r['net']) for r in prec])
t1=[r for r in rows if r["ts"]<=1]
print("  corrected 'ten<=1' members:", [(r['name'],r['od'],r['net']) for r in t1])

# ---- backtest reproduction ----
print("\n=== backtest reproduction (bt_closed_split_all) ===")
bt = json.load(open(f"{SCRATCH}/forming_backtest.json", encoding="utf-8"))
ev = [e for e in bt["events"] if e.get("result") == "entered" and e.get("entry_date")]
ev.sort(key=lambda e: (e["entry_date"], e["code"]))
seen = set(); dedup = []
for e in ev:
    if e["code"] in seen: continue
    seen.add(e["code"]); dedup.append(e)
closed = [e for e in dedup if not e.get("still_open")]
print(f"entered events {len(ev)}, dedup first-per-code {len(dedup)}, closed {len(closed)} (file: 110/74)")

# original (file) snapshot convention for bt tenure: keep-last-per-date, < D 09:00
by_date = {}
for iso, sha in commits:
    by_date[iso[:10]] = (sha, iso)   # oldest-first -> later commit same date overwrites
snap_dates = sorted(by_date)
def seq_filedef(cutoff):
    out=[]
    for d in snap_dates:
        sha, iso = by_date[d]
        if iso[:19] < cutoff:
            out.append(load(sha)[1])
    return out

btr=[]
for e in closed:
    seq = seq_filedef(e["entry_date"]+"T09:00:00")
    ts, tl, st, np_ = tenure(e["code"], seq)
    win = e["net_pct"] > 0
    rs = e.get("rs_open")
    btr.append(dict(name=e["name"], od=e["entry_date"], net=e["net_pct"], win=win, ts=ts, rs=rs, np=np_, cohort=e["cohort"]))
bn=[r for r in btr if r["ts"]<=2]; bm=[r for r in btr if 3<=r["ts"]<=4]; br=[r for r in btr if r["ts"]>=5]
show("bt newcomer", bn); show("bt mid", bm); show("bt regular", br)
print("  file: newcomer 49/12 24.5% -2.99 | mid 13/4 | regular 12/1 8.3% -7.84")
h5=[r for r in btr if r["np"]>=5]
print(f"  bt n_prior>=5: {len(h5)} (file 35)")
show("bt h5 newcomer", [r for r in h5 if r["ts"]<=2])
show("bt h5 regular", [r for r in h5 if r["ts"]>=5])
print("  bt cohorts in closed set:", Counter(r['cohort'] for r in btr))
print("  bt unique codes newcomer:", len(set((r['name']) for r in bn)), "of", len(bn))

# ---- hand spot-checks straight from git show ----
print("\n=== hand spot-checks (raw git show) ===")
def probe(date_sha, code, label):
    asof, snap = load(date_sha)
    v = snap.get(code)
    print(f"  {label}: asof={asof} code={code} rs/passed/all_pass = {v}")

sha_of = {}
for iso, sha in commits:
    sha_of.setdefault(iso[:10]+("m" if iso[11:16] < "09:00" else ""), None)
# simpler: named lookups
def sha_at(date, morning=False):
    cands = [(iso, sha) for iso, sha in commits if iso[:10] == date and ((iso[11:16] < "09:00") == morning)]
    return cands[-1][1] if cands else None

# anchor F&F 383220: file trail says 07-28: 77/5, 07-29: 81/8
probe(sha_at("2026-07-28"), "383220", "F&F @07-28 evening (file: 77/5)")
probe(sha_at("2026-07-29"), "383220", "F&F @07-29 evening (file: 81/8)")
probe(sha_at("2026-07-31", morning=True), "383220", "F&F @07-31 08:29 morning (dropped by file)")
# win 안국약품 001540 bought 07-06, file tenure 5 (06-30..07-05 all 83/8)
for d in ["2026-06-30","2026-07-02","2026-07-05"]:
    probe(sha_at(d), "001540", f"안국약품 @{d} (file: 8/8, rs~83)")
# random 코리안리 003690 bought 07-10, file trail 07-01: 82/6, 07-08: 87/8
probe(sha_at("2026-07-01"), "003690", "코리안리 @07-01 (file: 82/6)")
probe(sha_at("2026-07-08"), "003690", "코리안리 @07-08 (file: 87/8)")
# 대양금속 009190 anchor: 08-12: 80/7
probe(sha_at("2026-08-12"), "009190", "대양금속 @08-12 evening (file: 80/7)")

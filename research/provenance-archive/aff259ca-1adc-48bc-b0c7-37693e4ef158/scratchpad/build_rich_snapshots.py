# -*- coding: utf-8 -*-
"""Rich daily git snapshots of SEPA detector files (last commit per calendar date, 2026-06-29..2026-08-15)."""
import json, subprocess, os, collections

REPO = r"C:\Users\hanul\playground\my-stock"
SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
FILES = ["sepa-vcp-candidates.json", "sepa-3c-candidates.json", "sepa-power-play-candidates.json"]
SRC_KEY = {"sepa-vcp-candidates.json": "vcp", "sepa-3c-candidates.json": "3c", "sepa-power-play-candidates.json": "pp"}
MIN_DATE, MAX_DATE = "2026-06-29", "2026-08-15"

EXTRA = {
    "vcp": ["num_contractions", "base_depth_pct", "base_length_days", "tightness_pct", "volume_dryup_ratio"],
    "3c":  ["cup_depth_pct", "shelf_depth_pct", "shelf_length_days", "tightness_pct", "volume_dryup_ratio"],
    "pp":  ["flag_depth_pct", "flag_length_days", "flagpole_gain_pct", "tightness_pct", "volume_dryup_ratio"],
}

def git(args, binary=False):
    r = subprocess.run(["git"] + args, capture_output=True, cwd=REPO)
    if r.returncode != 0:
        return None
    return r.stdout if binary else r.stdout.decode("utf-8", errors="replace")

def num(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.replace(",", ""))
        except Exception:
            return None
    return None

def main():
    log = git(["log", "--format=%H|%cI", "--", *[f"public/data/{f}" for f in FILES]])
    by_date = {}
    for line in log.strip().splitlines():
        sha, iso = line.split("|")
        date = iso[:10]
        if MIN_DATE <= date <= MAX_DATE:
            if date not in by_date or iso > by_date[date][1]:
                by_date[date] = (sha, iso)
    snap_dates = sorted(by_date.keys())

    snapshots = []
    status_counter = collections.Counter()
    for d in snap_dates:
        sha, iso = by_date[d]
        snap = {"date": d, "sha": sha, "iso": iso, "records": []}
        for f in FILES:
            src = SRC_KEY[f]
            raw = git(["show", f"{sha}:public/data/{f}"], binary=True)
            if raw is None:
                continue
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception as e:
                print(f"WARN parse fail {d} {f}: {e}")
                continue
            cands = data.get("candidates") if isinstance(data, dict) else data
            if not isinstance(cands, list):
                continue
            for c in cands:
                if not isinstance(c, dict):
                    continue
                code = c.get("code")
                if code is None:
                    continue
                code = str(code).strip().zfill(6)
                pivot = None
                for k in ("pivot_price", "pivot"):
                    if k in c and num(c[k]) is not None:
                        pivot = num(c[k]); break
                status = c.get("status")
                rec = {
                    "code": code, "name": c.get("name"), "src": src,
                    "status": str(status).lower() if status is not None else None,
                    "entry_ready": bool(c.get("entry_ready")) if c.get("entry_ready") is not None else False,
                    "pivot": pivot,
                    "rs": num(c.get("rs")),
                    "pct_to_pivot": num(c.get("pct_to_pivot")),
                    "current_price": num(c.get("current_price")),
                }
                for k in EXTRA[src]:
                    rec[k] = num(c.get(k)) if not isinstance(c.get(k), (list, dict)) else None
                snap["records"].append(rec)
                status_counter[(src, rec["status"], rec["entry_ready"])] += 1
        snapshots.append(snap)

    with open(os.path.join(SCRATCH, "rich_snapshots.json"), "w", encoding="utf-8") as fh:
        json.dump({"snapshots": snapshots}, fh, ensure_ascii=False)
    print("snapshot dates:", len(snapshots))
    for s in snapshots:
        print(s["date"], s["sha"][:8], "n=", len(s["records"]))
    print("\n(src,status,entry_ready) counts:")
    for k, v in sorted(status_counter.items(), key=lambda x: str(x)):
        print(" ", k, v)

if __name__ == "__main__":
    main()

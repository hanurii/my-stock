import json, subprocess

REPO = r"C:\Users\hanul\playground\my-stock"

def show(sha, path):
    out = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=REPO,
                         capture_output=True).stdout
    if not out:
        return None
    return json.loads(out.decode("utf-8"))

def find(doc, code="212560"):
    if doc is None:
        return None
    items = doc.get("candidates") if isinstance(doc, dict) else doc
    if items is None:
        # try other keys
        for k, v in doc.items():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "code" in v[0]:
                items = v
                break
    if not isinstance(items, list):
        return "NOLIST:" + str(list(doc.keys()))
    for c in items:
        if c.get("code") == code:
            return c
    return None

# claimed first-appearance states
print("=== first-appearance states ===")
c = find(show("496beb0b", "public/data/sepa-vcp-candidates.json"))
print("vcp@496beb0b:", c.get("status"), c.get("reason"), c.get("pivot_price"))
c = find(show("496beb0b", "public/data/sepa-3c-candidates.json"))
print("3c @496beb0b:", c.get("status"), c.get("reason"), c.get("pivot_price"))
c = find(show("496beb0b", "public/data/sepa-power-play-candidates.json"))
print("pp @496beb0b:", c.get("status"), c.get("reason"), c.get("pivot_price"))
c = find(show("108e4712", "public/data/sepa-power-play-all-candidates.json"))
print("ppall@108e4712:", c.get("status"), c.get("reason"), c.get("pivot_price"))

# nightly commits touching pp-all, 08-03..08-14
log = subprocess.run(["git", "log", "--format=%h %ad", "--date=format:%m-%d %H:%M",
                      "--since=2026-08-02", "--until=2026-08-15",
                      "--", "public/data/sepa-power-play-all-candidates.json"],
                     cwd=REPO, capture_output=True, text=True).stdout
print("\n=== pp-all commits 08-02..08-14 and 212560 state ===")
for line in reversed(log.strip().splitlines()):
    sha, date = line.split(" ", 1)
    c = find(show(sha, "public/data/sepa-power-play-all-candidates.json"))
    if c is None or isinstance(c, str):
        print(sha, date, "->", c)
    else:
        print(sha, date, "->", c.get("status"), c.get("reason"), c.get("pivot_price"))

# vcp candidates around 08-12..08-14
log = subprocess.run(["git", "log", "--format=%h %ad", "--date=format:%m-%d %H:%M",
                      "--since=2026-08-11", "--until=2026-08-15",
                      "--", "public/data/sepa-vcp-candidates.json"],
                     cwd=REPO, capture_output=True, text=True).stdout
print("\n=== vcp commits 08-11..08-14 and 212560 presence ===")
for line in reversed(log.strip().splitlines()):
    sha, date = line.split(" ", 1)
    c = find(show(sha, "public/data/sepa-vcp-candidates.json"))
    if c is None or isinstance(c, str):
        print(sha, date, "-> absent" if c is None else c)
    else:
        print(sha, date, "->", c.get("status"), c.get("pivot_price"))

# 07-20 morning vcp forming claim + presence window 07-10..07-21
log = subprocess.run(["git", "log", "--format=%h %ad", "--date=format:%m-%d %H:%M",
                      "--since=2026-07-09", "--until=2026-07-22",
                      "--", "public/data/sepa-vcp-candidates.json"],
                     cwd=REPO, capture_output=True, text=True).stdout
print("\n=== vcp commits 07-09..07-21 and 212560 state ===")
for line in reversed(log.strip().splitlines()):
    sha, date = line.split(" ", 1)
    c = find(show(sha, "public/data/sepa-vcp-candidates.json"))
    if c is None or isinstance(c, str):
        print(sha, date, "-> absent")
    else:
        print(sha, date, "->", c.get("status"), c.get("reason"), c.get("pivot_price"))

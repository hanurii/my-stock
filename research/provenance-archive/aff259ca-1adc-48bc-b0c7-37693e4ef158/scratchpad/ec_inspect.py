# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
P = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad")

def safe(s):
    return str(s).encode("ascii", "backslashreplace").decode()

cons = json.loads((P/"ec_consensus.json").read_text(encoding="utf-8"))
act = json.loads((P/"ec_actuals.json").read_text(encoding="utf-8"))
rea = json.loads((P/"ec_reaction.json").read_text(encoding="utf-8"))

out = []
out.append(f"counts cons={len(cons['byCode'])} act={len(act['byCode'])} rea={len(rea)}")
# key overlap
kc, ka, kr = set(cons['byCode']), set(act['byCode']), set(rea)
out.append(f"key sets equal: {kc==ka==kr}")

# missing actuals detail
for c, v in act['byCode'].items():
    if v.get('missing'):
        out.append(f"ACT-MISSING {c} {safe(v['name'])} | {safe(v['missing'])} | q1={v['q1']} h1={v['h1']} q2={v['q2']}")

# unobservable reactions
unobs = [(c, v) for c, v in rea.items() if not v.get('observable')]
out.append(f"unobservable reactions: {len(unobs)}")
for c, v in unobs:
    out.append(f"  UNOBS {c} {safe(v.get('name'))} reveal={v.get('reveal_date')} kind={safe(v.get('reveal_kind'))} note={safe(v.get('note'))} keys={sorted(v.keys())}")

# fs_div variety
from collections import Counter
fsc = Counter(v.get('fs_div') for v in act['byCode'].values())
out.append(f"fs_div dist: {dict(fsc)}")

# mixed fs_div (q1:CFS/h1:OFS style)
for c, v in act['byCode'].items():
    fd = v.get('fs_div')
    if fd and '/' in str(fd):
        out.append(f"FS-MIX {c} {safe(v['name'])} fs_div={fd}")

# sign anomaly: |q2 op| > |h1 op| flag candidates (q2 op magnitude exceeding h1 magnitude)
for c, v in act['byCode'].items():
    q2 = v.get('q2', {}).get('op'); h1 = v.get('h1', {}).get('op')
    if q2 is not None and h1 is not None and abs(q2) > abs(h1):
        out.append(f"SIGN-ANOM {c} {safe(v['name'])} q1_op={v['q1'].get('op')} h1_op={h1} q2_op={q2}")

# h1_prior op missing (YoY 판정불가 후보)
n_noprior = 0
for c, v in act['byCode'].items():
    if v.get('h1_prior', {}).get('op') is None:
        n_noprior += 1
        out.append(f"NO-PRIOR {c} {safe(v['name'])} h1_prior={v.get('h1_prior')}")
out.append(f"no h1_prior op: {n_noprior}")

# consensus flag dist
fc = Counter(v['flag'] for v in cons['byCode'].values())
out.append(f"cons flags: {dict(fc)}")

# reaction fields for observable ones: any missing day_ret?
n_no_dayret = sum(1 for v in rea.values() if v.get('observable') and v.get('day_ret_pct') is None)
out.append(f"observable but day_ret None: {n_no_dayret}")

# anchors present?
for code, label in [("003690","KoreanRe"), ("007340","DN Auto"), ("383220","F&F"), ("111770","F&F old?")]:
    out.append(f"anchor {label} {code}: in92={code in ka}")

(P/"ec_inspect_out.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))

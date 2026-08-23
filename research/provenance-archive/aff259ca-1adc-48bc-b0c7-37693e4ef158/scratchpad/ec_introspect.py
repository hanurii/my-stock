# -*- coding: utf-8 -*-
"""Introspect fnlttSinglAcnt response shape for 2026 Q1/H1 on a couple of codes."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(ROOT / "scripts"))

# .env -> os.environ
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    k, v = k.strip(), v.strip().strip('"').strip("'")
    if k and k not in os.environ:
        os.environ[k] = v

from canslim_lib.fetch import dart_get, load_corp_code_map, resolve_corp_code  # noqa: E402

corp_map = load_corp_code_map()
print("corp_map size:", len(corp_map))

for code, label in [("009150", "SEMCO"), ("001450", "HyundaiM&F")]:
    cc, parent = resolve_corp_code(code, corp_map)
    print("=" * 60)
    print(code, label, "corp_code:", cc, "parent:", parent)
    for reprt in ("11013", "11012"):
        rows = dart_get("fnlttSinglAcnt", {
            "corp_code": cc, "bsns_year": "2026", "reprt_code": reprt,
        })
        print("-" * 40)
        print("reprt", reprt, "rows:", None if rows is None else len(rows))
        if rows:
            print("keys:", sorted(rows[0].keys()))
            for r in rows:
                print(json.dumps({k: r.get(k) for k in (
                    "fs_div", "sj_div", "account_nm", "thstrm_nm", "thstrm_dt",
                    "thstrm_amount", "thstrm_add_amount",
                    "frmtrm_nm", "frmtrm_dt", "frmtrm_amount", "frmtrm_add_amount",
                )}, ensure_ascii=False))

# -*- coding: utf-8 -*-
"""2026 Q2 (202606) operating-profit analyst consensus for the 92 earnings-calendar codes.

Source: m.stock.naver.com/api/stock/<code>/finance/quarter (FnGuide-fed).
Period 202606 with trTitleList isConsensus='Y' + numeric 영업이익 column = consensus (억원).
isConsensus='N' = actual already merged in (pre-report consensus not retrievable here).
'-' value = no analyst coverage.
"""
import sys, json, io, time
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from canslim_lib.fetch import _http_get_json, NAVER_HEADERS, NAVER_API

SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"

cal = json.load(open(SCRATCH + r"\ec_head.json", encoding="utf-8"))
by_code = cal["byCode"]


def parse_val(raw):
    """Naver cell value string -> float (억원), or None if missing ('-', '', None)."""
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "")
    if s in ("", "-", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


out = {}
counts = {"consensus": 0, "no_estimate": 0, "actual_reported": 0, "no_data": 0}

for i, (code, meta) in enumerate(by_code.items(), 1):
    name = meta.get("name", "")
    d = _http_get_json(f"{NAVER_API}/{code}/finance/quarter", NAVER_HEADERS)
    rec = {"name": name, "covered": False, "q2_op_consensus_eok": None,
           "n_analysts": None, "source_field": None, "flag": None}
    if not d:
        rec["flag"] = "no_data"
    else:
        fi = d.get("financeInfo") or {}
        periods = fi.get("trTitleList") or []
        p26 = next((p for p in periods if p.get("key") == "202606"), None)
        rows = fi.get("rowList") or []
        op = next((r for r in rows if r.get("title") == "영업이익"), None)
        raw = None
        if op:
            cell = (op.get("columns") or {}).get("202606")
            raw = cell.get("value") if isinstance(cell, dict) else cell
        val = parse_val(raw)
        if p26 is None:
            rec["flag"] = "no_data"  # 202606 period absent entirely
        elif p26.get("isConsensus") == "Y":
            if val is not None:
                rec.update(covered=True, q2_op_consensus_eok=val,
                           source_field="m.stock.naver.com finance/quarter 202606 isConsensus=Y 영업이익",
                           flag="consensus")
            else:
                rec["flag"] = "no_estimate"
        else:  # isConsensus == 'N' -> actual merged, consensus gone
            rec["flag"] = "actual_reported"
            rec["q2_op_actual_eok"] = val
    counts[rec["flag"]] = counts.get(rec["flag"], 0) + 1
    out[code] = rec
    print(f"{i:2d}/92 {code} {name}: {rec['flag']} {rec['q2_op_consensus_eok']}")
    time.sleep(0.12)  # + fetch helper's 0.15s politeness -> ~3.7 req/s

result = {
    "asof": "2026-08-17",
    "period": "202606",
    "metric": "영업이익 (operating profit)",
    "unit": "억원",
    "source": "m.stock.naver.com/api/stock/<code>/finance/quarter (FnGuide consensus, trTitleList isConsensus flag)",
    "notes": {
        "flags": {
            "consensus": "isConsensus=Y + numeric value -> analyst consensus estimate",
            "no_estimate": "isConsensus=Y but value '-' -> no analyst coverage (covered:false)",
            "actual_reported": "isConsensus=N -> Naver already replaced with reported actual; pre-report consensus not retrievable from this endpoint (covered:false, actual in q2_op_actual_eok)",
            "no_data": "endpoint returned nothing or no 202606 period",
        },
        "n_analysts": "not exposed by any probed Naver endpoint (integration consensusInfo has only target-price mean/recommendation) -> always null",
    },
    "coverage": counts,
    "byCode": out,
}
with open(SCRATCH + r"\ec_consensus.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\ncounts:", counts)

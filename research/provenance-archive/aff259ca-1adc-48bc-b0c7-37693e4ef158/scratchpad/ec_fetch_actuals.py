# -*- coding: utf-8 -*-
"""Fetch actual 2026 Q1(11013) / H1(11012) financials for the 92 earnings-calendar
codes from DART fnlttSinglAcnt, derive Q2 = H1 - Q1, write ec_actuals.json.

Field semantics (introspected 2026-08-17 on 009150/001450):
  - 11013 IS rows: thstrm_amount = Q1 3-month amount; frmtrm_amount = prior-year Q1.
  - 11012 IS rows: thstrm_amount = Q2 3-month, thstrm_add_amount = H1 cumulative;
                   frmtrm_amount = prior-year Q2 3-month, frmtrm_add_amount = prior-year H1.
  - fs_div: CFS preferred, OFS fallback when no CFS IS rows.
Raw responses cached under .cache/earnings_classify/fnltt_{code}_{reprt}.json.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\hanul\playground\my-stock")
SCRATCH = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad")
CACHE = ROOT / ".cache" / "earnings_classify"
CACHE.mkdir(parents=True, exist_ok=True)
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

calendar = json.loads((SCRATCH / "ec_calendar_head.json").read_text(encoding="utf-8"))
by_code = calendar["byCode"]
corp_map = load_corp_code_map()


def fetch_report(code: str, corp_code: str, reprt: str):
    """Return list of rows (cached). None only kept transiently for miss-cache."""
    cpath = CACHE / f"fnltt_{code}_{reprt}.json"
    if cpath.exists():
        cached = json.loads(cpath.read_text(encoding="utf-8"))
        if isinstance(cached, dict) and cached.get("status") == "no_data":
            return None
        return cached
    rows = dart_get("fnlttSinglAcnt", {
        "corp_code": corp_code, "bsns_year": "2026", "reprt_code": reprt,
    })
    if rows is None:
        cpath.write_text(json.dumps({"status": "no_data"}, ensure_ascii=False), encoding="utf-8")
        return None
    cpath.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def parse_amt(s):
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    if s in ("", "-"):
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def eok(v):
    return None if v is None else round(v / 1e8, 1)


NI_EXACT = [
    "당기순이익", "당기순이익(손실)", "당기순손익",
    "반기순이익", "반기순이익(손실)", "분기순이익", "분기순이익(손실)",
    "연결당기순이익", "연결반기순이익", "연결분기순이익",
]
OP_EXACT = ["영업이익", "영업이익(손실)", "영업손실", "영업손익"]
REV_EXACT = ["매출액", "수익(매출액)", "매출", "매출및지분법손익"]
REV_FALLBACK = ["영업수익", "보험수익", "보험영업수익", "이자수익", "순영업수익", "매출수익"]


def norm(s):
    return re.sub(r"\s+", "", s or "")


def pick(is_rows, exact_list, fallback_contains=None, exclude_contains=()):
    """is_rows: list of (account_nm_norm, row). Return (row, account_nm) or (None, None)."""
    for name in exact_list:
        for nm, row in is_rows:
            if nm == name:
                return row, nm
    if fallback_contains:
        for pat in fallback_contains:
            for nm, row in is_rows:
                if pat in nm and not any(x in nm for x in exclude_contains):
                    return row, nm
    return None, None


def extract(rows, reprt):
    """Return dict per fs_div choice: {fs_div, cur:{rev,op,ni}, prior:{...}, rev_account, ni_account, flags}."""
    if not rows:
        return None
    for fs in ("CFS", "OFS"):
        is_rows = [(norm(r.get("account_nm")), r) for r in rows
                   if r.get("fs_div") == fs and r.get("sj_div") == "IS"]
        if not is_rows:
            continue
        out = {"fs_div": fs, "cur": {}, "prior": {}, "accounts": {}, "flags": []}
        specs = {
            "rev": (REV_EXACT, REV_FALLBACK, ("비용", "원가")),
            "op": (OP_EXACT, ["영업이익"], ("외", "률", "비용")),
            "ni": (NI_EXACT, ["순이익", "순손익"], ("법인세", "지배", "포괄", "주당", "총")),
        }
        for key, (exact, fb, excl) in specs.items():
            row, nm = pick(is_rows, exact, fb, excl)
            if row is None:
                out["cur"][key] = None
                out["prior"][key] = None
                out["accounts"][key] = None
                continue
            out["accounts"][key] = nm
            if reprt == "11013":
                cur = parse_amt(row.get("thstrm_amount"))
                if cur is None:
                    cur = parse_amt(row.get("thstrm_add_amount"))
                prior = parse_amt(row.get("frmtrm_amount"))
                if prior is None:
                    prior = parse_amt(row.get("frmtrm_add_amount"))
            else:  # 11012: cumulative preferred
                cur = parse_amt(row.get("thstrm_add_amount"))
                if cur is None:
                    cur = parse_amt(row.get("thstrm_amount"))
                    if cur is not None:
                        out["flags"].append(f"h1_{key}_from_thstrm_amount")
                prior = parse_amt(row.get("frmtrm_add_amount"))
                if prior is None:
                    prior = parse_amt(row.get("frmtrm_amount"))
                    if prior is not None:
                        out["flags"].append(f"h1prior_{key}_from_frmtrm_amount")
            out["cur"][key] = cur
            out["prior"][key] = prior
        return out
    return None


result = {}
stats = {"total": 0, "full_q2": 0, "ofs_fallback": 0, "missing": 0, "rev_mapped": 0}

for code, meta in by_code.items():
    stats["total"] += 1
    name = meta.get("name")
    entry = {"name": name, "q1": {"rev": None, "op": None, "ni": None},
             "h1": {"rev": None, "op": None, "ni": None},
             "h1_prior": {"rev": None, "op": None, "ni": None},
             "q2": {"rev": None, "op": None, "ni": None},
             "fs_div": None, "missing": None, "notes": []}
    cc, parent = resolve_corp_code(code, corp_map)
    if not cc:
        entry["missing"] = "corp_code not found in dart_corpcode.json"
        result[code] = entry
        continue
    if parent:
        entry["notes"].append(f"preferred-share: used common-stock corp_code of {parent}")

    q1_rows = fetch_report(code, cc, "11013")
    h1_rows = fetch_report(code, cc, "11012")
    q1x = extract(q1_rows, "11013")
    h1x = extract(h1_rows, "11012")

    miss = []
    fs_used = []
    if q1x is None:
        miss.append("Q1(11013): no data from DART (not filed or status 013)")
    else:
        entry["q1"] = {k: eok(v) for k, v in q1x["cur"].items()}
        fs_used.append(("q1", q1x["fs_div"]))
        for k, nm in q1x["accounts"].items():
            if nm is None:
                miss.append(f"Q1 {k}: no matching account")
    if h1x is None:
        miss.append("H1(11012): no data from DART (not filed or status 013)")
    else:
        entry["h1"] = {k: eok(v) for k, v in h1x["cur"].items()}
        entry["h1_prior"] = {k: eok(v) for k, v in h1x["prior"].items()}
        fs_used.append(("h1", h1x["fs_div"]))
        for k, nm in h1x["accounts"].items():
            if nm is None:
                miss.append(f"H1 {k}: no matching account")
        if h1x["flags"]:
            entry["notes"].extend(sorted(set(h1x["flags"])))

    # fs_div summary
    divs = sorted(set(d for _, d in fs_used))
    if len(divs) == 1:
        entry["fs_div"] = divs[0]
    elif divs:
        entry["fs_div"] = "/".join(f"{p}:{d}" for p, d in fs_used)
    if "OFS" in divs:
        stats["ofs_fallback"] += 1
        entry["notes"].append("OFS fallback (no CFS income-statement rows)")

    # revenue-account note (non-매출액 mapping)
    for x, tag in ((q1x, "q1"), (h1x, "h1")):
        if x and x["accounts"].get("rev") and x["accounts"]["rev"] not in ("매출액", "수익(매출액)"):
            entry["notes"].append(f"rev account ({tag}): {x['accounts']['rev']}")
    if any(n.startswith("rev account") for n in entry["notes"]):
        stats["rev_mapped"] += 1
    # ni-account note when quarterly naming used
    for x, tag in ((q1x, "q1"), (h1x, "h1")):
        if x and x["accounts"].get("ni") and norm(x["accounts"]["ni"]) not in ("당기순이익", "당기순이익(손실)"):
            entry["notes"].append(f"ni account ({tag}): {x['accounts']['ni']}")

    # q2 = h1 - q1 (원 단위에서 빼고 억 변환)
    if q1x and h1x:
        for k in ("rev", "op", "ni"):
            a, b = h1x["cur"].get(k), q1x["cur"].get(k)
            entry["q2"][k] = eok(a - b) if (a is not None and b is not None) else None
    if all(entry["q2"][k] is not None for k in ("rev", "op", "ni")):
        stats["full_q2"] += 1

    if miss:
        entry["missing"] = "; ".join(miss)
        stats["missing"] += 1
    entry["notes"] = sorted(set(entry["notes"]))
    if not entry["notes"]:
        del entry["notes"]
    result[code] = entry

out = {
    "asof": calendar.get("asof"),
    "bsns_year": 2026,
    "unit": "억원 (1e8 KRW, 1dp)",
    "source": "DART fnlttSinglAcnt (11013 Q1, 11012 half-year)",
    "field_semantics": {
        "q1": "11013 thstrm_amount (3-month)",
        "h1": "11012 thstrm_add_amount (cumulative; thstrm_amount fallback flagged)",
        "h1_prior": "11012 frmtrm_add_amount (prior-year cumulative half)",
        "q2": "h1 - q1 (null if either missing)",
    },
    "stats": stats,
    "byCode": result,
}
(SCRATCH / "ec_actuals.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

# cp949-safe console summary
print("total:", stats["total"], "| full_q2:", stats["full_q2"],
      "| ofs_fallback:", stats["ofs_fallback"], "| with_missing:", stats["missing"],
      "| rev_mapped:", stats["rev_mapped"])
for code, e in result.items():
    if e.get("missing"):
        print("MISS", code, "|", e["missing"].encode("ascii", "backslashreplace").decode())

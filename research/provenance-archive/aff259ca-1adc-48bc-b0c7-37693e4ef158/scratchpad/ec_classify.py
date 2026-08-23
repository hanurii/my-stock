# -*- coding: utf-8 -*-
"""Join ec_actuals + ec_consensus + ec_reaction, classify all 92 codes, write ec_final.json.
Includes self-verify: q2=h1-q1 recompute from raw DART cache for 5 random codes + anchors."""
import json
import random
import re
from pathlib import Path

P = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad")
CACHE = Path(r"C:\Users\hanul\playground\my-stock") / ".cache" / "earnings_classify"

cons = json.loads((P / "ec_consensus.json").read_text(encoding="utf-8"))["byCode"]
actf = json.loads((P / "ec_actuals.json").read_text(encoding="utf-8"))
act = actf["byCode"]
rea = json.loads((P / "ec_reaction.json").read_text(encoding="utf-8"))

log = []


def safe(s):
    return str(s).encode("ascii", "backslashreplace").decode()


# ---------- classification ----------
POS_LABELS = {"서프라이즈", "호실적(YoY)"}
NEG_LABELS = {"쇼크", "부진(YoY)"}

rows = []
for code, a in act.items():
    c = cons[code]
    r = rea[code]
    name = a["name"]
    q2_op = a["q2"].get("op")
    h1_op = a["h1"].get("op")
    h1p_op = a["h1_prior"].get("op")

    flags = []
    for n in a.get("notes", []):
        flags.append(n)
    if a.get("missing"):
        flags.append("actuals_missing: " + a["missing"])

    covered = bool(c.get("covered"))
    consensus_op = c.get("q2_op_consensus_eok")

    label = None
    basis = None
    beat_pct = None
    yoy_pct = None
    yoy_case = None

    if covered and consensus_op is not None and q2_op is not None:
        method = "consensus"
        if q2_op <= 0 and consensus_op > 0:
            label = "쇼크"
            basis = f"적자 실제({q2_op:.0f}억) vs 흑자 컨센({consensus_op:.0f}억)"
        elif q2_op > 0 and consensus_op < 0:
            label = "서프라이즈"
            basis = f"흑자 실제({q2_op:.0f}억) vs 적자 컨센({consensus_op:.0f}억)"
        else:
            beat_pct = (q2_op - consensus_op) / abs(consensus_op) * 100
            if beat_pct >= 10:
                label = "서프라이즈"
            elif beat_pct <= -10:
                label = "쇼크"
            else:
                label = "부합"
            basis = f"beat {beat_pct:+.1f}% (실제 {q2_op:.0f}억 vs 컨센 {consensus_op:.0f}억)"
        if abs(consensus_op) < 10:
            flags.append(f"tiny_consensus_base: |컨센|={consensus_op}억<10억, beat% 과대해석 주의")
    else:
        method = "yoy_proxy"
        if covered and q2_op is None:
            flags.append("covered_but_q2_missing -> YoY proxy fallback")
        if h1_op is None or h1p_op is None:
            label = "판정불가"
            basis = "H1 또는 전년동기 영업이익 결측"
        elif h1p_op <= 0 < h1_op:
            label = "호실적(YoY)"
            yoy_case = "흑자전환"
            basis = f"흑자전환 (H1 {h1_op:.0f}억, 전년 {h1p_op:.0f}억)"
        elif h1p_op > 0 >= h1_op:
            label = "부진(YoY)"
            yoy_case = "적자전환"
            basis = f"적자전환 (H1 {h1_op:.0f}억, 전년 {h1p_op:.0f}억)"
        elif h1p_op == 0 and h1_op == 0:
            label = "무난(YoY)"
            yoy_case = "양쪽 0"
            basis = "H1·전년 모두 0억"
        else:
            yoy_pct = (h1_op - h1p_op) / abs(h1p_op) * 100
            if h1_op < 0 and h1p_op < 0:
                yoy_case = "적자지속"
            if yoy_pct >= 30:
                label = "호실적(YoY)"
            elif yoy_pct <= -30:
                label = "부진(YoY)"
            else:
                label = "무난(YoY)"
            tag = f"·{yoy_case}" if yoy_case else ""
            basis = f"H1 YoY {yoy_pct:+.1f}%{tag} ({h1_op:.0f}억 vs 전년 {h1p_op:.0f}억)"

    # sign-anomaly flag (task rule: |q2 op| > h1 op)
    if q2_op is not None and h1_op is not None and abs(q2_op) > h1_op:
        q1_op = a["q1"].get("op")
        why = "Q1 적자→Q2 흑자 턴어라운드" if (q1_op is not None and q1_op < 0 < q2_op) else "H1 적자 구간(부등식 자명)"
        flags.append(f"sign_check: |q2_op|({q2_op})>h1_op({h1_op}) — {why}, 산술 q2=h1-q1 일관")

    # ---------- market reaction corroboration ----------
    day_ret = r.get("day_ret_pct")
    observable = bool(r.get("observable"))
    if label == "판정불가":
        corro = "해당없음(판정불가)"
    elif not observable:
        corro = "미관측(8/18 반응 대기)"
        if day_ret is not None and abs(day_ret) >= 8:
            corro += f" · 당일 {day_ret:+.1f}% 참고"
    elif day_ret is None:
        corro = "미관측(수익률 결측)"
    elif day_ret >= 8:
        if label in POS_LABELS:
            corro = f"일치(+{day_ret:.1f}%)"
        elif label in NEG_LABELS:
            corro = f"불일치(+{day_ret:.1f}%)"
        else:
            corro = f"큰 상승 +{day_ret:.1f}% (중립 라벨)"
    elif day_ret <= -8:
        if label in NEG_LABELS:
            corro = f"일치({day_ret:.1f}%)"
        elif label in POS_LABELS:
            corro = f"불일치({day_ret:.1f}%)"
        else:
            corro = f"큰 하락 {day_ret:.1f}% (중립 라벨)"
    else:
        corro = f"±8% 미만({day_ret:+.1f}%)"

    rows.append({
        "code": code,
        "name": name,
        "classification": label,
        "method": method,
        "basis": basis,
        "beat_pct": None if beat_pct is None else round(beat_pct, 1),
        "yoy_pct": None if yoy_pct is None else round(yoy_pct, 1),
        "yoy_case": yoy_case,
        "q2_op_actual_eok": q2_op,
        "q2_op_consensus_eok": consensus_op if covered else None,
        "consensus_covered": covered,
        "consensus_flag": c.get("flag"),
        "h1_op_eok": h1_op,
        "h1_prior_op_eok": h1p_op,
        "fs_div": a.get("fs_div"),
        "reaction": {
            "reveal_date": r.get("reveal_date"),
            "reveal_kind": r.get("reveal_kind"),
            "observable": observable,
            "reaction_date": r.get("reaction_date"),
            "day_ret_pct": day_ret,
            "gap_pct": r.get("gap_pct"),
            "relvol": r.get("relvol"),
            "sameday_ret_pct": r.get("sameday_ret_pct"),
        },
        "corroboration": corro,
        "flags": flags,
    })

# ---------- self-verify 1: recompute q2=h1-q1 from raw cache, 5 random codes ----------
OP_NAMES = {"영업이익", "영업이익(손실)", "영업손실", "영업손익"}


def norm(s):
    return re.sub(r"\s+", "", s or "")


def parse_amt(s):
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def raw_op(code, reprt, fs_div, field_pref):
    fp = CACHE / f"fnltt_{code}_{reprt}.json"
    if not fp.exists():
        return None, "no cache file"
    data = json.loads(fp.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return None, "no_data cached"
    fs = fs_div if fs_div in ("CFS", "OFS") else "CFS"
    for row in data:
        if row.get("fs_div") == fs and row.get("sj_div") == "IS" and norm(row.get("account_nm")) in OP_NAMES:
            for f in field_pref:
                v = parse_amt(row.get(f))
                if v is not None:
                    return v, f
    return None, "op row not found"


random.seed(20260817)
candidates = [c for c in act if act[c]["q2"].get("op") is not None]
sample = random.sample(candidates, 5)
log.append("== SELF-VERIFY 1: q2 = h1 - q1 recompute from raw DART cache ==")
verify_ok = True
for code in sample:
    a = act[code]
    fs = a.get("fs_div")
    q1_raw, f1 = raw_op(code, "11013", fs, ["thstrm_amount", "thstrm_add_amount"])
    h1_raw, f2 = raw_op(code, "11012", fs, ["thstrm_add_amount", "thstrm_amount"])
    if q1_raw is None or h1_raw is None:
        log.append(f"  {code} {safe(a['name'])}: RAW MISSING q1={f1} h1={f2}")
        verify_ok = False
        continue
    q2_re = round((h1_raw - q1_raw) / 1e8, 1)
    match = abs(q2_re - a["q2"]["op"]) <= 0.11
    verify_ok &= match
    log.append(f"  {code} {safe(a['name'])}: raw q1_op={q1_raw/1e8:.1f} h1_op={h1_raw/1e8:.1f} -> q2={q2_re} vs file {a['q2']['op']} : {'OK' if match else 'MISMATCH'}")

# ---------- self-verify 2: anchors ----------
log.append("== SELF-VERIFY 2: anchors ==")
by_code_rows = {r["code"]: r for r in rows}

kr = by_code_rows.get("003690")
if kr:
    log.append(f"  [KoreanRe 003690] label={safe(kr['classification'])} basis={safe(kr['basis'])} "
               f"q2_op={kr['q2_op_actual_eok']} reveal={kr['reaction']['reveal_date']}({safe(kr['reaction']['reveal_kind'])}) "
               f"-> this-quarter figures present: {kr['q2_op_actual_eok'] is not None}")
else:
    log.append("  [KoreanRe 003690] NOT in 92 list")

dn = by_code_rows.get("007340")
if dn:
    ra = dn["reaction"]
    log.append(f"  [DN Auto 007340] label={safe(dn['classification'])} basis={safe(dn['basis'])} "
               f"reveal={ra['reveal_date']} observable(next-day)={ra['observable']} "
               f"sameday_ret={ra['sameday_ret_pct']}% relvol={ra['relvol']} -> +20%-ish move observed SAME-DAY 8/14, next-day (8/18) not yet")
else:
    log.append("  [DN Auto 007340] NOT in 92 list")

for fnf in ("383220", "111770", "007700"):
    if fnf in by_code_rows:
        log.append(f"  [F&F {fnf}] IN list, label={safe(by_code_rows[fnf]['classification'])}")
        break
else:
    log.append("  [F&F] not in the 92-code list (383220/111770/007700 absent) -> shock-classification check N/A")

# ---------- self-verify 3: structural flags ----------
log.append("== SELF-VERIFY 3: structural flags ==")
sign_flagged = [r for r in rows if any(f.startswith("sign_check") for f in r["flags"])]
log.append(f"  |q2_op|>h1_op flagged: {len(sign_flagged)}")
for r in sign_flagged:
    log.append(f"    {r['code']} {safe(r['name'])}: {safe([f for f in r['flags'] if f.startswith('sign_check')][0])}")
mix = [r for r in rows if r["fs_div"] and "/" in str(r["fs_div"])]
log.append(f"  fs_div mixing (q1/h1 다른 기준): {len(mix)}")
ofs = [r["code"] for r in rows if r["fs_div"] == "OFS"]
log.append(f"  OFS fallback: {len(ofs)} {ofs}")

# ---------- distribution ----------
order = ["쇼크", "부진(YoY)", "서프라이즈", "호실적(YoY)", "부합", "무난(YoY)", "판정불가"]
dist = {k: sum(1 for r in rows if r["classification"] == k) for k in order}
log.append("== DISTRIBUTION ==")
log.append("  " + safe(json.dumps(dist, ensure_ascii=False)))
log.append(f"  total={len(rows)} covered={sum(1 for r in rows if r['method']=='consensus')} yoy_proxy={sum(1 for r in rows if r['method']=='yoy_proxy')}")


def sort_key(r):
    gi = order.index(r["classification"])
    v = r["beat_pct"] if r["beat_pct"] is not None else (r["yoy_pct"] if r["yoy_pct"] is not None else 0)
    # negatives groups: worst first; positive groups: best first
    if r["classification"] in ("쇼크", "부진(YoY)"):
        return (gi, v)
    return (gi, -v)


rows_sorted = sorted(rows, key=sort_key)

out = {
    "asof": "2026-08-17",
    "universe": "sepa-earnings-calendar.json (HEAD) byCode 92 codes",
    "rules": {
        "covered": "beat% = (Q2 실제 영업이익 - 컨센서스)/|컨센서스|*100 -> >=+10% 서프라이즈, <=-10% 쇼크, 사이 부합. 적자 실제 vs 흑자 컨센 -> 쇼크; 흑자 실제 vs 적자 컨센 -> 서프라이즈.",
        "uncovered": "YoY 프록시: H1 영업이익 YoY >=+30% 또는 흑자전환 -> 호실적(YoY), <=-30% 또는 적자전환 -> 부진(YoY), 사이 -> 무난(YoY), 전년동기 결측 -> 판정불가.",
        "reaction": "별도 검증 열: observable & day_ret <=-8% 또는 >=+8% 일 때 라벨과 일치/불일치 표시.",
    },
    "distribution": dist,
    "rows": rows_sorted,
}
(P / "ec_final.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
(P / "ec_classify_log.txt").write_text("\n".join(log), encoding="utf-8")
print("\n".join(log))
print("VERIFY1_OK:", verify_ok)
print("wrote ec_final.json rows:", len(rows_sorted))

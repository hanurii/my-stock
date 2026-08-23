# -*- coding: utf-8 -*-
"""TASK 3: ec_report_v2.md — 결론 먼저, 분포, 발표시점 분포, 교차표, 92행 테이블."""
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"

with open(os.path.join(SCRATCH, "ec_final_v2.json"), encoding="utf-8") as f:
    final = json.load(f)
rows = final["rows"]

ORDER = ["쇼크", "부진(YoY)", "서프라이즈", "호실적(YoY)", "부합", "무난(YoY)"]
POS = {"서프라이즈", "호실적(YoY)"}
NEG = {"쇼크", "부진(YoY)"}


def sort_key(r):
    cls = r["classification"]
    v = r["beat_pct"] if r["beat_pct"] is not None else (r["yoy_pct"] if r["yoy_pct"] is not None else 0)
    gi = ORDER.index(cls)
    # 쇼크/부진: 가장 나쁜 것부터. 서프라이즈/호실적: 가장 좋은 것부터. 부합/무난: 값 내림차순.
    if cls in NEG:
        return (gi, v)
    return (gi, -v)


rows_sorted = sorted(rows, key=sort_key)


def md(d):
    """'2026-08-14' -> '8/14'"""
    if not d:
        return "?"
    return f"{int(d[5:7])}/{int(d[8:10])}"


def fmt_when(r):
    t = r["timing"]
    s = f"{md(r['reaction']['reveal_date'])} {t['timing_class']}"
    if t["time"]:
        s += f" ({t['time']})"
    return s


def fmt_reaction(r):
    t = r["timing"]
    if not t["observable_v2"]:
        return f"{md(t['reaction_date_v2'])} 대기"
    ret = t["reaction_ret"]
    rv = t["reaction_relvol"]
    s = f"{ret:+.1f}%"
    if rv is not None:
        s += f" ·거래량{rv:.1f}배"
    return s


def fmt_basis(r):
    if r["method"] == "consensus":
        return f"beat {r['beat_pct']:+.1f}%"
    if r["yoy_case"] and r["yoy_case"] != "yoy":
        return f"YoY {r['yoy_case']}"
    if r["yoy_pct"] is not None:
        return f"YoY {r['yoy_pct']:+.1f}%"
    return "—"


def fmt_op(r):
    v = r["q2_op_actual_eok"]
    if v is None:
        return "—"
    return f"{v:,.0f}"


# ---- aggregates ----
cls_dist = Counter(r["classification"] for r in rows)
timing_dist = Counter(r["timing"]["timing_class"] for r in rows)
kind_timing = defaultdict(Counter)
for r in rows:
    kind_timing[r["reaction"]["reveal_kind"]][r["timing"]["timing_class"]] += 1
cross = defaultdict(Counter)
for r in rows:
    cross[r["classification"]][r["timing"]["timing_class"]] += 1

concord = Counter(r["concord_v2"] for r in rows)
# concord among observable, directional classes only
dir_obs = [r for r in rows if r["timing"]["observable_v2"] and r["classification"] in POS | NEG]
dir_c = Counter(r["concord_v2"] for r in dir_obs)

n_814 = sum(1 for r in rows if r["reaction"]["reveal_date"] == "2026-08-14")
n_814_obs = sum(1 for r in rows if r["reaction"]["reveal_date"] == "2026-08-14" and r["timing"]["observable_v2"])
obs_v2 = sum(1 for r in rows if r["timing"]["observable_v2"])

# v1 -> v2 remap size: how many rows' reaction day moved (장전/장중 on trading-day reveal)
n_remap = sum(1 for r in rows
              if r["timing"]["timing_class"] in ("장전", "장중")
              and r["reaction"].get("reaction_date") != r["timing"]["reaction_date_v2"])

TCLS = ["장전", "장중", "장후", "시각미상"]

L = []
L.append("# 실적 분류 92종목 — 발표시각 반영 v2 (2026-08-17)")
L.append("")
L.append("## 결론")
L.append("")
L.append(f"- **발표시각 92/92 전수 확보** (출처: KIND 상장공시시스템 공시시각, 보조검증 다음금융). 시각미상 0건.")
L.append(f"- 발표시점: 장전 {timing_dist['장전']} · 장중 {timing_dist['장중']} · 장후 {timing_dist['장후']}. "
         f"**과반({timing_dist['장전']+timing_dist['장중']}건, {100*(timing_dist['장전']+timing_dist['장중'])/len(rows):.0f}%)이 장전·장중 발표** → 시장 반응은 발표 '다음날'이 아니라 **당일**에 봐야 맞는 종목이 절반 이상.")
L.append(f"- 반응일 재배정: {n_remap}건의 반응일이 다음날→당일로 이동. 8/14 공시 {n_814}건 중 **{n_814_obs}건(장중 발표)이 당일 데이터로 관측 가능**해졌고, 장후 발표 {n_814-n_814_obs}건만 8/18 대기.")
L.append(f"- 관측 가능 {obs_v2}/92. 방향성 분류(서프라이즈·호실적·쇼크·부진) 중 관측된 {len(dir_obs)}건의 정합: ✓ {dir_c['✓']} · ✗ {dir_c['✗']} · ±8%미만 {dir_c['·']} — **±8% 이상 움직인 경우 정합({dir_c['✓']})이 역행({dir_c['✗']})보다 많음**.")
L.append(f"- 잠정실적·반기보고서 모두 장중 발표가 최다(잠정 {kind_timing['잠정']['장중']}/{sum(kind_timing['잠정'].values())}, 반기 {kind_timing['반기보고서']['장중']}/{sum(kind_timing['반기보고서'].values())}). '실적은 장 마감 후 나온다'는 통념과 달리 **3분의 2가 장중·장전에 공개**됐다.")
L.append("")
L.append("## 분류 분포")
L.append("")
L.append("| " + " | ".join(ORDER) + " |")
L.append("|" + "---:|" * len(ORDER))
L.append("| " + " | ".join(str(cls_dist[c]) for c in ORDER) + " |")
L.append("")
L.append("## 발표시점 분포 (발표 종류별)")
L.append("")
L.append("| 종류 | 장전 | 장중 | 장후 | 시각미상 | 계 |")
L.append("|---|---:|---:|---:|---:|---:|")
for k in ["잠정", "반기보고서"]:
    c = kind_timing[k]
    L.append(f"| {k} | {c['장전']} | {c['장중']} | {c['장후']} | {c['시각미상']} | {sum(c.values())} |")
L.append(f"| **계** | {timing_dist['장전']} | {timing_dist['장중']} | {timing_dist['장후']} | {timing_dist['시각미상']} | {len(rows)} |")
L.append("")
L.append("## 교차표: 분류 × 발표시점")
L.append("")
L.append("| 분류 | 장전 | 장중 | 장후 | 계 |")
L.append("|---|---:|---:|---:|---:|")
for c in ORDER:
    cc = cross[c]
    L.append(f"| {c} | {cc['장전']} | {cc['장중']} | {cc['장후']} | {sum(cc.values())} |")
L.append("")
L.append("## 전체 92종목")
L.append("")
L.append("- 반응 = 발표가 장전/장중이면 **공시 당일**, 장후면 **다음 거래일**의 등락률·상대거래량(직전 50일 평균 대비).")
L.append("- 정합: 방향성 분류는 반응 ±8% 이상이 같은 방향이면 ✓, 반대면 ✗, ±8% 미만이면 ·. 부합/무난은 ±8% 미만이면 ✓(조용한 반응=정합). 미관측 —.")
L.append("")
L.append("| 종목(코드) | 분류 | 근거 | Q2 영업이익(억) | 발표일·시점 | 반응 | 정합 |")
L.append("|---|---|---|---:|---|---|:-:|")
for r in rows_sorted:
    L.append(f"| {r['name']}({r['code']}) | {r['classification']} | {fmt_basis(r)} | {fmt_op(r)} | {fmt_when(r)} | {fmt_reaction(r)} | {r['concord_v2']} |")
L.append("")
L.append("---")
L.append("*발표시각 출처: KIND(kind.krx.co.kr) 공시목록 공시시각. 장전<09:00 · 장중 09:00~15:30 · 장후>15:30 (KRX 정규장). "
         "당일 반응 재계산은 OHLCV 캐시(~8/14) 기준. 8/18 대기 = 8/14 장후 공시분.*")

out = "\n".join(L)
with open(os.path.join(SCRATCH, "ec_report_v2.md"), "w", encoding="utf-8") as f:
    f.write(out)
print("report written, lines:", len(L))
print("concord all:", dict(concord))
print("dir obs:", len(dir_obs), dict(dir_c))
print("cross:", {c: dict(cross[c]) for c in ORDER})
print("kind_timing:", {k: dict(v) for k, v in kind_timing.items()})
print("n_remap:", n_remap)

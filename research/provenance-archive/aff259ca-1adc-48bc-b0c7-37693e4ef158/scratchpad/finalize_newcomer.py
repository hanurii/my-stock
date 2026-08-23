# -*- coding: utf-8 -*-
"""Assemble newcomer_flag.json + newcomer_flag.md"""
import json, os
from scipy.stats import fisher_exact

SCRATCH = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(SCRATCH, "newcomer_raw_results.json"), encoding="utf-8"))


def grp(rows):
    n = len(rows)
    if n == 0:
        return {"n": 0, "wins": 0, "win_rate": None, "avg_net": None, "sum_net": None}
    w = sum(1 for x in rows if x["win"])
    nets = [x["net_pct"] for x in rows if x["net_pct"] is not None]
    return {"n": n, "wins": w, "win_rate": round(100 * w / n, 1),
            "avg_net": round(sum(nets) / len(nets), 2), "sum_net": round(sum(nets), 2)}


def fp(a, b):
    if not a or not b:
        return None
    aw = sum(1 for x in a if x["win"]); bw = sum(1 for x in b if x["win"])
    return round(fisher_exact([[aw, len(a) - aw], [bw, len(b) - bw]])[1], 4)


def vflag(x, ten, rs, op):
    a = x["tenure10_strict"] <= ten if ten is not None else None
    b = (x["rs_display"] is not None and x["rs_display"] <= rs) if rs is not None else None
    if a is None: return bool(b)
    if b is None: return bool(a)
    return (a or b) if op == "OR" else (a and b)


L = R["trades_listing"]
Ball = [x for x in R["bt_listing"] if not x["still_open"]]
Bh5 = [x for x in Ball if x["n_prior_snaps"] >= 5]

# ---- bt h5 supplementary analyses ----
bth5 = {
    "n": len(Bh5), "baseline": grp(Bh5),
    "newcomer": grp([x for x in Bh5 if x["tenure10_strict"] <= 2]),
    "mid_3_4": grp([x for x in Bh5 if 3 <= x["tenure10_strict"] <= 4]),
    "regular_ge5": grp([x for x in Bh5 if x["tenure10_strict"] >= 5]),
    "fisher_new_vs_reg": fp([x for x in Bh5 if x["tenure10_strict"] <= 2],
                            [x for x in Bh5 if x["tenure10_strict"] >= 5]),
    "rs_le82": grp([x for x in Bh5 if x["rs_display"] is not None and x["rs_display"] <= 82]),
    "rs_83_89": grp([x for x in Bh5 if x["rs_display"] is not None and 83 <= x["rs_display"] <= 89]),
    "rs_ge90": grp([x for x in Bh5 if x["rs_display"] is not None and x["rs_display"] >= 90]),
    "fisher_rslo_vs_hi": fp([x for x in Bh5 if x["rs_display"] is not None and x["rs_display"] <= 82],
                            [x for x in Bh5 if x["rs_display"] is not None and x["rs_display"] >= 90]),
    "flag_proposed": {
        "flagged": grp([x for x in Bh5 if vflag(x, 2, 82, "OR")]),
        "kept": grp([x for x in Bh5 if not vflag(x, 2, 82, "OR")]),
        "fisher": fp([x for x in Bh5 if vflag(x, 2, 82, "OR")],
                     [x for x in Bh5 if not vflag(x, 2, 82, "OR")]),
    },
    "variant_ten1_and_rs84": {
        "flagged": grp([x for x in Bh5 if vflag(x, 1, 84, "AND")]),
        "kept": grp([x for x in Bh5 if not vflag(x, 1, 84, "AND")]),
        "flagged_names": [f'{x["name"]}({x["entry_date"]},{x["net_pct"]:+.1f})' for x in Bh5 if vflag(x, 1, 84, "AND")],
    },
}

divergent = [x for x in L if x["tenure10_strict"] <= 2 and x["tenure10_loose"] > 2]

variant_best = {
    "tenure_only_le2": {
        "flagged_trades": [f'{x["name"]}({x["open_date"]},{x["net_pct"]:+.1f}%)' for x in L if vflag(x, 2, None, "-")],
        "trades": {"flagged": grp([x for x in L if vflag(x, 2, None, "-")]),
                   "kept": grp([x for x in L if not vflag(x, 2, None, "-")])},
        "bt_h5": {"flagged": grp([x for x in Bh5 if vflag(x, 2, None, "-")]),
                  "kept": grp([x for x in Bh5 if not vflag(x, 2, None, "-")])},
    },
    "ten1_and_rs84": {
        "flagged_trades": [f'{x["name"]}({x["open_date"]},{x["net_pct"]:+.1f}%)' for x in L if vflag(x, 1, 84, "AND")],
        "trades": {"flagged": grp([x for x in L if vflag(x, 1, 84, "AND")]),
                   "kept": grp([x for x in L if not vflag(x, 1, 84, "AND")])},
        "bt_h5": bth5["variant_ten1_and_rs84"],
    },
}

conclusions = {
    "headline": "신참(직전 10스냅샷 중 8/8 통과 2회 이하) 실거래 12건 승률 16.7%·평균 -4.96% vs 단골(5회 이상) 29건 41.4%·-0.44% — 방향은 가설 지지, Fisher p=0.165로 유의하지는 않음(표본 소)",
    "anchors": "F&F(tenure=1, streak=1, RS81, RS변동폭15↑ 유일 최대)·대양금속(tenure=0, 직전 스냅샷 7/8, RS80) 둘 다 신참+RS바닥 정의에 정확히 부합",
    "independence": "신참 열세는 셋업null·조정국면·저거래량의 재탕이 아님 — 셋업 있는 거래 안에서도 20% vs 48.5%, 조정국면 안에서도 18.2% vs 32.3%, relvol<1 안에서도 14.3% vs 50%로 유지",
    "loose_definition": "7/8 통과까지 재직으로 쳐주면(loose) 신호 소멸(승률 28.6%, p=1.0). 엄격/느슨 판정이 갈린 5건(GS우·제이에스링크·에스에스알·일지테크·F&F)은 전부 손실 = '만성 7/8 언저리였다가 방금 편입된 종목'이 정확히 위험군",
    "rs_floor_alone": "RS<=82 단독은 실거래에서 승률 신호 없음(37.5%, p=1.0) — 평균 -4.51%는 F&F 한 건이 끌어내린 것. 백테스트에서는 오히려 RS<=82가 최고 그룹(43%/+2.52)·RS>=90이 최악(14%/-6.05)으로 역방향",
    "proposed_flag": "제안 플래그(tenure<=2 OR rs<=82): 34패 중 11패 포착(32%)·19승 중 4승 오검출(타이거일렉7/1 +7.6%p는 스냅샷 이력 1개뿐인 초기 아티팩트, 가비아 +0.8, 한국주강 +0.6, 달바글로벌 +5.2). 남긴 38건 평균 -0.37%로 개선(전체 -1.37%). 단 손실의 68%는 못 잡음(DN오토모티브형 단골 손실) — 배제 필터가 아니라 주의 배지 수준",
    "backtest_reversal": "백테스트(청산 74건, 이력>=5 35건)에서는 tenure·RS 효과 모두 역전 — 플래그가 오히려 나은 그룹을 걸러냄(남긴 그룹 16% vs 걸러낸 그룹 31%). 백테스트 모집단은 forming 피벗매수+조정국면+기계적 20/10 청산이라 실거래와 다른 동물; 실거래 신호가 이 표본에는 이식 안 됨",
    "recommendation": "추천: (a) 넓게 = tenure10<=2 단독(10패/2승 포착, 남긴 41건 -0.33%), (b) 정밀 = tenure10<=1 AND rs<=84(6건 전부 손실: 나이스정보통신·오리온·GS우·에스에스알·F&F·대양금속, 승 희생 0, 회피 +48.7%p; 백테스트 h5에서도 3건만 걸러 거의 중립). RS<=82 OR 결합은 실거래에서 오검출만 보태고 백테스트에선 역신호라 비추천",
    "caveats": "전부 사후 튜닝·인샘플(n=53, 신참 12)·모든 p>0.1. 7월 초 7건은 스냅샷 이력<5개라 tenure 측정 자체가 불가(타이거일렉 7/1 오검출의 원인). 8/3부터 스냅샷 유니버스 축소(2485→1346)됐으나 all_pass 판정에는 영향 없음. 하드 배제 말고 ⚠️ 배지+비중 축소 용도로만",
}

final = {
    "meta": R["meta"],
    "definitions": {
        "tenure10_strict": "진입일 09:00 이전 마지막 10개 스냅샷 중 all_pass(8/8) 횟수",
        "tenure10_loose": "같은 창에서 passed_count>=7 횟수",
        "streak": "직전 스냅샷에서 끝나는 연속 all_pass 길이(창 제한 없음)",
        "newcomer": "(직전 스냅샷 all_pass 또는 페이지 노출) AND tenure10_strict<=2",
        "regular": "tenure10_strict>=5",
        "rs_floor": "표시 RS<=82",
        "rs_vol10": "창 내 RS 최대-최소",
    },
    "trades_split": R["trades_split"],
    "trades_split_excl_low_history": R["trades_split_excl_low_history"],
    "crosstabs": {"setup": R["crosstab_setup"], "regime": R["crosstab_regime"], "relvol": R["crosstab_relvol"]},
    "newcomer_composition": R["newcomer_composition"],
    "strict_loose_divergent_trades": [
        {"name": x["name"], "open_date": x["open_date"], "net_pct": x["net_pct"],
         "tenure_strict": x["tenure10_strict"], "tenure_loose": x["tenure10_loose"]} for x in divergent],
    "flag_proposed_trades": R["flag_proposed_trades"],
    "bt_closed_split_all": R["bt_closed_split"],
    "bt_closed_hist_ge5": bth5,
    "flag_proposed_bt_closed_all": R["flag_proposed_bt_closed"],
    "variants_trades": R["variants_trades"],
    "variants_recommended": variant_best,
    "trades_listing": R["trades_listing"],
    "bt_listing": R["bt_listing"],
    "conclusions": conclusions,
}
with open(os.path.join(SCRATCH, "newcomer_flag.json"), "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=1)
print("json written")

# ---------------- markdown ----------------
def g(d, pct=True):
    if d["n"] == 0:
        return "0건"
    return f'{d["n"]}건 · 승률 {d["win_rate"]}% · 평균 {d["avg_net"]:+.2f}%'

ts = R["trades_split"]; te = R["trades_split_excl_low_history"]
fpt = R["flag_proposed_trades"]

md = []
md.append("# 문턱 신참(threshold newcomer) 가설 검증 — tenure·RS바닥 주의 플래그\n")
md.append("**가설**: 8조건 관문을 처음(또는 하루만) 전부 통과했거나 RS가 입장 커트라인(80) 언저리인 종목은 목록 단골보다 실패가 잦다. 앵커: F&F(7/31 매수, -21.25%)·대양금속(8/13, -4.91%).\n")
md.append("## 방법\n")
md.append("- 스냅샷: `sepa-trend-candidates.json` 날짜별 마지막 커밋 31개(6/30~8/15). 매수일 D의 기준 = D 09:00 이전 마지막 스냅샷.")
md.append("- **tenure10** = 직전 10개 스냅샷 중 8/8 전부통과 횟수(엄격) / 7개 이상 통과 횟수(느슨). **streak** = 직전 스냅샷에서 끝나는 연속 전부통과. **신참** = tenure10(엄격)<=2, **단골** = >=5.")
md.append("- 주의: 7/1~7/3 매수 7건은 확보된 이전 스냅샷이 1~3개뿐(tenure 측정 불가에 가까움). 8/3부터 스냅샷 수록 종목이 2485→1346으로 줄었으나 전부통과 판정엔 영향 없음.\n")

md.append("## 1) 실거래 53건 — tenure 구분 (기준선: 승률 35.8%, 평균 -1.37%)\n")
md.append("| 구분 | 건수 | 승률 | 평균 손익 |")
md.append("|---|---|---|---|")
for lab, key in [("신참(tenure<=2)", "newcomer"), ("중간(3~4)", "mid_3_4"), ("단골(>=5)", "regular_ge5")]:
    d = ts[key]; md.append(f'| {lab} | {d["n"]} | {d["win_rate"]}% | {d["avg_net"]:+.2f}% |')
md.append(f'\n- Fisher p(신참 vs 단골) = **{ts["fisher_new_vs_reg"]}** — 방향은 가설 지지, 유의 수준엔 미달.')
md.append(f'- 이력<5개 7건 제외해도 신참 {te["newcomer"]["n"]}건 승률 {te["newcomer"]["win_rate"]}%·{te["newcomer"]["avg_net"]:+.2f}% vs 단골 {te["regular_ge5"]["win_rate"]}% — 방향 유지(p={te["fisher_new_vs_reg"]}).')
md.append(f'- **느슨 정의(7/8도 재직으로 인정)면 신호 소멸**: 신참(느슨) 승률 {ts["newcomer_loose"]["win_rate"]}%, p={ts["fisher_loose"]}. 엄격/느슨이 갈린 5건(GS우·제이에스링크·에스에스알·일지테크·F&F)은 **전부 손실** — "만성 7/8 언저리에서 방금 넘어온 종목"이 정확한 위험군.\n')

md.append("## 2) RS 구간·streak·RS변동폭 (실거래)\n")
md.append("| 축 | 구간 | 건수 | 승률 | 평균 |")
md.append("|---|---|---|---|---|")
for lab, key in [("RS", "rs_le82"), ("RS", "rs_83_89"), ("RS", "rs_ge90")]:
    d = ts[key]
    name = {"rs_le82": "<=82(바닥)", "rs_83_89": "83~89", "rs_ge90": ">=90"}[key]
    md.append(f'| RS | {name} | {d["n"]} | {d["win_rate"]}% | {d["avg_net"]:+.2f}% |')
for key, name in [("streak0", "0"), ("streak1", "1"), ("streak2_4", "2~4"), ("streak_ge5", ">=5")]:
    d = ts[key]; md.append(f'| streak | {name} | {d["n"]} | {d["win_rate"]}% | {d["avg_net"]:+.2f}% |')
for key, name in [("rsvol_ge15", ">=15"), ("rsvol_lt15", "<15")]:
    d = ts[key]; md.append(f'| RS변동폭 | {name} | {d["n"]} | {d["win_rate"]}% | {d["avg_net"]:+.2f}% |')
md.append("\n- RS바닥 단독은 승률 신호 없음(p=1.0). 평균 -4.51%는 F&F 한 건 탓. RS변동폭>=15는 F&F 1건뿐이라 판단 불가.")
md.append("- streak는 완만한 단조(>=5연속 42.1% vs 그 미만 ~33%).\n")

md.append("## 3) 독립성 점검 — 기존 축의 재탕인가?\n")
md.append("| 층 | 신참 | 비신참 |")
md.append("|---|---|---|")
ct = R["crosstab_setup"]["setup_null"]["setup_present"]
md.append(f'| 셋업 있음(43건) | {g(ct["newcomer"])} | {g(ct["non_newcomer"])} |')
ct = R["crosstab_regime"]["regime"]["regime_down"]
md.append(f'| 조정국면(42건) | {g(ct["newcomer"])} | {g(ct["non_newcomer"])} |')
ct = R["crosstab_relvol"]["relvol"]["relvol_lt1"]
md.append(f'| relvol<1(37건) | {g(ct["newcomer"])} | {g(ct["non_newcomer"])} |')
nc = R["newcomer_composition"]
md.append(f'\n- 신참 12건 구성: 셋업null {nc["setup_null_share"]}%(전체 {nc["vs_all"]["setup_null_share"]}%), 조정국면 {nc["regime_down_share"]}%(전체 {nc["vs_all"]["regime_down_share"]}%), relvol<1 {nc["relvol_lt1_share"]}%(전체 {nc["vs_all"]["relvol_lt1_share"]}%).')
md.append("- **결론: 재탕 아님.** 셋업이 있어도, 조정국면 안에서도, 저거래량 안에서도 신참이 일관되게 열세. 조정국면 쏠림(92%)은 있으나 층 내 격차가 유지됨.\n")

md.append("## 4) 제안 플래그 평가 — `⚠️ tenure10<=2 OR rs<=82` (실거래 53건)\n")
md.append(f'- 플래그 {fpt["n_flagged"]}건: **34패 중 {fpt["losses_flagged"]}패 포착(32%)**, **19승 중 {fpt["wins_flagged"]}승 오검출**: ' + ", ".join(fpt["wins_flagged_names"]))
md.append(f'- 남긴 {fpt["kept"]["n"]}건: 승률 {fpt["kept"]["win_rate"]}%·평균 {fpt["kept"]["avg_net"]:+.2f}% (전체 -1.37% 대비 개선). 회피 손익 합 +{fpt["net_avoided_sum"]}%p. Fisher p={fpt["fisher_flag"]}.')
md.append("- 앵커 2건(F&F·대양금속) 모두 포착. 타이거일렉 7/1 오검출은 스냅샷 이력이 1개뿐이던 초기 아티팩트(같은 종목 7/10 재진입은 tenure=8로 통과·+14.8% 승). DN오토모티브(-5.0%)는 tenure=7·RS90 단골 손실이라 미포착 — **이 플래그는 손실의 68%를 못 잡는 가장자리 필터임.**\n")

md.append("## 5) 백테스트 교차검증 — 결과 역전 주의\n")
md.append(f'- 청산 완료 74건(코드당 첫 진입), 이력>=5 확보분 35건 기준선: 승률 {bth5["baseline"]["win_rate"]}%·평균 {bth5["baseline"]["avg_net"]:+.2f}%.')
md.append("| 구분 | 신참 | 중간 | 단골 | RS<=82 | RS>=90 |")
md.append("|---|---|---|---|---|---|")
md.append(f'| 이력>=5 (35건) | {g(bth5["newcomer"])} | {g(bth5["mid_3_4"])} | {g(bth5["regular_ge5"])} | {g(bth5["rs_le82"])} | {g(bth5["rs_ge90"])} |')
md.append(f'\n- **tenure·RS 모두 실거래와 반대 방향**(단골 최악 8%/-7.84, RS>=90 최악 14%/-6.05; p 각 {bth5["fisher_new_vs_reg"]}, {bth5["fisher_rslo_vs_hi"]}).')
fb = bth5["flag_proposed"]
md.append(f'- 제안 플래그를 백테스트에 적용하면 **더 나은 그룹을 걸러냄**: 걸러낸 {g(fb["flagged"])} vs 남긴 {g(fb["kept"])}.')
md.append("- 해석: 백테스트 모집단은 forming 피벗 자동매수+조정국면+기계식 +20/-10 청산이라 실거래(사람이 고른 actionable 돌파)와 모집단이 다름. 여기서 '단골'은 몇 주째 관문에 걸려 있는 늦은/소진된 베이스일 가능성. **실거래 신참 신호는 이 표본으로는 확증도 반증도 안 됨 — 이식 실패로 기록.**\n")

md.append("## 6) 변형 탐색 (전부 사후 튜닝 — 인샘플 성적임)\n")
md.append("| 규칙 | 플래그 | 패 포착 | 승 희생 | 남긴 평균 | 회피 합 |")
md.append("|---|---|---|---|---|---|")
want = {"tenure10<=2", "tenure10<=2 OR rs<=82", "tenure10<=1 AND rs<=84", "tenure10<=2 AND rs<=84", "rs<=82", "tenure10<=1"}
for v in sorted(R["variants_trades"], key=lambda v: -(v["kept_avg_net"] if v["kept_avg_net"] is not None else -99)):
    if v["rule"].strip() in want:
        md.append(f'| `{v["rule"].strip()}` | {v["n_flagged"]} | {v["losses_flagged"]}/34 | {v["wins_flagged"]}/19 | {v["kept_avg_net"]:+.2f}% | +{v["avoided_net_sum"]:.1f}%p |')
vb = variant_best["ten1_and_rs84"]
md.append(f'\n- **정밀형 추천: `tenure10<=1 AND rs<=84`** — 6건 전부 손실(나이스정보통신·오리온·GS우·에스에스알·**F&F**·**대양금속**), 승 희생 0, 회피 +48.7%p. 백테스트 이력>=5에서도 3건만 걸러 거의 중립({g(vb["bt_h5"]["flagged"])}) → 역신호 부작용 최소.')
md.append("- **넓은형: `tenure10<=2` 단독** — 남긴 41건 평균 -0.33%로 최고, 승 희생 2건은 이력 아티팩트(타이거일렉 7/1)+미미(가비아 +0.8). 단 백테스트에서는 역방향.")
md.append("- 제안안의 `OR rs<=82` 부분은 실거래에서 오검출(한국주강·달바글로벌)만 보태고 백테스트에선 역신호 → **OR 결합 비추천**.")
md.append("- **정직한 경고**: 위 순위는 53건(신참 12건)에 맞춘 사후 선택이며 모든 p>0.1. 하드 배제가 아니라 ⚠️ 주의 배지+비중 축소 용도로 시작할 것.\n")

md.append("## 7) 전체 53건 목록 (매수일 순)\n")
md.append("| 종목 | 매수일 | 손익% | 승패 | tenure(엄/느) | streak | RS표시 | RS변동폭 | 이력수 | 신참 | 플래그 |")
md.append("|---|---|---|---|---|---|---|---|---|---|---|")
for x in L:
    rv = x["rs_vol10"] if x["rs_vol10"] is not None else "-"
    md.append(f'| {x["name"]} | {x["open_date"][5:]} | {x["net_pct"]:+.2f} | {"승" if x["win"] else "패"} | {x["tenure10_strict"]}/{x["tenure10_loose"]} | {x["streak_strict"]} | {x["rs_display"]} | {rv} | {x["n_prior_snaps"]} | {"O" if x["newcomer"] else ""} | {"⚠️" if x["flag_raw"] else ""} |')

md.append("\n### 앵커 2건의 궤적")
for x in L:
    if x["name"] in ("F&F", "대양금속"):
        trail = " ".join(f'{d[5:]}:{rs if rs is not None else "-"}/{pc if pc is not None else "-"}' for d, rs, pc in x["rs_trail"])
        md.append(f'- **{x["name"]}** ({x["open_date"]}, {x["net_pct"]:+.2f}%): tenure {x["tenure10_strict"]}(엄격)/{x["tenure10_loose"]}(느슨), streak {x["streak_strict"]}, RS변동폭 {x["rs_vol10"]}. 직전 10스냅샷 RS/통과수: {trail}')
md.append("\n- F&F: 10일 내내 5~7개 통과에 머물다 7/29 단 하루 8/8+RS81 → 7/31 매수 → -21.25%. RS변동폭 15는 53건 중 유일 최대.")
md.append("- 대양금속: 매수 전 10스냅샷 중 전부통과 0회(직전이 7/8·RS80), 8/13 당일에야 첫 전부통과 → -4.91%.\n")

md.append("## 결론\n")
for k in ["headline", "independence", "loose_definition", "rs_floor_alone", "proposed_flag", "backtest_reversal", "recommendation", "caveats"]:
    md.append(f"- {conclusions[k]}")
md.append("")

with open(os.path.join(SCRATCH, "newcomer_flag.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print("md written", len("\n".join(md)))

#!/usr/bin/env python3
"""4개 종목 (하나금융지주/SNT에너지/비에이치아이/GS) C+A 원칙 일괄 평가.

C: criteria.evaluate_c_detailed
A: criteria_a.evaluate_a_detailed → 미통과 시 turnaround → 미통과 시 new_listing
"""

from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

from canslim_lib.fetch import (
    fetch_annual,
    fetch_dart_quarterly_eps_history,
    fetch_dart_quarterly_sales_history,
    fetch_integration,
    fetch_majorstock_holding,
    fetch_preliminary_quarter,
    fetch_quarter,
    fetch_yahoo_chart,
    get_row_values,
    load_corp_code_map,
    merge_naver_dart_quarters,
    resolve_corp_code,
    yahoo_symbol,
)
from canslim_lib.criteria import (
    evaluate_c_detailed,
    evaluate_i,
    evaluate_l,
    evaluate_m,
    evaluate_n,
    evaluate_s,
)
from canslim_lib.criteria_a import (
    evaluate_a_detailed,
    evaluate_new_listing_detailed,
    evaluate_turnaround_detailed,
)
from screen_canslim_a import (
    fetch_annual_eps_extended,
    fetch_dart_annual_cfo,
    fetch_dart_industry_code,
    collect_quarterly_eps_for_stability,
    passes_c_main,
)


STOCKS = [
    ("086790", "하나금융지주", "KOSPI"),
    ("100840", "SNT에너지", "KOSPI"),
    ("083650", "비에이치아이", "KOSPI"),
    ("078930", "GS", "KOSPI"),
]


def evaluate_market_state():
    ks = fetch_yahoo_chart("^KS11", "1y", "1d")
    if not ks or len(ks["closes"]) < 220:
        return None, None
    passed, value, detail = evaluate_m(ks["closes"])
    return {"passed": passed, "value": value, "detail": detail}, ks["closes"]


def fmt_pct(v):
    if v is None:
        return "—"
    return f"{v:+.1f}%"


def evaluate_one(code: str, name: str, market: str, corp_map: dict, kospi_closes) -> None:
    print(f"\n{'='*70}")
    print(f"  {code}  {name}")
    print(f"{'='*70}")

    ig = fetch_integration(code)
    if not ig:
        print("  ❌ Naver integration 미수집 — 스킵")
        return

    market_cap = ig.get("market_cap_eok") or 0
    price = ig.get("price") or 0
    print(f"  시총: {market_cap:,.0f}억원 · 현재가: {price:,.0f}원")

    corp_code, common = resolve_corp_code(code, corp_map)

    # ────────────────────────────────────────
    # C 원칙 평가
    # ────────────────────────────────────────
    qtr = fetch_quarter(code)
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    quarter_sales = get_row_values(qtr, "매출액") if qtr else []

    if corp_code and quarter_eps:
        from datetime import datetime as _dt
        cur_year = _dt.now().year
        naver_latest_year = int(quarter_eps[-1][0][:4]) if quarter_eps[-1][0][:4].isdigit() else cur_year
        dart_eps_combined: list = []
        dart_sales_combined: list = []
        eps_old = fetch_dart_quarterly_eps_history(corp_code, naver_latest_year - 1)
        sales_old = fetch_dart_quarterly_sales_history(corp_code, naver_latest_year - 1)
        if eps_old:
            dart_eps_combined.extend(eps_old)
        if sales_old:
            dart_sales_combined.extend(sales_old)
        if cur_year >= naver_latest_year:
            eps_new = fetch_dart_quarterly_eps_history(corp_code, cur_year)
            sales_new = fetch_dart_quarterly_sales_history(corp_code, cur_year)
            if eps_new:
                dart_eps_combined.extend(eps_new)
            if sales_new:
                dart_sales_combined.extend(sales_new)
        if dart_eps_combined:
            quarter_eps = merge_naver_dart_quarters(quarter_eps, dart_eps_combined)
        if dart_sales_combined:
            dart_sales_eok = [(p, v / 1e8) for p, v in dart_sales_combined]
            quarter_sales = merge_naver_dart_quarters(quarter_sales, dart_sales_eok)

    c_detail = evaluate_c_detailed(quarter_eps, quarter_sales)

    print(f"\n  📊 C 원칙 (분기 EPS YoY)")
    print(f"     최신 분기: {c_detail.get('latest_quarter')} · EPS {c_detail.get('latest_eps')} 원")
    print(f"     YoY: {fmt_pct(c_detail.get('yoy_pct'))} (직전 분기 {fmt_pct(c_detail.get('prev_yoy_pct'))}, 가속 Δ {c_detail.get('accel_delta_pp')})")
    print(f"     매출 YoY: {fmt_pct(c_detail.get('sales_yoy_pct'))} · 3분기 가속: {c_detail.get('sales_accel_3q')}")
    print(f"     EPS 가속(3분기 단조): {c_detail.get('eps_accel_3q')} · 12M 신고점: {c_detail.get('eps_new_high')}")
    print(f"     경고: 2분기 연속 감소 {c_detail.get('consecutive_decline_quarters')} · 심각 둔화: {c_detail.get('severe_decel')}")

    # C 메인 통과 여부 (page.tsx 와 동일 로직)
    c_pass = passes_c_main(c_detail)
    if c_pass:
        print(f"     ✅ C 메인 게이트 통과")
    else:
        # 실패 사유 진단
        reasons = []
        yoy = c_detail.get("yoy_pct")
        if yoy is None:
            reasons.append("YoY 계산 불가")
        elif yoy < 25:
            reasons.append(f"YoY {yoy:.1f}% < 25%")
        sales_accel = c_detail.get("sales_accel_3q", False)
        sales_yoy = c_detail.get("sales_yoy_pct")
        if not ((sales_yoy is not None and sales_yoy >= 25) or sales_accel):
            reasons.append(f"매출 동반 미통과 (YoY {sales_yoy}, accel {sales_accel})")
        accel_delta = c_detail.get("accel_delta_pp") or 0
        if not (c_detail.get("eps_accel_3q") or accel_delta > 0):
            reasons.append(f"가속 미통과 (Δ {accel_delta})")
        if (c_detail.get("consecutive_decline_quarters") or 0) >= 2:
            reasons.append(f"2분기 연속 감소")
        if c_detail.get("severe_decel"):
            reasons.append("2/3 둔화")
        print(f"     ❌ C 메인 게이트 미통과: {' / '.join(reasons)}")

    # ────────────────────────────────────────
    # A 원칙 평가 (C 통과 여부 무관, 정보 제공용으로 항상 수행)
    # ────────────────────────────────────────
    annual_eps = fetch_annual_eps_extended(code, corp_code)
    ann = fetch_annual(code)
    annual_roe = get_row_values(ann, "ROE") if ann else []
    induty_code = fetch_dart_industry_code(corp_code) if corp_code else None
    quarterly_eps_for_stability = collect_quarterly_eps_for_stability(code, corp_code)
    latest_qy = c_detail.get("yoy_pct")
    eps_yoy_history = [(str(p), float(v)) for p, v in (c_detail.get("eps_yoy_history") or [])]
    sales_yoy_history = [(str(p), float(v)) for p, v in (c_detail.get("sales_yoy_history") or [])]

    # CPS
    annual_cps: list = []
    if corp_code and market_cap > 0 and price > 0:
        shares = market_cap * 1e8 / price
        if shares > 0:
            cps_years = sorted({int(k[:4]) for k, _ in annual_eps[-3:] if k[:4].isdigit()})
            for y in cps_years:
                cfo = fetch_dart_annual_cfo(corp_code, y)
                if cfo is not None:
                    annual_cps.append((f"{y}12", round(cfo / shares, 2)))
                time.sleep(0.1)

    print(f"\n  📈 A 원칙 (연간 EPS)")
    print(f"     연간 EPS ({len(annual_eps)}년): {', '.join(f'{k[:4]}: {v:,.0f}' for k, v in annual_eps[-5:])}")
    if annual_roe:
        print(f"     연간 ROE: {', '.join(f'{k[:4]}: {v:.1f}%' for k, v in annual_roe[-3:])}")
    print(f"     산업 KSIC: {induty_code} ({'경기민감' if induty_code and induty_code[:2] in ('24','20','17','22','29') else '비경기민감'})")

    a_detail = evaluate_a_detailed(
        annual_eps=annual_eps,
        annual_roe=annual_roe,
        annual_cps=annual_cps,
        latest_quarter_yoy=latest_qy,
        induty_code=induty_code,
        quarterly_eps_for_stability=quarterly_eps_for_stability,
    )

    if a_detail["main_track_pass"]:
        print(f"     ✅ A 메인 트랙 통과")
        print(f"        3년 평균 증가율 {a_detail['three_year_avg_growth']}% · ROE {a_detail['latest_roe']}% · 안정성 {a_detail['earnings_stability_score']}")
        print(f"        배지: {', '.join(a_detail['badges']) if a_detail['badges'] else '—'}")
    else:
        print(f"     ❌ A 메인 미통과: {' / '.join(a_detail['fail_reasons'][:3])}")

        # 턴어라운드 평가
        t_detail = evaluate_turnaround_detailed(
            annual_eps=annual_eps,
            annual_roe=annual_roe,
            quarterly_eps_yoy_history=eps_yoy_history,
            latest_quarter_yoy=latest_qy,
            induty_code=induty_code,
            quarterly_eps_for_stability=quarterly_eps_for_stability,
        )
        if t_detail["turnaround_pass"]:
            print(f"     🔄 턴어라운드 트랙 통과")
            print(f"        연 YoY {t_detail['latest_annual_yoy']}% · {t_detail['two_quarter_surge_detail']}")
            print(f"        TTM 비율: {t_detail['ttm_high_ratio']*100:.0f}%" if t_detail['ttm_high_ratio'] else "        TTM N/A")
            print(f"        배지: {', '.join(t_detail['badges']) if t_detail['badges'] else '—'}")
        elif t_detail["preliminary_turnaround_pass"]:
            print(f"     🟡 예비 턴어라운드 (한두 항목 약간 미달)")
            print(f"        연 YoY {t_detail['latest_annual_yoy']}% · {t_detail['two_quarter_surge_detail']}")
            print(f"        TTM 비율: {t_detail['ttm_high_ratio']*100:.0f}%" if t_detail['ttm_high_ratio'] else "        TTM N/A")
            print(f"        배지: {', '.join(t_detail['badges']) if t_detail['badges'] else '—'}")
        else:
            print(f"     ❌ 턴어라운드 미통과: {' / '.join(t_detail['fail_reasons'][:2])}")

            # 신규 상장 (연간 < 4년)
            if len(annual_eps) < 4:
                n_detail = evaluate_new_listing_detailed(
                    annual_eps=annual_eps,
                    quarterly_eps_yoy_history=eps_yoy_history,
                    sales_yoy_history=sales_yoy_history,
                    induty_code=induty_code,
                    annual_roe=annual_roe,
                    quarterly_eps_for_stability=quarterly_eps_for_stability,
                )
                if n_detail["new_listing_pass"]:
                    print(f"     🆕 신규 상장 트랙 통과 (연 데이터 {n_detail['annual_eps_count']}년)")
                    print(f"        배지: {', '.join(n_detail['badges']) if n_detail['badges'] else '—'}")
                else:
                    print(f"     ❌ 신규 상장 미통과: {' / '.join(n_detail['fail_reasons'][:2])}")

    # ────────────────────────────────────────
    # N/S/L/I 평가 (M 은 시장 전체)
    # ────────────────────────────────────────
    chart = fetch_yahoo_chart(yahoo_symbol(code, market), "1y", "1d")
    if not chart or len(chart["closes"]) < 200:
        print(f"\n  ⚠ Yahoo 차트 데이터 부족 — N/S/L 평가 불가")
        return

    closes = chart["closes"]
    volumes = chart["volumes"]

    # N
    n_pass, n_val, n_detail = evaluate_n(closes)
    print(f"\n  📍 N 원칙 (52주 신고가 근접)")
    print(f"     {'✅' if n_pass else '❌'} {n_val} · {n_detail}")

    # S
    s_pass, s_val, s_detail = evaluate_s(volumes, market_cap)
    print(f"\n  💧 S 원칙 (수급/거래량)")
    print(f"     {'✅' if s_pass else '❌'} {s_val} · {s_detail}")

    # L
    l_pass, l_val, l_detail = evaluate_l(closes, kospi_closes, None)
    print(f"\n  🎯 L 원칙 (상대강도 RS)")
    print(f"     {'✅' if l_pass else '❌'} {l_val} · {l_detail}")

    # I
    inst_data = fetch_majorstock_holding(corp_code) if corp_code else None
    inst_pct = inst_data.get("institutional_pct") if inst_data else None
    inst_trend = inst_data.get("recent_trend") if inst_data else None
    foreign = ig.get("foreign_ownership", 0) or 0
    i_pass, i_val, i_detail = evaluate_i(foreign, inst_pct, inst_trend)
    print(f"\n  🏢 I 원칙 (기관 매집)")
    print(f"     {'✅' if i_pass else '❌'} {i_val} · {i_detail}")

    # ────────────────────────────────────────
    # 매도/보유 판단 (O'Neil 매도 룰 종합)
    # ────────────────────────────────────────
    print(f"\n  🎬 O'Neil 매도/보유 종합 판단")

    # 강한 모멘텀 신호
    strong_signals = []
    if c_detail.get("never_sell"):
        strong_signals.append("매출+EPS 모두 3분기 가속 (절대 매도 금지)")
    if c_detail.get("eps_new_high"):
        strong_signals.append("12개월 EPS 신고점")
    if n_pass:
        strong_signals.append("52주 신고가 근접")
    if l_pass:
        strong_signals.append("RS 우월")
    if i_pass:
        strong_signals.append("기관 매집")

    # 매도 위험 신호
    sell_signals = []
    if (c_detail.get("consecutive_decline_quarters") or 0) >= 2:
        sell_signals.append(f"{c_detail['consecutive_decline_quarters']}분기 연속 EPS 감소 (O'Neil 즉시 매도)")
    if c_detail.get("severe_decel"):
        sell_signals.append("EPS 증가율 2/3 이상 둔화 (사이클 톱 신호)")
    if c_detail.get("dilution_flag"):
        sell_signals.append("증자 희석 이력")
    accel_delta = c_detail.get("accel_delta_pp") or 0
    if accel_delta < 0 and not c_detail.get("severe_decel"):
        sell_signals.append(f"분기 EPS 가속 둔화 (Δ {accel_delta:+.1f}%p)")
    if not n_pass:
        # 가격 베이스 위치
        from_high = (max(closes) - closes[-1]) / max(closes) * 100 if max(closes) > 0 else 0
        if from_high > 25:
            sell_signals.append(f"고점 대비 -{from_high:.1f}% 이탈 (베이스 손상)")

    print(f"     🟢 강세 신호 ({len(strong_signals)}): {' / '.join(strong_signals) if strong_signals else '없음'}")
    print(f"     🔴 매도 신호 ({len(sell_signals)}): {' / '.join(sell_signals) if sell_signals else '없음'}")

    # 최종 판단
    is_cyclical_industry_flag = induty_code and induty_code[:2] in ("24", "20", "17", "22", "29")
    if c_detail.get("never_sell"):
        verdict = "⛔ 절대 매도 금지 (O'Neil 원전 — 매출+EPS 모두 3분기 가속)"
    elif len(sell_signals) >= 2:
        if is_cyclical_industry_flag:
            verdict = "⚠️ 매도 검토 강력 권고 (cyclical + 다중 매도 신호)"
        else:
            verdict = "⚠️ 매도 검토 (다중 매도 신호)"
    elif len(sell_signals) >= 1 and len(strong_signals) <= 1:
        verdict = "🟡 부분 차익실현 검토 (매도 신호 우세)"
    elif len(strong_signals) >= 3 and len(sell_signals) == 0:
        verdict = "🟢 보유 (강한 모멘텀 지속)"
    else:
        verdict = "⚪ 중립 보유 (혼재 신호)"
    print(f"     → {verdict}")


def main():
    corp_map = load_corp_code_map()

    # M 원칙 (시장 추세) — 한 번만 평가
    market, kospi_closes = evaluate_market_state()
    print(f"\n{'='*70}")
    print(f"  📊 M 원칙 (시장 추세 — KOSPI)")
    print(f"{'='*70}")
    if market:
        print(f"  {'✅' if market['passed'] else '❌'} {market['value']}")
        print(f"  {market['detail']}")
    else:
        print(f"  ⚠ KOSPI 데이터 미수집")
        return

    for code, name, mkt in STOCKS:
        evaluate_one(code, name, mkt, corp_map, kospi_closes)
        time.sleep(0.5)


if __name__ == "__main__":
    main()

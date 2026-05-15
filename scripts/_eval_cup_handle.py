"""오닐 컵앤핸들 자동 진단.

사용법:
  python3 _eval_cup_handle.py 005930 KOSPI 삼성전자
  python3 _eval_cup_handle.py 005930,KOSPI,삼성전자 000660,KOSPI,SK하이닉스

6개월 일봉을 가져와 베이스 자동 식별 + 오닐 7체크리스트 평가.
"""

from __future__ import annotations

import io
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from canslim_lib.fetch import fetch_yahoo_chart, yahoo_symbol  # noqa: E402


def fmt_pct(x: float) -> str:
    return f"{x:+.2f}%"


def fmt_price(x: float) -> str:
    return f"{int(x):,}"


def find_local_extrema(closes: list[float], window: int = 5) -> tuple[list[int], list[int]]:
    highs, lows = [], []
    n = len(closes)
    for i in range(window, n - window):
        seg = closes[i - window:i + window + 1]
        if closes[i] == max(seg):
            highs.append(i)
        if closes[i] == min(seg):
            lows.append(i)
    return highs, lows


def grade_check(label: str, ok: bool, detail: str) -> str:
    mark = "✓" if ok else "✗"
    return f"  {mark} {label}: {detail}"


def analyze(code: str, market: str, name: str) -> None:
    sym = yahoo_symbol(code, market)
    print(f"\n{'=' * 70}")
    print(f"  {name} ({code}) | {sym}")
    print('=' * 70)

    chart = fetch_yahoo_chart(sym, range_="6mo", interval="1d")
    if not chart:
        print("데이터 수집 실패")
        return

    closes = chart["closes"]
    vols = chart["volumes"]
    n = len(closes)
    if n < 60:
        print(f"데이터 부족: {n} 거래일")
        return
    dates = [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in chart["timestamps"]]

    cur_idx = n - 1
    cur_price = closes[cur_idx]
    cur_date = dates[cur_idx]

    # 거시 흐름
    hi_idx = max(range(n), key=lambda i: closes[i])
    lo_idx = min(range(n), key=lambda i: closes[i])
    avg_vol_50 = sum(vols[max(0, cur_idx - 49):cur_idx + 1]) / min(50, cur_idx + 1)

    print(f"\n[거시] 현재가 {fmt_price(cur_price)}원 ({cur_date})")
    print(f"  6M 최고: {fmt_price(closes[hi_idx])} ({dates[hi_idx]})")
    print(f"  6M 최저: {fmt_price(closes[lo_idx])} ({dates[lo_idx]})")
    print(f"  6M 상승률: {fmt_pct((closes[hi_idx]/closes[lo_idx]-1)*100)}")
    print(f"  현재가 vs 6M 최고: {fmt_pct((cur_price/closes[hi_idx]-1)*100)}")
    print(f"  50일 평균 거래량: {int(avg_vol_50):,}")

    # local extrema
    highs, lows = find_local_extrema(closes, window=5)
    if not highs or not lows:
        print("\nlocal extrema 부족 → 패턴 분석 불가")
        return

    # 최근 60일 내 가장 최근 local high를 우측 림 후보로
    recent_highs = [i for i in highs if i >= n - 60]
    if not recent_highs:
        print("\n최근 60일 내 local high 없음")
        return
    right_rim_idx = recent_highs[-1]
    right_rim_price = closes[right_rim_idx]

    # 컵 바닥: 우측 림 이전, 깊이 5%+ 인 가장 가까운 low
    prior_lows = [i for i in lows if i < right_rim_idx and (1 - closes[i] / right_rim_price) > 0.05]
    cup_bottom_idx = prior_lows[-1] if prior_lows else None

    # 좌측 림: 컵 바닥 이전 가장 가까운 high
    left_rim_idx = None
    if cup_bottom_idx is not None:
        prior_highs = [i for i in highs if i < cup_bottom_idx]
        if prior_highs:
            left_rim_idx = prior_highs[-1]

    print(f"\n[베이스 후보 자동 식별]")
    print(f"  우측 림: {dates[right_rim_idx]} {fmt_price(right_rim_price)} (idx={right_rim_idx})")
    if cup_bottom_idx is None or left_rim_idx is None:
        print("  컵 바닥/좌측 림 미식별 → 베이스 패턴 명확하지 않음")
        # 그래도 손잡이/현재 위치는 분석
        analyze_handle_only(dates, closes, vols, right_rim_idx, cur_idx, avg_vol_50, cur_price)
        return

    cup_bottom_price = closes[cup_bottom_idx]
    left_rim_price = closes[left_rim_idx]
    cup_depth = (1 - cup_bottom_price / left_rim_price) * 100
    cup_days = right_rim_idx - left_rim_idx
    rim_diff = abs(right_rim_price - left_rim_price) / left_rim_price * 100

    print(f"  컵 바닥: {dates[cup_bottom_idx]} {fmt_price(cup_bottom_price)}")
    print(f"  좌측 림: {dates[left_rim_idx]} {fmt_price(left_rim_price)}")

    print(f"\n[오닐 7체크리스트]")
    print(grade_check("컵 길이 (≥7주=35일)", cup_days >= 35, f"{cup_days} 거래일 (~{cup_days/5:.1f}주)"))
    print(grade_check("컵 깊이 (12~33%)", 12 <= cup_depth <= 33, f"{cup_depth:.1f}%"))
    print(grade_check("좌·우 림 차이 (±5% 내)", rim_diff <= 5, f"{rim_diff:.1f}%"))

    # 손잡이 (우측 림 이후)
    handle_indices = list(range(right_rim_idx + 1, cur_idx + 1))
    if not handle_indices:
        print("  손잡이 미형성 (우측 림 = 마지막날)")
        return

    handle_low_idx = min(handle_indices, key=lambda i: closes[i])
    handle_low = closes[handle_low_idx]
    handle_high_idx = max(handle_indices, key=lambda i: closes[i])
    handle_high = closes[handle_high_idx]
    handle_depth = (1 - handle_low / right_rim_price) * 100
    handle_len = len(handle_indices)
    handle_avg_vol = sum(vols[i] for i in handle_indices) / len(handle_indices)
    handle_vol_ratio = handle_avg_vol / avg_vol_50 * 100 if avg_vol_50 else 0

    print(grade_check("손잡이 깊이 (10~15% 내)", handle_depth <= 15, f"{handle_depth:.1f}%"))
    print(grade_check("손잡이 길이 (5~15일)", 5 <= handle_len <= 15, f"{handle_len} 거래일"))
    print(grade_check("손잡이 거래량 위축 (<80%)", handle_vol_ratio < 80, f"50평 대비 {handle_vol_ratio:.0f}%"))

    # 컵 상단 1/3 안에 손잡이?
    cup_top_third = left_rim_price - (left_rim_price - cup_bottom_price) / 3
    handle_in_top = handle_low >= cup_top_third
    print(grade_check("손잡이가 컵 상단 1/3 안", handle_in_top, f"손잡이 저점 {fmt_price(handle_low)} vs 컵 상단 1/3 {fmt_price(cup_top_third)}"))

    # 피벗 = max(우측 림, 손잡이 고점)
    pivot = max(right_rim_price, handle_high)
    extended_5 = pivot * 1.05
    pivot_pos = (cur_price / pivot - 1) * 100

    # 오늘 거래량
    today_vol_ratio = vols[cur_idx] / avg_vol_50 * 100

    print(f"\n[피벗 & 매수 판단]")
    print(f"  피벗: {fmt_price(pivot)} | +5% 한계: {fmt_price(extended_5)}")
    print(f"  현재가 {fmt_price(cur_price)} → 피벗 대비 {fmt_pct(pivot_pos)}")
    print(f"  오늘 거래량 vs 50평: {today_vol_ratio:.0f}%")

    if cur_price < pivot * 0.97:
        verdict = "피벗 미돌파 — 베이스 형성 중, 돌파 대기"
    elif cur_price <= extended_5:
        if today_vol_ratio > 140:
            verdict = "✓ 피벗 +5% 이내 + 거래량 폭증 — 오닐 매수 신호"
        else:
            verdict = "△ 피벗 +5% 이내지만 거래량 부족 (140%↓) — 약한 돌파"
    else:
        verdict = "✗ 피벗 +5% 초과 — 추격 매수 금지 (extended)"
    print(f"  >>> {verdict}")

    # 종합 점수
    checks = [cup_days >= 35, 12 <= cup_depth <= 33, rim_diff <= 5,
              handle_depth <= 15, 5 <= handle_len <= 15, handle_vol_ratio < 80, handle_in_top]
    score = sum(checks)
    print(f"\n[종합] 7항목 중 {score}개 통과 ({score}/7)")
    if score >= 6:
        print("  → 정통 컵앤핸들에 매우 가까움")
    elif score >= 4:
        print("  → 부분적 컵앤핸들, 약점 있음")
    else:
        print("  → 컵앤핸들이라기 어려움")


def analyze_handle_only(dates, closes, vols, right_rim_idx, cur_idx, avg_vol_50, cur_price):
    handle_indices = list(range(right_rim_idx + 1, cur_idx + 1))
    if not handle_indices:
        return
    right_rim_price = closes[right_rim_idx]
    handle_low_idx = min(handle_indices, key=lambda i: closes[i])
    handle_low = closes[handle_low_idx]
    handle_high = max(closes[i] for i in handle_indices)
    handle_depth = (1 - handle_low / right_rim_price) * 100
    handle_len = len(handle_indices)
    handle_avg_vol = sum(vols[i] for i in handle_indices) / len(handle_indices)
    handle_vol_ratio = handle_avg_vol / avg_vol_50 * 100 if avg_vol_50 else 0
    pivot = max(right_rim_price, handle_high)
    pivot_pos = (cur_price / pivot - 1) * 100
    today_vol_ratio = vols[cur_idx] / avg_vol_50 * 100

    print(f"\n[손잡이 후보 분석]")
    print(f"  손잡이 깊이 {handle_depth:.1f}%, 길이 {handle_len}일, 거래량 50평 {handle_vol_ratio:.0f}%")
    print(f"  피벗 {fmt_price(pivot)}, 현재가 피벗 대비 {fmt_pct(pivot_pos)}")
    print(f"  오늘 거래량 vs 50평: {today_vol_ratio:.0f}%")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and "," not in sys.argv[1]:
        analyze(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 2:
        for arg in sys.argv[1:]:
            parts = arg.split(",")
            if len(parts) == 3:
                analyze(parts[0], parts[1], parts[2])
    else:
        # 기본: 삼성전자/SK하이닉스/삼성전기
        for code, mkt, name in [
            ("005930", "KOSPI", "삼성전자"),
            ("000660", "KOSPI", "SK하이닉스"),
            ("009150", "KOSPI", "삼성전기"),
        ]:
            analyze(code, mkt, name)

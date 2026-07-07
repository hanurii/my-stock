"""자동매수 봇 순수 판정 함수 — 실시간 시세/거래량으로 매수·청산·국면을 판정.
부작용 없음(주문·네트워크 없음) → 합성 입력으로 전수 테스트 가능."""
from __future__ import annotations


def evaluate_entry(price, pivot, acml_vol, avg50_vol, elapsed_frac, *,
                   slots_used, slots_max, held,
                   vol_pace_min=1.5, chase_max_pct=3.0):
    """돌파+거래량pace+추격상한(하드)+슬롯+미보유 전부 충족 시 (True,"buy").
    반환: (매수여부, 사유). 사유: buy|already_held|no_slot|below_pivot|extended|no_baseline|low_volume."""
    if held:
        return (False, "already_held")
    if slots_used >= slots_max:
        return (False, "no_slot")
    if price < pivot:
        return (False, "below_pivot")
    if price > pivot * (1 + chase_max_pct / 100):
        return (False, "extended")            # 추격 금지 — 하드 상한
    if avg50_vol <= 0 or elapsed_frac <= 0:
        return (False, "no_baseline")
    vol_pace = acml_vol / (avg50_vol * elapsed_frac)
    if vol_pace < vol_pace_min:
        return (False, "low_volume")
    return (True, "buy")


def evaluate_exit(price, entry_price, *, target_pct=20.0, stop_pct=10.0):
    """진입가 대비 -stop% 손절 / +target% 목표 선착. 반환 (매도여부, stop|target|hold).
    손절 우선(같은 틱에 둘 다면 손절)."""
    if price <= entry_price * (1 - stop_pct / 100):
        return (True, "stop")
    if price >= entry_price * (1 + target_pct / 100):
        return (True, "target")
    return (False, "hold")


def is_uptrend(closes, ma=20):
    """지수 종가열 최신값이 ma일 이동평균 위면 상승추세(=매매 ON). 데이터 부족 시 False(보수)."""
    if len(closes) < ma:
        return False
    return closes[-1] > sum(closes[-ma:]) / ma

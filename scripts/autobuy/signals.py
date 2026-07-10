"""자동매수 봇 순수 판정 함수 — 실시간 시세/거래량으로 매수·청산·국면을 판정.
부작용 없음(주문·네트워크 없음) → 합성 입력으로 전수 테스트 가능.
기본 문턱값은 canslim_lib.strategy_params(단일 공급원)에서 가져온다(legacy 하드코딩 금지)."""
from __future__ import annotations

from canslim_lib import strategy_params as SP


def evaluate_entry(price, pivot, acml_vol, avg50_vol, vol_frac, *,
                   slots_used, slots_max, held,
                   vol_pace_min=SP.VOL_PACE_MIN, chase_max_pct=SP.CHASE_MAX_PCT,
                   spike_pace=None, spike_min=SP.SPIKE_MIN):
    """돌파+거래량pace+추격상한(하드)+슬롯+미보유 전부 충족 시 (True,"buy").
    반환: (매수여부, 사유). 사유: buy|already_held|no_slot|below_pivot|extended|no_baseline|low_volume.

    vol_frac = '평소 이 시각까지 하루 거래량의 몇 %가 나오는가'(장중 거래량 곡선 C(t), autobuy.vol_curve).
    ★선형 경과시간이 아님 — 거래량이 U자로 몰려(장초반 폭증) 선형은 아침 돌파를 다 부풀리므로,
    '동시간대 대비'로 정규화해야 진짜 강한 거래량을 선별한다. vol_pace = 지금까지 누적 / (50일일평균 × C(t)).

    spike_pace = 단기-창 거래량 페이스(최근 W분 거래량 / (avg50 × [C(t)−C(t−W)]), autobuy.vol_curve.window_vol_frac).
    None이면 누적만 본다(하위호환). 주면 거래량 게이트는 OR: 누적≥vol_pace_min '또는' spike≥spike_min.
    누적이 굼떠 놓치는 '이른 돌파+늦은 거래량' 버스트를 잡기 위함."""
    if held:
        return (False, "already_held")
    if slots_used >= slots_max:
        return (False, "no_slot")
    if price < pivot:
        return (False, "below_pivot")
    if price > pivot * (1 + chase_max_pct / 100):
        return (False, "extended")            # 추격 금지 — 하드 상한
    if avg50_vol <= 0 or vol_frac <= 0:
        return (False, "no_baseline")
    vol_pace = acml_vol / (avg50_vol * vol_frac)
    vol_ok = vol_pace >= vol_pace_min or (spike_pace is not None and spike_pace >= spike_min)
    if not vol_ok:
        return (False, "low_volume")
    return (True, "buy")


def evaluate_exit(price, entry_price, *, target_pct=SP.TARGET_PCT, stop_pct=SP.STOP_PCT):
    """진입가 대비 -stop% 손절 / +target% 익절 선착. 반환 (매도여부, 손절|익절|보유).
    손절 우선(같은 틱에 둘 다면 손절)."""
    if price <= entry_price * (1 - stop_pct / 100):
        return (True, "손절")
    if price >= entry_price * (1 + target_pct / 100):
        return (True, "익절")
    return (False, "보유")


def is_uptrend(closes, ma=20):
    """지수 종가열 최신값이 ma일 이동평균 위면 상승추세(=매매 ON). 데이터 부족 시 False(보수)."""
    if len(closes) < ma:
        return False
    return closes[-1] > sum(closes[-ma:]) / ma

"""초수익 잠재력 점수 + 주도력 요인 — 매수 추천 리스트용.

방법충실 돌파 백테스트(2022-2026, 트렌드템플릿+검출기 피벗돌파 진입, -8%손절/트레일)로 검증.
검증 결과: 점수 4+ = 6개월 내 '더블(+100%)' 도달률 36% vs 0~1점 15% (전체 평균 28%).
점수 요인(최대 6점):
  · 직전 상승폭 (100%+=2, 50~100%=1)  ← 최강 예측자("가장 강한 VCP는 이미 50%+ 오른 뒤")
  · RS 상대강도 (90+=2, 80~89=1)
  · RS선 신고가 (주가÷지수 선이 최근 10일 내 신고가 = +1)
  · RS선 선행 (RS선이 주가보다 먼저 신고가 = 기관 매집 조짐 = +1)
패턴은 진입 시점용이라 점수에서 제외.
"""
from __future__ import annotations


def _days_since_high(arr: list[float]) -> int:
    m = max(arr)
    for i in range(len(arr) - 1, -1, -1):
        if arr[i] == m:
            return len(arr) - 1 - i
    return 0


def compute_factors(dates, closes, highs, index_closes, look: int = 252, window: int = 120) -> dict:
    """as-of 시계열 + 시장지수({date:close})로 주도력 요인 계산.

    Returns: {prior_adv, rs_nh_days, rs_leads, dist_52wh} (계산 불가 항목은 None).
    """
    prior_adv = None
    cm = [c for c in closes[-window:] if c]
    if cm and closes and closes[-1]:
        prior_adv = closes[-1] / min(cm) - 1

    rs_nh_days = px_nh_days = dist_52wh = None
    if index_closes:
        rs, rc, rh = [], [], []
        for i, d in enumerate(dates):
            v = index_closes.get(d)
            if v and closes[i]:
                rs.append(closes[i] / v)
                rc.append(closes[i])
                rh.append(highs[i] or closes[i])
        if len(rs) >= 65:
            lk = min(look, len(rs))
            rs_nh_days = _days_since_high(rs[-lk:])
            px_nh_days = _days_since_high(rc[-lk:])
            dist_52wh = round((rc[-1] / max(rh[-lk:]) - 1) * 100, 1)

    rs_leads = (px_nh_days - rs_nh_days) if (rs_nh_days is not None and px_nh_days is not None) else None
    return {"prior_adv": prior_adv, "rs_nh_days": rs_nh_days, "rs_leads": rs_leads, "dist_52wh": dist_52wh}


def score(rs, prior_adv, rs_nh_days, rs_leads) -> tuple[int, list[str]]:
    """초수익 잠재력 점수(0~6)와 근거 목록."""
    pts = 0
    reasons: list[str] = []
    if prior_adv is not None:
        if prior_adv >= 1.0:
            pts += 2; reasons.append("직전 100%+ 상승")
        elif prior_adv >= 0.5:
            pts += 1; reasons.append("직전 50%+ 상승")
    if rs is not None:
        if rs >= 90:
            pts += 2; reasons.append("RS 90+")
        elif rs >= 80:
            pts += 1; reasons.append("RS 80+")
    if rs_nh_days is not None and rs_nh_days <= 10:
        pts += 1; reasons.append("RS선 신고가")
    if rs_leads is not None and rs_leads > 0:
        pts += 1; reasons.append("RS선 선행")
    return pts, reasons

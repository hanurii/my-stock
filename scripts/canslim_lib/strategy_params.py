"""SEPA 매매 전략 최적값 — 단일 진실 공급원(single source of truth).

시행착오·백테스트로 확정한 정본값. 봇(autobuy)·백테스트·검증 스크립트는 여기서 import해서 쓰고,
값을 바꿀 땐 여기서만 바꾼다. (검출기 VCP/3C/PP 최적값은 여기가 아니라 각 모듈의 DEFAULT_PARAMS가 정본.)
"""
from __future__ import annotations

# ── 손익비 (익절/손절 %) ──────────────────────────────────
# 6년 검증(2020-2026, 상폐포함)으로 확정한 최적. 옛 15.0/7.5(R-분석)는 대체됨.
TARGET_PCT: float = 20.0
STOP_PCT: float = 10.0

# ── 진입 거래량 문턱 (동시간대-대비 페이스, autobuy.vol_curve 정규화) ──
# 1.5 = 사용자 확정(어중간 거래량 승자도 매수). 검증상 ≥3~5가 선별력 최고지만 승자 놓침 방지 우선.
# 옛 signals.evaluate_entry 기본값 3.0을 대체.
VOL_PACE_MIN: float = 1.5

# ── 단기-창 거래량 스파이크 (누적 pace가 굼떠서 놓치는 "이른 돌파+늦은 거래량" 대응) ──
# spike_pace = 최근 W분 거래량 / (avg50 × [C(t)−C(t−W)]). 누적과 OR로 결합(어느 하나 충족이면 거래량OK).
# 시작값(백테스트로 보정 예정). 코스맥스엔비티 7/9서 매수존 순간relvol ~4 관측 → 3 시작.
SPIKE_MIN: float = 3.0
SPIKE_WINDOW_MIN: int = 5

# ── 추격 상한 (피벗 대비 %; 초과 시 매수 금지) ──────────────
# 미너비니 규칙(피벗 코앞에서만 매수, 돌파 후 익스텐디드는 안 쫓음). 변동 없음.
CHASE_MAX_PCT: float = 3.0

# ── 동시 보유 슬롯 수 ─────────────────────────────────────
# 포트폴리오 검증: 4~5 최적(5가 수익 최고·MaxDD 최저). 과분산(10~15) 열위. 옛 10 대체.
SLOTS: int = 5

# ── 국면 규칙 (등가중 breadth 지수 이동평균) ───────────────
# 등가중 breadth 지수 > REGIME_MA일 이평(상승중)이면 매매 ON. 20MA가 최선(50·200MA 열위).
# 사용처: autobuy.signals.is_uptrend(index, ma=REGIME_MA).
REGIME_MA: int = 20

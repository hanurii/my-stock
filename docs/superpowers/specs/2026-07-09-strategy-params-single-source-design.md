# SEPA 매매 전략값 단일 공급원 — 설계

작성: 2026-07-09

## 배경 & 목표

시행착오·백테스트로 확정한 최적 매매값(손익비·거래량문턱·슬롯 등)이 코드 곳곳에 흩어져 있고, 일부는 legacy 값 그대로다. **실제 불일치:** 라이브 봇(`autobuy/config.py`)이 손익비 **15/7.5**·슬롯 **10**을 쓰는데, 우리 최종 검증은 **20/10·슬롯 5**다. signals 기본값 vol_pace_min은 **3.0**인데 config는 **1.5**.

**목표:** 매매 전략 최적값을 **한 곳(단일 공급원)** 에 모으고, 봇·백테스트·검증 코드가 그걸 참조해 legacy 값을 쓰지 않게 한다.

## 확정된 정본값

| 값 | 정본 | 근거 / 대체된 legacy |
|---|---|---|
| TARGET_PCT (익절%) | **20.0** | 6년 검증 최적. 옛 15.0(R-분석) 대체 |
| STOP_PCT (손절%) | **10.0** | 6년 검증 최적. 옛 7.5 대체 |
| VOL_PACE_MIN (거래량 문턱) | **1.5** | 사용자 확정(승자 놓침 방지). 옛 signals 기본값 3.0 대체 |
| CHASE_MAX_PCT (추격 상한%) | **3.0** | 변동 없음(미너비니 규칙) |
| SLOTS (동시 보유) | **5** | 포트폴리오 검증 최적(4~5, 5가 최고). 옛 10 대체 |
| REGIME_MA (국면 이평) | **20** | 등가중 breadth>20MA가 최선(50·200MA 열위) |

## 설계

**신설: `scripts/canslim_lib/strategy_params.py`** — 위 정본값을 상수로, 각 값에 "출처·결정·대체된 legacy" 주석과 함께. 값 변경은 여기서만.

**참조하도록 수정(라이브 경로):**
- `autobuy/config.py` — `CFG`의 TARGET_PCT·STOP_PCT·VOL_PACE_MIN·SLOTS·CHASE_MAX_PCT를 strategy_params에서 가져옴.
- `autobuy/signals.py` — `evaluate_entry`의 `vol_pace_min` 기본값, `evaluate_exit`의 `target_pct`/`stop_pct` 기본값을 strategy_params에서.
- `autobuy/replay.py` — `resolve_forward_daily`의 `target_pct`/`stop_pct` 기본값을 strategy_params에서.

**그대로 두는 것:**
- **검출기(VCP/3C/PP) 파라미터**: 각 `canslim_lib/{vcp,cheat,power_play}.py`의 `DEFAULT_PARAMS`가 이미 단일 공급원(오라클 튜닝 반영). strategy_params에서 "검출기 최적값은 각 DEFAULT_PARAMS가 정본"이라고 포인터만.
- **옛 백테스트 스크립트**(`pivot_backtest*.py` 10/5, `*_history.py` 8/20): 라이브 경로 아님. 이번 범위 밖(주석으로 legacy 명시만, 마이그레이션은 나중에).

## 범위 밖 (다음에)

- **청산 방식(절반매도+본전+트레일-3%)**: 값이 아니라 로직 변경. 라이브 봇은 현재 전량 익절. 이번엔 값 통합만.
- 옛 백테스트/history 스크립트 마이그레이션.

## 테스트

- `strategy_params` import + 값 확인.
- `config.CFG`가 정본값(20/10·1.5·5·3.0)과 일치.
- `signals.evaluate_exit`/`evaluate_entry` 기본값이 정본값과 일치.
- 기존 autobuy 테스트 무회귀.

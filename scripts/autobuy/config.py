"""자동매수 봇 설정. 주문 수량은 여기에 없다(항상 1주, kis_trade에 하드코딩)."""
from pathlib import Path
BASE = Path(r"C:\Users\hanul\playground\my-stock")   # 후보 JSON·캐시가 있는 주 작업트리
CFG = {
    "SLOTS": 10,            # 동시 보유 상한(10~20)
    "VOL_PACE_MIN": 1.5,
    "CHASE_MAX_PCT": 3.0,  # 하드
    "TARGET_PCT": 20.0, "STOP_PCT": 10.0,
    "POLL_SEC": 4,
    "REGIME_FILTER": True,
    "MODE": "dryrun",      # dryrun | live — live 전환은 실행인자로도 재확인
    "MARKET_OPEN": "0905", "NEW_BUY_UNTIL": "1520", "MARKET_CLOSE": "1530",
}
CANDIDATE_PATHS = [str(BASE / "public" / "data" / f"sepa-{p}-candidates.json")
                   for p in ("vcp", "3c", "power-play")]

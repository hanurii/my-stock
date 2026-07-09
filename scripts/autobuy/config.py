"""자동매수 봇 설정. 주문 수량은 여기에 없다(항상 1주, kis_trade에 하드코딩).
매매 전략값(손익비·거래량문턱·슬롯 등)은 canslim_lib.strategy_params(단일 공급원)에서 가져온다 —
legacy 값 직접 하드코딩 금지. 값 변경은 strategy_params에서만."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # scripts/ (canslim_lib import 위해)
from canslim_lib import strategy_params as SP
BASE = Path(r"C:\Users\hanul\playground\my-stock")   # 후보 JSON·캐시가 있는 주 작업트리
CFG = {
    "SLOTS": SP.SLOTS,
    "VOL_PACE_MIN": SP.VOL_PACE_MIN,
    "CHASE_MAX_PCT": SP.CHASE_MAX_PCT,
    "TARGET_PCT": SP.TARGET_PCT, "STOP_PCT": SP.STOP_PCT,
    "POLL_SEC": 4,
    "REGIME_FILTER": True,
    "MODE": "dryrun",      # dryrun | live — live 전환은 실행인자로도 재확인
    "MARKET_OPEN": "0905", "NEW_BUY_UNTIL": "1520", "MARKET_CLOSE": "1530",
}
CANDIDATE_PATHS = [str(BASE / "public" / "data" / f"sepa-{p}-candidates.json")
                   for p in ("vcp", "3c", "power-play")]

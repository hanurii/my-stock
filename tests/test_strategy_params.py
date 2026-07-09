import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib import strategy_params as SP


def test_canonical_values():
    assert SP.TARGET_PCT == 20.0
    assert SP.STOP_PCT == 10.0
    assert SP.VOL_PACE_MIN == 1.5
    assert SP.CHASE_MAX_PCT == 3.0
    assert SP.SLOTS == 5
    assert SP.REGIME_MA == 20


def test_config_uses_strategy_params():
    # 봇 config가 단일 공급원을 그대로 참조하는지(legacy 값 아님)
    from autobuy.config import CFG
    assert CFG["TARGET_PCT"] == SP.TARGET_PCT
    assert CFG["STOP_PCT"] == SP.STOP_PCT
    assert CFG["VOL_PACE_MIN"] == SP.VOL_PACE_MIN
    assert CFG["CHASE_MAX_PCT"] == SP.CHASE_MAX_PCT
    assert CFG["SLOTS"] == SP.SLOTS


def test_signals_defaults_match():
    # signals 기본 인자도 단일 공급원과 일치(옛 3.0 기본값 잔존 방지)
    import inspect
    from autobuy import signals
    entry_def = inspect.signature(signals.evaluate_entry).parameters["vol_pace_min"].default
    exit_t = inspect.signature(signals.evaluate_exit).parameters["target_pct"].default
    exit_s = inspect.signature(signals.evaluate_exit).parameters["stop_pct"].default
    assert entry_def == SP.VOL_PACE_MIN
    assert exit_t == SP.TARGET_PCT and exit_s == SP.STOP_PCT

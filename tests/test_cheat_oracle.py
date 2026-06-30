import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.cheat import evaluate_cheat

FIX = Path(__file__).resolve().parent / "fixtures" / "oracle"


def load_asof(ticker: str, date: str) -> dict:
    """fixture에서 date(포함) 이하로 슬라이스한 series dict."""
    rows = json.loads((FIX / f"{ticker}.json").read_text(encoding="utf-8"))["rows"]
    rows = [r for r in rows if r["date"] <= date]
    return {"dates": [r["date"] for r in rows],
            "closes": [r["close"] for r in rows],
            "highs": [r["high"] for r in rows],
            "lows": [r["low"] for r in rows],
            "volumes": [r["volume"] for r in rows]}


# ── NU 2023-10-18: 완성/상단 치트(위치 84%, 선반 2일) — v2b에서 성립 ──
def test_oracle_nu_actionable_at_cheat():
    r = evaluate_cheat(load_asof("NU", "2023-10-18"))
    assert r["pattern_detected"] is True
    assert r["status"] == "actionable"
    assert 7.8 <= r["pivot_price"] <= 8.2     # 문서 cheat range top ~$8.03


def test_oracle_nu_breakout_next_day():
    r = evaluate_cheat(load_asof("NU", "2023-10-19"))
    assert r["status"] == "breakout"


# ── GOOG 2004-12-23: low/middle 치트 — v2a부터 성립(회귀 없음) ──
def test_oracle_goog_pattern():
    r = evaluate_cheat(load_asof("GOOG", "2004-12-23"))
    assert r["pattern_detected"] is True
    assert r["shelf_position_pct"] <= 66.0


# ── CRUS 2010-02-25: 치트를 정확히 '위치'(pattern은 borderline, 단언 안 함) ──
def test_oracle_crus_locates_cheat():
    r = evaluate_cheat(load_asof("CRUS", "2010-02-25"))
    assert r["left_rim_date"] == "2010-01-12"
    assert r["cup_low_date"] == "2010-02-05"
    assert 20 <= r["cup_depth_pct"] <= 27
    assert 7.2 <= r["pivot_price"] <= 7.6
    assert r["status"] in ("actionable", "forming", "breakout")


# ── v2c 확장 오라클 ──────────────────────────────────────────────
def test_oracle_jblu_pattern():
    r = evaluate_cheat(load_asof("JBLU", "2014-11-03"))
    assert r["pattern_detected"] is True
    assert 11.0 <= r["pivot_price"] <= 12.5
    assert 25 <= r["shelf_position_pct"] <= 90


def test_oracle_aapl_pattern():
    r = evaluate_cheat(load_asof("AAPL", "2004-08-12"))
    assert r["pattern_detected"] is True
    assert 80 <= r["shelf_position_pct"] <= 92


def test_oracle_vm_pattern():   # 브이엠 089970
    r = evaluate_cheat(load_asof("089970", "2021-03-19"))
    assert r["pattern_detected"] is True
    assert 20000 <= r["pivot_price"] <= 21500
    assert 40 <= r["shelf_position_pct"] <= 55


def test_oracle_doosan_pattern():   # 두산 000150
    r = evaluate_cheat(load_asof("000150", "2021-07-02"))
    assert r["pattern_detected"] is True
    assert 90000 <= r["pivot_price"] <= 105000


def test_oracle_jinyang_known_miss():   # 진양폴리 010640 — 의도적 미검출(느슨 선반)
    r = evaluate_cheat(load_asof("010640", "2021-12-08"))
    assert r["pattern_detected"] is False
    assert r["reason"] == "shelf_too_loose"

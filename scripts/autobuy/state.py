"""봇 상태(보유 포지션)·킬스위치·로그. 파일 기반."""
from __future__ import annotations
import json, datetime, os
from pathlib import Path
_DIR = Path(__file__).resolve().parent / "_run"
_DIR.mkdir(exist_ok=True)
STATE_PATH = _DIR / "positions.json"
KILL_PATH = _DIR / "KILL"
LOG_PATH = _DIR / "autobuy.log"

def load() -> list[dict]:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def save(positions: list[dict]) -> None:
    """원자적 저장 — 임시파일에 쓴 뒤 os.replace. 쓰다 중단돼도 positions.json 은 항상 이전 값 아니면 새 값, 반쪽 파일이 되지 않는다."""
    tmp = STATE_PATH.with_suffix(STATE_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(positions, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATE_PATH)

def kill_switch_on() -> bool:
    return KILL_PATH.exists()

def log(event: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"{ts} {event}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _today_str() -> str:
    return datetime.datetime.now().strftime("%Y%m%d")

def _traded_path(date_str: str | None = None) -> Path:
    return _DIR / f"traded_{date_str or _today_str()}.json"

def load_traded_today(date_str: str | None = None) -> set[str]:
    """오늘(또는 지정 날짜) 이미 매수한 종목코드 집합. 재시작해도 남아있음(중복 재매수 방지)."""
    p = _traded_path(date_str)
    try:
        return set(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        return set()

def add_traded_today(code: str, date_str: str | None = None) -> None:
    p = _traded_path(date_str)
    traded = load_traded_today(date_str)
    traded.add(code)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(sorted(traded), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)

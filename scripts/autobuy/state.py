"""봇 상태(보유 포지션)·킬스위치·로그. 파일 기반."""
from __future__ import annotations
import json, datetime
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
    STATE_PATH.write_text(json.dumps(positions, ensure_ascii=False), encoding="utf-8")

def kill_switch_on() -> bool:
    return KILL_PATH.exists()

def log(event: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"{ts} {event}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / ".cache" / "canslim_stocks"


def _path(code: str) -> Path:
    return CACHE_DIR / f"{code}.json"


def get(code: str, max_age_hours: float = 24.0) -> dict | None:
    p = _path(code)
    if not p.exists():
        return None
    if max_age_hours > 0:
        age_sec = time.time() - p.stat().st_mtime
        if age_sec > max_age_hours * 3600:
            return None
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def put(code: str, data: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with _path(code).open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
    except Exception:
        pass


def clear() -> int:
    if not CACHE_DIR.exists():
        return 0
    n = 0
    for p in CACHE_DIR.glob("*.json"):
        try:
            p.unlink()
            n += 1
        except Exception:
            pass
    return n

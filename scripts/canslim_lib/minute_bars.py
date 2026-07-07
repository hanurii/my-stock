# scripts/canslim_lib/minute_bars.py
"""KIS 과거 1분봉(FHKST03010230, 주식일별분봉조회) 수집 + 로컬 캐시.
검증된 페이징 로직(scripts/_fetch_min_all.py)을 과거 TR로 정리·모듈화.
캐시·인증은 주 작업트리(my-stock) 절대경로 기준(정션 금지)."""
from __future__ import annotations

import json
import os
import time
import urllib.parse as up
import urllib.request as ur
from pathlib import Path

from canslim_lib import kis_api

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
CACHE_DIR = MAIN / ".cache" / "min_daily"
BASE = "https://openapi.koreainvestment.com:9443"


def _headers() -> dict:
    return {
        "content-type": "application/json",
        "authorization": f"Bearer {kis_api.get_access_token()}",
        "appkey": os.environ["KIS_APP_KEY"],
        "appsecret": os.environ["KIS_APP_SECRET"],
        "custtype": "P",
        "tr_id": "FHKST03010230",
    }


def _call(code: str, date: str, end: str, headers: dict) -> list[dict]:
    qs = up.urlencode({
        "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code,
        "FID_INPUT_DATE_1": date, "FID_INPUT_HOUR_1": end,
        "FID_PW_DATA_INCU_YN": "Y", "FID_FAKE_TICK_INCU_YN": "N",
    })
    url = f"{BASE}/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice?{qs}"
    for _ in range(4):
        try:
            with ur.urlopen(ur.Request(url, headers=headers), timeout=10) as r:
                d = json.loads(r.read().decode("utf-8"))
            if d.get("rt_cd") == "0":
                return d.get("output2") or []
            if d.get("msg_cd") == "EGW00201":   # 초당 호출 초과
                time.sleep(0.6); continue
            return []
        except Exception:
            time.sleep(0.4)
    return []


def _dec_min(h: str) -> str | None:
    s = int(h[:2]) * 3600 + int(h[2:4]) * 60 + int(h[4:6]) - 60
    return None if s < 0 else f"{s // 3600:02d}{(s % 3600) // 60:02d}{s % 60:02d}"


def fetch_day_minutes(code: str, date: str, force: bool = False) -> list[dict]:
    """date='YYYY-MM-DD' 또는 'YYYYMMDD'. 해당일 1분봉(오름차순). 실패 시 []."""
    ymd = date.replace("-", "")
    cache = CACHE_DIR / f"{code}_{ymd}.json"
    if cache.exists() and not force:
        return json.loads(cache.read_text(encoding="utf-8"))

    headers = _headers()
    bars: dict[str, dict] = {}
    end = "153000"
    for _ in range(8):
        rows = _call(code, ymd, end, headers)
        time.sleep(0.12)
        if not rows:
            break
        for r in rows:
            t = r.get("stck_cntg_hour")
            if not t:
                continue
            bars[t] = {"t": t, "o": float(r["stck_oprc"]), "h": float(r["stck_hgpr"]),
                       "l": float(r["stck_lwpr"]), "c": float(r["stck_prpr"]),
                       "v": float(r["cntg_vol"])}
        earliest = min(bars)
        if earliest <= "090000":
            break
        nxt = _dec_min(earliest)
        if not nxt or nxt >= end:
            break
        end = nxt

    out = [bars[t] for t in sorted(bars)]
    if out:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out

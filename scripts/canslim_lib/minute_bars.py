# scripts/canslim_lib/minute_bars.py
"""KIS 분봉 수집 — 당일/과거 TR 자동 분기 + 로컬 캐시(과거일만) + 신뢰성 검증.

★당일(오늘)과 과거일은 반드시 다른 TR을 써야 한다:
  - 과거일: FHKST03010230(주식일별분봉조회). 확정된 값.
  - 당일  : FHKST03010200(당일 분봉). ← 당일 데이터를 과거일용 TR로 받으면 provisional/미확정
            값이 섞여 종가·거래량이 틀리게 나온다(실측: 코스맥스엔비티 종가 7160 vs 실제 7930).
당일 데이터는 장중 계속 갱신되므로 캐시하지 않는다(항상 새로). 과거일만 캐시.
validate_minutes()로 공식 종가·거래량과 대조해 신뢰성을 검증할 수 있다(오염 자동 감지).
캐시·인증은 주 작업트리(my-stock) 절대경로 기준(정션 금지)."""
from __future__ import annotations

import datetime
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

_PAST_TR, _PAST_EP = "FHKST03010230", "inquire-time-dailychartprice"    # 과거일
_TODAY_TR, _TODAY_EP = "FHKST03010200", "inquire-time-itemchartprice"   # 당일


def _headers(tr: str) -> dict:
    return {
        "content-type": "application/json",
        "authorization": f"Bearer {kis_api.get_access_token()}",
        "appkey": os.environ["KIS_APP_KEY"],
        "appsecret": os.environ["KIS_APP_SECRET"],
        "custtype": "P",
        "tr_id": tr,
    }


def _call(endpoint: str, params: dict, headers: dict) -> list[dict]:
    url = f"{BASE}/uapi/domestic-stock/v1/quotations/{endpoint}?{up.urlencode(params)}"
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


def _page(tr: str, endpoint: str, base_params: dict) -> list[dict]:
    """FID_INPUT_HOUR_1을 역방향 페이징(09:00까지)해 하루 1분봉을 모은다. TR·EP·기타파라미터는 인자."""
    headers = _headers(tr)
    bars: dict[str, dict] = {}
    end = "153000"
    for _ in range(20):   # 당일 TR은 30봉/콜(~14페이지), 과거 TR은 120봉/콜(~4페이지) — 09:00 도달 시 break
        rows = _call(endpoint, {**base_params, "FID_INPUT_HOUR_1": end}, headers)
        time.sleep(0.12)
        if not rows:
            break
        for r in rows:
            try:
                t = r.get("stck_cntg_hour")
                if not t:
                    continue
                bars[t] = {"t": t, "o": float(r["stck_oprc"]), "h": float(r["stck_hgpr"]),
                           "l": float(r["stck_lwpr"]), "c": float(r["stck_prpr"]),
                           "v": float(r["cntg_vol"])}
            except (KeyError, ValueError, TypeError):
                continue
        if not bars:
            break
        earliest = min(bars)
        if earliest <= "090000":
            break
        nxt = _dec_min(earliest)
        if not nxt or nxt >= end:
            break
        end = nxt
    return [bars[t] for t in sorted(bars)]


def fetch_day_minutes(code: str, date: str, force: bool = False) -> list[dict]:
    """date='YYYY-MM-DD' 또는 'YYYYMMDD'. 해당일 1분봉(오름차순, 마지막=15:30). 실패 시 [].
    ★당일이면 당일용 TR(FHKST03010200)로 받고 캐시하지 않는다(장중 갱신·미확정 회피).
    과거일이면 과거용 TR(FHKST03010230) + 캐시."""
    ymd = date.replace("-", "")
    if ymd == datetime.datetime.now().strftime("%Y%m%d"):   # 당일 — 당일 TR, 캐시 안 함
        return _page(_TODAY_TR, _TODAY_EP, {
            "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code,
            "FID_ETC_CLS_CODE": "", "FID_PW_DATA_INCU_YN": "N"})

    cache = CACHE_DIR / f"{code}_{ymd}.json"
    if cache.exists() and not force:
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass  # 손상 캐시 → 재수집
    out = _page(_PAST_TR, _PAST_EP, {
        "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code,
        "FID_INPUT_DATE_1": ymd, "FID_PW_DATA_INCU_YN": "Y", "FID_FAKE_TICK_INCU_YN": "N"})
    if out:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def validate_minutes(minutes: list[dict], ref_close: float, ref_volume: float,
                     close_tol_pct: float = 1.5, cov_lo: float = 90.0, cov_hi: float = 115.0):
    """분봉을 공식값과 대조해 신뢰성 판정. ref_close/ref_volume은 공식 종가·종일거래량
    (당일=실시간시세 fetch_quote_with_volume, 과거=pdata/일봉캐시).
    반환 (ok, close_err_pct, coverage_pct). 종가 오차 ≤tol% AND 거래량 완전성 cov_lo~cov_hi% 면 ok."""
    if not minutes or not ref_close or not ref_volume:
        return (False, None, None)
    mc = minutes[-1]["c"]
    mv = sum(b.get("v", 0) for b in minutes)
    close_err = abs(mc - ref_close) / ref_close * 100
    cov = mv / ref_volume * 100
    return (close_err <= close_tol_pct and cov_lo <= cov <= cov_hi, close_err, cov)

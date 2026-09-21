"""NXT 프리마켓 거래량 분모 만들기 — 「같은 시각까지의 누적」을 종목·날짜별로 쌓는다.

왜 필요한가:
  장중 거래량 배수는 정규장 일봉 평균을 분모로 쓴다(pivot_alert.avg_recent_volume).
  프리마켓에 그 분모를 쓰면 늘 0.0X 배로 나와 뜻이 없다 — 프리마켓 거래량이
  정규장 하루의 1~10% 수준이기 때문이다(26-09-21 실측).
  그래서 프리마켓은 «같은 시간대의 프리마켓 거래량»과 견줘야 한다.

무엇을 쌓나:
  NXT(넥스트레이드) 프리마켓 08:00~08:50 의 «분 단위 누적» 거래량.
  같은 시각끼리 견주려면 「08:36 까지 얼마나 나왔나」를 날짜별로 알아야 한다.
  자료 출처: KIS inquire-time-dailychartprice (TR FHKST03010230),
  FID_COND_MRKT_DIV_CODE=NX. 2026-04 까지 거슬러 받아진다(26-09-21 확인,
  2025-04 는 자료 없음).

산출: .cache/premarket/premarket-vol-history.json
  (로컬 도구 전용 캐시라 커밋하지 않는다 — 날마다 늘고 웹 페이지는 안 읽는다)
  {"asof": "...", "window_days": N,
   "codes": {"005930": {"20260918": {"0830": 1234, ...}, ...}}}

실행: python -X utf8 scripts/build_premarket_vol.py [--days 20] [--codes 005930,000660]
  종목을 안 주면 pivot_alert 의 현재 감시 목록을 쓴다.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import urllib.parse as _up
import urllib.request as _ur
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pivot_alert  # noqa: E402  (.env 로드도 겸한다)
from canslim_lib import kis_api  # noqa: E402

OUT = ROOT / ".cache" / "premarket" / "premarket-vol-history.json"
PRE_START = "080000"
PRE_END = "085959"
_EP = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
_TR = "FHKST03010230"


def fetch_premarket_minutes(code: str, ymd: str, token: str) -> dict[str, float] | None:
    """그 날 NXT 프리마켓의 «분 단위 누적» 거래량 {HHMM: 누적}. 못 받으면 None.

    🚨 휴일을 요청하면 KIS 가 «조용히 직전 거래일»을 돌려준다(26-09-21 실측:
    일요일 20260920 을 물었더니 20260918 자료가 왔다). 요청 날짜를 믿고 저장하면
    같은 날이 여러 날짜로 복제돼 분모가 그 날에 쏠린다. 그래서 응답 «안»의
    stck_bsop_date 를 보고 요청과 다르면 버린다.
    """
    qs = _up.urlencode({
        "FID_COND_MRKT_DIV_CODE": "NX", "FID_INPUT_ISCD": code,
        "FID_INPUT_DATE_1": ymd, "FID_INPUT_HOUR_1": "090000",
        "FID_PW_DATA_INCU_YN": "Y", "FID_FAKE_TICK_INCU_YN": "N",
    })
    headers = {
        "content-type": "application/json", "authorization": f"Bearer {token}",
        "appkey": os.environ.get("KIS_APP_KEY", ""),
        "appsecret": os.environ.get("KIS_APP_SECRET", ""),
        "tr_id": _TR, "custtype": "P",
    }
    kis_api._throttle()
    try:
        req = _ur.Request(kis_api._base_url() + _EP + "?" + qs, headers=headers)
        with _ur.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read().decode("utf-8")).get("output2") or []
    except Exception:
        return None
    bars = sorted((r.get("stck_cntg_hour") or "", float(r.get("cntg_vol") or 0))
                  for r in rows
                  if PRE_START <= (r.get("stck_cntg_hour") or "") <= PRE_END
                  and (r.get("stck_bsop_date") or "") == ymd)   # 날짜가 다르면 버린다
    if not bars:
        return {}
    cum, out = 0.0, {}
    for hhmmss, v in bars:
        cum += v
        out[hhmmss[:4]] = cum
    return out


def trading_days_back(n: int) -> list[str]:
    """오늘 «이전» 달력일을 넉넉히 뽑는다 — 휴일은 자료가 비어 스스로 걸러진다."""
    today = datetime.now(pivot_alert.KST).date()
    return [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(1, int(n * 1.7) + 6)]


def main() -> None:
    ap = argparse.ArgumentParser(description="NXT 프리마켓 거래량 분모 쌓기")
    ap.add_argument("--days", type=int, default=20, help="모을 거래일 수 (기본 20)")
    ap.add_argument("--codes", default="", help="쉼표로 구분. 없으면 현재 감시 목록")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    codes = ([c.strip() for c in a.codes.split(",") if c.strip()]
             or [r["code"] for r in pivot_alert.load_watch_universe()])
    token = kis_api.get_access_token()
    if not token:
        print("KIS 토큰 발급 실패 — .env 확인"); return

    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8")).get("codes") or {}
        except (OSError, json.JSONDecodeError):
            prev = {}

    days = trading_days_back(a.days)
    print(f"종목 {len(codes)} · 날짜 후보 {len(days)} (거래일 {a.days}개 목표)")

    def one(code: str) -> tuple[str, dict]:
        got = dict(prev.get(code) or {})
        n_new = 0
        for ymd in days:
            if ymd in got:                      # 이미 있으면 다시 안 받는다
                continue
            # 거래가 «있던» 날만 센다 — 휴일({})을 세면 분모가 목표보다 얇아진다
            if sum(1 for d, v in got.items() if v and d in days) >= a.days:
                break
            m = fetch_premarket_minutes(code, ymd, token)
            if m is None:
                continue
            got[ymd] = m                        # 빈 dict 도 기록한다 — 「휴일/무거래」와 「미조회」를 가른다
            n_new += 1
        return code, got

    out: dict[str, dict] = {}
    done = 0
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for code, got in ex.map(one, codes):
            out[code] = got
            done += 1
            if done % 10 == 0:
                print(f"   진행 {done}/{len(codes)}")

    filled = sum(1 for c in out for d in out[c] if out[c][d])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"asof": f"{datetime.now(pivot_alert.KST):%Y-%m-%d %H:%M}",
         "window_days": a.days, "source": "KIS inquire-time-dailychartprice NX",
         "codes": out}, ensure_ascii=False), encoding="utf-8")
    print(f"저장 {OUT}")
    print(f"   종목 {len(out)} · 거래 있던 (종목,날짜) 칸 {filled}")


if __name__ == "__main__":
    main()

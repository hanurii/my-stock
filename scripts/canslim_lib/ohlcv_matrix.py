"""날짜별 배치 OHLCV 행렬 — 종목별 Naver 일봉 루프 대체.

배경:
  기존 screen_canslim / screen_trend_template 은 종목마다 api.stock.naver.com 일봉을
  1회씩 호출(2,500종목 = 2,500회). 단일 호스트라 병렬 워커를 늘리면 차단 위험.

해결:
  공공데이터포털(pdata.py) 은 basDt(영업일) 1회 호출로 전 종목 OHLCV 를 준다.
  → 가격 fetch 차원을 "2,500종목 × 매일" → "영업일 1회 × 매일(증분)" 로 붕괴.
  최초 1회만 ~400 영업일 백필(각 1 pdata 호출, 영구 캐시), 이후 매일 최신 1일만 추가.

저장:
  pdata 일자 캐시(.cache/pdata/price_YYYYMMDD.json) 를 1차 소스로,
  종목별 시계열로 피벗해 .cache/ohlcv/series/<code>.json 에 저장(워커가 1파일씩 읽음).

외국인지분율:
  pdata 응답엔 외인 필드가 없음. KIS inquire-price(hts_frgn_ehrt) 로 보강.
  현재값 1개만 필요(시계열 불필요)하고 느리게 변하므로 TTL 캐시(.cache/ohlcv/foreign.json).
  (pykrx by-date 는 현재 KRX 엔드포인트와 불호환이라 사용 안 함.)
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# standalone 실행(python scripts/canslim_lib/ohlcv_matrix.py) 시 scripts/ 를 path 에 추가.
# (모듈 import 시엔 이미 entrypoint 가 scripts/ 를 path 에 올려둠 — 무해)
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from canslim_lib import pdata

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / ".cache" / "ohlcv"
SERIES_DIR = CACHE_DIR / "series"
FOREIGN_PATH = CACHE_DIR / "foreign.json"

# 백필 영업일 수 기본값. screen_canslim 은 days_back=400(달력)≈270 영업일,
# trend_template 은 더 길게 봄(200+ MA·52주). 안전하게 영업일 400(≈19개월) 보유.
DEFAULT_TRADING_DAYS = 400
_KST = timezone(timedelta(hours=9))

# 모듈 레벨 캐시 (워커 1프로세스 내 동일 코드 재조회 대비)
_series_mem: dict[str, dict | None] = {}
_foreign_mem: dict[str, list] | None = None


# ── 영업일 목록 + 일자 캐시 확보 ─────────────────────────────

def _trading_days(window: int) -> list[str]:
    """최신 영업일부터 거꾸로, 데이터가 있는 basDt 를 window 개 모아 오름차순 반환.

    pdata.fetch_pdata_price_info 는 일자별 영구 캐시라 두 번째 호출부터 무료.
    휴일/주말은 빈 응답({}) → 건너뜀.
    """
    latest = pdata._latest_available_basDt()
    if not latest:
        return []
    days: list[str] = []
    cur = datetime.strptime(latest, "%Y%m%d")
    # window 영업일을 채우되, 과도한 역추적 방지 (영업일 1개당 달력 ~1.5일 + 여유)
    max_back = int(window * 1.6) + 40
    for _ in range(max_back):
        bd = cur.strftime("%Y%m%d")
        rows = pdata.fetch_pdata_price_info(bd)
        if rows:
            days.append(bd)
            if len(days) >= window:
                break
        cur -= timedelta(days=1)
    days.sort()
    return days


def _apply_adjustment(s: dict) -> None:
    """수정주가 복원 — pdata clpr 은 비수정주가라 액면분할·감자·증자 권리락에서
    과거 가격이 불연속. 일별 등락률(fltRt)을 최신 종가에서 역방향 체이닝하면
    수정주가 시계열을 복원할 수 있음(거래소 등락률은 수정 기준 변화율).

    closes 를 수정주가로 치환하고, opens/highs/lows 는 같은 일별 배수로 스케일.
    volumes 는 그대로(상대 거래량 비교라 무영향). _flt 누락일은 비수정 비율로 폴백.
    """
    closes = s["closes"]
    flt = s["_flt"]
    n = len(closes)
    if n < 2:
        return
    adj = [0.0] * n
    adj[-1] = closes[-1]
    for i in range(n - 2, -1, -1):
        f = flt[i + 1]
        if f is not None:
            ratio = 1.0 + float(f) / 100.0
        elif closes[i]:
            ratio = closes[i + 1] / closes[i]  # 등락률 누락 → 비수정 비율(권리락 아님 가정)
        else:
            ratio = 1.0
        adj[i] = adj[i + 1] / ratio if ratio else adj[i + 1]
    for i in range(n):
        raw = closes[i]
        fac = adj[i] / raw if raw else 1.0
        s["opens"][i] = round(s["opens"][i] * fac, 2)
        s["highs"][i] = round(s["highs"][i] * fac, 2)
        s["lows"][i] = round(s["lows"][i] * fac, 2)
        closes[i] = round(adj[i], 2)


# ── 업데이트 (단일 프로세스, 워커 실행 전 1회) ──────────────

def update_to_latest(window: int = DEFAULT_TRADING_DAYS, verbose: bool = True) -> dict:
    """pdata 일자 캐시를 최신까지 채우고 종목별 시계열 파일을 (재)생성.

    네트워크 호출은 미캐시 영업일(보통 신규 1일)만 발생. 나머지는 캐시 hit.
    """
    t0 = time.time()
    SERIES_DIR.mkdir(parents=True, exist_ok=True)

    day_list = _trading_days(window)
    if not day_list:
        if verbose:
            print("⚠️  ohlcv_matrix: pdata 영업일 확보 실패 (DATA_GO_KR_KEY 확인)")
        return {"days": 0, "codes": 0, "sec": 0.0}

    if verbose:
        print(f"📦 ohlcv_matrix: {len(day_list)} 영업일 ({day_list[0]}~{day_list[-1]}) 피벗 중...")

    # 종목별 시계열 누적: code → {dates, closes, opens, highs, lows, volumes, timestamps}
    series: dict[str, dict] = {}
    for bd in day_list:
        rows = pdata.fetch_pdata_price_info(bd)  # 캐시 hit
        iso = f"{bd[:4]}-{bd[4:6]}-{bd[6:8]}"
        try:
            ts = int(datetime.strptime(bd + " 16:00", "%Y%m%d %H:%M")
                     .replace(tzinfo=_KST).timestamp())
        except ValueError:
            ts = 0
        for code, row in rows.items():
            cp = row.get("clpr")
            if cp is None:
                continue
            s = series.get(code)
            if s is None:
                s = series[code] = {"dates": [], "timestamps": [], "closes": [],
                                    "opens": [], "highs": [], "lows": [], "volumes": [],
                                    "_flt": []}
            s["dates"].append(iso)
            s["timestamps"].append(ts)
            s["closes"].append(float(cp))
            s["opens"].append(float(row.get("mkp") or cp))
            s["highs"].append(float(row.get("hipr") or cp))
            s["lows"].append(float(row.get("lopr") or cp))
            try:
                s["volumes"].append(int(row.get("trqu") or 0))
            except (ValueError, TypeError):
                s["volumes"].append(0)
            s["_flt"].append(row.get("fltRt"))

    # 종목별로 수정주가 복원 후 파일 기록 (워커가 1파일씩 읽음)
    written = 0
    for code, s in series.items():
        _apply_adjustment(s)
        s.pop("_flt", None)
        (SERIES_DIR / f"{code}.json").write_text(
            json.dumps(s, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        written += 1

    sec = time.time() - t0
    if verbose:
        print(f"✅ ohlcv_matrix: {written}종목 시계열 저장 ({sec:.1f}초)")
    return {"days": len(day_list), "codes": written, "sec": round(sec, 1)}


# ── 조회 (워커에서 종목별) ───────────────────────────────────

def get_series(code: str, days_back: int | None = None) -> dict | None:
    """종목 시계열 반환. fetch_naver_day_chart(code, days_back) 와 동일 키·의미.

    {timestamps, dates, closes, opens, highs, lows, volumes, foreign_rates}
    days_back: 오늘 기준 그만큼의 달력일 이후만 슬라이스 (Naver days_back 의미 재현 —
      특히 closes[0] 위치가 12M 수익률 계산에 영향). None 이면 전체.
    foreign_rates 는 [현재 외인소진율] 1원소 리스트 (없으면 []).
    데이터 없으면 None.
    """
    from bisect import bisect_left
    if code in _series_mem:
        s = _series_mem[code]
    else:
        p = SERIES_DIR / f"{code}.json"
        s = None
        if p.exists():
            try:
                s = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                s = None
        _series_mem[code] = s
    if not s or not s.get("closes"):
        return None

    i0 = 0
    if days_back is not None:
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        i0 = bisect_left(s["dates"], cutoff)  # ISO 날짜 오름차순 → 사전식 bisect

    out = {k: (v[i0:] if i0 else list(v)) for k, v in s.items()}
    if not out.get("closes"):
        return None
    fr = get_foreign(code)
    out["foreign_rates"] = [fr] if fr is not None else []
    return out


# ── 외국인지분율 (KIS, TTL 캐시) ─────────────────────────────

def _load_foreign() -> dict[str, list]:
    global _foreign_mem
    if _foreign_mem is not None:
        return _foreign_mem
    if FOREIGN_PATH.exists():
        try:
            _foreign_mem = json.loads(FOREIGN_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            _foreign_mem = {}
    else:
        _foreign_mem = {}
    return _foreign_mem


def get_foreign(code: str) -> float | None:
    """캐시된 외인소진율(%). 없으면 None."""
    entry = _load_foreign().get(code)
    if isinstance(entry, list) and entry and entry[0] is not None:
        try:
            return float(entry[0])
        except (ValueError, TypeError):
            return None
    return None


def _save_foreign(cache: dict) -> None:
    FOREIGN_PATH.parent.mkdir(parents=True, exist_ok=True)
    FOREIGN_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def refresh_foreign(codes: list[str], ttl_days: float = 7.0,
                    max_refresh: int | None = None, verbose: bool = True) -> dict:
    """미보유/만료(ttl_days 초과) 종목만 KIS inquire-price 로 외인소진율 갱신.

    단일 프로세스에서 워커 실행 전 호출 (KIS rate limit 은 app-key 단위라
    멀티프로세스 동시 호출 시 초과 위험 → 직렬 1프로세스).
    - max_refresh: 1회 갱신 상한 (가장 오래된 것부터). 콜드 캐시의 전수 스윕(~6분)을
      여러 날에 분산하고 싶을 때 사용. None=제한 없음.
    - 200건마다 체크포인트 저장 → 중단되어도 진척 보존(다음 실행이 이어받음).
    """
    from canslim_lib import kis_api
    global _foreign_mem
    if not kis_api._have_keys():
        if verbose:
            print("⏭️  refresh_foreign: KIS 키 없음 → 외인 갱신 skip (기존 캐시 사용)")
        return {"updated": 0, "skipped": len(codes), "reason": "no_kis"}

    cache = _load_foreign()
    now = time.time()
    cutoff = now - ttl_days * 86400

    def _age(c: str) -> float:
        e = cache.get(c)
        return e[1] if (isinstance(e, list) and len(e) >= 2 and e[1]) else 0.0

    stale = [c for c in codes if _age(c) < cutoff]
    if not stale:
        if verbose:
            print(f"✅ refresh_foreign: 전부 신선 (TTL {ttl_days:.0f}일), 갱신 0")
        return {"updated": 0, "skipped": len(codes)}

    # 오래된(또는 미보유) 순으로 우선 갱신 — 상한 적용 시 가장 stale 한 것부터
    stale.sort(key=_age)
    capped = stale[:max_refresh] if max_refresh else stale

    token = kis_api.get_access_token()
    if not token:
        return {"updated": 0, "skipped": len(codes), "reason": "no_token"}

    if verbose:
        cap_note = f" (상한 {max_refresh})" if max_refresh and len(capped) < len(stale) else ""
        print(f"🌐 refresh_foreign: {len(capped)}/{len(stale)} stale 종목 KIS 외인 갱신{cap_note}...")
    updated = 0
    for i, c in enumerate(capped):
        rate = kis_api.fetch_foreign_rate(c, token)
        if rate is not None:
            cache[c] = [rate, now]
            updated += 1
        if (i + 1) % 200 == 0:
            _save_foreign(cache)  # 체크포인트 (중단 내성)
            if verbose:
                print(f"  ... {i + 1}/{len(capped)} (성공 {updated}, 체크포인트 저장)")

    _save_foreign(cache)
    _foreign_mem = cache
    if verbose:
        print(f"✅ refresh_foreign: {updated}종목 갱신 저장 (잔여 stale {len(stale) - len(capped)})")
    return {"updated": updated, "skipped": len(codes) - len(stale),
            "remaining_stale": len(stale) - len(capped)}


# ── CLI (make-hero 단계용) ───────────────────────────────────

def _main() -> None:
    import argparse
    import os

    # .env 로드 (standalone 실행 시)
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

    ap = argparse.ArgumentParser(description="OHLCV 배치 행렬 갱신")
    ap.add_argument("--update", action="store_true", help="pdata 시계열 행렬 갱신")
    ap.add_argument("--window", type=int, default=DEFAULT_TRADING_DAYS, help="보유 영업일 수")
    ap.add_argument("--foreign", action="store_true", help="외인소진율 갱신(KIS)")
    ap.add_argument("--foreign-ttl", type=float, default=7.0, help="외인 캐시 TTL(일)")
    ap.add_argument("--foreign-max", type=int, default=None,
                    help="1회 외인 갱신 상한 (콜드 스윕 분산용, 기본 무제한)")
    args = ap.parse_args()

    if args.update:
        update_to_latest(window=args.window)
    if args.foreign:
        # universe = 최신 pdata 전 종목
        latest = pdata._latest_available_basDt()
        codes = list(pdata.fetch_pdata_price_info(latest).keys()) if latest else []
        refresh_foreign(codes, ttl_days=args.foreign_ttl, max_refresh=args.foreign_max)


if __name__ == "__main__":
    _main()

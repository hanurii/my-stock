"""피벗 근접 알림 — 후보가 피벗 언저리에 오면 알린다.

왜 필요한가:
  사용자는 장 시작 전에 «진입임박» 종목만 피벗 가격으로 자동매수를 예약한다.
  «예의주시» 종목은 예약을 안 걸어 두는데, 그 종목이 장중에 피벗으로 다가오면
  그때 예약을 걸고 싶다. 이 도구는 «예약을 걸 시점»만 알린다 — 매수는 안 한다.

무엇을 보나:
  /stocks/sepa 페이지 표에 «뜨는 종목 그대로». 화면과 알림이 갈리면
  「왜 저 종목은 알림이 안 왔지」가 생기고 그 어긋남은 찾기 어렵다.
  분류 정본은 src/app/stocks/sepa/sepaPatterns.ts 이고, 같은 집합인지는
  scripts/check_watchlist_parity.py 로 확인한다(페이지 코드를 직접 돌려 대조).
  sepa-exclusions.json(상장폐지 예정 등 수동 제외)도 페이지와 같이 적용한다.
  한 종목이 두 패턴에 잡히면 피벗이 둘이므로 «먼저 닿는» 쪽만 남긴다.

언제 우나:
  피벗 대비 −3% ~ +30% 밴드(26-09-17 결정 · 26-09-18 아래를 2→3 으로 넓힘).
  비대칭인 까닭은 예약을 걸 자리는 좁고, 이미 넘어 달리는 종목은 놓치기 싫어서다.
  해당 종목이 없으면 «아무것도 보내지 않는다» — 빈 알림이 1분마다 오면 안 본다.

시세:
  KIS inquire-price 현재가(kis_api.fetch_quote_with_volume). 정규장 전(08:00~09:00)
  에는 전일 종가가 그대로 나오므로 문구에 「장 전」이라고 적어 구분한다.
  애프터마켓(16:00~20:00)에서는 실제 체결가가 움직인다(26-09-17 실측).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

ROOT = Path(__file__).resolve().parents[1]

# .env 로드 — KIS 키가 여기 있다(autobuy/runner.py 와 같은 방식).
_ENV_PATH = ROOT / ".env"
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k, _v)

DATA_DIR = ROOT / "public" / "data"
KST = timezone(timedelta(hours=9))

# 후보 파일 → (문구에 쓸 패턴 이름, 구조 판정 종류, 검출 필드)
#   /stocks/sepa 페이지의 PATTERNS 레지스트리와 «같은 값»이어야 한다.
#   정본: src/app/stocks/sepa/sepaPatterns.ts — 바꾸면 양쪽을 같이 바꾸고
#   scripts/check_watchlist_parity.py 로 집합이 같은지 확인한다.
SOURCES = {
    "sepa-vcp-candidates.json": ("VCP", "vcp", "vcp_detected"),
    "sepa-power-play-candidates.json": ("파워플레이", "powerplay", "pattern_detected"),
    "sepa-power-play-all-candidates.json": ("파워플레이(전수)", "powerplay", "pattern_detected"),
    "sepa-3c-candidates.json": ("3C", "3c", "pattern_detected"),
}

# 페이지가 「피벗 근처」로 보는 폭. sepaPatterns.ts 의 WATCH_PCT 와 같아야 한다.
WATCH_PCT = 12.0

# 감시 대상 제한 (사용자 결정 2026-09-17).
#   페이지 분류(classify)를 «깎지 않고» 그 위에 얹는다 — 깎으면 페이지와 어긋난
#   것인지 일부러 뺀 것인지 구분이 안 되고, 대조 검사(check_watchlist_parity.py)도
#   의미를 잃는다.
#   빈 집합 = 그 파일 전부 제외.
#   까닭: 3C 는 «검출 없이» 피벗만 있으면 예의주시가 되어 헐겁다(26-09-17 실측
#   예의주시 27 중 24가 미검출). 파워플레이 «전수»는 모집단이 RS80 전 종목이라
#   예의주시가 100여 종목씩 올라온다 — 그래서 둘 다 «진입임박»만 받는다.
#   전수를 통째로 뺐다가 되살린 계기(26-09-18): 디아이(003160)가 매수 추천
#   리스트에는 진입임박으로 올랐는데 알림에는 «안» 떴다. 노이즈는 예의주시에
#   몰려 있지 피벗에 바짝 붙은 종목에 있는 게 아니다.
MONITOR_TIERS = {
    "sepa-vcp-candidates.json": {"breakout", "actionable", "watch"},
    "sepa-power-play-candidates.json": {"breakout", "actionable", "watch"},
    "sepa-power-play-all-candidates.json": {"actionable"},
    "sepa-3c-candidates.json": {"actionable"},
}

# 후보 파일의 status → 사람이 읽는 말
STATUS_KO = {
    "breakout": "돌파",
    "actionable": "진입임박",
    "forming": "예의주시",
    "failed": "붕괴",
}

# KRX 정규장 시간 (분 단위, KST). 두 가지가 «이 하나»에서 갈린다 —
#   ① 폴링 주기(정규장은 빠르게) ② 시세 계열(정규장은 J, 밖은 UN).
#   두 곳에 따로 적으면 한쪽만 고쳐져 어긋난다.
REGULAR_START = 9 * 60              # 09:00
REGULAR_END = 15 * 60 + 30          # 15:30 (포함)
DEFAULT_FAST_INTERVAL = 15          # 59종목 조회가 7초라 10초는 빠듯하다
DEFAULT_VOL_WINDOW = 20             # 거래량 배수의 분모 — 최근 N거래일 평균

# 밴드는 비대칭 — 아래 3% · 위 30%.
#   26-09-17 아래 2%로 시작, 26-09-18 «3%로 넓힘» — 케이씨가 −2.80% 로
#   0.8%p 모자라 안 떴다. 아래가 좁은 건 예약을 걸 자리가 좁아서고,
#   위가 넓은 건 이미 넘어 달리는 종목을 놓치지 않으려는 것이다.
DEFAULT_BELOW_PCT = 3.0
DEFAULT_ABOVE_PCT = 30.0


# ── 순수 로직 (시험 대상) ────────────────────────────────────

def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and v == v else None


def structure_ok(raw: dict, kind: str) -> bool:
    """패턴이 검출되진 않았어도 «구조는 섰나» — 페이지의 structureOk 와 같은 규칙."""
    if kind == "vcp":
        n = _num(raw.get("num_contractions"))
        return n is not None and n >= 2
    if kind == "powerplay":
        ln, dp = _num(raw.get("flag_length_days")), _num(raw.get("flag_depth_pct"))
        return ln is not None and ln > 0 and dp is not None and dp > 0
    if kind == "3c":
        return _num(raw.get("pivot_price")) is not None
    return False


def classify(raw: dict, kind: str, watch_pct: float = WATCH_PCT) -> str | None:
    """페이지 표에 뜨는 티어. 안 뜨면 None.

    정본은 src/app/stocks/sepa/sepaPatterns.ts 의 classify — 네 갈래다.
      ①②③ 패턴 검출 + 상태(돌파·진입임박·형성중)
      ④ 검출이 «안» 돼도 피벗 watch_pct 안이고 구조가 서면 예의주시
    ④ 를 빠뜨리면 화면에는 있는데 알림은 안 오는 종목이 생긴다.
    """
    detected = bool(raw.get("vcp_detected") or raw.get("pattern_detected"))
    status = str(raw.get("status") or "")
    if detected and status == "breakout":
        return "breakout"
    if detected and status == "actionable":
        return "actionable"
    if detected and status == "forming":
        return "watch"
    pivot, pct = _num(raw.get("pivot_price")), _num(raw.get("pct_to_pivot"))
    near = pivot is not None and pct is not None and 0 <= pct <= watch_pct
    if status != "failed" and near and structure_ok(raw, kind):
        return "watch"
    return None


def signed_gap(price: float, pivot: float) -> float:
    """피벗 대비 현재가 위치. 아래면 음수, 넘었으면 양수.

    사용자 확정 표기(26-09-17): 「−0.19%」는 피벗 0.19% 아래, 「+0.19%」는 넘었다는 뜻.
    """
    return (price - pivot) / pivot * 100.0


def dedup_by_code(rows: list[dict]) -> list[dict]:
    """한 종목이 여러 패턴에 잡히면 «가까운 피벗»만 남긴다.

    먼저 닿는 피벗이 예약을 걸 자리다(삼성E&A: VCP 51,100 · 3C 51,801).
    """
    best: dict[str, dict] = {}
    for r in rows:
        pv = r.get("pivot_price")
        if not pv:
            continue
        cur = best.get(r["code"])
        if cur is None or pv < cur["pivot_price"]:
            best[r["code"]] = r
    return list(best.values())


def select_near_pivot(rows: list[dict],
                      below_pct: float = DEFAULT_BELOW_PCT,
                      above_pct: float = DEFAULT_ABOVE_PCT) -> list[dict]:
    """밴드 안에 든 종목, 피벗에 가까운 순서로.

    밴드는 «비대칭»이다: 아래 −3% · 위 +30%(26-09-18).
      아래가 좁은 건 예약을 걸 자리가 좁아서고,
      위가 넓은 건 이미 넘어 달리는 종목을 놓치지 않으려는 것이다.
    """
    out = []
    for r in rows:
        pv, px = r.get("pivot_price"), r.get("price")
        if not pv or not px:
            continue
        gap = signed_gap(px, pv)
        if -below_pct <= gap <= above_pct:
            out.append({**r, "gap_pct": gap})
    out.sort(key=lambda r: abs(r["gap_pct"]))
    return out


def _gap_of(r: dict) -> float:
    g = r.get("gap_pct")
    return signed_gap(r["price"], r["pivot_price"]) if g is None else g


def _line(r: dict) -> str:
    status = STATUS_KO.get(r.get("status"), r.get("status") or "")
    vm = r.get("vol_mult")
    vol = f"거래량 {vm:.1f}배  " if vm else ""
    # (전) = NXT 에서 아직 체결이 없다 → 보이는 값은 «전일 종가»지 실시간이 아니다
    mark = "(전) " if r.get("no_trade") else ""
    return (f"{mark}{_gap_of(r):+.2f}%  {r['name']}  {r['price']:,.0f}  {vol}"
            f"{r.get('pattern', '')}·{status}  ({r['pivot_price']:,.0f})")


def format_message(rows: list[dict], now: str, session: str) -> str:
    """알림 한 통. 해당 종목이 없으면 빈 문자열(= 안 보냄).

    두 칸으로 나눈다(사용자 결정 26-09-17).
      [피벗 근접] −3% ~ +0% — 아직 예약을 걸 수 있는 자리
      [피벗 돌파] 0% 초과 전부 — 이미 지나간 자리
    두 칸 모두 피벗에 가까운 순서로.
    """
    if not rows:
        return ""
    near = sorted((r for r in rows if _gap_of(r) <= 0), key=lambda r: abs(_gap_of(r)))
    over = sorted((r for r in rows if _gap_of(r) > 0), key=lambda r: _gap_of(r))
    lines = [f"피벗 알림 {len(rows)}종목 · {now} · {session}"]
    for label, group in (("[피벗 근접]", near), ("[피벗 돌파]", over)):
        if not group:
            continue
        if len(lines) > 1:
            lines.append("")
        lines.append(label)
        lines += [_line(r) for r in group]
    return "\n".join(lines)


def should_measure_volume(now: datetime) -> bool:
    """지금 장중 거래량을 잴 것인가 (사용자 결정 2026-09-20).

    정규장(09:00~15:30)에만 잰다.
      · 09:00 전 — 통합(UN) 조회가 거래량을 «안 준다». 잴 수가 없다.
      · 15:30 후 — 분자(KIS 누적 거래량)에 애프터마켓이 섞이는데 분모(일봉
        거래량)는 정규장 기준이라 기준이 갈린다. 26-09-20 실측: 삼성전자
        acml_vol 이 캐시 09-18 거래량의 1.163배였고 다른 다섯은 1.000 이었다
        — 종목에 따라 섞이기도 하고 안 섞이기도 해서 보정이 안 선다.
    """
    hm = now.hour * 60 + now.minute
    return REGULAR_START <= hm <= REGULAR_END


def avg_recent_volume(series: dict, window: int, today: str) -> float | None:
    """최근 window 거래일 평균 거래량. «오늘은 뺀다».

    오늘을 넣으면 오늘의 폭발이 분모를 키워 배수를 스스로 눌러 버린다.
    """
    dates, vols = series.get("dates") or [], series.get("volumes") or []
    past = [v for d, v in zip(dates, vols) if d < today and v]
    if len(past) < window:
        return None
    tail = past[-window:]
    return sum(tail) / len(tail)


def premarket_baseline(hist: dict, hhmm: str) -> float | None:
    """프리마켓 분모 — 과거 날짜들의 «같은 시각까지» 누적 거래량의 중앙값.

    정규장 일봉 평균을 쓰면 안 된다. 프리마켓 거래량은 정규장 하루의 1~10%
    수준이라 늘 0.0X 배가 나온다(26-09-21 실측). 같은 시간대끼리 견뎌야 한다.

    누적이라 단조 증가하므로, 그 시각 정각 봉이 없으면 «그 이전 마지막» 값을 쓴다.
    거래가 없던 날(빈 칸)은 세지 않는다 — 세면 분모가 눌린다.
    자료: .cache/premarket/premarket-vol-history.json (scripts/build_premarket_vol.py 가 쌓는다)
    """
    vals = []
    for mins in (hist or {}).values():
        if not mins:
            continue
        ks = sorted(k for k in mins if k <= hhmm)
        if ks:
            vals.append(float(mins[ks[-1]]))
    if not vals:
        return None
    vals.sort()
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def volume_multiple(acml_vol: float | None, day_frac: float,
                    avg_vol: float | None) -> float | None:
    """지금 페이스가 평소 하루의 몇 배인가.

    누적 거래량을 «그 시각까지 평소 나오는 비율»로 나눠 하루로 환산한 뒤
    최근 평균과 견준다. 환산을 안 하면 09:10 에는 모든 종목이 「거래량 없음」이
    된다(그 시각엔 원래 하루치의 일부만 나온다).
    비율 정본: public/data/intraday-vol-curve.json — 09:30 20.8% · 10:00 32.1%.
    """
    if not acml_vol or not avg_vol or not day_frac:
        return None
    return (acml_vol / day_frac) / avg_vol


def poll_interval(now: datetime, base: int, fast: int) -> int:
    """지금 몇 초 주기로 볼 것인가 (사용자 결정 2026-09-18).

    정규장(09:00~15:30)은 빠르게 본다. 그 밖은 base.
    빠른 쪽이 base 보다 크면 뜻이 없으므로 작은 쪽을 쓴다.
    """
    hm = now.hour * 60 + now.minute
    rush = REGULAR_START <= hm <= REGULAR_END
    return min(base, fast) if rush else base


def sleep_seconds(interval: int, elapsed: float) -> float:
    """다음 바퀴까지 쉴 시간.

    interval 은 «주기»지 «쉬는 시간»이 아니다. 조회에 걸린 만큼 빼야
    15초 주기가 실제로 15초가 된다(안 빼면 7+15=22초가 된다).
    조회가 주기보다 오래 걸리면 쉬지 않는다.
    """
    return max(0.0, interval - elapsed)


def quote_market_div(now: datetime) -> str:
    """지금 어느 계열로 현재가를 잴 것인가 (사용자 결정 2026-09-18).

    정규장(09:00~15:30) → "J"(KRX). 피벗이 «정규장» 일봉에서 나온 값이라
      같은 계열로 재야 「돌파」 판정이 피벗과 앞뒤가 맞는다.
    그 밖(장 전·장후·애프터마켓) → "UN"(통합, KRX+NXT). 정규장이 닫히면 J 는
      «굳은 값»이라 현재가가 아니다. 실측 둘:
        08:1x 장 전   — 삼성전자 J 252,500(=전일 종가) vs UN 259,500
        16:10 애프터  — 케이씨 J 41,300(=당일 정규장 종가) vs UN 41,000(MTS 와 같음)
      애프터마켓 체결이 NXT 로 가면 J 에는 «안» 잡힌다.
      🚨 그 시간대 UN 가격은 공식 종가도 다음 날 기준가도 «아니다»(26-09-17 조사).
         그래도 지금 실제로 거래되는 값이라 이걸로 돌파를 판정한다(사용자 결정).
    """
    hm = now.hour * 60 + now.minute
    if REGULAR_START <= hm <= REGULAR_END:
        return "J"
    if hm < REGULAR_START:
        return "NX"          # 프리마켓 — 체결 유무를 가르려면 NXT 단독으로 받아야 한다
    return "UN"


def session_label(now: datetime) -> str:
    """지금이 어느 장인가 — 문구에 붙여 현재가의 뜻을 분명히 한다.

    어느 «계열»로 잰 값인지도 같이 적는다. 두 계열이 갈릴 때 구분이 안 되면
    「NXT 에서는 넘었는데 KRX 기준으로는 아직」을 못 읽는다.
    """
    hm = now.hour * 60 + now.minute
    div = quote_market_div(now)
    series = {"J": "KRX", "NX": "NXT", "UN": "NXT 통합"}.get(div, div)
    if hm < REGULAR_START:
        name = "장 전"
    elif hm <= REGULAR_END:
        name = "정규장"
    elif hm < 16 * 60:
        name = "장후 종가매매"
    else:
        name = "애프터마켓"
    return f"{name}({series})"


# ── 자료 읽기 ────────────────────────────────────────────────

def is_monitored(raw: dict, fname: str, kind: str) -> bool:
    """페이지엔 뜨더라도 «감시»할 것인가 — 분류 위에 얹는 한 겹."""
    tier = classify(raw, kind)
    return tier is not None and tier in MONITOR_TIERS.get(fname, set())


def load_premarket_history() -> dict:
    """프리마켓 거래량 이력 {종목: {날짜: {HHMM: 누적}}}. 없으면 빈 dict."""
    p = ROOT / ".cache" / "premarket" / "premarket-vol-history.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("codes") or {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_exclusions() -> set[str]:
    """수동 제외(상장폐지 예정 등). 페이지도 같은 파일을 쓴다."""
    p = DATA_DIR / "sepa-exclusions.json"
    if not p.exists():
        return set()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {e["code"] for e in (d.get("exclusions") or []) if e.get("code")}


def load_watch_universe() -> list[dict]:
    """/stocks/sepa 페이지 표에 뜨는 종목 전부. price 는 아직 비어 있다."""
    excluded = load_exclusions()
    rows: list[dict] = []
    for fname, (pattern, kind, _field) in SOURCES.items():
        p = DATA_DIR / fname
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for r in d.get("candidates") or []:
            if r["code"] in excluded:
                continue
            tier = classify(r, kind)
            if tier is None or not r.get("pivot_price"):
                continue
            if tier not in MONITOR_TIERS.get(fname, set()):
                continue
            rows.append({
                "code": r["code"], "name": r.get("name") or r["code"],
                "pivot_price": float(r["pivot_price"]),
                "status": r.get("status"), "tier": tier, "pattern": pattern,
                "price": None,
            })
    rows = dedup_by_code(rows)
    attach_avg_volume(rows)
    return rows


def attach_avg_volume(rows: list[dict], window: int = DEFAULT_VOL_WINDOW) -> None:
    """거래량 배수의 «분모» — 최근 window 거래일 평균 거래량을 붙인다.

    시계열 캐시(.cache/ohlcv/series)에서 읽는다. 그 캐시의 거래량은 정규장
    기준이고(26-09-20 3출처 대조: 캐시=FDR=네이버), 분자인 KIS acml_vol 도
    정규장 중에는 같은 기준이다(실측 비율 1.000). 그래서 정규장에만 잰다.
    """
    from canslim_lib import ohlcv_matrix
    today = f"{datetime.now(KST):%Y-%m-%d}"
    for r in rows:
        p = ohlcv_matrix.SERIES_DIR / f"{r['code']}.json"
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        r["avg_vol"] = avg_recent_volume(s, window, today)


def attach_live_prices(rows: list[dict], verbose: bool = False,
                       max_workers: int = 8) -> list[dict]:
    """KIS 현재가를 붙인다. 못 받은 종목은 price=None 으로 남아 걸러진다.

    종목이 140개를 넘으므로 순차로는 1분 안에 못 돈다(실측 31종목 50초).
    kis_api._throttle 이 잠금으로 초당 호출을 스스로 제한하니 스레드로 띄워도
    호출 속도는 그 한도를 안 넘는다 — 없애는 건 «대기 시간»이지 한도가 아니다.
    """
    import concurrent.futures as _cf
    from canslim_lib import kis_api
    token = kis_api.get_access_token()
    now = datetime.now(KST)
    div = quote_market_div(now)
    with_vol = should_measure_volume(now)
    day_frac = 0.0
    if with_vol:
        from autobuy import vol_curve
        day_frac = vol_curve.expected_vol_frac(f"{now:%H%M%S}", base=ROOT)
    # 프리마켓은 «같은 시각까지의 프리마켓 누적»과 견준다(정규장 평균은 못 쓴다)
    pre_hist, pre_hhmm = ({}, f"{now:%H%M}")
    if div == "NX":
        pre_hist = load_premarket_history()

    def _one(r):
        try:
            if div == "NX":
                # 프리마켓 — NXT 단독으로 받는다. 체결이 없으면 현재가가 0 으로 와서
                # 「안 움직인 것」과 「거래가 없는 것」이 갈린다(UN 은 전일 종가로 덮는다).
                q = kis_api.fetch_nxt_quote(r["code"], token=token)
                if q and q.get("current") and q.get("acml_vol"):
                    base = premarket_baseline(pre_hist.get(r["code"]) or {}, pre_hhmm)
                    if base:
                        r["vol_mult"] = q["acml_vol"] / base
                if q and not q.get("current"):
                    r["no_trade"] = True
                    q = kis_api.fetch_integrated_price(r["code"], token=token, market_div="UN")
            elif div == "UN":
                q = kis_api.fetch_integrated_price(r["code"], token=token, market_div="UN")
            else:
                q = kis_api.fetch_quote_with_volume(r["code"], token=token)
        except Exception:
            return
        if q and q.get("current"):
            r["price"] = float(q["current"])
        if with_vol and q and q.get("acml_vol"):
            r["vol_mult"] = volume_multiple(q["acml_vol"], day_frac, r.get("avg_vol"))

    t0 = time.time()
    with _cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        list(ex.map(_one, rows))
    ok = sum(1 for r in rows if r.get("price"))
    if verbose:
        print(f"   시세 {ok}/{len(rows)}종목 ({time.time() - t0:.1f}초)")
    return rows


# ── 내보내기 ────────────────────────────────────────────────

def send_console(text: str) -> None:
    print(text)


def build_telegram_request(token: str, chat_id: str, text: str) -> tuple[str, dict]:
    """sendMessage 호출 주소와 본문. 둘 중 하나라도 비면 바로 멈춘다."""
    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN · TELEGRAM_CHAT_ID 를 .env 에 넣어야 한다 "
            "(chat_id 는 --chat-id 로 조회)")
    return (f"https://api.telegram.org/bot{token}/sendMessage",
            {"chat_id": chat_id, "text": text, "disable_web_page_preview": True})


def send_telegram(text: str) -> None:
    import urllib.request as _u
    url, body = build_telegram_request(os.environ.get("TELEGRAM_BOT_TOKEN", ""),
                                       os.environ.get("TELEGRAM_CHAT_ID", ""), text)
    req = _u.Request(url, data=json.dumps(body).encode(), method="POST",
                     headers={"content-type": "application/json"})
    with _u.urlopen(req, timeout=15) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    if not out.get("ok"):
        raise RuntimeError(f"텔레그램 전송 실패: {out}")


def discover_chat_id() -> None:
    """봇과 대화를 한 번 시작한 뒤 이걸 돌리면 chat_id 가 나온다."""
    import urllib.request as _u
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("TELEGRAM_BOT_TOKEN 이 .env 에 없다"); return
    with _u.urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=15) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    chats = {}
    for u in out.get("result") or []:
        c = (u.get("message") or u.get("channel_post") or {}).get("chat") or {}
        if c.get("id"):
            chats[c["id"]] = c.get("username") or c.get("title") or c.get("first_name") or ""
    if not chats:
        print("대화 기록이 없다 — 텔레그램에서 봇에게 아무 말이나 한 번 보내고 다시 돌려라")
        return
    for cid, who in chats.items():
        print(f"TELEGRAM_CHAT_ID={cid}   ({who})")


# ── 실행 ────────────────────────────────────────────────────

def poll_once(below_pct: float, above_pct: float, sink,
              verbose: bool = False) -> int:
    now = datetime.now(KST)
    universe = load_watch_universe()
    if verbose:
        print(f"[{now:%H:%M:%S}] 감시 {len(universe)}종목 ({session_label(now)})")
    attach_live_prices(universe, verbose=verbose)
    hits = select_near_pivot(universe, below_pct, above_pct)
    msg = format_message(hits, now=f"{now:%Y-%m-%d %H:%M}", session=session_label(now))
    if msg:
        sink(msg)
    elif verbose:
        near = sorted((r for r in universe if r.get("price") and r.get("pivot_price")),
                      key=lambda r: abs(signed_gap(r["price"], r["pivot_price"])))[:3]
        tail = "  ".join(f"{r['name']} {signed_gap(r['price'], r['pivot_price']):+.2f}%"
                         for r in near)
        print(f"   해당 없음. 제일 가까운 셋 — {tail or '없음'}")
    return len(hits)


def main() -> None:
    ap = argparse.ArgumentParser(description="피벗 근접 알림")
    ap.add_argument("--below", type=float, default=DEFAULT_BELOW_PCT,
                    help="피벗 «아래» 몇 퍼센트까지 (기본 2)")
    ap.add_argument("--above", type=float, default=DEFAULT_ABOVE_PCT,
                    help="피벗을 «넘은» 쪽 몇 퍼센트까지 (기본 30)")
    ap.add_argument("--once", action="store_true", help="한 번만 재고 끝낸다(문구 검토용)")
    ap.add_argument("--interval", type=int, default=60, help="기본 주기(초, 기본 60)")
    ap.add_argument("--fast-interval", type=int, default=DEFAULT_FAST_INTERVAL,
                    help="09:00~09:30 주기(초, 기본 15)")
    ap.add_argument("--until", default="20:00", help="이 시각까지 돈다 (HH:MM)")
    ap.add_argument("--telegram", action="store_true", help="콘솔 대신 텔레그램으로 보낸다")
    ap.add_argument("--vol-window", type=int, default=DEFAULT_VOL_WINDOW,
                    help="거래량 배수의 분모 — 최근 N거래일 평균 (기본 20)")
    ap.add_argument("--chat-id", action="store_true", help="텔레그램 chat_id 를 조회하고 끝낸다")
    ap.add_argument("--test-send", action="store_true", help="텔레그램으로 시험 한 통 보내고 끝낸다")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    if a.chat_id:
        discover_chat_id()
        return
    if a.test_send:
        send_telegram(f"피벗 근접 알림 연결 확인 · {datetime.now(KST):%Y-%m-%d %H:%M}")
        print("보냈다 — 폰을 확인해라")
        return

    sink = send_telegram if a.telegram else send_console
    if a.once:
        poll_once(a.below, a.above, sink, verbose=True)
        return

    end_h, end_m = (int(x) for x in a.until.split(":"))
    print("=" * 52)
    print(f"  피벗 근접 알림 — 아래 −{a.below:g}% ~ 위 +{a.above:g}% 안에 들면 알린다")
    print(f"  {a.interval}초 주기 · {a.until} 까지 · "
          f"{'텔레그램' if a.telegram else '콘솔'}로 보냄")
    print(f"  09:00~15:30 정규장은 {min(a.interval, a.fast_interval)}초 주기")
    print("  매수는 하지 않는다. 예약을 걸 시점만 알린다.")
    print("  멈추기: Ctrl+C")
    print("=" * 52)
    prev_iv = None
    while True:
        now = datetime.now(KST)
        if (now.hour, now.minute) >= (end_h, end_m):
            print(f"[{now:%H:%M}] {a.until} 도달 — 종료")
            return
        iv = poll_interval(now, a.interval, a.fast_interval)
        if iv != prev_iv:
            print(f"[{now:%H:%M}] 주기 {iv}초")
            prev_iv = iv
        t0 = time.time()
        try:
            poll_once(a.below, a.above, sink, verbose=a.verbose)
        except Exception as e:                      # 한 번 실패로 하루가 멈추면 안 된다
            print(f"[{now:%H:%M}] 조회 실패 — {type(e).__name__}: {e}")
        time.sleep(sleep_seconds(iv, time.time() - t0))


if __name__ == "__main__":
    main()

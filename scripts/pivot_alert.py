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
  피벗 대비 −2% ~ +30% 밴드(사용자 결정 26-09-17). 비대칭인 까닭은 예약을 걸
  자리는 좁고, 이미 넘어 달리는 종목은 놓치기 싫어서다.
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
#   예의주시 27 중 24가 미검출). 파워플레이 전수는 모집단이 RS80 전 종목이라
#   120종목이 통째로 올라온다.
MONITOR_TIERS = {
    "sepa-vcp-candidates.json": {"breakout", "actionable", "watch"},
    "sepa-power-play-candidates.json": {"breakout", "actionable", "watch"},
    "sepa-power-play-all-candidates.json": set(),
    "sepa-3c-candidates.json": {"actionable"},
}

# 후보 파일의 status → 사람이 읽는 말
STATUS_KO = {
    "breakout": "돌파",
    "actionable": "진입임박",
    "forming": "예의주시",
    "failed": "붕괴",
}

# 밴드는 비대칭 — 아래 2% · 위 30% (사용자 결정 26-09-17)
DEFAULT_BELOW_PCT = 2.0
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

    밴드는 «비대칭»이다(사용자 결정 26-09-17): 아래 −2% · 위 +30%.
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
    return (f"{_gap_of(r):+.2f}%  {r['name']}  {r['price']:,.0f}  "
            f"{r.get('pattern', '')}·{status}  ({r['pivot_price']:,.0f})")


def format_message(rows: list[dict], now: str, session: str) -> str:
    """알림 한 통. 해당 종목이 없으면 빈 문자열(= 안 보냄).

    두 칸으로 나눈다(사용자 결정 26-09-17).
      [피벗 근접] −2% ~ +0% — 아직 예약을 걸 수 있는 자리
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


def session_label(now: datetime) -> str:
    """지금이 어느 장인가 — 문구에 붙여 현재가의 뜻을 분명히 한다."""
    hm = now.hour * 60 + now.minute
    if hm < 9 * 60:
        return "장 전"          # 현재가 = 전일 종가
    if hm <= 15 * 60 + 30:
        return "정규장"
    if hm < 16 * 60:
        return "장후 종가매매"
    return "애프터마켓"


# ── 자료 읽기 ────────────────────────────────────────────────

def is_monitored(raw: dict, fname: str, kind: str) -> bool:
    """페이지엔 뜨더라도 «감시»할 것인가 — 분류 위에 얹는 한 겹."""
    tier = classify(raw, kind)
    return tier is not None and tier in MONITOR_TIERS.get(fname, set())


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
    return dedup_by_code(rows)


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

    def _one(r):
        try:
            q = kis_api.fetch_quote_with_volume(r["code"], token=token)
        except Exception:
            return
        if q and q.get("current"):
            r["price"] = float(q["current"])

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
    ap.add_argument("--interval", type=int, default=60, help="반복 간격(초, 기본 60)")
    ap.add_argument("--until", default="20:00", help="이 시각까지 돈다 (HH:MM)")
    ap.add_argument("--telegram", action="store_true", help="콘솔 대신 텔레그램으로 보낸다")
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
    print(f"  {a.interval}초 간격 · {a.until} 까지 · "
          f"{'텔레그램' if a.telegram else '콘솔'}로 보냄")
    print("  매수는 하지 않는다. 예약을 걸 시점만 알린다.")
    print("  멈추기: Ctrl+C")
    print("=" * 52)
    while True:
        now = datetime.now(KST)
        if (now.hour, now.minute) >= (end_h, end_m):
            print(f"[{now:%H:%M}] {a.until} 도달 — 종료")
            return
        try:
            poll_once(a.below, a.above, sink, verbose=a.verbose)
        except Exception as e:                      # 한 번 실패로 하루가 멈추면 안 된다
            print(f"[{now:%H:%M}] 조회 실패 — {type(e).__name__}: {e}")
        time.sleep(a.interval)


if __name__ == "__main__":
    main()

"""SEPA 종목 실적발표 캘린더 — DART 공시만으로 다음 실적발표 시점 추정.

대상 종목(합집합):
  (a) sepa-trend-candidates.json candidates[] 중 all_pass 또는 gate_near
  (b) sepa-vcp / sepa-3c / sepa-power-play candidates[] 전부
  (c) sepa-holdings.json holdings[]

판정 로직 (estimate_next_earnings — 순수 함수, 단위테스트 대상):
  1. confirmed: asof 21일 이내 결산실적공시예고(이후 잠정/정기 없음) → 창 [예고+1, 예고+14],
     대표일 = 작년 같은 분기 잠정실적 월/일이 창 안이면 그 날, 아니면 예고+8.
     예고 없고 10일 이내 IR개최 안내 → 창 [IR일, IR+7] (약한 신호).
  2. estimated: 작년 같은 시기 이벤트(잠정실적·분기/반기/사업보고서) 월/일 투영(±4일 창,
     법정기한 상한: 분기 5/15·11/14, 반기 8/14, 사업 3/31) + 법정기한 자체를 후보로 추가,
     가장 이른 다가올 후보 채택.
  3. 다가올 예상일이 지평(HORIZON_DAYS) 안일 때만 byCode 에 수록. 페이지는 ≤14일만 표시.

출력: public/data/sepa-earnings-calendar.json  (--save 시 저장, 아니면 드라이런)
DART 예산: 종목당 list.json 1콜, .cache/earnings_calendar/<code>.json 3일 TTL 캐시.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Windows cp949 콘솔에서 한글/이모지 안전 출력
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_dotenv() -> None:
    """프로젝트 루트의 .env 파일에서 환경변수 주입 (이미 설정된 키는 보존)."""
    import os
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

from canslim_lib.fetch import (  # noqa: E402
    dart_get,
    load_corp_code_map,
    resolve_corp_code,
)

DATA_DIR = ROOT / "public" / "data"
OUT_PATH = DATA_DIR / "sepa-earnings-calendar.json"
CACHE_DIR = ROOT / ".cache" / "earnings_calendar"

CACHE_TTL_DAYS = 3      # 캐시 신선 기간 — 야간 반복 실행 시 API 호출 절약
LOOKBACK_DAYS = 400     # 공시 조회 범위 (작년 같은 분기 패턴 확보용)
# 수록 지평. 계약 초안은 60일이었으나 스펙 자체 예시(8/17 → 11/5 잠정 패턴 = 80일)가
# "수록되어야 한다"고 명시 → 다음 분기 이벤트가 항상 들어오도록 100일로 확장.
# 페이지는 어차피 ≤14일만 표시하므로 하류 영향 없음.
HORIZON_DAYS = 100

# 실적 이벤트로 취급하는 공시 종류 (잠정실적 + 정기보고서 3종)
EVENT_KINDS = {"잠정실적", "분기보고서", "반기보고서", "사업보고서"}


# ── 제목 분류 ─────────────────────────────────────────────────────────

def classify_title(title: str) -> str | None:
    """DART report_nm → 이벤트 종류. 해당 없으면 None. 정정공시는 원공시 중복이라 제외."""
    t = str(title or "")
    if "정정" in t:  # [기재정정]·[첨부정정] 재제출 — 날짜 패턴을 오염시키므로 무시
        return None
    if "결산실적공시예고" in t:
        return "예고"
    if "기업설명회" in t and "개최" in t:
        return "IR"
    if "잠정" in t and ("실적" in t or "영업" in t):
        return "잠정실적"  # 연결재무제표기준영업(잠정)실적(공정공시) 등
    if "분기보고서" in t:
        return "분기보고서"
    if "반기보고서" in t:
        return "반기보고서"
    if "사업보고서" in t:
        return "사업보고서"
    return None


def _to_date(v) -> date | None:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None


def _project(d: date, year: int) -> date:
    """월/일을 다른 해에 투영 (2/29 → 2/28)."""
    try:
        return date(year, d.month, d.day)
    except ValueError:
        return date(year, 2, 28)


def _legal_deadline(kind: str, month: int, year: int) -> date | None:
    """12월 결산 가정 법정 제출기한 — 투영일의 상한."""
    if kind == "사업보고서":
        return date(year, 3, 31)
    if kind == "반기보고서":
        return date(year, 8, 14)
    if kind == "분기보고서":
        return date(year, 5, 15) if month <= 7 else date(year, 11, 14)
    if kind == "잠정실적":  # 잠정은 해당 시기 정기보고서 기한을 상한으로
        if month <= 3:
            return date(year, 3, 31)
        if month <= 6:
            return date(year, 5, 15)
        if month <= 9:
            return date(year, 8, 14)
        return date(year, 11, 14)
    return None


# ── 핵심: 다음 실적발표 추정 (순수 함수) ──────────────────────────────

def estimate_next_earnings(filings: list[dict], asof: date | str) -> dict | None:
    """공시 이력 → 다음 실적발표 추정.

    filings: [{"date": "YYYY-MM-DD"|date, "title": str}, ...] (순서 무관)
    반환: {"status","expected","window","d_day","basis","last_report"} 또는 None.
    asof 이후 공시는 무시 (as-of 안전).
    """
    asof = _to_date(asof)
    if asof is None:
        return None

    past: list[tuple[date, str, str | None]] = []
    for f in filings or []:
        d = _to_date(f.get("date"))
        if d is None or d > asof:
            continue
        t = str(f.get("title") or "")
        past.append((d, t, classify_title(t)))
    past.sort(key=lambda x: x[0])
    if not past:
        return None

    events = [(d, t, k) for d, t, k in past if k in EVENT_KINDS]
    last_report = None
    if events:
        ld, lt, _ = events[-1]
        last_report = {"date": ld.isoformat(), "title": lt}

    def _pack(status: str, expected: date, win: tuple[date, date], basis: str) -> dict:
        return {
            "status": status,
            "expected": expected.isoformat(),
            "window": [win[0].isoformat(), win[1].isoformat()],
            "d_day": (expected - asof).days,
            "basis": basis,
            "last_report": last_report,
        }

    def _pattern_in_window(anchor: date, win: tuple[date, date], kinds: set[str]) -> date | None:
        """anchor 반년 이상 이전(=작년 시즌) 이벤트의 월/일을 창 안에 투영. 최근 것 우선."""
        hit = None
        for d, _t, k in events:
            if k not in kinds or d > anchor - timedelta(days=180):
                continue
            for yr in {win[0].year, win[1].year}:
                c = _project(d, yr)
                if win[0] <= c <= win[1]:
                    hit = c
        return hit

    # 1a. confirmed — 결산실적공시예고 (asof 21일 이내, 이후 잠정/정기 아직 없음)
    yego = [d for d, _t, k in past if k == "예고" and (asof - d).days <= 21]
    if yego:
        yd = max(yego)
        if not any(d >= yd for d, _t, _k in events):
            win = (yd + timedelta(days=1), yd + timedelta(days=14))
            exp = _pattern_in_window(yd, win, {"잠정실적"}) or (yd + timedelta(days=8))
            return _pack("confirmed", exp, win, f"{yd.month}/{yd.day} 결산실적공시예고")

    # 1b. confirmed(약) — IR개최 안내 (asof 10일 이내, 예고 없고 이후 잠정/정기 없음)
    irs = [d for d, _t, k in past if k == "IR" and (asof - d).days <= 10]
    if irs:
        ird = max(irs)
        if not any(d >= ird for d, _t, _k in events):  # 같은 날 공시도 소진으로 간주
            win = (ird, ird + timedelta(days=7))
            exp = _pattern_in_window(ird, win, EVENT_KINDS) or (ird + timedelta(days=3))
            return _pack("confirmed", exp, win, f"{ird.month}/{ird.day} IR개최 안내")

    # 2. estimated — 작년 패턴 투영 + 법정기한 후보 중 가장 이른 다가올 날짜
    cands: list[tuple[date, int, tuple[date, date], str]] = []  # (expected, 우선순위, 창, 근거)

    def _already_filed(kind: str, cand: date) -> bool:
        """같은 종류 공시가 이번 시즌에 이미 나왔으면(후보일 60일 이내) 재예측 금지."""
        return any(k2 == kind and cand - timedelta(days=60) < d2 <= asof
                   for d2, _t2, k2 in events)

    for d, _t, k in events:
        for yr in (asof.year, asof.year + 1):
            c = _project(d, yr)
            if c <= asof or _already_filed(k, c):
                continue
            dl = _legal_deadline(k, c.month, c.year)
            exp = min(c, dl) if dl else c
            win_end = min(exp + timedelta(days=4), dl) if dl else exp + timedelta(days=4)
            cands.append((exp, 0, (exp - timedelta(days=4), win_end),
                          f"작년 {k} {d.month}/{d.day} 패턴"))

    deadline_md = {"분기보고서": [(5, 15), (11, 14)], "반기보고서": [(8, 14)], "사업보고서": [(3, 31)]}
    kinds_present = {k for _d, _t, k in events}
    # 정기보고서를 하나라도 내는 회사는 세 종류 모두 낸다 (12월 결산 상장사 의무)
    # — 공시가 많아 조회창(100건)이 짧아진 대형주도 기한 폴백은 살리기 위함.
    if kinds_present & set(deadline_md):
        kinds_present |= set(deadline_md)
    for k, mds in deadline_md.items():
        if k not in kinds_present:
            continue
        for m, dd in mds:
            for yr in (asof.year, asof.year + 1):
                c = date(yr, m, dd)
                if c <= asof or _already_filed(k, c):
                    continue
                cands.append((c, 1, (c - timedelta(days=14), c), f"{k} 기한 {m}/{dd}"))

    if not cands:
        return None
    cands.sort(key=lambda x: (x[0], x[1]))
    exp, _prio, win, basis = cands[0]
    return _pack("estimated", exp, win, basis)


# ── 대상 종목 수집 ────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_targets() -> dict[str, str]:
    """대상 코드 → 이름. (a) trend all_pass/gate_near (b) 패턴 후보 3종 (c) 보유."""
    targets: dict[str, str] = {}

    def add(code, name) -> None:
        code = str(code or "").strip()
        if code and code not in targets:
            targets[code] = str(name or code)

    try:
        tr = _load_json(DATA_DIR / "sepa-trend-candidates.json")
        for c in tr.get("candidates", []):
            if c.get("all_pass") or c.get("gate_near"):
                add(c.get("code"), c.get("name"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    for fn in ("sepa-vcp-candidates.json", "sepa-3c-candidates.json",
               "sepa-power-play-candidates.json"):
        try:
            d = _load_json(DATA_DIR / fn)
            for c in d.get("candidates", []):
                add(c.get("code"), c.get("name"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    try:
        h = _load_json(DATA_DIR / "sepa-holdings.json")
        for x in h.get("holdings", []):
            add(x.get("code"), x.get("name"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return targets


# ── DART 공시 수집 (종목당 1콜 + 3일 TTL 캐시) ───────────────────────

def fetch_filings(code: str, corp_map: dict[str, str], asof: date) -> tuple[list[dict] | None, bool]:
    """(filings, from_cache). 실패 시 (None, False) — 실패는 캐시하지 않음."""
    cache_path = CACHE_DIR / f"{code}.json"
    if cache_path.exists():
        try:
            c = json.loads(cache_path.read_text(encoding="utf-8"))
            fetched = datetime.fromisoformat(c["fetched_at"])
            if (datetime.now() - fetched) < timedelta(days=CACHE_TTL_DAYS):
                return c["filings"], True
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            pass

    corp_code, _parent = resolve_corp_code(code, corp_map)
    if not corp_code:
        return None, False

    rows = dart_get("list", {
        "corp_code": corp_code,
        "bgn_de": (asof - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d"),
        "end_de": asof.strftime("%Y%m%d"),
        "page_no": "1",
        "page_count": "100",
    })
    if rows is None:
        return None, False

    filings = []
    for r in rows:
        dt = str(r.get("rcept_dt") or "")
        nm = str(r.get("report_nm") or "").strip()
        if len(dt) == 8 and dt.isdigit():
            filings.append({"date": f"{dt[:4]}-{dt[4:6]}-{dt[6:]}", "title": nm})
    filings.sort(key=lambda f: f["date"])

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"fetched_at": datetime.now().isoformat(timespec="seconds"),
                    "filings": filings}, ensure_ascii=False),
        encoding="utf-8")
    return filings, False


# ── 메인 ─────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="SEPA 실적발표 캘린더 (DART 공시 기반)")
    ap.add_argument("--save", action="store_true", help="결과를 JSON 파일로 저장")
    ap.add_argument("--asof", default=None, help="기준일 YYYY-MM-DD (기본: 오늘)")
    args = ap.parse_args()
    asof = date.fromisoformat(args.asof) if args.asof else date.today()

    targets = collect_targets()
    print(f"대상 종목: {len(targets)}개 (asof {asof.isoformat()})")

    corp_map = load_corp_code_map()
    if not corp_map:
        print("❌ corp_code 매핑 없음 — .cache/dart_corpcode.json / DART_API_KEY 확인")
        return 1

    by_code: dict[str, dict] = {}
    n_cache = n_api = n_fail = 0
    for code, name in sorted(targets.items()):
        filings, from_cache = fetch_filings(code, corp_map, asof)
        if filings is None:
            n_fail += 1
            continue
        if from_cache:
            n_cache += 1
        else:
            n_api += 1

        res = estimate_next_earnings(filings, asof)
        if res is None:
            continue
        if res["d_day"] > HORIZON_DAYS:
            continue  # 너무 먼 미래 — 수록 생략
        if date.fromisoformat(res["window"][1]) < asof:
            continue  # 창이 이미 닫힘 (지나간 이벤트)
        by_code[code] = {"name": name, **res}

    ordered = dict(sorted(by_code.items(), key=lambda kv: kv[1]["d_day"]))
    out = {
        "asof": asof.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "byCode": ordered,
    }

    print(f"조회: 캐시 {n_cache} / API {n_api} / 실패 {n_fail}")
    print(f"다가올 실적발표 산출: {len(ordered)}개 (지평 {HORIZON_DAYS}일)")
    print("가장 가까운 5개:")
    for code, e in list(ordered.items())[:5]:
        print(f"  D{e['d_day']:+d} {e['expected']} [{e['status']}] "
              f"{e['name']}({code}) — {e['basis']}")

    if args.save:
        OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(f"💾 저장: {OUT_PATH.relative_to(ROOT)}")
    else:
        print("(드라이런 — --save 로 저장)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

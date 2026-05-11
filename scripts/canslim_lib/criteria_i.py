"""CAN SLIM 'I' 원칙 (Institutional Sponsorship) 평가 로직.

데이터 소스:
- DART majorstock (5%룰 대량보유 보고)
- finance.naver.com /item/frgn.nhn (일별 기관 순매매 — 백필)

평가 구조:
1. 보고자 분류 (한국 운용사 / 글로벌 운용사 / 연기금 / 기타)
2. 5%룰 추세 (신규 진입 · 지분율 누적 변동)
3. 기관 매매 누적 (60일 · 가용 한도)
4. 이탈 게이트 — 기관이 빠져나가면 제외 (오닐: 기관 매도면 매수 금지)
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


# 보고자 분류 키워드
KOREAN_AM_KEYWORDS = ["자산운용", "투자신탁운용", "투자자문"]
GLOBAL_AM_KEYWORDS = [
    "BlackRock", "Capital", "Vanguard", "Fidelity", "StateStreet", "State Street",
    "Norges", "Macquarie", "Nomura", "Morgan", "Goldman", "JPMorgan", "Schroder",
    "Asset Management", "Investment", "Fund", "Advisors", "LP",
]
PENSION_KEYWORDS = ["국민연금공단", "사학연금", "공무원연금", "우정사업본부"]


def classify_reporter(name: str) -> str:
    """보고자 분류: korean_am / global_am / pension / other (계열사·임원·기타)."""
    if not name:
        return "other"
    if any(k in name for k in PENSION_KEYWORDS):
        return "pension"
    if any(k in name for k in KOREAN_AM_KEYWORDS):
        return "korean_am"
    if any(k.lower() in name.lower() for k in GLOBAL_AM_KEYWORDS):
        return "global_am"
    return "other"


def analyze_majorstock(items: list[dict]) -> dict:
    """majorstock raw items → 보고자별 시계열 + 종합 시그널.

    신규 진입 3 카테고리 (각각 별도 플래그):
      - is_strict_new_1y       : first_rcept_dt 가 1년 이내 (DART 시계열 첫 등장)
      - is_recent_buyer_90d    : 최근 90일 내 stkrt_irds > 0 보고 1건+ (기보유 운용사 추가 매수)
      - is_returning_after_gap : 보고 간격 ≥ 180일 + 최근 보고 1년 내 + 현재 5%+
      - is_new_or_increasing_1y: (위 셋 중 하나) AND is_active AND 운용사/연기금 카테고리

    Returns:
      {
        "reporters": [...],
        "summary": {
          "korean_am_count", "global_am_count", "pension_count",
          "new_or_increasing_1y": [...],       # 종합 플래그 충족 보고자
          "strict_new_count", "recent_buyer_count", "returning_count",
          "exits_1y": [...],
          "total_stkrt_change_1y_pct": X,
          "any_institutional": bool,
        }
      }
    """
    if not items:
        return {
            "reporters": [],
            "summary": {
                "korean_am_count": 0,
                "global_am_count": 0,
                "pension_count": 0,
                "new_or_increasing_1y": [],
                "strict_new_count": 0,
                "recent_buyer_count": 0,
                "returning_count": 0,
                "exits_1y": [],
                "total_stkrt_change_1y_pct": 0.0,
                "any_institutional": False,
            },
        }

    by_reporter: dict[str, list[dict]] = {}
    for it in items:
        name = (it.get("repror") or "").strip()
        if not name:
            continue
        by_reporter.setdefault(name, []).append(it)

    now = datetime.now()
    one_year_ago = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    ninety_days_ago = (now - timedelta(days=90)).strftime("%Y-%m-%d")

    reporters = []
    new_or_increasing = []
    exits = []
    total_irds = 0.0
    korean_am_count = 0
    global_am_count = 0
    pension_count = 0
    strict_new_count = 0
    recent_buyer_count = 0
    returning_count = 0

    for name, filings in by_reporter.items():
        category = classify_reporter(name)
        filings_sorted = sorted(filings, key=lambda x: x.get("rcept_dt", ""))
        try:
            current_stkrt = float((filings_sorted[-1].get("stkrt") or "0").replace(",", ""))
        except (ValueError, AttributeError):
            current_stkrt = 0.0
        first_dt = filings_sorted[0].get("rcept_dt", "")
        last_dt = filings_sorted[-1].get("rcept_dt", "")

        history = []
        peak_stkrt = 0.0
        recent_positive_irds = False  # 최근 90일 내 stkrt_irds > 0 보고
        for f in filings_sorted:
            try:
                v = float((f.get("stkrt") or "0").replace(",", ""))
                irds = float((f.get("stkrt_irds") or "0").replace(",", ""))
            except (ValueError, AttributeError):
                v, irds = 0.0, 0.0
            f_date = f.get("rcept_dt", "")
            history.append({"rcept_dt": f_date, "stkrt": v, "stkrt_irds": irds})
            peak_stkrt = max(peak_stkrt, v)
            if f_date >= one_year_ago:
                total_irds += irds
            if f_date >= ninety_days_ago and irds > 0:
                recent_positive_irds = True

        # 공백 후 재등장: 시계열 안에 보고 간격 ≥ 180일이 있고, 마지막 보고가 1년 내
        gap_then_return = False
        if len(filings_sorted) >= 2 and last_dt >= one_year_ago:
            try:
                for i in range(1, len(filings_sorted)):
                    prev = datetime.strptime(filings_sorted[i - 1].get("rcept_dt", ""), "%Y-%m-%d")
                    curr = datetime.strptime(filings_sorted[i].get("rcept_dt", ""), "%Y-%m-%d")
                    if (curr - prev).days >= 180 and curr.strftime("%Y-%m-%d") >= one_year_ago:
                        gap_then_return = True
                        break
            except ValueError:
                pass

        is_active = current_stkrt >= 5.0
        is_strict_new_1y = first_dt >= one_year_ago and is_active
        is_recent_buyer_90d = recent_positive_irds and is_active
        is_returning_after_gap = gap_then_return and is_active

        is_eligible_cat = category in ("korean_am", "global_am", "pension")
        is_new_or_increasing_1y = is_eligible_cat and (
            is_strict_new_1y or is_recent_buyer_90d or is_returning_after_gap
        )

        # 이탈: 한때 5%+ 였는데 현재 5% 미만 (마지막 보고일이 1년 내)
        is_exit_1y = (
            not is_active
            and peak_stkrt >= 5.0
            and last_dt >= one_year_ago
        )

        if is_active:
            if category == "korean_am":
                korean_am_count += 1
            elif category == "global_am":
                global_am_count += 1
            elif category == "pension":
                pension_count += 1

        if is_new_or_increasing_1y:
            # 라벨 결정 (우선순위: strict > returning > recent_buyer)
            if is_strict_new_1y:
                label = "strict_new"
                strict_new_count += 1
            elif is_returning_after_gap:
                label = "returning"
                returning_count += 1
            else:
                label = "recent_buyer"
                recent_buyer_count += 1
            new_or_increasing.append({
                "name": name,
                "category": category,
                "label": label,
                "first_rcept_dt": first_dt,
                "current_stkrt": current_stkrt,
            })

        if is_exit_1y and is_eligible_cat:
            exits.append({
                "name": name,
                "category": category,
                "peak_stkrt": peak_stkrt,
                "current_stkrt": current_stkrt,
                "last_rcept_dt": last_dt,
            })

        reporters.append({
            "name": name,
            "category": category,
            "current_stkrt": current_stkrt,
            "peak_stkrt": peak_stkrt,
            "first_rcept_dt": first_dt,
            "last_rcept_dt": last_dt,
            "filings": len(filings_sorted),
            "is_active": is_active,
            "is_strict_new_1y": is_strict_new_1y,
            "is_recent_buyer_90d": is_recent_buyer_90d,
            "is_returning_after_gap": is_returning_after_gap,
            "is_new_or_increasing_1y": is_new_or_increasing_1y,
            "is_exit_1y": is_exit_1y,
            "stkrt_history": history,
        })

    reporters.sort(key=lambda r: (not r["is_active"], -r["current_stkrt"]))

    return {
        "reporters": reporters,
        "summary": {
            "korean_am_count": korean_am_count,
            "global_am_count": global_am_count,
            "pension_count": pension_count,
            "new_or_increasing_1y": new_or_increasing,
            "strict_new_count": strict_new_count,
            "recent_buyer_count": recent_buyer_count,
            "returning_count": returning_count,
            "exits_1y": exits,
            "total_stkrt_change_1y_pct": round(total_irds, 2),
            "any_institutional": (korean_am_count + global_am_count + pension_count) > 0,
        },
    }


# ─── 네이버 기관 매매 ───────────────────────────────────────────

FRGN_URL = "https://finance.naver.com/item/frgn.nhn?code={code}&page={page}"
NAVER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


def _parse_signed_int(raw: str) -> int | None:
    cleaned = raw.replace(",", "").replace(" ", "")
    if not re.match(r"^[+-]?\d+$", cleaned):
        return None
    return int(cleaned)


def fetch_naver_org_flow(code: str, pages: int = 3, sleep_ms: int = 300) -> list[dict]:
    """finance.naver.com /item/frgn.nhn → 일별 기관·외인 순매매.

    pages=3 약 60영업일, pages=12 약 1년.
    Returns: [{"date","close","org_net","fgn_net"}, ...] 최신→과거
    """
    rows: list[dict] = []
    seen: set[str] = set()
    for page in range(1, pages + 1):
        url = FRGN_URL.format(code=code, page=page)
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": NAVER_UA, "Referer": "https://finance.naver.com/"},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read()
        except (urllib.error.URLError, urllib.error.HTTPError):
            break
        html = raw.decode("euc-kr", errors="replace")

        for m in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", html):
            cell_text = re.sub(r"<[^>]+>", "|", m.group(1))
            cell_text = cell_text.replace("&nbsp;", " ")
            cell_text = re.sub(r"[\s ]+", " ", cell_text)
            cell_text = re.sub(r"\|+", "|", cell_text).strip("|").strip()
            date_m = re.search(r"(\d{4}\.\d{2}\.\d{2})", cell_text)
            if not date_m:
                continue
            parts = [p.strip() for p in cell_text.split("|") if p.strip()]
            if len(parts) < 7:
                continue
            int_vals: list[int] = []
            for p in parts[1:]:
                v = _parse_signed_int(p)
                if v is not None:
                    int_vals.append(v)
            # int_vals: [종가, 등락폭, 거래량, 기관, 외인, 보유주식수]
            if len(int_vals) < 5:
                continue
            fgn_net = int_vals[-2]
            org_net = int_vals[-3]
            close = int_vals[0]
            iso_date = date_m.group(1).replace(".", "-")
            if iso_date in seen:
                continue
            seen.add(iso_date)
            rows.append({
                "date": iso_date,
                "close": close,
                "org_net": org_net,
                "fgn_net": fgn_net,
            })
        time.sleep(sleep_ms / 1000)
    return sorted(rows, key=lambda x: x["date"], reverse=True)


def analyze_org_flow(rows: list[dict]) -> dict:
    """기관 매매 누적 분석. 60일 / 직전 분기(60일) / 그 전 분기(60~120일) 비교까지.

    Returns:
      {
        "days_covered", "first_date", "last_date",
        "cum_60d",         # 최근 60영업일 누적
        "cum_prev_60d",    # 그 전 60영업일 누적 (60~120일)
        "trend_60d",       # "up"|"flat"|"down"
        "trend_qoq",       # 직전 분기 vs 그 전 분기: "improving"|"flat"|"deteriorating"
        "is_outflow",      # cum_60d < 0
        "is_consistently_declining",  # 직전 분기 < 그 전 분기 < 0
        "is_sharp_drop_qoq", # 직전 분기가 그 전 분기 대비 큰 하락
      }
    """
    if not rows:
        return {
            "days_covered": 0,
            "first_date": None,
            "last_date": None,
            "cum_60d": 0,
            "cum_prev_60d": 0,
            "trend_60d": "flat",
            "trend_qoq": "flat",
            "is_outflow": False,
            "is_consistently_declining": False,
            "is_sharp_drop_qoq": False,
        }
    rows_sorted = sorted(rows, key=lambda x: x["date"], reverse=True)
    recent = rows_sorted[:60]
    prev = rows_sorted[60:120]
    cum_60 = sum(r["org_net"] for r in recent)
    cum_prev = sum(r["org_net"] for r in prev)

    trend_60d = "up" if cum_60 > 0 else "down" if cum_60 < 0 else "flat"

    # qoq: 직전 분기 vs 그 전 분기
    if cum_prev == 0:
        trend_qoq = "flat"
    else:
        delta = cum_60 - cum_prev
        if abs(delta) < abs(cum_prev) * 0.1:
            trend_qoq = "flat"
        elif delta > 0:
            trend_qoq = "improving"
        else:
            trend_qoq = "deteriorating"

    is_outflow = cum_60 < 0
    # 두 분기 연속 음수면 꾸준한 이탈 (악화 조건 제거 — 책 기준: 한 분기 매도여도 경계)
    is_consistently_declining = cum_60 < 0 and cum_prev < 0
    # 큰 하락: 직전 분기가 음수이고, 그 전 분기 대비 절댓값 50% 이상 더 하락
    is_sharp_drop = (
        cum_60 < 0
        and (cum_prev >= 0 or cum_60 < cum_prev * 1.5)
    )

    return {
        "days_covered": len(rows_sorted),
        "first_date": rows_sorted[-1]["date"],
        "last_date": rows_sorted[0]["date"],
        "cum_60d": cum_60,
        "cum_prev_60d": cum_prev,
        "trend_60d": trend_60d,
        "trend_qoq": trend_qoq,
        "is_outflow": is_outflow,
        "is_consistently_declining": is_consistently_declining,
        "is_sharp_drop_qoq": is_sharp_drop,
    }


# ─── 페이지 노출 게이트 ──────────────────────────────────────

def evaluate_i(majorstock_analysis: dict, org_flow_analysis: dict) -> dict:
    """페이지 노출 게이트 (책 기준: 기관 이탈 종목 제외).

    제외 조건 (OR — 하나라도 해당하면 제외, UI 에서 회색 음영 처리):
      G1. 기관 매매 꾸준한 이탈 — 직전 60일 음수 AND 그 전 60일도 음수
      G2. 5%룰 지분 1년 감소 + 종합 신규 시그널 부재 — total_stkrt_change_1y_pct < -2.0%p AND
          new_or_increasing_1y(strict 신규+추가 매수+공백 후 재등장) 0건
      G3. 5%룰 이탈 다수 — 1년 내 5%→미만 이탈 보고자 ≥ 2건
      G4. 기관 뒷받침 완전 부재 — 5%+ 기관 0개 AND 60일 매매 ≤ 0 AND 종합 신규 시그널 0건

    경고 시그널 (제외는 아니지만 표시):
      C1. 1년간 종합 신규 시그널 부재 (책 기준: 신규 편입이 가장 중요)
      C2. 직전 분기 큰 하락
      C3. 분기 추세 악화
      C4. 5%룰 기관 부재 + 60일 이탈

    Returns:
      {
        "passes_i": bool,
        "exclusion_reasons": [...],
        "warning_signals": [...],
      }
    """
    exclusions: list[str] = []
    warnings: list[str] = []

    s = majorstock_analysis["summary"]
    o = org_flow_analysis

    new_or_inc_count = len(s.get("new_or_increasing_1y", []))

    # G1: 기관 매매 꾸준한 이탈 (두 분기 연속 음수)
    if o["is_consistently_declining"]:
        exclusions.append(
            f"기관 매매 두 분기 연속 이탈 (직전 60일 {o['cum_60d']:+,}주, 그 전 60일 {o['cum_prev_60d']:+,}주)"
        )

    # G2: 5%룰 지분 1년 감소 + 종합 신규 시그널 부재
    if s["total_stkrt_change_1y_pct"] < -2.0 and new_or_inc_count == 0:
        exclusions.append(
            f"5%룰 지분 1년 감소 {s['total_stkrt_change_1y_pct']:+.2f}%p + 신규/추가매수/재등장 0건"
        )

    # G3: 5%룰 이탈 다수
    if len(s["exits_1y"]) >= 2:
        names = ", ".join(e["name"][:20] for e in s["exits_1y"][:3])
        exclusions.append(f"1년 내 5% 이탈 {len(s['exits_1y'])}건 ({names})")

    # G4: 기관 뒷받침 완전 부재 (양·추세·신규 모두 죽음)
    if (
        not s["any_institutional"]
        and o["cum_60d"] <= 0
        and new_or_inc_count == 0
    ):
        exclusions.append(
            "기관 뒷받침 완전 부재 (5%+ 기관 0 + 60일 매매 ≤ 0 + 신규 시그널 0)"
        )

    # C1: 종합 신규 시그널 0건 경고 (책 기준 신규 편입 강조)
    if new_or_inc_count == 0:
        warnings.append("1년간 신규 진입/추가 매수/재등장 시그널 0건")

    # C2: 직전 분기 큰 하락
    if o["is_sharp_drop_qoq"] and not o["is_consistently_declining"]:
        warnings.append(
            f"직전 분기 큰 하락 (이번 {o['cum_60d']:+,}주, 직전 {o['cum_prev_60d']:+,}주)"
        )

    # C3: 분기 추세 악화
    if o["trend_qoq"] == "deteriorating":
        warnings.append("분기 추세 악화")

    # C4: 5%룰 기관 부재 + 60일 이탈
    if not s["any_institutional"] and o["is_outflow"]:
        warnings.append("5%룰 기관 부재 + 기관 매매 이탈")

    return {
        "passes_i": len(exclusions) == 0,
        "exclusion_reasons": exclusions,
        "warning_signals": warnings,
    }


# ─── 운용사 등급 (fundguide 수동 입력) ─────────────────────────

def assign_relative_grades(rankings_raw: list[dict]) -> list[dict]:
    """fundguide Top 10 수익률 → a+/a/a- 3등급 상대평가.

    Top 10 한정이라 b/c 등급 없음. 단순 순위 기반 3/4/3 분할:
      rank 1-3 → a+
      rank 4-7 → a
      rank 8-10 → a-

    Args:
      rankings_raw: [{"rank": 1, "manager": "...", "return_pct": 12.3}, ...]
    Returns:
      [{"manager": "...", "rank": 1, "return_pct": 12.3, "grade": "a+"}, ...]
    """
    if not rankings_raw:
        return []
    sorted_raw = sorted(rankings_raw, key=lambda x: x.get("rank", 999))
    out = []
    for entry in sorted_raw:
        rank = entry.get("rank", 999)
        if rank <= 3:
            grade = "a+"
        elif rank <= 7:
            grade = "a"
        elif rank <= 10:
            grade = "a-"
        else:
            grade = "unrated"
        out.append({
            "manager": entry.get("manager", ""),
            "rank": rank,
            "return_pct": entry.get("return_pct"),
            "grade": grade,
        })
    return out


def consolidate_quarterly_to_annual(quarterly: dict[str, list[dict]]) -> list[dict]:
    """4분기 raw Top 10 → 1년 환산 종합 등급.

    로직:
      1. 각 분기별로 a+/a/a- 부여 (assign_relative_grades) — 분기 점수 a+=3, a=2, a-=1, 미등장=0
      2. 운용사별 평균 점수 = Σ(등장 분기 점수) / 등장 분기 수
      3. 가중 점수 = 평균 점수 × (등장 분기 수 / 4) — 4분기 모두 등장 운용사 우선
      4. 가중 점수 내림차순 정렬 → 상위 10 → a+/a/a- 재부여

    Args:
      quarterly: {"Q1": [raw...], "Q2": [...], "Q3": [...], "Q4": [...]}
    Returns:
      [{"manager", "grade", "appearances", "avg_return_pct", "weighted_score", "quarterly_detail"}, ...]
    """
    if not quarterly:
        return []
    # 분기별 등급 부여
    score_map = {"a+": 3, "a": 2, "a-": 1}
    manager_data: dict[str, dict] = {}
    for q_key, raw in quarterly.items():
        graded = assign_relative_grades(raw)
        for g in graded:
            mgr = g["manager"]
            entry = manager_data.setdefault(mgr, {
                "manager": mgr,
                "quarterly_detail": [],
                "returns": [],
            })
            entry["quarterly_detail"].append({
                "quarter": q_key,
                "rank": g["rank"],
                "return_pct": g["return_pct"],
                "grade": g["grade"],
                "score": score_map.get(g["grade"], 0),
            })
            entry["returns"].append(g["return_pct"] or 0)

    # 평균 점수 + 가중 점수
    consolidated = []
    for mgr, entry in manager_data.items():
        details = entry["quarterly_detail"]
        appearances = len(details)
        avg_score = sum(d["score"] for d in details) / appearances if appearances else 0
        weighted = avg_score * (appearances / 4)
        avg_return = sum(entry["returns"]) / appearances if appearances else 0
        consolidated.append({
            "manager": mgr,
            "appearances": appearances,
            "avg_return_pct": round(avg_return, 2),
            "avg_quarterly_score": round(avg_score, 3),
            "weighted_score": round(weighted, 3),
            "quarterly_detail": details,
        })

    # 가중 점수 → 평균 수익률 내림차순 정렬, 상위 10
    consolidated.sort(key=lambda x: (-x["weighted_score"], -x["avg_return_pct"]))
    top10 = consolidated[:10]

    # 최종 a+/a/a- 부여 (3/4/3 분할)
    for i, m in enumerate(top10, start=1):
        if i <= 3:
            m["grade"] = "a+"
        elif i <= 7:
            m["grade"] = "a"
        else:
            m["grade"] = "a-"
        m["consolidated_rank"] = i

    return top10


def load_fund_rankings(json_path: Path | str) -> dict:
    """fund-rankings.json 로드 + 운용사명 → 등급 매핑 헬퍼 추가.

    Returns:
      {
        "snapshot_date": ...,
        "rankings": {...},
        "grade_lookup_1y": {"미래에셋자산운용": "a+", ...},
        "grade_lookup_3y": {...},
      }
    Empty/missing 시 빈 lookup 반환 (에러 X).
    """
    p = Path(json_path)
    empty = {
        "snapshot_date": None,
        "rankings": {"1year": {"raw": [], "computed": {}}, "3year": {"raw": [], "computed": {}}},
        "grade_lookup_1y": {},
        "grade_lookup_3y": {},
    }
    if not p.exists():
        return empty
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return empty

    out = {
        "snapshot_date": data.get("snapshot_date"),
        "rankings": data.get("rankings", empty["rankings"]),
        "grade_lookup_1y": {},
        "grade_lookup_3y": {},
    }

    for key, alias in (("1year", "grade_lookup_1y"), ("3year", "grade_lookup_3y")):
        section = data.get("rankings", {}).get(key, {})
        managers = section.get("computed", {}).get("managers", []) or []
        out[alias] = {m["manager"]: m.get("grade", "unrated") for m in managers if m.get("manager")}

    return out


def normalize_manager_name(name: str) -> str:
    """운용사 표기 정규화 — `미래에셋자산운용(주)` / `미래에셋자산운용` 통합 등.

    공백 제거, 괄호 안 (주)/(유)/Inc/Ltd/Co 등 부가어 제거.
    """
    if not name:
        return ""
    s = name.strip()
    # 한국 법인 부가어
    s = re.sub(r"\((주|유)\)", "", s)
    s = re.sub(r"\((Inc|Ltd|Co|LLC|LP)\.?\)", "", s, flags=re.IGNORECASE)
    # 끝의 (주) 같은 패턴
    s = re.sub(r"\(주\)$", "", s)
    s = s.strip().replace(" ", "")
    return s


def lookup_manager_grade(reporter_name: str, fund_rankings: dict) -> dict:
    """보고자 이름에 대해 1년/3년 등급 조회. 매칭 안 되면 unrated.

    Returns: {"grade_1y": "a+"|"unrated", "grade_3y": ...}
    """
    norm = normalize_manager_name(reporter_name)
    # 매핑 lookup (정규화된 매니저명으로 키 비교)
    g1y_lookup = {normalize_manager_name(k): v for k, v in fund_rankings.get("grade_lookup_1y", {}).items()}
    g3y_lookup = {normalize_manager_name(k): v for k, v in fund_rankings.get("grade_lookup_3y", {}).items()}
    return {
        "grade_1y": g1y_lookup.get(norm, "unrated"),
        "grade_3y": g3y_lookup.get(norm, "unrated"),
    }

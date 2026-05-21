"""경영진 품질 자동 분류 — DART 공시 시그널 수집 + 규칙 기반 점수화.

설계 명세: research/oneil-model-book/MANAGEMENT_AUTO_CLASSIFY.md

흐름:
  fetch_management_signals(corp_code, years=5)
    → DART list.json 호출, report_nm 키워드 매칭으로 시그널 분류·증거 수집
  classify_management(signals)
    → 가중치 합산 → excellent / professional / poor
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .fetch import dart_get


# ── 시그널 가중치 (문서 MANAGEMENT_AUTO_CLASSIFY.md 와 동기화) ──

W_BUYBACK_CANCEL = 3.0       # 자사주 소각 1건당 +3
W_BUYBACK_ACQUIRE = 1.0      # 자사주 매입 1건당 +1
W_BUYBACK_ACQUIRE_CAP = 3.0  # 매입 가산점 캡
W_RIGHTS_ISSUE = -2.0        # 유상증자 1건당 -2
W_CB_BW = -1.5               # CB / BW 1건당 -1.5
W_CEO_CHURN_PENALTY = -3.0   # 5년 3회+ CEO 교체 시 -3
W_CEO_CHURN_THRESHOLD = 3    # 임계값
W_AUDIT_ISSUE_PENALTY = -10.0  # 감사 사고 1건+ 즉시 -10 (사실상 poor 확정)

TIER_EXCELLENT_MIN = 3.0
TIER_POOR_MAX = -2.0


# ── 키워드 매칭 ──

def _matches_buyback_cancel(report_nm: str) -> bool:
    """자사주 소각 — '자기주식 소각', '자사주 소각'."""
    if "소각" not in report_nm:
        return False
    return "자기주식" in report_nm or "자사주" in report_nm


def _matches_buyback_acquire(report_nm: str) -> bool:
    """자사주 매입 — '자기주식 취득', '자사주 취득'. '처분'·'소각' 제외."""
    if "처분" in report_nm or "소각" in report_nm:
        return False
    if "취득" not in report_nm:
        return False
    return "자기주식" in report_nm or "자사주" in report_nm


def _matches_rights_issue(report_nm: str) -> bool:
    """유상증자 — '유상증자결정'. 무상증자 제외."""
    return "유상증자" in report_nm


def _matches_cb(report_nm: str) -> bool:
    """전환사채 — '전환사채권발행결정'."""
    return "전환사채" in report_nm and "발행" in report_nm


def _matches_bw(report_nm: str) -> bool:
    """신주인수권부사채 — '신주인수권부사채권발행결정'."""
    return "신주인수권부사채" in report_nm and "발행" in report_nm


def _matches_ceo_change(report_nm: str) -> bool:
    """대표이사 변경 — '대표이사 변경'."""
    if "대표이사" not in report_nm:
        return False
    return "변경" in report_nm or "선임" in report_nm


def _matches_audit_issue(report_nm: str) -> bool:
    """감사 사고 — 의견거절·감사범위제한·회계처리기준위반·횡령·배임 등."""
    audit_kw = [
        "의견거절",
        "감사범위제한",
        "회계처리기준위반",
        "회계처리기준 위반",
        "횡령",
        "배임",
        "상장폐지",
    ]
    return any(kw in report_nm for kw in audit_kw)


# ── DART 공시 수집 ──

def fetch_disclosure_list(corp_code: str, bgn_de: str, end_de: str, max_pages: int = 10) -> list[dict[str, Any]]:
    """corp_code 의 [bgn_de, end_de] 기간 모든 공시 list. 페이지네이션 자동.

    bgn_de/end_de: 'YYYYMMDD'.
    """
    all_items: list[dict[str, Any]] = []
    for page_no in range(1, max_pages + 1):
        items = dart_get("list", {
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_no": str(page_no),
            "page_count": "100",
        })
        if not items:
            break
        all_items.extend(items)
        if len(items) < 100:
            break
    return all_items


def fetch_management_signals(corp_code: str, years: int = 5) -> dict[str, Any]:
    """corp_code 의 최근 N년 DART 공시에서 경영진 시그널 추출.

    Returns:
      {
        "buyback_cancel": [{"date": "20231115", "title": "..."}, ...],
        "buyback_acquire": [...],
        "rights_issue": [...],
        "cb_bw": [...],
        "ceo_change": [...],
        "audit_issue": [...],
      }
    """
    today = datetime.now()
    bgn = (today - timedelta(days=365 * years)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    items = fetch_disclosure_list(corp_code, bgn, end)

    signals: dict[str, list[dict[str, str]]] = {
        "buyback_cancel": [],
        "buyback_acquire": [],
        "rights_issue": [],
        "cb_bw": [],
        "ceo_change": [],
        "audit_issue": [],
    }

    for it in items:
        nm = it.get("report_nm", "")
        dt = it.get("rcept_dt", "")
        ev = {"date": dt, "title": nm.strip()}

        # 정정 공시는 원본과 동일 키워드를 포함하므로 별도 처리 안 함 (재집계).
        # 실제 본문 차이는 v2 에서 보강.
        if _matches_audit_issue(nm):
            signals["audit_issue"].append(ev)
        if _matches_buyback_cancel(nm):
            signals["buyback_cancel"].append(ev)
        elif _matches_buyback_acquire(nm):
            signals["buyback_acquire"].append(ev)
        if _matches_rights_issue(nm):
            signals["rights_issue"].append(ev)
        if _matches_cb(nm) or _matches_bw(nm):
            signals["cb_bw"].append(ev)
        if _matches_ceo_change(nm):
            signals["ceo_change"].append(ev)

    return signals


# ── 규칙 기반 분류 ──

def classify_management(signals: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    """시그널 → 가중치 합산 → 분류.

    Returns:
      {
        "quality": "excellent" | "professional" | "poor",
        "total_score": float,
        "score_breakdown": {...},  # 시그널별 점수 영향
        "signals": {...},          # 시그널별 카운트
        "evidence": [...],         # 점수에 영향 준 공시 목록 (최대 20건)
      }
    """
    audit_n = len(signals.get("audit_issue", []))
    cancel_n = len(signals.get("buyback_cancel", []))
    acquire_n = len(signals.get("buyback_acquire", []))
    rights_n = len(signals.get("rights_issue", []))
    cb_bw_n = len(signals.get("cb_bw", []))
    ceo_n = len(signals.get("ceo_change", []))

    # 점수 계산
    score_cancel = cancel_n * W_BUYBACK_CANCEL
    score_acquire = min(acquire_n * W_BUYBACK_ACQUIRE, W_BUYBACK_ACQUIRE_CAP)
    score_rights = rights_n * W_RIGHTS_ISSUE
    score_cb_bw = cb_bw_n * W_CB_BW
    score_ceo = W_CEO_CHURN_PENALTY if ceo_n >= W_CEO_CHURN_THRESHOLD else 0.0
    score_audit = W_AUDIT_ISSUE_PENALTY if audit_n >= 1 else 0.0

    total = score_cancel + score_acquire + score_rights + score_cb_bw + score_ceo + score_audit

    # 분류
    if audit_n >= 1:
        quality = "poor"  # 감사 사고 즉시 강등
    elif total >= TIER_EXCELLENT_MIN:
        quality = "excellent"
    elif total <= TIER_POOR_MAX:
        quality = "poor"
    else:
        quality = "professional"

    # 증거 모음 (대표 공시, 최대 20건)
    evidence: list[dict[str, str]] = []
    for cat, weight_str in [
        ("audit_issue", f"{W_AUDIT_ISSUE_PENALTY:+.1f} (감사 사고)"),
        ("buyback_cancel", f"{W_BUYBACK_CANCEL:+.1f} (자사주 소각)"),
        ("buyback_acquire", f"{W_BUYBACK_ACQUIRE:+.1f} (자사주 매입)"),
        ("rights_issue", f"{W_RIGHTS_ISSUE:+.1f} (유상증자)"),
        ("cb_bw", f"{W_CB_BW:+.1f} (CB/BW)"),
        ("ceo_change", "ceo change (cumulative)"),
    ]:
        for ev in signals.get(cat, [])[:5]:
            evidence.append({"date": ev["date"], "title": ev["title"], "impact": weight_str, "category": cat})

    return {
        "quality": quality,
        "total_score": round(total, 2),
        "score_breakdown": {
            "buyback_cancel": round(score_cancel, 2),
            "buyback_acquire": round(score_acquire, 2),
            "rights_issue": round(score_rights, 2),
            "cb_bw": round(score_cb_bw, 2),
            "ceo_change": round(score_ceo, 2),
            "audit_issue": round(score_audit, 2),
        },
        "signals": {
            "buyback_cancel_count": cancel_n,
            "buyback_acquire_count": acquire_n,
            "rights_issue_count": rights_n,
            "cb_bw_count": cb_bw_n,
            "ceo_change_count": ceo_n,
            "audit_issue_count": audit_n,
        },
        "evidence": evidence[:20],
    }

"""HPSP(403870) 단독 CAN SLIM 점수 평가 (v2 점수체계).

기존 `_eval_single_canslim.py` 가 구버전 evaluate_a_detailed API 호출로 깨져
있어 v2 (evaluate_a_v2 + score_s_v2) 를 직접 호출하는 일회용 스크립트.

산정:
  C 100점: C-file `c_score` 그대로
  A  50점: evaluate_a_v2 (DART/Yahoo 원본 호출)
  N  30점: 수동 리서치 필요 (build_n_v2.py 하드코딩 사전) — 미산정 0점
  S  60점: score_s_v2 (sr_entry 없음 → 기본 25점 + 부채비율 점수)
  L  99점: C-screener 가 산출해 둔 RS (C-file 의 L.detail) — KOSDAQ 종목은
           fetch_l_rs.py 의 L-file (KOSPI 300 모집단) 에 들어가지 않음.
  I/M    : 미산정.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_dotenv() -> None:
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

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from canslim_lib.fetch import (
    DART_API,
    UA,
    dart_get,
    fetch_annual,
    fetch_dart_quarterly_eps_history,
    fetch_quarter,
    get_row_values,
    load_corp_code_map,
    merge_naver_dart_quarters,
    resolve_corp_code,
)
from canslim_lib.criteria_a import evaluate_a_v2
from canslim_lib.criteria_s_v2 import score_s_v2

TARGET_CODE = sys.argv[1] if len(sys.argv) > 1 else "403870"
TARGET_NAME = sys.argv[2] if len(sys.argv) > 2 else "HPSP"
TARGET_MARKET = sys.argv[3] if len(sys.argv) > 3 else "KOSDAQ"

C_JSON = ROOT / "public" / "data" / "can-slim-candidates.json"
SR_JSON = ROOT / "public" / "data" / "shareholder-returns.json"
CURRENT_YEAR = datetime.now().year


def fetch_dart_annual_eps(corp_code: str, year: int):
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": "11011", "fs_div": fs_div,
        })
        if not items:
            continue
        for it in items:
            if it.get("sj_div") not in ("IS", "CIS"):
                continue
            name = (it.get("account_nm") or "").replace(" ", "")
            if any(k in name for k in ("기본주당이익", "기본주당순이익", "기본및희석주당이익", "주당순이익", "기본주당손익")):
                raw = it.get("thstrm_amount")
                if raw and raw not in ("-", ""):
                    try:
                        return float(str(raw).replace(",", ""))
                    except (ValueError, TypeError):
                        continue
    return None


def fetch_dart_annual_pretax_margin(corp_code: str, year: int):
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": "11011", "fs_div": fs_div,
        })
        if not items:
            continue
        sales_val = None
        pretax_val = None
        for it in items:
            if it.get("sj_div") not in ("IS", "CIS"):
                continue
            nm = (it.get("account_nm") or "").replace(" ", "")
            raw = it.get("thstrm_amount")
            if not raw or raw in ("-", ""):
                continue
            try:
                v = float(str(raw).replace(",", ""))
            except (ValueError, TypeError):
                continue
            if sales_val is None and any(k in nm for k in ("매출액", "수익(매출액)", "영업수익")):
                sales_val = v
            if pretax_val is None and any(k in nm for k in ("법인세비용차감전순이익", "법인세비용차감전이익", "법인세차감전순이익", "법인세차감전이익", "법인세차감전계속사업이익")):
                pretax_val = v
            if sales_val and pretax_val:
                break
        if sales_val and pretax_val and sales_val > 0:
            return round(pretax_val / sales_val * 100, 2)
    return None


def fetch_dart_industry_code(corp_code: str):
    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        return None
    url = f"{DART_API}/company.json?crtfc_key={api_key}&corp_code={corp_code}"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError, TimeoutError):
        return None
    if data.get("status") != "000":
        return None
    return data.get("induty_code") or None


def fetch_dart_debt_ratio(corp_code: str, year: int) -> float | None:
    """직전 사업연도 부채비율 (DART fnlttSinglAcntAll, 부채총계/자본총계)."""
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": "11011", "fs_div": fs_div,
        })
        if not items:
            continue
        debt = None
        equity = None
        for it in items:
            if it.get("sj_div") != "BS":
                continue
            nm = (it.get("account_nm") or "").replace(" ", "")
            raw = it.get("thstrm_amount")
            if not raw or raw in ("-", ""):
                continue
            try:
                v = float(str(raw).replace(",", ""))
            except (ValueError, TypeError):
                continue
            if debt is None and nm == "부채총계":
                debt = v
            if equity is None and nm == "자본총계":
                equity = v
            if debt is not None and equity is not None:
                break
        if debt is not None and equity is not None and equity > 0:
            return round(debt / equity * 100, 2)
    return None


def collect_quarterly_eps_tuples(code, corp_code):
    qtr = fetch_quarter(code)
    quarter_eps = get_row_values(qtr, "EPS") if qtr else []
    if not corp_code:
        return quarter_eps
    if quarter_eps:
        latest_year = int(quarter_eps[-1][0][:4]) if quarter_eps[-1][0][:4].isdigit() else datetime.now().year
    else:
        latest_year = datetime.now().year
    dart_combined = []
    for delta in range(0, 5):
        year = latest_year - delta
        items = fetch_dart_quarterly_eps_history(corp_code, year)
        if items:
            dart_combined.extend(items)
        time.sleep(0.1)
    if dart_combined:
        quarter_eps = merge_naver_dart_quarters(quarter_eps, dart_combined)
    return quarter_eps


def fetch_annual_eps_extended(code, corp_code):
    ann = fetch_annual(code)
    annual_eps = get_row_values(ann, "EPS") if ann else []
    if len(annual_eps) >= 6 or not corp_code:
        return annual_eps
    have_years = {k[:4] for k, _ in annual_eps if len(k) >= 4 and k[:4].isdigit()}
    earliest_year = min(int(y) for y in have_years) if have_years else datetime.now().year
    augment = []
    for delta in range(1, 5):
        year = earliest_year - delta
        if str(year) in have_years:
            continue
        eps_val = fetch_dart_annual_eps(corp_code, year)
        if eps_val is not None:
            augment.append((f"{year}12", round(eps_val, 2)))
        time.sleep(0.15)
    return sorted(annual_eps + augment, key=lambda x: x[0])


def find_c_entry(code: str) -> dict | None:
    data = json.loads(C_JSON.read_text(encoding="utf-8"))
    for c in data.get("candidates", []):
        if c["code"] == code:
            return c
    return None


def load_sr_entry(code: str) -> dict | None:
    if not SR_JSON.exists():
        return None
    data = json.loads(SR_JSON.read_text(encoding="utf-8"))
    for s in data.get("stocks", []):
        if s.get("code") == code:
            return s
    return None


def main() -> None:
    print(f"📊 {TARGET_NAME} ({TARGET_CODE}) CAN SLIM 단독 평가 — v2", file=sys.stderr)

    c_entry = find_c_entry(TARGET_CODE)
    if not c_entry:
        print(f"❌ C JSON에 {TARGET_CODE} 없음", file=sys.stderr)
        sys.exit(1)

    c_cr = c_entry["criteria"]["C"]
    print(f"  C 결과: pass={c_cr['pass']}, YoY={c_cr.get('yoy_pct')}%, 매출YoY={c_cr.get('sales_yoy_pct')}%", file=sys.stderr)
    print(f"  c_score={c_entry.get('c_score')}", file=sys.stderr)

    corp_map = load_corp_code_map()
    corp_code, _ = resolve_corp_code(TARGET_CODE, corp_map)
    print(f"  corp_code={corp_code}", file=sys.stderr)

    # ── A v2 평가 ──
    print("\n[A] 평가 중…", file=sys.stderr)
    ann = fetch_annual(TARGET_CODE)
    annual_eps = fetch_annual_eps_extended(TARGET_CODE, corp_code)
    annual_roe = get_row_values(ann, "ROE") if ann else []
    induty_code = fetch_dart_industry_code(corp_code) if corp_code else None
    pretax_margin = None
    if corp_code and annual_eps:
        latest_year_str = annual_eps[-1][0][:4] if annual_eps[-1][0][:4].isdigit() else None
        if latest_year_str:
            pretax_margin = fetch_dart_annual_pretax_margin(corp_code, int(latest_year_str))

    quarterly_eps_tuples = collect_quarterly_eps_tuples(TARGET_CODE, corp_code)
    prelim_quarter = c_cr.get("latest_quarter")
    prelim_eps_value = c_cr.get("latest_eps")
    prelim_is_p = c_cr.get("latest_is_preliminary", False)
    if prelim_is_p and prelim_quarter and prelim_eps_value is not None:
        if not any(p == prelim_quarter for p, _ in quarterly_eps_tuples):
            quarterly_eps_tuples = sorted(
                list(quarterly_eps_tuples) + [(prelim_quarter, float(prelim_eps_value))]
            )
    quarterly_eps_for_stability = [v for _, v in quarterly_eps_tuples]

    annual_eps_for_a = list(annual_eps)
    annual_last_period = annual_eps[-1][0] if annual_eps else "000000"
    ttm_eps = None
    ttm_period = None
    if len(quarterly_eps_tuples) >= 4:
        ttm_eps = round(sum(v for _, v in quarterly_eps_tuples[-4:]), 2)
        ttm_period = quarterly_eps_tuples[-1][0]
        if ttm_period > annual_last_period:
            annual_eps_for_a = list(annual_eps) + [(f"TTM_{ttm_period}", ttm_eps)]

    latest_qy = c_cr.get("yoy_pct")
    eps_yoy_history_raw = c_cr.get("eps_yoy_history") or []
    quarterly_eps_yoy_history = [(str(p), float(v)) for p, v in eps_yoy_history_raw]
    sales_yoy_history_raw = c_cr.get("sales_yoy_history") or []
    sales_yoy_history = [(str(p), float(v)) for p, v in sales_yoy_history_raw]

    a_result = evaluate_a_v2(
        annual_eps=annual_eps_for_a,
        annual_roe=annual_roe,
        quarterly_eps_yoy_history=quarterly_eps_yoy_history,
        sales_yoy_history=sales_yoy_history,
        latest_quarter_yoy=latest_qy,
        induty_code=induty_code,
        quarterly_eps_for_stability=quarterly_eps_for_stability,
        pretax_margin=pretax_margin,
    )
    a_score = a_result.get("score", 0)
    a_track = a_result.get("track_label", "unclassified")
    a_grade = a_result.get("grade", "—")
    print(f"  → A {a_score}/50 [{a_track}] {a_grade}", file=sys.stderr)
    if a_result.get("fail_reasons"):
        print(f"     사유: {'; '.join(a_result['fail_reasons'])}", file=sys.stderr)

    # ── S v2 평가 ──
    print("\n[S] 평가 중…", file=sys.stderr)
    sr_entry = load_sr_entry(TARGET_CODE)
    debt_ratio = None
    if corp_code:
        # 직전·전전 연도 시도
        for delta in (1, 2):
            debt_ratio = fetch_dart_debt_ratio(corp_code, CURRENT_YEAR - delta)
            if debt_ratio is not None:
                break

    s_result = score_s_v2(
        name=TARGET_NAME,
        induty_code=induty_code,
        sr_entry=sr_entry,
        debt_ratio=debt_ratio,
        current_year=CURRENT_YEAR,
    )
    print(f"  → S {s_result['s_score']}/60 (주주가치 {s_result['shareholder_score']} + 부채 {s_result['debt_score']})", file=sys.stderr)
    print(f"     부채비율: {debt_ratio}% / sr_entry: {'있음' if sr_entry else '없음 (기본 25점)'}", file=sys.stderr)

    # ── L: C-file 의 RS 사용 ──
    import re
    l_value = c_entry["criteria"]["L"].get("value", "") or ""
    rs_match = re.search(r"RS\s+(\d+)", l_value)
    rs_score = int(rs_match.group(1)) if rs_match else 0
    print(f"\n[L] (C-screener 산출): {l_value} → RS={rs_score}", file=sys.stderr)

    # 종합
    c_score = c_entry.get("c_score") or 0
    n_score = 0    # 미산정 (build_n_v2.py 하드코딩 사전 미포함)

    total = c_score + a_score + n_score + s_result["s_score"] + rs_score

    print()
    print("=" * 72)
    print(f"  {TARGET_NAME} ({TARGET_CODE}) — CAN SLIM 종합 점수 [추정]")
    print("=" * 72)
    print(f"  C  : {c_score:>5.1f} / 100   (c_score)")
    print(f"  A  : {a_score:>5} / 50    [{a_track}]")
    print(f"  N  : {n_score:>5} / 30    (미산정 — 수동 리서치 필요)")
    print(f"  S  : {s_result['s_score']:>5} / 60    (주주가치 {s_result['shareholder_score']} + 부채 {s_result['debt_score']})")
    print(f"  L  : {rs_score:>5} / 99    (RS {rs_score})")
    print(f"  I  : {'—':>5} / —     (미산정)")
    print(f"  M  : {'—':>5} / —     (시장 추세 통과)")
    print("-" * 72)
    print(f"  TOTAL: {total:.1f} / 339  ({total/339*100:.1f}%)")
    print()
    print(f"  ※ C-게이트 (`passesCGate`) 미통과로 /stocks/canslim/ranking 페이지에서 노출 안됨")
    print(f"     사유: 매출 YoY {c_cr.get('sales_yoy_pct')}% (<+25% 요건 미달, sales_accel_3q={c_cr.get('sales_accel_3q')})")
    print()


if __name__ == "__main__":
    main()

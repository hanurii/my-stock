"""다종목 CAN SLIM 일괄 평가 (v2). _eval_hpsp.py 의 batch 버전.

사용법:
  python scripts/_eval_batch.py
  python scripts/_eval_batch.py 066570 011070 ...   # 코드만 받기

코드만 받으면 C-file 에서 name/market 자동 lookup.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import concurrent.futures
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

C_JSON = ROOT / "public" / "data" / "can-slim-candidates.json"
SR_JSON = ROOT / "public" / "data" / "shareholder-returns.json"
CURRENT_YEAR = datetime.now().year

# 기본 대상 (사용자 질문 11종목)
DEFAULT_TARGETS = [
    "066570",  # LG전자
    "064400",  # LG씨엔에스
    "011070",  # LG이노텍
    "018260",  # 삼성에스디에스
    "307950",  # 현대오토에버
    "181710",  # NHN
    "003550",  # LG
    "000150",  # 두산
    "035420",  # NAVER
    "034220",  # LG디스플레이
    "012330",  # 현대모비스
]


def fetch_dart_annual_eps(corp_code, year):
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


def fetch_dart_annual_pretax_margin(corp_code, year):
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


def fetch_dart_industry_code(corp_code):
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


def fetch_dart_debt_ratio(corp_code, year):
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
        time.sleep(0.05)
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
        time.sleep(0.1)
    return sorted(annual_eps + augment, key=lambda x: x[0])


def load_c_index() -> dict[str, dict]:
    data = json.loads(C_JSON.read_text(encoding="utf-8"))
    return {c["code"]: c for c in data.get("candidates", [])}


def load_sr_index() -> dict[str, dict]:
    if not SR_JSON.exists():
        return {}
    data = json.loads(SR_JSON.read_text(encoding="utf-8"))
    return {s["code"]: s for s in data.get("stocks", [])}


def evaluate_one(code: str, c_index: dict, sr_index: dict, corp_map: dict) -> dict:
    c_entry = c_index.get(code)
    if not c_entry:
        return {"code": code, "error": "C JSON 미수록"}

    name = c_entry["name"]
    market = c_entry["market"]
    c_cr = c_entry["criteria"]["C"]
    corp_code, _ = resolve_corp_code(code, corp_map)

    # A v2
    ann = fetch_annual(code)
    annual_eps = fetch_annual_eps_extended(code, corp_code)
    annual_roe = get_row_values(ann, "ROE") if ann else []
    induty_code = fetch_dart_industry_code(corp_code) if corp_code else None
    pretax_margin = None
    if corp_code and annual_eps:
        latest_year_str = annual_eps[-1][0][:4] if annual_eps[-1][0][:4].isdigit() else None
        if latest_year_str:
            pretax_margin = fetch_dart_annual_pretax_margin(corp_code, int(latest_year_str))

    quarterly_eps_tuples = collect_quarterly_eps_tuples(code, corp_code)
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
    a_track = a_result.get("track_label", "—")
    a_grade = a_result.get("grade", "—")

    # S v2
    sr_entry = sr_index.get(code)
    debt_ratio = None
    if corp_code:
        for delta in (1, 2):
            debt_ratio = fetch_dart_debt_ratio(corp_code, CURRENT_YEAR - delta)
            if debt_ratio is not None:
                break

    s_result = score_s_v2(
        name=name,
        induty_code=induty_code,
        sr_entry=sr_entry,
        debt_ratio=debt_ratio,
        current_year=CURRENT_YEAR,
    )

    # L from C-file
    l_value = c_entry["criteria"]["L"].get("value", "") or ""
    rs_match = re.search(r"RS\s+(\d+)", l_value)
    rs_score = int(rs_match.group(1)) if rs_match else 0

    c_score = c_entry.get("c_score") or 0
    total = c_score + a_score + 0 + s_result["s_score"] + rs_score

    # C-게이트 통과 여부 (cFilter.ts 와 동일)
    sales_y = c_cr.get("sales_yoy_pct")
    sales_accel = c_cr.get("sales_accel_3q", False)
    sales_accompany = (sales_y is not None and sales_y >= 25) or sales_accel
    q = c_cr.get("eps_accel_quality")
    eps_accel_3q = c_cr.get("eps_accel_3q", False)
    quality_accel = q in ("mild", "strong", "explosive")
    accelerating = eps_accel_3q or quality_accel
    cdq = c_cr.get("consecutive_decline_quarters", 0)
    severe = c_cr.get("severe_decel", False)
    c_gate = (
        latest_qy is not None and latest_qy >= 25
        and sales_accompany and accelerating
        and cdq < 2 and not severe
    )

    return {
        "code": code,
        "name": name,
        "market": market,
        "c_score": c_score,
        "a_score": a_score,
        "a_track": a_track,
        "a_grade": a_grade,
        "n_score": 0,
        "s_score": s_result["s_score"],
        "sh_score": s_result["shareholder_score"],
        "debt_score": s_result["debt_score"],
        "debt_ratio": debt_ratio,
        "rs_score": rs_score,
        "total": total,
        "c_gate_pass": c_gate,
        "yoy_pct": latest_qy,
        "sales_yoy_pct": sales_y,
        "twelve_m_return": c_entry.get("twelve_m_return"),
        "pct_from_52w_high": c_entry.get("pct_from_52w_high"),
        "market_cap_eok": c_entry.get("market_cap_eok"),
        "induty_code": induty_code,
    }


def main():
    codes = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_TARGETS
    print(f"📊 일괄 평가 {len(codes)}종목 시작…", file=sys.stderr)

    c_index = load_c_index()
    sr_index = load_sr_index()
    corp_map = load_corp_code_map()

    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(evaluate_one, code, c_index, sr_index, corp_map): code for code in codes}
        for fut in concurrent.futures.as_completed(futures):
            try:
                r = fut.result()
                results.append(r)
                if "error" in r:
                    print(f"  ❌ {r['code']}: {r['error']}", file=sys.stderr)
                else:
                    print(f"  ✓ {r['code']} {r['name']:<12} → 합 {r['total']:.0f}", file=sys.stderr)
            except Exception as e:
                code = futures[fut]
                print(f"  ❌ {code}: {e}", file=sys.stderr)
                results.append({"code": code, "error": str(e)})

    # 원본 순서대로 정렬
    results.sort(key=lambda r: codes.index(r["code"]) if r["code"] in codes else 999)

    print()
    print("=" * 110)
    print(f"  CAN SLIM 일괄 평가 (총점 339 만점)")
    print("=" * 110)
    header = (
        f"  {'코드':<8} {'종목':<12} {'C':>5} {'A':>4}/50 {'트랙':<8} "
        f"{'N':>3} {'S':>3}/60 {'L(RS)':>6} {'합':>6} "
        f"{'%':>6} {'C게이트':<5} {'12M%':>7} {'52w-':>6}"
    )
    print(header)
    print("-" * 110)
    for r in results:
        if "error" in r:
            print(f"  {r['code']:<8} {'-- ERROR --':<12} {r['error']}")
            continue
        pct = r["total"] / 339 * 100
        gate = "✓" if r["c_gate_pass"] else "✗"
        tm = r.get("twelve_m_return")
        tm_str = f"{tm:+.1f}" if tm is not None else "—"
        pfh = r.get("pct_from_52w_high")
        pfh_str = f"{pfh:+.1f}" if pfh is not None else "—"
        print(
            f"  {r['code']:<8} {r['name'][:11]:<12} "
            f"{r['c_score']:>5.0f} {r['a_score']:>4}/50 {r['a_track'][:7]:<8} "
            f"{r['n_score']:>3} {r['s_score']:>3}/60 RS{r['rs_score']:>3} "
            f"{r['total']:>6.0f} {pct:>5.1f}% {gate:<5} {tm_str:>7} {pfh_str:>6}"
        )

    # 점수 내림차순도 같이
    print()
    print("=" * 110)
    print(f"  ⬇ 총점 내림차순")
    print("=" * 110)
    sorted_r = sorted([r for r in results if "error" not in r], key=lambda r: r["total"], reverse=True)
    for i, r in enumerate(sorted_r, 1):
        pct = r["total"] / 339 * 100
        gate = "✓ 통과" if r["c_gate_pass"] else "✗ 미통과"
        print(f"  {i:>2}. {r['name']:<12} {r['total']:>5.0f}점 ({pct:.1f}%) — C게이트 {gate}")


if __name__ == "__main__":
    main()

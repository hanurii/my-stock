"""트렌드 템플레이트 + C 원칙 통과 종목 중 "코드 33" 판별.

코드 33 = EPS · 매출 · 순이익률 세 지표 모두 3분기 연속 단조 가속.

입력 : public/data/trend-template-c-scored.json
진입 필터: c_gate_pass == True  OR  c_score >= 70
산출 : public/data/trend-template-code33.json + 콘솔 표

EPS·매출 가속 판정은 c_detailed (eps_accel_3q, sales_accel_3q) 그대로 사용.
순이익률 가속만 이 스크립트에서 새로 산출:
  - 분기 NI / 분기 매출 = 분기 net margin (%)
  - net margin YoY 시계열 (period_key 정확 매칭) → _is_accel 동일 패턴 적용

사용 예:
  python scripts/screen_trend_template_code33.py
  python scripts/screen_trend_template_code33.py --c-min 60   # 진입선 낮춤
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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

from canslim_lib import pdata  # noqa: E402
from canslim_lib.fetch import (  # noqa: E402
    fetch_dart_quarterly_ni_history,
    fetch_dart_quarterly_sales_history,
    resolve_corp_code,
    load_corp_code_map,
)
from canslim_lib.criteria import _find_yoy_prior  # noqa: E402

KST = timezone(timedelta(hours=9))
INPUT_PATH = ROOT / "public" / "data" / "trend-template-c-scored.json"
OUTPUT_PATH = ROOT / "public" / "data" / "trend-template-code33.json"
MAX_WORKERS = 8
MARGIN_DENOM_FLOOR_PCT = 1.0   # net margin YoY 분모 floor (%p) — 폭주 방지


def _is_accel(history: list[tuple[str, float]]) -> bool:
    """마지막 3개가 a < b < c 단조 + c > 0 (criteria.py 의 _is_accel 과 동일 규칙)."""
    if len(history) < 3:
        return False
    last3 = [v for _, v in history[-3:]]
    return last3[-1] > 0 and last3[0] < last3[1] < last3[2]


def compute_net_margin_accel(corp_code: str, current_year: int) -> dict:
    """분기 NI/매출 → 분기 net_margin → YoY history → 3분기 가속 판정.

    Returns:
      {
        "net_margin_accel_3q": bool,
        "net_margin_series": list[(period, margin_pct)] | None,
        "net_margin_yoy_history": list[(period, yoy_pp)] | None,
        "latest_net_margin": float | None,
        "latest_net_margin_yoy_pp": float | None,
        "reason": str | None,
      }
    """
    sales_dict: dict[str, float] = {}
    ni_dict: dict[str, float] = {}
    for yr in (current_year - 2, current_year - 1, current_year):
        for p, v in (fetch_dart_quarterly_sales_history(corp_code, yr) or []):
            sales_dict[p] = v
        for p, v in (fetch_dart_quarterly_ni_history(corp_code, yr) or []):
            ni_dict[p] = v

    common_periods = sorted(set(sales_dict) & set(ni_dict))
    if not common_periods:
        return {"net_margin_accel_3q": False, "net_margin_series": None,
                "net_margin_yoy_history": None, "latest_net_margin": None,
                "latest_net_margin_yoy_pp": None,
                "reason": "분기 NI 또는 매출 시계열 없음"}

    margin_series: list[tuple[str, float]] = []
    for p in common_periods:
        s = sales_dict[p]
        n = ni_dict[p]
        if s and s > 0:
            margin_series.append((p, n / s * 100.0))   # 단위: %

    if len(margin_series) < 5:
        return {"net_margin_accel_3q": False,
                "net_margin_series": margin_series,
                "net_margin_yoy_history": None,
                "latest_net_margin": margin_series[-1][1] if margin_series else None,
                "latest_net_margin_yoy_pp": None,
                "reason": f"net margin 시계열 {len(margin_series)}분기 (< 5)"}

    last_idx = len(margin_series) - 1
    margin_yoy_hist: list[tuple[str, float]] = []
    # 최신 5분기까지 정확한 전년 동기 매칭만
    for i in range(last_idx, max(last_idx - 5, -1), -1):
        prior_idx = _find_yoy_prior(margin_series, i)
        if prior_idx is None:
            continue
        curr_key, curr = margin_series[i]
        _, prior = margin_series[prior_idx]
        denom = max(abs(prior), MARGIN_DENOM_FLOOR_PCT)
        margin_yoy_hist.append((curr_key, round((curr - prior) / denom * 100.0, 2)))
    margin_yoy_hist.reverse()

    accel = _is_accel(margin_yoy_hist)
    latest_margin = margin_series[-1][1]
    latest_yoy = margin_yoy_hist[-1][1] if margin_yoy_hist else None
    return {
        "net_margin_accel_3q": accel,
        "net_margin_series": [(p, round(v, 4)) for p, v in margin_series],
        "net_margin_yoy_history": margin_yoy_hist,
        "latest_net_margin": round(latest_margin, 4),
        "latest_net_margin_yoy_pp": latest_yoy,
        "reason": None,
    }


def evaluate_one(stock: dict, pdata_price: dict, corp_map: dict,
                 current_year: int) -> dict:
    code = stock["code"]
    name = stock["name"]
    market = stock["market"]
    pi = pdata_price.get(code, {})
    lstgStCnt = pi.get("lstgStCnt") if pi else None

    corp_code, _common = resolve_corp_code(code, corp_map)
    if not corp_code:
        return {"code": code, "name": name, "market": market,
                "ok": False, "reason": "DART corp_code 매핑 실패"}

    margin_result = compute_net_margin_accel(corp_code, current_year)
    c_detailed = stock.get("c_detailed") or {}
    eps_accel = bool(c_detailed.get("eps_accel_3q"))
    sales_accel = bool(c_detailed.get("sales_accel_3q"))
    margin_accel = margin_result["net_margin_accel_3q"]
    code33 = eps_accel and sales_accel and margin_accel

    return {
        "code": code, "name": name, "market": market,
        "ok": True,
        "market_cap_eok": stock.get("market_cap_eok"),
        "listed_shares": lstgStCnt,  # 상장주식수 = 유통주식수 (자사주 제외 없음)
        "rs": stock.get("rs"),
        "c_score": stock.get("c_score"),
        "c_score_tier": stock.get("c_score_tier"),
        "c_gate_pass": stock.get("c_gate_pass"),
        "eps_accel_3q": eps_accel,
        "sales_accel_3q": sales_accel,
        "net_margin_accel_3q": margin_accel,
        "code33_pass": code33,
        "latest_quarter": c_detailed.get("latest_quarter"),
        "eps_yoy_pct": c_detailed.get("yoy_pct"),
        "sales_yoy_pct": c_detailed.get("sales_yoy_pct"),
        "latest_net_margin_pct": margin_result["latest_net_margin"],
        "latest_net_margin_yoy_pp": margin_result["latest_net_margin_yoy_pp"],
        "net_margin_yoy_history": margin_result["net_margin_yoy_history"],
        "net_margin_series_tail": (margin_result["net_margin_series"] or [])[-5:],
        "margin_reason": margin_result.get("reason"),
    }


def _fmt_share(n: int | float | None) -> str:
    if n is None:
        return "?"
    n = int(n)
    if n >= 1e8:
        return f"{n/1e8:,.2f}억주"
    if n >= 1e4:
        return f"{n/1e4:,.1f}만주"
    return f"{n:,}주"


def _print_table(passes: list[dict]) -> None:
    print()
    print("=" * 100)
    print(f"코드 33 통과 종목 — {len(passes)}건 (C 점수 내림차순)")
    print("=" * 100)
    if not passes:
        print("  (없음)")
        return
    print(f"{'코드':7s} {'종목명':14s} {'시장':6s} {'시총(억)':>10s} "
          f"{'유통주식수':>12s} {'RS':>3s} {'C점수':>5s} "
          f"{'EPS YoY%':>9s} {'매출 YoY%':>10s} {'순이익률%':>10s} {'순이익률 YoY‱':>15s}")
    print("-" * 100)
    for c in passes:
        eps_yoy = f"{c['eps_yoy_pct']:+.0f}" if c.get("eps_yoy_pct") is not None else "-"
        s_yoy = f"{c['sales_yoy_pct']:+.0f}" if c.get("sales_yoy_pct") is not None else "-"
        m_now = f"{c['latest_net_margin_pct']:+.2f}" if c.get("latest_net_margin_pct") is not None else "-"
        m_yoy = f"{c['latest_net_margin_yoy_pp']:+.0f}" if c.get("latest_net_margin_yoy_pp") is not None else "-"
        cap = c.get("market_cap_eok") or 0
        sh = _fmt_share(c.get("listed_shares"))
        name = c["name"][:13]
        print(f"{c['code']:7s} {name:14s} {c['market']:6s} {cap:>10,} {sh:>12s} "
              f"{c.get('rs', '-'):>3} {c.get('c_score', 0):>5.1f} "
              f"{eps_yoy:>9s} {s_yoy:>10s} {m_now:>10s} {m_yoy:>15s}")


def main() -> None:
    parser = argparse.ArgumentParser(description="트렌드 템플레이트 코드 33 (EPS·매출·순이익률 3분기 가속)")
    parser.add_argument("--c-min", type=float, default=70.0,
                        help="진입 필터: C 점수 최소 (default 70). c_gate_pass 인 종목도 포함됨.")
    parser.add_argument("--no-save", action="store_true",
                        help="JSON 저장 생략 (콘솔만)")
    args = parser.parse_args()

    if not INPUT_PATH.exists():
        print(f"❌ 입력 파일 없음: {INPUT_PATH}")
        print("   먼저 screen_trend_template.py --save 와 screen_trend_template_c_score.py 를 실행하세요.")
        sys.exit(1)

    if "DART_API_KEY" not in os.environ:
        print("❌ DART_API_KEY 환경변수 없음 — .env 확인.")
        sys.exit(1)

    print(f"📂 입력 로드: {INPUT_PATH.relative_to(ROOT)}")
    src = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    src_asof = src.get("asof")
    candidates = src["candidates"]
    eligible = [c for c in candidates
                if c.get("c_gate_pass") or (c.get("c_score") or 0) >= args.c_min]
    print(f"  C 통과 종목 (게이트 통과 OR 점수 ≥ {args.c_min}): {len(eligible)} / 전체 {len(candidates)}")

    print("\n🏛  pdata batch preload (유통주식수 lstgStCnt 용)")
    basDt = pdata._latest_available_basDt()
    pdata_price = pdata.fetch_pdata_price_info(basDt) if basDt else {}
    print(f"  price_info: {len(pdata_price)}")

    print("\n📦 DART corp_code 매핑 로드")
    corp_map = load_corp_code_map()
    print(f"  매핑된 상장사: {len(corp_map)}")

    current_year = datetime.now(KST).year
    print(f"\n💎 분기 순이익 + 매출 수집 + 코드 33 판별 (병렬 {MAX_WORKERS}워커)")
    start = time.time()
    results: list[dict] = []
    completed = 0
    def task(s):
        return evaluate_one(s, pdata_price, corp_map, current_year)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for r in ex.map(task, eligible):
            results.append(r)
            completed += 1
            if completed % 10 == 0 or completed == len(eligible):
                p33 = sum(1 for x in results if x.get("code33_pass"))
                print(f"  진행 {completed}/{len(eligible)} (코드 33 통과 {p33})")

    elapsed = time.time() - start
    print(f"\n  완료 ({elapsed:.1f}s)")

    passes = [r for r in results if r.get("ok") and r.get("code33_pass")]
    passes.sort(key=lambda x: (-(x.get("c_score") or 0.0),
                               -(x.get("market_cap_eok") or 0)))

    out = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": src_asof,
        "source": "trend-template-c-scored.json",
        "input_count": len(candidates),
        "eligible_count": len(eligible),
        "code33_pass_count": len(passes),
        "filter": {"c_score_min_or_gate": args.c_min},
        "passes": passes,
        "all_evaluated": results,
    }
    if not args.no_save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 저장: {OUTPUT_PATH.relative_to(ROOT)}")

    _print_table(passes)


if __name__ == "__main__":
    main()

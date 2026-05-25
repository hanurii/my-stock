"""Step 2: 2025-11-25 점-시점 C·A 점수 universe 전체 계산.

점-시점 안전 규칙:
  - 분기 라벨 ≤ '202509' 만 사용 (2025년 3Q. 공시일 ≤ 11/14 무렵, ASOF 11/25 이전)
  - 연간 라벨 ≤ '202412' 만 사용 (2024년 연간. 2025년 연간은 2026-03 공시)
  - ROE도 동일 필터

캐시 입력: .cache/canslim_stocks/*.json (이미 풀스캔되어 있음)
출력: research/oneil-model-book/_asof_2025-11-25_c_a.json

추가 메타(induty_code, pretax_margin) 누락 → None 처리 (보조 지표).
"""
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path("C:/Users/hanul/playground/my-stock")
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib.criteria import evaluate_c_detailed, compute_c_score, passes_c_gate
from canslim_lib.criteria_a import evaluate_a_v2

ASOF = "2025-11-25"
QUARTER_MAX = "202509"   # 2025-11-25 시점 공시 가용 마지막 분기 (보수적)
ANNUAL_MAX = "202412"    # 2024년 연간 (2025년 연간은 26-03 공시)

CACHE_DIR = ROOT / ".cache" / "canslim_stocks"
OUT = ROOT / "research" / "oneil-model-book" / "_asof_2025-11-25_c_a.json"


def filter_history(history, max_label):
    """라벨 ≤ max_label 만 유지. history = [[label, value], ...]"""
    if not history:
        return []
    return [(k, v) for k, v in history if k <= max_label]


def process_stock(data: dict) -> dict | None:
    code = data.get("code")
    if not code:
        return None

    # 점-시점 필터링
    q_eps_full = data.get("quarter_eps") or []
    q_sales_full = data.get("quarter_sales") or []
    a_eps_full = data.get("annual_eps") or []
    a_roe_full = data.get("annual_roe") or []

    q_eps = filter_history(q_eps_full, QUARTER_MAX)
    q_sales = filter_history(q_sales_full, QUARTER_MAX)
    a_eps = filter_history(a_eps_full, ANNUAL_MAX)
    a_roe = filter_history(a_roe_full, ANNUAL_MAX)

    # 분기 5개 미만은 C 평가 불가
    if len(q_eps) < 5:
        return {
            "code": code,
            "name": data.get("name"),
            "market": data.get("market"),
            "c_score": None,
            "c_passes_gate": False,
            "a_score": None,
            "a_track": None,
            "skip_reason": f"q_eps={len(q_eps)} a_eps={len(a_eps)}",
        }

    # C
    c_detailed = evaluate_c_detailed(q_eps, q_sales)
    c_score_result = compute_c_score(c_detailed)
    c_passes = passes_c_gate(c_detailed)

    # A — 시도, 실패 시 0
    quarterly_eps_yoy_history = c_detailed.get("eps_yoy_history", [])
    sales_yoy_history = c_detailed.get("sales_yoy_history", [])
    latest_q_yoy = c_detailed.get("yoy_pct")
    quarterly_eps_for_stability = [v for _, v in q_eps]
    a_eval = {"score": 0, "track": "data_truncated", "grade": "—"}
    if len(a_eps) >= 2:
        try:
            a_eval = evaluate_a_v2(
                annual_eps=a_eps,
                annual_roe=a_roe,
                quarterly_eps_yoy_history=quarterly_eps_yoy_history,
                sales_yoy_history=sales_yoy_history,
                latest_quarter_yoy=latest_q_yoy,
                induty_code=None,
                quarterly_eps_for_stability=quarterly_eps_for_stability,
                pretax_margin=None,
            )
        except Exception:
            a_eval = {"score": 0, "track": "a_eval_error", "grade": "—"}

    return {
        "code": code,
        "name": data.get("name"),
        "market": data.get("market"),
        "c_score": round(c_score_result["total"], 2),
        "c_tier": c_score_result["tier"],
        "c_passes_gate": c_passes,
        "c_latest_quarter": c_detailed.get("latest_quarter"),
        "c_yoy_pct": c_detailed.get("yoy_pct"),
        "c_sales_yoy_pct": c_detailed.get("sales_yoy_pct"),
        "a_score": a_eval.get("score"),
        "a_track": a_eval.get("track"),
        "a_grade": a_eval.get("grade"),
        "a_latest_annual": a_eps[-1][0] if a_eps else None,
        "q_eps_truncated_from": len(q_eps_full) - len(q_eps),
        "a_eps_truncated_from": len(a_eps_full) - len(a_eps),
    }


def main():
    files = sorted(CACHE_DIR.glob("*.json"))
    print(f"캐시 파일 수: {len(files)}", file=sys.stderr)

    out_rows = []
    err = 0
    for i, f in enumerate(files):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result = process_stock(data)
            if result:
                out_rows.append(result)
        except Exception as e:
            err += 1
            if err <= 5:
                print(f"  err {f.name}: {e}", file=sys.stderr)
        if (i + 1) % 500 == 0:
            print(f"  진행 {i + 1}/{len(files)} (오류 {err})", file=sys.stderr)

    # 통계
    c_pass = sum(1 for r in out_rows if r.get("c_passes_gate"))
    c_strong = sum(1 for r in out_rows if (r.get("c_score") or 0) >= 80)
    a_scored = sum(1 for r in out_rows if r.get("a_score") is not None and r.get("a_score") > 0)
    print(f"\n총 처리: {len(out_rows)} / 오류 {err}", file=sys.stderr)
    print(f"  C 게이트 통과: {c_pass}", file=sys.stderr)
    print(f"  C 80+ '강력': {c_strong}", file=sys.stderr)
    print(f"  A 점수 보유: {a_scored}", file=sys.stderr)

    OUT.write_text(json.dumps({
        "asof": ASOF,
        "quarter_max": QUARTER_MAX,
        "annual_max": ANNUAL_MAX,
        "rows": out_rows,
        "summary": {"c_pass": c_pass, "c_strong": c_strong, "a_scored": a_scored},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()

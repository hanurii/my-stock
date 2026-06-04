"""L 원칙 v4 — C 페이지 노출 종목들의 RS(상대강도) 점수 = 트렌드 템플레이트 RS 차용.

이전 v3 는 KOSPI 시총 상위 300 모집단 + Yahoo 1y 로 자체 산출했지만,
트렌드 템플레이트가 KOSPI+KOSDAQ 전 종목 + Naver 252거래일 기반으로 별도 산출하면서
같은 종목의 RS 가 두 곳에서 서로 다른 문제 발생 (예: 222040 코스맥스엔비티 38 vs 82).

해결: 트렌드 템플레이트의 RS 결과를 그대로 차용 → 모집단·데이터 소스·기간 완전 통일.

입력:
  - public/data/can-slim-candidates.json (C 페이지 노출 종목 선별용)
  - public/data/trend-template-candidates.json (RS 값 lookup)
  - public/data/can-slim-a-candidates.json (A 점수 동점 정렬 보조)

산출: public/data/can-slim-l-candidates.json
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C_DATA = ROOT / "public" / "data" / "can-slim-candidates.json"
A_DATA = ROOT / "public" / "data" / "can-slim-a-candidates.json"
TT_DATA = ROOT / "public" / "data" / "trend-template-candidates.json"
OUT = ROOT / "public" / "data" / "can-slim-l-candidates.json"
KST = timezone(timedelta(hours=9))

# C 페이지 노출 게이트 (src/app/stocks/canslim/lib/cFilter.ts 의 passesCGate 포팅).
USER_C_THRESHOLD = 25


def passes_c_gate(cr: dict) -> bool:
    """C 페이지에 실제로 노출되는 종목인지 판정. cFilter.ts:passesCGate 와 동일."""
    yoy = cr.get("yoy_pct")
    if yoy is None or yoy < USER_C_THRESHOLD:
        return False
    sales_yoy = cr.get("sales_yoy_pct")
    sales_accel_3q = cr.get("sales_accel_3q", False)
    sales_accompany = (sales_yoy is not None and sales_yoy >= 25) or sales_accel_3q
    if not sales_accompany:
        return False
    q = cr.get("eps_accel_quality")
    eps_accel_3q = cr.get("eps_accel_3q", False)
    quality_accel = q in ("mild", "strong", "explosive")
    if not (eps_accel_3q or quality_accel):
        return False
    if cr.get("consecutive_decline_quarters", 0) >= 2:
        return False
    if cr.get("severe_decel", False):
        return False
    return True


def main() -> None:
    if not C_DATA.exists():
        print(f"[ERROR] {C_DATA.relative_to(ROOT)} 가 없습니다. 먼저 screen_canslim.py --save 를 실행하세요.", file=sys.stderr)
        sys.exit(1)
    if not TT_DATA.exists():
        print(f"[ERROR] {TT_DATA.relative_to(ROOT)} 가 없습니다. 먼저 screen_trend_template.py --save 를 실행해 RS 모집단을 만드세요.", file=sys.stderr)
        sys.exit(1)

    c_data = json.loads(C_DATA.read_text(encoding="utf-8"))
    c_passed = [c for c in c_data["candidates"] if passes_c_gate(c.get("criteria", {}).get("C", {}))]
    print(f"[1/3] C 페이지 노출 종목 {len(c_passed)}개 로드 (passes_c_gate)", file=sys.stderr)

    a_score_by_code: dict[str, int] = {}
    if A_DATA.exists():
        a_data = json.loads(A_DATA.read_text(encoding="utf-8"))
        for c in a_data.get("candidates", []):
            score = c.get("score")
            if score is not None:
                a_score_by_code[c["code"]] = int(score)
        print(f"  → A 점수 lookup {len(a_score_by_code)}개 로드", file=sys.stderr)

    # 트렌드 템플레이트 RS 차용 (모집단 = KOSPI+KOSDAQ 전 종목, 252거래일 Naver 일봉)
    tt_data = json.loads(TT_DATA.read_text(encoding="utf-8"))
    tt_by_code: dict[str, dict] = {c["code"]: c for c in tt_data.get("candidates", [])}
    tt_asof = tt_data.get("asof") or tt_data.get("generated_at")
    tt_universe_n = tt_data.get("rs_universe_n")
    print(f"[2/3] 트렌드 템플레이트 RS lookup {len(tt_by_code)}종목 로드 (asof {tt_asof}, RS 모집단 {tt_universe_n})", file=sys.stderr)

    print(f"[3/3] C 통과 종목 L 점수 산출 (= 트렌드 RS)…", file=sys.stderr)
    out_candidates: list[dict] = []
    for c in c_passed:
        code = c["code"]
        a_score = a_score_by_code.get(code)
        tt = tt_by_code.get(code)
        if not tt or tt.get("rs") is None:
            out_candidates.append({
                "code": code,
                "name": c["name"],
                "market": c["market"],
                "rs_score": 0,
                "return_window_pct": None,
                "rs_basis": None,
                "current_price": c.get("current_price"),
                "a_score": a_score,
                "data_missing_reason": (
                    "트렌드 템플레이트 RS 미산출 (데이터 부족 또는 트렌드 evaluate 실패)"
                    if not tt else "RS None (단축 윈도우 표본 < 100)"
                ),
            })
            continue
        out_candidates.append({
            "code": code,
            "name": c["name"],
            "market": c["market"],
            "rs_score": int(tt["rs"]),
            "return_window_pct": tt.get("return_window_pct"),
            "rs_basis": tt.get("rs_basis"),
            "rs_window_days": tt.get("rs_window_days"),
            "current_price": c.get("current_price"),
            "a_score": a_score,
            "data_missing_reason": None,
        })

    # 정렬: 1차 RS 내림차순, 2차 A 점수 내림차순, 3차 코드 사전순.
    out_candidates.sort(key=lambda c: (
        -(c["rs_score"] or 0),
        -(c["a_score"] or 0),
        c["code"],
    ))

    evaluated = [c for c in out_candidates if c["data_missing_reason"] is None]
    data_missing = [c for c in out_candidates if c["data_missing_reason"] is not None]

    result = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d"),
        "schema_version": "v4",
        "c_input_count": len(c_passed),
        "l_evaluated_count": len(evaluated),
        "data_missing_count": len(data_missing),
        "universe": {
            "type": "트렌드 템플레이트 RS 차용 (KOSPI+KOSDAQ 전 종목 모집단)",
            "source": "public/data/trend-template-candidates.json",
            "trend_template_asof": tt_asof,
            "trend_template_universe_n": tt_universe_n,
            "return_period": "252 거래일 (Naver 일봉)",
            "scoring": "백분위 1~99 (트렌드 _compute_rs_for_all 결과 그대로)",
        },
        "candidates": out_candidates,
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {OUT.relative_to(ROOT)}", file=sys.stderr)
    print(f"  C 입력 {len(c_passed)}개 → L 평가 {len(evaluated)}개 + 데이터 없음 {len(data_missing)}개", file=sys.stderr)

    top_n = 20
    print(f"\n상위 {top_n}:", file=sys.stderr)
    for c in evaluated[:top_n]:
        rs_str = f"RS {c['rs_score']:>2}"
        ret = c.get("return_window_pct")
        ret_str = f"252d {ret:+7.2f}%" if ret is not None else "252d   ?  "
        a_str = f"A{c['a_score']:>2}" if c["a_score"] is not None else "A -"
        print(f"  {c['code']} {c['name']:<12}: {rs_str} {a_str} ({ret_str})", file=sys.stderr)

    if data_missing:
        print(f"\n데이터 없음 ({len(data_missing)}개, RS 0 처리):", file=sys.stderr)
        for c in data_missing[:10]:
            print(f"  {c['code']} {c['name']:<12}: {c['data_missing_reason']}", file=sys.stderr)
        if len(data_missing) > 10:
            print(f"  ... 외 {len(data_missing)-10}개", file=sys.stderr)


if __name__ == "__main__":
    main()

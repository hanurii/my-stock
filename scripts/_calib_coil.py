"""5예시 돌파일 as-of 코일 피벗 보정 측정 (임시 진단, 머지 전 삭제 가능).

vcp_examples.json 의 코드·날짜·피벗을 신뢰원으로 사용(메리츠 138040 제외).
FDR로 돌파일까지 일봉을 받아 as-of evaluate_vcp 를 돌리고 표로 출력한다.
선택적으로 DEFAULT_PARAMS 코일값을 오버라이드해 빠르게 스윕할 수 있다.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import FinanceDataReader as fdr  # noqa: E402
from canslim_lib.vcp import evaluate_vcp, DEFAULT_PARAMS  # noqa: E402

EXAMPLES = json.loads(
    (Path(__file__).resolve().parents[1] / "public/data/vcp_examples.json").read_text(encoding="utf-8")
)["examples"]
CASES = [e for e in EXAMPLES if e["code"] != "138040"]  # 메리츠 제외


def as_of_series(code, breakout_date, lookback=400):
    df = fdr.DataReader(code, "2019-06-01", breakout_date)  # 돌파일 포함까지
    df = df.tail(lookback)
    return {
        "dates":   [d.strftime("%Y-%m-%d") for d in df.index],
        "closes":  df["Close"].tolist(),
        "opens":   df["Open"].tolist(),
        "highs":   df["High"].tolist(),
        "lows":    df["Low"].tolist(),
        "volumes": df["Volume"].tolist(),
    }


def run(params=None):
    print(f"params override: {params}")
    print(f"{'종목':12} {'detect':6} {'status':10} {'pivot':>10} {'주석':>9} "
          f"{'오차':>8} {'coil_len':>8} {'dry':>6} {'range%':>7} {'reason'}")
    n_pass = 0
    for e in CASES:
        code, bd, ann, label = e["code"], e["breakout_date"], e["pivot"], e["note"]
        r = evaluate_vcp(as_of_series(code, bd), params)
        piv = r["pivot_price"]
        err = f"{(piv-ann)/ann*100:+.1f}%" if piv else "-"
        ok = r["vcp_detected"] and r["status"] == "breakout"
        n_pass += 1 if ok else 0
        print(f"{label:12} {str(r['vcp_detected']):6} {str(r['status']):10} "
              f"{str(piv):>10} {ann:>9} {err:>8} {str(r.get('coil_len')):>8} "
              f"{str(r.get('coil_dry_mean')):>6} {str(r.get('coil_range_pct')):>7} "
              f"{r['reason']}")
    print(f"==> breakout 충족: {n_pass}/{len(CASES)}")


if __name__ == "__main__":
    print("### baseline (현 DEFAULT_PARAMS) ###")
    print({k: DEFAULT_PARAMS[k] for k in ("coil_tight_pct", "coil_min_days", "coil_max_days", "coil_dry_max")})
    run(None)
    # 참고 스윕(보정 근거): 켐트로스/다올1은 dry_max를 비합리적으로 키워야만 통과 → 제외.
    for ov in [
        {"coil_max_days": 25, "coil_dry_max": 0.9},   # 보정 전 값
        {"coil_max_days": 10, "coil_dry_max": 1.0},    # 대안
    ]:
        print()
        run(ov)

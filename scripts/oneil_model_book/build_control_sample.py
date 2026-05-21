"""비위너 대조군 표본 생성 — 선별골격 lift 검증용.

winners.json ranked_valid(전 유니버스 2,552) 에서 위너 상위200 코드를
제외한 '비위너'에서 시드 고정 랜덤 추출 → cycles/c2024-12-ctrl/
winners_final.json (위너와 *동일 스키마*) 로 기록해, 기존 파이프라인
(detect_pivot→compute_rs→collect_variables)을 그대로 태운다.

비위너 = 사이클을 거쳤으나 지속성 위너 상위200에 들지 못한 종목 =
'규칙이 헛발동했을 때 마주치는 모집단'. 무작위라 대표성↑, 시드로 재현.

사용:  python build_control_sample.py [--n 30] [--seed 42]
"""
import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "research" / "oneil-model-book" / "cycles" / "c2024-12"
CTRL_DIR = ROOT / "research" / "oneil-model-book" / "cycles" / "c2024-12-ctrl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", default=None,
                    help="대상 사이클 디렉터리명 (예: c2024-12-ctrl500). "
                         "미지정 시 c2024-12-ctrl")
    ap.add_argument("--src", default="c2024-12",
                    help="위너 표본 출처 사이클 (예: c2020-03). 그 사이클의 "
                         "winners.json/winners_final.json 에서 비위너 풀 추출")
    args = ap.parse_args()

    src_dir = CTRL_DIR.parent / args.src
    out_dir = (CTRL_DIR if not args.outdir
               else CTRL_DIR.parent / args.outdir)

    w = json.loads((src_dir / "winners.json").read_text(encoding="utf-8"))
    rv = w["ranked_valid"]
    wf = json.loads((src_dir / "winners_final.json").read_text(encoding="utf-8"))
    win_codes = {x["code"] for x in wf["winners"]}

    pool = [r for r in rv
            if r["code"] not in win_codes
            and not r.get("exclude_reason")
            and r.get("trough_date") and r.get("peak_date")
            and r.get("n_days", 0) >= 60]          # 위너 지속성 하한과 동일 맥락
    random.seed(args.seed)
    # 시드 고정 → 표본·순서 재현(세션 분할 배치가 안정적으로 이어짐)
    sample = random.sample(pool, min(args.n, len(pool)))

    out_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "generated_at": "control-sample",
        "cycle_start_date": wf.get("cycle_start_date"),
        "cycle_end_date": wf.get("cycle_end_date"),
        "sustain_filter": {"note": "비위너 대조군 — 위너200 제외 무작위(시드 고정)",
                           "seed": args.seed, "source_pool": len(pool)},
        "passed_count": len(sample),
        "top_n": len(sample),
        "winners": sample,                          # 동일 스키마 (detect_pivot 호환)
        "dropped_by_sustain": [],
    }
    (out_dir / "winners_final.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"control sample n={len(sample)} (pool {len(pool)}, seed {args.seed}) "
          f"-> {out_dir/'winners_final.json'}")


if __name__ == "__main__":
    main()

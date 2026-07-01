# scripts/snapshot_sepa.py
"""SEPA 티어 히스토리 스냅샷 — 파이프라인 마지막 스텝.

현재 public/data의 4개 패턴 후보 파일을 트림해 sepa-tier-history.json 에 그 asof 날짜로
추가하고, 최근 3일(오늘+2일)치만 유지한다. 페이지의 '추이' 컬럼 계산에 쓰인다.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
HIST_PATH = DATA / "sepa-tier-history.json"
MAX_DATES = 3

# 패턴키(페이지 PATTERNS와 동일) → 후보 파일명
PATTERN_FILES = {
    "vcp": "sepa-vcp-candidates.json",
    "powerplayTrend": "sepa-power-play-candidates.json",
    "powerplayAll": "sepa-power-play-all-candidates.json",
    "threeC": "sepa-3c-candidates.json",
}
# 분류·표시에 필요한 최소 키(존재하는 것만 보존)
KEEP_KEYS = [
    "code", "name", "market", "rs", "status", "pivot_price", "pct_to_pivot",
    "vcp_detected", "pattern_detected", "num_contractions",
    "flag_length_days", "flag_depth_pct",
]


def _trim(cand: dict) -> dict:
    return {k: cand[k] for k in KEEP_KEYS if k in cand}


def snapshot_from(data_dir: Path, hist_path: Path) -> None:
    asof = None
    by_pattern: dict[str, list] = {}
    for key, fname in PATTERN_FILES.items():
        p = data_dir / fname
        if not p.exists():
            by_pattern[key] = []
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            by_pattern[key] = []
            continue
        by_pattern[key] = [_trim(c) for c in d.get("candidates", [])]
        asof = asof or d.get("asof")
    if not asof:
        print("❌ asof 없음(후보 파일 부재) — 스냅샷 건너뜀")
        return

    hist = {"dates": [], "byDate": {}}
    if hist_path.exists():
        try:
            hist = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            hist = {"dates": [], "byDate": {}}
    hist.setdefault("dates", [])
    hist.setdefault("byDate", {})

    hist["byDate"][asof] = by_pattern
    dates = sorted(set(hist["byDate"].keys()))     # 오래된→최신
    dates = dates[-MAX_DATES:]                      # 최근 3일만
    hist["byDate"] = {d: hist["byDate"][d] for d in dates}
    hist["dates"] = dates

    hist_path.parent.mkdir(parents=True, exist_ok=True)
    hist_path.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {k: len(v) for k, v in by_pattern.items()}
    print(f"💾 스냅샷: {hist_path.relative_to(ROOT)} | {asof} 추가 | dates={dates} | {counts}")


def main() -> None:
    ap = argparse.ArgumentParser(description="SEPA 티어 히스토리 스냅샷")
    ap.add_argument("--data-dir", default=None, help="후보 파일 디렉토리(부트스트랩용, 기본 public/data)")
    args = ap.parse_args()
    data_dir = Path(args.data_dir) if args.data_dir else DATA
    snapshot_from(data_dir, HIST_PATH)


if __name__ == "__main__":
    main()

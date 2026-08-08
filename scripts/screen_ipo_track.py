"""find-ipo — IPO 트랙(신규상장 대체 관문) 후보 정리 + 과열 딱지.

입력: public/data/sepa-trend-candidates.json 의 ipo_candidates
      (1단계 screen_trend_template.py --ipo-track 산출 — 여기서 재평가하지 않는다)
출력: public/data/sepa-ipo-candidates.json
비차단: 입력에 ipo_candidates 가 없으면(관문이 플래그 없이 돌았음) 경고 후 exit 0.

과열 딱지 근거: 과거 재현 검증(docs/research/2026-08-08-ipo-track-replay-findings.md)
— iRS≥90·상장 최고가 -5% 이내·상장 60일 미만 통과는 성과가 오히려 나빴다(소표본).
청산 주의: 통과 종목에 -10% 손절은 부적합(검증상 91%가 4일 내 손절 → 기대값 0).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))
IN_PATH = ROOT / "public" / "data" / "sepa-trend-candidates.json"
OUT_PATH = ROOT / "public" / "data" / "sepa-ipo-candidates.json"

# 과열 딱지 문턱 (검증 소표본 기반 — 방향성 참고용 표시, 차단 아님)
OVERHEAT_IRS = 90
OVERHEAT_NEAR_HIGH_PCT = 5.0     # I4 value(고점 대비 -x%) ≤ 5
EARLY_DAYS = 60
NEAR_MISS_MIN = 5                # 5~6/7 = 통과 임박

EXIT_CAUTION = ("IPO 통과 종목에 기본 -10% 손절 부적합 — 과거 재현에서 91%가 "
                "중앙값 4거래일 만에 손절(기대값 0). 전용 청산 규칙 미확립, 매매 전 주의.")


def overheat_flags(c: dict) -> list[str]:
    flags = []
    if (c.get("ipo_rs") or 0) >= OVERHEAT_IRS:
        flags.append(f"iRS {c['ipo_rs']} ≥ {OVERHEAT_IRS} — 검증상 과열 역신호")
    i4 = (c.get("criteria") or {}).get("I4", {}).get("value")
    if i4 is not None and i4 <= OVERHEAT_NEAR_HIGH_PCT:
        flags.append(f"상장 최고가 -{i4:g}% 코앞 — 꼭대기 근접 통과가 최악 구간")
    if (c.get("listed_days") or 999) < EARLY_DAYS:
        flags.append(f"상장 {c['listed_days']}일 < {EARLY_DAYS}일 — 조기 통과 열세 구간")
    return flags


def main():
    ap = argparse.ArgumentParser(description="find-ipo — IPO 트랙 후보 정리")
    ap.add_argument("--in", dest="inp", default=None, help=f"입력(default {IN_PATH.name})")
    ap.add_argument("--out", dest="out", default=None, help=f"출력(default {OUT_PATH.name})")
    a = ap.parse_args()
    in_path = Path(a.inp) if a.inp else IN_PATH
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    out_path = Path(a.out) if a.out else OUT_PATH
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    if not in_path.exists():
        print(f"⚠️ 입력 없음({in_path.name}) — find-trend-template 먼저. 이전 산출 유지")
        return
    data = json.loads(in_path.read_text(encoding="utf-8"))
    cands = data.get("ipo_candidates")
    if cands is None:
        print("⚠️ ipo_candidates 없음 — 관문이 --ipo-track 없이 실행됨. 이전 산출 유지")
        return

    passers, near = [], []
    for c in cands:
        row = {k: c.get(k) for k in
               ("code", "name", "market", "market_cap_eok", "current_price",
                "last_date", "first_date", "listed_days", "ipo_rs",
                "passed_count", "all_pass")}
        if c.get("all_pass"):
            row["overheat"] = overheat_flags(c)
            passers.append(row)
        elif (c.get("passed_count") or 0) >= NEAR_MISS_MIN:
            row["fails"] = [f"{k}: {v.get('detail', '')[:60]}"
                            for k, v in (c.get("criteria") or {}).items()
                            if not v.get("pass")]
            near.append(row)

    passers.sort(key=lambda r: -(r["ipo_rs"] or 0))
    near.sort(key=lambda r: (-r["passed_count"], -(r["ipo_rs"] or 0)))
    output = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": data.get("asof"),
        "ipo_track": data.get("ipo_track"),
        "evaluated": len(cands),
        "pass_count": len(passers),
        "exit_caution": EXIT_CAUTION,
        "pass": passers,
        "near_miss": near,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(f"💾 저장: {out_path.name} — 평가 {len(cands)} · 통과 {len(passers)} · 임박 {len(near)}")
    for r in passers:
        oh = " ⚠️" + " ·".join(f[:24] for f in r["overheat"]) if r["overheat"] else ""
        print(f"  🐣 {r['code']} {r['name']} 상장{r['listed_days']}일 iRS{r['ipo_rs']}{oh}")
    for r in near[:8]:
        print(f"  ◔ {r['passed_count']}/7 {r['name']} 상장{r['listed_days']}일 iRS{r['ipo_rs']} "
              f"— {r['fails'][0] if r['fails'] else ''}")
    if passers:
        print(f"  ⚠️ {EXIT_CAUTION}")


if __name__ == "__main__":
    main()

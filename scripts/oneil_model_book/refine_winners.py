"""1단계-b — 지속성 필터 적용 후 위너 상위 30 확정.

사용자 확정 규칙:
- 유지(retention) = (현재가 - 저점) / (고점 - 저점) >= 0.50  (되돌림형 제외)
- 상승 지속기간 = 고점일 - 저점일 > 1개월(>= 60 캘린더일)  (후반 1개월 급등 제외)
- 저점 시점은 사이클 내 무관
- 위 필터 통과분을 유지배수 내림차순 상위 30

해석/판정 없음. 가격 사실만.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cyclecfg  # noqa: E402
DIR = cyclecfg.DIR
SRC = DIR / "winners.json"
OUT = DIR / "winners_final.json"
TXT = DIR / "_winners_final.txt"

RETENTION_MIN = 0.50
ADVANCE_DAYS_MIN = 60  # 1개월 초과 (안전하게 약 2개월)
TOP_N = 200


def days_between(d1: str, d2: str) -> int:
    a = datetime.strptime(d1, "%Y-%m-%d")
    b = datetime.strptime(d2, "%Y-%m-%d")
    return (b - a).days


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    v = d["ranked_valid"]

    enriched = []
    for r in v:
        T = r["trough_close"]
        P = r["peak_close"]
        L = r["last_close"]
        gain = P - T
        retention = (L - T) / gain if gain > 0 else 0.0
        adv_days = days_between(r["trough_date"], r["peak_date"])
        rr = {
            **r,
            "retention": round(retention, 3),
            "advance_days": adv_days,
        }
        # 제외 사유 판정
        reasons = []
        if retention < RETENTION_MIN:
            reasons.append(f"되돌림(유지율 {retention:.0%} < 50%)")
        if adv_days < ADVANCE_DAYS_MIN:
            reasons.append(f"단기급등(상승 {adv_days}일 < 60일)")
        rr["sustain_exclude_reason"] = " / ".join(reasons) if reasons else None
        enriched.append(rr)

    passed = [r for r in enriched if r["sustain_exclude_reason"] is None]
    passed.sort(key=lambda r: r["sustained_multiple"], reverse=True)
    final = passed[:TOP_N]
    dropped = [r for r in enriched if r["sustain_exclude_reason"] is not None]

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "cycle_start_date": d["cycle_start_date"],
        "cycle_end_date": d["cycle_end_date"],
        "sustain_filter": {
            "retention_min": RETENTION_MIN,
            "advance_days_min": ADVANCE_DAYS_MIN,
            "retention_def": "(현재가-저점)/(고점-저점)",
            "note": "되돌림형·후반 1개월 급등 제외. 저점 시점 무관.",
        },
        "passed_count": len(passed),
        "top_n": TOP_N,
        "winners": final,
        "dropped_by_sustain": sorted(
            dropped, key=lambda r: r["sustained_multiple"], reverse=True
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append(f"사이클 {d['cycle_start_date']} ~ {d['cycle_end_date']}")
    lines.append(f"지속성 필터: 유지율>=50% AND 상승지속>60일 → 통과 {len(passed)}종목 중 상위 {TOP_N}")
    lines.append("")
    lines.append("순위 종목명(코드/시장) | 유지배수 | 저점일 저점가 → 고점일 고점가 (상승 N일) | 현재가 (유지율)")
    for i, r in enumerate(final, 1):
        lines.append(
            "%2d. %s (%s/%s) | %.2f배 | %s %s → %s %s (%d일) | %s (%.0f%%)"
            % (
                i, r["name"], r["code"], r["market"], r["sustained_multiple"],
                r["trough_date"], format(int(r["trough_close"]), ","),
                r["peak_date"], format(int(r["peak_close"]), ","),
                r["advance_days"], format(int(r["last_close"]), ","),
                r["retention"] * 100,
            )
        )
    lines.append("")
    lines.append(f"=== 지속성 필터로 탈락한 상위 15 (상승배수는 컸으나 되돌림/단기) ===")
    for r in payload["dropped_by_sustain"][:15]:
        lines.append(
            "  %s (%s) %.2f배 | %s→%s (%d일) 현재 %s | 탈락: %s"
            % (
                r["name"], r["code"], r["sustained_multiple"],
                r["trough_date"], r["peak_date"], r["advance_days"],
                format(int(r["last_close"]), ","), r["sustain_exclude_reason"],
            )
        )
    TXT.write_text("\n".join(lines), encoding="utf-8")
    print("written", OUT)


if __name__ == "__main__":
    main()

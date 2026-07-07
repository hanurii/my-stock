# scripts/pivot_backtest_report.py
"""pivot-backtest JSON → 마크다운 리포트."""
from __future__ import annotations
import json, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
ASOF = "2026-04-01"
IN = ROOT / "public" / "data" / f"pivot-backtest-{ASOF}.json"
OUT = ROOT / "docs" / "research" / f"{ASOF}-pivot-backtest.md"


def wr(t):
    return "-" if t["win_rate_resolved"] is None else f"{t['win_rate_resolved']}%"


def table(title, groups):
    rows = [f"### {title}\n", "| 구간 | n | 승 | 패 | 예외 | 미결 | 결착승률 |",
            "|---|--:|--:|--:|--:|--:|--:|"]
    for k, t in groups.items():
        rows.append(f"| {k} | {t['n']} | {t['win']} | {t['loss']} | {t['ambiguous']} | {t['unresolved']} | {wr(t)} |")
    return "\n".join(rows) + "\n"


def main():
    d = json.loads(IN.read_text(encoding="utf-8"))
    p, s = d["params"], d["summary"]
    L = []
    L.append(f"# SEPA 피벗 백테스트 — {ASOF} 스냅샷\n")
    L.append(f"> 생성 {d['generated_at']} · 기준일 {p['asof']} · 전진 마지막 {p['forward_last']} "
             f"· 목표 +{p['target_pct']}% / 손절 -{p['stop_pct']}% · RS≥{p['rs_min']}\n")
    L.append(f"**총 {s['n']}건** — 승 {s['win']} · 패 {s['loss']} · 예외(ambiguous) {s['ambiguous']} "
             f"· 미결(unresolved) {s['unresolved']} · **결착 승률 {wr(s)}**\n")
    L.append("> 결착 승률 = 승 / (승+패). 예외=일봉으로 선착 판별 불가(분봉 확인 필요), 미결=창 내 미도달.\n")
    L.append(f"> ⚠️ 결착 승률 {wr(s)} 는 결착 {s['win']+s['loss']}/{s['n']}건만의 값. 예외 {s['ambiguous']}건이 하방(돌파일 -5% 관통)으로 쏠려 **정직한 범위는 최악 {s['win_rate_worst']}% ~ 최선 {s['win_rate_best']}%**.\n")
    L.append(f"> 종목·돌파일 중복 제거 시 고유 엔트리 {d['unique_stock_days']}건 → stock-level 결착 승률 {wr(d['summary_stock_level'])} (같은 종목+같은 날 다패턴 동시발화 존재).\n")
    L.append(table("패턴별", d["by_pattern"]))
    for label, key in [("시장", "market"), ("가격대", "price_bucket"),
                       ("돌파일 상대거래량", "rel_vol_bucket"), ("RS 구간", "rs_bucket")]:
        L.append(table(label, d["by_feature"][key]))
    # 인사이트: 결착 표본 ≥ 5 인 버킷 중 승률 최고/최저
    cand = []
    for key, groups in d["by_feature"].items():
        for k, t in groups.items():
            if t["win"] + t["loss"] >= 5 and t["win_rate_resolved"] is not None:
                cand.append((t["win_rate_resolved"], key, k, t))
    if cand:
        cand.sort(reverse=True)
        hi, lo = cand[0], cand[-1]
        L.append("## 인사이트 (결착 n≥5 버킷)\n")
        L.append(f"- **최고 승률**: {hi[1]}={hi[2]} → {hi[0]}% (n {hi[3]['n']})")
        L.append(f"- **최저 승률**: {lo[1]}={lo[2]} → {lo[0]}% (n {lo[3]['n']})\n")
    # 예외 목록(분봉 확인 요청)
    L.append("## ⚠️ 예외(ambiguous) — 분봉 확인 필요\n")
    L.append("분봉으로도 판정 불가로 남은 건: 진입 미확인(no_entry)·일봉↔분봉 가격 스케일 불일치(scale_mismatch).\n")
    L.append("| 종목 | 패턴 | 돌파일 | 피벗 | 사유 |")
    L.append("|---|---|---|--:|---|")
    for e in d["ambiguous"]:
        L.append(f"| {e['name']}({e['code']}) | {e['pattern']} | {e['breakout_date']} | {e['pivot']:,.0f} | {e['exit_reason']} |")
    L.append("\n## 한계\n- 전진 64거래일·단일 기준일·단일 국면 → 일반화 금지.\n"
             "- 잔존 생존자 편향(2024-11 이전 상폐주 없음).\n- 먼 기간·다중 기준일은 후속 과제.\n"
             "- 게이트는 각 돌파일 기준 point-in-time 재평가(look-ahead 제거됨).\n"
             "- 이벤트는 (종목·패턴) 단위 — 같은 종목이 여러 패턴/날 중복 기여할 수 있어 유효 표본은 이벤트 수보다 작음(stock-level 병기 참고).\n"
             "- 일부 종목은 일봉·분봉 가격 스케일 불일치(수정주가 복원 드리프트)로 scale_mismatch 처리(판정 제외).\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"💾 저장: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

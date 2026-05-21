"""정제 복합 가드 — '최근 고점 직후 + 거기서 크게 빠짐'(=고점후 분산).

발견: D 단독(고점근접)·C 단독(최근 매도반전) 모두 위너/비위너 못 가름.
이유: 진짜 pivot은 base *바닥*이라 (a)최근 고점이 옛날이거나 (b)돌파형
이면 고점에 *밀착*(아직 안 빠짐). 라이브 4가짜의 특징은 *둘의 결합*:
"며칠 전 고점 찍고 → 지금 그 고점서 크게 하락 중". 돌파형 위너(고점
밀착·아직 상승)와 base바닥 위너(고점 옛날)는 둘 다 이 결합에 안 걸림.

가드_fail(K,Dr) = (직전60일 고점이 최근 K거래일 이내) AND
                  (현재 종가가 그 고점 대비 −Dr% 이하).
위너 fail% 낮고(=안 버림) + 라이브 4가짜 잡으면 성공.

근거: cycles/<id>/_universe_prices.json(위너·대조 동일 유니버스 캐시)
+ model_book pivot_date. 라이브는 _universe_prices_5y.json(2026-05-15).
한계: 종가·상폐제외·인-샘플·대조 n. 컷오프는 위너보존율로 도출.

사용:  python analyze_postpeak_guard.py
"""
import bisect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CY = ROOT / "research" / "oneil-model-book" / "cycles"
OUT = CY / "c2024-12" / "_postpeak_guard.txt"


def mb(tag):
    return json.loads((CY / tag / "model_book.json").read_text("utf-8"))["rows"]


def hi_metrics(closes, idx, win):
    """idx 기준 직전 win거래일: (고점이 며칠전, 종가/그고점−1 %)."""
    lo = max(0, idx - win + 1)
    seg = closes[lo:idx + 1]
    if len(seg) < 10:
        return None, None
    hv = max(seg)
    hoff = max(range(len(seg)), key=lambda i: seg[i])
    days_since = (len(seg) - 1) - hoff
    pct_vs = (closes[idx] / hv - 1) * 100 if hv else None
    return days_since, pct_vs


def collect(U, rows):
    out = []
    for r in rows:
        code, pv = r.get("code"), r.get("pivot_date")
        s = U.get(code)
        if not s or not pv:
            continue
        d, c = s.get("d"), s.get("c")
        if not d or not c:
            continue
        j = bisect.bisect_right(d, pv) - 1
        if j < 10:
            continue
        ds, pv_ = hi_metrics(c, j, 60)
        if ds is None:
            continue
        out.append((ds, pv_))
    return out


def fail(ds, pvs, K, Dr):
    return ds is not None and pvs is not None and ds <= K and pvs <= -Dr


def main():
    U = json.loads((CY / "c2024-12" / "_universe_prices.json")
                    .read_text("utf-8"))
    W = collect(U, mb("c2024-12"))
    C = collect(U, mb("c2024-12-ctrl"))
    L = ["정제 복합 가드 — '최근 K일내 고점 AND 거기서 −Dr% 이하 하락'",
         f"위너 {len(W)} vs 대조 {len(C)} (pivot 시점, 직전60일 고점기준)",
         "fail = 고점후 분산으로 판정(좋은 가드=위너fail 낮고 대조fail 높음)",
         "",
         "K일 | Dr% | 위너fail% | 대조fail% | 분리도pp | 위너보존%",
         "----|-----|----------|----------|---------|--------"]
    grid = []
    for K in (5, 10, 15):
        for Dr in (8, 12, 15, 20):
            fw = sum(1 for ds, pv in W if fail(ds, pv, K, Dr)) / len(W) * 100
            fc = sum(1 for ds, pv in C if fail(ds, pv, K, Dr)) / len(C) * 100
            grid.append((K, Dr, fw, fc, fc - fw))
            L.append(f"{K:>3} | {Dr:>3} | {fw:6.1f}% | {fc:6.1f}% | "
                     f"{fc-fw:+6.1f} | {100-fw:5.1f}%")
    # 위너보존 ≥90% 중 분리도 최대
    safe = [g for g in grid if (100 - g[2]) >= 90]
    rec = max(safe, key=lambda g: g[4]) if safe else max(grid, key=lambda g: g[4])
    L += ["", f"== 권고 == 위너보존 ≥90% 중 분리도 최대 → "
          f"K={rec[0]}일·Dr={rec[1]}%  "
          f"(위너fail {rec[2]:.0f}%·대조fail {rec[3]:.0f}%·분리 {rec[4]:+.0f}pp)"]

    # 라이브 24후보 + 문제4 적용
    U5 = json.loads((CY / "c2024-12" / "_universe_prices_5y.json")
                     .read_text("utf-8"))
    bc = (CY / "c2024-12" / "_buy_candidates.txt")
    L += ["", f"== 라이브 24후보(2026-05-15) — 권고 K={rec[0]}·Dr={rec[1]}% 적용 =="]
    if bc.exists():
        names = {}
        for ln in bc.read_text("utf-8").splitlines():
            m = re.match(r"^(\d{6})\s+(\S+)\(", ln)
            if m:
                names[m.group(1)] = m.group(2)
        survive = []
        for code, nm in names.items():
            s = U5.get(code)
            if not s:
                continue
            c = s.get("c")
            if not c or len(c) < 61:
                continue
            ds, pvs = hi_metrics(c, len(c) - 1, 60)
            f = fail(ds, pvs, rec[0], rec[1])
            tag = " ❌제외(고점후분산)" if f else " ✅통과"
            L.append(f"  {nm}({code}) | 고점 {ds}일전·고점대비 "
                     f"{pvs:+.0f}%{tag}")
            if not f:
                survive.append(f"{nm}({code})")
        L += ["", f"라이브 생존 {len(survive)}: " + ", ".join(survive)]
    L += ["", "== 정직한 한계 ==",
          "· D·C 단독은 모델북서 무용 확인 → 본 복합가드가 그 대안.",
          "· 종가·상폐제외·인-샘플·대조 n=100. 컷오프=위너보존율 도출.",
          "· 분리도=농축이지 실거래 수익 보장 아님. 2020 미적용(차기)."]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nsaved: {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()

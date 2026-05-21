"""C 가드 컷오프 캘리브레이션 — '주도 수급주체 최근 N일 매도반전'.

발견3 결론: 진짜 가드는 D(고점근접)가 아니라 C(60일을 끌어올린 주도
주체가 *최근 며칠* 새 순매도로 돌아섰나). _pivot_dailyflow.json(위너
200·대조100 pivot 직전 일별)으로 N을 데이터에서 도출.

논리: 진짜 pivot(터지기 직전)에선 주도 큰손이 계속 사거나 최소한
크게 안 판다 → 위너의 '최근N일 매도반전' 비율은 낮아야. 대조군은
더 자주 반전. N을 키우며 (대조 fail% − 위너 fail%) 최대 + 위너
보존(위너 fail% 낮음) 지점을 권고.

주도주체 = model_book fgn_net_60d / inst_net_60d 중 양(+)이고 더 큰 쪽.
fail(N) = 그 주체의 최근 N거래일(pivot까지) 순매수 합 < 0.
+ 강도판: fail_mag(N) = 최근N일 순매도가 60일 일평균매수의 1배↑.

한계: 종가·상폐제외·인-샘플·대조 n=100. enrichment=농축이지 수익 아님.

사용:  python analyze_c_guard.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CY = ROOT / "research" / "oneil-model-book" / "cycles"
FLOW = json.loads((CY / "c2024-12" / "_pivot_dailyflow.json")
                   .read_text("utf-8"))
OUT = CY / "c2024-12" / "_c_guard.txt"


def mb(tag):
    return {r["code"]: r for r in json.loads(
        (CY / tag / "model_book.json").read_text("utf-8"))["rows"]}


def lead_actor(r):
    """(키, 60일합) — 양(+)이고 더 큰 주체. 없으면 None."""
    fg, og = r.get("fgn_net_60d"), r.get("inst_net_60d")
    cands = []
    if isinstance(fg, (int, float)) and fg > 0:
        cands.append(("fgn_net", fg))
    if isinstance(og, (int, float)) and og > 0:
        cands.append(("org_net", og))
    if not cands:
        return None
    return max(cands, key=lambda x: x[1])


def recent_net(rows, field, n):
    seg = rows[-n:] if len(rows) >= n else rows
    if len(seg) < min(n, 5):
        return None
    return sum((x.get(field) or 0) for x in seg)


def evaluate(codes_mb, kind):
    """각 종목: 주도주체·일별로 N별 fail(매도반전) 판정."""
    res = []
    for code, r in codes_mb.items():
        pv = r.get("pivot_date")
        rec = FLOW.get(f"{code}@{pv}")
        if not rec or len(rec.get("rows", [])) < 10:
            continue
        la = lead_actor(r)
        if la is None:
            continue
        field, sum60 = la
        rows = rec["rows"]
        avg_day = sum60 / 60.0
        row = {"code": code, "kind": kind, "field": field}
        for n in (3, 5, 10, 15, 20):
            rn = recent_net(rows, field, n)
            row[f"net{n}"] = rn
            row[f"fail{n}"] = (rn is not None and rn < 0)
            row[f"failmag{n}"] = (rn is not None and avg_day > 0
                                  and rn < -avg_day * n)
        res.append(row)
    return res


def rate(rows, key):
    v = [r[key] for r in rows if r.get(key) is not None]
    return (sum(1 for x in v if x) / len(v) if v else None), len(v)


def main():
    W = evaluate(mb("c2024-12"), "W")
    C = evaluate(mb("c2024-12-ctrl"), "C")
    L = ["C 가드 캘리브레이션 — 주도 수급주체 '최근 N일 매도반전'",
         f"위너 {len(W)} vs 대조 {len(C)} (pivot 직전 일별, 주도=60일+큰쪽)",
         "fail = 주도주체 최근 N거래일 순매수합 < 0 (매도로 돌아섬)",
         "좋은 가드 = 위너 fail% 낮고(=위너 안 버림) 대조 fail% 높음",
         "",
         "N | 위너fail% | 대조fail% | 분리도(대조-위너) | 위너보존%",
         "--|--|--|--|--"]
    best = None
    for n in (3, 5, 10, 15, 20):
        pw, _ = rate(W, f"fail{n}")
        pc, _ = rate(C, f"fail{n}")
        if pw is None or pc is None:
            continue
        sep = (pc - pw) * 100
        keep = (1 - pw) * 100
        L.append(f"{n} | {pw*100:.1f}% | {pc*100:.1f}% | {sep:+.1f}pp | "
                 f"{keep:.1f}%")
        if best is None or sep > best[1]:
            best = (n, sep, pw, pc)
    L += ["", "[강도판] fail = 최근N일 순매도가 60일 일평균매수의 N배↑",
          "N | 위너fail% | 대조fail% | 분리도 | 위너보존%",
          "--|--|--|--|--"]
    for n in (3, 5, 10, 15, 20):
        pw, _ = rate(W, f"failmag{n}")
        pc, _ = rate(C, f"failmag{n}")
        if pw is None or pc is None:
            continue
        L.append(f"{n} | {pw*100:.1f}% | {pc*100:.1f}% | "
                 f"{(pc-pw)*100:+.1f}pp | {(1-pw)*100:.1f}%")

    if best:
        n, sep, pw, pc = best
        L += ["", f"== 권고 == 분리도 최대 N={n}일 "
              f"(위너 fail {pw*100:.0f}%·대조 fail {pc*100:.0f}%, "
              f"분리 {sep:+.0f}pp). 단순 부호반전 기준.",
              "위너 보존 우선이면 위 표서 위너fail% ≤15% 중 분리도 큰 N 선택."]
    L += ["", "== 정직한 한계 ==",
          "· 주도주체=model_book 60일합 기준(라이브와 동일 정의).",
          "· 종가·상폐제외·인-샘플·대조 n=100·일별 frgn 깊이 의존.",
          "· enrichment/분리도=농축이지 실거래 수익 보장 아님."]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nsaved: {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()

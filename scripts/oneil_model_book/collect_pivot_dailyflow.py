"""C 가드 캘리브레이션용 — 위너·대조군 pivot 직전 *일별* 수급 재수집.

발견3: D(고점근접) 단독 무용 → 진짜 가드는 C(주도 수급주체가 최근
며칠 새 순매도 반전). 모델북엔 60일·직전60일 합만 있고 일별이 없어
캘리 불가 → pivot 직전 ~25거래일 일별 외인/기관을 네이버 frgn에서
재수집해 캐시한다. (사이클 c2024-12 = 2025~26 상승, frgn 깊이 충분.)

각 종목 pivot까지 필요한 페이지를 날짜 간격으로 산정(과잉 호출 방지).
산출: cycles/c2024-12/_pivot_dailyflow.json
  { code: {pivot_date, name, kind:'W'|'C',
           rows:[{date,close,fgn_net,org_net}...(pivot까지 최근 30개)]} }
환각 금지: 미가용·페이지부족은 결손 표기(rows 짧음). 인-샘플·상폐제외.

사용:  python collect_pivot_dailyflow.py [--limit N] [--sleep 120]
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

CY = ROOT / "research" / "oneil-model-book" / "cycles" / "c2024-12"
OUT = CY / "_pivot_dailyflow.json"
CACHE_LAST = "2026-05-15"


def pages_for(pivot_date):
    """pivot −25거래일까지 닿도록: (지금~pivot) 개월 + 여유. 3p≈3개월."""
    try:
        pv = datetime.strptime(pivot_date, "%Y-%m-%d")
        last = datetime.strptime(CACHE_LAST, "%Y-%m-%d")
    except Exception:
        return 12
    months = (last - pv).days / 30.0
    return max(4, min(24, int(months) + 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0=전체")
    ap.add_argument("--sleep", type=int, default=120)
    args = ap.parse_args()

    W = json.loads((CY / "model_book.json").read_text("utf-8"))["rows"]
    C = json.loads((CY.parent / "c2024-12-ctrl" / "model_book.json")
                    .read_text("utf-8"))["rows"]
    targets = ([("W", r) for r in W] + [("C", r) for r in C])
    if args.limit:
        targets = targets[:args.limit]

    out = {}
    if OUT.exists():
        out = json.loads(OUT.read_text("utf-8"))   # 이어받기(메모이즈)

    done = ok = miss = 0
    for kind, r in targets:
        code, pv, nm = r.get("code"), r.get("pivot_date"), r.get("name")
        if not code or not pv:
            continue
        key = f"{code}@{pv}"
        if key in out and len(out[key].get("rows", [])) >= 25:
            ok += 1
            continue
        pg = pages_for(pv)
        try:
            fr = fetch_naver_org_flow(code, pages=pg, sleep_ms=args.sleep)
            fr = [x for x in fr if x["date"] <= pv]      # pivot까지(전향 차단)
            fr.sort(key=lambda x: x["date"])
            rows = [{"date": x["date"], "close": x["close"],
                     "fgn_net": x.get("fgn_net"), "org_net": x.get("org_net")}
                    for x in fr[-30:]]
            out[key] = {"code": code, "name": nm, "pivot_date": pv,
                        "kind": kind, "pages": pg, "rows": rows}
            if len(rows) >= 20:
                ok += 1
            else:
                miss += 1
        except Exception as e:
            out[key] = {"code": code, "name": nm, "pivot_date": pv,
                        "kind": kind, "error": str(e), "rows": []}
            miss += 1
        done += 1
        if done % 25 == 0:
            OUT.write_text(json.dumps(out, ensure_ascii=False), "utf-8")
            print(f"  ...{done}/{len(targets)} (ok{ok} miss{miss})",
                  file=sys.stderr, flush=True)

    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"DONE collected={len(out)} ok≥20일={ok} 결손={miss} → {OUT}",
          file=sys.stderr)


if __name__ == "__main__":
    main()

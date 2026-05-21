"""pivot 직전 20거래일 외인+기관 누적 순매수 수집 — 병렬 분할.

목적: 'I 20일 합산 > 0' 이 핵심 변별축이 될 수 있나 검정용 데이터.
대상 4개: c2024-12 / c2024-12-ctrl500 / c2020-03 / c2020-03-ctrl500.
각 model_book.json 의 (code, pivot_date) 기준, naver frgn 일별에서
pivot 이전 20·60 거래일 fgn_net·org_net 누적을 모은다. 깊이 부족 등
미도달은 결손(추정 없음).

병렬: --cycle <dir> --worker K [--batch 100]  → _flow20.partK.json
합치기: --cycle <dir> --reduce               → _flow20.json
무인자(--cycle만): 그 사이클 전체 직렬(소규모/검증용 --limit).

정직: naver frgn 깊이 한계(옛 pivot은 90p로도 결손 가능)→결손 명시.
사용:
  python collect_flow20.py --cycle c2024-12 --worker 0
  python collect_flow20.py --cycle c2024-12 --reduce
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.criteria_i import fetch_naver_org_flow  # noqa: E402

CYC = ROOT / "research" / "oneil-model-book" / "cycles"


def _digits(s):
    return "".join(ch for ch in str(s) if ch.isdigit())[:8]


def _dyn_pages(pivot):
    """pivot~오늘 개월수 기준 페이지. naver frgn 1p≈15거래일이라
    1개월(약 21거래일)≈1.8p로 환산, 여유 +12, 캡 220."""
    try:
        pv = datetime.strptime(pivot, "%Y-%m-%d")
    except ValueError:
        return 200
    months = (datetime.now().year - pv.year) * 12 + (datetime.now().month - pv.month)
    return max(8, min(220, int(months * 1.8) + 12))


def collect_one(code, pivot):
    pkey = _digits(pivot)
    pages = _dyn_pages(pivot)
    try:
        rows = fetch_naver_org_flow(code, pages=pages, sleep_ms=150)
    except Exception as e:
        return {"err": f"fetch:{type(e).__name__}"}
    # 최신→과거. pivot 이전(<=) 행만, 날짜 오름차순
    elig = [r for r in rows if _digits(r.get("date")) and _digits(r.get("date")) <= pkey]
    elig.sort(key=lambda r: _digits(r["date"]))
    if len(elig) < 20:
        return {"err": "frgn_depth", "avail": len(elig), "pages": pages}
    w20, w60 = elig[-20:], elig[-60:] if len(elig) >= 60 else None

    def s(seg, k):
        return sum((r.get(k) or 0) for r in seg)
    out = {"asof": elig[-1]["date"], "n": len(elig),
           "f20": s(w20, "fgn_net"), "o20": s(w20, "org_net")}
    out["sum20"] = out["f20"] + out["o20"]
    if w60:
        out["f60"], out["o60"] = s(w60, "fgn_net"), s(w60, "org_net")
        out["sum60"] = out["f60"] + out["o60"]
    return out


def load_rows(cdir):
    mb = json.loads((cdir / "model_book.json").read_text(encoding="utf-8"))["rows"]
    return [r for r in mb if not r.get("error") and r.get("code") and r.get("pivot_date")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", required=True, help="model_book 디렉터리명")
    ap.add_argument("--worker", type=int, default=None)
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--reduce", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="검증용 N")
    a = ap.parse_args()
    cdir = CYC / a.cycle
    if not (cdir / "model_book.json").exists():
        print(f"!! {cdir}/model_book.json 없음", file=sys.stderr)
        sys.exit(2)

    if a.reduce:
        merged = {}
        parts = sorted(cdir.glob("_flow20.part*.json"))
        for p in parts:
            merged.update(json.loads(p.read_text(encoding="utf-8")))
        outp = cdir / "_flow20.json"
        outp.write_text(json.dumps(merged, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        ok = sum(1 for v in merged.values() if "sum20" in v)
        print(f"[reduce] {a.cycle}: {len(merged)} 종목(정상 {ok}, "
              f"결손 {len(merged)-ok}, 조각 {len(parts)}) → {outp}",
              file=sys.stderr)
        return

    rows = load_rows(cdir)
    total = len(rows)
    if a.worker is not None:
        off = a.worker * a.batch
        rows = rows[off:off + a.batch]
        shard = cdir / f"_flow20.part{a.worker}.json"
        tag = f"워커{a.worker} [{off}:{off+len(rows)}]/{total}"
    else:
        if a.limit:
            rows = rows[:a.limit]
        shard = cdir / "_flow20.part_serial.json"
        tag = f"직렬 {len(rows)}/{total}"
    if not rows:
        print(f"[{tag}] 대상 없음(범위 초과)", file=sys.stderr)
        return

    res = json.loads(shard.read_text(encoding="utf-8")) if shard.exists() else {}
    print(f"[{a.cycle}] {tag} 시작 (기존 {len(res)})", file=sys.stderr)
    for i, r in enumerate(rows, 1):
        c = r["code"]
        if c in res and ("sum20" in res[c] or res[c].get("err") == "frgn_depth"):
            continue                                  # 이미 됨(결손 확정 포함)
        res[c] = collect_one(c, r["pivot_date"])
        if i % 20 == 0:
            shard.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
            print(f"  {i}/{len(rows)} ...", file=sys.stderr)
        time.sleep(0.05)
    shard.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    ok = sum(1 for v in res.values() if "sum20" in v)
    print(f"[{tag} 끝] {len(res)}종목(정상 {ok}) → {shard.name}. "
          f"모두 끝나면 `--cycle {a.cycle} --reduce`", file=sys.stderr)


if __name__ == "__main__":
    main()

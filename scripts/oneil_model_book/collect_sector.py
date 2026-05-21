"""[가드RT·패키지C] 유니버스 업종(섹터) 매핑 — 핫섹터 가드용.

695/유니버스만 induty_code 보유(winners+ctrl). 미보유분만 DART 조회.
collect_volume.py 와 *동일* 샤드 인터페이스(--worker/--workers-total/
--reduce/--limit). 결손=결손(추정 금지). KSIC≠실제테마(기존 인지).

출력: research/oneil-model-book/_universe_sector.json {code: induty3}
      (+ _universe_sector_meta.json {code:{src|error}})
샤드: --worker K 는 _universe_sector.partK.json 에만 기록.
사용:
  병렬:  python collect_sector.py --worker K --workers-total T
  병합:  python collect_sector.py --reduce
  직렬:  python collect_sector.py
  스팟:  python collect_sector.py --limit 10
"""
import argparse
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
RES = ROOT / "research" / "oneil-model-book"
CYDIR = RES / "cycles"
PRICE_FILE = {"c2024-12": "_universe_prices_5y.json",
              "c2020-03": "_universe_prices.json"}


def target_codes():
    """두 사이클 유니버스 합집합 − 이미 induty 보유분(model_book)."""
    codes = set()
    for cid, pf in PRICE_FILE.items():
        codes |= set(json.loads((CYDIR / cid / pf)
                                .read_text(encoding="utf-8")).keys())
    have = {}
    for mb in ["c2024-12/model_book.json",
               "c2024-12-ctrl500/model_book.json",
               "c2020-03/model_book.json",
               "c2020-03-ctrl500/model_book.json"]:
        p = CYDIR / mb
        if p.exists():
            for r in json.loads(p.read_text(encoding="utf-8")).get("rows", []):
                ic = r.get("induty_code")
                if r.get("code") and ic:
                    have[r["code"]] = str(ic)[:3]
    missing = sorted(c for c in codes if c not in have)
    return have, missing


def do_reduce():
    base = RES / "_universe_sector.json"
    SEC = json.loads(base.read_text(encoding="utf-8")) if base.exists() else {}
    have, _ = target_codes()
    SEC.update({k: v for k, v in have.items() if k not in SEC})  # 보유분 흡수
    for sp in sorted(glob.glob(str(RES / "_universe_sector.part*.json"))):
        for k, v in json.loads(Path(sp).read_text(encoding="utf-8")).items():
            SEC.setdefault(k, v)
    base.write_text(json.dumps(SEC, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"[reduce] sector {len(SEC)}종 → {base}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", type=int, default=None)
    ap.add_argument("--workers-total", type=int, default=12)
    ap.add_argument("--reduce", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    if a.reduce:
        do_reduce()
        return

    from canslim_lib.fetch import resolve_corp_code, load_corp_code_map
    from collect_variables import dart_company

    have, missing = target_codes()
    if a.limit > 0:
        missing = missing[:a.limit]
    if a.worker is not None:
        bs = -(-len(missing) // a.workers_total)
        missing = missing[a.worker * bs:(a.worker + 1) * bs]
        outp = RES / f"_universe_sector.part{a.worker}.json"
    else:
        outp = RES / "_universe_sector.json"
    SEC = json.loads(outp.read_text(encoding="utf-8")) \
        if outp.exists() else {}
    if a.worker is None:
        SEC.update({k: v for k, v in have.items() if k not in SEC})

    cmap = load_corp_code_map()
    n = len(missing)
    got = miss = 0
    print(f"[sector{('' if a.worker is None else ' w%d' % a.worker)}] "
          f"미보유 {n}종 조회 → {outp.name}", file=sys.stderr)
    for i, code in enumerate(missing, 1):
        if code in SEC and not a.refresh:
            continue
        try:
            corp = resolve_corp_code(code, cmap)[0]
            ic = (dart_company(corp) or {}).get("induty_code") if corp else None
            if ic:
                SEC[code] = str(ic)[:3]
                got += 1
            else:
                miss += 1
        except Exception:
            miss += 1
        if i % 40 == 0:
            print(f"  .. {i}/{n} (수집 {got}, 결손 {miss})", file=sys.stderr)
            outp.write_text(json.dumps(SEC, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        time.sleep(0.1)
    outp.write_text(json.dumps(SEC, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"[sector 끝] 수집 {got} 결손 {miss} 누적 {len(SEC)} → {outp}. "
          f"{'모두 끝나면 --reduce' if a.worker is not None else ''}",
          file=sys.stderr)


if __name__ == "__main__":
    main()

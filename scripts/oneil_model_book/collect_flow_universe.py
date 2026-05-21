"""[가드RT·패키지B] 유니버스 일별 수급(외인/기관) 수집 — I가드용.

canslim_lib.criteria_i.fetch_naver_org_flow 재사용(네이버, ~2010+,
종목당 다(多)페이지·느림=병목). collect_volume.py 와 *동일* 샤드
인터페이스. **부분수집 허용·결손=결손(추정 금지)**. 네이버는 *최근
구간 위주* — 오래된 구간 결손 불가피 → D 에서 I '판정보류'(제외 아님).

출력: cycles/<cyc>/_universe_flow.json
        {code:{"d":[],"fgn":[],"org":[]}}
      cycles/<cyc>/_universe_flow_meta.json {code:{n,first,last|error}}
사용:
  병렬:  python collect_flow_universe.py --cycle c2024-12 --worker K --workers-total T
  병합:  python collect_flow_universe.py --cycle c2024-12 --reduce
  직렬:  python collect_flow_universe.py --cycle c2024-12
  스팟:  python collect_flow_universe.py --cycle c2024-12 --limit 3
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
CYDIR = ROOT / "research" / "oneil-model-book" / "cycles"
PRICE_FILE = {"c2024-12": "_universe_prices_5y.json",
              "c2020-03": "_universe_prices.json"}


def universe_codes(cid):
    return list(json.loads((CYDIR / cid / PRICE_FILE[cid])
                           .read_text(encoding="utf-8")).keys())


def do_reduce(cid):
    od = CYDIR / cid
    base = od / "_universe_flow.json"
    FL = json.loads(base.read_text(encoding="utf-8")) if base.exists() else {}
    mb = od / "_universe_flow_meta.json"
    MT = json.loads(mb.read_text(encoding="utf-8")) if mb.exists() else {}
    for sp in sorted(glob.glob(str(od / "_universe_flow.part*.json"))):
        for k, v in json.loads(Path(sp).read_text(encoding="utf-8")).items():
            FL.setdefault(k, v)
    for sp in sorted(glob.glob(str(od / "_universe_flow_meta.part*.json"))):
        for k, v in json.loads(Path(sp).read_text(encoding="utf-8")).items():
            MT.setdefault(k, v)
    base.write_text(json.dumps(FL, ensure_ascii=False), encoding="utf-8")
    mb.write_text(json.dumps(MT, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"[reduce] {cid} flow {len(FL)}종 → {base}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", required=True, choices=list(PRICE_FILE))
    ap.add_argument("--worker", type=int, default=None)
    ap.add_argument("--workers-total", type=int, default=18)
    ap.add_argument("--pages", type=int, default=30,
                    help="네이버 페이지(많을수록 과거↑·느림). 결손=결손")
    ap.add_argument("--reduce", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--codes-file", default=None,
                    help="이 파일의 코드만 수집(매수후보 한정·범위축소)")
    a = ap.parse_args()

    if a.reduce:
        do_reduce(a.cycle)
        return

    from canslim_lib.criteria_i import fetch_naver_org_flow

    if a.codes_file:
        cf = Path(a.codes_file)
        if not cf.is_absolute():
            cf = ROOT / "research" / "oneil-model-book" / cf
        codes = [x.strip() for x in cf.read_text(encoding="utf-8").splitlines()
                 if x.strip()]
    else:
        codes = universe_codes(a.cycle)
    if a.limit > 0:
        codes = codes[:a.limit]
    od = CYDIR / a.cycle
    if a.worker is not None:
        bs = -(-len(codes) // a.workers_total)
        codes = codes[a.worker * bs:(a.worker + 1) * bs]
        op = od / f"_universe_flow.part{a.worker}.json"
        om = od / f"_universe_flow_meta.part{a.worker}.json"
    else:
        op, om = od / "_universe_flow.json", od / "_universe_flow_meta.json"
    FL = json.loads(op.read_text(encoding="utf-8")) if op.exists() else {}
    MT = json.loads(om.read_text(encoding="utf-8")) if om.exists() else {}
    n = len(codes)
    got = miss = 0
    print(f"[flow{('' if a.worker is None else ' w%d' % a.worker)}] "
          f"{a.cycle} {n}종 (pages={a.pages}) → {op.name}", file=sys.stderr)
    for i, code in enumerate(codes, 1):
        if code in FL and not a.refresh:
            continue
        try:
            fr = sorted(fetch_naver_org_flow(code, pages=a.pages,
                                             sleep_ms=180),
                        key=lambda r: r["date"])
        except Exception as e:
            MT[code] = {"error": f"{type(e).__name__}:{str(e)[:40]}"}
            miss += 1
            continue
        if not fr:
            MT[code] = {"error": "결손(수급 없음/네이버 미제공)"}
            miss += 1
            continue
        d = [r["date"] for r in fr]
        FL[code] = {"d": d,
                    "fgn": [int(r.get("fgn_net") or 0) for r in fr],
                    "org": [int(r.get("org_net") or 0) for r in fr]}
        MT[code] = {"n": len(d), "first": d[0], "last": d[-1]}
        got += 1
        if i % 20 == 0:
            print(f"  .. {i}/{n} (수집 {got}, 결손 {miss})", file=sys.stderr)
            op.write_text(json.dumps(FL, ensure_ascii=False),
                          encoding="utf-8")
            om.write_text(json.dumps(MT, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        time.sleep(0.15)
    op.write_text(json.dumps(FL, ensure_ascii=False), encoding="utf-8")
    om.write_text(json.dumps(MT, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"[flow 끝] 수집 {got} 결손 {miss} 누적 {len(FL)} → {op}. "
          f"{'모두 끝나면 --reduce' if a.worker is not None else ''}",
          file=sys.stderr)


if __name__ == "__main__":
    main()

"""[가드RT·패키지A] 유니버스 일별 거래량 수집 — '거래량-조용' 가드용.

가격파일엔 종가만 있어 거래량-조용(≤1.2×50일평균) 가드를 실시간
재현 못 함. FDR(OHLCV+Volume, 2018+ NA0% 실측)로 거래량만 수집.
가격은 기존 _universe_prices*.json 재사용. 결손=결손(추정 금지).

출력: cycles/<cyc>/_universe_volume.json   {code:{"d":[],"v":[]}}
      cycles/<cyc>/_universe_volume_meta.json {code:{n,first,last|error}}
재실행 안전·샤드 병렬(collect_ctrl500 패턴):
  1창 1회:  python collect_volume.py --cycle c2024-12 --setup-only(생략가)
  병렬:     python collect_volume.py --cycle c2024-12 --worker 0..K
  병합:     python collect_volume.py --cycle c2024-12 --reduce
  직렬재개: python collect_volume.py --cycle c2024-12   (기본)
  스팟:     python collect_volume.py --cycle c2024-12 --limit 5

한계: FDR 거래량 단위/분할·액면 정정거래 보정 여부 불명(주석).
대상 사이클=유니버스 가격파일 키. anchor−3y~cycle_end(선행상승·RS
룩백 정합).
"""
import argparse
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CYDIR = ROOT / "research" / "oneil-model-book" / "cycles"

PRICE_FILE = {                       # 사이클별 유니버스 가격파일(키=대상)
    "c2024-12": "_universe_prices_5y.json",
    "c2020-03": "_universe_prices.json",
}


def cycle_window(cid):
    ci = json.loads((CYDIR / "cycles_index.json").read_text(encoding="utf-8"))
    lst = ci["cycles"] if isinstance(ci, dict) else ci
    for c in lst:
        if c["cycle_id"] == cid:
            return c["anchor"], c["cycle_end"]
    raise SystemExit(f"cycle {cid} not in cycles_index.json")


def _shift_y(iso, dy):
    y, m, d = iso.split("-")
    return f"{int(y)+dy:04d}-{m}-{d}"


def universe_codes(cid):
    pf = CYDIR / cid / PRICE_FILE[cid]
    return list(json.loads(pf.read_text(encoding="utf-8")).keys())


def collect(cid, codes, fdr, px_start, cend, out_px, out_mt,
            shard=None, refresh=False):
    PX = json.loads(out_px.read_text(encoding="utf-8")) \
        if (out_px.exists() and shard is None) else {}
    MT = json.loads(out_mt.read_text(encoding="utf-8")) \
        if (out_mt.exists() and shard is None) else {}
    done = set(PX) | set(MT)
    n = len(codes)
    got = miss = 0
    for i, code in enumerate(codes, 1):
        if code in done and not refresh:
            continue
        try:
            df = fdr.DataReader(code, px_start, cend)
        except Exception as e:
            MT[code] = {"error": f"{type(e).__name__}:{str(e)[:50]}"}
            miss += 1
            continue
        if df is None or df.empty or "Volume" not in df:
            MT[code] = {"error": "결손(거래량 없음)"}
            miss += 1
            continue
        df = df[df["Volume"].notna()]
        d = [x.strftime("%Y-%m-%d") for x in df.index]
        v = [int(x) for x in df["Volume"]]
        if len(d) < 60:
            MT[code] = {"error": f"결손(거래일<60: {len(d)})"}
            miss += 1
            continue
        PX[code] = {"d": d, "v": v}
        MT[code] = {"n": len(d), "first": d[0], "last": d[-1]}
        got += 1
        if i % 50 == 0:
            print(f"  .. {i}/{n} (수집 {got}, 결손 {miss})", file=sys.stderr)
            out_px.write_text(json.dumps(PX, ensure_ascii=False),
                              encoding="utf-8")
            out_mt.write_text(json.dumps(MT, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        time.sleep(0.12)
    out_px.write_text(json.dumps(PX, ensure_ascii=False), encoding="utf-8")
    out_mt.write_text(json.dumps(MT, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    return got, miss, len(PX)


def do_reduce(cid, out_dir):
    base = out_dir / "_universe_volume.json"
    PX = json.loads(base.read_text(encoding="utf-8")) if base.exists() else {}
    MT = {}
    mb = out_dir / "_universe_volume_meta.json"
    if mb.exists():
        MT = json.loads(mb.read_text(encoding="utf-8"))
    for sp in sorted(glob.glob(str(out_dir / "_universe_volume.part*.json"))):
        for k, val in json.loads(Path(sp).read_text(encoding="utf-8")).items():
            PX.setdefault(k, val)
    for sp in sorted(glob.glob(str(out_dir
                                   / "_universe_volume_meta.part*.json"))):
        for k, val in json.loads(Path(sp).read_text(encoding="utf-8")).items():
            MT.setdefault(k, val)
    base.write_text(json.dumps(PX, ensure_ascii=False), encoding="utf-8")
    mb.write_text(json.dumps(MT, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"[reduce] {cid}: {len(PX)}종 병합 → {base}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", required=True, choices=list(PRICE_FILE))
    ap.add_argument("--worker", type=int, default=None,
                    help="병렬 K번째(0부터). batch=ceil(N/창수)")
    ap.add_argument("--workers-total", type=int, default=5)
    ap.add_argument("--reduce", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help=">0 스팟체크")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    out_dir = CYDIR / a.cycle
    if a.reduce:
        do_reduce(a.cycle, out_dir)
        return

    try:
        import FinanceDataReader as fdr
    except ModuleNotFoundError:
        raise SystemExit("pip install finance-datareader")

    anchor, cend = cycle_window(a.cycle)
    px_start = _shift_y(anchor, -3)
    codes = universe_codes(a.cycle)
    if a.limit > 0:
        codes = codes[:a.limit]

    if a.worker is not None:
        tot = len(codes)
        bs = -(-tot // a.workers_total)
        codes = codes[a.worker * bs:(a.worker + 1) * bs]
        out_px = out_dir / f"_universe_volume.part{a.worker}.json"
        out_mt = out_dir / f"_universe_volume_meta.part{a.worker}.json"
        print(f"[worker {a.worker}] {len(codes)}종 → {out_px.name}",
              file=sys.stderr)
        g, m, t = collect(a.cycle, codes, fdr, px_start, cend, out_px,
                          out_mt, shard=a.worker, refresh=a.refresh)
        print(f"[worker {a.worker} 끝] 수집{g} 결손{m}. 모두 끝나면 "
              f"--reduce", file=sys.stderr)
        return

    out_px = out_dir / "_universe_volume.json"
    out_mt = out_dir / "_universe_volume_meta.json"
    print(f"[{a.cycle}] 거래량 수집 {len(codes)}종 ({px_start}~{cend})"
          f"{' [스팟]' if a.limit else ''}", file=sys.stderr)
    g, m, t = collect(a.cycle, codes, fdr, px_start, cend, out_px, out_mt,
                      refresh=a.refresh)
    print(f"[{a.cycle}] 완료: 누적 {t}종 (이번 수집 {g}, 결손 {m}) "
          f"→ {out_px}", file=sys.stderr)


if __name__ == "__main__":
    main()

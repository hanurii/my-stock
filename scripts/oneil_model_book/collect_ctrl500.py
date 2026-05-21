"""안오름(비위너) 500종목 — 세션 분할 / 병렬 재개형 수집 러너.

위너 200에서 본 변별축을 *안오름* 쪽에서 거꾸로 검증할 대조군 대량
표본. 출력 사이클 = c2024-12-ctrl500 (OMB_CYCLE). 구간은 c2024-12와
동일(cyclecfg 폴백). 변수 스키마는 위너 200과 100% 동일.

모드:
  --setup            1회 셋업만 (500표본→detect_pivot→compute_rs). 멱등.
  --worker K         병렬: K번째 100개(offset=K*batch)를 자기 조각
                     model_book.partK.json 에만 기록(공용 파일 미접촉).
                     창 5개면 K=0..4 동시 실행 가능(서로 안 건드림).
  --reduce           모든 조각(+있으면 model_book.json)을 code 기준
                     합쳐 model_book.json 생성, 섹터수 전체 재계산.
  (인자 없음)        단일 세션 재개: 다음 batch개를 --merge로 이어붙임
                     (직렬용, 기존 동작).

병렬 절차:
  1) (한 창에서 1회)  python collect_ctrl500.py --setup
  2) (창 0~4 동시)    python collect_ctrl500.py --worker 0   ... --worker 4
  3) (모두 끝난 뒤)   python collect_ctrl500.py --reduce
부분 실패/중단해도 안전: 워커는 자기 조각만 덮어쓰며 재실행=그 조각만
다시. reduce 는 있는 조각만으로도 동작(결손은 결손대로, 추정 없음).
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
N_SAMPLE, SEED = 500, 42
# main()에서 인자로 설정 (기본 = 기존 c2024-12-ctrl500 동작)
CYCLE = "c2024-12"            # 가격창·앵커 (cycles_index 의 실 사이클 id)
OUTDIR = "c2024-12-ctrl500"   # 출력 폴더 (OMB_OUTDIR)
SRC = "c2024-12"              # 위너 표본 출처 사이클
CDIR = ROOT / "research" / "oneil-model-book" / "cycles" / OUTDIR


def run(argv, label):
    env = {**os.environ, "OMB_CYCLE": CYCLE, "OMB_OUTDIR": OUTDIR,
           "PYTHONIOENCODING": "utf-8"}
    print(f"\n>>> {label}: {' '.join(argv)}", file=sys.stderr)
    r = subprocess.run([sys.executable, *argv], cwd=str(ROOT), env=env)
    if r.returncode != 0:
        print(f"!! {label} 실패 (exit {r.returncode}) — 중단", file=sys.stderr)
        sys.exit(r.returncode)


def ensure_setup():
    if not (CDIR / "winners_final.json").exists():
        run(["scripts/oneil_model_book/build_control_sample.py",
             "--n", str(N_SAMPLE), "--seed", str(SEED),
             "--src", SRC, "--outdir", OUTDIR], "표본 500 생성")
    if not (CDIR / "pivots.json").exists():
        run(["scripts/oneil_model_book/detect_pivot.py"], "pivot 탐지(1회)")
    if not (CDIR / "rs.json").exists():
        run(["scripts/oneil_model_book/compute_rs.py"], "RS 계산(1회)")


def pivots_total():
    return len(json.loads((CDIR / "pivots.json").read_text(encoding="utf-8"))["pivots"])


def do_reduce(batch):
    total = pivots_total()
    by_code = {}
    srcs = sorted(glob.glob(str(CDIR / "model_book.part*.json")))
    mb = CDIR / "model_book.json"
    if mb.exists():
        srcs.append(str(mb))                       # 직렬분도 흡수
    for sp in srcs:
        for r in json.loads(Path(sp).read_text(encoding="utf-8")).get("rows", []):
            c = r.get("code")
            cur = by_code.get(c)
            # 정상 행이 error 행을 덮어쓰도록(반대는 금지)
            if cur is None or (cur.get("error") and not r.get("error")):
                by_code[c] = r
    rows = list(by_code.values())

    def pfx(c):
        return str(c)[:3] if c else None
    grp = Counter(pfx(r.get("induty_code")) for r in rows if r.get("induty_code"))
    for r in rows:
        p = pfx(r.get("induty_code"))
        r["induty_group3"] = p
        r["sector_group_winner_count"] = grp.get(p) if p else None

    out = {"generated_at": "reduced", "principle": "CAN SLIM 미적용. raw 값만.",
           "note": f"안오름 대조군 {len(rows)}/{total} (조각 {len(srcs)}개 병합, "
                   f"섹터수 전체 재계산, 결손=결손 유지·추정 없음)",
           "rows": rows}
    mb.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in rows if not r.get("error"))
    print(f"\n[reduce 완료] {len(rows)}/{total} 행 (정상 {ok}, 조각 {len(srcs)}) "
          f"→ {mb}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--worker", type=int, default=None,
                    help="병렬 K번째(0부터). offset=K*batch")
    ap.add_argument("--reduce", action="store_true")
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--cycle", default="c2024-12",
                    help="가격창 사이클 id (cycles_index, 예: c2020-03)")
    ap.add_argument("--outdir", default="c2024-12-ctrl500",
                    help="출력 폴더 (예: c2020-03-ctrl500)")
    ap.add_argument("--src", default="c2024-12",
                    help="위너 표본 출처 사이클 (예: c2020-03)")
    a = ap.parse_args()

    global CYCLE, OUTDIR, SRC, CDIR
    CYCLE, OUTDIR, SRC = a.cycle, a.outdir, a.src
    CDIR = ROOT / "research" / "oneil-model-book" / "cycles" / OUTDIR

    if a.setup:
        ensure_setup()
        print(f"\n[셋업 완료] 표본·pivot·RS 준비됨. 총 {pivots_total()}개. "
              f"이제 창 0~4에서 --worker 0..4 동시 실행 가능.", file=sys.stderr)
        return

    if a.reduce:
        do_reduce(a.batch)
        return

    if a.worker is not None:
        if not (CDIR / "pivots.json").exists() or not (CDIR / "rs.json").exists():
            print("!! 셋업 미완 — 먼저 한 창에서 `--setup` 실행 후 워커 시작.",
                  file=sys.stderr)
            sys.exit(2)
        total = pivots_total()
        off = a.worker * a.batch
        if off >= total:
            print(f"[워커 {a.worker}] offset {off} ≥ 총 {total} — 할 일 없음.",
                  file=sys.stderr)
            return
        lim = min(a.batch, total - off)
        print(f"\n[워커 {a.worker}] {off+1}~{off+lim}/{total} → "
              f"model_book.part{a.worker}.json", file=sys.stderr)
        run(["scripts/oneil_model_book/collect_variables.py",
             "--offset", str(off), "--limit", str(lim),
             "--shard", f"part{a.worker}"], f"워커{a.worker} 수집")
        print(f"\n[워커 {a.worker} 끝] 조각 기록 완료. 5창 모두 끝나면 한 창에서 "
              f"`python scripts/oneil_model_book/collect_ctrl500.py --reduce`.",
              file=sys.stderr)
        return

    # 인자 없음 = 단일 세션 재개(직렬, 기존 동작)
    ensure_setup()
    total = pivots_total()
    mb = CDIR / "model_book.json"
    done_codes = ({r.get("code") for r in
                   json.loads(mb.read_text(encoding="utf-8")).get("rows", [])}
                  if mb.exists() else set())
    pivots = json.loads((CDIR / "pivots.json").read_text(encoding="utf-8"))["pivots"]
    done = 0
    for rec in pivots:
        if rec.get("code") in done_codes:
            done += 1
        else:
            break
    if done >= total:
        print(f"[완료] 전체 {total} 수집 끝.", file=sys.stderr)
        return
    lim = min(a.batch, total - done)
    print(f"[세션] 누적 {done}/{total} → {done+1}~{done+lim}", file=sys.stderr)
    run(["scripts/oneil_model_book/collect_variables.py",
         "--offset", str(done), "--limit", str(lim), "--merge"], "세션 수집")
    print(f"[세션 끝] 다음 세션: 같은 명령 다시. (병렬 원하면 --worker 사용)",
          file=sys.stderr)


if __name__ == "__main__":
    main()

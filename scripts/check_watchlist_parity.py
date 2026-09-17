"""페이지와 pivot_alert 가 «같은 종목 집합»을 내는지 대조한다.

왜 있나:
  /stocks/sepa 의 티어 분류(sepaPatterns.ts)를 pivot_alert.py 가 파이썬으로 옮겨
  적었다. 같은 규칙을 두 언어로 손으로 맞추면 갈라진다. 값이 같은지만 봐서는
  «어디서 재느냐»가 다른 것을 못 잡는다(CLAUDE.md §1.5).
  그래서 페이지 코드 «자체»를 돌린 결과와 맞댄다.

쓰기:
  python -X utf8 scripts/check_watchlist_parity.py
  (npx tsx 로 scripts/dump_page_watchlist.ts 를 돌려 기준을 만든다)

어긋나면 종목과 티어를 찍고 종료 코드 1 을 낸다.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pivot_alert  # noqa: E402


def dump_page_side() -> dict[str, dict[str, str]]:
    """페이지 로직을 그대로 돌려 {파일: {코드: 티어}} 를 받는다."""
    with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False,
                                     encoding="utf-8") as fh:
        out_path = Path(fh.name)
    try:
        with out_path.open("w", encoding="utf-8") as fh:
            r = subprocess.run(["npx", "tsx", "scripts/dump_page_watchlist.ts"],
                               cwd=str(ROOT), stdout=fh, stderr=subprocess.PIPE,
                               text=True, shell=True)
        if r.returncode != 0:
            raise RuntimeError(f"npx tsx 실패: {r.stderr[-400:]}")
        return json.loads(out_path.read_text(encoding="utf-8"))
    finally:
        out_path.unlink(missing_ok=True)


def dump_python_side() -> dict[str, dict[str, str]]:
    """pivot_alert 의 분류를 파일별로(«합치기 전») 뽑는다."""
    exclusions = pivot_alert.load_exclusions()

    out: dict[str, dict[str, str]] = {}
    for fname, (_pattern, kind, _field) in pivot_alert.SOURCES.items():
        path = pivot_alert.DATA_DIR / fname
        rows: dict[str, str] = {}
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            for raw in d.get("candidates") or []:
                if raw["code"] in exclusions:
                    continue
                tier = pivot_alert.classify(raw, kind)
                if tier:
                    rows[raw["code"]] = tier
        out[fname] = rows
    return out


def main() -> int:
    page = dump_page_side()
    py = dump_python_side()

    bad = 0
    print(f"{'파일':<38}{'페이지':>7}{'파이썬':>8}  판정")
    for fname in sorted(set(page) | set(py)):
        a, b = page.get(fname, {}), py.get(fname, {})
        same = a == b
        bad += 0 if same else 1
        print(f"{fname:<38}{len(a):>7}{len(b):>8}  {'일치' if same else '어긋남'}")
        if same:
            continue
        for code in sorted(set(a) | set(b)):
            ta, tb = a.get(code), b.get(code)
            if ta != tb:
                print(f"    {code}  페이지={ta}  파이썬={tb}")

    # 합집합도 따로 센다 — 파일별로 맞아도 합칠 때 어긋날 수 있다
    ua = {c for v in page.values() for c in v}
    ub = {c for v in py.values() for c in v}
    print(f"\n종목 합집합 — 페이지 {len(ua)} · 파이썬 {len(ub)} · "
          f"{'일치' if ua == ub else '어긋남'}")
    if ua != ub:
        bad += 1
        print("  페이지에만:", sorted(ua - ub))
        print("  파이썬에만:", sorted(ub - ua))

    print("\n판정:", "같은 집합" if bad == 0 else f"어긋난 곳 {bad}군데")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

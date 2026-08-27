# -*- coding: utf-8 -*-
r"""91d — 월말 패널 «어긋남»의 분해. **/tmp 에 있던 것을 커밋본으로 올린다.**

왜 이 파일이 필요한가
---------------------
90번의 「Sharadar 는 정적이 아니다」가 **이 계산 위에 서 있는데** 산출 코드가 `/tmp` 에 있었다.
[[verification-failure-modes]] 질문 12 — **숫자에 넷(값·커밋된 스크립트·커밋된 입력·정의)**.
검증 세션이 정확히 그걸 지적했다(`35f2aaa4`).

🚨 **그리고 검증 세션이 「산수가 안 닫힌다」고 했다** — `6,495 vs 5,948+547+762=7,257`.
   **닫힌다.** 762 는 «다름»의 갈래가 아니라 **별개 범주**다:
       771,213(겹침) = 같음 763,956 + **다름 6,495** + **없음 762**
       그중 다름 6,495 = 2026-08 5,948 + 분할 547
   → 이 스크립트는 **그 배타성을 `assert` 로 강제한다.** 말로 해명하지 않는다.
"""
from __future__ import annotations

import collections
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import us_loader as U                                          # noqa: E402

OUT = ROOT / ".cache" / "bt5y" / "out"
OLD = OUT / "61-monthly-us.json"
NEW = OUT / "91-monthly-us-full.json"

GREW_YM = "2026-08"        # 자료 끝이 8/21 → 8/26 로 자란 달
SPLIT_FROM = "2026-08-20"  # 옛 스냅숏 이후의 분할만 본다
EPS = 1e-9


def main() -> int:
    o = json.loads(OLD.read_text(encoding="utf-8"))["monthly"]
    n = json.loads(NEW.read_text(encoding="utf-8"))["monthly"]

    same = 0
    diff_grew = []          # ① 마지막 달이 자람
    diff_other = []         # ② 그 밖 (분할 후보)
    missing = []            # ③ 새 파일에 없음
    for t, dd in o.items():
        nd = n.get(t)
        for ym, v in dd.items():
            nv = nd.get(ym) if nd is not None else None
            if nv is None:
                missing.append((t, ym))
            elif abs(nv - v) <= EPS * max(1.0, abs(v)):
                same += 1
            elif ym == GREW_YM:
                diff_grew.append((t, ym, v, nv))
            else:
                diff_other.append((t, ym, v, nv))

    tot = sum(len(d) for d in o.values())
    n_diff = len(diff_grew) + len(diff_other)
    print("겹치는 칸 %s" % "{:,}".format(tot), flush=True)
    print("  같음 %s · **다름 %s** · 없음 %s"
          % ("{:,}".format(same), "{:,}".format(n_diff), "{:,}".format(len(missing))),
          flush=True)
    print("  다름의 분해 — ① 마지막 달이 자람 %s · ② 그 밖 %s"
          % ("{:,}".format(len(diff_grew)), "{:,}".format(len(diff_other))), flush=True)

    # ★ 배타성·완전성을 **코드가 강제한다** (말로 해명하지 않는다)
    assert same + n_diff + len(missing) == tot, \
        "🚨 세 범주가 겹침 전체를 안 덮는다"
    assert len(diff_grew) + len(diff_other) == n_diff, \
        "🚨 다름의 두 갈래가 다름 전체를 안 덮는다"
    assert all(ym == GREW_YM for _t, ym, _v, _nv in diff_grew)
    assert all(ym != GREW_YM for _t, ym, _v, _nv in diff_other)
    print("  ✅ 배타·완전 확인: 같음+다름+없음 = 겹침 · ①+② = 다름 (assert 통과)", flush=True)

    # ── ② 를 actions 표로 «맞혀» 본다 ────────────────────────────────────
    bycode = collections.defaultdict(list)
    for t, ym, v, nv in diff_other:
        if v:
            bycode[t].append(nv / v)
    print("\n② 그 밖 %s칸 = **종목 %d개**" % ("{:,}".format(len(diff_other)), len(bycode)),
          flush=True)

    want = set(bycode)
    splits = collections.defaultdict(list)
    with zipfile.ZipFile(U.ACTIONS_ZIP) as z:
        f = io.TextIOWrapper(z.open(z.infolist()[0].filename), encoding="utf-8")
        for r in csv.DictReader(f):
            if r["ticker"] in want and r["action"] == "split" and r["date"] >= SPLIT_FROM:
                splits[r["ticker"]].append((r["date"], float(r["value"])))

    ok = unexplained = 0
    print("  %-8s %6s %11s  %-26s %s" % ("종목", "칸", "필요배수", "actions split", "판정"),
          flush=True)
    for t in sorted(bycode):
        rs = bycode[t]
        need = sum(rs) / len(rs)
        hs = splits.get(t, [])
        if hs:
            # 여러 건이면 곱한다 (배수는 곱셈으로 쌓인다)
            v = 1.0
            for _d, x in hs:
                v *= x
            pred = 1.0 / v
            good = abs(pred - need) <= 0.02 * max(1.0, need)
            ok += good
            print("  %-8s %6d %11.4f  %-26s %s"
                  % (t, len(rs), need, str([(d, x) for d, x in hs])[:26],
                     "✅ 일치" if good else "🚨 안 맞음(예측 %.4f)" % pred), flush=True)
        else:
            unexplained += 1
            print("  %-8s %6d %11.4f  %-26s %s" % (t, len(rs), need, "없음", "⚠️ 설명 안 됨"),
                  flush=True)
    print("\n  **분할로 설명됨 %d / %d 종목** · 설명 안 됨 %d"
          % (ok, len(bycode), unexplained), flush=True)

    # ── ③ 없어진 종목 ────────────────────────────────────────────────────
    m_by_t = collections.Counter(t for t, _ in missing)
    gone = [t for t in m_by_t if t not in n]
    print("\n③ 없음 %s칸 = 종목 %d개 (그중 **통째로 사라진 종목 %d개**)"
          % ("{:,}".format(len(missing)), len(m_by_t), len(gone)), flush=True)
    print("   상위 8: %s" % m_by_t.most_common(8), flush=True)

    print("\n" + "=" * 88, flush=True)
    print("정본 문장: 겹침 %s = 같음 %s + 다름 %s(자람 %s + 분할 %s) + 없음 %s"
          % tuple("{:,}".format(x) for x in
                  (tot, same, n_diff, len(diff_grew), len(diff_other), len(missing))),
          flush=True)
    print("=" * 88, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

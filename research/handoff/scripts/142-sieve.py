# -*- coding: utf-8 -*-
r"""142 — 「베이스의 «모양»」 체. **적합 파라미터 0개.**

사전등록 `tasks/142-base-shape.md`.

🚨 첫 줄 — **특징 함수는 `pre_*` 만 받는다. `v` 는 «안 넘긴다».**
   봉투(`entry_envelope.entry_view`)가 구조로 막고, 관문 ⓑ 가 «막히는지» 증명한다.

특징 넷 — **원전이 부호를 준 것만**
```
① 수축 개수    2~6 안인가                                    이진 (+)
② 축소비       |(c_last/c_first)^(1/(T−1)) − 0.5|             연속 (−)
④ 베이스 깊이   10~35% 안인가  (= max(contractions))            이진 (+)
⑦ 극저거래량    ≥1일인가       (detect_final_coil)              이진 (+)
```
🚨 ③(최종수축 ≤10%)·⑥(거래량 마름 수치)는 **원전이 아니라 «우리 공학값»**이다
   — 독서 노트 둘과 `docs/superpowers/specs/2026-06-29-find-vcp-design.md` §3.5 가 «둘 다» 그렇게 말한다.
   → **부지표**로만 찍는다. 판정을 승격시킬 수 없다.

점수 = 그날 후보 «안»의 백분위 순위 × 원전 부호 → 동일가중 합. **맞출 것이 없다.**
결측 = 그날 순위의 **중앙(0.5)**. 좋은 칸도 나쁜 칸도 아니게.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/142-sieve.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))

import entry_envelope as env                                    # noqa: E402
from canslim_lib.vcp import (evaluate_vcp, detect_final_coil,    # noqa: E402
                             volume_ma, DEFAULT_PARAMS)

_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_s)
_s.loader.exec_module(r102)
r91, f92a = r102.r91, r102.f92a

_s3 = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_s3)
_s3.loader.exec_module(r103)

# ═════════════════════════════════════════════════════════════════════════
# 🚨 뒤 구간 차단 — 이 블록을 고치지 말 것 (관문 ⓔ)
# ═════════════════════════════════════════════════════════════════════════
NEW = Path("D:/stock-data/uspath-warm/full")
FRONT_D0, FRONT_D1 = "1999-04-01", "2011-12-31"
YEARS = tuple(range(1999, 2012))                # ← 2012 이후는 «없다»
SPLIT = "2006-01-01"
LABELS = ROOT / "research" / "handoff" / "data" / "142-labels-frozen.json"
CACHE = ROOT / ".cache" / "bt5y" / "out"


def _guard():
    bad = [y for y in YEARS if y >= 2012]
    if bad:
        raise RuntimeError("🚨 뒤 구간 차단 — %r" % (bad,))


# ═════════════════════════════════════════════════════════════════════════
# 특징 — **봉투가 준 것만** 쓴다
# ═════════════════════════════════════════════════════════════════════════
SIGN = {"c1_count": +1, "c2_halving": -1, "c4_depth": +1, "c7_dryday": +1}
MAIN = tuple(SIGN)
SUB = ("s3_final", "s6_dryup")          # 부지표 — 판정 승격 불가


def _series(e):
    """봉투에서 «진입 전» 창만 꺼내 검출기 입력 모양으로."""
    return {"dates": e["pre_d"], "closes": e["pre_c"], "highs": e["pre_h"],
            "lows": e["pre_l"], "opens": e["pre_o"], "volumes": e["pre_v"]}


def features(e):
    """`e` = `entry_envelope.entry_view(rec)`. 🚨 `d/o/h/l/c/v` 는 «없다»."""
    s = _series(e)
    r = evaluate_vcp(s, None)
    p = DEFAULT_PARAMS
    lb = p["lookback_days"]
    cl, hi = s["closes"][-lb:], s["highs"][-lb:]
    lo, vo = s["lows"][-lb:], s["volumes"][-lb:]
    coil = detect_final_coil(hi, lo, cl, vo, volume_ma(vo, 50), len(cl) - 1, p) if cl else None
    c = r["contractions"]
    T = r["num_contractions"]
    f = {k: None for k in MAIN + SUB}
    if c:
        f["c1_count"] = 1.0 if 2 <= T <= 6 else 0.0
        # ② 「각 수축이 «직전»의 약 절반」 → 연속 비율의 «기하평균»
        if T >= 2 and c[0] > 0 and c[-1] > 0:
            f["c2_halving"] = abs((c[-1] / c[0]) ** (1.0 / (T - 1)) - 0.5)
        f["c4_depth"] = 1.0 if 10.0 <= max(c) <= 35.0 else 0.0
        f["s3_final"] = c[-1]
    if coil is not None:
        f["c7_dryday"] = 1.0 if coil["coil_extreme_days"] >= 1 else 0.0
    f["s6_dryup"] = r["volume_dryup_ratio"]
    return f


# ═════════════════════════════════════════════════════════════════════════
# 점수 — 그날 후보 «안»의 백분위 순위 × 부호. 적합 «0»
# ═════════════════════════════════════════════════════════════════════════
def _rank(vals):
    """[0,1] 백분위. 동순위는 «평균 순위». 결측(None)은 **0.5**."""
    idx = [i for i, v in enumerate(vals) if v is not None]
    out = [0.5] * len(vals)
    if not idx:
        return out
    order = sorted(idx, key=lambda i: vals[i])
    n = len(order)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        pr = 0.5 if n == 1 else ((i + j) / 2.0) / (n - 1)
        for k in range(i, j + 1):
            out[order[k]] = pr
        i = j + 1
    return out


def score_day(feats):
    """같은 날 후보들의 특징 목록 → 점수 목록. 클수록 「대박일 것 같다」."""
    sc = [0.0] * len(feats)
    for name in MAIN:
        pr = _rank([f.get(name) for f in feats])
        for i, v in enumerate(pr):
            sc[i] += SIGN[name] * v
    return sc


# ═════════════════════════════════════════════════════════════════════════
def collect():
    _guard()
    r91.TARGET, r91.STOP, r91.HALF = 30.0, 10.0, 0.5
    r91.SUB = NEW
    import _lean_load as ll
    # 🚨🚨 `_lean_load` 는 **자기 `r91` 인스턴스를 따로 가진다**(importlib 으로 다시 exec 한다).
    #    `r102.r91.SUB` 만 바꾸면 `load_combo` 는 여전히 «옛» `.cache/bt5y/sub` 를 읽는다.
    #    2026-09-01 실사고: 그래서 라벨을 «옛 자료»로 얼렸고, 「140 과 일치」가 «자명»해져 버렸다.
    ll.r91.SUB = NEW
    assert ll.r91.SUB == NEW, ll.r91.SUB
    # 🚨 **분모는 `by_f`** — 성장 둔화 필터까지 «현행 규칙»이다 (139:102-113 과 같은 코드).
    #    142 는 「현행 규칙 «위에» 베이스 모양이 무엇을 더하나」를 잰다.
    #    🚨 140 은 by2 였다 → **140 과 직접 비교 «불가»**.
    fund, ixf = f92a.load()
    ixm = {f: i for i, f in enumerate(ixf)}

    def keep_f(p):
        arq = (fund.get(p["code"]) or {}).get("ARQ") or []
        a = f92a.asof(arq, p["entry_date"]) if arq else None
        v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                      > r102.STALE_MAX)
             else r103.judge(arq, arq.index(a), ixm, 1, 2))
        return v is not False

    rows = []
    for y in YEARS:
        cf = CACHE / ("_142_y%d.json" % y)
        if cf.exists():
            rows.extend(json.loads(cf.read_text(encoding="utf-8")))
            print("   %d년 — 저장분 (누적 %d)" % (y, len(rows)), flush=True)
            continue
        by1, _c, _n = ll.load_combo((y,), FRONT_D0, FRONT_D1)
        byf = {y: [p for p in by1.get(y, []) if keep_f(p)]}
        keep = {(p["scan_date"], p["code"], p["pattern"]): p for p in byf[y]}
        e1, _b, _t = r91.replay(byf)
        out = []
        for t in e1:
            p = keep.get((t["scan_date"], t["code"], t["pattern"]))
            if p is None:
                continue
            e = env.entry_view(p)                 # 🚨 봉투 — pre_* 만
            f = features(e)
            out.append({"scan_date": t["scan_date"], "code": t["code"],
                        "pattern": t["pattern"], "entry_date": t["entry_date"],
                        "f": f})
        cf.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
        rows.extend(out)
        del by1, byf, e1, keep, out
        print("   %d년 — 누적 %d (저장)" % (y, len(rows)), flush=True)
    return rows


def main() -> int:
    print("=" * 96, flush=True)
    print("142 — 베이스의 «모양» 체 · **적합 파라미터 0개** · 앞 구간 %s ~ %s 만"
          % (FRONT_D0, FRONT_D1), flush=True)
    print("=" * 96, flush=True)

    # ── 관문 ⓑ 커닝 시험 — «먼저» ────────────────────────────────────
    print("", flush=True)
    print("관문 ⓑ 커닝 시험 (봉투가 «실제로» 막는가)", flush=True)
    rc = env._selftest()
    if rc != 0:
        print("🚨 봉투가 안 막는다. 멈춘다.", flush=True)
        return 2

    rows = collect()
    print("", flush=True)
    print("후보 **%s건**" % "{:,}".format(len(rows)), flush=True)

    # ── 관문 ⓒ 결측률 ────────────────────────────────────────────────
    miss = Counter()
    for r in rows:
        for k in MAIN + SUB:
            if r["f"].get(k) is None:
                miss[k] += 1
    print("", flush=True)
    print("관문 ⓒ 결측률 — 「수축 사슬 없음」이 만드는 결측", flush=True)
    for k in MAIN + SUB:
        print("   %-11s %6d / %6d = **%5.1f%%**%s"
              % (k, miss[k], len(rows), 100 * miss[k] / max(1, len(rows)),
                 "   ← 주판정" if k in MAIN else "   (부지표)"), flush=True)
    if miss["c1_count"] > len(rows) * 0.5:
        print("   🚨 **결측이 절반을 넘는다** — 이 판은 「모양」이 아니라 "
              "「사슬이 있나 없나」를 재는 판이다. 결론에 그렇게 적는다", flush=True)

    # ── ①④⑦ 통과율 (붕괴 여부) ─────────────────────────────────────
    print("", flush=True)
    print("이진 셋의 «통과율» (한 칸으로 붕괴하면 실질 특징 수가 준다)", flush=True)
    for k in ("c1_count", "c4_depth", "c7_dryday"):
        v = [r["f"][k] for r in rows if r["f"].get(k) is not None]
        p1 = 100 * sum(v) / max(1, len(v))
        print("   %-11s 1인 비율 **%5.1f%%** (n=%d)%s"
              % (k, p1, len(v), "   🚨 **붕괴 — 실질 특징 하나 줄어듦**"
                 if (p1 > 99.0 or p1 < 1.0) else ""), flush=True)

    # ── 점수 — 그날 후보 안에서 ──────────────────────────────────────
    byday = defaultdict(list)
    for i, r in enumerate(rows):
        byday[r["entry_date"]].append(i)
    for _d, idxs in byday.items():
        sc = score_day([rows[i]["f"] for i in idxs])
        for i, s in zip(idxs, sc):
            rows[i]["s"] = s

    # ── 관문 ⓓ 동점 ─────────────────────────────────────────────────
    allsc = [r["s"] for r in rows]
    ties = len(allsc) - len(set(allsc))
    print("", flush=True)
    print("관문 ⓓ 동점 — 서로 다른 점수 **%d개** / %d · **동점 %.1f%%** (140 은 56.3%%)"
          % (len(set(allsc)), len(allsc), 100 * ties / max(1, len(allsc))), flush=True)

    # ── 자체점검 — A ↔ B ────────────────────────────────────────────
    lab = json.loads(LABELS.read_text(encoding="utf-8"))
    keys = set(lab["front"]["keys"])
    for r in rows:
        r["win"] = "|".join((r["scan_date"], r["code"], r["pattern"])) in keys
    print("", flush=True)
    print("자체점검 — 얼린 라벨 사용 (앞 K=%d · 문턱 %+.4f%%)"
          % (lab["front"]["K"], lab["front"]["cut"]), flush=True)
    print("   맞춘 대박 %d / %d" % (sum(1 for r in rows if r["win"]),
                                   lab["front"]["K"]), flush=True)

    A = [r for r in rows if r["entry_date"] < SPLIT]
    B = [r for r in rows if r["entry_date"] >= SPLIT]
    rnd = random.Random(142)
    print("", flush=True)
    print("   %-14s %10s %10s %10s" % ("구간", "유지 50%", "유지 25%", "동전 5~95%"),
          flush=True)
    res = {}
    for name, sub in (("A 1999~2005", A), ("B 2006~2011", B), ("앞 구간 전체", rows)):
        tot = sum(1 for r in sub if r["win"])
        sc = sorted(sub, key=lambda r: -r["s"])
        cells = []
        for kp in (0.50, 0.25):
            m = max(1, int(round(len(sc) * kp)))
            cells.append(100.0 * sum(1 for r in sc[:m] if r["win"]) / max(1, tot))
        band = []
        for _ in range(2000):
            idx = rnd.sample(range(len(sub)), len(sub) // 2)
            band.append(sum(1 for i in idx if sub[i]["win"]) / max(1, tot))
        band.sort()
        res[name] = {"n": len(sub), "K": tot, "keep50": cells[0], "keep25": cells[1],
                     "coin5": 100 * band[100], "coin95": 100 * band[1900]}
        print("   %-14s %9.1f%% %9.1f%%   %4.1f~%4.1f%%"
              % (name, cells[0], cells[1], 100 * band[100], 100 * band[1900]), flush=True)
    print("", flush=True)
    print("   🚨 **적합이 «없으므로» A→B·B→A 를 나눌 필요가 없다** — 체가 «앞 구간을 안 봤다».",
          flush=True)
    print("   그래서 A·B 는 «교차검정»이 아니라 **두 구간에서 각각 잰 것**이다.", flush=True)

    (CACHE / "142-sieve.json").write_text(
        json.dumps({"n": len(rows), "miss": dict(miss), "ties_pct": 100 * ties / max(1, len(allsc)),
                    "res": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("🚨 **뒤 구간은 열지 않았습니다.**", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

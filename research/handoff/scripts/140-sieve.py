# -*- coding: utf-8 -*-
r"""140 — **체(選別)**. 「대박을 알아보는 점수」를 앞 구간에서만 만든다.

사전등록 `tasks/140-sieve.md` — **특징 8개 · 라벨은 139 코드 그대로 · 지표는 하나**.

🚨🚨 **뒤 구간(2012-01-01 이후)을 «절대» 열지 않는다.**
   `YEARS = range(1999, 2012)` 를 하드코딩하고, 그 밖 연도를 요구하면 «예외»를 던진다.
   이 파일을 고칠 때도 그 줄을 건드리지 말 것.

🚨 의뢰서의 재료 설명이 틀렸다 — 경로에 **웜업도 거래량도 없다**(`d[0] == entry_date`).
   그래서 진입 «전» 값은 전부 **월봉 패널 · 시점 시총 · 시점 실적**에서 가져온다.

내는 것
------
```
research/handoff/data/140-sieve-const.json   ← 검증 세션이 «그대로» 쓸 상수
   {"features": [...], "bins": {...}, "logl": {...}, "prior": ...}
```
그리고 `score(feat)` 를 이 파일에서 import 해 쓰면 된다:
```python
import importlib.util as u
s = u.spec_from_file_location("s140", ".../140-sieve.py"); m = u.module_from_spec(s)
s.loader.exec_module(m)
m.load_const()                 # 상수 적재 (한 번)
m.score(m.features(t, p))      # 클수록 「대박일 것 같다」
```

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/140-sieve.py
"""
from __future__ import annotations

import bisect
import datetime as _dt
import importlib.util as _u
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                          # noqa: E402

_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_s)
_s.loader.exec_module(r102)
r91, f92a = r102.r91, r102.f92a

_s3 = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_s3)
_s3.loader.exec_module(r103)

# ═════════════════════════════════════════════════════════════════════════
# 0. 🚨 뒤 구간 차단 — 이 블록을 고치지 말 것
# ═════════════════════════════════════════════════════════════════════════
FRONT_D0, FRONT_D1 = "1999-04-01", "2011-12-31"
YEARS = tuple(range(1999, 2012))                # ← 2012 이후는 «없다»
SPLIT = "2006-01-01"                            # 자체점검 A|B 경계
# 관문 ⑳ — 13년치를 «통째로» 실었을 때의 진입 수(2026-08-31 실측). 해마다 나눠 실어도 같아야 한다.
N_EV_GATE = 4231


def _guard(years, d1):
    bad = [y for y in years if y >= 2012]
    if bad:
        raise RuntimeError("🚨 뒤 구간 차단 — 2012 이후 연도를 요구했다: %r" % (bad,))
    if d1 > FRONT_D1:
        raise RuntimeError("🚨 뒤 구간 차단 — d1 이 %s 를 넘었다: %s" % (FRONT_D1, d1))


# ═════════════════════════════════════════════════════════════════════════
# 1. 라벨 규약 — 139 그대로
# ═════════════════════════════════════════════════════════════════════════
TARGET, STOP, HALF = 30.0, 10.0, 0.5
TOPS = (0.01, 0.05, 0.10)                       # 주지표는 0.05
KEEPS = (0.50, 0.25, 0.10)                      # 주지표는 0.50
ALPHA = 20.0                                    # 라플라스 평활
NBIN = 4                                        # 🚨 4분위 — 두뇌 세션 권고, **값 보기 전** 확정
CONST = ROOT / "research" / "handoff" / "data" / "140-sieve-const.json"
CAP_PIT = Path(r"D:\stock-data\derived\95-cap-pit.json")
CACHE = ROOT / ".cache" / "bt5y" / "out"       # 해마다 적어 두는 곳 (중간에 멎어도 다시 안 돈다)

FEATURES = ("pattern", "atr_band", "gap", "m6", "m12", "hi12", "logtov", "acc")
NUMERIC = ("gap", "m6", "m12", "hi12", "logtov")
CATEG = ("pattern", "atr_band", "acc")
MISS = "«결측»"


def label(t):
    """139-filter-curve.py:145-149 와 «같은» 식."""
    m = t["masks"][next(iter(t["masks"]))]
    return sum(sh * (px / t["entry_px"] * 100.0 - 100.0) for _d, sh, px in m["exits"])


# ═════════════════════════════════════════════════════════════════════════
# 2. 특징 — **진입 시점에 아는 것만**
# ═════════════════════════════════════════════════════════════════════════
def _prev_ym(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    m -= k
    while m <= 0:
        m += 12
        y -= 1
    return "%04d-%02d" % (y, m)


def _ord(d):
    return _dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()


class Side:
    """경로 «밖» 재료. 전부 as-of 축."""

    def __init__(self, codes):
        """🚨 `codes` 로 «미리» 잘라 담는다 — 세 파일 합이 250MB 라 통째로 들면 터진다."""
        pack = json.loads((r91.OUT / "91-monthly-us-full.json").read_text(encoding="utf-8"))
        self.monthly = {k: v for k, v in pack["monthly"].items() if k in codes}
        del pack
        cap = json.loads(CAP_PIT.read_text(encoding="utf-8"))
        self.tov = {k: (v.get("tov") or []) for k, v in cap.items() if k in codes}
        del cap
        fund, flds = f92a.load()
        self.ixf = {f: i for i, f in enumerate(flds)}        # 103:101 과 «같은» 변환
        assert flds[0] == "date" and self.ixf["eps"] == 3, flds     # 103:102 과 같은 관문
        self.fund = {k: v for k, v in fund.items() if k in codes}
        del fund

    # ── 월봉: scan_date 의 «직전 달»까지만 본다 ──────────────────────────
    def _px(self, code, ym):
        return (self.monthly.get(code) or {}).get(ym)

    def month_feats(self, code, scan_date):
        base = _prev_ym(scan_date[:7], 1)            # 🚨 진입 달은 «안» 본다
        p0 = self._px(code, base)
        out = {"m6": None, "m12": None, "hi12": None}
        if not p0 or p0 <= 0:
            return out
        p6, p12 = self._px(code, _prev_ym(base, 6)), self._px(code, _prev_ym(base, 12))
        if p6 and p6 > 0:
            out["m6"] = p0 / p6 - 1.0
        if p12 and p12 > 0:
            out["m12"] = p0 / p12 - 1.0
        hi = [self._px(code, _prev_ym(base, k)) for k in range(0, 12)]
        hi = [x for x in hi if x and x > 0]
        if len(hi) >= 6:
            out["hi12"] = p0 / max(hi) - 1.0
        return out

    # ── 거래대금: 진입 «전날» 축 (95a 관문 ①) ───────────────────────────
    def logtov(self, code, entry_date):
        rows = self.tov.get(code) or []
        if not rows:
            return None
        i = bisect.bisect_left([r[0] for r in rows], entry_date)   # date < entry_date
        lo = max(0, i - 20)
        vals = [r[1] for r in rows[lo:i] if r[1] and r[1] > 0]
        if len(vals) < 5:
            return None
        return math.log10(sum(vals) / len(vals))

    # ── 실적 가속: 공시일 < 진입일 ──────────────────────────────────────
    def acc(self, code, entry_date):
        arq = (self.fund.get(code) or {}).get("ARQ") or []
        if not arq:
            return None
        r = f92a.asof(arq, entry_date)
        if r is None or _ord(entry_date) - _ord(r[0]) > r102.STALE_MAX:
            return None
        return r103.judge(arq, arq.index(r), self.ixf, 1, 2)


def features(t, side):
    """`t` = `pt.resolve_trade` 산출(진입 시점 기록만 씀) · `side` = Side"""
    code, sd = t["code"], t["scan_date"]
    pv, ep = t.get("pivot"), t["entry_px"]
    f = {"pattern": t.get("pattern") or MISS,
         "atr_band": t.get("atr_band") or MISS,
         "gap": (ep / pv - 1.0) if (pv and pv > 0 and ep) else None,
         "logtov": side.logtov(code, t["entry_date"]),
         "acc": {True: "가속", False: "둔화", None: MISS}[side.acc(code, t["entry_date"])]}
    f.update(side.month_feats(code, sd))
    return f


# ═════════════════════════════════════════════════════════════════════════
# 3. 점수 — 나이브 베이즈(구간별 우도비). 최적화기 없음
# ═════════════════════════════════════════════════════════════════════════
_C = None


def _binof(v, edges):
    if v is None:
        return MISS
    return "b%d" % bisect.bisect_right(edges, v)


def fit(rows, top_q=0.05):
    """rows = [(feat, r_)] → 상수 dict.  🚨 앞 구간 자료로만 부른다."""
    ys = sorted((r for _f, r in rows), reverse=True)
    k = max(1, int(round(len(ys) * top_q)))
    cut = ys[k - 1]
    lab = [(f, r >= cut) for f, r in rows]
    prior = sum(1 for _f, y in lab if y) / max(1, len(lab))

    bins = {}
    for name in NUMERIC:
        vs = sorted(f[name] for f, _y in lab if f.get(name) is not None)
        if len(vs) < NBIN * 20:
            bins[name] = []
            continue
        bins[name] = [vs[int(round(len(vs) * i / NBIN))] for i in range(1, NBIN)]

    cnt_all, cnt_top = defaultdict(Counter), defaultdict(Counter)
    for f, y in lab:
        for name in FEATURES:
            b = _binof(f.get(name), bins[name]) if name in NUMERIC else (f.get(name) or MISS)
            cnt_all[name][b] += 1
            if y:
                cnt_top[name][b] += 1
    logl = {}
    for name in FEATURES:
        logl[name] = {b: math.log(((cnt_top[name][b] + ALPHA * prior)
                                   / (n + ALPHA)) / prior)
                      for b, n in cnt_all[name].items()}
    return {"features": list(FEATURES), "numeric": list(NUMERIC), "bins": bins,
            "logl": logl, "prior": prior, "top_q": top_q, "n_fit": len(lab),
            "cut": cut, "alpha": ALPHA, "nbin": NBIN,
            "label": "139 r_ = sum(sh*(px/entry_px*100-100))",
            "window": [FRONT_D0, FRONT_D1]}


def score(feat, const=None):
    """클수록 「대박일 것 같다」."""
    c = const or _C
    if c is None:
        raise RuntimeError("상수가 없다 — load_const() 를 먼저 부르라")
    s = 0.0
    for name in c["features"]:
        b = (_binof(feat.get(name), c["bins"][name]) if name in c["numeric"]
             else (feat.get(name) or MISS))
        s += c["logl"][name].get(b, 0.0)          # 못 본 칸은 «중립»(0)
    return s


def load_const(path=None):
    global _C
    _C = json.loads(Path(path or CONST).read_text(encoding="utf-8"))
    return _C


# ═════════════════════════════════════════════════════════════════════════
# 4. 지표 — 「절반 남길 때 대박이 몇 % 살아남나」
# ═════════════════════════════════════════════════════════════════════════
def retention(rows, const, keep=0.50, top_q=0.05):
    ys = sorted((r for _f, r in rows), reverse=True)
    k = max(1, int(round(len(ys) * top_q)))
    cut = ys[k - 1]
    sc = sorted(((score(f, const), r) for f, r in rows), key=lambda x: -x[0])
    m = max(1, int(round(len(sc) * keep)))
    kept = sc[:m]
    tot = sum(1 for _f, r in rows if r >= cut)
    got = sum(1 for _s, r in kept if r >= cut)
    return got / max(1, tot), tot, len(kept)


# ═════════════════════════════════════════════════════════════════════════
# 5. 자료 모으기
# ═════════════════════════════════════════════════════════════════════════
def collect():
    _guard(YEARS, FRONT_D1)
    r91.TARGET, r91.STOP, r91.HALF = TARGET, STOP, HALF

    # 🚨 **해마다 싣고 해마다 버린다** — 13년치를 통째로 들면 다른 작업과 부딪친다.
    #    `r91.replay` 는 `open_until` 을 **해마다 새로** 만든다(91:154) → 해마다 나눠 돌려도
    #    결과가 «같다». 관문 ⑳ 가 그걸 확인한다.
    #    그리고 해마다 **디스크에 적어 둔다** — 중간에 멎어도 다시 안 돈다.
    import _lean_load as ll
    CACHE.mkdir(parents=True, exist_ok=True)
    ev, n_all, blk = [], 0, 0
    for y in YEARS:
        cf = CACHE / ("_140_y%d.json" % y)
        if cf.exists():
            pk = json.loads(cf.read_text(encoding="utf-8"))
            ev.extend(pk["rows"])
            n_all += pk["n_all"]
            blk += pk["blocked"]
            print("   %d년 — 저장분 재사용 (누적 후보 %d · 진입 %d)"
                  % (y, n_all, len(ev)), flush=True)
            continue
        by1, _cand, n1 = ll.load_combo((y,), FRONT_D0, FRONT_D1)
        if y not in by1:
            raise SystemExit("🚨 경로 파일 없음 %d" % y)
        pmeta = {(p["scan_date"], p["code"], p["pattern"]):
                 (p.get("pivot"), p.get("atr_band")) for p in by1[y]}
        e1, b1, _t1 = r91.replay(by1)
        rows1 = []
        for t in e1:
            pv, ab = pmeta.get((t["scan_date"], t["code"], t["pattern"]), (None, None))
            rows1.append({"code": t["code"], "scan_date": t["scan_date"],
                          "pattern": t["pattern"], "entry_date": t["entry_date"],
                          "entry_px": t["entry_px"], "pivot": pv, "atr_band": ab,
                          "r": label(t)})
        cf.write_text(json.dumps({"rows": rows1, "n_all": n1, "blocked": b1},
                                 ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
        ev.extend(rows1)
        n_all += n1
        blk += b1
        del by1, e1, pmeta, rows1
        print("   %d년 — 누적 후보 %d · 진입 %d (저장)" % (y, n_all, len(ev)), flush=True)
    print("   후보 %d → 진입 %d (막힘 %d)" % (n_all, len(ev), blk), flush=True)
    if len(ev) != N_EV_GATE:
        raise SystemExit("🚨 관문 ⑳ 미통과 — 해마다 나눠 실은 진입 수 %d ≠ 통째 실은 %d. "
                         "맞추지 말고 «왜인지»부터." % (len(ev), N_EV_GATE))
    print("   관문 ⑳ **통과** — 통째로 실었을 때(%d)와 같다" % N_EV_GATE, flush=True)

    # 🚨 경로를 «버린 뒤»에 옆 재료를 든다 — 필요한 종목으로 미리 잘라서
    codes = {t["code"] for t in ev}
    print("월봉·시총·실적 적재 (종목 %d개로 잘라서) …" % len(codes), flush=True)
    side = Side(codes)

    rows, nmiss = [], Counter()
    for t in ev:
        f = features(t, side)
        for name in FEATURES:
            if f.get(name) is None or f.get(name) == MISS:
                nmiss[name] += 1
        rows.append((f, t["r"], t["entry_date"]))
    return rows, nmiss, len(ev)


# ═════════════════════════════════════════════════════════════════════════
def main() -> int:
    print("=" * 96, flush=True)
    print("140 — 체 만들기 · **앞 구간 %s ~ %s 만** (뒤 구간 차단)" % (FRONT_D0, FRONT_D1),
          flush=True)
    print("=" * 96, flush=True)
    print("사전등록 tasks/140-sieve.md · 특징 **%d개** · 라벨 = 139 r_ · 지표 = 유지율\n"
          % len(FEATURES), flush=True)

    rows3, nmiss, n_ev = collect()
    rows = [(f, r) for f, r, _d in rows3]

    print("\n결측 — 특징마다 몇 건이 «값 없음» 칸으로 갔나 (버리지 «않는다»)", flush=True)
    for name in FEATURES:
        print("   %-9s %6d / %6d = %5.1f%%"
              % (name, nmiss[name], n_ev, 100 * nmiss[name] / max(1, n_ev)), flush=True)

    # ── 앞 구간 전체로 상수를 만든다 (검증 세션이 쓸 정본) ────────────────
    const = fit(rows, 0.05)
    CONST.parent.mkdir(parents=True, exist_ok=True)
    CONST.write_text(json.dumps(const, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n상수 저장: %s  (대박 문턱 r_ = %+.2f%%)" % (CONST.name, const["cut"]), flush=True)

    # ── 특징이 «어느 방향»으로 잡혔나 — 사전등록 방향과 대조 ──────────────
    print("\n특징마다 «가장 대박스러운 칸 → 가장 아닌 칸» (앞 구간 전체 기준)", flush=True)
    for name in FEATURES:
        d = const["logl"][name]
        if not d:
            continue
        o = sorted(d.items(), key=lambda x: -x[1])
        print("   %-9s  %s" % (name, " · ".join("%s %+.2f" % (b, v) for b, v in o[:3])
                               + "   …   "
                               + " · ".join("%s %+.2f" % (b, v) for b, v in o[-2:])),
              flush=True)
    if const["bins"].get("m6"):
        e = const["bins"]["m6"]
        print("   (m6 %d분위 경계: %s)"
              % (NBIN, " ".join("%+.0f%%" % (x * 100) for x in e)), flush=True)

    # ── 🚨 자체점검 — A로 만들어 B에서, B로 만들어 A에서 ──────────────────
    A = [(f, r) for f, r, d in rows3 if d < SPLIT]
    B = [(f, r) for f, r, d in rows3 if d >= SPLIT]
    print("\n" + "=" * 96, flush=True)
    print("자체점검 (규율 ④) — A %d건(~%s) · B %d건(%s~)"
          % (len(A), SPLIT, len(B), SPLIT), flush=True)
    print("=" * 96, flush=True)
    cA, cB = fit(A, 0.05), fit(B, 0.05)
    print("  %-26s %10s %10s %10s" % ("", "유지 50%", "유지 25%", "유지 10%"), flush=True)
    for lab, c, ds, honest in (("A로 만들어 **B에서**", cA, B, True),
                               ("B로 만들어 **A에서**", cB, A, True),
                               ("A→A (성적 «아님»)", cA, A, False),
                               ("B→B (성적 «아님»)", cB, B, False)):
        cells = []
        for kp in KEEPS:
            r_, tot, _n = retention(ds, c, kp, 0.05)
            cells.append("%6.1f%%" % (100 * r_))
        print("  %-26s %10s %10s %10s   %s"
              % (lab, cells[0], cells[1], cells[2],
                 "" if honest else "← 자기 자료"), flush=True)
    print("\n  무작위 = 유지 비율과 «같다» (50 / 25 / 10%) · **합격선 61%** (유지 50% 칸)",
          flush=True)

    # ── 곁들여 — 앞 구간 전체 상수로 상위 1%·10% 도 ───────────────────────
    print("\n곁들여 — 앞 구간 «전체» 상수(= 자기 자료라 성적 아님)", flush=True)
    for tq in TOPS:
        c2 = fit(rows, tq)
        r_, tot, _n = retention(rows, c2, 0.50, tq)
        print("   대박을 상위 %4.0f%% 로 잡으면 (n=%4d) — 절반 남길 때 유지 %5.1f%%"
              % (tq * 100, tot, 100 * r_), flush=True)

    # ── 무작위 대조 (같은 수를 «동전»으로 남긴다) ─────────────────────────
    rnd = random.Random(140)
    ys = sorted((r for _f, r in rows), reverse=True)
    cut = ys[max(1, int(round(len(ys) * 0.05))) - 1]
    keeps = []
    for _ in range(200):
        idx = rnd.sample(range(len(rows)), len(rows) // 2)
        keeps.append(sum(1 for i in idx if rows[i][1] >= cut)
                     / max(1, sum(1 for _f, r in rows if r >= cut)))
    keeps.sort()
    print("\n대조 — «동전»으로 절반 남기면 유지율 중앙 %.1f%% (200판 · 5~95%% %.1f~%.1f%%)"
          % (100 * keeps[100], 100 * keeps[10], 100 * keeps[190]), flush=True)

    print("\n🚨 **뒤 구간은 열지 않았습니다.** 검증 세션이 %s 를 그대로 쓰면 됩니다."
          % CONST.name, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

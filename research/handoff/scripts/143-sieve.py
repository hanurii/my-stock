# -*- coding: utf-8 -*-
r"""143 — 「부호만 배우는」 체. 본판. 사전등록 tasks/143-sign-only-sieve.md (624줄) 그대로.

🚨 이 파일은 사전등록을 «집행»만 한다. 결과를 보고 무엇도 바꾸지 않는다.

  자 A  「체 1등 − 그날 평균」                분모 후보 2+ 인 날 전부
  자 B  「상위 s개 평균 − 무작위 s개 평균」   s = 기준판(씨앗 143) 체결 수 · 1 ≤ s < k 인 날
  문턱  max(z_A, z_B) 순열분포의 98.75 백분위  (앞 판 넷 본페로니 · 자 둘은 max 흡수)
  순열  4,000판 · 씨앗 143 · 「같은 날 · 같은 후보 집합 · 그 «안»에서 순서만」
  ⛔ 뒤 구간(2012~) 열지 않는다

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/143-sieve.py
"""
from __future__ import annotations

import bisect
import datetime as _dt
import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_s)
_s.loader.exec_module(r102)
r91, f92a = r102.r91, r102.f92a
_s3 = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_s3)
_s3.loader.exec_module(r103)
import slot_sim_lots as sl                                       # noqa: E402

# ══════════════════════════════════════════════════════════════════════════
# 0. 🚨 뒤 구간 차단 — 이 블록을 고치지 말 것
# ══════════════════════════════════════════════════════════════════════════
FRONT_D0, FRONT_D1 = "1999-04-01", "2011-12-31"
YEARS = tuple(range(1999, 2012))
CUT = {20.0: "2003-11-19", 30.0: "2003-11-26"}      # 143a 가 «후보 수»로 낸 지점


def _guard():
    bad = [y for y in YEARS if y >= 2012]
    if bad:
        raise RuntimeError("🚨 뒤 구간 차단 — %r" % (bad,))
    if FRONT_D1 > "2011-12-31":
        raise RuntimeError("🚨 뒤 구간 차단 — d1 %s" % FRONT_D1)


NEW = Path("D:/stock-data/uspath-warm/full")
CAP_PIT = Path(r"D:\stock-data\derived\95-cap-pit.json")
CACHE = ROOT / ".cache" / "bt5y" / "out"
OUT = ROOT / "research" / "handoff" / "data" / "143-result.json"

STOP, HALF = 10.0, 0.5
FEATURES = ("atr_band", "gap", "m6", "m12", "hi12", "logtov", "acc")   # ⛔ pattern 뺌
NPERM, PERM_SEED, REF_SEED = 4000, 143, 143
NRAND = 5                                           # R1~R5
# 🚨 atr_band 파싱을 고치기 «전»에 찍힌 학습 구간 부호 통계(+20 · 2026-09-01).
#    파싱«만» 고쳤다면 이 다섯은 **글자 그대로 같아야** 한다.
#    하나라도 다르면 그건 파싱 말고 «다른 게» 바뀐 것이다 → 멈춘다.
PRE_FIX_T20 = {"gap": (-0.01214, -0.10398, 0.07614),
               "m6": (-0.01023, 0.03943, -0.05796),
               "m12": (0.21688, 0.18112, 0.25125),
               "hi12": (-0.14325, -0.49400, 0.19386),
               "logtov": (-0.22456, 0.23852, -0.66964)}
ALPHA = 0.05 / 4                                    # N_앞 = 4 · 자 둘은 max 가 흡수
PCTL = 100.0 * (1.0 - ALPHA)                        # 98.75


def label(t):
    m = t["masks"][next(iter(t["masks"]))]
    return sum(sh * (px / t["entry_px"] * 100.0 - 100.0) for _d, sh, px in m["exits"])


def _ord(d):
    return _dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()


def _prev_ym(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    m -= k
    while m <= 0:
        m += 12
        y -= 1
    return "%04d-%02d" % (y, m)


# ══════════════════════════════════════════════════════════════════════════
# 1. 특징 — 140 것 «그대로»(pattern 만 뺌). 진입 시점에 아는 것만
# ══════════════════════════════════════════════════════════════════════════
class Side:
    def __init__(self, codes):
        pack = json.loads((r91.OUT / "91-monthly-us-full.json").read_text(encoding="utf-8"))
        self.monthly = {k: v for k, v in pack["monthly"].items() if k in codes}
        del pack
        cap = json.loads(CAP_PIT.read_text(encoding="utf-8"))
        self.tov = {k: (v.get("tov") or []) for k, v in cap.items() if k in codes}
        del cap
        fund, flds = f92a.load()
        self.ixf = {f: i for i, f in enumerate(flds)}
        assert flds[0] == "date" and self.ixf["eps"] == 3, flds
        self.fund = {k: v for k, v in fund.items() if k in codes}
        del fund

    def _px(self, code, ym):
        return (self.monthly.get(code) or {}).get(ym)

    def month_feats(self, code, scan_date):
        base = _prev_ym(scan_date[:7], 1)          # 🚨 진입 달은 «안» 본다
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

    def logtov(self, code, entry_date):
        rows = self.tov.get(code) or []
        if not rows:
            return None
        i = bisect.bisect_left([r[0] for r in rows], entry_date)
        lo = max(0, i - 20)
        vals = [r[1] for r in rows[lo:i] if r[1] and r[1] > 0]
        if len(vals) < 5:
            return None
        return math.log10(sum(vals) / len(vals))

    def acc(self, code, entry_date):
        arq = (self.fund.get(code) or {}).get("ARQ") or []
        if not arq:
            return None
        r = f92a.asof(arq, entry_date)
        if r is None or _ord(entry_date) - _ord(r[0]) > r102.STALE_MAX:
            return None
        return r103.judge(arq, arq.index(r), self.ixf, 1, 2)


# \ud83d\udea8 2026-09-01 \uc815\uc815 \u2014 \uc2e4\uc81c \uac12\uc740 '\u2460\uc870\uc6a9 <2.5%' \uac19\uc740 \u00ab\ud1b5\uc9f8 \ubb38\uc790\uc5f4\u00bb\uc774\ub2e4.
#    \uae30\ud638 \u00ab\ud55c \uae00\uc790\u00bb\ub9cc \ucc3e\ub2e4\uac00 \u00ab\uc804\ubd80\u00bb \uc870\ud68c \uc2e4\ud328 \u2192 atr_band 100% \uacb0\uce21 \u2192 \uc0c1\uc218 \u2192
#    \ubd80\ud638 \uad00\ubb38\uc5d0\uc11c \u00ab\ub5a8\uc5b4\uc9c4\u00bb \uac8c \uc544\ub2c8\ub77c \u00ab\ucd9c\uc804 \uc790\uccb4\ub97c \ubabb \ud588\ub2e4\u00bb.
#    \u00a72 \uc5d0 `atr_band(\u2460<\u2461<\u2462<\u2463 \uc21c\uc11c\ud615)`\uc774 \u00ab\uc774\ubbf8 \ub4f1\ub85d\u00bb\ub3fc \uc788\uc5c8\uace0 \ucf54\ub4dc\uac00 \uadf8\uac78 \u00ab\uc77d\uc9c0 \ubabb\ud55c\u00bb \uac83\uc774\ub77c,
#    \uc774 \uace0\uce68\uc740 \u00ab\uc124\uacc4 \ubcc0\uacbd\u00bb\uc774 \uc544\ub2c8\ub77c \u00ab\uc9d1\ud589\u00bb\uc774\ub2e4.
_ABAND = {"\u2460": 1.0, "\u2461": 2.0, "\u2462": 3.0, "\u2463": 4.0,
          "1": 1.0, "2": 2.0, "3": 3.0, "4": 4.0}


def _aband(v):
    """\ub9e8 \u00ab\uc55e \uae00\uc790\u00bb\ub85c \uc77d\ub294\ub2e4. \ubabb \uc77d\uc73c\uba74 None \u2014 \uadf8\ub9ac\uace0 \uad00\ubb38\uc774 \uadf8\uac78 \u00ab\uc13c\ub2e4\u00bb."""
    if v is None:
        return None
    s = str(v).strip()
    return _ABAND.get(s[:1]) if s else None


def features(t, side):
    """전부 «수»로 낸다 — 부호만 배우므로 순위만 매기면 된다."""
    code = t["code"]
    pv, ep = t.get("pivot"), t["entry_px"]
    ab = t.get("atr_band")
    a = side.acc(code, t["entry_date"])
    f = {"atr_band": _aband(ab),
         "gap": (ep / pv - 1.0) if (pv and pv > 0 and ep) else None,
         "logtov": side.logtov(code, t["entry_date"]),
         "acc": (1.0 if a is True else 0.0 if a is False else None)}
    f.update(side.month_feats(code, t["scan_date"]))
    return f


# ══════════════════════════════════════════════════════════════════════════
# 2. 점수 — 그날 «안»의 백분위 순위 × 부호 · 동일가중. 결측 = 중앙 0.5
# ══════════════════════════════════════════════════════════════════════════
def rank_within(vals):
    """동점은 평균 순위 · 결측은 0.5 (사전등록 §2 — 일곱 «전부»에 같게)."""
    idx = [i for i, v in enumerate(vals) if v is not None]
    out = [0.5] * len(vals)
    if len(idx) <= 1:
        return out
    order = sorted(idx, key=lambda i: vals[i])
    n, i = len(order), 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        pr = ((i + j) / 2.0) / (n - 1) if n > 1 else 0.5
        for k in range(i, j + 1):
            out[order[k]] = pr
        i = j + 1
    return out


def day_ranks(days, byday, key):
    return {d: rank_within([key(c) for c in byday[d]]) for d in days}


def stat_of(days, byday, ranks):
    """부호 뽑기용 — 날마다 (순위, r) 의 «날 안» 공분산. 점수식과 «같은 꼴»."""
    tot, n = 0.0, 0
    for d in days:
        cs = byday[d]
        if len(cs) < 2:
            continue
        rk, rr = ranks[d], [c["r"] for c in cs]
        mk, mr = sum(rk) / len(rk), sum(rr) / len(rr)
        tot += sum((a - mk) * (b - mr) for a, b in zip(rk, rr)) / len(cs)
        n += 1
    return (tot / n) if n else 0.0


# ══════════════════════════════════════════════════════════════════════════
# 3. 자 A · 자 B
# ══════════════════════════════════════════════════════════════════════════
def metric_A(days, byday, order):
    v = []
    for d in days:
        cs = byday[d]
        m = sum(c["r"] for c in cs) / len(cs)
        v.append(cs[order[d][0]]["r"] - m)
    return v


def metric_B(days_b, byday, order, sday):
    v = []
    for d in days_b:
        cs = byday[d]
        s = min(sday.get(d, 0), len(cs))
        m = sum(c["r"] for c in cs) / len(cs)
        v.append(sum(cs[i]["r"] for i in order[d][:s]) / s - m)
    return v


def order_by(days, byday, score):
    """점수 «내림차순» 인덱스. 동점은 원래 순서(안정 정렬)."""
    return {d: sorted(range(len(byday[d])), key=lambda i: -score[d][i]) for d in days}


# ══════════════════════════════════════════════════════════════════════════
# 4. 적재 — by_f (등급 + 103 성장 필터). 해마다 디스크에 적어 둔다
# ══════════════════════════════════════════════════════════════════════════
def load_rows(target):
    r91.TARGET, r91.STOP, r91.HALF = target, STOP, HALF
    import _lean_load as ll
    ll.r91.SUB = NEW
    assert ll.r91.SUB == NEW, ll.r91.SUB
    CACHE.mkdir(parents=True, exist_ok=True)
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    def keep_f(p):
        arq = (fund.get(p["code"]) or {}).get("ARQ") or []
        a = f92a.asof(arq, p["entry_date"]) if arq else None
        v = (None if (a is None or _ord(p["entry_date"]) - _ord(a[0]) > r102.STALE_MAX)
             else r103.judge(arq, arq.index(a), ix, 1, 2))
        return v is not False

    rows = []
    for y in YEARS:
        cf = CACHE / ("_143_rows_t%d_y%d.json" % (int(target), y))
        if cf.exists():
            rows.extend(json.loads(cf.read_text(encoding="utf-8")))
            continue
        by1, _c, _n = ll.load_combo((y,), FRONT_D0, FRONT_D1)
        keep = [p for p in by1.get(y, []) if keep_f(p)]
        pmeta = {(p["scan_date"], p["code"], p["pattern"]):
                 (p.get("pivot"), p.get("atr_band")) for p in keep}
        r1 = []
        for t in r91.replay({y: keep})[0]:
            pv, ab = pmeta.get((t["scan_date"], t["code"], t["pattern"]), (None, None))
            r1.append({"code": t["code"], "scan_date": t["scan_date"],
                       "pattern": t["pattern"], "entry_date": t["entry_date"],
                       "entry_px": t["entry_px"], "pivot": pv, "atr_band": ab,
                       "r": label(t)})
        cf.write_text(json.dumps(r1, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
        rows.extend(r1)
        del by1, keep, pmeta, r1
        print("   %d년 — 누적 %d" % (y, len(rows)), flush=True)
    del fund
    return rows


def ref_fills(target):
    """s 를 정하는 «무작위 순서 기준판» — 씨앗 143 고정 (사전등록 §0)."""
    r91.TARGET, r91.STOP, r91.HALF = target, STOP, HALF
    import _lean_load as ll
    ll.r91.SUB = NEW
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    def keep_f(p):
        arq = (fund.get(p["code"]) or {}).get("ARQ") or []
        a = f92a.asof(arq, p["entry_date"]) if arq else None
        v = (None if (a is None or _ord(p["entry_date"]) - _ord(a[0]) > r102.STALE_MAX)
             else r103.judge(arq, arq.index(a), ix, 1, 2))
        return v is not False

    ev = []
    for y in YEARS:
        by1, _c, _n = ll.load_combo((y,), FRONT_D0, FRONT_D1)
        ev.extend(r91.replay({y: [p for p in by1.get(y, []) if keep_f(p)]})[0])
        del by1
    del fund
    with r91.r41.Cost(*r91.COST):
        r = sl.sim_lots(ev, seed=REF_SEED, slots=r91.SLOTS, risk=r91.RISK,
                        cap=r91.CAP, reserve=False, fill_rule="truncate",
                        cash_rule="per_slot")
    return Counter(x[3] for x in r["fill_log"]), ev


# ══════════════════════════════════════════════════════════════════════════
# 5. 본판 — 목표 하나를 처음부터 끝까지
# ══════════════════════════════════════════════════════════════════════════
def run(target, cut, side_cache):
    print("", flush=True)
    print("=" * 98, flush=True)
    print("목표 **+%.0f%%** / 손절 -%.0f%%  ·  쪼갠 지점 **%s**" % (target, STOP, cut), flush=True)
    print("=" * 98, flush=True)

    rows = load_rows(target)
    codes = {t["code"] for t in rows}
    if side_cache[0] is None or not codes <= side_cache[1]:
        side_cache[0] = Side(codes | (side_cache[1] or set()))
        side_cache[1] = codes | (side_cache[1] or set())
    side = side_cache[0]

    byday = defaultdict(list)
    for t in rows:
        byday[t["entry_date"]].append({"r": t["r"], "f": features(t, side), "t": t})
    alldays = sorted(byday)
    tr_days = [d for d in alldays if d < cut and len(byday[d]) >= 2]
    te_days = [d for d in alldays if d >= cut and len(byday[d]) >= 2]
    n_tr = sum(len(byday[d]) for d in alldays if d < cut)
    n_te = sum(len(byday[d]) for d in alldays if d >= cut)

    # ── 관문 A★ · B★ ────────────────────────────────────────────────────
    gap = abs(n_tr - n_te) / max(1.0, (n_tr + n_te) / 2.0) * 100.0
    gA = gap <= 5.0
    gB = not [d for d in alldays if d >= "2012-01-01"]
    print("", flush=True)
    print("## 관문", flush=True)
    print("  A* 학습/시험 후보 %d / %d · 어긋남 %.1f%%   %s"
          % (n_tr, n_te, gap, "**통과**" if gA else "🚨 **미통과**"), flush=True)
    print("  B* 뒤 구간 연도 실림 %d건                    %s"
          % (0 if gB else 1, "**통과**" if gB else "🚨 **미통과**"), flush=True)

    # ── 관문 G★ 🚨 «출전 자체를 못 하는» 특징이 있는가 (2026-09-01 신설) ──
    #    D★ 은 「관문이 무는가」만 셌지 「물 «것»이 있었나」는 안 셌다 —
    #    그래서 상수가 된 특징 둘을 「버렸다」로 세고 «거짓 통과»를 냈다.
    #    자격 = **학습 구간**에서 서로 다른 값 ≥ 2  (조건 ③)
    print("  G* 특징 자격 — **«출전 자체를 못 하는» 것이 있는가**  (자격: 학습 구간 서로 다른 값 >= 2)",
          flush=True)
    live, dead = [], []
    for nm in FEATURES:
        vtr = [c["f"].get(nm) for d in alldays if d < cut for c in byday[d]]
        vall = [c["f"].get(nm) for d in alldays for c in byday[d]]
        u = len({x for x in vtr if x is not None})
        ok = sum(1 for x in vall if x is not None)
        (live if u >= 2 else dead).append(nm)
        print("     %-9s 겹침 %5.1f%% (전체)  ·  학습 «서로 다른 값» %d%s"
              % (nm, 100.0 * ok / len(vall), u,
                 "" if u >= 2 else "   🚨 **상수 — 출전 불가**"), flush=True)
    print("     → 대상 %d개 중 **겨룰 수 있는 것 %d개** · **출전 불가 %d개** %s"
          % (len(FEATURES), len(live), len(dead),
             ("(%s)" % ",".join(dead)) if dead else ""), flush=True)
    if dead:
        print("     🚨 **판정 낱말은 「일곱 중」이 «아니라» 「겨룬 %d 중」이다**" % len(live),
              flush=True)
        print("     ⛔ 출전 불가는 「뺐다」가 «아니라» **「기여할 수 «없었다»」**로 적는다",
              flush=True)
        print("        (모두 0.5 → 그날 «모든» 후보에 같은 상수 → 순위 완전 동일 →"
              " **빼든 두든 판정이 같다**)", flush=True)

    # ── 부호 뽑기 + 안정 관문 (학습을 «다시 둘로») ────────────────────────
    h_cut, run_n = None, 0
    half = n_tr / 2.0
    for d in [x for x in alldays if x < cut]:
        run_n += len(byday[d])
        if run_n >= half:
            h_cut = d
            break
    h1 = [d for d in tr_days if d < h_cut]
    h2 = [d for d in tr_days if d >= h_cut]

    def sign_of(days_, key):
        rk = day_ranks(days_, byday, key)
        return stat_of(days_, byday, rk)

    signs, dropped, detail = {}, [], []
    for nm in FEATURES:
        key = (lambda n: (lambda c: c["f"].get(n)))(nm)
        s_all, s1, s2 = (sign_of(tr_days, key), sign_of(h1, key), sign_of(h2, key))
        ok = (s1 > 0) == (s2 > 0) and s1 != 0 and s2 != 0
        detail.append((nm, s_all, s1, s2, ok))
        if ok:
            signs[nm] = 1.0 if s_all > 0 else -1.0
        else:
            dropped.append(nm)

    # ── R1~R5 (양성 대조) — 학습 구간 «안»에서 뒤섞은 잡음 ────────────────
    rnd = random.Random(PERM_SEED)
    rkeep, rnames = 0, []
    cells = [c for d in tr_days for c in byday[d]]
    for j in range(NRAND):
        src = FEATURES[j % len(FEATURES)]
        pool = [c["f"].get(src) for c in cells]
        rnd.shuffle(pool)
        tag = "_R%d" % (j + 1)
        for c, v in zip(cells, pool):
            c[tag] = v
        key = (lambda g: (lambda c: c.get(g)))(tag)
        s1, s2 = sign_of(h1, key), sign_of(h2, key)
        if (s1 > 0) == (s2 > 0) and s1 != 0 and s2 != 0:
            rkeep += 1
            rnames.append("R%d" % (j + 1))

    print("", flush=True)
    print("## 부호 안정 관문 — 학습을 «다시 둘로» (%s 기준)" % h_cut, flush=True)
    print("  %-9s %12s %12s %12s  %s" % ("특징", "학습 전체", "앞 절반", "뒤 절반", "판정"), flush=True)
    for nm, sa, s1, s2, ok in detail:
        tag = ("**남음** %+d" % int(signs[nm])) if ok else (
            "🚨 출전 불가(상수)" if nm in dead else "버림")
        print("  %-9s %12.5f %12.5f %12.5f  %s" % (nm, sa, s1, s2, tag), flush=True)

    # ── 🚨 회귀 관문 — 「파싱«만» 고쳤다」를 «수»로 보인다 ──────────────
    if abs(target - 20.0) < 1e-9:
        bad = []
        for nm, (e0, e1, e2) in PRE_FIX_T20.items():
            g = [x for x in detail if x[0] == nm][0]
            if (round(g[1], 5), round(g[2], 5), round(g[3], 5)) != (e0, e1, e2):
                bad.append((nm, (g[1], g[2], g[3]), (e0, e1, e2)))
        print("  🔧 **회귀 관문** — 고치기 «전» 다섯의 부호 통계와 «글자 그대로» 같은가  %s"
              % ("**통과** (다섯 다 동일 → 파싱«만» 바뀌었다)" if not bad
                 else "🚨 **미통과 — 파싱 말고 «다른 게» 바뀌었다. 멈춘다**"), flush=True)
        for nm, got, exp in bad:
            print("     %-9s 지금 %s  vs  전 %s" % (nm, got, exp), flush=True)
        if bad:
            raise SystemExit("🚨 회귀 관문 미통과 — 맞추지 말고 «왜»부터.")
    nk = len(signs)
    print("  → **살아남은 특징 %d개** / 7   ·   **R1~R5 중 «붙은» 것 %d개** / %d %s"
          % (nk, rkeep, NRAND, ("(%s)" % ",".join(rnames)) if rnames else ""), flush=True)
    gD = len(dropped) > 0
    print("  D* 부호 관문이 «무는가» — 버린 것 %d개  %s"
          % (len(dropped), "**통과**" if gD else "🚨 **안 뭄 — 「작동했다」고 못 씀**"), flush=True)
    if nk <= 2:
        print("", flush=True)
        print("  🚨🚨 **살아남은 특징이 2개 이하 → 판정은 「통과/미달」이 아니라 «체를 못 만들었다»**",
              flush=True)
        print("     「재료가 무력하다」도 「자유도가 원인이다」도 **주장하지 않는다**", flush=True)

    return dict(byday=byday, tr_days=tr_days, te_days=te_days, signs=signs,
                dropped=dropped, detail=detail, rkeep=rkeep, rnames=rnames, h_cut=h_cut,
                n_tr=n_tr, n_te=n_te, gap=gap, gA=gA, gB=gB, gD=gD, side=side)


# ══════════════════════════════════════════════════════════════════════════
# 6. 채점 + 순열 + 관문 C* E* F* + 판정
# ══════════════════════════════════════════════════════════════════════════
def score_of(days, byday, signs, extra=None):
    """점수 = 그날 «안»의 백분위 순위 × 부호 → 동일가중 «합»."""
    acc = {d: [0.0] * len(byday[d]) for d in days}
    use = dict(signs)
    if extra:
        use.update(extra)
    for nm, sg in use.items():
        if nm == "_CHEAT":
            rk = day_ranks(days, byday, lambda c: c["r"])       # 🚨 미래. C* 전용
        else:
            rk = day_ranks(days, byday, (lambda n: (lambda c: c["f"].get(n)))(nm))
        for d in days:
            v = acc[d]
            for i, x in enumerate(rk[d]):
                v[i] += sg * x
    return acc


def perm_null(days_a, days_b, byday, sday, nperm, seed):
    """🚨 «같은 날 · 같은 후보 집합 · 그 «안»에서 순서만» 섞는다.
    ⛔ 날을 가로지르지도, 재표집하지도 않는다 (dataaxis 재표집 결함 원천 회피)."""
    rnd = random.Random(seed)
    idx = {d: list(range(len(byday[d]))) for d in set(days_a) | set(days_b)}
    a_l, b_l = [], []
    for _ in range(nperm):
        o = {}
        for d, v in idx.items():
            w = v[:]
            rnd.shuffle(w)
            o[d] = w
        a_l.append(sum(metric_A(days_a, byday, o)) / len(days_a))
        bb = metric_B(days_b, byday, o, sday)
        b_l.append(sum(bb) / len(bb) if bb else 0.0)
    return a_l, b_l


def zof(x, lst):
    m = sum(lst) / len(lst)
    sd = math.sqrt(sum((v - m) ** 2 for v in lst) / (len(lst) - 1))
    return (x - m) / sd if sd > 0 else 0.0, m, sd


def pct(lst, q):
    s = sorted(lst)
    i = q / 100.0 * (len(s) - 1)
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (i - lo)


def judge(target, R):
    byday, te_days, signs = R["byday"], R["te_days"], R["signs"]
    sday = R["sday"]
    b_days = [d for d in te_days
              if 1 <= min(sday.get(d, 0), len(byday[d])) < len(byday[d])]

    sc = score_of(te_days, byday, signs)
    order = order_by(te_days, byday, sc)
    A = metric_A(te_days, byday, order)
    B = metric_B(b_days, byday, order, sday)
    Abar = sum(A) / len(A)
    Bbar = (sum(B) / len(B)) if B else float("nan")

    print("", flush=True)
    print("## 순열 귀무 %d판 (씨앗 %d · 같은 날 «안» 순서만)" % (NPERM, PERM_SEED), flush=True)
    an, bn = perm_null(te_days, b_days, byday, sday, NPERM, PERM_SEED)
    zA, mA, sA = zof(Abar, an)
    zB, mB, sB = zof(Bbar, bn) if B else (float("nan"),) * 3
    zan = [(x - mA) / sA if sA > 0 else 0.0 for x in an]
    zbn = [(x - mB) / sB if sB > 0 else 0.0 for x in bn]
    mx = [max(a, b) for a, b in zip(zan, zbn)]
    thr = pct(mx, PCTL)

    # ── 관문 F* — max-T 문턱을 «자 A 혼자»에 대면 넘는 비율이 괄호 안이어야 ──
    exc = 100.0 * sum(1 for z in zan if z > thr) / len(zan)
    lo_f = 100.0 * (1.0 - math.sqrt(1.0 - ALPHA))
    hi_f = 100.0 * ALPHA
    gF = lo_f <= exc <= hi_f
    zlo, zhi = 2.2414, 2.4966
    pos = (thr - zlo) / (zhi - zlo)

    print("  귀무 자 A  평균 %+.4f · SD %.4f     ·  자 B  평균 %+.4f · SD %.4f"
          % (mA, sA, mB, sB), flush=True)
    print("  **max-T 문턱 z = %.4f**  (98.75 백분위 · 문턱 위 %d판)"
          % (thr, round(NPERM * ALPHA)), flush=True)
    print("  F* 괄호 — 자 A 혼자에 대었을 때 넘는 비율 **%.3f%%**  (있어야 할 곳 %.3f%% ~ %.3f%%)  %s"
          % (exc, lo_f, hi_f, "**통과**" if gF else "🚨 **미통과 — 구현이 틀렸다**"), flush=True)
    print("     F* 부속 «괄호 안 위치» = **%.3f**  (0 = 완전상관 쪽 · 1 = 독립 쪽)  %s"
          % (pos, "→ 예상대로 상관 쪽" if pos < 0.5 else "🚨 독립 쪽 — 구조와 «왜» 안 맞는지부터"),
          flush=True)

    # ── 관문 C* 커닝 시험 ────────────────────────────────────────────────
    sc_c = score_of(te_days, byday, signs, extra={"_CHEAT": 1.0})
    Ac = sum(metric_A(te_days, byday, order_by(te_days, byday, sc_c))) / len(te_days)
    gC = Ac > Abar
    print("  C* 커닝 시험 — 미래(r)를 특징에 넣으면 자 A 가 %+.4f → **%+.4f**  %s"
          % (Abar, Ac, "**통과**" if gC else "🚨 **미통과 — 관문이 죽은 코드**"), flush=True)
    print("  E* 순열 = 같은 날 «안» 순서만 · 재표집 «안» 씀            **통과**(구조상)", flush=True)

    # ── 네 칸 표 ────────────────────────────────────────────────────────
    okA, okB = zA > thr, (zB > thr) if B else False
    print("", flush=True)
    print("## 네 칸 표", flush=True)
    print("  자 A  분모 **%d일**  ·  관측 **%+.4f%%p/날**  ·  **z = %.4f**  → %s"
          % (len(te_days), Abar, zA, "**넘음**" if okA else "**못 넘음**"), flush=True)
    print("  자 B  분모 **%d일**  ·  관측 **%+.4f%%p/날**  ·  **z = %.4f**  → %s"
          % (len(b_days), Bbar, zB, "**넘음**" if okB else "**못 넘음**"), flush=True)
    print("  max(z_A, z_B) = **%.4f**   vs   문턱 **%.4f**  →  %s"
          % (max(zA, zB), thr, "✅ **자격 얻음**" if max(zA, zB) > thr else "❌ **자격 못 얻음**"),
          flush=True)
    cell = {(True, True): "✅ **고르는 능력이 있고 «돈으로도» 바뀐다** — 가장 강한 결과",
            (True, False): "**「능력은 있는데 «고를 기회»가 없다」** → 처방이 «체»가 아니라 «자리»로. "
                           "🚨 B 는 2.8배 무디니 「돈이 안 된다」로 «못» 읽는다",
            (False, True): "🚨 **설명이 필요한 자리** — 능력을 못 보였는데 돈이 됐다? 잡음·결함을 먼저 의심",
            (False, False): "**못 넘음.** 갈림표(㉠자유도 / ㉡재료 / ㉢부호만은 거칠다)로 읽는다"}
    print("  → %s" % cell[(okA, okB)], flush=True)

    # ── 동반 지표 (자를 바꿔 «피하지» 않는다) ──────────────────────────
    srt = sorted(A, reverse=True)
    ntop = max(1, int(round(len(A) * 0.01)))
    A_not = [x for x in srt[ntop:]]
    print("", flush=True)
    print("## 동반 지표 — 항상 같이 적는다", flush=True)
    print("  ㉠ 중앙 **%+.4f%%p**   ·   ㉡ 「양(+)인 날」 비율 **%.1f%%**"
          % (st.median(A), 100.0 * sum(1 for x in A if x > 0) / len(A)), flush=True)
    print("  ㉢ 상위 1%%(%d날) 제거 후 평균 **%+.4f%%p**  — 우세의 **%.1f%%**가 그 %d날에서 왔다"
          % (ntop, sum(A_not) / len(A_not),
             (100.0 * (Abar - sum(A_not) / len(A_not)) / Abar) if Abar else float("nan"),
             ntop), flush=True)
    print("     🚨 이건 «기술»이지 «관문»이 아니다 — 죽음은 「상위 1% 빼고 «유의하게 음»」일 때만",
          flush=True)
    return dict(Abar=Abar, Bbar=Bbar, zA=zA, zB=zB, thr=thr, okA=okA, okB=okB,
                exc=exc, gF=gF, gC=gC, pos=pos, n_a=len(te_days), n_b=len(b_days),
                median=st.median(A), pos_rate=100.0 * sum(1 for x in A if x > 0) / len(A),
                A_ex1=sum(A_not) / len(A_not), A=A, order=order, b_days=b_days)


# ══════════════════════════════════════════════════════════════════════════
# 7. 묘사 — 판정에 «안» 쓴다
# ══════════════════════════════════════════════════════════════════════════
def describe(R, J, ev):
    byday, te_days, sday = R["byday"], R["te_days"], R["sday"]
    order, A = J["order"], J["A"]
    print("", flush=True)
    print("## 묘사 — **판정에 안 쓴다**", flush=True)

    # ㉠ 좁힌 자 A — «살 수 있었던» 날만
    nar = [a for d, a in zip(te_days, A) if sday.get(d, 0) >= 1]
    if nar:
        print("  ㉠ 좁힌 자 A (체결이 «있던» 날 %d일) 평균 **%+.4f%%p**  vs  전체 %d일 **%+.4f%%p**"
              % (len(nar), sum(nar) / len(nar), len(A), J["Abar"]), flush=True)
    else:
        print("  ㉠ 좁힌 자 A — 체결이 있던 날이 없다", flush=True)

    # ㉡ k 별 자 A
    print("  ㉡ k 별 자 A  (🚨 k≥5 인 날은 «대부분 살 수 없던» 날인데 자 A 는 같은 무게로 센다)",
          flush=True)
    grp = defaultdict(list)
    for d, a in zip(te_days, A):
        k = len(byday[d])
        grp[2 if k == 2 else 3 if k <= 4 else 5].append((a, 1 if sday.get(d, 0) >= 1 else 0))
    NM = {2: "k = 2  ", 3: "k = 3~4", 5: "k >= 5 "}
    for g in sorted(grp):
        v = grp[g]
        print("       %s  날 %4d · 평균 **%+.4f%%p** · 그중 «살 수 있던» 날 %.1f%%"
              % (NM[g], len(v), sum(x for x, _ in v) / len(v),
                 100.0 * sum(y for _, y in v) / len(v)), flush=True)

    # ㉢ §9 슬롯 시뮬 — 체 순서 vs 무작위 순서 (세후 총액)
    key = {}
    for d in te_days:
        for rank, i in enumerate(order[d]):
            c = byday[d][i]["t"]
            key[(c["scan_date"], c["code"], c["pattern"])] = rank
    ev_te = [t for t in ev if t["entry_date"] >= min(te_days)]
    try:
        with r91.r41.Cost(*r91.COST):
            base = [sl.sim_lots(ev_te, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                reserve=False, fill_rule="truncate", cash_rule="per_slot")["final"]
                    for s in range(10)]
            sieve = [sl.sim_lots(ev_te, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                 reserve=False, fill_rule="truncate", cash_rule="per_slot",
                                 order_fn=lambda _s, t: key.get(
                                     (t["scan_date"], t["code"], t["pattern"]), 9999))["final"]
                     for s in range(10)]
        print("  ㉢ §9 슬롯 시뮬 (시험 구간 · 10판) — 무작위 순서 중앙 **%.2f** vs 체 순서 중앙 **%.2f**"
              % (st.median(base), st.median(sieve)), flush=True)
        print("     🚨 판마다 흔들림이 커서 «크기»만 본다. 판정 아님", flush=True)
    except Exception as e:                                     # noqa: BLE001
        print("  ㉢ §9 슬롯 시뮬 — 못 냈다: %r" % (e,), flush=True)


# ══════════════════════════════════════════════════════════════════════════
def main() -> int:
    _guard()
    print("=" * 98, flush=True)
    print("143 — 「부호만 배우는」 체 · **본판** · 앞 구간 %s ~ %s 만 (뒤 구간 차단)"
          % (FRONT_D0, FRONT_D1), flush=True)
    print("사전등록 tasks/143-sign-only-sieve.md 그대로 · 결과를 보고 «무엇도» 바꾸지 않는다",
          flush=True)
    print("=" * 98, flush=True)
    res, side_cache = {}, [None, None]
    for target, cut in CUT.items():
        R = run(target, cut, side_cache)
        sday, ev = ref_fills(target)
        R["sday"] = sday
        if len(R["signs"]) <= 2:
            print("", flush=True)
            print("  ⏹ **체를 못 만들었다** — 채점·순열로 «안» 넘어간다", flush=True)
            res["t%d" % int(target)] = {"verdict": "체를 못 만들었다",
                                        "kept": list(R["signs"]), "rkeep": R["rkeep"]}
            continue
        J = judge(target, R)
        describe(R, J, ev)
        v = ("자격 얻음" if max(J["zA"], J["zB"]) > J["thr"] else "자격 못 얻음")
        if not (R["gA"] and R["gB"] and R["gD"] and J["gC"] and J["gF"]):
            v = "🚨 관문 미통과 — 아래 수를 «안» 읽는다"
        print("", flush=True)
        print("  ▶ **판정(+%.0f%%) : %s**" % (target, v), flush=True)
        res["t%d" % int(target)] = {
            "verdict": v, "kept": {k: int(s) for k, s in R["signs"].items()},
            "dropped": R["dropped"], "rkeep": R["rkeep"], "rnames": R["rnames"],
            "h_cut": R["h_cut"], "n_tr": R["n_tr"], "n_te": R["n_te"], "gap": R["gap"],
            "Abar": J["Abar"], "Bbar": J["Bbar"], "zA": J["zA"], "zB": J["zB"],
            "thr": J["thr"], "okA": J["okA"], "okB": J["okB"], "n_a": J["n_a"],
            "n_b": J["n_b"], "Fexc": J["exc"], "Fpos": J["pos"],
            "median": J["median"], "pos_rate": J["pos_rate"], "A_ex1": J["A_ex1"],
            "gates": {"A": R["gA"], "B": R["gB"], "C": J["gC"], "D": R["gD"], "F": J["gF"]}}
        del R, J, ev

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: %s" % OUT.name, flush=True)
    print("⛔ 뒤 구간(2012~)은 «열지 않았다». 여는 것은 «따로» 정한다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

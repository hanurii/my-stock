# -*- coding: utf-8 -*-
r"""156v — 🚨 **154(+30 · 세대 A)와 156①(+30 · 세대 B)이 «어긋난다». 어디서인지 «가른다»**

  규약 ⑦ — 같은 것을 가리키는 수가 «둘»이면 멈춘다.
  ```
  154  세대 A · 숏 20% · 씨앗 60 · 목표 +30   세후 **11,981만**
  155  같은 판 +20 에서 숏 제거 → **+4.2%**   ⇒ 154 의 +30 무숏 ≈ **12,484만** «이어야»
  156① 세대 B · 숏 «없음» · 씨앗 60 · +30     세후 **10,668만**   ⇒ **−14.5%**
  ```
  ⇒ **숏 제거는 «올려야» 하는데 «내려갔다».** 어느 쪽이 맞는지 «모른다».

  🚨 가르는 법 — 「한 번에 하나씩」 바꾸며 «네 지점»을 찍는다:
     A  154 «그대로»            (r91.replay · 숏 있음 · 라벨 «안» 거름)   → 11,981 재현되나?
     B  A 와 «같은 ev·같은 씨앗», 계산만 `account_lib`(숏 «없음»)
     C  B 에 **라벨 없는 107건 제외**만 추가
     D  C 를 «내 build_ev»로 (dedup 을 내가 다시 짬)          → 10,668 나오나?
  ⇒ **A→B→C→D 중 «어디서» 뚝 떨어지는지가 범인이다**
"""
from __future__ import annotations
import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
r108 = _load("r108", "108-short-index.py")
r124 = _load("r124", "124-jeonse-horizon.py")
acc = _load("acc", "account_lib.py")
f92a = r102.f92a
pt = r91.pt

CAP_PIT = Path(r"D:\stock-data\derived\95-cap-pit.json")
TERCILE = Path(r"D:\stock-data\derived\156-cap-tercile.json")
D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
FEE, SHORT_SIZE, BORROW = 0.002, 0.20, 2.0
TARGET, STOP, HALF = 30.0, 10.0, 0.5
START, YRS = 1000.0, 27.4
NSEED = 60


def acct_A(x, on, spy_ret, bo):
    """154 «그대로» — 숏 20% 얹은 세후 총액"""
    fd = Counter(f[3] for f in x["fill_log"] if f[1] == "pilot")
    vv = ([(d, v) for d, v in x["curve"]]
          + [(x["curve"][-1][0], 1.0 + x["equity_pct"] / 100.0)])
    cds, ccv, V = [vv[0][0]], [1.0], 1.0
    for i in range(1, len(vv)):
        if vv[i - 1][1] <= 0:
            break
        d = vv[i][0]
        rl = vv[i][1] / vv[i - 1][1] - 1.0
        sh = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
        V *= (1.0 + rl + sh - FEE * 0.20 * fd.get(d, 0))
        cds.append(d)
        ccv.append(max(V, 1e-9))
    real = {}
    for d, pl in x["exit_log"]:
        real[d] = real.get(d, 0.0) + pl
    return r124.taxed_window(cds, ccv, real, 0, len(ccv) - 1)


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    P = print
    P("=" * 100)
    P("156v — 🚨 **154 와 156① 의 «어긋남»을 «네 지점»으로 가른다** · 씨앗 %d판" % n_seed)
    P("=" * 100)
    P("")
    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k
    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}
    bo = BORROW / 100.0 / 252.0 * SHORT_SIZE

    # 라벨(156 이 거른 것)
    caps = {k2: v.get("cap") or []
            for k2, v in json.loads(CAP_PIT.read_text(encoding="utf-8")).items()}
    ter = json.loads(TERCILE.read_text(encoding="utf-8"))["q"]
    qd = sorted(ter)
    labeled = set()
    for y in sorted(by_f):
        for p in by_f[y]:
            rows = caps.get(p["code"]) or []
            best = None
            for dt, v in rows:
                if dt < p["entry_date"] and (best is None or dt > best[0]):
                    best = (dt, v)
            if best is None:
                continue
            lo, hh, i = 0, len(qd) - 1, 0
            while lo <= hh:
                m = (lo + hh) // 2
                if qd[m] <= best[0]:
                    i, lo = m, m + 1
                else:
                    hh = m - 1
            if qd and qd[i] <= best[0]:
                labeled.add((p["scan_date"], p["code"], p["pattern"]))

    # ── A · B — 154 «그대로»의 ev ────────────────────────────────────────
    r91.TARGET, r91.STOP, r91.HALF = TARGET, STOP, HALF
    ev_A, blocked, trunc = r91.replay(by_f)
    rs_A = r91.sim(ev_A, n_seed)
    A = [acct_A(x, on, spy_ret, bo) for x in rs_A]
    B = [acc.account(x)[0] for x in rs_A]
    P("**A** 154 «그대로»(r91.replay · 숏 20%%)      중앙 **%.0f만**  ·  ev %d 건"
      % (st.median(A), len(ev_A)), flush=True)
    P("**B** 같은 ev·같은 씨앗 · `account_lib`(숏 «없음»)  중앙 **%.0f만**  (A 대비 %+.1f%%)"
      % (st.median(B), 100.0 * (st.median(B) / st.median(A) - 1)), flush=True)

    # ── C — 라벨 없는 것만 제외 (r91.replay 의 dedup 그대로) ──────────────
    ev_C = [t for t in ev_A if (t["scan_date"], t["code"], t["pattern"]) in labeled]
    rs_C = r91.sim(ev_C, n_seed)
    C = [acc.account(x)[0] for x in rs_C]
    P("**C** B + 라벨 없는 것 제외(ev %d → %d)          중앙 **%.0f만**  (B 대비 %+.1f%%)"
      % (len(ev_A), len(ev_C), st.median(C), 100.0 * (st.median(C) / st.median(B) - 1)),
      flush=True)

    # ── D — «내» build_ev (라벨 없는 것을 «dedup 전»에 뺀다) ──────────────
    res = {}
    for y in sorted(by_f):
        for p in by_f[y]:
            key = (p["scan_date"], p["code"], p["pattern"])
            if key in labeled:
                res[key] = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP,
                                            target=TARGET, half=HALF, shares=(1.0,),
                                            add_stop="floor_entry")
    ev_D = []
    for y in sorted(by_f):
        open_until = {}
        for p in by_f[y]:
            key = (p["scan_date"], p["code"], p["pattern"])
            if key not in labeled:
                continue
            if p["code"] in open_until and p["entry_date"] <= open_until[p["code"]]:
                continue
            t = res[key]
            open_until[p["code"]] = t["masks"][()]["resolve_date"] or p["entry_date"]
            ev_D.append(t)
    rs_D = r91.sim(ev_D, n_seed)
    D = [acc.account(x)[0] for x in rs_D]
    P("**D** 156 «그대로»(내 build_ev · ev %d)         중앙 **%.0f만**  (C 대비 %+.1f%%)"
      % (len(ev_D), st.median(D), 100.0 * (st.median(D) / st.median(C) - 1)), flush=True)

    P("")
    P("```")
    P("A 154 재현      **%.0f만**   (154 기록 **11,981만** — %s)"
      % (st.median(A), "✅ 재현" if abs(st.median(A) / 11981 - 1) < 0.02 else "🚨 **어긋남**"))
    P("B 숏 제거만     **%.0f만**   (%+.1f%%  ← 155 는 +4.2%% 였다)"
      % (st.median(B), 100.0 * (st.median(B) / st.median(A) - 1)))
    P("C 라벨 제외     **%.0f만**   (%+.1f%%)" % (st.median(C), 100.0 * (st.median(C) / st.median(B) - 1)))
    P("D 내 build_ev   **%.0f만**   (%+.1f%%)   ← 156① 기록 **10,668만**"
      % (st.median(D), 100.0 * (st.median(D) / st.median(C) - 1)))
    P("")
    P("★ **뚝 떨어지는 자리가 «범인»이다.** ev 건수: A/B %d · C %d · D %d"
      % (len(ev_A), len(ev_C), len(ev_D)))
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

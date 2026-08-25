# -*- coding: utf-8 -*-
"""60번 — **원전에 가까운 국면 필터 + 전량 현금 + 귀무 검정**. 사전등록: `tasks/60`

🚨 M1 룩어헤드 차단 — 「최근 결착 50건」은 `resolve_date < 스캔일` 인 것만 쓴다.
🚨 전량 현금 구현 관문 — 국면 항상 켜짐이면 원본과 비트 단위로 같아야 한다.
🚨 귀무 검정 — 칸이 일곱이 됐으므로 「효과가 없어도 나올 최대치」를 낸다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python 60-regime-faithful.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from bisect import bisect_left
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataaxis as da                                         # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_SEED = 200
N_NULL = 200
M1_LOOKBACK = 50          # 최근 결착 건수
M1_THRESH = 0.70          # 손실 비율이 이보다 크면 «병들었다» (전수 67.0% 기준)
HLD0, HLD1 = "2017-01-01", "2021-01-31"


# ─────────────────────────────────────────────────────────────────────────
def ma_flag(curve, w):
    d = [x[0] for x in curve]
    v = [x[1] for x in curve]
    return {d[i]: (None if i + 1 < w else v[i] >= st.mean(v[i - w + 1:i + 1]))
            for i in range(len(d))}


def m1_flag(ev, cal):
    """★ 원전이 「최고의 지표」라 한 것 — **돌파 종목 자신의 최근 성적**.

    🚨 스캔일 D 에서 «이미 결착된» 거래만 본다 (`resolve_date < D`).
    반환: 날짜 → True(건강) / False(병듦)
    """
    done = sorted(((e["resolve_date"], e["result"]) for e in ev if e["resolve_date"]),
                  key=lambda x: x[0])
    dates = [x[0] for x in done]
    out, n_bad = {}, 0
    for D in cal:
        k = bisect_left(dates, D)          # resolve_date < D 인 것의 개수
        if k < M1_LOOKBACK:
            out[D] = True                  # 자료 부족 — 막지 않는다
            continue
        win = done[k - M1_LOOKBACK:k]
        assert win[-1][0] < D, "🚨 룩어헤드 — 결착 안 난 거래를 봤다"
        loss = sum(1 for _d, res in win if res != "win") / M1_LOOKBACK
        out[D] = loss <= M1_THRESH
        n_bad += (loss > M1_THRESH)
    return out, n_bad


def force_cash(ev, pmap, offdays):
    """국면이 꺼진 날 **보유를 그날 종가로 전량 청산**한 거래 목록을 만든다.

    다리를 그 날짜 앞까지만 남기고, 남은 몫을 그날 종가로 판 다리 하나를 붙인다.
    """
    off = sorted(offdays)
    out, n_cut = [], 0
    for e in ev:
        legs = e["legs"]
        last = legs[-1][0]
        i = bisect_left(off, e["entry_date"])
        # 진입 «다음»부터 마지막 다리 «전»까지 사이에 꺼진 날이 있나
        cut = None
        while i < len(off) and off[i] <= last:
            if off[i] > e["entry_date"]:
                cut = off[i]
                break
            i += 1
        if cut is None:
            out.append(e)
            continue
        p = pmap.get((e["scan_date"], e["code"], e["pattern"]))
        if p is None:
            out.append(e)
            continue
        try:
            j = p["d"].index(cut)
        except ValueError:
            out.append(e)
            continue
        keep = [lg for lg in legs if lg[0] < cut]
        rest = 1.0 - sum(lg[1] for lg in keep)
        if rest <= 1e-9:
            out.append(e)
            continue
        g = (p["c"][j] / p["entry_price"] - 1) * 100
        new = {**e, "legs": keep + [(cut, rest, g)], "resolve_date": cut,
               "result": "win" if sum(f * gg for _d, f, gg in keep + [(cut, rest, g)]) > 0
                         else "loss"}
        out.append(new)
        n_cut += 1
    return out, n_cut


def sim_band(ev, reg, n=N_SEED):
    with r41.Cost(*reg):
        rs = [sf.sim_frac(ev, slots=5, seed=i, sizing="cash") for i in range(n)]
    eq = sorted(r["equity_pct"] for r in rs)
    return {"rs": rs, "eq": st.median(eq), "p5": eq[int(n * .05)],
            "p95": eq[int(n * .95)], "mdd": st.median(r["mdd_pct"] for r in rs),
            "n_filled": st.median(r["n_filled"] for r in rs),
            "curves": [r["curve"] for r in rs[:da.N_STREAM]]}


def block_shuffle(flags, cal, block, rnd):
    """켜진 날 비율과 자기상관을 보존한 «가짜» 국면 깃발."""
    v = [flags.get(d, True) for d in cal]
    nb = (len(v) + block - 1) // block
    blocks = [v[i * block:(i + 1) * block] for i in range(nb)]
    rnd.shuffle(blocks)
    flat = [x for b in blocks for x in b][:len(cal)]
    return dict(zip(cal, flat))


# ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.", flush=True)
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by.values() for p in ps}
    eqw = json.loads((OUT / "26-eqw-us9y.json").read_text(encoding="utf-8"))
    spx = json.loads((OUT / "38-indices.json").read_text(encoding="utf-8"))["US500"]
    cal = sorted(spx)
    f50 = ma_flag([(k, spx[k]) for k in cal], 50)
    f20 = ma_flag(eqw["curve_harness_filt"], 20)

    print("=" * 80, flush=True)
    print("60번 — **원전에 가까운 국면 + 전량 현금 + 귀무 검정**", flush=True)
    print("=" * 80, flush=True)

    r41.TARGET_FILL, r41.STOP_FILL = "close", "close"
    ev0 = None
    for vname, fn, _l, _h in r41.VARIANTS:
        if vname == "1a":
            ev0, _b = r41.replay(by, fn)
    m1, n_bad = m1_flag(ev0, cal)
    on = 100.0 * sum(1 for d in cal if m1.get(d)) / len(cal)
    print("M1(주도주 건강도) — 켜진 날 **%.1f%%** · 병든 날 %d일 "
          "(최근 %d건 손실률 > %.0f%%)" % (on, n_bad, M1_LOOKBACK, M1_THRESH * 100),
          flush=True)
    if not (5 < on < 95):
        print("🚨 관문3 미통과 — M1 이 상수다. 멈춘다.", flush=True)
        return 3

    # ── 관문 1: 항상 켜짐이면 원본과 같아야 ─────────────────────────────
    ev_id, n_cut0 = force_cash(ev0, pmap, [])
    a = sf.sim_frac(ev0, slots=5, seed=0, sizing="cash")["equity_pct"]
    b = sf.sim_frac(ev_id, slots=5, seed=0, sizing="cash")["equity_pct"]
    print("관문1 전량현금 구현 — 항상 켜짐: 자르기 %d건 · 자산 차 %.2e → %s"
          % (n_cut0, abs(a - b), "**통과**" if abs(a - b) < 1e-9 else "🚨 미통과"),
          flush=True)
    if abs(a - b) > 1e-9:
        return 3

    def offd(fl):
        return [d for d in cal if fl.get(d) is False]

    CELLS = [("R0 없음", None, None),
             ("M1 주도주건강", m1, None),
             ("M1C +전량현금", m1, m1),
             ("C50 S&P50+현금", f50, f50),
             ("C20 등가중20+현금", f20, f20)]

    RES = {}
    for reg, rn in ((( 0.0, 0.0), "무비용"), ((0.0014, 0.0034), "미래에셋")):
        print("\n" + "─" * 80, flush=True)
        print("[1a · %s] 9년 · seed %d" % (rn, N_SEED), flush=True)
        print("  %-18s %6s %6s %11s %11s %8s" %
              ("칸", "진입", "체결", "자산중앙", "5%하단", "MDD"), flush=True)
        got = {}
        for cname, entry_fl, cash_fl in CELLS:
            ev = ev0 if entry_fl is None else [e for e in ev0
                                               if entry_fl.get(e["scan_date"], True)]
            n_cut = 0
            if cash_fl is not None:
                ev, n_cut = force_cash(ev, pmap, offd(cash_fl))
            r = sim_band(ev, reg)
            got[cname] = r
            print("  %-18s %6d %6d %+10.2f%% %+10.2f%% %7.1f%%%s"
                  % (cname, len(ev), r["n_filled"], r["eq"], r["p5"], r["mdd"],
                     ("  (강제청산 %d건)" % n_cut) if n_cut else ""), flush=True)
            RES["%s|%s" % (rn, cname)] = {k: v for k, v in r.items()
                                          if k not in ("rs", "curves")}
        print("  ── A. 자료 축 짝비교 (vs R0) ──", flush=True)
        for cname, _e, _c in CELLS[1:]:
            sw = da.sweep(got[cname]["curves"], got["R0 없음"]["curves"])
            w = sw["_widest"]
            rr = sw[w]
            print("    %-18s 블록%-3d 중앙 %+8.2f%%  95%% %+8.2f ~ %+8.2f → **%s**"
                  % (cname, w, rr["median"], rr["lo"], rr["hi"],
                     "0 배제" if rr["excl0"] else "0 포함"), flush=True)
            RES["%s|%s" % (rn, cname)]["paired"] = {
                "block": w, "median": rr["median"], "lo": rr["lo"],
                "hi": rr["hi"], "excl0": rr["excl0"]}

        # ── B. 귀무 검정 (무비용에서만) ──────────────────────────────────
        if rn == "무비용":
            print("  ── ★ B. **귀무 검정** — 가짜 국면 %d회 (블록 셔플) ──"
                  % N_NULL, flush=True)
            rnd = random.Random(600825)
            base = got["R0 없음"]["eq"]
            null = []
            for i in range(N_NULL):
                fake = block_shuffle(f50, cal, 20, rnd)
                ev = [e for e in ev0 if fake.get(e["scan_date"], True)]
                with r41.Cost(*reg):
                    rs = [sf.sim_frac(ev, slots=5, seed=s, sizing="cash")["equity_pct"]
                          for s in range(12)]
                null.append(st.median(rs) - base)
            null.sort()
            p95 = null[int(N_NULL * .95)]
            obs = {c: got[c]["eq"] - base for c, _e, _c in CELLS[1:]}
            best = max(obs, key=lambda k: obs[k])
            print("    귀무 분포 — 중앙 %+.2f%%p · 95%% **%+.2f%%p** · 최대 %+.2f%%p"
                  % (null[N_NULL // 2], p95, null[-1]), flush=True)
            for c in obs:
                print("    관측 %-18s %+8.2f%%p  → %s"
                      % (c, obs[c], "**귀무 95%% 초과**" if obs[c] > p95
                         else "귀무 안"), flush=True)
            print("    ★ 관측 최선 = %s (%+.2f%%p) vs 귀무 95%% %+.2f%%p → **%s**"
                  % (best, obs[best], p95,
                     "통과" if obs[best] > p95 else "**미통과 — 「고른 것」과 구분 안 됨**"),
                  flush=True)
            RES["null"] = {"median": null[N_NULL // 2], "p95": p95, "max": null[-1],
                           "obs": obs, "best": best, "pass": obs[best] > p95}
    (OUT / "60-regime-faithful.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 60-regime-faithful.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

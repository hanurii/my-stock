# -*- coding: utf-8 -*-
"""74v — **검증 세션의 독립 경로**. 사양서 `tasks/74-pyramid-rebuilt.md` 만 보고 짰다.

🚨 조사 세션의 `pyr_trigger.py` · 두뇌 세션의 `slot_sim_lots.py` · `74-pyramid-rebuilt.py`
   **어느 것도 읽지 않았다.** 옛 코드(`47-round3-pyramid.py` · `slot_sim_pyr.py` ·
   `73-pyramid-on-combo.py`)는 대조군이므로 읽었다.

단계 ① — 「산수 예측」을 실측으로 확인
--------------------------------------
두뇌 세션의 주장(사양서 §1①):

    옛 도구는 세 단을 «1/3 @ 1.000 + 2/3 @ 1.030» 으로 뭉갠다.
    → 옛 P2 값은 «부풀려진» 값이고, 고치면 자산·하단 «둘 다 내려간다».

이 파일이 하는 일:

  (a) **셈 사실** — `resolve_pyr` 이 두 번째 증액을 `add` 에 안 싣는 건수를 «센다».
  (b) **독립 재구성** — 사양서만 보고 트랜치 목록을 다시 만들고,
      해결자의 «청산가»로 역산해 서로 맞는지 **다른 경로로** 확인한다
      (손실: 청산가 = min(a×0.92, 시가) · 승리: 첫 청산가 = max(a×1.20, 시가)).
  (c) **분포** — 옛 시뮬 취득단가 vs 참 취득단가의 벌어짐을 «거래별»로 잰다
      (중앙 · P10 · P90). 두뇌 세션의 산수는 1%p 균일을 가정하지만
      실제 체결가는 갭업 때문에 다르다.
  (d) **자산까지** — `net()` 이 g 에 «아핀»이고 거래당 수익률이 트랜치별
      수익률의 가중평균이므로, 조화합이 같은 «등가 2단 가격»
          pilot/epx + (1−pilot)/P* = Σ (1/3)/epx_i
      을 넣으면 **옛 시뮬로도 참 취득단가를 정확히 재현**한다.
      → 옛 판 vs 등가판을 같은 seed 로 돌려 «가격 통로만» 떼어 낸다.
      ⚠️ 이건 **가격 통로**만이다. 참 세계는 현금이 2단이 아니라 3단에 나가므로
         **현금 시점 통로**는 여기 없다 — 그건 새 시뮬이 답한다.
  (e) **꼬리 질문**(유형 19) — 「이 꼬리는 전체의 몇 분의 몇인가」.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/74v-independent-gate.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                             # noqa: E402
import slot_sim_pyr as sp                                   # noqa: E402

_s = _u.spec_from_file_location("r61b", HERE / "61b-matched-null.py")
r61b = _u.module_from_spec(_s)
_s.loader.exec_module(r61b)
r41, r61 = r61b.r41, r61b.r61

_s3 = _u.spec_from_file_location("r47", HERE / "47-round3-pyramid.py")
r47 = _u.module_from_spec(_s3)
_s3.loader.exec_module(r47)

OUT = ROOT / ".cache" / "bt5y" / "out"
COST = (0.0, 0.002)          # 우대수수료 — 73번과 같다
RISK, CAP = 0.02, 0.20       # = 5칸 20%
N_SEED = 200                 # 73b 와 같다
SLOTS = dict(max_positions=5, cash_rule="per_slot")   # 73b 의 «5칸 규약»
ADDS_P1 = ((3.0, 0.5),)
ADDS_P2 = ((3.0, 1 / 3), (6.0, 1 / 3))


# ─────────────────────────────────────────────────────────────────────────
# 독립 재구성 — 사양서 §1 만 보고 짰다
# ─────────────────────────────────────────────────────────────────────────
def my_lots(p, adds, resolve_date):
    """진입일부터 결착일까지 걸으며 «실제로 산 트랜치»를 전부 만든다.

    규약(사양서 §1 · 47번 문서열):
      · 발동선 = 진입가 × (1 + 상승률/100)
      · 그날 고가가 발동선 이상이면 산다.  체결가 = max(발동선, 시가)  (시가 없으면 발동선)
      · 증액은 «그날의 청산 판정보다 먼저» 일어난다 → 결착일도 «포함»해서 걷는다
    반환: [(날짜, 가격, 목표대비 몫), ...]  — 첫 원소가 파일럿
    """
    h, d = p["h"], p["d"]
    o = p.get("o") or [None] * len(d)
    epx = p["entry_price"]
    pilot = 1.0 - sum(a[1] for a in adds)
    out = [(p["entry_date"], epx, pilot)]
    pend = list(adds)
    for i in range(len(d)):
        while pend and h[i] is not None and h[i] >= epx * (1 + pend[0][0] / 100.0):
            lvl = epx * (1 + pend[0][0] / 100.0)
            px = lvl if o[i] is None else max(lvl, o[i])
            out.append((d[i], px, pend[0][1]))
            pend.pop(0)
        if d[i] == resolve_date:
            break
    return out


def wavg(lots):
    s = sum(f for _d, _px, f in lots)
    return sum(px * f for _d, px, f in lots) / s if s else 0.0


def harm(lots):
    """Σ (몫/합) / 가격 — 거래당 수익률을 결정하는 «진짜» 통계량."""
    s = sum(f for _d, _px, f in lots)
    return sum((f / s) / px for _d, px, f in lots) if s else 0.0


def per_trade_r(exits, tranches):
    """옛 시뮬 `close_out` 과 «같은» 식. tranches = [(취득가, 비중), ...]"""
    tot = sum(w for _px, w in tranches)
    return sum(fr * slot_sim.net(round(px / epx_i * 100 - 100, 2)) * (w_i / tot)
               for _d, fr, px in exits for epx_i, w_i in tranches)


def replay_pyr(paths, adds):
    """73번과 «같은» open_until 규약."""
    ev = []
    for y in sorted(paths):
        open_until = {}
        for p in paths[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                continue
            e = r47.resolve_pyr(p, "limit", "market", stop=8.0, target=20.0, adds=adds)
            open_until[c] = e.get("resolve_date") or p["entry_date"]
            e["stop_frac"] = 0.08
            e["_path"] = p
            ev.append(e)
    return ev


def pct(xs, q):
    if not xs:
        return float("nan")
    ys = sorted(xs)
    return ys[min(len(ys) - 1, max(0, int(round(q * (len(ys) - 1)))))]


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 로 실행해야 한다 (지금 %d)" % r41.YEARS[0])
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2

    # ── 「지금 조합」 — 73번과 같은 경로 단계 필터 ──────────────────────
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for d in monthly.values() for y in d if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pctm = r61b.make_flags(mret, sector)

    def keep_path(p):
        sn = sector.get(p["code"])
        if sn:
            tp = top.get(r61.prev_ym(p["scan_date"][:7], 1))
            if tp is not None and sn not in tp:
                return False
        v = pctm.get(r61.prev_ym(p["scan_date"][:7], 1), {}).get(p["code"])
        return (v is None) or (0.10 <= v < 0.30)

    by2 = {y: [p for p in ps if keep_path(p)] for y, ps in by.items()}
    print("=" * 92)
    print("74v ① — 「세 단은 실제보다 싸게 산 것으로 계산된다」를 독립으로 검정")
    print("=" * 92)
    print("경로 %d → 지금 조합 %d"
          % (sum(len(v) for v in by.values()), sum(len(v) for v in by2.values())),
          flush=True)

    rows = {}
    for nm, adds, pilot in (("P1 두 단", ADDS_P1, 0.5), ("P2 세 단", ADDS_P2, 1 / 3)):
        ev = replay_pyr(by2, adds)
        n_add_true = n_add_rec = 0
        n_k = {0: 0, 1: 0, 2: 0}
        chk_ok = chk_bad = chk_skip = 0
        gap_px, gap_r, recs = [], [], []
        for e in ev:
            p = e["_path"]
            lots = my_lots(p, adds, e["resolve_date"])
            k = len(lots) - 1
            n_k[k] = n_k.get(k, 0) + 1
            n_add_true += k
            n_add_rec += (1 if e["add"] else 0)

            # (b) 독립 확인 — 해결자의 청산가로 평균단가를 역산
            a_mine = wavg(lots)
            o = p.get("o") or [None] * len(p["d"])
            try:
                ri = p["d"].index(e["resolve_date"])
            except ValueError:
                ri = None
            if e["result"] == "loss" and ri is not None:
                want = a_mine * 0.92
                got = e["exits"][0][2]
                oo = o[ri]
                exp = want if oo is None else min(want, oo)
                if abs(got - exp) <= 1e-9 * max(1.0, abs(exp)):
                    chk_ok += 1
                else:
                    chk_bad += 1
                    if chk_bad <= 3:
                        recs.append(("loss", e["code"], e["entry_date"], got, exp))
            elif e["result"] == "win":
                # 첫 청산 = 목표 도달일 · max(a×1.20, 시가)
                di = p["d"].index(e["exits"][0][0])
                want = a_mine * 1.20
                oo = o[di]
                exp = want if oo is None else max(want, oo)
                got = e["exits"][0][2]
                if abs(got - exp) <= 1e-9 * max(1.0, abs(exp)):
                    chk_ok += 1
                else:
                    chk_bad += 1
                    if chk_bad <= 3:
                        recs.append(("win", e["code"], e["entry_date"], got, exp))
            else:
                chk_skip += 1

            # (c) 옛 시뮬이 «쓰는» 트랜치 vs 참 트랜치
            epx = p["entry_price"]
            if e["add"]:
                tw_old = [(epx, pilot), (e["add"][1], 1.0 - pilot)]
            else:
                tw_old = [(epx, pilot)]
            tw_new = [(px, f) for _d, px, f in lots]
            a_old = sum(px * w for px, w in tw_old) / sum(w for _p, w in tw_old)
            gap_px.append((a_mine / a_old - 1) * 100)
            gap_r.append(per_trade_r(e["exits"], tw_old) - per_trade_r(e["exits"], tw_new))
            e["_lots"] = lots
            e["_k"] = k
            e["_r_true"] = per_trade_r(e["exits"], tw_new)
        print("")
        print("── %s ──" % nm, flush=True)
        print("  거래 %d · 실제 증액 %d회 · `add` 에 실린 것 %d회 → **누락 %d회**"
              % (len(ev), n_add_true, n_add_rec, n_add_true - n_add_rec), flush=True)
        print("  증액 횟수별 거래 수: %s"
              % " · ".join("%d회 %d건(%.1f%%)" % (k, v, 100.0 * v / len(ev))
                           for k, v in sorted(n_k.items())), flush=True)
        print("  독립 역산 대조 — 일치 %d · **불일치 %d** · 대조불가(ambiguous/unresolved) %d"
              % (chk_ok, chk_bad, chk_skip), flush=True)
        for r in recs:
            print("     불일치 예: %s" % (r,), flush=True)
        nz = [x for x in gap_px if abs(x) > 1e-12]
        print("  취득단가 벌어짐(참 − 옛, %%): 0 아닌 건 %d건(%.1f%%) · "
              "전체 중앙 %+.4f · P10 %+.4f · P90 %+.4f"
              % (len(nz), 100.0 * len(nz) / len(ev), pct(gap_px, .5),
                 pct(gap_px, .10), pct(gap_px, .90)), flush=True)
        if nz:
            print("     0 아닌 것만: 중앙 %+.4f · P10 %+.4f · P90 %+.4f · 최대 %+.4f"
                  % (pct(nz, .5), pct(nz, .10), pct(nz, .90), max(nz)), flush=True)
        nzr = [x for x in gap_r if abs(x) > 1e-12]
        print("  거래당 수익률 부풀림(옛 − 참, %%p): 0 아닌 건 %d건 · "
              "평균 %+.4f · 중앙 %+.4f · P10 %+.4f · P90 %+.4f · 최대 %+.4f"
              % (len(nzr), (st.mean(gap_r) if gap_r else 0.0), pct(gap_r, .5),
                 pct(gap_r, .10), pct(gap_r, .90), (max(gap_r) if gap_r else 0.0)),
              flush=True)
        # 유형 19 — 꼬리가 결론을 만드는가
        if nzr:
            tot = sum(gap_r)
            top5 = sorted(gap_r, reverse=True)[:5]
            print("  🔎 꼬리 점검 — 부풀림 합 %+.2f%%p 중 상위 5건이 %+.2f%%p (%.1f%%) · "
                  "음수 건 %d개"
                  % (tot, sum(top5), (100.0 * sum(top5) / tot if tot else 0.0),
                     sum(1 for x in gap_r if x < -1e-12)), flush=True)
        byk = {}
        for e in ev:
            byk.setdefault(e["_k"], []).append(e["_r_true"])
        print("  증액 횟수별 «참» 거래당 수익률: %s"
              % " · ".join("%d회 n=%d %+.2f%%" % (k, len(v), st.mean(v))
                           for k, v in sorted(byk.items())), flush=True)
        rows[nm] = {"n": len(ev), "n_add_true": n_add_true, "n_add_rec": n_add_rec,
                    "k": n_k, "chk_ok": chk_ok, "chk_bad": chk_bad,
                    "gap_px_med": pct(gap_px, .5), "gap_r_mean": st.mean(gap_r) if gap_r else 0.0,
                    "ev": ev}

    # ── (d) 자산까지 — 등가 2단 가격으로 «가격 통로»만 떼어 낸다 ────────
    print("")
    print("── (d) 자산 통로 — 옛 판 vs 「참 취득단가 등가판」 (seed %d) ──" % N_SEED,
          flush=True)
    ev2 = rows["P2 세 단"]["ev"]
    ev2_fix = []
    n_equiv_bad = 0
    for e in ev2:
        f = dict(e)
        lots = e["_lots"]
        if len(lots) >= 2:
            epx = e["entry_px"]
            pilot = 1 / 3
            need = harm(lots) - pilot / epx        # = (1−pilot)/P*
            if need > 1e-15:
                f["add"] = (e["add"][0], (1.0 - pilot) / need)
            else:
                n_equiv_bad += 1
        ev2_fix.append(f)
    print("  등가가격 실패 %d건" % n_equiv_bad, flush=True)

    # 🔎 등가가격이 «정말» 참 트랜치를 재현하는가 — 이 검정의 전제다
    worst = 0.0
    for e, f in zip(ev2, ev2_fix):
        if len(e["_lots"]) < 2:
            continue
        tw_eq = [(e["entry_px"], 1 / 3), (f["add"][1], 2 / 3)]
        worst = max(worst, abs(per_trade_r(e["exits"], tw_eq) - e["_r_true"]))
    print("  🔎 등가가격 자체 검정 — 거래당 수익률 최대 편차 %.3e%%p "
          "(0 이 아니면 round(g,2) 때문)" % worst, flush=True)

    # 🚨 두 통로를 «같은 자»로 — 목표 대비 비중 × 거래당 수익률
    #    k=0: 옛·참 둘 다 1/3 · k=1: 옛 1 vs 참 2/3 · k=2: 둘 다 1
    c_old = c_new = 0.0
    per_k = {}
    for e in ev2:
        k = e["_k"]
        w_o = (1 / 3) if k == 0 else 1.0
        w_n = (1 / 3) if k == 0 else (2 / 3 if k == 1 else 1.0)
        epx = e["entry_px"]
        tw_o = ([(epx, 1 / 3)] if not e["add"]
                else [(epx, 1 / 3), (e["add"][1], 2 / 3)])
        r_o = per_trade_r(e["exits"], tw_o)
        c_old += w_o * r_o
        c_new += w_n * e["_r_true"]
        a = per_k.setdefault(k, [0, 0.0, 0.0])
        a[0] += 1
        a[1] += w_o * r_o
        a[2] += w_n * e["_r_true"]
    n = len(ev2)
    # 두 통로를 «따로» — 가격만 고친 중간값을 끼워 넣는다
    c_mid = 0.0
    n_line_price = n_line_size = 0
    for e in ev2:
        k = e["_k"]
        w_o = (1 / 3) if k == 0 else 1.0
        c_mid += w_o * e["_r_true"]          # 가격만 고침 · 비중은 옛 규약
        if k == 2:
            n_line_price += 1
        if k == 1:
            n_line_size += 1
    print("")
    print("")
    print("  ── 두 결함을 «같은 자»로: 목표대비 비중 × 거래당 수익률 (거래 %d건 평균) ──" % n,
          flush=True)
    for k in sorted(per_k):
        cnt, so, sn = per_k[k]
        print("     증액 %d회 n=%4d · 옛 %+7.4f · 참 %+7.4f · 차 %+7.4f  (전체 평균 기준)"
              % (k, cnt, so / n, sn / n, (so - sn) / n), flush=True)
    print("     합계            · 옛 %+7.4f · 참 %+7.4f · **차 %+7.4f**"
          % (c_old / n, c_new / n, (c_old - c_new) / n), flush=True)
    print("     ── 통로 분해 (차 = 옛 − 참) ──", flush=True)
    print("        가격 통로 %+7.4f  (뭉갠 취득가 · 걸린 줄이 %d회 돌았다)"
          % ((c_old - c_mid) / n, n_line_price), flush=True)
    print("        크기 통로 %+7.4f  (한 번만 난 증액에 2/3 · 걸린 줄이 %d회 돌았다)"
          % ((c_mid - c_new) / n, n_line_size), flush=True)
    print("     → 가격 결함(2회)과 크기 결함(1회)이 **부호가 반대**다. 합이 답이다.",
          flush=True)

    # 잔차가 0 과 구분되는가 — 진입일 블록 부트스트랩 (자료 축)
    import random as _rnd
    dif = {}
    for e in ev2:
        k = e["_k"]
        w_o = (1 / 3) if k == 0 else 1.0
        w_n = (1 / 3) if k == 0 else (2 / 3 if k == 1 else 1.0)
        epx = e["entry_px"]
        tw_o = ([(epx, 1 / 3)] if not e["add"]
                else [(epx, 1 / 3), (e["add"][1], 2 / 3)])
        dif.setdefault(e["entry_date"], []).append(
            w_o * per_trade_r(e["exits"], tw_o) - w_n * e["_r_true"])
    days = sorted(dif)
    for BL in (20, 40):
        rg = _rnd.Random(410824)
        nb = max(1, len(days) // BL)
        bs = []
        for _ in range(1000):
            vals = []
            for _b in range(nb):
                st0 = rg.randrange(0, max(1, len(days) - BL))
                for dd in days[st0:st0 + BL]:
                    vals.extend(dif[dd])
            bs.append(sum(vals) / len(vals))
        bs.sort()
        print("     블록 %d일 부트스트랩(1000회, 날 %d) — 잔차 95%% 구간 [%+.4f, %+.4f]"
              % (BL, len(days), bs[25], bs[975]), flush=True)
    n_over = sum(1 for e in ev2 if e["_k"] == 1)
    print("  🚨 **크기 결함**(두뇌 세션 §1① 에 없던 것) — 증액이 «한 번만» 난 %d건(%.1f%%)에서"
          " 옛 시뮬은 목표의 2/3 를 넣는다. 참 세계는 1/3 이다 → **목표 크기의 1.5배**를 건다."
          % (n_over, 100.0 * n_over / len(ev2)), flush=True)
    with r41.Cost(*COST):
        old = [sp.sim_pyr(ev2, risk=RISK, cap=CAP, seed=i, pilot=1 / 3, **SLOTS)
               for i in range(N_SEED)]
        new = [sp.sim_pyr(ev2_fix, risk=RISK, cap=CAP, seed=i, pilot=1 / 3, **SLOTS)
               for i in range(N_SEED)]
    for lab, rs in (("옛 판(뭉갠 값)", old), ("참 취득단가 등가판", new)):
        eq = sorted(x["equity_pct"] for x in rs)
        print("  %-18s 자산중앙 %+9.2f%% · 5%%하단 %+9.2f%% · MDD %6.2f%% · "
              "체결 %d · 증액 %d · 증액막힘 %d"
              % (lab, st.median(eq), eq[int(N_SEED * .05)],
                 st.median(x["mdd_pct"] for x in rs),
                 int(st.median(x["n_filled"] for x in rs)),
                 int(st.median(x["n_added"] for x in rs)),
                 int(st.median(x["n_add_blocked"] for x in rs))), flush=True)
    d_eq = [n["equity_pct"] - o["equity_pct"] for o, n in zip(old, new)]
    print("  짝비교(등가판 − 옛 판, 같은 seed): 중앙 %+.2f%%p · "
          "음수 %d/%d판 · 최소 %+.2f · 최대 %+.2f"
          % (st.median(d_eq), sum(1 for x in d_eq if x < 0), N_SEED,
             min(d_eq), max(d_eq)), flush=True)
    print("")
    print("  ⚠️ 이 표는 **가격 통로만** 뗀 것이다. 참 세계는 현금이 3단에 나가므로"
          " «현금 시점»은 여전히 옛 규약이다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


# ═════════════════════════════════════════════════════════════════════════
# 단계 ② — 「새 고가 눌림 후 재돌파」 방아쇠, **사양서 §3 만 보고** 짰다
# ═════════════════════════════════════════════════════════════════════════
# 🚨 조사 세션의 `pyr_trigger.py` 를 «보기 전»에 쓴다.
#
# 사양서 §3 이 정하지 «않은» 것 — 내가 고른 해석을 여기 적는다.
#   (가) TR 은 첫 봉에서 전일 종가가 없다 → `h−l` 로 둔다.
#        ATR = 최근 min(14, 쌓인 봉) 의 평균. **3봉 미만이면 눌림 판정 보류**(§3 명시).
#   (나) H 를 «오늘 고가까지» 갱신한 뒤 오늘 저가를 잰다(문장 순서 그대로).
#        대안(어제까지의 H 로 잰다)도 같이 세어 «몇 건이 갈리는지» 찍는다.
#   (다) 「아래로 내려가고」 = 엄격히 `<`.
#   (라) 「2거래일 이상 머물면」 = **연속 2일** 모두 저가가 선 아래.
#        선은 그날의 ATR 로 매일 다시 잰다(H 는 달리는 최대).
#   (마) 잠그는 L = **확정된 날의 달리는 H**.
#   (바) 「그 뒤」 = 확정일 **다음 날부터** 고가 ≥ L 을 찾는다.
#   (사) 증액 뒤에는 눌림 상태를 «지우고» 다시 찾는다(H 는 계속 달린다).
#   (아) ④ 목표는 **진입가 × 1.20**. 평균단가로 잡으면 방아쇠가 트랜치에 의존해
#        «순환»한다(§2 가 순환 없음을 규약으로 못박았다). **더 «이른» 날에 닿았으면 막는다**
#        — 같은 날은 막지 않는다(그 날 L 은 목표선보다 아래다).
#   (자) ⑤ 250봉 = 인덱스 `i < 250`.

ATR_N = 14


def my_atr(p, cap=None):
    """경로 봉만으로 ATR. 어느 시점에서도 «그날까지»만 쓴다(룩어헤드 아님)."""
    h, l, c = p["h"], p["l"], p["c"]
    n = len(h) if cap is None else min(len(h), cap)
    tr, out = [], []
    for i in range(n):
        if h[i] is None or l[i] is None:
            tr.append(None)
            out.append(None)
            continue
        t = h[i] - l[i]
        if i > 0 and c[i - 1] is not None:
            t = max(t, abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        tr.append(t)
        w = [x for x in tr[max(0, i - ATR_N + 1):i + 1] if x is not None]
        out.append(sum(w) / len(w) if len(w) >= 3 else None)
    return out


def my_trigger(p, n_adds, atr_mult=1.0, dwell=2, cap_bars=250, h_incl_today=True,
               dwell_on="low"):
    """사양서 §3 의 「새 고가 눌림 후 재돌파」. 반환 [(날짜, 체결가, 인덱스), ...]"""
    h, l, d, c = p["h"], p["l"], p["d"], p["c"]
    o = p.get("o") or [None] * len(d)
    epx = p["entry_price"]
    tgt = epx * 1.20
    atr = my_atr(p, cap_bars)
    n = min(len(d), cap_bars)
    H = None
    run = 0                 # 선 아래 연속 일수
    lock = None             # 잠근 방아쇠 선 L
    hit_target_before = False
    out = []
    for i in range(n):
        hi, lo = h[i], l[i]
        H_prev = H
        if hi is not None:
            H = hi if H is None else max(H, hi)
        base = H if h_incl_today else H_prev

        # ③ 재돌파 — 잠긴 선이 있고 «확정일 다음 날부터»
        if lock is not None and hi is not None and hi >= lock["L"] and i > lock["i"]:
            if not hit_target_before and len(out) < n_adds:
                px = lock["L"] if o[i] is None else max(lock["L"], o[i])
                out.append((d[i], px, i))
                lock = None
                run = 0
            else:
                lock = None
                run = 0

        # ② 눌림 — 저가가 base − ATR 아래에서 연속 dwell 일
        probe = lo if dwell_on == "low" else c[i]
        if base is not None and probe is not None and atr[i] is not None:
            if probe < base - atr_mult * atr[i]:
                run += 1
                if run >= dwell and lock is None:
                    lock = {"L": base, "i": i}
            else:
                run = 0
        else:
            run = 0

        # ④ 목표에 닿았는가 — «다음 날부터» 막는다
        if hi is not None and hi >= tgt:
            hit_target_before = True
        if len(out) >= n_adds:
            break
    return out


def stage2() -> int:
    """방아쇠를 내 방식으로 구현해 «후보 증액»을 통째로 내보낸다.
    조사 세션 `pyr_trigger.py` 가 커밋되면 이 파일과 대조한다."""
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 로 실행해야 한다 (지금 %d)" % r41.YEARS[0])
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
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

    paths = [p for y in sorted(by) for p in by[y] if keep_path(p)]
    print("=" * 92)
    print("74v ② — 「새 고가 눌림 후 재돌파」 독립 구현 (사양서 §3 만 보고)")
    print("=" * 92)
    print("경로 %d" % len(paths), flush=True)

    dump = {}
    for lab, nad, mult in (("H 1/2→1/2", 1, 1.0), ("T 1/3×3", 2, 1.0),
                           ("민감도 0.5ATR", 1, 0.5), ("민감도 1.5ATR", 1, 1.5)):
        n_any = n_full = 0
        first_i, diff_alt, diff_cls = [], 0, 0
        rows = {}
        for p in paths:
            a = my_trigger(p, nad, atr_mult=mult)
            b = my_trigger(p, nad, atr_mult=mult, h_incl_today=False)
            cc = my_trigger(p, nad, atr_mult=mult, dwell_on="close")
            key = lambda z: [(x[0], round(x[1], 6)) for x in z]
            if key(a) != key(b):
                diff_alt += 1
            if key(a) != key(cc):
                diff_cls += 1
            if a:
                n_any += 1
                first_i.append(a[0][2])
            if len(a) >= nad:
                n_full += 1
            rows["%s|%s|%s" % (p["scan_date"], p["code"], p["pattern"])] =                 [[x[0], x[1], 1.0 / (nad + 1)] for x in a]
        print("  %-14s 증액 한 번 이상 %4d(%.1f%%) · 끝까지 %4d(%.1f%%) · "
              "첫 증액 봉 중앙 %s · 갈림: H해석 %d(%.1f%%) · 머묾=종가 %d(%.1f%%)"
              % (lab, n_any, 100.0 * n_any / len(paths), n_full,
                 100.0 * n_full / len(paths),
                 ("%d" % st.median(first_i)) if first_i else "—",
                 diff_alt, 100.0 * diff_alt / len(paths),
                 diff_cls, 100.0 * diff_cls / len(paths)), flush=True)
        dump[lab] = rows
    f = OUT / "74v-trigger.json"
    f.write_text(json.dumps(dump, ensure_ascii=False), encoding="utf-8")
    print("저장: %s" % f, flush=True)
    return 0


# ═════════════════════════════════════════════════════════════════════════
# 단계 ②-대조 — 내 해결자 vs 조사 세션 `pyr_trigger.resolve_all_masks`
# ═════════════════════════════════════════════════════════════════════════
# 🚨 **독립인 것은 «방아쇠»뿐이다.** 청산(−8% / +20% 절반 / 본전→25일 추격)은
#    양쪽 다 `47-round3-pyramid.py::_phase2` 에서 왔다 — «공유 의존»이지 독립이 아니다.
#    (두뇌 세션이 관문 A 에서 같은 지적을 했다.)
# 내 해결자는 위 `my_trigger` 의 규약을 그대로 쓰되 청산과 얽히게 «하루씩» 푼다.

def my_resolve(p, shares, atr_mult=1.0, dwell=2, cap_bars=None,
               stop=8.0, target=20.0, half=0.5, trail=25,
               add_stop="floor_entry", target_base="avg",
               h_incl_today=True, dwell_on="low"):
    """전부 산다고 보고(mask 전부 True) 경로를 푼다.
    `target_base` — ④ 목표를 무엇에 걸 것인가: "avg"(평균단가) 또는 "entry"(진입가)."""
    h, l, c, d = p["h"], p["l"], p["c"], p["d"]
    o = p.get("o") or [None] * len(d)
    epx = p["entry_price"]
    atr = my_atr(p, cap_bars)
    n = len(c) if cap_bars is None else min(len(c), cap_bars)
    lots = [(d[0], epx, shares[0])]
    sched = []
    k, H, run, L, armed = 1, None, 0, None, -1

    def avg():
        s = sum(x[2] for x in lots)
        return sum(px * fr for _dt, px, fr in lots) / s if s else epx

    def close(rd, res, ex, at_end):
        return {"lots": lots, "sched": sched, "exits": ex, "resolve_date": rd,
                "result": res, "at_end": at_end}

    for i in range(n):
        if k < len(shares):
            if L is not None:
                if i > armed and h[i] is not None and h[i] >= L:
                    px = L if o[i] is None else max(L, o[i])
                    sched.append((d[i], px, shares[k]))
                    lots.append((d[i], px, shares[k]))
                    k += 1
                    H, run, L, armed = h[i], 0, None, -1
            else:
                H_prev = H
                if h[i] is not None:
                    H = h[i] if H is None else max(H, h[i])
                base = H if h_incl_today else H_prev
                probe = l[i] if dwell_on == "low" else c[i]
                if base is not None and atr[i] is not None and probe is not None:
                    run = run + 1 if probe < base - atr_mult * atr[i] else 0
                else:
                    run = 0
                if run >= dwell:
                    L, armed = base, i
        a = avg()
        S = a * (1 - stop / 100)
        if add_stop == "floor_entry" and len(lots) > 1:
            S = max(S, epx)
        T = (a if target_base == "avg" else epx) * (1 + target / 100)
        hit_t = h[i] is not None and h[i] >= T
        hit_s = l[i] is not None and l[i] <= S
        if i == 0:
            if hit_s:
                return close(d[0], "ambiguous", [(d[0], 1.0, c[0])], False)
            if hit_t:
                return _my_phase2(p, i, a, half, trail, close, T, o, n)
            continue
        if hit_t and hit_s:
            return close(d[i], "ambiguous", [(d[i], 1.0, c[i])], False)
        if hit_t:
            return _my_phase2(p, i, a, half, trail, close, T, o, n)
        if hit_s:
            px = S if o[i] is None else min(S, o[i])
            return close(d[i], "loss", [(d[i], 1.0, px)], False)
    return close(d[n - 1], "unresolved", [(d[n - 1], 1.0, c[n - 1])], True)


def _my_phase2(p, i, a, half, trail, close, T, o, n):
    l, c, d = p["l"], p["c"], p["d"]
    tpx = T if o[i] is None else max(T, o[i])
    ex = [(d[i], half, tpx)]
    for j in range(i + 1, n):
        seg = [x for x in l[max(0, j - trail):j] if x is not None]
        s2 = max(a, min(seg)) if seg else a
        if l[j] is not None and l[j] <= s2:
            px = s2 if o[j] is None else min(s2, o[j])
            ex.append((d[j], 1.0 - half, px))
            return close(d[j], "win", ex, False)
    ex.append((d[n - 1], 1.0 - half, c[n - 1]))
    return close(d[n - 1], "win", ex, True)


def stage2b() -> int:
    import pyr_trigger as pt
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for d in monthly.values() for y in d if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pctm = r61b.make_flags(mret, sector)

    def keep_path(q):
        sn = sector.get(q["code"])
        if sn:
            tp = top.get(r61.prev_ym(q["scan_date"][:7], 1))
            if tp is not None and sn not in tp:
                return False
        v = pctm.get(r61.prev_ym(q["scan_date"][:7], 1), {}).get(q["code"])
        return (v is None) or (0.10 <= v < 0.30)

    paths = [q for y in sorted(by) for q in by[y] if keep_path(q)]
    print("=" * 92)
    print("74v ②-대조 — 내 해결자 vs pyr_trigger (mask 전부 True)")
    print("=" * 92)
    print("경로 %d" % len(paths), flush=True)

    for lab, shares in (("H 1/2→1/2", (0.5, 0.5)), ("T 1/3×3", (1 / 3, 1 / 3, 1 / 3))):
        mask = tuple([True] * (len(shares) - 1))
        n_sched_diff = n_rd_diff = n_res_diff = n_px_diff = 0
        n_both_none = n_only_mine = n_only_theirs = 0
        ex = []
        for q in paths:
            mine = my_resolve(q, shares)
            got = pt.resolve_all_masks(q, shares=shares)[mask]
            a = [(x[0], round(x[1], 9), round(x[2], 9)) for x in mine["sched"]]
            b = [(x[0], round(x[1], 9), round(x[2], 9)) for x in got["sched"]]
            if a != b:
                n_sched_diff += 1
                if [x[0] for x in a] == [x[0] for x in b]:
                    n_px_diff += 1
                if not a and b:
                    n_only_theirs += 1
                elif a and not b:
                    n_only_mine += 1
                if len(ex) < 6:
                    ex.append((q["code"], q["scan_date"], a[:3], b[:3],
                               mine["resolve_date"], got["resolve_date"],
                               mine["result"], got["result"], len(q["d"])))
            if not a and not b:
                n_both_none += 1
            if mine["resolve_date"] != got["resolve_date"]:
                n_rd_diff += 1
            if mine["result"] != got["result"]:
                n_res_diff += 1
        print("")
        print("── %s ──" % lab, flush=True)
        print("  증액 일정 불일치 **%d건 (%.2f%%)** · 그중 날짜는 같고 «가격»만 %d건"
              % (n_sched_diff, 100.0 * n_sched_diff / len(paths), n_px_diff), flush=True)
        print("  한쪽만 증액: 나만 %d · 저쪽만 %d · 양쪽 다 증액 없음 %d"
              % (n_only_mine, n_only_theirs, n_both_none), flush=True)
        print("  결착일 불일치 %d건 · 결과 라벨 불일치 %d건" % (n_rd_diff, n_res_diff),
              flush=True)
        for r in ex:
            print("     %s %s 봉%d | 나 %s → %s(%s) | 저쪽 %s → %s(%s)"
                  % (r[0], r[1], r[8], r[2], r[4], r[6], r[3], r[5], r[7]), flush=True)
    return 0


def stage2c() -> int:
    """🚨 유형 2′ — 「0 불일치」가 «검정이 아니라 같은 계산»일 수 있다.
    일부러 규약을 하나씩 틀어 **대조가 그걸 잡아내는지** 본다.
    한 줄이라도 0 이 나오면 그 축은 «대조가 못 보는 축»이다."""
    import pyr_trigger as pt
    if r41.YEARS[0] != 2017:
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        return 2
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for d in monthly.values() for y in d if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pctm = r61b.make_flags(mret, sector)

    def keep_path(q):
        sn = sector.get(q["code"])
        if sn:
            tp = top.get(r61.prev_ym(q["scan_date"][:7], 1))
            if tp is not None and sn not in tp:
                return False
        v = pctm.get(r61.prev_ym(q["scan_date"][:7], 1), {}).get(q["code"])
        return (v is None) or (0.10 <= v < 0.30)

    paths = [q for y in sorted(by) for q in by[y] if keep_path(q)]
    print("=" * 92)
    print("74v ②-감도 — 「0 불일치」가 진짜 검정인가 (경로 %d)" % len(paths))
    print("=" * 92)
    MUT = (("(대조) 내가 고른 그대로", {}),
           ("④ 목표를 «진입가»에 건다", dict(target_base="entry")),
           ("⑤ 250봉에서 자른다", dict(cap_bars=250)),
           ("(나) H 에 오늘 고가를 안 넣는다", dict(h_incl_today=False)),
           ("(라) 「머물면」을 종가로 잰다", dict(dwell_on="close")),
           ("머무는 날 2 → 3", dict(dwell=3)),
           ("눌림 깊이 1.0 → 1.5 ATR", dict(atr_mult=1.5)),
           ("증액 후 손절 바닥 없음", dict(add_stop="avg")))
    for vlab, shares in (("H 1/2→1/2", (0.5, 0.5)),
                         ("T 1/3×3", (1 / 3, 1 / 3, 1 / 3))):
        mask = tuple([True] * (len(shares) - 1))
        theirs = []
        for q in paths:
            r = pt.resolve_all_masks(q, shares=shares)[mask]
            theirs.append([(x[0], round(x[1], 9), round(x[2], 9)) for x in r["sched"]])
        print("")
        print("── %s ──" % vlab, flush=True)
        for lab, kw in MUT:
            bad = 0
            for q, b in zip(paths, theirs):
                m = my_resolve(q, shares, **kw)
                if [(x[0], round(x[1], 9), round(x[2], 9)) for x in m["sched"]] != b:
                    bad += 1
            print("  %-28s 불일치 %5d (%5.2f%%)%s"
                  % (lab, bad, 100.0 * bad / len(paths),
                     "   ← 대조가 «못 보는» 축" if (bad == 0 and kw) else ""), flush=True)
    return 0




# ═════════════════════════════════════════════════════════════════════════
# 단계 ③ — 관문. 새 시뮬 `slot_sim_lots.py` 에 «내 코드로» 건다
# ═════════════════════════════════════════════════════════════════════════
# 관문은 두뇌 세션 개정본(③′③″③‴)을 따른다. 관문마다
# **「이 관문이 실패할 수 있는가」**를 같이 찍는다 — 두뇌 세션 자기 지적 1.

def my_levels(p, shares, levels, mask, stop=8.0, target=20.0, half=0.5,
              trail=25, add_stop="avg"):
    """옛 «+3%/+6% 수준» 방아쇠를 mask 와 함께 푼다 (47번 규약 · 내 구현)."""
    h, l, c, d = p["h"], p["l"], p["c"], p["d"]
    o = p.get("o") or [None] * len(d)
    epx = p["entry_price"]
    n = len(c)
    lots = [(d[0], epx, shares[0], -1)]
    sched = []
    pend = list(enumerate(levels))

    def avg():
        s = sum(x[2] for x in lots)
        return sum(px * fr for _dt, px, fr, _k in lots) / s if s else epx

    def close(rd, res, ex, at_end):
        return {"lots": lots, "sched": sched, "exits": ex,
                "resolve_date": rd, "result": res, "at_end": at_end}

    for i in range(n):
        while pend and h[i] is not None and h[i] >= epx * (1 + pend[0][1] / 100.0):
            k, lv = pend.pop(0)
            lvl = epx * (1 + lv / 100.0)
            px = lvl if o[i] is None else max(lvl, o[i])
            sched.append((d[i], px, shares[k + 1], k))
            if mask[k]:
                lots.append((d[i], px, shares[k + 1], k))
        a = avg()
        S = a * (1 - stop / 100)
        if add_stop == "floor_entry" and len(lots) > 1:
            S = max(S, epx)
        T = a * (1 + target / 100)
        hit_t = h[i] is not None and h[i] >= T
        hit_s = l[i] is not None and l[i] <= S
        if i == 0:
            if hit_s:
                return close(d[0], "ambiguous", [(d[0], 1.0, c[0])], False)
            if hit_t:
                return _my_phase2(p, i, a, half, trail, close, T, o, n)
            continue
        if hit_t and hit_s:
            return close(d[i], "ambiguous", [(d[i], 1.0, c[i])], False)
        if hit_t:
            return _my_phase2(p, i, a, half, trail, close, T, o, n)
        if hit_s:
            px = S if o[i] is None else min(S, o[i])
            return close(d[i], "loss", [(d[i], 1.0, px)], False)
    return close(d[n - 1], "unresolved", [(d[n - 1], 1.0, c[n - 1])], True)


def build_masks(p, shares, levels):
    import itertools
    m = len(shares) - 1
    return {"code": p["code"], "scan_date": p["scan_date"], "pattern": p["pattern"],
            "entry_date": p["entry_date"], "entry_px": p["entry_price"],
            "stop_frac": 0.08, "shares": tuple(shares),
            "masks": {mk: my_levels(p, shares, levels, mk)
                      for mk in itertools.product((False, True), repeat=m)}}


def _sel(by2, sector, top, pctm):
    return by2


def stage3() -> int:
    import slot_sim_frac as sfr
    import slot_sim_lots as sl
    if r41.YEARS[0] != 2017:
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        return 2
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for dd in monthly.values() for y in dd if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pctm = r61b.make_flags(mret, sector)

    def keep_path(q):
        sn = sector.get(q["code"])
        if sn:
            tp = top.get(r61.prev_ym(q["scan_date"][:7], 1))
            if tp is not None and sn not in tp:
                return False
        v = pctm.get(r61.prev_ym(q["scan_date"][:7], 1), {}).get(q["code"])
        return (v is None) or (0.10 <= v < 0.30)

    by2 = {y: [q for q in ps if keep_path(q)] for y, ps in by.items()}
    print("=" * 92)
    print("74v 3 - 관문 (내 코드로 · slot_sim_lots a3fc4559)")
    print("=" * 92)

    def replay(adds, shares, levels):
        old, new = [], []
        for y in sorted(by2):
            ou = {}
            for q in by2[y]:
                cd = q["code"]
                if cd in ou and q["entry_date"] <= ou[cd]:
                    continue
                e = r47.resolve_pyr(q, "limit", "market", stop=8.0, target=20.0,
                                    adds=adds)
                ou[cd] = e.get("resolve_date") or q["entry_date"]
                e["stop_frac"] = 0.08
                old.append(e)
                new.append(build_masks(q, shares, levels))
        return old, new

    # 관문 1 — 트랜치 1개 == sim_frac(5칸 cash)
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev_ref, _b = r41.replay(by2, lambda q: r41.resolve_half_then_trail(q, 8.0, 20.0))
    one = []
    for y in sorted(by2):
        ou = {}
        for q in by2[y]:
            cd = q["code"]
            if cd in ou and q["entry_date"] <= ou[cd]:
                continue
            e = r47.resolve_pyr(q, "limit", "market", stop=8.0, target=20.0, adds=())
            ou[cd] = e.get("resolve_date") or q["entry_date"]
            one.append(build_masks(q, (1.0,), ()))
    with r41.Cost(*COST):
        w1 = [sl.sim_lots(one, risk=RISK, cap=CAP, seed=i, slots=5,
                          fill_rule="truncate", cash_rule="per_slot")
              for i in range(10)]
        w2 = [sfr.sim_frac(ev_ref, slots=5, seed=i, sizing="cash") for i in range(10)]
    worst = max(abs(a["equity_pct"] - b["equity_pct"]) / max(1e-12, abs(b["equity_pct"]))
                for a, b in zip(w1, w2))
    print("관문 1  트랜치 1개 == sim_frac(5칸·cash) — 최대 상대오차 %.3e -> **%s**"
          % (worst, "통과" if worst < 1e-9 else "미통과"), flush=True)
    print("        분해능 — seed 10판 자산이 서로 %s"
          % ("전부 다르다" if len({round(x["equity_pct"], 6) for x in w2}) == 10
             else "겹친다(관문이 무디다)"), flush=True)

    # 관문 2 — P1 두 단 새 == 옛
    o1, n1 = replay(((3.0, 0.5),), (0.5, 0.5), (3.0,))
    with r41.Cost(*COST):
        a1 = [sp.sim_pyr(o1, risk=RISK, cap=CAP, seed=i, pilot=0.5,
                         max_positions=5, cash_rule="per_slot") for i in range(10)]
        b1 = [sl.sim_lots(n1, risk=RISK, cap=CAP, seed=i, slots=5,
                          fill_rule="block", cash_rule="per_slot") for i in range(10)]
    w = max(abs(x["equity_pct"] - y["equity_pct"]) / max(1e-12, abs(y["equity_pct"]))
            for x, y in zip(a1, b1))
    print("관문 2  P1 두 단 새==옛 — 최대 상대오차 %.3e -> **%s**"
          % (w, "통과" if w < 1e-9 else "미통과"), flush=True)
    print("        진단 — 옛 %+.4f%% vs 새 %+.4f%% (seed 0) · 옛 증액 %d/막힘 %d · "
          "새 증액 %d/막힘 %d/잘림 %d"
          % (a1[0]["equity_pct"], b1[0]["equity_pct"], a1[0]["n_added"],
             a1[0]["n_add_blocked"], b1[0]["n_added"], b1[0]["n_add_blocked"],
             b1[0]["truncated"]), flush=True)

    # 관문 3' — P2 세 단 새 != 옛
    o2, n2 = replay(((3.0, 1 / 3), (6.0, 1 / 3)), (1 / 3, 1 / 3, 1 / 3), (3.0, 6.0))
    with r41.Cost(*COST):
        a2 = [sp.sim_pyr(o2, risk=RISK, cap=CAP, seed=i, pilot=1 / 3,
                         max_positions=5, cash_rule="per_slot") for i in range(10)]
        b2 = [sl.sim_lots(n2, risk=RISK, cap=CAP, seed=i, slots=5,
                          fill_rule="block", cash_rule="per_slot") for i in range(10)]
    dif = [y["equity_pct"] - x["equity_pct"] for x, y in zip(a2, b2)]
    print("관문 3'  P2 세 단 새 != 옛 — 다른 판 %d/10 · 차 중앙 %+.2f%%p "
          "(최소 %+.2f · 최대 %+.2f) -> **%s**"
          % (sum(1 for x in dif if abs(x) > 1e-9), st.median(dif), min(dif), max(dif),
             "통과" if all(abs(x) > 1e-9 for x in dif) else "미통과"), flush=True)
    print("        옛 자산중앙 %+.2f%% · 새 자산중앙 %+.2f%%"
          % (st.median(x["equity_pct"] for x in a2),
             st.median(x["equity_pct"] for x in b2)), flush=True)

    # 관문 3'' / 3''' — 크기·평균단가
    bad2 = tot2 = bad3 = tot3 = inv_ok = inv_bad = 0
    for t in n2:
        r = t["masks"][(True, True)]
        k = len(r["lots"]) - 1
        ssum = sum(x[2] for x in r["lots"])
        if k == 1:
            tot2 += 1
            if abs(ssum - 2 / 3) > 1e-12:
                bad2 += 1
        if k == 2:
            tot3 += 1
            if abs(ssum - 1.0) > 1e-12:
                bad3 += 1
            a = sum(px * fr for _d, px, fr, _k in r["lots"]) / ssum
            if r["result"] == "loss":
                if r["exits"][0][2] <= a * 0.92 + 1e-9:
                    inv_ok += 1
                else:
                    inv_bad += 1
    print("관문 3'' 증액 1회 Σ몫 == 2/3 — 대상 %d · 어긋남 **%d** -> **%s**"
          % (tot2, bad2, "통과" if bad2 == 0 else "미통과"), flush=True)
    print("관문 3''' 증액 2회 Σ몫 == 1.0 — 대상 %d · 어긋남 **%d** · "
          "손절가 역산 일치 %d / 어긋남 %d -> **%s**"
          % (tot3, bad3, inv_ok, inv_bad,
             "통과" if (bad3 == 0 and inv_bad == 0) else "미통과"), flush=True)

    # 관문 4 — 예약함 판 증액막힘 0
    with r41.Cost(*COST):
        rv = [sl.sim_lots(n2, risk=RISK, cap=CAP, seed=i, slots=5, reserve=True,
                          fill_rule="truncate", cash_rule="per_slot") for i in range(10)]
        nr = [sl.sim_lots(n2, risk=RISK, cap=CAP, seed=i, slots=5, reserve=False,
                          fill_rule="truncate", cash_rule="per_slot") for i in range(10)]
    print("관문 4  예약함 증액막힘 == 0 — 중앙 %d -> **%s**"
          % (st.median(x["n_add_blocked"] for x in rv),
             "통과" if all(x["n_add_blocked"] == 0 for x in rv) else "미통과"),
          flush=True)
    print("        🚨 이 관문은 **실패할 수 없다** — 예약 가지에서는 n_add_blocked 를"
          " 올리는 줄 자체가 없다(slot_sim_lots.py 증액 블록). 코드가 틀려도 0 이다.",
          flush=True)
    print("        대신 재는 것 — 예약함 증액 %d회 vs 예약 안 함 %d회(막힘 %d) · 더 샀는가: %s"
          % (st.median(x["n_added"] for x in rv), st.median(x["n_added"] for x in nr),
             st.median(x["n_add_blocked"] for x in nr),
             "예" if st.median(x["n_added"] for x in rv)
             > st.median(x["n_added"] for x in nr) else "아니오 — 예약이 안 듣는 것"),
          flush=True)

    # 관문 5 — 진입·체결·놀린 자본
    print("관문 5  진입 후보 %d건" % len(n2), flush=True)
    for lab, rs in (("예약함", rv), ("예약안함", nr)):
        print("        %-8s 체결 %3d · 증액 %3d · 잘림 %3d · 현금부족 %3d · "
              "묶인자본 평균 %.2f%%(최대 %.2f%%) · 안 쓴 예약 %d건 평균 %.1f%% · 자산 %+.2f%%"
              % (lab, st.median(x["n_filled"] for x in rs),
                 st.median(x["n_added"] for x in rs),
                 st.median(x["truncated"] for x in rs),
                 st.median(x["blocked_cash"] for x in rs),
                 st.median(x["resv_frac_mean"] for x in rs),
                 st.median(x["resv_frac_max"] for x in rs),
                 st.median(x["idle_end_n"] for x in rs),
                 st.median(x["idle_end_mean"] for x in rs),
                 st.median(x["equity_pct"] for x in rs)), flush=True)
    return 0




def stage3b() -> int:
    """관문 2 미통과의 «원인»을 가른다.

    가설 — 두 단에서도 새/옛이 갈리는 이유는 «가격»이 아니라
    «현금 부족으로 막힌 증액을 어떻게 처리하나»다.
      옛 `slot_sim_pyr` : 막혀도 청산선은 «샀다고 치고» 그대로 둔다
      새 `slot_sim_lots`: 안 산 조합으로 «다시 푼다»(reslot)
    검정 — 위험을 아주 작게 해 **막힘이 0 건**이 되게 만들면 둘이 같아야 한다.
    같아지면 원인이 확정되고, 안 같아지면 «다른» 원인이 하나 더 있는 것이다.
    """
    import slot_sim_lots as sl
    if r41.YEARS[0] != 2017:
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        return 2
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for dd in monthly.values() for y in dd if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pctm = r61b.make_flags(mret, sector)

    def keep_path(q):
        sn = sector.get(q["code"])
        if sn:
            tp = top.get(r61.prev_ym(q["scan_date"][:7], 1))
            if tp is not None and sn not in tp:
                return False
        v = pctm.get(r61.prev_ym(q["scan_date"][:7], 1), {}).get(q["code"])
        return (v is None) or (0.10 <= v < 0.30)

    by2 = {y: [q for q in ps if keep_path(q)] for y, ps in by.items()}
    old, new = [], []
    for y in sorted(by2):
        ou = {}
        for q in by2[y]:
            cd = q["code"]
            if cd in ou and q["entry_date"] <= ou[cd]:
                continue
            e = r47.resolve_pyr(q, "limit", "market", stop=8.0, target=20.0,
                                adds=((3.0, 0.5),))
            ou[cd] = e.get("resolve_date") or q["entry_date"]
            e["stop_frac"] = 0.08
            old.append(e)
            new.append(build_masks(q, (0.5, 0.5), (3.0,)))

    print("=" * 92)
    print("74v 3b - 관문 2 미통과의 원인 가르기 (P1 두 단 · 거래 %d)" % len(old))
    print("=" * 92)
    print("  %-22s %10s %12s %12s %8s %8s"
          % ("판", "옛 자산", "새 자산", "상대오차", "옛 막힘", "새 막힘"), flush=True)
    for lab, rk, cp, sc in (("헤드라인 5칸 20%", 0.02, 0.20, 5),
                            ("위험 1/10 (막힘 줄임)", 0.002, 0.02, 5),
                            ("위험 1/100 (막힘 0 목표)", 0.0002, 0.002, 5)):
        with r41.Cost(*COST):
            a = [sp.sim_pyr(old, risk=rk, cap=cp, seed=i, pilot=0.5,
                            max_positions=sc, cash_rule="per_slot") for i in range(10)]
            b = [sl.sim_lots(new, risk=rk, cap=cp, seed=i, slots=sc,
                             fill_rule="block", cash_rule="per_slot") for i in range(10)]
        w = max(abs(x["equity_pct"] - y["equity_pct"]) / max(1e-12, abs(y["equity_pct"]))
                for x, y in zip(a, b))
        print("  %-22s %+9.4f%% %+11.4f%% %11.3e %8d %8d   %s"
              % (lab, st.median(x["equity_pct"] for x in a),
                 st.median(y["equity_pct"] for y in b), w,
                 sum(x["n_add_blocked"] for x in a),
                 sum(y["n_add_blocked"] for y in b),
                 "일치" if w < 1e-9 else "다름"), flush=True)
    print("", flush=True)
    print("  → 막힘이 0 이 되는 판에서 상대오차가 1e-9 밑으로 내려가면"
          " 「원인은 막힌 증액 처리」가 확정된다.", flush=True)

    # 관문 3'' 의 짝 — 옛 도구가 정말 3/3 을 거는가 (두뇌 세션 요청)
    o2, n2 = [], []
    for y in sorted(by2):
        ou = {}
        for q in by2[y]:
            cd = q["code"]
            if cd in ou and q["entry_date"] <= ou[cd]:
                continue
            e = r47.resolve_pyr(q, "limit", "market", stop=8.0, target=20.0,
                                adds=((3.0, 1 / 3), (6.0, 1 / 3)))
            ou[cd] = e.get("resolve_date") or q["entry_date"]
            e["stop_frac"] = 0.08
            o2.append(e)
            n2.append(build_masks(q, (1 / 3, 1 / 3, 1 / 3), (3.0, 6.0)))
    k1 = k2 = 0
    old_full = 0
    for e, t in zip(o2, n2):
        r = t["masks"][(True, True)]
        k = len(r["lots"]) - 1
        if k == 1:
            k1 += 1
            # 옛 도구: 파일럿 1/3 + 첫 증액에서 남은 2/3 = 3/3
            if e["add"] is not None:
                old_full += 1
        elif k == 2:
            k2 += 1
    print("", flush=True)
    print("  관문 3'' 의 짝 — 증액 «한 번만» 난 거래 %d건에서" % k1, flush=True)
    print("      새 도구 Σ몫 = 2/3 (관문 3'' 이 %d번 돌았다)" % k1, flush=True)
    print("      옛 도구는 `w2 = target*(1-pilot)` 이라 **3/3** — `add` 가 실린 것 %d건"
          % old_full, flush=True)
    print("      증액 두 번 난 거래 %d건 (여기서 옛 도구는 취득가를 뭉갠다)" % k2, flush=True)
    return 0




def stage3c() -> int:
    """청산 축 — 마지막 남은 미검정 축을 «다시 짜지 않고» 닫는다.

    양쪽 구현이 둘 다 `47-round3-pyramid.py::_phase2` 에서 왔으므로
    «세 번째 구현»을 또 쓰면 그것도 같은 조상을 갖는다. 그래서 방식을 바꾼다 —
    **산출물이 청산 규칙의 «정의»를 만족하는지**를 검사한다(성질 검사).
    구현을 흉내 내지 않으므로 조상이 같아도 독립이다.

    검사하는 성질 (1a · 기준은 «그날까지 실제로 산» lots 의 평균단가)
      P1  청산 몫의 합 == 1.0
      P2  loss  : 청산가 == min(S_r, 시가) · S_r = max(a_r×0.92, 진입가)[floor_entry]
      P3  win   : 첫 청산가 == max(a_t×1.20, 시가) · 몫 0.5
      P4  ★ «첫» 교차인가 — 결착일 «이전» 어느 날도 목표·손절을 건드리지 않았다
          (a_i 를 그날까지의 lots 로 매일 다시 낸다)
      P5  ★ 추격 다리 — 청산가 == min(max(a, 직전 25일 저가 최솟값), 시가) 이고
          목표일 이후 «그보다 이른» 교차가 없다. 창은 [j−25, j) — 당일 제외(룩어헤드)
      P6  ambiguous 는 같은 날 목표·손절이 «둘 다» 걸린 날이다
    """
    import pyr_trigger as pt
    if r41.YEARS[0] != 2017:
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        return 2
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for dd in monthly.values() for y in dd if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pctm = r61b.make_flags(mret, sector)

    def keep_path(q):
        sn = sector.get(q["code"])
        if sn:
            tp = top.get(r61.prev_ym(q["scan_date"][:7], 1))
            if tp is not None and sn not in tp:
                return False
        v = pctm.get(r61.prev_ym(q["scan_date"][:7], 1), {}).get(q["code"])
        return (v is None) or (0.10 <= v < 0.30)

    paths = [q for y in sorted(by) for q in by[y] if keep_path(q)]
    shares = (0.5, 0.5)
    mask = (True,)
    T2 = 1e-9
    bad = {k: 0 for k in ("P1", "P2", "P3", "P4", "P5", "P6")}
    ran = {k: 0 for k in ("P1", "P2", "P3", "P4", "P5", "P6")}
    ex_show = []

    for q in paths:
        r = pt.resolve_all_masks(q, shares=shares)[mask]
        h, l, c, d = q["h"], q["l"], q["c"], q["d"]
        o = q.get("o") or [None] * len(d)
        epx = q["entry_price"]
        idx = {dt: i for i, dt in enumerate(d)}
        lots = r["lots"]
        ri = idx[r["resolve_date"]]

        # 그날까지의 lots 로 평균단가를 매일 다시 낸다
        def avg_at(i):
            sel = [(px, fr) for dt, px, fr, _k in lots if idx[dt] <= i]
            s = sum(f for _p, f in sel)
            return (sum(px * f for px, f in sel) / s) if s else epx

        ran["P1"] += 1
        if abs(sum(f for _dt, f, _px in r["exits"]) - 1.0) > T2:
            bad["P1"] += 1

        first_i = idx[r["exits"][0][0]]

        # P4 — 결착(또는 목표) 이전에 교차가 없었는가
        ran["P4"] += 1
        early = None
        for i in range(0, first_i):
            a = avg_at(i)
            S = a * 0.92
            if len(lots) > 1 and any(idx[dt] <= i for dt, _p, _f, k in lots if k >= 0):
                S = max(S, epx)
            T = a * 1.20
            if i == 0:
                if (l[0] is not None and l[0] <= S) or (h[0] is not None and h[0] >= T):
                    early = i
                    break
                continue
            if (h[i] is not None and h[i] >= T) or (l[i] is not None and l[i] <= S):
                early = i
                break
        if early is not None:
            bad["P4"] += 1
            if len(ex_show) < 4:
                ex_show.append(("P4", q["code"], q["scan_date"], early, first_i))

        if r["result"] == "loss":
            ran["P2"] += 1
            a = avg_at(ri)
            S = a * 0.92
            if any(k >= 0 for _dt, _p, _f, k in lots):
                S = max(S, epx)
            want = S if o[ri] is None else min(S, o[ri])
            if abs(r["exits"][0][2] - want) > T2 * max(1.0, want):
                bad["P2"] += 1
        elif r["result"] == "win":
            ran["P3"] += 1
            a = avg_at(first_i)
            Tg = a * 1.20
            want = Tg if o[first_i] is None else max(Tg, o[first_i])
            if abs(r["exits"][0][2] - want) > T2 * max(1.0, want) \
                    or abs(r["exits"][0][1] - 0.5) > T2:
                bad["P3"] += 1
            # P5 — 추격 다리
            if len(r["exits"]) > 1 and not r["at_end"]:
                ran["P5"] += 1
                jj = idx[r["exits"][1][0]]
                ok = True
                for j in range(first_i + 1, jj + 1):
                    seg = [x for x in l[max(0, j - 25):j] if x is not None]
                    s2 = max(a, min(seg)) if seg else a
                    hit = l[j] is not None and l[j] <= s2
                    if j < jj and hit:
                        ok = False
                        break
                    if j == jj:
                        if not hit:
                            ok = False
                            break
                        want2 = s2 if o[j] is None else min(s2, o[j])
                        if abs(r["exits"][1][2] - want2) > T2 * max(1.0, want2):
                            ok = False
                if not ok:
                    bad["P5"] += 1
                    if len(ex_show) < 8:
                        ex_show.append(("P5", q["code"], q["scan_date"], first_i, jj))
        elif r["result"] == "ambiguous":
            ran["P6"] += 1
            a = avg_at(ri)
            S = a * 0.92
            if any(k >= 0 for _dt, _p, _f, k in lots):
                S = max(S, epx)
            Tg = a * 1.20
            both = (l[ri] is not None and l[ri] <= S) and (h[ri] is not None and h[ri] >= Tg)
            if ri == 0:
                both = l[0] is not None and l[0] <= S
            if not both or abs(r["exits"][0][2] - c[ri]) > T2 * max(1.0, c[ri]):
                bad["P6"] += 1

    print("=" * 92)
    print("74v 3c - 청산 축 성질 검사 (경로 %d · H 1/2->1/2 · mask 전부 True)" % len(paths))
    print("=" * 92)
    NAMES = {"P1": "청산 몫 합 == 1.0",
             "P2": "loss 청산가 == min(손절선, 시가)",
             "P3": "win 첫 청산가 == max(목표선, 시가) · 몫 0.5",
             "P4": "★ 결착 이전에 «더 이른 교차»가 없다",
             "P5": "★ 추격 다리 = min(max(평단, 직전25일 최저), 시가) · 더 이른 교차 없음",
             "P6": "ambiguous 는 같은 날 둘 다 걸린 날"}
    for k in ("P1", "P2", "P3", "P4", "P5", "P6"):
        print("  %-3s %-52s 대상 %5d · 어긋남 **%d**%s"
              % (k, NAMES[k], ran[k], bad[k],
                 "" if ran[k] else "   <- 한 번도 안 돌았다(검사 아님)"), flush=True)
    for e in ex_show:
        print("     예: %s" % (e,), flush=True)
    print("", flush=True)
    print("  이 검사는 «구현을 흉내 내지 않는다» — 산출물이 규칙의 정의를 만족하는지만 본다.",
          flush=True)
    print("  분해능 확인 — 추격 창 25 -> 10 으로 바꾸면 P5 가 몇 건 어긋나는가:",
          flush=True)
    print("     (창을 [j-25, j] 로 «당일 포함» 바꾸는 변이는 쓸 수 없다 — 그 변이는"
          " 청산 «날짜»를 바꾸지 않는다. l[j] <= max(a, min) 이 두 창에서 동치임을"
          " 손으로 확인했다. 그래서 창 «길이»를 흔든다.)", flush=True)
    mis = tot = 0
    for q in paths[:2000]:
        r = pt.resolve_all_masks(q, shares=shares)[mask]
        if r["result"] != "win" or len(r["exits"]) < 2 or r["at_end"]:
            continue
        d = q["d"]
        l = q["l"]
        idx = {dt: i for i, dt in enumerate(d)}
        first_i = idx[r["exits"][0][0]]
        jj = idx[r["exits"][1][0]]
        lots = r["lots"]
        s = sum(f for _dt, _p, f, _k in lots)
        a = sum(px * f for _dt, px, f, _k in lots) / s
        tot += 1
        okj = True
        for j in range(first_i + 1, jj + 1):
            seg = [x for x in l[max(0, j - 10):j] if x is not None]
            s2 = max(a, min(seg)) if seg else a
            hit = l[j] is not None and l[j] <= s2
            if j < jj and hit:
                okj = False
                break
            if j == jj:
                if not hit:
                    okj = False
                else:
                    o3 = (q.get("o") or [None] * len(d))[j]
                    w3 = s2 if o3 is None else min(s2, o3)
                    if abs(r["exits"][1][2] - w3) > 1e-9 * max(1.0, w3):
                        okj = False
        if not okj:
            mis += 1
    print("     -> 대상 %d 중 %d 건 어긋난다 (0 이면 이 검사는 창을 못 본다)"
          % (tot, mis), flush=True)
    return 0




def stage2d() -> int:
    """H′ 대조 — 두뇌 세션 개정 3 의 `h_lag=True, stay_on="close"` 판.
    ②와 «같은 방식»: 먼저 분해능(일부러 틀리기), 그 다음 대조."""
    import pyr_trigger as pt
    if r41.YEARS[0] != 2017:
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        return 2
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for dd in monthly.values() for y in dd if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pctm = r61b.make_flags(mret, sector)

    def keep_path(q):
        sn = sector.get(q["code"])
        if sn:
            tp = top.get(r61.prev_ym(q["scan_date"][:7], 1))
            if tp is not None and sn not in tp:
                return False
        v = pctm.get(r61.prev_ym(q["scan_date"][:7], 1), {}).get(q["code"])
        return (v is None) or (0.10 <= v < 0.30)

    paths = [q for y in sorted(by) for q in by[y] if keep_path(q)]
    print("=" * 92)
    print("74v 2d - H' 대조 (h_lag=True · stay_on=close) · 경로 %d" % len(paths))
    print("=" * 92)
    KEY = dict(h_incl_today=False, dwell_on="close")
    MUT = (("(대조) H' 규약 그대로", {}),
           ("h_lag 를 도로 끈다", dict(h_incl_today=True)),
           ("stay_on 을 도로 저가로", dict(dwell_on="low")),
           ("머무는 날 2 -> 3", dict(dwell=3)),
           ("깊이 1.0 -> 1.5 ATR", dict(atr_mult=1.5)))
    for vlab, shares in (("H' 1/2->1/2", (0.5, 0.5)),
                         ("T' 1/3x3", (1 / 3, 1 / 3, 1 / 3))):
        mask = tuple([True] * (len(shares) - 1))
        theirs, n_any = [], 0
        for q in paths:
            r = pt.resolve_all_masks(q, shares=shares, h_lag=True,
                                     stay_on="close")[mask]
            b = [(x[0], round(x[1], 9), round(x[2], 9)) for x in r["sched"]]
            theirs.append(b)
            if b:
                n_any += 1
        print("")
        print("-- %s -- (방아쇠가 «난» 경로 %d / %d = %.1f%%)"
              % (vlab, n_any, len(paths), 100.0 * n_any / len(paths)), flush=True)
        for lab, kw in MUT:
            kk = dict(KEY)
            kk.update(kw)
            bad = 0
            for q, b in zip(paths, theirs):
                m = my_resolve(q, shares, **kk)
                if [(x[0], round(x[1], 9), round(x[2], 9)) for x in m["sched"]] != b:
                    bad += 1
            print("  %-26s 불일치 %5d (%5.2f%%)%s"
                  % (lab, bad, 100.0 * bad / len(paths),
                     "   <- 대조가 못 보는 축" if (bad == 0 and kw) else ""), flush=True)
    return 0




def _paths_now():
    by, miss = r41.v39.load_paths()
    if miss:
        raise SystemExit("uspath_%d.json 이 없다" % miss)
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for dd in monthly.values() for y in dd if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pctm = r61b.make_flags(mret, sector)

    def keep(q):
        sn = sector.get(q["code"])
        if sn:
            tp = top.get(r61.prev_ym(q["scan_date"][:7], 1))
            if tp is not None and sn not in tp:
                return False
        v = pctm.get(r61.prev_ym(q["scan_date"][:7], 1), {}).get(q["code"])
        return (v is None) or (0.10 <= v < 0.30)

    return {y: [q for q in ps if keep(q)] for y, ps in by.items()}


def _mk_trades(by2, shares, **kw):
    """pyr_trigger 로 masks 를 만들되 `open_until` 규약은 73/74 와 같게."""
    import pyr_trigger as pt
    out = []
    for y in sorted(by2):
        ou = {}
        for q in by2[y]:
            cd = q["code"]
            if cd in ou and q["entry_date"] <= ou[cd]:
                continue
            got = pt.resolve_all_masks(q, shares=shares, **kw)
            full = tuple([True] * (len(shares) - 1))
            r0 = got[full]
            ou[cd] = r0["resolve_date"] or q["entry_date"]
            out.append({"code": q["code"], "scan_date": q["scan_date"],
                        "pattern": q["pattern"], "entry_date": q["entry_date"],
                        "entry_px": q["entry_price"], "stop_frac": 0.08,
                        "shares": tuple(shares),
                        "masks": {m: {"lots": r["lots"], "sched": r["sched"],
                                      "exits": r["exits"],
                                      "resolve_date": r["resolve_date"],
                                      "result": r["result"]}
                                  for m, r in got.items()}})
    return out


def stage5() -> int:
    """④′ (fill_log 로 «밖에서») + 「12판과 200판이 왜 다른가」."""
    import slot_sim_lots as sl
    if r41.YEARS[0] != 2017:
        return 2
    by2 = _paths_now()
    H2 = dict(add_stop="floor_entry")
    HP = dict(add_stop="floor_entry", h_lag=True, stay_on="close")
    HPA = dict(add_stop="avg", h_lag=True, stay_on="close")
    print("=" * 92)
    print("74v 5 - 관문 4' (fill_log) + 12판 vs 200판")
    print("=" * 92)

    tv = {"P0": _mk_trades(by2, (1.0,)),
          "H": _mk_trades(by2, (0.5, 0.5), **H2),
          "H'": _mk_trades(by2, (0.5, 0.5), **HP),
          "H'-avgstop": _mk_trades(by2, (0.5, 0.5), **HPA)}
    for k, v in tv.items():
        print("  %-12s 진입 후보 %d" % (k, len(v)), flush=True)

    # ── 관문 ④′ — 예약함 판에서 «방아쇠 난 트랜치» == «실제로 산 트랜치» ──
    print("", flush=True)
    print("-- 관문 4' — 예약함 판: 방아쇠 난 트랜치 == 실제로 산 트랜치 --", flush=True)
    for lab in ("H", "H'"):
        tot_add = tot_blocked = tot_short = 0
        n_runs = 10
        with r41.Cost(*COST):
            for s in range(n_runs):
                r = sl.sim_lots(tv[lab], risk=RISK, cap=CAP, seed=s, slots=5,
                                reserve=True, fill_rule="truncate",
                                cash_rule="per_slot")
                for key, kind, k, d, px, wgt, target in r["fill_log"]:
                    if kind == "blocked":
                        tot_blocked += 1
                    elif kind == "add":
                        tot_add += 1
                        want = target * tv[lab][0]["shares"][k + 1]
                        if wgt < want - 1e-12:
                            tot_short += 1
        print("  %-12s 10판 합 — 증액 %d회 · blocked %d회 · **몫이 모자란 증액 %d회** -> %s"
              % (lab, tot_add, tot_blocked, tot_short,
                 "통과" if (tot_blocked == 0 and tot_short == 0) else "미통과"),
              flush=True)
    # 분해능 — 예약을 «끄면» 이 관문이 깨지는가
    with r41.Cost(*COST):
        rr = sl.sim_lots(tv["H"], risk=RISK, cap=CAP, seed=0, slots=5,
                         reserve=False, fill_rule="truncate", cash_rule="per_slot")
    nb = sum(1 for x in rr["fill_log"] if x[1] == "blocked")
    print("  분해능 — 예약을 끄면 blocked 가 %d회 찍힌다 (0 이면 관문 4' 도 무디다)"
          % nb, flush=True)

    # ── 12판 vs 200판 ────────────────────────────────────────────────────
    print("", flush=True)
    print("-- 12판과 200판이 왜 다른가 (같은 200판 벡터에서 앞 12판을 떼어 본다) --",
          flush=True)
    N = 200
    eqs = {}
    for lab in ("P0", "H'-avgstop", "H", "H'"):
        rsv = (lab != "P0")
        with r41.Cost(*COST):
            eqs[lab] = [sl.sim_lots(tv[lab], risk=RISK, cap=CAP, seed=s, slots=5,
                                    reserve=rsv, fill_rule="truncate",
                                    cash_rule="per_slot")["equity_pct"]
                        for s in range(N)]
        v = sorted(eqs[lab])
        print("  %-12s 200판 중앙 %+9.2f%% · P5 %+9.2f%% · P95 %+9.2f%% · "
              "앞12판 중앙 %+9.2f%%"
              % (lab, st.median(eqs[lab]), v[int(N * .05)], v[int(N * .95)],
                 st.median(eqs[lab][:12])), flush=True)

    a, b = eqs["H'-avgstop"], eqs["P0"]
    d200 = st.median(a) - st.median(b)
    d12 = st.median(a[:12]) - st.median(b[:12])
    print("", flush=True)
    print("  H'-avgstop − P0 :  앞12판 %+.2f%%p   vs   200판 %+.2f%%p"
          % (d12, d200), flush=True)
    # 12판을 «무작위로» 골랐다면 얼마나 자주 이겼을까 — 순수한 뽑기 잡음
    import random as _rnd
    rg = _rnd.Random(410824)
    idx = list(range(N))
    wins, draws = 0, 4000
    diffs = []
    for _ in range(draws):
        pick = rg.sample(idx, 12)
        dd = st.median([a[i] for i in pick]) - st.median([b[i] for i in pick])
        diffs.append(dd)
        wins += dd > 0
    diffs.sort()
    print("  🔎 같은 200판에서 12판을 무작위로 뽑으면 — 이기는 비율 **%.1f%%** · "
          "차 중앙 %+.2f%%p · 2.5%% %+.2f · 97.5%% %+.2f"
          % (100.0 * wins / draws, diffs[draws // 2], diffs[int(draws * .025)],
             diffs[int(draws * .975)]), flush=True)
    print("  -> 12판 표는 «다른 결론»이 아니라 «같은 분포에서 뽑은 한 번»이다.", flush=True)

    # 짝비교(같은 seed) — 뽑기 잡음을 없애면 무엇이 남나
    pair = [x - y for x, y in zip(a, b)]
    pair.sort()
    print("", flush=True)
    print("  같은 seed 짝비교 H'-avgstop − P0 : 중앙 %+.2f%%p · 음수 %d/%d판 · "
          "P5 %+.2f · P95 %+.2f"
          % (st.median(pair), sum(1 for x in pair if x < 0), N,
             pair[int(N * .05)], pair[int(N * .95)]), flush=True)
    return 0




def stage6() -> int:
    """🚨 「짝 안 지음 B」와 「짝 지음 A」가 왜 갈리나 — **내 자료로** 가른다.

    두뇌 세션 77번에서 두 통계가 크게 어긋났다. 원인 후보가 셋인데
    **내가 이미 가진 200판 벡터로 전부 가를 수 있다**(77번 코드 불필요):

      ① 단위      — %p(수준 차) vs %(상대 성과). 애초에 다른 자
      ② 중앙의 중앙 — median(A) − median(B) ≠ median(A − B)
      ③ 스트림 10 — `dataaxis` 는 **앞 10 seed** 만 쓴다(N_STREAM). 200판과 다를 수 있다

    셋을 같은 표에 놓으면 어느 것이 범인인지 «보인다».
    """
    import dataaxis as da
    import slot_sim_lots as sl
    if r41.YEARS[0] != 2017:
        return 2
    by2 = _paths_now()
    HPA = dict(add_stop="avg", h_lag=True, stay_on="close")
    tv = {"P0": _mk_trades(by2, (1.0,)),
          "H'-avgstop": _mk_trades(by2, (0.5, 0.5), **HPA)}
    N = 200
    runs = {}
    for lab, trades in tv.items():
        rsv = (lab != "P0")
        with r41.Cost(*COST):
            runs[lab] = [sl.sim_lots(trades, risk=RISK, cap=CAP, seed=s, slots=5,
                                     reserve=rsv, fill_rule="truncate",
                                     cash_rule="per_slot")
                         for s in range(N)]
    A = [r["equity_pct"] for r in runs["H'-avgstop"]]
    B = [r["equity_pct"] for r in runs["P0"]]

    def rel(a, b):
        return ((1 + a / 100.0) / (1 + b / 100.0) - 1) * 100.0

    d_all = [rel(a, b) for a, b in zip(A, B)]
    mA, mB = st.median(A), st.median(B)
    print("=" * 92)
    print("74v 6 - 「짝 안 지음」 vs 「짝 지음」이 갈리는 이유 (P0 vs H'-avgstop · 200판)")
    print("=" * 92)
    print("  자산 중앙   H'-avgstop %+9.2f%%   P0 %+9.2f%%" % (mA, mB), flush=True)
    print()
    print("  %-46s %12s" % ("통계", "값"))
    print("  %-46s %+11.2f%%p" % ("B  중앙끼리 «수준» 차 (%p)", mA - mB))
    print("  %-46s %+11.2f%%" % ("B′ 같은 것을 «상대»로 환산", rel(mA, mB)))
    print("  %-46s %+11.2f%%" % ("A₂₀₀ 짝지은 상대차의 중앙 (200판)", st.median(d_all)))
    print("  %-46s %+11.2f%%" % ("A₁₀  짝지은 상대차의 중앙 (앞 10판)",
                                 st.median(d_all[:10])))
    for b in (20, 40, 80):
        r = da.band_paired([x["curve"] for x in runs["H'-avgstop"]],
                           [x["curve"] for x in runs["P0"]], b)
        print("  %-46s %+11.2f%%   95%% [%+.2f, %+.2f]"
              % ("A  band_paired 중앙 (블록 %d · 스트림 10)" % b,
                 r["median"], r["lo"], r["hi"]))
    print()
    print("  짝지은 상대차가 양수인 판 %d/%d · P5 %+.2f%% · P95 %+.2f%%"
          % (sum(1 for x in d_all if x > 0), N,
             sorted(d_all)[int(N * .05)], sorted(d_all)[int(N * .95)]), flush=True)
    # 중앙을 낸 seed 가 같은가 — ②의 직접 증거
    iA = sorted(range(N), key=lambda i: A[i])[N // 2]
    iB = sorted(range(N), key=lambda i: B[i])[N // 2]
    print("  중앙을 낸 seed — H'-avgstop %d · P0 %d  → %s"
          % (iA, iB, "같다" if iA == iB else "**다르다(②가 성립할 조건)**"), flush=True)
    print()
    print("  ★ 읽는 법: B′ 와 A₂₀₀ 이 크게 갈리면 ②(중앙의 중앙)가 범인이고,")
    print("             A₂₀₀ 와 A₁₀ 이 갈리면 ③(스트림 10)이 범인이다.")
    print("             B 와 B′ 의 차이는 ①(단위)일 뿐이다.")
    return 0


if __name__ == "__main__":
    if "--stage6" in sys.argv:
        raise SystemExit(stage6())
    if "--stage5" in sys.argv:
        raise SystemExit(stage5())
    if "--stage2d" in sys.argv:
        raise SystemExit(stage2d())
    if "--stage3c" in sys.argv:
        raise SystemExit(stage3c())
    if "--stage3b" in sys.argv:
        raise SystemExit(stage3b())
    if "--stage3" in sys.argv:
        raise SystemExit(stage3())
    if "--stage2c" in sys.argv:
        raise SystemExit(stage2c())
    if "--stage2b" in sys.argv:
        raise SystemExit(stage2b())
    raise SystemExit(stage2() if "--stage2" in sys.argv else main())

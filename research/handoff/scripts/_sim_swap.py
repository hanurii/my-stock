# -*- coding: utf-8 -*-
"""점진적 노출 시뮬레이터 **v2** — 사양: `tasks/74-pyramid-rebuilt.md`

`slot_sim_pyr.py` 를 «고치지 않고» 옆에 세운다 — 47·73 이 그대로 돌아가야
「고쳤다」를 증명할 대조군이 남는다.

옛 도구에서 고친 것 셋
----------------------
① **트랜치가 몇 개든 제대로 센다.**
   옛 도구는 `add = (증액일, 증액가)` 한 쌍만 받아, 세 단 이상이면
   «1/3 @ 1.000 + 2/3 @ 1.030» 으로 뭉갰다(실제는 1/3씩 세 번).
   → 평균단가가 1.0200 vs 1.0300 으로 어긋나 **이겨도 지어도 유리한 쪽으로** 계산됐다.

② **현금이 없어 못 산 트랜치를 «없던 것»으로 다시 푼다.**
   옛 도구는 증액이 막혀도 청산선을 「샀다고 치고」 그대로 뒀다.
   여기서는 `masks` 로 미리 풀어 둔 결과에서 **실제로 산 조합**을 찾아 갈아 끼운다.
   🚨 조합 수는 증액 트랜치가 m 개면 2**m 뿐이다(두 단이면 2, 세 단이면 4).
      그래서 «미리 전부» 풀어 두면 순환이 사라진다.

③ **파일럿이 자리를 예약할 수 있다** (`reserve=True`).
   47번 실측: 증액 시도 267건 중 183건(68.5%)이 현금 부족으로 막혔고
   동시 보유가 7 → 12 로 늘었다(미너비니 4~8종목 밖). 파일럿이 목표의 반만
   잡으니 **남은 돈이 다른 종목을 사러 갔기** 때문이다.
   예약하면 그 돈은 이 종목 몫으로 묶인다 — **놀린 자본을 반드시 보고한다.**

거래 dict 에 필요한 키
----------------------
`code` · `scan_date` · `pattern` · `entry_date` · `entry_px` · `stop_frac` ·
`shares` = (트랜치별 «목표 대비» 몫, 합 1.0) ·
`masks` = {mask: resolved} — mask 는 **증액** 트랜치를 실제로 샀는지의 tuple
          (길이 = len(shares) − 1 · 파일럿은 항상 산다)
  resolved = {"lots":  [(날짜, 체결가, 몫, k), ...]   실제로 «산» 것
              "sched": [(날짜, 체결가, 몫, k), ...]   방아쇠가 «난» 것 전부 (mask 무관)
              "exits": [(날짜, 포지션전체대비몫, 가격), ...]
              "resolve_date" · "result"}

🚨 **양방향 관문**: 트랜치가 하나면(`shares=(1.0,)`, mask 키 `()` 하나)
   `slot_sim_frac.sim_frac(slots=5, sizing="cash")` 와 «같아야» 한다.
"""
from __future__ import annotations

import random as _rnd
import statistics as st
from collections import defaultdict

import slot_sim
from slot_sim import net, order_key      # noqa: F401


def _res(t, mask):
    return t["masks"][tuple(mask)]


def sim_swap(trades, risk=0.02, cap=0.20, seed=0, slots=5,
             reserve=False, fill_rule="truncate", cash_rule="per_slot",
             use_cash=True, pick=None, order_fn=None, size_fn=None, recent_n=5,
             ev_fn=None, swap="off", pathmap=None, swap_seed=0):
    """🚨 `slot_sim_lots.sim_lots` 의 **사본** + 「갈아타기」 하나.  (177 전용)

    swap = "off"  → **원본과 «완전히» 같아야 한다**(MA★ 이 그것을 «확인»한다)
           "low"  → 자리가 «찼을» 때 새 후보가 오면 **「보유 중 «수익률 제일 낮은» 것」**을 «판다»
           "rand" → 같은 «횟수»만큼 **«무작위» 보유분**을 «판다»(플라세보)

    🚨 「수익률」은 **«전날 종가»**로 잰다 — «오늘 시가»에 파는 «결정»을 «오늘 값»으로 하면
       «룩어헤드»다. 판 값은 «오늘 시가»(새 후보를 사는 그 값).
    🚨 «오늘» 산 것은 «오늘» 안 판다.
    """
    # `size_fn(recent, seed, t) -> 배수` 를 주면 **거래 크기**를 직전 청산 결과로 정한다(원전 사다리).
    #   원전: 「1/4 포지션으로 시작, 성공 거래의 연속선상에서 «두 배씩» 늘린다.
    #          손실 나는 종목은 매도해서 비중을 줄인다」 (99 사전등록 §1-1)
    #   `recent` = 직전 청산 «최대 recent_n 건»의 승패(True=win) — 아래 `pick` 과 같은 것.
    #   🚨 `recent_n=5` 는 `pick`(78) 의 원문 「last 4 or 5」에 맞춘 «기존» 값이다.
    #      **사다리는 5건으로 «상태»를 복원 못 한다** — 반례 `W L W L W` 가 시작점에 따라
    #      lvl 1 / lvl 2 로 갈린다. 항상 0 에서 시작하므로 **«참 상태 이하»로만 나온다**.
    #      → 사다리를 쓸 때는 `recent_n` 을 크게(20+) 준다. 걸음이 [0,2] 에 갇혀 시작점을 잊는다.
    # 🚨 None 이면 배수 1.0 — **옛 동작이 «완전히» 보존된다**(order_fn 과 같은 방식).
    # `order_fn(seed, t) -> 정렬키` 를 주면 같은 날 후보를 «규칙으로» 고른다.
    # 🚨 None 이면 기존 `order_key`(거래별 난수) 그대로 — 옛 동작이 «완전히» 보존된다.
    #    86번 관문 ①이 그것을 < 1e-12 로 확인한다.
    """자산곡선. 크기 = min(자산×위험÷손절폭, 자산×상한).

    reserve   : True 면 진입 때 **목표 금액 전체**를 현금에서 뺀다(안 쓴 몫은 결착 때 복귀).
    fill_rule : "truncate" = 살 수 있는 만큼만 산다 (`slot_sim_frac(sizing="cash")` 규약)
                "block"    = 모자라면 아예 안 산다 (옛 `slot_sim_pyr` 규약)
    cash_rule : "per_slot" = 빈 칸 수로 현금을 나눠 상한을 건다 (`sim_frac` 과 같다)
                "seq"      = 남은 현금 전부를 쓸 수 있다
    """
    if fill_rule not in ("truncate", "block"):
        raise ValueError("fill_rule")
    if cash_rule not in ("per_slot", "seq"):
        raise ValueError("cash_rule")

    byday = defaultdict(list)
    for t in trades:
        byday[t["entry_date"]].append(t)
    for k in byday:
        byday[k].sort(key=lambda x: (x["code"], x.get("pattern", ""),
                                     x.get("scan_date", "")))

    # ── 날짜 축은 «모든 조합»에서 모은다 ────────────────────────────────────
    #    조합에 따라 결착일·증액일이 달라지므로, 하나만 보면 날짜를 빠뜨린다.
    dset = set(byday)
    for t in trades:
        for r in t["masks"].values():
            dset.add(r["resolve_date"])
            for e in r["exits"]:
                dset.add(e[0])
            for s in r["sched"]:
                dset.add(s[0])
    dates = sorted(x for x in dset if x)

    eq = 1.0
    held = {}                 # id(t) -> 보유 상태
    n = w = mw = 0
    peak, mdd = 1.0, 0.0
    streak = best = 0
    curve, conc = [], []
    cash_floor = 1e9
    nomw, arith, fills = {}, [0.0], []
    n_blocked_cash = n_add_blocked = n_added = n_trunc = 0
    resv_frac = []            # 날짜별 «묶여서 놀고 있는» 비중
    expo_frac = []            # 날짜별 «주식에 들어가 있는» 비중 (노출)
    # ★ 조건부 분할매수 (78번 A) — 진입 «그때» 전액/파일럿을 고른다.
    #   `pick(recent) -> True` 면 `t["alt"]`(대개 한 트랜치 전액)를 쓴다.
    #   `recent` = 직전 청산 «최대 5건»의 승패(True=win). 원문 「last 4 or 5 stocks」.
    #   🚨 자료가 5건 안 쌓였으면 판단 근거가 없다 — 호출자가 그때 무엇을 반환할지 정한다.
    recent = []
    _srg = _rnd.Random(1000 * seed + swap_seed + 31)
    n_swap = 0
    swap_ret = []            # 「내보낸 것」의 «그 시점» 수익률(%) — 사전등록 ④
    swap_log = []            # (판 날, (scan_date, code, pattern), path 날 번호, 수익률%)
    n_alt = n_base = 0
    idle_end = []             # 결착 때 끝내 안 쓴 예약금 (목표 대비 몫)
    # 🚨 «어느 거래가 자본을 얼마나 받았나» — 밖에서 감사할 수 있어야 한다.
    #    (2026-08-25 되살림: 관문 ④ 가 «실패할 수 없는» 관문이라 검증 세션이
    #     밖에서 ④′「방아쇠 난 트랜치 수 == 실제로 산 트랜치 수」를 걸 수 있게.)
    #    항목: (키, 종류, 트랜치번호 k, 날짜, 체결가, 실제비중, 목표크기)
    #    종류: "pilot" | "add" | "blocked"(방아쇠는 났으나 현금이 없어 못 삼)
    fill_log = []
    exit_log = []          # 🚨 121b 용 — (청산일, 계좌 기준 실현손익 배수). 기존 동작 불변
    ret_log = []          # [125] (청산일, **그 자리의 수익률 %**, 계좌 대비 크기). 기존 동작 불변

    def credit(items):
        nonlocal eq
        # 🚨 정렬 키에 «거래 dict» 가 들어가면 비교 불가로 터진다 — code 로 정렬한다
        for _d, _code, _t, tw, fr, px in sorted(items, key=lambda x: (x[0], x[1])):
            tot = sum(x[1] for x in tw)
            for epx_i, w_i in tw:
                g = round(px / epx_i * 100 - 100, 2)
                eq += w_i * fr * net(g) / 100
                arith[0] += nomw.get(id(_t), 0.0) * (w_i / max(1e-12, tot)) \
                    * fr * net(g) / 100

    def close_out(h):
        nonlocal n, w, mw, streak, best
        t, tw = h["t"], h["w"]
        n += 1
        tot = sum(x[1] for x in tw)
        r = sum(fr * net(round(px / epx_i * 100 - 100, 2)) * (w_i / max(1e-12, tot))
                for _d, fr, px in h["all_exits"] for epx_i, w_i in tw)
        fills.append(r)
        is_w = h["result"] == "win"
        recent.append(bool(is_w))
        del recent[:-recent_n]
        w += is_w
        mw += r > 0
        streak = 0 if is_w else streak + 1
        best = max(best, streak)
        # 🚨 세금을 «정확히» 재려면 «언제 얼마를 실현했나»가 필요하다.
        #    r 은 «그 자리»의 수익률(%)이고, 실제로 계좌에 든 돈은 tot 이다.
        #    → 계좌 기준 실현손익 = tot × r/100.  청산일은 마지막 exit 날짜.
        _last = max((e[0] for e in h["all_exits"]), default=h["t"]["entry_date"])
        exit_log.append((_last, tot * r / 100.0))
        ret_log.append((_last, r, tot))
        if h["resv"] > 1e-12:
            idle_end.append(h["resv"] / max(1e-12, h["target"]))

    def reslot(h, d):
        """실제로 산 조합으로 «다시 푼다» — 그날 «이후»의 청산선만 갈아 끼운다."""
        r = _res(h["spec"], h["mask"])
        h["exits"] = [e for e in r["exits"] if e[0] >= d]
        h["sched"] = [s for s in r["sched"] if s[0] >= d and s[3] > h["k"]]
        h["resolve_date"] = r["resolve_date"]
        h["result"] = r["result"]
        h["all_exits"] = list(r["exits"])

    for d in dates:
        # ── 오늘 «이전»에 난 청산을 반영 ─────────────────────────────────
        due, done = [], []
        for key, h in list(held.items()):
            rest = []
            for ex in h["exits"]:
                if ex[0] < d:
                    due.append((ex[0], h["t"]["code"], h["t"], h["w"], ex[1], ex[2]))
                else:
                    rest.append(ex)
            h["exits"] = rest
            if h["resolve_date"] < d:
                done.append(key)
        credit(due)
        for key in sorted(done, key=lambda k: (held[k]["resolve_date"],
                                               held[k]["t"]["code"])):
            close_out(held[key])
            del held[key]

        # ── 가용 현금 ────────────────────────────────────────────────────
        #    🚨 예약금은 «묶여 있다» — 자산에는 있지만 다른 종목이 쓸 수 없다.
        open_w = sum(w_i * sum(fr for _d2, fr, _p in h["exits"])
                     for h in held.values() for _e, w_i in h["w"])
        resv_tot = sum(h["resv"] for h in held.values())
        cash = eq - open_w - resv_tot
        cash_floor = min(cash_floor, cash)
        resv_frac.append(resv_tot / eq if eq > 0 else 0.0)
        # 🚨 «실제로 주식에 들어가 있는» 비중 — 노출을 맞춘 대조에 필요하다.
        #    이게 없으면 「낙폭이 얕다」와 「그냥 덜 샀다」를 못 가른다.
        expo_frac.append(open_w / eq if eq > 0 else 0.0)

        # ── 증액 ─────────────────────────────────────────────────────────
        for h in sorted(held.values(), key=lambda x: x["t"]["code"]):
            while h["sched"] and h["sched"][0][0] == d:
                _ad, apx, ashare, k = h["sched"][0]
                h["k"] = k
                need = h["target"] * ashare
                if reserve:
                    # 예약분에서 낸다 — «현금 부족으로» 막힐 수 없다
                    take = min(need, h["resv"])
                    h["resv"] -= take
                    h["w"].append((apx, take))
                    n_added += 1
                    fill_log.append((h["key"], "add", k, d, apx, take, h["target"]))
                    h["sched"].pop(0)
                elif need > cash + 1e-12:
                    h["mask"][k] = False
                    n_add_blocked += 1
                    fill_log.append((h["key"], "blocked", k, d, apx, 0.0, h["target"]))
                    reslot(h, d)             # ← 안 산 것으로 «다시 푼다»
                else:
                    cash -= need
                    h["w"].append((apx, need))
                    n_added += 1
                    fill_log.append((h["key"], "add", k, d, apx, need, h["target"]))
                    h["sched"].pop(0)

        # ── 🆕 갈아타기 ──────────────────────────────────────────────────
        def _unreal(h, dd):
            """«전날 종가» 기준 미실현 수익률(%). 못 재면 None."""
            p = (pathmap or {}).get(id(h["t"]))
            if not p:
                return None
            try:
                j = p["d"].index(dd)
            except ValueError:
                return None
            if j < 1 or p["c"][j - 1] is None:
                return None
            return p["c"][j - 1] / h["t"]["entry_px"] * 100.0 - 100.0

        def _px_today(h, dd):
            p = (pathmap or {}).get(id(h["t"]))
            if not p:
                return None
            try:
                j = p["d"].index(dd)
            except ValueError:
                return None
            return p["o"][j]

        def _try_swap(dd):
            nonlocal n_swap, cash
            cand = []
            for k2, h2 in held.items():
                if h2["t"]["entry_date"] == dd:      # 🚨 «오늘» 산 것은 «오늘» 안 판다
                    continue
                u = _unreal(h2, dd)
                px2 = _px_today(h2, dd)
                if u is None or px2 is None:
                    continue
                if sum(fr for _d3, fr, _p3 in h2["exits"]) <= 1e-12:
                    continue
                cand.append((u, h2["t"]["code"], k2, px2,
                             (pathmap or {})[id(h2["t"])]["d"].index(dd)))
            if not cand:
                return False
            if swap == "rand":
                pickk = cand[_srg.randrange(len(cand))]
            else:
                pickk = min(cand, key=lambda x: (x[0], x[1]))
            u, _cd, k2, px2, _j = pickk
            h2 = held[k2]
            rem = sum(fr for _d3, fr, _p3 in h2["exits"])
            credit([(dd, h2["t"]["code"], h2["t"], h2["w"], rem, px2)])
            h2["all_exits"] = [e for e in h2["all_exits"] if e[0] < dd] + [(dd, rem, px2)]
            h2["exits"] = []
            h2["resolve_date"] = dd
            _r = sum(fr * (px3 / h2["t"]["entry_px"] * 100.0 - 100.0)
                     for _d3, fr, px3 in h2["all_exits"])
            h2["result"] = "win" if _r > 0 else "loss"
            close_out(h2)
            del held[k2]
            n_swap += 1
            swap_ret.append(u)
            swap_log.append((dd, h2["key"], _j, u))
            return True

        # ── 새 진입 (파일럿) ─────────────────────────────────────────────
        if d in byday:
            free = slots - len(held)
            share_cap = (max(0.0, cash) / free) if (cash_rule == "per_slot"
                                                    and free > 0) else None
            _ok = order_fn if order_fn is not None else order_key
            # 🚨 146 — «못 산 사건»을 적는 훅. ev_fn 이 None 이면 옛 동작 «그대로»
            _cands = sorted(byday[d], key=lambda x: _ok(seed, x))
            for _ci, t in enumerate(_cands):
                if len(held) >= slots:
                    if swap == "off" or not _try_swap(d):
                        if ev_fn is not None:
                            # ㉠ — 자리가 차서 «남은 후보 전부»가 «닿지도» 못한다
                            ev_fn("A", d, _cands[_ci:], free, held)
                        break
                    # ── 갈아탔다 — 현금·상한을 «다시» 센다 ────────────────
                    open_w = sum(w_i * sum(fr for _d2, fr, _p in hh["exits"])
                                 for hh in held.values() for _e, w_i in hh["w"])
                    resv_tot = sum(hh["resv"] for hh in held.values())
                    cash = eq - open_w - resv_tot
                    free = slots - len(held)
                    share_cap = (max(0.0, cash) / free) if (cash_rule == "per_slot"
                                                            and free > 0) else None
                sf_ = t.get("stop_frac") or 0.10
                lim = min(eq * risk / sf_, eq * cap)
                # ★ 원전 사다리 — 직전 청산 결과가 «이번 거래의 크기»를 정한다
                if size_fn is not None:
                    lim *= size_fn(recent, seed, t)
                # 🚨 예약하면 «목표 전체»가 나가고, 아니면 파일럿만 나간다
                # ★ 조건부: 이 거래를 «전액»으로 갈지 «파일럿»으로 갈지 지금 고른다
                spec = t
                if pick is not None and t.get("alt") is not None and pick(recent):
                    spec = t["alt"]
                    n_alt += 1
                else:
                    n_base += 1
                sh0 = spec["shares"][0]
                need = lim if reserve else lim * sh0
                avail = cash if not use_cash else (
                    cash if share_cap is None else min(cash, share_cap))
                _tr = False
                if use_cash and need > avail + 1e-12:
                    if fill_rule == "block":
                        n_blocked_cash += 1
                        if ev_fn is not None:
                            ev_fn("B", d, [t], free, held)
                        continue
                    need = avail                     # 살 수 있는 만큼만
                    n_trunc += 1
                    _tr = True
                if need <= 1e-12:
                    n_blocked_cash += 1
                    if ev_fn is not None:
                        ev_fn("B", d, [t], free, held)   # ㉡ — 현금이 사실상 0
                    continue
                if ev_fn is not None:
                    # ㉢ = 잘려서 «조금 샀다»(매수다) · BUY = 온전히 샀다
                    ev_fn("C" if _tr else "BUY", d, [t], free, held)
                target = need if reserve else need / sh0
                nomw[id(t)] = target / eq if eq > 0 else 0.0
                mask = [True] * (len(spec["shares"]) - 1)
                r0 = _res(spec, mask)
                key = (t["scan_date"], t["code"], t.get("pattern", ""))
                fill_log.append((key, "pilot", -1, d, t["entry_px"],
                                 target * sh0, target))
                h = {"t": t, "spec": spec, "mask": mask, "k": -1,
                     "target": target, "key": key,
                     "w": [(t["entry_px"], target * sh0)],
                     "resv": (target * (1.0 - sh0)) if reserve else 0.0,
                     "exits": list(r0["exits"]), "all_exits": list(r0["exits"]),
                     "sched": list(r0["sched"]),
                     "resolve_date": r0["resolve_date"], "result": r0["result"]}
                held[id(t)] = h
                cash -= (target if reserve else target * sh0)
        if ev_fn is not None:
            ev_fn("DAY", d, [], slots - len(held), held)   # 자리-일 회계
        conc.append(len(held))
        curve.append((d, eq))
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)

    # ── 남은 보유 정산 ────────────────────────────────────────────────────
    rest = [(ex[0], h["t"]["code"], h["t"], h["w"], ex[1], ex[2])
            for h in held.values() for ex in h["exits"]]
    credit(rest)
    for key in sorted(held, key=lambda k: (held[k]["resolve_date"],
                                           held[k]["t"]["code"])):
        close_out(held[key])
    peak = max(peak, eq)
    mdd = min(mdd, eq / peak - 1)
    cc = sorted(conc)
    m = len(cc)
    return {"curve": curve, "fill_log": fill_log,
            "exit_log": exit_log,
            "ret_log": ret_log,
            "equity_pct": (eq - 1) * 100, "n_filled": n,
            "arith_pct": arith[0] * 100,
            "filled_per_trade": (st.mean(fills) if fills else 0.0),
            "win_rate": (w / n * 100 if n else 0.0),
            "money_win_rate": (mw / n * 100 if n else 0.0),
            "mdd_pct": mdd * 100, "max_loss_streak": best,
            "cash_floor": cash_floor,
            "blocked_cash": n_blocked_cash, "truncated": n_trunc,
            "n_swap": n_swap, "swap_ret": list(swap_ret),
            "swap_log": list(swap_log),
            "n_alt": n_alt, "n_base": n_base,
            "n_added": n_added, "n_add_blocked": n_add_blocked,
            # 예약의 «대가» — 이걸 안 찍으면 예약판이 공짜로 보인다
            "expo_mean": (st.mean(expo_frac) * 100 if expo_frac else 0.0),
            "resv_frac_mean": (st.mean(resv_frac) * 100 if resv_frac else 0.0),
            "resv_frac_max": (max(resv_frac) * 100 if resv_frac else 0.0),
            "idle_end_n": len(idle_end),
            "idle_end_mean": (st.mean(idle_end) * 100 if idle_end else 0.0),
            "nom_w_mean": (st.mean(nomw.values()) if nomw else 0.0),
            "conc_mean": st.mean(cc) if cc else 0.0,
            "conc_median": cc[m // 2] if cc else 0,
            "conc_p90": cc[9 * m // 10] if cc else 0,
            "conc_max": cc[-1] if cc else 0}


def band(trades, n_runs: int = 200, seed0: int = 0, **kw):
    rs = [sim_lots(trades, seed=s, **kw) for s in range(seed0, seed0 + n_runs)]
    eq = sorted(r["equity_pct"] for r in rs)
    out = {"median": st.median(eq), "p5": eq[int(n_runs * .05)],
           "p95": eq[int(n_runs * .95)], "runs": rs}
    for k in ("mdd_pct", "n_filled", "win_rate", "money_win_rate", "arith_pct",
              "filled_per_trade", "conc_mean", "conc_median", "conc_p90",
              "n_added", "n_add_blocked", "blocked_cash", "truncated",
              "resv_frac_mean", "resv_frac_max", "idle_end_n", "idle_end_mean"):
        out[k.replace("_pct", "")] = st.median([r[k] for r in rs])
    out["conc_max"] = max(r["conc_max"] for r in rs)
    out["cash_floor"] = min(r["cash_floor"] for r in rs)
    return out


def from_legs(ev, entry_px=100.0):
    """관문용 어댑터 — 41번 `legs`(총수익%) 사건을 **트랜치 하나** 거래로 바꾼다.

    🚨 가격이 아니라 «수익률»로 온 사건이므로, 되돌아갈 때 반올림이 어긋나지 않도록
       기준가를 `entry_px` 로 두고 `px = entry_px * (1 + g/100)` 를 쓴다.
       `credit` 이 다시 `round(px/epx*100-100, 2)` 를 하므로 **g 가 소수 둘째 자리면
       왕복이 정확하다**(41번 `_mk` 가 이미 `round(...,2)` 로 만든 값이라 성립).
    """
    out = []
    for e in ev:
        exits = [(d, fr, entry_px * (1 + g / 100.0)) for d, fr, g in e["legs"]]
        out.append({"code": e["code"], "scan_date": e["scan_date"],
                    "pattern": e["pattern"], "entry_date": e["entry_date"],
                    "entry_px": entry_px, "stop_frac": e.get("stop_frac") or 0.08,
                    "shares": (1.0,),
                    "masks": {(): {"lots": [(e["entry_date"], entry_px, 1.0, -1)],
                                   "sched": [], "exits": exits,
                                   "resolve_date": e["resolve_date"],
                                   "result": e["result"]}}})
    return out

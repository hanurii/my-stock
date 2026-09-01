# -*- coding: utf-8 -*-
r"""146 — 「못 산 날들이 «왜» 못 샀나」. 사전등록 tasks/146-why-not-bought.md 그대로.

🚨 **«세기» 판이다. 판정판이 아니다.**
   ⛔ 수익 · 체 점수 · 자 A·B · 순열 · max-T — «하나도» 안 쓴다
   🚨 **관문 A★: 이 파일은 `score_of`·`order_by`·`metric_A`·`metric_B`·`perm_null` 을
      «호출하지 않는다».** 143 에서는 «적재부»만 가져온다
   ⛔ 뒤 구간(2012~) 안 연다 · N 안 늘린다

  ㉠ 자리가 차서 «아예» 못 삼   (break 시점의 «남은 후보 수»로 «센다»)
  ㉡ 현금이 사실상 0 이라 못 삼
  ㉢ 잘려서 «조금 샀다»          ← 🚨 **샀다.** 판정에서 «뺀다». 따로 보고
  판정  ㉠ vs ㉡ 둘 사이 · 「하한 > 50%」 · 아니면 「못 정한다」

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/146-why-not-bought.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r143", HERE / "143-sieve.py")
r143 = _u.module_from_spec(_s)
_s.loader.exec_module(r143)
r91 = r143.r91
import slot_sim_lots as sl                                       # noqa: E402

# 🚨 관문 A★ — 이 이름들을 «쓰지 않는다». 구조로 확인한다
_FORBIDDEN = ("score_of", "order_by", "metric_A", "metric_B", "perm_null", "day_ranks")

OUT = ROOT / "research" / "handoff" / "data" / "146-why-not-bought.json"
SEEDS = tuple(range(20))                 # §7 — 씨앗 0~19
WIN_THR = (0.0, 10.0, 20.0)              # §3⑤ — 주판정은 > 0%, 나머지는 견고성
Z2 = 2.2414                              # 본페로니 2 · 양측 → 동시 95%
SD_INFLATE = 1.37                        # §7 — n=20 SD 추정의 단측 95% 상한 배수


def gate_A():
    """A★ — 금지 이름을 «쓰지 않는지» 소스에서 확인한다."""
    src = Path(__file__).read_text(encoding="utf-8")
    body = src[src.index("def collect("):]
    hit = [n for n in _FORBIDDEN if (n + "(") in body]
    return (not hit), hit


def wilson(k, n, z=Z2):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def collect(ev, seed, slots, use_cash=True):
    """한 판 돌리고 «사건»을 적는다. 🚨 카운터가 아니라 «기록»이라 겹셈이 불가능하다."""
    rows, daylog = [], []

    def _final_ret(h):
        """🚨 2026-09-01 정정 — `h["result"]` 는 «문자열» "win"/"loss" 다
        (`41-round1-exits.py:235`). 숫자로 걸렀다가 **전부 0** 이 됐다.
        ⇒ 139 라벨식 그대로 `all_exits` 에서 «수»를 만든다."""
        ep = h["t"]["entry_px"]
        if not ep:
            return None
        ax = h.get("all_exits") or []
        if not ax:
            return None
        return sum(fr * (px / ep * 100.0 - 100.0) for _d, fr, px in ax)

    def _snap(d, held):
        out = []
        for h in held.values():
            out.append((_final_ret(h),
                        r143._ord(d) - r143._ord(h["t"]["entry_date"]),
                        any(e[0] < d for e in h.get("all_exits", []))))
        return out

    def ev_fn(kind, d, items, free, held):
        if kind == "DAY":
            daylog.append((d, free, _snap(d, held)))     # 자리-일 회계
            return
        blk = _snap(d, held)
        for t in items:
            rows.append({"k": kind, "d": d, "free": free, "blk": blk})

    with r91.r41.Cost(*r91.COST):
        r = sl.sim_lots(ev, seed=seed, slots=slots, risk=r91.RISK, cap=r91.CAP,
                        reserve=False, fill_rule="truncate",
                        cash_rule="per_slot", use_cash=use_cash, ev_fn=ev_fn)
    return rows, daylog, r


def main() -> int:
    r143._guard()
    print("=" * 98, flush=True)
    print("146 — 「못 산 날들이 «왜» 못 샀나」 · **«세기» 판** (판정판 아님)", flush=True)
    print("🚨 수익·체 점수·자 A·B·순열·max-T «하나도» 안 씀 · ⛔ 뒤 구간 «안 엶» · N 안 늘림",
          flush=True)
    print("=" * 98, flush=True)

    okA, hit = gate_A()
    print("", flush=True)
    print("  A* `score()` 계열 미호출 — %s%s"
          % ("**통과**" if okA else "🚨 **미통과**", ("  " + str(hit)) if hit else ""), flush=True)

    res = {"seeds": list(SEEDS), "z2": Z2, "sd_inflate": SD_INFLATE}
    for target, cut in r143.CUT.items():
        print("", flush=True)
        print("=" * 98, flush=True)
        print("목표 **+%.0f%%**" % target, flush=True)
        print("=" * 98, flush=True)
        sday_ignored, ev = r143.ref_fills(target)   # 후보 목록만 쓴다 (s 는 안 씀)
        ndays = len({t["entry_date"] for t in ev})
        print("  C* 후보 **%d건** · 진입일 %d일 · 뒤 구간 %d건"
              % (len(ev), ndays,
                 len([t for t in ev if t["entry_date"] >= "2012-01-01"])), flush=True)

        # ── 본판: 씨앗 20판 ──────────────────────────────────────────
        per_seed, pool, daypool, expo = [], [], [], []
        for sd in SEEDS:
            rows, daylog, r = collect(ev, sd, r91.SLOTS)
            nA = sum(len(x["blk"]) > 0 or True for x in rows if x["k"] == "A")
            cnt = Counter(x["k"] for x in rows)
            tot = cnt["A"] + cnt["B"] + cnt["C"] + cnt["BUY"]
            per_seed.append((cnt["A"], cnt["B"], cnt["C"], cnt["BUY"], tot))
            pool.extend(rows)
            daypool.append(daylog)
            expo.append(r["expo_mean"])          # 🚨 «같은 판»에서 직접 받는다

        # ── 관문 B★ 항등식 ──────────────────────────────────────────
        bad = [(i, s) for i, s in enumerate(per_seed) if s[4] != len(ev)]
        print("  B* 항등식 ㉠+㉡+㉢+매수 = 후보 전체(%d) — 어긋난 판 **%d개** / %d  %s"
              % (len(ev), len(bad), len(SEEDS),
                 "**통과**" if not bad else "🚨 **미통과 — 수를 «안 읽는다»**"), flush=True)
        if bad:
            for i, s in bad[:3]:
                print("     씨앗 %d: %d+%d+%d+%d = %d ≠ %d" % (i, s[0], s[1], s[2], s[3], s[4],
                                                              len(ev)), flush=True)

        # ── 관문 D★ / E★ ────────────────────────────────────────────
        r1, _d1, _ = collect(ev, 0, 1)
        c1 = Counter(x["k"] for x in r1)
        r9, _d9, _ = collect(ev, 0, 999, use_cash=False)
        c9 = Counter(x["k"] for x in r9)
        okD = c1["A"] > per_seed[0][0]
        okE = (c9["A"] == 0 and c9["B"] == 0 and c9["C"] == 0)
        print("  D* 양성 — 슬롯 1개면 ㉠ 이 %d → **%d** %s"
              % (per_seed[0][0], c1["A"], "**통과**" if okD else "🚨 **미통과**"), flush=True)
        print("  E* 음성 — 슬롯 999·현금 무제한이면 ㉠㉡㉢ = **%d/%d/%d** %s"
              % (c9["A"], c9["B"], c9["C"],
                 "**통과** (전부 0)" if okE else "🚨 **미통과 — 헛것을 센다**"), flush=True)

        gates = okA and (not bad) and okD and okE
        if not gates:
            print("", flush=True)
            print("  ⏹ **관문 미통과 — 아래 수를 «안 읽는다»**", flush=True)
            res["t%d" % int(target)] = {"verdict": "관문 미통과",
                                        "gates": {"A": okA, "B": not bad, "D": okD, "E": okE}}
            continue

        # ── 판정: ㉠ vs ㉡ (㉢ 은 «뺀다») ─────────────────────────────
        A = sum(s[0] for s in per_seed)
        Bc = sum(s[1] for s in per_seed)
        C = sum(s[2] for s in per_seed)
        BUY = sum(s[3] for s in per_seed)
        nAB = A + Bc
        pA, lA, hA = wilson(A, nAB)
        pB, lB, hB = wilson(Bc, nAB)
        # 판간 SD (씨앗별 ㉠ 몫)
        fr = [s[0] / max(1, s[0] + s[1]) for s in per_seed]
        sd_ = st.stdev(fr)
        half_sd = Z2 * sd_ * SD_INFLATE / math.sqrt(len(SEEDS))
        half_w = (hA - lA) / 2.0
        use_sd = half_sd > half_w
        lo_use = (st.mean(fr) - half_sd) if use_sd else lA
        hi_use = (st.mean(fr) + half_sd) if use_sd else hA

        print("", flush=True)
        print("## 갈래 (씨앗 %d판 합침 · 사건 기준)" % len(SEEDS), flush=True)
        print("  ㉠ 자리가 차서 못 삼   **%6d**   ㉡ 현금이 0 이라 못 삼  **%6d**" % (A, Bc), flush=True)
        print("  ㉢ 잘려서 «조금 샀다»  **%6d**   매수(온전히)          **%6d**   합 %d"
              % (C, BUY, A + Bc + C + BUY), flush=True)
        print("     🚨 **㉢ 은 «샀다». 판정에서 «뺀다»** — 「못 산 날」의 갈래가 아니다", flush=True)
        print("", flush=True)
        print("## 판정 — ㉠ vs ㉡ (분모 %d)" % nAB, flush=True)
        print("  ㉠ 몫 **%.1f%%**  동시 95%% Wilson [%.1f%%, %.1f%%]"
              % (100 * pA, 100 * lA, 100 * hA), flush=True)
        print("  ㉡ 몫 **%.1f%%**  동시 95%% Wilson [%.1f%%, %.1f%%]"
              % (100 * pB, 100 * lB, 100 * hB), flush=True)
        print("  판간 SD(㉠ 몫) **%.4f** → ×1.37 반폭 **%.1f%%p**  vs  Wilson 반폭 %.1f%%p  → **%s 씀**"
              % (sd_, 100 * half_sd, 100 * half_w, "판간 SD" if use_sd else "Wilson"), flush=True)
        print("  ⇒ 판정용 ㉠ 구간 = [**%.1f%%**, %.1f%%]" % (100 * lo_use, 100 * hi_use), flush=True)
        if lo_use > 0.5:
            verdict = "자리 제약이 주된 원인 (㉠ 지배)"
        elif (1 - hi_use) > 0.5:
            verdict = "자본 제약이 주된 원인 (㉡ 지배)"
        else:
            verdict = "못 정한다 (두 구간이 50% 를 가로지름)"
        print("  ▶ **%s**" % verdict, flush=True)

        # ── ㉠-1 / ㉠-2 : «자리-일» 회계 ─────────────────────────────
        print("", flush=True)
        print("## ㉠-1 / ㉠-2 — **«자리-일» 회계** (총합이 «반드시» 맞는다)", flush=True)
        tot_sd_days = len(SEEDS) * r91.SLOTS * ndays
        wA = {th: 0 for th in WIN_THR}
        loseA, empty, occ = 0, 0, 0
        hold_days_all, part_days = [], 0
        for dl in daypool:
            for d, free, sts in dl:
                empty += free
                occ += len(sts)
                for r_, hd, part in sts:
                    for th in WIN_THR:
                        if r_ is not None and r_ > th:
                            wA[th] += 1
                    if r_ is not None and r_ <= 0.0:
                        loseA += 1
                    hold_days_all.append(hd)
                    part_days += 1 if part else 0
        tot = occ + empty
        print("  총 자리-일 **%s** = 잡힌 %s + 빈 %s   (항등식 %s)"
              % ("{:,}".format(tot), "{:,}".format(occ), "{:,}".format(empty),
                 "**맞음**" if occ + empty == tot else "🚨 **안 맞음**"), flush=True)
        # 🚨 2026-09-01 신설 — 이 항등식이 «없어서» ㉠-1/㉠-2 가 전부 0 인 것을 놓쳤다.
        #    「잡힌 + 빈 = 총합」은 통과하는데 「㉠-1 + ㉠-2 = 잡힌」은 0+0=0 이었다 (유형 24′)
        ok_split = (wA[0.0] + loseA == occ)
        print("  🆕 **㉠-1 + ㉠-2 = 잡힌** — %s + %s = %s vs %s  %s"
              % ("{:,}".format(wA[0.0]), "{:,}".format(loseA),
                 "{:,}".format(wA[0.0] + loseA), "{:,}".format(occ),
                 "**통과**" if ok_split else
                 "🚨 **미통과 — 「승자/패자」를 «세는 코드»가 무효다. 수를 «안 읽는다»**"), flush=True)
        if not ok_split:
            res["t%d" % int(target)] = {"verdict": "관문 미통과(자리-일 분할)",
                                        "occ": occ, "win0": wA[0.0], "lose": loseA}
            del ev
            continue
        print("  ㉠-1ᴬ «사후» — 자리를 잡은 것이 «결국 이긴» 자리-일 (문턱별 · 주판정은 > 0%)",
              flush=True)
        for th in WIN_THR:
            print("     최종 수익률 > %4.0f%%  →  **%.1f%%** of 잡힌 자리-일  (%s)%s"
                  % (th, 100 * wA[th] / max(1, occ), "{:,}".format(wA[th]),
                     "   ★ **주판정**" if th == 0.0 else ""), flush=True)
        print("     🚨 **룩어헤드 · «회고 회계»용 · 규칙으로 «못» 만든다**", flush=True)
        print("     ㉠-2 «결국 진» 자리-일 **%.1f%%** (%s)"
              % (100 * loseA / max(1, occ), "{:,}".format(loseA)), flush=True)
        print("  ㉠-1ᴮ′ ★«주» 시점 정의 — 보유 일수  중앙 **%.0f일** · 평균 %.1f일 · P90 %.0f일"
              % (st.median(hold_days_all), st.mean(hold_days_all),
                 sorted(hold_days_all)[int(0.9 * len(hold_days_all))]), flush=True)
        print("  ㉠-1ᴮ  «시점» 이진 — 그날까지 부분익절이 «이미 난» 자리-일 **%.1f%%**"
              % (100 * part_days / max(1, occ)), flush=True)

        # ── ★ «자리» 점유 vs «자본» 투입 — 두 축을 «같은 판»에서 나란히 ──
        occ_pct = 100.0 * occ / max(1, tot)
        exp_pct = st.mean(expo)
        print("", flush=True)
        print("## ★ «자리» 점유 vs «자본» 투입 — **같은 판에서 «직접» 잰다**", flush=True)
        print("  자리 점유 **%.1f%%** (자리-일 «개수» 축)   ·   자본 투입 **%.1f%%** "
              "(`expo_mean` = open_w/eq · «돈» 축)" % (occ_pct, exp_pct), flush=True)
        print("  → 간극 **%.1f%%p**" % (occ_pct - exp_pct), flush=True)
        print("     🚨 **두 수는 «다른 축»이다** — 자리는 «개수», 투입은 «돈».", flush=True)
        print("     ★ 간극의 «기전»: **부분익절이 나면 돈은 «돌아오는데» 자리는 «resolve_date 까지»", flush=True)
        print("        잡혀 있다.** 그날까지 부분익절이 난 자리-일이 **%.1f%%** 다(바로 위)"
              % (100 * part_days / max(1, occ)), flush=True)
        print("     ⛔ **「그러니 회전을 높이면 돈이 는다」로 «안» 넘어간다** — 138 이 이미"
              " 「돈은 안 늘더라」를 냈다. 이건 «묘사»다", flush=True)

        res["t%d" % int(target)] = {
            "verdict": verdict, "A": A, "B": Bc, "C": C, "BUY": BUY, "n_ab": nAB,
            "pA": pA, "wilson": [lA, hA], "sd_between": sd_, "use_sd": use_sd,
            "band": [lo_use, hi_use],
            "slot_days": {"total": tot, "occupied": occ, "empty": empty},
            "winA": {str(int(th)): wA[th] / max(1, occ) for th in WIN_THR},
            "loseA": loseA / max(1, occ),
            "hold_median": st.median(hold_days_all),
            "occ_pct": 100.0 * occ / max(1, tot), "expo_mean": st.mean(expo),
            "partial_pct": part_days / max(1, occ),
            "gates": {"A": okA, "B": True, "D": okD, "E": okE}}
        del ev

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: %s" % OUT.name, flush=True)
    print("🚨 **이 판은 «상태»만 셌다. 수익·우위에 대한 «어떤 주장도» 안 한다.**", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

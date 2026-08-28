# -*- coding: utf-8 -*-
r"""99 — **원전 «절차»를 우리 자료에 돌린다.** 사전등록 `tasks/99-source-faithful.md`.

원전(사용자가 옮긴 1차 본문 · 검산 완료):
```
전체 포지션 25% · 손절 **−10%** · 익절 +20% (손익비 2:1)
사다리  ¼(6.25%) → ½(12.5%) → 전체(25%)   «두 배씩»
방아쇠  **직전 거래의 성공**
개수    **산출물**. 격자로 돌리지 않는다
```

## 🚨 설계검증(`25bd1c97`)이 값 보기 «전»에 고치라 한 여섯 — 전부 반영
```
1. **본문 −10% vs 트윗 5% 충돌**을 적는다 (아래 §충돌)
2. `recent` 5 → **20**  (5 로는 사다리 «상태»를 복원 못 한다. 반례 W L W L W)
3. **「한 칸 내림」은 본문에 «없다»** → A안(우리 구성) / B안(본문·래칫) **둘 다** 돌린다
4. `slots` 12 → **20** (사다리는 ¼ 로 시작해 «4배 많은» 종목을 든다. 12 가 그걸 잘랐다)
5. **가짜 사다리 대조** — 형태는 같고 «내용»만 없앤다. **B★ 가 무엇을 재는지 이것만이 가른다**
6. **−10% 판이라 74·82·86·91·94(−8%)와 «직접 비교 불가»**
```

## 🚨 충돌 — 값 보기 «전»에 기록
```
트윗 [검색요약]        "A 25% position size **requires a 5% stop**"  → 25%×5%  = 위험 1.25%
본문 [1차·사용자 전사]  25% 포지션 · 손절 $1,000                      → 25%×10% = 위험 2.50%
```
**같은 25% 에 손절이 5% 와 10% 로 갈린다. 둘 다 그의 것이라 한다.**
→ **이 판은 «본문 표»를 따라 −10% 로 간다. 트윗과 어긋난다는 것을 «알고» 고른다.**
→ **책 목록에 새 항목**으로 넣는다.
"""
from __future__ import annotations

import json
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                       # noqa: E402
import slot_sim_lots as sl                                     # noqa: E402
import _lean_load as LL                                        # noqa: E402

r91 = LL.r91
r41 = r91.r41

# ── 원전 값 ───────────────────────────────────────────────────────────────
STOP_SRC, TARGET_SRC = 10.0, 20.0      # 원전 −10% / +20%
CAP_SRC, RISK_SRC = 0.25, 0.025        # 전체 포지션 25% · 계좌 위험 최대 2.5%
# 🚨 `cash_rule` 이 결정적이다 (첫 판에서 틀렸다):
#   "per_slot" = 현금을 «빈 칸 수»로 나눈다 → 슬롯이 크면 포지션이 «자동으로» 작아진다
#                → **원전의 「전체 포지션 25%」가 전혀 안 나온다.** 첫 판이 그래서 무의미했다.
#                신호는 **「체결 수가 양쪽 «똑같이» 나온 것」**이었다.
#   "seq"      = 현금을 «순차»로 쓴다 → 각 포지션이 cap(25%)씩, **개수는 «현금»이 정한다**
CASH_RULE = "seq"
RECENT_N = 20                          # 🚨 5 로는 사다리 «상태»를 복원 못 한다
SLOTS_SRC = 20                         # 🚨 «묶으면 안 된다» — 20 × 6.25% = 125% > 100% 라
                                       #    «현금»이 먼저 문다. 12 는 사다리 팔에서 물었다.
MULT = (0.25, 0.50, 1.00)              # ¼ · ½ · 전체
N_SEED = 200
A_PASS = 55.0

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
BLOCKS = (("닷컴 1999~2001", "1999-04-01", "2001-12-31"),
          ("2002~2017", "2002-01-01", "2017-08-31"),
          ("2018~2026", "2017-09-01", "2026-08-21"))
# 🚨 가짜약은 **팔마다 «그 팔의» 칸 비율**에 맞춰야 한다.
#    첫 판은 래칫 비율(¼2%/½2%/전체96%)에 맞춘 가짜약 «하나»만 뒀는데,
#    A안은 «완전히 다른» 비율을 내므로 **A안의 대조가 못 됐다.**
ARMS = ("A 내림있음(우리구성)", "  가짜(A비율)", "B 래칫(본문)", "  가짜(B비율)")


def _walk(recent, down):
    """직전 청산들의 성패를 이어 «칸»을 만든다. `down=False` 면 «한 방향 래칫»."""
    lvl = 0
    for w in recent:
        if w:
            lvl = min(2, lvl + 1)
        elif down:
            lvl = max(0, lvl - 1)
    return lvl


def ladder_down(recent, seed=None, t=None):
    """A안 — 성공하면 올리고 **실패하면 한 칸 내린다**.

    🚨 **「한 칸 내림」은 본문에 «없다»**(설계검증 `25bd1c97`).
       본문은 「손실 나는 «종목»을 매도해 비중을 줄인다」 = **보유 관리**이지
       「다음 «거래»를 작게 산다」가 아니다. → **정본/우리 구성**으로 라벨한다.
    """
    return MULT[_walk(recent, True)]


def ladder_ratchet(recent, seed=None, t=None):
    """B안 — **본문에 «있는» 것만**. 「성공 거래의 연속선상에서 두 배씩 늘린다」.

    내리는 규칙이 «없으므로» 한 방향 래칫이다. **이쪽이 본문에 더 가깝다.**
    """
    return MULT[_walk(recent, False)]


def make_random(props):
    """가짜 사다리 — **형태는 같고 «내용»만 없앤다** (86 의 처방 그대로).

    성적과 «무관하게» ¼/½/전체 를 **진짜 사다리가 낸 것과 같은 비율**로 뽑는다.
    🚨 **가짜도 B★ 를 넘으면 B★ 가 잰 건 «사다리»가 아니라 «덜 드는 것»이다.**
    난수를 (seed, 거래 신원)에 걸어 **짝비교가 성립**하게 한다.
    """
    cum, acc = [], 0.0
    for m, pr in zip(MULT, props):
        acc += pr
        cum.append((acc, m))

    def f(recent, seed, t):
        u = random.Random("%d|%s|%s|%s" % (seed, t["code"], t["scan_date"],
                                           t.get("pattern", ""))).random()
        for c, m in cum:
            if u <= c:
                return m
        return MULT[-1]
    return f


def realized(t):
    """한 거래의 «실현» 손익(진입가 대비 %). 전체 크기 기준."""
    m = t["masks"][()]
    lots = m.get("lots") or []
    if not lots:
        return None
    epx = lots[0][1]
    g = 0.0
    for _d, sh, px in (m.get("exits") or []):
        g += sh * (px / epx - 1.0)
    return g * 100.0


def build(d0, d1, stop):
    """원전 손절폭으로 경로를 결착한다. 🚨 −8% 가 아니라 −10% 다."""
    by2, _cand, n_all = LL.load_combo(YEARS, d0, d1)
    ev, blocked = [], 0
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blocked += 1
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=stop,
                                 target=TARGET_SRC, shares=(1.0,), add_stop="floor_entry")
            open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
            t["_hold"] = r91._ord(t["masks"][()]["resolve_date"] or p["entry_date"]) \
                - r91._ord(p["entry_date"])
            ev.append(t)
    return ev, n_all, blocked


def run(ev, size_fn, n_seed):
    with r41.Cost(*r91.COST):
        return [sl.sim_lots(ev, seed=k, slots=SLOTS_SRC, risk=RISK_SRC, cap=CAP_SRC,
                            reserve=False, fill_rule="truncate", cash_rule=CASH_RULE,
                            size_fn=size_fn, recent_n=RECENT_N) for k in range(n_seed)]


def level_props(ev, size_fn, n_seed):
    """진짜 사다리가 «실제로» 낸 ¼/½/전체 비율 — 가짜약을 그 비율에 맞춘다."""
    cnt = [0, 0, 0]

    def spy(recent, seed, t):
        m = size_fn(recent, seed, t)
        cnt[MULT.index(m)] += 1
        return m
    run(ev, spy, n_seed)
    tot = sum(cnt) or 1
    return [c / tot for c in cnt]


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else N_SEED
    print("=" * 112, flush=True)
    print("99 — 원전 «절차»를 우리 자료에 돌린다 · 사전등록 tasks/99 (설계검증 25bd1c97 반영)",
          flush=True)
    print("=" * 112, flush=True)
    print("원전: 전체 25%% · 손절 **−10%%**(본문 표) · 익절 +20%% · 사다리 ¼→½→전체", flush=True)
    print("🚨 트윗은 「25%% 면 손절 5%%」라 한다 — **어긋난다는 걸 «알고» 본문을 따른다**", flush=True)
    print("🚨 예상(등록): ㉠ 켈리는 «작거나 음수» · ㉡ 자산 낮아지고 낙폭 얕아진다\n", flush=True)

    # ── 관문 ② ────────────────────────────────────────────────────────
    ev8, _n, _b = build("2017-09-01", "2026-08-21", 8.0)
    a = run(ev8, None, 3)
    with r41.Cost(*r91.COST):
        b = [sl.sim_lots(ev8, seed=k, slots=SLOTS_SRC, risk=RISK_SRC, cap=CAP_SRC,
                         reserve=False, fill_rule="truncate", cash_rule=CASH_RULE)
             for k in range(3)]
    same = all(abs(x["equity_pct"] - y["equity_pct"]) < 1e-12 for x, y in zip(a, b))
    print("관문 ② size_fn=None 이 옛 경로와 같은가 → **%s**"
          % ("통과" if same else "🚨 미통과 — 멈춘다"), flush=True)
    if not same:
        return 2

    # ── 관문 ③′ 사다리 «상태 복원» — 5건 vs 20건이 얼마나 다른가 ────────
    rnd = random.Random(0)
    diff = 0
    for _ in range(20000):
        seq = [rnd.random() < 0.4 for _ in range(20)]
        if _walk(seq[-5:], True) != _walk(seq, True):
            diff += 1
    print("관문 ③′ `recent` 5건 vs 20건이 «다른 칸»을 내는 비율 = **%.1f%%** (무작위 2만 판)"
          % (100.0 * diff / 20000), flush=True)

    # ── 관문 ④ ────────────────────────────────────────────────────────
    ev10, n_all, blk10 = build(D0, D1, STOP_SRC)
    ev08, _n8, blk08 = build(D0, D1, 8.0)
    print("관문 ④ 손절폭이 진입 수를 바꾼다 — 후보 %s · −8%% 진입 %s · **−10%% 진입 %s** (차 %+d)"
          % ("{:,}".format(n_all), "{:,}".format(len(ev08)),
             "{:,}".format(len(ev10)), len(ev10) - len(ev08)), flush=True)
    print("   🚨 그래서 이 판은 74·82·86·91·94(−8%%)와 **직접 비교 불가**다", flush=True)

    # ── ㉠ 켈리 (서술) ────────────────────────────────────────────────
    print("\n" + "=" * 112, flush=True)
    print("㉠ 원전 절차로 «비중»을 풀면  (서술 · 문턱 없음 · 손절 −10%% 기준)", flush=True)
    print("  %-16s %8s %8s %10s %10s %8s %11s"
          % ("창", "거래", "승률 p", "평균이익", "평균손실", "손익비 b", "**켈리 f***"), flush=True)
    print("  " + "-" * 88, flush=True)
    kel = {}
    for lab, a_, b_ in BLOCKS + (("── 전체", D0, D1),):
        g = [realized(t) for t in ev10 if a_ <= t["entry_date"] <= b_]
        g = [x for x in g if x is not None]
        w = [x for x in g if x > 0]
        l = [-x for x in g if x <= 0]
        if not w or not l:
            continue
        p = len(w) / len(g)
        bb = st.mean(w) / st.mean(l)
        f = p - (1 - p) / bb
        kel[lab] = {"n": len(g), "p": p, "b": bb, "f": f}
        print("  %-16s %8s %7.1f%% %+9.2f%% %9.2f%% %8.2f %+10.2f%%"
              % (lab, "{:,}".format(len(g)), 100 * p, st.mean(w), st.mean(l), bb, 100 * f),
              flush=True)
    print("  " + "-" * 88, flush=True)
    print("  대조(원전)       p=50.0%% · b=2.00 → f* = **+25.00%%**", flush=True)

    # ── ㉡ 판정 — 세 팔 ───────────────────────────────────────────────
    print("\n" + "=" * 112, flush=True)
    print("㉡ 사다리 판정 · seed %d · **세 창 «모두»** 넘어야 통과" % n_seed, flush=True)
    verd = {}
    for lab, a_, b_ in BLOCKS:
        ev = [t for t in ev10 if a_ <= t["entry_date"] <= b_]
        c = run(ev, None, n_seed)
        pA = level_props(ev, ladder_down, min(12, n_seed))
        pB = level_props(ev, ladder_ratchet, min(12, n_seed))
        arms = {ARMS[0]: ladder_down, ARMS[1]: make_random(pA),
                ARMS[2]: ladder_ratchet, ARMS[3]: make_random(pB)}
        ce = [z["equity_pct"] for z in c]
        marc = abs(st.median(ce) / st.median(z["mdd_pct"] for z in c))
        print("\n  ### %s  (거래 %s)" % (lab, "{:,}".format(len(ev))), flush=True)
        print("     낸 칸 비율   A안 ¼%.0f%% ½%.0f%% 전체%.0f%%   ·   B래칫 ¼%.0f%% ½%.0f%% 전체%.0f%%"
              % (100 * pA[0], 100 * pA[1], 100 * pA[2],
                 100 * pB[0], 100 * pB[1], 100 * pB[2]), flush=True)
        print("     %-18s 자산 %+9.2f%%  · MAR %5.2f · MDD %6.1f%% · 노출 %5.1f%% · 동시 %4.1f · 체결 %5.0f"
              % ("(대조·전부 전체)", st.median(ce), marc,
                 st.median(z["mdd_pct"] for z in c),
                 st.median(z["expo_mean"] for z in c),
                 st.median(z["conc_median"] for z in c),
                 st.median(z["n_filled"] for z in c)), flush=True)
        for anm, afn in arms.items():
            x = run(ev, afn, n_seed)
            te = [z["equity_pct"] for z in x]
            dif = sorted(u - v for u, v in zip(te, ce))
            win = 100.0 * sum(1 for v in dif if v > 0) / n_seed
            mart = abs(st.median(te) / st.median(z["mdd_pct"] for z in x))
            mde = 2.8 * st.pstdev(dif) / math.sqrt(n_seed)
            okA, okB = win > A_PASS, mart > marc
            verd.setdefault(lab, {})[anm] = {
                "win": win, "med": st.median(dif), "mar_c": marc, "mar_t": mart,
                "A": okA, "B": okB, "mde": mde,
                "expo": st.median(z["expo_mean"] for z in x),
                "conc": st.median(z["conc_median"] for z in x),
                "n_filled": st.median(z["n_filled"] for z in x)}
            print("     %-18s 자산 %+9.2f%% (짝차 %+7.2f) · **MAR %5.2f** · A★%5.1f%%%s B★%s"
                  " · MDE %5.1f · 노출 %5.1f%% · 동시 %4.1f · 체결 %5.0f"
                  % (anm, st.median(te), st.median(dif), mart, win,
                     "✅" if okA else "❌", "✅" if okB else "❌", mde,
                     st.median(z["expo_mean"] for z in x),
                     st.median(z["conc_median"] for z in x),
                     st.median(z["n_filled"] for z in x)), flush=True)

    print("\n" + "=" * 112, flush=True)
    for anm in ARMS:
        oa = all(verd[l][anm]["A"] for l in verd)
        ob = all(verd[l][anm]["B"] for l in verd)
        print("  %-18s A★ %s · B★ %s  →  **%s**"
              % (anm, "통과" if oa else "미통과", "통과" if ob else "미통과",
                 "★ 통과" if (oa and ob) else "미통과"), flush=True)
    print("\n  ★ 짝지어 읽는다 — **진짜 vs «그 팔의» 가짜** (짝차 중앙)", flush=True)
    for real, fake in ((ARMS[0], ARMS[1]), (ARMS[2], ARMS[3])):
        print("     %-18s" % real.strip(), end="", flush=True)
        for l in verd:
            print("   %s 진짜 %+7.2f / 가짜 %+7.2f"
                  % (l.split()[0], verd[l][real]["med"], verd[l][fake]["med"]),
                  end="", flush=True)
        print("", flush=True)
    print("\n🚨 **가짜가 진짜만큼 하면, 잰 건 «사다리»가 아니라 «덜 드는 것/작게 여럿 드는 것»이다.**",
          flush=True)
    print("🚨 **−10%% 판이라 74·82·86·91·94(−8%%)와 직접 비교 불가.**", flush=True)
    (r91.OUT / "99-source-faithful.json").write_text(json.dumps(
        {"kelly": kel, "verdict": verd, "n_seed": n_seed,
         "n_entry_10": len(ev10), "n_entry_08": len(ev08),
         "slots": SLOTS_SRC, "recent_n": RECENT_N, "cash_rule": CASH_RULE},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("저장: 99-source-faithful.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

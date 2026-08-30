# -*- coding: utf-8 -*-
"""114 — **「깨지면 규모를 줄이면」 낙폭이 얼마나 주는가** (사용자 물음 2026-08-30)

113 에서 −45% 낙폭의 정체가 나왔다 — 3년 동안 이긴 비율이 35% → 26% 로 떨어진 채 버틴 것.
**그리고 미너비니가 말하는 「연속으로 깨지면 규모를 줄인다」를 우리는 «안 켰다».**
77·99 에서 «수익»엔 도움이 안 됐지만 **«낙폭»은 안 쟀다.**

# 🚨 방향을 «먼저» 적는다
```
노출을 줄이면 낙폭이 주는 건 **당연하다**(정의상).
→ 그래서 물음은 「주는가」가 아니라 **「신호 때문인가, 그냥 덜 들어서인가」**다
→ **동전 던지기 짝**이 이 판의 전부다. 같은 «크기 분포»를 무작위로 배정한다
예상: 99·102·103·108 에서 «전부» 동전이 진짜만큼 했다 → **이번에도 그럴 것**
```

# 팔 — 91 정본과 «같은 구성»(5칸 · 손절 −8%)에서 크기만 바꾼다
```
바탕      늘 전체 크기
㉮ 15번   최근 5건 중 «2승 미만»이면 절반   ← 미너비니 15번의 근사
          🚨 원전은 「합산 손익 > 0」인데 하네스가 승패만 넘긴다.
             승률 40%·이기면 +20 지면 −8 이라 «2승이면 대개 플러스» → 근사로 쓴다
㉯ 사다리  ¼ → ½ → 전체 (성공하면 올리고 실패하면 내림) — 99 의 A안
㉰ 연패    3연패면 절반 · 5연패면 ¼
동전      팔마다 «그 팔의» 크기 분포를 무작위 배정
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim_lots as sl                                        # noqa: E402
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
r41 = r91.r41

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
WIN = (("전체 1999~2026", "1999-04-01", "2026-08-21", 27.4),
       ("닷컴 1999~2001", "1999-04-01", "2001-12-31", 2.75),
       ("2002~2017", "2002-01-01", "2017-08-31", 15.66),
       ("2018~2026", "2017-09-01", "2026-08-21", 8.96))
MULT = (0.25, 0.50, 1.00)


def f_15(recent, seed, t):
    """미너비니 15번 근사 — 최근 5건 중 2승 미만이면 절반."""
    r = recent[-5:]
    if len(r) < 5:
        return 1.0
    return 1.0 if sum(1 for x in r if x) >= 2 else 0.5


def f_ladder(recent, seed, t):
    """99 의 A안 — ¼ → ½ → 전체. 성공하면 한 칸 위, 실패하면 한 칸 아래."""
    k = 0
    for w in recent:
        k = min(2, k + 1) if w else max(0, k - 1)
    return MULT[k]


def f_streak(recent, seed, t):
    """3연패면 절반 · 5연패면 ¼."""
    s = 0
    for w in reversed(recent):
        if w:
            break
        s += 1
    return 0.25 if s >= 5 else (0.5 if s >= 3 else 1.0)


def make_fake(props, seed0):
    """같은 «크기 분포»를 무작위로 배정한다."""
    def fn(recent, seed, t):
        r = random.Random((seed0 * 1000003) ^ (seed * 7919) ^ (id(t) & 0xFFFF))
        u = r.random()
        acc = 0.0
        for m, p in props:
            acc += p
            if u <= acc:
                return m
        return props[-1][0]
    return fn


def props_of(ev, fn, n_seed):
    cnt = {}

    def spy(recent, seed, t):
        m = fn(recent, seed, t)
        cnt[m] = cnt.get(m, 0) + 1
        return m
    run(ev, spy, min(8, n_seed))
    tot = sum(cnt.values()) or 1
    return sorted(((m, c / tot) for m, c in cnt.items()), key=lambda x: x[0])


def run(ev, size_fn, n_seed):
    with r41.Cost(*r91.COST):
        return [sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                            reserve=False, fill_rule="truncate", cash_rule="per_slot",
                            size_fn=size_fn, recent_n=20) for s in range(n_seed)]


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else 100
    print("=" * 106, flush=True)
    print("114 — **「깨지면 규모를 줄이면」 낙폭이 얼마나 주는가** · 운의 번호 %d판" % n_seed,
          flush=True)
    print("=" * 106, flush=True)
    print("🚨 노출을 줄이면 낙폭이 주는 건 **당연하다**. 물음은", flush=True)
    print("   **「신호 때문인가, 그냥 덜 들어서인가」**다 → **동전 던지기 짝**이 이 판의 전부다\n",
          flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    ev_all, _x, _y = r91.replay(by2)

    # 관문 — size_fn=None 이 91 정본과 «같은가»
    a = run(ev_all[:400], None, 3)
    with r41.Cost(*r91.COST):
        b = [sl.sim_lots(ev_all[:400], seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                         reserve=False, fill_rule="truncate", cash_rule="per_slot")
             for s in range(3)]
    same = all(abs(x["equity_pct"] - y["equity_pct"]) < 1e-12 for x, y in zip(a, b))
    print("관문 size_fn=None 이 91 정본과 같은가 → **%s**\n"
          % ("통과" if same else "🚨 미통과"), flush=True)
    if not same:
        return 3

    ARMS = (("바탕 (늘 전체)", None),
            ("㉮ 15번 (최근5중 2승미만→½)", f_15),
            ("㉯ 사다리 ¼→½→전체", f_ladder),
            ("㉰ 3연패→½ · 5연패→¼", f_streak))

    out = {}
    for lab, a0, b0, yrs in WIN:
        ev = [t for t in ev_all if a0 <= t["entry_date"] <= b0]
        print("### %s" % lab, flush=True)
        print("  %-30s %10s %10s %10s %9s"
              % ("", "연평균", "**최대낙폭**", "수익÷낙폭", "투입율"), flush=True)
        print("  " + "-" * 74, flush=True)
        row = {}
        for nm, fn in ARMS:
            for tag in (("진짜",) if fn is None else ("진짜", "동전")):
                f = fn
                if tag == "동전":
                    f = make_fake(props_of(ev, fn, n_seed), abs(hash(nm)) % 9999)
                rs = run(ev, f, n_seed)
                med = st.median(x["equity_pct"] for x in rs)
                cg = ((1 + med / 100.0) ** (1 / yrs) - 1) * 100
                md = st.median(x["mdd_pct"] for x in rs)
                ex = st.median(x["expo_mean"] for x in rs)
                key = nm if tag == "진짜" else "  동전(" + nm + ")"
                row[key] = {"cagr": cg, "mdd": md, "rr": abs(cg / md) if md else 0.0,
                            "expo": ex}
                print("  %-30s %+9.2f%% %9.1f%% %10.3f %8.1f%%"
                      % (key, cg, md, row[key]["rr"], ex), flush=True)
        out[lab] = row
        print("", flush=True)

    # ── ★ 짝지어 읽는다 ─────────────────────────────────────────────
    print("=" * 106, flush=True)
    print("★★ **진짜 vs «그 팔의» 동전** — 낙폭이 «신호 때문»에 준 만큼", flush=True)
    print("  %-30s %s" % ("", "구간별 [진짜 낙폭 − 동전 낙폭]  (**양수**면 «신호가» 더 줄인 것 — 둘 다 음수라 «덜 음수»가 좋다)"),
          flush=True)
    print("  " + "-" * 88, flush=True)
    for nm, fn in ARMS[1:]:
        cells = []
        for lab, _a, _b, _y in WIN:
            r = out[lab][nm]["mdd"]
            f = out[lab]["  동전(" + nm + ")"]["mdd"]
            cells.append("%s %+6.2f%%p" % (lab.split()[0], r - f))
        print("  %-30s %s" % (nm, "  ".join(cells)), flush=True)

    (r91.OUT / "114-shrink-drawdown.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 114-shrink-drawdown.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

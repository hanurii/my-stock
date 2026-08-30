# -*- coding: utf-8 -*-
"""115 — **114 의 발견을 «확인»한다: 연패 축소가 진짜인가** (사전등록 · 값 보기 «전»)

114 에서 「3연패→½ · 5연패→¼」가 **네 구간 모두 동전 던지기를 이겼다**(낙폭·수익 둘 다).
그런데 **사전등록한 문턱이 없었고 세 규칙 중 하나였다.** 여기서 «등록하고 다시» 잰다.

# 🚨 114 와 다른 점 셋
```
① **짝비교로 「이긴 판 비율」을 잰다** (114 는 중앙값 차이만 봤다)
② **격자를 흔든다** — 그 칸에서만 되는지 본다
③ **동전 격자의 «최대»**를 같이 잰다 (103 에서 배운 것 — 격자를 훑으면 최선은 좋아 보인다)
```

# 격자 — 6칸
```
첫 문턱 N ∈ {2, 3, 4}        (두 번째 문턱은 N+2 로 «고정»)
크기 (f1, f2) ∈ {(½, ¼), (¾, ½)}
→ 3 × 2 = **6칸**.  114 가 쓴 것은 (N=3, ½/¼) 한 칸이다
```

# 합격선 — 값 보기 «전»
| | 문턱 | |
|---|---|---|
| **X**★ | 네 구간 «모두» 낙폭이 «그 칸의» 동전보다 작은 판 > 55% | |
| **Y**★ | 네 구간 «모두» 수익도 동전보다 큰 판 > 55% | |
| **Z**★ | 그 칸의 낙폭 이득이 **동전 격자 6칸의 «최대»**를 넘는다 | 🚨 **주지표** |
| **W** | 6칸을 «전부» 적는다 + 투입율을 같이 찍는다 | 서술 |

**X★·Y★·Z★ 를 셋 다** 넘어야 「확인됐다」다.

# ★ 방향을 «먼저» 적는다
```
㉠ 114 가 맞다면 (N=3, ½/¼) 이 X★·Y★ 를 넘을 것이다
㉡ **격자가 «매끄러우면»** 진짜다 — N 이 커질수록 덜 줄이니 효과가 «매끄럽게» 작아져야 한다
   들쭉날쭉하면 **잡음이다**(103 에서 이 검산이 실패해 M★ 의 무게를 깎았다)
㉢ 🚨 **Z★ 는 못 넘을 수도 있다** — 6칸을 훑으니 동전 최대도 커진다
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
WIN = (("전체", "1999-04-01", "2026-08-21", 27.4),
       ("닷컴", "1999-04-01", "2001-12-31", 2.75),
       ("2002~2017", "2002-01-01", "2017-08-31", 15.66),
       ("2018~2026", "2017-09-01", "2026-08-21", 8.96))
A_PASS = 55.0
GRID = [(n, f1, f2) for n in (2, 3, 4) for f1, f2 in ((0.5, 0.25), (0.75, 0.5))]


def make_streak(n1, f1, f2):
    n2 = n1 + 2

    def fn(recent, seed, t):
        s = 0
        for w in reversed(recent):
            if w:
                break
            s += 1
        return f2 if s >= n2 else (f1 if s >= n1 else 1.0)
    return fn


def make_fake(props, tag):
    def fn(recent, seed, t):
        r = random.Random((tag * 1000003) ^ (seed * 7919) ^ (id(t) & 0xFFFF))
        u, acc = r.random(), 0.0
        for m, p in props:
            acc += p
            if u <= acc:
                return m
        return props[-1][0]
    return fn


def run(ev, fn, n_seed):
    with r41.Cost(*r91.COST):
        return [sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                            reserve=False, fill_rule="truncate", cash_rule="per_slot",
                            size_fn=fn, recent_n=20) for s in range(n_seed)]


def props_of(ev, fn, n_seed):
    cnt = {}

    def spy(recent, seed, t):
        m = fn(recent, seed, t)
        cnt[m] = cnt.get(m, 0) + 1
        return m
    run(ev, spy, min(8, n_seed))
    tot = sum(cnt.values()) or 1
    return sorted(((m, c / tot) for m, c in cnt.items()), key=lambda x: x[0])


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else 100
    print("=" * 112, flush=True)
    print("115 — **114 의 발견을 «확인»한다** · 사전등록 · 격자 6칸 + 칸마다 동전 · 운의 번호 %d판"
          % n_seed, flush=True)
    print("=" * 112, flush=True)
    print("🚨 114 와 다른 점: ① 짝비교로 «이긴 판 비율» ② 격자를 흔든다 ③ 동전 격자의 «최대»\n",
          flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    ev_all, _x, _y = r91.replay(by2)

    res, fake_gain = {}, []
    print("  %-18s %s" % ("칸", "구간별 [낙폭 · 낙폭이긴판 · 수익이긴판 · 투입율]"), flush=True)
    print("  " + "-" * 104, flush=True)
    for gi, (n1, f1, f2) in enumerate(GRID):
        nm = "%d연패→%s·%d연패→%s" % (n1, "½" if f1 == 0.5 else "¾",
                                      n1 + 2, "¼" if f2 == 0.25 else "½")
        fn = make_streak(n1, f1, f2)
        cells, rec = [], {}
        for lab, a0, b0, yrs in WIN:
            ev = [t for t in ev_all if a0 <= t["entry_date"] <= b0]
            rt = run(ev, fn, n_seed)
            fk = run(ev, make_fake(props_of(ev, fn, n_seed), gi + 1), n_seed)
            # 🚨 같은 seed 끼리 «짝»으로 견준다
            dm = [x["mdd_pct"] - y["mdd_pct"] for x, y in zip(rt, fk)]   # 양수 = 진짜가 «덜» 깎임
            de = [x["equity_pct"] - y["equity_pct"] for x, y in zip(rt, fk)]
            wm = 100.0 * sum(1 for v in dm if v > 0) / n_seed
            we = 100.0 * sum(1 for v in de if v > 0) / n_seed
            md = st.median(x["mdd_pct"] for x in rt)
            ex = st.median(x["expo_mean"] for x in rt)
            rec[lab] = {"mdd": md, "win_mdd": wm, "win_eq": we, "expo": ex,
                        "gain": st.median(dm)}
            if lab == "전체":
                fake_gain.append(st.median(dm))
            cells.append("%s %5.1f%% %5.1f%%%s %5.1f%%%s %4.0f%%"
                         % (lab, md, wm, "✅" if wm > A_PASS else "❌",
                            we, "✅" if we > A_PASS else "❌", ex))
        res[nm] = rec
        print("  %-18s %s" % (nm, "  ".join(cells)), flush=True)

    # ── 판정 ─────────────────────────────────────────────────────────
    print("\n" + "=" * 112, flush=True)
    X = [k for k, v in res.items() if all(v[l]["win_mdd"] > A_PASS for l in v)]
    Y = [k for k, v in res.items() if all(v[l]["win_eq"] > A_PASS for l in v)]
    print("  **X★** 네 구간 «모두» 낙폭이 동전보다 작은 판 > 55%%  →  %s"
          % (", ".join(X) if X else "**없음 — 미통과**"), flush=True)
    print("  **Y★** 네 구간 «모두» 수익도 동전보다 큰 판 > 55%%  →  %s"
          % (", ".join(Y) if Y else "**없음 — 미통과**"), flush=True)

    # Z★ — 동전 격자의 «최대» (진짜를 안 쓰고 동전끼리 6칸을 훑는다)
    print("\n  **Z★** 낙폭 이득이 «동전 격자 6칸의 최대»를 넘는가  (**주지표**)", flush=True)
    ev = [t for t in ev_all if WIN[0][1] <= t["entry_date"] <= WIN[0][2]]
    fmax = -99.0
    for gi, (n1, f1, f2) in enumerate(GRID):
        fn = make_streak(n1, f1, f2)
        pr = props_of(ev, fn, n_seed)
        a = run(ev, make_fake(pr, 900 + gi), n_seed)
        b = run(ev, make_fake(pr, 500 + gi), n_seed)
        g = st.median(x["mdd_pct"] - y["mdd_pct"] for x, y in zip(a, b))
        fmax = max(fmax, g)
    best = max(res.items(), key=lambda kv: kv[1]["전체"]["gain"])
    print("        동전 «끼리» 6칸의 최대 낙폭 이득 = **%+.2f%%p**" % fmax, flush=True)
    print("        진짜 격자의 최선 = %s **%+.2f%%p**  →  **%s**"
          % (best[0], best[1]["전체"]["gain"],
             "넘는다 — 통과" if best[1]["전체"]["gain"] > fmax else "못 넘는다 — 미통과"),
          flush=True)

    # ㉡ 격자가 «매끄러운가»
    print("\n  ★ ㉡ **격자가 매끄러운가** — N 이 커질수록 효과가 작아져야 진짜다", flush=True)
    for f1, f2, tag in ((0.5, 0.25, "½·¼"), (0.75, 0.5, "¾·½")):
        line = []
        for n1 in (2, 3, 4):
            nm = "%d연패→%s·%d연패→%s" % (n1, "½" if f1 == 0.5 else "¾",
                                          n1 + 2, "¼" if f2 == 0.25 else "½")
            line.append("%d연패 %+6.2f%%p" % (n1, res[nm]["전체"]["gain"]))
        print("     %-6s %s" % (tag, "  ".join(line)), flush=True)

    ok = bool(X) and bool(Y) and best[1]["전체"]["gain"] > fmax
    print("\n  → **확인됐는가: %s**" % ("예" if ok else "**아니오**"), flush=True)
    (r91.OUT / "115-streak-confirm.json").write_text(
        json.dumps({"res": res, "fmax": fmax, "X": X, "Y": Y, "n_seed": n_seed},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 115-streak-confirm.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

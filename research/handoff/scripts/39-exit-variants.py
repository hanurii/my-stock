# -*- coding: utf-8 -*-
"""39 · **청산 변형 오프라인 재현기** (38번 1회차) + **0회차 재현 관문**.

왜 오프라인인가
---------------
네 변형은 «진입 규칙»이 같고 «청산»만 다르다. 그런데 **청산이 바뀌면 결착일이 바뀌고 →
`open_until` 이 바뀌고 → «그 뒤 진입»까지 바뀐다**(실측: 손절 −10% 3,776 vs −5% 5,074).
그래서 **실현 진입만으로는 부족**하고 **「방아쇠가 당겨진 전수」**가 있어야 재현된다.
하네스가 `--emit-paths` 로 그걸 남긴다(`open_until` 검사 «전»에 기록).

🚨 **이 파일의 기초는 관문 하나다.**
   **0회차 규칙(−10% / +20% 전량)을 여기서 돌려 `us_YYYY.json` 과 «항목별로» 대조한다.**
   진입 수 · 체결 · 거래당 · 자산 · MDD · **연도별 분포**까지.
   **어긋나면 얼마나·어느 방향으로.** 안 맞으면 **이 계산기를 쓸 수 없다.**
   ⚠️ 오늘 배운 것: **서로 다른 규칙이 정확히 같은 값을 내면 «같은 코드»를 의심한다.**
      여기는 «같아야 맞는» 드문 경우지만, **「우연히 같은 것」과 「같은 계산인 것」을 갈라 둔다** —
      그래서 한 항목이 아니라 **여섯 항목을 다** 대조한다.

재현 순서
---------
`trigger_paths` 는 하네스의 **처리 순서 그대로** 쌓였다(스캔일 → 종목 → VCP·3C·PP).
그 순서로 훑으면서 `open_until` 을 그대로 재현하면 하네스와 같은 진입 집합이 나온다.
**연도별 파일을 따로 돌린다** — 하네스도 연도별 실행이라 `open_until` 이 해마다 초기화된다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/39-exit-variants.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
YEARS = tuple(range(2021, 2027))
N_SEED = 200


def resolve_base(p, target=20.0, stop=10.0):
    """0회차 규칙 — 하네스 `simulate_pivot_trade` 를 «그대로» 옮긴다.

    ⚠️ 기준은 **진입가**(`entry_price`)다. 피벗이 아니다(오늘 확립).
    ⚠️ 돌파일(0번째)만 특례: 둘 다 닿으면 ambiguous, 손절만 닿아도 ambiguous.
       그 뒤부터는 둘 다 → ambiguous · 목표 → win · 손절 → loss.
    """
    epx = p["entry_price"]
    T, S = epx * (1 + target / 100), epx * (1 - stop / 100)
    h, l, c, d = p["h"], p["l"], p["c"], p["d"]
    n = len(c)
    for i in range(n):
        hit_t = h[i] is not None and h[i] >= T
        hit_s = l[i] is not None and l[i] <= S
        if i == 0:
            if hit_t and hit_s:
                return d[0], "ambiguous", c[0] / epx * 100 - 100
            if hit_t:
                return d[0], "win", c[0] / epx * 100 - 100
            if hit_s:
                return d[0], "ambiguous", c[0] / epx * 100 - 100
            continue
        if hit_t and hit_s:
            return d[i], "ambiguous", c[i] / epx * 100 - 100
        if hit_t:
            return d[i], "win", c[i] / epx * 100 - 100
        if hit_s:
            return d[i], "loss", c[i] / epx * 100 - 100
    # 🚨 여기 닿았다 = **250일 상한**(또는 시계열 끝)에 걸렸다는 뜻이다.
    #    상한은 «우리가 검정하려는 바로 그 변형»(승자를 굴린다)을 잘라낸다 —
    #    **방향이 정해진 편향**이다. 그래서 변형마다 **상한 도달 수·비율·미실현**을 찍는다.
    return d[n - 1], "unresolved", c[n - 1] / epx * 100 - 100


CAP_DAYS = 250


def cap_report(paths_by_year, ev, label):
    """🚨 **250일 상한이 무는가** — 「이게 문제인가」를 논쟁하지 말고 «얼마인가»를 잰다.

    - 2% 미만이면 상한은 사실상 안 문다. **그 사실을 적고 넘어간다.**
    - 2%를 넘으면 **상한에 닿은 방아쇠만 골라 경로를 연장해 다시 뽑는다**(전수 재수집 불필요).
    ⚠️ **그 전까지 「굴려도 안 된다」류 문장을 쓰지 않는다.**
    """
    plen = {}
    for y, ps in paths_by_year.items():
        for p in ps:
            plen[(p["scan_date"], p["code"], p["pattern"])] = len(p["c"])
    hit = [e for e in ev
           if e["result"] == "unresolved"
           and plen.get((e["scan_date"], e["code"], e["pattern"]), 0) >= CAP_DAYS]
    pct = len(hit) / len(ev) * 100 if ev else 0.0
    g = [e["gain"] for e in hit]
    print("  [상한] %s — **%d일 상한에 닿은 거래 %d / %d = %.2f%%**"
          % (label, CAP_DAYS, len(hit), len(ev), pct), flush=True)
    if g:
        print("         상한 시점 미실현 — 평균 %+.2f%% · 중앙 %+.2f%% · "
              "최대 %+.2f%% · 플러스 %.1f%%"
              % (st.mean(g), st.median(g), max(g),
                 sum(1 for x in g if x > 0) / len(g) * 100), flush=True)
    print("         → %s"
          % ("**2%% 미만 — 상한은 사실상 안 문다. 이 사실을 적고 넘어간다.**" if pct < 2.0
             else "🚨 **2%% 초과 — 상한이 문다. 닿은 방아쇠의 경로를 연장해 다시 뽑아야 한다.**"
                  " 그 전까지 「굴려도 안 된다」류를 쓰지 않는다."), flush=True)
    return {"n_hit": len(hit), "pct": pct, "cap_days": CAP_DAYS,
            "unrealized_mean": st.mean(g) if g else None,
            "unrealized_median": st.median(g) if g else None,
            "needs_extension": pct >= 2.0}


def replay(paths_by_year, resolver):
    """`open_until` 을 재현하며 진입 집합을 만든다. **연도별로 따로.**"""
    ev, blocked = [], 0
    for y in YEARS:
        open_until = {}
        for p in paths_by_year.get(y, ()):
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blocked += 1
                continue
            rd, res, gain = resolver(p)
            open_until[c] = rd or p["entry_date"]
            ev.append({"code": c, "scan_date": p["scan_date"],
                       "pattern": p["pattern"], "entry_date": p["entry_date"],
                       "resolve_date": rd, "gain": gain, "result": res, "year": y})
    return ev, blocked


def load_paths():
    by = {}
    for y in YEARS:
        f = BT / "sub" / ("uspath_%d.json" % y)
        if not f.exists():
            return None, y
        by[y] = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    return by, None


def load_ref():
    ev = []
    for y in YEARS:
        f = BT / "sub" / ("us_%d.json" % y)
        d = json.loads(f.read_text(encoding="utf-8"))
        for e in d["events"]:
            e["year"] = y
            ev.append(e)
    return ev


def summarize(trades, label):
    b = slot_sim.band(trades, n_runs=N_SEED)
    pt = st.mean(slot_sim.net(t["gain"]) for t in trades)
    return {"label": label, "n": len(trades), "n_filled": b["n_filled"],
            "equity": b["median"], "mdd": b["mdd"], "per_trade": pt,
            "win_rate": b["win_rate"]}


def main():
    by, missing = load_paths()
    if by is None:
        print("🚨 `uspath_%d.json` 이 아직 없다 — 경로 방출을 먼저 끝낸다." % missing,
              flush=True)
        return
    tot = sum(len(v) for v in by.values())
    print("방아쇠 전수 경로 %d건 (연도별 %s)"
          % (tot, ", ".join("%d:%d" % (y, len(by[y])) for y in YEARS)), flush=True)

    ev, blocked = replay(by, resolve_base)
    ref = load_ref()
    print("", flush=True)
    print("=" * 88, flush=True)
    print("🚨 **0회차 재현 관문** — 오프라인 계산기가 하네스와 «항목별로» 같은가", flush=True)
    print("=" * 88, flush=True)
    tr = [{"code": e["code"], "scan_date": e["scan_date"], "pattern": e["pattern"],
           "entry_date": e["entry_date"], "resolve_date": e["resolve_date"],
           "gain": e["gain"], "result": e["result"]} for e in ev]
    rt = [{"code": e["code"], "scan_date": e["scan_date"],
           "pattern": e.get("pattern", ""), "entry_date": e["entry_date"],
           "resolve_date": e.get("resolve_date") or e["entry_date"],
           "gain": e["gain_at_resolve_pct"], "result": e["result"]} for e in ref
          if e.get("gain_at_resolve_pct") is not None]
    a, b = summarize(tr, "오프라인"), summarize(rt, "하네스")
    rows = [("진입 수", a["n"], b["n"], "%d"),
            ("체결 수", a["n_filled"], b["n_filled"], "%.0f"),
            ("거래당(%)", a["per_trade"], b["per_trade"], "%+.4f"),
            ("자산 중앙(%)", a["equity"], b["equity"], "%+.2f"),
            ("MDD(%)", a["mdd"], b["mdd"], "%.2f"),
            ("승률(%)", a["win_rate"], b["win_rate"], "%.2f")]
    bad = []
    print("  %-14s %14s %14s %14s" % ("항목", "오프라인", "하네스", "차이"), flush=True)
    for name, x, y, f in rows:
        d = x - y
        ok = abs(d) < (1e-9 if "수" in name else 1e-6)
        if not ok:
            bad.append((name, x, y, d))
        print("  %-14s %14s %14s %14s  %s"
              % (name, f % x, f % y, f % d, "일치" if ok else "🚨**불일치**"), flush=True)
    # 연도별 분포까지
    ay = {y: sum(1 for e in ev if e["year"] == y) for y in YEARS}
    byr = {y: sum(1 for e in ref if e["year"] == y) for y in YEARS}
    print("  연도별 진입 — 오프라인 %s" % ay, flush=True)
    print("             하네스   %s" % byr, flush=True)
    for y in YEARS:
        if ay[y] != byr[y]:
            bad.append(("연도 %d" % y, ay[y], byr[y], ay[y] - byr[y]))
    # 거래 단위 완전 대조
    K = lambda e: (e["scan_date"], e["code"], e["pattern"])
    A = {K(e): e for e in ev}
    B = {(e["scan_date"], e["code"], e.get("pattern", "")): e for e in ref}
    only_a = [k for k in A if k not in B]
    only_b = [k for k in B if k not in A]
    diff_g = [k for k in A if k in B
              and abs(A[k]["gain"] - (B[k].get("gain_at_resolve_pct") or 0)) > 1e-6]
    print("  거래 단위 대조 — 오프라인에만 %d · 하네스에만 %d · 수익률 다른 것 %d"
          % (len(only_a), len(only_b), len(diff_g)), flush=True)
    if only_a or only_b or diff_g:
        bad.append(("거래 단위", len(only_a), len(only_b), len(diff_g)))
        for k in (only_a[:3] + only_b[:3]):
            print("    예: %s" % (k,), flush=True)
    print("", flush=True)
    if bad:
        print("  🚨 **관문 미통과 — %d항목 어긋남. 이 계산기를 쓸 수 없다.**" % len(bad),
              flush=True)
        for r in bad:
            print("    - %s" % (r,), flush=True)
    else:
        print("  ✅ **여섯 항목 + 연도별 분포 + 거래 단위 전부 일치 — 관문 통과**", flush=True)
        print("     한 항목이 아니라 **전부**를 댔다. 「우연히 같은 것」이 아니라 "
              "**「같은 계산인 것」**이다.", flush=True)
    print("", flush=True)
    cap = cap_report(by, ev, "0회차(−10% / +20% 전량)")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "39-round0-replay-gate.json").write_text(json.dumps(
        {"offline": a, "harness": b, "cap": cap, "by_year_offline": ay, "by_year_harness": byr,
         "only_offline": len(only_a), "only_harness": len(only_b),
         "gain_mismatch": len(diff_g), "blocked_by_open_until": blocked,
         "passed": not bad}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/39-round0-replay-gate.json", flush=True)


if __name__ == "__main__":
    main()

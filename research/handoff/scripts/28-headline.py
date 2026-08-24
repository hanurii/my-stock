# -*- coding: utf-8 -*-
"""28 · **2단계 헤드라인 — 미국 vs 한국** (숫자와 구간만. 판정 문장 없음).

두뇌 세션 확정 사양
-------------------
- **비용 두 팔** — `US-실제`(수수료·거래세 0) vs `US-한국비용`(매수 0.14% · 매도 0.14% + 세금 0.2%).
  한국은 `KR-한국비용` 하나. 비용은 **하네스가 아니라 슬롯5 단계**에서 건다.
- 슬롯5 자산 중앙 · **200 seed 밴드** · 최대낙폭 · 체결 수 · 거래당 · 승률 — **전부 구간과 함께**.
- **leave-one-year 여섯 해 전부, 의존율로. 연도 이름을 미리 지목하지 않는다.**
- 🚨 **진입 수는 「연도 × 시장 × 유니버스 정규화」로만 낸다.** 원시 건수 비교는 넣지 않는다
  (두뇌 세션 결정 A — 미국 절대 건수는 많아도 유니버스로 나누면 뒤집힐 수 있다).
- 🚨 **판정 문장 금지.** 시장 간 거래당 MDE 가 2.02%p 라 이 팔은 판정력이 없다.
  판정은 2.5단계 절제가 낸다.

불확실성의 단위는 **자료**다(M10) — 거래당은 **날짜 블록 부트스트랩**(20~40거래일 · 1,000회)으로
구간을 낸다. 슬롯5 밴드는 seed 축이라 **다른 것**이며 둘을 섞어 쓰지 않는다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/28-headline.py
난수 seed: 슬롯 0~199 · 부트스트랩 280824
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
N_BOOT = 1000
BOOT_SEED = 280824
BLOCK = (20, 40)
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]

# 🚨 **비용은 「시장」이 아니라 「제도」다.** 두 시장의 거래 목록에 **같은 세 제도를 다 건다.**
#    (유형 18 짝 규칙 — 한쪽만 두 판이면 「미국이 낫다」가 제도 차이인지 방법 차이인지 못 가린다.)
# (매수 수수료, 매도 수수료+세금)
REGIMES = {
    # 미국 실제: 수수료 사실상 0 · 거래세 없음
    "무비용(미국 실제)": (0.0, 0.0),
    # 한국 우대수수료 — 사용자가 26-08-18부터 병행하는 신규 증권사(세금 0.2%만)
    "한국-우대(세금만)": (0.0, 0.0020),
    # 한국 미래에셋 — 매수 0.14% · 매도 0.14% + 세금 0.2%
    "한국-미래에셋": (0.0014, 0.0034),
}
# 🚨 **어느 것도 헤드라인으로 고르지 않는다.** 사용자는 두 증권사를 **병행**한다.
MARKETS = ("KR", "US")


def load_kr():
    ev, per = [], []
    for y in YEARS:
        f = BT / ("bt_%d.json" % y)
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        ev += d["events"]
        per += d.get("per_date") or []
    return ev, per


def load_us():
    f = BT / "sub" / "us_full.json"
    if not f.exists():
        return None, None
    d = json.loads(f.read_text(encoding="utf-8"))
    return d["events"], (d.get("per_date") or [])


def to_trades(events):
    """중복 제거는 (scan_date, code, pattern) 첫 등장. 미결착은 마지막 날짜로 결착 처리."""
    seen = set()
    out = []
    last = max((e.get("resolve_date") or e["entry_date"]) for e in events)
    for e in sorted(events, key=lambda x: (x["entry_date"], x["code"],
                                           x.get("pattern", ""))):
        k = (e["scan_date"], e["code"], e.get("pattern", ""))
        if k in seen:
            continue
        seen.add(k)
        g = e.get("gain_at_resolve_pct")
        if g is None:
            continue
        out.append({"code": e["code"], "scan_date": e["scan_date"],
                    "pattern": e.get("pattern", ""), "entry_date": e["entry_date"],
                    "resolve_date": e.get("resolve_date") or last,
                    "gain": g, "result": e["result"]})
    return out


class Cost:
    """`slot_sim.net` 은 모듈 전역을 읽는다 → 팔마다 바꿔 끼우고 되돌린다."""

    def __init__(self, buy, sell):
        self.b, self.s = buy, sell

    def __enter__(self):
        self.ob, self.os_ = slot_sim.FEE_BUY, slot_sim.FEE_SELL
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s
        return self

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.ob, self.os_


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[min(len(s) - 1, int(len(s) * hi / 100))]


def per_trade_boot(trades):
    """거래당 순수익의 **자료 축** 구간 — 진입일 블록 재추출."""
    byd = defaultdict(list)
    for t in trades:
        byd[t["entry_date"]].append(slot_sim.net(t["gain"]))
    dates = sorted(byd)
    n = len(dates)
    rnd = random.Random(BOOT_SEED)
    means = []
    for _ in range(N_BOOT):
        acc, cnt, tot = 0.0, 0, 0
        while tot < n:
            L = rnd.randint(*BLOCK)
            a = rnd.randint(0, max(0, n - L))
            for j in range(min(L, n - tot)):
                for v in byd[dates[a + j]] if a + j < n else ():
                    acc += v
                    cnt += 1
            tot += L
        means.append(acc / cnt if cnt else 0.0)
    obs = st.mean(slot_sim.net(t["gain"]) for t in trades)
    lo, hi = ci(means)
    return obs, lo, hi, st.pstdev(means)


def arm(label, trades, buy, sell):
    with Cost(buy, sell):
        b = slot_sim.band(trades, n_runs=N_SEED)
        obs, lo, hi, sd = per_trade_boot(trades)
        wins = sum(1 for t in trades if t["result"] == "win")
    r = {"label": label, "n_trades": len(trades),
         "equity_median": b["median"], "equity_p5": b["p5"], "equity_p95": b["p95"],
         "n_filled": b["n_filled"], "slot_win_rate": b["win_rate"], "mdd": b["mdd"],
         "per_trade": obs, "per_trade_lo": lo, "per_trade_hi": hi,
         "per_trade_mde": 2.80 * sd,
         "raw_win_rate": wins / len(trades) * 100 if trades else 0.0}
    print("  %-12s 거래 %6d · 체결 %6.0f · 슬롯5 자산 중앙 **%+9.2f%%** "
          "(5~95%% %+.1f ~ %+.1f) · MDD %.2f%%"
          % (label, r["n_trades"], r["n_filled"], r["equity_median"],
             r["equity_p5"], r["equity_p95"], r["mdd"]), flush=True)
    print("  %-12s 거래당 **%+.4f%%** (자료 축 95%% %+.4f ~ %+.4f · MDE %.4f%%p) · "
          "전수 승률 %.1f%% · 체결분 승률 %.1f%%"
          % ("", r["per_trade"], r["per_trade_lo"], r["per_trade_hi"],
             r["per_trade_mde"], r["raw_win_rate"], r["slot_win_rate"]), flush=True)
    return r


def loy(label, trades, buy, sell, full_eq):
    """leave-one-year — 의존율 = (전체 − 그 해를 뺀 값) / 전체."""
    out = {}
    with Cost(buy, sell):
        for y in YEARS:
            keep = [t for t in trades if int(t["entry_date"][:4]) != y]
            if not keep:
                continue
            m = slot_sim.band(keep, n_runs=N_SEED)["median"]
            out[str(y)] = {"equity": m,
                           "dependence_pct": ((1 - m / full_eq) * 100
                                              if full_eq else None)}
    return out


def norm_table(per, label):
    """🚨 결정 A — **깔때기**로 낸다. 비율 하나만 내면 «어디서 갈렸는지»를 못 본다.

    | 단계 | 지표 | 무엇을 말하나 |
    |---|---|---|
    | ① 상장 → 평가 | `n_eval / n_universe` | **시장 구조**(유동성·정지·시계열 길이) — 3-D 항목 |
    | ② 평가 → 후보 | `n_candidates / n_eval` | 관문+검출기가 얼마나 자주 통과시키나 |
    | ③ 후보 → 진입 | `진입 / n_candidates` | 피벗이 실제로 뚫리는 비율 |
    | (전체) | `진입 / n_eval` | **주지표** |

    ②가 다르면 **추세 종목의 밀도 차이**, ③이 다르면 **변동성·갭 구조 차이**다.
    두 뜻이 완전히 다르므로 하나로 뭉치지 않는다.

    주지표 분모는 **`n_eval`**(두뇌 세션 확정) — 하네스는 그 안에서만 산다.
    ⚠️ 다만 `n_eval` 은 유동성 문턱을 통해 **환율 환산에 의존**한다.
       `n_universe` 판에는 그 의존이 **없다**. **두 열이 같은 방향이면
       환산이 답을 만든 게 아님이 자동 증명된다**(등가중 벤치마크와 같은 구조).
    """
    y = defaultdict(lambda: {"d": 0, "u": 0, "e": 0, "c": 0, "en": 0})
    for p in per:
        k = p["scan_date"][:4]
        r = y[k]
        r["d"] += 1
        r["u"] += p.get("n_universe") or 0
        r["e"] += p.get("n_eval") or 0
        r["c"] += p.get("n_candidates") or 0
        r["en"] += p.get("n_entered") or 0
    print("", flush=True)
    print("  [%s] 깔때기 — 연도별" % label, flush=True)
    print("   %-6s %6s %8s %8s %8s %8s | %7s %7s %7s | %10s %10s"
          % ("연도", "거래일", "유니버스", "평가", "후보", "진입",
             "①평가율", "②후보율", "③체결률",
             "진입/천평가", "진입/천유니"), flush=True)
    rows = {}
    tot = {"d": 0, "u": 0, "e": 0, "c": 0, "en": 0}
    for k in sorted(y):
        r = y[k]
        for kk in tot:
            tot[kk] += r[kk]
        rows[k] = _funnel_row(r)
        _print_row(k, r, rows[k])
    rows["_total"] = _funnel_row(tot)
    _print_row("전체", tot, rows["_total"])
    return rows


def _funnel_row(r):
    u = r["u"] / r["d"] if r["d"] else 0
    e = r["e"] / r["d"] if r["d"] else 0
    return {
        "days": r["d"], "universe_avg": u, "eval_avg": e,
        "candidates": r["c"], "entered": r["en"],
        # ① 상장 → 평가 : 시장 구조 (3-D)
        "stage1_eval_share_pct": (r["e"] / r["u"] * 100) if r["u"] else None,
        # ② 평가 → 후보 : 관문+검출기 통과 빈도
        "stage2_cand_per_eval_pct": (r["c"] / r["e"] * 100) if r["e"] else None,
        # ③ 후보 → 진입 : 피벗이 실제로 뚫리는 비율
        "stage3_fill_pct": (r["en"] / r["c"] * 100) if r["c"] else None,
        # 주지표 · 부지표
        "entered_per_1k_eval_day": (r["en"] / r["d"] / e * 1000) if (r["d"] and e) else None,
        "entered_per_1k_universe_day": (r["en"] / r["d"] / u * 1000) if (r["d"] and u) else None,
        "entered_per_day": (r["en"] / r["d"]) if r["d"] else None,
    }


def _print_row(k, r, f):
    def q(x, w=7, p=3):
        return ("%*.*f" % (w, p, x)) if x is not None else ("%*s" % (w, "-"))
    print("   %-6s %6d %8.0f %8.0f %8d %8d | %s %s %s | %s %s"
          % (k, r["d"], f["universe_avg"], f["eval_avg"], r["c"], r["en"],
             q(f["stage1_eval_share_pct"], 7, 2), q(f["stage2_cand_per_eval_pct"], 7, 3),
             q(f["stage3_fill_pct"], 7, 2),
             q(f["entered_per_1k_eval_day"], 10, 4),
             q(f["entered_per_1k_universe_day"], 10, 4)), flush=True)


def sub_dollar(events):
    """결정 6 — 미국 진입 중 **진입가 $1 미만** 건수. 0에 가까우면 무시하고 그 사실을 적는다."""
    n = sum(1 for e in events if (e.get("entry_price") or 0) < 1.0)
    return n, len(events)


def extreme_set():
    """결정 2(b) 민감도용 — 하루 |움직임| > 90%p 인 (종목, 날짜) 목록.
    미국은 G3′ ④ 잔차, 한국은 27번 감사(>100%p + 50~100%p 둘 다)."""
    kr, us = set(), set()
    for nm in ("27-kr-extreme-audit-100-inf.json", "27-kr-extreme-audit-50-100.json"):
        f = OUT / nm
        if f.exists():
            for h in json.loads(f.read_text(encoding="utf-8"))["hits"]:
                if abs(h["ret_pct"]) > 90:
                    kr.add((h["code"], h["date"]))
    f = OUT / "25-g3prime.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        for h in d.get("top") or []:
            us.add((h["code"], h["date"]))
    return kr, us


def drop_extreme(trades, ext):
    """보유 구간에 극단 종목-일이 든 거래를 뺀다."""
    by = {}
    for c, d in ext:
        by.setdefault(c, []).append(d)
    out, dropped = [], 0
    for t in trades:
        hit = any(t["entry_date"] <= d <= t["resolve_date"]
                  for d in by.get(t["code"], ()))
        if hit:
            dropped += 1
        else:
            out.append(t)
    return out, dropped


def main():
    kr_ev, kr_per = load_kr()
    us_ev, us_per = load_us()
    if us_ev is None:
        print("🚨 `.cache/bt5y/sub/us_full.json` 이 없다. 본 실행을 먼저 끝낸다.", flush=True)
        return
    kr = to_trades(kr_ev)
    us = to_trades(us_ev)
    print("한국 거래 %d · 미국 거래 %d" % (len(kr), len(us)), flush=True)
    res = {}

    print("\n" + "=" * 78, flush=True)
    print("슬롯5 · 200 seed 밴드 · 거래당(자료 축 구간)", flush=True)
    print("=" * 78, flush=True)
    trades = {"KR": kr, "US": us}
    for m in MARKETS:
        for rg, (fb, fs) in REGIMES.items():
            res["%s / %s" % (m, rg)] = arm("%s / %s" % (m, rg), trades[m], fb, fs)
        print("", flush=True)

    print("=" * 78, flush=True)
    print("비용 제도 차 — **같은 거래 목록에 제도만 바꾼 것이라 항등식이다**", flush=True)
    print("=" * 78, flush=True)
    print("  왕복 비용: 무비용 0.00% · 우대 0.20% · 미래에셋 0.48% (0.14+0.14+0.2)", flush=True)
    THEORY = {"한국-우대(세금만)": 0.20, "한국-미래에셋": 0.48}
    for m in MARKETS:
        a0 = res["%s / 무비용(미국 실제)" % m]
        for rg in ("한국-우대(세금만)", "한국-미래에셋"):
            b0 = res["%s / %s" % (m, rg)]
            got = a0["per_trade"] - b0["per_trade"]
            print("  %-3s 무비용 − %-14s : 거래당 %+.4f%%p (이론 %.2f%%p · 차이 %+.4f) · "
                  "자산 %+.2f%%p · 체결 %.0f vs %.0f %s"
                  % (m, rg, got, THEORY[rg], got - THEORY[rg],
                     a0["equity_median"] - b0["equity_median"],
                     a0["n_filled"], b0["n_filled"],
                     "**일치**" if a0["n_filled"] == b0["n_filled"]
                     else "🚨**불일치=구현오류**"), flush=True)
    print("  ⚠️ 거래당 차이는 **항등식이다 — 구간을 붙이지 않는다.** 이론값과 어긋나면 구현 오류다.", flush=True)
    print("  ⚠️ 미세한 차이의 출처: net() 은 (1+g)(1-매도)/(1+매수)-1 이라 **곱셈**이고 "
          "이론값은 덧셈 근사다. 수익률 g 가 0 이 아니면 그만큼 어긋난다.", flush=True)

    print("\n" + "=" * 78, flush=True)
    print("leave-one-year (의존율 %) — 연도를 미리 지목하지 않는다", flush=True)
    print("=" * 78, flush=True)
    lo = {}
    for m in MARKETS:
        for rg in REGIMES:
            k = "%s / %s" % (m, rg)
            c = REGIMES[rg]
            lo[k] = loy(k, trades[m], c[0], c[1], res[k]["equity_median"])
        print("  %-12s %s" % (k, " · ".join(
            "%s %+.0f%%" % (y, v["dependence_pct"]) for y, v in sorted(lo[k].items()))),
            flush=True)
    res["_loy"] = lo

    print("\n" + "=" * 78, flush=True)
    print("깔때기 — 상장→평가→후보→진입 (결정 A · 주지표 분모는 **n_eval**)", flush=True)
    print("=" * 78, flush=True)
    res["_norm_kr"] = norm_table(kr_per, "한국")
    res["_norm_us"] = norm_table(us_per, "미국")
    k, u = res["_norm_kr"]["_total"], res["_norm_us"]["_total"]
    print("", flush=True)
    print("  **두 시장 나란히 (전체 구간)**", flush=True)
    print("   %-22s %12s %12s %12s" % ("", "한국", "미국", "미국/한국"), flush=True)
    for lab, key, unit in (
            ("① 평가율(평가/유니버스)", "stage1_eval_share_pct", "%"),
            ("② 후보율(후보/평가)", "stage2_cand_per_eval_pct", "%"),
            ("③ 체결률(진입/후보)", "stage3_fill_pct", "%"),
            ("**주지표** 진입/천평가·일", "entered_per_1k_eval_day", ""),
            ("부지표 진입/천유니·일", "entered_per_1k_universe_day", "")):
        a, b = k.get(key), u.get(key)
        rat = (b / a) if (a and b) else None
        print("   %-22s %11.4f%s %11.4f%s %11s"
              % (lab, a or 0, unit, b or 0, unit,
                 ("%.3f배" % rat) if rat else "-"), flush=True)
    print("   ⚠️ ②가 갈리면 **추세 종목의 밀도 차이**, ③이 갈리면 **변동성·갭 구조 차이**다."
          " 뜻이 완전히 다르므로 하나로 뭉치지 않는다.", flush=True)
    print("   ⚠️ 주지표(n_eval)는 유동성 문턱을 통해 **환율 환산에 의존**한다."
          " 부지표(n_universe)에는 그 의존이 **없다** —"
          " **두 열이 같은 방향이면 환산이 답을 만든 게 아님이 자동 증명**된다.", flush=True)

    # ── 결정 6 · 결정 2(b) ────────────────────────────────────────────────
    print("", flush=True)
    print("=" * 78, flush=True)
    print("결정 6 · 결정 2(b)", flush=True)
    print("=" * 78, flush=True)
    n1, nt = sub_dollar(us_ev)
    print("  [결정 6] 미국 진입 중 **진입가 $1 미만: %d / %d = %.2f%%**"
          % (n1, nt, n1 / nt * 100 if nt else 0), flush=True)
    res["_sub_dollar_us"] = {"n": n1, "total": nt}
    kre, use = extreme_set()
    print("  [결정 2(b)] ±90%%p 넘는 종목-일 배제 민감도 — 한국 목록 %d · 미국 목록 %d"
          % (len(kre), len(use)), flush=True)
    for lab, tr, ext, cost in (
            ("KR / 한국-미래에셋", kr, kre, REGIMES["한국-미래에셋"]),
            ("US / 무비용(미국 실제)", us, use, REGIMES["무비용(미국 실제)"]),
            ("US / 한국-미래에셋", us, use, REGIMES["한국-미래에셋"])):
        kept, dropped = drop_extreme(tr, ext)
        if dropped == 0:
            print("    %-12s 배제된 거래 **0건** → 헤드라인 불변" % lab, flush=True)
            res.setdefault("_ex90", {})[lab] = {"dropped": 0, "equity": None}
            continue
        with Cost(*cost):
            m = slot_sim.band(kept, n_runs=N_SEED)["median"]
        print("    %-12s 배제 %d건 → 슬롯5 자산 중앙 %+.2f%% (원판 %+.2f%% · 차이 %+.2f%%p)"
              % (lab, dropped, m, res[lab]["equity_median"],
                 m - res[lab]["equity_median"]), flush=True)
        res.setdefault("_ex90", {})[lab] = {"dropped": dropped, "equity": m}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "28-headline.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/28-headline.json", flush=True)
    print("🚨 이 문서에 판정 문장을 쓰지 않는다 — 시장 간 거래당 MDE 2.02%p.", flush=True)


if __name__ == "__main__":
    main()

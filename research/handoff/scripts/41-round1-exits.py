# -*- coding: utf-8 -*-
"""41 — **1회차 · 청산 변형**. 헤드라인 `1a` 는 결과를 보기 «전»에 고정됐다.

변형 (두뇌 세션 사전 지정)
--------------------------
| | 손절 | 부분 익절 | 나머지 |
|---|---|---|---|
| **0회차** | −10% 전량 | 없음 | +20% 전량 |
| **1a (헤드라인)** | −8% | **+20%에 절반** | 본전 스톱 → **25일 저가 추격** |
| **1b** | −8% | **+25%에 절반** | 본전 스톱 → 25일 저가 추격 |
| **1c** | 없음 | 없음 | **−15% 고정 추격**(전량) |
| **1d** | **−6%** | +20%에 절반 | 본전 스톱 → 25일 저가 추격 |

🚨 **`1d` 는 해석이 하나로 정해지지 않았다.** 지시는 「1d — −6%」뿐이었다.
   **「1a 에서 손절만 −6% 로 바꾼 것」으로 읽었다**(변형족이 헤드라인에서 손잡이
   하나씩 돌리는 구조이므로). **「0회차에서 손절만 −6%」로 읽는 것도 가능하다.**
   **이 가정을 결과에 적는다.** 다른 뜻이었으면 다시 돌리면 된다.

규약 — 0회차와 «같은 것»을 쓴다 (짝 규칙)
------------------------------------------
- 모든 청산은 **그날 종가**로 잡는다. 목표가·손절가로 잡지 않는다.
  🚨 **0회차가 종가 규약이므로 변형만 지정가 체결로 잡으면 변형이 «공짜로» 좋아진다.**
  둘 다 종가라 **지정가 체결의 이득은 양쪽에서 똑같이 빠져 있다.**
- 수익률은 **소수 2자리**(하네스 `pivot_backtest.py:47` 규약).
- 돌파일(0번째) 특례·`ambiguous` 규약도 0회차 그대로.
- 추격선은 **그날 «이전»** 자료로만 만든다(당일 저가를 쓰면 룩어헤드).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/41-round1-exits.py
난수 seed: 슬롯 0~199 · 부트스트랩 410824
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

import importlib.util as _u                                   # noqa: E402
import slot_sim                                               # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402

_s = _u.spec_from_file_location("v39", HERE / "39-exit-variants.py")
v39 = _u.module_from_spec(_s)
_s.loader.exec_module(v39)

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
N_BOOT = 1000
BOOT_SEED = 410824
BLOCK = (20, 40)
TRAIL_WINDOW = 25
# 🚨 기본은 «옛 범위»다 — 바꾸면 지난 결과가 조용히 달라진다.
#    9년판은 `BT_Y0=2017` 로 «명시해서» 연다.
import os as _os
Y0 = int(_os.environ.get("BT_Y0", "2021"))
YEARS = tuple(range(Y0, 2027))
EXT_NAME = "uspath_ext.json" if Y0 == 2021 else "uspath_ext%d.json" % Y0
REGIMES = (("미국 실제(무비용)", 0.0, 0.0),
           ("한국-미래에셋", 0.0014, 0.0034))


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.o = (slot_sim.FEE_BUY, slot_sim.FEE_SELL)
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.o


# ─────────────────────────────────────────────────────────────────────────
# 청산 규칙 — 다리 목록을 낸다: [(청산일, 몫, 총수익%), ...]
# ─────────────────────────────────────────────────────────────────────────
TARGET_FILL = "close"        # "close" | "limit"   — limit = max(목표가, 시가)
STOP_FILL = "close"          # "close" | "market"  — market = min(선, 시가)
N_NO_OPEN = [0]              # 시가가 없어 종가로 되돌린 횟수 (0이 아니면 결과에 적는다)


def _mk(epx):
    def g(px):
        return round(px / epx * 100 - 100, 2)
    return g


def _open_px(p, i):
    o = p.get("o")
    if not o or i >= len(o) or o[i] is None:
        N_NO_OPEN[0] += 1
        return None
    return o[i]


def _tgt_gain(p, g, i, target_pct):
    """목표 다리의 체결 수익률.

    - `close` : 그날 종가 (하네스 규약 · **헤드라인**)
    - `limit` : **`max(목표가, 시가)`** — 지정가 매도는 그날 고가가 목표를 찍었으므로
      체결되고, **시가가 목표 위로 갭업했으면 «시가»에 체결된다.**
      🚨 처음엔 「목표가 정확히」로 만들었는데 **틀렸다**(2026-08-24 자기 정정).
         그건 지정가 전략의 **하한**이지 지정가 자체가 아니다.
    """
    c = p["c"][i]
    if TARGET_FILL != "limit":
        return g(c)
    T = p["entry_price"] * (1 + target_pct / 100)
    o = _open_px(p, i)
    return g(T if o is None else max(T, o))


def _stop_gain(p, g, i, line_pct):
    """손절·추격 다리의 체결 수익률.

    - `close`  : 그날 종가 (하네스 규약)
    - `market` : **`min(선, 시가)`** — 사용자는 손절을 **시장가**로 집행하므로
      선이 걸린 순간 나간다. **갭다운이면 시가에 나간다.**
      ⚠️ 종가 규약은 「방아쇠가 걸린 뒤 하루 종일 더 떨어지는 것을 그대로 맞는」 모형이다.
    """
    c = p["c"][i]
    if STOP_FILL != "market" or line_pct is None:
        return g(c)
    L = p["entry_price"] * (1 + line_pct / 100)
    o = _open_px(p, i)
    return g(L if o is None else min(L, o))


def resolve_v0(p, target=20.0, stop=10.0):
    """0회차 — 판정(날짜·승패)은 `39-exit-variants.resolve_base` 그대로, 체결가만 규약대로."""
    d, res, gain = v39.resolve_base(p, target, stop)
    epx = p["entry_price"]
    g = _mk(epx)
    i = p["d"].index(d) if d in p["d"] else len(p["c"]) - 1
    kind = {"win": "목표", "loss": "손절", "ambiguous": "예외", "unresolved": "미결"}[res]
    if kind == "목표":
        gain = _tgt_gain(p, g, i, target)
        lvl = target
    elif kind == "손절":
        gain = _stop_gain(p, g, i, -stop)
        lvl = -stop
    else:
        lvl = None                      # 예외·미결은 규약을 안 바꾼다
    return d, res, [(d, 1.0, gain)], res == "unresolved", [(kind, lvl, g(p["c"][i]))]


def _trail_stop(lows, j, floor_px):
    """그날 «이전» 최대 `TRAIL_WINDOW` 일의 저가 최솟값과 바닥 중 큰 값.

    🚨 `lows[j]`(당일)는 쓰지 않는다 — 쓰면 룩어헤드다.
    ⚠️ 경로는 진입일부터라 진입 «전» 저가는 없다. 있는 만큼만 쓴다(한계에 적는다).
    """
    a = max(0, j - TRAIL_WINDOW)
    seg = [x for x in lows[a:j] if x is not None]
    return max(floor_px, min(seg)) if seg else floor_px


def resolve_half_then_trail(p, stop=8.0, half_at=20.0, half=0.5):
    """1a / 1b / 1d — 고정 손절 → 목표에서 절반 → 본전 스톱 + 25일 저가 추격."""
    epx = p["entry_price"]
    g = _mk(epx)
    S, T = epx * (1 - stop / 100), epx * (1 + half_at / 100)
    h, l, c, d = p["h"], p["l"], p["c"], p["d"]
    n = len(c)
    for i in range(n):
        hit_t = h[i] is not None and h[i] >= T
        hit_s = l[i] is not None and l[i] <= S
        if i == 0:
            if hit_t and hit_s:
                return d[0], "ambiguous", [(d[0], 1.0, g(c[0]))], False, [("예외", None, g(c[0]))]
            if hit_s:
                return d[0], "ambiguous", [(d[0], 1.0, g(c[0]))], False, [("예외", -stop, g(c[0]))]
            if hit_t:
                return _phase2(p, g, i, half, d[i], _tgt_gain(p, g, i, half_at), half_at)
            continue
        if hit_t and hit_s:
            return d[i], "ambiguous", [(d[i], 1.0, g(c[i]))], False, [("예외", None, g(c[i]))]
        if hit_t:
            return _phase2(p, g, i, half, d[i], _tgt_gain(p, g, i, half_at), half_at)
        if hit_s:
            return (d[i], "loss", [(d[i], 1.0, _stop_gain(p, g, i, -stop))], False,
                    [("손절", -stop, g(c[i]))])
    return (d[n - 1], "unresolved", [(d[n - 1], 1.0, g(c[n - 1]))], True,
            [("미결", None, g(c[n - 1]))])


def _phase2(p, g, i, half, half_date, half_gain, half_at):
    """절반을 판 뒤 — 남은 몫은 **본전 스톱 + 25일 저가 추격**."""
    epx = p["entry_price"]
    l, c, d = p["l"], p["c"], p["d"]
    n = len(c)
    legs = [(half_date, half, half_gain)]
    ex = [("목표", half_at, g(c[i]))]
    for j in range(i + 1, n):
        s2 = _trail_stop(l, j, epx)          # 본전이 바닥 (내려가지 않는다)
        if l[j] is not None and l[j] <= s2:
            lvl = round(s2 / epx * 100 - 100, 2)
            legs.append((d[j], 1.0 - half, _stop_gain(p, g, j, lvl)))
            ex.append(("본전" if s2 <= epx else "추격", lvl, g(c[j])))
            return d[j], "win", legs, False, ex
    legs.append((d[n - 1], 1.0 - half, g(c[n - 1])))
    ex.append(("미결", None, g(c[n - 1])))
    return d[n - 1], "win", legs, True, ex    # 남은 절반이 «경로 끝»에서 끊겼다


def resolve_trail_only(p, trail=15.0):
    """1c — 부분 익절 없음. **고점 대비 −15% 추격** 전량."""
    epx = p["entry_price"]
    g = _mk(epx)
    h, l, c, d = p["h"], p["l"], p["c"], p["d"]
    n = len(c)
    peak = h[0] if h[0] is not None else epx
    for j in range(n):
        lvl_px = peak * (1 - trail / 100)
        lvl = round(lvl_px / epx * 100 - 100, 2)
        if j > 0:                            # 🚨 추격선은 «어제까지»의 고점으로
            if l[j] is not None and l[j] <= lvl_px:
                gg = _stop_gain(p, g, j, lvl)
                return (d[j], ("win" if gg > 0 else "loss"), [(d[j], 1.0, gg)], False,
                        [("추격", lvl, g(c[j]))])
        else:
            if l[0] is not None and l[0] <= lvl_px:
                return (d[0], "ambiguous", [(d[0], 1.0, g(c[0]))], False,
                        [("예외", lvl, g(c[0]))])
        if h[j] is not None:
            peak = max(peak, h[j])
    gg = g(c[n - 1])
    return d[n - 1], ("win" if gg > 0 else "loss"), [(d[n - 1], 1.0, gg)], True, [("미결", None, gg)]


VARIANTS = (
    ("0회차", lambda p: resolve_v0(p), "−10% 전량 / +20% 전량", True),
    ("1a", lambda p: resolve_half_then_trail(p, 8.0, 20.0), "−8% / +20% 절반 / 본전→25일추격", True),
    ("1b", lambda p: resolve_half_then_trail(p, 8.0, 25.0), "−8% / +25% 절반 / 본전→25일추격", True),
    ("1c", lambda p: resolve_trail_only(p, 15.0), "부분없음 / −15% 고정추격", False),
    ("1d", lambda p: resolve_half_then_trail(p, 6.0, 20.0), "−6% / +20% 절반 / 본전→25일추격", True),
)


# ─────────────────────────────────────────────────────────────────────────
def replay(paths_by_year, resolver):
    """`open_until` 재현 — 39번과 «같은» 규약. 슬롯은 마지막 다리까지 잡힌다."""
    ev, blocked = [], 0
    for y in YEARS:
        open_until = {}
        for p in paths_by_year.get(y, ()):
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blocked += 1
                continue
            rd, res, legs, at_end, ex = resolver(p)
            open_until[c] = rd or p["entry_date"]
            ev.append({"code": c, "scan_date": p["scan_date"], "pattern": p["pattern"],
                       "entry_date": p["entry_date"], "resolve_date": rd,
                       "legs": legs, "result": res, "year": y, "at_end": at_end,
                       "exits": ex})
    return ev, blocked


def per_trade(ev):
    """거래당 순수익 — 다리 몫으로 가중한다."""
    return [sum(fr * slot_sim.net(gn) for _d, fr, gn in e["legs"]) for e in ev]


def boot(ev):
    byd = defaultdict(list)
    for e, v in zip(ev, per_trade(ev)):
        byd[e["entry_date"]].append(v)
    dates = sorted(byd)
    n = len(dates)
    rnd = random.Random(BOOT_SEED)
    means = []
    for _ in range(N_BOOT):
        acc = cnt = tot = 0
        while tot < n:
            L = rnd.randint(*BLOCK)
            a = rnd.randint(0, max(0, n - L))
            for j in range(min(L, n - tot)):
                v = byd[dates[a + j]]
                acc += sum(v)
                cnt += len(v)
            tot += L
        means.append(acc / cnt if cnt else 0.0)
    means.sort()
    return (means[int(N_BOOT * .025)], means[int(N_BOOT * .975)],
            2.80 * st.pstdev(means))


def limits(paths_by_year, ev):
    """🚨 **끊긴 이유를 갈라 센다.**

    ① **250일 상한** — 우리가 경로를 250거래일에서 잘라서 끊겼다 (**없앨 수 있는 한계**)
    ② **자료 끝**   — 그 해 하네스가 본 마지막 날까지 갔다 (**어쩔 수 없는 한계**)
    연장(`40-extend-cap-paths.py`)한 경로는 ②다.
    「끊겼는가」는 **추론하지 않고 해결자가 낸 `at_end` 를 쓴다.**
    """
    plen, isext = {}, {}
    for ps in paths_by_year.values():
        for p in ps:
            k = (p["scan_date"], p["code"], p["pattern"])
            plen[k] = len(p["c"])
            isext[k] = "_ext_from" in p
    cap, dend, ug = 0, 0, []
    for e in ev:
        if not e.get("at_end"):
            continue
        k = (e["scan_date"], e["code"], e["pattern"])
        if isext.get(k) or plen.get(k, 0) < v39.CAP_DAYS:
            dend += 1
        else:
            cap += 1
        ug.append(sum(fr * gn for _d, fr, gn in e["legs"]))
    return {"cap": cap, "data_end": dend, "n": len(ev),
            "cap_pct": cap / len(ev) * 100 if ev else 0.0,
            "at_end_pct": (cap + dend) / len(ev) * 100 if ev else 0.0,
            "unreal_median": st.median(ug) if ug else None}


def gap_table(ev):
    """🚨 **방아쇠선 대비 종가 이격** — 청산 종류별로.

    「아래로 찍어 나가는 청산은 그날이 하락일이라 종가가 방아쇠선보다 더 아래」가
    **얼마인지**를 잰다. **한계에 적는 데서 멈추지 않고 크기를 낸다.**
    이격 = 종가수익률 − 방아쇠선수익률 (음수 = 종가가 방아쇠선보다 아래)
    """
    from collections import defaultdict
    g = defaultdict(list)
    for e_ in ev:
        for kind, lvl, close_g in e_.get("exits", ()):
            if lvl is None:
                continue
            g[kind].append(close_g - lvl)
    out = {}
    for k, v in g.items():
        v.sort()
        n = len(v)
        out[k] = {"n": n, "median": v[n // 2], "p10": v[n // 10], "p90": v[9 * n // 10],
                  "mean": st.mean(v), "min": v[0], "max": v[-1]}
    return out


def run_combo(by, ft, fs, sizing):
    """한 조합(체결 규약 × 칸 크기 규약)을 통째로 돈다."""
    global TARGET_FILL, STOP_FILL
    TARGET_FILL, STOP_FILL = ft, fs
    N_NO_OPEN[0] = 0
    res = {}
    for name, fn, label, has_target in VARIANTS:
        ev, blocked = replay(by, fn)
        row = {"label": label, "n": len(ev), "blocked": blocked,
               "limits": limits(by, ev), "gaps": gap_table(ev),
               "has_target": has_target, "arms": {}}
        if name == "0회차" and ft == "close" and fs == "close" and sizing == "canon":
            bad = sf.gate_vs_canon(ev, n_seed=20)
            row["gate"] = "통과" if not bad else str(bad[:3])
            print("  🚨 **양방향 관문**(분할 시뮬 vs 정본, seed 0~19): %s"
                  % ("**통과 — 20 seed 전부 동일**" if not bad else "**미통과** %s" % bad[:3]),
                  flush=True)
            if bad:
                return None
        for rname, fb, fs_ in REGIMES:
            with Cost(fb, fs_):
                b = sf.band(ev, n_runs=N_SEED, sizing=sizing)
                m = st.mean(per_trade(ev))
                lo, hi, mde = boot(ev)
            row["arms"][rname] = {
                "equity_median": b["median"], "p5": b["p5"], "p95": b["p95"],
                "mdd": b["mdd"], "n_filled": b["n_filled"], "win_rate": b["win_rate"],
                "money_win_rate": b["money_win_rate"], "per_trade": m,
                "pt_lo": lo, "pt_hi": hi, "pt_mde": mde,
                "arith_pred": b["n_filled"] * 0.20 * m}
        res[name] = row
    return res


# 체결 규약 네 판 + 정본 연속성 한 판.
# 🚨 승·패가 «반대로» 당기므로 ①②를 갈라 낸다 — 합치면 상쇄돼 안 보인다
#    (한국 3,776건: 승 쪽만 −0.069%p · 패 쪽만 +0.132%p · 둘 다 +0.062%p).
COMBOS = (
    ("cash", "close", "close", "종가판", "**헤드라인** · 0회차와 짝 · 사전등록 보존"),
    ("cash", "limit", "close", "① 목표만 지정가", "승 쪽 효과 — max(목표가, 시가)"),
    ("cash", "close", "market", "② 손절·추격만 시장가", "패 쪽 효과 — min(선, 시가)"),
    ("cash", "limit", "market", "③ 실집행 근사판", "**사용자가 실제로 하는 것**"),
    ("canon", "close", "close", "정본 크기 · 종가", "옛 결과와의 연속성"),
)


def main() -> int:
    by, miss = v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    idx = json.loads((OUT / "38-indices.json").read_text(encoding="utf-8"))
    eqw = json.loads((OUT / "26-eqw-us.json").read_text(encoding="utf-8"))

    R = {}
    for sizing, ft, fs, tag, note in COMBOS:
        print("", flush=True)
        print("#" * 92, flush=True)
        print("# %s  (%s)" % (tag, note), flush=True)
        print("#   칸 크기 = %s · 목표 = %s · 손절·추격 = %s"
              % ("min(자산/5, 가용현금/빈칸)" if sizing == "cash" else "자산/5",
                 "그날 종가" if ft == "close" else "**max(목표가, 시가)**",
                 "그날 종가" if fs == "close" else "**min(선, 시가)**"), flush=True)
        print("#" * 92, flush=True)
        r = run_combo(by, ft, fs, sizing)
        if r is None:
            print("  → 분할 시뮬을 쓸 수 없다. 중단한다.", flush=True)
            return 1
        R["%s|%s|%s" % (sizing, ft, fs)] = r
        if N_NO_OPEN[0]:
            print("  ⚠️ 시가가 없어 종가로 되돌린 횟수 **%d** — 0이 아니면 결과에 적는다"
                  % N_NO_OPEN[0], flush=True)
        for name, _f, label, has_t in VARIANTS:
            row = r[name]
            a0 = row["arms"][REGIMES[0][0]]
            a1 = row["arms"][REGIMES[1][0]]
            print("  %-6s 체결 %5.0f · 무비용 %+8.2f%% (%+7.2f ~ %+7.2f) MDD %6.2f%% · "
                  "한국 %+8.2f%% · 거래당 %+.4f%%"
                  % (name, a0["n_filled"], a0["equity_median"], a0["p5"], a0["p95"],
                     a0["mdd"], a1["equity_median"], a0["per_trade"]), flush=True)

    # ── 🚨 암묵적 레버리지의 값 ──────────────────────────────────────────
    print("", flush=True)
    print("=" * 92, flush=True)
    print("🚨 **암묵적 레버리지의 값** = 정본판 − 현금제약판 (같은 체결 규약끼리)", flush=True)
    print("=" * 92, flush=True)
    print("  %-8s %-6s %14s %14s %12s"
          % ("비용", "변형", "현금제약(집행가능)", "정본(없는돈)", "차이"), flush=True)
    for rname, _a, _b in REGIMES:
        for name, _f, _l, _h in VARIANTS:
            c = R["cash|close|close"][name]["arms"][rname]["equity_median"]
            k = R["canon|close|close"][name]["arms"][rname]["equity_median"]
            print("  %-8s %-6s %+13.2f%% %+13.2f%% %+11.2f%%p"
                  % (rname[:6], name, c, k, k - c), flush=True)
    print("  ⚠️ 차이가 **양수면 「없는 돈」이 성적을 부풀렸다**는 뜻이다.", flush=True)

    # ── 이격 표 ──────────────────────────────────────────────────────────
    print("", flush=True)
    print("=" * 92, flush=True)
    print("🚨 방아쇠선 대비 **종가 이격** — 「추격이 더 깎이는가」의 크기", flush=True)
    print("=" * 92, flush=True)
    print("  %-6s %-6s %7s %9s %9s %9s %9s"
          % ("변형", "종류", "n", "중앙", "평균", "P10", "P90"), flush=True)
    for name, _f, _l, _h in VARIANTS:
        for kind in ("목표", "손절", "추격", "본전", "예외"):
            g = R["cash|close|close"][name]["gaps"].get(kind)
            if not g:
                continue
            print("  %-6s %-6s %7d %+8.2f%% %+8.2f%% %+8.2f%% %+8.2f%%"
                  % (name, kind, g["n"], g["median"], g["mean"], g["p10"], g["p90"]),
                  flush=True)
    print("  ⚠️ 음수 = **종가가 방아쇠선보다 아래**. "
          "「가운데가 치우쳤나」와 「꼬리가 두꺼운가」를 갈라 본다.", flush=True)

    # ── 분해 (헤드라인 조합) ─────────────────────────────────────────────
    H = R["cash|close|close"]
    print("", flush=True)
    print("=" * 92, flush=True)
    print("분해 — 산술 예측 vs 관측 (무비용 팔 · **헤드라인 = 현금제약·종가**)", flush=True)
    print("=" * 92, flush=True)
    print("  %-8s %8s %11s %12s %12s %12s"
          % ("변형", "체결", "거래당", "산술 예측", "관측", "**격차**"), flush=True)
    for name, _f, _l, _h in VARIANTS:
        a = H[name]["arms"][REGIMES[0][0]]
        print("  %-8s %8.0f %10.4f%% %11.2f%% %11.2f%% %11.2f%%p"
              % (name, a["n_filled"], a["per_trade"], a["arith_pred"],
                 a["equity_median"], a["equity_median"] - a["arith_pred"]), flush=True)
    print("  ⚠️ 산술 예측은 **칸 크기 20%%를 가정**한다. 현금제약판은 칸이 더 작을 수 있어"
          " **예측 자체가 위로 치우친다**(격차의 일부는 그 탓이다).", flush=True)

    # ── 문턱 ─────────────────────────────────────────────────────────────
    lo_d, hi_d = "2021-02-01", "2026-08-21"
    bm = {}
    for sym in ("US500", "IXIC"):
        ks = sorted(k for k in idx[sym] if lo_d <= k <= hi_d)
        bm[sym] = (idx[sym][ks[-1]] / idx[sym][ks[0]] - 1) * 100
    hr = (eqw.get("ladder", {}) or {}).get("harness", {}) or {}
    for kk in ("filt_daily", "filt_bh", "all_daily", "all_bh"):
        bm["등가중:" + kk] = hr.get(kk)
    print("", flush=True)
    print("=" * 92, flush=True)
    print("두 문턱 — 본전(자산 5%% 하단 > 0) · **시장 = S&P500 %+.2f%%**" % bm["US500"], flush=True)
    print("=" * 92, flush=True)
    print("  나스닥 %+.2f%% · 등가중 4판 %s" % (bm["IXIC"], " · ".join(
        "%s %+.2f%%" % (k.split(":")[1], v) for k, v in bm.items()
        if k.startswith("등가중:") and v is not None)), flush=True)
    print("  ⚠️ 등가중은 **130배 벌어져 문턱이 못 된다**. 전부 싣되 문턱은 S&P500 하나.",
          flush=True)
    print("  ⚠️ **S&P500 은 시총가중 대형주 · 우리는 중소형 다섯 칸** — "
          "«귀속»이 아니라 **「이 돈으로 이게 최선이었나」의 잣대**다.", flush=True)
    for sizing, ft, fs, tag, _n in COMBOS:
        print("  [%s]" % tag, flush=True)
        for rname, _a, _b in REGIMES:
            for name, _f, _l, _h in VARIANTS:
                a = R["%s|%s|%s" % (sizing, ft, fs)][name]["arms"][rname]
                print("    %-8s %-6s 자산 %+8.2f%% (하단 %+8.2f%%) → 본전 %s · 시장 %s"
                      % (rname[:6], name, a["equity_median"], a["p5"],
                         "**통과**" if a["p5"] > 0 else "미통과",
                         "**통과**" if a["p5"] > bm["US500"] else "미통과"), flush=True)

    # ── 증분·누적 ────────────────────────────────────────────────────────
    print("", flush=True)
    print("=" * 92, flush=True)
    print("0회차 대비 — 증분과 누적 · **다섯 조합 나란히**", flush=True)
    print("=" * 92, flush=True)
    for rname, _a, _b in REGIMES:
        print("  [%s]" % rname, flush=True)
        print("    %-6s %-22s %-22s %-22s %-22s %-22s"
              % ("변형", "종가판(헤드라인)", "①목표만", "②손절·추격만", "③실집행", "정본크기"),
              flush=True)
        for name, _f, _l, _h in VARIANTS:
            cells = []
            for sizing, ft, fs, _tg, _nt in COMBOS:
                k = "%s|%s|%s" % (sizing, ft, fs)
                v = R[k][name]["arms"][rname]["equity_median"]
                b0 = R[k]["0회차"]["arms"][rname]["equity_median"]
                cells.append("%+.2f (%+.2f%%p)" % (v, v - b0))
            print("    %-6s %-22s %-22s %-22s %-22s %-22s" % (name, *cells), flush=True)
    print("  ⚠️ **증분은 자산 중앙끼리의 차이지 짝비교가 아니다.**", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "41-round1.json").write_text(
        json.dumps({"combos": R, "benchmark": bm, "window": [lo_d, hi_d]},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/41-round1.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

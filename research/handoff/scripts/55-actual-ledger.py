# -*- coding: utf-8 -*-
"""55번 — **실제 장부: 재량 vs 규칙**. 사전등록: `tasks/55-actual-ledger.md`

정산표 왕복 63건에 **+20% / −10% 규칙을 다시 태운다.** 종목·진입일·진입가는 그대로 두고
청산만 규칙으로 바꾼다 → **「재량과 규칙이 달랐나」**를 짝비교로 잰다.

🚨 `scorecard-fills.json` 은 «읽지도» 않는다. `scorecard.json` 의 `trades` 만 읽는다.
"""
from __future__ import annotations

import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PDATA = ROOT / ".cache" / "pdata"
OUT = ROOT / ".cache" / "bt5y" / "out"

TARGET = 20.0
STOP = -10.0
FEE_BUY = 0.0014          # 미래에셋 관행 (장부 net 과 맞추는 용도)
FEE_SELL = 0.0014 + 0.002
N_BOOT = 2000
BOOT_SEED = 550825


# ─────────────────────────────────────────────────────────────────────────
def load_days(lo, hi):
    """[lo, hi] 사이 pdata 일봉을 code -> [(날짜, o,h,l,c)] 로."""
    files = sorted(p for p in PDATA.glob("price_*.json")
                   if lo <= p.stem[6:] <= hi)
    by = defaultdict(list)
    cap, ks = {}, {}
    for p in files:
        d = p.stem[6:]
        day = json.loads(p.read_text(encoding="utf-8"))
        tot = 0.0
        for code, r in day.items():
            try:
                o, h, l, c = (float(r["mkp"]), float(r["hipr"]),
                              float(r["lopr"]), float(r["clpr"]))
            except (KeyError, TypeError, ValueError):
                continue
            if c <= 0:
                continue
            by[code].append((d, o, h, l, c))
            if r.get("mrktCtg") == "KOSPI":
                tot += float(r.get("mrktTotAmt") or 0.0)
                ks.setdefault(d, {})[code] = c
        cap[d] = tot
    return by, cap, ks


def replay(bars, i0, entry, fill):
    """진입 다음 봉부터 +20 / −10 결착. fill: 'line' | 'market'

    반환 (총수익%, 결착일, 사유)  — 끝까지 안 끝나면 마지막 종가로 평가.
    """
    tgt = entry * (1 + TARGET / 100)
    stp = entry * (1 + STOP / 100)
    for j in range(i0, len(bars)):
        d, o, h, l, c = bars[j]
        # 🚨 손절을 먼저 본다 — 같은 날 둘 다 닿으면 «나쁜 쪽»을 택한다(보수적)
        if l <= stp:
            px = min(stp, o) if fill == "market" else stp
            return (px / entry - 1) * 100, d, "stop"
        if h >= tgt:
            px = max(tgt, o) if fill == "market" else tgt
            return (px / entry - 1) * 100, d, "target"
    d, _o, _h, _l, c = bars[-1]
    return (c / entry - 1) * 100, d, "open"


def net_of(gross):
    return (1 + gross / 100) * (1 - FEE_SELL) / (1 + FEE_BUY) * 100 - 100


def boot_ci(pairs, keys):
    """블록 부트스트랩 — `open_date` 로 묶는다."""
    byk = defaultdict(list)
    for v, k in zip(pairs, keys):
        byk[k].append(v)
    ks = sorted(byk)
    rnd = random.Random(BOOT_SEED)
    ms = []
    for _ in range(N_BOOT):
        pick = [rnd.choice(ks) for _ in ks]
        vals = [v for k in pick for v in byk[k]]
        ms.append(st.mean(vals))
    ms.sort()
    lo, hi = ms[int(N_BOOT * .025)], ms[int(N_BOOT * .975)]
    return lo, hi, (hi - lo) / 2


# ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    sc = json.loads((ROOT / "public" / "data" / "scorecard.json")
                    .read_text(encoding="utf-8"))
    tr = sc["trades"]
    op = sc["open_positions"]
    # ── 진입 원칙 준수로 가른다 (사용자 고지 26-08-25: 63건은 공부하며 한 매매라 오염) ──
    #   🚨 `setup` 은 **매수 체결 시점에 장부에 적힌** 라벨이라 결과와 무관하다.
    #   🚨 `stop_violation` 은 «쓰지 않는다» — 손절선을 어겼다 = 크게 잃었다 이므로 순환이다.
    import os as _os
    ONLY = _os.environ.get("SETUP_ONLY") == "1"
    if ONLY:
        tr = [t for t in tr if t.get("setup")]
        op = [o for o in op if o.get("setup")]
        print("🔎 **셋업 있는 진입만** (%d건) — 진입 원칙 준수 부분집합" % len(tr),
              flush=True)
    lo = min(t["open_date"] for t in tr).replace("-", "")
    hi = "20260821"
    bars, cap, ks = load_days(lo, hi)

    print("=" * 74, flush=True)
    print("55번 — **실제 장부: 재량 vs 규칙** (사전등록 tasks/55)", flush=True)
    print("=" * 74, flush=True)
    print("왕복 **%d건** · 미청산 %d건 · 창 %s ~ 2026-08-21"
          % (len(tr), len(op), min(t["open_date"] for t in tr)), flush=True)

    # ── D. 지수 대용 ────────────────────────────────────────────────────
    ds = sorted(cap)
    kospi = (cap[ds[-1]] / cap[ds[0]] - 1) * 100
    a0, a1 = ks[ds[0]], ks[ds[-1]]
    com = [c for c in a0 if c in a1 and a0[c] > 0]
    rr = sorted(a1[c] / a0[c] - 1 for c in com)
    eqw = st.mean(rr) * 100
    med = rr[len(rr) // 2] * 100
    print("KOSPI 대용 같은 창 — **시총가중 %+.2f%%** · 등가중 %+.2f%% · "
          "**종목 중앙 %+.2f%%** (%d 거래일 · %d종목)"
          % (kospi, eqw, med, len(ds), len(com)), flush=True)
    print("  🚨 **시총가중과 중앙이 %.1f%%p 벌어진다** — 대형주만 빠진 장이다. "
          "사용자는 중소형을 사므로 **중앙 쪽이 맞는 대조다.**"
          % abs(kospi - med), flush=True)

    # ── A. 서술 ─────────────────────────────────────────────────────────
    print("\n" + "─" * 74, flush=True)
    print("A. **실제 청산이 어디에 떨어지나** — 세는 것, 문턱 없음", flush=True)
    wins = [t for t in tr if t["outcome"] == "win"]
    loss = [t for t in tr if t["outcome"] == "loss"]

    def near(xs, line, tol=2.0):
        return sum(1 for t in xs if abs(t["net_pct"] - line) <= tol)

    print("  승 %d건 — net 중앙 **%+.2f%%** · 최대 %+.2f%% · "
          "**목표 +20%% ±2%%p 안 %d건 (%.1f%%)**"
          % (len(wins), st.median(t["net_pct"] for t in wins),
             max(t["net_pct"] for t in wins), near(wins, 20.0),
             100.0 * near(wins, 20.0) / len(wins)), flush=True)
    print("  패 %d건 — net 중앙 **%+.2f%%** · 최소 %+.2f%% · "
          "**손절 −10%% ±2%%p 안 %d건 (%.1f%%)**"
          % (len(loss), st.median(t["net_pct"] for t in loss),
             min(t["net_pct"] for t in loss), near(loss, -10.0),
             100.0 * near(loss, -10.0) / len(loss)), flush=True)
    over = [t for t in wins if t["net_pct"] >= 18.0]
    print("  → 승 중 **+18%% 이상 %d건** · **+10%% 미만 %d건**"
          % (len(over), sum(1 for t in wins if t["net_pct"] < 10.0)), flush=True)
    print("  보유일 중앙 — 승 **%.0f일** · 패 **%.0f일**"
          % (st.median(t["hold_days"] for t in wins),
             st.median(t["hold_days"] for t in loss)), flush=True)

    # ── 관문 ────────────────────────────────────────────────────────────
    print("\n" + "─" * 74, flush=True)
    print("관문 — 진입가가 그날 봉 안에 들어오나", flush=True)
    rows, miss, outside, rebase = [], [], 0, []
    for t in tr:
        b = bars.get(t["code"])
        if not b:
            miss.append(t["code"])
            continue
        d0 = t["open_date"].replace("-", "")
        i = next((k for k, x in enumerate(b) if x[0] == d0), None)
        if i is None:
            miss.append(t["code"])
            continue
        # 🚨 `avg_buy` 는 «주당 평균단가»다 — 총액이 아니다.
        #    처음에 buy_qty 로 나눴다가 관문이 59/63 을 봉 밖으로 잡아냈다.
        entry = t["avg_buy"]
        _dd, _o, h, l, _c = b[i]
        if not (l * 0.97 <= entry <= h * 1.03):
            outside += 1
        # 🚨 pdata 는 «비수정주가»다 — 보유 구간에 제한폭(±30%)을 넘는 봉간 도약이
        #    있으면 분할·병합 재베이스일 수 있다. 세어서 적는다.
        seg = b[i:min(len(b), i + 60)]
        if any(seg[k + 1][4] / seg[k][4] - 1 > 0.45 or seg[k + 1][4] / seg[k][4] - 1 < -0.45
               for k in range(len(seg) - 1) if seg[k][4] > 0):
            rebase.append(t["code"])
        rows.append((t, b, i + 1, entry))
    print("  자료 없음 %d건 · 진입가가 봉 밖 **%d건** / %d건 · "
          "재베이스 의심 **%d건**"
          % (len(miss), outside, len(rows), len(set(rebase))), flush=True)
    if outside > len(rows) * 0.1:
        print("  🚨 관문 **미통과** — 진입가가 봉 밖인 것이 10%%를 넘는다. 멈춘다.",
              flush=True)
        return 3
    if miss:
        print("  자료 없는 종목: %s" % ", ".join(sorted(set(miss))[:8]), flush=True)

    # ── B. 짝비교 ───────────────────────────────────────────────────────
    print("\n" + "─" * 74, flush=True)
    print("B. **같은 63건에 규칙을 다시 태운다** — 짝비교", flush=True)
    RES = {"kospi_proxy": kospi, "n_trades": len(tr), "n_open": len(op),
           "gate_outside": outside, "gate_missing": len(miss), "arms": {}}
    for fill, flabel in (("line", "선 정확히 (달성 불가 낙관치)"),
                         ("market", "**실집행 근사** — 사용자가 실제로 하는 것")):
        diffs, keys, unres, rule_net = [], [], 0, []
        for t, b, i0, entry in rows:
            g, _rd, why = replay(b, i0, entry, fill)
            unres += (why == "open")
            rn = net_of(g)
            rule_net.append(rn)
            diffs.append(t["net_pct"] - rn)          # 재량 − 규칙
            keys.append(t["open_date"])
        m = st.mean(diffs)
        blo, bhi, mde = boot_ci(diffs, keys)
        pas = (blo > 0) or (bhi < 0)
        RES["arms"][fill] = {"label": flabel, "n": len(diffs),
                             "actual_mean": st.mean(t["net_pct"] for t, _b, _i, _e in rows),
                             "rule_mean": st.mean(rule_net),
                             "diff_mean": m, "ci_lo": blo, "ci_hi": bhi,
                             "mde": mde, "unresolved": unres,
                             "pass": pas}
        print("\n  [%s]" % flabel, flush=True)
        print("    재량 거래당 **%+.3f%%** · 규칙 거래당 **%+.3f%%** "
              "(미결착 %d건은 08-21 종가 평가)"
              % (RES["arms"][fill]["actual_mean"], st.mean(rule_net), unres),
              flush=True)
        print("    → **차이 %+.3f%%p** [95%% %+.3f ~ %+.3f] · **MDE ±%.3f%%p** → **%s**"
              % (m, blo, bhi, mde, "0 배제 — 가림" if pas else "0 포함 — **못 가림**"),
              flush=True)
        if not pas:
            print("    ⚠️ **미통과이므로 부호를 읽지 않는다**(사전등록 B2)", flush=True)

    # ── C. 감도 — 미청산 11건 포함 ──────────────────────────────────────
    print("\n" + "─" * 74, flush=True)
    print("C. 감도 — **미청산 %d건을 08-21 종가로 넣으면**" % len(op), flush=True)
    unreal = []
    for o in op:
        b = bars.get(o["code"])
        if not b:
            continue
        unreal.append(net_of((b[-1][4] / o["avg_buy"] - 1) * 100))
    allv = [t["net_pct"] for t, _b, _i, _e in rows] + unreal
    print("  미청산 %d건 평가 거래당 **%+.2f%%** (중앙 %+.2f%%)"
          % (len(unreal), st.mean(unreal), st.median(unreal)), flush=True)
    print("  청산분만 **%+.3f%%** → 미청산 포함 **%+.3f%%** — 부호 %s"
          % (st.mean(t["net_pct"] for t, _b, _i, _e in rows), st.mean(allv),
             "**유지**" if (st.mean(allv) < 0) == (
                 st.mean(t["net_pct"] for t, _b, _i, _e in rows) < 0)
             else "🚨 **바뀜 — 63건 결론 폐기**"), flush=True)
    RES["sens"] = {"n_open_priced": len(unreal),
                   "open_mean": st.mean(unreal) if unreal else None,
                   "closed_mean": st.mean(t["net_pct"] for t, _b, _i, _e in rows),
                   "all_mean": st.mean(allv)}
    RES["index"] = {"cap_weighted": kospi, "equal_weighted": eqw, "median": med}

    (OUT / "55-actual-ledger.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 55-actual-ledger.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

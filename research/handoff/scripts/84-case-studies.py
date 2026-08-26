# -*- coding: utf-8 -*-
"""84 — **여러 케이스로 걸어 보기** (사용자 요청, 83번 확장)

렌즈 넷 — **앞 둘은 «눈으로 보는 것»(n 작음), 뒤 둘은 «측정»(n 큼)**:
```
① 두 날 대조   2020-04 (폭락 직후 반등)  vs  2022-06 (하락장 한복판)   ← 실제 종목
② 최대 승자    9년 최대 승자 다섯 + 하나의 «일생»                      ← 실제 종목
③ 손절 뒤      「팔고 나면 그 종목은 어떻게 되나」                      ← n 큼 · 측정
④ 최고점 대비  「최고점의 몇 %를 챙기나」                               ← n 큼 · 측정
```
🚨 ①② 는 **검정이 아니다.** n 이 한 자리다. 숫자를 근거로 쓰지 않는다.
🚨 ③④ 는 n 이 크지만 **«서술»이지 «비교»가 아니다** — 대조군이 없다. 문턱도 없다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/84-case-studies.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r83", HERE / "83-mar15-walkthrough.py")
r83 = _u.module_from_spec(_s)
_s.loader.exec_module(r83)
r74, r41, pt = r83.r74, r83.r41, r83.pt

OUT = ROOT / ".cache" / "bt5y" / "out"
STOP, TARGET = r74.STOP, r74.TARGET
COST, SLOTS, RISK, CAP = r74.COST, r74.SLOTS, r74.RISK, r74.CAP
N_SEED = 200
AFTER = 60          # 손절 뒤 며칠을 볼 것인가


def gain_of(t):
    e = t["entry_px"]
    return sum(f * (px / e - 1) * 100 for _d, f, px in t["masks"][()]["exits"])


def load():
    by2, _a, _b, _c = r74.load_filtered()
    ev, blk, _sp = r74.replay_masks(by2, (1.0,), "floor_entry")
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by2.values() for p in ps}
    return by2, ev, blk, pmap


# ═════════════════════════════════════════════════════════════════════════
def lens1(ev, pmap, fills):
    print("\n" + "=" * 98, flush=True)
    print("【렌즈 ①】 **같은 규칙 · 다른 장세** — 실제 종목으로 (🚨 n 작음 · 검정 아님)", flush=True)
    print("=" * 98, flush=True)
    for label, ym, note in (("폭락 직후 반등", "2020-04",
                             "지수 200일선 필터를 걸었다면 «이 달을 통째로 막았다»"),
                            ("하락장 한복판", "2022-06",
                             "가짜 반등이 반복되던 구간 — 방법이 가장 약한 곳")):
        got = [t for t in ev if t["entry_date"].startswith(ym)]
        got.sort(key=lambda t: t["entry_date"])
        print("\n" + "─" * 98, flush=True)
        print("▶ **%s (%s)** — 진입 %d건   · %s" % (label, ym, len(got), note), flush=True)
        if not got:
            continue
        gs = [gain_of(t) for t in got]
        w = sum(1 for g in gs if g > 0)
        print("   %-7s %-6s %-11s %11s %9s %8s %s"
              % ("종목", "패턴", "진입일", "결과", "보유", "체결률", "최고점"), flush=True)
        print("   " + "-" * 76, flush=True)
        for t in got[:14]:
            p = pmap[(t["scan_date"], t["code"], t["pattern"])]
            m = t["masks"][()]
            i0 = p["d"].index(t["entry_date"])
            i1 = p["d"].index(m["exits"][-1][0])
            mfe = (max(p["h"][i0:i1 + 1]) / t["entry_px"] - 1) * 100
            fr = fills.get((t["scan_date"], t["code"], t["pattern"]), 0)
            print("   %-7s %-6s %-11s %+10.2f%% %7d일 %7.1f%% %+8.1f%%"
                  % (t["code"], t["pattern"], t["entry_date"], gain_of(t), i1 - i0 + 1,
                     100.0 * fr / N_SEED, mfe), flush=True)
        if len(got) > 14:
            print("   … 외 %d건" % (len(got) - 14), flush=True)
        print("   ⇒ **%d건 중 %d건 이익 (%.0f%%)** · 거래당 평균 **%+.2f%%** · 중앙 %+.2f%%"
              % (len(gs), w, 100.0 * w / len(gs), st.mean(gs), st.median(gs)), flush=True)


# ═════════════════════════════════════════════════════════════════════════
def lens2(ev, pmap, fills):
    print("\n" + "=" * 98, flush=True)
    print("【렌즈 ②】 **9년 최대 승자** — 「대박은 어떻게 생겼나」 (🚨 n 작음 · 꼬리다)",
          flush=True)
    print("=" * 98, flush=True)
    top = sorted(ev, key=gain_of, reverse=True)[:6]
    print("   %-7s %-6s %-11s %11s %9s %8s"
          % ("종목", "패턴", "진입일", "결과", "보유", "체결률"), flush=True)
    print("   " + "-" * 66, flush=True)
    for t in top:
        p = pmap[(t["scan_date"], t["code"], t["pattern"])]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(t["masks"][()]["exits"][-1][0])
        fr = fills.get((t["scan_date"], t["code"], t["pattern"]), 0)
        print("   %-7s %-6s %-11s %+10.2f%% %7d일 %7.1f%%"
              % (t["code"], t["pattern"], t["entry_date"], gain_of(t), i1 - i0 + 1,
                 100.0 * fr / N_SEED), flush=True)
    base = [fills.get((t["scan_date"], t["code"], t["pattern"]), 0) / N_SEED for t in ev]
    top30 = [fills.get((t["scan_date"], t["code"], t["pattern"]), 0) / N_SEED
             for t in sorted(ev, key=gain_of, reverse=True)[:30]]
    bot30 = [fills.get((t["scan_date"], t["code"], t["pattern"]), 0) / N_SEED
             for t in sorted(ev, key=gain_of)[:30]]
    print(chr(10) + "   🚨 **체결률을 «기준선 없이» 읽으면 안 된다** — "
          "최대 승자가 0%인 건 특별한 게 아니다:", flush=True)
    print("      전체 %d건  평균 **%.1f%%** · **0%%인 거래가 %.1f%%**  (5칸으로는 대부분 못 산다)"
          % (len(base), 100 * st.mean(base),
             100.0 * sum(1 for x in base if x == 0) / len(base)), flush=True)
    print("      상위 30 승자 평균 %.1f%% · 하위 30 패자 평균 %.1f%%  → "
          "**승자를 «골라서» 놓치는 게 아니다**"
          % (100 * st.mean(top30), 100 * st.mean(bot30)), flush=True)
    gs = sorted((gain_of(t) for t in ev), reverse=True)
    tot = sum(g for g in gs)
    print("\n   🚨 **꼬리가 전부다** — 위 %d건이 «거래 %d건 전체 합»의 **%.1f%%**"
          % (len(top), len(gs), 100.0 * sum(gs[:len(top)]) / tot if tot else 0), flush=True)
    print("      상위 1%%(%d건)가 **%.1f%%** · 상위 5%%가 **%.1f%%**"
          % (len(gs) // 100, 100.0 * sum(gs[:len(gs) // 100]) / tot,
             100.0 * sum(gs[:len(gs) // 20]) / tot), flush=True)
    t = top[0]
    r83.show_trade(pmap[(t["scan_date"], t["code"], t["pattern"])], t, tag=" ← 9년 최대")


# ═════════════════════════════════════════════════════════════════════════
def lens3(ev, pmap):
    print("\n" + "=" * 98, flush=True)
    print("【렌즈 ③】 **손절하고 나면 그 종목은 어떻게 되나** (측정 · n 큼)", flush=True)
    print("=" * 98, flush=True)
    print("   🚨 «서술»이다 — 대조군도 문턱도 없다. 「손절이 옳았나」를 «판정»하지 않는다.",
          flush=True)
    back, n_short = [], 0
    for t in ev:
        m = t["masks"][()]
        if gain_of(t) > -STOP + 0.5:
            continue                        # 손절이 아닌 것
        p = pmap[(t["scan_date"], t["code"], t["pattern"])]
        j = p["d"].index(m["exits"][-1][0])
        seg = p["c"][j + 1:j + 1 + AFTER]
        hi = p["h"][j + 1:j + 1 + AFTER]
        if len(seg) < 20:
            n_short += 1
            continue
        px = m["exits"][-1][2]
        back.append({"code": t["code"], "n": len(seg),
                     "end": (seg[-1] / px - 1) * 100,
                     "peak": (max(hi) / px - 1) * 100,
                     "recover": (max(hi) / t["entry_px"] - 1) * 100})
    n = len(back)
    ends = sorted(x["end"] for x in back)
    peaks = sorted(x["peak"] for x in back)
    print("\n   손절 **%d건** 중 이후 %d거래일 자료가 충분한 **%d건** (짧아서 뺀 것 %d건)"
          % (sum(1 for t in ev if gain_of(t) <= -STOP + 0.5), AFTER, n, n_short), flush=True)
    print("\n   판 «가격 대비» 그 뒤 %d거래일" % AFTER, flush=True)
    print("     종가 기준 — 중앙 **%+.2f%%** · 오른 것 **%.1f%%** · P10 %+.1f%% · P90 %+.1f%%"
          % (ends[n // 2], 100.0 * sum(1 for x in ends if x > 0) / n,
             ends[n // 10], ends[9 * n // 10]), flush=True)
    print("     «한 번이라도» 오른 폭 — 중앙 **%+.2f%%** · +10%% 넘긴 것 **%.1f%%** · "
          "+20%% 넘긴 것 **%.1f%%**"
          % (peaks[n // 2], 100.0 * sum(1 for x in peaks if x >= 10) / n,
             100.0 * sum(1 for x in peaks if x >= 20) / n), flush=True)
    rec = sorted(x["recover"] for x in back)
    print("     **«원래 진입가»를 다시 넘긴 것 %.1f%%** · 진입가 +20%% 까지 간 것 **%.1f%%**"
          % (100.0 * sum(1 for x in rec if x > 0) / n,
             100.0 * sum(1 for x in rec if x >= 20) / n), flush=True)
    print("\n   ⇒ 읽는 법: **손절 뒤 반등은 «흔하다»**(한 번이라도 +10%% 가 %.0f%%). "
          "그런데 **종가로는 중앙 %+.1f%%** 다."
          % (100.0 * sum(1 for x in peaks if x >= 10) / n, ends[n // 2]), flush=True)
    print("      «최고점»과 «끝값»을 섞으면 안 된다 — 반등을 «팔 수 있었는가»는 다른 물음이다.",
          flush=True)
    return {"n": n, "end_med": ends[n // 2], "peak_med": peaks[n // 2],
            "peak10": 100.0 * sum(1 for x in peaks if x >= 10) / n,
            "reentry": 100.0 * sum(1 for x in rec if x > 0) / n}


# ═════════════════════════════════════════════════════════════════════════
def lens4(ev, pmap):
    print("\n" + "=" * 98, flush=True)
    print("【렌즈 ④】 **최고점의 몇 %를 챙기나** (측정 · n 큼)", flush=True)
    print("=" * 98, flush=True)
    rows = []
    for t in ev:
        m = t["masks"][()]
        p = pmap[(t["scan_date"], t["code"], t["pattern"])]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(m["exits"][-1][0])
        mfe = (max(p["h"][i0:i1 + 1]) / t["entry_px"] - 1) * 100
        rows.append((gain_of(t), mfe))
    tot_g = sum(g for g, _m in rows)
    tot_m = sum(m for _g, m in rows if m > 0)
    per = [g / m for g, m in rows if m > 1e-9]
    win = [g / m for g, m in rows if m > 1e-9 and g > 0]
    g20 = sum(g for g, m in rows if m >= 20)
    m20 = sum(m for _g, m in rows if m >= 20)
    n20 = sum(1 for _g, m in rows if m >= 20)
    print("   🚨 **「최고점의 몇 %%를 챙기나」는 «정의»에 따라 4.7%% ~ 51.7%% 로 «열 배» 달라진다.**",
          flush=True)
    print("      숫자 하나만 인용하면 안 된다. 넷을 다 적는다 (거래 %d건):" % len(rows) + chr(10),
          flush=True)
    print("      ① 합 기준 (실현합 ÷ 최고점합)            **%.1f%%**   "
          "← 손절 거래가 분모를 채워 «가장 낮게» 나온다" % (100.0 * tot_g / tot_m), flush=True)
    print("      ② 거래별 비율의 중앙                     %.1f%%   "
          "← 무의미하다(최고점 작고 −8%%로 끝난 것이 다수)" % (100.0 * st.median(per)), flush=True)
    print("      ③ **이익으로 끝난 것만** 중앙 (n=%d)      **%.1f%%**" % (len(win), 100.0 * st.median(win)),
          flush=True)
    print("      ④ **최고점 +20%% 넘은 것만** 합 기준 (n=%d) **%.1f%%**"
          % (n20, 100.0 * g20 / m20), flush=True)
    print("      ⚠️ 65번의 「최고점의 38%%만 챙긴다」와 견주려면 «그쪽 정의»를 먼저 봐야 한다 — "
          "안 보고 비교하면 안 된다." + chr(10), flush=True)
    print("\n   최고점 구간별 — «거기까지 갔던» 거래가 실제로 얼마를 냈나", flush=True)
    print("     %-14s %7s %11s %11s %s" % ("최고점", "건수", "실현 중앙", "실현 평균",
                                           "손실로 끝난 비율"), flush=True)
    print("     " + "-" * 66, flush=True)
    for lo, hi, nm in ((0, 5, "+0~5%"), (5, 10, "+5~10%"), (10, 20, "+10~20%"),
                       (20, 50, "+20~50%"), (50, 1e9, "+50% 이상")):
        sel = [g for g, m in rows if lo <= m < hi]
        if not sel:
            continue
        print("     %-14s %7d %+10.2f%% %+10.2f%% %13.1f%%"
              % (nm, len(sel), st.median(sel), st.mean(sel),
                 100.0 * sum(1 for g in sel if g < 0) / len(sel)), flush=True)
    up20 = [(g, m) for g, m in rows if m >= 20]
    bad = [g for g, _m in up20 if g < 0]
    print("\n   🚨 **+20%% 까지 갔다가 «손실»로 끝난 거래가 %d건 (그 구간의 %.1f%%)**"
          % (len(bad), 100.0 * len(bad) / len(up20)), flush=True)
    return {"capture_sum": 100.0 * tot_g / tot_m,
            "capture_win_median": 100.0 * st.median(win),
            "capture_mfe20_sum": 100.0 * g20 / m20, "n": len(rows), "n_mfe20": n20}


# ═════════════════════════════════════════════════════════════════════════
def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    print("=" * 98, flush=True)
    print("84 — 여러 케이스로 걸어 보기  🚨 ①② 는 검정 아님 · ③④ 는 «서술»(대조군 없음)",
          flush=True)
    print("=" * 98, flush=True)
    by2, ev, blk, pmap = load()
    print("조합 %d 경로 → 진입 **%d건** · 「이미 보유 중」으로 막힌 것 %d건 (%.1f배)"
          % (sum(len(v) for v in by2.values()), len(ev), blk, blk / len(ev)), flush=True)

    with r41.Cost(*COST):
        rs = [sl.sim_lots(ev, seed=s, slots=SLOTS, risk=RISK, cap=CAP, reserve=False,
                          fill_rule="truncate", cash_rule="per_slot")
              for s in range(N_SEED)]
    fills = Counter()
    for r in rs:
        for key, kind, _k, _d, _p, _a, _t in r["fill_log"]:
            if kind == "pilot":
                fills[key] += 1

    lens1(ev, pmap, fills)
    lens2(ev, pmap, fills)
    s3 = lens3(ev, pmap)
    s4 = lens4(ev, pmap)

    (OUT / "84-cases.json").write_text(json.dumps(
        {"n_events": len(ev), "n_blocked": blk, "after_stop": s3, "capture": s4},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 84-cases.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

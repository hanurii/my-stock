# -*- coding: utf-8 -*-
"""83 — **2026-03-15(일) 시점 «실제 종목» 전 과정 시뮬레이션** (사용자 요청)

🚨 **이것은 «검정»이 아니라 «걸어 보기»다.** 문턱도 판정도 없다. n 이 한 자리다.
   여기서 나온 어떤 수치도 «근거»로 쓰지 않는다. 기전을 눈으로 보는 것이 목적이다.

흐름 — 사용자 실제 집행 방식([[entry-execution-method]])을 그대로 따른다:
```
2026-03-13(금) 종가로 스캔  →  주말에 검토  →  2026-03-16(월) 장 전에 «피벗 가격 예약매수»
체결되면  손절 진입가 −8%(시장가) · +20%에 절반 → 나머지 손절선 본전 → 추격
```
★ 이 판이 실제로 가르쳐 준 것: **그날 살 것이 «없다».** 통과한 셋을 이미 들고 있었다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/83-mar15-walkthrough.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

import pyr_trigger as pt                                      # noqa: E402
import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r74", HERE / "74-pyramid-rebuilt.py")
r74 = _u.module_from_spec(_s)
_s.loader.exec_module(r74)
r41, r61, r61b = r74.r41, r74.r61b.r61, r74.r61b

OUT = ROOT / ".cache" / "bt5y" / "out"
SCAN, ENTRY = "2026-03-13", "2026-03-16"
STOP, TARGET = r74.STOP, r74.TARGET
COST, SLOTS, RISK, CAP = r74.COST, r74.SLOTS, r74.RISK, r74.CAP
LO, HI = r74.LO, r74.HI
N_SEED, SNAP_SEED = 200, 0
POT = 10_000_000          # 계좌 1,000만원 가정 — 한 칸 20% = 200만원


def won(x):
    return "{:,.0f}원".format(x)


def _glyph(r):
    for th, ch in ((1.20, "█"), (1.10, "▆"), (1.04, "▅"), (0.995, "▃"), (0.96, "▂")):
        if r >= th:
            return ch
    return "▁"


def _why(px, e, k, n, at_end, peak):
    """🚨 라벨은 «순서»까지 봐야 한다 — 2차 매도가 +20% 위라고 «목표 도달»이 아니다."""
    g = (px / e - 1) * 100
    if g <= -STOP + 0.5:
        return "**손절 −8% (시장가로 집행)**"
    if k == 0 and n > 1 and g >= TARGET - 0.5:
        return "**목표 +20% 도달 → 절반 익절** (남은 절반은 손절선을 본전으로)"
    if at_end and k == n - 1:
        return "🚨 **자료 끝 — 아직 안 팔린 «평가값»**"
    if abs(g) < 0.8:
        return "**본전선** — 절반 판 뒤 손절선을 진입가로 올려 둔 것이 걸림"
    return "**25일 추격선** 이탈 (최고점 대비 %+.1f%%)" % ((px / peak - 1) * 100)


def show_trade(p, t, tag=""):
    m = t["masks"][()]
    e, exits = t["entry_px"], m["exits"]
    i0 = p["d"].index(t["entry_date"])
    last_i = p["d"].index(exits[-1][0])
    seg = list(range(i0, last_i + 1))
    hi_i = max(seg, key=lambda i: p["h"][i])
    lo_i = min(seg, key=lambda i: p["l"][i])
    gain = sum(f * (px / e - 1) * 100 for _d, f, px in exits)
    print("\n" + "─" * 98, flush=True)
    print("■ **%s** (%s)%s — 진입 **%s @ %.2f** · 한 칸 %s"
          % (p["code"], p["pattern"], tag, t["entry_date"], e, won(POT * CAP)), flush=True)
    print("   보유 **%d거래일** · 최고 %.2f (%+.1f%%, %s) · 최저 %.2f (%+.1f%%, %s)"
          % (len(seg), p["h"][hi_i], (p["h"][hi_i] / e - 1) * 100, p["d"][hi_i],
             p["l"][lo_i], (p["l"][lo_i] / e - 1) * 100, p["d"][lo_i]), flush=True)
    for k, (dd, fr, px) in enumerate(exits):
        print("   %s 매도 #%d  %s  %5.0f%% 를 %.2f 에 (%+.2f%%) · %s"
              % ("└" if k == len(exits) - 1 else "├", k + 1, dd, fr * 100, px,
                 (px / e - 1) * 100,
                 _why(px, e, k, len(exits), m["at_end"], p["h"][hi_i])), flush=True)
    print("   ⇒ **%+.2f%%**  ·  한 칸 %s → **%s**  (%s%s원)"
          % (gain, won(POT * CAP), won(POT * CAP * (1 + gain / 100)),
             "+" if gain > 0 else "", "{:,.0f}".format(POT * CAP * gain / 100)), flush=True)
    if m["at_end"]:
        print("   🚨 **이 종목은 %s 에 «거래가 끊긴다»** — 다른 종목은 2026-08-21 까지 있다."
              % p["d"][-1], flush=True)
        print("      인수·상장폐지로 보인다. 하네스는 «그날 종가로 판 것»으로 친다 — "
              "실제로는 인수 프리미엄일 수도, 정리매매일 수도 있다. **이 +0.84%%는 «가정»이다.**",
              flush=True)
    step = max(1, len(seg) // 26)
    print("   흐름 %s   (▁ −8%%  ▃ 본전  ▆ +10%%  █ +20%%↑)"
          % "".join(_glyph(p["c"][i] / e) for i in seg[::step]), flush=True)
    return gain


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    print("=" * 98, flush=True)
    print("83 — 2026-03-15(일) 시점 «실제 종목» 전 과정   🚨 검정 아님 · 걸어 보기", flush=True)
    print("=" * 98, flush=True)

    # ── 1. 검출기가 올린 것 ──────────────────────────────────────────────
    ext_idx, _n = pt._load_ext()
    raw = [p for y in pt.YEARS for p in (pt._load_year(y, ext_idx) or [])
           if p["scan_date"] == SCAN]
    print("\n【1】 2026-03-13(금) 종가로 스캔 — **검출기가 올린 것 %d건** %s"
          % (len(raw), dict(Counter(p["pattern"] for p in raw))), flush=True)

    # ── 2. 조합 필터 ─────────────────────────────────────────────────────
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({m for d in monthly.values() for m in d if m >= "2016-12"})
    sec_top, in_pct = r61b.make_flags(r61b.month_returns(monthly, sector, months), sector)
    ym = r61.prev_ym(SCAN[:7], 1)
    top = sorted(sec_top.get(ym) or [])
    print("\n【2】 조합 필터 — 기준 달 **%s**(직전 달, 룩어헤드 없음) · "
          "주도 3업종 = **%s**" % (ym, ", ".join(top)), flush=True)
    print("\n   %-7s %-5s %-14s %-7s %s" % ("종목", "패턴", "업종", "그룹내", "판정"), flush=True)
    print("   " + "-" * 78, flush=True)
    keep = []
    for p in sorted(raw, key=lambda q: q["code"]):
        sec, v = sector.get(p["code"]), in_pct.get(ym, {}).get(p["code"])
        if not sec or v is None:
            why, ok = "미상 → 통과(61번 규약)", True
        elif sec not in top:
            why, ok = "❌ 주도 3업종이 아니다", False
        elif LO <= v < HI:
            why, ok = "✅ **2·3등급 = 산다**", True
        elif v < LO:
            why, ok = "❌ 상위 %.0f%% = **1등급 → «일부러» 뺀다**" % (v * 100), False
        else:
            why, ok = "❌ 하위 %.0f%%" % (v * 100), False
        print("   %-7s %-5s %-14s %-7s %s"
              % (p["code"], p["pattern"], (sec or "—")[:14],
                 ("%.0f%%" % (v * 100)) if v is not None else "—", why), flush=True)
        if ok:
            keep.append(p)
    print("\n   → **%d건 중 %d건 통과: %s**"
          % (len(raw), len(keep), ", ".join(sorted(p["code"] for p in keep))), flush=True)

    # ── 3. ★ 그런데 살 것이 없다 ─────────────────────────────────────────
    by2, _a, _b, _c = r74.load_filtered()
    ev, blk, _sp = r74.replay_masks(by2, (1.0,), "floor_entry")
    byc = {}
    for t in ev:
        byc.setdefault(t["code"], []).append(t)
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by2.values() for p in ps}

    print("\n" + "=" * 98, flush=True)
    print("【3】 🚨 **그날 새로 살 것은 «없다»** — 셋 다 «이미 들고 있다»", flush=True)
    print("=" * 98, flush=True)
    print("   규칙: 같은 종목을 이미 보유 중이면 또 사지 않는다.", flush=True)
    print("\n   %-7s %-12s %-12s %-11s %s"
          % ("종목", "«이미» 진입일", "청산 예정일", "3/16 주가", "3/16 시점 평가"), flush=True)
    print("   " + "-" * 74, flush=True)
    open_now = []
    for p in sorted(keep, key=lambda q: q["code"]):
        cand = [t for t in byc.get(p["code"], [])
                if t["entry_date"] <= ENTRY
                and (t["masks"][()]["resolve_date"] or "9999") >= ENTRY]
        if not cand:
            print("   %-7s (열린 포지션 없음 — 이 판에선 안 잡힘)" % p["code"], flush=True)
            continue
        t = cand[-1]
        q = pmap[(t["scan_date"], t["code"], t["pattern"])]
        j = q["d"].index(ENTRY) if ENTRY in q["d"] else None
        now = q["c"][j] if j is not None else float("nan")
        print("   %-7s %-12s %-12s %11.2f %+13.2f%%"
              % (p["code"], t["entry_date"], t["masks"][()]["resolve_date"] or "미결",
                 now, (now / t["entry_px"] - 1) * 100), flush=True)
        open_now.append((q, t))
    print("\n   → **신규 매수 0건.** 스캔 목록은 «살 것 목록»이 아니다 — "
          "들고 있는 동안 매일 다시 올라온다.", flush=True)
    print("   (참고: 이 창 전체에서 «같은 종목 보유 중»으로 막힌 후보가 **%d건**, "
          "실제 진입 %d건의 %.1f배다)" % (blk, len(ev), blk / len(ev)), flush=True)

    # ── 4. 그날 계좌 스냅샷 ──────────────────────────────────────────────
    with r41.Cost(*COST):
        rs = [sl.sim_lots(ev, seed=s, slots=SLOTS, risk=RISK, cap=CAP, reserve=False,
                          fill_rule="truncate", cash_rule="per_slot")
              for s in range(N_SEED)]
    r0 = rs[SNAP_SEED]
    filled = {}
    for key, kind, _k, dd, _px, _amt, _tg in r0["fill_log"]:
        if kind == "pilot":
            filled.setdefault(key, dd)
    hold = []
    for t in ev:
        key = (t["scan_date"], t["code"], t.get("pattern", ""))
        if key not in filled:
            continue
        rd = t["masks"][()]["resolve_date"] or "9999"
        if t["entry_date"] <= ENTRY <= rd:
            hold.append(t)
    print("\n【4】 2026-03-16 그날 계좌 안 (추첨 %d번 판 하나 · 5칸)" % SNAP_SEED, flush=True)
    print("   %-7s %-12s %11s %11s %s" % ("종목", "진입일", "진입가", "3/16", "평가"), flush=True)
    print("   " + "-" * 60, flush=True)
    for t in sorted(hold, key=lambda x: x["entry_date"]):
        q = pmap[(t["scan_date"], t["code"], t["pattern"])]
        j = q["d"].index(ENTRY) if ENTRY in q["d"] else None
        now = q["c"][j] if j is not None else t["entry_px"]
        print("   %-7s %-12s %11.2f %11.2f %+10.2f%%"
              % (t["code"], t["entry_date"], t["entry_px"], now,
                 (now / t["entry_px"] - 1) * 100), flush=True)
    print("   → **%d칸 사용 · %d칸 빔**" % (len(hold), SLOTS - len(hold)), flush=True)
    occ = []
    for r in rs:
        f2 = {k for k, kd, _k, _d, _p, _a, _t in r["fill_log"] if kd == "pilot"}
        occ.append(sum(1 for t in ev
                       if (t["scan_date"], t["code"], t.get("pattern", "")) in f2
                       and t["entry_date"] <= ENTRY <= (t["masks"][()]["resolve_date"] or "9999")))
    print("   추첨 %d판 전체 — 그날 쓰인 칸 수: 중앙 **%d칸** · 5칸 꽉 찬 판 %.1f%% · "
          "0칸인 판 %.1f%%"
          % (N_SEED, sorted(occ)[N_SEED // 2], 100.0 * sum(1 for x in occ if x >= 5) / N_SEED,
             100.0 * sum(1 for x in occ if x == 0) / N_SEED), flush=True)

    # ── 5. 셋의 전 과정 ─────────────────────────────────────────────────
    print("\n" + "=" * 98, flush=True)
    print("【5】 그 셋은 «어떻게 끝났나» — 진짜 진입일부터 청산까지", flush=True)
    print("=" * 98, flush=True)
    gains = {}
    for q, t in open_now:
        gains[t["code"]] = show_trade(q, t)

    # ── 6. 실제 체결률 ──────────────────────────────────────────────────
    print("\n" + "=" * 98, flush=True)
    print("【6】 «진짜로 샀을까» — 추첨 %d판 중 체결된 판" % N_SEED, flush=True)
    got = Counter()
    for r in rs:
        for key, kind, _k, dd, _px, _amt, _tg in r["fill_log"]:
            if kind == "pilot" and key[1] in gains:
                for q, t in open_now:
                    if key == (t["scan_date"], t["code"], t.get("pattern", "")):
                        got[key[1]] += 1
    for c in sorted(gains):
        n = got.get(c, 0)
        print("   %-7s %3d판 (%5.1f%%) %s  결과 %+.2f%%"
              % (c, n, 100.0 * n / N_SEED, "█" * int(n / N_SEED * 34), gains[c]), flush=True)
    if gains:
        print("\n   셋 다 산 경우 한 칸씩 %s → 합계 **%s원** (%+.2f%%)"
              % (won(POT * CAP), "{:,.0f}".format(POT * CAP * sum(gains.values()) / 100),
                 sum(gains.values()) / len(gains)), flush=True)

    (OUT / "83-mar15.json").write_text(json.dumps(
        {"scan": SCAN, "entry": ENTRY, "n_raw": len(raw),
         "keep": sorted(p["code"] for p in keep), "top_sectors": top, "ym": ym,
         "already_open": {t["code"]: {"entry_date": t["entry_date"],
                                      "entry_px": t["entry_px"],
                                      "resolve": t["masks"][()]["resolve_date"],
                                      "gain": gains.get(t["code"])}
                          for _q, t in open_now},
         "n_blocked_same_code": blk, "n_events": len(ev),
         "slots_used_median": sorted(occ)[N_SEED // 2],
         "fill_rate": {c: got.get(c, 0) / N_SEED for c in gains}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 83-mar15.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""44 — 진단 셋. **판정 아님. 숫자만.** (문턱은 «계산 전»에 못 박았다)

① 🚨 **미국 패 갭다운** — 가격제한폭 가설
   한국 대조군(검증 세션): **갭다운 9.0% · 그때 평균 −11.55%**(손절선 −10% 대비 **−1.55%p**).
   미국은 가격제한폭이 없다. **더 깊으면 「제한폭이 한국에 유리하다」가 선다.**
   ### 사전 문턱 (결과 보기 «전»에 고정)
   - 선 대비 이격이 한국의 **두 배(−3.1%p)를 넘으면** → **가설 확정**
   - 한국과 **같은 자릿수(−1.0 ~ −2.1%p)면** → **기각**
   - 그 사이(−2.1 ~ −3.1%p)면 → **못 가림**

② 🚨 **①(목표만 지정가)에서 거래당↑ 자산↓** — 「경로 의존성」으로 닫지 않는다
   그건 어떤 결과든 흡수해 **반증 불가**(유형 1). 검정 가능한 기전부터 본다:
   1. 두 팔의 **`mean log(1+r/100)`** — 지정가가 낮으면 **꼬리 절단 → 기하평균 하락**으로 닫힌다
   2. **log 수익이 가장 많이 깎인 상위 5건** — 하락이 거기 몰렸으면 **「몇 건」이 답**이다
   **둘 다 아니면 그때 경로 의존성을 쓴다. 순서가 그렇다.**

③ **Sharadar `open` 과 `close` 가 같은 규약인가** — 한국에서 «원시 시가 vs 수정 진입가»
   비교로 한 번 틀린 자리다. 미국에도 같은 함정이 있는지 **코드와 실측 둘 다** 본다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/44-diagnostics.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                          # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)
v39 = r41.v39
OUT = ROOT / ".cache" / "bt5y" / "out"

KR_GAP_RATE = 9.0          # 한국 실측 (검증 세션)
KR_GAP_FILL = -11.55       # 한국 실측 평균 체결
KR_STOP = -10.0
KR_EXCESS = KR_GAP_FILL - KR_STOP     # −1.55%p
TH_CONFIRM = 2 * KR_EXCESS            # −3.10%p 보다 깊으면 확정
TH_REJECT = KR_EXCESS * 1.35          # −2.09%p 보다 얕으면 기각


def main() -> int:
    by, miss = v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2

    # ── ③ 규약 확인 (실측) ────────────────────────────────────────────────
    print("=" * 92, flush=True)
    print("③ Sharadar `open` 과 `close` 가 «같은 규약»인가", flush=True)
    print("=" * 92, flush=True)
    print("  코드: `us_loader._iter_prices` 가 `row[2..5]` = open/high/low/close 를 «같은 행»에서 낸다.", flush=True)
    print("       `closeadj`(row[7]) · `closeunadj`(row[8]) 는 **안 쓴다**. 하네스는 `close`(row[5]).", flush=True)
    bad_o = bad_c = tot = 0
    for ps in by.values():
        for p in ps:
            for i in range(len(p["c"])):
                o, h, l, c = p["o"][i], p["h"][i], p["l"][i], p["c"][i]
                if None in (o, h, l, c):
                    continue
                tot += 1
                if not (l - 1e-6 <= o <= h + 1e-6):
                    bad_o += 1
                if not (l - 1e-6 <= c <= h + 1e-6):
                    bad_c += 1
    print("  실측 %d 바 — **low <= open <= high 를 깨는 바 %d개(%.4f%%)** · "
          "close 를 깨는 바 %d개(%.4f%%)"
          % (tot, bad_o, 100 * bad_o / tot, bad_c, 100 * bad_c / tot), flush=True)
    print("  → %s" % ("**같은 규약이다.** 시가가 다른 배율이면 고저 범위를 벗어난다."
                      if bad_o <= bad_c + tot * 1e-5
                      else "🚨 **시가만 범위를 벗어난다 — 규약이 다르다**"), flush=True)

    # ── ① 패 갭다운 ──────────────────────────────────────────────────────
    print("", flush=True)
    print("=" * 92, flush=True)
    print("① 미국 **패 갭다운** — 가격제한폭 가설", flush=True)
    print("=" * 92, flush=True)
    print("  🚨 사전 문턱(계산 전 고정): 선 대비 이격 **< %.2f%%p 확정** · "
          "**> %.2f%%p 기각** · 그 사이 못 가림" % (TH_CONFIRM, TH_REJECT), flush=True)
    r41.TARGET_FILL, r41.STOP_FILL = "close", "close"
    ev0, _b = r41.replay(by, lambda p: r41.resolve_v0(p))
    idx = {(q["scan_date"], q["code"], q["pattern"]): q
           for ps in by.values() for q in ps}
    gaps, n_stop = [], 0
    for e in ev0:
        if e["result"] != "loss":
            continue
        n_stop += 1
        p = idx[(e["scan_date"], e["code"], e["pattern"])]
        i = p["d"].index(e["resolve_date"])
        epx = p["entry_price"]
        S = epx * 0.90
        o = p["o"][i]
        if o is not None and o < S:
            gaps.append(round(o / epx * 100 - 100, 2))
    n = len(gaps)
    rate = 100 * n / n_stop if n_stop else 0
    mean_fill = st.mean(gaps) if gaps else None
    excess = (mean_fill - KR_STOP) if gaps else None
    print("  손절 %d건 중 **시가가 손절선(−10%%) 아래로 갭다운 %d건 = %.2f%%**"
          % (n_stop, n, rate), flush=True)
    if gaps:
        gs = sorted(gaps)
        print("     그때 시가 체결 — 평균 **%+.2f%%** · 중앙 %+.2f%% · P10 %+.2f%% · 최소 %+.2f%%"
              % (mean_fill, gs[n // 2], gs[n // 10], gs[0]), flush=True)
        print("     **선 대비 이격 %+.2f%%p**  (한국 %+.2f%%p · 갭다운률 %.1f%%)"
              % (excess, KR_EXCESS, KR_GAP_RATE), flush=True)
        v = ("**확정 — 미국이 훨씬 깊다**" if excess < TH_CONFIRM else
             ("**기각 — 한국과 같은 자릿수**" if excess > TH_REJECT else "**못 가림**"))
        print("     → 사전 문턱 대비: %s" % v, flush=True)

    # ── ② 거래당↑ 자산↓ ─────────────────────────────────────────────────
    print("", flush=True)
    print("=" * 92, flush=True)
    print("② ①(목표만 지정가)에서 **거래당은 올랐는데 자산은 내렸다**", flush=True)
    print("=" * 92, flush=True)
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "close"
    ev1, _b2 = r41.replay(by, lambda p: r41.resolve_v0(p))
    a = {(e["scan_date"], e["code"], e["pattern"]): e for e in ev0}
    b = {(e["scan_date"], e["code"], e["pattern"]): e for e in ev1}
    both = [k for k in a if k in b]
    la = [math.log(1 + slot_sim.net(a[k]["legs"][0][2]) / 100) for k in both]
    lb = [math.log(1 + slot_sim.net(b[k]["legs"][0][2]) / 100) for k in both]
    print("  방아쇠 전수 %d건 (진입 집합은 같다 — 청산 «날짜»가 안 바뀌므로)" % len(both), flush=True)
    print("  %-10s %14s %14s %12s" % ("", "종가", "지정가", "차이"), flush=True)
    print("  %-10s %+13.6f %+13.6f %+11.6f"
          % ("mean log", st.mean(la), st.mean(lb), st.mean(lb) - st.mean(la)), flush=True)
    print("  %-10s %+13.4f%% %+13.4f%% %+11.4f%%p"
          % ("mean 산술", st.mean(slot_sim.net(a[k]["legs"][0][2]) for k in both),
             st.mean(slot_sim.net(b[k]["legs"][0][2]) for k in both),
             st.mean(slot_sim.net(b[k]["legs"][0][2]) for k in both)
             - st.mean(slot_sim.net(a[k]["legs"][0][2]) for k in both)), flush=True)
    dl = st.mean(lb) - st.mean(la)
    print("  → %s" % ("**기하평균이 «낮다» — 꼬리 절단으로 닫힌다**" if dl < 0
                      else "**기하평균도 «높다» — 이 기전으로는 안 닫힌다**"), flush=True)
    print("", flush=True)
    print("  **log 수익이 가장 많이 깎인 상위 8건**", flush=True)
    d = sorted(both, key=lambda k: (math.log(1 + slot_sim.net(b[k]["legs"][0][2]) / 100)
                                    - math.log(1 + slot_sim.net(a[k]["legs"][0][2]) / 100)))
    for k in d[:8]:
        print("    %-6s %s  종가 %+9.2f%% → 지정가 %+9.2f%%  (Δlog %+.4f)"
              % (k[1], k[0], a[k]["legs"][0][2], b[k]["legs"][0][2],
                 math.log(1 + slot_sim.net(b[k]["legs"][0][2]) / 100)
                 - math.log(1 + slot_sim.net(a[k]["legs"][0][2]) / 100)), flush=True)
    tot_dl = sum(math.log(1 + slot_sim.net(b[k]["legs"][0][2]) / 100)
                 - math.log(1 + slot_sim.net(a[k]["legs"][0][2]) / 100) for k in both)
    top5 = sum(math.log(1 + slot_sim.net(b[k]["legs"][0][2]) / 100)
               - math.log(1 + slot_sim.net(a[k]["legs"][0][2]) / 100) for k in d[:5])
    print("  전체 Δlog 합 %+.4f · 상위 5건 몫 %+.4f (**%.1f%%**)"
          % (tot_dl, top5, 100 * top5 / tot_dl if tot_dl else 0), flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "44-diagnostics.json").write_text(json.dumps({
        "convention": {"bars": tot, "open_out_of_range": bad_o, "close_out_of_range": bad_c},
        "gapdown": {"n_stop": n_stop, "n_gap": n, "rate": rate, "mean_fill": mean_fill,
                    "excess_vs_line": excess, "kr_excess": KR_EXCESS,
                    "th_confirm": TH_CONFIRM, "th_reject": TH_REJECT},
        "limit_anomaly": {"mean_log_close": st.mean(la), "mean_log_limit": st.mean(lb),
                          "delta_log": dl, "total_dlog": tot_dl, "top5_dlog": top5},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/44-diagnostics.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

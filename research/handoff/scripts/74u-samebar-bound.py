# -*- coding: utf-8 -*-
"""74u — 같은 봉 순서 규약의 **크기 상한**. 산수만 한다. 시뮬 안 돌린다.

74t 가 «빈도»를 묶었다(해결 전수의 0.70% / 1.35%). 여기서 «폭»을 묶는다.
빈도가 작아도 한 건이 크면 곱이 안 작을 수 있다.

재는 것 (두뇌 세션 지시 그대로)
--------------------------------
미뤄진 해결마다
```
① 실제로 실현된 거래당 순수익            — 실제 lots · 실제 exits
② 그 봉에서 «전량 +20%» 로 결착했다면    — 증액 «전» lots(lots[:j]) 만으로,
                                           가격 = 증액 «전» 평균단가 × 1.20 에 전량
Δ = ② − ①    →  Σ Δ ÷ 분모  =  이 규약이 «최대로» 움직일 수 있는 폭
```
🚨 **②는 상한이지 추정치가 아니다.** 실제 1a 는 절반만 팔고 나머지에 추격이 붙는다.
   **전량 +20% 는 그 자리에서 가능한 «가장 좋은» 결말이므로 ②는 과대하다.**
   따라서 Δ 는 **양의 방향으로 부풀려진 값**이다. 라벨을 그대로 달아 둔다.

🚨 **반사실이 아니다.** `open_until` 을 건드리지 않는다. **같은 해결 집합 위에서
   산수만 바꾼다.** (결착일을 바꾸면 진입 집합까지 달라져 «다른 변형»이 된다.)

🚨 왜 증액 «전» lots 만 쓰나 — 목표를 먼저 잡았다면 규칙 ④에 따라 그 증액은
   애초에 일어나지 않는다. 증액 후 lots 로 잡으면 «사지도 않은 것»을 파는 셈이다.

🚨 분모가 둘이다 — **같은 이름의 다른 양**
------------------------------------------
```
(a) 해결 전수 (경로 × mask 조합)   ← 지시서의 분모. «모든 조합»을 다 센다
(b) 경로 수, mask 전부-True 한 판  ← 시뮬 한 판에서 경로 하나는 mask 하나만 쓴다
```
(a)는 한 경로를 여러 번 센다. **51번에서 「40 seed 합집합」을 「한 판 비율」로 읽어
한 번 틀린 적이 있다.** 둘 다 찍고 어느 물음의 답인지 옆에 적는다.

관문
----
**74t 의 「미뤄진 해결」 수(630 / 2,377)를 여기서 다시 세어 맞춘다.**
어긋나면 겹침 판정이 두 파일에서 갈라진 것이므로 멈춘다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/74u-samebar-bound.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                   # noqa: E402
import slot_sim                                            # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
YEARS = tuple(range(2017, 2027))
EXT_NAME = "uspath_ext2017.json"
TARGET = 20.0
CONFIGS = (("두 단 (1/2,1/2)", (0.5, 0.5), 630),
           ("세 단 (1/3×3)", (1 / 3, 1 / 3, 1 / 3), 2377))
FEES = (("우대수수료 (74번 헤드라인)", 0.0, 0.002), ("무비용", 0.0, 0.0))


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.o = (slot_sim.FEE_BUY, slot_sim.FEE_SELL)
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.o


def first_defer(p, r):
    """첫 «미뤄진» 증액을 찾는다. → (j, 증액 전 평균단가) 또는 None"""
    h, d = p["h"], p["d"]
    idx = {x: i for i, x in enumerate(d)}
    lots = r["lots"]
    for j in range(1, len(lots)):
        i = idx.get(lots[j][0])
        if i is None or h[i] is None:
            continue
        w0 = sum(x[2] for x in lots[:j])
        w1 = sum(x[2] for x in lots[:j + 1])
        a0 = sum(px * fr for _dt, px, fr, _k in lots[:j]) / w0
        a1 = sum(px * fr for _dt, px, fr, _k in lots[:j + 1]) / w1
        if h[i] >= a0 * (1 + TARGET / 100) and h[i] < a1 * (1 + TARGET / 100):
            return j, a0, w0
    return None


def ret_actual(r):
    """① 실제 거래당 순수익 — 다른 문서(50~53)와 «같은» 셈법."""
    lots = r["lots"]
    tot = sum(x[2] for x in lots)
    return sum(fr * slot_sim.net(round(px / ep * 100 - 100, 2)) * (w / tot)
               for _d, fr, px in r["exits"] for _d2, ep, w, _k in lots)


def ret_counterfactual(r, j, a0, w0):
    """② 그 봉에서 «전량 +20%» — 증액 «전» lots 만."""
    px = a0 * (1 + TARGET / 100)
    return sum(slot_sim.net(round(px / ep * 100 - 100, 2)) * (w / w0)
               for _d, ep, w, _k in r["lots"][:j])


def main() -> int:
    ef = BT / "sub" / EXT_NAME
    ext = {}
    if ef.exists():
        for q in json.loads(ef.read_text(encoding="utf-8"))["trigger_paths"]:
            ext[(q["scan_date"], q["code"], q["pattern"])] = q

    # 원자료 수집 — 수수료와 무관한 부분(가격·몫)만 먼저 모은다
    rows = {lab: {"all": [], "full": []} for lab, _s, _e in CONFIGS}
    n_res = {lab: 0 for lab, _s, _e in CONFIGS}
    n_path = 0
    for y in YEARS:
        f = BT / "sub" / ("uspath_%d.json" % y)
        if not f.exists():
            print("🚨 uspath_%d.json 이 없다" % y, flush=True)
            return 2
        ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
        for i, p in enumerate(ps):
            q = ext.get((p["scan_date"], p["code"], p["pattern"]))
            if q is not None:
                ps[i] = q
        n_path += len(ps)
        for p in ps:
            for lab, shares, _exp in CONFIGS:
                got = pt.resolve_all_masks(p, ft="limit", fs="market", shares=shares)
                fullmask = tuple([True] * (len(shares) - 1))
                for mask, r in got.items():
                    n_res[lab] += 1
                    if len(r["lots"]) < 2:
                        continue
                    fd = first_defer(p, r)
                    if fd is None:
                        continue
                    j, a0, w0 = fd
                    rec = (r, j, a0, w0)
                    rows[lab]["all"].append(rec)
                    if mask == fullmask:
                        rows[lab]["full"].append(rec)
        del ps

    # ── 관문 — 74t 와 「미뤄진 해결」 수가 같은가 ─────────────────────────
    print("", flush=True)
    print("관문  74t 의 「미뤄진 해결」 수를 여기서 다시 센다", flush=True)
    ok = True
    for lab, _shares, exp in CONFIGS:
        got = len(rows[lab]["all"])
        ok &= (got == exp)
        print("   %-16s 74t %5d · 74u %5d → %s"
              % (lab, exp, got, "**일치**" if got == exp else "🚨 **어긋남**"), flush=True)
    if not ok:
        print("   → 겹침 판정이 두 파일에서 갈라졌다. 맞추지 말고 «왜인지»부터. 멈춘다.",
              flush=True)
        return 1

    print("", flush=True)
    print("경로 %d개 · 실집행 근사(limit/market) · 목표 +%.0f%%" % (n_path, TARGET), flush=True)
    print("🚨 **②는 상한이다** — 실제 1a 는 절반만 팔고 추격이 붙는다. 전량 +20%는 과대.",
          flush=True)

    res = {}
    for fname, fb, fs in FEES:
        print("", flush=True)
        print("=" * 92, flush=True)
        print("[%s]" % fname, flush=True)
        print("=" * 92, flush=True)
        with Cost(fb, fs):
            for lab, shares, _exp in CONFIGS:
                for scope, denom, dlab in (
                        ("all", n_res[lab], "(a) 해결 전수 = 경로 × mask 조합"),
                        ("full", n_path, "(b) 경로 수 · mask 전부-True 한 판")):
                    recs = rows[lab][scope]
                    d1 = [ret_actual(r) for r, _j, _a, _w in recs]
                    d2 = [ret_counterfactual(r, j, a0, w0) for r, j, a0, w0 in recs]
                    dd = [b - a for a, b in zip(d1, d2)]
                    # 명목 가중 — «목표 크기» 대비 실제 투입분으로 환산
                    nom = [w0 * b - sum(x[2] for x in r["lots"]) * a
                           for (r, _j, _a0, w0), a, b in zip(recs, d1, d2)]
                    s = sum(dd)
                    print("", flush=True)
                    print("  【%s】 %s" % (lab, dlab), flush=True)
                    print("    미뤄진 해결 %5d / 분모 %6d = %.4f%%"
                          % (len(recs), denom, 100 * len(recs) / max(1, denom)), flush=True)
                    if not recs:
                        continue
                    print("    ① 실제 거래당 평균 %+8.4f%%  ·  ② 전량+20%% 평균 %+8.4f%%"
                          % (st.mean(d1), st.mean(d2)), flush=True)
                    print("    Δ(②−①) 건당 — 평균 %+8.4f%%p · 중앙 %+8.4f%%p · "
                          "P10 %+8.4f · P90 %+8.4f · 최대 %+8.4f"
                          % (st.mean(dd), st.median(dd),
                             sorted(dd)[len(dd) // 10], sorted(dd)[9 * len(dd) // 10],
                             max(dd)), flush=True)
                    print("    Δ<0 인 건 %d / %d (%.1f%%)"
                          % (sum(1 for x in dd if x < 0), len(dd),
                             100 * sum(1 for x in dd if x < 0) / len(dd)), flush=True)
                    print("    ★ **Σ Δ ÷ 분모 = %+.4f%%p / 거래**  ← 이 규약의 «폭 상한»"
                          % (s / max(1, denom)), flush=True)
                    print("      (명목 가중판: %+.4f%%p — 목표 크기 대비 실제 투입분 반영. "
                          "②는 파일럿만 들고 있어 투입이 작다)"
                          % (sum(nom) / max(1, denom)), flush=True)
                    res["%s|%s|%s" % (fname, lab, scope)] = {
                        "n": len(recs), "denom": denom,
                        "mean_actual": st.mean(d1), "mean_cf": st.mean(d2),
                        "mean_delta": st.mean(dd), "median_delta": st.median(dd),
                        "max_delta": max(dd), "n_neg": sum(1 for x in dd if x < 0),
                        "bound_pp_per_trade": s / max(1, denom),
                        "bound_pp_nominal": sum(nom) / max(1, denom)}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "74u-samebar-bound.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/74u-samebar-bound.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

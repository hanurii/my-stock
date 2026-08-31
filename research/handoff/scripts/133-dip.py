# -*- coding: utf-8 -*-
"""133 — **+22.5 골짜기의 «이유»를 캔다** (사전등록 · 값 보기 «전»)

사용자(2026-08-31): 「**22.5 골짜기의 이유를 먼저 확인해줘요.**」

132 에서 목표 축의 모양이 이랬다 (60판 중앙 · 세후):
```
+20 9,052  →  **+22.5 7,387(골짜기)**  →  +25 7,764  →  +27.5 9,921  →  +30 11,981
```
**「목표를 올릴수록 좋아진다」면 +22.5 가 +20 보다 나빠서는 안 된다.**

# 후보 셋 — 미리 적는다
```
㉠ **그냥 잡음이다**        60판도 모자라거나, 중앙값 하나가 흔들린 것
㉡ **꼬리 때문이다**        이미 안다: 「상위 1% 거래가 전체 이익의 115.7%」(85번).
                          목표를 +22.5 로 두면 «큰 승자 몇 개»가 거기서 절반 잘리고
                          남은 절반이 추격에 털려 **덜 번다**
㉢ **추격 구조와의 맞물림**  청산이 「목표에서 절반 팔고 나머지는 «본전 바닥 + 25일 저가» 추격」이다.
                          특정 목표대에서 «절반 팔자마자 추격에 걸려 본전에 파는» 일이 몰릴 수 있다
```

# 재는 법 — 세 갈래를 «같이»
```
① **짝비교**  같은 운의 번호에서 +22.5 vs +20 · vs +25 · vs +27.5
   → 판마다 «일관되게» 지면 진짜, **반반이면 ㉠(잡음)**
② ★★ **꼬리 제거**  Σ(자리 손익) = 총수익 이라는 **항등식**(AJ★ 로 이미 검증)을 쓴다.
   상위 1% · 상위 5% 거래를 «빼고» 다시 더한다.
   → **빼면 골짜기가 사라지면 ㉡(꼬리)**, 그대로면 ㉡ 아님
③ **거래 수준 묘사**  목표별 매수 수 · 승률 · 평균이익 · 상위 1%가 이익에서 차지하는 몫
```
목표 +20 · +22.5 · +25 · +27.5 · +30 · 손절 −10 · 절반+추격 · **60판**

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **BC**★ | 🚨 관문 — Σ(자리 손익) = 총수익 (0.5% 안). 꼬리 제거가 이 항등식 위에 서 있다 |
| **BD**★ | 짝비교에서 +22.5 가 +20 에게 지는 판이 **60판 중 70% 초과**여야 「골짜기가 진짜」 |
| **BE** | 꼬리(상위 1%·5%)를 빼면 골짜기가 «사라지는가» |
| **BF** | 목표별 「상위 1%가 이익에서 차지하는 몫」을 적는다 |

# ★ 방향을 «먼저» 적는다
```
㉮ 🚨 **BD★ 를 «못 넘을» 것으로 본다** — 즉 **㉠(잡음)이 답일 가능성이 가장 높다.**
   132 에서 골짜기가 +25 → +22.5 로 «옮겨 다녔다». 위치가 움직이는 건 잡음의 표시다
㉯ **㉡(꼬리)도 일부 맞을 것이다** — 이익의 대부분이 상위 1% 라는 건 이미 안다.
   꼬리를 빼면 «칸 사이 차이 자체»가 작아질 것이다
㉰ 🚨 **㉠ 과 ㉡ 은 «배타적이지 않다»** — 「꼬리가 지배하니 잡음이 커진다」가 같은 말일 수 있다.
   그렇다면 답은 **「골짜기는 실체가 없고, 목표 축 전체가 꼬리 몇 건에 흔들린다」**가 된다
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
f92a = r102.f92a

YEARS = tuple(range(1999, 2027))
TARGETS = (20.0, 22.5, 25.0, 27.5, 30.0)
DIP, LEFT = 22.5, 20.0
STOP = 10.0
PASS = 70.0


def cut_tail(pl, frac):
    """수익 «큰» 쪽에서 frac 만큼 빼고 다시 더한다 (항등식 위에서)."""
    s = sorted(pl, reverse=True)
    k = int(len(s) * frac)
    return sum(s[k:])


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 60
    print("=" * 104, flush=True)
    print("133 — **+22.5 골짜기의 «이유»** · 사전등록 · 운의 번호 %d판" % n_seed, flush=True)
    print("=" * 104, flush=True)
    print("🚨 방향 먼저: **BD★ 를 못 넘을 것 = ㉠(잡음)이 답일 가능성이 가장 높다**", flush=True)
    print("   (132 에서 골짜기가 +25 → +22.5 로 «옮겨 다녔다» — 위치가 움직이는 건 잡음의 표시)\n",
          flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, "1999-04-01", "2026-08-21", "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                          > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k

    r91.STOP, r91.HALF = STOP, 0.5
    per, cut1, cut5, desc = {}, {}, {}, {}
    for tg in TARGETS:
        r91.TARGET = tg
        ev, _b1, _b2 = r91.replay(by_f)
        rs = r91.sim(ev, n_seed)
        tot, c1, c5, sh1, wr, aw, ns = [], [], [], [], [], [], []
        for x in rs:
            pl = [r_ * t / 100.0 for _d, r_, t in x["ret_log"]]     # 계좌 단위 손익
            s = sum(pl)
            g = abs(s - x["equity_pct"] / 100.0) / max(1e-9, abs(x["equity_pct"] / 100.0))
            if g >= 0.005:
                print("🚨 BC★ 미통과 — 항등식 어긋남 %.3f%%" % (g * 100), flush=True)
                return 3
            tot.append(s)
            c1.append(cut_tail(pl, 0.01))
            c5.append(cut_tail(pl, 0.05))
            pos = sum(p for p in pl if p > 0)
            top = sorted(pl, reverse=True)[:max(1, int(len(pl) * 0.01))]
            sh1.append(100.0 * sum(top) / pos if pos > 0 else 0.0)
            r_ = [e[1] for e in x["ret_log"]]
            wr.append(100.0 * sum(1 for v in r_ if v > 0) / len(r_))
            aw.append(st.mean([v for v in r_ if v > 0]) if any(v > 0 for v in r_) else 0.0)
            ns.append(len(r_))
        per[tg], cut1[tg], cut5[tg] = tot, c1, c5
        desc[tg] = {"share1": st.median(sh1), "wr": st.median(wr),
                    "aw": st.median(aw), "n": st.median(ns)}
        print("  목표 +%-5.1f  총수익 배수 중앙 %6.2f · 상위1% 제거 %6.2f · 상위5% 제거 %6.2f"
              % (tg, st.median(tot), st.median(c1), st.median(c5)), flush=True)

    print("\n" + "=" * 104, flush=True)
    print("### BD★ — **짝비교**: +22.5 가 이웃에게 «일관되게» 지는가 (60판)", flush=True)
    res = {}
    for other in (20.0, 25.0, 27.5):
        lose = sum(1 for i in range(n_seed) if per[DIP][i] < per[other][i])
        res["%.1f<%.1f" % (DIP, other)] = 100.0 * lose / n_seed
        print("   +22.5 가 +%-5.1f 에게 «지는» 판   **%5.1f%%** (%2d/%d)"
              % (other, 100.0 * lose / n_seed, lose, n_seed), flush=True)
    BD = res["%.1f<%.1f" % (DIP, LEFT)] > PASS
    print("\n   **BD★** +22.5 가 +20 에게 지는 판 > %.0f%% → **%s**"
          % (PASS, "통과 — 골짜기가 «진짜»다" if BD else "**미통과 — 골짜기는 «잡음»이다**"),
          flush=True)

    print("\n### BE — **꼬리를 빼면 골짜기가 사라지는가** (총수익 «배수» 중앙)", flush=True)
    print("   %-14s %11s %13s %13s" % ("", "그대로", "상위1% 제거", "상위5% 제거"), flush=True)
    print("   " + "-" * 54, flush=True)
    for tg in TARGETS:
        print("   목표 +%-6.1f %10.2f %12.2f %12.2f"
              % (tg, st.median(per[tg]), st.median(cut1[tg]), st.median(cut5[tg])), flush=True)
    for lab, box in (("그대로", per), ("상위1% 제거", cut1), ("상위5% 제거", cut5)):
        d = st.median(box[DIP]) < st.median(box[LEFT])
        print("   → [%s] +22.5 < +20 인가: **%s**" % (lab, "그렇다" if d else "**아니다**"),
              flush=True)

    print("\n### BF — **상위 1% 가 이익에서 차지하는 몫**", flush=True)
    for tg in TARGETS:
        d = desc[tg]
        print("   목표 +%-6.1f 상위1%% 몫 **%5.1f%%** · 승률 %4.1f%% · 평균이익 +%5.2f%% · 매수 %4.0f"
              % (tg, d["share1"], d["wr"], d["aw"], d["n"]), flush=True)

    (r91.OUT / "133-dip.json").write_text(
        json.dumps({"med": {str(t): st.median(per[t]) for t in TARGETS},
                    "cut1": {str(t): st.median(cut1[t]) for t in TARGETS},
                    "cut5": {str(t): st.median(cut5[t]) for t in TARGETS},
                    "paired_lose": res, "BD": BD,
                    "desc": {str(t): desc[t] for t in TARGETS}},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 133-dip.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

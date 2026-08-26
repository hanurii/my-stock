# -*- coding: utf-8 -*-
"""pyr_trigger — 경로 하나를 **가능한 모든 매수 조합**에 대해 미리 풀어 둔다.

74번(`tasks/74-pyramid-rebuilt.md`)의 «해결자» 쪽이다. 시뮬(`slot_sim_lots.py`)과
실행부(`74-pyramid-rebuilt.py`)는 여기 있지 않다.

왜 «모든 조합»인가
------------------
증액이 실제로 들어가는지는 그날 현금이 있느냐에 달렸고, 그건 seed 마다 다르다.
그런데 조합 수는 트랜치 2개면 **2가지**, 3개면 **4가지**뿐이다. 전부 미리 풀어 두면
시뮬은 «찾아 쓰기»만 하면 되고 순환이 사라진다.

🚨 **`sched` 는 mask 에 따라 달라질 수 있다.** 목표선이 «평균단가»에 달렸고,
   평균단가는 «실제로 산 트랜치»가 정한다. 목표에 닿으면 그 자리에서 청산 단계로
   넘어가므로(규칙 ④) 뒤의 방아쇠는 아예 나지 않는다. **이것이 mask 별로 따로 푸는 이유다.**

방아쇠 (사전등록 §3)
--------------------
```
① 진입 후 최고 고가 H 를 갱신해 나간다 (H 는 «그날까지»의 최고 고가)
② 저가가 H − atr_k×ATR(atr_n) 아래로 내려가고, 그 아래에서 min_days 거래일 이상
   «연속으로» 머물면 → 「눌림」. 그때의 H 를 방아쇠 선 L 로 잠근다
③ 그 뒤 고가 ≥ L 인 첫날 증액. 체결가 = max(L, 시가)      ← 갭업이면 시가
④ 목표(평균단가 × (1+target/100))에 «닿은 뒤»에는 증액하지 않는다
⑤ 경로 안에서만. 증액 뒤에는 ①로 돌아가 H 를 새로 쌓는다(다음 트랜치용)
```

**ATR**: 경로는 진입일부터라 이전 자료가 없다. **있는 봉만으로** 계산하고
**3봉 미만이면 눌림 판정 보류**. True Range 는 표준
`max(h−l, |h−pc|, |l−pc|)`, **첫 봉은 h−l**. 평활 없이 최근 ≤`atr_n`개의 단순 평균.
어느 시점에서도 **그날까지의 봉만** 쓴다(룩어헤드 없음).

청산 (47번 `1a` 그대로 · 기준만 «평균단가»)
--------------------------------------------
```
평균단가 a = Σ(체결가 × 몫) / Σ몫              ← «실제로 산» lots 기준
손절선  S = a × (1 − stop/100)
        add_stop=="floor_entry" 이고 증액이 «하나라도» 있었으면
            S = max(S, entry_px)
목표선  T = a × (1 + target/100)
목표 닿으면 half 를 팔고 → 본전(a) + trail일 저가 추격
```

체결가 규약
-----------
`47-round3-pyramid.py` 의 `_buy_px` / `_sell_up_px` / `_sell_dn_px` 와 **같은 구현**이다.
(import 하면 `41 → 39 → slot_sim*` 까지 딸려 오므로 여기서는 네 줄짜리를 다시 적고,
 **자기 점검 「관문 0」에서 47번 것과 값이 같은지 실제로 확인**한다. 주석으로만
 「같다」고 적으면 나중에 갈라져도 아무도 모른다.)

⚠️ **한 봉 안의 순서** — 증액 방아쇠와 목표가 «같은 날» 걸리면
   47번과 같이 **증액을 먼저** 처리한다(증액 → 평균단가 상승 → 목표선 상승 →
   그날 목표가 안 걸릴 수도 있다). 일봉으로는 장중 선후를 알 수 없다.
   규칙 ④의 「닿은 뒤」를 «엄격히 뒤»로 읽은 것이다.

⚠️ **무장 뒤에는 H 를 더 쌓지 않는다.** L 이 잠긴 뒤 재돌파 없이 계속 흘러내리면
   그 경로는 더 이상 증액하지 않는다(더 낮은 자리에서 다시 무장하지 않는다).
   §3 ③ 「그 뒤 고가 ≥ L 인 첫날」의 문자 그대로다.

방아쇠 정의의 손잡이 둘 (검증 세션 지적 · 두뇌 세션 개정 3 · 2026-08-25)
------------------------------------------------------------------------
```
h_lag=False   ← 기본. H 를 «오늘 고가까지» 갱신한 뒤 오늘 저가를 잰다
h_lag=True       H 를 «어제까지»의 최고 고가로 잠근다 (오늘 고가를 넣고 오늘 저가를 재지 않는다)
stay_on="low" ← 기본. 「머물다」를 «저가»로 잰다
stay_on="close"  「머물다」를 «종가»로 잰다
```
🚨 **기본값은 지금 동작 그대로다.** `h_lag=False, stay_on="low"` 에서 관문 0·A·B·C·D 와
   74t·74u 가 **전부 그대로 재현된다**(자기 점검이 그 재현을 찍는다).

⚠️ **`stay_on` 의 적용 범위 — 사양이 정하지 않은 곳.** §3 ②는 「저가가 아래로 «내려가고»,
   그 아래에서 «머물면»」이라 «내려감»과 «머묾»이 두 문장인데, 이 구현은 **연속 일수를 세는
   그 한 판정이 곧 「머물다」**다. 그래서 `stay_on="close"` 면 **세는 날 전부를 종가로** 잰다
   (첫날만 저가, 이후 종가로 나누지 않았다). 다른 뜻이면 한 줄 고치면 된다.

⚠️ **무장한 그날은 방아쇠가 나지 않는다** — §3 ③ 「그 뒤」. 같은 봉에서 잠그고
   같은 봉에서 재돌파하면 늘 참이 되므로(L = 그날 H ≤ 그날 고가) 자명하게 참이 되는
   방아쇠가 된다.

실행(자기 점검): PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/pyr_trigger.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BT = ROOT / ".cache" / "bt5y"

TOL = 1e-9


# ─────────────────────────────────────────────────────────────────────────
# 체결가 — 47번과 «같은» 구현 (관문 0 이 실제로 대조한다)
# ─────────────────────────────────────────────────────────────────────────
def _buy_px(p, i, lvl_px, fill):
    """위로 사는 체결가 — 갭업이면 시가."""
    if fill != "limit":
        return p["c"][i]
    o = (p.get("o") or [None] * len(p["c"]))[i]
    return lvl_px if o is None else max(lvl_px, o)


def _sell_up_px(p, i, lvl_px, fill):
    """목표(위로 파는 것) — 갭업이면 시가."""
    if fill != "limit":
        return p["c"][i]
    o = (p.get("o") or [None] * len(p["c"]))[i]
    return lvl_px if o is None else max(lvl_px, o)


def _sell_dn_px(p, i, lvl_px, fill):
    """손절·추격(아래로 파는 것) — 갭다운이면 시가."""
    if fill != "market":
        return p["c"][i]
    o = (p.get("o") or [None] * len(p["c"]))[i]
    return lvl_px if o is None else min(lvl_px, o)


# ─────────────────────────────────────────────────────────────────────────
# ATR — 그날까지의 봉만
# ─────────────────────────────────────────────────────────────────────────
def true_ranges(p):
    """경로의 True Range 목록. 자료가 빠진 봉은 None."""
    h, l, c = p["h"], p["l"], p["c"]
    out = []
    for i in range(len(c)):
        if h[i] is None or l[i] is None:
            out.append(None)
            continue
        if i == 0:
            out.append(h[0] - l[0])
            continue
        pc = c[i - 1]
        if pc is None:
            out.append(h[i] - l[i])
        else:
            out.append(max(h[i] - l[i], abs(h[i] - pc), abs(l[i] - pc)))
    return out


def atr_series(trs, atr_n=14, min_bars=3):
    """`atr[i]` = 그날까지의 최근 ≤`atr_n` 개 TR 의 단순 평균. `min_bars` 미만이면 None."""
    out, buf = [], []
    for tr in trs:
        if tr is not None:
            buf.append(tr)
            if len(buf) > atr_n:
                buf.pop(0)
        out.append(sum(buf) / len(buf) if len(buf) >= min_bars else None)
    return out


# ─────────────────────────────────────────────────────────────────────────
# 해결자
# ─────────────────────────────────────────────────────────────────────────
def _mk(p, epx, lots, sched, ex, rd, result, at_end, stop):
    return {"code": p["code"], "scan_date": p["scan_date"], "pattern": p["pattern"],
            "entry_date": p["entry_date"], "entry_px": epx, "stop_frac": stop / 100.0,
            "lots": lots, "sched": sched, "exits": ex,
            "resolve_date": rd, "result": result, "at_end": at_end}


def _phase2(p, i, a, half, trail, ft, fs, epx, lots, sched, stop, tpx):
    """절반 판 뒤 — 본전(평균단가) + `trail`일 저가 추격. (47번 `_phase2` 와 같은 규약)"""
    l, c, d = p["l"], p["c"], p["d"]
    n = len(c)
    ex = [(d[i], half, tpx)]
    for j in range(i + 1, n):
        seg = [x for x in l[max(0, j - trail):j] if x is not None]
        s2 = max(a, min(seg)) if seg else a
        if l[j] is not None and l[j] <= s2:
            ex.append((d[j], 1.0 - half, _sell_dn_px(p, j, s2, fs)))
            return _mk(p, epx, lots, sched, ex, d[j], "win", False, stop)
    ex.append((d[n - 1], 1.0 - half, c[n - 1]))
    return _mk(p, epx, lots, sched, ex, d[n - 1], "win", True, stop)


def resolve_one(path, mask, *, ft="limit", fs="market", stop=8.0, target=20.0,
                half=0.5, trail=25, shares=(0.5, 0.5), atr_n=14, atr_k=1.0,
                min_days=2, add_stop="floor_entry", h_lag=False, stay_on="low",
                atr=None, px_round=None,
                exit_mode="half_trail", run_trail=25.0,
                trig_mode="rebreak", trac_days=3, trac_gain=0.0,
                trac_gain_hi=None):
    """매수 조합 하나(`mask`)에 대해 경로를 푼다. 반환 형식은 `resolve_all_masks` 참조."""
    if add_stop not in ("floor_entry", "avg"):
        raise ValueError("add_stop 은 'floor_entry' 또는 'avg' 여야 한다: %r" % (add_stop,))
    if stay_on not in ("low", "close"):
        raise ValueError("stay_on 은 'low' 또는 'close' 여야 한다: %r" % (stay_on,))
    if len(mask) != len(shares) - 1:
        raise ValueError("mask 길이 %d ≠ shares 길이−1 (%d)" % (len(mask), len(shares) - 1))
    p = path
    h, l, c, d = p["h"], p["l"], p["c"], p["d"]
    n = len(c)
    epx = p["entry_price"]
    if atr is None:
        atr = atr_series(true_ranges(p), atr_n=atr_n)

    # 🚨 트랜치 번호 `k` — **파일럿은 −1**, 증액만 0부터 센다
    #    (`slot_sim_lots_selftest.py::three()` 규약 · 두뇌 세션 2026-08-25)
    lots = [(d[0], epx, shares[0], -1)]      # 파일럿은 «항상» 산다
    sched = []
    k = 1                                    # 다음 트랜치 번호
    H = None                                 # ① 진입 후 최고 고가
    below = 0                                # ② 문턱 아래 연속 일수
    L = None                                 # ② 잠긴 방아쇠 선
    armed_at = -1
    peak = None                              # 「끝까지」 청산용 — «어제까지»의 고점
    last_add = -1                            # 「견인력」 방아쇠용 — 마지막 증액 봉
    pend_add = None                          # 「견인력」 예약 — (날짜, 체결가). 다음 봉에 체결

    def avg():
        s = sum(x[2] for x in lots)
        return sum(px * fr for _dt, px, fr, _k in lots) / s if s else epx

    for i in range(n):
        # ── 증액 방아쇠 ────────────────────────────────────────────────
        # 🚨 **순서 버그 수정 (2026-08-26)** — 「견인력」 증액은 «그날 종가»에 체결되는데,
        #    같은 봉에서 바로 청산 검사를 하면 **이미 지나간 그날 저가**로 새 손절선을
        #    검사하게 된다(= 룩어헤드). 첫 구현이 그랬고 M1 이 −76% · 승률 6.5% 로
        #    무너져 잡혔다. **판정 전에 잡았고, 파라미터가 아니라 «순서»를 고친 것이다.**
        #    → 봉 i 끝에 조건을 확인해 «예약»하고, 봉 i+1 «시작»에 체결한다(체결가는 c[i]).
        if pend_add is not None:
            _pd, _ppx = pend_add
            sched.append((_pd, _ppx, shares[k], k - 1))
            if mask[k - 1]:
                lots.append((_pd, _ppx, shares[k], k - 1))
            k += 1
            last_add = i
            pend_add = None
        # ★ 결합 방아쇠 (78번 D) — **1차는 견인력, 2차 이후는 재돌파**.
        #   원문 두 대목이 각각 절반씩이라 둘 다 쓰는 판을 만든다:
        #     ①「잘 진행되면 바로 채운다」 = 견인력   ②「새로운 저위험 진입 시점」 = 재돌파
        _tm = trig_mode
        if trig_mode == "hybrid":
            _tm = "traction" if k == 1 else "rebreak"
        if k < len(shares) and _tm == "traction":
            # ★ 미너비니 규약 (77번) — 「파일럿을 먼저 보내고 «견인력»이 확인되면 더 넣는다」.
            #   «가격이 얼마 올랐나»가 아니라 «이 파일럿이 살아서 이익 중인가»를 본다.
            #   조건: 진입 후 `trac_days` 거래일이 지났고 종가가 진입가 대비 +`trac_gain`% 이상.
            #   🚨 체결가는 «그날 종가» — 재량 매매자가 그날 보고 사는 자리다(지정가 아님).
            #   증액 사이에 `trac_days` 를 다시 세어 한 봉에 몰아 사지 않는다.
            # 78번 사용자 지적 — 지금은 "산 값 위이기만 하면" 산다. +1% 든 +30% 든 같다.
            #   원문은 <연장된 주식은 안 산다>고 한다 -> trac_gain_hi 로 "위 문턱"을 건다.
            #   기본값 None = 위 문턱 없음 = 지금까지의 동작 그대로.
            _g = None if c[i] is None else (c[i] / epx - 1) * 100.0
            if (i >= last_add + trac_days and _g is not None
                    and _g >= trac_gain
                    and (trac_gain_hi is None or _g <= trac_gain_hi)):

                pend_add = (d[i], c[i])          # 다음 봉 시작에 체결
        elif k < len(shares) and _tm == "rebreak":
            if L is not None:
                # ③ 무장 상태 — 「그 뒤」 고가 ≥ L 인 첫날
                if i > armed_at and h[i] is not None and h[i] >= L:
                    px = _buy_px(p, i, L, ft)
                    sched.append((d[i], px, shares[k], k - 1))
                    if mask[k - 1]:
                        lots.append((d[i], px, shares[k], k - 1))
                    k += 1
                    # ⑤ ①로 돌아가 H 를 새로 쌓는다
                    H = h[i]
                    below, L, armed_at = 0, None, -1
            else:
                # ① H 갱신 — `h_lag=False` 면 «그날 포함», True 면 «어제까지»
                if not h_lag and h[i] is not None:
                    H = h[i] if H is None else max(H, h[i])
                # ② 눌림 세기 — `stay_on` 이 「머물다」를 재는 계열을 고른다
                a_i = atr[i]
                v = l[i] if stay_on == "low" else c[i]
                if H is not None and a_i is not None and v is not None:
                    below = below + 1 if v < H - atr_k * a_i else 0
                else:
                    below = 0
                if below >= min_days:
                    L, armed_at = H, i
                if h_lag and h[i] is not None:
                    H = h[i] if H is None else max(H, h[i])

        # ── 청산 ───────────────────────────────────────────────────────
        a = avg()
        S = a * (1 - stop / 100)
        if add_stop == "floor_entry" and len(lots) > 1:
            S = max(S, epx)                  # 이긴 것을 지게 두지 않는다
        T = a * (1 + target / 100)
        # 🚨 **부동소수 칼끝** (관문 E · 2026-08-26): 2자리 십진 가격끼리는 「정확히 닿는」
        #    일이 자주 나고, 그때 40.43999999999999 vs 40.440000000000005 로 승패가 갈린다
        #    (90,240 중 21건 = 0.023%). `px_round=2` 면 «가격 격자»로 반올림해 없앤다 —
        #    새 규약이 아니라 하네스가 이미 쓰는 규약(41번이 추격 수준선을 round(...,2) 한다).
        #    🚨 기본값 None = 옛 동작 그대로. 74번 값은 안 바뀐다.
        if px_round is not None:
            S, T = round(S, px_round), round(T, px_round)

        # ── 「끝까지」 청산 (76번) — 절반 익절 없음 · 고점 대비 고정폭 추격 ──
        #    🚨 추격선은 «어제까지»의 고점으로 잰다(41번 `resolve_trail_only` 와 같은 규약).
        #       기본값 exit_mode="half_trail" = 지금까지의 동작 그대로다.
        if exit_mode == "runner":
            lvl = S if peak is None else max(S, peak * (1 - run_trail / 100))
            if px_round is not None:
                lvl = round(lvl, px_round)
            if i > 0 and l[i] is not None and l[i] <= lvl:
                px = _sell_dn_px(p, i, lvl, fs)
                return _mk(p, epx, lots, sched, [(d[i], 1.0, px)], d[i],
                           ("win" if px > a else "loss"), False, stop)
            if i == 0 and l[0] is not None and l[0] <= lvl:
                return _mk(p, epx, lots, sched, [(d[0], 1.0, c[0])], d[0],
                           "ambiguous", False, stop)
            if h[i] is not None:
                peak = h[i] if peak is None else max(peak, h[i])
            continue

        hit_t = h[i] is not None and h[i] >= T
        hit_s = l[i] is not None and l[i] <= S
        if i == 0:
            if hit_s:
                return _mk(p, epx, lots, sched, [(d[0], 1.0, c[0])], d[0],
                           "ambiguous", False, stop)
            if hit_t:
                return _phase2(p, i, a, half, trail, ft, fs, epx, lots, sched, stop,
                               _sell_up_px(p, i, T, ft))
            continue
        if hit_t and hit_s:
            return _mk(p, epx, lots, sched, [(d[i], 1.0, c[i])], d[i],
                       "ambiguous", False, stop)
        if hit_t:
            return _phase2(p, i, a, half, trail, ft, fs, epx, lots, sched, stop,
                           _sell_up_px(p, i, T, ft))
        if hit_s:
            return _mk(p, epx, lots, sched,
                       [(d[i], 1.0, _sell_dn_px(p, i, S, fs))], d[i], "loss", False, stop)
    return _mk(p, epx, lots, sched, [(d[n - 1], 1.0, c[n - 1])], d[n - 1],
               "unresolved", True, stop)


def resolve_all_masks(path, *, ft="limit", fs="market",
                      stop=8.0, target=20.0, half=0.5, trail=25,
                      shares=(0.5, 0.5),
                      atr_n=14, atr_k=1.0, min_days=2,
                      add_stop="floor_entry", px_round=None, h_lag=False,
                      stay_on="low", exit_mode="half_trail", run_trail=25.0,
                      trig_mode="rebreak", trac_days=3, trac_gain=0.0,
                      trac_gain_hi=None):
    """경로 하나를 «가능한 모든 매수 조합»에 대해 미리 풀어 둔다.

    반환: {mask: resolved}
      mask = 증액 트랜치를 실제로 «샀는지»의 tuple[bool, ...]  길이 = len(shares)-1
             (트랜치 0 = 파일럿은 «항상» 산다)
             shares 가 2개면 키 2개, 3개면 키 4개. 그게 전부다.
      resolved = {
        "code","scan_date","pattern","entry_date","entry_px","stop_frac",
        "lots":   [(날짜, 체결가, 목표대비몫, k), ...]  # 실제로 «산» 것만
        "sched":  [(날짜, 체결가, 목표대비몫, k), ...]  # 방아쇠가 «난» 것 전부(막힌 것 포함)
        # k = 트랜치 번호 — **파일럿 −1 · 증액 0부터**
        "exits":  [(날짜, 포지션전체대비몫, 가격), ...]
        "resolve_date","result","at_end"
      }

    🚨 `sched` 는 mask 에 따라 달라질 수 있다 — 모듈 문서 참조.
    """
    tot = sum(shares)
    # 🚨 **합 == 1.0 제약을 풀었다** (두뇌 세션 2026-08-26 · 리버모어 재검토).
    #    `shares` 의 단위는 「평소 한 칸」이다. `shares[0] == 1.0` 이면 파일럿이 평소 전액이고,
    #    `(1.0, 0.5)` 는 최종 **1.5배**가 된다. 합이 1.0 이면 «같은 크기를 늦게 채우는 것»뿐이라
    #    크기가 안 커진다 — 그게 74번이 잰 것이었다.
    #    합 < 1.0 은 여전히 막는다(파일럿조차 한 칸을 못 채우는 판은 이 도구의 물음이 아니다).
    if tot < 1.0 - 1e-9:
        raise ValueError("shares 합이 1.0 미만이다: %r (합 %.12f)" % (shares, tot))
    if any(x <= 0 for x in shares):
        raise ValueError("shares 는 전부 양수여야 한다: %r" % (shares,))
    atr = atr_series(true_ranges(path), atr_n=atr_n)
    out = {}
    for mask in itertools.product((False, True), repeat=len(shares) - 1):
        out[mask] = resolve_one(path, mask, ft=ft, fs=fs, stop=stop, target=target,
                                half=half, trail=trail, shares=shares, atr_n=atr_n,
                                atr_k=atr_k, min_days=min_days, add_stop=add_stop,
                                h_lag=h_lag, stay_on=stay_on, atr=atr,
                                px_round=px_round, exit_mode=exit_mode,
                                run_trail=run_trail, trig_mode=trig_mode,
                                trac_days=trac_days, trac_gain=trac_gain,
                                trac_gain_hi=trac_gain_hi)
    return out


def resolve_trade(path, **kw):
    """`slot_sim_lots` 가 먹는 «거래 하나»의 모양으로 싸서 낸다.

    `resolve_all_masks` 는 계약대로 `{mask: resolved}` 만 낸다. 시뮬은
    `{..., "shares": (...), "masks": {mask: {...}}}` 를 먹으므로(`slot_sim_lots_selftest.py`)
    그 사이를 여기서 잇는다. **계약을 바꾼 것이 아니라 덧붙인 것이다** —
    시뮬 쪽에 이미 어댑터가 있으면 이 함수는 안 써도 된다.
    """
    shares = kw.get("shares", (0.5, 0.5))
    got = resolve_all_masks(path, **kw)
    any_r = next(iter(got.values()))
    return {"code": any_r["code"], "scan_date": any_r["scan_date"],
            "pattern": any_r["pattern"], "entry_date": any_r["entry_date"],
            "entry_px": any_r["entry_px"], "stop_frac": any_r["stop_frac"],
            "shares": tuple(shares),
            "masks": {m: {"lots": r["lots"], "sched": r["sched"], "exits": r["exits"],
                          "resolve_date": r["resolve_date"], "result": r["result"],
                          "at_end": r["at_end"]}
                      for m, r in got.items()}}


# ═════════════════════════════════════════════════════════════════════════
# 자기 점검 — 관문 0 · A · B · C · D
# ═════════════════════════════════════════════════════════════════════════
YEARS = tuple(range(2017, 2027))
EXT_NAME = "uspath_ext2017.json"


def _load_year(y, ext_idx):
    import json
    f = BT / "sub" / ("uspath_%d.json" % y)
    if not f.exists():
        return None
    ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    if ext_idx:
        for i, p in enumerate(ps):
            q = ext_idx.get((p["scan_date"], p["code"], p["pattern"]))
            if q is not None:
                ps[i] = q
    return ps


def _load_ext():
    import json
    f = BT / "sub" / EXT_NAME
    if not f.exists():
        return {}, 0
    ext = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    return {(q["scan_date"], q["code"], q["pattern"]): q for q in ext}, len(ext)


def _gain(px, epx):
    return round(px / epx * 100 - 100, 2)


def main() -> int:
    import importlib.util as _u
    sys.path.insert(0, str(HERE))

    # ── 관문 0 — 체결가 세 함수가 47번 것과 «같은가» ───────────────────
    print("", flush=True)
    print("관문 0  체결가 규약이 47번과 같은가 (import 해서 실제로 대조)", flush=True)
    _s = _u.spec_from_file_location("r47", HERE / "47-round3-pyramid.py")
    r47 = _u.module_from_spec(_s)
    _s.loader.exec_module(r47)
    _s2 = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
    r41 = _u.module_from_spec(_s2)
    _s2.loader.exec_module(r41)
    fake = {"c": [10.0, 11.0, 12.0], "o": [9.5, 11.5, None]}
    g0 = []
    for i in range(3):
        for lvl in (10.5, 11.5, 12.5):
            for fl in ("close", "limit", "market"):
                g0.append((_buy_px(fake, i, lvl, fl), r47._buy_px(fake, i, lvl, fl)))
                g0.append((_sell_up_px(fake, i, lvl, fl), r47._sell_up_px(fake, i, lvl, fl)))
                g0.append((_sell_dn_px(fake, i, lvl, fl), r47._sell_dn_px(fake, i, lvl, fl)))
    bad0 = [x for x in g0 if x[0] != x[1]]
    print("   대조 %d쌍 · 어긋난 쌍 **%d**  →  %s"
          % (len(g0), len(bad0), "**통과**" if not bad0 else "**미통과** %s" % bad0[:3]),
          flush=True)
    if bad0:
        print("   🚨 체결가 규약이 갈라졌다. 멈춘다.", flush=True)
        return 1

    ext_idx, n_ext = _load_ext()
    print("", flush=True)
    print("   연장 경로 %d개를 갈아끼운다 (%s)" % (n_ext, EXT_NAME), flush=True)

    # 누적 계수기
    n_path = 0
    A = {}                        # (ft,fs) -> [대조 다리 수, 어긋난 거래 수, 최대 |차이|, 예시]
    for key in (("close", "close"), ("limit", "market")):
        A[key] = [0, 0, 0.0, []]
    # 🚨 «세는 것»과 «예시»를 분리한다. 목록만 두면 상한이 곧 개수가 되어
    #    **조용한 절단**이 된다(74번 관문 ⑤ 「조용한 절단 금지」).
    nB = nC = nCF = 0
    B_bad, C_bad, C_full_bad = [], [], []
    D_tot = D_none = 0
    # 🚨 「막힘 갈래가 실제로 돌았는가」 — 통과 표시만 보고 넘어가지 않기 위해 «센다»
    #    (두뇌 세션 2026-08-25: 첫 관문은 막힘이 0이라 재해결 경로가 한 번도 안 돌았다)
    n_blocked_exercised = 0
    k_seen = set()
    # H′ — 방아쇠 정의를 고친 판. **관문 D 만** 다시 찍는다(기본값 판정에는 안 쓴다)
    HP = dict(h_lag=True, stay_on="close")
    Dp = {"두 단": [0, 0, {}], "세 단": [0, 0, {}]}
    # 관문 E — **규모가 가격 논리로 새지 않는가.** 비율이 같은 두 `shares` 는
    #          날짜·결과·가격이 «한 자리도» 달라선 안 된다(몫만 배율만큼 커진다).
    nE = nE_bad = nE_share = nE_px = nE_round = 0
    E_bad = []
    E_relmax = [0.0]
    D3_tot = D3_none = 0
    n_sched_by_mask_differs = 0
    add_hist, add_hist3 = {}, {}

    for y in YEARS:
        ps = _load_year(y, ext_idx)
        if ps is None:
            print("   🚨 uspath_%d.json 이 없다" % y, flush=True)
            return 2
        n_path += len(ps)
        for p in ps:
            epx = p["entry_price"]

            # ── 관문 A — 트랜치 1개 = 41번 `1a` ────────────────────────
            for (ft, fs) in A:
                r41.TARGET_FILL, r41.STOP_FILL = ft, fs
                mine = resolve_all_masks(p, ft=ft, fs=fs, shares=(1.0,))[()]
                rd, res, legs, at_end, _ex = r41.resolve_half_then_trail(p, 8.0, 20.0)
                slot = A[(ft, fs)]
                same = (rd == mine["resolve_date"] and res == mine["result"]
                        and at_end == mine["at_end"] and len(legs) == len(mine["exits"]))
                worst = 0.0
                if same:
                    for (da, fa, ga), (db, fb, pb) in zip(legs, mine["exits"]):
                        slot[0] += 1
                        dd = abs(ga - _gain(pb, epx))
                        worst = max(worst, dd)
                        if da != db or abs(fa - fb) > TOL or dd > TOL:
                            same = False
                if not same:
                    slot[1] += 1
                    slot[2] = max(slot[2], worst)
                    if len(slot[3]) < 3:
                        slot[3].append((p["code"], p["scan_date"], (rd, res, at_end, legs),
                                        (mine["resolve_date"], mine["result"], mine["at_end"],
                                         [(a_, b_, _gain(c_, epx)) for a_, b_, c_ in
                                          mine["exits"]])))
                else:
                    slot[2] = max(slot[2], worst)

            # ── 관문 B·C·D — 두 단 / 세 단 ────────────────────────────
            for shares, is_head in (((0.5, 0.5), True), ((1 / 3, 1 / 3, 1 / 3), False)):
                got = resolve_all_masks(p, shares=shares)
                scheds = set()
                for mask, r in got.items():
                    fsum = sum(f for _d, f, _px in r["exits"])
                    if abs(fsum - 1.0) > TOL:
                        nB += 1
                        if len(B_bad) < 5:
                            B_bad.append((p["code"], p["scan_date"], mask, fsum))
                    lsum = sum(f for _d, _px, f, _k in r["lots"])
                    ssum = sum(shares)          # 🚨 상한은 1.0 이 아니라 **Σshares** 다
                    if lsum > ssum + TOL:
                        nC += 1
                        if len(C_bad) < 5:
                            C_bad.append((p["code"], p["scan_date"], mask, lsum))
                    if all(mask) and abs(lsum - ssum) > TOL:
                        nCF += 1
                        if len(C_full_bad) < 5:
                            C_full_bad.append((p["code"], p["scan_date"], mask, lsum,
                                               len(r["sched"])))
                    scheds.add(tuple(x[0] for x in r["sched"]))
                    if len(r["sched"]) > len(r["lots"]) - 1:
                        n_blocked_exercised += 1
                    for x in r["lots"] + r["sched"]:
                        k_seen.add(x[3])
                if len(scheds) > 1:
                    n_sched_by_mask_differs += 1
                fullmask = tuple([True] * (len(shares) - 1))
                gp = resolve_all_masks(p, shares=shares, **HP)[fullmask]
                sl = Dp["두 단" if is_head else "세 단"]
                sl[0] += 1
                if not gp["sched"]:
                    sl[1] += 1
                nadd = len(gp["lots"]) - 1
                sl[2][nadd] = sl[2].get(nadd, 0) + 1
                full = got[fullmask]
                # ── 관문 E — (1.0,0.5) 는 (2/3,1/3) 의 1.5배 «규모»일 뿐이다
                if is_head:
                    g1 = resolve_all_masks(p, shares=(1.0, 0.5))
                    g2 = resolve_all_masks(p, shares=(2 / 3, 1 / 3))
                    for mk in g1:
                        nE += 1
                        a, b = g1[mk], g2[mk]
                        # ① 구조 — 날짜·결과·다리 수는 **정확히** 같아야 한다
                        st_ok = (a["resolve_date"] == b["resolve_date"]
                                 and a["result"] == b["result"]
                                 and a["at_end"] == b["at_end"]
                                 and [x[0] for x in a["exits"]] == [x[0] for x in b["exits"]]
                                 and [x[:2] for x in a["sched"]] == [x[:2] for x in b["sched"]]
                                 and [x[:2] for x in a["lots"]] == [x[:2] for x in b["lots"]])
                        if not st_ok:
                            nE_bad += 1
                            if len(E_bad) < 3:
                                E_bad.append((p["code"], p["scan_date"], mk,
                                              a["resolve_date"], b["resolve_date"],
                                              a["result"], b["result"]))
                            continue
                        # ② 몫 — 1.5배
                        for x, y in zip(a["lots"], b["lots"]):
                            if abs(x[2] - y[2] * 1.5) > TOL * max(1.0, abs(x[2])):
                                nE_share += 1
                                break
                        # ③ 청산가 — 평균단가가 «나눗셈»으로 나오므로 부동소수 마지막 비트가
                        #    움직인다(Σ(px·fr)/Σfr 은 대수적으로만 규모 불변이다).
                        #    **하네스가 실제로 쓰는 2자리 반올림값**이 같은지를 함께 본다.
                        ep = a["entry_px"]
                        for x, y in zip(a["exits"], b["exits"]):
                            rel = abs(x[2] - y[2]) / max(1e-12, abs(y[2]))
                            E_relmax[0] = max(E_relmax[0], rel)
                            if rel > 1e-12:
                                nE_px += 1
                            if round(x[2] / ep * 100 - 100, 2) != round(y[2] / ep * 100 - 100, 2):
                                nE_round += 1
                if is_head:
                    D_tot += 1
                    if not full["sched"]:
                        D_none += 1
                    add_hist[len(full["lots"]) - 1] = add_hist.get(len(full["lots"]) - 1, 0) + 1
                else:
                    D3_tot += 1
                    if not full["sched"]:
                        D3_none += 1
                    add_hist3[len(full["lots"]) - 1] = add_hist3.get(len(full["lots"]) - 1, 0) + 1
        del ps

    print("", flush=True)
    print("   경로 %d개 (%d~%d년)" % (n_path, YEARS[0], YEARS[-1]), flush=True)
    print("", flush=True)
    print("관문 A  shares=(1.0,) → mask 는 () 하나 · 41번 resolve_half_then_trail(p,8,20) 과 같은가",
          flush=True)
    okA = True
    for (ft, fs), v in A.items():
        okA = okA and v[1] == 0
        print("   %-14s 대조 다리 %7d · **어긋난 거래 %d** · 최대 |수익률 차| %.2e"
              % ("%s/%s" % (ft, fs), v[0], v[1], v[2]), flush=True)
        for ex in v[3]:
            print("      %s %s" % (ex[0], ex[1]), flush=True)
            print("        41번 %s" % (ex[2],), flush=True)
            print("        내것 %s" % (ex[3],), flush=True)
    print("   →  %s" % ("**통과**" if okA else "**미통과** — 맞추지 말고 «왜인지»부터"), flush=True)

    print("", flush=True)
    print("관문 B  모든 mask 에서 Σ exits 몫 == 1.0 (1e-9)", flush=True)
    print("   어긋난 곳 **%d** → %s"
          % (nB, "**통과**" if not nB else "**미통과** (예시) %s" % B_bad[:3]), flush=True)

    print("", flush=True)
    print("관문 C  Σ lots 몫 ≤ **Σshares** · mask 전부 True 면 == Σshares", flush=True)
    print("   ≤Σshares 어긋남 **%d** · 전부-True 인데 ≠Σshares **%d**" % (nC, nCF), flush=True)
    if nCF:
        print("   ⚠️ **「mask 전부 True → Σ lots == Σshares」는 «방아쇠가 난 경로»에서만 참이다.**",
              flush=True)
        print("      방아쇠가 한 번도 안 나면 살 기회 자체가 없다 — 관문 D 의 「방아쇠 안 남」과"
              " 「1회만 남」이 여기 다 들어온다.", flush=True)
        print("      예: %s" % (C_full_bad[:3],), flush=True)
    print("   →  %s" % ("**통과**" if not nC else "**미통과**"), flush=True)

    print("", flush=True)
    print("관문 D  방아쇠가 «한 번도 안 난» 경로의 비율 (mask 전부 True 기준)", flush=True)
    print("   두 단 (1/2,1/2)     %6d / %6d = **%.1f%%**"
          % (D_none, D_tot, 100 * D_none / max(1, D_tot)), flush=True)
    print("   세 단 (1/3×3)       %6d / %6d = **%.1f%%**"
          % (D3_none, D3_tot, 100 * D3_none / max(1, D3_tot)), flush=True)
    print("   증액 횟수 분포(두 단·전부-True): %s"
          % " · ".join("%d회 %d건(%.1f%%)" % (k, v, 100 * v / max(1, D_tot))
                       for k, v in sorted(add_hist.items())), flush=True)
    print("   증액 횟수 분포(세 단·전부-True): %s"
          % " · ".join("%d회 %d건(%.1f%%)" % (k, v, 100 * v / max(1, D3_tot))
                       for k, v in sorted(add_hist3.items())), flush=True)
    if 100 * D_none / max(1, D_tot) > 90:
        print("   🚨 **90%% 초과 — 눌림 조건이 빡빡하다. 값은 바꾸지 않고 «보고»만 한다.**",
              flush=True)

    print("", flush=True)
    print("관문 E  **규모가 가격 논리로 새지 않는가** — shares=(1.0,0.5) vs (2/3,1/3)", flush=True)
    print("        비율이 같으니 날짜·결과·청산가가 «한 자리도» 달라선 안 되고, 몫만 1.5배여야 한다",
          flush=True)
    print("   ① 구조(날짜·결과·다리) 어긋남 **%d** / %d → %s"
          % (nE_bad, nE, "**통과**" if not nE_bad else "**미통과** %s" % E_bad[:2]), flush=True)
    print("   ② 몫이 1.5배 아님 **%d**" % nE_share, flush=True)
    print("   ③ 청산 «가격» 상대차 > 1e-12 인 다리 **%d** · 최대 상대차 **%.2e**"
          % (nE_px, E_relmax[0]), flush=True)
    print("      🚨 평균단가가 Σ(px·fr)/Σfr 이라 **대수적으로만** 규모 불변이다 — 마지막 비트가 움직인다.",
          flush=True)
    print("   ④ **하네스 2자리 반올림 뒤** 어긋난 다리 **%d**  ← 시뮬이 실제로 보는 값"
          % nE_round, flush=True)

    print("", flush=True)
    print("관문 D′  방아쇠 정의를 고친 판 (h_lag=True · stay_on=\"close\") — **관문 D 만** 다시",
          flush=True)
    print("        🚨 기본값 판정에는 안 쓴다. 위 관문들은 전부 기본값(h_lag=False·stay_on=\"low\")",
          flush=True)
    for lab in ("두 단", "세 단"):
        tot, none, hist = Dp[lab]
        base = D_none if lab == "두 단" else D3_none
        print("   %s  방아쇠 안 남 %6d / %6d = **%.1f%%**  (기본값 %.1f%% → **%+.1f%%p**)"
              % (lab, none, tot, 100 * none / max(1, tot), 100 * base / max(1, tot),
                 100 * (none - base) / max(1, tot)), flush=True)
        print("        증액 횟수 분포: %s"
              % " · ".join("%d회 %d건(%.1f%%)" % (k, v, 100 * v / max(1, tot))
                           for k, v in sorted(hist.items())), flush=True)
    print("", flush=True)
    print("점검  «막힌 트랜치»가 실제로 나온 해결 = **%d**건 (0 이면 그 갈래는 한 번도 안 돌았다)"
          % n_blocked_exercised, flush=True)
    print("      트랜치 번호로 실제 등장한 값: %s  (파일럿 −1 · 증액 0부터)"
          % sorted(k_seen), flush=True)
    print("", flush=True)
    print("참고  `sched` 가 mask 에 따라 «달라진» 경로: **%d**건"
          % n_sched_by_mask_differs, flush=True)
    print("      (0 이면 이 자료에서는 규칙 ④가 조합별로 갈라지지 않았다는 뜻 — "
          "계약은 그래도 mask 별로 푼다)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

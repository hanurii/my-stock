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
                min_days=2, add_stop="floor_entry", atr=None):
    """매수 조합 하나(`mask`)에 대해 경로를 푼다. 반환 형식은 `resolve_all_masks` 참조."""
    if add_stop not in ("floor_entry", "avg"):
        raise ValueError("add_stop 은 'floor_entry' 또는 'avg' 여야 한다: %r" % (add_stop,))
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

    def avg():
        s = sum(x[2] for x in lots)
        return sum(px * fr for _dt, px, fr, _k in lots) / s if s else epx

    for i in range(n):
        # ── 증액 방아쇠 ────────────────────────────────────────────────
        if k < len(shares):
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
                # ① H 갱신 (그날 포함)
                if h[i] is not None:
                    H = h[i] if H is None else max(H, h[i])
                # ② 눌림 세기
                a_i = atr[i]
                if H is not None and a_i is not None and l[i] is not None:
                    below = below + 1 if l[i] < H - atr_k * a_i else 0
                else:
                    below = 0
                if below >= min_days:
                    L, armed_at = H, i

        # ── 청산 ───────────────────────────────────────────────────────
        a = avg()
        S = a * (1 - stop / 100)
        if add_stop == "floor_entry" and len(lots) > 1:
            S = max(S, epx)                  # 이긴 것을 지게 두지 않는다
        T = a * (1 + target / 100)
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
                      add_stop="floor_entry"):
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
    if abs(tot - 1.0) > 1e-9:
        raise ValueError("shares 합이 1.0 이 아니다: %r (합 %.12f)" % (shares, tot))
    atr = atr_series(true_ranges(path), atr_n=atr_n)
    out = {}
    for mask in itertools.product((False, True), repeat=len(shares) - 1):
        out[mask] = resolve_one(path, mask, ft=ft, fs=fs, stop=stop, target=target,
                                half=half, trail=trail, shares=shares, atr_n=atr_n,
                                atr_k=atr_k, min_days=min_days, add_stop=add_stop,
                                atr=atr)
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
                    if lsum > 1.0 + TOL:
                        nC += 1
                        if len(C_bad) < 5:
                            C_bad.append((p["code"], p["scan_date"], mask, lsum))
                    if all(mask) and abs(lsum - 1.0) > TOL:
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
                full = got[tuple([True] * (len(shares) - 1))]
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
    print("관문 C  Σ lots 몫 ≤ 1.0 · mask 전부 True 면 == 1.0", flush=True)
    print("   ≤1.0 어긋남 **%d** · 전부-True 인데 ≠1.0 **%d**" % (nC, nCF), flush=True)
    if nCF:
        print("   ⚠️ **계약의 「mask 전부 True → Σ lots == 1.0」은 «방아쇠가 난 경로»에서만 참이다.**",
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

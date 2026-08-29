# -*- coding: utf-8 -*-
"""101 — **무한매수법 V4.0** 을 일봉으로 굴린다. (사용자가 판본을 V4.0 으로 고름 · 2026-08-29)

규칙 출처: `canon/infinite-buying-rules.md` (조사 세션 수집 · quantstack V4.0 일반/리버스 페이지)

# 🚨 «가정»을 박은 자리 여섯 — 결과 문서에 그대로 옮긴다
```
가정1  3/4 지정가매도가 «단독» 체결되면 T = T × 0.25
       출처에 있는 건 「지정가매도 «후» LOC매수 → T×0.25 + 1」이라는 «복합 사건» 하나뿐이다.
       ×0.25 를 떼어 읽는 것은 조사 세션의 추론이고 «완전 리셋(T=0)» 가능성이 안 지워진다
       → **민감도로 «완전 리셋» 판도 같이 돌린다**
가정2  같은 날 매도·매수가 다 나면 **매도 → 매수** 순 (출처가 그 조합 하나는 못 박았다)
가정3  T=0 인 첫날을 «전반전»으로 본다
       (같은 페이지가 「T는 0에서 시작」이면서 「전반전: T = 1 ~ 분할수/2」라 문서 «안»이 어긋난다)
가정4  리버스 「첫날」은 전환 «당일»
가정5  보유가 0 이 되면 「첫 매수」 규칙(전일 종가 +15% LOC)으로 돌아간다 (출처에 없다)
가정6  매도 두 주문은 «하루 시작 보유량»을 분모로 «동시에» 걸어 둔다
       (1/4 은 별% LOC · 3/4 은 +15% 지정가. 둘 다 체결되면 그날 전량이 나간다)
```

# 체결 규약 — 일봉으로 «되는» 것만 쓴다
```
LOC 매수   종가 <= 지정가 이면 «종가»로 체결
LOC 매도   종가 >= 지정가 이면 «종가»로 체결
MOC        무조건 «종가»로 체결
지정가매도  **장중 고가 >= 지정가** 이면 «지정가»로 체결
           ← ETF 하나짜리 별도 코드라 high 를 그대로 쓴다(조사 세션 동의)
```

# 🚨 30분할은 «안» 돌린다 — 별% 공식이 20·40 만 나와 있다
# 🚨 비용(수수료·세금·환전)은 «안» 넣었다 — 네 방식 «모두» 안 넣어 같은 자로 잰다
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".cache" / "bt5y" / "out"

STAR0 = {"TQQQ": 15.0, "SOXL": 20.0}              # 별% 시작값
SLOPE = {(20, "TQQQ"): 1.5, (40, "TQQQ"): 0.75,
         (20, "SOXL"): 2.0, (40, "SOXL"): 1.0}
TGT = {"TQQQ": 15.0, "SOXL": 20.0}                # 3/4 지정가 목표(평단 대비 %)
REV_OUT = {"TQQQ": -15.0, "SOXL": -20.0}          # 리버스 복귀선(평단 대비 %)
FIRST_BUY_UP = 15.0                               # 첫 매수 LOC 지정가 = 전일종가 × 1.15

_CACHE = {}


def load(tk):
    if not _CACHE:
        _CACHE.update(json.loads((OUT / "101-fund-ohlc.json").read_text(encoding="utf-8")))
    s = _CACHE[tk]["series"]
    return sorted(s), s


def run(tk, n_split, d0, d1, principal=1.0, t_on_limit_sell="quarter"):
    """t_on_limit_sell: 'quarter'(가정1) 또는 'reset'(민감도)"""
    ds_all, ser = load(tk)
    ds = [d for d in ds_all if d0 <= d <= d1]
    if not ds:
        return None
    slope, star0 = SLOPE[(n_split, tk)], STAR0[tk]

    cash, sh, cost = principal, 0.0, 0.0          # 현금 · 보유수량 · 매입원가합
    T = 0.0
    rev = rev_day1 = False
    rev_base_sh = 0.0
    closes, eq = [], []
    n_buy = n_rev = n_full = n_limit_only = 0
    expo = []
    peak, mdd = principal, 0.0
    first_rev = None
    rev_days = 0

    for i, d in enumerate(ds):
        h, c = ser[d][1], ser[d][3]
        closes.append(c)
        sh0 = sh                                   # 가정6 — 주문 분모는 «하루 시작 보유량»
        avg = (cost / sh) if sh > 0 else None

        # ── 리버스 «진입» 판정 (그날 시작에) ─────────────────────────
        if not rev and T > n_split - 1:
            rev, rev_day1, rev_base_sh = True, True, sh
            n_rev += 1
            first_rev = first_rev or d

        sold_limit = sold_q = False
        bought = 0.0                               # 0 · 0.5 · 1.0

        if not rev:
            # ══ 일반모드 ═══════════════════════════════════════════
            star = star0 - slope * T               # 별%
            if sh0 > 0:
                sp = avg * (1 + star / 100.0)      # 별지점
                tgt = avg * (1 + TGT[tk] / 100.0)
                if h >= tgt:                       # ① 3/4 지정가매도 (장중 고가)
                    q = min(sh, sh0 * 0.75)
                    cash += q * tgt; cost -= q * avg; sh -= q
                    sold_limit = True
                if sh > 0 and c >= sp:             # ② 1/4 별% LOC매도 (종가)
                    q = min(sh, sh0 * 0.25)
                    cash += q * c; cost -= q * avg; sh -= q
                    sold_q = True
                if sh <= 1e-12:
                    sh, cost = 0.0, 0.0
                    n_full += 1
            # ③ 매수 (가정2 — 매도 뒤)
            if T <= n_split - 1 and cash > 0:
                unit = cash / max(1e-12, n_split - T)
                if sh <= 0:                        # 가정5 — 첫 매수 규칙
                    prev = ser[ds[i - 1]][3] if i > 0 else c
                    if c <= prev * (1 + FIRST_BUY_UP / 100.0):
                        amt = min(unit, cash)
                        sh += amt / c; cost += amt; cash -= amt
                        bought = 1.0
                else:
                    a = cost / sh
                    sp = a * (1 + star / 100.0)
                    if T < n_split / 2.0:          # 전반전 — ½ 별% · ½ 평단
                        for lim, frac in ((sp, 0.5), (a, 0.5)):
                            if c <= lim and cash > 0:
                                amt = min(unit * frac, cash)
                                sh += amt / c; cost += amt; cash -= amt
                                bought += frac
                    elif c <= sp and cash > 0:     # 후반전 — 전액 별%
                        amt = min(unit, cash)
                        sh += amt / c; cost += amt; cash -= amt
                        bought = 1.0
            # ── T 갱신 ────────────────────────────────────────────
            if sold_limit and bought > 0:
                T = T * 0.25 + bought              # 출처: 지정가매도 «후» LOC매수
            elif sold_limit:
                n_limit_only += 1                  # 관문 — 이 가지가 «실제로» 밟히는가
                T = 0.0 if t_on_limit_sell == "reset" else T * 0.25      # 🚨 가정1
            elif sold_q:
                T = T * 0.75 + bought              # 쿼터매도
            else:
                T = T + bought
            T = max(0.0, T)
        else:
            # ══ 리버스모드 — 🚨 별지점이 «직전 5거래일 종가 평균» ════
            rev_days += 1
            win = closes[-6:-1] if len(closes) >= 6 else closes[:-1]
            sp = (sum(win) / len(win)) if win else c
            if rev_day1:                           # 가정4 — 전환 «당일», 무조건 MOC
                q = sh0 / (n_split / 2.0)          # 20분할 1/10 · 40분할 1/20
                q = min(sh, q)
                if q > 0:
                    cash += q * c; cost -= q * (cost / sh); sh -= q
                    T *= (0.9 if n_split == 20 else 0.95)
                rev_base_sh, rev_day1 = sh, False
            else:
                if sh > 0 and c >= sp:             # 매도 — 별지점 «위»
                    q = min(sh, rev_base_sh / (n_split / 2.0))
                    if q > 0:
                        cash += q * c; cost -= q * (cost / sh); sh -= q
                        T *= (0.9 if n_split == 20 else 0.95)
                if c <= sp and cash > 0:           # 매수 — 잔금/4 를 별지점 «아래»
                    amt = cash / 4.0
                    sh += amt / c; cost += amt; cash -= amt
                    T = T + (n_split - T) * 0.25
                    bought = 1.0
            if sh <= 1e-12:
                sh, cost = 0.0, 0.0
            if sh > 0 and (c / (cost / sh) - 1) * 100 > REV_OUT[tk]:
                rev = False                        # 일반모드 복귀

        if bought > 0:
            n_buy += 1
        v = cash + sh * c
        expo.append(0.0 if v <= 0 else sh * c / v)
        eq.append(v)
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)

    fin, yrs = eq[-1], len(ds) / 252.0
    return {"ticker": tk, "n_split": n_split, "t_rule": t_on_limit_sell,
            "d0": ds[0], "d1": ds[-1], "days": len(ds),
            "final": fin, "total_pct": (fin / principal - 1) * 100,
            "cagr": ((fin / principal) ** (1 / yrs) - 1) * 100,
            "mdd_pct": mdd * 100, "n_buy": n_buy, "n_rev": n_rev,
            "rev_days_pct": 100.0 * rev_days / len(ds),
            "n_full_exit": n_full, "first_rev": first_rev,
            "n_limit_only": n_limit_only,
            "expo_mean": 100.0 * sum(expo) / len(expo),
            "expo_series": expo,        # 104(투입한 돈 기준)가 «날마다» 쓴다
            "end_cash_pct": cash / principal * 100, "eq": eq, "dates": ds}


def bench(tk, d0, d1, principal=1.0):
    ds_all, ser = load(tk)
    ds = [d for d in ds_all if d0 <= d <= d1]
    c0 = ser[ds[0]][3]
    eq = [principal * ser[d][3] / c0 for d in ds]
    peak, mdd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    yrs = len(ds) / 252.0
    return {"ticker": tk, "final": eq[-1], "total_pct": (eq[-1] / principal - 1) * 100,
            "cagr": ((eq[-1] / principal) ** (1 / yrs) - 1) * 100,
            "mdd_pct": mdd * 100, "days": len(ds), "eq": eq, "dates": ds}


def main() -> int:
    D0, D1 = "2010-03-11", "2026-08-21"            # SOXL 상장일 = 두 종목이 같은 창에 든다
    print("=" * 104, flush=True)
    print("101 — 무한매수법 **V4.0** (사용자 선택) · %s ~ %s" % (D0, D1), flush=True)
    print("=" * 104, flush=True)
    print("🚨 가정 여섯을 박았다(파일 머리말). 그중 «가정1」은 민감도로 둘 다 돌린다.", flush=True)
    print("🚨 30분할은 «안» 돌린다 — 별%% 공식이 20·40 만 나와 있다.", flush=True)
    print("🚨 비용은 네 방식 «모두» 안 넣었다 — 같은 자로 잰다.\n", flush=True)

    print("  %-24s %11s %10s %9s %9s %7s %7s %8s"
          % ("", "1,000만원→", "총수익", "연환산", "최대낙폭", "투입율", "리버스", "단독매도"),
          flush=True)
    print("  " + "-" * 98, flush=True)
    rows = {}
    for tk in ("TQQQ", "SOXL"):
        for ns in (20, 40):
            for mode, mlab in (("quarter", "가정1"), ("reset", "리셋")):
                r = run(tk, ns, D0, D1, t_on_limit_sell=mode)
                if r is None:
                    continue
                k = "%s %d분할 %s" % (tk, ns, mlab)
                rows[k] = r
                print("  %-24s %10.0f만 %+9.1f%% %+8.2f%% %8.1f%% %7.1f%% %6d %7d"
                      % (k, r["final"] * 1000, r["total_pct"], r["cagr"], r["mdd_pct"],
                         r["expo_mean"], r["n_rev"], r["n_limit_only"]), flush=True)
        print("  " + "-" * 98, flush=True)
    for tk in ("SPY", "QQQ", "TQQQ"):
        b = bench(tk, D0, D1)
        rows["(그냥 보유) " + tk] = b
        print("  %-24s %10.0f만 %+9.1f%% %+8.2f%% %8.1f%%"
              % ("(그냥 보유) " + tk, b["final"] * 1000, b["total_pct"], b["cagr"], b["mdd_pct"]),
              flush=True)

    (OUT / "101-infinite-buying.json").write_text(
        json.dumps({k: {a: b for a, b in v.items()
                            if a not in ("eq", "dates", "expo_series")}
                    for k, v in rows.items()}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print("\n저장: 101-infinite-buying.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

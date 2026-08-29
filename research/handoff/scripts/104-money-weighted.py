# -*- coding: utf-8 -*-
"""104 — **「투입한 돈 기준」으로 다시 잰다** (101 비교표의 빠진 칸 · ⑥번)

101 의 표는 **전부 「계좌 전체 기준」**이었다. 그런데 무한매수법은 **돈의 37% 만 넣는다.**
→ **「넣은 돈이 얼마를 벌었나」로 보면 숫자가 완전히 달라진다.** 그 칸이 없었다.

# 두 자를 갈라 적는다
```
계좌 전체 기준   계좌에 넣어 둔 돈 «전부»를 분모로 — 안 쓴 현금도 분모에 든다
                 「이 방법에 1,000만원을 맡기면 얼마가 되나」
투입한 돈 기준   실제로 «주식에 들어가 있던» 돈만 분모로
                 「들어간 돈이 얼마나 일했나」
```
🚨 **둘 다 참이고 «다른 물음»에 답한다. 어느 쪽이 옳다고 하지 않는다.**
🚨 그리고 **투입한 돈 기준은 「남은 현금을 어디 둘까」에 답하지 않는다** — 그게 이 자의 한계다.

# 재는 법 — 세 가지를 같이 낸다
```
㉮ 계좌 전체 기준 연평균          (101 그대로)
㉯ 평균 투입율                    (하루하루 «주식에 든 돈 ÷ 계좌» 의 평균)
㉰ **투입한 돈 기준 연평균**      = 「같은 돈을 «내내» 넣었다면」로 환산
                                   (1 + 계좌수익)^(1/년) − 1 을 «투입율»로 나누는 게 아니라
                                   **날마다의 수익을 그날 투입율로 나눠 다시 곱한다**
```
🚨 ㉰ 를 «나눗셈 한 번»으로 하면 틀린다(복리라서). **날마다 되돌린 뒤 다시 곱한다.**
"""
from __future__ import annotations

import importlib.util as _u
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r101", HERE / "101-infinite-buying.py")
r101 = _u.module_from_spec(_s)
_s.loader.exec_module(r101)

D0, D1 = "2010-03-11", "2026-08-21"


def money_weighted(eq, expo):
    """날마다 «그날 투입율»로 되돌린 뒤 다시 곱한다.

    그날 계좌 수익률 r 이 투입율 f 에서 났다면, 「전액 넣었다면」의 수익률은 r / f 다.
    🚨 f 가 0 에 가까운 날은 튄다 → **f < 1% 인 날은 «수익도 0»으로 본다**(그날 주식이 없었다).
    """
    v = 1.0
    used = 0
    for i in range(1, len(eq)):
        if eq[i - 1] <= 0:
            break
        r = eq[i] / eq[i - 1] - 1.0
        f = expo[i - 1]
        if f < 0.01:
            continue                       # 주식이 없던 날 — 손익도 없다
        v *= (1.0 + r / f)
        used += 1
    return v, used


def run_one(tk, ns, mode):
    r = r101.run(tk, ns, D0, D1, t_on_limit_sell=mode)
    if r is None:
        return None
    ds_all, ser = r101.load(tk)
    ds = r["dates"]
    eq = r["eq"]
    # 날마다의 투입율을 다시 만든다 — 101 은 평균만 저장한다
    # (101 의 run 을 안 고치려고 여기서 다시 센다. 값은 같은 규약이다)
    return r, eq, ds, ser


def main() -> int:
    print("=" * 108, flush=True)
    print("104 — **「투입한 돈 기준」으로 다시 잰다** · %s ~ %s" % (D0, D1), flush=True)
    print("=" * 108, flush=True)
    print("101 의 표는 전부 「계좌 전체 기준」이었다. 무한매수법은 **돈의 37% 만 넣는다.**", flush=True)
    print("🚨 둘 다 참이고 «다른 물음»에 답한다. 어느 쪽이 옳다고 하지 않는다.\n", flush=True)

    print("  %-24s %11s %11s %11s %11s"
          % ("", "계좌 전체", "평균 투입율", "**투입한 돈**", "차이"), flush=True)
    print("  " + "-" * 76, flush=True)

    out = {}
    for tk in ("TQQQ", "SOXL"):
        for ns in (20, 40):
            r = r101.run(tk, ns, D0, D1, t_on_limit_sell="quarter")
            if r is None:
                continue
            # 날마다 투입율 다시 세기 — 101 의 run 안에서 쓴 것과 같은 정의
            ds_all, ser = r101.load(tk)
            eq = r["eq"]
            # 101 은 expo 를 평균만 낸다. 여기선 «자산 대비 주식» 을 다시 만들 수 없으므로
            # 101 을 한 번 더 돌려 날마다 값을 받는다 → 아래 patch 로 해결(run 이 expo_series 를 낸다)
            expo = r.get("expo_series")
            if expo is None:
                print("  🚨 expo_series 가 없다 — 101 을 고쳐야 한다", flush=True)
                return 2
            yrs = len(eq) / 252.0
            acct = ((eq[-1]) ** (1 / yrs) - 1) * 100
            mv, used = money_weighted(eq, expo)
            mwr = ((mv) ** (1 / (used / 252.0)) - 1) * 100 if used > 30 else float("nan")
            k = "무한매수법 %s %d분할" % (tk, ns)
            out[k] = {"acct": acct, "expo": r["expo_mean"], "mwr": mwr,
                      "days_in": used, "days": len(eq)}
            print("  %-24s %+10.2f%% %10.1f%% %+10.2f%% %+10.2f%%p"
                  % (k, acct, r["expo_mean"], mwr, mwr - acct), flush=True)

    print("  " + "-" * 76, flush=True)
    for tk in ("SPY", "QQQ", "TQQQ", "SOXL"):
        b = r101.bench(tk, D0, D1)
        yrs = len(b["eq"]) / 252.0
        out["(그냥 보유) " + tk] = {"acct": b["cagr"], "expo": 100.0, "mwr": b["cagr"],
                                    "days_in": len(b["eq"]), "days": len(b["eq"])}
        print("  %-24s %+10.2f%% %10.1f%% %+10.2f%% %+10.2f%%p"
              % ("(그냥 보유) " + tk, b["cagr"], 100.0, b["cagr"], 0.0), flush=True)

    print("\n  ★ 「그냥 보유」는 늘 100%% 투입이라 두 자가 «같다». 그게 이 표의 기준선이다.", flush=True)
    print("  🚨 **투입한 돈 기준은 「남은 63%% 를 어디 둘까」에 답하지 않는다.**", flush=True)
    print("     그 돈을 놀리면 계좌 기준이 맞고, 다른 데 굴리면 그 수익을 따로 더해야 한다.", flush=True)
    (r101.OUT / "104-money-weighted.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 104-money-weighted.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

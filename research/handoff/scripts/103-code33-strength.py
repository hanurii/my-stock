# -*- coding: utf-8 -*-
"""103 — **「원전이 숫자를 안 준 자리」를 «끝까지» 훑는다** (사전등록 `tasks/103`, 커밋 637b4c0d)

사용자 지시: 「좋은 숫자를 찾을 때까지 «단정하지 말자»」 → 받는다. **12칸을 전부 훑는다.**
🚨 그리고 «같은 줄»에 「효과가 없어도 최선 칸은 얼마나 좋아 보이나」를 잰다(23번 전례 +87.47%p).

격자 = 몇 분기(1·2·3) × 몇 항목(이익매출 / ＋이익률) × 실적자료 없는 후보(안삼 / 그냥삼) = **12칸**
      + 칸마다 «그 칸과 같은 비율»의 동전던지기

# 말 풀이 (사용자 요청 2026-08-29 — 「seed·가짜·불가통과·불가탈락이 안 와닿는다」)
```
운의번호(seed)   하루에 살 만한 종목이 5칸보다 많으면 «어느 5개를 사느냐»가 운이다.
                 200판 = 같은 27년을 «200번 다시 살아 보는 것». 「운이 좋았을 뿐인가」를 가른다
동전던지기       종목을 «같은 개수»만큼 걸러내되 조건이 아니라 «동전»으로 고른다.
                 「조건이 한 일」과 「그냥 덜 산 것이 한 일」을 가른다
자료없으면 안삼   과거 8분기 실적이 없는 후보(전체의 47.5%)를 «안 산다»
자료없으면 그냥삼 그 후보를 «그냥 산다»
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                          # noqa: E402

_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_s)
_s.loader.exec_module(r102)
r91, f92a = r102.r91, r102.f92a
BLOCKS, YRS, SPY = r102.BLOCKS, r102.YRS, r102.SPY_CAGR
NAN, _nan, _yoy, _ord = r102.NAN, r102._nan, r102._yoy, r102._ord

A_PASS = 55.0
NQ = (1, 2, 3)
NITEM = (2, 3)                       # 둘(이익·매출) · 셋(＋이익률)
UNK = ("자료없으면 안삼", "자료없으면 그냥삼")   # 실적 자료가 «없는» 후보를 어찌할까


def judge(arq, j, ix, nq, nitem):
    """None = 판정 불가 · True/False = 가속인가."""
    if j < 4 + nq:
        return None

    def g(k, f):
        return arq[k][ix[f]] if 0 <= k < len(arq) else None
    for q in range(j, j - nq, -1):
        e0, e1 = _yoy(g(q, "eps"), g(q - 4, "eps")), _yoy(g(q - 1, "eps"), g(q - 5, "eps"))
        r0, r1 = _yoy(g(q, "revenue"), g(q - 4, "revenue")), \
            _yoy(g(q - 1, "revenue"), g(q - 5, "revenue"))
        if _nan(e0) or _nan(e1) or _nan(r0) or _nan(r1):
            return None
        ok = (e0 > e1) and (r0 > r1)
        if nitem == 3:
            m0, m4 = g(q, "netmargin"), g(q - 4, "netmargin")
            if _nan(m0) or _nan(m4):
                return None
            ok = ok and (m0 > m4)
        if not ok:
            return False
    return True


def per_trade(paths):
    out = []
    for p in paths:
        t = pt.resolve_trade(p, ft="limit", fs="market", stop=r91.STOP,
                             target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
        m = t["masks"][()]
        epx = t["entry_px"]
        if not epx or not m["exits"]:
            continue
        w = sum(x[1] for x in m["exits"]) or 1.0
        out.append((sum(x[1] * x[2] for x in m["exits"]) / w / epx - 1.0) * 100.0)
    return out


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else r91.N_SEED
    print("=" * 118, flush=True)
    print("103 — 「원전이 숫자를 안 준 자리」를 «끝까지» 훑는다 · 12칸 + 칸마다 동전던지기 · 운의번호 %d판"
          % n_seed, flush=True)
    print("=" * 118, flush=True)
    print("🚨 격자를 훑으면 «효과가 없어도» 최선 칸은 좋아 보인다(23번 실측 +87.47%p).", flush=True)
    print("   그래서 **동전던지기 12칸의 «최대»**를 같은 줄에 잰다. 그게 M★ 다.\n", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        r102.YEARS, r102.D0, r102.D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    assert ixf[0] == "date" and ix["eps"] == 3, ixf

    # ── 후보마다 «판정»을 한 번만 계산해 둔다 (6가지 = 3분기 × 2항목) ──
    keys, verdict = [], {}
    for y in sorted(by2):
        for p in by2[y]:
            k = (y, id(p))
            keys.append((k, y, p))
            rec = fund.get(p["code"])
            arq = (rec or {}).get("ARQ") or []
            r = f92a.asof(arq, p["entry_date"]) if arq else None
            if r is None or _ord(p["entry_date"]) - _ord(r[0]) > r102.STALE_MAX:
                verdict[k] = {c: None for c in [(q, n) for q in NQ for n in NITEM]}
                continue
            j = arq.index(r)
            verdict[k] = {(q, n): judge(arq, j, ix, q, n) for q in NQ for n in NITEM}

    # ── 바탕 ─────────────────────────────────────────────────────────
    ev_b, _x, _y = r91.replay(by2)
    base = {}
    for lab, a, b in BLOCKS:
        e = [t for t in ev_b if a <= t["entry_date"] <= b]
        base[lab] = [x["equity_pct"] for x in r91.sim(e, n_seed)]
    base_pt = per_trade([p for y in sorted(by2) for p in by2[y]])
    print("바탕 매수 %s · 후보 %s · 매매 한 번당 %+.3f%%\n"
          % ("{:,}".format(len(ev_b)), "{:,}".format(len(keys)), st.mean(base_pt)), flush=True)

    rnd = random.Random(20260829)
    rows, fake_rows = [], []
    print("  %-22s %7s %7s  %s" % ("칸", "남는비율", "매수", "구간별 [연평균 · 바탕과 차 · 200판중 이긴비율]"),
          flush=True)
    print("  " + "-" * 112, flush=True)

    for q in NQ:
        for n in NITEM:
            for u in UNK:
                keep = []
                for k, y, p in keys:
                    v = verdict[k][(q, n)]
                    if v is True or (v is None and u == "자료없으면 그냥삼"):
                        keep.append((y, p))
                rate = 100.0 * len(keep) / len(keys)
                by = {}
                for y, p in keep:
                    by.setdefault(y, []).append(p)
                ev, _x, _y = r91.replay(by)
                cells, name = [], "%d분기·%s·%s" % (q, "이익매출" if n == 2 else "이익매출이익률", u)
                rec = {"name": name, "q": q, "nitem": n, "unk": u, "rate": rate,
                       "n_entry": len(ev), "win": {}}
                for lab, a, b in BLOCKS:
                    e = [t for t in ev if a <= t["entry_date"] <= b]
                    rs = r91.sim(e, n_seed)          # 🚨 한 번만 돌린다(전엔 노출 때문에 두 번 돌았다)
                    eq = [x["equity_pct"] for x in rs]
                    d = sorted(x - z for x, z in zip(eq, base[lab]))
                    med = st.median(eq)
                    cg = ((1 + med / 100.0) ** (1 / YRS[lab]) - 1) * 100
                    w = 100.0 * sum(1 for v in d if v > 0) / n_seed
                    rec["win"][lab] = {"cagr": cg, "dif": st.median(d), "win": w,
                                       "beat_spy": cg > SPY[lab],
                                       "expo": st.median(x["expo_mean"] for x in rs)}
                    cells.append("%s %+.2f%%%s %+6.1f %4.1f%%"
                                 % (lab.split()[0], cg, "✅" if cg > SPY[lab] else "❌",
                                    st.median(d), w))
                rec["pt"] = per_trade([p for _y, p in keep])
                rows.append(rec)
                print("  %-22s %6.1f%% %7s  %s"
                      % (name, rate, "{:,}".format(len(ev)), "  ".join(cells)), flush=True)

                # ── 짝 — «그 칸과 같은 비율»의 동전던지기 ──────────────
                pick = set()
                for k, y, p in keys:
                    if rnd.random() < rate / 100.0:
                        pick.add(k)
                fby = {}
                for k, y, p in keys:
                    if k in pick:
                        fby.setdefault(y, []).append(p)
                fev, _x, _y = r91.replay(fby)
                frec = {"name": "  동전던지기(" + name + ")", "rate": 100.0 * len(pick) / len(keys),
                        "n_entry": len(fev), "win": {}}
                for lab, a, b in BLOCKS:
                    e = [t for t in fev if a <= t["entry_date"] <= b]
                    eq = [x["equity_pct"] for x in r91.sim(e, n_seed)]
                    d = sorted(x - z for x, z in zip(eq, base[lab]))
                    frec["win"][lab] = {"dif": st.median(d),
                                        "win": 100.0 * sum(1 for v in d if v > 0) / n_seed}
                fake_rows.append(frec)

    # ── 판정 ─────────────────────────────────────────────────────────
    print("\n" + "=" * 118, flush=True)
    print("  관문 ㉑ 동전던지기가 «그 칸과 같은 비율»로 걸러졌는가 → 최대 어긋남 **%.2f%%p**"
          % max(abs(r["rate"] - f["rate"]) for r, f in zip(rows, fake_rows)), flush=True)

    KEY = "2002~2017"
    L = [r for r in rows if r["win"][KEY]["win"] > A_PASS
         and all(r["win"][l]["beat_spy"] for l in r["win"])]
    fmax = max(f["win"][KEY]["dif"] for f in fake_rows)
    fmax_all = max(max(f["win"][l]["dif"] for l in f["win"]) for f in fake_rows)
    best = max(rows, key=lambda r: r["win"][KEY]["dif"])

    print("\n  **L★** 12칸 중 «2002~2017 에서 200판 중 55%% 넘게 이기고, 세 구간 모두 지수를 이김» → %s"
          % (", ".join(r["name"] for r in L) if L else "**없음 — 미통과**"), flush=True)
    print("  **M★** 동전던지기 12칸의 최대 차이 = **%+.2f%%p** (세 창 통틀어 %+.2f%%p)"
          % (fmax, fmax_all), flush=True)
    print("        진짜 격자의 최선 칸 = %s **%+.2f%%p**  →  %s"
          % (best["name"], best["win"][KEY]["dif"],
             "**넘는다**" if best["win"][KEY]["dif"] > fmax else "**못 넘는다 — 미통과**"),
          flush=True)

    # N★ — 최선 칸의 «매매 한 번당» 우위가 0 을 배제하는가
    A, B = best["pt"], base_pt
    r2 = random.Random(7)
    ds = sorted(sum(r2.choice(A) for _ in range(len(A))) / len(A)
                - sum(r2.choice(B) for _ in range(len(B))) / len(B) for _ in range(2000))
    lo, hi = ds[50], ds[1949]
    print("  **N★** 최선 칸의 «매매 한 번당» 우위 = %+.3f%%p  구간 [%+.3f, %+.3f]  →  %s  (n=%s)"
          % (st.mean(A) - st.mean(B), lo, hi,
             "0 배제" if not (lo <= 0 <= hi) else "**0 포함 — 미통과**", "{:,}".format(len(A))),
          flush=True)

    # O — 「거래당 우위가 «세기»에 따라 매끄럽게 주는가」 = 내부 검산
    print("\n  ★ O — **매매 한 번당 우위의 «모양»** (진짜 신호면 느슨할수록 매끄럽게 준다)", flush=True)
    for n in NITEM:
        for u in UNK:
            line = []
            for q in NQ:
                r = next(x for x in rows if x["q"] == q and x["nitem"] == n and x["unk"] == u)
                line.append("%d분기 %+6.3f%%p(남는비율%5.1f%%)"
                            % (q, st.mean(r["pt"]) - st.mean(base_pt), r["rate"]))
            print("     %s·불가%s   %s" % ("둘" if n == 2 else "셋", u, "  ".join(line)),
                  flush=True)

    (r91.OUT / "103-code33-strength.json").write_text(
        json.dumps({"rows": [{k: v for k, v in r.items() if k != "pt"} for r in rows],
                    "fake": fake_rows, "fmax": fmax, "n_seed": n_seed},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 103-code33-strength.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

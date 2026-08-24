# -*- coding: utf-8 -*-
"""30 · **2.5단계 — 검출기 몫 `C` 를 양 시장 나란히** (이 과제에서 판정력이 있는 유일한 팔).

사전등록 (두뇌 세션 확정)
-------------------------
- **헤드라인 = 「양 시장의 C 를 나란히」.** 교호작용(`C_US − C_KR`)은 **둘이 갈릴 때만**.
- **검정은 「전체 vs 관문만」 하나.** `+VCP`·`+3C`·`+PP` 는 **분해이지 검정이 아니다.**
- **축은 «거래당»**(슬롯5 자산 금지) — 팔마다 거래 수가 자릿수로 달라 자산으로 재면
  차이 대부분이 **거래 수**에서 온다.
- **동등성 문턱 `|C| < 0.090%p`** 여야 「값을 안 한다」고 쓸 수 있다.
- **10 스트림 × 100회**, 복제마다 **스트림 먼저** 고르고 날짜 블록 재추출(M32-2).
- **동점 규칙 `>` / `>=` 를 둘 다 무조건** 돌린다. 결과를 보고 고르지 않는다.
  규율: **문턱을 하나 더 다는 것보다 둘 다 돌리는 게 싸면, 둘 다 돌린다.**
- 🚨 **3C(n≈723)·PP(n≈104)는 사전 판정불가**(MDE 3.2 / 8.4%p). 「PP가 +N%p」류 금지.

순서 고정 분해에 붙이는 주의 (라벨의 일부다)
--------------------------------------------
하네스는 `for pname in ("VCP", "3C", "PP")` 순으로 돌다가 먼저 진입하면 `open_until` 로
나머지를 막는다. 그래서 세 몫은 **한계 기여**다.
- 쓸 수 있는 말: "VCP 다음에 3C가 더해 주는 몫"
- 쓰면 안 되는 말: "3C 단독의 값어치"
- **세 몫을 서로 비교하지 않는다. 팔이 중첩이라 구간을 더하지 않는다.**

preflight (계산보다 «먼저», 순서대로)
-------------------------------------
0. **`params` 대조** — 파일 이름을 믿지 않는다
1. **스캔일 수** — 패턴 팔 정본에서 «읽어» 대조(하드코딩 금지)
2. **24/24** — 빠진 칸 목록
3. **동점 검산 셋** — (a) `n_tie` 두 판 일치 (b) `ge >= strict` (c) **네 항 항등식**
그 뒤 **Δ 천장** — 관측·예측·천장 나란히
🚨 **관문은 「통과/실패」가 아니라 「얼마나·어느 방향으로」까지 낸다.**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/30-arm25.py
난수 seed: 스트림 300824+s · 부트스트랩 300924
"""
from __future__ import annotations

import json
import os
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_STREAM = 10
N_REP = 100
STREAM_SEED = 300824
BOOT_SEED = 300924
BLOCK = (20, 40)
EQUIV = 0.090
PATTERN_ORDER = ("VCP", "3C", "PP")
YEARS = tuple(range(2021, 2027))
COMBOS = (("kr", "strict"), ("kr", "ge"), ("us", "strict"), ("us", "ge"))
UNI = {"kr": (1800, 3200), "us": (3500, 5600)}


def gate_path(mkt, tie, y):
    return BT / "sub" / ("%s_gate%s_%d.json" % (mkt, "" if tie == "strict" else "ge", y))


def jload(f):
    return json.loads(f.read_text(encoding="utf-8"))


# ── preflight 0 · `params` 대조 ──────────────────────────────────────────────

def params_preflight():
    """🚨 **파일 이름을 믿지 말고 산출물의 `params` 를 읽는다.**

    실제 사고: `_gate_run.sh` 에서 `--gate-tie "$TIE"` 가 빠져 **이름은 `gatege` 인데
    내용은 `strict`** 인 파일 여섯 개가 만들어졌다. 항등 검산이 잡았지만 그건
    **결과를 만든 뒤에** 잡는다. `params` 대조는 **읽는 순간에** 잡는다.
    🚨 **그 버그는 「두 판이 완전히 같다」는 «우리가 기대하던 답»을 냈다.**
       **가장 위험한 버그는 기대하던 답을 내는 버그다.**
    """
    bad, ind, n = [], 0, 0
    for mkt, tie in COMBOS:
        for y in YEARS:
            f = gate_path(mkt, tie, y)
            if not f.exists():
                continue
            n += 1
            d = jload(f)
            p = d.get("params") or {}
            if p.get("arm") != "gate":
                bad.append((f.name, "arm", "gate", p.get("arm")))
            if p.get("gate_tie") != tie:
                bad.append((f.name, "gate_tie", tie, p.get("gate_tie")))
            want_ser = "pdata" if mkt == "kr" else "cache"
            if p.get("series_source") != want_ser:
                bad.append((f.name, "series_source", want_ser, p.get("series_source")))
            gm = p.get("market")
            if gm is None:
                # 코드 형식으로 **직접** 확인 — 유니버스 규모(간접)보다 강하다.
                # 한국은 6자리 숫자(005930), 미국은 영문 티커(AAPL). **섞일 수 없다.**
                codes = {e.get("code") for e in (d.get("events") or [])}
                codes.discard(None)
                if codes:
                    ok = (all(c.isdigit() and len(c) == 6 for c in codes)
                          if mkt == "kr" else all(not c.isdigit() for c in codes))
                    if not ok:
                        bad.append((f.name, "코드 형식", mkt, "섞여 있음"))
                    else:
                        ind += 1
                else:
                    per = d.get("per_date") or []
                    u = st.median([x.get("n_universe") or 0 for x in per]) if per else 0
                    lo, hi = UNI[mkt]
                    if not (lo <= u <= hi):
                        bad.append((f.name, "market(간접)", mkt, "유니버스 %.0f" % u))
                    else:
                        ind += 1
            elif gm != mkt:
                bad.append((f.name, "market", mkt, gm))
    print("0단계 · `params` 대조 — 파일 %d개" % n, flush=True)
    if bad:
        print("  🚨 **불일치 %d건**" % len(bad), flush=True)
        for nm, k, w, g in bad:
            print("    - %-22s %-14s 기대 %r · 실제 %r" % (nm, k, w, g), flush=True)
    else:
        print("  ✅ **불일치 0건**"
              + ("  (그중 %d개는 `market` 미기록 → 코드 형식으로 «직접» 확인)" % ind
                 if ind else ""), flush=True)
    return bad


# ── preflight 1 · 스캔일 수 ─────────────────────────────────────────────────

def scan_len_check():
    """🚨 **「파일이 있다」와 「온전하다」는 다르다.**

    24/24 와 `params` 대조는 **중간에 잘린 파일을 둘 다 통과시킨다** —
    `params` 의 `start`/`end` 는 **인자에서 나오므로 실제로 며칠을 돌았는지와 무관**하다.

    기대값은 **하드코딩하지 않는다** — 같은 창을 돈 **패턴 팔 정본**에서 읽는다.
    → 「같은 이름의 숫자가 두 개」가 **애초에 안 생긴다.** 2026 부분 구간도 자동으로 맞는다.
    ⚠️ **단, 정본이 잘렸으면 「잘린 값끼리」 비교해 통과한다.** 정본의 거래일 수는
       28번 깔때기 표에서 **사람이 한 번 본다** — 그게 이 사슬의 «닻»이고 달력에 닿는 값이다.
    """
    ref = {}
    for y in YEARS:
        for mkt, f in (("kr", BT / ("bt_%d.json" % y)),
                       ("us", BT / "sub" / ("us_%d.json" % y))):
            if f.exists():
                ref[(mkt, y)] = len(jload(f).get("per_date") or [])
    bad, ok = [], 0
    for mkt, tie in COMBOS:
        for y in YEARS:
            f = gate_path(mkt, tie, y)
            if not f.exists():
                continue
            got = len(jload(f).get("per_date") or [])
            want = ref.get((mkt, y))
            if want is None:
                bad.append((f.name, got, None, "정본 파일 없음"))
            elif got != want:
                bad.append((f.name, got, want, "**%+d일**" % (got - want)))
            else:
                ok += 1
    print("1단계 · 스캔일 수 — 패턴 팔 정본과 «정확히» 같아야 한다", flush=True)
    if bad:
        print("  🚨 **어긋남 %d건**" % len(bad), flush=True)
        for nm, g, w, note in bad:
            print("    - %-22s 실제 %s · 기대 %s · %s" % (nm, g, w, note), flush=True)
    else:
        print("  ✅ **%d개 파일 전부 일치** (기대값은 하드코딩이 아니라 `bt_*`·`us_*` 에서 읽었다)"
              % ok, flush=True)
    return bad


# ── preflight 2 · 24/24 ─────────────────────────────────────────────────────

def count_check():
    miss = ["%s/%s/%d" % (mkt, tie, y)
            for mkt, tie in COMBOS for y in YEARS if not gate_path(mkt, tie, y).exists()]
    n = 24 - len(miss)
    print("2단계 · 관문만 팔 산출물 **완료 %d/24**" % n, flush=True)
    if miss:
        print("  🚨 빠진 칸 %d개: %s" % (len(miss), ", ".join(miss)), flush=True)
    else:
        print("  빠진 칸 없음 — 네 조합 여섯 해 전부 있다.", flush=True)
    return n, miss


# ── preflight 3 · 동점 검산 셋 ──────────────────────────────────────────────

def tie_checks():
    """🚨 **옛 검산 `strict 진입 + 동점 == ge 진입` 은 «성립할 수 없는 식»이었다.**

    ge 팔에서 동점이 진입하면 `open_until` 이 걸려(`backtest_volatility_pilot_us.py:404`)
    **그 종목의 나중 진입이 막힌다.** 그 나중 진입은 strict 에서는 «일어났던» 진입이다.

    **실측이 낸 진짜 항등식 — 네 항이다:**
    ```
    ge = strict + (동점 중 «실제로 진입한» 것) − 밀려남 + (ge 에만 있는 비동점 신규)
    ```
    ⚠️ 「동점 131 중 121이 밀어냈다」는 추정은 **틀렸다.** 실측은
       **동점 131 중 ge 에서 실제 진입한 건 25뿐**이고 나머지 106은 그 종목을
       **이미 보유 중이라 애초에 진입도 못 했다.** 밀려난 건 19건뿐이다.
       → **동점의 대부분은 「대체」가 아니라 「무효」였다.**
    남는 «비동점 신규»는 **연쇄**다 — 밀어냄이 다른 날 진입을 열어 준 것.

    ⚠️ `open_until` 은 **이미 알고 있었다**(패턴 분해가 겹침 0인 이유가 그것이었다).
       **알고 있었는데 이 식에 적용하지 않았다.** 유형 18 — 관문이 «성립할 수 없는 것»을 쟀다.
       **한 시간을 멈춰 세운 건 관문이 제대로 작동한 게 아니라 «틀린 식을 줘서»다.**
    """
    rows, bad = [], []
    for mkt in ("kr", "us"):
        for y in YEARS:
            fs, fg = gate_path(mkt, "strict", y), gate_path(mkt, "ge", y)
            if not (fs.exists() and fg.exists()):
                continue
            ds, dg = jload(fs), jload(fg)
            ts = sum(p.get("n_tie") or 0 for p in ds.get("per_date") or [])
            tg = sum(p.get("n_tie") or 0 for p in dg.get("per_date") or [])
            if ts != tg:
                bad.append("%s %d (a) `n_tie` 다름: strict %d vs ge %d (차이 %+d)"
                           % (mkt, y, ts, tg, tg - ts))
            key = lambda e: (e["scan_date"], e["code"], e.get("pattern", ""))
            Es = {key(e): e for e in ds["events"]}
            Eg = {key(e): e for e in dg["events"]}
            if len(Eg) < len(Es):
                bad.append("%s %d (b) ge 진입 %d < strict 진입 %d (차이 %+d)"
                           % (mkt, y, len(Eg), len(Es), len(Eg) - len(Es)))
            ties = {(t["code"], t["entry_date"]) for t in (ds.get("tie_events") or [])}
            tie_ent = [e for e in dg["events"] if (e["code"], e["entry_date"]) in ties]
            gone = [Es[k] for k in Es if k not in Eg]
            newg = [Eg[k] for k in Eg if k not in Es
                    and (Eg[k]["code"], Eg[k]["entry_date"]) not in ties]
            rhs = len(Es) + len(tie_ent) - len(gone) + len(newg)
            if len(Eg) != rhs:
                bad.append("%s %d (c) **네 항 항등식 불일치**: ge %d vs strict %d + "
                           "동점진입 %d − 밀려남 %d + 비동점신규 %d = %d (차이 %+d)"
                           % (mkt, y, len(Eg), len(Es), len(tie_ent), len(gone),
                              len(newg), rhs, len(Eg) - rhs))
            twin, awin = defaultdict(list), defaultdict(list)
            for e in dg["events"]:
                w = (e["entry_date"], e.get("resolve_date") or e["entry_date"])
                awin[e["code"]].append(w)
                if (e["code"], e["entry_date"]) in ties:
                    twin[e["code"]].append(w)
            cov = lambda e, W: any(a <= e["entry_date"] <= b
                                   for a, b in W.get(e["code"], ()))
            by_tie = [e for e in gone if cov(e, twin)]
            by_casc = [e for e in gone if not cov(e, twin) and cov(e, awin)]
            unexp = [e for e in gone if not cov(e, awin)]
            if unexp:
                bad.append("%s %d (c) 밀려난 %d건 중 **설명 안 되는 %d건** (예: %s)"
                           % (mkt, y, len(gone), len(unexp),
                              ", ".join("%s@%s" % (e["code"], e["entry_date"])
                                        for e in unexp[:3])))
            g = [slot_sim.net(e["gain_at_resolve_pct"]) for e in gone
                 if e.get("gain_at_resolve_pct") is not None]
            rows.append({"market": mkt, "year": y, "n_tie": ts,
                         "tie_entered": len(tie_ent),
                         "entered_strict": len(Es), "entered_ge": len(Eg),
                         "displaced": len(gone), "by_tie": len(by_tie),
                         "by_cascade": len(by_casc), "unexplained": len(unexp),
                         "ge_new_nontie": len(newg), "identity_ok": len(Eg) == rhs,
                         "displaced_per_trade": st.mean(g) if g else None})
    print("3단계 · 동점 검산 셋 — 옛 식(`strict + 동점 == ge`)은 «성립할 수 없어» 폐기했다",
          flush=True)
    print("  (a) `n_tie` 두 판 일치 · (b) `ge >= strict` · "
          "(c) **네 항 항등식** + 밀어냄이 전부 설명되는가", flush=True)
    for r in rows:
        print("   %s %d: 동점 %d · 그중 ge 진입 **%d** · 진입 %d→%d · "
              "밀려남 %d(동점 %d·연쇄 %d·**미설명 %d**) · 비동점신규 %d · 항등 %s · "
              "밀려난 거래당 %s"
              % (r["market"], r["year"], r["n_tie"], r["tie_entered"],
                 r["entered_strict"], r["entered_ge"], r["displaced"], r["by_tie"],
                 r["by_cascade"], r["unexplained"], r["ge_new_nontie"],
                 "OK" if r["identity_ok"] else "🚨",
                 ("%+.4f%%" % r["displaced_per_trade"])
                 if r["displaced_per_trade"] is not None else "-"), flush=True)
    if bad:
        print("  🚨 **어긋남 %d건**" % len(bad), flush=True)
        for x in bad:
            print("    - %s" % x, flush=True)
    else:
        print("  ✅ **셋 다 통과** — 네 항 항등식이 12칸 전부 «정확히» 맞고, "
              "밀려난 건이 전부 ge 보유 구간으로 설명된다", flush=True)
    return rows, bad


# ── 자료 ────────────────────────────────────────────────────────────────────

def dedupe(events):
    seen, out = set(), []
    for e in sorted(events, key=lambda x: (x["entry_date"], x["code"],
                                           x.get("pattern", ""))):
        k = (e["scan_date"], e["code"], e.get("pattern", ""))
        if k in seen or e.get("gain_at_resolve_pct") is None:
            continue
        seen.add(k)
        out.append(e)
    return out


def load(mkt, tie):
    """우리 팔(패턴)은 동점규칙과 무관하게 같다 — 동점 규칙은 **대조군에만** 걸린다."""
    ours = []
    if mkt == "kr":
        for y in YEARS:
            f = BT / ("bt_%d.json" % y)
            if f.exists():
                ours += jload(f)["events"]
    else:
        # 🚨 미국도 연도별 여섯 실행이다(워밍업 430 · `open_until` 연도 초기화)
        #    → 한국 `bt_YYYY.json` 과 **구조까지 같다**.
        #    옛 연속 실행판 `us_full_DEADZONE.json` 은 **인용 금지**다.
        for f in sorted((BT / "sub").glob("us_20*.json")):
            ours += jload(f)["events"]
    gate = []
    for y in YEARS:
        f = gate_path(mkt, tie, y)
        if f.exists():
            gate += jload(f)["events"]
    return dedupe(ours), dedupe(gate)


def per_trade(rows):
    return st.mean(slot_sim.net(e["gain_at_resolve_pct"]) for e in rows)


def byday(rows):
    d = defaultdict(list)
    for e in rows:
        d[e["entry_date"]].append(slot_sim.net(e["gain_at_resolve_pct"]))
    return d


def draw(ours, gate, seed, by_atr=False):
    """날짜별로 우리 건수만큼 대조군을 뽑는다. 풀이 모자라면 **부족분을 세어 보고**한다."""
    key = ((lambda e: (e["entry_date"], e.get("atr_band"))) if by_atr
           else (lambda e: e["entry_date"]))
    pool = defaultdict(list)
    for e in gate:
        pool[key(e)].append(e)
    need = defaultdict(int)
    for e in ours:
        need[key(e)] += 1
    rnd = random.Random(seed)
    got, short, short_days = [], 0, 0
    for k, n in need.items():
        p = pool.get(k) or []
        if len(p) <= n:
            got += p
            if len(p) < n:
                short += n - len(p)
                short_days += 1
        else:
            got += rnd.sample(p, n)
    return got, short, short_days


def blocks(dates, rnd):
    n = len(dates)
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(*BLOCK)
        a = rnd.randint(0, max(0, n - L))
        out.append((a, min(L, n - tot)))
        tot += L
    return out


def c_stat(ours, gate, by_atr=False):
    """다중 스트림 × 날짜 블록 부트스트랩으로 C 의 구간을 낸다.
    🚨 복제마다 **스트림을 먼저 고른다**(M32-2). 단일 스트림 구간은 폐기 대상이다."""
    streams, shorts = [], []
    for i in range(N_STREAM):
        g, sh, sd = draw(ours, gate, STREAM_SEED + i, by_atr)
        streams.append(g)
        shorts.append((sh, sd))
    obs = [per_trade(ours) - per_trade(g) for g in streams]
    o_by = byday(ours)
    g_by = [byday(g) for g in streams]
    dates = sorted(o_by)
    rnd = random.Random(BOOT_SEED)
    reps = []
    for r in range(N_STREAM * N_REP):
        s = r % N_STREAM
        oa = ga = 0.0
        oc = gc = 0
        for a, L in blocks(dates, rnd):
            for j in range(L):
                d = dates[a + j]
                v = o_by[d]
                oa += sum(v)
                oc += len(v)
                w = g_by[s].get(d)
                if w:
                    ga += sum(w)
                    gc += len(w)
        if oc and gc:
            reps.append(oa / oc - ga / gc)
    reps.sort()
    return {"C_mean": st.mean(obs), "C_by_stream": obs,
            "C_stream_min": min(obs), "C_stream_max": max(obs),
            "ci_lo": reps[int(len(reps) * .025)], "ci_hi": reps[int(len(reps) * .975)],
            "mde": 2.80 * st.pstdev(reps),
            "n_ours": len(ours), "n_gate_pool": len(gate),
            "n_drawn": st.mean(len(g) for g in streams),
            "short_trades": st.mean(x[0] for x in shorts),
            "short_days": st.mean(x[1] for x in shorts),
            "streams": streams}


def decomp(ours, gate):
    """순서 고정 분해 — 누적 팔(VCP / VCP+3C / 전체). **한계 기여**로만 읽는다."""
    out = {}
    for i in range(1, len(PATTERN_ORDER) + 1):
        keep = set(PATTERN_ORDER[:i])
        sub = [e for e in ours if e.get("pattern") in keep]
        if not sub:
            continue
        r = c_stat(sub, gate)
        r.pop("streams", None)
        lab = "+".join(PATTERN_ORDER[:i])
        out[lab] = r
        print("    %-12s n=%5d · C **%+.4f%%p** (95%% %+.4f ~ %+.4f · MDE %.4f) · "
              "스트림 %+.4f~%+.4f"
              % (lab, r["n_ours"], r["C_mean"], r["ci_lo"], r["ci_hi"], r["mde"],
                 r["C_stream_min"], r["C_stream_max"]), flush=True)
    return out


def extreme_list(mkt):
    ext = set()
    if mkt == "kr":
        for nm in ("27-kr-extreme-audit-100-inf.json",
                   "27-kr-extreme-audit-50-100.json"):
            f = OUT / nm
            if f.exists():
                for h in jload(f)["hits"]:
                    if abs(h["ret_pct"]) > 90:
                        ext.add((h["code"], h["date"]))
    else:
        f = OUT / "25-g3prime.json"
        if f.exists():
            for h in jload(f).get("top") or []:
                ext.add((h["code"], h["date"]))
    return ext


def workb(streams, mkt):
    """작업 B — **추첨 집합**에 극단 종목-일이 든 횟수(양 시장)."""
    ext = extreme_list(mkt)
    if not ext:
        print("  [작업 B] %s 극단 목록이 비어 있다." % mkt.upper(), flush=True)
        return None
    cnt = [sum(1 for e in g if (e["code"], e["entry_date"]) in ext) for g in streams]
    m = st.mean(cnt)
    print("  [작업 B] 추첨 집합에 극단(|하루|>90%%p)이 든 횟수 — 목록 %d건 · "
          "스트림별 %s (평균 %.1f · 목록 대비 %.4f%%)"
          % (len(ext), cnt, m, m / len(ext) * 100), flush=True)
    print("        🚨 두 시장의 극단 목록 크기가 자릿수로 다르다 → "
          "**든 횟수를 그대로 비교하지 말 것.**", flush=True)
    return {"list_size": len(ext), "per_stream": cnt, "mean": m,
            "pct_of_list": m / len(ext) * 100}


def tie_shadow(mkt):
    """관문만 팔의 «동점» 그림자 거래(진입 아님). strict 판 하네스가 남긴다."""
    out = []
    for y in YEARS:
        f = gate_path(mkt, "strict", y)
        if f.exists():
            out += jload(f).get("tie_events") or []
    return [e for e in out if e.get("gain_at_resolve_pct") is not None]


def tie_rate(mkt):
    """동점 비율 — 분모는 **「방아쇠에 닿은 것」**(진입 + 동점). 대조군의 «엄격함»을 곧바로 잰다.
    (후보 대비는 「닿는 빈도」가 섞여 시장 간 비교가 흐려진다 — 참고로만.)"""
    tie = ent = cand = 0
    for y in YEARS:
        f = gate_path(mkt, "strict", y)
        if not f.exists():
            continue
        for p in jload(f).get("per_date") or []:
            tie += p.get("n_tie") or 0
            ent += p.get("n_entered") or 0
            cand += p.get("n_candidates") or 0
    touch = ent + tie
    sh = tie_shadow(mkt)
    return {"n_tie": tie, "n_entered": ent, "n_candidates": cand,
            "pct_of_touch": (tie / touch * 100) if touch else None,
            "pct_of_candidates": (tie / cand * 100) if cand else None,
            "n_shadow": len(sh),
            "shadow_per_trade": per_trade(sh) if sh else None}


def diff_ci(shadow, streams):
    """(동점 그림자 거래당 − 대조군 거래당)의 **자료 축 95% 구간**.
    🚨 원칙: **방아쇠는 「영향이 있다고 확인될 때」가 아니라
       「영향이 없다고 «배제할 수 없을» 때」 켜진다.** 그래서 «구간의 바깥 끝»을 쓴다."""
    if not shadow or not streams:
        return None, None, None
    sh = byday(shadow)
    ct = [byday(g) for g in streams]
    dates = sorted(set(sh) | set().union(*[set(d) for d in ct]))
    rnd = random.Random(BOOT_SEED + 7)
    reps = []
    for r in range(N_STREAM * N_REP):
        i = r % N_STREAM
        sa = ca = 0.0
        sc = cc = 0
        for a, L in blocks(dates, rnd):
            for j in range(L):
                d = dates[a + j]
                v = sh.get(d)
                if v:
                    sa += sum(v)
                    sc += len(v)
                w = ct[i].get(d)
                if w:
                    ca += sum(w)
                    cc += len(w)
        if sc and cc:
            reps.append(sa / sc - ca / cc)
    if not reps:
        return None, None, None
    reps.sort()
    lo, hi = reps[int(len(reps) * .025)], reps[int(len(reps) * .975)]
    return lo, hi, max(abs(lo), abs(hi))


def paired_tie_diff(ours, gate_s, gate_g):
    """`C_> − C_>=` 를 **(스트림, 복제) 짝비교**로. 두 판을 각각 평균 낸 뒤 빼면
    추첨 잡음이 두 번 들어간다. ⚠️ 풀이 달라 짝이 완벽하진 않고,
    **얼마나 나은지가 퍼짐으로 보인다.**"""
    ss = [draw(ours, gate_s, STREAM_SEED + i)[0] for i in range(N_STREAM)]
    gg = [draw(ours, gate_g, STREAM_SEED + i)[0] for i in range(N_STREAM)]
    o_by = byday(ours)
    S, G = [byday(x) for x in ss], [byday(x) for x in gg]
    dates = sorted(o_by)
    rnd = random.Random(BOOT_SEED + 11)
    diffs, per_stream = [], defaultdict(list)
    for r in range(N_STREAM * N_REP):
        i = r % N_STREAM
        oa = sa = ga = 0.0
        oc = sc = gc = 0
        for a, L in blocks(dates, rnd):      # ← **같은 블록을 두 판에 쓴다**
            for j in range(L):
                d = dates[a + j]
                v = o_by[d]
                oa += sum(v)
                oc += len(v)
                w = S[i].get(d)
                if w:
                    sa += sum(w)
                    sc += len(w)
                u = G[i].get(d)
                if u:
                    ga += sum(u)
                    gc += len(u)
        if oc and sc and gc:
            d0 = (oa / oc - ga / gc) - (oa / oc - sa / sc)
            diffs.append(d0)
            per_stream[i].append(d0)
    if not diffs:
        return None
    d2 = sorted(diffs)
    means = [st.mean(v) for v in per_stream.values() if v]
    return {"median": st.median(diffs), "p2.5": d2[int(len(d2) * .025)],
            "p97.5": d2[int(len(d2) * .975)],
            "spread": d2[int(len(d2) * .975)] - d2[int(len(d2) * .025)],
            "stream_spread": (max(means) - min(means)) if means else None}


# ── 본체 ────────────────────────────────────────────────────────────────────

def main():
    pbad = params_preflight()
    if pbad:
        print("\n🚨 **`params` 가 파일 이름과 어긋난다. 멈춘다 — 결과를 만들지 않는다.**",
              flush=True)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "30-arm25-PARAMS-FAIL.json").write_text(
            json.dumps([{"file": n, "field": k, "expected": w, "actual": g}
                        for n, k, w, g in pbad], ensure_ascii=False, indent=1),
            encoding="utf-8")
        return
    sbad = scan_len_check()
    if sbad:
        print("\n🚨 **스캔일 수가 정본과 어긋난다 = 잘린 파일이다. 멈춘다.**", flush=True)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "30-arm25-SCANLEN-FAIL.json").write_text(
            json.dumps([{"file": n, "actual": g, "expected": w, "note": t}
                        for n, g, w, t in sbad], ensure_ascii=False, indent=1),
            encoding="utf-8")
        return
    n_files, miss = count_check()
    # 🚨 24칸이 다 차기 전에는 **계산도 출력도 안 한다.**
    #    처음엔 이 정지가 없어 스모크 테스트가 «한국 C 를 미국보다 먼저» 계산했다.
    #    규칙: **점검용 실행과 결과 산출을 «같은 문»으로 하면, 점검이 결과를 만든다.**
    if miss and os.environ.get("ARM25_ALLOW_PARTIAL") != "1":
        print("\n🚨 **24칸이 다 차지 않았다(%d/24). 계산하지 않고 멈춘다.**" % n_files,
              flush=True)
        print("   (구조 점검만 하려면 `ARM25_ALLOW_PARTIAL=1` — 그때 나온 값은 인용 금지)",
              flush=True)
        return
    idrows, idbad = tie_checks()
    if idbad:
        print("\n🚨 **동점 검산이 깨졌다. 멈춘다 — 결과를 만들지 않는다.**", flush=True)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "30-arm25-TIE-FAIL.json").write_text(
            json.dumps({"rows": idrows, "bad": idbad}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        return

    res, stash, ties = {}, {}, {}
    for mkt, tie in COMBOS:
        ours, gate = load(mkt, tie)
        if not ours or not gate:
            print("🚨 %s/%s 자료 없음" % (mkt, tie), flush=True)
            continue
        key = "%s/%s" % (mkt, tie)
        stash[key] = (ours, gate)
        lab = ("`>` (16번 β1 짝 · **헤드라인**)" if tie == "strict"
               else "`>=` (패턴 팔과 규칙 일치 · **항상 보고하는 민감도**)")
        print("", flush=True)
        print("=" * 78, flush=True)
        print("%s · 동점규칙 %s" % (mkt.upper(), lab), flush=True)
        print("우리 %d거래 · 관문만 풀 %d거래" % (len(ours), len(gate)), flush=True)
        print("=" * 78, flush=True)
        base = per_trade(gate)
        print("  **관문만 팔의 절대 수준: 거래당 %+.4f%%** "
              "(기저가 다르면 「검출기가 무엇 위에 얹혔나」가 달라진다)" % base, flush=True)
        r = c_stat(ours, gate)
        print("  **C(전체 − 관문만) = %+.4f%%p** (95%% %+.4f ~ %+.4f · MDE %.4f)"
              % (r["C_mean"], r["ci_lo"], r["ci_hi"], r["mde"]), flush=True)
        print("    스트림 10개 범위 %+.4f ~ %+.4f · 추첨 평균 %.0f건 · 풀 부족 %.0f건(%.0f일)"
              % (r["C_stream_min"], r["C_stream_max"], r["n_drawn"],
                 r["short_trades"], r["short_days"]), flush=True)
        eq = max(abs(r["C_mean"]), abs(r["ci_lo"]), abs(r["ci_hi"])) < EQUIV
        print("    동등성 문턱 |C| < %.3f%%p : %s"
              % (EQUIV, "충족" if eq else "**미충족** — 기각도 동등도 아니다"), flush=True)
        ra = c_stat(ours, gate, by_atr=True)
        print("  **ATR 구간 맞춤판 C = %+.4f%%p** (95%% %+.4f ~ %+.4f) · 풀 부족 %.0f건"
              % (ra["C_mean"], ra["ci_lo"], ra["ci_hi"], ra["short_trades"]), flush=True)
        print("  순서 고정 분해 (VCP → 3C → PP · **한계 기여**로만 읽는다)", flush=True)
        dc = decomp(ours, gate)
        wb = workb(r["streams"], mkt)
        if tie == "strict":
            tr = tie_rate(mkt)
            ctrl_pt = st.mean(per_trade(g) for g in r["streams"])
            dlo, dhi, dbound = diff_ci(tie_shadow(mkt), r["streams"])
            tr["ctrl_per_trade"] = ctrl_pt
            tr["diff_ci"] = [dlo, dhi]
            if dbound is not None and tr["pct_of_touch"] is not None:
                tr["delta_point"] = (tr["pct_of_touch"] / 100.0) * (
                    tr["shadow_per_trade"] - ctrl_pt)
                tr["delta"] = (tr["pct_of_touch"] / 100.0) * dbound
            else:
                tr["delta_point"] = tr["delta"] = None
            ties[mkt] = tr
            print("  [동점] 닿은 %d건(진입 %d + 동점 %d) 중 동점 **%.3f%%** ← 문턱 대상 · "
                  "후보 %d 대비 %.3f%%(참고)"
                  % (tr["n_entered"] + tr["n_tie"], tr["n_entered"], tr["n_tie"],
                     tr["pct_of_touch"] or 0, tr["n_candidates"],
                     tr["pct_of_candidates"] or 0), flush=True)
            print("        그림자 거래 **%d건** · 거래당 %s · 대조군 거래당 %+.4f%%"
                  % (tr["n_shadow"],
                     ("%+.4f%%" % tr["shadow_per_trade"])
                     if tr["shadow_per_trade"] is not None else "없음", ctrl_pt),
                  flush=True)
            if tr["delta"] is not None:
                print("        차이 95%% %+.4f ~ %+.4f · 바깥 끝 %.4f → "
                      "**Δ_bound = %.4f%%p** (점추정 %+.4f%%p)"
                      % (dlo, dhi, dbound, tr["delta"], tr["delta_point"]), flush=True)
            if tr["n_shadow"] <= 99:
                print("        ⚠️ 그림자 거래가 두 자릿수 이하다 — **한계 문단에 적는다.**",
                      flush=True)
        r.pop("streams", None)
        ra.pop("streams", None)
        res[key] = {"gate_level": base, "C": r, "C_atr": ra, "decomp": dc,
                    "workB_extreme_in_draw": wb,
                    **({"tie": ties[mkt]} if tie == "strict" else {})}

    # ── 두 동점 규칙 나란히 ────────────────────────────────────────────────
    print("", flush=True)
    print("=" * 78, flush=True)
    print("**두 동점 규칙 나란히 — 결과를 보고 고르지 않는다**", flush=True)
    print("=" * 78, flush=True)
    for m in ("kr", "us"):
        a, b = res.get("%s/strict" % m), res.get("%s/ge" % m)
        if not (a and b):
            continue
        print("  %-3s  `>`  C %+8.4f%%p (%+.3f~%+.3f)   `>=` C %+8.4f%%p (%+.3f~%+.3f)   "
              "두 판 차이 **%+.4f%%p**"
              % (m.upper(), a["C"]["C_mean"], a["C"]["ci_lo"], a["C"]["ci_hi"],
                 b["C"]["C_mean"], b["C"]["ci_lo"], b["C"]["ci_hi"],
                 b["C"]["C_mean"] - a["C"]["C_mean"]), flush=True)
    print("  ⚠️ `>` = 16번 β1 과 **짝이 맞는 판** · `>=` = 패턴 팔과 **규칙이 같은 판**. "
          "서로 다른 미덕이다.", flush=True)

    # ── Δ 예측 vs 관측 (짝비교) ────────────────────────────────────────────
    print("", flush=True)
    print("  **예측 Δ vs 관측 |C_> − C_>=|** — 구간을 붙이지 않는다(Δ는 예측, Δ_bound는 천장)",
          flush=True)
    print("     ⚠️ 동점은 «더해지기만» 하지 않는다 — 들어오면서 다른 진입을 «밀어낸다».",
          flush=True)
    print("        두 항이 부분 상쇄되므로 **Δ는 과대예측**이다. **상한으로만** 쓴다.",
          flush=True)
    for m in ("kr", "us"):
        t = ties.get(m)
        a, b = res.get("%s/strict" % m), res.get("%s/ge" % m)
        if not (t and a and b):
            continue
        pr = paired_tie_diff(stash["%s/strict" % m][0], stash["%s/strict" % m][1],
                             stash["%s/ge" % m][1])
        obs = abs(pr["median"]) if pr else abs(b["C"]["C_mean"] - a["C"]["C_mean"])
        ceil_ = t.get("delta")
        c_used = ceil_ if ceil_ is not None else 0.2
        over = obs > c_used
        print("   %-3s 관측(짝비교 중앙) **%+.4f%%p** · 예측 Δ %.4f%%p · 천장 %s → %s"
              % (m.upper(), pr["median"] if pr else obs,
                 abs(t.get("delta_point") or 0),
                 ("%.4f%%p" % ceil_) if ceil_ is not None else "계산 불가(대체 0.2000%p)",
                 ("🚨**천장 초과 %.4f%%p = 구현 오류**" % (obs - c_used)) if over
                 else "천장 이내(여유 %.4f%%p)" % (c_used - obs)), flush=True)
        if pr:
            weak = pr["spread"] > max(abs(t.get("delta_point") or 0), 1e-12)
            print("       짝비교 95%% %+.4f ~ %+.4f (퍼짐 **%.4f%%p**) · "
                  "스트림 평균 퍼짐 %.4f%%p"
                  % (pr["p2.5"], pr["p97.5"], pr["spread"], pr["stream_spread"] or 0),
                  flush=True)
            print("       → %s" % ("🚨**퍼짐 > Δ — 이 표본에서 탐지기는 무력하다. "
                                   "억지로 판정하지 않고 그 사실을 적는다.**" if weak
                                   else "퍼짐 < Δ — **탐지기가 작동한다**"), flush=True)
        res.setdefault("_tie_predict", {})[m] = {
            "observed_paired_median": pr["median"] if pr else None, "paired": pr,
            "predicted_delta": t.get("delta_point"), "ceiling": ceil_,
            "over_ceiling": over}

    if ties.get("kr") and ties.get("us"):
        k, u = ties["kr"], ties["us"]
        print("", flush=True)
        print("  🚨 **동점 비율(닿은 것 대비) — 한국 %.3f%% · 미국 %.3f%% · 차이 %.3f%%p**"
              % (k["pct_of_touch"], u["pct_of_touch"],
                 abs(u["pct_of_touch"] - k["pct_of_touch"])), flush=True)
        print("     호가 단위 차이가 대조군의 «엄격함»에 얼마나 들어오는지의 실측이다. "
              "**문턱 장치는 없앴다 — 두 판을 무조건 돌린다.**", flush=True)

    if "kr/strict" in res and "us/strict" in res:
        d = res["us/strict"]["C"]["C_mean"] - res["kr/strict"]["C"]["C_mean"]
        print("", flush=True)
        print("  교호작용 C_US − C_KR = **%+.4f%%p** — **둘이 갈릴 때만 쓴다**" % d,
              flush=True)
        res["_interaction"] = d

    res["_preflight"] = {"n_files": n_files, "missing": miss}
    res["_tie_checks"] = idrows
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "30-arm25.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/30-arm25.json", flush=True)
    print("🚨 3C·PP 는 **사전 판정불가**(MDE 3.2 / 8.4%p). 「PP가 +N%p」류를 쓰지 않는다.",
          flush=True)


if __name__ == "__main__":
    main()

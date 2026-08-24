# -*- coding: utf-8 -*-
"""30 · **2.5단계 — 검출기 몫 `C` 를 양 시장 나란히** (이 과제에서 판정력이 있는 유일한 팔).

사전등록 (두뇌 세션 확정)
-------------------------
- **헤드라인 = 「양 시장의 C 를 나란히」.** 교호작용(`C_US − C_KR`)은 **둘이 갈릴 때만** 쓴다.
- **검정은 「전체 vs 관문만」 하나.** `+VCP`·`+3C`·`+PP` 는 **분해이지 검정이 아니다.**
- **축은 «거래당»이다.** 슬롯5 자산 금지 — 팔마다 거래 수가 자릿수로 달라 자산으로 재면
  차이 대부분이 **거래 수**에서 온다.
- **동등성 문턱 `|C| < 0.090%p`** 여야 「값을 안 한다」고 쓸 수 있다.

이식할 때 「같아야 하는 넷」 (유형 18 짝 규칙)
---------------------------------------------
1. **관문만 팔의 방아쇠는 β1** — 스캔일 D 당일 고가, **동점이면 진입 없음(엄격 `>`)**.
   `backtest_volatility_pilot_us.py` 의 `ARM=="gate"` 분기가 그렇게 돼 있다.
   ⚠️ **패턴 팔은 동점에 진입한다**(`hi < pivot` 이면 건너뜀). 이 차이는 **설계상 그대로 둔다** —
   대조군을 우리 쪽에 맞추면 대조군이 아니게 된다.
2. **추첨 건수를 날짜별로 맞춘다.** 그날 우리 진입이 k건이면 대조군도 그날에서 k건 뽑는다.
   풀이 모자라면 **부족분을 세어 보고**한다(조용히 줄이지 않는다).
3. **다중 스트림(M32-2): 10 스트림 × 100회.** 복제마다 **스트림 먼저 고르고** 날짜 블록 재추출.
   🚨 **단일 스트림 구간은 폐기 대상이다** — 16번에서 스트림만 바꿔 라벨이 뒤집혔다.
4. **ATR 구간 맞춤 팔** — 원판·맞춤판 둘 다 낸다.

순서 고정 분해에 붙이는 주의 (라벨의 일부다)
--------------------------------------------
하네스는 `for pname in ("VCP", "3C", "PP")` 순으로 돌다가 **먼저 진입하면 `open_until` 로
나머지를 막는다.** 그래서 세 몫은 **한계 기여**다:
- ✅ **"VCP 다음에 3C가 더해 주는 몫"** ← 이렇게만 쓴다
- ❌ **"3C 단독의 값어치"** ← 쓰지 않는다. 순서가 만든 말이다
- **세 몫을 서로 비교하지 않는다.** PP 는 앞의 둘이 흡수한 뒤 남은 것이다.
- **팔이 중첩이라 구간을 더하지 않는다.**
🚨 **사전 판정: VCP(n 2,949) MDE 1.6%p · 3C(723) 3.2%p · PP(104) 8.4%p
   → 잴 수 있는 건 VCP 뿐이다. 3C·PP 는 어떤 값이 나와도 판정불가다.**

작업 B — 대조군이 **실제로 추첨한** 종목-일의 극단값 노출
--------------------------------------------------------
가짜 상승 바 하나가 대조군에 들어가면 대조군이 좋아지고 C 가 더 마이너스로 간다.
**추첨 집합에 극단 목록(27번)이 든 횟수**를 스트림별로 센다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/30-arm25.py
난수 seed: 스트림 300824+s · 블록 부트스트랩 300924
"""
from __future__ import annotations

import json
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
EQUIV = 0.090          # 동등성 문턱 %p
PATTERN_ORDER = ("VCP", "3C", "PP")


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


def load(mkt, tie="strict"):
    sfx = "" if tie == "strict" else "ge"
    if mkt == "kr":
        ours = []
        for y in range(2021, 2027):
            f = BT / ("bt_%d.json" % y)
            if f.exists():
                ours += json.loads(f.read_text(encoding="utf-8"))["events"]
        gfs = sorted((BT / "sub").glob("kr_gate%s_*.json" % sfx))
    else:
        f = BT / "sub" / "us_full.json"
        if not f.exists():
            return None, None
        ours = json.loads(f.read_text(encoding="utf-8"))["events"]
        gfs = sorted((BT / "sub").glob("us_gate%s_*.json" % sfx))
    if not gfs:
        return dedupe(ours), None
    gate = []
    for f in gfs:                       # 연도별로 쪼개 돌린 산출물을 합친다
        gate += json.loads(f.read_text(encoding="utf-8"))["events"]
    print("  관문만 팔 파일 %d개 합침: %s"
          % (len(gfs), ", ".join(f.stem for f in gfs)), flush=True)
    return dedupe(ours), dedupe(gate)


def draw(ours, gate, seed, by_atr=False):
    """날짜별로 우리 건수만큼 대조군을 뽑는다. ATR 맞춤이면 구간 안에서 뽑는다.

    반환 (뽑힌 목록, 부족 건수, 부족한 날 수)."""
    pool = defaultdict(list)
    for e in gate:
        k = (e["entry_date"], e.get("atr_band")) if by_atr else e["entry_date"]
        pool[k].append(e)
    need = defaultdict(int)
    for e in ours:
        k = (e["entry_date"], e.get("atr_band")) if by_atr else e["entry_date"]
        need[k] += 1
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


def per_trade(rows):
    return st.mean(slot_sim.net(e["gain_at_resolve_pct"]) for e in rows)


def blocks(dates, rnd):
    n = len(dates)
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(*BLOCK)
        a = rnd.randint(0, max(0, n - L))
        out.append((a, min(L, n - tot)))
        tot += L
    return out


def diff_ci(shadow, streams):
    """(동점 그림자 거래당 − 대조군 거래당) 의 **자료 축 95% 구간**.

    🚨 원칙: **방아쇠는 「영향이 있다고 확인될 때」가 아니라
       「영향이 없다고 «배제할 수 없을» 때」 켜진다.**
    그래서 점추정이 아니라 **구간의 바깥 끝**을 쓴다. 동점이 적어 구간이 넓어지면
    상한이 커지고 **민감도가 켜진다** — 그게 옳은 방향이다.
    (검정력 부족이 「안전 신호」로 둔갑하는 것을 막는다.)

    복제마다 **스트림을 먼저 고르고** 날짜 블록을 재추출한다(c_stat 과 같은 형태).
    """
    if not shadow or not streams:
        return None, None, None
    sh = defaultdict(list)
    for e in shadow:
        sh[e["entry_date"]].append(slot_sim.net(e["gain_at_resolve_pct"]))
    ct = []
    for g in streams:
        d = defaultdict(list)
        for e in g:
            d[e["entry_date"]].append(slot_sim.net(e["gain_at_resolve_pct"]))
        ct.append(d)
    dates = sorted(set(sh) | set().union(*[set(d) for d in ct]))
    rnd = random.Random(BOOT_SEED + 7)
    reps = []
    for r in range(N_STREAM * N_REP):
        st_i = r % N_STREAM
        sa = sc = ca = cc = 0.0
        scn = ccn = 0
        for a, L in blocks(dates, rnd):
            for j in range(L):
                d = dates[a + j]
                v = sh.get(d)
                if v:
                    sa += sum(v)
                    scn += len(v)
                w = ct[st_i].get(d)
                if w:
                    ca += sum(w)
                    ccn += len(w)
        if scn and ccn:
            reps.append(sa / scn - ca / ccn)
    if not reps:
        return None, None, None
    reps.sort()
    lo, hi = reps[int(len(reps) * .025)], reps[int(len(reps) * .975)]
    return lo, hi, max(abs(lo), abs(hi))


def c_stat(ours, gate, by_atr=False):
    """다중 스트림 × 날짜 블록 부트스트랩으로 C 의 구간을 낸다."""
    streams = []
    shorts = []
    for s in range(N_STREAM):
        g, sh, sd = draw(ours, gate, STREAM_SEED + s, by_atr)
        streams.append(g)
        shorts.append((sh, sd))
    obs = [per_trade(ours) - per_trade(g) for g in streams]

    o_by = defaultdict(list)
    for e in ours:
        o_by[e["entry_date"]].append(slot_sim.net(e["gain_at_resolve_pct"]))
    g_by = []
    for g in streams:
        d = defaultdict(list)
        for e in g:
            d[e["entry_date"]].append(slot_sim.net(e["gain_at_resolve_pct"]))
        g_by.append(d)
    dates = sorted(o_by)
    rnd = random.Random(BOOT_SEED)
    reps = []
    for r in range(N_STREAM * N_REP):
        s = r % N_STREAM                     # 🚨 스트림을 먼저 고른다
        bs = blocks(dates, rnd)
        oa = oc = ga = gc = 0.0
        gcn = 0
        for a, L in bs:
            for j in range(L):
                d = dates[a + j]
                v = o_by[d]
                oa += sum(v)
                oc += len(v)
                w = g_by[s].get(d)
                if w:
                    ga += sum(w)
                    gcn += len(w)
        if oc and gcn:
            reps.append(oa / oc - ga / gcn)
    reps.sort()
    lo, hi = reps[int(len(reps) * .025)], reps[int(len(reps) * .975)]
    return {"C_mean": st.mean(obs), "C_by_stream": obs,
            "C_stream_min": min(obs), "C_stream_max": max(obs),
            "ci_lo": lo, "ci_hi": hi, "mde": 2.80 * st.pstdev(reps),
            "n_ours": len(ours), "n_gate_pool": len(gate),
            "n_drawn": st.mean(len(g) for g in streams),
            "short_trades": st.mean(x[0] for x in shorts),
            "short_days": st.mean(x[1] for x in shorts),
            "streams": streams}


def decomp(ours, gate, res_full):
    """순서 고정 분해 — 누적 팔(VCP / VCP+3C / 전체)의 C. **한계 기여**로만 읽는다."""
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
    """극단 종목-일 목록. 한국 = 27번 감사(>100%p + 50~100%p), 미국 = G3′ ④ 잔차 전수."""
    ext = set()
    if mkt == "kr":
        for nm in ("27-kr-extreme-audit-100-inf.json", "27-kr-extreme-audit-50-100.json"):
            f = OUT / nm
            if f.exists():
                for h in json.loads(f.read_text(encoding="utf-8"))["hits"]:
                    if abs(h["ret_pct"]) > 90:
                        ext.add((h["code"], h["date"]))
    else:
        f = OUT / "25-g3prime.json"
        if f.exists():
            for h in json.loads(f.read_text(encoding="utf-8")).get("top") or []:
                ext.add((h["code"], h["date"]))
    return ext


def workb(res, mkt):
    """작업 B — 추첨 집합에 극단 종목-일이 든 횟수. **양 시장 모두.**"""
    ext = extreme_list(mkt)
    if not ext:
        print("  [작업 B] %s 극단 목록이 비어 있다 — 먼저 감사를 돌린다." % mkt.upper(),
              flush=True)
        return None
    cnt = []
    for g in res["streams"]:
        cnt.append(sum(1 for e in g if (e["code"], e["entry_date"]) in ext))
    m = st.mean(cnt)
    print("  [작업 B] 추첨 집합에 극단(|하루|>90%%p) 종목-일이 든 횟수 — "
          "목록 %d건 · 스트림별 %s (평균 %.1f)" % (len(ext), cnt, m), flush=True)
    print("        🚨 두 시장의 극단 목록 크기가 자릿수로 다르다 → "
          "**든 횟수를 그대로 비교하지 말 것.** 목록 대비 **%.4f%%** 로 정규화해 읽는다."
          % (m / len(ext) * 100), flush=True)
    return {"list_size": len(ext), "per_stream": cnt, "mean": m,
            "pct_of_list": m / len(ext) * 100}


def tie_shadow(mkt):
    """관문만 팔의 «동점» 그림자 거래(진입 아님). strict 판 하네스가 `tie_events` 로 남긴다."""
    pre = "kr_gate_" if mkt == "kr" else "us_gate_"
    out = []
    for f in sorted((BT / "sub").glob(pre + "*.json")):
        out += json.loads(f.read_text(encoding="utf-8")).get("tie_events") or []
    return [e for e in out if e.get("gain_at_resolve_pct") is not None]


def tie_rate(mkt):
    """🚨 「같아야 하는 넷」의 다섯 번째 — 동점 비율.

    한국은 호가 단위가 굵어 `hi == thr` 이 흔하고, 미국은 1센트라 드물 수 있다.
    비율이 두 시장에서 다르면 **대조군의 엄격함이 다르다** → `C_US − C_KR` 에
    「검출기 차이」가 아니라 **「호가 단위 차이」**가 섞인다.
    사전등록 문턱(결과 보기 전 고정): **두 시장의 차이가 1%p를 넘으면**
    관문만 팔에 `>=` 민감도를 추가로 돌린다. 1%p 이하면 안 돌리고 그 사실을 적는다.
    """
    pre = "kr_gate_" if mkt == "kr" else "us_gate_"     # strict 판에서 읽는다
    tie = cand = ent = 0
    for f in sorted((BT / "sub").glob(pre + "*.json")):
        for p in json.loads(f.read_text(encoding="utf-8")).get("per_date") or []:
            tie += p.get("n_tie") or 0
            ent += p.get("n_entered") or 0
            cand += p.get("n_candidates") or 0
    # 🚨 분모를 둘 다 낸다.
    #   (i) **닿은 것 중 동점** = tie / (진입 + 동점) ← **이게 사전등록 문턱의 대상**이다.
    #       「방아쇠에 닿은 종목-일 가운데 «엄격 >» 때문에 잘려 나가는 비율」이라 대조군의
    #       엄격함을 곧바로 잰다.
    #   (ii) 후보 대비 = tie / 후보 — 「방아쇠에 닿는 빈도」가 섞여 시장 간 비교가 흐려진다.
    touch = ent + tie
    # 그림자 거래(진입 아님) — 「동점을 넣었다면」의 거래당을 낸다
    shadow = tie_shadow(mkt)
    return {"n_tie": tie, "n_entered": ent, "n_candidates": cand,
            "pct_of_touch": (tie / touch * 100 if touch else None),
            "pct_of_candidates": (tie / cand * 100 if cand else None),
            "n_shadow": len(shadow),
            "shadow_per_trade": (per_trade(shadow) if shadow else None)}


def preflight():
    """🚨 24 실행 중 하나가 조용히 빠져도 안 보인다 → **파일 존재를 먼저 센다.**"""
    miss = []
    n = 0
    for mkt in ("kr", "us"):
        for tie, sfx in (("strict", ""), ("ge", "ge")):
            for y in range(2021, 2027):
                f = BT / "sub" / ("%s_gate%s_%d.json" % (mkt, sfx, y))
                if f.exists():
                    n += 1
                else:
                    miss.append("%s/%s/%d" % (mkt, tie, y))
    print("관문만 팔 산출물 **완료 %d/24**" % n, flush=True)
    if miss:
        print("  🚨 빠진 칸 %d개: %s" % (len(miss), ", ".join(miss)), flush=True)
    else:
        print("  빠진 칸 없음 — 네 조합 여섯 해 전부 있다.", flush=True)
    return n, miss


def tie_identity():
    """🚨 **항등식 검산**: `strict 진입 + 동점 == ge 진입`.

    두 실행이 같은 후보·같은 날짜를 봤다면 **반드시** 성립한다.
      성립  = 두 판이 «같은 세계»를 봤다는 증거
      불성립 = 발견이 아니라 **구현 오류**
    3-A 버그 탐지기와 같은 성질이므로 **결정론적 값이다 — 구간을 붙이지 않는다.**
    """
    bad = []
    rows = []
    for mkt in ("kr", "us"):
        for y in range(2021, 2027):
            fs = BT / "sub" / ("%s_gate_%d.json" % (mkt, y))
            fg = BT / "sub" / ("%s_gatege_%d.json" % (mkt, y))
            if not (fs.exists() and fg.exists()):
                continue
            ds = json.loads(fs.read_text(encoding="utf-8"))
            dg = json.loads(fg.read_text(encoding="utf-8"))
            es = sum(p.get("n_entered") or 0 for p in ds.get("per_date") or [])
            ts = sum(p.get("n_tie") or 0 for p in ds.get("per_date") or [])
            eg = sum(p.get("n_entered") or 0 for p in dg.get("per_date") or [])
            ok = (es + ts == eg)
            rows.append({"market": mkt, "year": y, "strict_entered": es,
                         "strict_tie": ts, "ge_entered": eg, "ok": ok,
                         "diff": eg - (es + ts)})
            if not ok:
                bad.append((mkt, y, es, ts, eg))
    print("", flush=True)
    print("**항등 검산 — `strict 진입 + 동점 == ge 진입`** (결정론 · 구간 없음)", flush=True)
    if not rows:
        print("  대조할 짝이 없다.", flush=True)
    elif not bad:
        print("  어긋난 건 **0건** — 두 판이 **같은 후보 집합**을 봤다. (%d개 연도-시장 대조)"
              % len(rows), flush=True)
    else:
        print("  🚨 **어긋남 %d건** — 발견이 아니라 구현 오류다:" % len(bad), flush=True)
        for mkt, y, es, ts, eg in bad:
            print("    %s %d: strict %d + 동점 %d = %d  vs  ge %d (차이 %+d)"
                  % (mkt, y, es, ts, es + ts, eg, eg - es - ts), flush=True)
    return rows, bad


def main():
    res = {}
    ties = {}
    n_files, miss = preflight()
    idrows, idbad = tie_identity()
    if idbad:
        print("", flush=True)
        print("🚨 **항등 검산이 깨졌다. 여기서 멈춘다 — 결과를 만들지 않는다.**", flush=True)
        (OUT / "30-arm25-IDENTITY-FAIL.json").write_text(
            json.dumps({"identity": idrows, "bad": idbad, "missing": miss},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        return
    for mkt in ("kr", "us"):
        ours, gate = load(mkt)
        if ours is None:
            print("🚨 %s: 본 실행 산출물 없음" % mkt.upper(), flush=True)
            continue
        if gate is None:
            print("🚨 %s: 관문만 팔 산출물(`sub/%s_gate_YYYY.json`) 없음 — "
                  "`bash research/handoff/scripts/_gate_run.sh %s` 를 먼저 돌린다."
                  % (mkt.upper(), mkt, mkt), flush=True)
            continue
        print("\n" + "=" * 78, flush=True)
        print("%s · 우리 %d거래 · 관문만 풀 %d거래" % (mkt.upper(), len(ours), len(gate)),
              flush=True)
        print("=" * 78, flush=True)
        base = per_trade(gate)
        print("  **관문만 팔의 절대 수준: 거래당 %+.4f%%** (기저가 다르면 "
              "「검출기가 무엇 위에 얹혔나」가 달라진다)" % base, flush=True)
        r = c_stat(ours, gate)
        print("  **C(전체 − 관문만) = %+.4f%%p** (95%% %+.4f ~ %+.4f · MDE %.4f)"
              % (r["C_mean"], r["ci_lo"], r["ci_hi"], r["mde"]), flush=True)
        print("    스트림 10개 범위 %+.4f ~ %+.4f · 추첨 평균 %.0f건 · "
              "풀 부족 %.0f건(%.0f일)"
              % (r["C_stream_min"], r["C_stream_max"], r["n_drawn"],
                 r["short_trades"], r["short_days"]), flush=True)
        eq = abs(r["C_mean"]) < EQUIV and abs(r["ci_lo"]) < EQUIV and abs(r["ci_hi"]) < EQUIV
        print("    동등성 문턱 |C| < %.3f%%p : %s"
              % (EQUIV, "충족" if eq else "**미충족** — 기각도 동등도 아니다"), flush=True)
        ra = c_stat(ours, gate, by_atr=True)
        print("  **ATR 구간 맞춤판 C = %+.4f%%p** (95%% %+.4f ~ %+.4f) · 풀 부족 %.0f건"
              % (ra["C_mean"], ra["ci_lo"], ra["ci_hi"], ra["short_trades"]), flush=True)
        print("  순서 고정 분해 (VCP → 3C → PP · **한계 기여**로만 읽는다)", flush=True)
        dc = decomp(ours, gate, r)
        wb = workb(r, mkt)
        if tie != "strict":                       # 설명 수치는 strict 판에서 한 번만
            r.pop("streams", None)
            ra.pop("streams", None)
            res[key] = {"gate_level": base, "C": r, "C_atr": ra, "decomp": dc,
                        "workB_extreme_in_draw": wb}
            continue
        tr = tie_rate(mkt)
        # 🚨 **영향 «상한» Δ_bound** (두뇌 세션 정정 사양 · 결과 보기 전 확정):
        #      Δ_bound = 동점비율(닿은 것 대비) × upper95(|동점 그림자 거래당 − 대조군 거래당|)
        #    **점추정이 아니라 구간의 바깥 끝**을 쓴다.
        #    대조군 거래당은 **실제 추첨된 집합**의 평균이다 — 풀 전체를 쓰면 날짜별 추첨
        #    가중이 빠져 **C 와 다른 양**을 재게 된다(두뇌 세션 승인).
        streams = r.get("streams") or []
        ctrl_pt = st.mean(per_trade(g) for g in streams) if streams else base
        shadow = tie_shadow(mkt)
        dlo, dhi, dbound = diff_ci(shadow, streams)
        tr["diff_ci"] = [dlo, dhi]
        tr["diff_bound"] = dbound
        if dbound is not None and tr["pct_of_touch"] is not None:
            tr["delta_point"] = (tr["pct_of_touch"] / 100.0) * (tr["shadow_per_trade"] - ctrl_pt)
            tr["delta"] = (tr["pct_of_touch"] / 100.0) * dbound        # ← 상한
        else:
            tr["delta_point"] = tr["delta"] = None
        tr["ctrl_per_trade"] = ctrl_pt
        ties[mkt] = tr
        print("  [동점] 방아쇠에 닿은 %d건(진입 %d + 동점 %d) 중 동점 **%.3f%%** "
              "← 문턱 대상 · 후보 %d 대비 %.3f%%(참고)"
              % ((tr["n_entered"] + tr["n_tie"]), tr["n_entered"], tr["n_tie"],
                 tr["pct_of_touch"] or 0, tr["n_candidates"],
                 tr["pct_of_candidates"] or 0), flush=True)
        print("        그림자 거래 **%d건** · 거래당 %s · 대조군 거래당 %+.4f%%"
              % (tr["n_shadow"],
                 ("%+.4f%%" % tr["shadow_per_trade"]) if tr["shadow_per_trade"] is not None else "없음",
                 ctrl_pt), flush=True)
        if tr["delta"] is None:
            print("        차이 구간 계산 불가 → **Δ_bound 계산 불가**", flush=True)
        else:
            print("        차이 95%% 구간 %+.4f ~ %+.4f · 바깥 끝 %.4f "
                  "→ **Δ_bound = %.4f%%p** (점추정 %+.4f%%p)"
                  % (dlo, dhi, dbound, tr["delta"], tr["delta_point"]), flush=True)
        if tr["n_shadow"] <= 99:
            print("        ⚠️ 그림자 거래가 두 자릿수 이하다 — **한계 문단에 적는다.**",
                  flush=True)
        r.pop("streams", None)
        ra.pop("streams", None)
        res[key] = {"gate_level": base, "C": r, "C_atr": ra, "decomp": dc,
                    "workB_extreme_in_draw": wb, "tie": tr}
    print("", flush=True)
    print("=" * 78, flush=True)
    print("**두 동점 규칙 나란히 — 결과를 보고 고르지 않는다**", flush=True)
    print("=" * 78, flush=True)
    print("  %-6s %28s %28s" % ("시장", "`>` (헤드라인)", "`>=` (민감도)"), flush=True)
    for m in ("kr", "us"):
        a, b = res.get("%s/strict" % m), res.get("%s/ge" % m)
        if not (a and b):
            continue
        print("  %-6s   C %+8.4f%%p (%+.3f~%+.3f)   C %+8.4f%%p (%+.3f~%+.3f)"
              % (m.upper(), a["C"]["C_mean"], a["C"]["ci_lo"], a["C"]["ci_hi"],
                 b["C"]["C_mean"], b["C"]["ci_lo"], b["C"]["ci_hi"]), flush=True)
        print("         두 판 차이 **%+.4f%%p**"
              % (b["C"]["C_mean"] - a["C"]["C_mean"]), flush=True)
    print("  ⚠️ `>` = 16번 β1 과 **짝이 맞는 판** · `>=` = 패턴 팔과 **규칙이 같은 판**", flush=True)
    print("     서로 다른 미덕이다. **두 판이 일치하면 그 사실 자체가 강한 결과다.**", flush=True)

    if ties.get("kr") and ties.get("us"):
        k, u = ties["kr"], ties["us"]
        gap = abs(u["pct_of_touch"] - k["pct_of_touch"])
        dgap = (abs(u["delta"] - k["delta"])
                if (u["delta"] is not None and k["delta"] is not None) else None)
        print("", flush=True)
        print("  🚨 **동점 — «설명 수치»** (발동 조건이 아니다. 두 판이 갈렸을 때 "
              "**왜 갈렸는지**를 설명한다)", flush=True)
        print("     ① 비율(닿은 것 대비): 한국 %.3f%% · 미국 %.3f%% · **차이 %.3f%%p**"
              % (k["pct_of_touch"], u["pct_of_touch"], gap), flush=True)
        if dgap is None:
            print("     ② 영향 Δ: **계산 불가** (그림자 거래 없음)", flush=True)
        else:
            print("     ② 영향 **상한**: Δ_bound_KR %.4f%%p · Δ_bound_US %.4f%%p · "
                  "|차이| %.4f%%p (참고: MDE 0.701%%p)"
                  % (k["delta"], u["delta"], dgap), flush=True)
        print("     🚨 **문턱 장치는 없앴다.** 조건부 발동 대신 **`>` 와 `>=` 를 둘 다 무조건**"
              " 돌린다.", flush=True)
        print("        규율: **문턱을 하나 더 다는 것보다 둘 다 돌리는 게 싸면, 둘 다 돌린다.**"
              " 판단을 아끼는 게 아니라 **«판단할 필요 자체»를 없앤다.**", flush=True)
        print("        원칙(살려 둔다): 방아쇠는 「영향이 있다고 확인될 때」가 아니라 "
              "**「영향이 없다고 배제할 수 없을 때」** 켜진다 — 이번엔 «무조건 켠다»로 실현됐다.",
              flush=True)
        res["_tie"] = {"kr": k, "us": u, "pct_gap": gap, "delta_gap": dgap,
                       "role": "설명 수치 (발동 조건 아님) — 두 판을 둘 다 돌린다"}
    if "kr/strict" in res and "us/strict" in res:
        d = res["us/strict"]["C"]["C_mean"] - res["kr/strict"]["C"]["C_mean"]
        print("\n  교호작용 C_US − C_KR = **%+.4f%%p** — **둘이 갈릴 때만 쓴다**" % d,
              flush=True)
        res["_interaction"] = d
    res["_preflight"] = {"n_files": n_files, "missing": miss}
    res["_tie_identity"] = idrows
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "30-arm25.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print("\n저장: .cache/bt5y/out/30-arm25.json", flush=True)


if __name__ == "__main__":
    main()

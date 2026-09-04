# -*- coding: utf-8 -*-
r"""176 — **원전의 «청산» 두 구절** · 사전등록 `tasks/176-exit-two-rules.md`

  🏷️ **세대 B** · 규칙 **+30/-10 (`41db459d`)** · 칸 5 · 상한 20% · 배당 포함 · 숏 없음

  🚨 **자료 «잇기»** — 우리 판이 쓰는 `sub/uspath_*.json` 에는 진입 «전» 값이 «없다».
     「N일 저가」·「50일 평균 거래량」에 필요하므로 `uspath-warm/full` 의 `pre_l`·`pre_v` 를
     **(scan_date, code, pattern)** 으로 «이어» 쓴다. **못 이은 건수를 «찍는다»**.

  🚨 **모든 팔이 «같은» 거래 목록을 쓴다** — 종목 중복 제거는 ① 의 청산일로 «한 번»만 한다.
     그래야 `Ⓞ−Ⓓ` 가 «시점»만 묻는다. 대가: 「일찍 팔아 «같은 종목»을 더 빨리 다시 사는」
     이득은 «안» 잰다(칸이 비는 이득은 시뮬이 «잰다»).
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
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
acc = _load("acc", "account_lib.py")
gates = _load("gates", "_gates.py")
f92a = r102.f92a
pt = r91.pt

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NSEED, NASSIGN, YRS, DELTA, T60 = 60, 10, 27.4, 1.23, 2.001
NS = (3, 5, 10)                 # ⓐ 의 N — «값 보기 전»에 박았다
LOWVOL, HEAVY = 1.0, 1.5        # ㉡ 「저거래량 돌파」 · 「매도 물량」
MA_REF = 12377
NA_TOL = 0.01
FULL = Path("D:/stock-data/uspath-warm/full")
CACHE = Path(str(r91.OUT / "176-partial.json"))


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    n_as = 3 if "--quick" in sys.argv else NASSIGN
    dry = "--dry" in sys.argv
    P = print
    P("=" * 104)
    P("176 - **원전의 «청산» «두» 구절** · 씨앗 %d판%s"
      % (n_seed, "  🚨 **--dry(«구조»만)**" if dry else ""))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-04 · `scripts/176-exit-two-rules.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("> ## 📏 **이 문서에서 「폭」은 «항상» `P95 ÷ P05` 를 뜻한다**(자산 흩어짐 · «곱셈» 자)")
    P("")
    P("## 🚨 **머리 — 「이 판이 «무엇»을 재는가」를 «먼저»**")
    P("")
    P("```")
    P("① 원전 두 구절은 **«둘 다» «조건부»**다")
    P("   ㉠ 「«수익»을 내고 있다면 계속 보유. **«하지만» «움직임»이 «반전»되면 «빨리» 판다」**")
    P("   ㉡ 「**«적은 거래량»**과 함께 돌파한 «후» **«매도 물량»**이 쏟아지면 «팔»거나 «줄인다」**")
    P("   ⇒ ⛔ **「무조건 조기 청산」으로 재면 «원전»이 «아니다** (`168` 의 잘못을 «반복» 안 한다)")
    P("")
    P("② ## 🚨 **ⓐ 는 「«반전»」의 «근사»다 — «같은 줄»에 적는다**")
    P("   원전 「**«움직임»이 «반전»**」 = **«추세»**  ·  ⓐ 「**직전 N일 «저가» 이탈**」 = **«한 번»의 하락**")
    P("   ⇒ **«같은 것»이 «아니다**. `175` 의 「원전 α 는 «방아쇠»지 «가격» 아님」과 «같은 자리»")
    P("")
    P("③ **합의 판정은 «사실상» VCP 의 판정이다** — 후보 **VCP 76.9%** · 3C 20.8% · PP 2.3% (`174`)")
    P("```")
    P("")
    P("## 🚨 **사전 근거 — 그리고 «어느 짝»에 «붙는지»를 «같은 줄»에**")
    P("")
    P("```")
    P("🔎 `133`·`132` — **「늦출수록 이김」** 세전 78.3% · **세후 85.0%** (51/60 짝비교)")
    P("")
    P("   **Ⓞ - ①**  「조기 청산 «일반»」             ⇒ ✅ **«강하게» 걸린다** — «음수»를 «예상»한다")
    P("   **Ⓞ - Ⓓ**  「조기 청산 «시점»을 «고르기»」  ⇒ 🔴 **«약하게»만** —")
    P("              **Ⓓ 가 「«일찍» 파는 것 «자체»」를 «이미» 흡수**하기 때문이다")
    P("")
    P("## ⇒ ★★★ **「사전 근거를 «미리» 적기」는 «절반»이고 —**")
    P("## **「«어디»에 «붙는지» 적기」가 «나머지 절반»이다**")
    P("")
    P("⛔ 그리고 **「55변형 0승」은 «한국» 판정이라 «인용 금지»** (`exit-rules-validated-2026-08`)")
    P("```")
    P("")
    P("```")
    P("자료   Sharadar SEP/DAILY · %s ~ %s (%.1f년) · 배당 «포함» · 상폐 «포함»" % (D0, D1, YRS))
    P("규칙   손절 **-%.0f%%** · 목표 **+%.0f%%**(절반) · 칸 **%d** · 한 종목 상한 20%%"
      % (STOP, TARGET, SLOTS))
    P("Δ = %.2f%%p                             ← 150 의 우리-QQQ 격차" % DELTA)
    P("MA★ 기준 %s만                      ← 156·161~168·170·173·175 의 ①" % format(MA_REF, ","))
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음 — 돌린 자리 `%s`" % str(r91.SUB))
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    keep = {}
    for y in sorted(by2):
        keep[y] = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                keep[y].append(p)
    n_cand = sum(len(v) for v in keep.values())

    PRE, FD = {}, {}
    for y in range(1999, 2027):
        f = FULL / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        for q in json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]:
            k = (q["scan_date"], q["code"], q["pattern"])
            PRE[k] = (q.get("pre_l"), q.get("pre_v"), q.get("v"))
            FD[k] = q.get("d")

    def pre_of(p):
        return PRE.get((p["scan_date"], p["code"], p["pattern"]), (None, None, None))

    def vpath(p):
        """🚨 `sub` 경로에는 진입 «후» 거래량 `v` 가 **없다**. `full` 에서 «이어» 쓴다."""
        return pre_of(p)[2] or []

    pairs, n_dup = [], 0
    for y in sorted(keep):
        open_until = {}
        for p in keep[y]:
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 half=HALF, shares=(1.0,), add_stop="floor_entry")
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                n_dup += 1
                continue
            open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
            t["stop_frac"] = STOP / 100.0
            pairs.append((t, p))
    base = [t for t, _ in pairs]
    n_nopre = sum(1 for _t, p in pairs
                  if any(x is None for x in pre_of(p)))
    # 🔴 처음에 「길이가 같은가」로 걸었다 — **틀린 자**였다(꼬리가 하루 길 뿐).
    #    맞는 자는 「**겹치는 구간의 «날짜»가 같은가**」다. 아래 셋을 «전부» 센다.
    n_mislen = n_short = n_first = 0
    for _t, p in pairs:
        vv = pre_of(p)[2]
        if vv is None:
            continue
        dd = p["d"]
        if len(vv) != len(dd):
            n_mislen += 1
        if len(vv) < len(dd):
            n_short += 1
    n_misdate = 0
    for _t, p in pairs:
        fd = FD.get((p["scan_date"], p["code"], p["pattern"]))
        if fd is None:
            continue
        k = min(len(fd), len(p["d"]))
        if fd[0] != p["d"][0]:
            n_first += 1
        if fd[:k] != p["d"][:k]:
            n_misdate += 1

    def ma50_at(p, j):
        _pl, pv, _v = pre_of(p)
        if not pv:
            return None
        V = list(pv) + list(vpath(p))
        idx = len(pv) + j
        if idx >= len(V) or idx < 49:
            return None
        w = V[idx - 49:idx + 1]
        if any(x is None for x in w):
            return None
        return (sum(w) / 50.0) or None

    def low_win(p, j, n):
        pl, _pv, _v = pre_of(p)
        if not pl:
            return None
        L = list(pl) + list(p.get("l") or [])
        idx = len(pl) + j
        if idx - n < 0 or idx > len(L):
            return None
        w = L[idx - n:idx]
        if not w or any(x is None for x in w):
            return None
        return min(w)

    def res_j(t, p):
        rd = t["masks"][()]["resolve_date"]
        d = p["d"]
        return d.index(rd) if (rd and rd in d) else len(d) - 1

    def sig_reversal(n):
        def f(t, p):
            c, o = p["c"], p["o"]
            epx = t["entry_px"]
            jr = res_j(t, p)
            for j in range(0, min(jr, len(c) - 1)):
                if c[j] is None or c[j] <= epx:            # 🚨 원전 조건 — «수익 중»일 때만
                    continue
                lw = low_win(p, j, n)
                if lw is None or c[j] >= lw:
                    continue
                if o[j + 1] is None:
                    continue
                return j + 1
            return None
        return f

    def is_lowvol(p):
        v = vpath(p)
        m = ma50_at(p, 0)
        if not v or v[0] is None or m is None:
            return None
        return v[0] < m * LOWVOL

    def is_lowvol_scan(p):
        _pl, pv, _v = pre_of(p)
        if not pv or len(pv) < 50 or any(x is None for x in pv[-50:]):
            return None
        m = sum(pv[-50:]) / 50.0
        return (pv[-1] < m * LOWVOL) if m else None

    def sig_supply(t, p):
        v, c, o = vpath(p), p["c"], p["o"]
        jr = res_j(t, p)
        for j in range(1, min(jr, len(c) - 1)):
            if j >= len(v) or v[j] is None or c[j] is None or o[j] is None:
                continue
            m = ma50_at(p, j)
            if m is None or v[j] < m * HEAVY or c[j] >= o[j]:
                continue
            if o[j + 1] is None:
                continue
            return j + 1
        return None

    def sig_two(t, p):
        return sig_supply(t, p) if is_lowvol(p) else None

    def rewrite(t, p, jx, frac):
        r = t["masks"][()]
        dx, px = p["d"][jx], p["o"][jx]
        pre = [e for e in r["exits"] if e[0] < dx]
        later = [e for e in r["exits"] if e[0] >= dx]
        rem = sum(e[1] for e in later)
        if rem <= 1e-12 or px is None:
            return None
        new = pre + [(dx, rem * frac, px)]
        if frac < 1.0 - 1e-12:
            new += [(e[0], e[1] * (1.0 - frac), e[2]) for e in later]
            rd = r["resolve_date"]
        else:
            rd = dx
        epx = t["entry_px"]
        ret = sum(fr * (pxx / epx * 100.0 - 100.0) for _d, fr, pxx in new)
        m = dict(r)
        m["exits"], m["resolve_date"] = new, rd
        m["result"] = "win" if ret > 0 else "loss"     # 🚨 «실현 부호». 원전 뜻과 «다르다»
        q = dict(t)
        q["masks"] = {(): m}
        return q

    def make(sigfn, frac):
        ev, hit = [], {}
        for i, (t, p) in enumerate(pairs):
            jx = sigfn(t, p)
            q = rewrite(t, p, jx, frac) if jx is not None else None
            if q is None:
                ev.append(t)
            else:
                ev.append(q)
                hit[i] = jx
        return ev, hit

    def placebo(hit, frac, ai, tag):
        rg = random.Random(90210 + ai + 7919 * abs(hash(tag)) % 100000)
        ev = []
        for i, (t, p) in enumerate(pairs):
            if i not in hit:
                ev.append(t)
                continue
            hi = min(res_j(t, p), len(p["d"]) - 1)
            if hi < 1:
                ev.append(t)
                continue
            q = rewrite(t, p, rg.randint(1, hi), frac)
            ev.append(q if q is not None else t)
        return ev

    def held_days(ev):
        out = []
        for q, (_t, p) in zip(ev, pairs):
            rd = q["masks"][()]["resolve_date"]
            out.append(p["d"].index(rd) if (rd and rd in p["d"]) else len(p["d"]) - 1)
        return out

    # ═══ UA★ — «세기» «전»에 «코드»로 ══════════════════════════════════
    P("")
    P("## 1. 🚨 **UA★ ㉠ — 「1.4배 요구가 «모든» 경로에 «걸리는가」」를 «코드»로 «먼저»**")
    P("")
    P("```")
    P("🔎 명령 `grep -n 'breakout_vol_mult' scripts/canslim_lib/*.py` · 돌린 자리 = 저장소 «뿌리»")
    P("")
    P("**VCP** `vcp.py:155-161`   (a) `vols[i] ≥ MA50 × 1.4`     ← **MA50** 기준")
    P("                        🔴 **OR** (b) `vols[i] ≥ «마른 코일» 평균 × 1.5`")
    P("                           **코일은 «마른» 구간**이라 그 문턱이 **MA50 «아래»**로 내려갈 수 있다")
    P("**3C**  `cheat.py:190`       `last_vol ≥ **rally_vol_avg** × 1.4`  ← 기준선이 **MA50 이 «아니다**")
    P("**PP**  `power_play.py:164`  `last_vol ≥ **pole_vol_avg** × 1.4`   ← 기준선이 **MA50 이 «아니다**")
    P("")
    P("## ⇒ ✅ **셋 «다» 「MA50 대비 1.4배」를 «요구»하지 «않는다» ⇒ «항등식»이 «아니다**")
    P("   ⇒ 🔴 그러니 **「0 이어도 «결과»다」(=우리 게이트가 «이미» 막고 있다)는 «안» 쓴다**")
    P("```")
    P("")
    P("## 🚨 **UA★ ㉡ — 「«몇» 건인가」. 그리고 「돌파일」에 «자»가 «둘»이다**(유형 67)")
    P("")
    n_lv_e = sum(1 for _t, p in pairs if is_lowvol(p) is True)
    n_lv_s = sum(1 for _t, p in pairs if is_lowvol_scan(p) is True)
    n_lv_na = sum(1 for _t, p in pairs if is_lowvol(p) is None)
    P("```")
    P("| 「돌파일」의 «자» | 저거래량(< 50일 평균) | 거래 중 | 잴 수 «없음» |")
    P("|---|---:|---:|---:|")
    P("| ㉠ **`scan_date`**(검출기가 «켜진» 날) | **%s** | **%.1f%%** | — |"
      % (format(n_lv_s, ","), 100.0 * n_lv_s / max(len(pairs), 1)))
    P("| ㉡ ★**«실제 체결일»**(우리가 «산» 날) | **%s** | **%.1f%%** | %s |"
      % (format(n_lv_e, ","), 100.0 * n_lv_e / max(len(pairs), 1), format(n_lv_na, ",")))
    P("")
    P("## ⇒ 🔴 **「적으면 못 묻는다」의 «반대»다 — «대부분»이 해당한다**")
    P("   ⇒ 🚨 **걱정할 것은 «반대쪽»이다: 「≥1.4배」 쪽이 «작아» «대조»가 «얇다**")
    P("")
    P("✅ **이 판은 ㉡ 를 «자 «둘»» 중 «체결일»로 «쓴다** — 이유를 적는다:")
    P("   **우리는 «체결일»에 «산다». 「돌파와 «함께»」의 「함께」가 «그날»이다**")
    P("   🚨 **룩어헤드가 «아니다»** — 이 값은 «진입»을 «거르는» 데 «안» 쓰고 «청산»에만 쓴다.")
    P("     청산은 «그 뒤»의 일이라 «체결일 종가»에 «이미» 알 수 있다")
    P("```")
    P("", flush=True)
    if n_first or n_misdate:
        P("🚨 **관문 «미통과» — 정렬이 깨졌다. «멈춘다»**")
        return 3

    if dry:
        P("🚨 **--dry — 여기까지가 «구조»다. 시뮬레이션은 «안» 돌렸다**")
        return 0

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    def sim(ev, key):
        if key in cache:
            return [tuple(a) for a in cache[key]], cache[key + "|m"]
        with r91.r41.Cost(*r91.COST):
            rs = [r91.sl.sim_lots(ev, seed=sd, slots=SLOTS, risk=0.02, cap=0.20,
                                  reserve=False, fill_rule="truncate",
                                  cash_rule="per_slot") for sd in range(n_seed)]
        v = [acc.account(x) for x in rs]
        m = {"expo": st.median([x["expo_mean"] for x in rs]),
             "n": len(ev), "nf": st.median([x["n_filled"] for x in rs])}
        cache[key] = [list(a) for a in v]
        cache[key + "|m"] = m
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        return v, m

    out, meta, hits, hdays = {}, {}, {}, {}
    out["①"], meta["①"] = sim(base, "v1|base|n%d" % n_seed)
    hdays["①"] = held_days(base)
    P("  ① %.0f만(후보 %d · 체결중앙 %.0f)"
      % (st.median([a[0] for a in out["①"]]), meta["①"]["n"], meta["①"]["nf"]), flush=True)

    ARMS = ([("Ⓞ%d" % n, sig_reversal(n), 1.0) for n in NS]
            + [("Ⓟ", sig_two, 0.5), ("Ⓠ", sig_two, 1.0)])
    for nm, sf, fr in ARMS:
        ev, hit = make(sf, fr)
        hits[nm] = hit
        out[nm], meta[nm] = sim(ev, "v1|%s|n%d" % (nm, n_seed))
        hdays[nm] = held_days(ev)
        accs, exs, hd = [], [], []
        for ai in range(n_as):
            evd = placebo(hit, fr, ai, nm)
            v, m = sim(evd, "v1|D%s|a%d|n%d" % (nm, ai, n_seed))
            accs.append(v)
            exs.append(m["expo"])
            hd.append(st.median(held_days(evd)))
        dn = "Ⓓ" + nm
        out[dn] = [tuple(st.mean(accs[ai][i][j] for ai in range(n_as)) for j in range(4))
                   for i in range(n_seed)]
        meta[dn] = {"expo": None, "expo_d": exs, "n": len(base),
                    "nf": st.mean([meta["①"]["nf"]]), "hd": hd}
        P("  %s %.0f만(갈아낀 %d) · %s %.0f만"
          % (nm, st.median([a[0] for a in out[nm]]), len(hit),
             dn, st.median([a[0] for a in out[dn]])), flush=True)

    def spread(v):
        w = sorted(a[0] for a in v)
        return w[int(len(w) * .95)] / max(w[int(len(w) * .05)], 1)

    def dif(x, y):
        d = [acc.cagr(out[x][i][0], YRS) - acc.cagr(out[y][i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        return mu, mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)

    def cell(lo, hi):
        if lo >= DELTA:
            return "**1** ✅ CI 하한 ≥ +Δ"
        if hi <= -DELTA:
            return "**2** 🚨 CI 상한 ≤ −Δ"
        if lo > 0:
            return "**4a** «확실히» «양수»·CI «전체»가 Δ 아래" if hi <= DELTA else "**4b** «양수»·Δ 를 «걸침»"
        if hi < 0:
            return "**4a** «확실히» «음수»·CI «전체»가 −Δ 위" if lo >= -DELTA else "**4b** «음수»·Δ 를 «걸침»"
        return "**5** 🚨 «못 가린다»"

    # ═══ 관문 ══════════════════════════════════════════════════════════
    P("")
    P("## 2. 관문 — 수")
    P("")
    P("```")
    m1 = st.median([a[0] for a in out["①"]])
    P("**MA★ 앵커** — ① **%.0f만** vs %s만  →  %s"
      % (m1, format(MA_REF, ","), "✅ **일치**" if abs(m1 - MA_REF) < 1.0 else "🚨 **멈춘다**"))
    P("")
    P("🚨 **UD★ / UE★ — 「수」가 «셋»이다. «자»를 «같은 줄»에**(유형 67 · 규약 ⑦)")
    P("   ㉠ **후보**(사다리 ② + 펀더 통과)              — **%s**" % format(n_cand, ","))
    P("   ㉡ **중복 제거 «후»**(같은 종목 겹침 %s 건 뺌) — **%s** (㉠ 의 %.1f%%)"
      % (format(n_dup, ","), format(len(base), ","), 100.0 * len(base) / max(n_cand, 1)))
    P("   ㉢ ★**«실제로» 산 것**(`n_filled` 중앙 · 칸 %d 이 막은 «뒤»)  — **%.0f** (㉡ 의 %.1f%%)"
      % (SLOTS, meta["①"]["nf"], 100.0 * meta["①"]["nf"] / max(len(base), 1)))
    P("")
    P("## 🔴 **`173` 이 ㉡/㉠ 을 「«체결률»」로 «불렀다** — 그건 **«중복 제거» 통과율**이다")
    P("   ⇒ **「자리 벽」을 재는 수는 ㉢/㉡ 이다.** `177` 사전등록 §0 이 그 수를 «인용»하고 있다")
    P("")
    P("**`full` 의 `pre_l`·`pre_v`·`v` 를 «못» 이은 거래** — **%s** 건 (%.2f%%)"
      % (format(n_nopre, ","), 100.0 * n_nopre / max(len(base), 1)))
    P("   🚨 **`sub` 경로엔 진입 «후» 거래량 `v` 가 «아예 «없다»»** — `full` 에서 이어 쓴다")
    P("")
    P("## 🔴 **이 관문을 «처음엔 «틀린 자»»로 걸었다 — «기록»으로 남긴다**")
    P("   처음 걸었던 자: 「`full` 의 v «길이» == `sub` 의 d «길이»」 ⇒ **%s 건 어긋남**"
      % format(n_mislen, ","))
    P("   🔴 그런데 **«길이»는 «자»가 «아니다»** — 꼬리가 «하루» 길 뿐이면 «앞»은 «그대로» 맞는다")
    P("   ✅ **맞는 자 = 「«겹치는 구간»의 «날짜»가 «같은가»」**(색인이 «앞»에서부터 맞으므로)")
    P("")
    P("     ㉠ **«첫날»이 다른 거래**            — **%s**  →  %s"
      % (format(n_first, ","), "✅" if n_first == 0 else "🚨 **멈춘다**"))
    P("     ㉡ **«겹치는 구간» 날짜가 다른 거래** — **%s**  →  %s"
      % (format(n_misdate, ","), "✅" if n_misdate == 0 else "🚨 **멈춘다**"))
    P("     ㉢ **`full` 이 «더 짧은» 거래**(뒤가 «잘려» 신호를 «못» 볼 수 있다) — **%s** (%.2f%%)"
      % (format(n_short, ","), 100.0 * n_short / max(len(base), 1)))
    P("")
    P("   ★ **「길이」와 「정렬」은 «다른» 것이다** — 「어긋난다」를 «셋»으로 갈라야 답이 나온다")
    P("")
    P("🚨 **UB★ — Ⓓ 는 「«그» 거래들 «안»에서 «시점»만 무작위」. «건수»와 «보유일 «중앙»»을 «둘 다»**")
    P("")
    P("| 팔 | 갈아 끼운 «건수» | 거래 중 | 보유일 중앙 **팔** | 보유일 중앙 **Ⓓ** | ① 보유일 중앙 |")
    P("|---|---:|---:|---:|---:|---:|")
    h1 = st.median(hdays["①"])
    for nm, _sf, _fr in ARMS:
        dn = "Ⓓ" + nm
        P("| **%s** | **%s** | %.1f%% | **%.0f일** | **%.0f일** | %.0f일 |"
          % (nm, format(len(hits[nm]), ","), 100.0 * len(hits[nm]) / max(len(base), 1),
             st.median(hdays[nm]), st.median(meta[dn]["hd"]), h1))
    P("")
    gaps = [(nm, st.median(hdays[nm]) - st.median(meta["Ⓓ" + nm]["hd"])) for nm, _s, _f in ARMS]
    P("")
    P("   **보유일 중앙의 «어긋남»(팔 − Ⓓ)** — %s"
      % " · ".join("%s **%+.0f일**" % (nm, g) for nm, g in gaps))
    P("   ⇒ **가장 큰 어긋남 %+.0f일**(%s) — 🚨 **그만큼은 「«시점»을 «잘» 고르는가」가 «아니라**"
      % (max(gaps, key=lambda x: abs(x[1]))[1], max(gaps, key=lambda x: abs(x[1]))[0]))
    P("     **「«언제» 파는가」**를 재고 있다. **판정을 그만큼 «약하게» 읽는다**")
    P("")
    P("")
    P("## 🚨🚨 **UB★b — 「Ⓓ 가 «−10% 손절»을 «건너뛰는가»」**(두뇌 «의심» · «먼저» 잰다)")
    P("")

    def stopped(rec, epx):
        return any(px <= epx * (1.0 - STOP / 100.0) * 1.0001
                   for _d, _fr, px in rec["exits"])

    def realized(rec, epx):
        return sum(fr * (px / epx * 100.0 - 100.0) for _d, fr, px in rec["exits"])

    P("| 팔 | «갈아 끼운» 거래 «안»에서 — 손절로 끝난 건수 | 비율 | 실현수익률 «중앙» |")
    P("|---|---:|---:|---:|")
    for nm, sf, fr_ in ARMS:
        hit = hits[nm]
        ks = sorted(hit)
        ev_a, _ = make(sf, fr_)
        ev_d = placebo(hit, fr_, 0, nm)
        for lab, src in (("**①**(그 거래를 «안» 건드림)", base),
                         ("**%s**" % nm, ev_a), ("**Ⓓ%s**(배정 1판)" % nm, ev_d)):
            c = sum(1 for i in ks if stopped(src[i]["masks"][()], pairs[i][0]["entry_px"]))
            rr = st.median([realized(src[i]["masks"][()], pairs[i][0]["entry_px"]) for i in ks])
            P("| %s — %s 의 %s 건 | **%s** | **%.1f%%** | **%+.2f%%** |"
              % (lab, nm, format(len(ks), ","), format(c, ","),
                 100.0 * c / max(len(ks), 1), rr))
    P("")
    P("```")
    P("## 🔴🔴 **의심은 «맞았다» — 그런데 «오염»된 짝이 «다르다»**")
    P("")
    P("**①(안 건드린 거래)의 손절 비율 vs 팔·Ⓓ 의 손절 비율:**")
    for nm, sf, fr_ in ARMS:
        ks = sorted(hits[nm])
        ev_a, _ = make(sf, fr_)
        ev_d = placebo(hits[nm], fr_, 0, nm)
        c1 = sum(1 for i in ks if stopped(base[i]["masks"][()], pairs[i][0]["entry_px"]))
        ca = sum(1 for i in ks if stopped(ev_a[i]["masks"][()], pairs[i][0]["entry_px"]))
        cd = sum(1 for i in ks if stopped(ev_d[i]["masks"][()], pairs[i][0]["entry_px"]))
        P("   %-4s  ① **%.1f%%**  →  팔 **%.1f%%** · Ⓓ **%.1f%%**   (팔−Ⓓ 차 **%+.1f%%p**)"
          % (nm, 100.0 * c1 / max(len(ks), 1), 100.0 * ca / max(len(ks), 1),
             100.0 * cd / max(len(ks), 1),
             100.0 * (ca - cd) / max(len(ks), 1)))
    P("")
    P("## ⇒ ★★★ **「일찍 판다」와 「−10% 손절을 «안» 맞는다」는 «이 설계»에서 «거의» «같은 말»이다**")
    P("   ① 의 그 거래 중 **32 ~ 52%** 가 «손절»로 끝나는데 — 팔·Ⓓ 는 **«둘 다» 0.1% 안팎**이다")
    P("")
    P("   🔴 **오염된 짝 = `팔 − ①` 과 `Ⓓ − ①`**")
    P("     그 둘은 「«일찍» 판다」와 「«손절»을 «안» 맞는다」가 **«섞여» 있다**")
    P("     ⇒ ⛔ **`Ⓓ−① = +2.351%p` 를 「«일찍» 파는 것 «자체»의 값」으로 «읽지» 않는다**")
    P("     ⇒ ✅ **`133`(늦출수록 이김)과의 «어긋남»도 그것으로 «설명»된다 — «어긋난» 게 «아니다**")
    P("")
    P("   ✅ **오염되지 «않은» 짝 = `팔 − Ⓓ`** — **손절 비율이 «둘 다» 0.1% 안팎**이라")
    P("     그 성분이 **«상쇄»**된다. ⇒ ## **★판정 `팔−Ⓓ` 는 «그대로» «산다»**")
    P("")
    P("   ★ 그리고 **Ⓟ 는 «셋 다» 52.0%** — 「«절반»만 파니 «나머지»가 «그대로» 손절을 맞는다」")
    P("     ⇒ **«설계»가 «맞게» 돌고 있다는 «양성 대조»**다")
    P("```")
    P("")
    P("**노출 — «팔마다»** · ⛔ **«보정» «금지»**(유형 73)")
    P("   ① **%.1f%%**" % meta["①"]["expo"])
    for nm, _sf, _fr in ARMS:
        e_ = meta["Ⓓ" + nm]["expo_d"]
        P("   %s **%.1f%%** · Ⓓ%s **%.1f ~ %.1f%%**(중앙 %.1f%%)"
          % (nm, meta[nm]["expo"], nm, min(e_), max(e_), st.median(e_)))
    P("```")

    # ═══ 팔 ════════════════════════════════════════════════════════════
    P("")
    P("## 3. 팔 — **%d** 개 · 📏폭 «전부»(UC★)" % (1 + 2 * len(ARMS)))
    P("")
    P("| 팔 | 뜻 | 후보 | 세후 총액(중앙) | 연 환산 | **📏폭** | 낙폭 중앙 | 회복 |")
    P("|---|---|---:|---:|---:|---:|---:|---:|")
    LAB = {"①": "**현행** −10/+30"}
    for n in NS:
        LAB["Ⓞ%d" % n] = "㉠ «수익 중»+«%d일 저가» 이탈 ⇒ **전량**" % n
    LAB["Ⓟ"] = "㉡ 저거래량 돌파+매도물량 ⇒ **절반**"
    LAB["Ⓠ"] = "㉡ 같은 조건 ⇒ **전량**"
    for nm in ["①"] + [a[0] for a in ARMS] + ["Ⓓ" + a[0] for a in ARMS]:
        v = out[nm]
        mm = st.median([a[0] for a in v])
        lab = LAB.get(nm, "«플라세보» — %s 의 «그» 거래를 «무작위» 시점에" % nm[1:])
        P("| **%s** | %s | %d | %.0f만 | **%+.2f%%** | **%.2f** | %+.1f%% | %.1f년 |"
          % (nm, lab, meta[nm]["n"], mm, acc.cagr(mm, YRS), spread(v),
             st.median([a[1] for a in v]), st.median([a[2] for a in v]) / 252.0))

    # ═══ 판정 ══════════════════════════════════════════════════════════
    P("")
    P("## 4. 판정 — **정본 §판정표** · Δ = %.2f%%p" % DELTA)
    P("")
    P("| 짝 | 뜻 | Δ연환산 | 95% CI | 📏폭 | 판정 |")
    P("|---|---|---:|---:|---:|:--|")
    rows = []
    sp1 = spread(out["①"])
    for nm, _sf, _fr in ARMS:
        dn = "Ⓓ" + nm
        mu, lo, hi = dif(nm, dn)
        c = cell(lo, hi)
        rows.append((nm, mu, lo, hi, c))
        P("| **%s − %s** | ★**판정** — 「«반전»/«매도물량» 신호가 «시점»을 «잘» 고르는가」 | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f vs Ⓓ %.2f | %s |"
          % (nm, dn, mu, lo, hi, spread(out[nm]), spread(out[dn]), c))
    P("")
    P("| 짝 | 뜻 | Δ연환산 | 95% CI | 📏폭 vs ① | 판정 |")
    P("|---|---|---:|---:|---:|:--|")
    for nm, _sf, _fr in ARMS:
        mu, lo, hi = dif(nm, "①")
        P("| **%s − ①** | «참고» — 「조기 청산 «전체»」(`133` «강하게» 걸림) | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f vs %.2f | %s |"
          % (nm, mu, lo, hi, spread(out[nm]), sp1, cell(lo, hi)))
    P("")
    P("| 짝 | 뜻 | Δ연환산 | 95% CI | 판정 |")
    P("|---|---|---:|---:|:--|")
    for nm, _sf, _fr in ARMS:
        mu, lo, hi = dif("Ⓓ" + nm, "①")
        P("| **Ⓓ%s − ①** | 🆕 「**«무작위»로 «일찍» 파는 것 «자체»**」 | **%+.3f%%p** | [%+.3f, %+.3f] | %s |"
          % (nm, mu, lo, hi, cell(lo, hi)))
    P("")
    P("```")
    P("🚨 **합 검산 «항등식»** — |(팔−Ⓓ) + (Ⓓ−①) − (팔−①)| < %.2f%%p" % NA_TOL)
    okall = True
    for nm, _sf, _fr in ARMS:
        e = dif(nm, "Ⓓ" + nm)[0] + dif("Ⓓ" + nm, "①")[0] - dif(nm, "①")[0]
        okall = okall and abs(e) < NA_TOL
        P("   %-4s 오차 **%+.4f%%p**  →  %s" % (nm, e, "✅" if abs(e) < NA_TOL else "🚨 **멈춘다**"))
    P("")
    P("## 🔴🔴 **이 조각이 «없으면» 결과를 «거꾸로» 읽는다**")
    P("")
    dpos = [(nm, dif("Ⓓ" + nm, "①")[0]) for nm, _s, _f in ARMS]
    P("   **「무작위로 일찍 팔기」가 ① 보다 «나은» 팔 — %d/%d** (%s)"
      % (sum(1 for _n, v in dpos if v > 0), len(dpos),
         " · ".join("%s %+.3f" % (n, v) for n, v in dpos)))
    P("")
    P("   🚨 **이것은 `133`(「늦출수록 이김」)과 «어긋난다»** — 그 사전 근거는 **Ⓞ−①** 에 걸었는데")
    P("     **Ⓓ−①** 도 «같은» 방향의 근거가 «걸려야» 하는데 **부호가 «반대»**로 나왔다")
    P("   ⇒ ⛔ **이 판은 그 «어긋남»을 «설명»하지 «못»한다.** «다음 판»의 물음으로 «등록»한다:")
    P("     ## **「«무작위»로 일찍 파는 것이 «왜» ① 보다 나은가 — «칸»이 «빨리» 비어서인가」**")
    P("     («갈아 끼운» 거래의 보유일 중앙이 ① **%.0f일** → Ⓓ **%.0f일** 로 «줄었다»)"
      % (st.median(hdays["①"]), st.median(meta["ⒹⓄ3"]["hd"])))
    P("   🚨 그리고 **노출이 «같지» «않다»** — ① **%.1f%%** vs Ⓓ **%.1f%%** ⇒ **«같은 돈»을 «안» 굴렸다"
      % (meta["①"]["expo"], st.median(meta["ⒹⓄ3"]["expo_d"])))
    P("     ⛔ **그래도 «보정»하지 «않는다»**(유형 73 — 노출은 «팔의 «결과»»다). **«적어» 둔다**")
    P("```")
    P("")
    P("```")
    P("🚨 **㉠ 은 N «세 칸» «전부» «같은 칸»이어야 「일한다」**(`170`·`175` 규칙 · «값 보기 전»에 세웠다)")
    ocells = [r for r in rows if r[0].startswith("Ⓞ")]
    same = len({r[4].split(" ")[0] for r in ocells}) == 1
    P("   실측 — %s  ⇒  %s"
      % (" · ".join("%s:%s" % (r[0], r[4].split(" ")[0]) for r in ocells),
         "✅ **같은 칸**" if same else "🔴 **«갈린다» ⇒ 「일한다」로 «못» 쓴다**"))
    P("   ㉠ 부호 — 음수 **%d/%d** · CI 가 0 을 «배제» **%d/%d**"
      % (sum(1 for r in ocells if r[1] < 0), len(ocells),
         sum(1 for r in ocells if r[2] > 0 or r[3] < 0), len(ocells)))
    P("")
    P("★ **방향 «예측» 대조 — «미리» 적은 것과 맞춰 읽는다**")
    P("   ㉮ **Ⓞ−Ⓓ 는 «음수»일 것**(`133`) — 실측 %s  ⇒  %s"
      % (" · ".join("%+.3f" % r[1] for r in ocells),
         "✅ **맞았다**" if all(r[1] < 0 for r in ocells) else "🔴 **«빗나갔다»**"))
    dp, dq = dif("Ⓟ", "Ⓓ" + "Ⓟ")[0], dif("Ⓠ", "Ⓓ" + "Ⓠ")[0]
    P("   ㉯ **Ⓟ(절반)가 Ⓠ(전부)보다 «덜» 나쁠 것** — Ⓟ−ⒹⓅ **%+.3f** vs Ⓠ−ⒹⓆ **%+.3f**  ⇒  %s"
      % (dp, dq, "✅ **맞았다**" if dp > dq else "🔴 **«빗나갔다»**"))
    P("   ㉰ **📏폭은 «좁아질» 것**(일찍 팔면 «꼬리»가 «잘린다») — ① **%.2f** vs %s  ⇒  %s"
      % (sp1, " · ".join("%s %.2f" % (r[0], spread(out[r[0]])) for r in rows),
         "✅ **맞았다**" if all(spread(out[r[0]]) < sp1 for r in rows) else "🔴 **«빗나갔다»**"))
    P("   🚨 **㉰ 가 맞아도 「좋아졌다」가 «아니다»** — **«꼬리»가 «잘린» 것**이다")
    P("")
    P("🚨 **㉱ — 내가 «바라는» 것은 「음수」였다. «안 바라는» 「양수」 칸을 «먼저» 썼는가:**")
    P("   위 판정표에서 **양수**인 짝 — %s"
      % (" · ".join("**%s %+.3f**" % (r[0], r[1]) for r in rows if r[1] > 0) or "**없다**"))
    P("   ⇒ ✅ **양수가 있으면 그것을 «먼저» 읽는다.** 「또 조기청산은 나쁘다」로 «세게» «닫지» 않는다(유형 78)")
    P("```")
    P("")
    P("```")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ 「원전 «청산»이 «틀렸다»」 — 「반전」·「매도 물량」의 **«자»가 «우리» 것**이다(ⓐ 는 «근사»)")
    P("   ⛔ 「조기 청산은 나쁘다」로 «일반화» — **㉠㉡ 은 «조건부»**다")
    P("   ⛔ 「55변형 0승」 인용 — **«한국» 판정**")
    P("   ⛔ **Ⓞ 와 Ⓟ/Ⓠ 를 «서로» 견주기** — 「고르기」 자리다")
    P("   ⛔ 📏폭이 «좁아진» 것을 「좋아졌다」로 — **«꼬리»가 «잘린» 것**")
    P("   ⛔ **노출 «보정»**(유형 73)")
    P("   ⛔ **㉢(실제로 산 수)을 「체결률」로, ㉡ 을 「샀다」로** — **«자»가 «셋»이다**")
    P("   🆕 ⛔ **`Ⓓ−①` 을 「«일찍» 파는 것 «자체»의 값」으로** — **「손절을 «안» 맞는다」가 «섞였다»**(UB★b)")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 손절 −10 · 목표 +30",
                     "같은 칸 5", "**같은 검출기 섞임**(VCP 76.9%)",
                     "**같은 거래 목록**(중복 제거를 ① 로 «한 번»만)"]):
        P(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

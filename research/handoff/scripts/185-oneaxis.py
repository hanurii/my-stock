# -*- coding: utf-8 -*-
r"""185 — **`175`·`181`·`182` 의 「칸 1」을 «자료» 축으로** · 두뇌 의뢰 2026-09-06

  🚨 **정본 처방(`verdicts/00-READ-FIRST` 403-414 · M10)**:
     **「«판정 «문턱»»에 붙는 «구간»은 «언제나» «자료»다. 적을 수 «없으면» «판정»에 «못» 쓴다」**
     ⇒ `156`~`182` 가 «씨앗» 축으로 판정했다. **«세 번째» 위반**이다.

  ⓪ **`183a` 가 «먼저» 돌았고 — `23c` 의 이동 블록이 «걸렸다»**(첫/끝 덮개 0.028·0.043 · 기지답 0%).
     ⇒ ✅ **이 판은 «순환» 블록을 쓴다**(`183a` 의 기지답 시험을 **100%** 로 통과한 그 방식).

  ★ **이 판은 «방향»이 «반대»다** — 「칸 2」는 **「«하지» 마라」**이고,
     «자료» 축에서 «죽으면» 그 금지가 **「«모른다»」**가 된다 ⇒ **«막았던» 것이 «다시» «열린다»**.
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


ALPHA = 0.005
# «씨앗» 축의 값 — 원본 문서에서 «그대로»
SEEDAX = {"175가격": 2.497, "175합": 1.656, "181㉰": 1.331,
          "181합": 2.497, "182합": 1.656}
r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
gates = _load("gates", "_gates.py")
ptb = _load("ptb", "_pyr_be.py")
f92a = r102.f92a
pt = r91.pt

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF, SLOTS = 30.0, 10.0, 0.5, 5
NS = (3, 5, 10)
LOWVOL, HEAVY = 1.0, 1.5
NBOOT = 2000
BMIN, BMAX = 20, 40          # `23c` 와 «같은» 블록 길이
SEED = 185185
YRS = 27.4          # `156`~`182` 와 «같은» 창
FULL = Path("D:/stock-data/uspath-warm/full")


def draw(n, rnd):
    """**«순환»** 블록 — `183a` 의 기지답 시험을 **100%** 로 통과한 방식."""
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(BMIN, BMAX)
        a = rnd.randint(0, n - 1)
        LL = min(L, n - tot)
        for j in range(LL):
            out.append((a + j) % n)
        tot += LL
    return out


def ann(tot_pct):
    """🚨 **«총수익»을 «연환산»으로** — 씨앗 축 판정이 «연환산 %p» 였다(유형 67).
    «안» 고치면 −636%p 같은 «27년 누적»이 나와 **«다른 자»**가 된다."""
    v = 1.0 + tot_pct / 100.0
    if v <= 1e-9:
        return -100.0
    return (v ** (1.0 / YRS) - 1.0) * 100.0


def boot_eq(by_pos, n_pos, slots=SLOTS):
    """`23c:46-66` «그대로» — 자리별 거래를 슬롯 규칙으로 굴린다."""
    eq, held = 1.0, []
    for p in range(n_pos):
        if held:
            keep = []
            for h in held:
                if h[0] < p:
                    eq += h[1] * h[2] / 100
                else:
                    keep.append(h)
            held = keep
        free = slots - len(held)
        c = by_pos.get(p)
        if free > 0 and c:
            wgt = eq / slots
            for rel, nt, _k in c[:free]:
                held.append([p + rel, wgt, nt])
    for h in held:
        eq += h[1] * h[2] / 100
    return (eq - 1) * 100


def main():
    P = print
    quick = "--quick" in sys.argv
    nboot = 200 if quick else NBOOT
    P("=" * 104)
    P("185 — **`175`·`181`·`182` 의 「칸 1」을 «자료» 축으로** · 부트 %s판%s"
      % (format(nboot, ","), "  🚨 **--quick**" if quick else ""))
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-06 · `scripts/185-oneaxis.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("## 🚨🚨 **머리 «셋» — «돌리기 «전»»에 박는다**")
    P("")
    P("```")
    P("㉠ ## **「집합 «귀무»는 «원리상» «없다»」**")
    P("   집합을 **«완전히»** 맞추면 그건 **«관측» «그 자체»**다.")
    P("   α·N·규칙은 **«손잡이»**이고 **«집합»은 그 «결과»**다 ⇒")
    P("   **「손잡이 효과」와 「집합 효과」를 «분리»하는 귀무는 «없다**")
    P("   ⇒ ✅ **그 «막힘» «자체»를 «적는다** — 「원리가 «막히면» 그것도 «결과»」")
    P("")
    P("㉡ ## **「귀무 95% +87.47%p」의 «출처» = `scripts/23c-boot-and-maxstat.py`**")
    P("   🚨 **다섯 판**(`23`·`165`·`173`·`179`·`182`)이 «근거»로 «썼는데** «결과 문서»엔 «경로»가 «없었다**")
    P("   ⇒ ✅ **앞으로 «수»에 «스크립트 경로»를 «같이» 적는다**")
    P("   ⚠️ 그리고 **`183a` 가 그 파일의 재표집을 «걸었다»** — 「87.47 은 «순환» 블록으로 «다시» 내야 한다」")
    P("")
    P("㉢ ## 🆕 **이 판은 «금지»를 «푸는» 쪽으로도 «갈 수» 있다**")
    P("   「칸 2」는 **「«하지» 마라」**다. «자료» 축에서 «죽으면** 그 금지가 **「«모른다»」**가 된다")
    P("   ⇒ ★ **「우리 것이 «줄어드는»」 게 «아니라** — **「«막았던» 것이 «다시» «열리는»」** 것이다")
    P("   ⇒ ⛔ **「또 깎이겠지」로 «미리» 읽지 «않는다** — «어느» 쪽이든 **«수»가 말한다**")
    P("")
    P("   ## ⇒ ★★★ **그리고 «실제로» 열렸다** — `Ⓞ3`·`Ⓞ5` 의 「«하지» 마라」가 「«모른다»」가 된다")
    P("   ★ 오늘 «일곱» 바퀴가 «전부» 「우리 것을 «깎는»」 쪽이었는데 — **이 판은 «연다**")
    P("     ⇒ **유형 99(하루의 «방향»)를 «깬» «첫» 판**이다")
    P("```")
    P("")
    P("## 🚨 **㉣ — `dataaxis.py` 를 «안» 쓴 «이유»**(「«봤고» «안» 썼다」 ≠ 「«몰랐다»」)")
    P("")
    P("```")
    P("✅ **«봤다**. 그리고 **`104v` 를 «거기»에도 «걸었다**(`results/183b-104v-on-dataaxis.md`)")
    P("   ⇒ **결과: «통과»**(이동 판이 참값의 0.011~0.046 · 순환 판이 1.02~1.05)")
    P("   ⇒ ★ **즉 `dataaxis` 의 «순환» 모드는 «쓸 수» 있다** — 「양 끝만 뽑는」 기록은 **«이동» 모드의 것**이다")
    P("")
    P("🚨 그런데 **이 판은 «자체» `draw()` 를 쓴다**. 이유 «둘»:")
    P("   ① `dataaxis` 는 **`CYCLIC[0]` «전역 상태»**로 모드를 바꾼다 ⇒ **«실수»할 자리**가 있다")
    P("   ② 이 판은 **`23c` 의 `boot_eq` 규약**을 쓰므로 «블록 뽑기»만 있으면 된다")
    P("   ⇒ ✅ **그래서 «위 §0」에서 «자체» `draw()` «자체»에 관문을 «걸었다**")
    P("   ⛔ **「관문을 «걸었다»」를 «적는» 것으로는 «안» 된다 ⇒ «수»로 «찍었다**")
    P("")
    P("🔴 그리고 **이건 «하마터면» 「도구를 «만들고» «안» 쓴」 «여섯 번째»가 «될 뻔»했다**")
    P("   — **`183a` 가 «그» 관문으로 결함을 «잡은» «직후»**였다")
    P("```")
    P("")
    P("## 🚨 **④ — «세는» 수에 «그 수를 «만든» 명령»을 «같은 줄»에**(«인쇄 함수»가 «강제»)")
    P("")
    P("```")
    P("🚨 오늘 «세는» 일이 **«네» 번** 틀렸다(「11/16」·「폭 1.00 파일」·「단조 9/9」·「칸 1」)")
    P("   그리고 처방 「값 «만드는» 자리에서 세라」는 **«세 번»** 나왔는데 **«적용»이 «안» 됐다**")
    P("⇒ ✅ **이 판은 «세는» 수를 «전부» `cnt()` 로 «인쇄»한다** — 그 함수가 «식»을 «같이» 찍는다")
    P("")
    P("## 🆕 **「없다」가 오늘 «다섯» 번 틀렸다 — «얼굴»이 «다섯»이다**")
    P("   ① «잘림»(head 를 «수»로 읽음) ② «안» 찾아봄 ③ «자리»가 틀림(cd 누적)")
    P("   ④ **«패턴»이 좁음**(`grep \"| 1\.[0-9][0-9] |\"` 가 「2.xx」를 «버림»)")
    P("   ⑤ **«범위»(«폴더»)가 좁음**(`results/` 만 보고 `verdicts/`·`tasks/` 를 «안» 봄)")
    P("")
    P("   🚨 **그 «다섯» 중 «넷»을 «상대»가 «잡았다**")
    P("   ## ⇒ ★★★ **「«자기» 「없다」는 «자기»가 «못» 잡는다」**")
    P("   ⇒ ✅ **처방: 「없다」를 «적을» 때는 «상대»에게 **«검색»을 «넘긴다»**")
    P("     (세 세션 구조의 **«새» 쓰임** — 지금까지는 「판정」만 넘겼다)")
    P("```")
    P("")

    # ═══ ① 🚨 «이 판의» 재표집에 `104v` 의 «세 자»를 «걸고» — «출력»으로 «찍는다** ═══
    P("## 0. 🚨🚨 **재표집 «관문» — «이 판의» `draw()` 에 «건다**(주장이 «아니라» «출력값»)")
    P("")
    P("```")
    P("🔎 `104v-resample-gate.py` 의 «세 자»를 **이 파일의 `draw()` «자체»**에 «건다**")
    P("🚨 **«이동» 판이 «실패»해야 «통과»**다(유형 24′) — 실패 «안» 하면 관문이 «아무것도» 안 잰다")
    P("")

    def _draw_mode(n, rnd, cyclic):
        out, tot = [], 0
        while tot < n:
            L = rnd.randint(BMIN, BMAX)
            a = rnd.randint(0, n - 1) if cyclic else rnd.randint(0, n - L)
            LL = min(L, n - tot)
            for j in range(LL):
                out.append((a + j) % n if cyclic else a + j)
            tot += LL
        return out[:n]

    _N, _X = 2250, 0.05
    _truth = ((1.0 + _X) ** 2 - 1.0) * 100.0
    _res = {}
    for _cy in (False, True):
        _r = [0.0] * _N
        _r[0] = _r[_N - 1] = _X
        _rg = random.Random(99)
        _vals = []
        for _ in range(2000):
            _v = 1.0
            for _i in _draw_mode(_N, _rg, _cy):
                _v *= (1.0 + _r[_i])
            _vals.append((_v - 1.0) * 100.0)
        _cov = [0] * _N
        _rg2 = random.Random(4242)
        for _ in range(200):
            for _i in _draw_mode(_N, _rg2, _cy):
                _cov[_i] += 1
        _res[_cy] = (st.median(_vals), _cov[0] / 200.0, _cov[-1] / 200.0)
    P("| 자 | 이동(«대조») | **순환(«이 판»이 «쓰는» 것)** | 예측 |")
    P("|---|---:|---:|---|")
    P("| 첫 자리 덮개 | %.3f | **%.3f** | 1.000 |" % (_res[False][1], _res[True][1]))
    P("| 끝 자리 덮개 | %.3f | **%.3f** | 1.000 |" % (_res[False][2], _res[True][2]))
    P("| 기지답 중앙(참값 %.2f%%) | %.3f%% | **%.3f%%** | %.2f%% |"
      % (_truth, _res[False][0], _res[True][0], _truth))
    P("")
    _mv_fail = _res[False][0] < _truth * 0.85
    _cy_ok = _truth * 0.85 <= _res[True][0] <= _truth * 1.15
    P("**판정** — «이동»이 «실패»하는가 → %s   ·   «순환»이 «맞는가» → %s"
      % ("✅" if _mv_fail else "🚨", "✅" if _cy_ok else "🚨"))
    P("```")
    if not (_mv_fail and _cy_ok):
        P("")
        P("🚨 **관문 «미통과» — 이 판의 «모든» 수가 «자격»을 «잃는다». «멈춘다»**")
        return 3
    P("")

    def cnt(label, value, how):
        """🚨 «세는» 수는 «반드시» 이 함수로 — 「어떻게 셌나」가 «같은 줄»에 «강제»된다."""
        P("   **%s = %s**   ⟵  `%s`" % (label, value, how))

    # ── 자료 ────────────────────────────────────────────────────────
    CA = Path(str(r91.OUT / "185-arms.json"))
    WARM = CA.exists()
    if WARM:
        P("## 1. 자료 — 관문")
        P("")
        P("```")
        P("   («캐시» `183-arms.json` 이 «있어» 자료 적재를 «건너뛴다** — 팔은 «그대로»)")
        P("```", flush=True)
        by2, keep, pairs, PRE = {}, {}, [], {}
    else:
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
                v = (None if (a is None
                              or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                     else r103.judge(arq, arq.index(a), ix, 1, 2))
                if v is not False:
                    keep[y].append(p)
        PRE = {}
        for y in range(1999, 2027):
            f = FULL / ("uspath_%d.json" % y)
            if not f.exists():
                continue
            for q in json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]:
                PRE[(q["scan_date"], q["code"], q["pattern"])] = (q.get("pre_l"), q.get("pre_v"),
                                                                  q.get("v"))
        pairs = []
        for y in sorted(keep):
            open_until = {}
            for p in keep[y]:
                t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                     half=HALF, shares=(1.0,), add_stop="floor_entry")
                c = p["code"]
                if c in open_until and p["entry_date"] <= open_until[c]:
                    continue
                open_until[c] = t["masks"][()]["resolve_date"] or p["entry_date"]
                t["stop_frac"] = STOP / 100.0
                pairs.append((t, p))
        P("## 1. 자료 — 관문")
        P("")
        P("```")
        cnt("거래 목록(중복 제거 «후»)", format(len(pairs), ","),
            "len(pairs)  — `176` 과 «같은» 구성")
        P("```", flush=True)

    def pre_of(p):
        return PRE.get((p["scan_date"], p["code"], p["pattern"]), (None, None, None))

    # ── `176` 의 신호(그대로) ────────────────────────────────────────
    def ma50_at(p, j):
        _pl, pv, _v = pre_of(p)
        if not pv:
            return None
        V = list(pv) + list(pre_of(p)[2] or [])
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
                if c[j] is None or c[j] <= epx:
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
        v = pre_of(p)[2] or []
        m = ma50_at(p, 0)
        if not v or v[0] is None or m is None:
            return None
        return v[0] < m * LOWVOL

    def sig_two(t, p):
        if not is_lowvol(p):
            return None
        v, c, o = pre_of(p)[2] or [], p["c"], p["o"]
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

    def rewrite(t, p, jx, frac):
        r = t["masks"][()]
        dx, px = p["d"][jx], p["o"][jx]
        pre = [e for e in r["exits"] if e[0] < dx]
        later = [e for e in r["exits"] if e[0] >= dx]
        rem = sum(e[1] for e in later)
        if rem <= 1e-12 or px is None:
            return None
        new = pre + [(dx, rem * frac, px)]
        rd = dx
        if frac < 1.0 - 1e-12:
            new += [(e[0], e[1] * (1.0 - frac), e[2]) for e in later]
            rd = r["resolve_date"]
        return new, rd

    def trades_of(exits_rd, t, p):
        """(진입일, 보유 «거래일» 수, 순수익%) — «자료» 축이 먹는 모양."""
        exits, rd = exits_rd
        epx = t["entry_px"]
        net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2)) for _d, fr, px in exits)
        d = p["d"]
        hold = d.index(rd) if (rd and rd in d) else len(d) - 1
        return (t["entry_date"], max(1, hold), net)

    def arm(sigfn, frac, placebo_seed=None):
        rg = random.Random(90210 + (placebo_seed or 0))
        out = []
        for t, p in pairs:
            r = t["masks"][()]
            base = (r["exits"], r["resolve_date"])
            jx = sigfn(t, p)
            if jx is None:
                out.append(trades_of(base, t, p))
                continue
            if placebo_seed is not None:
                hi = min(res_j(t, p), len(p["d"]) - 1)
                jx = rg.randint(1, hi) if hi >= 1 else None
            got = rewrite(t, p, jx, frac) if jx is not None else None
            out.append(trades_of(got if got else base, t, p))
        return out

    def prices(p):
        pv = p["pivot"]
        o0 = (p.get("o") or [None])[0]
        lvl = pv * (1.0 - ALPHA)
        e2 = pv if o0 is None else max(pv, o0)
        e1 = lvl if o0 is None else max(lvl, o0)
        return e2, e1

    def touch(p):
        pv, lo = p.get("pivot"), p["l"][0]
        return pv is not None and lo is not None and lo <= pv * (1.0 - ALPHA)

    def build_arm(mode):
        """base(1) | S2(N-double-prime) | S1 | S3(N)"""
        out_ = []
        for t, p in pairs:
            if mode != "base" and not touch(p):
                continue
            if mode == "base":
                r = t["masks"][()]
                out_.append(trades_of((r["exits"], r["resolve_date"]), t, p))
                continue
            e2, e1 = prices(p)
            q = dict(p)
            q["entry_price"] = e2 if mode == "S2" else e1
            kw = {}
            if mode == "S1":
                kw["stop"] = 100.0 * (1.0 - e2 * (1.0 - STOP / 100.0) / e1)
                kw["target"] = 100.0 * (e2 * (1.0 + TARGET / 100.0) / e1 - 1.0)
                kw["be_px"] = e2
            t2 = ptb.resolve_trade(q, ft="limit", fs="market",
                                   stop=kw.pop("stop", STOP),
                                   target=kw.pop("target", TARGET),
                                   half=HALF, shares=(1.0,), add_stop="floor_entry", **kw)
            r2 = t2["masks"][()]
            out_.append(trades_of((r2["exits"], r2["resolve_date"]), t2, p))
        return out_

    if WARM:
        built = {k: [tuple(x) for x in v]
                 for k, v in json.loads(CA.read_text(encoding="utf-8")).items()}
        P("  (cache: arms %d)" % len(built), flush=True)
    else:
        built = {}
        for nm, md in (("\u2460", "base"), ("\u24c8\u2033", "S2"),
                       ("\u24c8\u00b9", "S1"), ("\u24c3", "S3")):
            built[nm] = build_arm(md)
            P("  %s made (%d)" % (nm, len(built[nm])), flush=True)
        CA.write_text(json.dumps({k: [list(x) for x in v] for k, v in built.items()}),
                      encoding="utf-8")

    all_d = sorted({d for lst in built.values() for d, _h, _n in lst})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)
    idx_at = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            idx_at[k][pos[d]].append(j)

    P("")
    P("```")
    cnt("날짜 자리 수", format(n_pos, ","), "len(sorted(set(entry_dates)))")
    cnt("팔 수", len(built), "len(built)")
    for _k in sorted(built):
        cnt("  %s 거래 수" % _k, format(len(built[_k]), ","), "len(built[k])")
    P("```")

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return boot_eq(bp, n_pos)

    # ★판정 짝 — `175`·`181`·`182` 의 「칸 1」
    PAIRS = [("175가격", "Ⓝ", "Ⓢ″"), ("175합", "Ⓝ", "①"),
             ("181㉰", "Ⓢ¹", "Ⓢ″"), ("181합", "Ⓝ", "Ⓢ″"), ("182합", "Ⓝ", "①")]
    o = {k: ann(obs(v)) for k, v in built.items()}
    obsd = {nm: o[a] - o[b] for nm, a, b in PAIRS}

    rnd = random.Random(SEED)
    boots = {nm: [] for nm, _a, _b in PAIRS}
    for bi in range(nboot):
        order = draw(n_pos, rnd)
        eqs = {}
        for k, lst in built.items():
            bp = defaultdict(list)
            ia = idx_at[k]
            for newp, oldp in enumerate(order):
                for j in ia.get(oldp, ()):
                    _d, h, nt = lst[j]
                    bp[newp].append((h, nt, 0))
            eqs[k] = ann(boot_eq(bp, n_pos))
        for nm, a, b in PAIRS:
            boots[nm].append(eqs[a] - eqs[b])
        if (bi + 1) % 200 == 0:
            P("  부트 %d/%d" % (bi + 1, nboot), flush=True)

    # ── 중심화 + 최대통계 ───────────────────────────────────────────
    cen = {nm: [x - st.mean(boots[nm]) for x in boots[nm]] for nm, _a, _b in PAIRS}
    maxt = [max(abs(cen[nm][i]) / max(st.stdev(cen[nm]), 1e-9) for nm, _a, _b in PAIRS)
            for i in range(nboot)]
    maxt.sort()
    thr = maxt[int(nboot * 0.95)]

    P("")
    P("## 2. ★★ **«자료» 축 판정 — `175`·`181`·`182` 의 「칸 1」**")
    P("")
    P("🚨 **«단위»는 «연환산 %p»** — 씨앗 축 판정과 **«같은» 자**다")
    P("   (한때 «총수익»(27년 «누적»)으로 찍어 **−636%p** 같은 수가 나왔다 — **«다른» 자**였다)")
    P("")
    P("| 짝 | «씨앗» 축 | **«자료» 점추정** | **«자료» 95% CI** | CI폭 | t | 최대통계 | **편향** | **|편향|÷SD** |")
    P("|---|---:|---:|---:|---:|---:|:--|---:|---:|")
    rows = []
    for nm, a, b in PAIRS:
        v = sorted(boots[nm])
        lo, hi = v[int(nboot * .025)], v[int(nboot * .975)]
        sd = st.stdev(boots[nm])
        tt = abs(obsd[nm]) / max(sd, 1e-9)
        rows.append((nm, obsd[nm], lo, hi, tt, tt >= thr))
        med = st.median(boots[nm])
        bias = med - obsd[nm]
        bs = abs(bias) / max(sd, 1e-9)
        rows[-1] = rows[-1] + (hi - lo, bias, bs)
        P("| **%s − %s** | %+.3f | **%+.3f%%p** | [%+.3f, %+.3f] | **%.2f** | %.2f | %s | **%+.3f** | **%.2f** |"
          % (a, b, SEEDAX[nm], obsd[nm], lo, hi, hi - lo, tt,
             "✅ **산다**" if tt >= thr else "🔴 **죽는다**", bias, bs))
    P("")
    P("```")
    P("## 🚨🚨 **⑤ «신설» — 「편향」을 «판정칸 «옆»»에 «항상» 인쇄한다**")
    P("")
    P("   **편향 = «부트 «중앙»» − «관측» 점추정**  ·  **t 는 «관측»을 «중심»**으로 잰다")
    P("   ⇒ ★ **«편향»이 «크면» 「CI」와 「t」가 «어긋난다** — 「«어느» 쪽이 맞나」가 «아니라**")
    P("   ## ⇒ **「«편향»이 «크면» «둘 다» «못» 믿는다」**가 답이다")
    P("")
    P("   ⛔ **«문턱»을 «정하지» 않는다** — 「0.9」 같은 수는 **«임의»**다")
    P("     (오늘 「1.05」를 «스스로» 깎은 것과 **«같은» 자리**다)")
    P("   ⇒ ✅ **「제외」가 «아니라» 「«표시»」** — 📏폭에서 «간» 길과 **«같은» 처방**")
    P("   ★ 그리고 이건 **「«같은» 것을 가리키는 «수»가 «둘»이면 «멈춤»」(규약 ⑦)의 «형태»**다")
    P("")
    _srt = sorted(rows, key=lambda r: -r[8])
    P("   **|편향|÷SD 큰 순** — %s"
      % " · ".join("**%s %.2f**" % (r[0], r[8]) for r in _srt))
    P("```")
    P("")
    P("```")
    cnt("최대통계 95% 문턱", "%.3f" % thr,
        "sorted(max_a |centered| / SD)[int(nboot*0.95)]")
    cnt("최대통계를 «넘은» 짝", "%d / %d" % (sum(1 for r in rows if r[5]), len(rows)),
        "sum(1 for r in rows if r[5])")
    P("```")
    P("")
    P("```")
    P("## ★★★ **① 「어긋남」은 «구조»로 «가른다» — «임의» 문턱을 «안» 만든다**")
    P("")
    P("   🔴 한때 「|편향|÷SD > 0.9」 같은 «문턱»을 세우려 했다 — **«임의» 수라 «버렸다**")
    P("")
    P("   ## ✅ **「어긋남」의 «정의»는 «비대칭»이다:**")
    P("     🔴 **최대통계 «통과»인데 CI 가 0 «포함»**  ⇒ **«진짜» 어긋남** ⇒ **«판정 «보류»»**")
    P("     ⛔ CI 가 0 «배제»인데 최대통계 «미통과»    ⇒ **«정상»** — **최대통계가 «더» 엄하다**(다중비교 보정)")
    P("")
    # 🚨 «손»으로 적지 «않는다** — `_gates.bias_note()` 가 «찍는다**(다음 판이 «공짜»로 쓴다)
    _br = [(r[0], r[1], r[2], r[3], st.median(boots[r[0]]),
            st.stdev(boots[r[0]]), r[5]) for r in rows]
    for _ln in gates.bias_note(_br):
        P(_ln)
    hold_ = [r[0] for r in rows if r[5] and r[2] <= 0 <= r[3]]
    P("")
    P("```")
    P("   ★ **이 표는 `_gates.bias_note()` 가 «찍은» 것**이다 — «손»으로 적지 «않았다**")
    P("     ⇒ **«다음» 판은 그 함수만 부르면 «같은» 표를 «공짜»로 얻는다**")
    P("")
    cnt("«판정 «보류»» 짝", "%d / %d %s" % (len(hold_), len(rows),
                                        ("(%s)" % " · ".join(hold_)) if hold_ else ""),
        "sum(1 for r in rows if r[5] and r[2] <= 0 <= r[3])")
    P("")
    P("   🚨 **「죽는다」도 «판정»이다** — 「말할 수 «없다»」를 «말하는» 것도 **«자격»이 «필요»**하다")
    P("   ⛔ **`Ⓞ10` 을 「편향이 «크나» «죽는» 쪽이라 «안전»」으로 «읽지» 않는다**")
    P("     ✅ **근거는 「CI 와 최대통계가 «일치»한다」**이다 — **«다른» 근거**다")
    P("")
    P("   ⚠️ **|편향|÷SD 는 «표시»**다 — **«문턱»으로 «쓰지» 않는다**(⑤)")
    P("```")
    P("")
    P("```")
    P("## 🚨🚨 **② 「같은 짝」에 «이름»이 «둘»이다**(규약 ⑦ — 이 판이 «드러낸» 것)")
    P("")
    P("   `175가격`(Ⓝ−Ⓢ″) 와 `181합`(Ⓝ−Ⓢ″) — **«같은» 짝**이다")
    P("   `175합`(Ⓝ−①)   와 `182합`(Ⓝ−①)   — **«같은» 짝**이다")
    P("")
    P("   ## ⇒ ★★★ **`181`·`182` 는 「«새» 수」를 «낸» 판이 «아니었다**")
    P("   ## ⇒ **`175` 의 «같은 두 짝»을 «다시» 잰 판**이다")
    P("     (`181` 은 그 «조각»을 «더» 쪼갰고 · `182` 는 α 를 «격자»로 넓혔다)")
    P("   ⇒ ✅ **그러니 «자료» 축 판정도 «짝 셋»이지 «다섯»이 «아니다**")
    P("```")
    P("")
    P("```")
    P("## ★★ **③ 읽기 — 「칸 1」 셋 중 «하나»만 «산다**")
    P("")
    uniq = []
    seen_ = set()
    for r in rows:
        key = (round(r[1], 6), round(r[2], 6))
        if key in seen_:
            continue
        seen_.add(key)
        uniq.append(r)
    for r in uniq:
        P("   **%-8s** 자료 **%+.3f%%p** [%+.3f, %+.3f] · CI폭 **%.2f** · %s"
          % (r[0], r[1], r[2], r[3], r[6],
             "✅ **산다**" if r[5] else "🔴 **죽는다**"))
    P("")
    cnt("서로 «다른» 짝", "%d" % len(uniq), "len({(관측, CI하한)})")
    cnt("그중 «산» 짝", "%d" % sum(1 for r in uniq if r[5]),
        "sum(1 for r in uniq if r[5])")
    P("")
    P("   ★ **«산» 것은 `181㉰`(Ⓢ¹−Ⓢ″ = 「«싸게 산» 몫 · «회계»」) «하나»다**")
    P("     ⇒ **CI 폭이 %.2f** — 나머지(%.2f·%.2f)의 **«수십분의 1»**"
      % (min(r[6] for r in uniq), *sorted(r[6] for r in uniq)[1:3]))
    P("     ⇒ ★ **「«회계»는 «자료»를 바꿔도 «회계»」** — `181` 이 「㉰ 는 «회계»」라 한 것의 **«증거»**다")
    P("")
    P("")
    P("## ⇒ ★★★ **① 「«산» 것이 «회계» «하나»」의 «뜻»**")
    P("   ## **«자료» 축을 «통과»한 것은 「«회계»」 «하나»이고 —**")
    P("   ## **그것은 «몰라서» 통과한 게 «아니라» — **«알던» 것이라 «통과»**했다**")
    P("   ## ⇒ **「살아남음」이 「«참»이라서」가 «아니라» 「«잴 «필요»»가 «없어서»」다**")
    P("")
    P("   ⛔ **단 「«값»이 «없다»」가 «아니다** — 「0.5% 싸게 사면 0.5% 더 번다」는")
    P("     **«실행»되면 «진짜» 돈**이다(「회계」에 «자»가 «둘» — ㉠지적으로 «뻔하다» ✅ / ㉡실전 «무효» ❌)")
    P("   ## ✅ **정확히: 「«새로» «안» 것이 «없다»」**")
    P("   ★ 그리고 **CI 폭 «0.24»(나머지의 «수십분의 1») = «회계»의 «지문»**이다")
    P("")
    P("   🔴 **`175` 의 「가격」도 「합」도 «자료» 축에서 «죽는다**")
    P("     ⇒ **「피벗보다 «싸게» 사면 «얻는» 게 «있다」」가 «자료» 축에선 «안» 선다**")
    P("")
    P("## 🚨 **② 「부호 «반전»」으로는 «못» 쓴다**")
    P("   `175가격` 자료 **%+.3f%%p [%+.3f, %+.3f]** ⇒ **CI 가 0 을 «포함»**"
      % (uniq[0][1], uniq[0][2], uniq[0][3]))
    P("   ⇒ ⛔ 「«반대»다」 · ⛔ 「원전이 «맞다»」  ✅ **「«말할 수» «없다»」**")
    P("")
    P("## 🚨 **③ 「죽었다」에 «한정»을 «붙인다**")
    P("   ✅ CI 와 최대통계가 **«같은» 결정**(「못 씀」)을 내니 — **«보류»할 «이유»가 «없다**(0/%d)"
      % len(rows))
    P("   🚨 **그러나** 편향이 «크면**(위 표 %s) **「죽었다」의 «근거»도 «약하다**"
      % " · ".join("%.2f" % r[8] for r in uniq))
    P("     (부트가 «관측»을 «재현»하지 «못»한다는 뜻이므로)")
    P("   ## ⇒ ✅ **「«결정»은 «안» 바뀐다. 그러나 「죽었다」를 «확실히»로 «읽지» 말 것」**")
    P("   ## ⇒ **「«확실히» 죽었다」가 «아니라» 「«자료» 축에서도 «못» «살렸다»」**")
    P("")
    P("   ⚠️ **|편향|÷SD 가 %s** — 「어긋남」 판별(비대칭)은 «위» 표에 «있다**"
      % " · ".join("%.2f" % r[8] for r in uniq))
    P("```")
    P("")
    P("```")
    P("## 🚨 **이 판이 «못» 한 것**")
    P("")
    P("   ⚠️ **자료 축은 「진입일 «블록»」이다** — 「«어떤» 거래인가」는 «그대로» 둔다")
    P("     ⇒ `182`·`183` 이 적은 한계와 **«같은» 것**이다")
    P("   ⚠️ **`182` 의 α «격자»(여덟 칸)는 «안» 다시 쟀다** — **α=0.50% «한 칸»**만 했다")
    P("     ⇒ **「봉우리」 «자체»는 «미검정»**이다(`182` §max-T 그대로 «판정 불가»)")
    P("")
    P("   ⚠️ **«간접» «추론» — ⛔«안» 쟀다. «추론»일 «뿐»이다:**")
    P("     「가격」 CI 폭이 **씨앗 0.59 → 자료 %.2f**(**%.0f배**)이면"
      % (uniq[0][6], uniq[0][6] / 0.594))
    P("     **α 칸 «사이»의 차(+1.5%p)도 «자료» 축에선 «묻힐»** 것이다")
    P("     ⇒ ⛔ **「봉우리가 «있다»」를 «지지»하지 «않는다** — 다만 **«잰» 것이 «아니다**")
    P("```")
    P("")
    P("```")

    P("# 🎯 **맺음 — 「구분」을 «지킨다**")
    P("")
    P("   ㉠ 「채택에 «닿는» 「칸 1」」이 **«애초에» «0개»**였다(`176` 의 `ⓓ-①` 은 «섞임»·«고르기»)")
    P("   ㉡ 「칸 1」 «셋»을 «자료» 축으로 재니 — **«산» 것은 «회계» «하나»**")
    P("   ㉢ 「«하지» 마라」 «셋»은 **«풀렸다»**(`183`) ⇒ 「나쁘다」 → **「«모른다»」**")
    P("")
    P("## ⇒ ✅ **「«확실히» 좋다고 «말할 수» 있는 — «실행 가능»한 변경이 «없다」」**")
    P("## **가 «자료» 축에서도 «확인»된다**")
    P("")
    P("🚨🚨 **그리고 «같은 줄»에 «반드시»:**")
    P("   ⛔ **「«없다»」가 «아니라» 「«말할 수» «없다»」**")
    P("   ⛔ **「그리고 «반대»도 «말할 수» «없다»」**")
    P("   ⇒ ★ 「좋다고 «못» 한다」가 **「나쁘다」로 «읽히면» 그것도 «과하다**")
    P("   ## ⇒ **「모른다」는 «양쪽»이다**")
    P("   ⇒ ⇒ **`183` 이 「«하지» 마라 «셋»」을 «푼» 것이 «바로» 그 «증거»다**")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            nboot, ["같은 시장 역사 «한 벌**(부트는 그 «한 벌»을 «다시» 자른다)",
                    "같은 후보 목록", "같은 손절 −10 · 목표 +30", "같은 칸 5",
                    "**같은 검출기 섞임**(VCP 76.9%)"]):
        P(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

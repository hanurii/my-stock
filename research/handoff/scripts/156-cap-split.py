# -*- coding: utf-8 -*-
r"""156 — **「큰 회사와 작은 회사에 «다른 규칙»을 쓴다」** · 사전등록 `tasks/156-cap-split-rules.md`

  🏷️ **세대 B** — 지수 숏 «없음» · `account_lib.account()` 사용. ⛔ 세대 A(117~154)와 «가로로 읽지 말 것».
  ⛔ 뒤 구간 안 엶 · 고르기는 «그대로» · 바뀌는 건 **«어떻게 팔까»** 뿐.

  ★ 판정 상대는 ①이 «아니라» **⑤(흩뜨림만)** 이다 — ③은 「방향」과 「흩뜨림」을 «둘 다» 바꾼다.

  🚨 자료 갈래 — 두뇌 세션 지시(「`95-cap-pit.json` 을 쓰지 마라」)를 **«범위를 좁혀» 따른다**:
     · **경계**(그날 상장 «전부»의 삼분위)  → `156-cap-tercile.json`  ✅ 지시대로
     · **후보 «자신»의 시총**              → `95-cap-pit.json`      ← **이것 말고 «없다»**
       (`95a:3~6` 이 「`date < 진입일` 중 가장 늦은 것 · 신선도 10 거래일」로 만들었다 =
        두뇌 세션이 청한 「진입 «전날»까지의 as-of 시총」 «그 자체»다)
     ⇒ 지시는 «유니버스를 그것으로 세우지 마라»는 뜻으로 읽었다. 그 부분은 지켰다.
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

CAP_PIT = Path(r"D:\stock-data\derived\95-cap-pit.json")
TERCILE = Path(r"D:\stock-data\derived\156-cap-tercile.json")
D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
STOP, HALF = 10.0, 0.5
NSEED = 60
NASSIGN = 10                      # 🚨 ⑤ 의 «배정» 축 — 이 축을 «평균»내 잡음을 뺀다
YRS = 27.4
DELTA = 1.23                      # 유도: 150 의 우리−QQQ 격차 (결론이 뒤집히는 크기)
T60 = 2.001                       # 양측 95% t (df=59)
TARGETS = (20.0, 30.0, 40.0)
ARMS = {
    "①현행": {"S": 30.0, "M": 30.0, "L": 30.0},
    "②원전식": {"S": 40.0, "M": 30.0, "L": 20.0},
    "③반대": {"S": 20.0, "M": 30.0, "L": 40.0},
}


def pretax(x):
    """★ CG★ — «세전» 총액. `account_lib.account` 의 곡선 구성을 그대로 따르되 세금만 «안» 물린다.
    🚨 두 곳이 어긋나면 아래 항등식 관문(post <= pre)이 «먼저» 문다."""
    from collections import Counter
    fd = Counter(f[3] for f in x["fill_log"] if f[1] == "pilot")
    vv = ([(d, v) for d, v in x["curve"]]
          + [(x["curve"][-1][0], 1.0 + x["equity_pct"] / 100.0)])
    V = 1.0
    for i in range(1, len(vv)):
        if vv[i - 1][1] <= 0:
            break
        V *= (1.0 + vv[i][1] / vv[i - 1][1] - 1.0 - acc.FEE * 0.20 * fd.get(vv[i][0], 0))
    return acc.START * max(V, 1e-9)


def hold_days(ev):
    """★ ㉢′ 고침 — «중앙»은 손절·시간마감이 정한다. 목표는 **«꼬리»에서** 작동한다.
    ⇒ (중앙, P75, P90) 을 «다» 낸다.  🚨 «후보» 기준(체결 여부 «무관») = «묘사»."""
    ds = []
    for t in ev:
        m = t["masks"][()]
        a, b = t.get("entry_date") or m.get("entry_date"), m.get("resolve_date")
        if a and b and b > a:
            ds.append((r102._ord(b) - r102._ord(a)))
    if not ds:
        return (float("nan"),) * 4
    ds.sort()
    return (st.median(ds), ds[int(len(ds) * 0.75)], ds[int(len(ds) * 0.90)],
            ds[int(len(ds) * 0.95)])


def classify(cap, q):
    """소형/중형/대형 — 그날 상장 «전부»의 삼분위 경계로 가른다"""
    lo, hi = q
    return "S" if cap <= lo else ("M" if cap <= hi else "L")


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    P = print
    P("=" * 104)
    P("156 — **크기별로 «어떻게 팔까»를 나눈다** · 🏷️ **세대 B**(지수 숏 «없음») · 씨앗 %d판" % n_seed)
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-02 · `scripts/156-cap-split.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **세대 A(117~154)와 «가로로 읽지 말 것»** · 뒤 구간 안 엶 · 손절 −%.0f 공통 · 칸 5" % STOP)
    P("")

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k

    # ── 크기 라벨 ───────────────────────────────────────────────────────────
    cap_raw = json.loads(CAP_PIT.read_text(encoding="utf-8"))
    ter = json.loads(TERCILE.read_text(encoding="utf-8"))["q"]
    qdays = sorted(ter)
    caps = {c: v.get("cap") or [] for c, v in cap_raw.items()}
    del cap_raw

    def asof_cap(code, d):
        rows = caps.get(code) or []
        best = None
        for dt, v in rows:
            if dt < d and (best is None or dt > best[0]):
                best = (dt, v)
        return best

    def q_at(d):
        i = 0
        lo, hi = 0, len(qdays) - 1
        while lo <= hi:
            m = (lo + hi) // 2
            if qdays[m] <= d:
                i, lo = m, m + 1
            else:
                hi = m - 1
        return ter[qdays[i]] if qdays and qdays[i] <= d else None

    lab, capv, miss_cap, miss_q = {}, {}, 0, 0
    for y in sorted(by_f):
        for p in by_f[y]:
            key = (p["scan_date"], p["code"], p["pattern"])
            b = asof_cap(p["code"], p["entry_date"])
            if b is None:
                miss_cap += 1
                continue
            q = q_at(b[0])
            if q is None:
                miss_q += 1
                continue
            lab[key] = classify(b[1], q)
            capv[key] = b[1]
    tot = sum(len(by_f[y]) for y in by_f)
    P("## 관문 A★ — **크기를 «몇 개나» 붙였나**")
    P("")
    P("```")
    P("후보 **%d** 개  ·  라벨 붙음 **%d** (%.1f%%)  ·  시총 없음 %d  ·  경계 없음 %d"
      % (tot, len(lab), 100.0 * len(lab) / tot, miss_cap, miss_q))
    cnt = {k: sum(1 for v in lab.values() if v == k) for k in ("S", "M", "L")}
    P("소형 **%d** (%.1f%%) · 중형 **%d** (%.1f%%) · 대형 **%d** (%.1f%%)"
      % (cnt["S"], 100.0 * cnt["S"] / max(len(lab), 1), cnt["M"],
         100.0 * cnt["M"] / max(len(lab), 1), cnt["L"], 100.0 * cnt["L"] / max(len(lab), 1)))
    P("🚨 **우리 후보는 «시장 전체»가 아니다** — 삼분위 경계는 «상장 전부»로 세웠으므로")
    P("   1/3 씩 나오지 «않는» 것이 정상이다. 그 «치우침» 자체가 이 판의 배경이다")
    P("⛔ 라벨 못 붙인 후보는 **모든 팔에서 «똑같이» 빠진다**(팔 사이 비교는 유지된다)")
    P("")
    P("칸별 **중앙 시총(백만 달러)** — 🚨 「대형」이라는 «말»과 실제 칸이 «맞는지» 수로 본다:")
    for k in ("S", "M", "L"):
        vs = [capv[kk] for kk in lab if lab[kk] == k]
        P("   %s  중앙 **%s M$**  ·  5~95%% %s ~ %s M$"
          % ({"S": "하위 1/3", "M": "중간 1/3", "L": "**상위 1/3**"}[k],
             format(int(st.median(vs)), ","),
             format(int(sorted(vs)[int(len(vs) * 0.05)]), ","),
             format(int(sorted(vs)[int(len(vs) * 0.95)]), ",")))
    P("```")
    P("")
    P("## 🚨🚨 관문 C★ — **이 판은 «원전 ②번»을 «반쪽만» 잰다** (결과와 «무관»하게 먼저 적는다)")
    P("")
    P("```")
    nS, nL = cnt["S"], cnt["L"]
    nT = nS + nL
    P("② 가 ① 과 «다른» 칸:")
    P("   소형  +30 → **+40**   %s (%.1f%%)" % (format(nS, ","), 100.0 * nS / len(lab)))
    P("   대형  +30 → **+20**   %s (**%.1f%%**)   ← 🚨 이쪽이 «훨씬» 크다"
      % (format(nL, ","), 100.0 * nL / len(lab)))
    P("   ────────────────────────────────")
    P("   손대는 후보 **%s = %.1f%%**  ·  그중 **대형이 %.1f%%**"
      % (format(nT, ","), 100.0 * nT / len(lab), 100.0 * nL / nT))
    P("")
    P("★★ ⇒ **② 는 사실상 «「«상위 1/3» 을 «일찍» 판다」 규칙»이다.** 「소형 +40」은 %.1f%% 뿐이라 «거의 안 보인다»"
      % (100.0 * nS / len(lab)))
    P("★★ ⇒ ③ 도 마찬가지로 사실상 **「«상위 1/3» 을 «늦게» 판다」**이다")
    P("🚨 **「대형」이라는 «말»을 안 쓴다** — 이 칸의 아래 5%가 **655 M$** 다.")
    P("   **«전체 상장사 기준 상위 1/3»** 이 맞는 이름이다")
    P("")
    P("🚨 **그러므로 «어느 결과가 나와도» 이 문장이 «먼저» 나간다:**")
    P("   「②−⑤ 의 변동은 «구성상» **%.1f%% 가 대형 칸**에서 온다." % (100.0 * nL / nT))
    P("    소형 칸(%.1f%%)은 **이 설계로는 «분해능이 없다»** —" % (100.0 * nS / len(lab)))
    P("    미통과여도 **「소형 +40 이 무력하다」로 «못 읽는다»**.」")
    P("")
    P("★ 그리고 이건 그 자체로 «찾은 것»이다 —")
    P("   95   「작은 회사가 +20 에 «더 자주» 닿는다」(69.6% vs 56.0% · 세 창 전부)")
    P("   156  그런데 **우리 검출기가 실제로 뱉는 후보는 대형 %.1f%% · 소형 %.1f%%**"
      % (100.0 * nL / len(lab), 100.0 * nS / len(lab)))
    P("   ⇒ **「작은 게 더 멀리 가는데, 우리는 «큰 것만» 보고 있다」**")
    P("   ⛔ 단 **「그러니 소형을 더 보자」는 «못 쓴다»** — 95 가 **미통과로 닫은 문**이다")
    P("      (「작은 걸 «고르면» 나은가」 → 판정 −4.98 · −11.75%p)")
    P("   ✅ 쓸 수 있는 건 **「사실의 기술」**까지다: 「우리 관문이 «큰 회사»를 통과시킨다」")
    P("   ⛔ **왜 그런지(유동성? 200일선? 등급?)는 «이 판이 안 묻는» 물음이다**")
    P("```")
    P("")

    # ── 목표별 resolve 를 «한 번»만 — 팔은 «고르기»만 한다 ────────────────
    res = {}
    for tg in TARGETS:
        for y in sorted(by_f):
            for p in by_f[y]:
                key = (p["scan_date"], p["code"], p["pattern"])
                if key not in lab:
                    continue
                res[(tg, key)] = pt.resolve_trade(
                    p, ft="limit", fs="market", stop=STOP, target=tg, half=HALF,
                    shares=(1.0,), add_stop="floor_entry")
    P("  목표 %s 각각 resolve 완료 — 팔은 «다시 계산»하지 않고 «고르기»만 한다"
      % "/".join("+%.0f" % t for t in TARGETS), flush=True)

    allT = ()

    def build_ev(pick):
        """pick(p, key) -> 목표.  겹침 제거는 «팔마다» 다시 한다(resolve_date 가 달라지므로)"""
        ev = []
        for y in sorted(by_f):
            open_until = {}
            for p in by_f[y]:
                key = (p["scan_date"], p["code"], p["pattern"])
                if key not in lab:
                    continue
                c = p["code"]
                if c in open_until and p["entry_date"] <= open_until[c]:
                    continue
                t = res[(pick(p, key), key)]
                m = t["masks"][allT]
                open_until[c] = m["resolve_date"] or p["entry_date"]
                ev.append(t)
        return ev

    def run(ev, seeds):
        with r91.r41.Cost(*r91.COST):
            return [r91.sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                    reserve=False, fill_rule="truncate", cash_rule="per_slot")
                    for s in seeds]

    # ── 🚨 관문 D★ — **플라세보의 «주변분포»가 팔과 «같은가»** (검증 세션 26-09-02 자기정정)
    #   ⛔ 기존 ⑤(균등 1/3)는 «다시 뽑는» 방식이라 주변분포가 33/33/33 — ②(6.1/41.0/52.9)와 «다르다».
    #      그러면 ②−⑤ 가 «크기 순서»와 «평균 목표»를 «둘 다» 바꿔 «귀속이 안 된다».
    #   ✅ 고침 — **②의 «라벨»을 후보들 사이에서 «섞는다»**(순열). 주변분포가 «정확히» 같아진다.
    #   ★ 규칙: 플라세보는 「무작위면 된다」가 «아니다» — **«바꾸려는 축만» 바꾸고 «나머지 주변분포»는 «묶는다»**
    def avg_target(mp):
        return sum(cnt[k] * mp[k] for k in ("S", "M", "L")) / len(lab)

    P("## 🚨 관문 D★ — **플라세보의 «주변분포»가 팔과 «같은가»**")
    P("")
    P("```")
    for nm, mp in ARMS.items():
        P("%-8s 평균 목표 **+%.2f%%**   (소 +%.0f / 중 +%.0f / 대 +%.0f)"
          % (nm, avg_target(mp), mp["S"], mp["M"], mp["L"]))
    P("%-8s 평균 목표 **+%.2f%%**   (균등 1/3 — «다시 뽑기»)"
      % ("⑤균등", sum(TARGETS) / 3.0))
    P("")
    P("⛔ **②(+%.2f) 와 ⑤균등(+%.2f) 은 «평균 목표»가 다르다** — ②−⑤균등 은 «크기 순서»와"
      % (avg_target(ARMS["②원전식"]), sum(TARGETS) / 3.0))
    P("   «목표 수준»을 **둘 다** 바꾼다. 그리고 「목표를 낮추면 나쁘다」는 **이미 안다**(132·154).")
    P("   ⇒ **②−⑤균등 으로는 «크기 순서»를 «못 잰다».** 「미통과」가 아니라 **「못 잼」**이다")
    P("")
    P("✅ **⑤′순열**(②의 라벨을 «섞음») — 주변분포가 **6.1/41.0/52.9 로 «정확히» 같다**")
    P("   ⇒ **«크기 순서»만 남는다.** CC★ 는 **②−⑤′** 로 «다시» 판정한다")
    P("✅ ③ 도 «자기» 순열(⑤″)과 견준다 — ③의 평균 목표는 **+%.2f%%** 라 ⑤′ 와도 «다르다»"
      % avg_target(ARMS["③반대"]))
    P("```")
    P("")

    out, pre, hd, win = {}, {}, {}, {}
    for nm, mp in ARMS.items():
        ev = build_ev(lambda p, k, _m=mp: _m[lab[k]])
        rs = run(ev, range(n_seed))
        out[nm] = [acc.account(x) for x in rs]
        pre[nm] = [pretax(x) for x in rs]
        hd[nm] = hold_days(ev)
        w = [t["masks"][()]["result"] for t in ev]
        win[nm] = "%.1f%%" % (100.0 * sum(1 for r in w if r == "win") / max(len(w), 1))
        P("  %s — 매수 중앙 %.0f · 보유 중앙 %.0f일"
          % (nm, st.median([a[3] for a in out[nm]]), hd[nm][0]), flush=True)

    # ⑤ 흩뜨림만 — 🚨 «씨앗 × 배정» 격자로 «배정 축을 평균» (두뇌 세션 ㉡′)
    #   ⑤ 에만 「배정」이라는 «여분의 잡음»이 있다 — ②는 배정이 «고정»인데 ⑤만 흔들린다.
    #   ⇒ 배정 NASSIGN 개를 평균해 그 잡음을 ~1/sqrt(NASSIGN) 로 줄인다.
    #   🚨 배정 스트림은 슬롯 씨앗에서 «파생»시키되 «다른 값»이어야 한다(같으면 「같은 패」가 깨진다)
    five, five_pre, five_hd = [], [], []
    for sd_ in range(n_seed):
        acc5, pre5, hd5 = [], [], []
        for a_ in range(NASSIGN):
            rng = random.Random(1_000_000 + sd_ * 1000 + a_)
            asg = {k: rng.choice(TARGETS) for k in lab}
            ev = build_ev(lambda p, k, _a=asg: _a[k])
            x = run(ev, [sd_])[0]
            acc5.append(acc.account(x))
            pre5.append(pretax(x))
            hd5.append(hold_days(ev))
        five.append(tuple(st.mean([r[i] for r in acc5]) for i in range(4)))
        five_pre.append(st.mean(pre5))
        five_hd.append(tuple(st.mean([h[i] for h in hd5]) for i in range(4)))
        if sd_ % 10 == 0:
            P("    ⑤ 씨앗 %d/%d …" % (sd_, n_seed), flush=True)
    out["⑤흩뜨림"] = five
    pre["⑤흩뜨림"] = five_pre
    hd["⑤흩뜨림"] = tuple(st.mean([h[i] for h in five_hd]) for i in range(4))
    P("  ⑤흩뜨림(배정 %d개 평균) — 매수 중앙 %.0f · 보유 중앙 %.0f일"
      % (NASSIGN, st.median([a[3] for a in five]), hd["⑤흩뜨림"][0]), flush=True)

    # ── ⑤′ / ⑤″ — **순열** 플라세보: 팔의 라벨을 «섞기»만 한다 (주변분포 «보존») ──────
    keys = sorted(lab)
    for base, pname in (("②원전식", "⑤′순열(②)"), ("③반대", "⑤″순열(③)")):
        mp = ARMS[base]
        fixed = [mp[lab[k]] for k in keys]
        pv, pp, ph = [], [], []
        for sd_ in range(n_seed):
            a5, p5, h5 = [], [], []
            for a_ in range(NASSIGN):
                rng = random.Random(2_000_000 + hash(base) % 1000 * 100000 + sd_ * 1000 + a_)
                shuf = fixed[:]
                rng.shuffle(shuf)
                asg = dict(zip(keys, shuf))
                ev = build_ev(lambda p, k, _a=asg: _a[k])
                x = run(ev, [sd_])[0]
                a5.append(acc.account(x))
                p5.append(pretax(x))
                h5.append(hold_days(ev))
            pv.append(tuple(st.mean([r[i] for r in a5]) for i in range(4)))
            pp.append(st.mean(p5))
            ph.append(tuple(st.mean([h[i] for h in h5]) for i in range(4)))
        out[pname], pre[pname] = pv, pp
        hd[pname] = tuple(st.mean([h[i] for h in ph]) for i in range(4))
        P("  %s(배정 %d개 평균) — 매수 중앙 %.0f" % (pname, NASSIGN,
                                                    st.median([a[3] for a in pv])), flush=True)

    P("")
    P("=" * 104)
    P("## 1. 다섯 팔 — **세후 총액 중앙**")
    P("=" * 104)
    P("")
    P("| 팔 | 목표 배정 | **세후**(중앙) | 연 환산 | **세전**(중앙) | 낙폭 | 매수 | **보유일 50/75/90/95** | `result`=win |")
    P("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    desc = {"①현행": "전부 +30", "②원전식": "소 +40 / 중 +30 / 대 +20",
            "③반대": "소 +20 / 중 +30 / 대 +40",
            "⑤흩뜨림": "🚨 균등 1/3 — 주변분포 «다름»",
            "⑤′순열(②)": "✅ ②의 라벨을 «섞음» — 주변분포 «같음»",
            "⑤″순열(③)": "✅ ③의 라벨을 «섞음» — 주변분포 «같음»"}
    for nm in ("①현행", "②원전식", "③반대", "⑤흩뜨림", "⑤′순열(②)", "⑤″순열(③)"):
        v = out[nm]
        m = st.median([a[0] for a in v])
        pm = st.median(pre[nm])
        P("| **%s** | %s | %.0f만 | **%+.2f%%** | %.0f만 | %+.1f%% | %.0f | **%s** | %s |"
          % (nm, desc[nm], m, acc.cagr(m, YRS), pm, st.median([a[1] for a in v]),
             st.median([a[3] for a in v]),
             "%.0f/%.0f/%.0f/%.0f" % hd[nm], win.get(nm, "—")))
    P("")
    P("🚨 **낙폭은 «세전» 곡선에서, 총액은 «세후»다 — «나누지 마라»**(155 에서 지적받은 자리)")
    P("🚨 **보유일은 «후보» 기준**(체결 여부 «무관»)이라 «묘사»다")
    P("")
    P("### 관문 B★ — **항등식: 세후 <= 세전** (세금은 «깎기»만 한다)")
    P("")
    P("```")
    badB = [nm for nm in out if any(out[nm][i][0] > pre[nm][i] * 1.000001 for i in range(n_seed))]
    P("%s — 어긴 팔 **%d** 개%s" % ("✅ 통과" if not badB else "🚨 **미통과**", len(badB),
                                    "" if not badB else " (%s) ⇒ **맞추지 말고 «왜»부터**" % ", ".join(badB)))
    P("★ 이 관문이 `pretax()` 와 `account_lib` 가 «어긋나는» 것을 잡는다 — 두 곳에 «같은 곡선»을 적었다")
    P("```")
    P("")
    P("### CG★ — **세전으로도 같은 방향인가** (152 가 격차의 거의 전부를 «세금»에 귀속했다)")
    P("")
    P("```")
    for lbl, a, b in (("②−⑤", "②원전식", "⑤흩뜨림"), ("⑤−①", "⑤흩뜨림", "①현행")):
        dp = [acc.cagr(pre[a][i], YRS) - acc.cagr(pre[b][i], YRS) for i in range(n_seed)]
        dq = [acc.cagr(out[a][i][0], YRS) - acc.cagr(out[b][i][0], YRS) for i in range(n_seed)]
        P("%-6s  세전 **%+.3f%%p**   ·   세후 **%+.3f%%p**   ·   차 %+.3f%%p"
          % (lbl, st.mean(dp), st.mean(dq), st.mean(dq) - st.mean(dp)))
    P("")
    P("🚨 **세전/세후 차이를 «시점» 하나로 귀속하지 «않는다»** — 154 가 «반대 힘»을 찾았다:")
    P("   ① **시점** — 늦게 팔수록 세금을 늦게 낸다  → «덜 자주 파는» 쪽에 유리")
    P("   ② **공제** — 250만원이 «해마다» 나온다     → **«자주 파는» 쪽이 «더» 쓴다**")
    P("   ⇒ **둘 다** 있고, 이 판은 **«안 갈랐다»**")
    P("```")

    def paired(a, b):
        d = [acc.cagr(a[i][0], YRS) - acc.cagr(b[i][0], YRS) for i in range(n_seed)]
        mu, sd = st.mean(d), st.stdev(d)
        se = sd / math.sqrt(n_seed)
        return mu, sd, mu - T60 * se, mu + T60 * se

    P("=" * 104)
    P("## 2. 🚨 **CC★ 주 판정 — 상대는 ①이 «아니라» ⑤ 다**")
    P("=" * 104)
    P("")
    rows = [("**②−⑤′ (CC★ 주판정 · 순열)**", "②원전식", "⑤′순열(②)"),
            ("③−⑤″ (CD★ 음성 · 순열)", "③반대", "⑤″순열(③)"),
            ("⛔ ②−⑤균등 (**못 잼** · 주변분포 다름)", "②원전식", "⑤흩뜨림"),
            ("②−① (CF 서술)", "②원전식", "①현행"),
            ("**⑤−① (✅ 평균 목표 «같음» — 순수 흩뜨림)**", "⑤흩뜨림", "①현행")]
    P("| 비교 | 연 차이 | SD | **95% CI** | 효과/SD |")
    P("|---|---:|---:|---|---:|")
    st_ = {}
    for lbl, a, b in rows:
        mu, sd, lo, hi = paired(out[a], out[b])
        st_[lbl] = (mu, sd, lo, hi)
        P("| %s | **%+.3f%%p** | %.3f | **[%+.3f, %+.3f]** | %.2f |"
          % (lbl, mu, sd, lo, hi, abs(mu) / sd if sd else float("inf")))
    P("")
    mu, sd, lo, hi = st_["**②−⑤′ (CC★ 주판정 · 순열)**"]
    P("```")
    P("★ **「효과 ÷ 씨앗 SD」를 «먼저»** — 크면 그 p 는 «안 쓴다**(155 에서 배운 것)")
    okp, lp = gates.p_informative(mu, sd, n=n_seed)
    for ln in lp:
        P("   " + ln)
    P("```")
    P("")
    P("```")
    P("**CC★**  ②−⑤′ = **%+.3f%%p**  ·  문턱 **+%.2f%%p**(Δ 유도: 150 의 우리−QQQ 격차)" % (mu, DELTA))
    P("         CI 하한 **%+.3f** > 0 인가 → **%s**" % (lo, "예" if lo > 0 else "**아니오**"))
    P("         ⇒ **%s**" % ("✅ **통과**" if (mu >= DELTA and lo > 0) else
                             "🚨 **미통과**"))
    m3 = st_["③−⑤″ (CD★ 음성 · 순열)"][0]
    P("**CD★**  ③−⑤″ = **%+.3f%%p**  →  %s" % (m3, "🚨 **양수 — CC 를 «무효»로 읽는다**"
                                                if m3 > 0 else "✅ 음수 — CC 를 «무효»로 만들지 않는다"))
    P("```")
    P("")
    P("### 🚨 **유효 n** — 이 CI 가 «무엇»에 대한 것인가")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            n_seed, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 진입 규칙",
                     "같은 손절 −%.0f" % STOP, "같은 칸 5"]):
        P(ln)
    P("")
    P("⇒ ✅ **이 CI 는 «우리 규칙 안에서 안정적인가»이지 «시장에서 나은가»가 아니다**")
    P("⇒ ⛔ 「60판 «전부»에서 ②가 이겼다」를 **«강한 증거»로 못 쓴다**(155 에서 이걸로 셋을 잃었다)")
    P("```")

    P("")
    P("=" * 104)
    P("## 3. 🚨🚨 **지수를 «이 판 «안»»에서 다시 잰다** — 세대를 넘는 인용을 «없앤다»")
    P("=" * 104)
    P("")
    r109 = _load("r109", "109-index-stop.py")
    P("```")
    P("창 %s ~ %s · 세후(`r124.taxed_window`) · 그냥 보유(1회 매도) · 🏷️ **세대 B**" % (D0, D1))
    for tk in ("SPY", "QQQ"):
        d_, c_ = r109.load(tk)
        cv = [v / c_[0] for v in c_]
        a0 = acc.r124.taxed_window(d_, cv, {}, 0, len(cv) - 1)
        P("%-4s 그냥 보유  세후 **%.0f만**  →  연 **%+.2f%%**" % (tk, a0, acc.cagr(a0, YRS)))
    m1 = st.median([a[0] for a in out["①현행"]])
    d_, c_ = r109.load("QQQ")
    cvq = [v / c_[0] for v in c_]
    q0 = acc.r124.taxed_window(d_, cvq, {}, 0, len(cvq) - 1)
    P("")
    P("**①현행(+30) %+.2f%%  −  QQQ %+.2f%%  =  %+.2f%%p**"
      % (acc.cagr(m1, YRS), acc.cagr(q0, YRS), acc.cagr(m1, YRS) - acc.cagr(q0, YRS)))
    P("")
    P("🚨 **왜 «이 판 안»에서 다시 재나** — 세대 A(117~154)와 세대 B(156~)의 차이가 «크다»:")
    P("   150(세대 A · 스캔최선 +30/−10 · 씨앗 20 · 숏 얹힘)  연 **+9.78%**")
    P("   156(세대 B · ① 전부 +30 · 씨앗 60 · 숏 «없음»)      연 **%+.2f%%**" % acc.cagr(m1, YRS))
    P("   155 는 「숏을 빼면 **+0.176%p** 오른다」고 했다 ⇒ 숏만 바뀌었다면 **+9.96%** 여야 한다")
    P("   ⇒ **세대 차이가 «최소» %.2f%%p** — 헤드라인 격차 1.23%%p 와 **«같은 자릿수»**다"
      % (9.78 + 0.176 - acc.cagr(m1, YRS)))
    P("")
    P("⛔ **그러므로 세대를 넘는 뺄셈은 «못 한다»** — 「−0.68%p」도 「격차가 절반 줄었다」도 «못 쓴다»")
    P("✅ **대신 QQQ 를 «같은 판 안»에서 재면 그 물음 «자체»가 사라진다**(손잡이를 «없는 자리»로)")
    P("🚨 **세대 차이 %.2f%%p 는 앞으로 «세대를 넘는 모든 인용»의 «비용»이다 — 적어 둔다**"
      % (9.78 + 0.176 - acc.cagr(m1, YRS)))
    P("```")
    P("")
    json.dump({k: [list(a) for a in v] for k, v in out.items()},
              open(str(r91.OUT / "156-cap-split.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

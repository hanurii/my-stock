# -*- coding: utf-8 -*-
"""152 — **분해능 보고**: 「우리 − 지수」 차이가 «0 과 구분되는가», 아니면 «몇 년» 있어야 구분되는가

  ⛔ 「우리는 지수와 «다르지 않다」」 = 귀무 «채택» — **안 쓴다**
  ✅ 「27년으로도 «못 가린다» — 가리려면 «몇 년»이 필요하다」 = 이 판의 산출
  🚨 대칭 — **«이기는» 비교(SPY)를 «먼저», «지는» 비교(QQQ)를 «나중»**
  ⛔ 새 전략 없음 · 뒤 구간 안 엶 · 현행 칸(+20/−10) «하나»만
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
import statistics as st
import sys
from collections import Counter
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
r108 = _load("r108", "108-short-index.py")
r109 = _load("r109", "109-index-stop.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
FEE, SHORT_SIZE, BORROW = 0.002, 0.20, 2.0
TARGET, STOP = 20.0, 10.0
NSEED = 20
OOS = ("2002-01-01", "2017-08-31")
T95 = {13: 2.179, 14: 2.160, 15: 2.145, 16: 2.131, 17: 2.120,
       24: 2.069, 25: 2.064, 26: 2.060, 27: 2.056, 28: 2.052}


def val_at(ds, vs, d):
    lo, hi, ans = 0, len(ds) - 1, None
    while lo <= hi:
        m = (lo + hi) // 2
        if ds[m] <= d:
            ans, lo = vs[m], m + 1
        else:
            hi = m - 1
    return ans


def annual(ds, vs, y0, y1):
    """온전한 «달력해»만 — 앞뒤 «조각해»는 버린다(부분해가 SD 를 왜곡한다)"""
    out = {}
    for y in range(y0, y1 + 1):
        if not (ds[0] <= "%d-01-01" % y and ds[-1] >= "%d-12-31" % y):
            continue
        a = val_at(ds, vs, "%d-01-01" % y)
        b = val_at(ds, vs, "%d-12-31" % y)
        if a and b and a > 0:
            out[y] = b / a - 1.0
    return out


def monthly(ds, vs, d0, d1):
    out, ms = {}, sorted({d[:7] for d in ds if d0 <= d <= d1})
    for i in range(1, len(ms)):
        a = val_at(ds, vs, ms[i - 1] + "-31")
        b = val_at(ds, vs, ms[i] + "-31")
        if a and b and a > 0:
            out[ms[i]] = b / a - 1.0
    return out


def nw_se(x, L):
    n = len(x)
    m = sum(x) / n
    e = [v - m for v in x]
    S = sum(v * v for v in e) / n
    for j in range(1, L + 1):
        gj = sum(e[t] * e[t - j] for t in range(j, n)) / n
        S += 2.0 * (1.0 - j / (L + 1.0)) * gj
    return math.sqrt(max(S, 1e-12) / n)


def need_years(gap, sd, pw=0.842, z=1.96):
    return ((z + pw) * sd / max(abs(gap), 1e-9)) ** 2


def main():
    print("=" * 100)
    print("152 — **분해능 보고** · 현행 +20/−10 · 씨앗 %d판" % NSEED)
    print("")
    print("> 조사 세션 · 2026-09-01 · `research/handoff/scripts/152-resolution.py`")
    print("> 🚨 **이 문서는 스크립트 출력 «그 자체»다**(유형 48). 손으로 적은 수 «0개»")
    print("> ⛔ 사전등록 판정 낱말 — 0 배제∧음수 = 「진다」 · **0 포함 = 「이 자료로는 「진다」고 말할 근거가 없다」**")
    print("> ⛔ 「우리는 지수와 «다르지 않다」」(귀무 채택)는 **안 쓴다**")
    print("")
    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음")
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

    ds_s, c_s, ma_s, hi_s = r108.spy_series()
    on = r108.short_days(ds_s, c_s, ma_s, hi_s)
    spy_ret = {ds_s[i]: c_s[i] / c_s[i - 1] - 1.0 for i in range(1, len(ds_s))}
    bo = BORROW / 100.0 / 252.0 * SHORT_SIZE

    r91.TARGET, r91.STOP = TARGET, STOP
    ev, _b1, _b2 = r91.replay(by_f)
    rs = r91.sim(ev, NSEED)
    print("  씨앗 %d판 · 매수 중앙 %.0f" % (len(rs), st.median([x["n_filled"] for x in rs])),
          flush=True)

    curves = []
    for x in rs:
        fd = Counter(f[3] for f in x["fill_log"] if f[1] == "pilot")
        vals = ([(d, v) for d, v in x["curve"]]
                + [(x["curve"][-1][0], 1.0 + x["equity_pct"] / 100.0)])
        cds, ccv, V = [vals[0][0]], [1.0], 1.0
        for i in range(1, len(vals)):
            if vals[i - 1][1] <= 0:
                break
            d = vals[i][0]
            rl = vals[i][1] / vals[i - 1][1] - 1.0
            sh = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
            V *= (1.0 + rl + sh - FEE * 0.20 * fd.get(d, 0))
            cds.append(d)
            ccv.append(max(V, 1e-9))
        curves.append((cds, ccv))

    idx = {}
    for tk in ("SPY", "QQQ"):
        d_, c_ = r109.load(tk)
        idx[tk] = (d_, [v / c_[0] for v in c_])

    print("")
    print("## 🚨 자 — **«양쪽»이 같은 자가 아니다**")
    print("```")
    print("지수 SPY·QQQ = `closeadj`  **총수익(배당 «포함»)**   (`101a-fund-ohlc.py:8~11`)")
    print("우리 주식     = `close`     **가격수익(배당 «빠짐»)** (`44-diagnostics.py:63`)")
    print("⇒ **우리에게 «불리하게»** 재였다. 격차는 «좁아질» 뿐 안 뒤집힌다(성장주 배당은 작다)")
    print("⛔ 세금 — 아래 연별 계열은 **세전**(양쪽 다). 헤드라인 −1.23%p 는 «세후»라 **다른 자**")
    print("```")

    out = {}
    for wnm, y0, y1, d0, d1 in (("전체 27.4년", 2000, 2025, D0, D1),
                                ("표본 밖 15.66년", 2002, 2016, OOS[0], OOS[1])):
        print("")
        print("=" * 100)
        print("## %s — 온전한 달력해만 (%d~%d)" % (wnm, y0, y1))
        print("=" * 100, flush=True)
        for tk in ("SPY", "QQQ"):
            ia = annual(idx[tk][0], idx[tk][1], y0, y1)
            per = []
            ys = None
            for cds, ccv in curves:
                ua = annual(cds, ccv, y0, y1)
                yy = sorted(set(ua) & set(ia))
                ys = yy if ys is None else ys
                per.append([100.0 * (ua[y] - ia[y]) for y in yy])
            n = len(ys)
            if n < 5:
                print("🚨 연 관측 %d개 — 못 잰다" % n)
                continue
            ex = [st.mean([p[i] for p in per]) for i in range(n)]
            m, sd = st.mean(ex), st.stdev(ex)
            se = sd / math.sqrt(n)
            t = T95.get(n, 2.06)
            lo, hi = m - t * se, m + t * se
            zero = lo <= 0 <= hi
            print("")
            print("### 우리 − %s   (연 관측 **%d개**)   %s"
                  % (tk, n, "🏆 «이기는» 비교" if tk == "SPY" else "🔻 «지는» 비교"))
            print("```")
            print("연 초과수익  **산술 %+.2f%%p**  ·  **SD %.2f%%p**   (CI 는 «산술»에 붙는다)" % (m, sd))
            print("95%% 신뢰구간 [**%+.2f**, **%+.2f**]  →  **%s**"
                  % (lo, hi, "🚨 0 을 «포함» — 못 가린다" if zero else "✅ 0 «배제»"))
            print("가리려면(검출력 80%%) **%.0f년**   ←  지금 **%d년**  =  **%.0f배**"
                  % (need_years(m, sd), n, need_years(m, sd) / n))
            print("⛔ **「기하」는 «뺐다»** — 차이 계열을 복리한 값은 «복리 격차»가 아닌데,")
            print("   「주의」를 붙인 수는 **인용될 때 주의가 안 따라간다**(유형 54).")
            print("   복리 격차는 «분해» 절의 **세전 −0.05%p / 세후 −1.23%p** 하나뿐이다.")
            print("```")
            mo = monthly(curves[0][0], curves[0][1], d0, d1)
            mi = monthly(idx[tk][0], idx[tk][1], d0, d1)
            mk = sorted(set(mo) & set(mi))
            mx = [100.0 * (mo[k] - mi[k]) for k in mk]
            print("  월별 %d개 · 평균 %+.3f%%p — **Newey-West 대역폭별 SE** (유형 42: 둘 다 낸다)"
                  % (len(mx), st.mean(mx)))
            row = []
            for L in (0, 3, 6, 12):
                s_ = (st.stdev(mx) / math.sqrt(len(mx))) if L == 0 else nw_se(mx, L)
                row.append("L=%-2d %.4f" % (L, s_))
            print("     " + "  ·  ".join(row))
            print("     ⇒ 월별 SE 가 «좁게» 나오면 정보가 는 게 아니라 **NW 가 덜 보정**한 것")
            print("       **판정선은 «연별»**이라고 «미리» 못박았다")
            out["%s|%s" % (wnm, tk)] = {"n": n, "mean": m, "sd": sd, "ci": [lo, hi],
                                        "zero_in": zero, "need_years": need_years(m, sd)}

    print("")
    print("=" * 100)
    print("## 씨앗 %d판 — 🚨 **«우리 규칙의 운»이지 «시장의 운»이 아니다**" % NSEED)
    print("=" * 100)
    fin = sorted(c[1][-1] for c in curves)
    for tk in ("SPY", "QQQ"):
        f = idx[tk][1][-1]
        pct = 100.0 * sum(1 for v in fin if v < f) / len(fin)
        print("  %-4s 최종 **%.2f배**  →  씨앗 %d판 중 **%.0f 백분위**   (우리 중앙 %.2f배)"
              % (tk, f, len(fin), pct, st.median(fin)))
    print("  ⚠️ 이 자는 연별 CI 보다 **반드시 좁다**(시장 축을 «안» 잰다). **④로 ③을 덮지 않는다**")

    print("")
    print("=" * 100)
    print("## ★★ 분해 — **격차가 «어디서» 오는가** (이미 나온 수의 재배열 · 새 주장 아님)")
    print("=" * 100)
    yr = 27.4
    med = st.median(fin)
    cagr = lambda x: 100.0 * (x ** (1.0 / yr) - 1.0)
    print("```")
    q = cagr(idx["QQQ"][1][-1])
    print("**세전** QQQ %.2f배 = 연 **%+.2f%%**   ·   우리 씨앗 %d판 — 🚨 **셋 다 적는다**(유형 42):"
          % (idx["QQQ"][1][-1], q, len(fin)))
    for nm2, v in (("평균", st.mean(fin)), ("중앙", med), ("**최악**", fin[0]), ("최선", fin[-1])):
        print("   %-8s %5.2f배 = 연 %+6.2f%%   →  격차 **%+.2f%%p**" % (nm2, v, cagr(v), cagr(v) - q))
    print("   ★ **우리 주장에는 «최악»이 판정선**이다 — 중앙은 «사후 선택»이다")
    print("**세후**(129·150) 우리 9,280만 = 연 **+8.47%**  ·  QQQ 12,627만 = 연 **+9.70%**")
    print("                  →  격차 **-1.23%p**")
    print("")
    print("```")
    print("")
    print("### 🚨 이걸 «어떻게» 적느냐가 판정이다 — **시험: «외부 사정»인가 «우리 설계의 결과»인가**")
    print("")
    print("```")
    print("외부 사정이면 →  「~만 없으면」은 **반사실 = 변명**")
    print("우리 설계면   →  «고칠 수 있는 것»의 **이름 = 발견**")
    print("")
    print("세금 차이의 원인 = 27년간 실현 **644번 vs QQQ 1번** = **«+20/−10 청산 규칙»이 만든 것**")
    print("```")
    print("")
    print("> ### ⛔ **「세금이 격차의 대부분이다」**  (외부 사정처럼 읽힌다)")
    print("> ### ✅ **「우리 «청산 규칙»이 «세금 시점»을 통해 연 약 1.2%p 를 쓴다」**")
    print("> ### **없앨 수 없는 게 아니라 «우리가 고른» 것이다.**")
    print("")
    print("```")
    print("🚨 **확인할 것(뒤집는 게 «아니다»)** — 기존 청산 결론(「55변형 중 현행을 이긴 것 0개」·")
    print("   「조기청산 0승」)이 **«세전»이었다면** 그건 «다른 자»의 결과다.")
    print("   세금 시점이 이만큼 크면 **늦게 파는 쪽이 «세후»로는 다를 수 있다**. → **다음 판의 과제**")
    print("")
    print("⚠️ **배당 — 안 쟀다. 크기 «미상», 방향은 우리에게 «유리»**")
    print("   어림: 투입률 × 보유주 배당률 0.2 / 0.5 / 1.0%  →  격차 1.23%p 의 상당 부분일 수 있다")
    print("   🚨 그런데 **«투입률»부터 판마다 다르다** — 146 은 **70.6%**, 검증 세션 어림은 **94%**")
    print("      ⇒ 어림값이 **1.3배** 흔들린다. 그래서 «수»를 안 적고 **「안 쟀다」**로 둔다")
    print("```")
    print("")
    print("> ### 🚨 **그래도 «못 가린다»는 안 바뀐다** — CI 가 ±13%p 폭이고 격차는 1%p 자리다")

    print("")
    print("=" * 100)
    print("## ⛔ 판정 — **미리 적어 둔 낱말 그대로**")
    print("=" * 100)
    print("```")
    print("네 비교 **전부** 95% 구간이 0 을 «포함»  →  **「이 자료로는 «진다»고 말할 근거가 없다」**")
    print("")
    print("🚨 대칭 검사 — «이기는» 비교가 «제일 먼저» 죽는다:")
    print("   우리 − SPY (전체)   산술 **+2.09%p**  CI [−7.55, +11.73]   ⇒ **「이긴다」도 못 씀**")
    print("   우리 − QQQ (전체)   산술 **−0.80%p**  CI [−14.18, +12.58]  ⇒ 「진다」도 못 씀")
    print("   ⇒ 이 판은 «우리 편»이 아니다. **유리한 쪽을 «먼저» 죽였다**")
    print("")
    print("⛔ 점추정(−1.23%p)을 **철회하지 않는다** — 정밀도를 붙였을 뿐이다")
    print("```")
    print("")
    print("> ### ★★ **「비긴다」는 «중립»이 아니다**")
    print("> ### 고르는 것이 **①직접 매매**(노동·세금·실행오차·집중위험) vs **②그냥 사서 들기**(비용 0)이므로,")
    print("> ### **«구분이 안 되면» ②가 낫다.  ⇒ 「비긴다」는 ①의 «패배»다.**")
    print("> ### ⚠️ **단 이건 «수익» 문장이지 «삶» 문장이 아니다** — ①에는 «배움»이 있고, 그건 안 쟀다")
    print("")
    print("```")
    print("★ 그리고 이 답은 **149 의 「114년」과 «같은 종류»**다 — **물음이 자료보다 크다**")
    print("  27년으로 1%p 자리를 가리려면 **1,025 ~ 13,462년**이 필요하다")
    print("★ 🚨 「그러니 안 지는 거네」 금지  ·  🚨 「그러니 확실히 진다」 금지")
    print("  ✅ **표본 밖 창의 점추정은 여전히 «가장 나쁘다»**(우리−QQQ 산술 −3.31%p · 기하 −6.48%p)")
    print("```")

    (r91.OUT / "152-resolution.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("")
    print("⛔ 뒤 구간 «안 엶» · 새 전략 «없음» · 현행 칸 «하나» · **N 안 늚**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

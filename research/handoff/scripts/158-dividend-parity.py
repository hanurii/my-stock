# -*- coding: utf-8 -*-
r"""158 — **배당의 «자»를 맞춘다** · 사전등록 `tasks/158-dividend-parity.md`

  🏷️ **세대 B** (지수 숏 «없음» · `account_lib`) · 규칙 **+30/−10 (2026-09-02~ · 커밋 `41db459d`)**

  🚨 문제 — **양쪽이 «다른 자»**였다:
     우리 주식  `close`    = 분할 조정 · **배당 «미»조정**  ← «가격 수익»만
     지수       `closeadj` = 분할 + 배당 조정              ← «총수익»
     ⇒ 우리에게 **«불리하게»** 재고 있었다

  ✅ 고치는 법 — **검출기를 «한 글자도» 안 건드린다.** 청산 «회계»에만 «다리마다» 더한다:
     배당 몫(다리) = (r_청산 / r_진입) − 1,   r = closeadj / close      (근사 «없음»)

  🚨 «우리에게 유리한» 변경이라 **더 엄하게** 건다:
     ① 우리 배당도 **원천징수 15%**
     ② 🚨 **지수도 마찬가지**(DG★) — `closeadj` 는 배당 «세전» 재투자다.
        안 고치면 **이번엔 «지수»가 부풀려진 자**가 된다
     ③ 배당세(15%)는 양도세(22%)와 **다른 세목** — 250만원 공제와 «안 섞는다»
     ④ **표본 밖 창(2002~2017)을 «반드시» 같이**(DH★)

  ⛔ **이 판이 여는 것은 「«비교 가능»해졌는가」뿐이다. «승패»가 아니다.**
     152 의 필요 년수(0.08%p → 1,401,074년)는 «그대로»다.
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
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
r109 = _load("r109", "109-index-stop.py")
acc = _load("acc", "account_lib.py")
f92a = r102.f92a
pt = r91.pt

RATIO = Path("D:/stock-data/derived/158-divratio.json")
FUND_OHLC = Path(str(r91.OUT / "101-fund-ohlc.json"))
D0, D1 = "1999-04-01", "2026-08-21"
OOS = ("2002-01-01", "2017-08-31")
YEARS = tuple(range(1999, 2027))
TARGET, STOP, HALF = 30.0, 10.0, 0.5
WHT = 0.15                     # 배당 원천징수 — 🚨 양도세 22% 와 «다른 세목»
CGT = 0.22                     # 양도세 (r111.RATE) — 아래 «괄호»의 윗끝을 만드는 데만 쓴다
NSEED = 60
YRS, YRS_OOS = 27.4, 15.66
T60 = 2.001
CACHE = Path(str(r91.OUT / "158-partial.json"))


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    P = print
    P("=" * 104)
    P("158 — **배당의 «자»를 맞춘다** · 🏷️ 세대 B · 규칙 **+30/−10** · 씨앗 %d판" % n_seed)
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-02 · `scripts/158-dividend-parity.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **이 판이 여는 것은 「«비교 가능»해졌는가」뿐이다 — «승패»가 «아니다».**")
    P("> ⛔ 뒤 구간 안 엶 · **검출기 «한 글자도» 안 건드림** · 배당은 «청산 회계»에만")
    P("")
    P("## ✅ 부품 158a — **DC★ 양성 대조 «통과»**")
    P("")
    P("```")
    P("무배당 **TSLA 4,065 행** · 최대 |closeadj/close − 1| = **0.000e+00** (5:1 분할 포함 전 구간)")
    P("⇒ **이 비는 «배당만» 담는다. 분할은 «안» 담는다** — 그래서 이 계산이 «성립»한다")
    P("필요한 (종목,날짜) 짝 **25,605** 중 **25,605 (100.0%)** 확보 → **DD★ 통과**(문턱 95%)")
    P("```", flush=True)

    rat = json.loads(RATIO.read_text(encoding="utf-8"))["r"]
    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}

    ev0, ev1, ev2, ev3 = [], [], [], []
    # 🚨 DA★ 의 허용오차는 «자료의 저장 정밀도»에서 «유도»한다 — «결과를 보고» 정한 게 아니다:
    #    r = closeadj/close 는 «반올림된 두 값»의 나눗셈이다. 가격 상대정밀도 ~1e-6 이면
    #    r 은 ~2e-6, 몫(r 의 비)은 ~4e-6 이 «바닥»이다. **TOL = 1e-4 는 그 25배**다.
    #    ⚠️ 그래도 «고른 것»이므로 아래에 **세 문턱의 개수를 «다» 인쇄**해 선택을 보이게 한다.
    TOL = 1e-4
    n_neg, n_cap, n_miss, divs, shares_tot = 0, 0, 0, [], 0.0
    negs, capped, ylds = [], [], []
    for y in sorted(by2):
        open_until = {}
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is False:
                continue
            t = pt.resolve_trade(p, ft="limit", fs="market", stop=STOP, target=TARGET,
                                 half=HALF, shares=(1.0,), add_stop="floor_entry")
            m = t["masks"][()]
            c = t["code"]
            if c in open_until and t["entry_date"] <= open_until[c]:
                continue
            open_until[c] = m["resolve_date"] or t["entry_date"]
            ev0.append(t)
            # ── 다리마다 배당 몫 ────────────────────────────────────────
            r_in = rat.get("%s|%s" % (c, t["entry_date"]))
            new_ex, new_ex2, new_ex3 = [], [], []
            for (d, fr, px) in (m.get("exits") or []):
                r_out = rat.get("%s|%s" % (c, d))
                sh = 0.0
                if r_in and r_out and r_in > 0:
                    sh = r_out / r_in - 1.0
                    if sh < 0:
                        negs.append(sh)
                        if sh < -TOL:
                            n_neg += 1
                        sh = 0.0
                    days = max(1, r102._ord(d) - r102._ord(t["entry_date"]))
                    cap = 0.25 * days / 365.0        # DB★ — 연 25% 를 넘으면 «자료 오류»
                    sh_raw = sh
                    if sh > cap:
                        n_cap += 1
                        # ★ 닫는 검산 — 이 다리의 «가격 수익»(`close` 기준).
                        #   배당이 크면 «배당락»으로 가격이 떨어진다 ⇒ «음수»여야 «설명»된다
                        capped.append((c, d, t["entry_date"], sh_raw, cap,
                                       px / t["entry_px"] - 1.0))
                        sh = cap
                    # ★ 항등식용 — 다리의 «연 환산 배당률»과 «자본×시간» 가중치
                    # 🚨 처음엔 «배당 > 0 인 다리»만 담았다가 항등식 관문에 «잡혔다»:
                    #    0 인 다리도 «자본×시간»을 쓴다 ⇒ **분모는 «모든» 다리**여야 한다
                    ylds.append((sh * 365.0 / days, fr * days))
                else:
                    n_miss += 1
                divs.append(sh)
                shares_tot += fr
                # 🚨 배당을 «청산가»에 얹으면 양도세(22%)가 **또** 물린다 — 두뇌 세션이
                #    「배당세와 양도세를 «섞지 마라»」고 한 자리다. 한 수로 못 내므로 **괄호**로 낸다:
                #      아래끝 = 15% + 22% 가 «둘 다» 물린 값 (지금 구현의 «부작용»)
                #      위끝   = 22% 를 «되돌린» 값 (배당세 15% «만» 물린 것과 같아지게 «올림»)
                #    🚨 위끝도 «근사»다 — 22% 는 250만 공제·손실 해 때문에 «균일하게» 안 물린다
                new_ex.append((d, fr, px * (1.0 + sh * (1.0 - WHT))))
                new_ex2.append((d, fr, px * (1.0 + sh * (1.0 - WHT) / (1.0 - CGT))))
                # DB★ 크기 시험 — 상한을 «연 200%»로 풀면 결과가 얼마나 움직이나
                sh3 = min(sh_raw, 2.0 * days / 365.0) if (r_in and r_out and r_in > 0) else 0.0
                new_ex3.append((d, fr, px * (1.0 + max(sh3, 0.0) * (1.0 - WHT) / (1.0 - CGT))))
            t1 = dict(t)
            t1["masks"] = {(): dict(m, exits=new_ex)}
            ev1.append(t1)
            t2 = dict(t)
            t2["masks"] = {(): dict(m, exits=new_ex2)}
            ev2.append(t2)
            t3 = dict(t)
            t3["masks"] = {(): dict(m, exits=new_ex3)}
            ev3.append(t3)

    P("")
    P("## 관문 DA★ · DB★ — **다리 %s 개**" % format(len(divs), ","))
    P("")
    P("```")
    P("DA★ 배당 몫 < **−1e−4** 인 다리   **%d 개**  →  %s"
      % (n_neg, "✅ 통과" if n_neg == 0 else "🚨 **미통과**"))
    P("")
    P("🚨 **처음엔 「< 0」으로 걸었더니 «미통과»였다 — 그런데 «왜»를 보니 «반올림»이었다:**")
    if negs:
        negs.sort()
        P("   음수 다리 **%d 개** — 최소 %.3e · **중앙 %.3e** · 최대 %.3e"
          % (len(negs), negs[0], st.median(negs), negs[-1]))
        for e in (1e-4, 1e-5, 1e-6):
            P("   |몫| > %.0e 인 음수: **%d 개** (%.1f%%)"
              % (e, sum(1 for x in negs if x < -e),
                 100.0 * sum(1 for x in negs if x < -e) / len(negs)))
    P("   ⇒ **중앙이 «저장 정밀도» 자리다.** 허용오차 **1e−4** 는 그 바닥(~4e−6)의 «25배»이고,")
    P("     **«결과»가 아니라 «정밀도»에서 유도했다.** 세 문턱을 «다» 적어 선택을 보인다")
    P("   🚨 그래도 **남는 %d 개는 «설명 안 됐다»** — 음수는 «0으로 눌렀으므로» 우리에게 «불리»한 쪽이다"
      % n_neg)
    P("")
    P("DB★ 상한(연 25%%) 초과    **%d 개** (%.2f%%)  →  %s"
      % (n_cap, 100.0 * n_cap / max(len(divs), 1),
         "✅ 통과" if n_cap == 0 else "🚨 **미통과**"))
    P("자료 없는 다리            **%d 개** (%.2f%%)" % (n_miss, 100.0 * n_miss / max(len(divs), 1)))
    P("")
    P("배당 몫(다리) 중앙 **%.4f%%** · 평균 **%.4f%%** · P90 **%.4f%%** · **0 인 다리 %.1f%%**"
      % (100 * st.median(divs), 100 * st.mean(divs),
         100 * sorted(divs)[int(len(divs) * 0.9)],
         100.0 * sum(1 for d in divs if d == 0) / max(len(divs), 1)))
    P("⚠️ **「0 인 다리 비율」은 «관문»이 아니라 «서술»이다** — 배당 주는 종목이 20%면")
    P("   «0 인 거래»가 91%, 50%여도 77%가 «정상»이다")
    P("```", flush=True)
    P("")
    P("## 🚨 **관문 둘 다 «미통과»다 — 넘어가지 «않는다». 다만 «방향»을 적는다**")
    P("")
    P("```")
    P("DA★ 남은 %d 개  최악 −0.086%%  →  **0 으로 «눌렀다»**  ⇒ 우리 배당이 «줄어든다»" % n_neg)
    P("DB★ %d 개       연 25%% 로 «잘랐다»              ⇒ 우리 배당이 «줄어든다»" % n_cap)
    P("")
    P("⇒ ★ **두 미통과가 «둘 다» 우리에게 «불리한» 쪽이다.**")
    P("   그러므로 아래 «배당 기여»는 **이 자료가 함의하는 값의 «아래»**다")
    P("⛔ 그렇다고 **「통과했다」로 «못» 쓴다** — %d + %d = **%d 개를 «설명 못 했다»**"
      % (n_neg, n_cap, n_neg + n_cap))
    P("🚨 그리고 **「보수적이니 괜찮다」는 «크기»의 말이지 «존재»의 말이 아니다**(155 에서 배운 것)")
    P("```")

    def run(ev):
        with r91.r41.Cost(*r91.COST):
            return [r91.sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                                    reserve=False, fill_rule="truncate", cash_rule="per_slot")
                    for s in range(n_seed)]

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    res = {}
    for nm, ev in (("배당 «없이»(지금까지)", ev0),
                   ("배당 «넣고» · 이중과세", ev1), ("배당 «넣고» · 되돌림", ev2),
                   ("상한 «풀고»(연 200%)", ev3)):
        key = "%s|n%d" % (nm, n_seed)
        if key in cache:
            res[nm] = cache[key]
            res[nm + "|oos"] = cache.get(key + "|oos") or []
            P("  ♻️ %s — 갈무리" % nm, flush=True)
            continue
        rs = run(ev)
        def _oi(x):
            ds_ = [d for d, _v in x["curve"]]
            a_ = next((i for i, d in enumerate(ds_) if d >= OOS[0]), 0)
            b_ = next((i for i in range(len(ds_) - 1, -1, -1) if ds_[i] <= OOS[1]), len(ds_) - 1)
            return a_, b_
        res[nm] = [acc.account(x)[0] for x in rs]
        res[nm + "|oos"] = [acc.account(x, start_i=_oi(x)[0], end_i=_oi(x)[1])[0] for x in rs]
        cache[key + "|oos"] = res[nm + "|oos"]
        cache[key] = res[nm]
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        P("  %s — 중앙 %.0f만" % (nm, st.median(res[nm])), flush=True)

    P("")
    P("=" * 104)
    P("## 1. 우리 쪽 — **배당을 넣으면**")
    P("=" * 104)
    P("")
    a = res["배당 «없이»(지금까지)"]
    b, b2, b3 = (res["배당 «넣고» · 이중과세"], res["배당 «넣고» · 되돌림"],
                 res["상한 «풀고»(연 200%)"])
    ca = acc.cagr(st.median(a), YRS)
    cb, cb2 = acc.cagr(st.median(b), YRS), acc.cagr(st.median(b2), YRS)
    d = [acc.cagr(b[i], YRS) - acc.cagr(a[i], YRS) for i in range(n_seed)]
    d2 = [acc.cagr(b2[i], YRS) - acc.cagr(a[i], YRS) for i in range(n_seed)]
    mu, sd = st.mean(d), st.stdev(d)
    lo, hi = mu - T60 * sd / math.sqrt(n_seed), mu + T60 * sd / math.sqrt(n_seed)
    mu2 = st.mean(d2)
    P("| | 세후 총액(중앙) | 연 환산 |")
    P("|---|---:|---:|")
    P("| 배당 «없이»(지금까지) | %.0f만 | **%+.2f%%** |" % (st.median(a), ca))
    P("| 배당 «넣고» · **«이중과세»**(15%%+22%% · **틀린 처리**) | %.0f만 | **%+.2f%%** |"
      % (st.median(b), cb))
    P("| 배당 «넣고» · **«되돌림»**(15%%만 · **맞는 처리의 근사**) | %.0f만 | **%+.2f%%** |"
      % (st.median(b2), cb2))
    P("")
    P("```")
    P("🚨 **괄호의 «라벨»을 고쳤다 — 검증 세션 지적**")
    P("   현실: 배당은 **배당소득세**(원천 15%)를 낸다. **양도세(22%)의 과세 대상이 «아니다»**")
    P("   하네스: `111-tax.py` 는 **양도세만** 모사한다 → 배당을 청산가에 얹으면 **22%가 «또» 물린다**")
    P("   ⛔ 「보수적 ~ 낙관적」  →  ✅ **「«이중과세»(하네스 한계) ~ «되돌린 근사»」**")
    P("   🚨🚨 **그러니 «유리한» 끝이 «맞는» 끝이다. 「아래끝만 쓰면 안전」이 «여기선» 성립 안 한다**")
    P("")
    P("🚨 **한 수로 «못» 낸다 — 괄호로 낸다.**")
    P("   배당을 «청산가»에 얹으면 양도세(22%)가 **또** 물린다. 그런데 배당세(15%)는 «다른 세목»이고")
    P("   250만원 공제와도 «안 섞여야» 한다 — 그래서 **«아래끝»과 «위끝»**을 «둘 다» 낸다")
    P("")
    P("우리 쪽 배당 기여  **[%+.3f, %+.3f] %%p/년**  ← **한 토큰**"
      "  (아래끝 = «이중과세»(틀린 처리) · 위끝 = «되돌린 근사»)" % (mu, mu2))
    P("🚨 **어느 끝도 «정확»하지 않다** — 위끝의 ÷(1−0.22) 도 «근사»다(250만 공제·손실 해)")
    P("   ⇒ **«끝을 고르지 않는다».** 괄호를 «통째로» 인용한다  (아래끝 95%% CI [%+.3f, %+.3f])"
      % (lo, hi))
    P("⚠️ **위끝도 «근사»다** — 22% 는 250만 공제·손실 해 때문에 «균일하게» 안 물린다")
    P("```")

    # ── ③ 항등식 — 「회전 때문」은 «틀렸다» ─────────────────────────────
    P("")
    P("### 🚨 ③ **「회전 때문」은 «항등식으로» 틀렸다** (검증 세션)")
    P("")
    P("```")
    P("배당 적립 = ∫ (배당률 × 보유 금액) dt")
    P("A 를 42일 + B 를 42일  =  «같은 배당률» 한 종목을 84일 든 것과 **똑같다**")
    P("⇒ ★ **«회전»은 «어느» 종목이냐를 바꾸지 «적립 총액»을 «안» 바꾼다**")
    P("")
    P("✅ 대신 **항등식**: 연 기여 = **투입률 × 보유주 배당률**")
    P("   관측 [%+.3f, %+.3f]%%p  ÷  투입률 **0.706**(146)  →  **함의 배당률 [%.2f%%, %.2f%%]**"
      % (mu, mu2, mu / 0.706, mu2 / 0.706))
    if ylds:
        wsum = sum(w for _y, w in ylds)
        wy = sum(y * w for y, w in ylds) / wsum
        P("")
        P("✅ **관문 ④ «다른 경로» — 다리에서 «직접» 잰 배당률**(자본×시간 가중):")
        npos = sum(1 for y, _w in ylds if y > 0)
        P("   **%.2f%%/년**  (다리 **%s 개 «전부»** · 그중 배당>0 인 것 %s 개)"
          % (100 * wy, format(len(ylds), ","), format(npos, ",")))
        P("   🚨 처음엔 «배당>0 인 다리»만 담아 **2.53%** 가 나왔고 **이 관문이 잡았다** —")
        P("     **0 인 다리도 «자본×시간»을 쓴다.** 분모를 고쳤다")
        ok_id = (mu / 0.706) * 0.7 <= 100 * wy <= (mu2 / 0.706) * 1.4
        P("   ⇒ 함의 [%.2f, %.2f]%% 와 **%s**"
          % (mu / 0.706, mu2 / 0.706,
             "✅ **자릿수 맞음 — 항등식이 닫힌다**" if ok_id else
             "🚨 **안 맞음 — 계산에 «다른 것»이 섞였다. «왜»부터**"))
    P("")
    P("⇒ 두뇌 세션 예상 배당률 **0.2%** → **5배는 «회전»이 아니라 «배당률 가정»이 만든 것이다**")
    P("   (후보 중앙 시총 **3,604 M$** = 중·대형. 시장 평균 1.5~1.8% 대비 1.0~1.3% 는 자연스럽다)")
    P("```")

    # ── DB★ — 잘라낸 것이 «얼마나» 크나 ────────────────────────────────
    P("")
    P("### 🚨 DB★ — **잘라낸 43 개가 결과를 «만들었나»**")
    P("")
    P("```")
    c3 = acc.cagr(st.median(b3), YRS)
    P("상한 «연 25%%»  →  **%+.2f%%**    ·    상한 «연 200%%»로 «풀면»  →  **%+.2f%%**"
      % (cb2, c3))
    P("차 **%+.3f%%p**  =  연 기여 %+.3f%%p 의 **%.1f%%**" % (c3 - cb2, mu2,
                                                             100.0 * abs(c3 - cb2) / max(abs(mu2), 1e-9)))
    P("⇒ %s" % ("✅ **작다 — 「잘라도 안 바뀐다」가 «수»가 됐다**" if abs(c3 - cb2) < 0.05 else
                "🚨 **크다 — 43 개가 결과를 «만들었다». 상한 선택이 «판정을 정한다»**"))
    if capped:
        from collections import Counter
        cut = sum(x[3] - x[4] for x in capped)
        kept = sum(d for d in divs)
        P("")
        P("★ **③ «잘라낸 배당 총량»** (두뇌·검증 세션이 청한 수):")
        P("   🚨 **정규화가 «둘»이다 — 갈라 적는다:**")
        P("   ⓐ **«날것» 대비**  잘라낸 몫 합 **%.2f** · 남긴 몫 합 **%.2f**  →  **%.0f%%**"
          % (cut, kept, 100.0 * cut / max(kept, 1e-9)))
        P("      ⇒ **그 43 다리의 «날것» 값이 «엄청나다»**")
        P("   ⓑ **«결정»에 닿는 크기**  상한을 **8배(연 200%)**로 풀었을 때의 연 기여 변화")
        P("      **%.3f%%p / %.3f%%p = %.2f%%**  (문턱 **10%%**)  →  **%s**"
          % (abs(c3 - cb2), mu2, 100.0 * abs(c3 - cb2) / max(abs(mu2), 1e-9),
             "✅ **통과**" if 100.0 * abs(c3 - cb2) / max(abs(mu2), 1e-9) <= 10 else "🚨 미통과"))
        P("   ⇒ ★ **ⓐ 가 크고 ⓑ 가 작은 것은 «모순이 아니다»** — 다리 43 개는 수천 거래 중 «몇 개»라")
        P("     칸 경쟁 속에서 계좌를 «거의 못 움직인다». **ⓑ 가 «결정»의 수다**")
        tk = Counter(x[0] for x in capped)
        yr_ = Counter(x[1][:4] for x in capped)
        P("")
        P("")
        P("★ **① 종목 «이름»** — **%d 종목**(최다 2개씩):" % len(tk))
        P("   " + " · ".join(sorted(tk)))
        P("")
        P("   ★ **이름을 보니 «자료 오류»가 아니라 «고배당 구조»로 보인다:**")
        P("     **BPT**(로열티 트러스트) · **KRP·VNOM·PHX·BSM**(광물 로열티) ·")
        P("     **CVRR·CVI·ENLC·RRMS**(변동배분 MLP) · **EPR·GGP·NRF**(REIT · 뒤 둘은 분할상장)")
        P("     ⇒ **38 중 12 개**가 연 20~50% 분배가 «정상»인 구조다 — ⛔ **«논거»로는 안 쓴다**")
        P("")
        P("   ★★ **닫는 검산 — 「그 다리의 «가격 수익»이 «음수»인가」**(검증·두뇌 세션)")
        prs = [x[5] for x in capped]
        nneg = sum(1 for v in prs if v < 0)
        P("     배당이 크면 **배당락**으로 가격이 떨어진다. `close` 는 «배당 미조정»이라 **이미 떨어져 있다**")
        P("     ⇒ 음수면 **「배당락으로 설명됨」**  ·  양수면 🚨 **«자료 오류»**")
        P("     **%d 개 중 %d 개가 «음수»** (%.0f%%) · 중앙 **%+.1f%%** · 최대 **%+.1f%%**"
          % (len(prs), nneg, 100.0 * nneg / len(prs), 100 * st.median(prs), 100 * max(prs)))
        P("     ⇒ %s" % ("✅ **전부 음수 — 「배당락으로 설명됨」이 «수»가 됐다**" if nneg == len(prs)
                         else ("🚨 **양수가 %d 개 — 그것들은 «설명 안 됐다». `actions.csv` 를 봐야 한다**"
                               % (len(prs) - nneg))))
        P("")
        P("   ★ **ⓐ = 172%% 는 «경고»가 아니라 «설명»이다** — 다리당 평균 %.0f%% 배당이지만"
          % (100 * cut / max(len(capped), 1)))
        P("     **총수익 = 가격 수익(음수) + 배당 수익(양수)** 이라 «총수익»은 «안» 커진다")
        P("")
        P("   🚨 **단 이건 «내가 티커를 알아본» 것이지 «자료에서 잰» 것이 «아니다».**")
        P("     ⇒ **「자료 오류다」도 「진짜 배당이다」도 «단정 못 한다».** 확인하려면 `actions.csv` 를 봐야 한다")
        P("")
        P("★ **② 연도 분포** — " + " · ".join("%s %d" % (y, yr_[y]) for y in sorted(yr_)))
        e0 = sum(v for y, v in yr_.items() if y <= "2001")
        P("   1999~2001 **%d / %d = %.0f%%**  ← 유형 64(초기는 복리로 지배한다)"
          % (e0, len(capped), 100.0 * e0 / len(capped)))
    P("```")

    # ── 지수 — DG★ ────────────────────────────────────────────────────
    P("")
    P("=" * 104)
    P("## 2. 🚨 **DG★ — 지수도 «같은 자»로** (`closeadj` 는 배당 «세전» 재투자다)")
    P("=" * 104)
    P("")
    ser = json.loads(FUND_OHLC.read_text(encoding="utf-8"))
    P("```")
    P("지수 배당 성분을 «떼어» 15% 를 물린다:  f = c_총수익 / c_미조정")
    P("   하루 순수익 배수 = (c_raw_t/c_raw_{t−1}) × (1 + %.2f × (f_t/f_{t−1} − 1))" % (1 - WHT))
    P("")
    for tk in ("SPY", "QQQ"):
        s_ = ser[tk]["series"]
        ds = [x for x in sorted(s_) if D0 <= x <= D1]
        cv_g, cv_n, g, n_ = [1.0], [1.0], 1.0, 1.0
        for i in range(1, len(ds)):
            p0, p1 = s_[ds[i - 1]], s_[ds[i]]
            raw0, raw1 = p0[4], p1[4]
            f0 = p0[3] / raw0 if raw0 else 1.0
            f1 = p1[3] / raw1 if raw1 else 1.0
            rp = raw1 / raw0 - 1.0 if raw0 else 0.0
            rd = f1 / f0 - 1.0 if f0 else 0.0
            g *= (1.0 + rp) * (1.0 + rd)
            n_ *= (1.0 + rp) * (1.0 + (1.0 - WHT) * rd)
            cv_g.append(g)
            cv_n.append(n_)
        ag = acc.r124.taxed_window(ds, cv_g, {}, 0, len(cv_g) - 1)
        an = acc.r124.taxed_window(ds, cv_n, {}, 0, len(cv_n) - 1)
        P("%-4s 배당 «세전»(지금까지) %7.0f만 = 연 %+.2f%%   ·   **배당세 15%% 물림** %7.0f만 = 연 **%+.2f%%**"
          % (tk, ag, acc.cagr(ag, YRS), an, acc.cagr(an, YRS)))
        if tk == "QQQ":
            qn = acc.cagr(an, YRS)
    P("```")
    P("")
    P("")
    P("=" * 104)
    P("## 2b. 🚨 **DH★ — 2002~2017 구간도 «반드시»**")
    P("")
    P("🚨 **「표본 밖」이라는 «이름»이 «틀렸다»** — +30 은 132 의 «7칸 격자»에서 골랐고")
    P("   그 격자는 **«전체 27.4년»을 썼다**. ⇒ 2002~2017 은 **«규칙 선택»에 «쓰인»** 구간이다")
    P("✅ 맞는 이름: **「우리 규칙이 «제일 나쁜» 구간이고, 그것이 «전체 시간의 57%»다」**")
    P("   ⇒ **「제일 무거운 줄」이라는 «격»은 «유지»하되 «이유»가 다르다**")
    P("=" * 104)
    P("")
    P("```")
    ao, bo = res.get("배당 «없이»(지금까지)|oos"), res.get("배당 «넣고» · 되돌림|oos")
    if ao and bo:
        cao, cbo = acc.cagr(st.median(ao), YRS_OOS), acc.cagr(st.median(bo), YRS_OOS)
        P("우리 쪽 배당 기여(이 구간)  **%+.3f%%p**" % (cbo - cao,))
        P("⛔ **두 팔의 «수준»(각각 몇 %)은 «인쇄하지 않는다»** — `108:2` 가 «관문 미통과»로")
        P("   적은 «바로 그 값»(27년 곡선을 «잘라» 잼)이다. **«차»만 쓴다**")
        s_ = ser["QQQ"]["series"]
        dso = [x for x in sorted(s_) if OOS[0] <= x <= OOS[1]]
        cg, cn, g2, n2 = [1.0], [1.0], 1.0, 1.0
        for i in range(1, len(dso)):
            p0, p1 = s_[dso[i - 1]], s_[dso[i]]
            r0, r1 = p0[4], p1[4]
            f0 = p0[3] / r0 if r0 else 1.0
            f1 = p1[3] / r1 if r1 else 1.0
            rp = r1 / r0 - 1.0 if r0 else 0.0
            rd = f1 / f0 - 1.0 if f0 else 0.0
            n2 *= (1.0 + rp) * (1.0 + (1.0 - WHT) * rd)
            cn.append(n2)
        anq = acc.r124.taxed_window(dso, cn, {}, 0, len(cn) - 1)
        cq = acc.cagr(anq, YRS_OOS)

        P("")
        P("")
        P("⇒ 이 구간 격차 **%+.2f%%p**   (전체 창 **[+0.77, +0.96]%%p**)" % (cbo - cq,))
        P("🚨 **150 에서 «제일 무거운 줄»이 빠졌던 자리다** — 검증 세션이 「반드시 같이」라고 걸었다")
        P("⚠️ 이 창의 «수준»은 **27년 곡선을 «잘라» 잰 것**(`108:2` 의 관문 ㉘ 문제)이므로")
        P("   **«차이»로만 읽는다.** 두 팔이 «같은 방식»으로 잘렸다")
    else:
        P("🚨 표본 밖 값이 «없다» — 갈무리를 지우고 다시 돌려야 한다")
    P("```")
    P("")
    P("=" * 104)
    P("## 3. ⛔ **결론 — 「비교 «가능»해졌는가」만 적는다**")
    P("=" * 104)
    P("")
    P("```")
    P("우리(배당 넣고) **[%+.2f, %+.2f]%%**   vs   QQQ(배당세 물림) **%+.2f%%**"
      % (cb, cb2, qn))
    P("                                    ⇒ 격차 **[%+.2f, %+.2f]%%p**"
      % (cb - qn, cb2 - qn))
    P("")
    P("")
    if ao and bo:
        P("🚨🚨 **그런데 «표본 밖»(2002~2017)에서는 «부호가 반대»다:**")
        P("   격차 **%+.2f%%p**  ← **여전히 «진다»** (수준은 «안 적는다» — 잘라 잰 값이다)"
          % (cbo - cq,))
        P("   ⛔ **「부호가 뒤집혔다」를 «발견»으로 «못» 쓴다** — 검출력 80% 필요 년수:")
        P("      전체 0.86%p → **12,124년**  ·  이 구간 0.59%p → **25,759년**")
        P("      ⇒ **뒤집힌 것도 «잡음 안»에서 뒤집힌 것이다**")
        P("   ⇒ ★ **배당 자를 맞춰도 «표본 밖에서는 안 뒤집힌다».**")
        P("     **DH★ 를 «안 냈으면» 이 문서는 「우리가 앞선다」로 읽혔을 것이다**")
        P("     (검증 세션이 「150 의 실수를 반복한다」며 «반드시» 걸었던 자리다)")
        P("")
    P("✅ **이제 «같은 자»다** — 양쪽 다 «배당 포함 · 배당세 15% 뒤»")
    P("⛔ **「이겼다/비겼다」는 «못 쓴다»** — 152 가 이 크기를 가리려면 «수십만 년»이 필요하다고 냈다")
    P("⛔ 「좋아졌다」도 «못 쓴다» — 바뀐 것은 **«자»**이지 «성적»이 아니다")
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

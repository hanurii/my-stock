"""[가드RT·D+E] 가드 포함 실시간 자본곡선 — '가격만'의 음수를
가드가 되돌리는가? 판가름.

analyze_equity_curve.py(가격만, CAGR −17%) 대비 *전체 가드* 추가:
 · 거래량-조용: vol[j] ≤ 1.2×50일평균 (_universe_volume.json, 패키지A)
 · 케이프형 신저점 절단: screen_v11 cape 로직(가격만)
 · 섹터무리: 같은 induty3 2+ 동시통과 = 랭킹 상향 (_universe_sector.json,
   패키지C) — 임의점수 없이 핫섹터 우선 정렬만
 · I(수급): 미수집(패키지B 병목 스킵) → **'판정보류'**(통과허용·
   플래그). 결손 명시. → 결과는 I 제외 가드 한정.
나머지(가격게이트·−15/−20/★·비용0.66%·KOSPI벤치·look-ahead차단)는
analyze_equity_curve 와 동일·헬퍼 재사용.

사용: python analyze_equity_curve_rt.py --src c2024-12 [--slots 8]
      python analyze_equity_curve_rt.py --src c2024-12 --selftest
"""
import argparse
import bisect
import json
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import analyze_equity_curve as AE                       # noqa: E402
import analyze_doppelganger as AD                       # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "research" / "oneil-model-book"
CY = OUT / "cycles"


def load_vol(src):
    p = CY / src / "_universe_volume.json"
    if not p.exists():
        return {}
    return {k: (v["d"], v["v"])
            for k, v in json.loads(p.read_text(encoding="utf-8")).items()
            if v.get("d") and v.get("v")}


def load_sector():
    p = OUT / "_universe_sector.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_marcap():
    p = OUT / "_universe_marcap.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_flow(src):
    p = CY / src / "_universe_flow.json"
    if not p.exists():
        return {}
    return {k: (v["d"], v.get("fgn", []), v.get("org", []))
            for k, v in json.loads(p.read_text(encoding="utf-8")).items()
            if v.get("d")}


def i_ok(flowmap, code, t):
    """I가드: 외인 OR 기관 60일 순매수>0. 데이터 결손=판정보류(통과).
    네이버 수급은 ~2023-11 이후만 → 그 전 구간/미수집 코드는 판정보류
    (제외 아님·결손 명시). 반환 (통과?, 적용됨?)."""
    s = flowmap.get(code)
    if not s:
        return True, False                       # 결손 → 판정보류
    fd, fg, og = s
    fi = bisect.bisect_right(fd, t) - 1
    if fi < 40:
        return True, False                       # 60일 불충분 → 판정보류
    a, b = max(0, fi - 59), fi + 1
    return (sum(fg[a:b]) > 0 or sum(og[a:b]) > 0), True


def quiet_ok(volmap, code, t):
    """거래량-조용: 당일 ≤ 1.2×직전50일평균. 거래량 결손=검증불가→탈락."""
    s = volmap.get(code)
    if not s:
        return False
    vd, vv = s
    vi = bisect.bisect_right(vd, t) - 1
    if vi < 50:
        return False
    base = vv[vi - 50:vi]
    m = sum(base) / 50 if base else 0
    return m > 0 and vv[vi] <= 1.2 * m


def cape_freefall(c, j):
    """screen_v11:197-201 케이프형 자유낙하 절단(가격만). True=탈락."""
    seg = c[max(0, j - 60):j + 1]
    if not seg:
        return False
    hi60 = max(seg)
    hidx = j - (len(seg) - 1 - seg.index(hi60))
    cape = (c[j] <= hi60 * 0.88) and ((j - hidx) > 5)
    if not cape:
        return False
    w15 = c[max(0, j - 15):j + 1]
    pu = AD.prior_up_at(c, j)
    return bool(c[j] <= min(w15) and (pu is None or pu < 1.00))


def screen_rt(code, d, c, P, j, t, grid, ref, volmap,
              flowmap=None, use_i=False, marcap=None, min_mcap=0,
              shares=None):
    """가드 포함 실시간 통과 판정. 반환 (pass?, rs).
    min_mcap>0 + shares 있으면 *점별*(close[j]×shares) 시총 사용
    (look-ahead 제거). 없으면 정적 marcap 폴백."""
    if j < 253 or c[j] <= 0 or c[j - 252] <= 0:
        return False, None
    if min_mcap > 0:
        if shares and code in shares:
            pit = c[j] * shares[code] / 1e8       # 억 (점별 시총)
            if pit < min_mcap:
                return False, None
        elif (marcap or {}).get(code, 0) < min_mcap:
            return False, None                   # 폴백: 정적 marcap
    if not AE.confirmed_p(c, P, j):
        return False, None
    m50 = AE.smap(P, j, 50)
    if not m50 or abs(c[j] / m50 - 1) > 0.10:
        return False, None
    hi52 = max(c[max(0, j - 251):j + 1])
    if not hi52 or c[j] > 0.88 * hi52:                    # 추격 아님
        return False, None
    if len(set(c[max(0, j - 60):j + 1])) < 10:            # 거래정지
        return False, None
    lo = max(61, j - 15)                                  # 추세확인 신선
    if not any(AE.confirmed_p(c, P, x) and not AE.confirmed_p(c, P, x - 1)
               for x in range(j, lo - 1, -1)):
        return False, None
    if cape_freefall(c, j):                               # ★가드: 케이프
        return False, None
    if not quiet_ok(volmap, code, t):                     # ★가드: 거래량조용
        return False, None
    gi = bisect.bisect_right(grid, t) - 1
    rp = AD.rs_pct(ref.get(grid[gi]) if gi >= 0 else None,
                   c[j] / c[j - 252] - 1)
    if rp is None or rp < 80:                              # L
        return False, None
    pu = AD.prior_up_at(c, j)                              # 선행상승(최후)
    if pu is None or pu < 0.50:
        return False, None
    if use_i and flowmap is not None:                      # ★I가드(수급)
        ok, _applied = i_ok(flowmap, code, t)
        if not ok:
            return False, None
    return True, rp


def screen_rt_lead(code, d, c, P, j, t, grid, ref, volmap,
                   flowmap=None, use_i=False, marcap=None, min_mcap=0,
                   shares=None):
    """대형주용 *주도주 모멘텀* 진입(눌림목과 정반대 철학).
    추세스택(50>200·상승) + 신고가 근접(≥90%) + 다타임프레임
    상승(21d/63d/252d 모두 +) + RS≥80 + I + 체급(점별)."""
    if j < 253 or c[j] <= 0 or c[j - 252] <= 0:
        return False, None
    if min_mcap > 0:
        if shares and code in shares:
            if c[j] * shares[code] / 1e8 < min_mcap:
                return False, None
        elif (marcap or {}).get(code, 0) < min_mcap:
            return False, None
    if len(set(c[max(0, j - 60):j + 1])) < 10:
        return False, None
    if j < 64 or c[j - 21] <= 0 or c[j - 63] <= 0:
        return False, None
    if c[j] <= c[j - 21] or c[j] <= c[j - 63]:        # 다타임프레임 상승
        return False, None
    m50 = AE.smap(P, j, 50)
    m200 = AE.smap(P, j, 200)
    if not m50 or not m200:
        return False, None
    if not (c[j] > m50 > m200 and c[j] > c[j - 20]):  # 정통 추세스택
        return False, None
    hi52 = max(c[max(0, j - 251):j + 1])
    if not hi52 or c[j] < 0.90 * hi52:                # 신고가 근접(주도주)
        return False, None
    gi = bisect.bisect_right(grid, t) - 1
    rp = AD.rs_pct(ref.get(grid[gi]) if gi >= 0 else None,
                   c[j] / c[j - 252] - 1)
    if rp is None or rp < 80:
        return False, None
    if use_i and flowmap is not None:
        ok, _ = i_ok(flowmap, code, t)
        if not ok:
            return False, None
    return True, rp


def simulate_rt(codes_d, grid, ref, kd, kc, volmap, sector,
                start, end, slots, use_switch, cost,
                flowmap=None, use_i=False,
                sizing="equal", maxw=0.30,
                ride_gain=None, ride_trail=0.65,
                marcap=None, min_mcap=0, shares=None,
                screen_fn=None):
    """sizing='equal'|'rs'(확신도=RS−79 가중, 종목당 maxw 상한).
    ride_gain: 이익 +ride_gain↑ 도달분은 트레일을 ride_trail(넓게)로
    완화 → 큰 위너 더 오래 보유(진단의 '이긴 걸 크게 못 먹음' 대응)."""
    axis = sorted({x for v in codes_d.values() for x in v[0]
                   if start <= x <= end})
    pos, cash, eq_d, eq = {}, 1.0, [], []
    trades = []
    for ti, t in enumerate(axis):
        on = True if not use_switch else (not AE.kbear_at(kd, kc, t))
        for code in list(pos):
            d, c, _ = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i < 0:
                continue
            px = c[i]
            p = pos[code]
            p["peak"] = max(p["peak"], px)
            gp = p["peak"] / p["entry"] - 1
            tw = (ride_trail if (ride_gain is not None and gp >= ride_gain)
                  else 0.80)                       # 큰 위너=넓은 트레일
            if (px <= p["entry"] * 0.85 or px <= p["peak"] * tw
                    or (use_switch and not on)):
                cash += p["inv"] * (px / p["entry"]) * (1 - cost)
                trades.append(px / p["entry"] - 1)
                del pos[code]
        if on and len(pos) < slots and ti % 5 == 0:
            cand = []
            for code, (d, c, P) in codes_d.items():
                if code in pos:
                    continue
                j = bisect.bisect_right(d, t) - 1
                fn = screen_fn or screen_rt
                ok, rp = fn(code, d, c, P, j, t, grid, ref, volmap,
                            flowmap, use_i, marcap, min_mcap, shares)
                if ok:
                    cand.append((sector.get(code), rp, code, c[j]))
            from collections import Counter
            sc = Counter(s for s, _, _, _ in cand if s)
            cand.sort(key=lambda x: (not (x[0] and sc.get(x[0], 0) >= 2),
                                     -x[1]))
            picks = cand[:slots - len(pos)]
            cash0 = cash                            # 이벤트 시작 현금 스냅샷
            if sizing == "rs" and picks:
                wsum = sum(max(1.0, rp - 79) for _, rp, _, _ in picks)
                for _, rp, code, px in picks:
                    if cash <= 1e-9:
                        break
                    frac = min(maxw, max(1.0, rp - 79) / wsum)
                    buy = min(cash, cash0 * frac)   # 확신도 비중·종목상한
                    cash -= buy
                    pos[code] = {"inv": buy * (1 - cost),
                                 "entry": px, "peak": px}
            else:
                for _, rp, code, px in picks:
                    if cash <= 1e-9:
                        break
                    buy = min(cash, cash / (slots - len(pos)))
                    cash -= buy
                    pos[code] = {"inv": buy * (1 - cost),
                                 "entry": px, "peak": px}
        mv = cash
        for code, p in pos.items():
            d, c, _ = codes_d[code]
            i = bisect.bisect_right(d, t) - 1
            if i >= 0:
                mv += p["inv"] * (c[i] / p["entry"])
        eq_d.append(t)
        eq.append(mv)
    return eq_d, eq, trades


def dump_candidates(src):
    """백테스트 전 구간에서 (I 제외) 가드스크린을 *한 번이라도* 통과한
    종목 = I가드 검증이 필요한 후보집합. 수급 수집 범위를 이걸로
    한정(전 유니버스 불필요 → 샤드 대폭 감소)."""
    U = AD.pick_universe_file(src)
    codes_d = {k: (s["d"], s["c"], AE.prefix(s["c"]))
               for k, s in U.items() if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _, _ in codes_d.values() for x in d})
    start, end = al[0], al[-1]
    run_start = al[min(len(al) - 1, 260)]
    grid, ref = AD.build_rs_grid(U, start, end)
    vm = load_vol(src)
    axis = [x for x in sorted({z for v in codes_d.values() for z in v[0]})
            if run_start <= x <= end]
    seen = set()
    for ti, t in enumerate(axis):
        if ti % 5 != 0:
            continue
        for code, (d, c, P) in codes_d.items():
            if code in seen:
                continue
            j = bisect.bisect_right(d, t) - 1
            ok, _ = screen_rt(code, d, c, P, j, t, grid, ref, vm)
            if ok:
                seen.add(code)
    outp = OUT / f"_flow_candidates_{src}.txt"
    outp.write_text("\n".join(sorted(seen)), encoding="utf-8")
    print(f"[dump {src}] 매수후보(I검증필요) {len(seen)}종 / "
          f"유니버스 {len(codes_d)} → {outp.name}", file=sys.stderr)


def selftest(src):
    """위너 model_book pivot일에 screen_rt 적용 → 통과율 방향 점검."""
    W = AD.rows(src)
    U = AD.pick_universe_file(src)
    codes_d = {k: (s["d"], s["c"], AE.prefix(s["c"]))
               for k, s in U.items() if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _, _ in codes_d.values() for x in d})
    grid, ref = AD.build_rs_grid(U, al[0], al[-1])
    vm = load_vol(src)
    npass = n = 0
    for r in W:
        cd, pdt = r["code"], r.get("pivot_date")
        if cd not in codes_d or not pdt:
            continue
        d, c, P = codes_d[cd]
        j = bisect.bisect_right(d, pdt) - 1
        if j < 0:
            continue
        n += 1
        ok, _ = screen_rt(cd, d, c, P, j, pdt, grid, ref, vm)
        npass += int(ok)
    print(f"[selftest {src}] 위너 {n}종 pivot일 가드스크린 통과 "
          f"{npass} ({100*npass//max(1,n)}%) — 0 아니면 방향 정상"
          f"(실시간·가드추가로 필드스크린보다 낮은 게 정상)",
          file=sys.stderr)


def bull_on(kd, kc, ds):
    """★ON(강세) = 코스피 종가>200일선 & 200일선 상승. look-ahead 없음."""
    j = bisect.bisect_right(kd, ds) - 1
    if j < 220:
        return False
    m, mp = AE.sma(kc, j, 200), AE.sma(kc, j - 20, 200)
    return bool(m and mp and kc[j] > m and m > mp)


def bull_only(src, slots, cost):
    """강세장(★ON) 구간만 떼어 시스템 vs *같은 구간* KOSPI 비교.
    시스템은 설계상 강세 전용(약세=현금) — 공정 평가는 강세 한정."""
    U = AD.pick_universe_file(src)
    codes_d = {k: (s["d"], s["c"], AE.prefix(s["c"]))
               for k, s in U.items() if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _, _ in codes_d.values() for x in d})
    start, end = al[0], al[-1]
    run_start = al[min(len(al) - 1, 260)]
    grid, ref = AD.build_rs_grid(U, start, end)
    kd, kc = AE.kospi_series()
    vm, sec, fm = load_vol(src), load_sector(), load_flow(src)
    ed, eq, tr = simulate_rt(codes_d, grid, ref, kd, kc, vm, sec,
                             run_start, end, slots, True, cost, fm, True)
    # 축에 KOSPI 정렬
    ks = [kc[max(0, bisect.bisect_right(kd, t) - 1)] for t in ed]
    bull = [bull_on(kd, kc, t) for t in ed]

    def chain(series, mask):
        v = 1.0
        for i in range(1, len(series)):
            if mask[i] and series[i - 1] > 0:
                v *= series[i] / series[i - 1]
        return v
    s_all, k_all = chain(eq, [True] * len(eq)), chain(ks, [True] * len(ks))
    s_b, k_b = chain(eq, bull), chain(ks, bull)
    bd = sum(1 for i in range(1, len(bull)) if bull[i])
    by = bd / 252

    def cagr(x):
        return (x ** (1 / by) - 1) if by > 0 and x > 0 else None
    # 강세 연속구간별 승부
    seg = []
    i = 1
    while i < len(bull):
        if bull[i]:
            a = i
            while i < len(bull) and bull[i]:
                i += 1
            sret = chain(eq[a - 1:i], [True] * (i - a + 1)) - 1
            kret = chain(ks[a - 1:i], [True] * (i - a + 1)) - 1
            if i - a >= 10:                       # 의미있는 길이만
                seg.append((ed[a], ed[i - 1], sret, kret))
        else:
            i += 1
    wins = sum(1 for *_, s, k in seg if s > k)
    L = [f"[강세장 한정 검증] [{src}] — 시스템은 강세 전용(약세=현금)."
         " 공정 비교 = ★ON 구간만",
         f"전체창 {run_start}~{end} 중 강세(★ON) 거래일 {bd} "
         f"(≈{by:.1f}년) / 약세·중립 제외",
         f"가드: 거래량+케이프+섹터+I(수급, {src} 데이터 한정)",
         "*★ON=코스피>200일선&200일선상승. look-ahead 없음. 사후·"
         "종가·일별·생존자잔존·세금0.66%.*",
         "=" * 66,
         f"■ 강세장 한정 누적수익  시스템 ×{s_b:.2f} "
         f"(CAGR {(cagr(s_b) or 0)*100:+.0f}%) · "
         f"KOSPI ×{k_b:.2f} (CAGR {(cagr(k_b) or 0)*100:+.0f}%)",
         f"■ (참고) 전구간 누적     시스템 ×{s_all:.2f} · "
         f"KOSPI ×{k_all:.2f}",
         "-" * 66,
         f"■ 강세 연속구간 {len(seg)}개 중 시스템이 KOSPI 이긴 횟수 "
         f"{wins}/{len(seg)}"]
    for a, b, s, k in seg:
        L.append(f"  {a}~{b}: 시스템 {s*100:+.0f}% vs KOSPI {k*100:+.0f}%"
                 f"  → {'승' if s > k else '패'}")
    verdict = ("강세장 한정 시 시스템 > KOSPI = 강세 전용 운용은 유의미"
               if s_b > k_b else
               "강세장만 떼도 KOSPI 미달 = 강세 전용이어도 알파 미입증")
    L += ["-" * 66, f"■ 판정: {verdict}",
          "=" * 66,
          "해석: 시스템을 *강세장에만* 쓰고 약세장은 다른 전략(범위밖)"
          "이라 가정한 공정 검증. 강세 한정 시스템>KOSPI 면 '약세에",
          "약했을 뿐 강세 스킬은 실재'. 강세만 떼도 미달이면 강세",
          "에서조차 알파 없음(사후착시가 본질) — 더 무거운 결론.",
          "한계: 강세 판정도 200일선(지각 ~−10%·87일)·전환 휩쏘",
          "구간 귀속 모호·수급 데이터 기간 한정·n=2·종가·생존자."]
    txt = "\n".join(L)
    tag = "" if src == "c2024-12" else "_c2020"
    (OUT / f"_equity_bull_only{tag}.txt").write_text(txt, encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 강세장 한정 검증 [{src}]\n\n```\n{txt}\n```\n")
    print(txt)


def conviction(src, cost):
    """확신도 가중 집중투자 실험: 등가중8 vs RS가중·소수칸·위너라이드.
    공정 평가 = 강세장(★ON) 한정 시스템 vs 같은구간 KOSPI."""
    U = AD.pick_universe_file(src)
    codes_d = {k: (s["d"], s["c"], AE.prefix(s["c"]))
               for k, s in U.items() if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _, _ in codes_d.values() for x in d})
    start, end = al[0], al[-1]
    rs0 = al[min(len(al) - 1, 260)]
    grid, ref = AD.build_rs_grid(U, start, end)
    kd, kc = AE.kospi_series()
    vm, sec, fm = load_vol(src), load_sector(), load_flow(src)

    CFG = [
        ("C0 등가중8(현행D3)", dict(slots=8, sizing="equal")),
        ("C1 RS가중·5칸", dict(slots=5, sizing="rs", maxw=0.30)),
        ("C2 RS가중·4칸+라이드", dict(slots=4, sizing="rs", maxw=0.35,
                                  ride_gain=0.50)),
        ("C3 RS가중·3칸+라이드", dict(slots=3, sizing="rs", maxw=0.45,
                                  ride_gain=0.50)),
    ]
    L = [f"[확신도 가중 집중투자 실험] [{src}] {rs0}~{end} "
         f"슬롯·비중·라이드 변형 (가드+I·★스위치·비용0.66%)",
         "공정 비교 = 강세장(★ON) 한정 시스템 vs 같은구간 KOSPI.",
         "*진단: '+410%를 1/8·중간잘림'→확신도비중·집중·위너라이드로 대응*",
         "=" * 70,
         f"  {'구성':<22}| 전구간 ×배 CAGR | 강세장만 시스템 vs KOSPI | 판정"]

    def bull_chain(ed, eq):
        ks = [kc[max(0, bisect.bisect_right(kd, x) - 1)] for x in ed]
        bl = [bull_on(kd, kc, x) for x in ed]

        def ch(s):
            v = 1.0
            for i in range(1, len(s)):
                if bl[i] and s[i - 1] > 0:
                    v *= s[i] / s[i - 1]
            return v
        bd = sum(1 for i in range(1, len(bl)) if bl[i])
        yb = bd / 252

        def cg(x):
            return (x ** (1 / yb) - 1) * 100 if yb > 0 and x > 0 else 0
        return ch(eq), ch(ks), cg(ch(eq)), cg(ch(ks))

    best = None
    for nm, kw in CFG:
        ed, eq, tr = simulate_rt(codes_d, grid, ref, kd, kc, vm, sec,
                                 rs0, end, kw.get("slots", 8), True, cost,
                                 fm, True, **{k: v for k, v in kw.items()
                                              if k != "slots"})
        m = AE.metrics(ed, eq)
        sB, kB, sCg, kCg = bull_chain(ed, eq)
        win = "승" if sB > kB else "패"
        if best is None or sCg > best[1]:
            best = (nm, sCg, kCg, win)
        L.append(f"  {nm:<22}| ×{m['final']:.2f} "
                 f"{(m['cagr'] or 0)*100:+.0f}% | "
                 f"시스템 {sCg:+.0f}% vs KOSPI {kCg:+.0f}% | {win}")
    L += ["-" * 70,
          f"■ 최고 구성: {best[0]} — 강세장 시스템 {best[1]:+.0f}% vs "
          f"KOSPI {best[2]:+.0f}% → {'KOSPI 상회!' if best[1] > best[2] else 'KOSPI 미달'}",
          "해석: 확신도 가중·집중·위너라이드가 등가중8 대비 강세장",
          "수익을 끌어올려 KOSPI 근접/상회면 = '큰 걸 크게 못 먹던",
          "구조'가 원인이었다는 증거(구조변경 유효). 그래도 미달이면",
          "선별 자체 한계 — 폐기/완전재설계가 정직.",
          "한계: 사후·종가·일별·생존자잔존·수급기간한정·n=2·"
          "RS가중도 사후RS근사·집중=단일종목 리스크↑(분산 희생)."]
    txt = "\n".join(L)
    tag = "" if src == "c2024-12" else "_c2020"
    (OUT / f"_conviction{tag}.txt").write_text(txt, encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 확신도 가중 집중 실험 [{src}]\n\n```\n{txt}\n```\n")
    print(txt)


def load_shares():
    p = OUT / "_universe_shares.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def size_test(src, cost):
    """체급 필터 실험: 정적(현재시총·look-ahead 有) vs 점별
    (close[t]×주식수·look-ahead 제거) 두 방식 *나란히* 비교."""
    U = AD.pick_universe_file(src)
    codes_d = {k: (s["d"], s["c"], AE.prefix(s["c"]))
               for k, s in U.items() if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _, _ in codes_d.values() for x in d})
    start, end = al[0], al[-1]
    rs0 = al[min(len(al) - 1, 260)]
    grid, ref = AD.build_rs_grid(U, start, end)
    kd, kc = AE.kospi_series()
    vm, sec, fm = load_vol(src), load_sector(), load_flow(src)
    mc = load_marcap()
    sh = load_shares()

    def bull_chain(ed, eq):
        ks = [kc[max(0, bisect.bisect_right(kd, x) - 1)] for x in ed]
        bl = [bull_on(kd, kc, x) for x in ed]

        def ch(s):
            v = 1.0
            for i in range(1, len(s)):
                if bl[i] and s[i - 1] > 0:
                    v *= s[i] / s[i - 1]
            return v
        bd = sum(1 for i in range(1, len(bl)) if bl[i])
        yb = bd / 252

        def cg(x):
            return (x ** (1 / yb) - 1) * 100 if yb > 0 and x > 0 else 0
        return cg(ch(eq)), cg(ch(ks))

    TH = [0, 5000, 10000, 30000]
    NM = ["전체", "≥5천억", "≥1조", "≥3조"]
    L = [f"[체급 필터 클린 테스트·점별 시총] [{src}] {rs0}~{end}",
         "정적(현재시총·look-ahead 有) vs 점별(close[t]×주식수·"
         "look-ahead 제거) **나란히 비교**. 가드+I·등가중8·★·강세장",
         "한정 vs KOSPI. *주식수=현재 추정(분할/증자 미반영=소오차)*.",
         "=" * 70,
         f"  {'체급':<10}| {'정적(LA有) 시스템/KOSPI':<24}| "
         f"{'점별(클린) 시스템/KOSPI':<24}| 점별판정"]
    rj = {}
    for th, nm in zip(TH, NM):
        # A: 정적(예전 결과 재현)
        edA, eqA, _ = simulate_rt(codes_d, grid, ref, kd, kc, vm, sec,
                                  rs0, end, 8, True, cost, fm, True,
                                  marcap=mc, min_mcap=th)
        sA, kA = bull_chain(edA, eqA)
        # B: 점별(클린)
        edB, eqB, trB = simulate_rt(codes_d, grid, ref, kd, kc, vm, sec,
                                    rs0, end, 8, True, cost, fm, True,
                                    shares=sh, min_mcap=th)
        mB = AE.metrics(edB, eqB)
        sB, kB = bull_chain(edB, eqB)
        rj[nm] = {"static_sys_bull": sA, "static_kospi_bull": kA,
                  "pit_sys_bull": sB, "pit_kospi_bull": kB,
                  "pit_final": mB["final"], "pit_trades": len(trB)}
        L.append(f"  {nm:<10}| 시{sA:+5.0f}% vs K{kA:+5.0f}% "
                 f"({'승' if sA>kA else '패'})        | "
                 f"시{sB:+5.0f}% vs K{kB:+5.0f}% "
                 f"({'승' if sB>kB else '패'}, ×{mB['final']:.2f}, "
                 f"{len(trB)}거래) | {'승' if sB>kB else '패'}")
    L += ["-" * 70,
          "해석: '점별(클린)' 컬럼이 정직한 결과. 정적→점별 격차가",
          "  크게 줄면 이전 ≥1조 +104% 같은 *낙관*은 look-ahead 거품",
          "  이었음 확정. 점별에서도 ≥1조 KOSPI 상회 = '대형주 전환은",
          "  진짜다'(2단계 진입재설계 진행 가치 큼). 점별도 패 = 체급",
          "  문제 아님(선별 본질). 메가캡 ≥3조는 종목수 적어 노이즈.",
          "한계: 주식수=현재 단일값(분할·증자 시점 미반영=소오차).",
          "  사후·종가·일별·n=2·수급기간한정·진입은 여전히 소형용 눌림목."]
    txt = "\n".join(L)
    tag = "" if src == "c2024-12" else "_c2020"
    (OUT / f"_size_test{tag}.txt").write_text(txt, encoding="utf-8")
    (CY / src / "size_test_rows.json").write_text(
        json.dumps(rj, ensure_ascii=False, indent=1), encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 체급 필터 실험 [{src}]\n\n```\n{txt}\n```\n")
    print(txt)


def lead_test(src, cost):
    """대형주용 *주도주 모멘텀* 진입 vs 기존 *눌림목* 진입 — 점별
    체급 필터(클린)와 결합. 클린 ≥5천억 +44% vs KOSPI +57%(c2024)
    의 13%p 격차를 모멘텀 재설계가 메우는가?"""
    U = AD.pick_universe_file(src)
    codes_d = {k: (s["d"], s["c"], AE.prefix(s["c"]))
               for k, s in U.items() if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _, _ in codes_d.values() for x in d})
    rs0 = al[min(len(al) - 1, 260)]
    grid, ref = AD.build_rs_grid(U, al[0], al[-1])
    kd, kc = AE.kospi_series()
    vm, sec, fm = load_vol(src), load_sector(), load_flow(src)
    sh = load_shares()

    def bull_chain(ed, eq):
        ks = [kc[max(0, bisect.bisect_right(kd, x) - 1)] for x in ed]
        bl = [bull_on(kd, kc, x) for x in ed]

        def ch(s):
            v = 1.0
            for i in range(1, len(s)):
                if bl[i] and s[i - 1] > 0:
                    v *= s[i] / s[i - 1]
            return v
        bd = sum(1 for i in range(1, len(bl)) if bl[i])
        yb = bd / 252

        def cg(x):
            return (x ** (1 / yb) - 1) * 100 if yb > 0 and x > 0 else 0
        return cg(ch(eq)), cg(ch(ks))

    CFG = [("눌림목·≥5천억(클린)", screen_rt, 5000),
           ("눌림목·≥1조(클린)", screen_rt, 10000),
           ("★주도주모멘텀·≥5천억", screen_rt_lead, 5000),
           ("★주도주모멘텀·≥1조", screen_rt_lead, 10000),
           ("★주도주모멘텀·≥3조", screen_rt_lead, 30000)]
    L = [f"[주도주 모멘텀 재설계 · 점별 체급 클린 테스트] [{src}]",
         "눌림목(소형용)을 대형주용 *주도주 모멘텀*(추세스택+신고가",
         "근접+다타임프레임 상승+RS≥80)으로 교체. 가드+I·등가중8·★.",
         f"대조: 강세장 한정 vs KOSPI. *클린 체급=close[t]×주식수.*",
         "=" * 70,
         f"  {'구성':<24}| 전 ×배 | 강세장 시스템 vs KOSPI | 거래 | 판정"]
    rj = {}
    for nm, fn, th in CFG:
        ed, eq, tr = simulate_rt(codes_d, grid, ref, kd, kc, vm, sec,
                                 rs0, al[-1], 8, True, cost, fm, True,
                                 shares=sh, min_mcap=th, screen_fn=fn)
        m = AE.metrics(ed, eq)
        sCg, kCg = bull_chain(ed, eq)
        rj[nm] = {"final": m["final"], "bull_sys": sCg,
                  "bull_kospi": kCg, "trades": len(tr)}
        L.append(f"  {nm:<24}| ×{m['final']:.2f} | "
                 f"시{sCg:+5.0f}% vs K{kCg:+5.0f}% | {len(tr):3d} | "
                 f"{'승' if sCg > kCg else '패'}")
    L += ["-" * 70,
          "해석: 주도주모멘텀이 같은 체급의 눌림목을 *뚜렷히 상회*하면",
          "  대형주는 모멘텀이 맞는 진입(가설 적중). KOSPI까지 넘으면",
          "  '대형주+모멘텀'이 라이브 후보. 모멘텀이 눌림목과 비슷/",
          "  미달이면 = 진입로직 바꿔도 KOSPI 못 이김(롱온리 종목선별",
          "  최종 한계). 체급↑일수록 종목수↓·집중 리스크 동반.",
          "한계: 주식수=현재 단일값(분할·증자 소오차)·사후·종가·",
          "  일별·n=2·수급 기간한정·메가캡(≥3조)은 표본 적음."]
    txt = "\n".join(L)
    tag = "" if src == "c2024-12" else "_c2020"
    (OUT / f"_lead_test{tag}.txt").write_text(txt, encoding="utf-8")
    (CY / src / "lead_test_rows.json").write_text(
        json.dumps(rj, ensure_ascii=False, indent=1), encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 주도주 모멘텀 재설계 [{src}]\n\n```\n{txt}\n```\n")
    print(txt)


def run(src, slots, cost):
    U = AD.pick_universe_file(src)
    codes_d = {k: (s["d"], s["c"], AE.prefix(s["c"]))
               for k, s in U.items() if s.get("d") and len(s.get("c", [])) > 260}
    al = sorted({x for d, _, _ in codes_d.values() for x in d})
    start, end = al[0], al[-1]
    run_start = al[min(len(al) - 1, 260)]
    grid, ref = AD.build_rs_grid(U, start, end)
    kd, kc = AE.kospi_series()
    vm, sec, fm = load_vol(src), load_sector(), load_flow(src)
    vcov = sum(1 for k in codes_d if k in vm)
    # 수급 데이터 시간 커버(네이버 ~2023-11+ 한계 — 그 전·c2020 결손)
    fdates = [x for s in fm.values() for x in (s[0][:1] + s[0][-1:])]
    fmin = min(fdates) if fdates else None
    in_win = bool(fmin and fmin <= end and fmin <= run_start) or \
        bool(fmin and fmin < end)
    flow_note = (f"수급 {len(fm)}종, 데이터 {fmin or '없음'}~ "
                 f"→ {'적용가능 구간 있음' if (fmin and fmin < end) else '전구간 결손'}")

    bh = AE.kospi_bh(kd, kc, run_start, end)
    bm = AE.metrics(bh[0], bh[1]) if bh else None
    yrs = (datetime.strptime(end, "%Y-%m-%d")
           - datetime.strptime(run_start, "%Y-%m-%d")).days / 365.25

    # I 제외(=종전 D2) vs I 포함(D3) — 둘 다 ★스위치 ON
    r_noI = simulate_rt(codes_d, grid, ref, kd, kc, vm, sec, run_start,
                        end, slots, True, cost, fm, False)
    r_I = simulate_rt(codes_d, grid, ref, kd, kc, vm, sec, run_start,
                      end, slots, True, cost, fm, True)
    m0, m1 = AE.metrics(r_noI[0], r_noI[1]), AE.metrics(r_I[0], r_I[1])
    tr = r_I[2]
    w = [x for x in tr if x > 0]
    L = [f"[가드+I 실시간 자본곡선·D3] [{src}] {run_start}~{end} "
         f"(≈{yrs:.1f}년) 슬롯{slots}·비용0.66%",
         f"가드: 거래량-조용+케이프+섹터무리+**I(수급)** / {flow_note} / "
         f"거래량커버 {vcov}/{len(codes_d)}",
         "*비교: 가격만 −17%(c2024)/−15%(c2020) · KOSPI +19%/+18%*",
         "=" * 66,
         f"■ 가드(I제외·종전)   {AE.fmtm(m0)}",
         f"■ 가드+I(D3)        {AE.fmtm(m1)}",
         f"■ KOSPI 매수보유     {AE.fmtm(bm) if bm else '결손'}"]
    if tr:
        s = sorted(tr)
        L += ["-" * 66,
              f"■ 체결(I포함) {len(tr)}건 (연 {len(tr)/max(.1,yrs):.0f}) · "
              f"승률 {100*len(w)/len(tr):.0f}% · 평균 {100*st.mean(tr):+.1f}% "
              f"· 중앙 {100*s[len(s)//2]:+.1f}% · 최악 {100*min(tr):+.0f}%"]
    d_cagr = ((m1["cagr"] or 0) - (m0["cagr"] or 0)) * 100 \
        if (m0 and m1) else 0
    L += ["-" * 66,
          f"■ I가드 기여: CAGR {(m0['cagr'] or 0)*100:+.0f}% → "
          f"{(m1['cagr'] or 0)*100:+.0f}% (Δ {d_cagr:+.1f}%p) · "
          f"vs KOSPI {(bm['cagr'] or 0)*100 if bm else 0:+.0f}%",
          f"■ 판정: " + (
              "I가드가 유의미 개선·KOSPI 근접/상회 → edge 보강 신호"
              if (m1 and m1["cagr"] and m1["cagr"] > 0
                  and abs(d_cagr) > 2) else
              "I가드 추가해도 KOSPI 대패/미미 → 사후 pivot 착시가 본질"),
          "=" * 66,
          "해석: I가드는 *수급데이터 있는 구간에서만* 작동. c2020-03 은",
          "네이버 수급 ~2023-11+ 라 전구간 결손→판정보류(=I제외와 동일,",
          "참고불가). c2024-12 도 2023-11 이전 진입은 판정보류. 즉 D3",
          "는 사실상 *c2024 후반 한정* I효과. Δ가 작거나 여전히 KOSPI",
          "대패면 '가드 다 넣어도 사후착시가 본질' 결론 확정.",
          "한계: 수급 네이버 ~2023-11+ 한정(2020·초기 결손=판정보류,",
          "추정없음)·종가·일별·생존자잔존·세금0.18%·이자0·단일연속창."]
    txt = "\n".join(L)
    tag = "" if src == "c2024-12" else "_c2020"
    (OUT / f"_equity_curve_rt{tag}.txt").write_text(txt, encoding="utf-8")
    (CY / src / "equity_curve_rt_rows.json").write_text(json.dumps(
        {"src": src, "guard_noI": m0, "guard_I": m1, "kospi": bm,
         "flow_codes": len(fm), "flow_from": fmin,
         "delta_cagr_pp": d_cagr, "trades": len(tr),
         "winrate": (len(w) / len(tr) if tr else None)},
        ensure_ascii=False, indent=1), encoding="utf-8")
    with (OUT / "analysis_history.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n## 가드포함 실시간 자본곡선 [{src}]\n\n```\n{txt}\n```\n")
    print(txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="c2024-12",
                    choices=["c2024-12", "c2020-03"])
    ap.add_argument("--slots", type=int, default=8)
    ap.add_argument("--cost", type=float, default=0.0066)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dump-candidates", action="store_true")
    ap.add_argument("--bull-only", action="store_true")
    ap.add_argument("--conviction", action="store_true")
    ap.add_argument("--size-test", action="store_true")
    ap.add_argument("--lead-test", action="store_true")
    a = ap.parse_args()
    if a.dump_candidates:
        dump_candidates(a.src)
        return
    if a.bull_only:
        bull_only(a.src, a.slots, a.cost)
        return
    if a.conviction:
        conviction(a.src, a.cost)
        return
    if a.size_test:
        size_test(a.src, a.cost)
        return
    if a.lead_test:
        lead_test(a.src, a.cost)
        return
    if a.selftest:
        selftest(a.src)
        return
    run(a.src, a.slots, a.cost)


if __name__ == "__main__":
    main()

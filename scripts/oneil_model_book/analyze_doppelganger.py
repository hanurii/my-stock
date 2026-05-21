"""[생존자편향] 도플갱어 부검 — 스크린을 통과했는데 죽은 종목의 실현 P&L.

문제: 모델북의 모든 결론(L+선행상승≥50% 정밀도 90%·lift 23.6x 등)은
*살아남아 폭발한 위너* 표본 위에 서 있고, 문서는 "생존자 편향(상폐 제외
→ 손실 과소)"을 한계로 고백만 했다. 이 스크립트는 그 고백을 숫자로 만든다.

도플갱어 = 안오름500(대조군) 중 pivot 시점에 선별 스크린을 *위너처럼*
통과했는데 폭발하지 못한 종목. 이들을 실제 시스템 출구 규칙으로 굴려
실현 손익을 측정하면, 이진(binary) 정밀도가 *돈*으로 환산된다
("부검 → 전략 기대값" 다리).

재사용:
  · analyze_trap_filter.py 의 base_L/F1/F3/F4/num·evaluate 정의 그대로
    (→ 문서 23.6x/90% 와 동일 정의·내부 정합성 게이트)
  · apply_system_exit.py 의 SYSTEM 출구 수식(③−15%재해·④−35%트레일·
    ★약세스위치 kbear) 인라인 복제(레포 인라인 관례·출처 주석)
  · analyze_loser_traps.py 의 분포대조 패턴(스크린통과 사망 vs 위너)

정직: 진짜 상장폐지 종목 명단은 프로젝트에 0개(외부수집 별건) →
*"생존했으나 −80% 미회복" 프록시*만 측정 = 모든 보정치는 생존자
편향의 **하한**(진짜 상폐 포함 시 정밀도는 더 낮음). 사후·종가·
2사이클·거래비용 무관·일별가드(거래량/케이프) 미적용.

사용: python scripts/oneil_model_book/analyze_doppelganger.py
      [--win c2024-12] [--ctl c2024-12-ctrl500] [--tag ""] [--limit N]
"""
import argparse
import bisect
import json
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CY = ROOT / "research" / "oneil-model-book" / "cycles"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
# 문서 23.6x/90% 와 *동일한* 스크린·정밀도 정의를 그대로 재사용
from analyze_trap_filter import base_L, F1, F3, F4, num  # noqa: E402
from canslim_lib.fetch import fetch_yahoo_chart  # noqa: E402


def F_I(r):
    """I (외인 OR 기관 매집) — korea_canslim 의 I 정의(F4 는 외인만)."""
    f, o = num(r.get("fgn_net_60d")), num(r.get("inst_net_60d"))
    return (f is not None and f > 0) or (o is not None and o > 0)


# 스크린 변형: 핵심 = 문서 권장 스위트스폿 L+선행상승≥50
SCREENS = [
    ("L만", [base_L]),
    ("L+선행상승>=50", [base_L, F1]),               # ★ 문서 23.6x/90%
    ("L+선행상승>=50+I", [base_L, F1, F_I]),
]
DOC = {"L만": "문서 lift7.8x·정밀도76%",
       "L+선행상승>=50": "문서 lift23.6x·정밀도90%(스위트스폿)",
       "L+선행상승>=50+I": "문서 참고(L+외인 12.0x·83%)"}


def passes(r, fs):
    return all(f(r) for f in fs)


def _cycle_window(cid):
    ci = json.loads((CY / "cycles_index.json").read_text(encoding="utf-8"))
    lst = ci["cycles"] if isinstance(ci, dict) else ci
    for c in lst:
        if c["cycle_id"] == cid:
            return c["anchor"], c["cycle_end"]
    raise SystemExit(f"cycle {cid} not in cycles_index.json")


def rows(cyc):
    p = CY / cyc / "model_book.json"
    return [r for r in json.loads(p.read_text(encoding="utf-8"))["rows"]
            if not r.get("error")]


def load_prices(cyc):
    p = CY / cyc / "_universe_prices.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def sma(c, i, w):
    return sum(c[i - w + 1:i + 1]) / w if i >= w - 1 else None


def nidx(d, ds):
    """ISO 'YYYY-MM-DD' 정렬열에서 ds 이하 마지막 인덱스(사전식=시간순)."""
    i = bisect.bisect_right(d, ds) - 1
    return i if i >= 0 else None


def build_kbear():
    """apply_system_exit.py 와 *동일* KOSPI 소스·로직(시스템 일관성).
    실패 시 None → ★스위치 결손 선언."""
    try:
        ks = fetch_yahoo_chart("%5EKS11", period1=_ep("2018-01-01"),
                               period2=_ep("2027-01-01"), interval="1d")
        if not ks or not ks.get("closes"):
            return None
        kd = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
              for t in ks["timestamps"]]
        kc = ks["closes"]
    except Exception:
        return None

    def kbear(ds):                                   # apply_system_exit:58-63
        j = nidx(kd, ds)
        if j is None or j < 220:
            return False
        m, mp = sma(kc, j, 200), sma(kc, j - 20, 200)
        return bool(m and mp and kc[j] < m and m < mp)
    return kbear


def system_exit(code, pivot_date, pivot_close, pmap, kbear):
    """진입=pivot_close(스크린이 본 가격) 가정, SYSTEM 출구 첫 발동 청산.
    apply_system_exit.py:83-99 수식 그대로(③−15%재해·④−35%트레일·★).
    반환: (실현수익%, 사유, 청산일, 기간최대%) 또는 None(가격 결손)."""
    s = pmap.get(code)
    if not s or not s.get("d") or not s.get("c") or not pivot_date:
        return None
    d, c = s["d"], s["c"]
    ei = nidx(d, pivot_date)
    if ei is None or ei >= len(c) - 1:
        return None
    e = pivot_close if (pivot_close and pivot_close > 0) else c[ei]
    return _sys_core(d, c, ei, e, kbear)


def _sys_core(d, c, ei, e, kbear):
    """SYSTEM 출구 코어 — apply_system_exit.py:83-99 수식 그대로
    (③진입대비-15%재해·④고점대비-35%트레일·★약세스위치). 폐지종목은
    가격열이 폐지일에 끊김 → 미발동 시 마지막 체결가(=사실상 전손)."""
    peak = e
    ret, why, dt = None, "보유중(미발동/폐지)", d[-1]
    for k in range(ei + 1, len(c)):
        peak = max(peak, c[k])
        if c[k] <= e * 0.85:
            ret, why, dt = c[k] / e - 1, "③-15%재해", d[k]
            break
        if c[k] <= peak * 0.65:
            ret, why, dt = c[k] / e - 1, "④-35%트레일", d[k]
            break
        if kbear and kbear(d[k]):
            ret, why, dt = c[k] / e - 1, "★약세스위치", d[k]
            break
    if ret is None:
        ret = c[-1] / e - 1
    peakret = max(c[ei:]) / e - 1
    return ret * 100, why, dt, peakret * 100


def classify(code, pivot_date, pivot_close, pmap):
    """도플갱어 사후 결과: 사망 / 횡보사망 / 준위너 (가격경로 기반)."""
    s = pmap.get(code)
    if not s or not s.get("d") or not s.get("c") or not pivot_date:
        return "결손", None, None
    d, c = s["d"], s["c"]
    ei = nidx(d, pivot_date)
    if ei is None or ei >= len(c) - 1:
        return "결손", None, None
    e = pivot_close if (pivot_close and pivot_close > 0) else c[ei]
    seg = c[ei:]
    maxgain = max(seg) / e - 1
    mdd = min(seg) / e - 1
    last = c[-1] / e - 1
    if mdd <= -0.80 and last <= -0.60:
        cls = "사망(-80%미회복=상폐프록시)"
    elif maxgain < 0.20 and last < 0:
        cls = "횡보사망(+20%미달·종료음수)"
    else:
        cls = "준위너(상승했으나 위너미달)"
    return cls, round(maxgain * 100, 1), round(last * 100, 1)


# ── 실측 폐지 코호트(생존자 보정) ──────────────────────────────
def pick_universe_file(win):
    """RS 백분위 기준 유니버스 — 사이클 시작 252거래일 전까지 필요.
    c2024-12 는 _5y, c2020-03 은 기본(둘 다 앵커 −1~3년 커버 확인)."""
    for fn in ("_universe_prices_5y.json", "_universe_prices.json"):
        p = CY / win / fn
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


def build_rs_grid(univ, anchor, cend, step=5):
    """주기적(≈주1회) as-of 격자마다 전종목 252거래일 수익률 정렬배열.
    screen_v11.rs_full 과 동일 정의(252일 수익률 전종목 백분위)."""
    cal = sorted({d for s in univ.values() for d in s.get("d", [])
                  if anchor <= d <= cend})
    grid = cal[::step] or cal
    pre = {}
    for code, s in univ.items():
        d, c = s.get("d"), s.get("c")
        if d and c and len(d) == len(c):
            pre[code] = (d, c)
    ref = {}
    for g in grid:
        arr = []
        for d, c in pre.values():
            i = bisect.bisect_right(d, g) - 1
            if i >= 252 and c[i] > 0 and c[i - 252] > 0:
                arr.append(c[i] / c[i - 252] - 1)
        arr.sort()
        ref[g] = arr
    return grid, ref


def rs_pct(arr, ret):
    if not arr:
        return None
    return 100 * bisect.bisect_left(arr, ret) / max(1, len(arr) - 1)


def prior_up_at(c, j):
    """screen_v11.py:181-190 의 선행상승 수식 그대로(j=평가시점 인덱스)."""
    st0 = max(0, j - 500)
    if j - 60 <= st0:
        return None                                  # 이력 부족
    loseg = c[st0:j - 60]
    if not loseg:
        return None
    lo = min(loseg)
    lo_i = st0 + loseg.index(lo)
    hiseg = c[lo_i:j - 20] if (j - 20) > lo_i else c[lo_i:j]
    if not hiseg or lo <= 0:
        return None
    return max(hiseg) / lo - 1


def screen_first_qualify(d, c, anchor, cend, grid, ref, kbear):
    """가격기반 L+선행상승≥50 (문서 스위트스폿). 사이클 창 안에서
    *처음* 충족한 날 = '샀을 법한 날'. 폐지종목엔 수급(I) 비제공이라
    L·선행상승만(=검증된 23.6x/90% 정의의 가격버전·I 결손 명시).

    충실성 가드(screen_v11 거동 반영):
     · ★약세스위치 ON(코스피 약세)인 날은 매수 안 함 — screen_v11 의
       '코스피 비강세=시스템 OFF, 추천 안 함' 게이트. (없으면 계엄
       크래시 바닥에서 매수→즉시 ★청산되는 가짜 0% 발생)
     · 거래정지(가격 동결) 구간 제외 — 최근 60봉 고유종가 <10 이면
       사실상 정지(체결 불가) → 스크린 대상 아님(screen_v11 의
       거래량-조용/신선도 게이트의 가격버전 대용)."""
    stage = "창내거래일없음"
    for j in range(len(c)):
        dj = d[j]
        if dj < anchor:
            continue
        if dj > cend:
            break
        if j < 253 or c[j] <= 0 or c[j - 252] <= 0:
            stage = "이력<252일"
            continue
        if kbear and kbear(dj):                        # 시스템 OFF — 매수X
            stage = "★약세(시스템OFF·매수X)"
            continue
        if len(set(c[max(0, j - 60):j + 1])) < 10:     # 거래정지(동결) 제외
            stage = "거래정지(가격동결·체결불가)"
            continue
        pu = prior_up_at(c, j)
        if pu is None or pu < 0.50:                   # 선행상승<50 탈락
            stage = "선행상승<50"
            continue
        gi = bisect.bisect_right(grid, dj) - 1        # ≤dj 최근 격자
        if gi < 0:
            continue
        arr = ref.get(grid[gi])
        rp = rs_pct(arr, c[j] / c[j - 252] - 1)
        if rp is None or rp < 80:                     # L(RS≥80) 탈락
            stage = "RS<80"
            continue
        return j, dj, c[j], round(pu * 100, 1), round(rp, 1)
    return stage


def run_dead_cohort(win, anchor, cend, kbear):
    """폐지 코호트에 가격기반 스위트스폿 스크린→SYSTEM 출구.
    반환: (전체수, 가격기반평가가능수, 스크린통과수, 통과종목 실현수익%,
           통과 상세행). 통과=시스템이 '사라'고 했을 종목(전부 사망)."""
    dd = CY / f"{win}-delisted"
    pxp, mtp = dd / "_universe_prices.json", dd / "delisted_meta.json"
    if not pxp.exists():
        return None
    PX = json.loads(pxp.read_text(encoding="utf-8"))
    META = json.loads(mtp.read_text(encoding="utf-8"))
    univ = pick_universe_file(win)
    grid, ref = build_rs_grid(univ, _shift_iso(anchor, -2), cend)
    from collections import Counter
    n_all = len(META)
    evaluable, passed, reals, detail = 0, [], [], []
    rej = Counter()
    for code, m in META.items():
        if m.get("error"):
            rej["가격수집실패"] += 1
            continue
        s = PX.get(code)
        if not s or len(s.get("c", [])) < 254:
            rej["이력<252일"] += 1
            continue
        evaluable += 1
        q = screen_first_qualify(s["d"], s["c"], anchor, cend,
                                 grid, ref, kbear)
        if isinstance(q, str):
            rej[q] += 1
            continue
        j, bd, bpx, pu, rp = q
        se = _sys_core(s["d"], s["c"], j, bpx, kbear)
        if not se:
            continue
        passed.append(code)
        reals.append(se[0])
        detail.append({"code": code, "name": m.get("name"),
                       "delisting_date": m.get("delisting_date"),
                       "reason": m.get("reason"), "buy_date": bd,
                       "buy_px": bpx, "prior_up_pct": pu, "rs": rp,
                       "sys_real_pct": round(se[0], 1), "sys_why": se[1]})
    return n_all, evaluable, passed, reals, detail, rej


def run_universe_death(win, anchor, cend, kbear):
    """폐지명단(서류 1~2년 지연·진행중 사이클엔 맹점) 대신 *살아있는
    전 유니버스* 에서 직접: 사이클 중 가격기반 스위트스폼 스크린을
    통과(=위너처럼 보임)한 뒤 −80%+ 미회복 / 장기 가격동결(거래정지)
    한 종목 = '샀는데 죽은' 진짜 도플갱어. 진행중 사이클의 거래정지
    (폐지 미완료) 종목까지 포착 — 사용자 지적 반영.

    반환 dict: 전 유니버스 스크린통과 n, 그중 위너/사망/그외,
    정밀도(가격기반 전수정의), EV/픽(SYSTEM 실현), 사망 상세."""
    U = pick_universe_file(win)
    if not U:
        return None
    grid, ref = build_rs_grid(U, _shift_iso(anchor, -2), cend)
    wcodes = {r["code"] for r in rows(win)}
    npass = 0
    win_real, dead_real, other_real = [], [], []
    dead_det = []
    for code, s in U.items():
        d, c = s.get("d"), s.get("c")
        if not d or not c or len(c) < 254:
            continue
        q = screen_first_qualify(d, c, anchor, cend, grid, ref, kbear)
        if isinstance(q, str):
            continue
        j, bd, bpx, pu, rp = q
        npass += 1
        se = _sys_core(d, c, j, bpx, kbear)
        sr = se[0] if se else None
        seg = c[j:]
        mdd = min(seg) / bpx - 1
        last = c[-1] / bpx - 1
        tail = c[-40:] if len(c) >= 40 else c
        frozen = len(set(tail)) <= 3                 # 거래정지(동결) 꼬리
        is_dead = (mdd <= -0.80 and last <= -0.60) or \
                  (frozen and last <= -0.30)
        if code in wcodes:
            if sr is not None:
                win_real.append(sr)
        elif is_dead:
            if sr is not None:
                dead_real.append(sr)
            dead_det.append({"code": code, "buy_date": bd,
                             "last_pct": round(last * 100),
                             "sys_real_pct": (None if sr is None
                                              else round(sr, 1))})
        else:
            if sr is not None:
                other_real.append(sr)
    nwin = len(win_real)
    ndead = len(dead_det)
    nother = npass - nwin - ndead
    prec = nwin / npass if npass else None
    allr = win_real + dead_real + other_real
    ev = st.mean(allr) if allr else None
    # 사망 제외(=생존자만 봤다면) 가정 EV — 편향 크기 비교용
    ev_surv = (st.mean(win_real + other_real)
               if (win_real or other_real) else None)
    return {"universe_pass": npass, "winner_pass": nwin,
            "dead_pass": ndead, "other_pass": nother,
            "precision_pricewise_pct": (None if prec is None
                                        else round(prec * 100, 1)),
            "ev_all": ev, "ev_survivors_only": ev_surv,
            "dead_sys": {"n": len(dead_real),
                         "median": (st.median(dead_real)
                                    if dead_real else None),
                         "mean": (st.mean(dead_real)
                                  if dead_real else None),
                         "worst10": worst10(dead_real)},
            "dead_detail": dead_det}


def _shift_iso(iso, yrs):
    y, m, d = iso.split("-")
    return f"{int(y)+yrs:04d}-{m}-{d}"


def quart(v):
    if not v:
        return None, None, None
    s = sorted(v)

    def qq(f):
        return s[max(0, min(len(s) - 1, int(round(f * (len(s) - 1)))))]
    return qq(.5), qq(.25), qq(.75)


def worst10(v):
    if not v:
        return None
    s = sorted(v)
    k = max(1, len(s) // 10)
    return sum(s[:k]) / k


# ── 단일 실패유형 대조축 (analyze_loser_traps 패턴) ──────────────
def _last_annual(r, key):
    v = r.get(key)
    if isinstance(v, list) and v and isinstance(v[-1], (list, tuple)):
        return num(v[-1][1])
    return None


AXES = [
    ("섹터무리(sector_group_winner_count)",
     lambda r: num(r.get("sector_group_winner_count"))),
    ("선행상승%(prior_uptrend_pct)", lambda r: num(r.get("prior_uptrend_pct"))),
    ("RS(rs_score)", lambda r: num(r.get("rs_score"))),
    ("신고가대비%(pivot_vs_prior_52w_high_pct)",
     lambda r: num(r.get("pivot_vs_prior_52w_high_pct"))),
    ("외인60일(fgn_net_60d)", lambda r: num(r.get("fgn_net_60d"))),
    ("기관60일(inst_net_60d)", lambda r: num(r.get("inst_net_60d"))),
    ("직전분기EPS YoY%(eps_yoy_q1_pct)",
     lambda r: num(r.get("eps_yoy_q1_pct"))),
    ("부채비율%(debt_ratio_3y말)", lambda r: _last_annual(r, "debt_ratio_3y")),
    ("순이익률%(net_margin_3y말)", lambda r: _last_annual(r, "net_margin_3y")),
    ("pivot시총억(market_cap_at_pivot_eok)",
     lambda r: num(r.get("market_cap_at_pivot_eok"))),
    ("base깊이%(base_depth_pct)", lambda r: num(r.get("base_depth_pct"))),
]


def axis_stat(rws, g):
    v = [x for x in (g(r) for r in rws) if x is not None]
    if not v:
        return None, None, len(rws)
    return st.median(v), len(rws) - len(v), len(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", default="c2024-12")
    ap.add_argument("--ctl", default="c2024-12-ctrl500")
    ap.add_argument("--tag", default="")
    ap.add_argument("--limit", type=int, default=0,
                    help=">0이면 대조군 앞 N개만(스팟체크)")
    a = ap.parse_args()

    W = rows(a.win)
    Lo = rows(a.ctl)
    if a.limit > 0:
        Lo = Lo[:a.limit]
    wf = json.loads((CY / a.ctl / "winners_final.json")
                    .read_text(encoding="utf-8"))
    src_pool = (wf.get("sustain_filter") or {}).get("source_pool")
    scale = (src_pool / len(rows(a.ctl))) if src_pool else None

    wpx = load_prices(a.win)
    lpx = load_prices(a.ctl)
    kbear = build_kbear()
    kb_note = ("ON(apply_system_exit 동일 KOSPI 소스)" if kbear
               else "결손(KOSPI 미수신 → ★스위치 미적용)")

    L = [f"[생존자편향] 도플갱어 부검 [{a.win} vs {a.ctl}]"
         f"{'  (스팟체크 limit=%d)' % a.limit if a.limit else ''}",
         f"위너 n={len(W)} : 안오름 n={len(Lo)}"
         f"{' (전체 %d 중)' % len(rows(a.ctl)) if a.limit else ''}"
         f" | 비위너 모집단 source_pool={src_pool}"
         f" → 표본배율 ×{scale:.2f}" if scale else "",
         f"★약세스위치: {kb_note}",
         "도플갱어 = 안오름 중 pivot 시점 스크린을 *위너처럼* 통과한 종목.",
         "SYSTEM 출구 = ③진입대비-15% · ④고점대비-35%트레일 · ★약세스위치.",
         "*사후·종가·확률도구. ★생존자 보정=실측 도산주 주입(아래) "
         "— 단 진짜도산 보통주만 → 보정도 하한.*",
         "=" * 70]

    rows_json = {"win": a.win, "ctl": a.ctl, "source_pool": src_pool,
                 "scale": scale, "kbear": bool(kbear), "screens": {}}

    for sname, fs in SCREENS:
        wpass = [r for r in W if passes(r, fs)]
        lpass = [r for r in Lo if passes(r, fs)]
        wp, lp = len(wpass), len(lpass)
        # ── analyze_trap_filter.evaluate 와 *동일* 정의(내부 정합성) ──
        wr = wp / len(W) if W else 0
        lr = 1 - (lp / len(Lo)) if Lo else 0
        lift = ((wp / len(W)) / (lp / len(Lo))) if (Lo and lp) else None
        prec = wp / (wp + lp) if (wp + lp) else None     # 자연혼합 200:500

        # 도플갱어(=스크린 통과 안오름) 사후 분류 + SYSTEM 실현손익
        from collections import Counter
        cc = Counter()
        l_real = []
        dop_dead = []
        for r in lpass:
            cls, mg, lt = classify(r["code"], r.get("pivot_date"),
                                   num(r.get("pivot_close")), lpx)
            cc[cls] += 1
            if cls.startswith("사망"):
                dop_dead.append(r)
            se = system_exit(r["code"], r.get("pivot_date"),
                             num(r.get("pivot_close")), lpx, kbear)
            if se:
                l_real.append(se[0])
        # 위너 통과자 SYSTEM 실현손익(사과-대-사과)
        w_real = []
        for r in wpass:
            se = system_exit(r["code"], r.get("pivot_date"),
                             num(r.get("pivot_close")), wpx, kbear)
            if se:
                w_real.append(se[0])

        # EV/픽 — 이진 정밀도를 *돈* 으로: 자연혼합 & 모집단 외삽
        def ev(nw, nl):
            tot = nw + nl
            if tot <= 0 or not (w_real or l_real):
                return None
            sw = (st.mean(w_real) if w_real else 0) * nw
            sl = (st.mean(l_real) if l_real else 0) * nl
            return (sw + sl) / tot
        ev_nat = ev(wp, lp)
        ev_pop = ev(wp, lp * scale) if scale else None

        wm, wq1, wq3 = quart(w_real)
        lm, lq1, lq3 = quart(l_real)

        L += [f"■ 스크린: {sname}   [{DOC.get(sname,'')}]",
              f"  통과 — 위너 {wp}/{len(W)} · 안오름 {lp}/{len(Lo)} "
              f"| 위너잔존 {wr*100:.0f}% · 안오름제거 {lr*100:.0f}% "
              f"| lift {('n/a' if lift is None else f'{lift:.1f}x')} "
              f"| 정밀도(자연혼합) {('n/a' if prec is None else f'{prec*100:.0f}%')}",
              f"  └ 도플갱어(스크린통과 안오름 {lp}) 사후: "
              + (", ".join(f"{k} {v}" for k, v in cc.most_common())
                 if cc else "없음"),
              f"  └ SYSTEM 실현수익  위너통과 n={len(w_real)} "
              f"중앙{_f(wm)} (Q1{_f(wq1)}~Q3{_f(wq3)}) 평균{_f(_mean(w_real))}",
              f"                     도플갱어 n={len(l_real)} "
              f"중앙{_f(lm)} (Q1{_f(lq1)}~Q3{_f(lq3)}) 평균{_f(_mean(l_real))} "
              f"최악10%{_f(worst10(l_real))}",
              f"  └ EV/픽(SYSTEM 실현, 거래비용 무관): "
              f"자연혼합(200:500) {_f(ev_nat)} · "
              f"모집단외삽(위너:안오름×{scale:.1f}) {_f(ev_pop) if ev_pop is not None else 'n/a'}",
              f"     해석: 이진 정밀도 {('n/a' if prec is None else f'{prec*100:.0f}%')}"
              f" 가 도플갱어 실현손실 반영 시 EV {_f(ev_pop) if ev_pop is not None else _f(ev_nat)}."
              f" 진짜 상폐 누락 → 실제 EV ≤ 이 값(하한).",
              "-" * 70]

        rows_json["screens"][sname] = {
            "winner_pass": wp, "ctrl_pass": lp,
            "winner_retain_pct": round(wr * 100, 1),
            "ctrl_removed_pct": round(lr * 100, 1),
            "lift": (None if lift is None else round(lift, 2)),
            "precision_natural_pct": (None if prec is None
                                      else round(prec * 100, 1)),
            "doppelganger_outcome": dict(cc),
            "sys_real_winner": {"n": len(w_real), "median": wm,
                                "mean": _mean(w_real)},
            "sys_real_doppelganger": {"n": len(l_real), "median": lm,
                                      "mean": _mean(l_real),
                                      "worst10": worst10(l_real)},
            "ev_per_pick_natural": ev_nat, "ev_per_pick_pop": ev_pop,
        }
        if sname == "L+선행상승>=50":               # 스위트스폿 캡처
            SWEET = dict(wp=wp, lp=lp, w_real=list(w_real),
                         l_real=list(l_real), prec=prec,
                         ev_pop=ev_pop, ev_nat=ev_nat)

    # ── ★ 생존자 보정 — 실측 폐지 코호트(진짜 도산 보통주) 주입 ──
    #   기존 풀(build_control_sample)은 trough/peak/n_days≥60 으로
    #   상폐로 고점 못 만든 종목을 *구조적으로 배제* → "사망 0"은
    #   생존자 편향의 가시화였다. collect_delisted 로 복원한 진짜
    #   도산 보통주를 *가격기반* 스위트스폿(L+선행상승≥50, I 결손)
    #   으로 굴려 거짓양성에 주입 → 정밀도/EV 실측 재보정.
    if a.limit == 0 and "SWEET" in dir() and (CY / f"{a.win}-delisted").exists():
        anchor, cend = _cycle_window(a.win)
        dc = run_dead_cohort(a.win, anchor, cend, kbear)
        if dc:
            n_all, evaln, dpass, dreal, ddet, rej = dc
            wp, lp = SWEET["wp"], SWEET["lp"]
            wr_, lr_ = SWEET["w_real"], SWEET["l_real"]
            dm, dq1, dq3 = quart(dreal)
            mw = st.mean(wr_) if wr_ else 0
            ml = st.mean(lr_) if lr_ else 0
            md = st.mean(dreal) if dreal else 0
            nd = len(dpass)
            prec0 = SWEET["prec"]
            # 보정 정밀도: 폐지통과를 거짓양성에 그대로 가산(폐지는
            # 표본 아닌 *거의 전수* → 스케일 안 함, 보수적).
            prec1 = wp / (wp + lp + nd) if (wp + lp + nd) else None
            # EV/픽 모집단: 위너 wp + 생존비위너 lp×scale + 폐지 nd(전수)
            cpop = (lp * scale) if scale else lp

            def evc(parts):
                tot = sum(n for n, _ in parts)
                return (sum(n * m for n, m in parts) / tot) if tot else None
            ev_surv = evc([(wp, mw), (cpop, ml)])
            ev_corr = evc([(wp, mw), (cpop, ml), (nd, md)])
            L += [
                "=" * 70,
                "★ 생존자 보정 — 실측 폐지 코호트 주입 "
                "(스위트스폿 L+선행상승≥50, 가격기반·I 결손)",
                f"  진짜 도산 보통주 {n_all}종 중 가격평가가능 {evaln} → "
                f"스크린이 '사라'고 했을 종목 {nd}개 "
                f"(= 시스템이 못 거른 실제 지뢰)",
                "  └ 미통과 사유(왜 안 사게 됐나): "
                + (", ".join(f"{k} {v}" for k, v in rej.most_common())
                   if rej else "없음"),
                f"  └ 그 {nd}개의 SYSTEM 실현수익: 중앙{_f(dm)} "
                f"(Q1{_f(dq1)}~Q3{_f(dq3)}) 평균{_f(md)} "
                f"최악10%{_f(worst10(dreal))}",
                f"  └ 정밀도(자연혼합 정의): 생존자限定 "
                f"{('n/a' if prec0 is None else f'{prec0*100:.0f}%')} "
                f"→ 폐지 주입 보정 "
                f"{('n/a' if prec1 is None else f'{prec1*100:.0f}%')} "
                f"(거짓양성에 +{nd})",
                f"  └ EV/픽(모집단, SYSTEM 실현): 생존자限定 "
                f"{_f(ev_surv)} → 폐지 보정 {_f(ev_corr)} "
                f"(Δ {_f((ev_corr or 0)-(ev_surv or 0))})",
            ]
            if nd > 0:
                L += [
                    "  해석: *구조적으로 빠졌던 진짜 도산주*를 주입하니 "
                    "스크린이",
                    f"  {nd}개를 '사라'고 했고(전손급) → EV {_f(ev_surv)}"
                    f"→{_f(ev_corr)} 실측 하락 = 생존자 편향의 *크기*."]
            else:
                L += [
                    "  해석: 진짜 도산주 *0개* 가 매수신호 — 스크린이",
                    "  똑똑해서가 아니라, 이 사이클 도산주들이 강세장 "
                    "전에 이미",
                    "  거래정지/★약세구간이라 *애초에 살 수 없었음*(미통과",
                    "  사유 참조). 즉 이 사이클의 폐지발 생존자편향은 "
                    "구조적으로",
                    "  ≈0 — 시스템이 회피한 게 아니라 시장에서 매수 불가였던 것."]
            if ddet:
                L.append("  주입된 지뢰(샘플): " + " · ".join(
                    f"{x['name']}({x['code']}) "
                    f"매수{x['buy_date']}→{x['sys_real_pct']:+.0f}%"
                    for x in sorted(ddet, key=lambda y: y["sys_real_pct"])[:6]))
            L += ["  한계: 폐지종목 외인/기관 비제공 → I 결손(L·선행상승만,",
                  "  검증된 23.6x 정의의 가격버전). RS=살아있는 유니버스",
                  "  근사. 사유필터=진짜도산만(합병·스팩·신탁 제외)이라",
                  "  보정도 *하한*(다른 폐지유형 미포함). 사후·종가.",
                  "=" * 70]
            rows_json["survivor_corrected"] = {
                "delisted_total": n_all, "evaluable": evaln,
                "screen_pass": nd, "pass_codes": dpass,
                "dead_sys_real": {"median": dm, "mean": md,
                                  "worst10": worst10(dreal)},
                "precision_survivor_only_pct": (None if prec0 is None
                                                else round(prec0*100, 1)),
                "precision_corrected_pct": (None if prec1 is None
                                            else round(prec1*100, 1)),
                "ev_pop_survivor_only": ev_surv,
                "ev_pop_corrected": ev_corr,
                "reject_breakdown": dict(rej), "detail": ddet}

    # ── ★★ 올바른 생존자 보정 — 살아있는 전 유니버스 직접 사망탐지 ──
    #   폐지명단은 한국 상폐서류가 거래정지 후 1~2년 지연 → 진행중
    #   사이클(c2024-12)엔 *맹점*(死전 좀비만 잡힘). 그래서 폐지명단
    #   대신 살아있는 전 유니버스에서 "사이클 중 스크린통과(위너처럼
    #   보임) → 그 뒤 −80%↓ 미회복/장기 거래정지(동결)" 를 직접 탐지
    #   = 진행중 사이클의 *현재 거래정지(폐지 미완료)* 종목까지 포착.
    #   (사용자 지적: 死전 좀비가 아니라 '거래중→정지'를 봐야 함)
    if a.limit == 0:
        anchor2, cend2 = _cycle_window(a.win)
        ud = run_universe_death(a.win, anchor2, cend2, kbear)
        if ud:
            np_ = ud["universe_pass"]
            L += [
                "=" * 70,
                "★★ 올바른 생존자 보정 — 살아있는 전 유니버스 직접 "
                "사망탐지 (폐지명단 비의존)",
                "  폐지명단은 상폐서류 1~2년 지연 → 진행중 사이클 맹점."
                " 대신 사이클 중",
                "  스크린통과(위너처럼) 후 −80%↓미회복/장기거래정지 "
                "= '샀는데 죽음'.",
                f"  전 유니버스 스크린통과(매수신호) {np_} → "
                f"위너 {ud['winner_pass']} · "
                f"사망/정지 {ud['dead_pass']} · 그외생존 {ud['other_pass']}",
                f"  └ 정밀도(가격기반 전수정의) "
                f"{_pct(ud['precision_pricewise_pct'])} "
                f"(= 매수신호 중 실제 위너 비율)",
                f"  └ 사망/정지 {ud['dead_pass']}종 SYSTEM 실현: "
                f"중앙{_f(ud['dead_sys']['median'])} "
                f"평균{_f(ud['dead_sys']['mean'])} "
                f"최악10%{_f(ud['dead_sys']['worst10'])}",
                f"  └ EV/픽(SYSTEM 실현): 사망포함 {_f(ud['ev_all'])} "
                f"vs 생존자만 봤다면 {_f(ud['ev_survivors_only'])} "
                f"(Δ {_f((ud['ev_all'] or 0)-(ud['ev_survivors_only'] or 0))})",
            ]
            dd = ud["dead_detail"]
            if dd:
                def _smp(x):
                    sv = x["sys_real_pct"]
                    sv = "n/a" if sv is None else f"{sv:+.0f}%"
                    return (f"{x['code']} 매수{x['buy_date']}"
                            f"→최종{x['last_pct']}%(SYS{sv})")
                L.append("  실제 지뢰(샘플): " + " · ".join(
                    _smp(x) for x in
                    sorted(dd, key=lambda y: y["last_pct"])[:8]))
            L += [
                "  해석: 이게 폐지서류 지연에 안 막히는 *진짜* 생존자",
                "  보정. 진행중 c2024-12 의 거래정지(미폐지) 종목까지 포함.",
                "  −15% 재해손절이 전손을 SYSTEM 실현 수준으로 한정하나",
                "  정밀도·EV 의 실측 하락폭이 곧 생존자 편향의 크기.",
                "  한계: 가격기반 스크린(I 결손·RS 근사)·사후·종가·",
                "  거래비용 무관. 위너=model_book 200 기준.",
                "=" * 70]
            rows_json["universe_death_correction"] = ud

    # ── 단일 실패유형: 스위트스폿(L+선행상승≥50) 통과 *사망 도플갱어*
    #    vs 통과 위너 — 두 그룹 다 스크린 통과 전제, 무엇이 가르나 ──
    fs_sweet = SCREENS[1][1]
    w_sweet = [r for r in W if passes(r, fs_sweet)]
    dead_sweet = []
    for r in (r2 for r2 in Lo if passes(r2, fs_sweet)):
        cls, _, _ = classify(r["code"], r.get("pivot_date"),
                             num(r.get("pivot_close")), lpx)
        if cls.startswith("사망"):
            dead_sweet.append(r)
    L += ["■ 단일 실패유형 — 스위트스폿(L+선행상승≥50) 통과 "
          f"*사망 도플갱어* n={len(dead_sweet)} vs 통과 위너 n={len(w_sweet)}",
          "  (둘 다 스크린 통과 = 스크린이 *진입 시점에 구분 못 한* 쌍)",
          "  축 | 위너중앙 | 사망도플갱어중앙 | Δ(위너-사망) | 결손"]
    diffs = []
    for nm, g in AXES:
        wmed, wmiss, wn = axis_stat(w_sweet, g)
        dmed, dmiss, dn = axis_stat(dead_sweet, g)
        if wmed is None or dmed is None:
            L.append(f"  {nm} | {_f(wmed)} | {_f(dmed)} | n/a "
                     f"| 위너{wmiss}/{len(w_sweet)} 사망{dmiss}/{len(dead_sweet)}")
            continue
        delta = wmed - dmed
        rel = abs(delta) / (abs(wmed) + 1e-9)
        diffs.append((rel, nm, delta))
        L.append(f"  {nm} | {_f(wmed)} | {_f(dmed)} | {delta:+,.1f} "
                 f"| 위너{wmiss}/{len(w_sweet)} 사망{dmiss}/{len(dead_sweet)}")
    diffs.sort(reverse=True)
    if diffs:
        L += ["",
              f"  ▶ 가장 크게 갈리는 축(상대격차순): "
              + " > ".join(n for _, n, _ in diffs[:3]),
              "  ▶ = '한국식 캔슬림이 진입 시점에 거르지 못하는' 후보 축."
              " v1.x 차기 1순위 검증 대상(원전·정밀컷 아님·방향 단서)."]

    L += ["=" * 70,
          "한계(정직): ① 진짜 상장폐지 종목 명단 프로젝트 내 0개 →",
          "  '−80% 미회복' 프록시만 → 모든 보정치는 생존자편향의 *하한*",
          "  (진짜 상폐 포함 시 정밀도·EV 더 낮음). ② 안오름은 무작위",
          f"  표본 500/{src_pool}(×{scale:.1f} 외삽) — 표본오차 존재.",
          "  ③ 사후·종가·일별리밸런스(실제 주1회)·거래비용/세금 무관.",
          "  ④ screen_v11 의 거래량-조용·v1.3 고점후분산·케이프 신저점",
          "  일별 가드는 model_book 필드로 재현 불가 → *미적용*(결손).",
          "  본 스크린 = L·선행상승·(I) 만 → 실제 라이브보다 느슨,",
          "  실제 도플갱어 통과는 더 적을 수 있음(보정=보수적 상한).",
          "  ⑤ ★스위치는 apply_system_exit 와 동일 KOSPI 소스(시스템",
          "  일관성 우선). ⑥ 단일~2사이클. 방향 참고용, 수익 보장 아님."]

    txt = "\n".join(x for x in L if x is not None)
    out = CY.parent / f"_doppelganger{a.tag}.txt"
    out.write_text(txt, encoding="utf-8")
    (CY / a.win / "doppelganger_rows.json").write_text(
        json.dumps(rows_json, ensure_ascii=False, indent=1), encoding="utf-8")

    # analysis_history.md append-only
    if a.limit == 0:
        hist = CY.parent / "analysis_history.md"
        with hist.open("a", encoding="utf-8") as f:
            f.write(f"\n\n## 도플갱어 부검(생존자편향) [{a.win}] "
                    f"위너{len(W)}:안오름{len(Lo)}\n\n```\n{txt}\n```\n")
    print(f"saved: {out}  (+doppelganger_rows.json"
          f"{'' if a.limit else ', analysis_history.md append'})",
          file=sys.stderr)


def _mean(v):
    return st.mean(v) if v else None


def _f(x):
    if x is None:
        return "결손"
    return f"{x:+,.1f}" if abs(x) >= 100 else f"{x:+.1f}"


def _pct(x):
    return "결손" if x is None else f"{x:.0f}%"


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""273 — **「대선 2년 전 매수 → 대선일 매도」 규칙(드러켄밀러 인용) 비교 검증** (사전등록 `tasks/273-election-cycle.md`)

규칙 정의 · 문턱 · 무너뜨리기 항목은 전부 사전등록 문서에 «먼저» 적혔다. 이 각본은 그것을 그대로 계산한다.

자료 (전부 `data/273-*.csv`, 머리줄에 출처·수집일):
  SPY / QQQ 총수익(야후 adjclose) · S&P 500 가격(야후 ^GSPC) · 무위험 = Ken French RF(1개월 국채, 월 %)
  🚨 FRED TB3MS 는 수집 당일 두 번 시간 초과 ⇒ 사전등록 §2 의 대체안(French RF)을 쓴다.
층 B 의 SPY/QQQ 는 122b 와 «같은» `101-fund-ohlc.json` 의 c(총수익)를 쓴다.
우리 규칙 곡선은 `122b-anytime-plus30.py` 의 코드를 «그대로» 복사해 재생성한다 (파라미터 손대지 않음).

실행:  PYTHONIOENCODING=utf-8 python3 scripts/273-election-cycle.py [--quick] [--no-our]
"""
from __future__ import annotations

import csv
import datetime as dt
import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
RES = HERE.parent / "results"
D_END = "2026-08-21"                       # 122b 와 같은 끝
D122 = "1999-04-01"                        # 122b 우리 규칙 곡선 시작
B1_START = "2021-02-01"                    # 두뇌 지정 층 B 구간
HOR = (3, 5, 10)
SHIFTS = (-20, -10, -5, 5, 10, 20)


# ───────────────────────────── 자료 ─────────────────────────────
def load_csv(fn, col):
    ds, vs = [], []
    with open(DATA / fn, encoding="utf-8") as f:
        rd = csv.reader(x for x in f if not x.lstrip('"').startswith("#"))
        hdr = next(rd)
        j = hdr.index(col)
        for r in rd:
            if r[j] in ("", "None"):
                continue
            ds.append(r[0])
            vs.append(float(r[j]))
    return ds, vs


def load_rf():
    """French RF: 월 % → 그 달의 거래일마다 (rf_m*12)/100/252 를 누적 (사전등록 §2)."""
    m = {}
    with open(DATA / "273-RF-french.csv", encoding="utf-8") as f:
        rd = csv.reader(x for x in f if not x.lstrip('"').startswith("#"))
        next(rd)
        for a, b in rd:
            m[a] = float(b)
    last = sorted(m)[-1]

    def daily(d):
        k = d[:4] + d[5:7]
        r = m.get(k, m[last])              # 자료 끝(2026-07) 뒤는 마지막 달 값
        return r * 12.0 / 100.0 / 252.0
    return daily, last


def clip(ds, vs, d0, d1):
    z = [(d, v) for d, v in zip(ds, vs) if d0 <= d <= d1]
    return [d for d, _ in z], [v for _, v in z]


# ───────────────────────────── 선거일 ─────────────────────────────
def election_day(y):
    nov1 = dt.date(y, 11, 1)
    first_mon = nov1 + dt.timedelta(days=(7 - nov1.weekday()) % 7)
    return (first_mon + dt.timedelta(days=1)).isoformat()


MIDTERMS = [y for y in range(1926, 2027) if y % 4 == 2]


def idx_after(ds, d):
    """d 보다 «뒤» 첫 거래일 인덱스 (없으면 None)."""
    for i, x in enumerate(ds):
        if x > d:
            return i
    return None


def idx_on_or_after(ds, d):
    for i, x in enumerate(ds):
        if x >= d:
            return i
    return None


def cycles(ds, shift=0):
    """사이클 목록: (중간선거해, 매수idx, 매도idx, 매도일 정확히 있었나, 다음매수idx)."""
    out = []
    n = len(ds)
    for m in MIDTERMS:
        e_mid, e_pres = election_day(m), election_day(m + 2)
        if e_pres < ds[0] or e_mid > ds[-1]:
            continue
        bi = idx_after(ds, e_mid)
        if bi is None:
            continue
        bi = max(0, min(n - 1, bi + shift))
        if e_mid < ds[0]:                  # 구간 시작 시 «이미 보유 중»
            bi = 0
        si = idx_on_or_after(ds, e_pres)
        exact = (si is not None and ds[si] == e_pres)
        if si is None:
            si = n - 1                      # 자료 끝에서 «잘림»
        if si <= bi:
            continue
        nb = idx_after(ds, election_day(m + 4))
        if nb is not None:
            nb = max(0, min(n - 1, nb + shift))
        out.append({"mid": m, "buy": bi, "sell": si, "exact": exact, "next_buy": nb,
                    "started_holding": e_mid < ds[0]})
    return out


def rule_curve(ds, px, rf_daily=None, shift=0):
    hold = set()
    cy = cycles(ds, shift)
    for c in cy:
        hold.update(range(c["buy"] + 1, c["sell"] + 1))
    v = [1.0]
    for i in range(1, len(ds)):
        if i in hold:
            v.append(v[-1] * px[i] / px[i - 1])
        else:
            v.append(v[-1] * (1.0 + (rf_daily(ds[i]) if rf_daily else 0.0)))
    return v, cy


# ───────────────────────────── 자 ─────────────────────────────
def years_between(d0, d1):
    a, b = dt.date.fromisoformat(d0), dt.date.fromisoformat(d1)
    return (b - a).days / 365.25


def cagr(ds, v):
    return ((v[-1] / v[0]) ** (1.0 / years_between(ds[0], ds[-1])) - 1) * 100


def mdd(v):
    pk, w = v[0], 0.0
    for x in v:
        pk = max(pk, x)
        w = min(w, x / pk - 1)
    return w * 100


def windows(ds, vals, yrs):
    """122b 의 windows() 그대로: 시작일 날마다, 창 = yrs*252 거래일, 연평균."""
    n = len(ds)
    step = int(round(yrs * 252))
    out = []
    for i in range(0, n - step):
        a, b = vals[i], vals[i + step]
        if a > 0 and b > 0:
            out.append(((b / a) ** (1.0 / yrs) - 1) * 100)
    return sorted(out)


def wstat(w):
    if not w:
        return None
    q = lambda f: w[int(len(w) * f)]                              # noqa: E731
    return {"min": w[0], "p10": q(0.10), "med": q(0.50), "p90": q(0.90), "max": w[-1],
            "n": len(w), "neg": 100.0 * sum(1 for x in w if x < 0) / len(w)}


def pct(x, p=2):
    return ("%+." + str(p) + "f%%") % x


def fmt_w(s):
    return "—" if s is None else "%s | %.0f%% | %s" % (pct(s["min"]), s["neg"], pct(s["med"]))


# ───────────────────────────── 우리 규칙 곡선 (122b 코드 «그대로») ─────────────────────────────
def our_rule_curve(n_seed):
    sys.path.insert(0, str(HERE))

    def _load(name, fn):
        s = _u.spec_from_file_location(name, HERE / fn)
        m = _u.module_from_spec(s)
        s.loader.exec_module(m)
        return m
    r91 = _load("r91", "91-us-out-of-sample.py")
    r102 = _load("r102", "102-implement-principles.py")
    r103 = _load("r103", "103-code33-strength.py")
    r108 = _load("r108", "108-short-index.py")
    r118 = _load("r118", "118-matched-placebo.py")
    f92a = r102.f92a
    YEARS = tuple(range(1999, 2027))
    SHORT_SIZE, BORROW = 0.20, 2.0
    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D122, D_END, "91-monthly-us-full.json", use_ext=False)
    if missing:
        raise SystemExit("🚨 경로 없음")
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            rec = fund.get(p["code"])
            arq = (rec or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                          > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k
    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}
    _n, ev = r118.fills_of(by_f)
    rs = r91.sim(ev, n_seed)
    curves = []
    for x in rs:
        vals = [(d, v) for d, v in x["curve"]] + [(x["curve"][-1][0],
                                                   1.0 + x["equity_pct"] / 100.0)]
        v, cur = 1.0, []
        bo = BORROW / 100.0 / 252.0 * SHORT_SIZE
        for i in range(1, len(vals)):
            if vals[i - 1][1] <= 0:
                break
            r_ = vals[i][1] / vals[i - 1][1] - 1.0
            d = vals[i][0]
            rs_ = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
            v *= (1.0 + r_ + rs_)
            cur.append((d, max(v, 1e-9)))
        curves.append(cur)
    L = min(len(x) for x in curves)
    our_ds = [x[0] for x in curves[0][:L]]
    our_v = [st.median(curves[j][i][1] for j in range(len(curves))) for i in range(L)]
    return our_ds, our_v, r91.OUT


def local_index(tk, out_dir):
    d = json.loads((out_dir / "101-fund-ohlc.json").read_text(encoding="utf-8"))
    s = d[tk]["series"]
    ds = [x for x in sorted(s) if D122 <= x <= D_END]
    return ds, [s[x][3] for x in ds]


# ───────────────────────────── 층 A 한 판 ─────────────────────────────
def layer(name, ds, px, rf_daily, basis, out, lines):
    v0, cy = rule_curve(ds, px)
    v1, _ = rule_curve(ds, px, rf_daily)
    hold_v = [p / px[0] for p in px]
    arms = (("규칙·현금0%", v0), ("규칙·국채", v1), ("지수 보유", hold_v))
    lines.append("\n## %s — %s ~ %s · %s · 사이클 %d회\n" % (name, ds[0], ds[-1], basis, len(cy)))
    lines.append("### 1차 — 전체 구간 연환산(CAGR) · 최대 낙폭\n")
    lines.append("| 팔 | 총수익 | CAGR | 최대 낙폭 |")
    lines.append("|---|---:|---:|---:|")
    o = {"start": ds[0], "end": ds[-1], "basis": basis, "arms": {}}
    for nm, v in arms:
        o["arms"][nm] = {"total": (v[-1] / v[0] - 1) * 100, "cagr": cagr(ds, v), "mdd": mdd(v)}
        lines.append("| %s | %s | %s | %s |" % (nm, pct(o["arms"][nm]["total"], 1),
                                               pct(o["arms"][nm]["cagr"]), pct(o["arms"][nm]["mdd"], 1)))
    d0 = o["arms"]["규칙·현금0%"]["cagr"] - o["arms"]["지수 보유"]["cagr"]
    d1 = o["arms"]["규칙·국채"]["cagr"] - o["arms"]["지수 보유"]["cagr"]
    o["cagr_gap_cash0"], o["cagr_gap_tbill"] = d0, d1
    lines.append("\n규칙 − 지수 CAGR: 현금0%% **%s** · 국채 **%s** (국채 − 현금0%% = %s)\n"
                 % (pct(d0), pct(d1), pct(d1 - d0)))
    lines.append("### 2차 — 3·5·10년 이동 창 (시작일 날마다 · 연평균)\n")
    lines.append("| 창 | 팔 | 최악 | 마이너스 비율 | 중앙 | 창 수 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    o["windows"] = {}
    for yrs in HOR:
        for nm, v in arms:
            s = wstat(windows(ds, v, yrs))
            o["windows"].setdefault(str(yrs), {})[nm] = s
            if s:
                lines.append("| %d년 | %s | %s | %.0f%% | %s | %d |"
                             % (yrs, nm, pct(s["min"]), s["neg"], pct(s["med"]), s["n"]))
            else:
                lines.append("| %d년 | %s | 불가 | 불가 | 불가 | 0 |" % (yrs, nm))
    # 손실 방어 판정 (2차): 최악·마이너스 비율 «둘 다» 나은가
    o["defense"] = {}
    for yrs in HOR:
        w = o["windows"][str(yrs)]
        for nm in ("규칙·현금0%", "규칙·국채"):
            a, b = w[nm], w["지수 보유"]
            o["defense"]["%d/%s" % (yrs, nm)] = (None if (a is None or b is None)
                                                 else (a["min"] > b["min"] and a["neg"] < b["neg"]))
    lines.append("\n손실 방어(최악 «그리고» 마이너스 비율 둘 다 나음): "
                 + " · ".join("%s → %s" % (k, {True: "✅", False: "❌", None: "불가"}[v])
                              for k, v in o["defense"].items()) + "\n")
    lines.append("### 3차 — 사이클별 (보유 2년 vs 그 뒤 현금 2년 동안의 지수)\n")
    lines.append("| 중간선거 | 매수일 | 매도일 | 보유 2년 수익 | 현금 2년 지수 수익 | 차이(%p) | 적중 |")
    lines.append("|---|---|---|---:|---:|---:|:-:|")
    o["cycles"] = []
    hit = tot = 0
    for c in cy:
        hr = (px[c["sell"]] / px[c["buy"]] - 1) * 100
        nb = c["next_buy"]
        trunc = nb is None
        cr = (px[(len(px) - 1) if trunc else nb] / px[c["sell"]] - 1) * 100
        h = hr > cr
        if not trunc:
            tot += 1
            hit += int(h)
        o["cycles"].append({"mid": c["mid"], "buy": ds[c["buy"]], "sell": ds[c["sell"]],
                            "hold_ret": hr, "cash_idx_ret": cr, "diff": hr - cr, "hit": h,
                            "truncated": trunc, "sell_exact": c["exact"],
                            "started_holding": c["started_holding"]})
        lines.append("| %d%s | %s%s | %s%s | %s | %s%s | %s | %s |"
                     % (c["mid"], "" if c["exact"] else " ⚠", ds[c["buy"]],
                        " (시작 시 보유 중)" if c["started_holding"] else "",
                        ds[c["sell"]], "" if c["exact"] else " ⚠(다음 거래일)",
                        pct(hr, 1), pct(cr, 1), " (자료 끝 잘림)" if trunc else "",
                        pct(hr - cr, 1), "○" if h else "×"))
    o["hit"], o["hit_total"] = hit, tot
    lines.append("\n적중(보유 2년 > 현금 2년 지수): **%d / %d** (자료 끝에서 잘린 사이클 제외)\n" % (hit, tot))
    return o, v0, v1, hold_v, cy


def midterm_12m(ds, px):
    """외부 인용 통계 재계산: 중간선거일 종가 → 12개월 뒤(그 날 또는 직전 거래일) 종가."""
    rows = []
    for m in MIDTERMS:
        e = election_day(m)
        if e < ds[0]:
            continue
        i = idx_on_or_after(ds, e)
        e1 = (dt.date.fromisoformat(e) + dt.timedelta(days=365)).isoformat()
        j = None
        for k in range(len(ds) - 1, -1, -1):
            if ds[k] <= e1:
                j = k
                break
        if i is None or j is None or j <= i or ds[j] < e1[:4] + "-10-01":
            continue
        rows.append((m, ds[i], ds[j], (px[j] / px[i] - 1) * 100))
    return rows


def breakers(name, ds, px, rf_daily, base, cy, lines, o):
    lines.append("\n### 무너뜨려 보기 — %s\n" % name)
    # ① 매수일 이동
    lines.append("**① 매수일 이동 (매도일 고정)** — 규칙 − 지수 CAGR(%p)\n")
    lines.append("| 이동(거래일) | 현금0% | 국채 |")
    lines.append("|---:|---:|---:|")
    hc = base["arms"]["지수 보유"]["cagr"]
    o["shift"] = {}
    for sft in SHIFTS:
        a, _ = rule_curve(ds, px, None, sft)
        b, _ = rule_curve(ds, px, rf_daily, sft)
        o["shift"][sft] = {"cash0": cagr(ds, a) - hc, "tbill": cagr(ds, b) - hc}
        lines.append("| %+d | %s | %s |" % (sft, pct(o["shift"][sft]["cash0"]), pct(o["shift"][sft]["tbill"])))
    lines.append("| 0 (기준) | %s | %s |" % (pct(base["cagr_gap_cash0"]), pct(base["cagr_gap_tbill"])))
    # ② 2008 사이클 제거 (2006 매수 다음날 ~ 2010 매수일 블록을 «둘 다»에서 잘라냄)
    c06 = next((c for c in cy if c["mid"] == 2006), None)
    if c06 and c06["next_buy"] is not None:
        lo, hi = c06["buy"] + 1, c06["next_buy"]
        keep = [i for i in range(1, len(ds)) if not (lo <= i <= hi)]
        yrs_removed = years_between(ds[c06["buy"]], ds[c06["next_buy"]])
        yrs_total = years_between(ds[0], ds[-1]) - yrs_removed

        def spliced(v):
            out, cur = [1.0], 1.0
            for i in keep:
                cur *= v[i] / v[i - 1]
                out.append(cur)
            return out
        v0, _ = rule_curve(ds, px)
        v1, _ = rule_curve(ds, px, rf_daily)
        hv = [p / px[0] for p in px]
        res = {}
        for nm, v in (("규칙·현금0%", v0), ("규칙·국채", v1), ("지수 보유", hv)):
            s = spliced(v)
            res[nm] = {"cagr": ((s[-1]) ** (1.0 / yrs_total) - 1) * 100,
                       "w3": wstat(windows(list(range(len(s))), s, 3)),
                       "w5": wstat(windows(list(range(len(s))), s, 5))}
        o["ex2008"] = res
        lines.append("\n**② 2008 사이클 제거** (%s 매수 다음날 ~ %s 블록 %.1f년을 규칙·지수 «둘 다»에서 잘라냄)\n"
                     % (ds[c06["buy"]], ds[c06["next_buy"]], yrs_removed))
        lines.append("| 팔 | CAGR | 3년 최악 | 3년 마이너스 | 5년 최악 | 5년 마이너스 |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for nm, r in res.items():
            lines.append("| %s | %s | %s | %.0f%% | %s | %.0f%% |"
                         % (nm, pct(r["cagr"]), pct(r["w3"]["min"]), r["w3"]["neg"],
                            pct(r["w5"]["min"]) if r["w5"] else "불가", r["w5"]["neg"] if r["w5"] else 0))
        g0 = res["규칙·현금0%"]["cagr"] - res["지수 보유"]["cagr"]
        g1 = res["규칙·국채"]["cagr"] - res["지수 보유"]["cagr"]
        lines.append("\n규칙 − 지수 CAGR (2008 사이클 없이): 현금0%% **%s** · 국채 **%s** (기준: %s · %s)\n"
                     % (pct(g0), pct(g1), pct(base["cagr_gap_cash0"]), pct(base["cagr_gap_tbill"])))
    else:
        lines.append("\n**② 2008 사이클 제거** — 이 층에는 2006 사이클이 없어 불가\n")
    return o


def start_years(name, ds, px, rf_daily, years, lines, o):
    lines.append("\n**③ 시작 연도 바꾸기 — %s** (시작 = 그 해 첫 거래일 · 시작 시 상태는 §2 규칙)\n" % name)
    lines.append("| 시작 | 끝 | 규칙·현금0% CAGR | 규칙·국채 CAGR | 지수 CAGR | 차이(현금0%) | 차이(국채) |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    o["start_years"] = {}
    for y in years:
        d0 = "%d-01-01" % y
        i = idx_on_or_after(ds, d0)
        if i is None:
            continue
        ds2, px2 = ds[i:], px[i:]
        a, _ = rule_curve(ds2, px2)
        b, _ = rule_curve(ds2, px2, rf_daily)
        h = [p / px2[0] for p in px2]
        ca, cb, ch = cagr(ds2, a), cagr(ds2, b), cagr(ds2, h)
        o["start_years"][y] = {"cash0": ca, "tbill": cb, "hold": ch}
        lines.append("| %s | %s | %s | %s | %s | %s | %s |"
                     % (ds2[0], ds2[-1], pct(ca), pct(cb), pct(ch), pct(ca - ch), pct(cb - ch)))


# ───────────────────────────── main ─────────────────────────────
def main() -> int:
    quick = "--quick" in sys.argv
    no_our = "--no-our" in sys.argv
    rf_daily, rf_last = load_rf()
    today = dt.date.today().isoformat()
    out = {"generated": today, "rf_last_month": rf_last}
    L = []
    L.append("# 273 — **「대선 2년 전 매수 → 대선일 매도」 규칙 vs 우리 규칙 vs 지수** · «묘사»(CI 없음 · 판정 아님)\n")
    L.append("> 조사 세션 · 각본 `research/handoff/scripts/273-election-cycle.py` · 사전등록 `tasks/273-election-cycle.md` · 생성 %s" % today)
    L.append("> 자료: `data/273-spy-yahoo.csv` · `273-qqq-yahoo.csv` (야후 adjclose = **총수익**, 수집 2026-09-12) · `273-gspc-yahoo.csv` (^GSPC **가격**, 배당 없음) · `273-RF-french.csv` (Ken French RF, 1개월 국채 월 %%, 마지막 달 %s)" % rf_last)
    L.append("> 🚨 FRED TB3MS(3개월 국채)는 수집 당일 두 번 시간 초과·연결 끊김 ⇒ 사전등록 §2 대체안(French RF, **1개월** 국채)을 쓴다. «국채» 팔은 «1개월 국채»다.")
    L.append("> 층 B 의 SPY/QQQ 는 122b 와 같은 `.cache/bt5y/out/101-fund-ohlc.json` c(총수익). 우리 규칙 곡선은 `122b-anytime-plus30.py` 코드 그대로 재생성(`91:87 STOP, TARGET = 10.0, 30.0` 그대로, 세전, 슬롯5 중앙 경로).")
    L.append("> 세금·수수료 없음(세전). 끝 날짜 %s 로 통일. 단위: 수익률 차이는 %%p." % D_END)
    L.append("> ⛔ **모든 표는 «묘사»다** — 자산곡선 «하나»에서 나온 창들이고 신뢰구간이 없다(`122c` 방식).\n")

    # ── 층 A1 SPY
    dsS, pS = load_csv("273-spy-yahoo.csv", "adjclose")
    dsS, pS = clip(dsS, pS, "1993-01-29", D_END)
    a1, v0S, v1S, hS, cyS = layer("층 A1 — SPY 총수익", dsS, pS, rf_daily, "총수익(배당 재투자)", out, L)
    out["A1"] = a1
    # ── 층 A2 ^GSPC 1950~
    dsG, pG = load_csv("273-gspc-yahoo.csv", "close")
    dsG, pG = clip(dsG, pG, "1950-01-01", D_END)
    a2, v0G, v1G, hG, cyG = layer("층 A2 — S&P 500 가격지수", dsG, pG, rf_daily, "가격(배당 없음)", out, L)
    out["A2"] = a2
    # ── 층 A3 QQQ
    dsQ, pQ = load_csv("273-qqq-yahoo.csv", "adjclose")
    dsQ, pQ = clip(dsQ, pQ, "1999-03-10", D_END)
    a3, v0Q, v1Q, hQ, cyQ = layer("층 A3 — QQQ 총수익", dsQ, pQ, rf_daily, "총수익(배당 재투자)", out, L)
    out["A3"] = a3

    # ── 외부 인용 통계 재계산
    L.append("\n## 외부 인용 통계 재계산 — 「1950년 이후 중간선거 후 12개월 S&P 500 19회 모두 상승, 평균 약 15%」\n")
    L.append("중간선거일 종가 → 365일 뒤(또는 직전 거래일) 종가. S&P 500 **가격**지수.\n")
    L.append("| 중간선거 | 시작 | 끝 | 12개월 수익 |")
    L.append("|---|---|---|---:|")
    rows = midterm_12m(dsG, pG)
    for m, a, b, r in rows:
        L.append("| %d | %s | %s | %s |" % (m, a, b, pct(r, 1)))
    rets = [r for *_, r in rows]
    out["midterm_12m"] = {"n": len(rets), "pos": sum(1 for r in rets if r > 0),
                          "mean": st.mean(rets), "median": st.median(rets), "min": min(rets), "max": max(rets)}
    L.append("\n재계산: **%d회 중 %d회 상승** · 단순평균 **%s** · 중앙값 %s · 최소 %s · 최대 %s"
             % (len(rets), out["midterm_12m"]["pos"], pct(st.mean(rets), 1), pct(st.median(rets), 1),
                pct(min(rets), 1), pct(max(rets), 1)))
    ok = (len(rets) == 19 and out["midterm_12m"]["pos"] == 19)
    L.append("⇒ 「19회 모두 상승」: **%s** · 「평균 약 15%%」: 재계산 단순평균 %s (%s)\n"
             % ("맞음" if ok else "틀림(%d/%d)" % (out["midterm_12m"]["pos"], len(rets)),
                pct(st.mean(rets), 1),
                "±3%p 안" if abs(st.mean(rets) - 15) <= 3 else "±3%p 밖"))
    # SPY 총수익으로도
    rowsS = midterm_12m(dsS, pS)
    retsS = [r for *_, r in rowsS]
    out["midterm_12m_spy"] = {"n": len(retsS), "pos": sum(1 for r in retsS if r > 0), "mean": st.mean(retsS)}
    L.append("SPY 총수익(1994~): %d회 중 %d회 상승 · 단순평균 %s\n" % (len(retsS), out["midterm_12m_spy"]["pos"], pct(st.mean(retsS), 1)))

    # ── 무너뜨려 보기
    L.append("\n# 무너뜨려 보기 (결과 나온 뒤 · 보고 전)\n")
    breakers("층 A1 SPY", dsS, pS, rf_daily, a1, cyS, L, out["A1"])
    start_years("층 A1 SPY", dsS, pS, rf_daily, (1993, 2001, 2009), L, out["A1"])
    breakers("층 A2 S&P 500 가격", dsG, pG, rf_daily, a2, cyG, L, out["A2"])
    start_years("층 A2 S&P 500 가격", dsG, pG, rf_daily, (1950, 1970, 1990, 2001, 2009), L, out["A2"])
    breakers("층 A3 QQQ", dsQ, pQ, rf_daily, a3, cyQ, L, out["A3"])
    start_years("층 A3 QQQ", dsQ, pQ, rf_daily, (2001, 2009), L, out["A3"])
    # ④ 현금 판 갈림 요약
    flips = []
    for lab, o in (("A1", out["A1"]), ("A2", out["A2"]), ("A3", out["A3"])):
        if (o["cagr_gap_cash0"] > 0) != (o["cagr_gap_tbill"] > 0):
            flips.append("%s 기준 CAGR" % lab)
        for s, r in o["shift"].items():
            if (r["cash0"] > 0) != (r["tbill"] > 0):
                flips.append("%s 이동 %+d" % (lab, s))
        for y, r in o["start_years"].items():
            if (r["cash0"] - r["hold"] > 0) != (r["tbill"] - r["hold"] > 0):
                flips.append("%s 시작 %d" % (lab, y))
        if "ex2008" in o:
            g0 = o["ex2008"]["규칙·현금0%"]["cagr"] - o["ex2008"]["지수 보유"]["cagr"]
            g1 = o["ex2008"]["규칙·국채"]["cagr"] - o["ex2008"]["지수 보유"]["cagr"]
            if (g0 > 0) != (g1 > 0):
                flips.append("%s 2008 제거" % lab)
    out["cash_flips"] = flips
    L.append("\n**④ 현금 0%% vs 국채에서 «부호»가 갈린 시험**: %s\n" % (" · ".join(flips) if flips else "없음"))

    # ── 층 B
    L.append("\n# 층 B — 우리 규칙과 같은 구간 (⛔ 표본 1개짜리 «묘사» · 판정 아님)\n")
    if no_our:
        L.append("(--no-our: 우리 규칙 곡선 생략)\n")
        our_ds = our_v = None
        from importlib import util as _uu  # noqa
        ROOT = HERE.parents[2]
        out_dir = ROOT / ".cache" / "bt5y" / "out"
    else:
        our_ds, our_v, out_dir = our_rule_curve(12 if quick else 40)
        out["our_seed"] = 12 if quick else 40
    dsLS, pLS = local_index("SPY", out_dir)
    dsLQ, pLQ = local_index("QQQ", out_dir)
    # 검산: 야후 총수익 vs 로컬 총수익 (겹치는 구간 일수익 차이)
    yS = dict(zip(dsS, pS))
    common = [d for d in dsLS if d in yS]
    dif = []
    for i in range(1, len(common)):
        a = pLS[dsLS.index(common[i])] / pLS[dsLS.index(common[i - 1])] - 1
        b = yS[common[i]] / yS[common[i - 1]] - 1
        dif.append(abs(a - b))
    tot_loc = pLS[dsLS.index(common[-1])] / pLS[dsLS.index(common[0])]
    tot_y = yS[common[-1]] / yS[common[0]]
    out["crosscheck_spy"] = {"days": len(dif), "max_abs_daily_diff": max(dif) * 100,
                             "mean_abs_daily_diff": st.mean(dif) * 100,
                             "total_local": (tot_loc - 1) * 100, "total_yahoo": (tot_y - 1) * 100}
    L.append("검산(SPY 로컬 c vs 야후 adjclose, %s~%s %d일): 일수익 차이 최대 %.3f%%p · 평균 %.4f%%p · 누적 %s vs %s\n"
             % (common[0], common[-1], len(dif), max(dif) * 100, st.mean(dif) * 100,
                pct((tot_loc - 1) * 100, 1), pct((tot_y - 1) * 100, 1)))

    def b_table(title, d0, hors):
        L.append("\n## %s — %s ~ %s\n" % (title, d0, D_END))
        arms = []
        if our_ds:
            i = idx_on_or_after(our_ds, d0)
            arms.append(("① 우리 규칙(122b 곡선)", our_ds[i:], [x / our_v[i] for x in our_v[i:]]))
        for nm, ds_, p_ in (("SPY", dsLS, pLS), ("QQQ", dsLQ, pLQ)):
            i = idx_on_or_after(ds_, d0)
            ds2, p2 = ds_[i:], p_[i:]
            r0, cy_ = rule_curve(ds2, p2)
            r1, _ = rule_curve(ds2, p2, rf_daily)
            arms.append(("이 규칙(%s)·현금0%%" % nm, ds2, r0))
            arms.append(("이 규칙(%s)·국채" % nm, ds2, r1))
            arms.append(("%s 보유" % nm, ds2, [x / p2[0] for x in p2]))
            if nm == "SPY":
                L.append("사이클 %d회: %s\n" % (len(cy_), ", ".join(
                    "%d(%s→%s%s)" % (c["mid"], ds2[c["buy"]], ds2[c["sell"]], " 시작 시 보유 중" if c["started_holding"] else "")
                    for c in cy_)))
        o = {}
        L.append("| 팔 | 총수익 | CAGR | 최대 낙폭 | " + " | ".join("%d년 최악 / 마이너스 / 중앙" % h for h in hors) + " |")
        L.append("|---|---:|---:|---:|" + "|".join("---" for _ in hors) + "|")
        for nm, ds_, v_ in arms:
            row = {"start": ds_[0], "end": ds_[-1], "total": (v_[-1] / v_[0] - 1) * 100, "cagr": cagr(ds_, v_), "mdd": mdd(v_)}
            ws = []
            for h in hors:
                s = wstat(windows(ds_, v_, h))
                row["w%d" % h] = s
                ws.append(fmt_w(s) if s else "불가")
            o[nm] = row
            L.append("| %s | %s | %s | %s | %s |" % (nm, pct(row["total"], 1), pct(row["cagr"]), pct(row["mdd"], 1), " | ".join(ws)))
        return o
    out["B1"] = b_table("B1 (두뇌 지정 · 사이클 1회)", B1_START, (3,))
    L.append("\n5·10년 창: 구간이 5.5년이라 **불가**.\n")
    out["B2"] = b_table("B2 (조사 추가 · 122b 곡선 전체 27.4년 · 사이클 7회)", D122, (3, 5, 10))
    L.append("\n🚨 두뇌 의뢰문의 「우리 규칙과 같은 구간 = 2021-02-01~」은 «한국» 표본 구간이다. `122b` 의 우리 규칙 곡선은 «미국» %s~%s 이므로 B2 를 추가했다. B2 도 CI 없음 ⇒ 묘사.\n" % (D122, D_END))

    # ── 검산과 한계
    L.append("\n# 검산과 한계\n")
    if our_ds:
        ref = json.loads((out_dir / "122b-anytime-plus30.json").read_text(encoding="utf-8"))["① 우리 규칙 (①+③)"]
        mine = out["B2"]["① 우리 규칙(122b 곡선)"]
        rows_ = []
        allok = True
        for h in HOR:
            a, b = ref[str(h)], mine["w%d" % h]
            ok_ = all(abs(a[k] - b[k]) < 0.005 for k in ("min", "med", "neg"))
            allok &= ok_
            rows_.append("| %d년 | %s / %.0f%% / %s | %s / %.0f%% / %s | %s |" % (
                h, pct(a["min"]), a["neg"], pct(a["med"]), pct(b["min"]), b["neg"], pct(b["med"]), "일치" if ok_ else "불일치"))
        out["reproduce_122b"] = allok
        L.append("**① 우리 규칙 곡선 재생성 검산** — `122b-anytime-plus30.json` 원본 vs 이 각본(seed %d)\n" % out["our_seed"])
        L.append("| 창 | 122b 원본 최악 / 마이너스 / 중앙 | 이 각본 | |")
        L.append("|---|---|---|---|")
        L.extend(rows_)
        L.append("\n⇒ %s\n" % ("세 창 모두 0.005 안에서 일치 — 122b 곡선이 그대로 재현됐다(양성 대조 통과)" if allok else "🚨 불일치 — B 층의 우리 규칙 수를 쓰면 안 된다"))
    L.append("**② SPY 자료 두 벌 검산** — 야후 adjclose(층 A) vs 로컬 `101-fund-ohlc.json` c(층 B): 일수익 차이 최대 %.3f%%p, 27.4년 누적 %s vs %s. 층 A 와 층 B 의 SPY 수가 소수점 둘째 자리에서 다를 수 있는 까닭은 이것이다(같은 것을 가리키는 수가 둘 — 규약 ⑦ 표시)."
             % (out["crosscheck_spy"]["max_abs_daily_diff"], pct(out["crosscheck_spy"]["total_local"], 1), pct(out["crosscheck_spy"]["total_yahoo"], 1)))
    L.append("\n**③ 한계 (고치지 않고 적는다)**\n")
    L.append("- 국채 팔은 3개월이 아니라 **1개월** 국채(French RF)다. FRED 가 막혀 사전등록 대체안을 썼다. 3개월 금리가 대개 조금 높으므로 «국채» 팔은 약간 «불리»하게 잰 셈이다.")
    L.append("- 층 A2(1950~)는 **가격**지수라 배당이 빠졌다. 규칙은 절반을 현금으로 보내므로 배당 누락은 «지수 보유» 쪽을 더 «불리»하게 만든다 ⇒ A2 의 규칙−지수 차이는 실제(총수익)보다 규칙에 «유리»한 쪽으로 치우쳐 있다. A1(총수익)이 더 정직한 자다.")
    L.append("- 1950~1968 년 선거일과 1972·1976·1980 년 대선일은 뉴욕증권거래소 휴장이라 매도가 «다음 거래일» 종가다(표에 ⚠). 규칙 정의 그대로다.")
    L.append("- 이동 창은 겹친다. 독립 조각은 A1 3년 약 11개 · 10년 약 3개, A2 3년 약 25개 · 10년 약 7개. 「마이너스 0%」는 「0/3」 로 읽는다(`122` 의 한계 ①).")
    L.append("- 세전이다. 규칙은 2년마다 전량 매도하므로 실제로는 지수 보유보다 세금을 «더» 낸다.")
    L.append("- 우리 규칙 곡선은 슬롯5 무작위 순서 %d회의 «중앙 경로» 하나다. CI 없음." % (out.get("our_seed", 0)))
    L.append("- 사이클 2022 의 「현금 2년 지수 수익」은 2026-08-21 에서 잘렸다(다음 매수 2026-11-04 전). 적중 셈에서 뺐다.\n")

    # ── 두 물음 한 줄씩
    L.append("\n# 두 물음 — 한 줄씩\n")
    if our_ds:
        b1, b2 = out["B1"], out["B2"]
        s1 = "2021-02~: 우리 %s vs 규칙(SPY·현금0%%) %s vs 규칙(QQQ·현금0%%) %s" % (
            pct(b1["① 우리 규칙(122b 곡선)"]["cagr"]), pct(b1["이 규칙(SPY)·현금0%"]["cagr"]), pct(b1["이 규칙(QQQ)·현금0%"]["cagr"]))
        s2 = "1999-04~(27.4년): 우리 %s vs 규칙(SPY·현금0%%) %s vs 규칙(QQQ·현금0%%) %s" % (
            pct(b2["① 우리 규칙(122b 곡선)"]["cagr"]), pct(b2["이 규칙(SPY)·현금0%"]["cagr"]), pct(b2["이 규칙(QQQ)·현금0%"]["cagr"]))
        L.append("**「우리 규칙보다 나은가」** → 표본 1개(B1)라 **판정 불가**. 방향만: %s. 참고(B2, CI 없음): %s." % (s1, s2))
    else:
        L.append("**「우리 규칙보다 나은가」** → (--no-our 실행이라 우리 규칙 곡선 없음)")
    a = out["A1"]
    d3 = a["defense"]["3/규칙·현금0%"]
    d5 = a["defense"]["5/규칙·현금0%"]
    d10 = a["defense"]["10/규칙·현금0%"]
    L.append("**「지수를 이기는가」**(A1 SPY 총수익 1993~2026) → CAGR 우위: **%s**(현금0%% %s · 국채 %s) / 손실 방어 우위(최악·마이너스 비율 둘 다): 3년 **%s** · 5년 **%s** · 10년 **%s**. 사이클 적중 %d/%d. A2(가격지수 1950~): CAGR 차이 현금0%% %s · 국채 %s, 적중 %d/%d."
             % ("있음" if a["cagr_gap_tbill"] > 0 else "없음", pct(a["cagr_gap_cash0"]), pct(a["cagr_gap_tbill"]),
                {True: "있음", False: "없음", None: "불가"}[d3], {True: "있음", False: "없음", None: "불가"}[d5],
                {True: "있음", False: "없음", None: "불가"}[d10], a["hit"], a["hit_total"],
                pct(out["A2"]["cagr_gap_cash0"]), pct(out["A2"]["cagr_gap_tbill"]), out["A2"]["hit"], out["A2"]["hit_total"]))

    (DATA / "273-election-cycle.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (RES / "273-election-cycle.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print("\n저장: data/273-election-cycle.json · results/273-election-cycle.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

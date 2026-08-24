# -*- coding: utf-8 -*-
"""26 · **「같은 유니버스 등가중」 벤치마크** — 한국·미국을 **한 함수**로 낸다 (M37-A).

두 시장을 같은 코드로 돌리는 게 요점이다. 규칙이 갈리면 결과가 무엇이든 오독된다.

사전등록 (두뇌 세션 확정)
-------------------------
**어느 쪽도 주지표가 아니다. 네 팔을 전부 대등하게 낸다.**
| | 일별 재조정 | 연 1회 재조정(매수보유) |
|---|---|---|
| 유동성 필터 적용 | O | O |
| 필터 없음(전 종목) | O | O |
결론은 **두 판 모두에서 성립할 때만** 쓴다. 갈리면 **그 갈림 자체가 결론**이다
(무필터 판에는 1,300원 환산이 전혀 안 들어가므로, 두 판이 일치하면 환율이
답을 만든 게 아님이 자동 증명된다).

**청소 규약 사다리** — 헤드라인이 흔들리면 결과가 아니라 한 건이다
------------------------------------------------------------------
`none` 손 안 댐 / `harness` 하네스 규약 / `cap100` |r|>100% 제외 /
`cap31` |r|>31% 제외 / `drop1..5` 가장 크게 기여한 관측 1~5개 제외.

🚨 **하네스 규약을 정확히 옮긴다 — 「제외」가 아니다.**
`canslim_lib/pdata_series.py:94` 는 `abs(fltRt) > 100` 이면 그 관측을 **버리지 않고**
**비수정 종가비로 «대체»**한다. 그래서 `harness` 는 대체판이고 `cap100` 이 제외판이다.
**둘은 다른 값이다.** 미국 로더에는 대응 가드가 **없다**(그 사실 자체가 G3′ ⑤의 항목).

기타 규약
---------
- 유니버스 = 하네스가 쓰는 그것. 한국: KOSPI·KOSDAQ · 스팩/리츠/ETF/ETN/인프라/우선주
  제외 · 외국법인 9xxxxx 제외. 미국: us_loader 기본판(보통주·3거래소·SPAC 제외).
- 유동성 필터 = 하네스와 같은 규칙: 50일 평균 거래대금 >= 5억원, 표본 25일 미만이면
  부적격(avg_turnover_asof 와 같게 **당일 포함**).
- 수익률은 **수정주가 기준**. 한국 fltRt, 미국 Sharadar close(분할 조정·배당 미조정).
  **closeadj 는 쓰지 않는다.**
- 🚨 **상장 첫날은 수익률에 넣지 않는다.** 지수 보유자는 공모 배정 없이는 못 먹는다.
  한국 실측: 넣으면 519건(평균 +29.7% · 최대 +300.0% 「따따블」)이 **+9.09% → +16.18%** 로 민다.
- **상폐**: 마지막 거래일까지 포함, 그 다음 날부터 분모에서 제외. **-100% 처리 없음**
  (M&A 프리미엄 상폐가 섞여 있다). 매수보유 팔은 사라진 평가액을 남은 종목에 비례 배분.
- 비용 없다.

⚠️ **일별 재조정은 호가 튐을 수익으로 수확한다**(소형주가 많을수록 크다) — 미국에 마이크로캡이
   더 많으니 이 부풀림은 **미국 쪽에 더 크게 실린다**. **두 팔의 차이가 곧 부풀림 크기**다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/26-eqw.py kr|us
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / ".cache" / "bt5y" / "out"

START, END = "2021-02-01", "2026-08-21"
MIN_TURNOVER_EOK = 5.0
TURNOVER_WINDOW = 50
MIN_SAMPLE = TURNOVER_WINDOW // 2
USD_KRW = 1300.0
RUNGS = ("none", "harness", "cap100", "cap31")
N_DROP = 5

EXCLUDE_KR = re.compile(
    "스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|[0-9]우$|우$|우\\(전환\\)|우B\\(전환\\)")
FOREIGN_KR = re.compile("^9[0-9]{5}$")


def clean(rung, prim, fallb):
    """사다리 한 칸의 수익률. None 이면 그날 그 종목은 안 센다."""
    if prim is None:
        return None
    if rung == "none":
        return prim
    if rung == "harness":                    # 대체(제외 아님) — 하네스와 같게
        return prim if abs(prim) <= 1.0 else fallb
    if rung == "cap100":
        return None if abs(prim) > 1.0 else prim
    if rung == "cap31":
        return None if abs(prim) > 0.31 else prim
    raise ValueError(rung)


# -- 시장별 공급기 -----------------------------------------------------------
# (날짜, {code: (ret_주, ret_대체, 거래대금_억원, 이름)}) 를 날짜 오름차순으로

def feed_kr():
    P = ROOT / ".cache" / "pdata"
    s, e = START.replace("-", ""), END.replace("-", "")
    prev = {}
    for p in sorted(x for x in P.glob("price_*.json") if s <= x.stem[6:] <= e):
        d = p.stem[6:]
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        day, cur = {}, {}
        for code, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ") or FOREIGN_KR.match(code):
                continue
            nm = r.get("itmsNm") or ""
            if EXCLUDE_KR.search(nm):
                continue
            try:
                c = float(r.get("clpr"))
            except (TypeError, ValueError):
                continue
            if not (c > 0):
                continue
            cur[code] = c
            pc = prev.get(code)
            try:
                f = float(r.get("fltRt"))
            except (TypeError, ValueError):
                f = None
            if f is not None and f != f:
                f = None
            prim = (f / 100.0) if (f is not None and pc is not None) else None
            fallb = (c / pc - 1) if (pc and pc > 0) else None
            tv = r.get("trPrc_eok")
            day[code] = (prim, fallb, float(tv) if tv is not None else 0.0, nm)
        prev = cur
        yield "%s-%s-%s" % (d[:4], d[4:6], d[6:]), day


def feed_us():
    """🚨 날짜별 dict 를 통째로 만들지 않는다.

    6.2M 행을 `{날짜: {코드: 튜플}}` 로 물질화하면 로더(실측 peak 2.87GB) 위에
    1.5~2GB 가 더 얹혀 RAM 규약에 걸린다. 종목마다 **커서**를 두고 달력을 훑으면
    한 번에 하루치만 들고 있으면 된다(연산은 1,396 × 5,700 = 8M 회로 싸다).
    """
    import us_loader
    print("Sharadar 적재 ...", flush=True)
    _u, _t, full, _m = us_loader.build_all(START, END, "base", USD_KRW)
    print("  시계열 %d종목" % len(full), flush=True)
    meta = us_loader.load_tickers("base")
    items = [(c, s["dates"], s["closes"], s["volumes"],
              (meta.get(c) or {}).get("name") or c) for c, s in full.items()]
    cal = sorted({d for _c, ds, _cl, _v, _n in items for d in ds})
    ptr = [0] * len(items)
    for d in cal:
        day = {}
        for k, (c, ds, cl, vo, nm) in enumerate(items):
            i = ptr[k]
            if i < len(ds) and ds[i] == d:
                r = (cl[i] / cl[i - 1] - 1) if (i > 0 and cl[i - 1] > 0) else None
                # 미국엔 fltRt 같은 별도 등락률이 없다 → 주·대체가 같은 값이다.
                day[c] = (r, r, cl[i] * vo[i] * USD_KRW / 1e8, nm)
                ptr[k] = i + 1
        yield d, day


# -- 공통 계산 ---------------------------------------------------------------

def core(stream):
    hist = {}
    seen_last = {}
    names = {}
    arms = [(r, a) for r in RUNGS for a in ("filt", "all")]
    day_sum = {k: [] for k in arms}          # (date, 합, 수)
    pos = {k: {} for k in arms}
    bh = {k: [] for k in arms}
    val = {k: 1.0 for k in arms}
    members = {"filt": [], "all": []}
    top = []                                 # (|기여|, r, code, date, name) — none 판
    year = None
    date = None
    n_days = 0
    for date, day in stream:
        n_days += 1
        elig = set()
        for c, (_p, _f, tv, nm) in day.items():
            h = hist.get(c)
            if h is None:
                h = hist[c] = deque(maxlen=TURNOVER_WINDOW)
            h.append(tv)
            if len(h) >= MIN_SAMPLE and sum(h) / len(h) >= MIN_TURNOVER_EOK:
                elig.add(c)
            seen_last[c] = date
            names[c] = nm
        newyear = year != date[:4]
        pools = {"filt": elig, "all": set(day)}
        for a in ("filt", "all"):
            members[a].append(len(pools[a]))
        for rung, a in arms:
            pool = pools[a]
            acc, n = 0.0, 0
            for c in pool:
                v = clean(rung, day[c][0], day[c][1])
                if v is None:
                    continue
                acc += v
                n += 1
                # 🚨 팔마다 편입 종목이 다르므로 **팔별로** 최대 기여를 따로 모은다.
                #    (한 팔에서 고른 관측을 다른 팔에서 빼면 그 팔엔 없던 걸 빼게 된다.)
                if rung == "none" and abs(v) > 3.0:
                    top.append((abs(v), v, c, date, day[c][3], a))
            day_sum[(rung, a)].append((date, acc, n))
            # 연 1회 재조정
            P = pos[(rung, a)]
            gone = [c for c in P if c not in day]
            if gone:
                freed = sum(P.pop(c) for c in gone)
                tot = sum(P.values())
                if tot > 0:
                    for c in list(P):
                        P[c] += freed * P[c] / tot
            for c in list(P):
                v = clean(rung, day[c][0], day[c][1])
                if v is not None:
                    P[c] *= (1 + v)
            if newyear and pool:
                tv2 = sum(P.values()) or val[(rung, a)]
                P.clear()
                for c in pool:
                    P[c] = tv2 / len(pool)
            val[(rung, a)] = sum(P.values()) or val[(rung, a)]
            bh[(rung, a)].append((date, val[(rung, a)]))
        if newyear:
            year = date[:4]
    top.sort(key=lambda x: -x[0])
    return {"day_sum": day_sum, "bh": bh, "members": members, "top": top[:120],
            "seen_last": seen_last, "n_days": n_days, "last_date": date}


def curve_of(rows):
    eq, out = 1.0, []
    for d, s, n in rows:
        eq *= (1 + (s / n if n else 0.0))
        out.append((d, eq))
    return out


def total(rows):
    return (curve_of(rows)[-1][1] - 1) * 100


def drop_k(rows, drops):
    """지정한 (date, r) 관측들을 빼고 다시 누적한다."""
    byd = {}
    for d, r in drops:
        byd.setdefault(d, []).append(r)
    eq = 1.0
    for d, s, n in rows:
        if d in byd:
            k = byd[d]
            s -= sum(k)
            n -= len(k)
        eq *= (1 + (s / n if n else 0.0))
    return (eq - 1) * 100


def mdd(curve):
    peak, m = 0.0, 0.0
    for _d, v in curve:
        peak = max(peak, v)
        m = min(m, v / peak - 1)
    return m * 100


def by_year(rows):
    y = {}
    for d, s, n in rows:
        y.setdefault(d[:4], []).append(s / n if n else 0.0)
    o = {}
    for k, v in y.items():
        p = 1.0
        for r in v:
            p *= (1 + r)
        o[k] = round((p - 1) * 100, 2)
    return o


def main():
    mkt = sys.argv[1] if len(sys.argv) > 1 else "kr"
    R = core(feed_kr() if mkt == "kr" else feed_us())
    ds, bh = R["day_sum"], R["bh"]
    print("", flush=True)
    print("=" * 78, flush=True)
    print("%s 같은-유니버스 등가중 · 거래일 %d · 마지막 %s"
          % (mkt.upper(), R["n_days"], R["last_date"]), flush=True)
    print("=" * 78, flush=True)
    print("하루 평균 편입 — 필터 %.0f · 무필터 %.0f"
          % (st.mean(R["members"]["filt"]), st.mean(R["members"]["all"])), flush=True)
    print("", flush=True)
    print("%-9s %14s %14s %14s %14s" % ("청소 규약", "필터·일별", "필터·연1회",
                                        "무필터·일별", "무필터·연1회"), flush=True)
    res = {}
    for rung in RUNGS:
        row = []
        for a in ("filt", "all"):
            row.append(total(ds[(rung, a)]))
            row.append((bh[(rung, a)][-1][1] - 1) * 100)
        res[rung] = row
        print("%-9s %13.2f%% %13.2f%% %13.2f%% %13.2f%%"
              % (rung, row[0], row[1], row[2], row[3]), flush=True)
    print("", flush=True)
    print("**drop1~%d — 가장 크게 기여한 관측을 하나씩 뺀다** (none 판 · **팔마다 따로 선정**)"
          % N_DROP, flush=True)
    picks = {a: [(t[3], t[1]) for t in R["top"] if t[5] == a][:N_DROP]
             for a in ("filt", "all")}
    dropres = {}
    for k in range(1, N_DROP + 1):
        v_filt = drop_k(ds[("none", "filt")], picks["filt"][:k])
        v_all = drop_k(ds[("none", "all")], picks["all"][:k])
        dropres[k] = (v_filt, v_all)
        print("  drop%d  필터·일별 %8.2f%%   무필터·일별 %8.2f%%" % (k, v_filt, v_all),
              flush=True)
    print("", flush=True)
    print("**최대 기여 관측 상위 %d (이름으로)**" % N_DROP, flush=True)
    for a in ("filt", "all"):
        print("  [%s]" % ("유동성 필터 통과" if a == "filt" else "무필터"), flush=True)
        for row in [t for t in R["top"] if t[5] == a][:N_DROP]:
            print("   %-8s %-26s %s  **%+.1f%%**"
                  % (row[2], (row[4] or "")[:26], row[3], row[1] * 100), flush=True)
    print("", flush=True)
    print("최대낙폭 (none · 일별) — 필터 %.2f%% · 무필터 %.2f%%"
          % (mdd(curve_of(ds[("none", "filt")])), mdd(curve_of(ds[("none", "all")]))),
          flush=True)
    print("연도별 (harness · 무필터 · 일별): %s"
          % by_year(ds[("harness", "all")]), flush=True)
    last, end = R["seen_last"], R["last_date"]
    deli = [c for c, d in last.items() if d < end]
    print("", flush=True)
    print("상폐(창 끝 전 마지막 거래일) **%d / %d = %.1f%%** — 마지막날까지 포함, -100%% 처리 없음"
          % (len(deli), len(last), len(deli) / len(last) * 100), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("26-eqw-%s.json" % mkt)).write_text(json.dumps({
        "market": mkt, "n_days": R["n_days"], "last_date": end,
        "avg_members": {a: st.mean(R["members"][a]) for a in ("filt", "all")},
        "ladder": {r: {"filt_daily": res[r][0], "filt_bh": res[r][1],
                       "all_daily": res[r][2], "all_bh": res[r][3]} for r in RUNGS},
        "drop": {("drop%d" % k): {"filt_daily": v[0], "all_daily": v[1]}
                 for k, v in dropres.items()},
        "top_contributors": [{"code": t[2], "name": t[4], "date": t[3],
                              "ret_pct": t[1] * 100, "arm": t[5]}
                             for t in R["top"][:40]],
        "mdd": {"filt": mdd(curve_of(ds[("none", "filt")])),
                "all": mdd(curve_of(ds[("none", "all")]))},
        "by_year_harness_all": by_year(ds[("harness", "all")]),
        "n_delisted": len(deli), "n_codes": len(last),
        "curve_harness_all": curve_of(ds[("harness", "all")]),
        "curve_harness_filt": curve_of(ds[("harness", "filt")]),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("저장: .cache/bt5y/out/26-eqw-%s.json" % mkt, flush=True)


if __name__ == "__main__":
    main()

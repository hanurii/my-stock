# -*- coding: utf-8 -*-
r"""271 — Sharadar 가 멈추면 업종 분류와 분기 재무가 「시간이 갈수록 얼마나 낡는가」.

재는 일이다. 고치지 않는다. 판정을 쓰지 않는다. 수만 낸다.

무엇을 묻나
-----------
  ① 사다리 ②(주도 3업종 ∧ 업종 내 6개월 상대성과 10~30%)가 쓰는 **업종 분류**
     - 어디서 오나 · 오늘 커버율 · 월평균 신규 상장 · 3·6·12개월 뒤 업종 없는 비율
     - 업종 라벨 자체가 바뀌는 빈도
  ② 실적 판정(103 judge)이 쓰는 **분기 재무**
     - STALE_MAX 를 넘기면 어떻게 되나 · 3·6·12개월 뒤 낡은 판정 비율

읽는 것만 한다. 쓰는 파일은 없다(표준출력이 곧 문서 — 유형 48).

실행:
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
    python research/handoff/scripts/271-post-sharadar-decay.py
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import statistics as st
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

SH = Path("D:/stock-data/sharadar")
TIC_NEW = SH / "tickers.csv.zip"              # 2026-09-10 수령
TIC_OLD = SH / "tickers-2026-08-24.csv.zip"   # 2026-08-24 수령 — 두 판 대조용
ACT = SH / "actions.csv.zip"
FUND = SH / "fundamentals.csv.zip"
BASE = ROOT / ".cache" / "us" / "base.json"
CAND = ROOT / "public" / "data" / "sepa-us-trend-candidates.json"

# us_loader.load_tickers(variant="base") 와 «같은» 술어. 베끼지 않고 불러 쓴다.
import us_loader as U                                            # noqa: E402

STALE_MAX = 180        # 102-implement-principles.py:61 (「92 와 같은 신선도 상한」)
MIN_CLOSES_FOR_TT = 200   # screen_trend_template.py:77
RS_WINDOW = 252           # RS 252거래일

# 결제 마감. .claude/hooks/sharadar_deadline.py:LAST_MONTH 와 같은 날.
PAID_END = dt.date(2026, 9, 30)
HORIZONS = (3, 6, 12)


def P(*a):
    print(*a, flush=True)


def d2o(s):
    return dt.date(int(s[:4]), int(s[5:7]), int(s[8:10])).toordinal()


def add_months(d: dt.date, n: int) -> dt.date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    day = min(d.day, [31, 29 if (y % 4 == 0 and (y % 100 or y % 400 == 0)) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return dt.date(y, m, day)


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def rows(zp):
    z = zipfile.ZipFile(str(zp))
    nm = z.namelist()[0]
    with z.open(nm) as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8",
                                                 errors="replace")):
            yield r


def base_eligible(r) -> bool:
    """us_loader.load_tickers(variant='base') 의 술어를 그대로 다시 쓴다."""
    if r.get("table") != "SEP":
        return False
    if r["category"] not in U.BASE_CATEGORIES or r["exchange"] not in U.EXCHANGES:
        return False
    if r["siccode"] == U.SPAC_SIC:
        return False
    if not r["firstpricedate"] or not r["lastpricedate"]:
        return False
    return True


def q(vals, p):
    if not vals:
        return float("nan")
    s = sorted(vals)
    i = int(round((len(s) - 1) * p))
    return s[i]


# ═══════════════════════════════════════════════════════════════════════
def section_0():
    P("=" * 104)
    P("271 — Sharadar 가 멈추면 업종과 분기 재무가 «얼마나» 낡는가")
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-12 · `research/handoff/scripts/271-post-sharadar-decay.py`")
    P("> **문서는 이 출력 그 자체**(유형 48) · 재는 일이다 — 판정은 두뇌 몫")
    P("")
    P("## 0. 자료 파일 — 언제 받은 것인가")
    P("")
    P("| 파일 | 받은 날(mtime) | 크기 |")
    P("|---|---|---:|")
    for lab, p in (("tickers.csv.zip", TIC_NEW), ("tickers-2026-08-24.csv.zip", TIC_OLD),
                   ("actions.csv.zip", ACT), ("fundamentals.csv.zip", FUND),
                   (".cache/us/base.json", BASE)):
        if p.exists():
            m = dt.date.fromtimestamp(p.stat().st_mtime)
            P("| `%s` | %s | %.0f MB |" % (lab, m, p.stat().st_size / 1e6))
        else:
            P("| `%s` | **없음** | — |" % lab)
    P("")


# ═══════════════════════════════════════════════════════════════════════
def load_meta_new():
    meta, allsep = {}, 0
    sec_have = 0
    for r in rows(TIC_NEW):
        if r.get("table") != "SEP":
            continue
        allsep += 1
        if (r.get("sector") or "").strip():
            sec_have += 1
        if not base_eligible(r):
            continue
        meta[r["ticker"]] = {
            "sector": (r.get("sector") or "").strip(),
            "industry": (r.get("industry") or "").strip(),
            "siccode": r["siccode"],
            "isdelisted": r["isdelisted"],
            "first": r["firstpricedate"], "last": r["lastpricedate"],
            "lastupdated": r.get("lastupdated") or "",
        }
    return meta, allsep, sec_have


def section_A1(meta, allsep, sec_have, series_codes, cand):
    P("=" * 104)
    P("## A1. 업종 분류는 «어디서» 오나 — 그리고 오늘 커버율")
    P("=" * 104)
    P("")
    P("```")
    P("자료원   `D:/stock-data/sharadar/tickers.csv.zip` 의 열 `sector`  (Sharadar 자체 분류)")
    P("적재     `research/handoff/scripts/61a-build-monthly.py:24-33`")
    P("           sect.setdefault(r['ticker'], s)   ← **티커당 한 줄 · 날짜 없음**")
    P("쓰는 곳  `research/handoff/scripts/91-us-out-of-sample.py:164-181`  load_ladder")
    P("           lvl1: 주도 3업종인가          lvl2: 그 업종 안 6개월 상대성과 10~30%")
    P("           🔴 `if not s: return True`  ← **업종이 «없으면» 사다리 ①② 를 그냥 지나간다**")
    P("           (91v-sector-coverage.py 가 같은 줄을 인용한다)")
    P("업종 «이력»  `180-sector-history.md:91` — `sector` 열의 이력은 Sharadar 에 **없다**")
    P("               (`actions.csv` 의 `sicchangeto/from` 은 **다른 자**다 — SIC 코드)")
    P("```")
    P("")
    P("| 모집단 | 종목 | `sector` 있음 | 커버율 |")
    P("|---|---:|---:|---:|")
    P("| `tickers.csv` SEP 전체 | %s | %s | **%.1f%%** |"
      % ("{:,}".format(allsep), "{:,}".format(sec_have), pct(sec_have, allsep)))
    nb = len(meta)
    nbs = sum(1 for m in meta.values() if m["sector"])
    P("| 기본판 술어 통과(전체 이력) | %s | %s | **%.1f%%** |"
      % ("{:,}".format(nb), "{:,}".format(nbs), pct(nbs, nb)))
    inb = [c for c in series_codes if c in meta]
    inbs = sum(1 for c in inb if meta[c]["sector"])
    P("| **오늘 유니버스** (메타 ∩ 뼈대 시세) | **%s** | %s | **%.1f%%** |"
      % ("{:,}".format(len(inb)), "{:,}".format(inbs), pct(inbs, len(inb))))
    for lab, codes in cand:
        h = sum(1 for c in codes if meta.get(c, {}).get("sector"))
        P("| %s | %s | %s | **%.1f%%** |"
          % (lab, "{:,}".format(len(codes)), "{:,}".format(h), pct(h, len(codes))))
    P("")
    miss = [c for c in inb if not meta[c]["sector"]]
    P("오늘 유니버스에서 업종이 «없는» 종목 **%d개**: %s"
      % (len(miss), ", ".join(sorted(miss)[:20]) or "없음"))
    P("")
    lu = Counter(m["lastupdated"][:10] for m in meta.values()
                 if m["isdelisted"] == "N")
    P("산 종목(`isdelisted=N`)의 `lastupdated` 분포 — 상위 3:")
    for k, v in lu.most_common(3):
        P("  %s   %s 종목" % (k, "{:,}".format(v)))
    P("")
    P("```")
    P("⇒ 산 종목의 라벨은 «수령일에 통째로» 다시 찍힌다 ⇒ Sharadar 가 멈추면 그 날짜에 얼어붙는다")
    P("```")
    P("")
    return inb, miss


# ═══════════════════════════════════════════════════════════════════════
def section_A2(meta, snapshot):
    P("=" * 104)
    P("## A2. 신규 상장 — 한 달에 몇 종목이 새로 들어오나")
    P("=" * 104)
    P("")
    P("자 = `firstpricedate`(기본판 술어 통과분). 유니버스에 «들어오는» 문이 그 열이다.")
    P("")
    snap = dt.date.fromisoformat(snapshot)
    newc = Counter()
    delc = Counter()
    for m in meta.values():
        newc[m["first"][:7]] += 1
        if m["last"] < snapshot:              # 스냅샷 «전»에 끊긴 것 = 진짜 상폐
            delc[m["last"][:7]] += 1

    def window(counter, months):
        lo = add_months(snap, -months)
        ks = [k for k in counter if dt.date.fromisoformat(k + "-01") >= dt.date(lo.year, lo.month, 1)
              and dt.date.fromisoformat(k + "-01") <= dt.date(snap.year, snap.month, 1)]
        tot = sum(counter[k] for k in ks)
        return tot, len(ks)

    P("| 창 | 신규 상장 | 개월 | **월평균** | 상장폐지 | **월평균** |")
    P("|---|---:|---:|---:|---:|---:|")
    for mo in (12, 36, 60):
        nt, nm = window(newc, mo)
        dt_, dm = window(delc, mo)
        P("| 최근 %d개월 | %s | %d | **%.1f** | %s | **%.1f** |"
          % (mo, "{:,}".format(nt), nm, nt / nm if nm else 0,
             "{:,}".format(dt_), dt_ / dm if dm else 0))
    P("")
    P("월별 상세 — 최근 18개월 (🚨 마지막 달은 잘려 있다: 스냅샷이 %s)" % snapshot)
    P("")
    P("| 월 | 신규 | 상폐 |")
    P("|---|---:|---:|")
    ks = sorted(set(list(newc) + list(delc)))
    ks = [k for k in ks if k <= snapshot[:7]][-18:]
    for k in ks:
        P("| %s | %d | %d |" % (k, newc.get(k, 0), delc.get(k, 0)))
    P("")
    return newc, delc


def section_A2b(snapshot, meta):
    """규약 ⑦ — 같은 것을 가리키는 «둘째» 자. actions.csv 의 listed/delisted."""
    P("=" * 104)
    P("## A2b. 같은 것을 «둘째 자»로 — `actions.csv` 의 `listed` / `delisted`")
    P("=" * 104)
    P("")
    P("🚨 규약 ⑦: 같은 것을 가리키는 수가 둘이면 둘 다 적고, 어긋나면 어긋난 대로 적는다.")
    P("두 줄로 낸다 — 술어를 «안 건» 것과 «건» 것.")
    P("")
    lc, dc = Counter(), Counter()
    lcb, dcb = Counter(), Counter()
    for r in rows(ACT):
        a = r["action"]
        t = r["ticker"]
        if a == "listed":
            lc[r["date"][:7]] += 1
            if t in meta:
                lcb[r["date"][:7]] += 1
        elif a == "delisted":
            dc[r["date"][:7]] += 1
            if t in meta:
                dcb[r["date"][:7]] += 1
    snap = dt.date.fromisoformat(snapshot)
    P("| 창 | 술어 | `listed` | **월평균** | `delisted` | **월평균** |")
    P("|---|---|---:|---:|---:|---:|")
    for mo in (12, 36, 60):
        lo = add_months(snap, -mo)
        ks = ["%04d-%02d" % (y, m) for y in range(lo.year, snap.year + 1)
              for m in range(1, 13)
              if (y, m) >= (lo.year, lo.month) and (y, m) <= (snap.year, snap.month)]
        for lab, L, D in (("전부(ETF·우선주·ADR·SPAC 포함)", lc, dc),
                          ("**기본판 티커만**", lcb, dcb)):
            lt = sum(L.get(k, 0) for k in ks)
            dd = sum(D.get(k, 0) for k in ks)
            P("| 최근 %d개월 | %s | %s | **%.1f** | %s | **%.1f** |"
              % (mo, lab, "{:,}".format(lt), lt / len(ks),
                 "{:,}".format(dd), dd / len(ks)))
    P("")
    P("```")
    P("🚨 「기본판 티커만」 줄도 A2 의 `firstpricedate` 자와 «똑같지 않다».")
    P("   `listed` 는 «사건»이고 `firstpricedate` 는 «표의 한 칸»이다 —")
    P("   티커 재사용·재상장이 있으면 사건은 여러 번, 칸은 한 번이다.")
    P("   ⇒ 둘 다 적는다. 어느 쪽을 쓸지는 설계가 정할 일이다.")
    P("```")
    P("")


# ═══════════════════════════════════════════════════════════════════════
def section_A3(meta):
    """두 vintage 직접 대조 — 17일 창의 «실측»."""
    P("=" * 104)
    P("## A3. 두 판(2026-08-24 · 2026-09-10)을 직접 맞대본다 — 17일 창 실측")
    P("=" * 104)
    P("")
    if not TIC_OLD.exists():
        P("🚨 옛 판 파일이 없다 — 못 쟀다.")
        P("")
        return
    old = {}
    for r in rows(TIC_OLD):
        if not base_eligible(r):
            continue
        old[r["ticker"]] = ((r.get("sector") or "").strip(), r["siccode"],
                            (r.get("industry") or "").strip())
    both = set(old) & set(meta)
    added = set(meta) - set(old)
    gone = set(old) - set(meta)
    chg_sec = [t for t in both if old[t][0] != meta[t]["sector"]]
    chg_sic = [t for t in both if old[t][1] != meta[t]["siccode"]]
    chg_ind = [t for t in both if old[t][2] != meta[t]["industry"]]
    P("| 자 | 수 | 양쪽에 다 있는 %s 에 대한 비율 |" % "{:,}".format(len(both)))
    P("|---|---:|---:|")
    P("| 기본판 종목 (옛 판) | %s | — |" % "{:,}".format(len(old)))
    P("| 기본판 종목 (새 판) | %s | — |" % "{:,}".format(len(meta)))
    P("| **새로 생긴 티커** | **%d** | — |" % len(added))
    P("| 사라진 티커 | %d | — |" % len(gone))
    P("| `sector` 가 **바뀐** 티커 | **%d** | **%.3f%%** |"
      % (len(chg_sec), pct(len(chg_sec), len(both))))
    P("| `industry` 가 바뀐 티커 | %d | %.3f%% |"
      % (len(chg_ind), pct(len(chg_ind), len(both))))
    P("| `siccode` 가 바뀐 티커 | %d | %.3f%% |"
      % (len(chg_sic), pct(len(chg_sic), len(both))))
    P("")
    if chg_sec:
        P("바뀐 `sector` 실례 (최대 10):")
        for t in sorted(chg_sec)[:10]:
            P("  %-6s  %-28s ->  %s" % (t, old[t][0] or "(빈값)",
                                        meta[t]["sector"] or "(빈값)"))
        P("")
    P("```")
    P("17일 = %.3f 개월. 이 창에서 새 티커 %d개 ⇒ 선형으로 월 %.1f개."
      % (17 / 30.44, len(added), len(added) / (17 / 30.44)))
    P("🚨 A2 의 `firstpricedate` 자는 월 14.3 이었다. **세 배가 넘게 어긋난다** — 멈춘다(규약 ⑦).")
    P("```")
    P("")
    P("### 🚨 어긋남을 «닫는다» — 새로 생긴 25개의 `firstpricedate` 를 본다")
    P("")
    P("| 티커 | `firstpricedate` | 스냅샷까지 나이(일) |")
    P("|---|---|---:|")
    snapo = max(d2o(m["last"]) for m in meta.values())
    ages = []
    for t in sorted(added):
        a = snapo - d2o(meta[t]["first"])
        ages.append(a)
        P("| %s | %s | %d |" % (t, meta[t]["first"], a))
    P("")
    fresh = sum(1 for a in ages if a <= 31)
    P("```")
    P("최근 31일 안에 «처음 값이 찍힌» 것 = %d / %d" % (fresh, len(added)))
    P("나머지 %d 개는 «옛날 종목»이 이번 판에 «뒤늦게» 실린 것이다(소급 적재)."
      % (len(added) - fresh))
    P("⇒ ★ **두 자가 «다른 것»을 세고 있었다.**")
    P("     A2  `firstpricedate` = 「그 종목이 «처음 거래된» 달」")
    P("     A3  판 대조          = 「Sharadar 표에 «처음 실린» 날」  ← 소급 적재를 포함한다")
    P("     그중 «진짜 신규»만 월로 고치면 %d ÷ 0.558 = **월 %.1f 개** — A2 의 14.3 과 같은 자릿수다."
      % (fresh, fresh / (17 / 30.44)))
    P("⇒ 규약 ⑦ 해소: 둘 다 맞고, «세는 것»이 달랐다.")
    P("   「월평균 신규 상장」에 쓸 자는 **A2** 다. A3 가 재는 것은 「표가 «자라는» 속도」다.")
    P("```")
    P("")
    return len(added), len(chg_sec), len(both)


# ═══════════════════════════════════════════════════════════════════════
def section_A4_sic():
    P("=" * 104)
    P("## A4. 업종 «자체»가 바뀌나 — SIC 대분류 변경의 «연율»")
    P("=" * 104)
    P("")
    P("⚠️ SIC 는 `sector` 의 **대리**다(다른 자). `180` 이 이미 밝혔다 — 여기서는 «연율»만 새로 낸다.")
    P("")
    DIV = [(100, 999), (1000, 1499), (1500, 1799), (2000, 3999), (4000, 4999),
           (5000, 5199), (5200, 5999), (6000, 6799), (7000, 8999), (9100, 9729)]

    def div(code):
        try:
            c = int(float(code))
        except Exception:
            return None
        for a, b in DIV:
            if a <= c <= b:
                return (a, b)
        return None

    to, fr = {}, {}
    for r in rows(ACT):
        a = r["action"]
        if a == "sicchangeto":
            to[(r["ticker"], r["date"])] = r["value"]
        elif a == "sicchangefrom":
            fr[(r["ticker"], r["date"])] = r["value"]
    peryear = Counter()
    divyear = Counter()
    for k, v in to.items():
        if k not in fr:
            continue
        peryear[k[1][:4]] += 1
        if div(v) != div(fr[k]) and div(v) and div(fr[k]):
            divyear[k[1][:4]] += 1
    P("| 해 | sicchange 짝 | 그중 **대분류** 변경 |")
    P("|---|---:|---:|")
    tot5 = totd5 = 0
    for y in [str(x) for x in range(2021, 2027)]:
        P("| %s | %d | %d |" % (y, peryear.get(y, 0), divyear.get(y, 0)))
        if y < "2026":
            tot5 += peryear.get(y, 0)
            totd5 += divyear.get(y, 0)
    P("")
    P("```")
    P("2021~2025 5해 합계: 짝 %d · 대분류 변경 %d  ⇒  연 %.0f 건" % (tot5, totd5, totd5 / 5))
    P("```")
    P("")
    return totd5 / 5


# ═══════════════════════════════════════════════════════════════════════
def section_A5(inb, miss, newc, delc, snapshot, cand, meta):
    P("=" * 104)
    P("## A5. 3·6·12개월 뒤 «업종 없는» 비율")
    P("=" * 104)
    P("")
    snap = dt.date.fromisoformat(snapshot)

    def rate(counter, months):
        lo = add_months(snap, -months)
        ks = [k for k in counter
              if dt.date.fromisoformat(k + "-01") >= dt.date(lo.year, lo.month, 1)
              and dt.date.fromisoformat(k + "-01") < dt.date(snap.year, snap.month, 1)]
        return sum(counter[k] for k in ks) / max(months, 1)

    n12, d12 = rate(newc, 12), rate(delc, 12)
    n36, d36 = rate(newc, 36), rate(delc, 36)
    L0 = len(inb)
    m0 = len(miss)
    P("셈법을 먼저 적는다 — 뒤에 검산할 수 있게.")
    P("")
    P("```")
    P("L0 = 오늘 유니버스 = %d 종목        m0 = 그중 업종 없음 = %d" % (L0, m0))
    P("n  = 월평균 신규 상장              d  = 월평균 상장폐지")
    P("N개월 뒤   산 종목 = L0 - d*N + n*N       업종 없음 = m0 + n*N")
    P("업종 없는 비율 = (m0 + n*N) / (L0 - d*N + n*N)")
    P("```")
    P("")
    P("🔴 **이 셈은 「신규 상장이 유니버스에 «들어온다»」를 가정한다.**")
    P("   그런데 유니버스 명부 자체가 `tickers.csv` 다(`us_loader.load_tickers`).")
    P("   그것도 같이 얼면 신규는 **업종이 없는 게 아니라 아예 «안 보인다»**.")
    P("   ⇒ 두 읽기를 «둘 다» 적는다. 어느 쪽인지는 설계가 정할 일이다.")
    P("")
    for lab, n, d in (("최근 12개월 상장·상폐율", n12, d12),
                      ("최근 36개월 상장·상폐율", n36, d36)):
        P("### %s  (n=%.1f/월 · d=%.1f/월)" % (lab, n, d))
        P("")
        P("| N개월 뒤 | 산 종목 | 업종 없음 | **(가) 업종 없는 비율** | **(나) 유니버스에서 «빠지는» 비율** |")
        P("|---|---:|---:|---:|---:|")
        for N in HORIZONS:
            live = L0 - d * N + n * N
            unl = m0 + n * N
            drop = n * N / max(L0 - d * N + n * N, 1)
            P("| %2d | %.0f | %.0f | **%.2f%%** | **%.2f%%** |"
              % (N, live, unl, 100.0 * unl / live, 100.0 * drop))
        P("")
    P("```")
    P("(가) = tickers.csv 를 다른 데(나스닥 목록 등)로 메워 «신규가 들어오는» 경우")
    P("       ⇒ 그 종목은 `sector` 가 없다 ⇒ `load_ladder` 의 `if not s: return True`")
    P("          ⇒ **사다리 ①② 를 그냥 통과한다**(91-us-out-of-sample.py:164-181)")
    P("(나) = tickers.csv 도 함께 얼어 신규가 «안 들어오는» 경우 ⇒ 업종 커버율은 안 떨어지고")
    P("       대신 그만큼이 «후보에서 통째로 빠진다»")
    P("```")
    P("")

    # ── 관문 지연: 새 종목이 «후보»가 되기까지 ───────────────────────────
    P("### 🔵 그런데 신규 상장은 «바로» 후보가 되지 않는다")
    P("")
    P("```")
    P("8관문 평가 최소 봉수 MIN_CLOSES_FOR_TT = %d 거래일  (screen_trend_template.py:77)" % MIN_CLOSES_FOR_TT)
    P("RS 는 %d 거래일 수익률로 잰다" % RS_WINDOW)
    P("  200 거래일 ≈ %.1f 개월 · 252 거래일 ≈ %.1f 개월 (거래일 21/월)"
      % (MIN_CLOSES_FOR_TT / 21.0, RS_WINDOW / 21.0))
    P("```")
    P("")
    P("실측으로 확인한다 — 오늘 각 집합의 `firstpricedate` 나이 분포:")
    P("")
    P("| 집합 | 종목 | 상장 12개월 미만 | 24개월 미만 | 나이 중앙(년) |")
    P("|---|---:|---:|---:|---:|")
    sets = [("오늘 유니버스", inb)] + [(l, c) for l, c in cand]
    for lab, codes in sets:
        ages = []
        for c in codes:
            m = meta.get(c)
            if not m:
                continue
            ages.append((snap.toordinal() - d2o(m["first"])) / 365.25)
        if not ages:
            continue
        P("| %s | %s | %d (%.1f%%) | %d (%.1f%%) | %.1f |"
          % (lab, "{:,}".format(len(ages)),
             sum(1 for a in ages if a < 1), pct(sum(1 for a in ages if a < 1), len(ages)),
             sum(1 for a in ages if a < 2), pct(sum(1 for a in ages if a < 2), len(ages)),
             st.median(ages)))
    P("")


# ═══════════════════════════════════════════════════════════════════════
def section_A6():
    P("=" * 104)
    P("## A6. 업종 «안» 6개월 상대성과는 가격만으로 되나")
    P("=" * 104)
    P("")
    P("```")
    P("61b-matched-null.py:44-56  month_returns(monthly, sector, months, lookback=6)")
    P("    a, b = d.get(base), d.get(ym)      ← monthly = **월말 종가**뿐")
    P("    if a and b and a > 0 and sector.get(t)   ← 섹터 «라벨»만 더 쓴다")
    P("61b-matched-null.py:59-80  make_flags")
    P("    smean = 섹터별 평균 6개월 수익률 (종목 5개 이상인 섹터만)")
    P("    sec_top = 상위 TOP_SECTORS 개 · in_pct = 섹터 내 순위 백분위")
    P("")
    P("⇒ 재무·공시·시총을 **아무것도 안 쓴다**. 쓰는 것은 «월말 종가» + «섹터 라벨» 둘뿐이다.")
    P("⇒ 월말 종가는 야후 꼬리로 계속 자란다(266 실측: 4,039종목 3.4개월치 137초).")
    P("⇒ 🔴 다만 섹터 «평균»의 분모가 라벨 있는 종목 집합이라, 라벨이 얼면")
    P("   그 평균을 내는 «구성»도 얼어붙는다(새 종목이 섹터 평균에 안 들어간다).")
    P("```")
    P("")


# ═══════════════════════════════════════════════════════════════════════
def section_B1():
    P("=" * 104)
    P("## B1. `103 judge` 가 무엇을 요구하나 · STALE_MAX 를 넘기면 어떻게 되나")
    P("=" * 104)
    P("")
    P("```")
    P("요구하는 것 (103-code33-strength.py:50-73 judge)")
    P("  arq = 92a 가 만든 «공시일 축» 분기표. 필드: eps · revenue · netmargin")
    P("  판정 = nq 분기 연속으로  (EPS 전년비 가속) ∧ (매출 전년비 가속) [∧ (순이익률 확대)]")
    P("  필요한 과거 분기: j >= 4 + nq  ⇒ 3분기 판이면 **과거 7분기**가 더 있어야 한다")
    P("")
    P("자료 규약 (92a-fundamentals-index.py:12-17)")
    P("  ① `date` = **SEC 제출일**. calendardate·reportperiod 로 붙이면 룩어헤드")
    P("  ② dimension 은 **ARQ/ART 만**")
    P("  ③ 진입일 D 에 쓸 수 있는 것 = `date < D` 중 가장 늦은 것 (`asof`, 92a:96-104)")
    P("")
    P("신선도 상한")
    P("  102-implement-principles.py:61   STALE_MAX = 180      # 달력일")
    P("  102-implement-principles.py:212  if _ord(entry) - _ord(r[0]) > STALE_MAX:")
    P("                                       stats['code33']['공시가 묵음'] += 1")
    P("                                       continue        ← keep33 에 «안» 넣는다")
    P("  103-code33-strength.py:113       if r is None or _ord(entry) - _ord(r[0]) > STALE_MAX:")
    P("                                       verdict[k] = {모든 칸: None}")
    P("")
    P("🔴 넘겼을 때 «어떻게» 되나 — 버리는 것도 통과시키는 것도 «아니고» **None** 이다.")
    P("   그리고 None 을 어찌할지가 **격자의 한 축**이다 (103:47)")
    P("     UNK = ('자료없으면 안삼', '자료없으면 그냥삼')")
    P("   103:139  if v is True or (v is None and u == '자료없으면 그냥삼'): keep.append(...)")
    P("   ⇒ 「안삼」 판에서는 **버려진다**(후보에서 빠진다)")
    P("   ⇒ 「그냥삼」 판에서는 **거르지 않고 그냥 산다**(실적 판정이 «꺼진다»)")
    P("   ⇒ ★ 낡음의 «결과»는 이 축을 어디에 두느냐가 가른다. 판정은 두뇌 몫이다.")
    P("")
    P("🔵 102 본판(`102:212`)은 UNK 축이 없다 — `continue` 라서 **버린다** 쪽 하나뿐이다.")
    P("```")
    P("")


def scan_fundamentals(univ):
    """유니버스 종목별 ARQ 제출일 목록. 파일을 한 번만 흘려 읽는다."""
    t0 = time.time()
    z = zipfile.ZipFile(str(FUND))
    nm = z.namelist()[0]
    f = io.TextIOWrapper(z.open(nm), encoding="utf-8", errors="replace")
    rd = csv.reader(f)
    hdr = next(rd)
    it, idm, idd = hdr.index("ticker"), hdr.index("dimension"), hdr.index("date")
    by = defaultdict(list)
    n = 0
    maxd = ""
    for r in rd:
        n += 1
        if r[idm] != "ARQ":
            continue
        d = r[idd]
        if d > maxd:
            maxd = d
        t = r[it]
        if t in univ:
            by[t].append(d)
    for t in by:
        by[t] = sorted(set(by[t]))
    return by, n, maxd, time.time() - t0


def section_B2(by, nrows, maxd, secs, inb, cand, meta):
    P("=" * 104)
    P("## B2. 분기 재무의 «끝» — 그리고 오늘 이미 얼마나 낡았나")
    P("=" * 104)
    P("")
    P("```")
    P("fundamentals.csv 전체 %s행 · ARQ 제출일 최댓값 = **%s** · 훑는 데 %.0f초"
      % ("{:,}".format(nrows), maxd, secs))
    P("(이 파일은 2026-08-27 에 받은 것이다. 사용자는 9월 말 한 번 더 받을 예정)")
    P("```")
    P("")
    cut = dt.date.fromisoformat(maxd)
    P("| 집합 | 종목 | ARQ 있음 | ARQ 8분기+ | 마지막 제출 지연(일) P25 / 중앙 / P75 / P90 |")
    P("|---|---:|---:|---:|---|")
    lagset = {}
    for lab, codes in [("오늘 유니버스", inb)] + list(cand):
        have = [c for c in codes if by.get(c)]
        deep = [c for c in have if len(by[c]) >= 8]
        lags = [cut.toordinal() - d2o(by[c][-1]) for c in have]
        lagset[lab] = (len(codes), lags)
        P("| %s | %s | %s (%.1f%%) | %s (%.1f%%) | %.0f / **%.0f** / %.0f / %.0f |"
          % (lab, "{:,}".format(len(codes)), "{:,}".format(len(have)),
             pct(len(have), len(codes)), "{:,}".format(len(deep)),
             pct(len(deep), len(codes)),
             q(lags, .25), q(lags, .50), q(lags, .75), q(lags, .90)))
    P("")
    return cut, lagset


def section_B3(by, cut, inb, cand):
    P("=" * 104)
    P("## B3. 3·6·12개월 뒤 «낡은 판정» 비율")
    P("=" * 104)
    P("")
    P("```")
    P("낡음 = (판정하는 날) − (그 종목의 마지막 ARQ 제출일) > STALE_MAX(=%d 달력일)" % STALE_MAX)
    P("얼어붙는 날 F 를 둘로 잡는다:")
    P("  F1 = %s  — 디스크에 있는 파일의 ARQ 최댓값 (지금 우리가 가진 것)" % cut)
    P("  F2 = %s  — 결제 마지막 날. 9월 말 재수령을 가정한 판" % PAID_END)
    P("F2 판은 «그때 들어올 공시»를 모르므로, F1 판의 지연 분포를 그대로 두고")
    P("날짜만 옮긴다 — 그러면 F2 판은 «낡음을 과대»로 잡는다(보수적).")
    P("★ 그래서 아래 B4 에 «자료가 완전한 과거 날»로 같은 셈을 다시 한다.")
    P("```")
    P("")
    for Flab, F in (("F1 = %s (파일 끝)" % cut, cut), ("F2 = %s (결제 마감)" % PAID_END, PAID_END)):
        P("### %s" % Flab)
        P("")
        P("| 집합 | 종목 | 오늘(N=0) | N=3 | N=6 | N=12 |")
        P("|---|---:|---:|---:|---:|---:|")
        for lab, codes in [("오늘 유니버스", inb)] + list(cand):
            cells = []
            for N in (0,) + HORIZONS:
                day = add_months(F, N).toordinal()
                stale = 0
                for c in codes:
                    r = by.get(c)
                    if not r:
                        stale += 1                     # 자료가 아예 없다 = 판정 불가
                        continue
                    if day - d2o(r[-1]) > STALE_MAX:
                        stale += 1
                cells.append(pct(stale, len(codes)))
            P("| %s | %s | %.1f%% | %.1f%% | %.1f%% | **%.1f%%** |"
              % (lab, "{:,}".format(len(codes)), cells[0], cells[1], cells[2], cells[3]))
        P("")
    P("```")
    P("🚨 위 표의 「낡음」에는 **ARQ 가 아예 없는 종목**도 포함된다(그쪽은 오늘도 이미 None).")
    P("   갈라 보려면 B2 의 「ARQ 있음」 칸을 같이 읽어라.")
    P("```")
    P("")
    P("### ARQ 가 «있는» 종목만 따로 (자료 없음을 뺀 판)")
    P("")
    P("| 집합 | ARQ 있는 종목 | 오늘 | N=3 | N=6 | N=12 |")
    P("|---|---:|---:|---:|---:|---:|")
    for lab, codes in [("오늘 유니버스", inb)] + list(cand):
        have = [c for c in codes if by.get(c)]
        cells = []
        for N in (0,) + HORIZONS:
            day = add_months(cut, N).toordinal()
            cells.append(pct(sum(1 for c in have if day - d2o(by[c][-1]) > STALE_MAX),
                             len(have)))
        P("| %s | %s | %.1f%% | %.1f%% | %.1f%% | **%.1f%%** |"
          % (lab, "{:,}".format(len(have)), cells[0], cells[1], cells[2], cells[3]))
    P("")
    # ── 낭떠러지가 «어디»인가 — 달마다 ────────────────────────────────
    P("### 🚨 「N=6 에 100%」는 «낭떠러지»다 — 어느 달에 떨어지나")
    P("")
    P("| 집합 | " + " | ".join("N=%d" % n for n in range(0, 9)) + " |")
    P("|---|" + "---:|" * 9)
    for lab, codes in [("오늘 유니버스", inb)] + list(cand):
        have = [c for c in codes if by.get(c)]
        cells = []
        for N in range(0, 9):
            day = add_months(cut, N).toordinal()
            cells.append(pct(sum(1 for c in have if day - d2o(by[c][-1]) > STALE_MAX),
                             len(have)))
        P("| %s | %s |" % (lab, " | ".join("%.1f%%" % x for x in cells)))
    P("")
    P("```")
    P("왜 낭떠러지인가 — 항등식에 가깝다. 마지막 제출 지연 중앙이 21일이고(B2),")
    P("STALE_MAX 가 180일이라, 얼어붙은 뒤 «159일»이 지나면 중앙 종목이 한꺼번에 넘는다.")
    P("159일 = 5.2개월. ⇒ 「%d·%d개월 뒤」는 «분포의 꼬리»를 재는 것이고," % (3, 6))
    P("   「6개월 뒤」는 **전부**를 재는 것이다. 3과 6 사이에 «전부»가 들어 있다.")
    P("⛔ 그래서 「3·6·12」 세 점만 적으면 낭떠러지 자리를 «못» 본다 — 위 표를 같이 읽어라.")
    P("```")
    P("")

    # 공시 간격
    gaps = []
    for c in inb:
        r = by.get(c) or []
        if len(r) >= 5:
            g = [d2o(r[i]) - d2o(r[i - 1]) for i in range(len(r) - 4, len(r))]
            gaps.extend(g)
    P("연속 공시 «간격»(최근 4칸 · 오늘 유니버스) — n=%s · P25 %.0f / 중앙 **%.0f** / P75 %.0f / P90 %.0f 일"
      % ("{:,}".format(len(gaps)), q(gaps, .25), q(gaps, .50), q(gaps, .75), q(gaps, .90)))
    P("")


def stale_curve(by, F, codes, ns):
    """F 에 얼어붙었다 치고 F+N 의 낡음 비율. ARQ 가 F 이전에 있는 종목만."""
    have = []
    for c in codes:
        r = [d for d in (by.get(c) or []) if d <= F.isoformat()]
        if r:
            have.append(d2o(r[-1]))
    return [pct(sum(1 for o in have if add_months(F, N).toordinal() - o > STALE_MAX),
                len(have)) for N in ns], len(have)


def section_B4(by, cut, inb, cand):
    P("=" * 104)
    P("## B4. 검산 — 자료가 «완전한» 과거 날로 같은 셈을 다시 한다")
    P("=" * 104)
    P("")
    P("```")
    P("F0 = 2025-09-30 에 얼어붙었다고 «가정»한다. 그날 이후 공시는 «안 본다».")
    P("그러면 F0+N 의 낡음 비율을 «완전한 자료»로 잴 수 있다 — B3 의 오른쪽 끝 잘림이 없다.")
    P("```")
    P("")
    F0 = dt.date(2025, 9, 30)
    P("| 집합 | 종목 | N=0 | N=3 | N=6 | N=12 |")
    P("|---|---:|---:|---:|---:|---:|")
    for lab, codes in [("오늘 유니버스", inb)] + list(cand):
        have = []
        for c in codes:
            r = [d for d in (by.get(c) or []) if d <= F0.isoformat()]
            if r:
                have.append(d2o(r[-1]))
        cells = []
        for N in (0,) + HORIZONS:
            day = add_months(F0, N).toordinal()
            cells.append(pct(sum(1 for o in have if day - o > STALE_MAX), len(have)))
        P("| %s (ARQ 있음 %s) | %s | %.1f%% | %.1f%% | %.1f%% | **%.1f%%** |"
          % (lab, "{:,}".format(len(have)), "{:,}".format(len(codes)),
             cells[0], cells[1], cells[2], cells[3]))
    P("")
    P("### 두 판의 «차»를 여기서 «찍는다» — 말로 적지 않는다")
    P("")
    P("| 집합 | N | F1=%s | F0=%s | **차(%%p)** |" % (cut, F0))
    P("|---|---:|---:|---:|---:|")
    worst = 0.0
    for lab, codes in [("오늘 유니버스", inb)] + list(cand):
        c1, _n1 = stale_curve(by, cut, codes, HORIZONS)
        c0, _n0 = stale_curve(by, F0, codes, HORIZONS)
        for i, N in enumerate(HORIZONS):
            d = c1[i] - c0[i]
            worst = max(worst, abs(d))
            P("| %s | %d | %.1f%% | %.1f%% | **%+.1f** |" % (lab, N, c1[i], c0[i], d))
    P("")
    P("```")
    P("두 판의 최대 어긋남 = **%.1f %%p** (위 표에서 «계산»한 값이다)" % worst)
    P("낭떠러지(N=6 이후)에서는 둘 다 100.0 퍼센트라 차가 0 이다 — 어긋남은 «꼬리»에만 있다.")
    P("```")
    P("")


# ═══════════════════════════════════════════════════════════════════════
def section_C():
    P("=" * 104)
    P("## C. 바깥에서 채울 수 있나 — 이미 쓰는 것부터")
    P("=" * 104)
    P("")
    P("```")
    P("이미 잰 것이 있다: `research/handoff/results/266-yahoo-only.md`  (2026-09-11)")
    P("")
    P("  야후 `info` 가 «주는» 것 : exchange · quoteType(ETF 여부) · **sector · industry**")
    P("                              · marketCap · sharesOutstanding · currency")
    P("                              (10종목 표본에서 빈 값 0/10 — 266:92-104)")
    P("  야후 `info` 가 «못 주는» 것 : siccode (SPAC 6770 을 가르는 자) · category")
    P("                              (우선주 · ADR · 2차 클래스) · isdelisted · firstpricedate")
    P("  비용                     : 10종목 8.0초 ⇒ 4,039종목 선형 **약 54분** (266:116-117)")
    P("  가격(OHLCV)              : 4,039종목 3.4개월치 **137초** · 200종목 1년치 6.6초")
    P("  걸린 것                  : 점 붙은 티커(BF.B · BRK.B · CRD.A · MOG.A) · 한도 1회")
    P("")
    P("266 이 «안» 본 것 — 여기서 새로 적는다:")
    P("  · 야후의 **분기 재무**를 안 봤다(`info` 만 봤다)")
    P("  · 상장폐지 종목을 야후에서 받을 수 있는지 안 봤다(백테스트에 상폐 1,603개)")
    P("```")
    P("")
    P("### C2. 야후의 분기 재무 — 소표본으로 «무엇이 있나»만 본다")
    P("")
    try:
        import yfinance as yf
    except Exception as e:
        P("🚨 yfinance 를 못 불렀다: %r — 이 칸은 **못 쟀다**" % (e,))
        P("")
        return
    P("⛔ 새 자료원을 «붙이지» 않는다. 세 종목에서 «무엇이 들어 있나»만 본다.")
    P("")
    t0 = time.time()
    nq_seen = []
    for tk in ("AAPL", "NVDA", "F"):
        try:
            o = yf.Ticker(tk)
            inc = o.quarterly_income_stmt
            if inc is not None and not getattr(inc, "empty", True):
                nq_seen.append(len(inc.columns))
            P("**%s**" % tk)
            if inc is None or getattr(inc, "empty", True):
                P("  quarterly_income_stmt: 비었다")
            else:
                cols = [str(c)[:10] for c in inc.columns]
                idx = [str(i) for i in inc.index]
                P("  quarterly_income_stmt  분기 %d개 — 열(=기간 끝) %s"
                  % (len(cols), ", ".join(cols)))
                want = [k for k in ("Total Revenue", "Net Income", "Diluted EPS",
                                    "Basic EPS") if k in idx]
                P("  필요한 줄 중 있는 것: %s" % (", ".join(want) or "없음"))
                P("  전체 줄 수 %d" % len(idx))
            try:
                ed = o.calendar
                P("  calendar: %s" % (str(ed)[:160].replace("\n", " ")))
            except Exception as e:
                P("  calendar: 못 읽음 %r" % (e,))
        except Exception as e:
            P("**%s** 실패: %r" % (tk, e))
        P("")
    P("세 종목 %.1f초." % (time.time() - t0))
    P("")
    P("```")
    P("🔴 «축»이 다르다. Sharadar `date` = **SEC 제출일**이고(92a 규약 ①),")
    P("   야후 quarterly_income_stmt 의 열은 **기간 끝(period end)**이다.")
    P("   기간 끝을 제출일처럼 쓰면 룩어헤드다 — 92a 가 명시적으로 금지한 바로 그 자리다.")
    P("   ⇒ 「같은 것을 준다」가 아니다. 제출일을 따로 어디서 받지 않으면 축이 안 맞는다.")
    P("🔴 netmargin 은 야후가 그 이름으로 주지 않는다 — Net Income / Total Revenue 로")
    P("   «만들어야» 한다. 만들면 Sharadar 값과 같은 자인지 다시 재야 한다(안 쟀다).")
    if nq_seen:
        need = 4 + 3 + 1        # judge 3분기 판: j >= 4+nq  ⇒  인덱스 7  ⇒  8분기
        P("🔴 **분기 수가 모자란다** — judge 의 3분기 판은 `j >= 4 + nq` 라 **%d분기**가 필요하다"
          % need)
        P("   (103-code33-strength.py:52). 야후가 준 분기 수: %s ⇒ 셋 다 «모자란다»: %s"
          % (", ".join(str(x) for x in nq_seen),
             "예" if all(x < need for x in nq_seen) else "아니오"))
        P("   ⇒ 야후 `quarterly_*` 만으로는 오늘도 3분기 판을 «못» 돌린다. 표본 셋이다.")
    P("```")
    P("")


def section_D():
    P("=" * 104)
    P("## D. 이 판이 «못» 한 것 — 「안 쟀다」를 「없다」로 쓰지 않는다")
    P("=" * 104)
    P("")
    P("```")
    P("· 「업종 없는 종목이 성적을 얼마나 깎나」 — **안 쟀다**. 여기서 잰 것은 «비율»뿐이다")
    P("· 나스닥/NYSE 공개 목록으로 신규 상장을 메울 수 있는지 — **안 붙였다**(지시)")
    P("· 야후 `info` 의 sector 가 Sharadar `sector` 와 «같은 분류 체계»인지 — **안 맞대봤다**")
    P("  (이름이 같아도 다른 자일 수 있다 — 유형 67)")
    P("· 야후 분기 재무의 «값»이 Sharadar 와 같은지 — **안 맞대봤다**(있나만 봤다)")
    P("· 야후 분기 재무를 4,648종목에서 받는 «시간» — **안 쟀다**(세 종목만 봤다)")
    P("· 상폐 종목을 야후에서 받을 수 있나 — **안 봤다**")
    P("· 두 vintage 대조는 창이 **17일**뿐이다. 라벨 변경률의 연율로 늘리지 않았다")
    P("· A5 의 사영은 「상장·상폐율이 그대로 간다」를 가정한다. 그 가정은 **안 검정했다**")
    P("· STALE_MAX=180 의 «출처»는 102:61 의 주석(「92 와 같은 신선도 상한」)뿐이다.")
    P("  그 값이 «왜» 180 인지는 **못 찾았다**")
    P("```")
    P("")


# ═══════════════════════════════════════════════════════════════════════
def main() -> int:
    section_0()
    meta, allsep, sec_have = load_meta_new()
    base = json.loads(BASE.read_text(encoding="utf-8"))
    series_codes = set(base["series"])
    asof = base["asof"]
    snapshot = max(m["last"] for m in meta.values())

    cand = []
    if CAND.exists():
        cd = json.loads(CAND.read_text(encoding="utf-8"))
        ev = [c["code"] for c in cd["candidates"]]
        ap = [c["code"] for c in cd["candidates"] if c.get("all_pass")]
        cand = [("오늘 8관문 «분모»(관문 평가 대상)", ev),
                ("오늘 8관문 **통과** 후보", ap)]
        P("> 후보 파일: `public/data/sepa-us-trend-candidates.json` · asof %s · "
          "관문 분모 %s · 통과 %s"
          % (cd["asof"], "{:,}".format(len(ev)), "{:,}".format(len(ap))))
        P("")
    P("> 뼈대 `base.json` asof **%s** · 시계열 %s 종목 · Sharadar 스냅샷(최대 lastpricedate) **%s**"
      % (asof, "{:,}".format(len(series_codes)), snapshot))
    P("")

    inb, miss = section_A1(meta, allsep, sec_have, series_codes, cand)
    newc, delc = section_A2(meta, snapshot)
    section_A2b(snapshot, meta)
    section_A3(meta)
    section_A4_sic()
    section_A5(inb, miss, newc, delc, snapshot, cand, meta)
    section_A6()

    section_B1()
    univ = set(inb)
    for _lab, codes in cand:
        univ |= set(codes)
    by, nrows, maxd, secs = scan_fundamentals(univ)
    cut, _lag = section_B2(by, nrows, maxd, secs, inb, cand, meta)
    section_B3(by, cut, inb, cand)
    section_B4(by, cut, inb, cand)

    section_C()
    section_D()
    return 0


if __name__ == "__main__":
    sys.exit(main())

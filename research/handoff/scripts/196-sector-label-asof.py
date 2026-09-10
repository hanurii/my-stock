# -*- coding: utf-8 -*-
r"""196 — **`61` 의 «업종 라벨»이 «시점» 자료인가** · 두뇌 의뢰 2026-09-06

  🚨 **왜 «급»한가** — `61`(주도3업종 ∧ 그룹내주도주)은 **«우리 정본 헤드라인»의 «일부»**다.
     `61a-build-monthly.py:24-33` 이 `tickers.csv` 의 `sector` 를 **티커당 «하나»**로 적재한다
     (`sect.setdefault(ticker, s)`) ⇒ **«날짜»가 «없다** ⇒ **「«지금» 라벨을 «과거»에 쓴다」**.
     ⇒ ★ 라벨이 «오염»됐으면 **「자료 축으로 «올려도» «소용없다»」** ⇒ **«이것»이 «먼저»**다.

  ⛔ **«돌리기 «전»»에 박은 것 — «넷»**
     ① 🚨 **`180` 의 「2.71%」를 «그대로» «쓰지» 않는다**(유형 67):
        `180` = **«SIC» 대분류**(`actions.csv` 의 `sicchange*`) · `61` = **Sharadar `sector`** ⇒ **«다른» 자**
     ② 🚨 **`tickers.csv` 에 «이력»이 «있나»부터** — «없으면» **「«못» 잼」이 «답»**이고 그것도 «결과»다
     ③ 🚨 **«있으면»** as-of 로 다시 매겨 「S1·S2·S3 가 «얼마나» 바뀌나」 — **판정 팔은 «하나»**
     ④ 🚨 두뇌 «바라는 답» = 「**오염이 «작길»**」 ⇒ ✅ **「오염이 «크다»」 쪽을 «더» 세게 본다**

  🚨 **「못 잼」이 나오면 그 «뜻»을 «미리» 적는다**(두뇌 지시):
     「이력이 «없어» «못» 잰다」 ⇒ **「`61` 의 판정이 «틀렸다»」가 «아니라**
     **「`61` 의 판정에 «룩어헤드»가 «있고» 그 «크기»를 «못» 잰다」**
     ⇒ ★ 그러면 **S1·S3 의 「귀무를 넘었다」도 «자격»을 «잃는다**
     ⇒ ⇒ **「«안» 닫힌 것」이 «아니라» 「«쓰면» 안 되는 것」** — **«더» 센 칸**이다

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/196-sector-label-asof.py
"""
from __future__ import annotations

import csv
import importlib.util as _u
import io as _io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.resolve().parents[2]

TIC = ROOT / ".cache" / "sharadar" / "tickers.csv.zip"
ACT = Path("D:/stock-data/sharadar/actions.csv.zip")
MON = ROOT / ".cache" / "bt5y" / "out" / "61-monthly-us.json"
W61 = ("2017-09-01", "2026-08-21")     # `61` 의 창


def rows(z):
    n = z.namelist()[0]
    with z.open(n) as f:
        for r in csv.DictReader(_io.TextIOWrapper(f, encoding="utf-8", errors="replace")):
            yield r


def main():
    P = print
    P("=" * 104)
    P("196 — **`61` 의 «업종 라벨»이 «시점» 자료인가**")
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-06 · `scripts/196-sector-label-asof.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("> 🚨 **`61` 은 «우리 정본 헤드라인»의 «일부»**다(「주도3업종 ∧ 2·3등급」) ⇒ **`190` §B 보다 «위»**")
    P("")
    P("```")
    P("## 🚨 **«돌리기 «전»»에 박은 것**")
    P("   ④ 두뇌 «바라는 답» = 「**오염이 «작길»**」  ⇒  ✅ **「오염이 «크다»」 쪽을 «더» 세게 본다**")
    P("   ① ⛔ **`180` 의 「2.71%」를 «그대로» «쓰지» 않는다** — `180`=«SIC» · `61`=`sector` = **«다른» 자**")
    P("```")
    P("")

    if not TIC.exists() or not ACT.exists():
        P("🚨 **멈춘다** — 자료 «없음**: `%s` / `%s`" % (TIC, ACT))
        return 3

    # ── 1. tickers.csv 에 «이력»이 있나 ──────────────────────────────
    P("=" * 104)
    P("## 1. ⛔ **`tickers.csv` 에 「업종 «이력»」이 «있나** — **«없다**")
    P("=" * 104)
    P("")
    with zipfile.ZipFile(TIC) as z:
        n = z.namelist()[0]
        with z.open(n) as f:
            rd = csv.reader(_io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
            hd = next(rd)
    P("```")
    P("열 **%d** 개 — %s" % (len(hd), " · ".join("`%s`" % h for h in hd)))
    P("")
    dated = [h for h in hd if h in ("lastupdated", "firstadded", "firstpricedate",
                                    "lastpricedate", "firstquarter", "lastquarter")]
    P("   «날짜» 열 — %s" % " · ".join("`%s`" % h for h in dated))
    P("   업종 관련 열 — `sector` · `industry` · `siccode` · `sicsector` · `sicindustry` · `famaindustry`")
    P("## ⇒ 🔴 **«업종» 열 «여섯»에 «날짜»가 «붙어» 있지 «않다** — **티커당 «한» 줄**이다")
    P("```")
    P("")

    # ── 2. actions.csv 가 「업종 변경」을 주나 ────────────────────────
    P("=" * 104)
    P("## 2. 🔴 **`actions.csv` 에 「`sector` 변경」 사건이 «있나** — **«없다**")
    P("=" * 104)
    P("")
    cnt = Counter()
    sic_by_ticker = defaultdict(list)
    with zipfile.ZipFile(ACT) as z:
        for r in rows(z):
            a = r.get("action") or ""
            cnt[a] += 1
            if a == "sicchangeto":
                sic_by_ticker[r.get("ticker")].append((r.get("date"), r.get("value")))
    P("```")
    P("`action` 종류 **%d** 가지 — 업종과 «닿는» 것만:" % len(cnt))
    for k in sorted(cnt):
        if "sic" in k or "sector" in k or "industry" in k:
            P("   `%-16s` **%s**" % (k, format(cnt[k], ",")))
    P("")
    has_sector_evt = any(("sector" in k or "industry" in k) for k in cnt)
    P("## ⇒ %s **「`sector` 변경」 사건 = %s**"
      % ("🚨" if has_sector_evt else "🔴", "«있다»" if has_sector_evt else "**«없다»**"))
    P("   있는 것은 **`sicchangeto` / `sicchangefrom` %s** «뿐»이고 — 그건 **«SIC»**다"
      % format(cnt.get("sicchangeto", 0), ","))
    P("```")
    P("")
    P("```")
    P("## ⇒ ★★★ **답 ② — 「이력이 «없다»」 ⇒ 「«못» 잼」**")
    P("")
    P("   **`61` 이 쓰는 `sector` 를 as-of 로 «되돌릴» 방법이 «없다**")
    P("   ⇒ 🚨 **「as-of 로 다시 매겨 S1·S2·S3 가 얼마나 바뀌나」(두뇌 ③)는 «불가»**하다")
    P("```")
    P("")

    # ── 3. 그러면 «무엇»을 잴 수 있나 — 대리 «둘** ─────────────────
    P("=" * 104)
    P("## 3. ✅ **그러면 «무엇»을 «잴» 수 있나 — «대리» «둘»**")
    P("=" * 104)
    P("")
    _s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
    r91 = _u.module_from_spec(_s)
    _s.loader.exec_module(r91)
    (_a, _b, by2), missing, _ = r91.load_ladder(
        tuple(range(1999, 2027)), "1999-04-01", "2026-08-21",
        "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 **멈춘다** — 경로 없음 %s" % missing)
        return 4
    paths = [(p["code"], p["entry_date"]) for y in by2 for p in by2[y]]
    p61 = [(c, d) for c, d in paths if W61[0] <= d <= W61[1]]

    # ㉠ SIC 가 스캔일 «뒤»에 바뀐 경로
    def after(lst, when):
        return any(dt and dt > when for dt, _v in lst)

    n_all = sum(1 for c, d in paths if after(sic_by_ticker.get(c, []), d))
    n_61 = sum(1 for c, d in p61 if after(sic_by_ticker.get(c, []), d))
    P("### ㉠ **SIC 가 «진입일 «뒤»»에 바뀐 경로** — ⚠️ **«대리»다**(`sector` 가 «아니다»)")
    P("")
    P("| 창 | 경로 | SIC 가 «뒤»에 바뀜 | 비율 |")
    P("|---|---:|---:|---:|")
    P("| 전체 27.4년 | %s | **%s** | **%.2f%%** |"
      % (format(len(paths), ","), format(n_all, ","), 100.0 * n_all / max(1, len(paths))))
    P("| `61` 창 9년 | %s | **%s** | **%.2f%%** |"
      % (format(len(p61), ","), format(n_61, ","), 100.0 * n_61 / max(1, len(p61))))
    P("")

    # ㉡ lastupdated 가 진입일 뒤인 경로 = «상한»
    lu, sec, sicsec = {}, {}, {}
    with zipfile.ZipFile(TIC) as z:
        for r in rows(z):
            if r.get("table") != "SEP":
                continue
            t = r.get("ticker")
            if not t:
                continue
            lu.setdefault(t, (r.get("lastupdated") or "")[:10])
            sec.setdefault(t, (r.get("sector") or "").strip())
            sicsec.setdefault(t, (r.get("sicsector") or "").strip())
    up_all = sum(1 for c, d in paths if lu.get(c, "") > d)
    up_61 = sum(1 for c, d in p61 if lu.get(c, "") > d)
    P("### ㉡ **`lastupdated` 가 «진입일 «뒤»»인 경로** — **«상한»**(어느 열이든 바뀌었을 수 «있다»)")
    P("")
    P("| 창 | 경로 | `lastupdated` > 진입일 | 비율 |")
    P("|---|---:|---:|---:|")
    P("| 전체 27.4년 | %s | **%s** | **%.2f%%** |"
      % (format(len(paths), ","), format(up_all, ","), 100.0 * up_all / max(1, len(paths))))
    P("| `61` 창 9년 | %s | **%s** | **%.2f%%** |"
      % (format(len(p61), ","), format(up_61, ","), 100.0 * up_61 / max(1, len(p61))))
    P("")
    P("```")
    P("⚠️ **㉡ 는 «아주» 느슨한 상한**이다 — `lastupdated` 는 **«어느» 열이 바뀌어도** 갱신된다")
    P("   ⇒ ★ 그래서 **「이만큼 «오염»됐다」가 «아니라** 「**이보다 «클» 수는 «없다»**」다")
    P("```")
    P("")

    # ㉢ sector vs sicsector 일치율 — 「SIC 를 «대리»로 써도 되나」
    both = [(t, sec[t], sicsec.get(t, "")) for t in sec if sec[t] and sicsec.get(t)]
    P("### ㉢ **`sector` 와 `sicsector` 가 «같은» 것을 가리키나** — 「㉠ 를 «대리»로 «써도» 되나」")
    P("")
    pair = Counter((a, b) for _t, a, b in both)
    top = pair.most_common(8)
    P("```")
    P("둘 «다» 있는 종목 **%s**" % format(len(both), ","))
    P("가장 흔한 (sector, sicsector) 짝 여덟:")
    for (a, b), v in top:
        P("   %-26s ↔ %-26s **%s**" % (a[:24], b[:24], format(v, ",")))
    same = sum(v for (a, b), v in pair.items() if a.lower() == b.lower())
    P("")
    P("## ⇒ **낱말이 «똑같은» 짝 = %s / %s (**%.1f%%**)**"
      % (format(same, ","), format(len(both), ","), 100.0 * same / max(1, len(both))))
    P("   ⇒ %s **두 «분류 체계»가 «다르다**"
      % ("🔴" if same / max(1, len(both)) < 0.5 else "⚠️"))
    P("")
    P("## ⚠️ **「0.0%」를 «과장»해 읽지 «않는다** — 이건 **«낱말»이 «다르다**는 뜻이지")
    P("##    **「SIC 가 `sector` 에 «정보»를 «안» 준다」가 «아니다**")
    P("   (Healthcare ↔ Manufacturing · Technology ↔ Services — **«체계»가 다를 뿐** 대응은 «있다»)")
    P("   ⇒ ✅ **쓸 말: 「대응표를 «만들지» «않으면» ㉠ 를 `sector` 의 «대리»로 «못» 쓴다」**")
    P("   ⇒ ⛔ **그리고 그 대응표를 «우리»가 만들면 «그 자체»가 «손잡이»**다(§남는 길 ㉮)")
    P("```")
    P("")

    # ── 4. 판정 ─────────────────────────────────────────────────────
    P("=" * 104)
    P("## ⇒ **판정**")
    P("=" * 104)
    P("")
    P("> # 🔴 **「«못» 잼」이다 — `61` 의 `sector` 를 as-of 로 «되돌릴» 자료가 «없다**.")
    P("")
    P("```")
    P("## 🚨 **그 «뜻»을 «미리» 적어 둔 대로**(두뇌 지시 · 결과 «보기 전»에 박음)")
    P("")
    P("   ⛔ **「`61` 의 판정이 «틀렸다»」가 «아니다**")
    P("   ✅ **「`61` 의 판정에 «룩어헤드»가 «있고» — 그 «크기»를 «못» 잰다」**")
    P("")
    P("   ⇒ ★★ 그러면 **S1(+133.89%p)·S3(+200.51%p) 의 「귀무를 «넘었다»」도 «자격»을 «잃는다**")
    P("   ⇒ ⇒ **「«안» 닫힌 것」이 «아니라» 「«쓰면» 안 되는 것」** — **«더» 센 칸**이다")
    P("```")
    P("")
    P("```")
    P("## ⚠️ **그런데 «과장»하지 «않는다** — 「오염이 «크다»」도 «못» 보였다")
    P("")
    P("   ㉠ **SIC 대리**는 «약하다**(위 ㉢) — 두 분류 체계가 «다른» 낱말을 쓴다")
    P("   ㉡ **`lastupdated` 상한**은 «너무» 느슨하다 — 「이보다 클 수 «없다»」까지다")
    P("   ⇒ ★ **「오염이 «있다»」는 «구조»로 «확실»**(날짜 없는 라벨을 과거에 씀)하나 —")
    P("     **「«얼마나»」는 «이 자료»로 «못» 잰다**")
    P("")
    P("   ⛔ **그리고 「작을 것」도 «말할 수» «없다**(두뇌가 «바라던» 쪽) —")
    P("     **«방향»조차 «못» 정한다**. 「모른다」가 «정확»하다")
    P("```")
    P("")
    P("```")
    P("## 🎯 **⇒ «남는» 길 «둘** — 어느 쪽도 «이 판»이 «아니다**")
    P("")
    P("   ㉮ **«다른» 자료로 as-of 업종을 «구한다**(예: `siccode` + SIC↔sector 대응표를 «만들어»")
    P("      `sicchange*` 로 «되돌리기») ⇒ ⚠️ **대응표를 «우리»가 만들면 그 «자체»가 «손잡이»**다")
    P("   ㉯ **업종을 «쓰지» 않는 팔로 «다시»** 낸다 ⇒ 그건 `61` 의 **R0**(자산 +44.60%)이고")
    P("      **S&P500(+209.92%)에 «크게» 진다**")
    P("")
    P("   ⇒ 🚨 **㉯ 가 「업종을 빼면 어떻게 되나」의 «답»에 «가깝다** — 그리고 **«나쁘다**")
    P("   ⇒ ⛔ 다만 R0 은 **「업종만 뺀」 것이 «아니라» 「선별을 «전부» 뺀」 것**이다 ⇒ **«같은 자»가 «아니다**")
    P("```")
    P("")
    P("=" * 104)
    P("## ⚠️ **이 판이 «못» 한 것**")
    P("=" * 104)
    P("")
    P("```")
    P("⛔ **`61` 을 «다시» 돌리지 «않았다** — 라벨을 «되돌릴» 수 «없으니** 돌릴 «대안»이 «없다**")
    P("⛔ **㉠ 의 경로 집합은 `91-monthly-us-full` 사다리**다 — `61` 은 `BT_Y0=2017` 의 «다른» 적재를 쓴다")
    P("   ⇒ **「`61` 창 9년」 줄은 «근사»**다(같은 창으로 «자른» 것이지 «같은» 집합이 «아니다»)")
    P("⛔ **`sector` 가 «실제로» 바뀐 종목이 «몇»인지 «못» 셌다** — 이력이 «없어서**")
    P("```")
    P("")
    P("> ## ✅ **⇒ 두뇌·검증께: 「업종 이력을 «다른» 데서 구할 수 «있나»」를 «넘깁니다**.")
    P("> ## **「«자기» 「없다」는 «자기»가 «못» 잡는다」 — 오늘 «아홉» 번 참이었습니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

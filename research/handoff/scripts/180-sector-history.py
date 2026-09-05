# -*- coding: utf-8 -*-
r"""180 — **「업종 «변경»이 «얼마나» 잦은가」** (남은 물음 ⑤ · 판 번호 180 · «자료 읽기» · 시뮬 «없음»)

  🚨 `174` 가 「«섹터 라벨» «자체»가 «스냅숏»」이라 «작은» 룩어헤드를 «등록»만 했고,
     「Sharadar 에 «업종 이력»이 «있는지»부터가 물음」이라 **«안 찾아봤다»**고 «신고»했다(유형 35).
     이 문서는 **«찾아본»** 결과다 — **«명령»과 «돌린 자리»를 «같이» 적는다**.
"""
from __future__ import annotations
import collections
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SH = Path("D:/stock-data/sharadar")
SUB = Path("C:/Users/hanul/playground/my-stock/.cache/bt5y/sub")

DIV = [(100, 999, "농림어업"), (1000, 1499, "광업"), (1500, 1799, "건설"),
       (2000, 3999, "제조"), (4000, 4999, "운수·공익"), (5000, 5199, "도매"),
       (5200, 5999, "소매"), (6000, 6799, "금융·보험·부동산"),
       (7000, 8999, "서비스"), (9100, 9729, "공공행정")]


def div(code):
    try:
        c = int(float(code))
    except Exception:
        return None
    for a, b, n in DIV:
        if a <= c <= b:
            return n
    return None


def main():
    P = print
    P("=" * 104)
    P("180 - **「업종 «변경»이 «얼마나» 잦은가」** (남은 물음 ⑤ · 판 번호 180 · «자료 읽기»)")
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-04 · `scripts/180-sector-history.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("## 🚨 **묻는 것 — 「«이력»이 «있나»」가 «먼저**")
    P("")
    P("```")
    P("`174`: 「«섹터 라벨» «자체»가 «스냅숏»」 ⇒ **«작은» 룩어헤드**")
    P("   그때 나는 **「없어 «보인다»」**고 적었는데 — 그건 **«안 찾아본»** 것이었다(유형 35)")
    P("⇒ ✅ 이 문서는 **«찾아본»** 것이다. **«명령»과 «돌린 자리»를 «같이» 적는다**")
    P("```")
    P("")

    # ── ㉠ tickers.csv ────────────────────────────────────────────────
    zf = zipfile.ZipFile(str(SH / "tickers.csv.zip"))
    nm = zf.namelist()[0]
    with zf.open(nm) as f:
        r = csv.reader(io.TextIOWrapper(f, encoding="utf-8"))
        hdr = next(r)
        it, tb = hdr.index("ticker"), hdr.index("table")
        cnt, nrow = collections.Counter(), 0
        for row in r:
            nrow += 1
            if row[tb] == "SEP":
                cnt[row[it]] += 1
    dup = sum(1 for v in cnt.values() if v > 1)

    P("## 1. ㉠ **`tickers.csv` — «열 목록»에 「업종 «이력»」이 «있나**")
    P("")
    P("```")
    P("🔎 명령 `python -c \"zipfile.ZipFile('tickers.csv.zip')…\"` · 돌린 자리 `%s`" % str(SH))
    P("")
    P("**열 %d개 «전부»:**" % len(hdr))
    for i in range(0, len(hdr), 4):
        P("   " + " · ".join("`%s`" % h for h in hdr[i:i + 4]))
    P("")
    P("**업종을 담은 열 — %s**"
      % " · ".join("`%s`" % h for h in hdr if h in
                   ("sector", "industry", "sicsector", "sicindustry", "siccode", "famaindustry")))
    P("**날짜를 담은 열 — %s**"
      % " · ".join("`%s`" % h for h in hdr if "date" in h or h in
                   ("lastupdated", "firstadded", "firstquarter", "lastquarter")))
    P("")
    P("## ⇒ 🔴 **업종 열 여섯 «전부» «값이 «하나»»다 — 「언제부터 그랬나」를 담은 열이 «없다**")
    P("   (`lastupdated` 는 「«이 줄»이 마지막으로 손댄 날」이지 「업종이 «바뀐» 날」이 «아니다»)")
    P("")
    P("**㉡ 「한 줄/종목」이 «맞나»** — SEP 행 **%s** · 서로 다른 티커 **%s** · **중복 %d개**"
      % (format(sum(cnt.values()), ","), format(len(cnt), ","), dup))
    P("   ⇒ %s **한 티커에 한 줄**이다 ⇒ **이 파일 «안»에는 «이력»이 «있을 수가» 없다**"
      % ("✅" if dup == 0 else "🚨"))
    P("```")
    P("")

    # ── ㉢ actions.csv ────────────────────────────────────────────────
    zf2 = zipfile.ZipFile(str(SH / "actions.csv.zip"))
    ev, kinds = {}, collections.Counter()
    with zf2.open(zf2.namelist()[0]) as f:
        r = csv.reader(io.TextIOWrapper(f, encoding="utf-8"))
        h2 = next(r)
        ia, idt, it2, iv = (h2.index("action"), h2.index("date"),
                            h2.index("ticker"), h2.index("value"))
        for row in r:
            kinds[row[ia]] += 1
            if row[ia] in ("sicchangeto", "sicchangefrom"):
                ev.setdefault((row[it2], row[idt]), {})[row[ia]] = row[iv]
    prs = [(k[0], k[1], v.get("sicchangefrom"), v.get("sicchangeto"))
           for k, v in ev.items() if len(v) == 2]
    cross = [(t, d) for t, d, a, b in prs
             if div(a) and div(b) and div(a) != div(b)]
    bycode = collections.defaultdict(list)
    for t, d in cross:
        bycode[t].append(d)

    P("## 2. 🔴🔴 **㉢ — 「없다」로 «닫으려다» 「«다른 파일»에 «있다»」를 찾았다**")
    P("")
    P("```")
    P("🔎 명령 `actions.csv.zip` 의 `action` 열 «전부» 세기 · 돌린 자리 `%s`" % str(SH))
    P("")
    P("**`action` 종류 %d개 중 «업종»에 해당하는 것:**" % len(kinds))
    P("   `sicchangeto`   — **%s** 건" % format(kinds["sicchangeto"], ","))
    P("   `sicchangefrom` — **%s** 건" % format(kinds["sicchangefrom"], ","))
    P("")
    P("## ⇒ 🔴 **「이력이 «없다»」는 «틀렸다** — **«날짜» 붙은 업종 변경이 «있다»**")
    P("")
    P("🚨 **그런데 «자»가 «다르다»**(또 유형 67):")
    P("   우리 판이 쓰는 라벨 — `61a-build-monthly.py:32` **`r.get(\"sector\")`** (Sharadar 자체 분류)")
    P("   `actions.csv` 가 주는 이력 — **`siccode`** (미국 SIC 코드)")
    P("   ⇒ ⛔ **「우리가 «쓰는» 자의 이력」은 «여전히» «없다**")
    P("   ⇒ ✅ **다만 SIC 를 «대리»로 쓰면 「얼마나 잦은가」의 «크기»는 «잴 수» 있다**")
    P("```")
    P("")

    P("## 3. ✅ **크기 — 「«대리»로」 잰다**")
    P("")
    P("```")
    P("**«대분류»(SIC division 10개)가 «바뀐» 것만 «업종 변경»으로 센다**")
    P("   (`6770 금융 → 4911 운수·공익` 같은 것. 같은 대분류 안의 코드 변경은 «업종»이 아니다)")
    P("")
    P("   sicchange «짝» — **%s**  ·  그중 «대분류»가 바뀐 것 — **%s** (**%.1f%%**)"
      % (format(len(prs), ","), format(len(cross), ","),
         100.0 * len(cross) / max(len(prs), 1)))
    P("   «대분류»가 바뀐 «종목» — **%s** 개" % format(len(bycode), ","))
    P("```")
    P("")

    seen = collections.defaultdict(list)
    npath = 0
    for y in range(1999, 2027):
        f = SUB / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        for p in json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]:
            npath += 1
            seen[p["code"]].append(p["scan_date"])
    hitc = [c for c in seen if c in bycode]
    after = tot = 0
    for c, ds in seen.items():
        chg = bycode.get(c)
        for sd in ds:
            tot += 1
            if chg and any(x > sd for x in chg):
                after += 1

    P("## 4. ★★ **「«작은» 룩어헤드」의 «크기» — «수»가 됐다**")
    P("")
    P("```")
    P("🔎 자리 `%s` (우리 판이 «읽는» 그 파일)" % str(SUB))
    P("")
    P("   원시 후보 경로 — **%s** · 서로 다른 종목 — **%s**"
      % (format(npath, ","), format(len(seen), ",")))
    P("   그중 «대분류» 변경이 «있었던» 종목 — **%s** (**%.1f%%**)"
      % (format(len(hitc), ","), 100.0 * len(hitc) / max(len(seen), 1)))
    P("")
    P("## ⇒ ★ **스캔일 «뒤»에 대분류가 바뀐 경로 — %s / %s = «%.2f%%»**"
      % (format(after, ","), format(tot, ","), 100.0 * after / max(tot, 1)))
    P("   **그 경로들만 «스냅숏» 라벨이 «그때»와 «다를» 수 있다**")
    P("```")
    P("")
    P("```")
    P("## ✅ **서는 문장**")
    P("")
    P("① **「우리가 «쓰는» 라벨(`sector`)의 «이력»은 Sharadar 에 «없다»」** — «찾아봤고» «없다»")
    P("   («명령»·«자리»·«열 목록 28개» 를 위에 «전부» 적었다)")
    P("")
    P("② 🔴 **「Sharadar 에 업종 이력이 «없다»」는 «틀린» 문장이다** — `actions.csv` 에")
    P("   **`sicchangeto/from` 이 «날짜»와 함께 %s 건씩** 있다. **«다른 자»의 이력이다**"
      % format(kinds["sicchangeto"], ","))
    P("")
    P("③ ★ **그 «대리»로 재니 「«작은» 룩어헤드」는 «경로의 %.2f%%»** 다"
      % (100.0 * after / max(tot, 1)))
    P("   ⇒ **「«못» 잰다」가 «아니라» 「«대리»로 «쟀고» «작다»」**로 «바뀌었다**")
    P("")
    P("⛔ **못 쓸 말**")
    P("   ⛔ 「업종 이력이 «없다»」 — **«어느» 자의 이력인지 «붙이지» 않으면 «틀린» 문장**")
    P("   ⛔ 「룩어헤드가 %.2f%% 다」 — **SIC 는 «대리»**다. `sector` 축의 «진짜» 크기는 «여전히» 미측정"
      % (100.0 * after / max(tot, 1)))
    P("   ⛔ 「%.2f%% 니 «무시»해도 된다」 — **«크기»를 쟀을 뿐 «영향»은 «안» 쟀다**"
      % (100.0 * after / max(tot, 1)))
    P("   🚨 그리고 이 수는 **«원시» 후보 경로 %s 기준**이다 — 판의 후보(16,150)와 «다른 자»다"
      % format(npath, ","))
    P("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

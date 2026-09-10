# -*- coding: utf-8 -*-
r"""196b — **「티커당 «한» 줄」은 «언제»의 라벨인가** · 검증 반박 확인 · 2026-09-06

  🚨 **검증 반박**: 「`tickers.csv` 의 라벨이 «오늘»이 «아니라» **«마지막»(상폐 시점)**일 수 있다」
     ⇒ ★ 그러면 **«여전히» 룩어헤드이나 «크기»가 «다르다**(산 종목은 «오늘» · 상폐는 «그때»)

  🔴🔴 **검증이 «스스로» 붙인 경고를 «그대로» 옮긴다**:
     「그러니 «내»가 «두뇌»가 «바라는» 쪽(오염이 «작다»)을 «찾은» 셈이다.
      «그래서» «확인»이 «필요»하다 — **「찾았다」로 «닫지» 말 것**」
     ⇒ ✅ **그러므로 이 판은 「오염이 «크다»」 쪽을 «더» 세게 본다**

  ⛔ **«머리»에 박는 것 — «둘»**(두뇌 지시)
     ① **「«못» 잼」 ≠ 「«괜찮다»」** — **「모른다」는 「작다」가 «아니다**
     ② 이 판은 「«도구»를 깎는」 것이 «아니라» **「우리가 «쓰는» 것의 «근거»를 깎는」** 것이다
        ⇒ **`61` 은 «정본» 헤드라인의 «일부»**다

  ⛔ **그리고 «구조»상 «먼저» 적어 두는 것** — 이 판이 «무엇»을 «바꿀» 수 «있나**
     라벨이 **「상폐 시점에 «얼어붙는다»」**여도 — **상폐일은 «진입일»보다 «뒤»**다.
     ⇒ ★ **룩어헤드가 «사라지는» 게 «아니라» «지평»이 «짧아질» 뿐**이다.
     ⇒ ⇒ 그러니 이 판이 낼 수 있는 최선은 **「오염의 «지평»을 «잰다»」**이지 「«없다»」가 «아니다».

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/196b-label-vintage.py
"""
from __future__ import annotations

import csv
import datetime as _dt
import importlib.util as _u
import io as _io
import statistics as st
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.resolve().parents[2]
TIC = ROOT / ".cache" / "sharadar" / "tickers.csv.zip"
W61 = ("2017-09-01", "2026-08-21")


def ordv(s):
    try:
        return _dt.date(int(s[:4]), int(s[5:7]), int(s[8:10])).toordinal()
    except Exception:
        return None


def pct(v, q):
    v = sorted(v)
    if not v:
        return float("nan")
    return v[min(len(v) - 1, int(len(v) * q))]


def main():
    P = print
    P("=" * 104)
    P("196b — **「티커당 «한» 줄」은 «언제»의 라벨인가** · 검증 반박 확인")
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-06 · `scripts/196b-label-vintage.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("```")
    P("## 🔴🔴 **검증이 «스스로» 붙인 «경고» — «그대로» 옮긴다**")
    P("")
    P("   「그러니 «내»가 «두뇌»가 «바라는» 쪽(오염이 «작다»)을 «찾은» 셈이다.")
    P("    «그래서» «확인»이 «필요»하다 — **「찾았다」로 «닫지» 말 것**」")
    P("   ⇒ ✅ **이 판은 「오염이 «크다»」 쪽을 «더» 세게 본다**")
    P("")
    P("## ⛔ **머리에 박는 것 — «둘**")
    P("   ① **「«못» 잼」 ≠ 「«괜찮다»」** — 「모른다」는 「작다」가 «아니다**")
    P("   ② 이 판은 **「우리가 «쓰는» 것의 «근거»를 깎는」** 것이다 — `61` 은 «정본» 헤드라인의 «일부**")
    P("")
    P("## ⛔ **그리고 «구조»상 «미리** — 이 판이 «무엇»을 «바꿀» 수 있나")
    P("   라벨이 「상폐 시점에 «얼어붙는다»」여도 — **상폐일은 «진입일»보다 «뒤»**다")
    P("   ⇒ ★ **룩어헤드가 «사라지는» 게 «아니라» «지평»이 «짧아질» 뿐**이다")
    P("   ⇒ ⇒ **최선은 「오염의 «지평»을 «잰다»」**이지 **「«없다»」가 «아니다**")
    P("```")
    P("")

    if not TIC.exists():
        P("🚨 **멈춘다** — `%s` 가 «없다**" % TIC)
        return 3

    rows = []
    with zipfile.ZipFile(TIC) as z:
        n = z.namelist()[0]
        with z.open(n) as f:
            for r in csv.DictReader(_io.TextIOWrapper(f, encoding="utf-8", errors="replace")):
                if r.get("table") != "SEP":
                    continue
                rows.append((r.get("ticker"), r.get("isdelisted"),
                             (r.get("sector") or "").strip(),
                             (r.get("lastupdated") or "")[:10],
                             (r.get("lastpricedate") or "")[:10]))

    # ── ㉠ 상폐 티커에 라벨이 있나 ───────────────────────────────────
    P("=" * 104)
    P("## ㉠ **«상폐»된 티커에 `sector` 가 «있나**")
    P("=" * 104)
    P("")
    P("| `isdelisted` | 종목 | `sector` «있음» | 비율 |")
    P("|---|---:|---:|---:|")
    for flag, lab in (("N", "산 종목"), ("Y", "**상폐**")):
        g = [r for r in rows if r[1] == flag]
        h = [r for r in g if r[2]]
        P("| %s (%s) | %s | %s | **%.1f%%** |"
          % (flag, lab, format(len(g), ","), format(len(h), ","),
             100.0 * len(h) / max(1, len(g))))
    P("")
    P("```")
    P("## ⇒ **상폐 종목에도 라벨이 «거의 다» 있다** ⇒ 「상폐되면 «지운다»」가 «아니다**")
    P("```")
    P("")

    # ── ㉡㉢ lastupdated 의 «나이» ────────────────────────────────────
    P("=" * 104)
    P("## ㉡㉢ **`lastupdated` 가 «언제»인가 — 산 종목 vs 상폐 종목**")
    P("=" * 104)
    P("")
    P("| 무리 | n | `lastupdated` P10 | 중앙 | P90 |")
    P("|---|---:|---|---|---|")
    for flag, lab in (("N", "산 종목"), ("Y", "**상폐**")):
        v = [r[3] for r in rows if r[1] == flag and r[3]]
        P("| %s | %s | %s | **%s** | %s |"
          % (lab, format(len(v), ","), pct(v, 0.10), pct(v, 0.50), pct(v, 0.90)))
    P("")

    # 상폐 종목: lastupdated − lastpricedate
    gap = []
    for t, fl, sec, lu, lp in rows:
        if fl != "Y" or not lu or not lp:
            continue
        a, b = ordv(lu), ordv(lp)
        if a is None or b is None:
            continue
        gap.append(a - b)
    P("### 🚨 **상폐 종목 — `lastupdated` − `lastpricedate`(«날» 수)**")
    P("")
    P("```")
    P("n = %s   ·   중앙 **%s 일**   ·   P10 %s   ·   P90 **%s 일**"
      % (format(len(gap), ","), format(int(st.median(gap)), ","),
         format(pct(gap, 0.10), ","), format(pct(gap, 0.90), ",")))
    near = sum(1 for g in gap if abs(g) <= 31)
    far = sum(1 for g in gap if g > 365)
    P("")
    P("   **«상폐일 «근처»»(±31일) = %s / %s = %.1f%%**"
      % (format(near, ","), format(len(gap), ","), 100.0 * near / max(1, len(gap))))
    P("   **1년 «넘게» «뒤»에 갱신 = %s / %s = %.1f%%**"
      % (format(far, ","), format(len(gap), ","), 100.0 * far / max(1, len(gap))))
    P("```")
    P("")
    P("```")
    P("")
    P("```")
    P("## 🆕🚨 **「22.4%」를 «주» 근거에서 «내린다**(검증 2차 · 2026-09-06)")
    P("")
    P("   🔴 **「«절반»에도 «못» 미친다」는 «문턱»(0.5)이 «든» 문장**이다 ⇒ **«보조»로만 쓴다**")
    P("   ✅ **«문턱»이 «필요 «없는»» 근거 «둘»이 «있다**:")
    P("")
    P("   ㉠ **산 종목 %s 의 `lastupdated` 가 P10 = 중앙 = P90 = «한» 날짜**"
      % format(sum(1 for r in rows if r[1] == "N"), ","))
    P("      ⇒ ★★ **「산 종목은 «오늘» 라벨」**이 «문턱» «없이» «보인다**")
    P("   ㉡ **경로를 «직접» 세면** — 아래 ㉣ 표의 **「상폐 시점 라벨」 칸**")
    P("      ⇒ ★ 「51.1% × 22.4%」로 **«곱하지» «않았다** — **«경로»마다 «직접» 셌다**")
    P("")
    P("## 🆕🚨 **«왜» 곱하면 «안» 되나 — «분모»가 «다르다**(검증 2차 · 2026-09-06)")
    P("   **「51.1%」는 «경로» 기준**  ·  **「22.4%」는 «티커» 기준**  ⇒ **«곱할» 수 «없다**")
    P("   (「상폐일 근처」 라벨인 티커가 «경로»를 «더 많이» 가지면 «곱셈»이 «어긋난다»)")
    P("   ⇒ ★ **실제로 «어긋났다** — 곱셈 **5.2%** vs «직접» 센 **16.5%**(`61` 창) = **«세» 배 «넘게»**")
    P("   ⇒ ⇒ 🚨 그리고 **«곱셈»이 오염을 «작게»** 보이게 했다 — **«우리»가 «바라던» 쪽**이다")
    P("")
    P("## ⇒ ✅ **처방: 「«비율»을 «곱하기» «전»에 **«분모»가 «같은지»** 묻는다. «다르면» «직접» 센다」**")
    P("")
    P("   ⇒ ★ 그리고 **«살아남는» 근거는 «하나»가 «아니라» «둘»**이다:")
    P("     **①** 산 종목의 `lastupdated` 가 «한» 날짜 — **«문턱» 없는 «직접» 관측**")
    P("     **②** 「상폐 시점 라벨」 **16.5%** — **«곱셈»이 «아니라» «센» 수**")
    P("```")
    P("")
    P("```")
    ok_frozen = near / max(1, len(gap)) >= 0.5
    P("## ⇒ %s **검증 반박의 «채점**" % ("✅" if ok_frozen else "🔴"))
    P("")
    if ok_frozen:
        P("   ✅ **「상폐 시점에 «얼어붙는다»」가 «절반 «넘게»» 맞다**(%.1f%%)"
          % (100.0 * near / max(1, len(gap))))
        P("   ⇒ ★ 그러면 **상폐 종목의 «오염 지평»은 「진입일 → 상폐일」로 «짧아진다**")
    else:
        P("   🔴 **「상폐 시점에 «얼어붙는다»」는 «절반»에도 «못» 미친다**(%.1f%%)"
          % (100.0 * near / max(1, len(gap))))
        P("   ⇒ ★★ **검증 반박이 «빗나갔다** — 상폐 종목도 **«한참» «뒤»에 갱신**된다")
        P("   ⇒ ⇒ 🚨 **두뇌가 «바라던» 「오염이 «작다»」 쪽이 «아니다**")
    P("```")
    P("")

    # ── ㉣ 우리 «경로»가 어느 무리인가 ───────────────────────────────
    P("=" * 104)
    P("## ㉣ ★★ **그런데 «정작» 중요한 것 — «우리» 경로가 «어느» 무리인가**")
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
    info = {t: (fl, lu) for t, fl, _sec, lu, _lp in rows}
    paths = [(p["code"], p["entry_date"]) for y in by2 for p in by2[y]]
    p61 = [(c, d) for c, d in paths if W61[0] <= d <= W61[1]]

    frozen = {t for t, fl, _sec, lu, lp in rows
              if fl == "Y" and lu and lp and ordv(lu) is not None and ordv(lp) is not None
              and abs(ordv(lu) - ordv(lp)) <= 31}
    P("| 창 | 경로 | 산 종목 | 상폐 종목 | **「상폐 시점」 라벨** | 라벨 «나이» 중앙 |")
    P("|---|---:|---:|---:|---:|---:|")
    froz_share, age_med = {}, {}
    for lab, ps in (("전체 27.4년", paths), ("`61` 창 9년", p61)):
        live = sum(1 for c, _d in ps if (info.get(c) or ("", ""))[0] == "N")
        dead = sum(1 for c, _d in ps if (info.get(c) or ("", ""))[0] == "Y")
        fz = sum(1 for c, _d in ps if c in frozen)
        froz_share[lab] = 100.0 * fz / max(1, len(ps))
        ages = []
        for c, d in ps:
            fl_lu = info.get(c)
            if not fl_lu or not fl_lu[1]:
                continue
            a, b = ordv(fl_lu[1]), ordv(d)
            if a is None or b is None:
                continue
            ages.append((a - b) / 365.25)
        P("| %s | %s | %s (%.1f%%) | %s (%.1f%%) | **%s (%.1f%%)** | **%.1f 년** |"
          % (lab, format(len(ps), ","), format(live, ","), 100.0 * live / max(1, len(ps)),
             format(dead, ","), 100.0 * dead / max(1, len(ps)),
             format(fz, ","), froz_share[lab],
             age_med.setdefault(lab, st.median(ages) if ages else float("nan"))))
    P("")
    P("```")
    P("## ⇒ ★★★ **「라벨 «나이»」는 «측정»이 «아니라» «서술»이다**(검증 2차)")
    P("")
    P("   ✅ **쓸 말** — 「**%.1f 년 «뒤»의 업종 «분류»로 «그날»을 «판단»했다**」(`61` 창)"
      % age_med.get("`61` 창 9년", float("nan")))
    P("")
    P("   ⛔ **「지평 × SIC 4.68%」를 «계산»해 «적지» «않는다**(검증 2차)")
    P("      (ㄱ) SIC 4.68% 는 **27.4년 «누적»** ⇒ «비례»하면 「연간 «균등»」을 «가정»한다")
    P("      (ㄴ) **SIC ↔ `sector` 는 «다른» 자**(`196` ③ 에서 «우리»가 «확인»)")
    P("   ⇒ ★★ **«두» 가정을 «쌓는다»** ⇒ **유형 68**(「«단가»를 «다른» 판으로 «옼긴다»」)")
    P("   ⇒ ⛔ **그 «수»를 «적으면» «인용»된다** — 오늘 「1.59배」·「87.47」·「2,000년」으로 **«세» 번** 겪은 일이다")
    P("```")
    P("")

    P("=" * 104)
    P("## ⇒ **맺음**")
    P("=" * 104)
    P("")
    P("```")
    P("⛔ **「«못» 잼」은 «그대로»다** — `sector` 이력이 «없다는 사실»은 «안» 바뀐다")
    P("✅ **바뀐 것**: 오염을 **«말»로 적을 수 «있게» 됐다** — 「**4.6년 «뒤»의 분류로 «그날»을 판단했다**」")
    P("   ⛔ **«수»가 «아니라» «말»이다** — 「«얼마나» 나쁜가」가 «아니라» 「**«무엇»이 나쁜가**」")
    P("⛔ **「지평이 «짧다»」가 「오염이 «작다»」가 «아니다** —")
    P("   업종이 «바뀌는» 일 «자체»가 «드물면**(SIC 대리 4.68%) 지평이 «길어도» 몫이 «작을» 수 있고,")
    P("   **«반대»도 «참»**이다. **«둘»을 «곱해야»** 하는데 — **`sector` 쪽 «변경률»을 «모른다**")
    P("## ⇒ 🔴 **그래서 «여전히» 「«못» 잼」이다. «지평»만 «알게» 됐다**")
    P("```")
    P("")
    P("> ## ✅ **⇒ 두뇌·검증께: 「이 «지평»으로 «충분»한가」를 «넘깁니다**.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
r"""233a - **«고치기» «전» 「지금 «수»」를 «갈무리**  (관문 ① · 조사 세션 2026-09-08)

  ⛔ **«아무것»도 «고치지» 않는다** - `201d-rs-threshold.md` 를 «읽어» «박아» 둔다.
  ⛔ 여기 적힌 MDE·CI 는 **「«전»/«후» «나란히»」 «자리»에서«만** 쓴다(인용 금지가 «산다»).

  ✅ 관문 ②(읽어 «확인»)도 «같이** - 불일치 14 «중» «셋»을 «눈»으로 본 결과를 «적는다**.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/233a-snapshot.py
"""
from __future__ import annotations

import re as _re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"

# 관문 ② - «눈»으로 «읽은» 셋(파일:줄과 «본» 글자를 «그대로»)
EYE = [
    ("184-swap-data-axis.py", 486, 'all_d = sorted({z[0] for z in folded})', "자리 = 진입일«만»"),
    ("184-swap-data-axis.py", 441, 'hold = d.index(rd) if (rd and rd in d) else len(d) - 1', "보유 = 「거래일」"),
    ("229-roe-threshold.py", 179, 'all_d = sorted({d for lst in built.values() for d, _h, _n in lst})', "자리 = 진입일«만»"),
    ("229-roe-threshold.py", 98, 'hold = d.index(rd) if (rd and rd in d) else len(d) - 1', "보유 = 「거래일」"),
    ("227b-noliq-judge.py", 216, 'all_d = sorted({d for lst in built.values() for d, _h, _n in lst})', "자리 = 진입일«만»"),
    ("227b-noliq-judge.py", 138, 'hold = d.index(rd) if (rd and rd in d) else len(d) - 1', "보유 = 「거래일」"),
]

ROW = _re.compile(r"^\|\s*(?P<arm>[^|]+?)\s*\|\s*\*\*(?P<pt>[+-][0-9.]+)%p\*\*\s*\|"
                  r"\s*\[(?P<lo>[+-][0-9.]+),\s*(?P<hi>[+-][0-9.]+)\]")


def main():
    P("# 233a - **«전» 갈무리**(관문 ①) + **«눈»으로 확인**(관문 ②)")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/233a-snapshot.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **«아무것»도 «고치지» 않았다** · 여기 MDE·CI 는 **「«전»/«후» 나란히」 자리에서«만** 쓴다")
    P("")
    P("---")
    P("")

    P("# 1. **관문 ② — «눈»으로 «읽어» «확인**(불일치 14 «중» **3** 각본)")
    P("")
    P(F3)
    seen = []
    for fn, ln, txt, what in EYE:
        real = (HERE / fn).read_text(encoding="utf-8", errors="replace").splitlines()
        got = real[ln - 1].strip() if ln - 1 < len(real) else "(줄 «없음»)"
        ok = got == txt
        seen.append(ok)
        P("   %-24s :%-4d %s" % (fn, ln, "✅ «맞다»" if ok else "🔴 «다르다»"))
        P("        %-14s %s" % (what, got))
    P("")
    P("   ★ **%d 중 %d** 이 «내»가 «적은» 것과 «같다** ⇒ %s"
      % (len(seen), sum(seen),
         "✅ **정규식 분류가 «맞는다**(3 각본 표본)" if all(seen) else "🔴 **«다르다** — 분류를 «다시**"))
    P("   ⛔ **3 각본 «표본»이다** — **14 «전부»를 «읽은» 게 «아니다**")
    P(F3)
    P("")
    P("---")
    P("")

    P("# 2. **`201d` 의 「지금 «수»」 — «전** (⛔ **«고치기» «전»에 «박는다**)")
    P("")
    P(F3)
    P("   출처 " + BQ + "results/201d-rs-threshold.md" + BQ + " · 캐시 "
      + BQ + ".cache/bt5y/out/201d-arms.json" + BQ)
    P("")
    src = (RES / "201d-rs-threshold.md").read_text(encoding="utf-8", errors="replace")
    for ln in src.splitlines():
        if "날짜 자리 수" in ln or "거래 수" in ln:
            P("   %s" % ln.strip())
    P(F3)
    P("")
    P("| 짝 | 점추정 | 95% CI | CI폭 | MDE | 판정칸 |")
    P("|---|---:|---:|---:|---:|:--|")
    n = 0
    for ln in src.splitlines():
        m = ROW.match(ln)
        if not m:
            continue
        n += 1
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        P("| %s | %s | %s | %s | %s | %s |"
          % (cells[0], cells[1], cells[2], cells[3],
             cells[4] if len(cells) > 4 else "—", cells[-1]))
    P("")
    P(F3)
    P("   찍은 행 **%d** (블록 «둘» x 팔 «넷»)" % n)
    P("   ★ **판정 짝은 " + chr(0x211D) + chr(0x2212) + chr(0x2460)
      + " «하나»** — 나머지 셋은 **«묘사»**다(`201d` 사전등록 ②)")
    P("   ⛔ **`233` 은 «판정» 짝«만** 다시 «잰다** — **묘사 셋은 «안** 잰다")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 갈무리가 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **3 각본만 «눈»으로 봤다** — 나머지 11 은 **정규식 «분류»뿐**")
    P("⛔ ② 🚨 **" + BQ + "232d" + BQ + " 가 " + BQ + "184" + BQ
      + " 의 «자리» 줄을 **:495**(=cnt 「라벨」)로 «찍었다** —")
    P("     **«진짜» 구성은 :486** 이다. **«분류»는 «맞고» «줄 번호»가 «라벨»을 가리켰다**")
    P("     ⇒ ★ **「«눈»으로 읽어라」가 «값»을 했다**(관문 ②)")
    P("⛔ ③ **여기 수는 「«전»/«후» 나란히」 «자리»에서«만** 쓴다 — **«인용» 금지가 «산다**")
    P("⛔ ④ **원본 " + BQ + "201d-rs-threshold.py" + BQ + "·"
      + BQ + "201d-arms.json" + BQ + " 은 «건드리지» 않았다** — 그것이 «진짜» 갈무리다")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

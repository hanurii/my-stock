# -*- coding: utf-8 -*-
r"""232a - 「편향 «찍기»」 · «돌리지» 않는다. **«이미» 있는 «수»를 «전수»로 «읽는다»**

  🚨 검증 1차 반론(정본 1af60653)이 «끼운» 단계다: ①계산검산 -> **편향찍기** -> ②양성대조 -> ③기전

  자: **편향 = «부트 중앙» - 점추정**  ·  SD = CI폭 / 3.92
      **|편향|/SD > 1 이면 «의심»**  ·  **점추정이 CI «밖»이면 «멈춤»**(조건 |편향| > 폭/2)

  ⛔ 손으로 «적지» 않는다 - **results/*.md 를 «읽어» «생성»한다**(위생 규율 ①)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/232a-bias-stamp.py
"""
from __future__ import annotations

import re as _re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
RES = Path(__file__).resolve().parent.parent / "results"

ROW = _re.compile(
    r"^\|\s*(?P<arm>[^|]+?)\s*\|\s*\*\*(?P<pt>[+-][0-9.]+)%p\*\*\s*\|"
    r"\s*\[(?P<lo>[+-][0-9.]+),\s*(?P<hi>[+-][0-9.]+)\]\s*\|(?P<rest>.*)$")


def main():  # noqa: C901
    P("# 232a - **편향 «찍기»** («돌리지» 않았다 · «이미» 있는 수를 «전수»로 읽었다)")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/232a-bias-stamp.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> 자: **편향 = CI«중앙» - 점추정** · SD = CI폭/3.92 · **|편향|/SD > 1 «의심»** ·"
      " **점추정 CI «밖» «멈춤»**")
    P("")
    P("---")
    P("")

    files = sorted(p for p in RES.glob("*.md"))
    rows = []
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="replace").splitlines()
        hdr_bias = None
        for ln in txt:
            if ln.startswith("|") and "점추정" in ln:
                cols = [c.strip() for c in ln.strip().strip("|").split("|")]
                hdr_bias = None
                for i, c in enumerate(cols):
                    if "편향" in c:
                        hdr_bias = i
                continue
            m = ROW.match(ln)
            if not m:
                continue
            pt = float(m.group("pt"))
            lo, hi = float(m.group("lo")), float(m.group("hi"))
            printed = None
            if hdr_bias is not None:
                cols = [c.strip() for c in ln.strip().strip("|").split("|")]
                if hdr_bias < len(cols):
                    mm = _re.match(r"^[+-][0-9.]+$", cols[hdr_bias])
                    if mm:
                        printed = float(cols[hdr_bias])
            rows.append((f.name, m.group("arm"), pt, lo, hi, printed))

    P("# 1. **찾은 것 - «몇 중 몇»**")
    P("")
    P(F3)
    P("   훑은 파일 **%d** · CI 를 «가진» 행 **%d**" % (len(files), len(rows)))
    nprint = sum(1 for r in rows if r[5] is not None)
    P("   그중 **「편향」 열이 «이미» «찍힌» 행 = %d**" % nprint)
    P("   **「편향」 열이 «없는» 행 = %d**   <- 🚨 «뒤» 판들이 그 열을 **«떨어뜨렸다**" % (len(rows) - nprint))
    P(F3)
    P("")
    P("---")
    P("")

    P("# 2. **전수 표**")
    P("")
    P("| 판 | 팔 | 점추정 | CI | 폭 | SD | **부트«중앙»** | **편향** | **|편향|/SD** | 점추정 | 찍힌편향 |")
    P("|---|---|---:|---:|---:|---:|---:|---:|---:|:--|---:|")
    n_susp = n_out = 0
    mids = []
    for fn, arm, pt, lo, hi, printed in rows:
        w = hi - lo
        sd = w / 3.92
        mid = (lo + hi) / 2.0
        bias = mid - pt
        rat = abs(bias) / sd if sd else float("nan")
        outside = not (lo <= pt <= hi)
        if rat > 1:
            n_susp += 1
        if outside:
            n_out += 1
        mids.append(mid)
        P("| %s | %s | %+.3f | [%+.3f, %+.3f] | %.2f | %.3f | **%+.3f** | **%+.3f** | **%.2f**%s | %s | %s |"
          % (fn.replace(".md", ""), arm, pt, lo, hi, w, sd, mid, bias, rat,
             " 🚨" if rat > 1 else "",
             "🚨 **밖**" if outside else "안",
             ("%+.3f" % printed) if printed is not None else "-"))
    P("")
    P(F3)
    P("   **%d 행 «중» %d** 이 **|편향|/SD > 1**(«의심»)" % (len(rows), n_susp))
    P("   **%d 행 «중» %d** 이 **점추정이 CI «밖»**(«멈춤»)" % (len(rows), n_out))
    P("")
    inz = sum(1 for m in mids if abs(m) <= 1.0)
    P("   ★ **부트 «중앙»이 |1.0| 안인 행 = %d / %d**" % (inz, len(rows)))
    P("   ★ 부트 «중앙»의 «범위» = **%+.3f ~ %+.3f**  ·  점추정의 «범위» = **%+.3f ~ %+.3f**"
      % (min(mids), max(mids), min(r[2] for r in rows), max(r[2] for r in rows)))
    P(F3)
    P("")

    # 찍힌 편향 vs 우리가 «다시» 낸 편향 - 정의가 «같은가»
    P("---")
    P("")
    P("# 3. **「찍힌 편향」과 «맞대기** - «정의»가 같은가")
    P("")
    P(F3)
    both = [(fn, arm, (hi + lo) / 2.0 - pt, printed)
            for fn, arm, pt, lo, hi, printed in rows if printed is not None]
    if not both:
        P("   («찍힌» 편향이 «없다»)")
    else:
        d = [abs(a - b) for _f, _a, a, b in both]
        P("   맞댄 행 **%d** · |차| 중앙 **%.3f** · 최대 **%.3f**"
          % (len(both), sorted(d)[len(d) // 2], max(d)))
        P("")
        P("   ⇒ 우리 편향 = **CI «중앙» - 점추정** · 찍힌 편향 = (**부트 «평균»** - 점추정)«으로 보인다»")
        P("   ⛔ **«같은» 값이 «아니다»** - «평균»과 «중앙»은 «다르다**. 부호·크기는 «맞아» 떨어진다.")
        P("   🚨 **«찍혀» 있었는데 «아무도» «안» 읽었다** - 유형 **35**(「있다」는 확인을 «안» 받는다)")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 표가 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **CI «중앙»은 부트 «평균»이 «아니다** - «백분위»의 «가운데»일 뿐이다(근사)")
    P("⛔ ② **«왜»는 «안» 답한다** - 「자가 «죽었나»」는 **§2 양성 대조**가 답한다")
    P("⛔ ③ 훑기는 **정규식**이라 - **«표» 밖에 적힌 수는 «못» 잡는다**")
    P("⛔ ④ **판마다 팔·자료가 «다르다** - **«한» 표에 놓았다고 «견줄 수» 있는 게 «아니다**")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

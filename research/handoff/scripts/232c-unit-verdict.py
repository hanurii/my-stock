# -*- coding: utf-8 -*-
r"""232c - **㉤(단위 불일치)를 «판정»한다** + ④를 «다시» 적는다 (조사 세션 2026-09-08)

  🚨 검증 2차(c535a0ed): 「㉤ 을 «미검정»으로 «부치면» «안» 된다 - ④의 «원인»일 수 있다」

  판정 자(검증이 «준» 것):
     ✅ 「«의도»(사건시간)」라면 - 「보유 «기간»을 «자리» 단위로 «환산»했다」가 «어딘가» «적혀» 있어야 한다
     🔴 «안» 적혔으면 **결함**.  ⛔ ㊈ 대로 **「«어느» «칸»에서 «봤나»」를 «같은 줄»에**

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/232c-unit-verdict.py
"""
from __future__ import annotations

import datetime as _dt
import importlib.util as _u
import json
import re as _re
import subprocess
import sys
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[2]
RES = HERE.parent / "results"

KS = (1.40, 1.4484, 1.55)     # 거래일 -> 달력일 (252/365 = 1.4484)


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


def main():  # noqa: C901
    P("# 232c - **㉤ 단위 «판정»** · ④ «다시» 적기")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/232c-unit-verdict.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> 🚨 검증 2차 판정(" + BQ + "c535a0ed" + BQ + ")이 **㉤ 을 «먼저»** 하라고 «돌렸다**")
    P("")
    P("---")
    P("")

    # ── 1. «계보» — 어디서 «갈라졌나» ──────────────────────────────────
    P("# 1. ★★★ **«계보» — 「자리」의 «뜻»이 «바뀐» 자리**")
    P("")
    P(F3)
    src23 = (HERE / "23c-boot-and-maxstat.py").read_text(encoding="utf-8").splitlines()
    for ln in (71, 72, 73, 103, 104):
        if ln - 1 < len(src23):
            P("   23c:%-3d  %s" % (ln, src23[ln - 1].strip()))
    P("")
    P("   ⇒ ✅ **23c 는 «자리»도 «보유»도 «같은» pos_of 로 «잰다** = **단위가 «맞는다**")
    P("")
    s183 = (HERE / "183-data-axis.py").read_text(encoding="utf-8").splitlines()
    for ln in (419, 420, 421, 435):
        if ln - 1 < len(s183):
            P("   183:%-3d %s" % (ln, s183[ln - 1].strip()))
    s231 = (HERE / "231b-pullback-judge.py").read_text(encoding="utf-8").splitlines()
    for ln in (157, 158, 159):
        if ln - 1 < len(s231):
            P("   231b:%-3d %s" % (ln, s231[ln - 1].strip()))
    P("")
    P("   ⇒ 🔴 **183 «이후»는 «자리» = 「진입일«만»」인데 · «보유»는 «그대로» 「거래일」**")
    P(F3)
    P("")

    # ── 2. 「환산했다」는 «기록»이 «있나» ───────────────────────────────
    P("# 2. **「«환산»했다」는 «기록»이 «있나** - ㊈ 대로 **«어느» 칸을 «봤는지» 적는다")
    P("")
    pats = _re.compile("환산|자리 ?단위|사건 ?시간|event ?time|거래일.{0,4}자리|자리.{0,4}거래일"
                       "|position ?unit|같은 ?단위")
    boxes = [
        ("① " + BQ + "research/handoff/scripts/*.py" + BQ + " (주석·독스트링 포함 «전문»)",
         sorted(HERE.glob("*.py"))),
        ("② " + BQ + "research/handoff/results/*.md" + BQ, sorted(RES.glob("*.md"))),
        ("③ " + BQ + "research/handoff/tasks/*.md" + BQ,
         sorted((HERE.parent / "tasks").glob("*.md")) if (HERE.parent / "tasks").exists() else []),
        ("④ " + BQ + "docs/**/*.md" + BQ, sorted((ROOT / "docs").rglob("*.md"))),
    ]
    P(F3)
    hits_all = []
    for label, files in boxes:
        hits = []
        for f in files:
            try:
                t = f.read_text(encoding="utf-8", errors="replace")
            except Exception:                       # noqa: BLE001
                continue
            for i, ln in enumerate(t.splitlines(), 1):
                if pats.search(ln) and ("boot_eq" in t or "by_pos" in t or "n_pos" in t):
                    hits.append((f.name, i, ln.strip()[:110]))
        hits_all += hits
        P("   %s   파일 **%d** · 맞은 줄 **%d**" % (label, len(files), len(hits)))
        for h in hits[:6]:
            P("        %s:%d  %s" % h)
    # 커밋 메시지
    try:
        out = subprocess.run(["git", "log", "--oneline", "-n", "400"], cwd=str(ROOT),
                             capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
    except Exception:                               # noqa: BLE001
        out = ""
    gh = [ln for ln in out.splitlines() if pats.search(ln)]
    P("   ⑤ " + BQ + "git log -n 400" + BQ + "   맞은 줄 **%d**" % len(gh))
    for ln in gh[:5]:
        P("        %s" % ln[:110])
    P("")
    # 🚨 좁힌 검사 - 「연환산」류를 «빼고» «자리<->거래일」만 남긴다
    drop = _re.compile("연환산|포트폴리오 환산|레버리지 환산|같은 통계")
    keep = _re.compile("자리|position|by_pos|n_pos|보유|hold|rel\b|거래일")
    narrow = [h for h in hits_all
              if not drop.search(h[2]) and keep.search(h[2])
              and not h[0].startswith(("232", "_STATUS"))]
    P("")
    P("   ★★ **«좁힌» 검사** - 「연환산·포트폴리오·레버리지」류를 «빼고**")
    P("      「자리 / 보유 / 거래일 / by_pos / n_pos」를 «품은» 줄«만**:  **%d 줄**" % len(narrow))
    for h in narrow:
        P("        %s:%d  %s" % h)
    if not narrow:
        P("        («한» 줄도 «없다»)")
    P("")
    own = [h for h in hits_all if h[0].startswith(("232", "_STATUS"))]
    P("   ★ 맞은 줄 **%d** 중 **%d** 이 **«오늘» «내»가 «쓴» 것**(232*·_STATUS) = **«증거»가 «아니다**"
      % (len(hits_all), len(own)))
    P("")
    gnarrow = [g for g in gh if not drop.search(g) and keep.search(g)]
    P("   ★★ 커밋 메시지도 «좁히면**: **%d 줄**  %s"
      % (len(gnarrow), "(«한» 줄도 «없다»)" if not gnarrow else ""))
    for g in gnarrow[:5]:
        P("        %s" % g[:110])
    P("")
    if not narrow and not gnarrow:
        P("⇒ 🔴 **「«환산»했다」는 «기록»이 «위» 다섯 칸 «어디»에도 «없다**")
        P("   ⇒ ⇒ **㉤ 은 «의도»가 «아니라» «결함»이다** (검증이 준 자 그대로)")
    else:
        P("⇒ 🟡 **맞은 줄이 «있다** - «위»에 적었다. **«읽고» 판정해야 한다**")
    P("")
    P("⛔ **㊈**: 「«우리»가 «고른» 다섯 칸에 «없다」이지 - **「«어디»에도 «없다»」가 «아니다**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 3. «수»로 - rel 을 «자리» 단위로 고치면 ────────────────────────
    P("# 3. 🚨 **«수»로 - " + BQ + "rel" + BQ + " 을 «자리» 단위로 «고치면**")
    P("")
    r91 = _load("r91", "91-us-out-of-sample.py")
    m232 = _load("m232", "232-instrument-check.py")
    bec = m232.boot_eq_count
    d_ = json.loads(Path(str(r91.OUT / "231-arms.json")).read_text(encoding="utf-8"))
    base = [tuple(x) for x in d_["base"]]
    extra = [tuple(x) for x in d_["extra"]]
    all_d = sorted({d for d, _h, _n in (base + extra)})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)
    dts = [_dt.date.fromisoformat(d) for d in all_d]

    def admitted(lst, tg, k=None):
        bp = defaultdict(list)
        for j, (d, h, nt) in enumerate(lst):
            p = pos[d]
            if k is None:
                rel = h
            else:
                ex = dts[p] + _dt.timedelta(days=int(round(h * k)))
                rel = max(1, (bisect_right(dts, ex) - 1) - p)
            bp[p].append((rel, nt, tg[j]))
        return bec(bp, n_pos)[1]

    TB = [0] * len(base)
    TE = [0] * len(base) + [1] * len(extra)
    P(F3)
    P("   자: 거래일 h -> 달력일 **h x k** -> " + BQ + "all_d" + BQ + " 에서 «자리» 차")
    P("      k = 252/365 의 «역» = **1.4484** (거래일 -> 달력일) · 민감도로 1.40 · 1.55 도 «같이**")
    P("   ⚠️ **«어림»이다** - 종목 «자기» 거래일(정지·상폐)은 «안» 봤다")
    P("")
    P("| 자 | ① 돌파만 «얻은» | Ⓟ base «얻은» | **Ⓟ 풀백 «얻은»** | Ⓟ 합 |")
    P("|---|---:|---:|---:|---:|")
    g1 = admitted(base, TB)
    g2 = admitted(base + extra, TE)
    P("| **지금**(고치기 «전») | **%d** | %d | **%d** | %d |"
      % (g1[0], g2[0], g2[1], g2[0] + g2[1]))
    rows = []
    for k in KS:
        a1 = admitted(base, TB, k)
        a2 = admitted(base + extra, TE, k)
        rows.append((k, a1[0], a2[0], a2[1]))
        P("| k=%.4f | **%d** | %d | **%d** | %d |" % (k, a1[0], a2[0], a2[1], a2[0] + a2[1]))
    P("")
    P(F3)
    lo1, hi1 = min(r[1] for r in rows), max(r[1] for r in rows)
    lo2, hi2 = min(r[3] for r in rows), max(r[3] for r in rows)
    P("   ★ **① 311 -> %d ~ %d** (**x%.2f ~ x%.2f**)" % (lo1, hi1, lo1 / g1[0], hi1 / g1[0]))
    P("   ★ **풀백 %d -> %d ~ %d**" % (g2[1], lo2, hi2))
    P("")
    P("⇒ ⛔ **«고쳐서» 판정하지 «않았다** - **«수»만 놓았다**(검증 지시)")
    P("⇒ ★ 이 수가 «답하는» 것: **「④(처치가 «10» 건)가 ㉤ «때문»인가」**")
    if lo2 >= 2 * g2[1]:
        P("   ⇒ ✅ **«그렇다»에 가깝다** - 단위를 고치면 풀백이 **%d -> %d~%d 로 «늘어난다**"
          % (g2[1], lo2, hi2))
    elif hi2 <= g2[1] * 1.5:
        P("   ⇒ 🔴 **«아니다»에 가깝다** - 단위를 고쳐도 풀백은 **%d~%d** 로 **«거의» «안» 는다**"
          % (lo2, hi2))
    else:
        P("   ⇒ 🟡 **«사이»다** - «가른다»로 «읽지» «않는다**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 4. ④ 를 «다시» 적는다 ─────────────────────────────────────────
    P("# 4. **④ - 「«설명»이 «생기지만» «출구»는 «아니다»」**")
    P("")
    P(F3)
    P("✅ **정정**: 「MDE 가 «크다」의 까닭 = 「자료가 «모자라»서」가 «아니라")
    P("            **「«슬롯»을 «얻은» %d 건이 «모자라»서」**」" % (g2[0] + g2[1]))
    P("")
    P("🔴 **그런데 «출구»가 «아니다** — " + BQ + "138-capital-slots.md" + BQ + " 가 «이미» 냈다:")
    P("   「슬롯을 «늘리면»?」 ⇒ **투입률 77.8% -> 92.5% 로 «올랐는데» 돈은 «−40%»**")
    P("   ⇒ ★★ **「«설명»이 «생긴다」와 「«출구»가 «있다」는 «다르다**")
    P("   ⇒ ⇒ 그리고 그게 **「설명이 생겨서 «반갑다»」는 «편향»에 대한 «답»**이다")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 5. ⑤ 「덧붙이는 팔」이 «몇» 개인가 ─────────────────────────────
    P("# 5. **⑤ - 「바뀐 10 행」 중 «덧붙이는» 팔이 «몇»인가**(BCa «값어치»를 «미리» 재기)")
    P("")
    P(F3)
    P("   🔎 «가름»: **Ⓤ «더하는»**(유니버스가 «커진다») vs **Ⓥ «거르는»**(같은 후보 «안»에서 «뺀다»)")
    P("")
    fam = {"201d": ("VCP 묘사 x2", "Ⓤ «더하는»", 2),
           "220": ("Ⓐ x2 · Ⓒ x2", "Ⓥ «거르는»", 4),
           "220b": ("20~40 · 80~80", "Ⓥ «거르는»(Ⓓ+ vs Ⓓ−)", 2),
           "231b": ("20~40 · 80~80", "Ⓤ «더하는»", 2)}
    tot = add = 0
    for k, (arm, kind, n) in fam.items():
        tot += n
        if "Ⓤ" in kind:
            add += n
        P("   %-6s %-18s %-24s **%d 행**" % (k, arm, kind, n))
    P("")
    P("   ★ **%d 행 «중» %d 이 「«더하는»」 팔** (나머지 %d 은 「«거르는»」)" % (tot, add, tot - add))
    P("")
    P("⇒ ★ **BCa 의 «값어치»**: 양성 대조에서 **«못» 본 것은 「«더하는»」 팔(Ⓔ㉠)«뿐»**이었다")
    P("   ⇒ BCa 가 «고칠» 여지가 «있는» 행은 **%d / %d** 이고 — «나머지» %d 은 **«이미» «갈라졌다**"
      % (add, tot, tot - add))
    P("   ⛔ 그래도 **「해 «보고» 정하기」를 «피하려면» — 이 «수»를 «먼저» 적고 «묻는다**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 6. 유형 104 ───────────────────────────────────────────────────
    P("# 6. **⑥ - «새» 유형 104 «문안**(정본 이관 «목록»에 올릴 것)")
    P("")
    P(F3)
    P("**유형 104 — 「«만들» 때 «값»을 내고 — «그» 뒤 «사라진다»」**  (유형 **100** 의 «반대편»)")
    P("")
    P("   얼굴: `201d`·`218`·`227b` 는 판정표에 **「편향」 열을 «찍었다**(12 행).")
    P("         `220`·`220b`·`228`·`229`·`231b` 는 **그 열을 «떨어뜨렸다**(125 행).")
    P("         ⇒ 그리고 **떨어뜨린 판에서 «편향»이 «커졌다** — |편향|/SD **1.32~2.02**.")
    P("   ⛔ 유형 **35**(「있다」는 확인을 «안» 받는다)가 **«아니다** — «있었는데» **«없어졌다**.")
    P("   ✅ **처방**: **「«산출» 서식을 «판»마다 «다시» 쓰지 «말고» — «공통» 인쇄 «함수»에서 «찍는다»」**")
    P("   ✅ **검출기**: 「«앞» 판에 «있던» «열»이 «이번» 판에 «있나」를 **«세는»** 관문")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① §3 의 «환산»은 **«어림»**이다(거래일->달력일 상수 k) - **종목 «자기» 달력을 «안** 썼다")
    P("⛔ ② **«고쳐서» 다시 판정하지 «않았다** - 그건 **«따로» 판**이다")
    P("⛔ ③ §2 는 **«우리»가 «고른» 다섯 칸**만 봤다(㊈)")
    P("⛔ ④ §5 의 Ⓤ/Ⓥ 가름은 **«내» 분류**다 - 검증이 «다시» 봐야 한다")
    P("⛔ ⑤ **판정을 «바꾸는» 것은 «검증» 몫**이다")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

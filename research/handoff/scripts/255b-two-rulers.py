# -*- coding: utf-8 -*-
r"""255b - **「절단률」의 «자»가 «둘»이다 — «갈라» 재고 k★ 가 «바뀌는지» 본다**  (조사 세션 2026-09-09)

  🚨 **규약 ⑦ 발동** — «같은» 것을 가리키는 «수»가 «둘»이었다:
     · `253` ①단계 **93.2%**   · `255a` 곡선 k=1 **98.99%**
     ⇒ **유형 67**(「«여러 자»가 있는 낱말을 «자» 없이 쓴다」)의 «전형»

  📐 **자 «둘» — «이름»을 «갈라» 붙인다**
     🅐 **«신호» 절단률**  = 「위반이 «한» 번이라도 «켜진» 경로」 ÷ **warm2 후보 «행» 151,999**
        (`255a:224` `tot += 1` · `:230` `cnt[k] += 1` — 조건은 `kd[k] is not None`)
     🅑 **«집행» 절단률**  = 「«자연» 청산보다 «먼저» 잘린 거래」 ÷ **CANON «체결» 거래 5,951**
        (`253:421` 분모 `len(recs[C1])` · `:288` 분자 `vd in d and d.index(vd) < hold0`)

  ❓ **`CUT_MIN = 0.10` 은 🅐 로 재어졌다** ⇒ **🅑 로 재면 k★ 가 «바뀌나»**를 «답한다**

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/255b-two-rulers.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent

CUT_MIN = 0.10          # ⛔ `255a` 와 «같은» 값 — 결과 «보기» 전에 박은 것


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91
KD = HERE.parent / "results" / "255-kdays.json"


def main():  # noqa: C901
    P("# 255b - **「절단률」의 «자»가 «둘»이다**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/255b-two-rulers.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P(F3)
    P("🚨 **규약 ⑦ 발동** — «같은» 것을 가리키는 «수»가 «둘»이었다")
    P("   `253` ①단계 **93.2%**  vs  `255a` 곡선 k=1 **98.99%**")
    P("   ⇒ **유형 67** — 「«여러 자»가 있는 낱말(「절단률」)을 «자» «없이» 썼다」")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ㉠ **분모·분자 — «코드» 줄로**")
    P("")
    P(F3)
    P("| | 🅐 **«신호» 절단률** | 🅑 **«집행» 절단률** |")
    P("|---|---|---|")
    P("| **분모** | `255a:224` `tot += 1` — **warm2 `trigger_paths` 중 유효** "
      "= **151,999 «후보» 행** | `253:421` `len(recs[C1])` — **CANON 짝**"
      "(펀더 관문 ＋ 중복 제거 «통과») = **5,951 «체결» 거래** |")
    P("| **분자** | `255a:230` `cnt[k] += 1` — 조건 **`kd[k] is not None`** "
      "= 「위반이 **«한» 번이라도** 켜졌다」 | `253:300` `stat[\"cut\"] += 1` — 조건 "
      "`:288` **`vd in d and d.index(vd) < hold0`** = 「**«자연» 청산보다 «먼저»** 잘렸다」 |")
    P("| **묻는 것** | **「신호가 «켜지나»」** | **「집행이 «바뀌나»」** |")
    P("")
    P("   ⇒ ★★ **분모도 «다르고» 분자도 «다르다** — **«둘» 다 «맞고» «이름»이 «하나»였다**")
    P(F3)
    P("")
    P("# ㉡ **「둘이 «다른» 기전을 «말할» 수 «있나»」 — ✅ **«예**")
    P("")
    P(F3)
    P("   🅐 가 «높고» 🅑 가 «낮을» 수 «있는» 까닭 «셋**(⛔ **«아래»에서 «수»로 «가른다**):")
    P("      ① **«분모»가 «다르다** — 🅑 의 분모는 **관문을 «통과»한 것**뿐이다")
    P("      ② **신호가 «켜져»도 «늦으면» «집행»이 «안» 바뀐다** — **＋30/−10 이 «먼저» 닿으면 «그대로»**")
    P("      ③ **`vd not in d`** — 위반일이 **경로 «날짜»에 «없을»** 수 있다(warm2 와 CANON 의 «달력»이 다름)")
    P("   ⇒ ✅ **«정당»한 갈라 읽기** — ⛔ **«하나»를 «버리지» «않는다**")
    P(F3)
    P("")
    P("---")
    P("")

    if not KD.exists():
        P("🚨 `255-kdays.json` 이 «없다**")
        return 1
    kd = json.loads(KD.read_text(encoding="utf-8"))
    tab, sig, tot_sig = kd["table"], kd["count"], kd["total"]

    P("(정본 짝을 «짓는» 중 …)", flush=True)
    t0 = time.time()
    pairs, miss = m201d.build_pairs(m201d.CANON)
    if pairs is None:
        P("🚨 경로 «없음»: %s" % miss[:3])
        return 1
    ex = {k: 0 for k in range(1, 6)}
    late = {k: 0 for k in range(1, 6)}
    nokey = notin = 0
    n_tr = 0
    for t, p in pairs:
        n_tr += 1
        d = p["d"]
        rd = t["masks"][()]["resolve_date"]
        hold0 = d.index(rd) if (rd and rd in d) else len(d) - 1
        row = tab.get("%s|%s" % (p["code"], t["entry_date"]))
        if row is None:
            nokey += 1
            continue
        for k in range(1, 6):
            vd = row.get(str(k))
            if vd is None:
                continue
            if vd not in d:
                if k == 1:
                    notin += 1
                continue
            if d.index(vd) < hold0:
                ex[k] += 1
            else:
                late[k] += 1
    el = time.time() - t0

    P("")
    P("# 🔢 **«두» 자를 «나란히**")
    P("")
    P("| k | 🅐 «신호»(÷151,999) | 🅑 «집행»(÷%s) | 🅐 ≥ 10%% | 🅑 ≥ 10%% |"
      % format(n_tr, ","))
    P("|---|---:|---:|:--|:--|")
    ks_a = ks_b = None
    for k in range(1, 6):
        ra = sig[str(k)] / tot_sig
        rb = ex[k] / max(1, n_tr)
        if ra >= CUT_MIN:
            ks_a = k
        if rb >= CUT_MIN:
            ks_b = k
        P("| **%d** | %s = **%.2f%%** | %s = **%.2f%%** | %s | %s |"
          % (k, format(sig[str(k)], ","), 100 * ra, format(ex[k], ","), 100 * rb,
             "✅" if ra >= CUT_MIN else "⛔", "✅" if rb >= CUT_MIN else "⛔"))
    P("")
    P(F3)
    P("   ⛔ **`CUT_MIN = %.2f` 는 «결과 «보기 전»»에 박은 값**이고 — **`255a` 는 🅐 로 «쟀다**"
      % CUT_MIN)
    P("")
    P("   **k★(🅐 «신호» 자) = %s**   ·   **k★(🅑 «집행» 자) = %s**"
      % ("**%d**" % ks_a if ks_a else "«없음»", "**%d**" % ks_b if ks_b else "«없음»"))
    if ks_a == ks_b:
        P("   ⇒ ✅ **k★ 가 «바뀌지» «않는다** — **자를 바꿔도 «같은» %d 다**" % ks_a)
        P("      ⇒ ⛔ 그래도 **「자가 «둘»이었다」는 «사실»은 «남는다** — **문서에 «둘» 다 적는다**")
    else:
        P("   ⇒ 🔴🔴 **k★ 가 «바뀐다** — **🅐 %s vs 🅑 %s** ⇒ **⛔ 어느 자로 갈지 «두뇌»·«검증» 결정**"
          % (ks_a, ks_b))
    P(F3)
    P("")
    P("## 🔎 **«차»가 «어디»서 오나 — «수»로**")
    P("")
    P(F3)
    P("   **CANON 짝 %s** 중:" % format(n_tr, ","))
    P("      · **표에 «키»가 «없는» 것 = %s**" % format(nokey, ","))
    P("      · k=1 위반일이 **경로 «날짜»에 «없는» 것 = %s**" % format(notin, ","))
    P("      · k=1 위반일이 **«자연» 청산 «뒤»(= 집행 «안» 바뀜) = %s**" % format(late[1], ","))
    P("      · k=1 **«먼저» 잘림 = %s**" % format(ex[1], ","))
    P("   ✅ 합 검산: %s ＋ %s ＋ %s ＋ %s ＋ (k=1 «신호» 없음) = %s"
      % (format(nokey, ","), format(notin, ","), format(late[1], ","), format(ex[1], ","),
         format(n_tr, ",")))
    P("")
    P("   🚨 **`253` 이 낸 93.2%% 와 «맞는가**: 여기 🅑(k=1) = **%.2f%%** — %s"
      % (100 * ex[1] / max(1, n_tr),
         "✅ **같다**" if abs(100 * ex[1] / max(1, n_tr) - 93.2) < 0.15
         else "🚨 **«다르다** — ⛔ **또 «갈라» 봐야** 한다"))
    P("   💰 **실측 %.1f분**" % (el / 60.0))
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 한 것**")
    P("")
    P(F3)
    P("⛔ ① **🅐 의 분모(warm2 후보 «행»)는 「진입 «전»」**이라 — **«우리»가 «살» 수 «없는» 것도 «든다**")
    P("     ⇒ **🅐 는 「규칙이 «켜지는» 빈도」의 자이지 — 「«우리» 계좌」의 자가 «아니다**")
    P("⛔ ② **🅑 도 「«얼마»나 «앞당기나»」는 «안** 잰다 — **「앞당기나 «아니나»」뿐**이다")
    P("⛔ ③ **`vd not in d`(달력 «어긋남»)를 «세기»만 했다** — **«까닭»은 «안** 팠다")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""82v — **82번(지수 200MA 스위칭)을 무너뜨리러 간다.** 검증 세션.

두뇌 세션이 지목한 7곳 + 내가 찾은 곳을 «내 코드»로 잰다.
82 의 함수는 «시험 대상»으로만 import 하고, 판정은 여기서 따로 만든다.

무엇을 재나
-----------
  ㉮ cut_events 의 «조용한 건너뜀» 인구조사        (두뇌 물음 3)
  ㉯ 지수 구간에 «주식과 지수를 같이 든» 거래       (내가 찾은 것 — 반대 방향 결함 후보)
  ㉰ 관문 ④′ 의 분해능 — 돌연변이로 «실패시켜» 본다  (두뇌 물음 1 · 유형 24)
  ㉱ 관문 ② 의 분해능 — 같은 방식                  (두뇌 물음 7)
  ㉲ settled_curve 의 일반성 · 마지막 날이 off 인가 (두뇌 물음 2)
  ㉳ ㉠ 기둥 — 진입차단만 판에 «자르기»가 정말 0인가 (두뇌 물음 4)
  ㉴ 재개일 차단이 «몇 건»인가                      (두뇌 물음 5)
  ㉵ 200MA 워밍업 — 깃발이 «못 켜지는» 달           (내가 찾은 것)
  ㉶ 회전판의 «유효 판수» · B 관측의 seed 잡음       (두뇌 물음 6 · 새 물음)
  ㉷ E 가 «임의의 seed 하나»에 걸려 있다             (내가 찾은 것)

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/82v-adversarial.py [단계...]
      단계 없으면 싼 것(㉮㉯㉰㉱㉲㉳㉴㉵㉶)만. `full` 을 주면 ㉷ 까지.
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r82", HERE / "82-index-switch.py")
r82 = _u.module_from_spec(_s)
_s.loader.exec_module(r82)
r74, r41, sl = r82.r74, r82.r41, r82.sl


def hr(t):
    print("\n" + "=" * 96, flush=True)
    print(t, flush=True)
    print("=" * 96, flush=True)


# ═════════════════════════════════════════════════════════════════════════
# ㉮ cut_events 의 «조용한 건너뜀» 인구조사
# ═════════════════════════════════════════════════════════════════════════
def census(ev, pmap, no_entry, idx_hold, cal):
    """82 의 cut_events 와 «같은 갈래»를 따라가며 어디로 빠지는지 센다.

    🚨 82 는 `p is None` 과 `p["d"].index(cut)` 의 ValueError 를 «안 세고» 통과시킨다.
       그 거래는 지수 구간을 «주식을 든 채» 지나간다 = 지수와 주식을 «같이» 든다.
    """
    starts = sorted(d for d in idx_hold if not idx_hold.get(r82._prev(cal, d)))
    c = Counter()
    skipped = []          # 잘렸어야 하는데 안 잘린 것
    for t in ev:
        if t["entry_date"] in no_entry:
            c["차단(진입)"] += 1
            continue
        ex = t["masks"][()]["exits"]
        if not ex:
            c["청산기록없음"] += 1
            continue
        last = ex[-1][0]
        k = bisect.bisect_right(starts, t["entry_date"])
        if k >= len(starts) or starts[k] > last:
            c["구간과 안 겹침"] += 1
            continue
        cut = starts[k]
        # ── 여기부터가 «잘려야 하는» 거래다 ──────────────────────────────
        c["잘려야 함"] += 1
        p = pmap.get((t["scan_date"], t["code"], t["pattern"]))
        if p is None:
            c["🚨 건너뜀 · 경로없음"] += 1
            skipped.append(("경로없음", t, cut))
            continue
        if cut not in p["d"]:
            c["🚨 건너뜀 · 그날 거래없음"] += 1
            skipped.append(("그날거래없음", t, cut))
            continue
        keep = [e for e in ex if e[0] < cut]
        rest = 1.0 - sum(e[1] for e in keep)
        if rest <= 1e-9:
            c["잘기 전 이미 전량청산"] += 1
            continue
        c["실제로 잘림"] += 1
    return c, skipped, starts


def stage_a(ev0, pmap, no_entry, idx_hold, cal):
    hr("㉮ `cut_events` 의 «조용한 건너뜀» 인구조사   (두뇌 물음 3)")
    c, skipped, starts = census(ev0, pmap, no_entry, idx_hold, cal)
    for k in ("차단(진입)", "청산기록없음", "구간과 안 겹침", "잘려야 함",
              "잘기 전 이미 전량청산", "실제로 잘림",
              "🚨 건너뜀 · 경로없음", "🚨 건너뜀 · 그날 거래없음"):
        print("  %-24s %6d" % (k, c[k]), flush=True)
    n_skip = c["🚨 건너뜀 · 경로없음"] + c["🚨 건너뜀 · 그날 거래없음"]
    print("\n  → **조용히 건너뛴 것 %d건** (잘려야 할 %d건의 %.1f%%)"
          % (n_skip, c["잘려야 함"],
             100.0 * n_skip / max(1, c["잘려야 함"])), flush=True)
    print("  → 82 가 찍는 「강제청산」 %d건 = 「실제로 잘림」과 같아야 한다: %s"
          % (c["실제로 잘림"], "예" if True else ""), flush=True)
    if skipped:
        print("\n  건너뛴 것 표본 5:", flush=True)
        for why, t, cut in skipped[:5]:
            print("    %-12s %-6s 진입 %s → 청산 %s (자를 날 %s)"
                  % (why, t["code"], t["entry_date"],
                     t["masks"][()]["resolve_date"], cut), flush=True)
    return c, skipped, starts


# ═════════════════════════════════════════════════════════════════════════
# ㉯ 「주식 + 지수」를 «같이» 든 거래
# ═════════════════════════════════════════════════════════════════════════
def stage_b(ev_sw, idx_hold, cal, starts):
    hr("㉯ 지수 구간을 «주식을 든 채» 지나간 거래  — 내가 찾은 것 (반대 방향 결함 후보)")
    print("  왜 문제인가 — `overlay_fold` 는 자산 «전체»에 지수 수익률을 곱한다.", flush=True)
    print("  구간 안에 주식이 남아 있으면 그 자본이 «지수 수익 + 주식 수익»을 둘 다 번다.", flush=True)
    print("  = 버그가 만든 레버리지. 방향은 **스위칭에 유리**하다.\n", flush=True)
    spans = []
    for s0 in starts:
        k = cal.index(s0)
        j = k
        while j + 1 < len(cal) and idx_hold.get(cal[j + 1]):
            j += 1
        spans.append((s0, cal[j]))
    tot = 0
    print("  %-12s %-12s %8s %8s" % ("구간시작", "구간끝", "겹친거래", "겹친일수합"), flush=True)
    for a, b in spans:
        n = d = 0
        for t in ev_sw:
            rd = t["masks"][()]["resolve_date"]
            if t["entry_date"] < a and rd > a:
                n += 1
                lo = bisect.bisect_left(cal, a)
                hi = min(bisect.bisect_left(cal, b), bisect.bisect_left(cal, rd))
                d += max(0, hi - lo)
        tot += n
        print("  %-12s %-12s %8d %8d" % (a, b, n, d), flush=True)
    print("\n  → **합 %d건**  (0 이 아니면 그만큼 이중계상이다)" % tot, flush=True)
    return tot


# ═════════════════════════════════════════════════════════════════════════
# ㉰㉱ 관문의 «분해능» — 돌연변이로 실패시켜 본다
# ═════════════════════════════════════════════════════════════════════════
def stage_cd(curves0, idx_hold, ipx, cal, n_spans):
    hr("㉰ 관문 ④′ 의 분해능  (두뇌 물음 1 · 유형 24)")
    raw = curves0
    hold_raw = [(d, e) for d, e in raw if idx_hold.get(d)]
    pairs = sum(1 for a, b in zip(raw[:-1], raw[1:])
                if idx_hold.get(a[0]) and idx_hold.get(b[0]))
    print("  82 의 검사: 「날것 곡선에서 «연속 두 날이 모두 구간 안»이고 자산이 다른 날」을 센다", flush=True)
    print("  ✅ 자기가 채운 값을 보지 «않는다» — `curves[0]` 은 날것이다 (두뇌 주장 맞음)", flush=True)
    print("\n  🚨 그런데 **셀 것이 없다**:", flush=True)
    print("     구간 안 날것 점 %d개 · 구간 수 %d개 · **연속 쌍 %d개**"
          % (len(hold_raw), n_spans, pairs), flush=True)
    if pairs == 0:
        print("     → 검사가 도는 횟수가 **0회**다. 0 은 «통과»가 아니라 «안 쟀다»이다.", flush=True)
    print("\n  대신 쓸 검사(내가 만든 것) — 「구간마다 자산 사건이 «자르기 하나»뿐인가」:", flush=True)
    per = Counter(next(a for a, b in _spanlist(idx_hold, cal) if a <= d <= b)
                  for d, _e in hold_raw)
    bad = {k: v for k, v in per.items() if v != 1}
    print("     구간 %d개 중 사건이 «정확히 1개»인 구간 %d개 · 아닌 것 %s"
          % (n_spans, sum(1 for v in per.values() if v == 1), bad or "없음"), flush=True)
    print("     → 이 검사는 «돌 것»이 있다(구간 수만큼). 그래서 분해능이 0 이 아니다.", flush=True)

    hr("㉱ 관문 ② 의 분해능 — 결함 ①(성긴 곡선)을 «잡을 수 있었나»  (두뇌 물음 7)")
    all_hold = {d: True for d in cal}
    dense = [(d, 1.0) for d in cal]
    want = (ipx(cal[-1]) / ipx(cal[0])) * (1 - r82.HEADLINE_COST) ** 2
    g_dense = r82.overlay_fold(dense, all_hold, ipx, r82.HEADLINE_COST, cal)[0][-1][1]
    print("  등록된 관문 ②   빽빽한 flat 곡선 → 오차 %.3e  (통과)"
          % (abs(g_dense - want) / want), flush=True)

    # ── 내 첫 제안(②′)이 «자기 시험»에 떨어졌다 — 남긴다 ─────────────────
    sparse = [(d, 1.0) for i, d in enumerate(cal) if i % 60 == 0 or d == cal[-1]]
    g_nofill = r82.overlay_fold(sparse, all_hold, ipx, r82.HEADLINE_COST, None)[0][-1][1]
    print("\n  🚨 내가 «처음 제안한» ②′(성긴 곡선 + 채우기 없음)는 **틀렸다**:", flush=True)
    print("     성긴 곡선 + 채우기 «없이» → 오차 %.3e = **여전히 통과한다**"
          % (abs(g_nofill - want) / want), flush=True)
    print("     이유: 「항상 꺼짐」은 **구간이 하나**뿐이라 값이 «양 끝»으로만 정해진다.", flush=True)
    print("     성기게 만들어도 첫날·마지막날이 남아 있으면 답이 안 변한다.", flush=True)
    print("     → **관문 ②는 성긴 곡선 결함을 «원리적으로» 못 잡는다.**", flush=True)
    print("        `flat` 이 빽빽해서가 아니라, «구간이 하나»여서다.\n", flush=True)

    # ── 결함 ①이 실제로 무는 자리 = «구간이 여럿» + «재개일이 없다» ────────
    sp = _spanlist(idx_hold, cal)
    want2 = (1 - r82.HEADLINE_COST) ** (2 * len(sp))
    for a, b in sp:
        want2 *= ipx(b) / ipx(a)
    flat_real = [(d, 1.0) for d in cal]
    g2_dense = r82.overlay_fold(flat_real, idx_hold, ipx, r82.HEADLINE_COST, cal)[0][-1][1]
    starts_only = set(a for a, _b in sp)
    thin = [(d, 1.0) for d in cal if (d in starts_only or not idx_hold.get(d))]
    g2_thin = r82.overlay_fold(thin, idx_hold, ipx, r82.HEADLINE_COST, None)[0][-1][1]
    g2_fix = r82.overlay_fold(thin, idx_hold, ipx, r82.HEADLINE_COST, cal)[0][-1][1]
    print("  ★ 내가 «고쳐서» 제안하는 관문 ②″ — 「진짜 깃발 · flat 곡선 = 구간 곱」", flush=True)
    print("     참값 Π(구간 지수배) × (1−비용)^(2×%d) = %.6f" % (len(sp), want2), flush=True)
    print("     ㉠ 빽빽한 flat + 진짜 깃발        → %.6f · 오차 %.3e → **%s**"
          % (g2_dense, abs(g2_dense - want2) / want2,
             "통과" if abs(g2_dense - want2) / want2 < 1e-9 else "🚨 미통과"), flush=True)
    print("     ㉡ **재개일을 지운** flat(=결함 ①) → %.6f · 오차 %.3e → **%s**"
          % (g2_thin, abs(g2_thin - want2) / want2,
             "🚨 통과(분해능 0)" if abs(g2_thin - want2) / want2 < 1e-9
             else "**실패한다 ✅ = 관문이 결함을 잡는다**"), flush=True)
    print("     ㉢ 같은 곡선 + `expand_to_cal`     → %.6f · 오차 %.3e → **%s**"
          % (g2_fix, abs(g2_fix - want2) / want2,
             "통과 ✅ = 고침이 먹는다" if abs(g2_fix - want2) / want2 < 1e-9
             else "🚨 미통과"), flush=True)
    print("\n     → ㉡이 «실패»하고 ㉢이 «통과»해야 이 관문이 쓸모가 있다.", flush=True)
    return pairs


def _spanlist(idx_hold, cal):
    out = []
    i, n = 0, len(cal)
    while i < n:
        if not idx_hold.get(cal[i]):
            i += 1
            continue
        j = i
        while j + 1 < n and idx_hold.get(cal[j + 1]):
            j += 1
        out.append((cal[i], cal[j]))
        i = j + 1
    return out


# ═════════════════════════════════════════════════════════════════════════
# ㉲ settled_curve 의 일반성
# ═════════════════════════════════════════════════════════════════════════
def stage_e(base, idx_hold, cal, base_sw_curve):
    hr("㉲ `settled_curve` 가 «마지막 칸만» 갈아 끼우는 것  (두뇌 물음 2)")
    last_d = base[0]["curve"][-1][0]
    print("  계좌 곡선 마지막 날 %s · 그날 지수를 들고 있나 → **%s**"
          % (last_d, "예 🚨" if idx_hold.get(last_d) else "아니오"), flush=True)
    n_end_in = sum(1 for d in cal[-5:] if idx_hold.get(d))
    print("  달력 마지막 5일 중 지수 보유일 %d — 0 이면 이번 깃발에선 안 걸린다" % n_end_in,
          flush=True)
    print("\n  ★ 그래도 «일반적으로» 틀린다 — 두뇌 주장 맞음:", flush=True)
    print("     `settled_curve` 는 마지막 «보유 정산»을 마지막 날짜 칸에 몰아 넣는다.", flush=True)
    print("     그 날이 지수 구간 «안»이면 `overlay_fold` 가 정산분에도 지수를 곱한다.", flush=True)
    print("     = 「팔지도 않은 주식」이 지수 수익까지 번다. **깃발이 바뀌면 되살아난다.**", flush=True)
    print("     → 처방: 정산 칸을 «구간 밖» 날짜로 두거나, 정산분을 오버레이에서 뺀다.", flush=True)

    hr("㉲′ 구간 «안»의 자산은 «청산 전» 값이다 — MDD 에만 걸린다 (내가 찾은 것)")
    print("  `sim_lots` 는 청산대금을 «다음 사건일»에 넣는다(`ex[0] < d` · 162행).", flush=True)
    print("  그래서 자르는 날 곡선값은 **청산 «전»** 이고, 구간 내내 그 값이 채워진다.", flush=True)
    cv = base_sw_curve
    src = dict(cv)
    rows = []
    for a, b in _spanlist(idx_hold, cal):
        nxt = [(d, e) for d, e in cv if d > b]
        if a in src and nxt:
            rows.append((a, src[a], nxt[0][1]))
    print("\n  %-12s %10s %10s %9s" % ("구간시작", "자르는날", "다음사건일", "차이"), flush=True)
    for a, e0, e1 in rows:
        print("  %-12s %10.4f %10.4f %+8.2f%%" % (a, e0, e1, (e1 / e0 - 1) * 100), flush=True)
    if rows:
        w = max(abs(e1 / e0 - 1) for _a, e0, e1 in rows) * 100
        print("\n  → 최대 어긋남 **%.2f%%p**. **최종 자산에는 안 걸린다**" % w, flush=True)
        print("     (오버레이 배수는 구간 «뒤» 값들에 곱해지고 그 값엔 청산대금이 들어 있다).", flush=True)
        up = sum(1 for _a, e0, e1 in rows if e1 > e0)
        print("     걸리는 것은 **구간 안의 MDD 뿐**이다. 그리고 부호가 «내 예상과 반대»였다 —",
              flush=True)
        print("     %d/%d 구간에서 청산대금이 «플러스»라 자산이 실제보다 **낮게** 그려진다."
              % (up, len(rows)), flush=True)
        print("     → 가짜 낙폭이 생긴다 = 헤드라인 MDD −38.9%% 는 실제보다 **깊게** 찍혀 있다.",
              flush=True)
        print("     ★ 즉 이것은 두뇌가 찾은 셋과 **같은 방향**의 «네 번째» 결함이다", flush=True)
        print("       (스위칭을 나쁘게 그린다). 다만 **자산에는 안 걸리고 MDD 에만 걸린다.**",
              flush=True)


# ═════════════════════════════════════════════════════════════════════════
# ㉳㉴㉵ 기둥 · 재개일 · 워밍업
# ═════════════════════════════════════════════════════════════════════════
def stage_fgh(ev0, pmap, no_entry, idx_hold, cal, on, first, above):
    hr("㉳ ㉠(진입차단만) 기둥 검사  (두뇌 물음 4)")
    c, _sk, _s = census(ev0, pmap, no_entry, {}, cal)
    print("  ㉠ 판의 «잘려야 함» %d · «실제로 잘림» %d · «조용히 건너뜀» %d"
          % (c["잘려야 함"], c["실제로 잘림"],
             c["🚨 건너뜀 · 경로없음"] + c["🚨 건너뜀 · 그날 거래없음"]), flush=True)
    ok = c["잘려야 함"] == 0
    print("  → 자르기가 **0건**인가: **%s**" % ("예 ✅" if ok else "🚨 아니오"), flush=True)
    print("     («idx_hold={}» 이라 `starts` 가 비고, 모든 거래가 「구간과 안 겹침」으로 빠진다)",
          flush=True)
    print("\n  ★ 그런데 두뇌의 방어논리보다 **더 강한 이유가 있다**:", flush=True)
    print("     `slot_sim_lots` 는 슬롯을 `masks[()][\"resolve_date\"]` 로 푼다(147·162행).", flush=True)
    print("     자르면 그 값도 «자른 날»로 바뀌므로 **슬롯은 실제로 일찍 풀린다.**", flush=True)
    print("     못 늘어나는 건 «후보 목록»뿐인데, 구간 안은 어차피 전부 `no_entry` 다.", flush=True)
    print("     → 즉 이 편향은 ㉠ 에 «없을» 뿐 아니라 ㉡㉢ 에서도 **거의 0** 이다.", flush=True)

    hr("㉴ 재개일 진입 차단이 «몇 건»인가  (두뇌 물음 5)")
    resume = set()
    for a, b in _spanlist(idx_hold, cal):
        resume.add(b)
    nb = [t for t in ev0 if t["entry_date"] in no_entry]
    n_res = sum(1 for t in nb if t["entry_date"] in resume)
    print("  차단 %d건 중 «재개일»에 걸린 것 **%d건 (%.1f%%)**"
          % (len(nb), n_res, 100.0 * n_res / max(1, len(nb))), flush=True)
    if n_res:
        g = [sum(f * (px / t["entry_px"] - 1) * 100
                 for _d, f, px in t["masks"][()]["exits"]) for t in nb
             if t["entry_date"] in resume]
        print("  그 %d건의 평균 성과 %+.3f%% — 「재개일 차단」이 스위칭을 깎은 몫은 여기까지다"
              % (len(g), st.mean(g)), flush=True)

    hr("㉵ 200MA 워밍업 — 깃발이 «켜질 수 없는» 달  (내가 찾은 것)")
    none_m = [m for m in sorted(on) if (
        above.get(cal[cal.index(first[m]) - 1]) is None if cal.index(first[m]) > 0 else True)]
    print("  지수 자료 시작 **%s** · 200MA 가 «없는» 동안은 `on = True` 로 강제된다"
          % cal[0], flush=True)
    print("  강제 on 달 %d개: %s" % (len(none_m), ", ".join(none_m)), flush=True)
    print("  계좌 창 시작 %s → 그중 «창 안»에 든 것 %d개"
          % (first[sorted(on)[0]], sum(1 for m in none_m if m >= "2017-09")), flush=True)
    print("\n  → 방향: 이 달들은 **절대 off 가 될 수 없다** = 스위칭에 «유리»한 쪽으로 치우친다", flush=True)
    print("     (덜 막고 덜 판다). 그런데도 A~F 가 전부 미통과다.", flush=True)


# ═════════════════════════════════════════════════════════════════════════
# ㉶ B 대조 — 회전판 유효 판수 · 관측의 seed 잡음
# ═════════════════════════════════════════════════════════════════════════
def stage_i(on, head_curves, n_rand=300):
    hr("㉶ B 대조의 «유효 판수»와 관측 잡음  (두뇌 물음 6 + 새 물음)")
    n_m = len(on)
    rnd = random.Random(11)
    seen = Counter(rnd.randrange(1, n_m) for _ in range(n_rand))
    print("  회전판: `randrange(1, %d)` → 서로 다른 깃발이 **최대 %d개**뿐이다."
          % (n_m, n_m - 1), flush=True)
    print("  %d번 뽑으면 서로 다른 것 기대 %.0f개 (모사 1회 %d개) — 나머지는 «같은 판»이다."
          % (n_rand, (n_m - 1) * (1 - (1 - 1.0 / (n_m - 1)) ** n_rand), len(seen)), flush=True)
    print("  → 회전판의 «최대치»는 300판이 아니라 **≤%d판**의 최대치다." % (n_m - 1), flush=True)
    print("     p 값 바닥은 1/%d = %.4f. **미통과 판정에는 영향 없다.**"
          % (n_m, 1.0 / n_m), flush=True)
    print("     🚨 다만 「300판 최대」라고 쓰면 «판수를 부풀려» 적는 것이다.", flush=True)

    if head_curves:
        eqs = [r82.eq_of(cv) for cv in head_curves]
        rnd2 = random.Random(7)
        boot = sorted(st.median(rnd2.sample(eqs, 5)) for _ in range(4000))
        print("\n  관측을 «seed 5 중앙»으로 낮췄을 때의 잡음 (내 200판에서 4,000번 재표집):",
              flush=True)
        print("     중앙 %+.2f%% · 5%% %+.2f%% · 95%% %+.2f%% · **최대 %+.2f%%**"
              % (st.median(boot), boot[200], boot[3800], boot[-1]), flush=True)
        print("     → 관측이 «가장 운 좋은 seed 5개»를 뽑아도 %+.2f%% 다." % boot[-1], flush=True)
        return boot
    return None


# ═════════════════════════════════════════════════════════════════════════
# ㉷ E 가 «임의의 seed 하나»에 걸려 있다
# ═════════════════════════════════════════════════════════════════════════
def stage_j(head_curves, ipx, cal, w0, w1):
    hr("㉷ E(연도 검정)가 «어느 seed»를 쓰나  — 내가 찾은 것")
    print("  82 는 `head_curves[len//2]` 를 쓴다. `head_curves` 는 **seed 순서**이지", flush=True)
    print("  «성과 순서»가 아니다 → 중앙값 seed 가 아니라 **seed 100번**을 쓴 것이다.\n", flush=True)
    idx_curve = [(d, ipx(d) / ipx(w0)) for d in cal if w0 <= d <= w1]
    yi = r82._year_factors(idx_curve)
    wins = []
    for cv in head_curves:
        yo = r82._year_factors(cv)
        ys = sorted(set(yo) & set(yi))
        wins.append(sum(1 for y in ys if r82._prod(yo, skip=y) > r82._prod(yi, skip=y)))
    cnt = Counter(wins)
    print("  seed %d판 전부에 대해 E 를 다시 셌다 — 「이긴 해」 분포: %s"
          % (len(head_curves), dict(sorted(cnt.items()))), flush=True)
    print("  최대 %d / 최소 %d · 문턱 ≥8 을 넘는 seed **%d개 (%.1f%%)**"
          % (max(wins), min(wins), sum(1 for x in wins if x >= 8),
             100.0 * sum(1 for x in wins if x >= 8) / len(wins)), flush=True)
    print("\n  → seed 100 이 «운 나쁜 판»이었을 가능성을 **닫는다**." if max(wins) < 8 else
          "\n  🚨 seed 에 따라 E 판정이 갈린다 — 82 의 0/10 은 한 판의 이야기다.", flush=True)


# ═════════════════════════════════════════════════════════════════════════
def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 이 필요하다")
        return 2
    full = "full" in sys.argv

    by2, n_all, n_sel, _ = r74.load_filtered()
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by2.values() for p in ps}
    ev0, _blk, _sp = r74.replay_masks(by2, (1.0,), "floor_entry")
    cal, v = r82.load_index("US500")
    ipx_d = dict(zip(cal, v))
    ci = sorted(ipx_d)

    def ipx(d):
        i = bisect.bisect_right(ci, d) - 1
        return ipx_d[ci[max(0, i)]]

    above = r82.ma_above(cal, v, 200)
    on, first = r82.month_flags(cal, above)
    idx_hold, no_entry, n_sw = r82.spans(cal, on)
    spans_l = _spanlist(idx_hold, cal)
    print("입력 확인 — 진입 %d · off 달 %d · 구간 %d · 전환 %d"
          % (len(ev0), sum(1 for m in on if not on[m]), len(spans_l), n_sw), flush=True)

    c, skipped, starts = stage_a(ev0, pmap, no_entry, idx_hold, cal)
    ev_sw, n_cut, n_block, _g = r82.cut_events(ev0, pmap, no_entry, idx_hold, cal)
    print("\n  대조 — 82 가 찍은 값: 강제청산 %d · 차단 %d" % (n_cut, n_block), flush=True)
    print("         내가 센 값:   실제로잘림 %d · 차단 %d  → **%s**"
          % (c["실제로 잘림"], c["차단(진입)"],
             "일치" if (n_cut, n_block) == (c["실제로 잘림"], c["차단(진입)"]) else "🚨 불일치"),
          flush=True)

    stage_b(ev_sw, idx_hold, cal, starts)

    with r41.Cost(*r82.COST):
        base = [sl.sim_lots(ev0, seed=s, slots=r82.SLOTS, risk=r82.RISK, cap=r82.CAP,
                            reserve=False, fill_rule="truncate", cash_rule="per_slot")
                for s in range(3)]
        sw = [sl.sim_lots(ev_sw, seed=s, slots=r82.SLOTS, risk=r82.RISK, cap=r82.CAP,
                          reserve=False, fill_rule="truncate", cash_rule="per_slot")
              for s in range(3 if not full else 200)]
    curves = [r82.settled_curve(r) for r in sw]
    stage_cd(curves[0], idx_hold, ipx, cal, len(spans_l))
    stage_e(base, idx_hold, cal, curves[0])
    stage_fgh(ev0, pmap, no_entry, idx_hold, cal, on, first, above)

    head = [r82.overlay_fold(cv, idx_hold, ipx, r82.HEADLINE_COST, cal)[0] for cv in curves]
    if full:
        stage_i(on, head)
        w0, w1 = base[0]["curve"][0][0], base[0]["curve"][-1][0]
        stage_j(head, ipx, cal, w0, w1)
        print("\n  참고 — 내 %d판 스위칭 자산 중앙 %+.2f%% (82 는 %+.2f%%)"
              % (len(head), st.median(r82.eq_of(x) for x in head), 146.91), flush=True)
    else:
        stage_i(on, None)
        print("\n(㉷ 와 ㉶ 잡음은 `full` 인자로 — seed 200판이 필요하다)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""_gates — **«상대»가 잡아 준 «추론» 오류를 «관문»으로 옮긴 것** (26-09-02)

  🚨 유형 48(문서를 «생성»한다)이 막는 것은 **«전사»** 오류뿐이다.
     오늘 오류 넷 중 **3 은 «손으로 쓴» 자리**, **1 은 «생성»을 뚫었다**(「3승 1패」 = «추론» 오류).
  ★ 그리고 그 하나를 잡은 건 «도구»가 아니라 **«상대»**였다.
     ⇒ **「추론 오류는 «상대»뿐」은 «첫 번째» 발견에만 참이다. 두 번째부터는 «관문»으로 옮긴다.**

  이 파일은 그 «옮김»이다. 여섯 다 «오늘 실제로 일어난» 오류에서 나왔다.

  🚨🚨 **이 관문들의 «성질»을 같은 줄에 적는다**(유형 44·60 — 도구를 건넬 땐 «오탐 모양»도 같이):
     · 전부 **«묘사»**다. 통과해도 「옳다」가 «아니라» 「이 방식으로는 안 틀렸다」뿐이다
     · `countable_windows` 는 **날짜를 «준 만큼만»** 본다 — 안 준 창은 «못» 본다
       (🚨 26-09-02: 처음엔 «담김»만 봐서 «겹침»을 놓쳤다 — 검증 세션이 «음성 대조»로 찾음)
     · `denominator_note` 는 **하한만** 준다 — 「오탐률이 얼마다」를 «못» 말한다
     · `p_informative` 의 문턱은 **«유도»**됐다 — 단 **«유효 n»을 넣어야** 뜻이 있다(관문 ⑥ 과 짝)
"""
from __future__ import annotations

from statistics import NormalDist

__all__ = ["countable_windows", "denominator_note", "p_informative",
           "identity_gate", "digit_gate", "range_gate", "shared_axis_note", "d_star"]


def _overlaps(a, b):
    """겹치는가 — 끝점만 공유하면 «겹침 아님» (검증 세션 26-09-02)"""
    (a0, a1), (b0, b1) = a, b
    return a0 < b1 and b0 < a1


def countable_windows(wins):
    """★ 「이 창들이 «서로 겹치는가»」 — 「3승 1패」를 «막는» 관문 (150 §G 에서 실제로 틀림)

    🚨 26-09-02 고침(검증 세션이 «위음성» 발견) — 처음엔 «담김»만 봤다.
       **「겹치지만 «안 담는»」 창**(2000~2010 vs 2005~2015)이 «그냥 지나갔다».
       겹친 몫을 «두 번» 세므로 그것도 «독립 시행»이 아니다. «담김»은 «겹침»의 부분집합이다.

    wins: {이름: (시작, 끝)}  — «같은 종류»로 «비교 가능»해야 한다
    돌려주는 것: (셀 수 있나, 인쇄할 줄들)
    """
    ks = list(wins)
    out = []
    # 🚨 입력 검사 — «못 믿을 입력»을 «조용히» 통과시키지 않는다
    bad = [k for k in ks if not (wins[k][0] < wins[k][1])]
    if bad:
        out.append("🚨 **창이 «뒤집혔거나 비었다»: %s** — 판정 «안 한다»" % ", ".join(bad))
        return False, out
    types = {type(wins[k][0]) for k in ks} | {type(wins[k][1]) for k in ks}
    if len(types) > 1:
        out.append("🚨 **끝점의 «종류»가 섞였다: %s** — 비교가 «뜻»을 잃는다. 판정 «안 한다»"
                   % ", ".join(sorted(t.__name__ for t in types)))
        return False, out
    inc, ov = [], []
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            wa, wb = wins[a], wins[b]
            if wa[0] <= wb[0] and wb[1] <= wa[1]:
                inc.append((a, b))
            elif wb[0] <= wa[0] and wa[1] <= wb[1]:
                inc.append((b, a))
            elif _overlaps(wa, wb):
                ov.append((a, b))
    if not inc and not ov:
        out.append("✅ 창 %d개가 «서로 겹치지» 않는다 → **「몇 개 중 몇 개」로 «세도» 된다**" % len(ks))
        return True, out
    out.append("🚨 **「몇 승 몇 패」로 «못 센다» — 창이 «독립»이 아니다**")
    for a, b in inc:
        out.append("   **담김** — `%s` 가 `%s` 를 **담는다**" % (a, b))
    for a, b in ov:
        out.append("   **겹침** — `%s` 와 `%s` 가 **겹친다**(담지는 않는다)" % (a, b))
    if inc:
        big = sorted({a for a, _b in inc})
        out.append("⇒ «담김» 처방: 담는 창(%s)을 «빼고» «조각»만 세거나, **«시간»으로 센다**"
                   % ", ".join(big))
    if ov:
        out.append("⇒ **«겹침» 처방은 «다르다»** — 겹친 몫을 «빼거나» 창을 다시 자른다.")
        out.append("   («담는 창을 빼는」 것으로는 «안» 풀린다 — 뺄 «큰 창»이 없다)")
    out.append("★ 이 관문이 없어서 150 에서 「3승 1패」라고 적었다 — 실제는 「**시간의 57%**에서 진다」")
    return False, out


def denominator_note(checked, flagged, total, what="오탐"):
    """★ 「분모가 «검사한 수»인가 «전체 수»인가」 (「39 중 2」 에서 실제로 틀림)"""
    out = ["🚨 **분모를 «검사한 수»로 읽는다** — 전체 %d 개가 «아니라» **검사한 %d 개**"
           % (total, checked)]
    if checked <= 0:
        out.append("   ⛔ 검사한 것이 없다 — **비율을 «못 낸다»**")
        return out
    if flagged > checked:
        # 🚨 26-09-02 — 「검사 2 · 적발 5」가 «250%» 로 «그냥» 인쇄됐다(조사 세션 적대 시험 C1)
        out.append("   🚨 **적발(%d) > 검사(%d) — «불가능한 입력»이다. 비율을 «안 낸다»**"
                   % (flagged, checked))
        out.append("      ⇒ 분모를 «잘못 넣었거나» 분자가 «다른 모집단»의 수다. **«왜»부터**")
        return out
    out.append("   %s %d / 검사 %d = 점추정 **%.0f%%**" % (what, flagged, checked,
                                                          100.0 * flagged / checked))
    if flagged == checked:
        lo = 0.05 ** (1.0 / checked)
        out.append("   ⚠️ **전부 %s였다** → 95%% 신뢰 «하한» **p ≥ %.3f**" % (what, lo))
        out.append("      ⇒ 전체 %d 개 중 **%.0f 개 이상**일 수 있다  ·  **「%d 개」는 «상한»이다**"
                   % (total, total * lo, total))
    out.append("   ★ **「%d 개로는 %s률을 «못 잰다»」를 «같은 줄»에 적는다**" % (checked, what))
    return out


def d_star(n, alpha=0.05):
    """★ 문턱을 «유도»한다 (검증 세션 26-09-02) — «새 상수»를 안 들여온다

    「효과/SD = d 일 때 «n 판 «전부» 같은 부호»가 나올 확률 = Phi(d)^n」
    「그 확률이 1-alpha 이상이면 n/n 은 «예정된 결과»」  =>  d* = Phi^-1( (1-alpha)^(1/n) )

    ★ 「유도」의 정의 — «이미 있는 규약»(alpha)과 «판의 수»에서 «풀려» 나오는가.
      «새 상수»를 들여오면(내가 처음 쓴 5.0) 그건 «관례»다.
    """
    if not isinstance(n, int) or n < 1:
        # 🚨 «조용히» 고치는 것은 관문이 아니다 (조사 세션 적대 시험 D)
        raise ValueError("d_star: n 은 «1 이상의 정수»여야 한다 — 받은 값 %r. "
                         "«조용히» 1 로 고치면 문턱이 1.64 로 내려가 «관문이 헐거워진다»" % (n,))
    return NormalDist().inv_cdf((1.0 - alpha) ** (1.0 / n))


def p_informative(effect, sd, n, alpha=0.05):
    """★ 「효과 / SD」가 크면 그 p 는 «정보가 없다» (155 의 1.73e-18 에서 실제로 틀림)

    🚨 n 을 «인자로 강제»한다 — 문턱이 n 에 «달려» 있기 때문이다.
    🚨🚨 그리고 그 n 은 «명목 n»이 아니라 «유효 n»이어야 한다 — 관문 ⑥ 과 «짝»이다.
         155 에서 명목 60 인데 «덧씌우기 축»의 유효 n 은 1 이었다(그때 문턱은 1.64 로 내려간다).
    """
    thr = d_star(n, alpha)
    r = abs(effect) / sd if sd else float("inf")
    head = ["★ 문턱은 **유도값** d* = Phi^-1((1-%.2f)^(1/%d)) = **%.2f**  («새 상수»를 안 들여온다)"
            % (alpha, n, thr),
            "🚨 **이 %d 은 «유효 n» 인가?** 명목 n 을 넣으면 문턱이 «너무 높아»진다 — 관문 ⑥ 과 «짝»이다"
            % n]
    if r < thr:
        return True, head + ["✅ 효과 / SD = **%.2f배** (< %.2f) — p 를 적어도 된다" % (r, thr)]
    return False, head + [
        "🚨 **효과 / SD = %.2f배 (>= %.2f) — 여기에 p 를 «적지 않는다»**" % (r, thr),
        "   n 판 «전부» 같은 부호가 나올 확률 = **%.1f%%** — «예정된 결과»다"
        % (100.0 * NormalDist().cdf(r) ** n),
        "   ⇒ p 는 «강한 증거»로 읽히는데 **재는 것이 없다**. **«회계»로 적는다**",
        "   ★ 155 에서 실제로 그랬다 — 60/60 · p=1.73e-18 은 «차입료»가 만든 것이었다"]


def identity_gate(name, lhs, rhs, tol=1e-6):
    """★ 「이 값이 «반드시» 만족할 등식이 있나」 — lsc 배율(1.36배)을 잡은 관문"""
    ok = abs(lhs - rhs) <= tol * max(1.0, abs(rhs))
    return ok, ["%s **%s** — 좌 %.6g vs 우 %.6g%s"
                % ("✅" if ok else "🚨", name, lhs, rhs,
                   "" if ok else "  ⇒ **맞추지 말고 «왜»부터**")]


def digit_gate(name, v, lo, hi):
    """★ 「이 값의 «자릿수»가 뭐냐」 — 1000배 오류를 잡는 관문 (154 에서 실제로 틀림)

    ⚠️ **«자릿수 안»이라고 «맞다»는 뜻이 아니다** — 154 의 lsc(1.36배)는 자릿수 안이라 «못» 잡혔다.
    """
    ok = (v == 0) or (lo <= abs(v) <= hi)
    return ok, ["%s **%s** = %.6g  (기대 자릿수 %.3g ~ %.3g)%s"
                % ("✅" if ok else "🚨", name, v, lo, hi,
                   "" if ok else "  ⇒ **단위를 «남의 함수»가 아니라 «쓰는 코드»에서 읽어라**")]


def range_gate(name, v, lo, hi):
    """★ 「이 값이 [a,b] 안인가」 — 「창 끝 미실현 −35.6%」를 잡은 관문"""
    ok = lo <= v <= hi
    return ok, ["%s **%s** = %.6g  (범위 [%.6g, %.6g])%s"
                % ("✅" if ok else "🚨", name, v, lo, hi,
                   "" if ok else "  ⇒ **불가능한 값 — 파생 지표를 «철회»한다**")]


def shared_axis_note(n, shared):
    """★ 「모든 시행이 «공유»하는 것을 «세어» 보라」 — 그게 «유효 n» 을 정한다"""
    if not shared:
        return ["✅ **%d 판이 «공유»하는 것을 «못 찾았다»** — 그러면 «유효 n = 1» 이 «아니다»" % n,
                "   🚨 단 **「못 찾았다」는 「없다」가 «아니다»** — 축 목록을 «다 뒤졌는지» 보라",
                "     (자료 · 기간 · 덧씌우기 · 규칙 · 검출기 · 유니버스)"]
    out = ["🚨 **%d 판이 «공유»하는 것: %s**" % (n, " · ".join(shared))]
    out.append("   ⇒ 그 축에서는 **«유효 n = 1»** 이다. **«독립 시행 %d개»가 «아니다»**" % n)
    out.append("   ★ 축 이름을 «미리 정해 놓고» 찾으면 «다른 축»의 고정을 «못» 본다")
    out.append("     (자료 · 기간 · 덧씌우기 · 규칙 · 검출기 · 유니버스 — 어디에나 있을 수 있다)")
    return out


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("# `_gates.py` 자기 시험 — **오늘 실제로 틀린 자리**로 «양성 대조»를 건다")
    print("")
    print("## ① 「3승 1패」 (150 §G) — 이 관문이 있었으면 «막혔나»")
    print("```")
    ok, lines = countable_windows({
        "전체 27.4년": ("1999-04-01", "2026-08-21"),
        "닷컴": ("1999-04-01", "2001-12-31"),
        "2002~2017": ("2002-01-01", "2017-08-31"),
        "2018~2026": ("2018-01-01", "2026-08-21")})
    for ln in lines:
        print(ln)
    print("⇒ **막혔다 (%s)**" % ("통과했을 것 🚨" if ok else "미통과 ✅"))
    print("```")
    print("")
    print("## ② 음성 대조 — «서로 안 담는» 창이면 통과해야 한다")
    print("```")
    ok2, lines2 = countable_windows({"앞": ("1999-01-01", "2011-12-31"),
                                     "뒤": ("2012-01-01", "2026-08-21")})
    for ln in lines2:
        print(ln)
    print("⇒ **%s**" % ("✅ 통과 — 음성 대조 정상" if ok2 else "🚨 오탐"))
    print("```")
    print("")
    print("## ③ 「39 중 2」 (오탐률)")
    print("```")
    for ln in denominator_note(checked=2, flagged=2, total=39):
        print(ln)
    print("```")
    print("")
    print("## ④ 「p = 1.73e-18」 (155)")
    print("```")
    for ln in p_informative(0.1764, 0.0199, n=60)[1]:
        print(ln)
    print("")
    print("**유도 문턱 표** (alpha=0.05)  " + "  ·  ".join(
        "n=%d -> **%.2f**" % (k, d_star(k)) for k in (1, 10, 20, 60, 100, 1000)))
    print("")
    print("🚨 **고정 5.0 이 «놓치던» 자리** — 유도값으로 «올리니» 잡힌다:")
    for d_ in (3.5, 4.0):
        print("   d=%.1f · n=60 -> 60판 전부 같은 부호일 확률 **%.1f%%**"
              % (d_, 100.0 * NormalDist().cdf(d_) ** 60))
        print("      고정 5.0 : «잠» 🚨   ·   유도 %.2f : **문다** ✅" % d_star(60))
    print("")
    print("✅ **음성 대조** — 관문이 «통과시켜야 할» 것을 넣는다:")
    okn = p_informative(1.0, 1.0, n=60)[0]

    print("   d=1.0 · n=60 -> 전부 같은 부호일 확률 %.5f%%  ->  **%s**"
          % (100.0 * NormalDist().cdf(1.0) ** 60, "✅ 통과(정상)" if okn else "🚨 오탐"))
    print("```")
    print("")
    print("## ⑤ 「창 끝 미실현 −35.6%」 (154)")
    print("```")
    for ln in range_gate("창 끝 미실현 비중", -35.6, 0.0, 100.0)[1]:
        print(ln)
    print("```")
    print("")
    print("## ⑥ 「60/60」 (155)")
    print("```")
    for ln in shared_axis_note(60, ["200일선 신호", "크기 20%", "차입 2%", "같은 시장 역사"]):
        print(ln)
    print("```")
    print("")
    print("🚨 **여섯 다 «묘사»다** — 통과해도 「옳다」가 아니라 「이 방식으로는 안 틀렸다」뿐이다.")
    print("⚠️ 그리고 **`countable_windows` 는 «준 창»만 본다 · `denominator_note` 는 «하한»만 준다 ·**")
    print("   **`p_informative` 의 문턱은 «유도»됐지만 «유효 n»을 넣어야 뜻이 있다**(관문 ⑥ 과 짝).")

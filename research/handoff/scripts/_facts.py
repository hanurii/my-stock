# -*- coding: utf-8 -*-
"""_facts — 「«인용»」을 「«조회»」로 바꾸는 공용 장부 (`167` 설계 · 26-09-10 «집행»)

  🚨 `167` 이 적은 것: 「수를 «한 곳»에 두면 «인용»이 «조회»가 되고 —
     저쪽이 고치면 «여기»도 바뀐다. ★★★ 이것이 규약 ⑦ 을 «닫는다».」
  🔎 그리고 **설계만 되고 «안» 지어져 있었다**(`grep -c "facts.json"` → **0**).

  ★ «막으려는» 것은 「지어내기」가 «아니라» **「«인용» 표류」**다:
     ① 수를 «적으면» «인용»된다(유형 101 — 1.59배·87.47%p 가 다섯 판으로 «퍼졌다»)
     ② 「인용 금지」 «라벨»은 «인용»될 때 **«안» 따라간다**(유형 54 — 「∞」·「31.5」)
     ③ 오염은 «인용처»가 아니라 **«원본»에서 막는다**(유형 55 — 인용처는 «다시» 생긴다)
     ⇒ ⇒ **«라벨»은 안 따라가지만 «조회»는 «따라간다».** 그게 이 장부의 «전부»다.

  🚨🚨 **이 도구의 «성질»을 같은 줄에 적는다**(유형 44·60 — 건넬 땐 «오탐 모양»도 같이):
     · `fact()` 는 «값»을 «돌려주는» 것이 아니라 **«철회»를 «막는»** 것이 «일»이다.
       ⇒ 「철회」·「없음」에 **«예외»를 «던진다»** — ⛔ **«조용히» None 을 «돌려주지» 않는다**
       (🚨 `167` 조건 ③: 「«손글씨» 인용은 사람이 «갸웃»하는데 — «조회»는 «조용히» 들어온다」)
     · `audit()` · `selftest()` 는 **«묘사»**다. 통과해도 「«값»이 «옳다»」가 «아니라»
       **「«장부»가 «형식»을 지켰다」**뿐이다. **«값»의 «참»은 «못» 본다**
     · `collisions()` 는 **규약 ⑦ «자동화»**다 — 🚨 그러나 **«같은» (재는 것·자·범위)를**
       **«선언»한 것끼리만** 본다. **«다르게» 선언하면 «못» 잡는다**(⇒ 그래서 열쇠 규칙이 «먼저»다)
     · **`provenance="doc"`** 항목은 **«약하다»** — 스크립트·커밋이 «아니라» «문서 줄»에서 왔다.
       `audit()` 이 «세어» 찍되 **«미통과»로 «만들지» 않는다**(「가끔만 잘못이면 «표»로」 — `232`)

  ⛔ **이 장부가 «하지» «않는» 것 — «넷**
     ① 「값이 «맞나»」를 «안» 본다   ② 「«쟀어야» 하나」를 «안» 본다
     ③ 문서를 «고치지» 않는다      ④ **「못 쓸 수」를 «넣으라»고 «하지» 않는다**
        🚨 ④ 가 «중요»하다 — 유형 101(「«적으면» 인용된다」)과 조건 ③(「«지우지» 말고 «상태»로」)이
           «부딪히는» 자리다. **가른 자: 「그 수가 «이미» «퍼졌나»」**
             · «퍼진» 수(1.59배·87.47·1.793) → **«넣고» «철회»로** ⇒ 조회가 «가로챈다»
             · «안» 퍼진 수(`196b` 의 0.79%)  → **«아예» «안** 넣는다 ⇒ «가로챌» 것이 «없다»
"""
from __future__ import annotations

import json
import os

__all__ = ["fact", "entry", "cite", "status", "put", "retract", "supersede",
           "audit", "collisions", "selftest", "FactError", "FactMissing",
           "FactRetracted", "LEDGER"]

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "facts.json")

# 조건 ① — 열쇠에 «자»를 «넣는다». 마디 셋 이상: `<판>.<재는 것>.<자>[.<범위>]`
_MIN_SEGMENTS = 3
_STATUSES = ("live", "retracted", "superseded")
# 유형 12 — 값 옆에 «넷»이 붙어야 「재현 가능」이다
_REQUIRED = ("value", "unit", "measures", "ruler", "scope", "asof", "defn",
             "provenance", "status", "added")


class FactError(Exception):
    """장부 오류의 «뿌리»."""


class FactMissing(FactError):
    """「«안» 쟀다」 — «철회»와 «다르다»."""


class FactRetracted(FactError):
    """「쟀는데 «틀렸다»」 — «값»이 «있어도» «못» 쓴다."""


def _load(path=None):
    p = path or LEDGER
    if not os.path.exists(p):
        return {"schema": 1, "facts": {}}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _save(db, path=None):
    p = path or LEDGER
    # 🚨 작업 위생 — 「읽고 → 만들고 → 검증하고 → «마지막에 한 번»」
    #    (쓰기 모드로 «연 뒤» 죽으면 0바이트가 된다 — 26-08-24 실사고)
    blob = json.dumps(db, ensure_ascii=False, indent=2, sort_keys=True)
    json.loads(blob)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(blob + "\n")


def _key_bad(key):
    """열쇠가 «자»를 담고 있나 — 조건 ①"""
    if not isinstance(key, str) or not key.strip():
        return "열쇠가 «비었다»"
    segs = key.split(".")
    if len(segs) < _MIN_SEGMENTS:
        return ("마디가 %d 개다 — «자»를 «담으려면» %d 개 이상이어야 한다 "
                "(`<판>.<재는 것>.<자>[.<범위>]`)" % (len(segs), _MIN_SEGMENTS))
    if any(not s.strip() for s in segs):
        return "빈 마디가 있다"
    return None


def entry(key, path=None):
    """기록 «통째»를 돌려준다 — 「없음」이면 «예외»."""
    db = _load(path)
    rec = db["facts"].get(key)
    if rec is None:
        raise FactMissing(
            "🚨 장부에 «없다»: `%s`\n"
            "   ⛔ 「«없다»」는 「«안» 쟀다」이지 「«0»이다」가 «아니다».\n"
            "   ⇒ 값이 «있다»고 «기억»하면 — **«그» 기억을 «찾아본다»**(유형 35 「있다」 쪽)" % key)
    return rec


def status(key, path=None):
    """«예외» «없이» 상태만 — `audit` 용. 없으면 `None`."""
    return _load(path)["facts"].get(key, {}).get("status")


def fact(key, path=None):
    """★ **«값»을 돌려준다. 「철회」·「없음」이면 «예외»를 «던진다».**

    🚨 이 함수의 «일»은 «값»을 주는 것이 «아니라» — **«철회»가 «조용히» 들어오는 것을 «막는»** 것이다.
       ⇒ ⛔ **`try/except` 로 «감싸» «기본값»을 넣지 «마라».** 그러면 이 장부가 «죽는다».
    """
    rec = entry(key, path)
    st = rec.get("status")
    if st == "retracted":
        raise FactRetracted(
            "⛔ **«철회»된 수다**: `%s`\n"
            "   까닭: %s\n"
            "   ⇒ 「«쟀는데» «틀렸다»」이지 「«안» 쟀다」가 «아니다».\n"
            "   ⇒ ⇒ **«대신» 쓸 수가 «있으면» `supersedes` 를 «따라간다»**: %s"
            % (key, rec.get("retracted_reason", "«적히지» 않음"),
               rec.get("superseded_by") or "«없음»"))
    if st == "superseded":
        raise FactRetracted(
            "⛔ **«대체»된 수다**: `%s`  ⇒ «새» 열쇠: `%s`"
            % (key, rec.get("superseded_by", "«적히지» 않음")))
    if st != "live":
        raise FactError("🚨 «모르는» 상태: `%s` → %r" % (key, st))
    return rec["value"]


def cite(key, path=None):
    """문서에 «박을» 한 토막 — «값»에 «자»와 «범위»가 «붙어» 나온다.

    ★ 유형 67(「여러 «자»가 있는 낱말을 «자» «없이» 쓴다」)를 **«서식»에서 «막는다»** —
      «값»만 떼어 쓰는 것이 «불편»해지도록.
    """
    rec = entry(key, path)
    v = fact(key, path)
    return "%s%s [%s · %s · %s 기준]" % (
        v, rec.get("unit", ""), rec.get("ruler", ""), rec.get("scope", ""), rec.get("asof", ""))


def put(key, value, unit, measures, ruler, scope, asof, defn,
        provenance, script=None, commit=None, doc=None, added=None, path=None):
    """장부에 «올린다». **«불완전»하면 «거절»한다**(조건 ②).

    provenance — `"script"`(스크립트＋커밋) 또는 `"doc"`(문서:줄).
      🚨 `"doc"` 은 **«약하다»** — `audit()` 이 «세어» 찍는다. «미통과»로는 «안» 만든다.
    """
    bad = _key_bad(key)
    if bad:
        raise FactError("🚨 열쇠 «거절»: `%s` — %s" % (key, bad))
    if provenance not in ("script", "doc"):
        raise FactError("🚨 `provenance` 는 `script` 또는 `doc` 이어야 한다: %r" % provenance)
    if provenance == "script" and not (script and commit):
        raise FactError(
            "🚨 «거절» — `provenance=script` 인데 «스크립트»나 «커밋»이 «없다».\n"
            "   ⇒ 조건 ②: **장부는 «단일 실패점»이다.** 한 번 틀리면 «모든» 문서가 «물려받는다»")
    if provenance == "doc" and not doc:
        raise FactError("🚨 «거절» — `provenance=doc` 인데 `doc`(파일:줄)이 «없다»")
    for f, v in (("unit", unit), ("measures", measures), ("ruler", ruler),
                 ("scope", scope), ("asof", asof), ("defn", defn)):
        if not (isinstance(v, str) and v.strip()):
            raise FactError(
                "🚨 «거절» — `%s` 가 «비었다». 유형 12: 값 옆에 «넷»이 «붙어야» 「재현 가능」이다\n"
                "   (값 · 커밋된 스크립트 · 커밋된 입력 · «정의»[창·모집단·통계 종류·청소 규약"
                "·«자료 기준일»·재표집 구성])" % f)
    db = _load(path)
    if key in db["facts"] and db["facts"][key].get("status") == "live":
        raise FactError(
            "🚨 «덮어쓰기» «거절»: `%s` 가 «이미» «살아» 있다.\n"
            "   ⇒ 조건 ③: **«지우기»가 «아니라» «상태 바꾸기»** — `retract()` 또는 `supersede()`")
    db["facts"][key] = {
        "value": value, "unit": unit, "measures": measures, "ruler": ruler,
        "scope": scope, "asof": asof, "defn": defn, "provenance": provenance,
        "script": script, "commit": commit, "doc": doc,
        "status": "live", "added": added or "", "retracted_reason": None,
        "superseded_by": None,
    }
    _save(db, path)
    return db["facts"][key]


def retract(key, reason, path=None):
    """「쟀는데 «틀렸다»」 — ⛔ **«지우지» 않는다**(조건 ③).

    🚨 «좁게» 쓴다: ㉠「«틀렸다»」«만». ㉡「«여기»선 «못» 쓴다」(범위)는 — **«열쇠»의 «범위»로 «푼다»**.
       («둘»을 «한» 칸에 넣으면 ㉡ 이 «과잉 차단» ⇒ 사람이 **장부를 «우회»** ⇒ **장부가 «죽는다»**)
    """
    if not (isinstance(reason, str) and reason.strip()):
        raise FactError("🚨 «철회»에는 «까닭»이 «필요»하다 — 「없다」로는 «못» 적는다")
    db = _load(path)
    if key not in db["facts"]:
        raise FactMissing("🚨 «없는» 열쇠는 «철회»할 수 «없다»: `%s`" % key)
    db["facts"][key]["status"] = "retracted"
    db["facts"][key]["retracted_reason"] = reason
    _save(db, path)
    return db["facts"][key]


def supersede(old, new, path=None):
    """「«대체»됐다」 — «새» 열쇠를 «가리킨다». `new` 는 «살아» 있어야 한다."""
    db = _load(path)
    if old not in db["facts"]:
        raise FactMissing("🚨 «없는» 열쇠: `%s`" % old)
    if db["facts"].get(new, {}).get("status") != "live":
        raise FactError("🚨 «대체»할 열쇠가 «살아» 있지 «않다»: `%s`" % new)
    db["facts"][old]["status"] = "superseded"
    db["facts"][old]["superseded_by"] = new
    _save(db, path)
    return db["facts"][old]


def collisions(path=None):
    """★★ **규약 ⑦ «자동화»** — 「같은 것을 가리키는 «수»가 «둘»이면 «멈춤»」.

    «같은» (재는 것 · 자 · 범위)를 «선언»한 «살아 있는» 항목끼리 «값»이 «다르면» 잡는다.
    🚨 «오탐 모양»: «다르게» 선언하면 **«못» 잡는다**. 그래서 «열쇠 규칙»이 «먼저»다.
    """
    db = _load(path)
    seen, hits = {}, []
    for k, r in sorted(db["facts"].items()):
        if r.get("status") != "live":
            continue
        sig = (r.get("measures"), r.get("ruler"), r.get("scope"))
        if sig in seen:
            k0, v0 = seen[sig]
            if r.get("value") != v0:
                hits.append((sig, k0, v0, k, r.get("value")))
        else:
            seen[sig] = (k, r.get("value"))
    return hits


def audit(path=None):
    """관문 — **«주장»이 아니라 «출력값»으로** 말한다(규약 ②). 돌려주는 것: (통과, 줄들)."""
    db = _load(path)
    facts = db.get("facts", {})
    out = ["🔎 장부 `%s` — 항목 **%d**" % (os.path.normpath(LEDGER if path is None else path),
                                          len(facts))]
    if not facts:
        out.append("⚠️ **«비었다»** — 「장부가 «있다»」와 「«쓰이고» 있다」는 «다르다»")
        return True, out
    bad = []
    for k, r in sorted(facts.items()):
        kb = _key_bad(k)
        if kb:
            bad.append("   🚨 `%s` — 열쇠: %s" % (k, kb))
        miss = [f for f in _REQUIRED if not r.get(f) and r.get(f) != 0]
        if miss:
            bad.append("   🚨 `%s` — «빈» 칸: %s" % (k, ", ".join(miss)))
        st = r.get("status")
        if st not in _STATUSES:
            bad.append("   🚨 `%s` — «모르는» 상태: %r" % (k, st))
        if st == "retracted" and not r.get("retracted_reason"):
            bad.append("   🚨 `%s` — «철회»인데 «까닭»이 «없다»" % k)
        if st == "superseded":
            nb = r.get("superseded_by")
            if not nb:
                bad.append("   🚨 `%s` — «대체»인데 «가리키는» 곳이 «없다»" % k)
            elif facts.get(nb, {}).get("status") != "live":
                bad.append("   🚨 `%s` — «가리킨» `%s` 가 «살아» 있지 «않다»" % (k, nb))
        if r.get("provenance") == "script" and not (r.get("script") and r.get("commit")):
            bad.append("   🚨 `%s` — `script` 인데 스크립트/커밋이 «없다»" % k)
    # «묘사» — «미통과»로 «만들지» 않는다(「가끔만 잘못이면 «표»로」)
    n_live = sum(1 for r in facts.values() if r.get("status") == "live")
    n_ret = sum(1 for r in facts.values() if r.get("status") == "retracted")
    n_sup = sum(1 for r in facts.values() if r.get("status") == "superseded")
    n_doc = sum(1 for r in facts.values() if r.get("provenance") == "doc")
    out.append("   살아 있음 **%d** · 철회 **%d** · 대체 **%d**" % (n_live, n_ret, n_sup))
    out.append("   ⚠️ `provenance=doc`(스크립트·커밋이 «아니라» «문서 줄») — **%d** "
               "⇒ **«약하다». «올릴» 자리다**" % n_doc)
    cols = collisions(path)
    for sig, k0, v0, k1, v1 in cols:
        bad.append("   🚨 **규약 ⑦ «발동»** — 같은 (재는 것·자·범위) %r 에 «수»가 «둘»: "
                   "`%s`=%r vs `%s`=%r" % (sig, k0, v0, k1, v1))
    if bad:
        out.append("🚨 **«미통과» %d 건**" % len(bad))
        out.extend(bad)
        return False, out
    out.append("✅ 형식 «통과» — ⛔ 단 **「«값»이 «옳다»」가 «아니다»**(이 관문은 «형식»만 본다)")
    return True, out


def selftest(tmpdir=None):
    """★ **양성 «대조»와 «음성» 대조를 «둘 다»** 건다(유형 24·103).

    🚨 「이 관문을 «통과»시키는 «입력»과 «떨어뜨리는» «입력»을 «둘 다» «댈 수» 있나」 —
       ⇒ «댈 수» 없으면 관문이 «아니다». 그래서 아래는 **«일부러» 틀린 입력**을 «넣는다».
    ★ 그리고 «성공»을 «스스로» 찍지 «않는다** — **«디스크»에서 «다시» 읽어** 확인한다(유형 22).
    """
    import tempfile
    out, ok = [], True
    d = tmpdir or tempfile.mkdtemp(prefix="_facts_selftest_")
    p = os.path.join(d, "facts.json")
    good = dict(unit="%p", measures="연환산 격차", ruler="계좌 %p/해",
                scope="미국 27.4년", asof="2026-09-09", defn="블록 부트 20~40 · 씨앗 60",
                provenance="doc", doc="results/x.md:1", added="2026-09-10")

    def chk(label, fn, want_fail):
        nonlocal ok
        try:
            fn()
            got_fail = False
        except FactError:
            got_fail = True
        good_ = (got_fail == want_fail)
        ok = ok and good_
        out.append("   %s %s — %s" % ("✅" if good_ else "🔴", label,
                                      "«떨어짐»" if got_fail else "«통과»"))

    out.append("🔎 **음성 대조** — 「«떨어져야» 하는」 입력이 «떨어지나»")
    chk("마디 «둘»짜리 열쇠(«자»가 «없다»)", lambda: put("a.b", 1.0, path=p, **good), True)
    chk("`provenance=script` 인데 커밋 «없음»",
        lambda: put("t.x.ruler", 1.0, path=p, **dict(good, provenance="script", script="s.py")),
        True)
    chk("`defn` 이 «빈» 칸", lambda: put("t.y.ruler", 1.0, path=p, **dict(good, defn="  ")), True)
    out.append("🔎 **양성 대조** — 「«통과»해야 하는」 입력이 «통과»하나")
    chk("온전한 항목", lambda: put("235.mde.min.us27y", 2.56, path=p, **good), False)
    chk("«살아» 있는 것 «덮어쓰기»", lambda: put("235.mde.min.us27y", 9.9, path=p, **good), True)

    out.append("🔎 **«디스크»에서 «다시» 읽어** 확인한다(⛔ «스스로» 찍지 «않는다»)")
    v = fact("235.mde.min.us27y", path=p)
    r1 = (v == 2.56)
    out.append("   %s `fact()` → %r" % ("✅" if r1 else "🔴", v))
    ok = ok and r1

    retract("235.mde.min.us27y", "«자»가 바뀌었다(시험용)", path=p)
    try:
        fact("235.mde.min.us27y", path=p)
        r2 = False
    except FactRetracted:
        r2 = True
    out.append("   %s «철회» 뒤 `fact()` 가 **«예외»를 던진다**(⛔ «조용한» None «아님»)"
               % ("✅" if r2 else "🔴"))
    ok = ok and r2

    try:
        fact("없는.열쇠.자", path=p)
        r3 = False
    except FactMissing:
        r3 = True
    out.append("   %s 「«없음»」과 「«철회»」가 **«다른» 예외**다" % ("✅" if r3 else "🔴"))
    ok = ok and r3

    out.append("🔎 **규약 ⑦** — 같은 (재는 것·자·범위)에 «수»가 «둘»이면 «잡히나»")
    put("A.dup.ruler.scope", 1.0, path=p, **good)
    put("B.dup.ruler.scope", 2.0, path=p, **good)
    hits = collisions(path=p)
    r4 = len(hits) == 1
    out.append("   %s 충돌 **%d** 건 (기대 1)" % ("✅" if r4 else "🔴", len(hits)))
    ok = ok and r4
    a_ok, _ = audit(path=p)
    r5 = (a_ok is False)
    out.append("   %s 충돌이 «있을» 때 `audit()` 이 **«미통과»**를 낸다" % ("✅" if r5 else "🔴"))
    ok = ok and r5
    return ok, out


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "audit"
    if cmd == "selftest":
        good, lines = selftest()
    elif cmd == "audit":
        good, lines = audit()
    elif cmd == "cite":
        print(cite(sys.argv[2]))
        raise SystemExit(0)
    else:
        raise SystemExit("쓰는 법: _facts.py [audit|selftest|cite <열쇠>]")
    print("\n".join(lines))
    raise SystemExit(0 if good else 1)

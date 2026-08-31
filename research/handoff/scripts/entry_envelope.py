# -*- coding: utf-8 -*-
r"""**봉투(envelope)** — 특징 함수에 「진입 시점에 «있는» 값」만 건네는 그릇.

왜 «금지 목록»이 아니라 «허용 목록»인가
--------------------------------------
`v` 하나를 빼도 **`d·o·h·l·c`(전부 진입 «이후» 경로)·`exits`·`masks`·`r_` 가 그대로 열려 있다.**
막을 것을 세는 방식은 셀 때마다 새는 자리가 생긴다. **가져갈 것을 세는 방식**이라야 닫힌다.

🚨 `.get()` 을 반드시 같이 막는다 — 안 막으면
```
t.get("exits")  →  «조용히» None  →  특징 함수가 「값 없는 종목」으로 처리
                →  누출이 «결측 특징»이라는 «기능»처럼 보인다
```

🚨 규약은 「어느 «키»냐」가 아니라 **「어느 «시점»의 값이냐」**다
```
진입 뷰   pre_* 만. 경로(d·o·h·l·c·v)는 **한 칸도** 안 준다
청산 뷰   경로를 주되 **[0] 칸(진입일)은 가린다** —
          v[0]  = 진입일 거래량   → 장 «전» 예약 시점에 없다
          h[0]·l[0]·c[0]          → 「진입일 종가를 보고 진입을 정하는」 규칙이 샌다
```

자체 시험: `PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/entry_envelope.py`
"""
from __future__ import annotations

ENTRY_KEYS = ("code", "pattern", "scan_date", "entry_date",
              "entry_price", "pivot", "atr_band")
PRE_KEYS = ("pre_d", "pre_o", "pre_h", "pre_l", "pre_c", "pre_v", "pre_n")
PATH_KEYS = ("d", "o", "h", "l", "c", "v")
HIDE0 = ("v", "h", "l", "c", "o")          # 청산 뷰에서 [0] 칸을 가릴 배열


class Sealed(dict):
    """허용 목록 밖은 «죽는다». `.get()` 우회도 막는다."""

    def __missing__(self, k):
        raise KeyError("진입 시점에 없는 값: %r" % (k,))

    def get(self, k, default=None):
        if k not in self:
            raise KeyError("get 으로 우회 금지: %r" % (k,))
        return dict.__getitem__(self, k)

    # dict 의 다른 «샛길»도 같이 막는다
    def setdefault(self, k, default=None):
        raise KeyError("setdefault 로 우회 금지: %r" % (k,))

    def pop(self, k, *a):
        raise KeyError("pop 으로 우회 금지: %r" % (k,))


class _Hidden(list):
    """[0] 칸만 «죽는» 배열. 나머지는 보통 리스트처럼 쓴다."""

    def __getitem__(self, i):
        if i == 0 or i == -len(self):
            raise IndexError("진입일 칸은 주문 시점에 «없는» 값이다 (index 0)")
        return list.__getitem__(self, i)


def entry_view(rec):
    """**진입** 결정용. `pre_*` 와 진입 시점 기록만. 경로는 «한 칸도» 없다."""
    miss = [k for k in ENTRY_KEYS if k not in rec]
    if miss:
        raise KeyError("경로 기록에 진입 키가 없다: %r" % (miss,))
    out = {k: rec[k] for k in ENTRY_KEYS}
    out.update({k: rec[k] for k in PRE_KEYS if k in rec})
    return Sealed(out)


def exit_view(rec):
    """**청산** 결정용. 경로를 주되 **[0] 칸(진입일)은 가린다**."""
    out = {k: rec[k] for k in ENTRY_KEYS if k in rec}
    for k in PATH_KEYS:
        if k in rec:
            out[k] = _Hidden(rec[k]) if k in HIDE0 else rec[k]
    out.update({k: rec[k] for k in PRE_KEYS if k in rec})
    return Sealed(out)


# ═════════════════════════════════════════════════════════════════════════
# 🚨 **봉투가 «진짜로» 막는지 증명한다** (실패유형 24′ — 「아무것도 안 하는 코드」 금지)
#    「고쳤다」의 증거는 **「고치기 «전» 상태가 실패하는지」**를 보는 것이다.
# ═════════════════════════════════════════════════════════════════════════
def _selftest() -> int:
    rec = {"code": "AAA", "pattern": "VCP", "scan_date": "2005-03-10",
           "entry_date": "2005-03-11", "entry_price": 10.0, "pivot": 10.0,
           "atr_band": "②보통 2.5~4%",
           "d": ["2005-03-11", "2005-03-14"], "o": [10.0, 11.0], "h": [11.0, 12.0],
           "l": [9.5, 10.5], "c": [10.5, 11.5], "v": [1000.0, 2000.0],
           "pre_d": ["2005-03-09", "2005-03-10"], "pre_o": [9.0, 9.5],
           "pre_h": [9.6, 10.1], "pre_l": [8.9, 9.4], "pre_c": [9.5, 10.0],
           "pre_v": [800.0, 700.0], "pre_n": 2,
           "exits": [("2005-03-14", 1.0, 11.5)], "masks": {}, "r": 15.0}

    def cheat_path(t):
        return t["c"][-1] / t["entry_price"]          # 미래 종가로 커닝

    def cheat_get(t):
        return t.get("exits")                          # .get 으로 조용히 우회

    def cheat_entryday(t):
        return t["v"][0]                               # 진입일 거래량

    def honest(t):
        return t["pre_c"][-1] / t["pre_c"][0] - 1.0    # 진입 «전»만

    rows = []

    # ① 봉투 «없이» 는 커닝이 통해야 한다 — 안 통하면 시험 자체가 무의미하다
    try:
        v = cheat_path(rec)
        rows.append(("① 봉투 «없이» 커닝", "값 %.4f 가 나옴" % v, True))
    except Exception as e:
        rows.append(("① 봉투 «없이» 커닝", "🚨 안 나옴 — 시험 무효 (%r)" % (e,), False))

    # ② 진입 뷰에서 경로 커닝은 죽어야 한다
    ev = entry_view(rec)
    for lab, fn in (("② 진입뷰 · 미래 종가", cheat_path),
                    ("③ 진입뷰 · .get 우회", cheat_get),
                    ("④ 진입뷰 · 진입일 거래량", cheat_entryday)):
        try:
            fn(ev)
            rows.append((lab, "🚨 **통과해 버렸다 — 봉투가 안 막는다**", False))
        except KeyError as e:
            rows.append((lab, "KeyError 로 죽음 %s" % (e,), True))

    # ⑤ 정직한 특징은 살아야 한다
    try:
        rows.append(("⑤ 진입뷰 · 정직한 특징", "값 %+.4f" % honest(ev), True))
    except Exception as e:
        rows.append(("⑤ 진입뷰 · 정직한 특징", "🚨 죽었다 — 너무 막았다 (%r)" % (e,), False))

    # ⑥ 청산 뷰: 경로는 되고 [0] 칸만 죽어야 한다
    xv = exit_view(rec)
    try:
        xv["c"][1]
        rows.append(("⑥ 청산뷰 · c[1]", "된다", True))
    except Exception as e:
        rows.append(("⑥ 청산뷰 · c[1]", "🚨 죽었다 (%r)" % (e,), False))
    for lab, k in (("⑦ 청산뷰 · v[0]", "v"), ("⑧ 청산뷰 · c[0]", "c")):
        try:
            xv[k][0]
            rows.append((lab, "🚨 **통과해 버렸다 — 진입일 칸이 샌다**", False))
        except IndexError as e:
            rows.append((lab, "IndexError 로 죽음 (%s)" % (e,), True))
    try:
        xv["exits"]
        rows.append(("⑨ 청산뷰 · exits", "🚨 **통과해 버렸다**", False))
    except KeyError:
        rows.append(("⑨ 청산뷰 · exits", "KeyError 로 죽음", True))

    print("=" * 88, flush=True)
    print("봉투 자체시험 — **막아야 할 것이 «실제로» 막히는가**", flush=True)
    print("=" * 88, flush=True)
    ok = True
    for lab, msg, good in rows:
        ok &= good
        print("  %-26s %-52s %s" % (lab, msg, "✅" if good else "🚨"), flush=True)
    print("", flush=True)
    print("→ %s" % ("**전부 통과.** 봉투는 「아무것도 안 하는 코드」가 아니다."
                    if ok else "🚨 **미통과 — 봉투를 쓰지 말 것.**"), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())

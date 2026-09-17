# -*- coding: utf-8 -*-
"""270 — **우리가 «실제로 실행할» 규칙으로 27.4년을 다시 돈다**

사전등록: `.superpowers/sdd/2026-09-10-us-sepa-skill/rerun-preregistration.md`
  ⛔ **그 문서는 안 고친다.** 조건을 바꿔야 하면 멈추고 두뇌에 알린다.

🚨 **왜 다시 도나** — 감사 셋(FABLE)이 같은 곳에 닿았다:
   **우리가 인용해 온 수는 «우리가 지은 도구»의 수가 아니다.**
```
헤드라인 흐름   사다리 ② ∧ 실적 판정 ∧ 지수 숏 ∧ 목표 +20 ∧ 연도 경계 결함 ∧ 마찰 0
우리 실전 도구  «셋 다 없음» ∧ 목표 +30 ∧ 경계 고침 ∧ 마찰 있음
```

⛔ **기존 각본을 «고치지» 않았다** — `91`·`129`·`152` 는 한 글자도 안 바뀐다.
   이 파일은 그 각본들의 «부품»(`load_ladder`·`pyr_trigger`·`slot_sim_lots`·
   `account_lib`·`124.taxed_window`)을 **불러 쓴다**.

🚨 **`91.replay` 를 «베끼지 않고 다시 쓴 까닭»이 둘이다**
```
① 연도 경계 — `91.replay` 는 `for y: open_until = {}` 로 해마다 보유를 지운다.
   사전등록 ⑤가 고치라고 한 «그» 줄이다. 91 을 고칠 수 없으므로 여기서 «다시» 쓴다.
② 기억 — `91.load_ladder` 는 28년치 경로(1.46GB json)를 «한꺼번에» 안는다(≈9GB).
   이 기계의 가용 RAM 이 그보다 작다. 그래서 «해마다 읽고 버리는» 흐름으로 바꿨다.
   ⇒ 🚨 그러면 「옮기다 어긋났나」가 생긴다. **관문 G1 이 그것을 «검사»한다**
      (짧은 창에서 `91.load_ladder` 와 «경로 집합»을 맞대어 0 차이를 요구).
```

# 관문 — 값 보기 «전»에 박는다
| | 무엇 |
|---|---|
| **G1** | 흘려 읽는 적재기 = `91.load_ladder` (by0·by2 경로 «집합» 0 차이) |
| **G2** | `A0` 가 `129-frontier.json` 의 `20/10.0` 칸을, `A0b` 가 `30/10.0` 칸을 재현 |
| **G3** | 내 계좌기(숏 없음) = `account_lib.account` (세후·낙폭·회복 0 차이) |
| **G4** | 경계 고치기 «전/후» 중복 진입 건수를 «센다». 감사 ①의 3,796 근처가 나와야 한다 |

# ⛔ 금지 (사전등록에서 옮김)
```
① 마찰 칸을 결과 보고 «고르지» 않는다. **F2 가 판정 칸**이다
② 목표·손절 격자에서 «제일 좋은 칸»을 골라 인용하지 않는다. +30/−10 «하나»만
③ 「구간이 0 을 포함」을 「효과 없다」로도 「있다」로도 읽지 않는다 — **「못 가림」**
④ 결과가 나쁘다고 조건을 고쳐 다시 돌리지 않는다
```

실행:
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/270-live-rules-rerun.py
  (짧은 시험) 같은 명령 + --y0 2018 --y1 2020 --d0 2018-01-01 --d1 2020-12-31 --gate
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gc
import importlib.util as _u
import json
import math
import statistics as st
import sys
import time
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                       # noqa: E402
import slot_sim_lots as sl                                     # noqa: E402

P = print
BQ = chr(96)
F3 = BQ * 3
PCT = chr(37)


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r61b = _load("r61b", "61b-matched-null.py")
r41, r61 = r61b.r41, r61b.r61
r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
r108 = _load("r108", "108-short-index.py")
r109 = _load("r109", "109-index-stop.py")
r124 = _load("r124", "124-jeonse-horizon.py")
acc = _load("acc", "account_lib.py")
shape = acc.r129.shape                # 낙폭·회복 — 129 의 «그» 함수를 그대로 쓴다
f92a = r102.f92a

OUT = ROOT / ".cache" / "bt5y" / "out"
SUB = ROOT / ".cache" / "bt5y" / "sub"

# ── 사전등록 값 — 「어느 규칙 판인가」를 «같은 줄»에 적는다 ──────────────────
SLOTS, RISK, CAP = 5, 0.02, 0.20          # 규칙판 2026-09-02(41db459d) 이전부터 불변
HALF = 0.5                                # 목표에서 «절반» 판다 — 규칙판 2026-09-02
NEW = (30.0, 10.0)                        # 목표·손절 — 규칙판 2026-09-02(41db459d)
OLD = (20.0, 10.0)                        # 옛 규칙판 2026-08-13 — «견주기 위해서만» 쓴다
NSEED = 20
START = 1000.0                            # 만원 — 129·150·261 과 «같은 자»
BASE_COST = (0.0, 0.002)                  # 옛 판의 비용(91: COST) — F0 가 이것과 «같다»
FEE_BUY_ACCT = 0.002                      # 계좌층 매수 비용(account_lib.FEE) · 자리 20%

# 🔴 마찰 — 결과를 보기 «전»에 박은 칸. **F2 가 판정 칸**
FRIC = {"F0": (0.0000, 0.0000),
        "F1": (0.0025, 0.0025),
        "F2": (0.0025, 0.0050),
        "F3": (0.0050, 0.0050)}
JUDGE_CELL = "F2"

SHORT_SIZE, BORROW = 0.20, 2.0            # 옛 얼개에만 쓴다 (A0·A0b·A1·A2)
# 감사 ①의 실측 — `.superpowers/sdd/2026-09-10-us-sepa-skill/audit-1-harness.md` §B
#   「39,733건 중 3,796건(9.6%)」 · 산출 각본 `audit-1-scripts/audit_delist.py`
AUDIT_TRADES, AUDIT_DUP = 39733, 3796
# 사다리 ②의 «표본 밖» 성적 — `91-us-out-of-sample.py` 「표본밖A정본」 창(2002-01-01~2017-08-31),
#   사다리 ②, **목표 +20/−10**, ext 미사용. 메모리 `us-out-of-sample-2026-08`:
#   「4/4 미통과 · 연 +3.16% vs SPY +7.04%」
#   🚨 아래 국면표의 2002~2017 행과는 **«다른 자»**다(목표 +30 · 앞 국면 자산 물려받음 · 세후).
OOS_LADDER_CAGR, OOS_SPY_CAGR, OOS_GATES = 3.16, 7.04, "4/4 미통과"
THRESH = 1.0                              # 채택 문턱 연 +1.0%p — 기회비용 문턱

# 국면 셋 — 사전등록 「닷컴 / 2002~2017 / 2018~2026」
REGIMES = (("닷컴 1999~2001", "1999-04-01", "2001-12-31"),
           ("2002~2017", "2002-01-01", "2017-08-31"),
           ("2018~2026", "2018-01-01", "2026-08-21"))

# 🔺 노출 사다리 — 사전등록 `ladder-preregistration.md` (2026-09-12, 돌리기 «전»)
#    원전에서 «확인된» 문장 하나만 쓴다:
#      "are your last 4 or 5 stocks profitable on balance" (2020-11-25)
#    ⛔ 안 쓰는 것: 고정 연패 횟수(114 의 「3연패」) · 타율 회복 · ¼→½→¾→풀 4단계
LADDER_MULT = (0.00, 0.25, 0.50, 1.00)   # L0 현금 · L1 파일럿¼ · L2 절반½ · L3 풀
LADDER_START = 1                          # 「5거래가 안 쌓였으면 L1 에서 시작」
LADDER_N = 5                              # 판정은 «5» 로만. 4 는 민감도로만 본다
TIGHTEN = 2.0 / 3.0                       # L2 팔의 「1/3 타이트하게」 — 30/10 -> 20/6.67

# (key, 이름, 모집단, 목표·손절, 경계carry, 숏, 마찰칸, 사다리)
#   사다리 = None | {"n": 최근 거래 수, "tighten": 설정 조이기 여부}
ARMS = (
    ("A0", "옛 헤드라인 얼개 — 사다리②＋실적＋숏 · +20/−10 · 경계 결함 · 마찰 0",
     "by2f", OLD, False, True, "F0", None),
    ("A0b", "양성 대조 — «같은» 얼개에 +30/−10 (129 격자의 30/10 칸)",
     "by2f", NEW, False, True, "F0", None),
    ("A1", "− 사다리② 뺌", "by0f", OLD, False, True, "F0", None),
    ("A2", "− 실적 판정 뺌", "by0", OLD, False, True, "F0", None),
    ("A3", "− 지수 숏 뺌", "by0", OLD, False, False, "F0", None),
    ("A4", "목표 +20 → +30", "by0", NEW, False, False, "F0", None),
    ("A5", "연도 경계 고침 (= 마찰 F0)", "by0", NEW, True, False, "F0", None),
    ("F1", "마찰 F1 — 진입 0.25 · 청산 0.25", "by0", NEW, True, False, "F1", None),
    ("A6", "🔴 **판정 칸** 마찰 F2 — 진입 0.25 · 청산 0.50",
     "by0", NEW, True, False, "F2", None),
    ("F3", "마찰 F3 — 진입 0.50 · 청산 0.50", "by0", NEW, True, False, "F3", None),
    # ── B 계열 — 사전등록 덧붙임(2026-09-12, 돌리기 «전»에 적음) ──────────
    #    물음: 「사다리 ②와 실적 판정을 «실전 도구에 넣으면» 얼마인가」
    #    ⛔ 분해표로 «빼서» 어림하면 안 된다 — 마찰이 «거래 수»에 붙는데 거래가 여러 배 다르다
    ("B1", "B 계열 — 사다리②＋실적 «있고» 지수 숏만 뺌 · 경계 결함 · 마찰 0",
     "by2f", NEW, False, False, "F0", None),
    ("B2", "B2 = B1 + 연도 경계 고침", "by2f", NEW, True, False, "F0", None),
    ("B3", "🔴 **B 계열 판정 칸** = B2 + 마찰 F2", "by2f", NEW, True, False, "F2", None),
    # ── L 계열 — 노출 사다리 (사전등록 `ladder-preregistration.md`) ────────
    ("L1", "🔴 **사다리 판정 칸** — 바닥 B3 · **크기만** 조절 (최근 5거래)",
     "by2f", NEW, True, False, "F2", {"n": 5, "tighten": False}),
    ("L2", "바닥 B3 · 크기 + **설정 조이기**(줄면 손절·목표 1/3 타이트)",
     "by2f", NEW, True, False, "F2", {"n": 5, "tighten": True}),
    ("L3", "바닥 A6(지금 실전 도구) · **크기만** 조절",
     "by0", NEW, True, False, "F2", {"n": 5, "tighten": False}),
    ("L1n4", "민감도 — L1 과 같되 최근 **4**거래 (⛔ 판정은 5 로만)",
     "by2f", NEW, True, False, "F2", {"n": 4, "tighten": False}),
    # ── C 계열 — 사전등록 덧붙임(2026-09-12, 돌리기 «전»에 적음) ──────────
    #    까닭: 271 이 「실적 판정은 2027-02 에 «전멸»」로 쟀다(낭떠러지 · 야후로 못 채움).
    #          업종은 유지된다 ⇒ **오래 쓸 수 있는 것은 사다리②만 있는 판**인데 안 쟀다.
    #    ⛔ A 계열 분해의 「실적 뺀 몫 −3.68%p」로 어림하지 않는다 — 순서가 다르면 몫도 다르다
    ("C1", "🔴 **C 계열 판정 칸** — 사다리② «만» (실적 판정 «없음») · 숏 없음 · 마찰 F2",
     "by2", NEW, True, False, "F2", None),
)
# 「무엇을 뺐나」의 몫 — 앞 칸 대비
CHAIN = (("A1", "A0", "사다리 ② 뺀 몫"),
         ("A2", "A1", "실적 판정 뺀 몫"),
         ("A3", "A2", "지수 숏 뺀 몫"),
         ("A4", "A3", "목표 +20 → +30 몫"),
         ("A5", "A4", "연도 경계 고친 몫"),
         ("A6", "A5", "마찰 F2 넣은 몫"))
# B 계열의 몫 — 출발이 A0b(사다리②＋실적＋숏 · +30/−10 · 경계 결함 · 마찰 0)
BCHAIN = (("B1", "A0b", "지수 숏 뺀 몫"),
          ("B2", "B1", "연도 경계 고친 몫"),
          ("B3", "B2", "마찰 F2 넣은 몫"))
REGIME_ARMS = ("A0", "A0b", "A5", "A6", "B3", "L1", "C1")   # 국면표에 넣는 팔
CI_ARMS = ("A0", "A0b", "A6", "B3", "L1", "C1")            # 연별 구간표에 넣는 팔
LADDER_ARMS = ("L1", "L2", "L3", "L1n4")
KEEP_CURVES = tuple(sorted(set(REGIME_ARMS) | set(CI_ARMS)))

T95 = {5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201,
       12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110,
       18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069,
       24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048}


def mem_gb():
    """이 기계의 (전체, 가용) 기억(GB). 🚨 어림이 아니라 «잰» 값이다."""
    try:
        import ctypes
        from ctypes import wintypes as wt

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return (None, None)
        return (m.ullTotalPhys / 1e9, m.ullAvailPhys / 1e9)
    except Exception:
        return (None, None)


def atomic_write(path, text):
    """⛔ 제자리 덮어쓰기 금지 — 임시 파일 -> 다시 읽어 확인 -> 옮기기."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    if tmp.read_text(encoding="utf-8") != text:
        raise SystemExit("🚨 임시 파일이 쓴 것과 다르다 — %s" % tmp)
    tmp.replace(path)


def _ord(d):
    return _dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()


def cagr_from_total(man, years):
    """세후 총액(만원) -> 연환산 %. 261 `ann` · 150:12 와 «같은 식»."""
    if years <= 0 or man <= 0:
        return float("nan")
    return ((man / START) ** (1.0 / years) - 1.0) * 100.0


def val_at(ds, vs, d):
    lo, hi, ans = 0, len(ds) - 1, None
    while lo <= hi:
        m = (lo + hi) // 2
        if ds[m] <= d:
            ans, lo = vs[m], m + 1
        else:
            hi = m - 1
    return ans


def annual(ds, vs, y0, y1):
    """온전한 «달력해»만 — 152 의 `annual` 과 «같은 식»(조각해는 버린다)."""
    out = {}
    for y in range(y0, y1 + 1):
        if not (ds[0] <= "%d-01-01" % y and ds[-1] >= "%d-12-31" % y):
            continue
        a = val_at(ds, vs, "%d-01-01" % y)
        b = val_at(ds, vs, "%d-12-31" % y)
        if a and b and a > 0:
            out[y] = b / a - 1.0
    return out


def need_years(gap, sd, pw=0.842, z=1.96):
    return ((z + pw) * sd / max(abs(gap), 1e-9)) ** 2


# ═════════════════════════════════════════════════════════════════════════
# 1. 모집단 — 흘려 읽는 적재기 (`91.load_ladder` 와 «같은 규약», 해마다 버린다)
# ═════════════════════════════════════════════════════════════════════════
def ladder_flags(d0, monthly_file):
    """사다리 ①·②가 쓰는 «월말 깃발». 연도 파일과 무관하므로 «한 번»만 만든다."""
    pack = json.loads((OUT / monthly_file).read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    lo_ym = r61.prev_ym(d0[:7], 8)
    months = sorted({m for d in monthly.values() for m in d if m >= lo_ym})
    mret = r61b.month_returns(monthly, sector, months)
    sec_top, in_pct = r61b.make_flags(mret, sector)
    return sector, sec_top, in_pct


def lvl2_ok(p, sector, sec_top, in_pct, lo=0.10, hi=0.30):
    """`91.load_ladder` 의 `lvl2` 를 «그대로» 옮긴 것. G1 이 어긋남을 검사한다."""
    s = sector.get(p["code"])
    if not s:
        return True                                   # 제3군 통과 (61번 규약)
    ym = r61.prev_ym(p["scan_date"][:7], 1)
    top = sec_top.get(ym)
    if top is None:
        return True
    if s not in top:
        return False
    v = in_pct.get(ym, {}).get(p["code"])
    return (v is None) or (lo <= v < hi)


def judge_ok(p, fund, ix):
    """`129`·`152` 의 실적 판정 — `if v is not False` 면 «남긴다»."""
    arq = (fund.get(p["code"]) or {}).get("ARQ") or []
    if not arq:
        return True                                   # v=None -> not False
    a = f92a.asof(arq, p["entry_date"])
    if a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX:
        return True
    return r103.judge(arq, arq.index(a), ix, 1, 2) is not False


def load_year(y, d0, d1):
    f = SUB / ("uspath_%d.json" % y)
    if not f.exists():
        return None
    ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    return [p for p in ps if d0 <= p["entry_date"] <= d1]


# ═════════════════════════════════════════════════════════════════════════
# 2. 리플레이 — 🔴 **연도 경계를 «고를 수 있게»** 만든 것이 사전등록 ⑤
# ═════════════════════════════════════════════════════════════════════════
def stream_replay(specs, years, d0, d1, monthly_file, log=True):
    """`{키: (모집단, (목표,손절), carry, 정렬, 경로보관, 조인설정)}` 를 한 번에 푼다.

    🔴 `carry=True` 면 보유 상태가 «해를 넘어» 이어진다 — 사전등록 ⑤.
    🔴 `carry=False` 는 `91.replay` 의 동작(해마다 `open_until = {}`) 그대로다.
    🔵 `정렬`: "file" = 경로 파일 순서(=`91.replay` 규약 · 헤드라인이 나온 순서)
              "sorted" = (진입일, 종목, 패턴, 스캔일) 전역 정렬(=감사 ① `audit_delist.py` 규약)
       같은 날 같은 종목에 경로가 여럿이면 «어느 것을 잡느냐»가 갈린다 — G4 가 그 크기를 잰다.
    """
    sector, sec_top, in_pct = ladder_flags(d0, monthly_file)
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    stt = {k: {"open_until": {}, "ou_year": {}, "ev": [], "blocked": 0,
               "n_path": 0, "xyear": 0, "n_trade": 0} for k in specs}
    need = {v[0] for v in specs.values()}
    t0 = time.time()
    for y in years:
        ps = load_year(y, d0, d1)
        if ps is None:
            raise SystemExit("🚨 경로 파일 없음 — uspath_%d.json" % y)
        pops = {"by0": ps}
        if "by0f" in need:
            pops["by0f"] = [p for p in ps if judge_ok(p, fund, ix)]
        if "by2" in need or "by2f" in need:
            pops["by2"] = [p for p in ps if lvl2_ok(p, sector, sec_top, in_pct)]
        if "by2f" in need:
            pops["by2f"] = [p for p in pops["by2"] if judge_ok(p, fund, ix)]
        order_cache = {}
        memo = {}
        for k in specs:
            pop, ts, carry, order, keep, alt_ts = specs[k]
            s_ = stt[k]
            if not carry:
                s_["open_until"] = {}
                s_["ou_year"] = {}
            if order == "sorted":
                if pop not in order_cache:
                    order_cache[pop] = sorted(
                        pops[pop], key=lambda q: (q["entry_date"], q["code"],
                                                  q["pattern"], q["scan_date"]))
                seq = order_cache[pop]
            else:
                seq = pops[pop]
            for p in seq:
                s_["n_path"] += 1
                c = p["code"]
                ou = s_["open_until"].get(c)
                if ou is not None and p["entry_date"] <= ou:
                    s_["blocked"] += 1
                    if s_["ou_year"].get(c) != y:
                        s_["xyear"] += 1
                    continue
                mk = (id(p), ts)
                t = memo.get(mk)
                if t is None:
                    t = pt.resolve_trade(p, ft="limit", fs="market",
                                         stop=ts[1], target=ts[0], half=HALF,
                                         shares=(1.0,), add_stop="floor_entry")
                    memo[mk] = t
                if alt_ts is not None and "alt" not in t:
                    ak = (id(p), alt_ts)
                    at = memo.get(ak)
                    if at is None:
                        at = pt.resolve_trade(p, ft="limit", fs="market",
                                              stop=alt_ts[1], target=alt_ts[0],
                                              half=HALF, shares=(1.0,),
                                              add_stop="floor_entry")
                        memo[ak] = at
                    t["alt"] = at
                m = t["masks"][()]
                s_["open_until"][c] = m["resolve_date"] or p["entry_date"]
                s_["ou_year"][c] = y
                s_["n_trade"] += 1
                if keep:
                    s_["ev"].append(t)
        del ps, pops, memo, order_cache
        gc.collect()
        if log:
            P("     %d  경과 %6.1f초" % (y, time.time() - t0), flush=True)
    for s_ in stt.values():
        s_.pop("open_until")
        s_.pop("ou_year")
    return stt


# ═════════════════════════════════════════════════════════════════════════
# 2b. 노출 사다리 — 사전등록 `ladder-preregistration.md` 규칙 «그대로»
# ═════════════════════════════════════════════════════════════════════════
# 🚨 왜 `slot_sim_lots` 의 `size_fn` 만으로 «안» 되나
#    `size_fn(recent, ...)` 의 `recent` 는 «승패 불리언»이다. 사전등록 규칙은
#    「최근 청산된 5거래의 **손익 «합»**」이라 «돈»이 필요하다. 승패로는 못 만든다.
#    (99·114·116 의 사다리는 «승패» 자였다 — 아래 걸린 것에 적는다.)
# ⇒ `slot_sim_lots` 를 «고치지 않고», `ev_fn`(날마다 `held` 를 준다)로 «청산»을
#    스스로 장부해 `size_fn`·`pick` 에 먹인다. 장부가 맞는지는 **관문 G5** 가
#    엔진 자신의 `exit_log`·`ret_log` 와 «원소별»로 맞대어 확인한다.
class Ladder:
    """L0 현금 · L1 ¼ · L2 ½ · L3 풀. 청산마다 최근 n거래 손익 «합»으로 한 칸."""

    def __init__(self, n=LADDER_N, tighten=False):
        self.n, self.tighten = n, tighten
        self.level = LADDER_START
        self.pend = {}          # 아직 안 닫힌 것: id(t) -> 스냅숏
        self.seen = set()
        self.pnl, self.wins, self.dates = [], [], []
        self.ties = 0
        self.tl = []            # (날짜, 그날 쓰인 칸)
        self.recent_ref = None

    @staticmethod
    def _pnl(h):
        """`slot_sim_lots.close_out` 의 식을 «그대로». G5 가 이 식을 검사한다."""
        tw = h["w"]
        tot = sum(x[1] for x in tw)
        r = sum(fr * sl.net(round(px / epx_i * 100 - 100, 2))
                * (w_i / max(1e-12, tot))
                for _d, fr, px in h["all_exits"] for epx_i, w_i in tw)
        return tot * r / 100.0, (h["result"] == "win"),             max((e[0] for e in h["all_exits"]), default=h["t"]["entry_date"])

    def _flush(self, d):
        due = [k for k, v in self.pend.items() if v["rd"] < d]
        due.sort(key=lambda k: (self.pend[k]["rd"], self.pend[k]["code"]))
        for k in due:
            v = self.pend.pop(k)
            self.pnl.append(v["pnl"])
            self.wins.append(v["win"])
            self.dates.append(v["xd"])
            if len(self.pnl) >= self.n:
                tot = sum(self.pnl[-self.n:])
                if tot > 0:
                    self.level = min(len(LADDER_MULT) - 1, self.level + 1)
                elif tot < 0:
                    self.level = max(0, self.level - 1)
                else:
                    self.ties += 1

    def ev(self, kind, d, cands, free, held):
        if kind != "DAY":
            return
        self._flush(d)
        for key, h in held.items():
            if key in self.seen:
                continue
            self.seen.add(key)
            pnl, win, xd = self._pnl(h)
            self.pend[key] = {"rd": h["resolve_date"] or h["t"]["entry_date"],
                              "code": h["t"]["code"], "pnl": pnl, "win": win,
                              "xd": xd}
        self.tl.append((d, self.level))

    def size(self, recent, seed, t):
        if self.recent_ref is None:
            self.recent_ref = recent
        self._flush(t["entry_date"])
        return LADDER_MULT[self.level]

    def pick(self, recent):
        return self.tighten and self.level < len(LADDER_MULT) - 1


def ladder_gate(lad, x):
    """관문 G5 — 내 장부 = 엔진 자신의 `exit_log`·`ret_log`·`recent`."""
    el = x["exit_log"]
    bad = []
    if len(lad.pnl) != len(el):
        bad.append("건수 %d vs %d" % (len(lad.pnl), len(el)))
    for i in range(min(len(lad.pnl), len(el))):
        if abs(lad.pnl[i] - el[i][1]) > 1e-9:
            bad.append("손익[%d] %.9g vs %.9g" % (i, lad.pnl[i], el[i][1]))
            break
        if lad.dates[i] != el[i][0]:
            bad.append("청산일[%d] %s vs %s" % (i, lad.dates[i], el[i][0]))
            break
    if lad.recent_ref is not None and lad.wins != list(lad.recent_ref):
        bad.append("승패열이 엔진 `recent` 와 다르다")
    return bad


def occupancy(lad):
    """노출 단계별로 «보낸 시간» — 달력일로 무게를 준다(사건일 수가 아니라)."""
    if len(lad.tl) < 2:
        return None
    tot, acc = 0, [0] * len(LADDER_MULT)
    for i in range(len(lad.tl) - 1):
        w = _ord(lad.tl[i + 1][0]) - _ord(lad.tl[i][0])
        acc[lad.tl[i][1]] += w
        tot += w
    return [100.0 * v / max(1, tot) for v in acc], tot


def sim(ev, cell, n_seed, ladder=None):
    b = BASE_COST[0] + FRIC[cell][0]
    s = BASE_COST[1] + FRIC[cell][1]
    out, lads, gate = [], [], []
    with r41.Cost(b, s):
        for i in range(n_seed):
            if ladder is None:
                out.append(sl.sim_lots(ev, seed=i, slots=SLOTS, risk=RISK, cap=CAP,
                                       reserve=False, fill_rule="truncate",
                                       cash_rule="per_slot"))
                continue
            lad = Ladder(n=ladder["n"], tighten=ladder["tighten"])
            x = sl.sim_lots(ev, seed=i, slots=SLOTS, risk=RISK, cap=CAP,
                            reserve=False, fill_rule="truncate",
                            cash_rule="per_slot", size_fn=lad.size,
                            pick=(lad.pick if ladder["tighten"] else None),
                            ev_fn=lad.ev, recent_n=10 ** 9)
            out.append(x)
            lads.append(lad)
            gate.extend(ladder_gate(lad, x))
    return out, lads, gate


# ═════════════════════════════════════════════════════════════════════════
# 3. 계좌 — `account_lib.account` 를 «구간별»로 쪼갤 수 있게 편 것 (G3 이 검사)
# ═════════════════════════════════════════════════════════════════════════
def build_curve(x, short_ctx=None):
    """한 판 -> (날짜열, 곡선, 실현손익). `short_ctx` 가 있으면 «옛» 숏을 얹는다."""
    fd = Counter(f[3] for f in x["fill_log"] if f[1] == "pilot")
    vv = ([(d, v) for d, v in x["curve"]]
          + [(x["curve"][-1][0], 1.0 + x["equity_pct"] / 100.0)])
    cds, ccv, V = [vv[0][0]], [1.0], 1.0
    for i in range(1, len(vv)):
        if vv[i - 1][1] <= 0:
            break
        d = vv[i][0]
        rl = vv[i][1] / vv[i - 1][1] - 1.0
        sh = 0.0
        if short_ctx is not None:
            on, spy_ret, bo = short_ctx
            if on.get(d) and d in spy_ret:
                sh = -SHORT_SIZE * spy_ret[d] - bo
        V *= (1.0 + rl + sh - FEE_BUY_ACCT * CAP * fd.get(d, 0))
        cds.append(d)
        ccv.append(max(V, 1e-9))
    real = {}
    for d, pl in x["exit_log"]:
        real[d] = real.get(d, 0.0) + pl
    return cds, ccv, real


def window_idx(cds, a, b):
    ii = [i for i, d in enumerate(cds) if a <= d <= b]
    return (ii[0], ii[-1]) if len(ii) > 1 else None


def acct(cds, ccv, real, i0, i1):
    post = r124.taxed_window(cds, ccv, real, i0, i1)
    mdd, rec = shape(cds[i0:i1 + 1], ccv[i0:i1 + 1])
    return post, mdd, rec


def bench_after_tax(tk, d0, d1):
    d_, c_ = r109.load(tk)
    ii = [i for i, d in enumerate(d_) if d0 <= d <= d1]
    if len(ii) < 2:
        return None
    ds = [d_[i] for i in ii]
    cv = [c_[i] / c_[ii[0]] for i in ii]
    post = r124.taxed_window(ds, cv, {}, 0, len(cv) - 1)
    mdd, rec = shape(ds, cv)
    yrs = (_ord(ds[-1]) - _ord(ds[0])) / 365.25
    return {"post": post, "cagr": cagr_from_total(post, yrs), "mdd": mdd,
            "rec": rec, "years": yrs, "d0": ds[0], "d1": ds[-1],
            "ds": ds, "cv": cv}


# ═════════════════════════════════════════════════════════════════════════
# 4. 본실행
# ═════════════════════════════════════════════════════════════════════════
def header(a, d0, d1, yrs):
    P("창       %s ~ %s   (%.2f년 · 연도 파일 %d~%d)" % (d0, d1, yrs, a.y0, a.y1))
    P("규칙     목표 +%.0f%s / 손절 −%.0f%s · 목표에서 %.0f%s 매도 → 나머지 25일 저가 추격"
      % (NEW[0], PCT, NEW[1], PCT, HALF * 100, PCT))
    P("         슬롯 %d칸 · 자리 상한 %.0f%s · 위험 %.0f%s · 씨앗 %d판"
      % (SLOTS, CAP * 100, PCT, RISK * 100, PCT, a.seeds))
    P("진입집합 8관문 → 검출기 셋(VCP·파워플레이·3C) → 피벗 예약")
    P("         ⛔ 사다리 «없음» · 실적 판정 «없음» · 지수 숏 «없음» (= 91 의 「사다리 0」)")
    P("비용     F0 = 옛 판의 비용 그대로 (매도 %.2f%s + 계좌층 매수 %.2f%s × 자리 %.0f%s)"
      % (BASE_COST[1] * 100, PCT, FEE_BUY_ACCT * 100, PCT, CAP * 100, PCT))
    P("마찰     그 «위에» 얹는다 — 아래 표. **F2 가 판정 칸**")
    tg, ag = mem_gb()
    P("기억     돌리기 «직전» 실측 — 전체 %s · **가용 %s**  (어림 아님)"
      % (("%.1fGB" % tg) if tg else "못 잼", ("%.1fGB" % ag) if ag else "못 잼"))


def gate_g1(years, d0, d1, mf):
    P("## 관문 G1 — 흘려 읽는 적재기 = " + BQ + "91.load_ladder" + BQ)
    P("")
    P(F3)
    t = time.time()
    (b0, _b1, b2), missing, _n = r91.load_ladder(years, d0, d1, mf, use_ext=False)
    if missing:
        raise SystemExit("🚨 경로 없음 %s" % (missing,))

    def key(p):
        return (p["scan_date"], p["code"], p["pattern"], p["entry_date"])

    ref0 = {key(p) for v in b0.values() for p in v}
    ref2 = {key(p) for v in b2.values() for p in v}
    del b0, _b1, b2
    gc.collect()
    sector, sec_top, in_pct = ladder_flags(d0, mf)
    my0, my2 = set(), set()
    for y in years:
        ps = load_year(y, d0, d1)
        for p in ps:
            my0.add(key(p))
            if lvl2_ok(p, sector, sec_top, in_pct):
                my2.add(key(p))
        del ps
        gc.collect()
    d_0, d_2 = len(ref0 ^ my0), len(ref2 ^ my2)
    P("by0  91 %7d개  ·  270 %7d개  ·  대칭차 **%d**" % (len(ref0), len(my0), d_0))
    P("by2  91 %7d개  ·  270 %7d개  ·  대칭차 **%d**" % (len(ref2), len(my2), d_2))
    P("소요 %.1f초" % (time.time() - t))
    P("덮은 범위 — 연도 파일 **%d개 중 %d개** (%d~%d)"
      % (28, len(years), years[0], years[-1]))
    P(F3)
    P("")
    P("🔵 **이 관문은 «전체» 창에서 «못» 돈다** — `91.load_ladder` 가 28년치를 한꺼번에 안아")
    P("   이 기계의 가용 RAM 을 넘는다. 즉 **다시 쓴 «까닭»이 관문의 «한계»이기도 하다**.")
    P("   ⇒ 전체 창의 뒷받침은 **관문 G2** 다 — 저장된 `129-frontier.json` 의 두 칸을")
    P("      «내» 적재기·재생기·시뮬·계좌기로 «끝까지» 다시 만들어 맞댄다(전체 27.4년).")
    ok = (d_0 == 0 and d_2 == 0)
    P("")
    P("✅ **G1 통과**" if ok else "🚨 **G1 미통과 — 멈춘다.** 적재기를 옮기다 어긋났다.")
    P("")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--y0", type=int, default=1999)
    ap.add_argument("--y1", type=int, default=2026)
    ap.add_argument("--d0", default="1999-04-01")
    ap.add_argument("--d1", default="2026-08-21")
    ap.add_argument("--seeds", type=int, default=NSEED)
    ap.add_argument("--gate", action="store_true",
                    help="G1(적재기 대조)·G3(계좌기 대조)을 돌린다")
    a = ap.parse_args()
    years = tuple(range(a.y0, a.y1 + 1))
    d0, d1 = a.d0, a.d1
    yrs = (_ord(d1) - _ord(d0)) / 365.25
    full = (a.y0, a.y1, d0, d1) == (1999, 2026, "1999-04-01", "2026-08-21")
    mf = "91-monthly-us-full.json"
    t_all = time.time()

    P("# 270 — **우리가 «실제로 실행할» 규칙으로 %.2f년** %s"
      % (yrs, "" if full else "(🔵 **짧은 시험 구간**)"))
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/270-live-rules-rerun.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48) · 손으로 옮긴 수 «0개»")
    P("> 사전등록 " + BQ
      + ".superpowers/sdd/2026-09-10-us-sepa-skill/rerun-preregistration.md" + BQ)
    P("")
    P(F3)
    header(a, d0, d1, yrs)
    P(F3)
    P("")
    P("| 칸 | 진입 | 청산 | 실제로 쓴 (FEE_BUY, FEE_SELL) | 쓰임 |")
    P("|---|---:|---:|---|---|")
    for c in ("F0", "F1", "F2", "F3"):
        b = BASE_COST[0] + FRIC[c][0]
        s = BASE_COST[1] + FRIC[c][1]
        mark = "**" if c == JUDGE_CELL else ""
        use = ("🔴 **판정 칸**" if c == JUDGE_CELL
               else ("옛 수와 견주는 기준선" if c == "F0" else "민감도"))
        P("| %s%s%s | %.2f%s | %.2f%s | (%.4f, %.4f) | %s |"
          % (mark, c, mark, FRIC[c][0] * 100, PCT, FRIC[c][1] * 100, PCT, b, s, use))
    P("")
    P("🔵 **실제 스프레드는 «안 쟀다».** F2 는 감사 ①이 자료에서 «어림»한 값이다.")
    P("   까닭: 손절이 시장가라 청산 쪽 미끄러짐이 진입(피벗 지정가 예약)보다 크다.")
    P("")

    if a.gate and not gate_g1(years, d0, d1, mf):
        return 3

    # ── 경로 재생 ───────────────────────────────────────────────────────
    def skey(pop, ts, carry, order="file"):
        return "%s|%.0f/%.0f|%d|%s" % (pop, ts[0], ts[1], int(carry), order)

    sp, arm_key = {}, {}
    for k, _nm, pop, ts, carry, _sh, _fc, _ld in ARMS:
        kk = skey(pop, ts, carry)
        alt = None
        if _ld is not None and _ld.get("tighten"):
            alt = (ts[0] * TIGHTEN, ts[1] * TIGHTEN)
        keep_alt = alt or (sp[kk][5] if kk in sp else None)
        sp[kk] = (pop, ts, carry, "file", True, keep_alt)
        arm_key[k] = kk
    # 🔵 G4 진단 — 감사 ①의 «정렬 규약»으로도 세어 본다(경로는 «안» 남긴다: 수만 필요)
    for cr in (False, True):
        sp[skey("by0", NEW, cr, "sorted")] = ("by0", NEW, cr, "sorted", False, None)
    P("## 경로 재생 — %d가지 (모집단 × 목표·손절 × 경계)" % len(sp))
    P("")
    P(F3)
    for k in sorted(sp):
        P("  %s" % k)
    t = time.time()
    stt = stream_replay(sp, years, d0, d1, mf)
    t_replay = time.time() - t
    P("재생 소요 **%.1f초**  ·  그때 가용 기억 %s"
      % (t_replay, ("%.2fGB" % mem_gb()[1]) if mem_gb()[1] else "못 잼"))
    P(F3)
    P("")

    # ── 관문 G4 — 경계 고치기 «전/후» 중복 진입 ─────────────────────────
    P("## 🔴 관문 G4 — 연도 경계 결함 «전»과 «후»")
    P("")
    P(F3)
    sb = stt[skey("by0", NEW, False)]
    sf = stt[skey("by0", NEW, True)]
    n_bug, n_fix, n_xy = sb["n_trade"], sf["n_trade"], sf["xyear"]
    dup = n_bug - n_fix
    ab = stt[skey("by0", NEW, False, "sorted")]["n_trade"]
    af = stt[skey("by0", NEW, True, "sorted")]["n_trade"]
    P("경로(후보)                      %7d  — 둘이 «같은» 집합이다" % sb["n_path"])
    P("거래  경계 결함(현행 91.replay) %7d" % n_bug)
    P("거래  경계 고침(사전등록 ⑤)     %7d" % n_fix)
    P("★ **중복 진입 = %d건**  (거래의 %.2f%s)"
      % (dup, 100.0 * dup / max(1, n_bug), PCT))
    P("")
    P("자가 «둘»이라 «둘 다» 적는다(규약 ⑦) — 가리키는 것이 «다르다»:")
    P("  🅐 거래 수 차            %7d   = 「고치면 «없어지는» 거래 수」" % dup)
    P("  🅑 «해를 넘어» 막힌 건수 %7d   = 「막은 «까닭»이 전년도 보유인 건수」"
      % n_xy)
    P("  ⇒ 🅐 와 🅑 의 차 **%d** = 「막았더니 «그 해 안»에서 «다음» 경로가 «대신» 들어온 수」"
      % (n_xy - dup))
    P("     (해 넘긴 진입을 막으면 그 종목 자리가 비고, 결함 판에서는 막혀 있던 뒤 경로가 산다.")
    P("      그래서 🅑 만큼 «막혀도» 거래는 🅐 만큼만 «줄어든다». 둘은 «다른 것»을 센다.)")
    P("")
    P("🔴 **감사 ①과 맞대기** — 감사 ①의 실측은 **3,796건 / 39,733건**")
    P("   (`audit_delist.py` 의 `len(select(False)) - len(select(True))` · 🅐 와 «같은 자»)")
    P("   위 수와 «작게» 어긋난다. 까닭이 «어디»인지를 세어서 닫는다 —")
    P("   두 판의 «다른 점»은 **같은 날 동순위를 어느 순서로 잡느냐** «하나»다.")
    P("")
    P("| 같은 날 정렬 규약 | 거래(결함) | 거래(고침) | 중복 |")
    P("|---|---:|---:|---:|")
    P("| 경로 파일 순서 — `91.replay` 규약 (이 판이 쓴 것) | %d | %d | **%d** |"
      % (n_bug, n_fix, dup))
    P("| (진입일, 종목, 패턴, 스캔일) 전역 정렬 — `audit_delist.py` 규약 | %d | %d | **%d** |"
      % (ab, af, ab - af))
    P("")
    if full:
        P("감사 ① 대비 — 전역 정렬 판:  거래 **%+d** · 중복 **%+d**  ->  **%s**"
          % (ab - AUDIT_TRADES, (ab - af) - AUDIT_DUP,
             "같은 수" if (ab == AUDIT_TRADES and ab - af == AUDIT_DUP)
             else "아직 어긋난다 — 정렬 말고 «다른» 까닭이 남았다"))
        P("감사 ① 대비 — 파일 순서 판:  거래 **%+d** · 중복 **%+d**"
          % (n_bug - AUDIT_TRADES, dup - AUDIT_DUP))
    else:
        P("🔵 감사 ①의 수는 **전체 27.4년**의 것이라 짧은 창에서는 «맞댈 자»가 없다.")
    P("")
    P("⇒ 이 판은 **파일 순서**를 쓴다 — `91.replay`·`129`·`152` 가 쓴 «그» 순서이고,")
    P("   관문 G2 가 옛 두 칸을 **차 0** 으로 재현한 것도 «그» 순서 위에서다.")
    P("   ⛔ 「어느 쪽이 옳은가」가 아니라 **「둘이 갈리는 크기」**가 여기서 낸 수다 —")
    P("      중복 %d 대 %d = **%.2f%s**" % (dup, ab - af,
                                            100.0 * abs(dup - (ab - af)) / max(1, ab - af),
                                            PCT))
    P(F3)
    P("")

    # ── 숏 문맥 (옛 얼개 전용) ──────────────────────────────────────────
    short_ctx = None
    if any(sh for _k, _n, _p, _t, _c, sh, _f, _l in ARMS):
        ds_s, c_s, ma_s, hi_s = r108.spy_series()
        on = r108.short_days(ds_s, c_s, ma_s, hi_s)
        spy_ret = {ds_s[i]: c_s[i] / c_s[i - 1] - 1.0 for i in range(1, len(ds_s))}
        short_ctx = (on, spy_ret, BORROW / 100.0 / 252.0 * SHORT_SIZE)

    # ── 판 돌리기 ───────────────────────────────────────────────────────
    P("## 팔 — 하나씩 켜고 끄며 («한꺼번에» 바꾸면 무엇 때문인지 모른다)")
    P("")
    res, sims, g3_rs, n_sim = {}, {}, [], 0
    t_sim = time.time()
    # 🚨 기억 — 같은 (경로, 마찰) 을 «나중» 팔이 안 쓰면 그 자리에서 버린다.
    def ckey(k, fc, ld):
        return (arm_key[k], fc, None if ld is None else (ld["n"], ld["tighten"]))

    later, last_rep = {}, {}
    for i, arm in enumerate(ARMS):
        later.setdefault(ckey(arm[0], arm[6], arm[7]), []).append(i)
        last_rep[arm_key[arm[0]]] = i
    for ai, (k, nm, pop, ts, carry, sh, fc, ld) in enumerate(ARMS):
        ck = ckey(k, fc, ld)
        got = sims.get(ck)
        if got is None:
            got = sim(stt[arm_key[k]]["ev"], fc, a.seeds, ladder=ld)
            sims[ck] = got
            n_sim += 1
            if got[2]:
                P("")
                P("🚨 **관문 G5 미통과 — 멈춘다.** 팔 %s 의 사다리 장부가 엔진과 어긋난다:" % k)
                for msg in got[2][:5]:
                    P("   %s" % msg)
                return 6
        rs, lads = got[0], got[1]
        posts, mdds, recs, cur = [], [], [], []
        for x in rs:
            cds, ccv, real = build_curve(x, short_ctx if sh else None)
            p_, m_, r_ = acct(cds, ccv, real, 0, len(ccv) - 1)
            posts.append(p_)
            mdds.append(m_)
            recs.append(r_)
            cur.append((cds, ccv, real))
        res[k] = {
            "name": nm, "pop": pop, "carry": carry, "short": sh, "fric": fc,
            "n_path": stt[arm_key[k]]["n_path"],
            "n_trade": stt[arm_key[k]]["n_trade"],
            "posts": posts, "mdds": mdds, "recs": recs,
            "cagrs": [cagr_from_total(p_, yrs) for p_ in posts],
            "n_filled": [x["n_filled"] for x in rs],
            "win": [x["win_rate"] for x in rs],
            "per_trade": [x["filled_per_trade"] for x in rs],
            "ladder": ld, "lads": lads, "gate": list(got[2]),
            "occ": [occupancy(l)[0] for l in lads if occupancy(l)],
            "curves": cur}
        P("  %-4s 세후 중앙 %9.1f만 · 연 %+7.3f%s   %s"
          % (k, st.median(posts), cagr_from_total(st.median(posts), yrs), PCT,
             nm), flush=True)
        if k == "A5":
            g3_rs = rs[:3]
        if max(later[ck]) <= ai:
            del sims[ck]
        if last_rep.get(arm_key[k], -1) <= ai:
            stt[arm_key[k]]["ev"] = []      # 🚨 기억 — 다 쓴 경로는 그 자리에서 버린다
        gc.collect()
    stt.clear()
    for k in res:                # 곡선은 국면·연별 표가 쓰는 팔만 남긴다
        if k not in KEEP_CURVES:
            res[k]["curves"] = []
    gc.collect()
    t_sim = time.time() - t_sim
    P("")
    P("판 돌리기 소요 **%.1f초** (%d판 × 씨앗 %d)  ·  그때 가용 기억 %s"
      % (t_sim, n_sim, a.seeds,
         ("%.2fGB" % mem_gb()[1]) if mem_gb()[1] else "못 잼"))
    P("")

    # ── 관문 G3 — 내 계좌기 = account_lib ───────────────────────────────
    if a.gate:
        P("## 관문 G3 — 내 계좌기(숏 «없음») = " + BQ + "account_lib.account" + BQ)
        P("")
        P(F3)
        worst = 0.0
        for x in g3_rs:
            cds, ccv, real = build_curve(x, None)
            p_, m_, r_ = acct(cds, ccv, real, 0, len(ccv) - 1)
            q_, qm, qr, _nf = acc.account(x)
            worst = max(worst, abs(p_ - q_), abs(m_ - qm), abs(r_ - qr))
        P("씨앗 3판 · 세후·낙폭·회복 최대 차이 **%.3e**" % worst)
        P(F3)
        P("")
        if worst > 1e-9:
            P("🚨 **G3 미통과 — 멈춘다.**")
            return 4
        P("✅ **G3 통과**")
        P("")

    # ── 관문 G2 — 옛 헤드라인 재현 ─────────────────────────────────────
    P("## 관문 G2 — " + BQ + "129-frontier.json" + BQ + " 의 두 칸을 재현하는가")
    P("")
    P(F3)
    gj = OUT / "129-frontier.json"
    g2 = None
    if not full:
        P("🔵 **건너뜀** — 129 의 격자는 1999-04-01~2026-08-21 «전체»에서 나온 값이다.")
        P("   짧은 시험 구간에는 «견줄 자»가 없다. 전체 실행에서만 검사한다.")
    elif not gj.exists():
        P("🚨 129-frontier.json 이 «없다» — 재현 검사를 **못 했다**")
    else:
        grid = json.loads(gj.read_text(encoding="utf-8"))["grid"]
        g2 = True
        for k, cell in (("A0", "20/10.0"), ("A0b", "30/10.0")):
            want = grid[cell]["post"]
            got = st.median(res[k]["posts"])
            ok = abs(got - want) <= 1e-6 * max(1.0, abs(want))
            g2 = g2 and ok
            P("%-4s 격자 %-8s  129 %13.4f만  ·  270 %13.4f만  ·  차 %+.3e  -> %s"
              % (k, cell, want, got, got - want, "일치" if ok else "🚨 어긋남"))
        P("   (씨앗 0~%d · 같은 order_key · 같은 부품 ⇒ «자릿수»가 아니라 «같은 값»이어야 한다)"
          % (a.seeds - 1,))
        P("   ★ **이것이 «전체 창»에서 도는 «유일한» 대조다** — G1 은 짧은 창에서만 돈다.")
        P("     덮는 것: 흘려 읽는 적재기 · 사다리 ② · 실적 판정 · 경계 «결함» 판 재생 ·")
        P("     `slot_sim_lots` · 숏 얹은 계좌기 · 세금. **덮지 «못하는» 것: `carry=True` 재생**")
        P("     (옛 판에 «그 모드가 없어서» 맞댈 자가 없다 — G4 의 «건수»로만 본다).")
    P(F3)
    P("")
    if g2 is False:
        P("🚨 **G2 미통과 — 멈추고 두뇌에 알린다.** 옛 얼개를 재현하지 못하면")
        P("   「무엇 때문에 달라졌나」의 분해가 «전부» 못 믿을 것이 된다.")
        return 5
    if g2:
        P("✅ **G2 통과**")
        P("")

    # ── 지수 ────────────────────────────────────────────────────────────
    bm = {tk: bench_after_tax(tk, d0, d1) for tk in ("QQQ", "SPY")}
    P("## 지수 — 세후 · 「그냥 사서 든다」 (옛 판과 «같은 자» · 261 참조)")
    P("")
    P("| | 세후 총액 | **연환산** | 낙폭 | 회복(년) |")
    P("|---|---:|---:|---:|---:|")
    for tk in ("QQQ", "SPY"):
        b = bm[tk]
        P("| %s 그냥 보유 | %.1f만 | **%+.4f%s** | %.2f%s | %.1f |"
          % (tk, b["post"], b["cagr"], PCT, b["mdd"], PCT, b["rec"] / 252.0))
    P("")
    P("🚨 지수는 " + BQ + "closeadj" + BQ + "(배당 «포함» 총수익), 우리 종목은 "
      + BQ + "close" + BQ + "(배당 «빠짐»). ⇒ **우리에게 «불리하게»** 잰 것이다.")
    P("")

    # ── 팔 표 ───────────────────────────────────────────────────────────
    P("## 팔별 결과 — 세후 · 씨앗 %d판" % a.seeds)
    P("")
    P("| 팔 | 무엇 | 후보 | 거래 | 체결 | 세후 총액 | **연환산** | 낙폭 | 회복(년) "
      "| 승률 | 거래당 |")
    P("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for k, _nm, _p, _t, _c, _s, _f, _l in ARMS:
        v = res[k]
        P("| %s | %s | %d | %d | %.0f | %.1f만 | **%+.4f%s** | %.2f%s | %.1f "
          "| %.1f%s | %+.3f%s |"
          % (k, v["name"], v["n_path"], v["n_trade"], st.median(v["n_filled"]),
             st.median(v["posts"]), cagr_from_total(st.median(v["posts"]), yrs), PCT,
             st.median(v["mdds"]), PCT, st.median(v["recs"]) / 252.0,
             st.median(v["win"]), PCT, st.median(v["per_trade"]), PCT))
    P("")
    P("🔵 「체결·승률·거래당」은 씨앗 %d판의 **중앙값**이다(슬롯이 차서 못 산 것이 씨앗마다 다르다)."
      % a.seeds)
    P("")

    # ── 분해 ────────────────────────────────────────────────────────────
    P("## 🔴 옛 헤드라인과의 차 — **원인별로 갈라서**")
    P("")
    P("⛔ 한꺼번에 바꾸면 «무엇 때문에» 달라졌는지 모른다. **하나씩 켜고 끄며** 쟀다.")
    P("🚨 순서가 «다르면» 몫도 «다르다»(상호작용). 이 표는 **위에서 아래 순서**의 몫이다.")
    P("")
    P("| 단계 | 무엇을 바꿨나 | 세후 총액(중앙) | 연환산 | **몫(%sp)** |" % PCT)
    P("|---|---|---:|---:|---:|")
    base = st.median(res["A0"]["posts"])
    P("| A0 | (출발) 옛 헤드라인 얼개 | %.1f만 | %+.4f%s | — |"
      % (base, cagr_from_total(base, yrs), PCT))
    for cur_k, prev_k, lab in CHAIN:
        c_ = cagr_from_total(st.median(res[cur_k]["posts"]), yrs)
        p_ = cagr_from_total(st.median(res[prev_k]["posts"]), yrs)
        P("| %s | %s | %.1f만 | %+.4f%s | **%+.4f** |"
          % (cur_k, lab, st.median(res[cur_k]["posts"]), c_, PCT, c_ - p_))
    P("")
    tot = (cagr_from_total(st.median(res["A6"]["posts"]), yrs)
           - cagr_from_total(base, yrs))
    P("합 **%+.4f%sp** — A0 → A6 (옛 헤드라인 얼개 → 우리가 실제로 실행할 규칙 + 마찰 F2)"
      % (tot, PCT))
    P("")

    # ── B 계열 ─────────────────────────────────────────────────────────
    P("## 🔴 B 계열 — 「사다리 ②와 실적 판정을 **실전 도구에 넣으면** 얼마인가」")
    P("")
    P("사전등록 덧붙임(2026-09-12, 돌리기 «전»에 적음). 270 의 A 계열은 A0 에서 «빼며 내려간»")
    P("길이라 이 물음에 답하지 «못한다».")
    P("⛔ **분해표로 «빼서» 어림하면 안 된다** — 마찰은 «거래 수»에 붙는데 두 계열의 거래 수가")
    P("   여러 배 다르다. 뺄셈으로 만든 수는 «재지 않은» 수다. 그래서 «따로 돌렸다».")
    P("")
    P("| 단계 | 무엇을 바꿨나 | 세후 총액(중앙) | 연환산 | **몫(%sp)** |" % PCT)
    P("|---|---|---:|---:|---:|")
    b0 = st.median(res["A0b"]["posts"])
    P("| A0b | (출발) 사다리②＋실적＋숏 · +30/−10 · 경계 결함 · 마찰 0 | %.1f만 | %+.4f%s | — |"
      % (b0, cagr_from_total(b0, yrs), PCT))
    for cur_k, prev_k, lab in BCHAIN:
        c_ = cagr_from_total(st.median(res[cur_k]["posts"]), yrs)
        p_ = cagr_from_total(st.median(res[prev_k]["posts"]), yrs)
        P("| %s | %s | %.1f만 | %+.4f%s | **%+.4f** |"
          % (cur_k, lab, st.median(res[cur_k]["posts"]), c_, PCT, c_ - p_))
    P("")
    P("### A6 과 B3 을 «나란히»")
    P("")
    P("| | A6 — 사다리 «없음» (지금 실전 도구) | B3 — 사다리②＋실적 «있음» |")
    P("|---|---:|---:|")
    rows = (("후보 경로", "%d", "n_path"), ("거래", "%d", "n_trade"))
    for lab, fmt, key in rows:
        P("| %s | %s | %s |" % (lab, fmt % res["A6"][key], fmt % res["B3"][key]))
    for lab, key, unit in (("체결(중앙)", "n_filled", ""), ("승률(중앙)", "win", PCT),
                           ("거래당(중앙)", "per_trade", PCT)):
        P("| %s | %.3f%s | %.3f%s |"
          % (lab, st.median(res["A6"][key]), unit, st.median(res["B3"][key]), unit))
    for lab, key in (("세후 총액(중앙·만원)", "posts"), ("낙폭(중앙)", "mdds")):
        P("| %s | %.2f | %.2f |" % (lab, st.median(res["A6"][key]), st.median(res["B3"][key])))
    ca6 = cagr_from_total(st.median(res["A6"]["posts"]), yrs)
    cb3 = cagr_from_total(st.median(res["B3"]["posts"]), yrs)
    P("| **연환산(세후)** | **%+.4f%s** | **%+.4f%s** |" % (ca6, PCT, cb3, PCT))
    for tk in ("QQQ", "SPY"):
        P("| 우리 − %s | %+.4f%sp | %+.4f%sp |"
          % (tk, ca6 - bm[tk]["cagr"], PCT, cb3 - bm[tk]["cagr"], PCT))
    P("| 회복 최장(년) | %.1f | %.1f |"
      % (max(res["A6"]["recs"]) / 252.0, max(res["B3"]["recs"]) / 252.0))
    P("")
    P("★ 거래 수 비 — **%d ÷ %d = %.2f배**  (마찰이 붙는 곳이 이만큼 다르다)"
      % (res["A6"]["n_trade"], res["B3"]["n_trade"],
         res["A6"]["n_trade"] / max(1, res["B3"]["n_trade"])))
    P("  체결 수 비 — **%.0f ÷ %.0f = %.2f배**"
      % (st.median(res["A6"]["n_filled"]), st.median(res["B3"]["n_filled"]),
         st.median(res["A6"]["n_filled"]) / max(1.0, st.median(res["B3"]["n_filled"]))))
    P("")
    P("### 🔴 결과를 «보기 전»에 사전등록에 적어 둔 것 둘 — 좋게 나와도 «안 사라진다»")
    P("")
    P(F3)
    P("① 사다리 ②는 **표본 밖 2002~2017 에서 SPY 에 졌다**")
    P("   연 **+%.2f%s** vs SPY **+%.2f%s** · **%s**"
      % (OOS_LADDER_CAGR, PCT, OOS_SPY_CAGR, PCT, OOS_GATES))
    P("   출처 `91-us-out-of-sample.py` 「표본밖A정본」 · 메모리 `us-out-of-sample-2026-08`")
    P("   🚨 아래 국면표의 2002~2017 행과 **«다른 자»**다 — 저것은 목표 **+20**·그 창만 «따로»")
    P("      돌린 값이고, 국면표는 목표 **+30**·앞 국면 자산을 «물려받은» 세후 값이다.")
    P("      ⛔ 두 수를 «맞대지» 말 것. 나란히 두는 것은 «둘 다 있다»를 보이기 위해서다.")
    P("")
    P("② **27.4년 전체에는 사다리를 «고른» 구간이 들어 있다.**")
    P("   사다리 ②(주도 3업종 ∧ 업종 내 상위 10~30%s)는 61·74 계보에서 «골라진» 칸이다." % PCT)
    P("   ⇒ 27.4년 수에는 «고르기»가 섞인다. 표본 밖에서 다시 재지 «않는» 한 그 몫을 못 가른다.")
    P(F3)
    P("")

    # ── 판정 ────────────────────────────────────────────────────────────
    P("## 🟣 C 계열 — 「사다리② **만**」 (실적 판정이 2027-02 에 전멸한다)")
    P("")
    P("`271` 이 쟀다: 실적 판정은 **2027-02 에 한꺼번에 전멸**한다(낭떠러지 · 야후로 못 채움).")
    P("업종은 유지된다. ⇒ **B3 는 수명이 5개월**이고, 오래 쓸 수 있는 것은 **사다리②만 있는 판**")
    P("인데 그 칸을 «안 쟀다». ⛔ A 계열 분해의 「실적 뺀 몫」으로 어림하지 «않는다» —")
    P("   마찰에서 이미 봤듯 **순서가 다르면 몫도 다르다**.")
    P("")
    P("### 🔴 돌리기 «전»에 물은 것 — 이 조건이 무언가를 «잴 수» 있는가")
    P("")
    P(F3)
    P("모집단 (창 %s ~ %s · 경로 «후보» 수)" % (d0, d1))
    P("  by0  사다리X 실적X  %8d   (A6 의 것)" % res["A6"]["n_path"])
    P("  by2  사다리O 실적X  %8d   (C1 의 것)" % res["C1"]["n_path"])
    P("  by2f 사다리O 실적O  %8d   (B3 의 것)" % res["B3"]["n_path"])
    P("")
    P("실적 판정이 사다리② 후보에서 걷어내는 몫 **%d건 (%.2f%s)**"
      % (res["C1"]["n_path"] - res["B3"]["n_path"],
         100.0 * (res["C1"]["n_path"] - res["B3"]["n_path"]) / max(1, res["C1"]["n_path"]),
         PCT))
    P("C1 후보 ÷ B3 후보 = **%.3f 배**  ·  C1 거래 ÷ B3 거래 = **%.3f 배**"
      % (res["C1"]["n_path"] / max(1, res["B3"]["n_path"]),
         res["C1"]["n_trade"] / max(1, res["B3"]["n_trade"])))
    P("C1 체결 ÷ B3 체결 = **%.3f 배** (중앙) — 슬롯 5칸이 묶는다"
      % (st.median(res["C1"]["n_filled"]) / max(1.0, st.median(res["B3"]["n_filled"]))))
    P("")
    P("⇒ **잴 수 있다**: 한쪽으로 무너지지 «않는다»(近동일도 아니고 폭발도 아니다).")
    P("⇒ 🚨 다만 **슬롯이 묶여 있으므로 C1 − B3 는 「거래가 «늘어난» 몫」이 아니라**")
    P("   **「같은 5칸을 «누가» 차지하나」의 몫**이다. 후보가 %.2f배인데 체결은 %.2f배다."
      % (res["C1"]["n_path"] / max(1, res["B3"]["n_path"]),
         st.median(res["C1"]["n_filled"]) / max(1.0, st.median(res["B3"]["n_filled"]))))
    P("⇒ ✅ 짝 비교가 «성립»한다: `order_key` 는 (씨앗, 종목, 스캔일, 패턴)으로만 정해지므로")
    P("   두 모집단에 «같이» 있는 후보는 두 판에서 **같은 순번**을 갖는다.")
    P(F3)
    P("")
    P("### A6 · B3 · C1 을 «나란히»")
    P("")
    P("| | A6 — 사다리 «없음» | B3 — 사다리②＋실적 | C1 — 사다리② «만» |")
    P("|---|---:|---:|---:|")
    for lab, key in (("후보 경로", "n_path"), ("거래", "n_trade")):
        P("| %s | %d | %d | %d |"
          % (lab, res["A6"][key], res["B3"][key], res["C1"][key]))
    for lab, key, unit in (("체결(중앙)", "n_filled", ""), ("승률(중앙)", "win", PCT),
                           ("거래당(중앙)", "per_trade", PCT)):
        P("| %s | %.3f%s | %.3f%s | %.3f%s |"
          % (lab, st.median(res["A6"][key]), unit, st.median(res["B3"][key]), unit,
             st.median(res["C1"][key]), unit))
    P("| 세후 총액(중앙·만원) | %.2f | %.2f | %.2f |"
      % (st.median(res["A6"]["posts"]), st.median(res["B3"]["posts"]),
         st.median(res["C1"]["posts"])))
    cs = {k: cagr_from_total(st.median(res[k]["posts"]), yrs) for k in ("A6", "B3", "C1")}
    P("| **연환산(세후)** | **%+.4f%s** | **%+.4f%s** | **%+.4f%s** |"
      % (cs["A6"], PCT, cs["B3"], PCT, cs["C1"], PCT))
    for tk in ("QQQ", "SPY"):
        P("| 우리 − %s | %+.4f%sp | %+.4f%sp | %+.4f%sp |"
          % (tk, cs["A6"] - bm[tk]["cagr"], PCT, cs["B3"] - bm[tk]["cagr"], PCT,
             cs["C1"] - bm[tk]["cagr"], PCT))
    P("| 낙폭(중앙) | %.2f%s | %.2f%s | %.2f%s |"
      % (st.median(res["A6"]["mdds"]), PCT, st.median(res["B3"]["mdds"]), PCT,
         st.median(res["C1"]["mdds"]), PCT))
    P("| 회복 최장(년) | %.1f | %.1f | %.1f |"
      % (max(res["A6"]["recs"]) / 252.0, max(res["B3"]["recs"]) / 252.0,
         max(res["C1"]["recs"]) / 252.0))
    P("")
    P("### C1 − B3 — 「실적 판정을 «뺀» 몫」. A 계열의 같은 이름과 «다른 수»인가")
    P("")
    dch = [res["C1"]["cagrs"][i] - res["B3"]["cagrs"][i] for i in range(a.seeds)]
    dmd = [res["C1"]["mdds"][i] - res["B3"]["mdds"][i] for i in range(a.seeds)]
    a_share = (cagr_from_total(st.median(res["A2"]["posts"]), yrs)
               - cagr_from_total(st.median(res["A1"]["posts"]), yrs))
    P("| 어디서 잰 몫 | 무엇에서 무엇으로 | 몫(%sp) |" % PCT)
    P("|---|---|---:|")
    P("| A 계열(위→아래 순서) | A1 -> A2 (사다리 «없는» 바닥에서 실적 뺌) | **%+.4f** |"
      % a_share)
    P("| C 계열(이 판) | B3 -> C1 (사다리② «있는» 바닥에서 실적 뺌) | **%+.4f** |"
      % (cs["C1"] - cs["B3"]))
    P("")
    gap_ = (cs["C1"] - cs["B3"]) - a_share
    fr_ = (cagr_from_total(st.median(res["A6"]["posts"]), yrs)
           - cagr_from_total(st.median(res["A5"]["posts"]), yrs))
    fr_b = cs["B3"] - cagr_from_total(st.median(res["B2"]["posts"]), yrs)
    P("★ 두 몫의 차 **%+.4f%sp** = 채택 문턱(%+.1f%sp)의 **%.0f%s**"
      % (gap_, PCT, THRESH, PCT, 100.0 * abs(gap_) / THRESH, PCT))
    P("  ⛔ 「그러니 빼서 어림해도 된다」로 읽지 «않는다» — «한» 손잡이의 «한» 관측이다.")
    P("  ★ 같은 자로 «마찰» 몫을 보면: A 계열 %+.4f vs B 계열 %+.4f = 차 **%+.4f%sp**"
      % (fr_, fr_b, fr_b - fr_, PCT))
    P("    ⇒ 손잡이마다 «다르다». 실적은 문턱의 %.0f%s, 마찰은 %.0f%s 만큼 어긋났다."
      % (100.0 * abs(gap_) / THRESH, PCT, 100.0 * abs(fr_b - fr_) / THRESH, PCT))
    P("")
    P("짝 비교 — 씨앗별 «같은 번호»끼리: C1 이 이긴 판 **%d / %d** · "
      "낙폭이 얕아진 판 **%d / %d**"
      % (sum(1 for v in dch if v > 0), a.seeds,
         sum(1 for v in dmd if v > 0), a.seeds))
    P("  수익 몫 중앙 **%+.4f%sp** · 낙폭 몫 중앙 **%+.2f%sp**"
      % (st.median(dch), PCT, st.median(dmd), PCT))
    P("")

    P("## 🔺 L 계열 — **노출 사다리** (사전등록 " + BQ
      + "ladder-preregistration.md" + BQ + ")")
    P("")
    P("27.4년을 여러 판 돌렸지만 **노출은 늘 5칸 고정**이었다. 「언제 크게 걸고 언제 손을")
    P("떼는가」를 «한 번도 안 쟀다». ⇒ 「없다」가 아니라 **「안 쟀다」**. 이 절이 그것을 잰다.")
    P("")
    P(F3)
    P("L0 현금 %.0f%s   L1 파일럿 %.0f%s   L2 절반 %.0f%s   L3 풀 %.0f%s   (평소 크기 대비)"
      % (LADDER_MULT[0] * 100, PCT, LADDER_MULT[1] * 100, PCT,
         LADDER_MULT[2] * 100, PCT, LADDER_MULT[3] * 100, PCT))
    P("")
    P("최근 «청산된» %d거래의 손익 «합» > 0  ->  한 칸 «올린다»" % LADDER_N)
    P("                              < 0  ->  한 칸 «내린다»")
    P("%d거래가 안 쌓였으면                ->  L%d 에서 시작 · 한 번에 «한 칸»만"
      % (LADDER_N, LADDER_START))
    P("자: 원전에서 «확인된» 문장 하나 — are your last 4 or 5 stocks profitable on balance")
    P("")
    P("⛔ 안 쓴 것: 고정 연패 횟수 · 타율 회복 · 파일럿 4단계 (원전 정리본이 「그의 것이 아니다」)")
    P("🚨 「손익」의 «단위» — 계좌 기준 «실현손익»(`sim_lots` 의 `exit_log` 와 «같은 자»)으로 읽었다.")
    P("   원전 「on balance」가 «돈» 이야기라서다. ⛔ 「자리 수익률 %s 의 합」으로는 «안 재 봤다»."
      % PCT)
    P(F3)
    P("")
    P("### 관문 G5 — 내 사다리 장부 = 엔진 자신의 청산 장부")
    P("")
    P(F3)
    P("`slot_sim_lots` 의 `size_fn` 이 주는 `recent` 는 **승패 불리언**이라 「손익 합」을")
    P("만들 수 «없다». 그래서 `ev_fn` 으로 청산을 «스스로» 장부했다 — 엔진은 «안» 고쳤다.")
    P("그 장부가 맞는지를 엔진 자신의 `exit_log`(청산일·계좌기준 실현손익)와 `recent`(승패열)에")
    P("**원소별로** 맞댄다. 어긋나면 그 자리에서 멈춘다.")
    P("")
    g5bad = 0
    for k in LADDER_ARMS:
        nseeds = len(res[k]["lads"])
        ncl = sum(len(l.pnl) for l in res[k]["lads"])
        nb = len(res[k]["gate"])
        g5bad += nb
        P("%-5s 씨앗 %d판 · 장부한 청산 %d건 · 어긋남 **%d건**" % (k, nseeds, ncl, nb))
    P(F3)
    P("")
    P("%s **G5** — 팔 %d개 · 씨앗 %d판 · 어긋남 합 **%d**"
      % ("✅" if g5bad == 0 else "🚨", len(LADDER_ARMS), a.seeds, g5bad))
    P("")
    P("### 노출 단계별로 «보낸 시간» — 달력일 무게 (사건일 수가 아니라)")
    P("")
    P("🔴 「대부분 현금이라 안 잃었다」면 그건 «다른» 이야기다. 이 수가 없으면 해석이 안 된다.")
    P("")
    P("| 팔 | L0 현금 | L1 ¼ | L2 ½ | L3 풀 | 덮은 날수 |")
    P("|---|---:|---:|---:|---:|---:|")
    for k in LADDER_ARMS:
        occ = [occupancy(l) for l in res[k]["lads"]]
        occ = [o for o in occ if o]
        if not occ:
            continue
        med = [st.median([o[0][i] for o in occ]) for i in range(len(LADDER_MULT))]
        P("| %s | %.1f%s | %.1f%s | %.1f%s | %.1f%s | %d |"
          % (k, med[0], PCT, med[1], PCT, med[2], PCT, med[3], PCT,
             int(st.median([o[1] for o in occ]))))
    P("")
    P("(씨앗 %d판의 «중앙값». 아래 L0 표가 판마다의 흩어짐을 본다)" % a.seeds)
    P("")
    P("### 🚨 L0 은 «흡수벽»이 될 수 있다 — 규칙에서 나오는 성질이라 «그대로» 잰다")
    P("")
    P("L0 에서는 «아무것도 안 산다» ⇒ 새 청산이 «안 생긴다» ⇒ **칸을 움직일 사건이 없다**.")
    P("들고 있던 것이 다 닫히고 나면 L0 에 **영원히** 갇힌다. ⛔ 규칙을 고치지 «않고» 센다.")
    P("")
    P("| 팔 | 끝났을 때 L0 인 씨앗 | L0 최장 연속(년) 중앙 | L0 최장 연속(년) 최악 | 동점(합=0) |")
    P("|---|---:|---:|---:|---:|")
    for k in LADDER_ARMS:
        stuck, runs, ties = 0, [], 0
        for l in res[k]["lads"]:
            if l.tl and l.tl[-1][1] == 0:
                stuck += 1
            ties += l.ties
            best = cur_ = 0
            for i in range(len(l.tl) - 1):
                if l.tl[i][1] == 0:
                    cur_ += _ord(l.tl[i + 1][0]) - _ord(l.tl[i][0])
                    best = max(best, cur_)
                else:
                    cur_ = 0
            runs.append(best / 365.25)
        P("| %s | %d / %d | %.2f | %.2f | %d |"
          % (k, stuck, len(res[k]["lads"]), st.median(runs), max(runs), ties))
    P("")
    P("### 사다리를 «얹은» 몫 — L1 − B3 · L3 − A6 (지수와의 비교와 «다른» 물음)")
    P("")
    P("| 얹은 곳 | 바닥 | 사다리 | 몫(%sp) | 낙폭 바닥 | 낙폭 사다리 | 낙폭 몫 |" % PCT)
    P("|---|---:|---:|---:|---:|---:|---:|")
    for lk, bk in (("L1", "B3"), ("L2", "B3"), ("L3", "A6"), ("L1n4", "B3")):
        cl = cagr_from_total(st.median(res[lk]["posts"]), yrs)
        cb = cagr_from_total(st.median(res[bk]["posts"]), yrs)
        ml, mb = st.median(res[lk]["mdds"]), st.median(res[bk]["mdds"])
        P("| %s − %s | %+.4f%s | %+.4f%s | **%+.4f** | %.2f%s | %.2f%s | **%+.2f** |"
          % (lk, bk, cb, PCT, cl, PCT, cl - cb, mb, PCT, ml, PCT, ml - mb))
    P("")
    P("⚠️ 사다리의 «목적»이 낙폭 줄이기다. **수익만 보면 이 판의 뜻을 놓친다.**")
    P("")
    P("### 짝 비교 — 씨앗별로 «같은 번호»끼리 (바닥 대비 사다리)")
    P("")
    P("| 얹은 곳 | 사다리가 이긴 판 | 낙폭이 얕아진 판 | 수익 몫 중앙 | 낙폭 몫 중앙 |")
    P("|---|---:|---:|---:|---:|")
    for lk, bk in (("L1", "B3"), ("L2", "B3"), ("L3", "A6"), ("L1n4", "B3")):
        dc = [res[lk]["cagrs"][i] - res[bk]["cagrs"][i] for i in range(a.seeds)]
        dm = [res[lk]["mdds"][i] - res[bk]["mdds"][i] for i in range(a.seeds)]
        P("| %s − %s | %d / %d | %d / %d | %+.4f%sp | %+.2f%sp |"
          % (lk, bk, sum(1 for v in dc if v > 0), a.seeds,
             sum(1 for v in dm if v > 0), a.seeds,
             st.median(dc), PCT, st.median(dm), PCT))
    P("")

    P("## ⛔ 판정 «칸»의 수 — 사전등록이 «미리» 박은 칸 «넷»")
    P("")
    P("⛔ **판정 문장은 여기서 «안» 쓴다** — 사전등록 표에 대는 것은 두뇌 몫이다. 수만 낸다.")
    P("")
    P(F3)
    P("채택 문턱 = 연 **+%.1f%sp** (우리 − QQQ). 기회비용 문턱이지 통계 문턱이 아니다."
      % (THRESH, PCT))
    P("")
    for k, what in (("A6", "A 계열 판정 칸 — 사다리 «없음» (지금 실전 도구) · 마찰 F2"),
                    ("B3", "B 계열 판정 칸 — 사다리②＋실적 «있음» · 숏 «없음» · 마찰 F2"),
                    ("L1", "L 계열 판정 칸 — B3 바닥 + 노출 사다리(크기만 · 최근 5거래)"),
                    ("C1", "C 계열 판정 칸 — 사다리② «만» · 실적 판정 «없음» · 마찰 F2")):
        ck_ = cagr_from_total(st.median(res[k]["posts"]), yrs)
        P("**%s** — %s" % (k, what))
        for tk in ("QQQ", "SPY"):
            P("   우리 − %-3s   연환산 **%+.4f%sp**   (우리 %+.4f%s · %s %+.4f%s)"
              % (tk, ck_ - bm[tk]["cagr"], PCT, ck_, PCT, tk, bm[tk]["cagr"], PCT))
        P("   씨앗 %d판 중 QQQ 를 «넘은» 판 **%d개** · SPY 를 넘은 판 **%d개**"
          % (a.seeds,
             sum(1 for x in res[k]["cagrs"] if x > bm["QQQ"]["cagr"]),
             sum(1 for x in res[k]["cagrs"] if x > bm["SPY"]["cagr"])))
        P("")
    P(F3)
    P("")
    P("### 씨앗 %d판 «전부» — ⛔ 중앙값 하나로 줄이지 않는다 (연환산 %s)" % (a.seeds, PCT))
    P("")
    for k, _nm, _p, _t, _c, _s, _f, _l in ARMS:
        P("**%s**  " % k + " · ".join("%+.2f" % x for x in sorted(res[k]["cagrs"])))
    P("")
    P("| 팔 | 최악 | 하위25 | 중앙 | 상위25 | 최선 | QQQ 대비 최악 | QQQ 대비 중앙 |")
    P("|---|---:|---:|---:|---:|---:|---:|---:|")
    q = bm["QQQ"]["cagr"]
    for k, _nm, _p, _t, _c, _s, _f, _l in ARMS:
        vv = sorted(res[k]["cagrs"])
        n_ = len(vv)
        P("| %s | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f |"
          % (k, vv[0], vv[max(0, n_ // 4)], st.median(vv),
             vv[min(n_ - 1, 3 * n_ // 4)], vv[-1], vv[0] - q, st.median(vv) - q))
    P("")
    P("🚨 이 분포는 **«우리 규칙의 운»(슬롯 고르기 난수)**이지 «시장의 운»이 아니다.")
    P("   시장 축은 아래 국면 표와 연별 구간이 잰다. **이 표로 그것을 덮지 않는다.**")
    P("")

    # ── 낙폭·회복 ───────────────────────────────────────────────────────
    P("## 낙폭(MDD)과 회복기간 — 「평생 굴리는 사람에게 bad case 는 낙폭이다」")
    P("")
    P("| 팔 | 낙폭 최악 | 낙폭 중앙 | 낙폭 최얕 | 회복 최장(년) | 회복 중앙(년) |")
    P("|---|---:|---:|---:|---:|---:|")
    for k, _nm, _p, _t, _c, _s, _f, _l in ARMS:
        m_ = sorted(res[k]["mdds"])
        r_ = sorted(res[k]["recs"])
        P("| %s | %.2f%s | %.2f%s | %.2f%s | %.1f | %.1f |"
          % (k, m_[0], PCT, st.median(m_), PCT, m_[-1], PCT,
             r_[-1] / 252.0, st.median(r_) / 252.0))
    for tk in ("QQQ", "SPY"):
        P("| %s 그냥 보유 | %.2f%s | %.2f%s | %.2f%s | %.1f | %.1f |"
          % (tk, bm[tk]["mdd"], PCT, bm[tk]["mdd"], PCT, bm[tk]["mdd"], PCT,
             bm[tk]["rec"] / 252.0, bm[tk]["rec"] / 252.0))
    P("")
    P("🚨 **이 낙폭은 «실현» 기준이다**(감사 ① 구멍 1) — " + BQ + "sim_lots" + BQ
      + " 의 곡선은 청산 때만 움직인다.")
    P("   미실현 평가가 없으므로 **실제 계좌 곡선보다 얕다**. 크기는 «안 쟀다».")
    P("")

    # ── 국면 셋 ─────────────────────────────────────────────────────────
    P("## 국면 셋으로 쪼갠 수 — 「부호가 한 국면에서 오는가」")
    P("")
    P("⚠️ 잘라 재는 것은 «따로 돌리는 것»과 **다르다**(108:2) — 앞 국면의 자산을 물려받는다.")
    P("")
    P("🚨 **세금은 국면마다 «따로» 매겼다** — 창 끝에 남은 미실현까지 판 것으로 친다.")
    # 🚨 「곱해도 안 나온다」의 까닭이 «둘»이다. «둘 다» 수로 낸다 — 말로 하면 하나만 적힌다.
    cov = 0
    gaps = []
    prev = d0
    for _l, ra, rb in REGIMES:
        aa, bb = max(ra, d0), min(rb, d1)
        if _ord(bb) <= _ord(aa):
            continue
        if _ord(aa) > _ord(prev):
            gaps.append((prev, aa))
        cov += _ord(bb) - _ord(aa)
        prev = bb
    if _ord(d1) > _ord(prev):
        gaps.append((prev, d1))
    span = _ord(d1) - _ord(d0)
    P("   ⇒ 까닭 ① 세금 — 국면 배수를 «곱하면» 창 끝 청산이 «세 번» 일어난 값이 된다.")
    P("   ⇒ 까닭 ② 덮개 — 국면 셋이 창의 **%.1f%s**(%d일/%d일)만 덮는다. 안 덮인 곳: %s"
      % (100.0 * cov / span, PCT, cov, span,
         (" · ".join("%s~%s(%d일)" % (x, y, _ord(y) - _ord(x)) for x, y in gaps))
         if gaps else "«없음»"))
    P("   ⇒ 그래서 **세전 배수끼리 곱해도 전체와 «안» 맞는다**. 세전 배수를 «같이» 적는 것은")
    P("      「세금 몫」과 「덮개 몫」을 읽는 이가 «갈라» 볼 수 있게 하려는 것이다.")
    P("🔵 마지막 국면의 곡선은 " + BQ + "d1" + BQ
      + " 뒤의 «청산까지» 포함한다(헤드라인과 «같은» 규약). 연수는 " + BQ + "d1" + BQ + " 까지로 센다.")
    P("")
    P("| 국면 | 팔 | 연수 | 세전 배수(중앙) | 세후 배수(중앙) | 연환산(세후) "
      "| QQQ 연환산 | 차 |")
    P("|---|---|---:|---:|---:|---:|---:|---:|")
    for lab, ra, rb in REGIMES:
        aa, bb = max(ra, d0), min(rb, d1)
        if _ord(bb) - _ord(aa) < 200:
            continue
        ry = (_ord(bb) - _ord(aa)) / 365.25
        bb_c = bb if bb < d1 else "9999-12-31"     # 마지막 국면은 청산까지 따라간다
        qb = bench_after_tax("QQQ", aa, bb)
        qc = qb["cagr"] if qb else float("nan")
        for k in REGIME_ARMS:
            mults, pre = [], []
            for cds, ccv, real in res[k]["curves"]:
                w = window_idx(cds, aa, bb_c)
                if w is not None:
                    mults.append(r124.taxed_window(cds, ccv, real, w[0], w[1]) / START)
                    pre.append(ccv[w[1]] / ccv[w[0]])
            if not mults:
                continue
            med = st.median(mults)
            cg = (med ** (1.0 / ry) - 1.0) * 100.0 if med > 0 else float("nan")
            P("| %s | %s | %.2f | %.3f배 | %.3f배 | %+.3f%s | %+.3f%s | %+.3f |"
              % (lab, k, ry, st.median(pre), med, cg, PCT, qc, PCT, cg - qc))
    P("")

    # ── 연별 초과수익 구간 ──────────────────────────────────────────────
    P("## 연별 초과수익과 95%s 구간 — **세전** (152 와 «같은 식»)" % PCT)
    P("")
    P("⛔ 「구간이 0 을 포함」을 「효과 없다」로도 「있다」로도 읽지 않는다. **「못 가림」**이다.")
    P("")
    P("| 비교 | 연 관측 | 산술 초과 | SD | 95 구간 | 0 | 가리려면 |")
    P("|---|---:|---:|---:|---|---|---:|")
    y0a, y1a = int(d0[:4]) + 1, int(d1[:4]) - 1
    for k in CI_ARMS:
        for tk in ("SPY", "QQQ"):
            ib = bm[tk]
            ia = annual(ib["ds"], ib["cv"], y0a, y1a)
            per, ys = [], None
            for cds, ccv, _real in res[k]["curves"]:
                ua = annual(cds, ccv, y0a, y1a)
                yy = sorted(set(ua) & set(ia))
                if ys is None:
                    ys = yy
                per.append([100.0 * (ua[y] - ia[y]) for y in yy])
            n_ = len(ys or [])
            if n_ < 5:
                P("| %s 우리−%s | %d | — | — | 못 잰다 | — | — |" % (k, tk, n_))
                continue
            ex = [st.mean([p[i] for p in per]) for i in range(n_)]
            m_, sd_ = st.mean(ex), st.stdev(ex)
            se = sd_ / math.sqrt(n_)
            tt = T95.get(n_, 2.06)
            lo, hi = m_ - tt * se, m_ + tt * se
            P("| %s 우리−%s | %d | %+.3f%sp | %.3f | [%+.3f, %+.3f] | %s | %.0f년 |"
              % (k, tk, n_, m_, PCT, sd_, lo, hi,
                 "🚨 포함" if lo <= 0 <= hi else "✅ 배제", need_years(m_, sd_)))
    P("")
    P("🚨 이 표는 **세전**이다(양쪽 다). 위의 판정 수는 **세후**라 «다른 자»다.")
    P("")

    # ── 저장 ────────────────────────────────────────────────────────────
    dump = {"window": {"d0": d0, "d1": d1, "years": yrs, "y0": a.y0, "y1": a.y1},
            "seeds": a.seeds, "fric": FRIC, "judge_cell": JUDGE_CELL,
            "dup_entries": {"trade_delta": dup, "cross_year_blocked": n_xy,
                            "n_trade_bug": n_bug, "n_trade_fix": n_fix},
            "bench": {tk: {kk: bm[tk][kk] for kk in
                           ("post", "cagr", "mdd", "rec", "years")} for tk in bm},
            "arms": {k: {kk: res[k][kk] for kk in
                         ("name", "pop", "carry", "short", "fric", "n_path",
                          "n_trade", "posts", "cagrs", "mdds", "recs",
                          "n_filled", "win", "per_trade", "ladder", "occ")}
                     for k in res}}
    pth = OUT / ("270-live-rules-rerun%s.json" % ("" if full else "-smoke"))
    atomic_write(pth, json.dumps(dump, ensure_ascii=False, separators=(",", ":")))
    P("저장: " + BQ + str(pth.name) + BQ)
    P("")
    P("전체 소요 **%.1f초** (경로 재생 %.1f · 판 돌리기 %.1f)"
      % (time.time() - t_all, t_replay, t_sim))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
r"""경로를 «해마다 걸러 버리며» 올린다 — 28년치를 통째로 올리면 메모리가 터진다.

🚨 실측: 경로 145,287건 × 약 250봉 × 5배열 × 32바이트 ≈ **5.8GB**.
   `91.load_ladder` 는 사다리 셋(by0·by1·by2)을 «다» 들고 있어 93 에서 겨우 들어갔고,
   다른 작업이 1GB 만 써도 **MemoryError** 가 난다(96 에서 두 번 났다).

이 모듈은 **필요한 것만** 남긴다:
  · `by2` (조합) 만 남기고 나머지는 «그 해가 끝나면 버린다»
  · `by0` 은 «날짜별 후보 «수»» 로만 요약해 둔다(97 의 시장 폭 신호에 그것만 필요하다)

🚨 «거르는 규칙»은 91 과 «같은 코드»를 쓴다 — 옮겨 적지 않는다.
"""
from __future__ import annotations

import importlib.util as _u
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
r61b, r61 = r91.r61b, r91.r61


def load_combo(years, d0, d1, monthly_file="91-monthly-us-full.json"):
    """조합(사다리 ②) 경로만 남기고 + 날짜별 «전체 후보 수»를 함께 낸다.

    반환: (by2, cand_per_day, n_all)
    """
    pack = json.loads((r91.OUT / monthly_file).read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    lo_ym = r61.prev_ym(d0[:7], 8)
    months = sorted({m for d in monthly.values() for m in d if m >= lo_ym})
    mret = r61b.month_returns(monthly, sector, months)
    sec_top, in_pct = r61b.make_flags(mret, sector)
    del pack, monthly, mret

    def lvl2(p):
        s = sector.get(p["code"])
        if not s:
            return True
        ym = r61.prev_ym(p["scan_date"][:7], 1)
        top = sec_top.get(ym)
        if top is None:
            return True
        if s not in top:
            return False
        v = in_pct.get(ym, {}).get(p["code"])
        return (v is None) or (r91.LO <= v < r91.HI)

    by2, cand, n_all = {}, Counter(), 0
    for y in years:
        f = r91.SUB / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        with open(f, encoding="utf-8") as fh:
            ps = json.load(fh)["trigger_paths"]
        keep = []
        for p in ps:
            if not (d0 <= p["entry_date"] <= d1):
                continue
            n_all += 1
            cand[p["entry_date"]] += 1          # ← 시장 폭은 «수»만 필요하다
            if lvl2(p):
                keep.append(p)
        by2[y] = keep
        del ps                                   # 🚨 그 해를 «버린다»
    return by2, cand, n_all

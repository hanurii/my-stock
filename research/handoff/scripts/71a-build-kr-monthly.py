# -*- coding: utf-8 -*-
"""71a — 한국 월말 종가 패널 + 업종 라벨 + KOSPI 대용. (미국 61a 의 한국판)

🚨 pdata 는 «비수정주가»다 — 미국 `close`(분할조정)와 성질이 다르다.
   그래서 **`fltRt`(전일 대비 등락률)로 «수익률 계열»을 만들어** 6개월 수익률을 낸다.
   (분할·병합이 있어도 등락률은 연속이다. 프로젝트 정본 규약: 일봉=pdata + fltRt 복원)
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
PDATA = ROOT / ".cache" / "pdata"
OUT = ROOT / ".cache" / "bt5y" / "out" / "71-monthly-kr.json"

def main() -> int:
    desc = json.loads((ROOT / ".cache" / "krx_desc.json").read_text(encoding="utf-8"))
    sect = {c: (v.get("industry") or "").strip() for c, v in desc.items()
            if (v.get("industry") or "").strip()}
    files = sorted(PDATA.glob("price_*.json"))
    files = [p for p in files if p.stem[6:] >= "20200101"]
    idx = defaultdict(float)          # 날짜 -> KOSPI 시총합
    lvl = {}                          # code -> 누적 지수(1.0 시작)
    mo = defaultdict(dict)            # code -> {YYYY-MM: 누적지수}
    n = 0
    for p in files:
        d = p.stem[6:]
        ym = "%s-%s" % (d[:4], d[4:6])
        day = json.loads(p.read_text(encoding="utf-8"))
        n += 1
        for code, r in day.items():
            try:
                fl = float(r.get("fltRt"))
                c = float(r.get("clpr"))
            except (TypeError, ValueError):
                continue
            if c <= 0:
                continue
            cur = lvl.get(code)
            lvl[code] = (1.0 if cur is None else cur * (1 + fl / 100.0))
            mo[code][ym] = lvl[code]
            if r.get("mrktCtg") == "KOSPI":
                try: idx[d] += float(r.get("mrktTotAmt") or 0.0)
                except (TypeError, ValueError): pass
    print("일자 %d · 종목 %d · 업종 라벨 %d" % (n, len(mo), len(sect)), flush=True)
    ks = sorted(idx)
    print("KOSPI 대용 %s ~ %s · %+.2f%%" % (ks[0], ks[-1], (idx[ks[-1]] / idx[ks[0]] - 1) * 100),
          flush=True)
    OUT.write_text(json.dumps({"sector": sect, "monthly": {k: v for k, v in mo.items()},
                               "kospi": {k: idx[k] for k in ks}},
                              ensure_ascii=False), encoding="utf-8")
    print("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

"""오늘 감시할 진입임박 후보 로드 + 국면지수(등가중) 구성."""
from __future__ import annotations
import json


def load_actionable(paths):
    """sepa-*-candidates.json 들에서 status=='actionable' & entry_ready & pivot 있는 것 로드.
    code 중복 제거(첫 등장 유지). 반환 [{code,name,pivot,pattern}].

    ★ entry_ready 필수 — 검출기의 status='actionable'은 패턴 미검출이어도 (가격이 피벗 5% 이내 +
    거래량 마름)만으로 찍힌다. 진짜 매수 대상은 패턴 확정(entry_ready = detected & status in
    breakout/actionable)이라야 하며, 이는 /stocks/sepa 페이지의 🟢진입임박 정의와 일치한다."""
    seen, out = set(), []
    for p in paths:
        try:
            d = json.loads(open(p, encoding="utf-8").read())
        except Exception:
            continue
        pat = "VCP" if "vcp" in p else "3C" if "3c" in p else "PP" if "power" in p else "?"
        for c in d.get("candidates", []):
            if c.get("status") == "actionable" and c.get("entry_ready") and c.get("pivot_price") and c["code"] not in seen:
                seen.add(c["code"])
                out.append({"code": c["code"], "name": c.get("name"),
                            "pivot": float(c["pivot_price"]), "pattern": pat})
    return out


def build_ew_index(get_series, codes):
    """등가중 시장지수 종가열 — 각 날짜 평균 일간수익을 누적. get_series(code)->{dates,closes}.
    첫 날짜는 기준(1.0)으로 포함 — 반환열 길이가 날짜열 길이와 일치."""
    from collections import defaultdict
    rs, rc, all_dates = defaultdict(float), defaultdict(int), set()
    for code in codes:
        s = get_series(code)
        if not s:
            continue
        ds, cl = s.get("dates") or [], s.get("closes") or []
        all_dates.update(ds)
        for i in range(1, len(cl)):
            if cl[i] and cl[i - 1] and 0.5 < cl[i] / cl[i - 1] < 1.5:
                rs[ds[i]] += cl[i] / cl[i - 1] - 1
                rc[ds[i]] += 1
    lvl, out = 1.0, []
    for dt in sorted(all_dates):
        if dt in rc:
            lvl *= (1 + rs[dt] / rc[dt])
        out.append(lvl)
    return out

# -*- coding: utf-8 -*-
"""pdata 일자 스냅샷 → 수정주가 시계열(백테스트용).

왜 필요한가
-----------
`.cache/ohlcv/series` 는 화면용 **400영업일 롤링**이라 2024-12 이전이 없다.
반면 `.cache/pdata/price_YYYYMMDD.json` 은 2020-01-02 부터 1,600일 넘게
그날 그대로 보존돼 있고 **상장폐지 종목도 들어 있다**(생존 편향 없음).
과거 구간 백테스트는 이쪽에서 시계열을 만들어 써야 한다.

핵심 문제 — pdata 는 비수정주가
-------------------------------
액면분할·병합·감자가 나면 가격이 통째로 점프한다. 그대로 200일선을 그리면
가짜 급등이 생겨 52주 신고가·RS·이평선이 전부 틀어진다(2026-07-31 금호전기
+360% 사고와 같은 종류).

해법은 **등락률(fltRt) 연쇄**다. fltRt 는 기준가 변경을 이미 반영한 값이라
`cumprod(1 + fltRt/100)` 이 곧 수정 지수가 된다. 그 지수를 **마지막 실제
종가**에 맞춰 배율만 옮기면 수정주가가 된다(최신 가격은 진짜 값 유지).

시·고·저는 같은 날 안에서는 분할의 영향을 받지 않으므로 **그날의 종가 대비
비율**을 그대로 옮긴다.

거래량은 분할이 나면 주식 수가 바뀌어 그대로 쓰면 안 된다. **거래대금은
분할에 불변**이므로 `거래대금 ÷ 수정가` 로 되돌린 것이 유일하게 안전한 경로다
(검출기들이 거래량 배수 v/MA50 을 쓰기 때문에 이 일관성이 중요하다).
"""
from __future__ import annotations

import re

__all__ = ["build_series"]

# '미너비니가 사지 않는 주식' 중 유니버스 단계에서 확정적으로 뺄 것.
# 우선주·저유동성은 하네스가 따로 거르므로 여기선 건드리지 않는다.
_FOREIGN = re.compile(r"^9\d{5}$")       # 코스닥 외국법인
_MARKETS = ("KOSPI", "KOSDAQ")           # KONEX 제외


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None          # NaN 배제


def build_series(days) -> dict[str, dict]:
    """pdata 일자 스냅샷 → {종목코드: 시계열 dict}.

    `days` 는 둘 중 하나:
      - `{날짜: {종목코드: 레코드}}` dict (작은 구간·테스트용)
      - `(날짜, {종목코드: 레코드})` 를 **날짜 오름차순**으로 내는 이터러블
        (1,600일치를 통째로 메모리에 올리지 않으려면 이쪽)

    반환 시계열은 `.cache/ohlcv/series` 와 같은 스키마다:
    dates / closes / opens / highs / lows / volumes (모두 같은 길이).
    거래일에 등장하지 않은 날은 **넣지 않는다**(보간하지 않음).
    """
    stream = (((d, days[d]) for d in sorted(days)) if isinstance(days, dict)
              else days)
    raw: dict[str, dict[str, list]] = {}
    for date, recs in stream:
        for code, r in (recs or {}).items():
            if r.get("mrktCtg") not in _MARKETS or _FOREIGN.match(code):
                continue
            close = _num(r.get("clpr"))
            if not close or close <= 0:
                continue
            b = raw.get(code)
            if b is None:
                b = raw[code] = {"dates": [], "close": [], "flt": [],
                                 "open": [], "high": [], "low": [], "trprc": []}
            b["dates"].append(date)
            b["close"].append(close)
            b["flt"].append(_num(r.get("fltRt")))
            b["open"].append(_num(r.get("mkp")) or close)
            b["high"].append(_num(r.get("hipr")) or close)
            b["low"].append(_num(r.get("lopr")) or close)
            trprc = _num(r.get("trPrc"))
            if trprc is None:
                q = _num(r.get("trqu")) or 0.0
                trprc = q * close
            b["trprc"].append(trprc)

    out: dict[str, dict] = {}
    for code, b in raw.items():
        n = len(b["dates"])
        # 1) 등락률 연쇄로 수정 지수를 만든다.
        idx = [1.0] * n
        for i in range(1, n):
            f = b["flt"][i]
            if f is None or abs(f) > 100.0:
                # 등락률이 없거나 말이 안 되면 종가비로 대체(분할이면 여기서
                # 어긋나지만, 그런 날은 fltRt 가 정상이라 실제로는 거의 안 탄다).
                prev = b["close"][i - 1]
                ratio = (b["close"][i] / prev) if prev else 1.0
            else:
                ratio = 1.0 + f / 100.0
            if ratio <= 0:
                ratio = 1.0
            idx[i] = idx[i - 1] * ratio

        # 2) 마지막 실제 종가에 배율을 맞춘다 → 최신 가격은 진짜 값.
        scale = b["close"][-1] / idx[-1] if idx[-1] else 1.0
        closes = [v * scale for v in idx]

        opens, highs, lows, vols = [], [], [], []
        for i in range(n):
            c_raw, c_adj = b["close"][i], closes[i]
            k = (c_adj / c_raw) if c_raw else 1.0     # 그날의 환산 배율
            opens.append(b["open"][i] * k)
            highs.append(b["high"][i] * k)
            lows.append(b["low"][i] * k)
            # 3) 거래량 = 거래대금 ÷ 수정가 (거래대금은 분할 불변)
            vols.append((b["trprc"][i] / c_adj) if c_adj else 0.0)

        out[code] = {"dates": b["dates"], "closes": closes, "opens": opens,
                     "highs": highs, "lows": lows, "volumes": vols}
    return out

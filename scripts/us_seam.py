"""이음매 — Sharadar 뼈대에 야후 꼬리를 붙인다.

★ 붙이기 전에 그 창의 분할을 검사한다. 있으면 멈춘다.
  Sharadar 역사는 분할 전 가격이고 야후 꼬리는 분할 후 가격이라
  이음매에서 배수만큼 가짜 계단이 난다. 우리 규칙은 그것을 급락으로 읽는다.
  실측(2026-08-21 기준 20일 창): 분할 29개, 그중 대형주 하나(APH 2배).

야후는 Close 를 쓴다. Adj Close 가 아니다.
분할 없는 대형주 10개에서 Sharadar 와 최대 0.001% 안에서 맞았고,
Adj Close 는 배당만큼 벌어진다(최대 1.331%).
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

# TAIL_PATH 는 us_matrix 가 정본이다(순환 import 방지 + 자가 둘이 되는 것 방지).
# 여기서 이름을 다시 내보내므로 `us_seam.TAIL_PATH` 는 종전대로 쓸 수 있다.
from canslim_lib.us_matrix import KEYS, TAIL_PATH, to_timestamp  # noqa: F401
# 분할 보정의 «판단 문턱»은 한국 쪽 상수를 «가져다» 쓴다 — 여기서 값을 다시
# 적으면 같은 것을 가리키는 자가 둘이 되고, 그 둘은 언젠가 갈라진다.
# (verify_frozen_params.py 의 2번 표가 이 두 상수를 얼려 두었다.)
#   REBASE_MIN_DEVIATION  이 안이면 「같다」로 본다
#   REBASE_RATIO_BOUNDS   이 밖의 배수는 기업행위로 안 본다
# 함수(rebase_history)는 «안» 가져온다 — 거래량을 안 건드리고 소수 둘째 자리로
# 반올림해서, 1달러 밑 미국 종목에서 값이 뭉개진다. 아래에서 새로 쓴다.
from canslim_lib.ohlcv_matrix import (  # noqa: E402
    REBASE_MIN_DEVIATION,
    REBASE_RATIO_BOUNDS,
)

ROOT = Path(__file__).resolve().parents[1]


def to_yahoo_symbol(code: str) -> str:
    """Sharadar 표기를 야후 표기로 바꾼다 — 점(.)이 대시(-)다. `BRK.B` -> `BRK-B`.

    왜 있나(2026-09-11 검토): 두 벤더가 «같은 종목»을 다르게 적는다. 야후는
    모르는 심볼에 예외를 내지 않고 «빈 표»를 준다. `fetch_tail` 의 계약은
    「표가 빈 종목은 실패가 아니다」(새 거래일이 없을 뿐)라서, 그 빈 표가
    `failed` 에 «안» 들어가고 그 종목은 날마다 «경고 없이» 옛 뼈대로 남는다.
    실측으로 뼈대 4,648종목 중 점 심볼 다섯(BF.B·BRK.B·CRD.A·LGF.B·MOG.A)이
    이 길로 새고 있었다. BRK.B 가 그중 하나다.

    ⛔ 뼈대와 산출물의 심볼 표기는 «바꾸지 않는다» — Sharadar 표기가 정본이다.
      바꾸는 것은 「야후에 물을 때」뿐이고, 받은 것은 «원래 심볼로 되돌려» 담는다.
    🔵 이 변환이 심볼 어긋남을 «전부» 잡는다고 읽지 마라. 우리가 아는 규칙
      하나를 푼 것이고, 야후가 다르게 적는 다른 꼴이 또 있으면 같은 길로 샌다.
      뼈대 4,648종목에 대시(-)를 쓰는 심볼은 0개이므로 이 변환이 두 종목을
      같은 야후 심볼로 뭉개는 일은 지금 자료에서는 없다(실측 2026-09-11).
    """
    return code.replace(".", "-")


# 분할 검사를 «몇 종목씩» 묶어 부르나. 2026-09-11 실측으로 고른 수다.
# 503종목 표본에서 50·200·500 셋 다 «똑같은» 분할 셋과 «똑같은» 미관측 목록을
# 냈고(야후가 조용히 자르지 않았다), 시간은 준비 한 번(첫 묶음 약 16초)을 빼면
# 200 과 500 이 같았다(503종목 14.6초 = 종목당 0.029초). 50 은 더 느렸다.
# 200 을 고른 까닭: 500 과 «속도가 같은데» 묶음 하나가 통째로 실패했을 때
# 따로 다시 물어야 할 종목이 절반 이하다.
SPLIT_BATCH = 200


def _splits_in_window(code: str, index, values, since: str, until: str) -> list[dict]:
    """(날짜, 배수) 짝에서 창 «안»의 0 아닌 분할만 골라 우리 모양으로 낸다.

    담을 때는 «원래»(Sharadar) 심볼을 쓴다 — 야후 표기는 물을 때만이다.
    """
    out = []
    for ts, ratio in zip(index, values):
        d = str(ts)[:10]
        if since <= d <= until and float(ratio) != 0.0:
            out.append({"code": code, "date": d, "ratio": float(ratio)})
    return out


def _splits_one(code: str, since: str, until: str) -> list[dict]:
    """한 종목만 «따로» 물어 창 안의 분할을 낸다. 못 보면 예외가 올라간다.

    묶음이 «못 본» 종목만 이 길로 다시 묻는다. 야후는 자기가 모르는 종목에도
    예외 없이 «빈» 답을 주므로, 빈 답은 여기서도 「분할 없음」으로 읽힌다 —
    그 구멍은 종전과 «같다»(`fetch_tail` docstring 이 이미 적어 둔 것).
    """
    sp = yf.Ticker(to_yahoo_symbol(code)).splits
    if sp is None or len(sp) == 0:
        return []
    return _splits_in_window(code, list(sp.index), list(sp.values), since, until)


def _splits_batch(codes: list[str], since: str, until: str) -> tuple[list, list]:
    """한 묶음을 `yf.download(..., actions=True)` 로 «묶어» 받는다.

    반환: (찾은 분할, 이 묶음에서 «못 본» 종목)
    세 갈래를 «코드로» 가른다 — 이 자리가 제일 깨지기 쉽다:
      ① 묶음 «전체»가 실패(예외·빈 표)      -> 그 묶음의 «모든» 종목이 미관측
      ② 그 종목의 열이 없거나 분할 열이 없음 -> 그 종목이 미관측
         (그 종목 봉이 «하나도» 없어 분할 값이 전부 NaN 인 경우도 여기다 —
          야후는 union 색인을 쓰므로 봉이 없는 날은 0 이 아니라 NaN 이다)
      ③ 열은 받았는데 분할 값이 0 뿐          -> «분할 없음»(정상). 미관측 아님
    """
    end = (datetime.date.fromisoformat(until)
           + datetime.timedelta(days=1)).isoformat()
    try:
        # 물을 때만 야후 표기로 바꾼다(to_yahoo_symbol).
        df = yf.download([to_yahoo_symbol(c) for c in codes], start=since, end=end,
                         interval="1d", actions=True, auto_adjust=False,
                         group_by="ticker", threads=True, progress=False)
    except Exception:
        return [], list(codes)                                      # ① 묶음 전체
    if df is None or len(df) == 0:
        return [], list(codes)                                      # ① 묶음 전체

    multi = isinstance(df.columns, pd.MultiIndex)
    top = set(df.columns.get_level_values(0)) if multi else set()
    splits: list[dict] = []
    unseen: list[str] = []
    for c in codes:
        y = to_yahoo_symbol(c)
        if multi:
            if y not in top:
                unseen.append(c)                                    # ② 열이 없다
                continue
            d = df[y]
        else:
            d = df
        if "Stock Splits" not in d.columns:
            unseen.append(c)                                        # ② 분할 열 없다
            continue
        col = d["Stock Splits"].dropna()
        if len(col) == 0:
            unseen.append(c)                                        # ② 봉이 없다
            continue
        splits += _splits_in_window(c, list(col.index), list(col.values),
                                    since, until)                   # ③ 0 뿐이면 빈 목록
    return splits, unseen


def check_splits(codes: list[str], since: str, until: str) -> dict:
    """[since, until] 안의 분할을 찾는다 — «닫힌» 구간이다(until 포함).

    반환: {"splits": [{"code","date","ratio"}], "failed": [code, ...]}
    둘 다 비어야 이어 붙여도 된다.
    failed 에 든 종목은 「분할 없음」이 아니라 「못 봤음」이다.
    부르는 쪽이 코드로 그 둘을 가릴 수 있어야 한다.

    ★ 왜 닫힌 구간인가: fetch_tail 은 end 없이 받아 «오늘 봉까지» 붙인다.
      이 검사 창이 반열린([since, until))이면 until 당일(=오늘)에 난 분할이
      검사 없이 그대로 붙는다 — 이 함수가 막으려던 바로 그 가짜 계단이다.
      ⇒ 이 함수의 창은 fetch_tail 이 «붙일» 범위와 «같아야» 한다.
    🔵 예고된 미래 분할(effective date 가 until 뒤)은 «일부러» 안 잡는다 —
      until 뒤는 여전히 창 밖이다(오늘 이후에 난 분할은 다음 번 검사가 잡는다).

    🔴 2026-09-11: 종목마다 `yf.Ticker(c).splits` 를 «따로» 부르던 것을
      `yf.download(..., actions=True)` 묶음으로 바꿨다. 4,648종목에 26.5분이
      걸려 `sepa-us` 한 판의 시간이 사실상 이 함수 하나였다.

      «못 본» 종목은 묶음이 끝난 뒤 «따로 한 번 더» 묻는다. 왜 그래야 하나 —
      묶음이 못 본 것을 그냥 「분할 없음」으로 읽으면 분할이 있는 종목이 조용히
      붙는다. 반대로 그것을 바로 `failed` 로 올리면, 야후에 자료가 «아예 없는»
      상장폐지 종목(실측 503종목 표본에서 9.9%)이 날마다 `failed` 에 들어가
      갱신이 영구히 멈춘다. 그래서 「따로 물어서도 못 보면」만 `failed` 다.
      ⇒ `failed` 의 뜻은 종전과 «똑같다»: 「물었는데 답을 못 받았음」.
    """
    splits: list[dict] = []
    failed: list[str] = []
    unseen: list[str] = []
    for i in range(0, len(codes), SPLIT_BATCH):
        got, miss = _splits_batch(codes[i:i + SPLIT_BATCH], since, until)
        splits += got
        unseen += miss
    for c in unseen:
        try:
            splits += _splits_one(c, since, until)
        except Exception:
            failed.append(c)
    splits.sort(key=lambda r: (r["code"], r["date"]))
    if failed:
        print(f"경고: {len(failed)} 종목 분할 조회 실패", file=sys.stderr)
    return {"splits": splits, "failed": failed}


def fetch_tail(codes: list[str], since: str) -> dict:
    """since «당일»부터 오늘까지 야후에서 받는다. Close 를 쓴다(Adj Close 아니다).

    🔴 2026-09-11 정정: 옛 문장은 「since «다음날»부터」였는데 «틀렸다».
      `yf.download(start=since)` 는 since 당일을 «포함»한다(실측: asof=2026-09-09 에
      09-09 봉이 같이 왔다). 결과는 무해하다 — `attach` 가 겹친 날을 버리고 뼈대를
      남기기 때문이다. 그러나 docstring 은 «계약»이라 틀린 채로 두면 언젠가 걸린다.
      ⇒ `check_splits` 의 창(`since <= d <= until`, 닫힌 구간)이 이 범위와 «같아야»
        하는 까닭도 이것이다. 좁으면 검사 안 된 날이 붙는다.

    반환: {"series": {code: {dates, opens, highs, lows, closes, volumes}},
           "failed": [code, ...]}
    check_splits 와 같은 결이다. failed 에 든 종목은 「거래가 없었음」이 아니라
    「받아 오지 «못» 했음」이다(전체 다운로드 예외·종목별 접근 예외). 부르는
    쪽이 코드로 그 둘을 가릴 수 있어야 한다.
    표가 비어 있는(거래일이 새로 없는) 종목은 실패가 아니다 — since 가
    최근 영업일 뒤일 때 흔히 생기며, 그냥 series 에 실리지 않는다.

    🔴 다만 «빈 표»에는 얼굴이 셋이다 — 「새 거래일이 없다」·「못 받았다」·
      «「심볼을 모른다」». 야후는 모르는 심볼에도 예외 없이 빈 표를 주므로
      셋째가 첫째로 새고, 그 종목은 «경고 없이» 영구히 옛 뼈대로 남는다.
      알려진 갈래 하나(점 심볼)는 `to_yahoo_symbol` 이 물을 때 풀지만,
      이 계약 문장은 여전히 「빈 표 = 새 거래일 없음」을 «주장하지 않는다».

    ★ yf.download 는 종목이 하나일 때와 여럿일 때 표 모양이 다르다.
      여럿이면 열이 (종목, 필드) 멀티인덱스라 df[code] 로 그 종목만 뗀다.
      하나면 열이 필드 하나짜리라 df[code] 는 없다(있어도 다른 뜻) —
      df.columns 가 멀티인덱스인지 직접 봐서 가른다.
    """
    series: dict = {}
    failed: list[str] = []
    if not codes:
        return {"series": series, "failed": failed}

    # 물을 때만 야후 표기로 바꾼다(to_yahoo_symbol). 받은 것은 아래에서
    # «원래» 심볼을 키로 담는다 — 뼈대·산출물의 표기는 Sharadar 가 정본이다.
    try:
        df = yf.download([to_yahoo_symbol(c) for c in codes], start=since,
                         interval="1d", auto_adjust=False,
                         group_by="ticker", threads=True, progress=False)
    except Exception:
        return {"series": series, "failed": list(codes)}

    multi = isinstance(df.columns, pd.MultiIndex)
    for c in codes:
        try:
            d = df[to_yahoo_symbol(c)] if multi else df
            d = d.dropna(how="all")
            if d.empty:
                continue
            series[c] = {
                "dates": [str(i)[:10] for i in d.index],
                "opens": [float(x) for x in d["Open"]],
                "highs": [float(x) for x in d["High"]],
                "lows": [float(x) for x in d["Low"]],
                "closes": [float(x) for x in d["Close"]],
                "volumes": [float(x) for x in d["Volume"]],
            }
        except Exception:
            failed.append(c)
    return {"series": series, "failed": failed}


def attach(base: dict, tail: dict) -> dict:
    """뼈대에 꼬리를 붙인다. 뼈대 기간 «안»은 뼈대가 정본이다(Sharadar).

    tail 은 fetch_tail 반환값의 "series" 그대로(코드 → 시계열)이지,
    fetch_tail 의 반환값 «전체»(failed 포함)가 아니다 — 부르는 쪽이 먼저
    실패를 가리고 성공분만 넘긴다.

    ⛔ fetch_tail(...) 의 반환값을 «그대로» 넘기면(unwrap 안 하면) tail 의
    키가 "series"·"failed" 뿐이라 모든 종목이 tail.get(code) → None 으로
    떨어진다 — 예외 «없이» base 를 그대로 복사해 돌려주므로 「새 거래일
    없음」(정상)과 «구분»이 안 된다. 그 모양을 여기서 미리 잡아 ValueError 로
    막는다(조용한 무동작 대신 시끄러운 실패).

    🔴 꼬리 봉을 «어느 것만» 붙이나 (2026-09-11 사용자 결정)

        꼬리 봉 날짜 <= 뼈대 마지막 날  ->  «버린다»
          · 뼈대에 이미 있으면 -> 겹침이다. 뼈대가 이긴다(종전과 같다)
          · 뼈대에 «없으면»   -> 뼈대 기간 «안»의 «구멍»이다. 다른 벤더 값으로
                                «메우지 않는다» — 뼈대 기간은 Sharadar 가
                                정본이고 27.4해 백테스트도 그 구멍이 «있는
                                채»로 돌았다. 메우면 그 구간만 벤더가 섞인다
        꼬리 봉 날짜 >  뼈대 마지막 날  ->  덧붙인다

    ★ 왜 바뀌었나: 종전 코드는 「뼈대에 없는 날」을 전부 «끝»에 덧붙였다.
      야후가 뼈대 마지막 날보다 «앞선» 봉을 돌려주면(실측 2026-09-11 CYCN:
      since=09-09 인데 09-08 봉이 왔다) 그 봉이 맨 뒤에 붙어 날짜 배열이
      «오름차순이 아니게» 된다. 그 아래 모든 것이 오름차순을 전제한다 —
      계열 자르기·`dates[-1]` 관문·RS 창·이동평균. 예외 없이 «값»이 틀린다.

    🔴 돌려주는 «모든» 계열이 날짜 오름차순임을 나가기 전에 확인하고, 아니면
      ValueError 로 «시끄럽게» 실패한다. 조용히 틀린 값을 내는 것이 이
      결함의 본체였다. 꼬리를 안 받은 계열(뼈대 그대로)도 함께 본다 —
      「어느 길로 왔나」에 기대면 안 보는 길이 하나 생긴다.

    반환값에 «버린 봉의 수와 종목»을 실어 보낸다(조용히 버리지 않는다):
        out["tail_dropped"] = {
            "n_codes":  구멍이 난 종목 수,
            "n_bars":   버린 구멍 봉 수,
            "n_overlap": 겹쳐서 버린 봉 수(뼈대에 «이미 있는» 날. 종전 동작),
            "codes":    {종목: [버린 날짜, ...]},
        }
      ⚠️ n_bars 와 n_overlap 은 «다른» 것을 센다. n_bars = 뼈대 기간 안인데
        뼈대에 «없는» 날(구멍), n_overlap = 뼈대에 «있는» 날(겹침). 한 낱말로
        묶지 마라.
    """
    if isinstance(tail.get("series"), dict) and isinstance(tail.get("failed"), list):
        raise ValueError(
            'attach() 의 tail 인자로 fetch_tail() 의 반환값 «전체»가 '
            '들어왔다({"series":..., "failed":...} 모양). tail 에는 '
            'fetch_tail(...)["series"] 만 넘겨라 — 실패는 부르는 쪽이 '
            '먼저 가려야 한다.'
        )
    out = {k: v for k, v in base.items() if k != "series"}
    ser = {}
    holes: dict[str, list[str]] = {}
    n_overlap = 0
    for c, s in base.get("series", {}).items():
        t = tail.get(c)
        if not t:
            ser[c] = s
            continue
        have = set(s["dates"])
        last = s["dates"][-1] if s["dates"] else ""
        add = []
        for i, d in enumerate(t["dates"]):
            if d in have:
                n_overlap += 1
                continue
            if d <= last:
                holes.setdefault(c, []).append(d)
                continue
            add.append(i)
        if not add:
            ser[c] = s
            continue
        # 꼬리가 스스로 뒤죽박죽일 수도 있으니 날짜순으로 세워 붙인다.
        add.sort(key=lambda i: t["dates"][i])
        new = {k: list(s[k]) + [t[k][i] for i in add] for k in KEYS}
        new["timestamps"] = [to_timestamp(d) for d in new["dates"]]
        ser[c] = new

    bad = []
    for c, s in ser.items():
        ds = s.get("dates") or []
        for a, b in zip(ds, ds[1:]):
            if a >= b:
                bad.append("%s(%s -> %s)" % (c, a, b))
                break
    if bad:
        raise ValueError(
            "attach(): 날짜가 오름차순이 아닌 계열 %d개 — 아래 모든 것이 "
            "오름차순을 전제하므로 조용히 내보내지 않는다. 앞 %d개: %s"
            % (len(bad), min(5, len(bad)), ", ".join(bad[:5])))

    out["series"] = ser
    out["asof"] = max((s["dates"][-1] for s in ser.values() if s["dates"]),
                      default=base.get("asof", ""))
    out["tail_dropped"] = {
        "n_codes": len(holes),
        "n_bars": sum(len(v) for v in holes.values()),
        "n_overlap": n_overlap,
        "codes": {c: v for c, v in sorted(holes.items())},
    }
    if holes:
        shown = ", ".join("%s(%s)" % (c, ",".join(v))
                          for c, v in sorted(holes.items())[:10])
        print("경고: 뼈대 기간 «안»의 꼬리 봉 %d개(%d종목)를 버렸다 — 그 자리는 "
              "뼈대의 구멍이고 다른 벤더 값으로 메우지 않는다. 앞 %d종목: %s"
              % (out["tail_dropped"]["n_bars"], len(holes),
                 min(10, len(holes)), shown), file=sys.stderr)
    return out


# ── 분할 보정 ──────────────────────────────────────────────────────────────
# 왜 생겼나(2026-09-11 사용자 결정): 예전에는 「창 안에 분할이 하나라도 있으면
# 멈춘다」였고, 적힌 해결책은 「Sharadar 를 다시 받아 뼈대를 새로 만든다」였다.
# Sharadar 결제가 2026-09 로 끝나 10월부터 그 길이 없다. 게다가 분할 검사 창은
# 「뼈대 기준일부터 오늘까지」라 날마다 넓어진다 — 그대로 두면 10월 첫 분할이
# 나는 날 갱신이 영구히 멈추고 후보가 9월 자료에 언다.
# 「분할 난 종목만 빼고 잇는다」는 사용자가 버린 길이다 — 우량주가 액면분할하면
# 오히려 놓치면 안 되는 그 종목을 못 보게 된다.
#
# 무엇을 곱하나: 야후가 주는 배수(ratio)는 「주식 수 배수」다. 2대1 액면분할이면
# 2.0, 1대10 주식병합이면 0.1. 분할 «전» 봉을 분할 «후» 기준으로 옮기려면
#     가격 / ratio     ·     거래량 * ratio
# 를 한다. 둘 다 해야 거래대금(가격 곱하기 거래량)이 보존된다. 가격만 줄이면 그
# 종목의 과거 거래대금이 배수만큼 쪼그라들고, 유동성 관문(50일 평균 거래대금)이
# 멀쩡한 종목을 잘못 떨어뜨린다. 한국 rebase_history 는 거래량을 안 건드리므로
# 그대로 쓸 수 없다(한국 코드는 고치지 않는다 — 우리 쪽에서 맞게 한다).


def _factor_per_bar(dates: list[str], code_splits: list[dict]) -> list[float]:
    """봉마다 나눠야 할 분할 배수를 낸다 — 그 봉 «뒤»에 난 분할만 곱한다.

    보정 대상은 분할일 «이전»의 봉이다. 분할일 당일 봉은 이미 분할 후 가격이라
    건드리면 안 된다. 뼈대는 전부 기준일 이하이므로 분할일이 기준일보다 뒤면
    모든 봉이 대상이 되고, 그때 이 함수는 모든 봉에 같은 배수(곱한 값)를 준다.
    """
    out = []
    for d in dates:
        f = 1.0
        for sp in code_splits:
            if sp["date"] > d:
                f *= float(sp["ratio"])
        out.append(f)
    return out


def _rebase_series(s: dict, factors: list[float]) -> dict:
    """가격은 배수로 나누고 거래량은 배수로 곱한 «새» 계열을 낸다.

    원본 dict 는 건드리지 않는다 — 뼈대(.cache/us/base.json)는 Sharadar 정본이고
    얼려 있어야 한다. 제자리에서 고치면 다시 돌릴 때 보정이 두 번 먹는다.
    반올림하지 않는다 — 1달러 밑 종목이 흔해서 소수 둘째 자리로 뭉개면 값이 죽는다.
    """
    out = dict(s)
    for key in ("opens", "highs", "lows", "closes"):
        vals = s.get(key) or []
        out[key] = [(v / f) if (v and f) else v for v, f in zip(vals, factors)]
    vols = s.get("volumes") or []
    out["volumes"] = [(v * f) if (v and f) else v for v, f in zip(vols, factors)]
    return out


def adjust_base_for_splits(base: dict, splits: list[dict],
                           tail: dict) -> tuple[dict, dict]:
    """분할 비율로 뼈대의 과거 가격을 맞춘 «새» 자료와 보고를 낸다.

    base  : 뼈대 자료(us_matrix.load_base() 가 낸 것). 건드리지 않는다.
    splits: check_splits(...)["splits"] 그대로. [{"code","date","ratio"}, ...]
    tail  : fetch_tail(...)["series"] 그대로(코드 → 시계열). 싸개가 아니다.
            왜 필요한가 — 「뼈대가 이 분할을 이미 반영했나」를 «재려면» 뼈대
            마지막 봉과 같은 날짜의 야후 봉이 있어야 한다. 벤더 규약을 짐작하지
            않고 잰다.

    반환: (보정된 새 자료, 보고)
      보고 = {"adjusted": [...], "unchanged": [...], "blocked": [...]}
      멈춘 종목은 «새 자료에서 빠진다». 조용히 옛 값으로 남기지 않는다 —
      남기면 이어 붙이는 쪽이 그 종목에 가짜 계단을 그대로 붙인다.

    「뼈대가 이미 반영했나」를 가르는 법(짐작 금지, 실측):
        관측비 = 뼈대 마지막 종가 / 같은 날 꼬리 종가
        관측비가 분할비율에 가까우면  -> 뼈대가 분할 전이다. 보정한다
        관측비가 1 에 가까우면        -> 이미 반영됐다. 손대지 않는다
                                        ★ 단 아래 「위험한 자리」를 먼저 본다
        둘 다 아니면                  -> 모르는 상황이다. 그 종목은 멈춘다
    「가깝다」의 자는 REBASE_MIN_DEVIATION 이고 분할비율이 성립하는 범위는
    REBASE_RATIO_BOUNDS 다. 둘 다 한국 쪽에서 가져다 쓴다(값을 다시 안 적는다).

    ★ 「같은 날」이지 「꼬리의 첫 봉」이 아니다. 뼈대 마지막 날이 꼬리에 없으면
      서로 다른 날을 견주게 되므로 그때는 «잴 수가 없다»로 보고 멈춘다.

    ★ 제일 위험한 자리 — 「관측비가 1」이 늘 「이미 반영됐다」는 아니다.
      분할일이 뼈대 마지막 봉보다 «뒤»인데 관측비가 1 이면, 그것은 «야후도 아직
      환산을 안 했다»는 뜻일 뿐이다. 두 자료가 «똑같이 분할 전»이어도 관측비는
      1 이 나온다. 오늘은 붙일 분할 후 봉이 없어 무해하지만, 야후가 분할 후 봉을
      내놓는 날 배수만큼 가짜 계단이 조용히 붙는다. 그래서 그 갈래는 멈춘다.
      실측(2026-09-11) CYCN 이 바로 이 모양이었다 — 기준일 당일 1대7 병합인데
      뼈대 마지막 봉이 하루 앞서고 야후에 분할 후 봉이 아직 없다. 관측비 1.018 로
      나와 「이미 반영됐다」로 «샜었다». 이 갈래가 그것을 잡는다.

    보정한 뒤 «이음매가 매끈해졌는지» 다시 잰다 — 뼈대 마지막 종가와 같은 날
    꼬리 종가의 비가 1에 가까워야 한다. 이 확인을 통과 못 하면 그 종목은 멈춘다.
    이 확인은 «분류 논리»에 대해서는 항등식이지만 «구현»에 대해서는 아니다 —
    나누기를 곱하기로 쓰거나 엉뚱한 봉에 걸면 여기서 걸린다(무력화 시험으로 확인).
    """
    lo, hi = REBASE_RATIO_BOUNDS
    by_code: dict[str, list[dict]] = {}
    for sp in splits:
        by_code.setdefault(sp["code"], []).append(sp)

    out = {k: v for k, v in base.items() if k != "series"}
    ser = dict(base.get("series", {}))
    report: dict = {"adjusted": [], "unchanged": [], "blocked": []}

    for code, code_splits in sorted(by_code.items()):
        ratio = 1.0
        for sp in code_splits:
            ratio *= float(sp["ratio"])
        shown = ",".join("%s(%g)" % (sp["date"], sp["ratio"]) for sp in code_splits)
        row = {"code": code, "ratio": ratio, "splits": shown}

        s = base.get("series", {}).get(code)
        if not s or not s.get("dates"):
            row["reason"] = "뼈대에 이 종목이 없다(또는 봉이 없다)"
            report["blocked"].append(row)
            ser.pop(code, None)
            continue

        if not (lo <= ratio <= hi) or abs(ratio - 1.0) <= REBASE_MIN_DEVIATION:
            row["reason"] = ("분할 배수가 기업행위로 볼 범위 밖이거나 1에 너무 "
                             "가깝다(REBASE_RATIO_BOUNDS=%s)" % (REBASE_RATIO_BOUNDS,))
            report["blocked"].append(row)
            ser.pop(code, None)
            continue

        last_date = s["dates"][-1]
        row["seam_date"] = last_date
        t = tail.get(code) or {}
        t_dates = t.get("dates") or []
        if last_date not in t_dates:
            row["reason"] = ("꼬리에 뼈대 마지막 날(%s) 봉이 없어 「이미 "
                             "반영됐나」를 잴 수가 없다" % last_date)
            report["blocked"].append(row)
            ser.pop(code, None)
            continue

        base_close = s["closes"][-1]
        tail_close = t["closes"][t_dates.index(last_date)]
        if not base_close or not tail_close:
            row["reason"] = "이음매 종가가 비어 있어 잴 수가 없다"
            report["blocked"].append(row)
            ser.pop(code, None)
            continue

        after_last = [sp for sp in code_splits if sp["date"] > last_date]
        observed = base_close / tail_close
        row["observed"] = observed
        if abs(observed / ratio - 1.0) <= REBASE_MIN_DEVIATION:
            row["verdict"] = "뼈대가 분할 전이다"
        elif abs(observed - 1.0) <= REBASE_MIN_DEVIATION and not after_last:
            # 분할일이 전부 뼈대 마지막 봉 «이하»다. 그 봉은 분할일 당일이거나
            # 그 뒤라 어느 자료에서나 이미 분할 후 시세이고, 이어 붙일 봉들도
            # 전부 분할 후다 — 이음매는 이대로 매끈하다.
            row["verdict"] = "뼈대가 이미 반영했다"
            report["unchanged"].append(row)
            continue
        elif abs(observed - 1.0) <= REBASE_MIN_DEVIATION:
            # ★ 제일 위험한 자리. 분할일이 뼈대 마지막 봉보다 «뒤»인데 두 자료가
            #   그 봉에서 같다 = 야후도 아직 환산을 «안» 했다는 뜻이다. 그러면
            #   「뼈대가 분할 전인가」를 이 자로는 가를 수가 없다. 오늘은 붙일
            #   봉이 없어 무해하지만, 야후가 분할 후 봉을 내놓는 날 배수만큼
            #   가짜 계단이 조용히 붙는다. 그래서 지금 멈춘다.
            #   실측(2026-09-11): CYCN 이 이 갈래다 — 기준일 당일 1대7 병합인데
            #   뼈대 마지막 봉이 하루 앞서고 야후에 분할 후 봉이 아직 없다.
            row["reason"] = ("분할일(%s)이 뼈대 마지막 봉(%s)보다 뒤인데 관측비가 "
                             "%.6g(=1)다 — 야후도 아직 환산을 안 했다는 뜻이라 "
                             "어느 쪽인지 가를 수가 없다. 멈춘다"
                             % (after_last[0]["date"], last_date, observed))
            report["blocked"].append(row)
            ser.pop(code, None)
            continue
        else:
            row["reason"] = ("관측비 %.6g 가 분할비율 %g 도 1 도 아니다 — "
                             "모르는 상황이라 멈춘다" % (observed, ratio))
            report["blocked"].append(row)
            ser.pop(code, None)
            continue

        factors = _factor_per_bar(s["dates"], code_splits)
        new_s = _rebase_series(s, factors)

        # 고치고 끝내지 않는다 — 고쳐졌는지 다시 잰다.
        check = new_s["closes"][-1] / tail_close
        if abs(check - 1.0) > REBASE_MIN_DEVIATION:
            row["reason"] = ("보정 뒤에도 이음매가 안 맞는다(보정 후 비 %.6g, "
                             "1 이어야 한다) — 멈춘다" % check)
            row["check"] = check
            report["blocked"].append(row)
            ser.pop(code, None)
            continue

        row["check"] = check
        row["n_bars"] = sum(1 for f in factors if f != 1.0)
        row["close_before"] = base_close
        row["close_after"] = new_s["closes"][-1]
        ser[code] = new_s
        report["adjusted"].append(row)

    out["series"] = ser
    return out, report


def format_split_report(report: dict) -> str:
    """보고를 사람이 읽는 줄로 바꾼다.

    조용히 고치면 다음 사람이 이 코드를 못 믿는다 — 무엇을 보정했고 무엇이
    실패했는지 반드시 찍는다.
    """
    lines = ["분할 보정: 보정 %d · 그대로 %d · 멈춤 %d" % (
        len(report["adjusted"]), len(report["unchanged"]),
        len(report["blocked"]))]
    for r in report["adjusted"]:
        lines.append("  [보정] %s 배수 %g (%s) 봉 %d개 · 종가 %g -> %g · "
                     "이음매 비 %.6g" % (
                         r["code"], r["ratio"], r["splits"], r["n_bars"],
                         r["close_before"], r["close_after"], r["check"]))
    for r in report["unchanged"]:
        lines.append("  [그대로] %s 배수 %g (%s) 관측비 %.6g — %s" % (
            r["code"], r["ratio"], r["splits"], r["observed"], r["verdict"]))
    for r in report["blocked"]:
        lines.append("  [멈춤] %s 배수 %g (%s) — %s" % (
            r["code"], r["ratio"], r["splits"], r["reason"]))
    if report["blocked"]:
        lines.append("  멈춘 종목은 합본에서 «빠졌다». 사용자에게 알려야 한다.")
    return "\n".join(lines)

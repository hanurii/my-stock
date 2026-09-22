"""캐시 종가 관문 — 배선 «밖»의 자로 재서, 어긋나면 파이프라인을 세운다.

왜 있나:
  2026-09-14 애프터마켓 개장으로 종가가 둘이 됐다(정규장 / 통합). 우리는 정규장
  종가만 쓴다. 그런데 어느 출처가 어느 쪽을 주는지를 26-09-16 에 «거꾸로» 적었고,
  그 믿음으로 넣은 고침이 09-14~09-21 캐시 종가의 60~66% 를 어긋나게 만들었다.

  그때 고침이 틀린 줄 몰랐던 까닭은 하나다 — **고른 두 출처끼리만 맞대 봤다.**
  pdata 와 FDR 이 다르다는 사실은 「어느 쪽이 맞나」를 «못» 말한다. 둘 다 틀렸을
  수도 있다. 그래서 이 관문은 채우기 사슬(pdata·FDR) «밖»의 자를 쓴다.

무엇으로 가리나:
  거래소가 «스스로 내는 수» — 기준가. KIS 일봉은 기준가를 자기 응답에서 밝힌다.
      기준가(D) = 종가(D) − prdy_vrss(D)
  기준가는 정의상 «전일 정규장 종가»다. 그러므로
      KIS 종가(D-1) == 기준가(D)
  가 성립하면 KIS 종가는 정규장 종가다. 이 연쇄가 양성 대조다 — 자가 «먼저»
  동작함을 보인 뒤에 결과를 읽는다. 연쇄가 깨지면 판정하지 않고 「못 가림」이다.

🚨 문턱은 결과를 보기 «전»에 아래 상수에 박았다. 보고 나서 고치지 않는다.
  · 어긋남 = 상대차 0.2% 초과 (반올림·수정주가 잔차를 흡수하는 폭)
  · 기업행위(상대차 5% 초과)는 «따로» 센다 — 머릿수에 섞지 않는다(액면분할 등)
  · 어긋난 종목-일이 5% 를 넘으면 실패(exit 1)

실행: python -X utf8 scripts/verify_close_gate.py [--sample 40] [--days 5]
  exit 0 = 통과 · 1 = 어긋남 문턱 초과 · 2 = 못 가림(자 자체가 안 섰다)
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# .env 로드 — KIS 키가 여기 있다(pivot_alert.py 와 같은 방식).
# 안 하면 토큰이 None 으로 나오고 관문이 «못 가림»으로 조용히 비켜선다.
_ENV_PATH = ROOT / ".env"
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k, _v)

# ── 사전 등록 문턱 — 결과를 보고 고치지 않는다 ────────────────
DIVERGE_PCT = 0.2          # 이 상대차를 넘으면 «어긋남»
CORP_ACTION_PCT = 5.0      # 이 상대차를 넘으면 기업행위로 보고 따로 센다
FAIL_ABOVE_RATE = 5.0      # 어긋난 종목-일이 이 비율을 넘으면 실패

SERIES_DIR = ROOT / ".cache" / "ohlcv" / "series"


# ── 순수 로직 (시험 대상) ────────────────────────────────────

def classify_pair(cache_close: float, ref_close: float) -> str:
    """캐시 종가와 자의 종가 한 쌍을 «맞음 / 어긋남 / 기업행위»로 가른다."""
    if not ref_close:
        return "unknown"
    pct = abs(cache_close - ref_close) / ref_close * 100
    if pct > CORP_ACTION_PCT:
        return "corp_action"
    if pct > DIVERGE_PCT:
        return "diverge"
    return "match"


def tally(pairs: list[tuple[float, float]]) -> dict:
    """(캐시종가, 자종가) 목록 → 센 결과. 기업행위는 분모에서 «뺀다».

    뺀 까닭: 액면분할은 종가가 틀린 게 아니라 «기준이 다른» 것이다. 머릿수에
    섞으면 관문이 기업행위 많은 날 저절로 시끄러워진다(유형: 다른 것을 한 자로).
    """
    n_corp = n_div = n_match = 0
    for c, r in pairs:
        k = classify_pair(c, r)
        if k == "corp_action":
            n_corp += 1
        elif k == "diverge":
            n_div += 1
        elif k == "match":
            n_match += 1
    base = n_div + n_match
    return {"n": base, "diverge": n_div, "match": n_match, "corp_action": n_corp,
            "rate": (n_div / base * 100) if base else 0.0}


def chain_ok(closes: list[float], bases: list[float]) -> dict:
    """KIS 종가(D-1) 와 기준가(D) 가 맞는가 — 자가 «섰는지» 보는 양성 대조."""
    n = bad = 0
    for i in range(1, len(closes)):
        n += 1
        if abs(bases[i] - closes[i - 1]) > 0.5:
            bad += 1
    return {"n": n, "bad": bad}


def verdict(t: dict, chain: dict) -> tuple[str, int]:
    """판정과 종료코드. 자가 안 섰으면 «판정하지 않는다»."""
    if chain["n"] == 0 or chain["bad"] > 0:
        return "못 가림 — 기준가 연쇄가 깨졌다. 자 자체를 먼저 봐야 한다", 2
    if t["n"] == 0:
        return "못 가림 — 비교할 쌍이 없다. 표본을 넓혀라", 2
    if t["rate"] > FAIL_ABOVE_RATE:
        return f"실패 — 캐시 종가가 정규장 종가와 어긋난다 ({t['rate']:.1f}%)", 1
    return f"통과 — 캐시 종가가 정규장 종가다 (어긋남 {t['rate']:.1f}%)", 0


def pick_sample(codes: list[str], k: int, day: str) -> list[str]:
    """표본을 날마다 «다르게» 고르되 그날 안에선 되풀이 가능하게.

    한 표본에 고정하면 그 표본 밖은 영원히 안 쓸린다. 날짜를 씨앗으로 두면
    날이 갈수록 전 종목을 훑으면서도 같은 날 재실행은 같은 답을 준다.
    """
    rnd = random.Random(day)
    pool = sorted(codes)
    return rnd.sample(pool, min(k, len(pool)))


# ── 자료 받기 ────────────────────────────────────────────────

def _cache_closes(code: str) -> dict[str, float]:
    p = SERIES_DIR / f"{code}.json"
    try:
        s = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {d.replace("-", ""): c for d, c in zip(s.get("dates") or [],
                                                  s.get("closes") or [])}


def main() -> int:
    ap = argparse.ArgumentParser(description="캐시 종가 관문 — 기준가로 잰다")
    ap.add_argument("--sample", type=int, default=40, help="표본 종목 수")
    ap.add_argument("--days", type=int, default=5, help="최근 몇 영업일을 보나")
    a = ap.parse_args()

    from check_close_source import kis_daily
    from canslim_lib import kis_api

    token = kis_api.get_access_token()
    if not token:
        print("못 가림 — KIS 토큰 발급 실패. .env 확인"); return 2

    codes = [p.stem for p in SERIES_DIR.glob("*.json")]
    if not codes:
        print("못 가림 — 시계열 캐시가 비었다"); return 2

    now = datetime.now()
    today = now.strftime("%Y%m%d")
    d1 = (now - timedelta(days=a.days + 12)).strftime("%Y%m%d")
    sample = pick_sample(codes, a.sample, today)

    print(f"캐시 종가 관문 · {now:%Y-%m-%d %H:%M} · 표본 {len(sample)}종목 "
          f"· 최근 {a.days}영업일")
    print(f"  자: KIS 일봉(J) + 거래소 기준가 연쇄 — 채우기 사슬(pdata·FDR) «밖»")

    def one(code: str):
        k = kis_daily(code, d1, today, token)
        if not k:
            return None
        kd = {r["stck_bsop_date"]: (float(r["stck_clpr"]), float(r["prdy_vrss"]))
              for r in k}
        return code, kd, _cache_closes(code)

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        res = [x for x in ex.map(one, sample) if x]
    if not res:
        print("못 가림 — KIS 자료를 못 받았다. 망 상태 확인"); return 2

    # 양성 대조: 자가 서는가
    c_n = c_bad = 0
    for _, kd, _c in res:
        ds = sorted(kd)
        c = chain_ok([kd[x][0] for x in ds], [kd[x][0] - kd[x][1] for x in ds])
        c_n += c["n"]; c_bad += c["bad"]
    chain = {"n": c_n, "bad": c_bad}

    # 본 검사: 최근 a.days 영업일만
    all_days = sorted({d for _, kd, _c in res for d in kd})[-a.days:]
    pairs: list[tuple[float, float]] = []
    per_day: dict[str, list] = {d: [] for d in all_days}
    for _code, kd, cc in res:
        for d in all_days:
            if d in kd and d in cc:
                pairs.append((cc[d], kd[d][0]))
                per_day[d].append((cc[d], kd[d][0]))

    print()
    print(" 날짜        비교  어긋남   비율   | 기업행위")
    for d in all_days:
        t = tally(per_day[d])
        print(f" {d} {t['n']:7d} {t['diverge']:7d} {t['rate']:7.1f}%  | {t['corp_action']:6d}")

    t = tally(pairs)
    print()
    print(f"기준가 연쇄(양성 대조): {chain['n']}쌍 중 어긋남 {chain['bad']}")
    print(f"합계: {t['n']}쌍 중 어긋남 {t['diverge']} ({t['rate']:.1f}%) "
          f"· 기업행위로 뺀 것 {t['corp_action']}")
    print(f"문턱(사전 등록): 어긋남 {FAIL_ABOVE_RATE:.0f}% 초과면 실패")
    msg, code = verdict(t, chain)
    print()
    print(f"  ▶ {msg}")
    return code


if __name__ == "__main__":
    sys.exit(main())

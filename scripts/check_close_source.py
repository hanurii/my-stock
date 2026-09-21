"""종가 출처 대조 — FDR 과 KIS(정규장) 중 어느 쪽이 정규장 종가인가.

왜 있나:
  2026-09-14 애프터마켓 개장으로 「종가」가 둘이 됐다.
    · 정규장 종가 — 15:30 가격. 공식 종가이고 다음날 상·하한가의 기준이다.
    · 통합 종가   — 애프터마켓까지 끝난 20:00 가격. 공식 종가가 «아니다».
  FDR 이 09-14 부터 통합 종가를 주기 시작했고 우리 캐시가 그것을 담았다.
  SEPA 는 종가로 피벗을 계산하므로 피벗이 그만큼 어긋난다.

무엇으로 가리나:
  KIS 일봉은 «기준가»를 스스로 밝힌다 — 기준가(D) = 종가(D) − prdy_vrss(D).
  기준가는 정의상 «전일 정규장 종가»다. 그러므로 KIS 종가(D-1) == 기준가(D) 가
  성립하면 KIS 종가는 정규장 종가다. 26-09-21 실측 513쌍 중 어긋남 0건.

🚨 사전 등록된 예측 (26-09-21 22:50 에 박음 — 결과를 보기 «전»이다):
  그날 종가는 «당일 저녁»엔 두 출처가 같다가 «다음날»에 갈린다(FDR 이 밤새 정산).
  따라서 2026-09-21 의 어긋남 비율은
      09-21 저녁  : 0%       (실측됨)
      09-22 아침  : 50% 이상  ← 이게 맞으면 예측 적중
  20% 미만이면 예측이 «빗나간» 것이고 위 모형을 다시 봐야 한다.
  그 사이(20~50%)는 «못 가림»이다. 「대체로 맞다」로 읽지 않는다.

  이 문턱은 아래 상수에 박혀 있다. 결과를 보고 «고치지 않는다».

실행: python -X utf8 scripts/check_close_source.py [--days 8] [--codes 003010,043260]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import urllib.parse as _up
import urllib.request as _ur
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# ── 사전 등록 문턱 — 결과를 보고 고치지 않는다 ────────────────
PREDICT_DATE = "20260921"
HIT_AT_OR_ABOVE = 50.0     # 이상이면 예측 적중
MISS_BELOW = 20.0          # 미만이면 예측 빗나감
PREDICTED_ON = "2026-09-21 22:50"

_EP = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"


# ── 순수 로직 (시험 대상) ────────────────────────────────────

def divergence_rate(pairs: list[tuple[float, float]], tol: float = 0.5) -> dict:
    """(FDR종가, KIS종가) 목록 → 어긋난 비율과 크기.

    tol 은 원 단위. 부동소수 반올림만 흡수하고 1원 차이는 «어긋남»으로 센다.
    """
    if not pairs:
        return {"n": 0, "bad": 0, "rate": 0.0, "median_pct": 0.0}
    bad = [(f, k) for f, k in pairs if abs(f - k) > tol]
    pcts = sorted(abs(f - k) / k * 100 for f, k in bad if k)
    med = pcts[len(pcts) // 2] if pcts else 0.0
    return {"n": len(pairs), "bad": len(bad), "rate": len(bad) / len(pairs) * 100,
            "median_pct": med}


def verdict(rate: float) -> str:
    """사전 등록한 문턱으로만 판정한다. 눈대중으로 「대체로 맞다」를 쓰지 않는다."""
    if rate >= HIT_AT_OR_ABOVE:
        return "예측 적중"
    if rate < MISS_BELOW:
        return "예측 빗나감"
    return "못 가림"


def can_judge_yet(today: str, predict_date: str) -> bool:
    """예측 대상일 «당일»에는 판정하지 않는다.

    예측 자체가 「그날 저녁엔 같다가 다음날 갈린다」이므로, 당일 저녁에 0% 를 보고
    「빗나갔다」로 읽으면 예측을 스스로 뒤집는 셈이 된다. 하루가 지나야 답이 나온다.
    """
    return today > predict_date


def chain_ok(closes: list[float], bases: list[float]) -> dict:
    """KIS 종가(D-1) 와 기준가(D) 가 맞는지. 어긋나면 KIS 종가도 정규장 종가가 아니다."""
    n = bad = 0
    for i in range(1, len(closes)):
        n += 1
        if abs(bases[i] - closes[i - 1]) > 0.5:
            bad += 1
    return {"n": n, "bad": bad}


# ── 자료 받기 ────────────────────────────────────────────────

def kis_daily(code: str, d1: str, d2: str, token: str) -> list[dict]:
    h = {"content-type": "application/json", "authorization": f"Bearer {token}",
         "appkey": os.environ.get("KIS_APP_KEY", ""),
         "appsecret": os.environ.get("KIS_APP_SECRET", ""),
         "tr_id": "FHKST03010100", "custtype": "P"}
    qs = _up.urlencode({"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code,
                        "FID_INPUT_DATE_1": d1, "FID_INPUT_DATE_2": d2,
                        "FID_PERIOD_DIV_CODE": "D", "FID_ORG_ADJ_PRC": "0"})
    from canslim_lib import kis_api
    kis_api._throttle()
    try:
        req = _ur.Request(kis_api._base_url() + _EP + "?" + qs, headers=h)
        with _ur.urlopen(req, timeout=12) as r:
            return sorted(json.loads(r.read().decode("utf-8")).get("output2") or [],
                          key=lambda x: x.get("stck_bsop_date") or "")
    except Exception:
        return []


def main() -> None:
    ap = argparse.ArgumentParser(description="종가 출처 대조 — FDR vs KIS(정규장)")
    ap.add_argument("--days", type=int, default=8, help="거슬러 볼 달력일 수")
    ap.add_argument("--codes", default="", help="쉼표 구분. 없으면 현재 감시 목록")
    a = ap.parse_args()

    import pivot_alert as pa
    from canslim_lib import kis_api
    import FinanceDataReader as fdr

    token = kis_api.get_access_token()
    if not token:
        print("KIS 토큰 발급 실패 — .env 확인"); return
    now = datetime.now(pa.KST)
    d1 = (now - timedelta(days=a.days + 6)).strftime("%Y%m%d")
    d2 = now.strftime("%Y%m%d")

    codes = ([c.strip() for c in a.codes.split(",") if c.strip()]
             or [r["code"] for r in pa.load_watch_universe()])
    print(f"종가 출처 대조 · 기준 {now:%Y-%m-%d %H:%M} · 표본 {len(codes)}종목")
    print("  FDR = FinanceDataReader · KIS = 한국투자 일봉(J, 정규장)")

    def one(code):
        k = kis_daily(code, d1, d2, token)
        if not k:
            return None
        try:
            f = fdr.DataReader(code, f"{d1[:4]}-{d1[4:6]}-{d1[6:]}", f"{d2[:4]}-{d2[4:6]}-{d2[6:]}")
            fm = {d.strftime("%Y%m%d"): float(x) for d, x in zip(f.index, f["Close"])}
        except Exception:
            return None
        return {r["stck_bsop_date"]: (float(r["stck_clpr"]), float(r["prdy_vrss"])) for r in k}, fm

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        res = [x for x in ex.map(one, codes) if x]
    if not res:
        print("자료를 못 받았다 — 망 상태 확인"); return

    dates = sorted({d for km, _ in res for d in km})
    print()
    print(" 날짜       비교  어긋남   비율     중앙 차이")
    rates = {}
    for d in dates:
        pairs = [(fm[d], km[d][0]) for km, fm in res if d in km and d in fm]
        r = divergence_rate(pairs)
        rates[d] = r["rate"]
        mark = "  ← 예측 대상" if d == PREDICT_DATE else ""
        print(f" {d} {r['n']:6d} {r['bad']:7d} {r['rate']:7.1f}%  {r['median_pct']:8.2f}%{mark}")

    # KIS 가 자기 기준가와 맞는가 — 이게 깨지면 위 판정 전체가 무의미하다
    tot = bad = 0
    for km, _ in res:
        ds = sorted(km)
        c = chain_ok([km[x][0] for x in ds], [km[x][0] - km[x][1] for x in ds])
        tot += c["n"]; bad += c["bad"]
    print()
    print(f"KIS 종가 ↔ 거래소 기준가 연쇄: {tot}쌍 중 어긋남 {bad} "
          f"({'정상 — KIS 는 정규장 종가다' if bad == 0 else '★비정상 — 이 검사 자체를 다시 봐야 한다'})")

    print()
    print(f"사전 등록된 예측 ({PREDICTED_ON} 에 박음, 결과 보기 전):")
    print(f"  {PREDICT_DATE} 의 어긋남 비율이 {HIT_AT_OR_ABOVE:.0f}% 이상 → 예측 적중 "
          f"(FDR 이 통합 종가로 정산된다)")
    print(f"  {MISS_BELOW:.0f}% 미만 → 예측 빗나감 (모형을 다시 봐야 한다)")
    print(f"  그 사이 → 못 가림")
    today = now.strftime("%Y%m%d")
    print()
    if PREDICT_DATE not in rates:
        print(f"  ▶ {PREDICT_DATE} 자료가 표본에 없다 — --days 를 늘려 다시 보라")
    elif not can_judge_yet(today, PREDICT_DATE):
        print(f"  ▶ {PREDICT_DATE} 실측 {rates[PREDICT_DATE]:.1f}%")
        print("     아직 판정할 때가 «아니다». 예측 자체가 「그날 저녁엔 같다가 다음날")
        print("     갈린다」이므로 당일 0% 는 예측과 «어긋나지 않는다».")
        print("     내일(거래일) 아침에 다시 돌려라. 그때 나오는 수가 답이다.")
    else:
        r = rates[PREDICT_DATE]
        v = verdict(r)
        print(f"  ▶ {PREDICT_DATE} 실측 {r:.1f}%  →  판정: {v}")
        if v == "예측 적중":
            print("     FDR 은 통합 종가로 정산된다. 캐시 종가 출처를 KIS(J) 로 바꾸는 것이 맞다.")
        elif v == "예측 빗나감":
            print("     모형이 틀렸다. 고치기 «전»에 다시 조사해야 한다 — 서두르지 말 것.")
        else:
            print("     못 가렸다. 「대체로 맞다」로 읽지 말 것. 표본을 넓혀 다시 보라.")


if __name__ == "__main__":
    main()

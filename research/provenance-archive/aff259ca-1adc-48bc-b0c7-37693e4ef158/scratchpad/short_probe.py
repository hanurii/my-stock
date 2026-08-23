# -*- coding: utf-8 -*-
"""한국 공매도·대차 데이터 수집 타당성 프로브 — 검증된 fetch 함수 모음.

프로브 일시: 2026-08-18 04:30~05:00 KST (직전 완결 거래일 = 2026-08-14 금;
8/15 광복절(토), 8/17 대체공휴일(월) → 8/18 화 새벽 실측)

결론 요약 (자세한 근거는 short_feasibility.md):
  [A] 공매도 일별 거래량·거래대금·비중 (종목별)
      → KIS OpenAPI daily-short-sale: ★즉시 사용 가능★ (기존 KIS_APP_KEY 재사용)
        실측: 8/18 새벽에 8/14(직전 거래일)분까지 서빙 = 야간 파이프라인에 충분
  [B] 공매도 잔고 일별 (종목별 잔고수량·잔고금액·비중)
      → KRX data.krx.co.kr MDCSTAT30501/30502: 2026-08 현재 '로그인 필수'(무료 회원).
        비로그인 3경로(JSON·세션워밍·CSV-OTP) 전부 400 LOGOUT 실측.
        KRX_ID/KRX_PW 환경변수 + 아래 krx_login() 으로 사용 (pykrx 1.2.8 동일 흐름).
  [C] 대차잔고 (선행 프록시)
      - 종목별 일별: 금융위_주식대차정보 API(data.go.kr 15059612)
        getStItemLendAndBorrStatu — 체결·상환·잔고 주식수. 갱신 T+1 영업일 13시.
        ※ 보유 DATA_GO_KR_KEY 는 유효하나 이 API 미신청 상태(에러 30) →
          data.go.kr 에서 '활용신청' 1회 클릭(자동승인) 후 즉시 동작.
      - 시장 전체 집계: KOFIA FreeSIS getMetaDataList.do — 무인증 동작 실측.

사용 예:
    python short_probe.py          # 동작 가능한 소스 실측 + 샘플 JSON 저장
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
REPO = Path("C:/Users/hanul/playground/my-stock")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 코드→ISIN (KRX finder_srtisu 로 실측 확인)
ISIN = {"005930": "KR7005930003", "007340": "KR7007340003", "219130": "KR7219130002"}


def load_env(path: Path = REPO / ".env") -> None:
    """레포 .env 를 os.environ 에 주입(기존 값 우선)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


# =========================================================================
# [A] KIS OpenAPI — 국내주식 공매도 일별추이 (실측 완료, 즉시 사용 가능)
#     GET /uapi/domestic-stock/v1/quotations/daily-short-sale
#     tr_id=FHPST04830000, FID_COND_MRKT_DIV_CODE=J (KOSPI·KOSDAQ 공통)
#     1콜당 최근 100거래일 상한 → 슬라이딩 윈도우 페이지네이션
#     응답 output2 필드(실측):
#       stck_bsop_date 일자 / stck_clpr 종가 / acml_vol 거래량
#       ssts_cntg_qty 공매도 거래량 / ssts_vol_rlim 공매도 거래량비중(%)
#       ssts_tr_pbmn 공매도 거래대금 / ssts_tr_pbmn_rlim 대금비중(%)
#       acml_ssts_cntg_qty(_rlim) 기간누적 공매도량(비중) — 잔고 아님 주의
# =========================================================================
def _kis_token() -> str | None:
    sys.path.insert(0, str(REPO / "scripts"))
    from canslim_lib import kis_api  # 토큰 캐시(.cache/kis_token.json) 재사용
    return kis_api.get_access_token()


def fetch_kis_short_sale(code: str, start: str, end: str,
                         token: str | None = None) -> list[dict]:
    """종목별 일별 공매도 거래 (start~end, YYYYMMDD). 100행 상한 자동 페이지네이션."""
    if token is None:
        token = _kis_token()
    if not token:
        raise RuntimeError("KIS 토큰 없음 (KIS_APP_KEY/SECRET 확인)")
    out: dict[str, dict] = {}
    cursor_end = end
    while True:
        qs = urllib.parse.urlencode({
            "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code,
            "FID_INPUT_DATE_1": start, "FID_INPUT_DATE_2": cursor_end})
        req = urllib.request.Request(
            f"https://openapi.koreainvestment.com:9443"
            f"/uapi/domestic-stock/v1/quotations/daily-short-sale?{qs}",
            headers={"content-type": "application/json",
                     "authorization": f"Bearer {token}",
                     "appkey": os.environ["KIS_APP_KEY"],
                     "appsecret": os.environ["KIS_APP_SECRET"],
                     "tr_id": "FHPST04830000", "custtype": "P"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            js = json.loads(resp.read().decode("utf-8"))
        if js.get("rt_cd") != "0":
            raise RuntimeError(f"KIS 오류 {js.get('msg_cd')}: {js.get('msg1')}")
        rows = [r for r in (js.get("output2") or []) if r.get("stck_bsop_date")]
        for r in rows:
            out[r["stck_bsop_date"]] = r
        if len(rows) < 100:          # 창 안이 100행 미만 = 끝까지 받음
            break
        oldest = min(r["stck_bsop_date"] for r in rows)
        if oldest <= start:
            break
        # 다음 창: 가장 오래된 날짜 전날까지
        import datetime as _dt
        cursor_end = (_dt.datetime.strptime(oldest, "%Y%m%d")
                      - _dt.timedelta(days=1)).strftime("%Y%m%d")
        time.sleep(0.15)             # KIS 레이트리밋 (초당 ~8회 안전)
    return [out[d] for d in sorted(out)]


# =========================================================================
# [B] KRX 정보데이터시스템 — 공매도 통계 (2026-08 현재 무료회원 로그인 필수)
#     비로그인 시 모든 경로가 HTTP 400 본문 "LOGOUT" (실측 3경로 확인).
#     short.krx.co.kr(공매도종합포털)도 data.krx.co.kr 로그인 페이지로 리다이렉트
#     = 동일 백엔드. bld 코드·파라미터는 pykrx 1.2.8 소스에서 확인, 형식은 유효
#     (finder_srtisu 는 비로그인 동작 → ISIN 해석에 사용 가능).
#       MDCSTAT30001 종합정보     : strtDd,endDd,isuCd  (거래+잔고 결합)
#       MDCSTAT30101 거래 전종목  : trdDd,mktId(STK/KSQ),inqCond=STMFRTSCIFDRFS
#       MDCSTAT30102 거래 개별추이: strtDd,endDd,isuCd
#       MDCSTAT30501 잔고 전종목  : trdDd,mktTpCd(1코스피/2코스닥)
#       MDCSTAT30502 잔고 개별추이: strtDd,endDd,isuCd  (RPT_DUTY_OCCR_DD,
#                                    BAL_QTY,LIST_SHRS,BAL_AMT,MKTCAP,BAL_RTO)
# =========================================================================
KRX_JSON = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"


def krx_login(krx_id: str | None = None, krx_pw: str | None = None) -> requests.Session:
    """KRX 무료회원 로그인 세션 생성 (pykrx 1.2.8 auth.py 와 동일 3단계).
    계정 없으면 data.krx.co.kr 회원가입(무료) 후 KRX_ID/KRX_PW 설정.
    ※ 본 프로브에서는 계정 부재로 로그인 이후 단계는 미실측."""
    krx_id = krx_id or os.environ.get("KRX_ID")
    krx_pw = krx_pw or os.environ.get("KRX_PW")
    if not (krx_id and krx_pw):
        raise RuntimeError("KRX_ID/KRX_PW 필요 (data.krx.co.kr 무료 회원)")
    s = requests.Session()
    s.headers["User-Agent"] = UA
    page = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001.cmd"
    s.get(page, timeout=15)                                   # 1) JSESSIONID
    s.get("https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp?site=mdc",
          headers={"Referer": page}, timeout=15)              # 2) iframe 초기화
    r = s.post("https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001D1.cmd",
               data={"mbrId": krx_id, "pw": krx_pw},
               headers={"Referer": page}, timeout=15)         # 3) 로그인
    r.raise_for_status()
    return s


def fetch_krx_srt(session: requests.Session, bld: str, **params) -> list[dict]:
    """로그인 세션으로 공매도 bld 조회. 예:
    fetch_krx_srt(s, 'dbms/MDC/STAT/srt/MDCSTAT30502',
                  strtDd='20260701', endDd='20260814', isuCd='KR7005930003')"""
    data = {"bld": bld, "locale": "ko_KR", "csvxls_isNo": "false",
            "share": "1", "money": "1"}
    data.update(params)
    r = session.post(KRX_JSON, data=data,
                     headers={"Referer": "http://data.krx.co.kr/contents/MDC/MDI/"
                                         "mdiLoader/index.cmd?menuId=MDC02030101"},
                     timeout=30)
    if r.status_code != 200 or "LOGOUT" in r.text[:20]:
        raise RuntimeError(f"KRX 응답 {r.status_code}: {r.text[:80]} (로그인 만료?)")
    js = r.json()
    for k in ("OutBlock_1", "output", "block1"):
        if k in js:
            return js[k]
    return []


# =========================================================================
# [C-1] 금융위_주식대차정보 (data.go.kr 15059612) — 종목별 일별 대차 체결·상환·잔고
#       ※ 활용신청 후 동작. 갱신: 기준일 T+1 영업일 13시 이후 (금→월요일).
#       응답 필드(문서 실추출): basDt, isinCd, isinCdNm,
#         lnbCclStckCnt(체결주수) lnbRdptStckCnt(상환주수) lnbRmanStckCnt(잔고주수)
# =========================================================================
FSC_LOAN = ("http://apis.data.go.kr/1160100/service/"
            "GetStocLendBorrInfoService/getStItemLendAndBorrStatu")


def fetch_fsc_stock_loan(bas_dt: str | None = None, isin: str | None = None,
                         num_rows: int = 500, page: int = 1) -> dict:
    """종목별 대차거래 현황. bas_dt 생략 시 최신일. isin 지정 시 해당 종목.
    반환: {'total': int, 'items': [...]} — 미신청 키면 RuntimeError(에러 30)."""
    p = {"serviceKey": os.environ["DATA_GO_KR_KEY"], "resultType": "json",
         "numOfRows": num_rows, "pageNo": page}
    if bas_dt:
        p["basDt"] = bas_dt
    if isin:
        p["isinCd"] = isin
    r = requests.get(FSC_LOAN, params=p, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"FSC 대차 API HTTP {r.status_code}: {r.text[:150]} "
                           "(활용신청 여부 확인: data.go.kr/data/15059612)")
    body = r.json()["response"]["body"]
    items = body.get("items") or {}
    return {"total": body.get("totalCount"),
            "items": items.get("item") if isinstance(items, dict) else items}


# =========================================================================
# [C-2] KOFIA FreeSIS — 대차거래 추이(시장 전체 집계). 무인증 동작 실측.
#       POST https://freesis.kofia.or.kr/meta/getMetaDataList.do (JSON body)
#       OBJ_NM=STATSCU0100000060BO (대차거래추이), 070BO·080BO 등 이웃 화면 존재.
#       종목별 화면은 미제공(집계·상위종목 중심) → 종목별은 [C-1] 사용.
# =========================================================================
def fetch_kofia_loan_aggregate(start: str, end: str) -> list[dict]:
    """시장 전체 대차거래 추이 (일별 집계). start/end=YYYYMMDD."""
    body = {"dmSearch": {"tmpV40": "1000000", "tmpV41": "1", "tmpV1": "12",
                         "tmpV45": start, "tmpV46": end,
                         "OBJ_NM": "STATSCU0100000060BO"}}
    r = requests.post("https://freesis.kofia.or.kr/meta/getMetaDataList.do",
                      data=json.dumps(body),
                      headers={"User-Agent": UA, "Content-Type": "application/json",
                               "Referer": "https://freesis.kofia.or.kr/stat/FreeSIS.do"},
                      timeout=30)
    r.raise_for_status()
    return r.json().get("ds1", [])


# =========================================================================
# 데모: 동작 소스 실측 + 샘플 저장
# =========================================================================
def main() -> None:
    load_env()
    samples: dict = {"probe_ts": time.strftime("%Y-%m-%d %H:%M:%S KST")}

    # A) KIS 공매도 거래 — 3종목 2026-07-01~08-18
    token = _kis_token()
    for code in ISIN:
        rows = fetch_kis_short_sale(code, "20260701", "20260818", token)
        keep = [{k: r.get(k) for k in
                 ("stck_bsop_date", "stck_clpr", "acml_vol", "ssts_cntg_qty",
                  "ssts_vol_rlim", "ssts_tr_pbmn", "ssts_tr_pbmn_rlim")}
                for r in rows]
        samples[f"kis_short_sale_{code}"] = keep
        print(f"[KIS] {code}: {len(rows)}일 "
              f"({rows[0]['stck_bsop_date']}~{rows[-1]['stck_bsop_date']}), "
              f"최신 공매도비중 {rows[-1]['ssts_vol_rlim']}%")
        time.sleep(0.2)

    # C-2) KOFIA 대차 집계
    agg = fetch_kofia_loan_aggregate("20260801", "20260818")
    samples["kofia_loan_aggregate"] = agg
    if agg:
        print(f"[KOFIA] 대차추이 {len(agg)}일, 최신일 {max(r['TMPV1'] for r in agg)}")

    # C-1) FSC 종목별 대차 — 활용신청 전이면 안내만
    try:
        res = fetch_fsc_stock_loan(isin=ISIN["005930"])
        samples["fsc_stock_loan_005930"] = res
        print(f"[FSC] 종목별 대차 total={res['total']}")
    except Exception as e:
        print(f"[FSC] 미신청 상태: {e}")

    # B) KRX — 계정 있으면 실측
    try:
        s = krx_login()
        bal = fetch_krx_srt(s, "dbms/MDC/STAT/srt/MDCSTAT30502",
                            strtDd="20260701", endDd="20260814",
                            isuCd=ISIN["005930"])
        samples["krx_short_balance_005930"] = bal[:10]
        print(f"[KRX] 잔고 개별추이 {len(bal)}행")
    except Exception as e:
        print(f"[KRX] 로그인 불가(계정 필요): {e}")

    out = HERE / "short_probe_samples.json"
    out.write_text(json.dumps(samples, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print("샘플 저장:", out)


if __name__ == "__main__":
    sys.stdout = __import__("io").TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()

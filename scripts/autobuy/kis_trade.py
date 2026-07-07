"""KIS 국내주식 주문/잔고 — 자동매수 봇 전용. 안전 최우선.
수량은 항상 1주(하드코딩). dryrun 모드는 실주문 없이 로그용 dict 반환."""
from __future__ import annotations
import json, os, urllib.request as _u
from canslim_lib import kis_api

ORD_QTY = "1"   # ★ 절대 변경/매개변수화 금지 — 1주 상한

def _order(code: str, side: str, mode: str) -> dict:
    base = {"code": code, "side": side, "qty": 1, "mode": mode}
    if mode != "live":
        return {**base, "ok": True, "note": "dryrun(주문 안 냄)"}
    # ★ live 경로는 전부 try 안 — env 누락(KeyError)·hashkey/네트워크 예외가
    #   러너 루프까지 올라가 크래시시키지 않고 ok=False 로 죽는다.
    try:
        token = kis_api.get_access_token()
        if not token:
            return {**base, "ok": False, "error": "no_token"}
        tr = "TTTC0802U" if side == "buy" else "TTTC0801U"   # 구현자: KIS 문서로 확인
        body = {"CANO": os.environ["KIS_ACCOUNT"], "ACNT_PRDT_CD": os.environ.get("KIS_ACNT_PRDT", "01"),
                "PDNO": code, "ORD_DVSN": "01", "ORD_QTY": ORD_QTY, "ORD_UNPR": "0"}  # 01=시장가
        payload = json.dumps(body)
        url = f"{kis_api._base_url()}/uapi/domestic-stock/v1/trading/order-cash"
        headers = {"content-type": "application/json", "authorization": f"Bearer {token}",
                   "appkey": os.environ["KIS_APP_KEY"], "appsecret": os.environ["KIS_APP_SECRET"],
                   "tr_id": tr, "custtype": "P", "hashkey": _hashkey(payload)}
        kis_api._throttle()
        with _u.urlopen(_u.Request(url, data=payload.encode(), headers=headers), timeout=8) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {**base, "ok": d.get("rt_cd") == "0", "resp": d}
    except Exception as e:
        return {**base, "ok": False, "error": f"{type(e).__name__}"}

def _hashkey(payload: str) -> str:
    url = f"{kis_api._base_url()}/uapi/hashkey"
    headers = {"content-type": "application/json", "appkey": os.environ["KIS_APP_KEY"],
               "appsecret": os.environ["KIS_APP_SECRET"]}
    kis_api._throttle()   # hashkey 콜도 초당 호출제한에 포함 — 스로틀 통과
    with _u.urlopen(_u.Request(url, data=payload.encode(), headers=headers), timeout=8) as r:
        return json.loads(r.read().decode("utf-8")).get("HASH", "")

def place_buy_1share(code: str, mode: str = "dryrun") -> dict:
    return _order(code, "buy", mode)

def place_sell_1share(code: str, mode: str = "dryrun") -> dict:
    return _order(code, "sell", mode)

def inquire_holdings() -> list[dict]:
    """보유 종목 [{code, qty, avg_price}]. 실패 시 빈 리스트. (TR TTTC8434R — 구현자 확인)"""
    token = kis_api.get_access_token()
    if not token:
        return []
    return _inquire_holdings_impl(token)


def _inquire_holdings_impl(token: str) -> list[dict]:
    """국내주식 잔고조회 TTTC8434R — GET /uapi/domestic-stock/v1/trading/inquire-balance.
    output1(보유종목 리스트)을 [{code, qty, avg_price}] 로 매핑. 실패·빈 응답 → []."""
    import urllib.parse as _up
    try:
        qs = _up.urlencode({
            "CANO": os.environ["KIS_ACCOUNT"],
            "ACNT_PRDT_CD": os.environ.get("KIS_ACNT_PRDT", "01"),
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        })
        url = f"{kis_api._base_url()}/uapi/domestic-stock/v1/trading/inquire-balance?{qs}"
        headers = {"content-type": "application/json", "authorization": f"Bearer {token}",
                   "appkey": os.environ["KIS_APP_KEY"], "appsecret": os.environ["KIS_APP_SECRET"],
                   "tr_id": "TTTC8434R", "custtype": "P"}
        kis_api._throttle()
        with _u.urlopen(_u.Request(url, headers=headers), timeout=8) as r:
            d = json.loads(r.read().decode("utf-8"))
        if d.get("rt_cd") != "0":
            return []
        rows = d.get("output1") or []
        return [
            {"code": row["pdno"], "qty": int(row["hldg_qty"]), "avg_price": float(row["pchs_avg_pric"])}
            for row in rows
        ]
    except Exception:
        return []

"""3단계 — 폭발 직전(pivot) 시점의 판단 변수 수집.

원칙: CAN SLIM 글자 분류·임계값·합격판정 일절 없음. pivot 직전 확정 분기 기준
"그 당시 투자자가 볼 수 있었던" 변수의 raw 값만 수집. 해석·결론은 사용자 몫.

pivot = pivots.json 의 되돌림 허용폭 20% variant (사용자 확정).
직전 2개 분기 순이익 증가율 = 오닐 델·시스코 서술의 핵심 변수.

사용법:
  python collect_variables.py            # 30종목 전체
  python collect_variables.py --limit 3  # 상위 3종목만(검증)
"""
import argparse
import functools
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cyclecfg  # noqa: E402

for _l in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in _l and not _l.strip().startswith("#"):
        _k, _, _v = _l.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

from canslim_lib.fetch import (  # noqa: E402
    fetch_yahoo_chart, yahoo_symbol, fetch_integration,
    fetch_annual, fetch_quarter, get_row_values,
    load_corp_code_map, resolve_corp_code, dart_get,
    _fetch_dart_quarterly_account_history, _extract_quarterly_eps_row,
    _extract_quarterly_sales_row, _extract_quarterly_account_row, sleep,
    dart_active_key, dart_mark_exhausted,
)
from canslim_lib.criteria_i import fetch_naver_org_flow, analyze_org_flow  # noqa: E402

REPRT = {3: "11013", 6: "11012", 9: "11014", 12: "11011"}


def _num(s):
    try:
        return int(str(s).replace(",", ""))
    except (ValueError, TypeError, AttributeError):
        return None


@functools.lru_cache(maxsize=None)
def dart_share_counts(corp_code: str, qkey: str) -> dict:
    """pivot 직전 분기 보고서의 발행주식총수·유통주식수 (DART 확정, point-in-time)."""
    y, q = int(qkey[:4]), int(qkey[4:6])
    items = dart_get("stockTotqySttus", {
        "corp_code": corp_code, "bsns_year": str(y), "reprt_code": REPRT.get(q, "11014")})
    if not items:
        return {"shares_outstanding": None, "shares_distributed": None}
    # '합계' 행 우선, 없으면 istc_totqy 가 가장 큰 숫자 행 선택 (보통주 등)
    tot = next((it for it in items if "합" in (it.get("se") or "") and _num(it.get("istc_totqy"))), None)
    if tot is None:
        cands = [(it, _num(it.get("istc_totqy"))) for it in items]
        cands = [(it, v) for it, v in cands if v]
        tot = max(cands, key=lambda x: x[1])[0] if cands else None
    if tot is None:
        return {"shares_outstanding": None, "shares_distributed": None}
    return {
        "shares_outstanding": _num(tot.get("istc_totqy")),
        "shares_distributed": _num(tot.get("distb_stock_co")),
    }

KST = timezone(timedelta(hours=9))
DIR = cyclecfg.DIR
PIV = DIR / "pivots.json"
OUT = DIR / "model_book.json"
CSV = DIR / "model_book.csv"
CHOSEN_DD = 0.20


def pick_pivot(rec: dict) -> dict | None:
    for v in rec.get("variants", []):
        if abs(v["drawdown"] - CHOSEN_DD) < 1e-6:
            return v
    return None


def row_by_keyword(parsed, keyword: str, only_confirmed=True):
    """parsed['rows']에서 title에 keyword 포함하는 첫 행의 (period,value) 리스트."""
    if not parsed:
        return []
    for r in parsed.get("rows", []):
        if keyword in (r.get("title") or ""):
            return get_row_values(parsed, r["title"], only_confirmed=only_confirmed)
    return []


def series_map(pairs):
    return {k: v for k, v in pairs}


def _f(raw):
    if raw is None or raw in ("-", ""):
        return None
    try:
        return float(str(raw).replace(",", ""))
    except (ValueError, TypeError):
        return None


# 보통주 우선 EPS 추출기 (다종주식 회사의 '보통주/우선주 ... 주당이익' 분리 대응).
# 공용 라이브러리 비수정 — 이 스터디 전용. 토큰 기반(표기 변형에 견고).
def _pick_eps_item(items: list[dict]) -> dict | None:
    """IS/CIS 행 중 '우선주' 제외, '주당 …이익/손익/손실' 행을 보통주·기본 우선 선택."""
    best = None
    for idx, it in enumerate(items):
        if it.get("sj_div") not in ("IS", "CIS"):
            continue
        nm = "".join((it.get("account_nm") or "").split())  # 유니코드 공백 전부 제거
        if not nm or "주당" not in nm or "우선주" in nm:
            continue
        if not any(t in nm for t in ("이익", "손익", "손실")):
            continue
        score = (0 if "보통주" in nm else 1,
                 0 if "기본" in nm else 1,
                 1 if ("희석" in nm and "기본" not in nm) else 0)
        if best is None or score < best[0]:
            best = (score, idx, it)
    return best[2] if best else None


def _eps_common_row(items: list[dict]) -> dict | None:
    """분기 단일(thstrm_amount) + 전년 동기(frmtrm_q/frmtrm) 추출."""
    it = _pick_eps_item(items)
    if it is None:
        return None
    cur = _f(it.get("thstrm_amount"))
    prv = _f(it.get("frmtrm_q_amount")) or _f(it.get("frmtrm_amount"))
    out = {}
    if cur is not None:
        out["current"] = cur
    if prv is not None:
        out["prior"] = prv
    return out or None


def _pick_sales_item(items: list[dict]) -> dict | None:
    """IS/CIS 매출 행 선택 (우선순위: 매출액>수익(매출액)>영업수익>매출)."""
    best = None
    for it in items:
        if it.get("sj_div") not in ("IS", "CIS"):
            continue
        nm = "".join((it.get("account_nm") or "").split())
        if not nm or "우선주" in nm:
            continue
        rank = next((i for i, k in enumerate(("매출액", "수익(매출액)", "영업수익", "매출"))
                     if k in nm), None)
        if rank is None:
            continue
        if best is None or rank < best[0]:
            best = (rank, it)
    return best[1] if best else None


@functools.lru_cache(maxsize=None)
def dart_cum9m(corp_code: str, year: int, kind: str) -> dict:
    """Q3 보고서(11014)의 9개월 누적 — 당기(thstrm_add)·전년(frmtrm_add) 동시.

    kind='eps'|'sales'. Returns {"cur": float|None, "prv": float|None}.
    """
    pick = _pick_eps_item if kind == "eps" else _pick_sales_item
    for fs in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": "11014", "fs_div": fs})
        if items:
            it = pick(items)
            if it is not None:
                cur = _f(it.get("thstrm_add_amount"))
                prv = _f(it.get("frmtrm_add_amount"))
                if cur is not None or prv is not None:
                    return {"cur": cur, "prv": prv}
    return {"cur": None, "prv": None}


@functools.lru_cache(maxsize=None)
def annual_quarter_single(corp_code: str, year: int, kind: str) -> dict[str, float]:
    """DART 분기단일 맵 (해당년+전년 03/06/09). kind: 'eps'|'sales'."""
    ext = _eps_common_row if kind == "eps" else _extract_quarterly_sales_row
    return series_map(_fetch_dart_quarterly_account_history(corp_code, year, ext))


@functools.lru_cache(maxsize=None)
def dart_annual_value(corp_code: str, year: int, kind: str) -> float | None:
    """DART 사업보고서(11011)에서 연간 EPS/매출 단일값."""
    sales_subs = ["매출액", "수익(매출액)", "영업수익", "매출"]
    for fs in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": "11011", "fs_div": fs})
        if items:
            row = (_eps_common_row(items) if kind == "eps"
                   else _extract_quarterly_account_row(items, sales_subs))
            if row and "current" in row:
                return row["current"]
    return None


def single_quarter(corp_code: str, year: int, q: int, kind: str) -> float | None:
    """단일 분기 값. 03/06/09 = DART 분기단일. 12 = 연간 − (Q1+Q2+Q3 단일)."""
    if q in (3, 6, 9):
        key = f"{year}{q:02d}"
        v = annual_quarter_single(corp_code, year, kind).get(key)
        if v is None:  # 견고화: 다음 해 보고서에 frmtrm(전년 동기)로 동봉됨
            v = annual_quarter_single(corp_code, year + 1, kind).get(key)
        return v
    if q == 12:
        ann = dart_annual_value(corp_code, year, kind)
        if ann is None:
            return None
        cum = dart_cum9m(corp_code, year, kind)  # 연간 − 9M누적 (견고: 2값)
        if cum.get("cur") is not None:
            return ann - cum["cur"]
        m = annual_quarter_single(corp_code, year, kind)  # 폴백: 연간 − (Q1+Q2+Q3)
        q123 = [m.get(f"{year}{x:02d}") for x in (3, 6, 9)]
        if all(v is not None for v in q123):
            return ann - sum(q123)
    return None


_NAVER_Q_CACHE: dict[tuple, dict] = {}


def naver_q_map(code: str, kind: str) -> dict:
    """Naver 분기재무 단일분기 맵 (확정, 최근 ~6분기). kind: 'eps'|'sales'."""
    key = (code, kind)
    if key in _NAVER_Q_CACHE:
        return _NAVER_Q_CACHE[key]
    q = fetch_quarter(code)
    if kind == "eps":
        pairs = row_by_keyword(q, "EPS")
    else:
        pairs = row_by_keyword(q, "매출액") or row_by_keyword(q, "영업수익")
    m = series_map(pairs)
    _NAVER_Q_CACHE[key] = m
    return m


def yoy_pct(corp_code: str, qkey: str, kind: str, code: str | None = None) -> tuple[float | None, str | None]:
    """qkey=YYYYMM 전년 동기 대비 증가율(%). (값, 출처) — 실패 시 (None, 사유)."""
    y, q = int(qkey[:4]), int(qkey[4:6])
    if corp_code:
        if q in (3, 6, 9):
            # 당기 보고서에 동봉된 전년 동기(frmtrm)를 그대로 사용 — 전년 재요청 X
            m = annual_quarter_single(corp_code, y, kind)
            cur = m.get(f"{y}{q:02d}")
            prv = m.get(f"{y - 1}{q:02d}")
        else:  # q == 12: Q4 = 연간 − 9M누적, 전년도 같은 Q3 보고서의 frmtrm_add 사용
            annY = dart_annual_value(corp_code, y, kind)
            annP = dart_annual_value(corp_code, y - 1, kind)
            c9 = dart_cum9m(corp_code, y, kind)
            cur = (annY - c9["cur"]) if (annY is not None and c9.get("cur") is not None) else None
            prv = (annP - c9["prv"]) if (annP is not None and c9.get("prv") is not None) else None
        if cur is not None and prv is not None and prv != 0:
            return round((cur - prv) / abs(prv) * 100, 1), "DART"
    # Naver 보강 (전년 동기가 Naver ~6분기 창에 있을 때만)
    if code:
        nm = naver_q_map(code, kind)
        ck, pk = qkey, f"{y - 1}{q:02d}"
        if ck in nm and pk in nm and nm[pk] not in (0, None):
            return round((nm[ck] - nm[pk]) / abs(nm[pk]) * 100, 1), "Naver보강"
    return None, "전년동기 부재/계정변형(신규상장·미공시 가능)"


def naver_day_chart(code: str, start: str, end: str):
    """api.stock.naver.com 일봉(외국인지분율 포함). start/end=YYYYMMDD."""
    import urllib.request
    url = (f"https://api.stock.naver.com/chart/domestic/item/{code}/day"
           f"?startDateTime={start}0900&endDateTime={end}1600")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return json.loads(urllib.request.urlopen(req, timeout=15).read())
    except Exception:
        return None


def foreign_trend(code: str, pivot_date: str) -> dict:
    """pivot 시점 외국인지분율 + 1년 전 대비 변화(%p). (Naver 일별, 과거 조회 가능)"""
    piv = datetime.strptime(pivot_date, "%Y-%m-%d")
    y0 = (piv - timedelta(days=400)).strftime("%Y%m%d")
    y1 = (piv + timedelta(days=5)).strftime("%Y%m%d")
    data = naver_day_chart(code, y0, y1)
    if not isinstance(data, list) or not data:
        return {"foreign_pct_at_pivot": None, "foreign_pct_1y_ago": None, "change_pp": None}
    rows = [d for d in data if d.get("localDate") and d.get("foreignRetentionRate") is not None]
    if not rows:
        return {"foreign_pct_at_pivot": None, "foreign_pct_1y_ago": None, "change_pp": None}
    pv = piv.strftime("%Y%m%d")
    at = min(rows, key=lambda d: abs(int(d["localDate"]) - int(pv)))
    ago = rows[0]
    fa = float(at["foreignRetentionRate"])
    fg = float(ago["foreignRetentionRate"])
    return {
        "foreign_pct_at_pivot": round(fa, 2),
        "foreign_pct_1y_ago": round(fg, 2),
        "change_pp": round(fa - fg, 2),
    }


def price_tech(code: str, market: str, pivot_date: str, trough_date: str | None = None) -> dict:
    """pivot 시점 신고가 근접·거래량 급증 + base 구조 + 유동성 (Yahoo 2y)."""
    ch = cyclecfg.yahoo(yahoo_symbol(code, market))
    if not ch or not ch.get("closes"):
        return {}
    ts = [datetime.fromtimestamp(t, KST).strftime("%Y-%m-%d") for t in ch["timestamps"]]
    cl, vol = ch["closes"], ch["volumes"]

    def nearest(dstr):
        return min(range(len(ts)), key=lambda i: abs(
            (datetime.strptime(ts[i], "%Y-%m-%d") - datetime.strptime(dstr, "%Y-%m-%d")).days))

    pi = nearest(pivot_date)
    lo = max(0, pi - 250)
    prior_52w_high = max(cl[lo:pi]) if pi > lo else cl[pi]
    near_high = round(cl[pi] / prior_52w_high * 100, 1) if prior_52w_high else None
    v50 = sum(vol[max(0, pi - 50):pi]) / max(1, len(vol[max(0, pi - 50):pi]))
    vol_surge = round(vol[pi] / v50, 2) if v50 else None

    # base 구조: pivot 직전 25일 최고선 아래 머문 마지막 연속 구간
    BW = 25
    bl = max(cl[max(0, pi - BW):pi]) if pi > 0 else cl[pi]
    b = pi - 1
    while b > 0 and cl[b] < bl:
        b -= 1
    bstart = b + 1
    base_slice = cl[bstart:pi] or [cl[pi]]
    base_depth = round((max(base_slice) - min(base_slice)) / max(base_slice) * 100, 1) \
        if max(base_slice) > 0 else None
    # base 직전 선행 상승폭 (사이클 저점 → base 시작)
    prior_up = None
    if trough_date:
        ti = nearest(trough_date)
        if 0 <= ti < bstart and cl[ti] > 0:
            prior_up = round((cl[bstart] - cl[ti]) / cl[ti] * 100, 1)

    # 유동성: pivot일·직전 50일 평균 거래대금(억)
    piv_turn = round(cl[pi] * vol[pi] / 1e8, 1)
    s = slice(max(0, pi - 50), pi)
    n = len(cl[s]) or 1
    avg_turn = round(sum(cl[s][k] * vol[s][k] for k in range(len(cl[s]))) / n / 1e8, 1)

    return {
        "pivot_vs_prior_52w_high_pct": near_high,   # 100 이상이면 신고가 경신
        "pivot_volume_vs_50d_avg": vol_surge,
        "base_start_date": ts[bstart],
        "base_len_days": pi - bstart,
        "base_depth_pct": base_depth,
        "prior_uptrend_pct": prior_up,              # 사이클 저점→base 시작 상승
        "pivot_turnover_eok": piv_turn,
        "pivot_turnover_50d_avg_eok": avg_turn,
    }


# ── 그룹 A/B/C/D 보강 헬퍼 ──

_IDX_CACHE: dict[str, dict | None] = {}


def _idx_series(sym: str) -> dict | None:
    if sym in _IDX_CACHE:
        return _IDX_CACHE[sym]
    ch = cyclecfg.yahoo(sym)
    s = None
    if ch and ch.get("closes"):
        s = {"d": [datetime.fromtimestamp(t, KST).strftime("%Y-%m-%d") for t in ch["timestamps"]],
             "c": ch["closes"]}
    _IDX_CACHE[sym] = s
    return s


def _idx_at(s: dict, dstr: str) -> int | None:
    return max((i for i in range(len(s["d"])) if s["d"][i] <= dstr), default=None)


def market_regime(market: str, pivot_date: str) -> str | None:
    """pivot 시점 시장 지수 국면 (오닐 'M'). 50/200일선 기준."""
    s = _idx_series("%5EKS11" if market == "KOSPI" else "%5EKQ11")
    if not s:
        return None
    i = _idx_at(s, pivot_date)
    if i is None or i < 200:
        return None
    c = s["c"]
    px, ma50, ma200 = c[i], sum(c[i - 49:i + 1]) / 50, sum(c[i - 199:i + 1]) / 200
    if px > ma50 and px > ma200 and ma50 > ma200:
        return "상승추세"
    return "중립" if px > ma200 else "하락추세"


def fx_regime(pivot_date: str) -> dict:
    """pivot 시점 원/달러 수준 + 6개월 변화(%) (Yahoo KRW=X)."""
    s = _idx_series("KRW=X")
    if not s:
        return {"krw_at_pivot": None, "krw_6m_change_pct": None}
    i = _idx_at(s, pivot_date)
    if i is None:
        return {"krw_at_pivot": None, "krw_6m_change_pct": None}
    c = s["c"]
    j = max(0, i - 126)
    chg = round((c[i] - c[j]) / c[j] * 100, 1) if c[j] else None
    return {"krw_at_pivot": round(c[i], 1), "krw_6m_change_pct": chg}


@functools.lru_cache(maxsize=None)
def dart_company(corp_code: str) -> dict:
    """company.json 직접 조회 (dart_get는 'list' 키만 반환해 불가). 키 페일오버."""
    import urllib.request as _u
    while True:
        ak = dart_active_key()
        if not ak:
            return {}
        try:
            url = f"https://opendart.fss.or.kr/api/company.json?crtfc_key={ak}&corp_code={corp_code}"
            d = json.loads(_u.urlopen(_u.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                                      timeout=15).read())
        except Exception:
            return {}
        st = d.get("status")
        if st == "000":
            return d
        if st == "020":             # 한도 초과 → 키 소진 표시, 다음 키
            dart_mark_exhausted(ak)
            continue
        return {}


def dart_largest_holder_pct(corp_code: str, qkey: str) -> float | None:
    """최대주주+특수관계인 기말 지분율 합 (DART hyslrSttus, point-in-time)."""
    y, q = int(qkey[:4]), int(qkey[4:6])
    items = dart_get("hyslrSttus", {"corp_code": corp_code, "bsns_year": str(y),
                                    "reprt_code": REPRT.get(q, "11014")})
    if not items:
        return None
    for it in items:  # '계' 합계행 우선
        lab = "".join(((it.get("nm") or "") + (it.get("relate") or "")).split())
        if lab in ("계", "합계", "소계"):
            v = _f(it.get("trmend_posesn_stock_qota_rt"))
            if v is not None:
                return round(v, 2)
    tot, any_ = 0.0, False
    for it in items:
        v = _f(it.get("trmend_posesn_stock_qota_rt"))
        if v is not None:
            tot += v
            any_ = True
    return round(tot, 2) if any_ else None


def dart_op_cashflow_annual(corp_code: str, year: int) -> float | None:
    """연간 영업활동현금흐름 (DART fnlttSinglAcntAll 사업보고서 CF)."""
    for fs in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {"corp_code": corp_code, "bsns_year": str(year),
                                               "reprt_code": "11011", "fs_div": fs})
        if items:
            for x in items:
                if x.get("sj_div") == "CF":
                    nm = "".join((x.get("account_nm") or "").split())
                    if "영업활동" in nm and "현금흐름" in nm:
                        v = _f(x.get("thstrm_amount"))
                        if v is not None:
                            return v
    return None


def step_q(qkey: str, n: int) -> str:
    """qkey(YYYYMM, 03/06/09/12)에서 n개 분기 뒤로."""
    y, m = int(qkey[:4]), int(qkey[4:6])
    for _ in range(n):
        m -= 3
        if m == 0:
            m, y = 12, y - 1
    return f"{y}{m:02d}"


def supply_flow(code: str, corp_code: str | None, pivot_date: str) -> dict:
    """pivot 직전 60/120영업일 기관·외국인·개인 누적 순매매 (point-in-time).

    finance.naver.com/item/frgn 일별(2.4년 깊이) → pivot 이전으로 필터.
    개인 ≈ −(기관+외국인) 근사(기타법인·기타외인 제외).
    """
    # pivot 까지 + 직전 120영업일만 필요 → 페이지 동적 산정 (frgn 1p≈20영업일)
    cal_days = (datetime.now(KST) - datetime.strptime(pivot_date, "%Y-%m-%d").replace(tzinfo=KST)).days
    need_rows = int(cal_days * 0.69) + 130
    # frgn 깊이 ∝ 페이지(검증: 200p→2010-02). 옛 사이클은 깊게, 상한 260p(~2008).
    pages = max(8, min(260, need_rows // 20 + 3))
    rows = fetch_naver_org_flow(code, pages=pages, sleep_ms=80)
    filt = sorted([r for r in rows if r["date"] <= pivot_date],
                  key=lambda x: x["date"], reverse=True)
    out = {"supply_flow_asof": filt[0]["date"] if filt else None,
           "supply_flow_days": len(filt),
           "supply_flow_src": "finance.naver.com frgn 일별(point-in-time, pivot 이전 필터)"}
    if len(filt) < 20:
        out["supply_flow_src"] = "결손(frgn 깊이 부족 — pivot 이전 데이터<20일)"
        return out
    a = analyze_org_flow(filt)              # 기관(org_net) 60d/QoQ
    r60, p60 = filt[:60], filt[60:120]
    fgn60 = sum(r["fgn_net"] for r in r60)
    fgnp = sum(r["fgn_net"] for r in p60)
    org60 = a["cum_60d"]
    out.update({
        "inst_net_60d": org60, "inst_net_prev60d": a["cum_prev_60d"],
        "inst_trend_60d": a["trend_60d"], "inst_trend_qoq": a["trend_qoq"],
        "fgn_net_60d": fgn60, "fgn_net_prev60d": fgnp,
        "fgn_trend_60d": "up" if fgn60 > 0 else "down" if fgn60 < 0 else "flat",
        "indiv_net_60d_approx": -(org60 + fgn60),
    })
    # 5%룰(fetch_majorstock_holding) 제거: Naver frgn 일별로 기관/외인 point-in-time
    # 이미 확보 → DART 5%룰은 "현재 스냅샷" 잉여(호출 절감, 분석 손실 없음).
    return out


def _datagokr(path: str, params: dict) -> dict | list | None:
    """apis.data.go.kr JSON 호출. 키 미승인 시 None (결손, 추정 금지)."""
    import urllib.request as _u
    import urllib.parse as _p
    import urllib.error as _e
    key = os.environ.get("DATA_GO_KR_KEY")
    if not key:
        return None
    url = f"https://apis.data.go.kr/{path}?" + _p.urlencode(
        {**params, "resultType": "json", "serviceKey": key})
    try:
        r = _u.urlopen(_u.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
        return json.loads(r.read().decode("utf-8", "replace"))
    except (_e.HTTPError, _e.URLError, json.JSONDecodeError, TimeoutError):
        return None


@functools.lru_cache(maxsize=None)
def _basi_item(crno: str, bas_dt: str) -> dict | None:
    """getItemBasiInfo_V3 특정 basDt(YYYYMMDD) 행. 비거래일이면 −6일까지 후퇴."""
    from datetime import datetime as _dt, timedelta as _td
    base = _dt.strptime(bas_dt, "%Y%m%d")
    for back in range(0, 7):
        bd = (base - _td(days=back)).strftime("%Y%m%d")
        d = _datagokr("1160100/GetStocIssuInfoService_V3/getItemBasiInfo_V3",
                      {"numOfRows": "1", "pageNo": "1", "crno": crno, "basDt": bd})
        if not d:
            continue
        try:
            it = d["response"]["body"]["items"]["item"]
            return it[0] if isinstance(it, list) else it
        except (KeyError, TypeError, IndexError):
            return None
    return None


def _pivot_qkey(pivot_date: str) -> str:
    """pivot 직전 종료 분기 키 YYYYMM(03/06/09/12) — DART stockTotqySttus용."""
    y, m = int(pivot_date[:4]), int(pivot_date[5:7])
    for qm in (12, 9, 6, 3):
        if m >= qm:
            return f"{y}{qm:02d}"
    return f"{y - 1}12"


@functools.lru_cache(maxsize=None)
def _basi_latest_lstgdt(crno: str) -> str | None:
    """basDt 없이 getItemBasiInfo_V3 → 상장일(lstgDt, 시간불변). 전 사이클 가용."""
    d = _datagokr("1160100/GetStocIssuInfoService_V3/getItemBasiInfo_V3",
                  {"numOfRows": "1", "pageNo": "1", "crno": crno})
    if not d:
        return None
    try:
        it = d["response"]["body"]["items"]["item"]
        it = it[0] if isinstance(it, list) else it
        return it.get("lstgDt") or it.get("listDt")
    except (KeyError, TypeError, IndexError):
        return None


def stock_basi(corp_code: str | None, pivot_date: str) -> dict:
    """상장일 + pivot시점·1년전 발행주식수.

    상장일: lstgDt 시간불변 → basDt 조회 실패 시 no-basDt 폴백(전 사이클 가용).
    발행주식수: ① data.go.kr getItemBasiInfo_V3 basDt(~2023-10+, point-in-time)
      → 실패 시 ② DART stockTotqySttus 과거 분기(~2015+, point-in-time) → 결손.
    """
    out = {"listing_date": None, "listing_date_src": None,
           "shares": None, "shares_prior": None, "shares_src": None}
    if not corp_code:
        out["listing_date_src"] = "corp_code 없음 — 결손"
        return out
    crno = "".join((dart_company(corp_code).get("jurir_no") or "").split()).replace("-", "")
    if not crno:
        out["listing_date_src"] = "DART 법인등록번호 없음 — 결손"
        return out
    pv = pivot_date.replace("-", "")
    from datetime import datetime as _dt, timedelta as _td
    prior = (_dt.strptime(pivot_date, "%Y-%m-%d") - _td(days=365)).strftime("%Y%m%d")
    it = _basi_item(crno, pv)
    itp = _basi_item(crno, prior)

    # 상장일 (시간불변): basDt별 실패해도 no-basDt 로 확보
    ld = (it.get("lstgDt") or it.get("listDt")) if it else None
    if not ld:
        ld = _basi_latest_lstgdt(crno)
    if ld:
        out["listing_date"] = ld
        out["listing_date_src"] = "data.go.kr getItemBasiInfo_V3 lstgDt(시간불변)"
    else:
        out["listing_date_src"] = "data.go.kr 미가용 — 결손(설립경과 참고)"

    # 발행주식수: data.go.kr point-in-time → 없으면 DART stockTotqySttus 과거폴백
    s = _num(it.get("issuStckCnt")) if it else None
    if s:
        out["shares"] = s
        out["shares_src"] = "data.go.kr getItemBasiInfo_V3(basDt point-in-time)"
    else:
        qk = _pivot_qkey(pivot_date)
        sc = dart_share_counts(corp_code, qk)
        if sc.get("shares_outstanding"):
            out["shares"] = sc["shares_outstanding"]
            out["shares_src"] = f"DART stockTotqySttus {qk}(과거 분기 point-in-time)"
        else:
            out["shares_src"] = "발행주식수 미가용(data.go.kr·DART 모두) — 결손"
    sp = _num(itp.get("issuStckCnt")) if itp else None
    if not sp:
        scp = dart_share_counts(corp_code, step_q(_pivot_qkey(pivot_date), 4))
        sp = scp.get("shares_outstanding")
    out["shares_prior"] = sp
    return out


def short_balance(code: str, pivot_date: str) -> tuple[float | None, str]:
    """공매도 잔고비율. data.go.kr엔 공매도 데이터셋 없음 →
    KRX OPEN API(openapi.krx.co.kr) 키 필요. 키 없으면 (None, 사유)."""
    krx = os.environ.get("KRX_OPENAPI_KEY")
    if not krx:
        return None, "공매도: data.go.kr 미제공, KRX OPEN API 키 미발급 — 결손(추정 금지)"
    # KRX OPEN API 공매도 엔드포인트는 키 발급 후 0단계에서 확정·구현
    return None, "공매도: KRX OPEN API 키 확보됨, 엔드포인트 확정 후 구현 예정"


def collect(rec: dict, corp_map: dict) -> dict:
    code, name, market = rec["code"], rec["name"], rec["market"]
    pv = pick_pivot(rec)
    base = {"code": code, "name": name, "market": market,
            "trough_date": rec["trough_date"], "peak_date": rec["peak_date"]}
    if pv is None:
        return {**base, "error": "20% pivot 없음"}
    q1, q2 = pv["prior_two_quarters"][0], pv["prior_two_quarters"][1]
    corp_code, _ = resolve_corp_code(code, corp_map)

    out = {
        **base,
        "pivot_date": pv["pivot_date"],
        "pivot_close": pv["pivot_close"],
        "pivot_method": pv["method"],
        "prior_q1": q1, "prior_q2": q2,
        "corp_code": corp_code,
    }

    # 1) 실적·성장 — 직전 2개 분기 순이익/매출 증가율 (DART 우선, Naver 보강)
    for fld, qk, kind in (("eps_yoy_q1", q1, "eps"), ("eps_yoy_q2", q2, "eps"),
                          ("sales_yoy_q1", q1, "sales"), ("sales_yoy_q2", q2, "sales")):
        val, src = yoy_pct(corp_code, qk, kind, code)
        out[f"{fld}_pct"] = val
        out[f"{fld}_src"] = src
    # 분기 EPS 절대값(원) — YoY 불가(신규상장 등) 시에도 데이터 제공
    if corp_code:
        for tag, qk in (("q1", q1), ("q2", q2)):
            y, qm = int(qk[:4]), int(qk[4:6])
            ev = single_quarter(corp_code, y, qm, "eps")
            nm = naver_q_map(code, "eps")
            out[f"eps_{tag}_value"] = (round(ev, 1) if ev is not None
                                       else nm.get(qk))
        sleep(120)

    # 2) 연간 추세·재무 — Naver 확정 연간 (과거 actual; 스냅샷 주의)
    a = fetch_annual(code)
    out["annual_eps_3y"] = [(k, v) for k, v in row_by_keyword(a, "EPS")][-3:]
    out["roe_3y"] = [(k, v) for k, v in row_by_keyword(a, "ROE")][-3:]
    out["debt_ratio_3y"] = [(k, v) for k, v in row_by_keyword(a, "부채비율")][-3:]
    out["op_margin_3y"] = [(k, v) for k, v in row_by_keyword(a, "영업이익률")][-3:]
    bps = row_by_keyword(a, "BPS")
    bps_recent = bps[-1][1] if bps else None

    # 3) 밸류에이션 — pivot 시점 PER 근사
    # TTM EPS = DART 직전 4개 분기 단일 EPS 합 (point-in-time). 적자면 N/A 명시.
    ttm_eps, ttm_src = None, None
    if corp_code:
        y, qm = int(q1[:4]), int(q1[4:6])
        seq, yy, mm = [], y, qm
        for _ in range(4):
            seq.append((yy, mm))
            mm -= 3
            if mm == 0:
                mm, yy = 12, yy - 1
        vals = [single_quarter(corp_code, yy, mm, "eps") for yy, mm in seq]
        if all(v is not None for v in vals):
            ttm_eps, ttm_src = sum(vals), "DART 4Q"
    if ttm_eps is None:  # Naver 보강 (6분기 창 내)
        eps_q = series_map(row_by_keyword(fetch_quarter(code), "EPS"))
        pk = [k for k in sorted(eps_q) if k <= q1]
        if len(pk) >= 4:
            ttm_eps, ttm_src = sum(eps_q[k] for k in pk[-4:]), "Naver 4Q"
    if ttm_eps is None:
        out["per_at_pivot_approx"] = "N/A(이력부족)"   # 4분기 EPS 미확보(신규상장 등)
    elif ttm_eps <= 0:
        out["per_at_pivot_approx"] = "N/A(적자)"
    else:
        out["per_at_pivot_approx"] = round(pv["pivot_close"] / ttm_eps, 1)
    out["per_ttm_eps"] = round(ttm_eps, 1) if isinstance(ttm_eps, (int, float)) else None
    out["per_src"] = ttm_src
    out["pbr_at_pivot_approx"] = (round(pv["pivot_close"] / bps_recent, 2)
                                  if bps_recent else None)

    # 발행주식수·유통주식수 (DART stockTotqySttus, point-in-time) / pivot 시총
    integ = fetch_integration(code) or {}
    out["market_cap_now_eok"] = integ.get("market_cap_eok")
    # 발행주식수·상장일: data.go.kr getItemBasiInfo_V3 (basDt point-in-time)
    sb = stock_basi(corp_code, pv["pivot_date"])
    shares = sb.get("shares")
    shares_src = sb.get("shares_src")
    if not shares:  # 폴백: Naver 현재 시총 ÷ 현재가 (현재 기준 근사)
        mc, pr = integ.get("market_cap_eok"), integ.get("price")
        if mc and pr:
            shares = round(mc * 1e8 / pr)
            shares_src = "Naver 시총÷현재가 근사(현재)"
    out["shares_outstanding"] = shares
    out["shares_src"] = shares_src
    out["market_cap_at_pivot_eok"] = (round(pv["pivot_close"] * shares / 1e8, 1)
                                      if shares else None)

    # PSR(주가매출비율) — 적자여도 산출 가능. = pivot 시총 ÷ 최근 4분기 매출
    ttm_sales, psr_src = None, None
    if corp_code:
        y, qm = int(q1[:4]), int(q1[4:6])
        seq, yy, mm = [], y, qm
        for _ in range(4):
            seq.append((yy, mm))
            mm -= 3
            if mm == 0:
                mm, yy = 12, yy - 1
        sv = [single_quarter(corp_code, a, b, "sales") for a, b in seq]
        if all(v is not None for v in sv):
            ttm_sales, psr_src = sum(sv), "DART 4Q"
    if ttm_sales is None:  # Naver 보강
        sq = series_map(row_by_keyword(fetch_quarter(code), "매출액")
                        or row_by_keyword(fetch_quarter(code), "영업수익"))
        pk = [k for k in sorted(sq) if k <= q1]
        if len(pk) >= 4:
            ttm_sales, psr_src = sum(sq[k] for k in pk[-4:]) * 1e8, "Naver 4Q(억원→원)"
    mc_won = (out["market_cap_at_pivot_eok"] * 1e8
              if out.get("market_cap_at_pivot_eok") else None)
    out["psr_at_pivot_approx"] = (round(mc_won / ttm_sales, 2)
                                  if mc_won and ttm_sales and ttm_sales > 0 else None)
    out["psr_ttm_sales_eok"] = (round(ttm_sales / 1e8, 1)
                                if isinstance(ttm_sales, (int, float)) else None)
    out["psr_src"] = psr_src

    out["sector_manual"] = ""  # 섹터·테마 — 사용자 기입 (자동 결손)

    # 4) 수급 — 외국인 지분율 추세 (Naver 일별, 과거 조회 가능)
    out.update({f"foreign_{k}": v for k, v in foreign_trend(code, pv["pivot_date"]).items()})

    # 5) 가격·기술 — 신고가 근접 / 거래량 / base 구조 / 유동성
    out.update(price_tech(code, market, pv["pivot_date"], rec["trough_date"]))

    # 6) 기업행위 — pivot 전후 6개월 증자 공시 (DART list)
    if corp_code:
        piv = datetime.strptime(pv["pivot_date"], "%Y-%m-%d")
        items = dart_get("list", {
            "corp_code": corp_code,
            "bgn_de": (piv - timedelta(days=180)).strftime("%Y%m%d"),
            "end_de": (piv + timedelta(days=180)).strftime("%Y%m%d"),
            "page_count": "100"})
        cap = [it.get("report_nm") for it in (items or [])
               if any(w in (it.get("report_nm") or "") for w in ("유상증자", "무상증자", "전환사채", "신주인수권"))]
        out["capital_actions_around_pivot"] = cap[:8]
        sleep(120)

    # 8) 보강 — 그룹 A(시장국면) / B(순이익률·CFPS·EPS가속·최대주주) /
    #         C(업종·설립경과) / D(환율·희석·지배구조)
    out["market_regime_at_pivot"] = market_regime(market, pv["pivot_date"])
    out.update(fx_regime(pv["pivot_date"]))

    # 세후 순이익률 3년 (Naver 확정 연간)
    out["net_margin_3y"] = [(k, v) for k, v in row_by_keyword(a, "순이익률")][-3:]

    # EPS YoY 4분기 시퀀스 + 가속 여부 (q1 최신 → q4)
    seqk = [q1, q2, step_q(q1, 2), step_q(q1, 3)]
    eps_yoy_4q = []
    for qk in seqk:
        v, _s = yoy_pct(corp_code, qk, "eps", code)
        eps_yoy_4q.append((qk, v))
    out["eps_yoy_4q"] = eps_yoy_4q
    nums = [v for _, v in eps_yoy_4q if isinstance(v, (int, float))]
    out["eps_accelerating"] = (len(nums) >= 3 and nums[0] > nums[1] > nums[2])

    if corp_code:
        # 최대주주+특수관계인 지분율 (오닐 S / 지배구조)
        out["largest_holder_pct"] = dart_largest_holder_pct(corp_code, q1)
        out["largest_holder_src"] = "DART hyslrSttus(기말, point-in-time)"
        # 주당현금흐름(CFPS) vs EPS — 직전 회계연도 영업CF ÷ 발행주식수
        fy = int(q1[:4]) - (1 if int(q1[4:6]) < 12 else 0)
        ocf = dart_op_cashflow_annual(corp_code, fy)
        out["cfps_fy"] = (round(ocf / shares, 1) if ocf and shares else None)
        out["cfps_fy_year"] = fy
        ae = out.get("annual_eps_3y") or []
        out["eps_fy_for_cfps"] = ae[-1][1] if ae else None
        # 희석: pivot 시점 vs 1년 전 발행주식수 증가율 (data.go.kr basDt)
        ps = sb.get("shares_prior")
        out["share_dilution_1y_pct"] = (round((shares - ps) / ps * 100, 2)
                                        if shares and ps else None)
        # 업종(DART 표준산업분류) + 설립 경과연수(상장연수 아님)
        co = dart_company(corp_code)
        out["induty_code"] = co.get("induty_code")
        est = co.get("est_dt")
        if est and len(est) == 8:
            out["years_since_establishment"] = int(pv["pivot_date"][:4]) - int(est[:4])
        else:
            out["years_since_establishment"] = None
        out["age_note"] = "설립 후 경과(상장연수 아님 — DART에 상장일 없음)"
        sleep(150)
    else:
        for k in ("largest_holder_pct", "cfps_fy", "share_dilution_1y_pct",
                  "induty_code", "years_since_establishment"):
            out[k] = None

    # 지주사 플래그(이름 휴리스틱)
    out["holding_co_flag"] = any(t in name for t in ("홀딩스", "지주", "HD현대", "지홀딩스"))

    # 10) 수급(#1) — 기관·외국인·개인 pivot 직전 누적순매매 (point-in-time)
    out.update(supply_flow(code, corp_code, pv["pivot_date"]))
    # 상장일(#2): stock_basi(getItemBasiInfo_V3)에서 이미 확보 (중복 호출 제거)
    ld = sb.get("listing_date")
    out["listing_date"] = ld
    out["listing_date_src"] = sb.get("listing_date_src")
    out["years_since_listing"] = (int(pv["pivot_date"][:4]) - int(ld[:4])
                                  if ld and len(ld) >= 4 and ld[:4].isdigit() else None)
    # 공매도(#3) — data.go.kr 미제공, KRX OPEN API 키 대기
    sbal, ssrc = short_balance(code, pv["pivot_date"])
    out["short_balance_ratio_pct"] = sbal
    out["short_balance_src"] = ssrc

    out["theme_manual"] = ""   # 테마·정책(밸류업·수출사이클 등) — 사용자 기입

    # 9) 정성 (수동 입력란)
    out["qualitative_memo"] = ""  # 신제품·신사업·경영변화·산업상황 — 사용자 기입
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0,
                    help="pivots 순서상 건너뛸 개수 (세션 분할 배치용)")
    ap.add_argument("--merge", action="store_true",
                    help="기존 model_book.json 보존하고 이번 배치만 갱신/추가 "
                         "(섹터수는 누적 전체로 재계산)")
    ap.add_argument("--shard", default=None,
                    help="병렬 안전: 이 배치를 model_book.<shard>.json 으로 "
                         "기록(공용 파일 미접촉). 섹터수는 reduce에서 전체 재계산.")
    args = ap.parse_args()

    out_path = (DIR / f"model_book.{args.shard}.json") if args.shard else OUT
    csv_path = (DIR / f"model_book.{args.shard}.csv") if args.shard else CSV

    piv = json.loads(PIV.read_text(encoding="utf-8"))["pivots"]
    if args.offset:
        piv = piv[args.offset:]
    if args.limit:
        piv = piv[:args.limit]
    corp_map = load_corp_code_map()

    rows = []
    for i, rec in enumerate(piv, 1):
        if rec.get("error"):
            rows.append({"code": rec["code"], "name": rec["name"], "error": rec["error"]})
            continue
        print(f"  [{i}/{len(piv)}] {rec['name']}", file=sys.stderr)
        rows.append(collect(rec, corp_map))

    # RS 머지 (compute_rs.py 산출물)
    rs_path = DIR / "rs.json"
    if rs_path.exists():
        rs_map = {x["code"]: x for x in json.loads(rs_path.read_text(encoding="utf-8"))["rows"]}
        for r in rows:
            x = rs_map.get(r.get("code"))
            if x:
                r["rs_score"] = x.get("rs")
                r["rs_52w_return_pct"] = x.get("winner_52w_return_pct")
                r["rs_src"] = x.get("rs_src") or x.get("rs_note")

    from collections import Counter

    def pfx(c):
        return str(c)[:3] if c else None

    if args.shard:
        # 병렬: 자기 조각만 기록. 섹터수는 reduce에서 전체 재계산(여기선 None).
        for r in rows:
            r["induty_group3"] = pfx(r.get("induty_code"))
            r["sector_group_winner_count"] = None
    else:
        # --merge: 기존 산출 보존, 이번 배치만 갱신/추가 (code 키, 신규 우선)
        if args.merge and OUT.exists():
            prev = json.loads(OUT.read_text(encoding="utf-8")).get("rows", [])
            by_code = {r.get("code"): r for r in prev}
            for r in rows:
                by_code[r.get("code")] = r
            allrows = list(by_code.values())
        else:
            allrows = rows
        # 업종 그룹강도: 누적 *전체* 기준 재계산 (배치마다 섹터수 정합)
        grp = Counter(pfx(r.get("induty_code"))
                      for r in allrows if r.get("induty_code"))
        for r in allrows:
            p = pfx(r.get("induty_code"))
            r["induty_group3"] = p
            r["sector_group_winner_count"] = grp.get(p) if p else None
        rows = allrows

    DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "chosen_drawdown": CHOSEN_DD,
        "principle": "CAN SLIM 미적용. pivot 직전 확정분기 raw 값만. 해석은 사용자 몫.",
        "data_notes": {
            "eps_sales_yoy": "DART 확정 공시(분기단일, Q4=연간−9M). point-in-time 정확.",
            "annual/roe/debt": "Naver 확정 연간(과거 actual, 현재 스냅샷 — 재작성 가능성 미미).",
            "per_pbr_at_pivot": "pivot가 ÷ (TTM EPS / 최근 BPS) 근사.",
            "foreign_pct": "Naver 일별 외국인지분율(과거 조회 가능).",
            "rs_score": "compute_rs.py — pivot일 52주수익률 전종목 백분위(오닐 L). 신규상장 결손.",
            "market_regime/fx": "Yahoo 지수·KRW=X 2y. pivot 시점 국면·환율.",
            "base/turnover": "Yahoo 2y — base 길이·깊이·선행상승·거래대금.",
            "largest_holder": "DART hyslrSttus 기말지분율(point-in-time).",
            "cfps": "DART 직전회계연도 영업활동현금흐름÷발행주식수. 연 EPS와 비교.",
            "induty_code": "DART 표준산업분류. 같은 코드 위너 수=그룹강도.",
            "age": "설립 후 경과(상장연수 아님 — DART에 상장일 없음).",
            "limitation": "국내 기관·3주체 수급 과거 시계열·정확 상장일·공매도잔고 = "
                          "자동수집 불가 → 결손 명시. 추정으로 채우지 않음.",
        },
        "rows": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV (핵심 열만)
    cols = ["code", "name", "market", "pivot_date", "prior_q1", "prior_q2",
            "rs_score", "eps_yoy_q1_pct", "eps_yoy_q2_pct", "eps_accelerating",
            "sales_yoy_q1_pct", "per_at_pivot_approx", "pbr_at_pivot_approx",
            "psr_at_pivot_approx",
            "market_cap_at_pivot_eok", "largest_holder_pct", "cfps_fy",
            "share_dilution_1y_pct", "market_regime_at_pivot", "krw_at_pivot",
            "foreign_foreign_pct_at_pivot", "foreign_change_pp",
            "pivot_vs_prior_52w_high_pct", "pivot_volume_vs_50d_avg",
            "base_len_days", "base_depth_pct", "prior_uptrend_pct",
            "induty_code", "sector_group_winner_count", "years_since_establishment"]
    lines = [",".join(cols)]
    for r in rows:
        lines.append(",".join(str(r.get(c, "")) for c in cols))
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"written {out_path} / {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

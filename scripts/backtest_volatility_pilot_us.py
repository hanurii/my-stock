"""변동성 파일럿 백테스트 — "종목의 평소 출렁임이 성적을 가르는가".

기존 pivot_backtest_nextday_multi.py 의 골격(매 스캔일 시계열 절단 → 관문 → 패턴 →
익일 피벗 돌파 진입)을 그대로 쓰되, 실거래 충실도를 위해 네 가지를 고쳤다:

  1. **entry_ready 적용** — 기존은 status=='actionable' 만 봐서 패턴이 검출되지 않은
     종목까지 세었다(실측 약 3배 부풀림). 여기서는 detected AND actionable 만 진입 후보.
  2. **손익비 +20/-10** — 기존 +10/-5 는 2026-08-13 이전 규칙.
  3. **시점 유니버스** — 기존은 오늘 상장 목록(FDR)이라 상장폐지 종목이 통째로 빠지는
     생존 편향이 있었다. 여기서는 .cache/pdata 의 그날 스냅샷을 쓴다(상폐분 포함).
  4. **거래대금 룩어헤드 제거** — 수정주가 시계열로 계산한 거래대금은 미래의 액면분할·
     감자를 미리 반영한다. 여기서는 pdata 의 원본 거래대금(trPrc_eok)을 쓴다.

변동성 정의: **ATR(20) ÷ 종가 × 100 = 하루 평균 변동폭(%)**.
종가끼리의 표준편차가 아니라 ATR을 쓰는 이유 — 우리 손절은 장중 저가가 -10%에 닿으면
발동하므로 장중 폭과 갭을 담는 잣대여야 한다(미너비니도 수축을 ATR로 잰다).

실행: python -X utf8 scripts/backtest_volatility_pilot.py --start 2025-11-26 --end 2026-08-21
산출: public/data/backtest-volatility-pilot.json (기본)
"""
from __future__ import annotations

import argparse, json, re, sys
from bisect import bisect_right
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from canslim_lib import ohlcv_matrix  # noqa: E402
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"

from canslim_lib.trend_template import evaluate_trend_template  # noqa: E402
from canslim_lib.cheat import evaluate_cheat, DEFAULT_PARAMS as CHEAT_P  # noqa: E402
from canslim_lib.vcp import evaluate_vcp  # noqa: E402
from canslim_lib.power_play import evaluate_power_play  # noqa: E402
from canslim_lib.pivot_backtest import (  # noqa: E402
    simulate_pivot_trade, price_bucket, truncate_series, tally, group_win_rate, rel_volume)
from canslim_lib import liveness  # noqa: E402
from canslim_lib.pdata_series import build_series as build_pdata_series  # noqa: E402
from screen_trend_template import _compute_rs_for_all  # noqa: E402

KST = timezone(timedelta(hours=9))
PDATA = MAIN / ".cache" / "pdata"
RS_MIN = 80
TARGET_PCT = 20.0
STOP_PCT = 10.0
MIN_TURNOVER_EOK = 5.0        # 미너비니 저유동성 컷(50일 평균 거래대금)
TURNOVER_WINDOW = 50
ATR_WINDOW = 20
MIN_CLOSES = 200              # 200일선 요구
REF = "005930"                # 거래일 달력 기준 (한국)

# ── 25번: 시장 스위치. 기본 "kr" 이면 원본과 완전히 같은 경로를 탄다(G1). ──
MARKET = "kr"                 # "kr" | "us"
US_VARIANT = "base"           # base | sec | adr
US_USD_KRW = 1300.0
US_LIMIT = None               # peak RSS 실측용 종목 샤드
_US_CACHE = None              # (universe, packed, full, meta)

# 제외 패턴 — pykrx_universe.EXCLUDE_PATTERN 과 동일(스팩·리츠·ETF·ETN·인프라·우선주)
EXCLUDE_PATTERN = re.compile(
    r"스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|\d우$|우$|우\(전환\)|우B\(전환\)")


# ── pdata: 시점 유니버스 + 원본 거래대금 ────────────────────────────────────

SERIES_SOURCE = "cache"          # "cache" | "pdata"
RESOLVE_TAIL_DAYS = 300          # 진입 후 결착(+20/-10)까지 볼 여유 (최장 보유 79거래일)


def series_load_end(end: str) -> str:
    """pdata 시계열을 어디까지 읽을지 — 스캔 종료일 + 결착 여유.

    end 에서 끊으면 마지막 매수분이 전부 '미결'로 빠져 승률이 왜곡된다.
    무한정 늘리면 메모리·시간이 커지므로 1년 이내로 묶는다.
    """
    d = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=RESOLVE_TAIL_DAYS)
    return d.strftime("%Y-%m-%d")


def _iter_pdata(start: str, end: str):
    """[start, end] pdata 파일을 날짜순으로 하나씩 열어 (날짜, 레코드)를 낸다."""
    s, e = start.replace("-", ""), end.replace("-", "")
    for p in sorted(PDATA.glob("price_*.json")):
        d = p.stem[6:]
        if not (s <= d <= e):
            continue
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        yield f"{d[:4]}-{d[4:6]}-{d[6:]}", recs


def load_pdata_range(start: str, end: str) -> tuple[dict, dict]:
    """[start, end] 의 pdata 일자 파일을 읽어 (날짜별 유니버스, 종목별 거래대금 시계열).

    universe[date] = {code: {"name","market","cap_eok"}}   ← 그날 실제 상장 종목
    turnover[code] = [(date, 거래대금_억원), ...]           ← 원본(비수정) 값
    """
    universe: dict[str, dict] = {}
    turnover: dict[str, list] = {}
    s, e = start.replace("-", ""), end.replace("-", "")
    files = sorted(p for p in PDATA.glob("price_*.json") if s <= p.stem[6:] <= e)
    for p in files:
        d = p.stem[6:]
        date = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        day = {}
        for code, r in recs.items():
            mkt = r.get("mrktCtg")
            if mkt not in ("KOSPI", "KOSDAQ"):
                continue                      # KONEX·외국주 제외
            name = r.get("itmsNm") or ""
            t = r.get("trPrc_eok")
            if t is not None:
                turnover.setdefault(code, []).append((date, t))
            if EXCLUDE_PATTERN.search(name):
                continue
            day[code] = {"name": name, "market": mkt, "cap_eok": r.get("market_cap_eok")}
        universe[date] = day
    packed = {c: ([d for d, _ in h], [t for _, t in h]) for c, h in turnover.items()}
    return universe, packed


def avg_turnover_asof(hist: tuple | None, asof: str, window: int = TURNOVER_WINDOW) -> float | None:
    """원본 거래대금의 asof 이전 window 일 평균(억원). 표본 부족이면 None.

    hist = (날짜리스트, 값리스트) 로 날짜 정렬돼 있어 bisect 로 자른다(전수 스캔 방지).
    """
    if not hist:
        return None
    dates, vals = hist
    k = bisect_right(dates, asof)
    if k < window // 2:
        return None
    seg = vals[max(0, k - window):k]
    return sum(seg) / len(seg)


# ── 변동성: ATR(20) / 종가 × 100 ────────────────────────────────────────────

def atr_pct(series: dict, window: int = ATR_WINDOW) -> float | None:
    """하루 평균 변동폭(%). True Range = max(고-저, |고-전종|, |저-전종|)."""
    h, l, c = series["highs"], series["lows"], series["closes"]
    n = len(c)
    if n < window + 1 or not c[-1]:
        return None
    trs = []
    for i in range(n - window, n):
        if h[i] is None or l[i] is None or c[i - 1] is None:
            continue
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    if len(trs) < window // 2:
        return None
    return (sum(trs) / len(trs)) / c[-1] * 100


def atr_band(v: float | None) -> str:
    """보고용 구간. 경계는 사전에 고정(사후 최적화 금지)."""
    if v is None:
        return "미상"
    if v < 2.5:
        return "①조용 <2.5%"
    if v < 4.0:
        return "②보통 2.5~4%"
    if v < 6.0:
        return "③큼 4~6%"
    return "④매우큼 6%+"


# 진입일 '종일' 거래량은 장중엔 알 수 없는 값이다. 기록만 하고 절대 필터로 쓰지 말 것
# (과거 이 프로젝트에서 이걸 필터로 써 승률이 69%→41%로 무너진 전례가 있다).
REL_VOL_FIELD = "rel_vol_entry_LOOKAHEAD_DO_NOT_FILTER"


def entry_price(pivot: float, open_px: float | None) -> float:
    """실제 체결가 — 익일 시가가 이미 피벗 위(갭업)면 피벗이 아니라 시가에 산다.

    피벗 가격으로 계산하면 기대값이 일관되게 부풀려진다(실측: 갭업 32.2%,
    전체 기대값 +2.16% → +1.48%). 감사 지적(26-08-22) 반영.
    """
    if open_px is None:
        return pivot
    return max(pivot, open_px)


# ── 백테스트 전용: 관문임박(gate_near) 재현 ────────────────────────────────
# 프로덕션은 26-08-21부터 GATE_NEAR_ENABLED=False 라 항상 None 이지만, 여기서는
# "완화를 켰다면 어땠을까"를 시험하기 위해 그 시절 판정 로직을 그대로 재현한다.
# 한도 정본(끄기 전 값): ①150·200MA -10% · ⑤50MA -15% · ⑦52주고가 -35%
GATE_NEAR_TOL_BT = {"ma150_200": 0.90, "ma50": 0.85, "high52w": 0.65}


def is_gate_near(result: dict, close: float | None, allow: set) -> bool:
    """6~7/8 통과 + 실패가 allow 안에만 + 근접 한도 이내면 True."""
    if result["pass"] or result["passed_count"] < 6 or not close:
        return False
    fails = {k for k, v in result["criteria"].items() if not v["pass"]}
    if not fails or not fails <= allow:
        return False
    ex = result.get("extras") or {}
    if "1" in fails:
        a, b = ex.get("sma150"), ex.get("sma200")
        if not a or not b or close < a * GATE_NEAR_TOL_BT["ma150_200"] or close < b * GATE_NEAR_TOL_BT["ma150_200"]:
            return False
    if "5" in fails:
        a = ex.get("sma50")
        if not a or close < a * GATE_NEAR_TOL_BT["ma50"]:
            return False
    if "7" in fails:
        h = ex.get("high_52w")
        if not h or close < h * GATE_NEAR_TOL_BT["high52w"]:
            return False
    return True


# 진입 후보로 삼을 패턴 상태. 기본은 actionable(피벗 미돌파)만 —
# forming(예의주시)까지 넓히면 "치솟기 전에 미리 걸어두기"를 시험한다.
ENTRY_STATUSES = {"actionable"}
GATE_NEAR_ALLOW: set = set()

# 2.5단계 「관문만」 팔 (β1 대조군). 패턴 피벗 대신 **스캔일 D의 고가**를 방아쇠로 쓴다.
# 🚨 부등호는 β1 정본(`research/handoff/scripts/16-selection-edge.py:118`)과 글자 그대로
#    같아야 한다 — `h[ni] <= thr` 이면 진입 없음, 즉 **동점은 진입 아님**.
#    패턴 팔은 `hi < pivot` 이면 건너뛰므로 **동점에 진입한다**. 둘이 다르다.
# 🚨 **방아쇠 전수 방출** (38번 · 오프라인 청산 변형 계산용).
#    청산 규칙이 바뀌면 **결착일이 바뀌고 → `open_until` 이 바뀌고 → «그 뒤 진입»이 바뀐다.**
#    (실측: 손절 −10% 3,776건 vs −5% 5,074건.) 그래서 **실현 진입만 뽑으면 부족하다** —
#    `open_until` 에 막힌 것까지 **방아쇠가 당겨진 전수**를 남겨야 오프라인이 하네스를 재현한다.
EMIT_PATHS = None              # 경로 파일 경로(None 이면 안 낸다)
PATH_DAYS = 250                # 최대 보유 기간(옛 방법충실 백테스트와 같게)
ARM = "pattern"                # "pattern" | "gate"
GATE_PAT = "GATE"
# 동점 규칙. **둘 다 무조건 돌린다**(두뇌 세션 확정) — 조건부 발동 없음.
#   "strict" = `hi <= thr` 이면 진입 없음. **16번 β1 과 짝이 맞는 판** ← 헤드라인
#   "ge"     = 동점에도 진입. **패턴 팔(`hi < pivot` 이면 건너뜀 = `>=`)과 규칙이 같아지는
#              «내부 일관성이 있는 판»** ← 항상 보고하는 민감도
# 🚨 규율: **문턱을 하나 더 다는 것보다 둘 다 돌리는 게 싸면, 둘 다 돌린다.**
#         판단을 아끼는 게 아니라 «판단할 필요 자체»를 없앤다.
GATE_TIE = "strict"            # "strict" | "ge"


# ── 패턴: entry_ready(검출 AND 진입임박)만 ──────────────────────────────────

def detect_entry_ready(st: dict, pname: str):
    """패턴이 **검출**되고 status=='actionable' 이면 피벗, 아니면 None.

    ARM=="gate" 의 `GATE` 패턴만 예외 — 패턴 검출 없이 **D 당일 고가**를 낸다(β1).

    기존 백테스트는 status 만 봤는데, status 는 패턴 성립과 무관하게 가격 위치로 붙는
    라벨이라 미검출 종목까지 셌다(실측 약 3배). 여기서는 검출 플래그를 함께 요구한다.
    돌파(breakout)는 제외 — 이 백테스트는 D 시점 미돌파분을 익일 돌파 시 사는 설계다.
    """
    if pname == GATE_PAT:
        h = st.get("highs") or []
        return h[-1] if h and h[-1] else None
    try:
        r = evaluate_vcp(st) if pname == "VCP" else (
            evaluate_cheat(st, CHEAT_P) if pname == "3C" else evaluate_power_play(st))
    except Exception:
        return None
    detected = r.get("vcp_detected")
    if detected is None:
        detected = r.get("pattern_detected")
    if not detected or r.get("status") not in ENTRY_STATUSES or not r.get("pivot_price"):
        return None
    return r["pivot_price"]


def run(start: str, end: str, step: int) -> dict:
    # 관문이 200일선·52주 신고가(253거래일)를 요구한다. 캐시 모드는 캐시가 이미
    # 400일을 들고 있어 140일이면 됐지만, pdata 모드는 시계열을 여기서 만드므로
    # 253거래일(≈370일) + 여유를 직접 확보해야 한다. 모자라면 조용히 후보 0이 된다.
    # 🚨 미국도 430이어야 한다. 기본값 140(≈97거래일)로는 **200일 종가·52주 고가를
    #    만들 수 없어** 창 앞부분이 통째로 죽는다 — 실측: 미국 전체 실행에서
    #    **평가 0인 날 103일 · 후보 0인 날 125일(첫 후보 2021-07-30)**.
    #    한국은 `--series pdata` 라 430을 받아 첫날부터 정상이었다. **두 시장 비대칭.**
    warm_days = 430 if (SERIES_SOURCE == "pdata" or MARKET == "us") else 140
    warm = (datetime.strptime(start, "%Y-%m-%d") - timedelta(days=warm_days)).strftime("%Y-%m-%d")
    if MARKET == "us":
        global _US_CACHE
        import us_loader
        print(f"Sharadar 적재 {warm}~{series_load_end(end)} (variant={US_VARIANT}) …", flush=True)
        _US_CACHE = us_loader.build_all(warm, series_load_end(end), US_VARIANT,
                                        US_USD_KRW, US_LIMIT)
        universe_by_date, turnover = _US_CACHE[0], _US_CACHE[1]
    else:
        print(f"pdata 적재 {warm}~{end} …", flush=True)
        universe_by_date, turnover = load_pdata_range(warm, end)
    print(f"  일자 {len(universe_by_date)}일 · 거래대금 시계열 {len(turnover)}종목", flush=True)

    full: dict[str, dict] = {}
    all_codes = {c for day in universe_by_date.values() for c in day}
    if MARKET == "us":
        full = _US_CACHE[2]
    elif SERIES_SOURCE == "pdata":
        # 400일 롤링 캐시로는 2024-12 이전을 못 본다 → pdata 원본에서 직접 만든다.
        # 하루씩 흘려보내 1,600일치를 통째로 메모리에 안 올린다.
        print(f"  pdata 시계열 생성 {warm}~{series_load_end(end)} (결착 여유 포함) …", flush=True)
        full = build_pdata_series(_iter_pdata(warm, series_load_end(end)))
    else:
        for c in all_codes:
            s = ohlcv_matrix.get_series(c)
            if s and s.get("closes"):
                full[c] = s
    print(f"  유니버스 등장 {len(all_codes)}종목 · 시계열 보유 {len(full)}종목", flush=True)

    ref = REF if MARKET == "kr" else __import__("us_loader").REF
    cal = (full.get(ref) or (ohlcv_matrix.get_series(ref) if MARKET == "kr" else None)
           or {"dates": sorted({d for s in full.values() for d in s["dates"]})})["dates"]
    scan_dates = [d for d in cal if start <= d <= end][::step]
    print(f"스캔일 {len(scan_dates)}개 ({scan_dates[0]}~{scan_dates[-1]}, step {step})", flush=True)

    events, per_date = [], []
    trig_paths = []            # 방아쇠 전수 경로(38번) — `open_until` 에 막힌 것도 포함
    tie_events = []            # 관문만 팔의 «동점» 그림자 거래 (진입 아님 · 영향 상한 계산용)
    open_until: dict[str, str] = {}
    n_skip_overlap = n_skip_halt = n_skip_liq = 0

    for D in scan_dates:
        day_univ = universe_by_date.get(D) or {}
        stD = {}
        for c in day_univ:
            s = full.get(c)
            if not s:
                continue
            t = truncate_series(s, D)
            if len(t["closes"]) < MIN_CLOSES or not t["dates"] or t["dates"][-1] != D:
                continue
            if liveness.is_halted(t, asof=D):
                n_skip_halt += 1
                continue
            tv = avg_turnover_asof(turnover.get(c), D)
            if tv is None or tv < MIN_TURNOVER_EOK:
                n_skip_liq += 1
                continue
            stD[c] = t
        if not stD:
            per_date.append({"scan_date": D, "n_universe": len(day_univ), "n_eval": 0,
                             "n_candidates": 0, "n_entered": 0,
                             **({"codes": []} if ARM == "gate" else {})})
            continue

        rs = _compute_rs_for_all([{"code": c, "closes": t["closes"], "ok": True}
                                  for c, t in stD.items()])
        n_cand = n_ent = n_tie = 0
        cand_codes = []          # 결정 B — 관문만 팔에서 «추첨 풀»의 종목 코드를 남긴다
        for c, t in stD.items():
            rsv = (rs.get(c) or {}).get("rs")
            tt = evaluate_trend_template(t["closes"], rs=rsv, rs_min=RS_MIN)
            near = bool(GATE_NEAR_ALLOW) and is_gate_near(tt, t["closes"][-1], GATE_NEAR_ALLOW)
            if not tt["pass"] and not near:
                continue
            for pname in (("VCP", "3C", "PP") if ARM == "pattern" else (GATE_PAT,)):
                pivot = detect_entry_ready(t, pname)
                if pivot is None:
                    continue
                n_cand += 1
                if ARM == "gate":
                    cand_codes.append(c)
                s = full[c]
                if D not in s["dates"]:
                    continue
                ni = s["dates"].index(D) + 1
                if ni >= len(s["dates"]):
                    continue
                hi = s["highs"][ni]
                if hi is None or hi < pivot:
                    continue                      # 익일 미돌파 → 진입 없음
                if EMIT_PATHS is not None:
                    # 🚨 **`open_until` 검사 «전에»** 낸다 — 막힌 것도 다른 청산 규칙에서는
                    #    진입이 될 수 있다. 본 팔의 `events`·`n_skip_overlap` 은 안 건드린다.
                    _o = (s.get("opens") or [None] * len(s["dates"]))[ni]
                    _epx = entry_price(pivot, _o)
                    _e = min(ni + PATH_DAYS, len(s["dates"]))
                    trig_paths.append({
                        "code": c, "pattern": pname, "scan_date": D,
                        "entry_date": s["dates"][ni],
                        "pivot": round(pivot, 4), "entry_price": round(_epx, 4),
                        "atr_band": atr_band(atr_pct(t)),
                        "d": s["dates"][ni:_e],
                        # 🚨 시가 추가 (2026-08-24) — «실집행 근사판»에 필요하다.
                        #    지정가 매도는 갭업이면 `max(목표가, 시가)` 에 체결되고,
                        #    시장가 손절은 갭다운이면 `min(손절선, 시가)` 에 나간다.
                        #    시가가 없으면 그 둘을 «잴 수 없다».
                        "o": [None if x is None else round(x, 4)
                              for x in (s.get("opens") or [None] * len(s["dates"]))[ni:_e]],
                        "h": [None if x is None else round(x, 4)
                              for x in s["highs"][ni:_e]],
                        "l": [None if x is None else round(x, 4)
                              for x in s["lows"][ni:_e]],
                        "c": [None if x is None else round(x, 4)
                              for x in s["closes"][ni:_e]],
                    })
                if ARM == "gate" and hi == pivot:
                    n_tie += 1     # 규칙과 무관하게 «동점이 몇 건인지»는 항상 센다
                if ARM == "gate" and GATE_TIE == "strict" and hi <= pivot:
                    # strict 판: **동점이면 진입하지 않는다**(β1 짝). —
                    # 🚨 한국은 호가 단위가 굵어 동점이 흔하고 미국은 1센트라 드물 수 있다.
                    #    동점 비율이 시장 간에 다르면 «대조군의 엄격함»이 달라져
                    #    C_US − C_KR 에 「호가 단위 차이」가 섞인다.
                    if hi == pivot:
                        # 🚨 **그림자 계산** — 진입은 여전히 시키지 않되 «들어갔다면 어땠을지»만
                        #    같은 하네스로 계산해 따로 남긴다. 두뇌 세션 사전등록:
                        #      Δ = 동점비율(닿은 것 대비) × (동점 거래당 − 대조군 거래당)
                        #    ⚠️ 이제 이 값들은 **발동 조건이 아니라 «설명 수치»**다 —
                        #       두 판(`>` / `>=`)이 갈렸을 때 **왜 갈렸는지**를 설명한다.
                        #    ⚠️ `open_until` 도 `n_ent` 도 건드리지 않는다 — 본 팔에 영향 0.
                        _epx = entry_price(
                            pivot, (s.get("opens") or [None] * len(s["dates"]))[ni])
                        _sim = simulate_pivot_trade(s, ni, _epx, TARGET_PCT, STOP_PCT)
                        tie_events.append({
                            "code": c, "pattern": pname, "scan_date": D,
                            "entry_date": s["dates"][ni],
                            "resolve_date": _sim.get("resolve_date"),
                            "pivot": round(pivot, 2), "entry_price": round(_epx, 2),
                            "result": _sim["result"],
                            "gain_at_resolve_pct": _sim.get("gain_at_resolve_pct"),
                            "atr_band": atr_band(atr_pct(t)),
                        })
                    continue
                edate = s["dates"][ni]
                if c in open_until and edate <= open_until[c]:
                    n_skip_overlap += 1
                    continue
                epx = entry_price(pivot, (s.get("opens") or [None] * len(s["dates"]))[ni])
                sim = simulate_pivot_trade(s, ni, epx, TARGET_PCT, STOP_PCT)
                open_until[c] = sim.get("resolve_date") or edate
                n_ent += 1
                v = atr_pct(t)
                events.append({
                    "code": c, "name": day_univ[c]["name"], "market": day_univ[c]["market"],
                    "pattern": pname, "gate_near": near, "scan_date": D, "entry_date": edate,
                    "resolve_date": sim.get("resolve_date"), "month": edate[:7],
                    "pivot": round(pivot, 2), "entry_price": round(epx, 2),
                    "gap_up_pct": round((epx / pivot - 1) * 100, 2), "rs": rsv,
                    "atr_pct": round(v, 2) if v is not None else None,
                    "atr_band": atr_band(v),
                    "turnover_eok": round(avg_turnover_asof(turnover.get(c), D) or 0, 2),
                    REL_VOL_FIELD: rel_volume(s, ni),
                    "price_bucket": price_bucket(epx),
                    "result": sim["result"], "days_held": sim.get("days_held"),
                    # 25번: 상폐 청산("open")과 손절("stop")을 구분해야 해서 복사한다.
                    # ⚠️ 원본 하네스에는 없는 키라 G1 대조에서 이 키만 제외한다.
                    "exit_reason": sim.get("exit_reason"),
                    "max_gain_pct": sim.get("max_gain_pct"),
                    "max_dd_pct": sim.get("max_dd_pct"),
                    "gain_at_resolve_pct": sim.get("gain_at_resolve_pct"),
                })
        per_date.append({"scan_date": D, "n_universe": len(day_univ), "n_eval": len(stD),
                         "n_candidates": n_cand, "n_entered": n_ent,
                         **({"codes": cand_codes, "n_tie": n_tie}
                            if ARM == "gate" else {})})
        print(f"  {D}: 평가 {len(stD)} · 후보 {n_cand} · 진입 {n_ent} (누적 {len(events)})", flush=True)

    return {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "params": {
            "method": "volatility_pilot_nextday_entry",
            "entry_fill": "max(피벗, 익일 시가) — 갭업 보정",
            "start": start, "end": end, "step": step,
            "target_pct": TARGET_PCT, "stop_pct": STOP_PCT, "rs_min": RS_MIN,
            "candidate_gate": "detected AND actionable (entry_ready)",
            # 🚨 이 문구가 미국 실행에도 «한국 것»으로 박혀 있었다 — 오늘 세 번째
            #    「라벨은 맞는데 내용이 다른」 사고와 같은 종류다. 시장별로 갈라 적는다.
            "market": MARKET,
            "warm_days": (430 if (SERIES_SOURCE == "pdata" or MARKET == "us") else 140),
            "gate_tie": GATE_TIE,
            "universe": ("pdata point-in-time (상장폐지 포함)" if MARKET == "kr"
                         else "Sharadar SEP point-in-time (상장폐지 포함 · 기본판)"),
            "turnover": ("pdata 원본 trPrc_eok 50일 평균 (수정주가 룩어헤드 제거)"
                         if MARKET == "kr"
                         else "close × volume × USD_KRW ÷ 1e8 의 50일 평균"),
            "volatility": f"ATR({ATR_WINDOW}) / 종가 × 100",
            "min_turnover_eok": MIN_TURNOVER_EOK,
            "n_scan_dates": len(scan_dates), "n_trades": len(events),
            "skipped": {"overlap": n_skip_overlap, "halted": n_skip_halt,
                        "low_turnover": n_skip_liq},
        },
        "summary": tally(events),
        "by_atr_band": group_win_rate(events, "atr_band"),
        "by_month": group_win_rate(events, "month"),
        "by_pattern": group_win_rate(events, "pattern"),
        "by_price": group_win_rate(events, "price_bucket"),
        "per_date": per_date,
        "events": events,
        **({"trigger_paths": trig_paths} if EMIT_PATHS is not None else {}),
        # 관문만 팔의 «동점» 그림자 거래. **진입이 아니다** — 영향 상한 Δ 계산 전용.
        **({"tie_events": tie_events} if ARM == "gate" else {}),
    }


def main():
    ap = argparse.ArgumentParser(description="변동성 파일럿 백테스트")
    ap.add_argument("--start", default="2025-11-26")
    ap.add_argument("--end", default="2026-08-21")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--out", default="public/data/backtest-volatility-pilot.json")
    ap.add_argument("--target", type=float, default=20.0,
                    help="익절 목표(%%) — 청산 규칙 비교용")
    ap.add_argument("--stop", type=float, default=10.0,
                    help="손절폭(%%) — 청산 규칙 비교용")
    ap.add_argument("--series", choices=["cache", "pdata"], default="cache",
                    help="시세 출처: cache=400일 롤링(최근만) · pdata=원본 2020~(과거 가능)")
    ap.add_argument("--gate-near", choices=["off", "ma", "ma+high"], default="off",
                    help="관문임박 포함 범위: off=8조건 필수 · ma=①⑤ 완화 · ma+high=①⑤⑦ 완화")
    ap.add_argument("--market", choices=["kr", "us"], default="kr",
                    help="kr=기존 pdata 경로(G1 동일성 검증) · us=Sharadar")
    ap.add_argument("--us-variant", choices=["base", "sec", "adr"], default="base")
    ap.add_argument("--usd-krw", type=float, default=1300.0)
    ap.add_argument("--us-limit", type=int, default=0, help="종목 샤드(0=전체)")
    ap.add_argument("--arm", choices=["pattern", "gate"], default="pattern",
                    help="pattern=VCP/3C/PP 피벗(기존) · gate=관문만 팔(β1: 스캔일 D 고가 "
                         "돌파, **동점이면 진입 없음**). 2.5단계 대조군.")
    ap.add_argument("--gate-tie", choices=["strict", "ge"], default="strict",
                    help="관문만 팔의 동점 규칙. strict=동점 진입 없음(16번 β1 짝 · 헤드라인) "
                         "· ge=동점에도 진입(패턴 팔과 규칙 일치 · 항상 보고하는 민감도). "
                         "🚨 둘 다 무조건 돌린다 — 결과를 보고 고르지 않는다.")
    ap.add_argument("--emit-paths", action="store_true",
                    help="방아쇠가 당겨진 «전수»의 일별 경로를 산출물에 함께 넣는다"
                         "(38번 오프라인 청산 변형용). `open_until` 에 막힌 것도 포함.")
    ap.add_argument("--include-forming", action="store_true",
                    help="예의주시(forming) 단계 종목도 피벗 도달 시 매수 대상에 포함")
    a = ap.parse_args()
    global GATE_NEAR_ALLOW, ENTRY_STATUSES, SERIES_SOURCE, TARGET_PCT, STOP_PCT
    SERIES_SOURCE = a.series
    TARGET_PCT, STOP_PCT = a.target, a.stop
    global MARKET, US_VARIANT, US_USD_KRW, US_LIMIT, ARM, GATE_TIE, EMIT_PATHS
    ARM, GATE_TIE = a.arm, a.gate_tie
    EMIT_PATHS = True if a.emit_paths else None
    MARKET, US_VARIANT = a.market, a.us_variant
    US_USD_KRW, US_LIMIT = a.usd_krw, (a.us_limit or None)
    GATE_NEAR_ALLOW = {"off": set(), "ma": {"1", "5"}, "ma+high": {"1", "5", "7"}}[a.gate_near]
    if a.include_forming:
        ENTRY_STATUSES = {"actionable", "forming"}
    print(f"설정: 팔={ARM}"
          + (f"(동점={GATE_TIE})" if ARM == "gate" else "")
          + f" · 관문임박={a.gate_near} · 진입상태={sorted(ENTRY_STATUSES)}", flush=True)
    res = run(a.start, a.end, a.step)
    res["params"]["gate_near"] = a.gate_near
    res["params"]["entry_statuses"] = sorted(ENTRY_STATUSES)
    res["params"]["series_source"] = SERIES_SOURCE
    res["params"]["arm"] = ARM
    res["params"]["gate_tie"] = GATE_TIE
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    s = res["summary"]
    print(f"\n💾 저장: {a.out}")
    print(f"거래 {s['n']}건 · 승 {s['win']} 패 {s['loss']} 예외 {s['ambiguous']} 미결 {s['unresolved']}")
    print(f"승률 결착 {s['win_rate_resolved']}% (최악 {s['win_rate_worst']}% ~ 최선 {s['win_rate_best']}%)")
    print("\n[변동성 구간별]")
    for k, v in res["by_atr_band"].items():
        print(f"  {k:<14} n={v['n']:>4}  승 {v['win']:>3} 패 {v['loss']:>3} 예외 {v['ambiguous']:>3} 미결 {v['unresolved']:>3}"
              f"  결착승률 {v['win_rate_resolved']}%  (최악 {v['win_rate_worst']}%)")


if __name__ == "__main__":
    main()

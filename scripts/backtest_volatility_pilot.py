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
REF = "005930"                # 거래일 달력 기준

# 제외 패턴 — pykrx_universe.EXCLUDE_PATTERN 과 동일(스팩·리츠·ETF·ETN·인프라·우선주)
EXCLUDE_PATTERN = re.compile(
    r"스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|\d우$|우$|우\(전환\)|우B\(전환\)")


# ── pdata: 시점 유니버스 + 원본 거래대금 ────────────────────────────────────

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


# ── 패턴: entry_ready(검출 AND 진입임박)만 ──────────────────────────────────

def detect_entry_ready(st: dict, pname: str):
    """패턴이 **검출**되고 status=='actionable' 이면 피벗, 아니면 None.

    기존 백테스트는 status 만 봤는데, status 는 패턴 성립과 무관하게 가격 위치로 붙는
    라벨이라 미검출 종목까지 셌다(실측 약 3배). 여기서는 검출 플래그를 함께 요구한다.
    돌파(breakout)는 제외 — 이 백테스트는 D 시점 미돌파분을 익일 돌파 시 사는 설계다.
    """
    try:
        r = evaluate_vcp(st) if pname == "VCP" else (
            evaluate_cheat(st, CHEAT_P) if pname == "3C" else evaluate_power_play(st))
    except Exception:
        return None
    detected = r.get("vcp_detected")
    if detected is None:
        detected = r.get("pattern_detected")
    if not detected or r.get("status") != "actionable" or not r.get("pivot_price"):
        return None
    return r["pivot_price"]


def run(start: str, end: str, step: int) -> dict:
    warm = (datetime.strptime(start, "%Y-%m-%d") - timedelta(days=140)).strftime("%Y-%m-%d")
    print(f"pdata 적재 {warm}~{end} …", flush=True)
    universe_by_date, turnover = load_pdata_range(warm, end)
    print(f"  일자 {len(universe_by_date)}일 · 거래대금 시계열 {len(turnover)}종목", flush=True)

    full: dict[str, dict] = {}
    all_codes = {c for day in universe_by_date.values() for c in day}
    for c in all_codes:
        s = ohlcv_matrix.get_series(c)
        if s and s.get("closes"):
            full[c] = s
    print(f"  유니버스 등장 {len(all_codes)}종목 · 시계열 보유 {len(full)}종목", flush=True)

    cal = ohlcv_matrix.get_series(REF)["dates"]
    scan_dates = [d for d in cal if start <= d <= end][::step]
    print(f"스캔일 {len(scan_dates)}개 ({scan_dates[0]}~{scan_dates[-1]}, step {step})", flush=True)

    events, per_date = [], []
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
                             "n_candidates": 0, "n_entered": 0})
            continue

        rs = _compute_rs_for_all([{"code": c, "closes": t["closes"], "ok": True}
                                  for c, t in stD.items()])
        n_cand = n_ent = 0
        for c, t in stD.items():
            rsv = (rs.get(c) or {}).get("rs")
            if not evaluate_trend_template(t["closes"], rs=rsv, rs_min=RS_MIN)["pass"]:
                continue
            for pname in ("VCP", "3C", "PP"):
                pivot = detect_entry_ready(t, pname)
                if pivot is None:
                    continue
                n_cand += 1
                s = full[c]
                if D not in s["dates"]:
                    continue
                ni = s["dates"].index(D) + 1
                if ni >= len(s["dates"]):
                    continue
                hi = s["highs"][ni]
                if hi is None or hi < pivot:
                    continue                      # 익일 미돌파 → 진입 없음
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
                    "pattern": pname, "scan_date": D, "entry_date": edate,
                    "resolve_date": sim.get("resolve_date"), "month": edate[:7],
                    "pivot": round(pivot, 2), "entry_price": round(epx, 2),
                    "gap_up_pct": round((epx / pivot - 1) * 100, 2), "rs": rsv,
                    "atr_pct": round(v, 2) if v is not None else None,
                    "atr_band": atr_band(v),
                    "turnover_eok": round(avg_turnover_asof(turnover.get(c), D) or 0, 2),
                    REL_VOL_FIELD: rel_volume(s, ni),
                    "price_bucket": price_bucket(epx),
                    "result": sim["result"], "days_held": sim.get("days_held"),
                    "max_gain_pct": sim.get("max_gain_pct"),
                    "max_dd_pct": sim.get("max_dd_pct"),
                    "gain_at_resolve_pct": sim.get("gain_at_resolve_pct"),
                })
        per_date.append({"scan_date": D, "n_universe": len(day_univ), "n_eval": len(stD),
                         "n_candidates": n_cand, "n_entered": n_ent})
        print(f"  {D}: 평가 {len(stD)} · 후보 {n_cand} · 진입 {n_ent} (누적 {len(events)})", flush=True)

    return {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "params": {
            "method": "volatility_pilot_nextday_entry",
            "entry_fill": "max(피벗, 익일 시가) — 갭업 보정",
            "start": start, "end": end, "step": step,
            "target_pct": TARGET_PCT, "stop_pct": STOP_PCT, "rs_min": RS_MIN,
            "candidate_gate": "detected AND actionable (entry_ready)",
            "universe": "pdata point-in-time (상장폐지 포함)",
            "turnover": "pdata 원본 trPrc_eok 50일 평균 (수정주가 룩어헤드 제거)",
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
    }


def main():
    ap = argparse.ArgumentParser(description="변동성 파일럿 백테스트")
    ap.add_argument("--start", default="2025-11-26")
    ap.add_argument("--end", default="2026-08-21")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--out", default="public/data/backtest-volatility-pilot.json")
    a = ap.parse_args()
    res = run(a.start, a.end, a.step)
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

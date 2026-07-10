"""봇 리플레이 — 과거 특정일 분봉을 봇 판정 로직에 흘려 매수·매도를 재현.
순수 핵심(replay_day_minutes·resolve_forward_daily)은 합성 입력으로 테스트 가능."""
from __future__ import annotations

from canslim_lib import strategy_params as SP


def _elapsed_frac(t: str) -> float:
    """t='HHMMSS' → 09:00~15:30(6.5h) 경과 비율(1e-6~1.0)."""
    s = int(t[:2]) * 3600 + int(t[2:4]) * 60 + int(t[4:6]) - 9 * 3600
    return max(1e-6, min(1.0, s / (6.5 * 3600)))


def replay_day_minutes(minutes_by_code, candidates, avg50_by_code, cfg, vol_frac_fn=None):
    """D일 분봉을 분 단위로 흘려 봇 판정. 반환 (events, open_positions).
    매수=분 종가로 evaluate_entry, 청산=evaluate_exit(분 고/저 터치, 손절 우선). 신규매수는 매수창만.
    같은 코드는 하루 한 번만 매수(손절 후 재발화 방지 — 실봇의 traded_today와 동일).
    vol_frac_fn(t)=평소 이 시각 거래량비(동시간대-대비). None이면 선형 경과시간(테스트 기본);
    실제 리플레이 run()은 vol_curve.expected_vol_frac 주입(실봇과 동일 정규화)."""
    from autobuy.signals import evaluate_entry, evaluate_exit
    if vol_frac_fn is None:
        vol_frac_fn = _elapsed_frac
    bar_at = {c["code"]: {b["t"]: b for b in minutes_by_code.get(c["code"], [])} for c in candidates}
    all_t = sorted({b["t"] for m in minutes_by_code.values() for b in m})
    cumvol = {c["code"]: 0.0 for c in candidates}
    held, skip, traded_today, events = {}, set(), set(), []
    for t in all_t:
        ef, hm = vol_frac_fn(t), t[:4]
        for c in candidates:                         # 누적거래량(모든 후보, 매 분)
            b = bar_at[c["code"]].get(t)
            if b:
                cumvol[c["code"]] += b["v"]
        for code in list(held):                      # 청산(보유) — 분 고/저, 손절 우선
            b = bar_at[code].get(t)
            if not b:
                continue
            ep = held[code]["entry_price"]
            sell_lo, r_lo = evaluate_exit(b["l"], ep, target_pct=cfg["TARGET_PCT"], stop_pct=cfg["STOP_PCT"])
            sell_hi, r_hi = evaluate_exit(b["h"], ep, target_pct=cfg["TARGET_PCT"], stop_pct=cfg["STOP_PCT"])
            if sell_lo and r_lo == "손절":
                events.append({"t": t, "code": code, "name": held[code]["name"],
                               "action": "sell", "reason": "손절", "price": round(ep * (1 - cfg["STOP_PCT"] / 100), 2)})
                del held[code]
            elif sell_hi and r_hi == "익절":
                events.append({"t": t, "code": code, "name": held[code]["name"],
                               "action": "sell", "reason": "익절", "price": round(ep * (1 + cfg["TARGET_PCT"] / 100), 2)})
                del held[code]
        if not (cfg["MARKET_OPEN"] <= hm <= cfg["NEW_BUY_UNTIL"]):
            continue
        fire = []                                    # 신규매수 판정
        for c in candidates:
            code = c["code"]
            if code in held or code in skip or code in traded_today:
                continue
            b = bar_at[code].get(t)
            if not b:
                continue
            price = b["c"]
            av = avg50_by_code.get(code, 0)
            ok, why = evaluate_entry(price, c["pivot"], cumvol[code], av, ef,
                                     slots_used=len(held), slots_max=cfg["SLOTS"], held=False,
                                     vol_pace_min=cfg["VOL_PACE_MIN"], chase_max_pct=cfg["CHASE_MAX_PCT"])
            if why == "extended":
                skip.add(code)
            if ok:
                fire.append((cumvol[code] / (av * ef), c, price))
        for pace, c, price in sorted(fire, key=lambda x: -x[0]):
            if len(held) >= cfg["SLOTS"]:
                break
            held[c["code"]] = {"entry_price": price, "name": c["name"]}
            traded_today.add(c["code"])
            events.append({"t": t, "code": c["code"], "name": c["name"],
                           "action": "buy", "price": price, "pace": round(pace, 1)})
    return events, held


def build_candidates_asof(asof, get_series, meta, rs_min=80):
    """asof 마지막 날 status=actionable + 트렌드 통과(RS≥rs_min) 후보. meta: {code: {name,...}}."""
    from canslim_lib.trend_template import evaluate_trend_template
    from canslim_lib.pivot_backtest import truncate_series
    from canslim_lib.vcp import evaluate_vcp
    from canslim_lib.cheat import evaluate_cheat, DEFAULT_PARAMS as CH
    from canslim_lib.power_play import evaluate_power_play
    from screen_trend_template import _compute_rs_for_all
    stD = {}
    for code in meta:
        s = get_series(code)
        if not s or not s.get("closes"):
            continue
        t = truncate_series(s, asof)
        if len(t["closes"]) >= 200:
            stD[code] = t
    rs = _compute_rs_for_all([{"code": c, "closes": t["closes"], "ok": True} for c, t in stD.items()])
    def _act(t, pname):
        try:
            r = evaluate_vcp(t) if pname == "VCP" else evaluate_cheat(t, CH) if pname == "3C" else evaluate_power_play(t)
        except Exception:
            return None
        return r["pivot_price"] if r.get("status") == "actionable" and r.get("pivot_price") else None
    out, seen = [], set()
    for code, t in stD.items():
        rsv = (rs.get(code) or {}).get("rs")
        if not evaluate_trend_template(t["closes"], rs=rsv, rs_min=rs_min)["pass"]:
            continue
        for pname in ("VCP", "3C", "PP"):
            pv = _act(t, pname)
            if pv is not None and code not in seen:
                seen.add(code)
                out.append({"code": code, "name": meta[code].get("name", code), "pivot": float(pv), "pattern": pname})
    return out


def resolve_forward_daily(open_positions, series_by_code, entry_date, *, target_pct=SP.TARGET_PCT, stop_pct=SP.STOP_PCT):
    """D 마감까지 미청산 포지션을 D+1부터 일봉 선착으로 결착. 같은날 둘다면 손절 가정."""
    out = []
    for code, pos in open_positions.items():
        ep = pos["entry_price"]
        T, S = ep * (1 + target_pct / 100), ep * (1 - stop_pct / 100)
        s = series_by_code.get(code)
        if not s or entry_date not in (s.get("dates") or []):
            out.append({"code": code, "name": pos["name"], "action": "unresolved", "reason": "no_data"})
            continue
        ds, hi, lo = s["dates"], s["highs"], s["lows"]
        ni, done = ds.index(entry_date), False
        for j in range(ni + 1, len(ds)):
            if lo[j] is not None and lo[j] <= S:
                out.append({"date": ds[j], "code": code, "name": pos["name"],
                            "action": "sell", "reason": "손절", "price": round(S, 2)}); done = True; break
            if hi[j] is not None and hi[j] >= T:
                out.append({"date": ds[j], "code": code, "name": pos["name"],
                            "action": "sell", "reason": "익절", "price": round(T, 2)}); done = True; break
        if not done:
            out.append({"code": code, "name": pos["name"], "action": "unresolved", "reason": "open"})
    return out


def _prev_trading_day(cal, d):
    prior = [x for x in cal if x < d]
    return prior[-1] if prior else None


def run(entry_date, slots=None):
    import os, sys
    from pathlib import Path
    MAIN = Path(r"C:\Users\hanul\playground\my-stock")
    THIS_SCRIPTS = Path(__file__).resolve().parents[1]  # 이 브랜치(worktree)의 scripts/ — autobuy·minute_bars 등 코드 원본
    sys.path.insert(0, str(THIS_SCRIPTS))
    from canslim_lib import ohlcv_matrix, minute_bars
    ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
    from canslim_lib.pykrx_universe import fetch_universe_with_cap
    from canslim_lib.pivot_backtest import truncate_series
    from autobuy.config import CFG
    from autobuy import watchlist, signals
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k, v)
    cfg = dict(CFG)
    if slots:
        cfg["SLOTS"] = slots
    meta = {u["code"]: u for u in fetch_universe_with_cap("ALL")}
    cal = ohlcv_matrix.get_series("005930")["dates"]
    scan = _prev_trading_day([d for d in cal if d <= entry_date], entry_date)
    print(f"=== 봇 리플레이 · 진입일 {entry_date} (스캔 {scan}) ===")
    # 국면 게이트(스캔일 기준)
    codes_all = [p.stem for p in (MAIN / ".cache" / "ohlcv" / "series").glob("*.json")]
    idx_full = watchlist.build_ew_index(ohlcv_matrix.get_series, codes_all)
    # scan 시점까지로 자른 지수로 판정
    scan_i = cal.index(scan) if scan in cal else len(idx_full) - 1
    if not signals.is_uptrend(idx_full[:scan_i + 1], 20):
        print(f"국면=하락추세(스캔일 지수<20MA) → 그날 봇은 매매 OFF."); return
    print("국면=상승추세 → 가동")
    cands = build_candidates_asof(scan, ohlcv_matrix.get_series, meta)
    print(f"감시목록 {len(cands)}종목 · 분봉 수집 중…")
    minutes, avg50 = {}, {}
    for c in cands:
        m = minute_bars.fetch_day_minutes(c["code"], entry_date)
        if m:
            minutes[c["code"]] = m
        s = ohlcv_matrix.get_series(c["code"])
        vs = [v for v in (truncate_series(s, scan).get("volumes") or [])[-50:] if v] if s else []
        avg50[c["code"]] = (sum(vs) / len(vs)) if vs else 0
    live = [c for c in cands if c["code"] in minutes]
    from autobuy import vol_curve
    events, held = replay_day_minutes(minutes, live, avg50, cfg,
                                      vol_frac_fn=vol_curve.expected_vol_frac)
    fwd = resolve_forward_daily(held, {code: ohlcv_matrix.get_series(code) for code in held}, entry_date)
    # 로그 출력(봇 형식)
    for e in sorted([x for x in events], key=lambda x: x["t"]):
        tt = f"{e['t'][:2]}:{e['t'][2:4]}"
        if e["action"] == "buy":
            print(f"{tt} 매수 {e['code']} {e['name']} @{e['price']} pace{e['pace']}")
        else:
            print(f"{tt} 매도 {e['code']} {e['reason']} @{e['price']}")
    for e in fwd:
        if e["action"] == "sell":
            print(f"{e['date']} 매도 {e['code']} {e['name']} {e['reason']} @{e['price']} (이후 일봉 결착)")
        else:
            print(f"       미청산 {e['code']} {e['name']} ({e['reason']})")
    n_buy = sum(1 for e in events if e["action"] == "buy")
    win = sum(1 for e in events if e.get("reason") == "익절") + sum(1 for e in fwd if e.get("reason") == "익절")
    loss = sum(1 for e in events if e.get("reason") == "손절") + sum(1 for e in fwd if e.get("reason") == "손절")
    unres = sum(1 for e in fwd if e["action"] == "unresolved")
    pnl = win * cfg["TARGET_PCT"] - loss * cfg["STOP_PCT"]
    print(f"\n요약: 매수 {n_buy} · 익절 {win} · 손절 {loss} · 미청산 {unres} · 합산손익 {pnl:+.0f}%p (익절+{cfg['TARGET_PCT']:.0f}/손절-{cfg['STOP_PCT']:.0f})")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="진입일 YYYY-MM-DD")
    ap.add_argument("--slots", type=int, default=None)
    a = ap.parse_args()
    run(a.date, a.slots)


if __name__ == "__main__":
    main()

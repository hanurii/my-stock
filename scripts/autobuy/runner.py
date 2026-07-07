"""장중 자동매수 봇 러너 — 조립만. 판정은 signals, 주문은 kis_trade, 상태는 state.
실행: python -X utf8 scripts/autobuy/runner.py            # dryrun(기본)
      python -X utf8 scripts/autobuy/runner.py --live      # 실주문(명시)
"""
from __future__ import annotations
import argparse, os, sys, time, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # scripts/
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from autobuy.config import CFG, CANDIDATE_PATHS, BASE
from autobuy import signals, state, kis_trade, watchlist
sys.path.insert(0, str(BASE / "scripts"))
from canslim_lib import ohlcv_matrix, kis_api
ohlcv_matrix.SERIES_DIR = BASE / ".cache" / "ohlcv" / "series"
# .env 로드(주 작업트리)
for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k, v)


def _elapsed_frac(now: datetime.datetime) -> float:
    op = now.replace(hour=9, minute=0, second=0, microsecond=0)
    total = 6.5 * 3600
    return max(1e-6, min(1.0, (now - op).total_seconds() / total))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="실주문(미지정 시 dryrun)")
    args = ap.parse_args()
    # ★ live 이중게이트 — 실행인자(--live) AND 설정(CFG["MODE"]=="live") 둘 다 있어야 live.
    #   둘 중 하나만 있으면 안전 측(dryrun)으로 떨어진다.
    mode = "live" if (args.live and CFG["MODE"] == "live") else "dryrun"
    state.log(f"=== 자동매수 봇 시작 mode={mode} slots={CFG['SLOTS']} ===")

    if mode == "live":
        missing = [k for k in ("KIS_ACCOUNT", "KIS_APP_KEY", "KIS_APP_SECRET") if not os.environ.get(k)]
        if missing:
            state.log(f"live 모드 필수 환경변수 누락: {missing} → 시작 중단"); return

    # 국면 게이트
    codes_all = [p.stem for p in (BASE / ".cache" / "ohlcv" / "series").glob("*.json")]
    if CFG["REGIME_FILTER"]:
        idx = watchlist.build_ew_index(ohlcv_matrix.get_series, codes_all)
        if not signals.is_uptrend(idx, 20):
            state.log("국면=하락추세(지수<20MA) → 오늘 매매 OFF. 종료."); return
        state.log("국면=상승추세 → 가동")

    wl = watchlist.load_actionable(CANDIDATE_PATHS)
    avg50 = {}
    for c in wl:
        s = ohlcv_matrix.get_series(c["code"])
        vols = [v for v in (s.get("volumes") or [])[-50:] if v] if s else []
        avg50[c["code"]] = (sum(vols) / len(vols)) if vols else 0
    state.log(f"감시목록 {len(wl)}종목")

    positions = {p["code"]: p for p in state.load()}

    # ★ FIX4 — 잔고 대조: 봇 상태에 없는 실보유종목을 편입(진입가=평단가)해 손절/목표 감시 대상에 포함.
    #   조회 실패(빈 리스트)는 아무 것도 안 바꾼다 — 절대 기존 포지션을 지우지 않는다(추가만).
    try:
        holdings = kis_trade.inquire_holdings()
    except Exception as e:
        state.log(f"잔고 조회 예외: {type(e).__name__} — 기존 포지션 유지"); holdings = []
    adopted = False
    for h in holdings or []:
        code = h.get("code")
        if code and code not in positions:
            positions[code] = {"code": code, "entry_price": h.get("avg_price")}
            state.log(f"잔고 대조: 미기록 보유종목 편입 {code} @{h.get('avg_price')}")
            adopted = True
    if adopted:
        state.save(list(positions.values()))

    today_str = datetime.datetime.now().strftime("%Y%m%d")
    traded_today = state.load_traded_today(today_str)   # ★ FIX3 — 재시작해도 남는 당일 매수이력(중복 재매수 방지)

    skip = set()   # 추격 초과 등 그날 영구 스킵
    kill_logged = False
    while True:
        killed = state.kill_switch_on()   # ★ FIX5 — KILL 은 신규매수만 막고 청산 감시는 계속
        if killed and not kill_logged:
            state.log("KILL 스위치 감지 → 신규매수 중단(청산 감시는 계속)"); kill_logged = True
        now = datetime.datetime.now(); hm = now.strftime("%H%M")
        if hm >= CFG["MARKET_CLOSE"]:
            state.log("장마감 → 종료"); break
        ef = _elapsed_frac(now)
        # 청산 감시(보유) — killed 여부와 무관하게 항상 수행
        for code, pos in list(positions.items()):
            try:
                q = kis_api.fetch_quote_with_volume(code)
                if not q: continue
                sell, why = signals.evaluate_exit(q["current"], pos["entry_price"],
                                                  target_pct=CFG["TARGET_PCT"], stop_pct=CFG["STOP_PCT"])
                if sell:
                    r = kis_trade.place_sell_1share(code, mode=mode)
                    state.log(f"매도 {code} {why} @{q['current']} → {r.get('ok')}")
                    if r.get("ok"):
                        # ★ FIX1 — 매도 성공 시에만 포지션 제거. 실패하면 유지 → 다음 폴링에서 재시도(손절 유지).
                        positions.pop(code, None); state.save(list(positions.values()))
            except Exception as e:
                state.log(f"청산감시 예외 {code}: {type(e).__name__} — 계속 진행")
        # 신규 매수(신호 초과 시 pace 높은 순) — killed 면 스킵
        if not killed and hm < CFG["NEW_BUY_UNTIL"] and hm >= CFG["MARKET_OPEN"]:
            cands = []
            for c in wl:
                if c["code"] in positions or c["code"] in skip or c["code"] in traded_today: continue
                try:
                    q = kis_api.fetch_quote_with_volume(c["code"])
                    if not q: continue
                    ok, why = signals.evaluate_entry(
                        q["current"], c["pivot"], q["acml_vol"], avg50[c["code"]], ef,
                        slots_used=len(positions), slots_max=CFG["SLOTS"], held=False,
                        vol_pace_min=CFG["VOL_PACE_MIN"], chase_max_pct=CFG["CHASE_MAX_PCT"])
                    if why == "extended": skip.add(c["code"])
                    if ok:
                        pace = q["acml_vol"] / (avg50[c["code"]] * ef)
                        cands.append((pace, c, q))
                except Exception as e:
                    state.log(f"신규매수 판정 예외 {c['code']}: {type(e).__name__} — 계속 진행")
            for pace, c, q in sorted(cands, key=lambda x: -x[0]):
                if len(positions) >= CFG["SLOTS"]: break
                try:
                    r = kis_trade.place_buy_1share(c["code"], mode=mode)
                except Exception as e:
                    state.log(f"매수주문 예외 {c['code']}: {type(e).__name__} — 계속 진행"); continue
                if r.get("ok"):
                    positions[c["code"]] = {"code": c["code"], "entry_price": q["current"]}
                    state.save(list(positions.values()))
                    traded_today.add(c["code"])
                    state.add_traded_today(c["code"], today_str)
                    state.log(f"매수 {c['code']} {c['name']} @{q['current']} pace{pace:.1f} → {mode}")
        time.sleep(CFG["POLL_SEC"])
    state.log("=== 종료 ===")


if __name__ == "__main__":
    main()

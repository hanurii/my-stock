"""거래량 매수 실시간 검증 관찰기 — 실전 봇 판정(evaluate_entry)을 그대로 재사용해
감시 후보를 실시간 판정하고 후보별 사유를 출력. 읽기 전용(주문 없음, kis_trade 미import).
순수 핵심 observe_sweep/_fmt_block은 합성 입력으로 테스트 가능."""
from __future__ import annotations


def _elapsed_frac(now) -> float:
    """datetime now → 09:00~15:30(6.5h) 경과 비율. 실전 runner._elapsed_frac과 동일식."""
    op = now.replace(hour=9, minute=0, second=0, microsecond=0)
    return max(1e-6, min(1.0, (now - op).total_seconds() / (6.5 * 3600)))


def _in_buy_window(hm, cfg):
    """실전 runner와 동일: MARKET_OPEN <= hm < NEW_BUY_UNTIL (상한 배타)."""
    return cfg["MARKET_OPEN"] <= hm < cfg["NEW_BUY_UNTIL"]


def observe_sweep(quotes_by_code, candidates, avg50_by_code, held_sim, skip, cfg,
                  vol_frac, in_buy_window=True):
    """한 사이클 후보 판정. 실제 매수 여부는 signals.evaluate_entry 재사용.
    vol_frac = 평소 이 시각까지 거래량 비율(동시간대-대비 정규화, autobuy.vol_curve). 선형 경과시간 아님.
    반환 (rows, buys). held_sim·skip는 제자리 갱신. 슬롯 상한 cfg['SLOTS'].
    in_buy_window=False면 판정·표시는 하되 매수 커밋(held 편입) 안 함(실전 봇 매수창 밖)."""
    from autobuy.signals import evaluate_entry
    rows, fire = [], []
    slots_used = len(held_sim)   # 실전 러너처럼 스윕 시작 시점 슬롯수로 판정, 커밋 때 상한 재확인
    for c in candidates:
        code, pivot, name = c["code"], c["pivot"], c["name"]
        q = quotes_by_code.get(code)
        if not q:
            rows.append({"code": code, "name": name, "price": None, "pivot": pivot,
                         "pct": None, "pace": None, "why": "no_quote"})
            continue
        price, acml, av = q["current"], q["acml_vol"], avg50_by_code.get(code, 0)
        pace = acml / (av * vol_frac) if (av > 0 and vol_frac > 0) else 0.0
        pct = (price / pivot - 1) * 100 if pivot else None
        held = code in held_sim
        # 그날 스킵(extended)은 sticky — 가격 돌아와도 계속 스킵
        if code in skip and not held:
            rows.append({"code": code, "name": name, "price": price, "pivot": pivot,
                         "pct": pct, "pace": pace, "why": "extended"})
            continue
        ok, why = evaluate_entry(price, pivot, acml, av, vol_frac,
                                 slots_used=slots_used, slots_max=cfg["SLOTS"], held=held,
                                 vol_pace_min=cfg["VOL_PACE_MIN"], chase_max_pct=cfg["CHASE_MAX_PCT"])
        if why == "extended":
            skip.add(code)
        rows.append({"code": code, "name": name, "price": price, "pivot": pivot,
                     "pct": pct, "pace": pace, "why": ("already_held" if held else why)})
        if ok and in_buy_window and not held:
            fire.append((pace, c, price))
    buys = []
    row_by_code = {r["code"]: r for r in rows}
    for pace, c, price in sorted(fire, key=lambda x: -x[0]):
        if len(held_sim) >= cfg["SLOTS"]:
            row_by_code[c["code"]]["why"] = "no_slot"
        else:
            held_sim.add(c["code"])
            buys.append({"code": c["code"], "name": c["name"], "price": price, "pace": round(pace, 1)})
            row_by_code[c["code"]]["why"] = "buy"
    return rows, buys


def _fmt_block(now_str, vol_frac, held_count, slots_max, cand_count,
               regime_note, rows, buys, in_buy_window, pace_min_show=0.8):
    """한 사이클 출력 블록 문자열. pace≥pace_min_show인 것만 표시하고,
    이미 익스텐디드(추격불가)인 종목은 별도 섹션으로 분류. 각 섹션 pace 내림차순.
    pace<문턱·조회실패는 개수만 요약(불필요한 나열 제거)."""
    win = "" if in_buy_window else "  [매수창 밖 — 신규매수 안 함]"
    lines = [f"=== {now_str} (평소 이 시각 거래량 {vol_frac*100:.0f}%) · 슬롯 {held_count}/{slots_max} · "
             f"감시 {cand_count}종목{win} ==="]
    lines.append(f"[국면 참고: {regime_note} — 게이트 아님(관찰만)]")
    if buys:
        tag = " · ".join(f"{b['code']} {b['name']} @{b['price']} pace{b['pace']}" for b in buys)
        lines.append(f"★매수 발생({len(buys)}): {tag}")

    def _row(r):
        mark = "★" if r["why"] == "buy" else ("▷" if r["why"] == "already_held" else "✗")
        return (f"{r['code']} {r['name']}  {r['price']} / {r['pivot']}  "
                f"{r['pct']:+.1f}%  pace{r['pace']:.1f}  {mark} {r['why']}")

    shown = [r for r in rows if r["price"] is not None and (r["pace"] or 0) >= pace_min_show]
    hidden = len(rows) - len(shown)
    ext = sorted((r for r in shown if r["why"] == "extended"), key=lambda x: -(x["pace"] or 0))
    main = sorted((r for r in shown if r["why"] != "extended"), key=lambda x: -(x["pace"] or 0))

    lines.append(f"--- 후보별 판정 (pace≥{pace_min_show}, {len(main)}종목) ---")
    lines += [_row(r) for r in main]
    if ext:
        lines.append(f"--- 이미 익스텐디드 (추격불가, {len(ext)}종목) ---")
        lines += [_row(r) for r in ext]
    if hidden:
        lines.append(f"(pace<{pace_min_show}·조회실패 {hidden}종목 숨김)")
    return "\n".join(lines)


def _load_env(base):
    import os
    for line in (base / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k, v)


def _regime_note(base, ohlcv_matrix, watchlist, signals):
    """국면 참고 문자열(게이트 아님). 등가중 지수 최신값 vs 20MA."""
    codes = [p.stem for p in (base / ".cache" / "ohlcv" / "series").glob("*.json")]
    idx = watchlist.build_ew_index(ohlcv_matrix.get_series, codes)
    up = signals.is_uptrend(idx, 20)
    return "상승추세(지수≥20MA)" if up else "하락추세(지수<20MA)"


def run(once=False, slots=None, interval=0, broad=False):
    import sys, time, datetime
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # scripts/
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from autobuy.config import CFG, CANDIDATE_PATHS, BASE
    from autobuy import signals, watchlist, vol_curve
    sys.path.insert(0, str(BASE / "scripts"))
    from canslim_lib import ohlcv_matrix, kis_api
    ohlcv_matrix.SERIES_DIR = BASE / ".cache" / "ohlcv" / "series"
    _load_env(BASE)

    cfg = dict(CFG)
    if slots is not None:
        cfg["SLOTS"] = slots

    run_dir = Path(__file__).resolve().parent / "_run"
    run_dir.mkdir(exist_ok=True)
    log_path = run_dir / f"verify_volume_{datetime.datetime.now():%Y%m%d}.log"

    def _logline(s):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(s + "\n")

    wl = (watchlist.load_watchlist_broad(CANDIDATE_PATHS) if broad
          else watchlist.load_actionable(CANDIDATE_PATHS))
    avg50 = {}
    for c in wl:
        s = ohlcv_matrix.get_series(c["code"])
        vols = [v for v in (s.get("volumes") or [])[-50:] if v] if s else []
        avg50[c["code"]] = (sum(vols) / len(vols)) if vols else 0
    note = _regime_note(BASE, ohlcv_matrix, watchlist, signals)
    mode_tag = "넓은 감시(진입임박+예의주시)" if broad else "진입임박만"
    print(f"=== 거래량 매수 검증 관찰기 · {mode_tag} · 감시 {len(wl)}종목 · 슬롯 {cfg['SLOTS']} · 국면 {note} ===")
    print("(읽기 전용 — 실주문 없음. 국면은 게이트 아니라 참고만)")

    held_sim, skip = set(), set()
    while True:
        now = datetime.datetime.now(); hm = now.strftime("%H%M")
        if hm >= cfg["MARKET_CLOSE"] and not once:
            print("장마감 → 종료"); break
        vf = vol_curve.expected_vol_frac(now.strftime("%H%M%S"))   # 동시간대-대비(선형 경과시간 아님)
        in_win = _in_buy_window(hm, cfg)
        quotes = {}
        for c in wl:
            if c["code"] in held_sim:
                continue                       # 이미 시뮬 보유 → 조회 아껴 already_held로 표시만
            try:
                q = kis_api.fetch_quote_with_volume(c["code"])
                if q:
                    quotes[c["code"]] = q
            except Exception as e:
                print(f"  조회 예외 {c['code']}: {type(e).__name__} — 계속", flush=True)
                continue
        # held_sim 종목도 already_held 행이 나오도록 최소 시세는 있으면 좋지만, 조회 절감 위해 생략 →
        # observe_sweep이 no_quote로 처리. held는 관찰 관심 밖이라 무방(매수 판정 검증이 목적).
        rows, buys = observe_sweep(quotes, [c for c in wl if c["code"] not in held_sim],
                                   avg50, held_sim, skip, cfg, vf, in_buy_window=in_win)
        block = _fmt_block(now.strftime("%H:%M:%S"), vf, len(held_sim), cfg["SLOTS"],
                           len(wl), note, rows, buys, in_win)
        print("\n" + block, flush=True)
        for b in buys:
            _logline(f"{now:%H:%M:%S} ★매수 {b['code']} {b['name']} @{b['price']} pace{b['pace']}")
        if once:
            break
        if interval:
            time.sleep(interval)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="거래량 매수 실시간 검증 관찰기(읽기 전용)")
    ap.add_argument("--once", action="store_true", help="한 번만 스윕하고 종료")
    ap.add_argument("--slots", type=int, default=None, help="슬롯 상한 override")
    ap.add_argument("--interval", type=int, default=0, help="스윕 사이 최소 대기(초)")
    ap.add_argument("--broad", action="store_true", help="예의주시까지 넓게 감시(기본: 진입임박만)")
    a = ap.parse_args()
    run(once=a.once, slots=a.slots, interval=a.interval, broad=a.broad)


if __name__ == "__main__":
    main()

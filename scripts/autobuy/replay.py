"""봇 리플레이 — 과거 특정일 분봉을 봇 판정 로직에 흘려 매수·매도를 재현.
순수 핵심(replay_day_minutes·resolve_forward_daily)은 합성 입력으로 테스트 가능."""
from __future__ import annotations


def _elapsed_frac(t: str) -> float:
    """t='HHMMSS' → 09:00~15:30(6.5h) 경과 비율(1e-6~1.0)."""
    s = int(t[:2]) * 3600 + int(t[2:4]) * 60 + int(t[4:6]) - 9 * 3600
    return max(1e-6, min(1.0, s / (6.5 * 3600)))


def replay_day_minutes(minutes_by_code, candidates, avg50_by_code, cfg):
    """D일 분봉을 분 단위로 흘려 봇 판정. 반환 (events, open_positions).
    매수=분 종가로 evaluate_entry, 청산=분 고/저 터치(손절 우선). 신규매수는 매수창만."""
    from autobuy.signals import evaluate_entry
    bar_at = {c["code"]: {b["t"]: b for b in minutes_by_code.get(c["code"], [])} for c in candidates}
    all_t = sorted({b["t"] for m in minutes_by_code.values() for b in m})
    cumvol = {c["code"]: 0.0 for c in candidates}
    held, skip, events = {}, set(), []
    for t in all_t:
        ef, hm = _elapsed_frac(t), t[:4]
        for c in candidates:                         # 누적거래량(모든 후보, 매 분)
            b = bar_at[c["code"]].get(t)
            if b:
                cumvol[c["code"]] += b["v"]
        for code in list(held):                      # 청산(보유) — 분 고/저, 손절 우선
            b = bar_at[code].get(t)
            if not b:
                continue
            ep = held[code]["entry_price"]
            if b["l"] <= ep * (1 - cfg["STOP_PCT"] / 100):
                events.append({"t": t, "code": code, "name": held[code]["name"],
                               "action": "sell", "reason": "손절", "price": round(ep * (1 - cfg["STOP_PCT"] / 100), 2)})
                del held[code]
            elif b["h"] >= ep * (1 + cfg["TARGET_PCT"] / 100):
                events.append({"t": t, "code": code, "name": held[code]["name"],
                               "action": "sell", "reason": "익절", "price": round(ep * (1 + cfg["TARGET_PCT"] / 100), 2)})
                del held[code]
        if not (cfg["MARKET_OPEN"] <= hm <= cfg["NEW_BUY_UNTIL"]):
            continue
        fire = []                                    # 신규매수 판정
        for c in candidates:
            code = c["code"]
            if code in held or code in skip:
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
            events.append({"t": t, "code": c["code"], "name": c["name"],
                           "action": "buy", "price": price, "pace": round(pace, 1)})
    return events, held

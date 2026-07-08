"""거래량 매수 실시간 검증 관찰기 — 실전 봇 판정(evaluate_entry)을 그대로 재사용해
감시 후보를 실시간 판정하고 후보별 사유를 출력. 읽기 전용(주문 없음, kis_trade 미import).
순수 핵심 observe_sweep/_fmt_block은 합성 입력으로 테스트 가능."""
from __future__ import annotations


def _elapsed_frac(now) -> float:
    """datetime now → 09:00~15:30(6.5h) 경과 비율. 실전 runner._elapsed_frac과 동일식."""
    op = now.replace(hour=9, minute=0, second=0, microsecond=0)
    return max(1e-6, min(1.0, (now - op).total_seconds() / (6.5 * 3600)))


def observe_sweep(quotes_by_code, candidates, avg50_by_code, held_sim, skip, cfg,
                  elapsed_frac, in_buy_window=True):
    """한 사이클 후보 판정. 실제 매수 여부는 signals.evaluate_entry 재사용.
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
        pace = acml / (av * elapsed_frac) if (av > 0 and elapsed_frac > 0) else 0.0
        pct = (price / pivot - 1) * 100 if pivot else None
        held = code in held_sim
        # 그날 스킵(extended)은 sticky — 가격 돌아와도 계속 스킵
        if code in skip and not held:
            rows.append({"code": code, "name": name, "price": price, "pivot": pivot,
                         "pct": pct, "pace": pace, "why": "extended"})
            continue
        ok, why = evaluate_entry(price, pivot, acml, av, elapsed_frac,
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

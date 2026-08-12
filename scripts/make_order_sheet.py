"""내일 아침 조건주문표 — HTS 자동감시주문에 그대로 입력하는 실행 시트. **온디맨드 도구.**

⚠️ 정기 파이프라인(/sepa) 단계 아님: 사용자가 상황별 직접 판단을 선호해 페이지 섹션과
정기 산출에서 제외됨(26-08-12). 조건주문 예약이 필요할 때만 수동 실행 — 콘솔 표가 정본,
출력 JSON 은 커밋하지 않는다(페이지가 읽지 않음).

배경: 직장인은 장중 돌파를 못 본다. 미너비니식 해법은 화면 감시가 아니라 주문 예약 —
감시가(피벗) 도달 시 "상한(피벗+5%)" 지정가로 발동하는 스탑리밋 조건주문. 상한이
지정가라서 갭업 추격이 기계적으로 차단된다(시장가 발동이면 차단 안 됨 — 반드시 지정가).
다바스 방식. 거래량 검증은 체결일 저녁에 수행, 손절만 시장가.

입력: sepa-{vcp,power-play,power-play-all,3c}-candidates.json (+ sepa-buy-recommendations.json
      의 초수익 점수, sepa-demand-watchlist.json 제외 목록) + OHLCV 캐시(거래대금)
출력: public/data/sepa-order-sheet.json (커밋 금지 — 로컬 확인용)

대상 선정(패턴 후보 상태 기준, 상태 우선순위 dedupe):
  · actionable(진입임박)                → 감시매수: 현재가 ≥ 감시가(피벗) 도달 시 매수
  · forming(예의주시) 중 피벗 -5% 이내  → 감시매수(패턴 완성 순간 예약 — 미리 사는 것 아님)
  · breakout 중 피벗 +5% 이내(매수범위) → 범위내: 상한 이하 지정가 매수 여지
제외(사유와 함께 skipped 기록): 기관수요 유보, 피벗 없음, 예산 대비 1주 미만, 저유동성.

수량: min(기준 포지션 POSITION_KRW, 하루평균 거래대금×5%) ÷ 감시가 — 매수한도 컬럼과 동일 논리.
가격은 KRX 호가단위로 정렬(감시가 올림, 상한 내림). 손절 예정가 -5%는 표시용(체결가 기준 재계산).
"""
from __future__ import annotations
import sys, json, argparse, math
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib import ohlcv_matrix  # noqa: E402
from canslim_lib.strategy_params import POSITION_KRW  # noqa: E402
from screen_buy_recommendations import (  # noqa: E402  (형제 스크립트 로직 재사용)
    PATTERN_FILES, _STATUS_PRI, load_demand_watch, liquidity_fields,
)

DATA = ROOT / "public" / "data"
KST = timezone(timedelta(hours=9))

BUY_RANGE_PCT = 5.0     # 미너비니 매수 유효 범위: 피벗 ~ 피벗+5% (넘으면 추격 금지)
NEAR_PIVOT_PCT = 5.0    # forming 중 피벗까지 이내면 감시주문 예약 대상
ADV_CAP_RATIO = 0.05    # 안전 매수 한도 = 하루평균 거래대금 × 5% (매수한도 컬럼과 동일)
STOP_HINT_PCT = -5.0    # 손절 예정가 표시용 — 수동 매매 기본(sepa-holdings.json stop_loss_pct_default), 체결가 기준 재계산·시장가 집행


def tick_size(price: float) -> int:
    """KRX 호가단위(2023-01 개편, 코스피·코스닥 공통)."""
    if price < 2_000: return 1
    if price < 5_000: return 5
    if price < 20_000: return 10
    if price < 50_000: return 50
    if price < 200_000: return 100
    if price < 500_000: return 500
    return 1_000


def round_up_tick(price: float) -> int:
    t = tick_size(price)
    return int(math.ceil(price / t) * t)


def round_down_tick(price: float) -> int:
    t = tick_size(price)
    return int(math.floor(price / t) * t)


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="내일 아침 조건주문표 산출")
    ap.add_argument("--out", default=str(DATA / "sepa-order-sheet.json"))
    a = ap.parse_args()

    # 초수익 점수는 매수추천 산출물에서 참조(없으면 0점 처리, 비차단)
    scores: dict[str, dict] = {}
    try:
        br = json.loads((DATA / "sepa-buy-recommendations.json").read_text(encoding="utf-8"))
        scores = {r["code"]: r for r in br.get("candidates", [])}
    except Exception:
        pass
    demand_watch = load_demand_watch()

    best: dict[str, dict] = {}
    asof = None
    for fname, pat in PATTERN_FILES:
        p = DATA / fname
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        asof = asof or d.get("asof")
        for c in d.get("candidates", []):
            det = c.get("vcp_detected")
            det = det if det is not None else c.get("pattern_detected")
            if not det:
                continue
            code = c["code"]
            rec = {**c, "pattern": pat}
            prev = best.get(code)
            if prev is None or _STATUS_PRI.get(rec.get("status"), 9) < _STATUS_PRI.get(prev.get("status"), 9):
                if prev is not None:
                    rec["gate_near"] = bool(rec.get("gate_near")) or bool(prev.get("gate_near"))
                best[code] = rec
            elif rec.get("gate_near") and not prev.get("gate_near"):
                prev["gate_near"] = True  # 진 레코드의 관문임박 표시도 승계(buy recs 와 동일 규칙)

    orders, skipped = [], []
    for code, c in best.items():
        name, status = c.get("name"), c.get("status")
        pivot, cur = c.get("pivot_price"), c.get("current_price")
        if status not in ("actionable", "forming", "breakout"):
            continue
        if not pivot or cur is None:
            skipped.append({"code": code, "name": name, "reason": "피벗/현재가 없음"})
            continue
        if code in demand_watch:
            skipped.append({"code": code, "name": name, "reason": "기관수요 유보(매수 보류 목록)"})
            continue

        # pct_to_pivot = (피벗-현재)/피벗 — 양수=피벗 아래, 음수=피벗 위
        below_pct = (pivot - cur) / pivot * 100
        if status == "forming" and not (0 <= below_pct <= NEAR_PIVOT_PCT):
            continue  # 피벗에서 먼 예의주시는 주문 대상 아님(리스트 소음 방지)
        if status == "breakout":
            above_pct = -below_pct
            if not (0 <= above_pct <= BUY_RANGE_PCT):
                skipped.append({"code": code, "name": name,
                                "reason": f"매수범위 이탈(피벗 +{above_pct:.1f}% > +{BUY_RANGE_PCT:.0f}%) — 추격 금지"})
                continue
        if status == "actionable" and below_pct < 0:
            # 진입임박 표시지만 이미 피벗 위(검출 시차) — 범위 검사로 넘김
            if -below_pct > BUY_RANGE_PCT:
                skipped.append({"code": code, "name": name,
                                "reason": f"매수범위 이탈(피벗 +{-below_pct:.1f}%) — 추격 금지"})
                continue

        s = ohlcv_matrix.get_series(code)
        if not s or not s.get("closes"):
            skipped.append({"code": code, "name": name, "reason": "시세 데이터 없음"})
            continue
        liq = liquidity_fields(s)
        adv_eok = liq.get("adv_50d_eok")
        if adv_eok is None:
            skipped.append({"code": code, "name": name, "reason": "거래대금 산출 불가(데이터 부족)"})
            continue
        limit_krw = adv_eok * 1e8 * ADV_CAP_RATIO          # 안전 매수 한도(원)
        budget = min(POSITION_KRW, limit_krw)
        trigger = round_up_tick(pivot)                      # 감시가 = 피벗 이상 첫 호가
        cap = round_down_tick(pivot * (1 + BUY_RANGE_PCT / 100))  # 매수 유효 상한
        # 수량 기준가: 스탑리밋은 체결가≈감시가. 이미 피벗 위(범위내)면 체결가≥현재가이므로
        # 현재가 기준으로 산정 — 예산·거래대금 5% 한도 초과를 막는다(적대 검증 26-08-11 지적).
        fill_basis = trigger if cur <= trigger else round_up_tick(cur)
        qty = int(budget // fill_basis)
        if qty <= 0:
            skipped.append({"code": code, "name": name, "reason": f"예산({budget:,.0f}원) < 1주 가격({fill_basis:,}원)"})
            continue
        if limit_krw < POSITION_KRW * 0.5:
            # 한도가 기준 포지션의 절반 미만이면 저유동성 경고 — 주문은 내되 축소분 명시
            note_liq = f"저유동성 — 매수한도 {limit_krw/1e8:.2f}억으로 수량 축소"
        else:
            note_liq = None

        sc = scores.get(code, {})
        order_type = "범위내 지정가" if (status == "breakout" or below_pct < 0) else "감시매수(스탑)"
        orders.append({
            "code": code, "name": name, "market": c.get("market"),
            "pattern": c.get("pattern"), "status": status,
            "gate_near": bool(c.get("gate_near")),
            "superperf_score": sc.get("superperf_score"),
            "rs": c.get("rs"),
            "current_price": cur, "pivot_price": pivot,
            "order_type": order_type,
            "trigger_price": trigger,          # 감시가(이 가격 도달 시 발동) / 범위내는 즉시 지정가 기준
            "limit_price": cap,                # 매수 유효 상한 — 넘어가면 미체결이 정상(추격 금지)
            "quantity": qty,
            "budget_krw": int(qty * fill_basis),
            "stop_price_hint": round_down_tick(trigger * (1 + STOP_HINT_PCT / 100)),
            "adv_50d_eok": adv_eok,
            "note": note_liq,
        })

    orders.sort(key=lambda o: (-(o["superperf_score"] or 0), abs((o["pivot_price"] - o["current_price"]) / o["pivot_price"])))

    out = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "asof": asof,
        "params": {"position_krw": POSITION_KRW, "buy_range_pct": BUY_RANGE_PCT,
                   "near_pivot_pct": NEAR_PIVOT_PCT, "adv_cap_ratio": ADV_CAP_RATIO},
        "count": len(orders),
        "orders": orders,
        "skipped": skipped,
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"💾 저장: {Path(a.out).name} — 주문 {len(orders)}건 / 제외 {len(skipped)}건 (asof {asof})")
    for o in orders:
        gate = " ⏳관문임박" if o["gate_near"] else ""
        score = f"{o['superperf_score']}점" if o["superperf_score"] is not None else "—"
        print(f"  {o['name']:<12} {o['pattern']:<5} {o['status']:<10} {score:>4} | "
              f"감시 {o['trigger_price']:>8,} 상한 {o['limit_price']:>8,} × {o['quantity']:>6,}주 "
              f"≈ {o['budget_krw']/1e4:>6,.0f}만 | 손절≈{o['stop_price_hint']:,}{gate}"
              + (f" | {o['note']}" if o["note"] else ""))
    for sk in skipped:
        print(f"  (제외) {sk['name']}: {sk['reason']}")


if __name__ == "__main__":
    main()

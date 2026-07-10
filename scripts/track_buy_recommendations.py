"""매수 추천 '살아있는 검증' — 매일 추천 리스트를 원장에 기록하고 전방 성과를 갱신.

ledger: public/data/sepa-buy-rec-ledger.json
  각 항목 = 추천일·종목·초수익점수·매수배지·추천시점가 + 전방 결착(최대상승·현수익·+20/-10·경과일).
매 실행마다: (1) 오늘 sepa-buy-recommendations.json 을 원장에 추가(중복 제외)
             (2) 모든 과거 항목의 전방 성과를 OHLCV로 재결착
             (3) 초수익 점수 구간별 실전 성과 요약 출력(=점수의 살아있는 검증).

시간이 쌓일수록 "4+점 추천이 정말 대박나나"를 실데이터로 누적 검증한다.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib import ohlcv_matrix

DATA = ROOT / "public" / "data"
KST = timezone(timedelta(hours=9))
LEDGER = DATA / "sepa-buy-rec-ledger.json"
TARGET_PCT, STOP_PCT = 20.0, 10.0   # 핵심 처방(strategy_params 손익비)와 동일


def resolve(code: str, rec_date: str, rec_price: float | None) -> dict | None:
    """추천 시점가 대비 전방 성과: 최대상승·현수익·+20/-10 첫도달·경과일."""
    s = ohlcv_matrix.get_series(code)
    if not s or rec_date not in s.get("dates", []):
        return None
    i = s["dates"].index(rec_date)
    hi, lo, cl = s["highs"], s["lows"], s["closes"]
    n = len(cl)
    if not rec_price:
        return {"days": 0, "outcome": "no_price"}
    tgt, stp = rec_price * (1 + TARGET_PCT / 100), rec_price * (1 - STOP_PCT / 100)
    mx = rec_price
    outcome = "open"
    for j in range(i + 1, n):
        if hi[j] and hi[j] > mx:
            mx = hi[j]
        if lo[j] and lo[j] <= stp:
            outcome = "stop"; break
        if hi[j] and hi[j] >= tgt:
            outcome = "target"; break
    return {
        "days": n - 1 - i,
        "max_gain_pct": round((mx / rec_price - 1) * 100, 1),
        "cur_ret_pct": round((cl[n - 1] / rec_price - 1) * 100, 1),
        "outcome": outcome,
    }


def summarize(entries: list[dict]) -> None:
    res = [e for e in entries if e.get("resolved") and e["resolved"].get("outcome") not in (None, "no_price")]
    print(f"\n=== 살아있는 검증 요약 (결착 {len(res)}건 / 원장 {len(entries)}건) ===")
    if not res:
        print("  아직 전방 데이터 없음 — 날이 지나면 채워집니다.")
        return

    def block(rows: list[dict], label: str):
        if not rows:
            return
        n = len(rows)
        mg = sum(r["resolved"]["max_gain_pct"] for r in rows) / n
        cr = sum(r["resolved"]["cur_ret_pct"] for r in rows) / n
        tg = sum(1 for r in rows if r["resolved"]["outcome"] == "target") / n * 100
        st = sum(1 for r in rows if r["resolved"]["outcome"] == "stop") / n * 100
        dd = sum(r["resolved"]["days"] for r in rows) / n
        print(f"  {label:14s}: {n:4d}건 최대상승{mg:+6.1f}% 현수익{cr:+6.1f}% "
              f"+20도달{tg:3.0f}% -10손절{st:3.0f}% 평균{dd:.0f}일")

    print("[초수익 점수 구간별]")
    for lo, hi, lab in [(6, 99, "6점"), (5, 5, "5점"), (4, 4, "4점"), (3, 3, "3점")]:
        block([r for r in res if lo <= r.get("score", 0) <= hi], lab)
    print("[매수 배지별]")
    for tier, lab in [("ready", "진입권"), ("near", "곧"), ("far", "멀음")]:
        block([r for r in res if r.get("entry_tier") == tier], lab)


def main() -> None:
    led = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {"entries": []}
    entries = led.get("entries", [])
    seen = {(e["date"], e["code"]) for e in entries}

    recf = DATA / "sepa-buy-recommendations.json"
    added = 0
    if recf.exists():
        r = json.loads(recf.read_text(encoding="utf-8"))
        d = r.get("asof") or datetime.now(KST).strftime("%Y-%m-%d")
        for c in r.get("candidates", []):
            if (d, c["code"]) not in seen:
                entries.append({
                    "date": d, "code": c["code"], "name": c.get("name"),
                    "score": c.get("superperf_score"), "entry_tier": c.get("entry_tier"),
                    "rec_price": c.get("current_price"),
                })
                seen.add((d, c["code"])); added += 1

    for e in entries:
        e["resolved"] = resolve(e["code"], e["date"], e.get("rec_price"))

    out = {"updated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
           "target_pct": TARGET_PCT, "stop_pct": STOP_PCT, "entries": entries}
    LEDGER.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 원장 갱신: {LEDGER.name}  (오늘 추가 {added}건, 총 {len(entries)}건)")
    summarize(entries)


if __name__ == "__main__":
    main()

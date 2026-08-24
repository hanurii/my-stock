"""장중 누적거래량 곡선 C(t) 생성 — "평소 이 시각까지 하루 거래량의 몇 %가 나오는가".
캐시된 분봉(.cache/min_daily)의 모든 종목·날짜를 평균해 public/data/intraday-vol-curve.json 에 저장.
봇(signals 게이트)이 이 곡선으로 거래량 페이스를 '동시간대 대비'로 정규화한다(선형 경과시간의 시간대 오염 제거).

실행: python scripts/autobuy/build_vol_curve.py
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(r"C:\Users\hanul\playground\my-stock")
MIN_DIR = BASE / ".cache" / "min_daily"
OUT = BASE / "public" / "data" / "intraday-vol-curve.json"


def build() -> dict:
    curve: dict[str, list[float]] = defaultdict(list)
    n_days = 0
    for p in MIN_DIR.glob("*.json"):
        try:
            bars = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        full = sum(b.get("v", 0) for b in bars)
        if full <= 0:
            continue
        run = 0.0
        for b in bars:
            run += b.get("v", 0)
            curve[b["t"]].append(run / full)   # 그날 t까지 누적/종일
        n_days += 1
    # 시각별 평균 → 단조증가 보정 → 마지막 1.0 정규화
    ts = sorted(curve)
    prev = 0.0
    out = {}
    for t in ts:
        v = sum(curve[t]) / len(curve[t])
        v = max(v, prev)          # 단조 비감소 강제(평균 잡음 방지)
        out[t] = v
        prev = v
    if out:
        last = out[max(out)]
        if last > 0:
            out = {t: round(v / last, 6) for t, v in out.items()}   # 종가시각=1.0 정규화
    return out, n_days


def main():
    curve, n_days = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(curve, ensure_ascii=False), encoding="utf-8")
    print(f"곡선 저장 → {OUT}  ({len(curve)} 시각, {n_days} 종목·일 평균)")
    for probe in ["091000", "093000", "100000", "113000", "133000", "150000", "153000"]:
        if probe in curve:
            print(f"  {probe[:2]}:{probe[2:4]}  누적 {curve[probe]*100:.0f}%")


if __name__ == "__main__":
    main()

"""주도 섹터 동행성 판정 도구 — 아리까리(확신 medium/low) 종목의 편입/제외 근거 산출.

아이디어: 진짜 섹터 주도주라면 "확실(high) 멤버 바스켓"과 주가가 시장 전체보다
더 같이 움직인다. 동행성 점수 = corr(종목, 섹터 바스켓) − corr(종목, 시장 프록시).

입력: public/data/leading-sectors-config.json + OHLCV 캐시(.cache/ohlcv/series)
출력: public/data/_sector_evidence.json (판정표 — 큐레이션 작업 파일, 페이지 무접촉)

검증 장치(매 실행 포함):
  · 양성 대조 = high 멤버를 자기제외(leave-one-out) 바스켓으로 채점 → 대부분 양수여야 함
  · 음성 대조 = reviewed_none(해당없음 확정) 표본 채점 → 대부분 음수여야 함
  · 안정성 = 창을 반으로 갈라 두 반쪽 점수의 부호 일치 여부

판정은 권고일 뿐 — 최종 편입/제외는 사용자가 확정해 config에 반영한다(큐레이션 정본 유지).
"""
import argparse
import json
import math
import random
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib import ohlcv_matrix  # noqa: E402

DATA = ROOT / "public" / "data"
CONFIG_PATH = DATA / "leading-sectors-config.json"
OUT_PATH = DATA / "_sector_evidence.json"

# 문턱: 일간 상관은 시장 베타가 지배적이라 차이가 작다 — ±0.05 수준이 유의미.
TH_INCLUDE = 0.02   # 이상 = 편입 권고
TH_EXCLUDE = -0.05  # 이하 = 제외 권고
MIN_OVERLAP = 80    # 최소 겹침 거래일


def ret_map(code: str, window: int) -> dict[str, float] | None:
    s = ohlcv_matrix.get_series(code)
    if not s:
        return None
    cl, dt = s["closes"][-(window + 1):], s["dates"][-(window + 1):]
    if len(cl) < MIN_OVERLAP // 2:
        return None
    return {dt[i + 1]: cl[i + 1] / cl[i] - 1 for i in range(len(cl) - 1) if cl[i]}


def basket_of(maps: list[dict[str, float]], dates: list[str]) -> dict[str, float]:
    return {d: sum(m.get(d, 0.0) for m in maps) / len(maps) for d in dates}


def corr(m: dict[str, float], ref: dict[str, float], dates: list[str],
         min_n: int = MIN_OVERLAP) -> float | None:
    xs = [m[d] for d in dates if d in m]
    ys = [ref[d] for d in dates if d in m]
    n = len(xs)
    if n < min_n:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def score(m: dict[str, float], basket: dict[str, float], market: dict[str, float],
          dates: list[str]) -> dict | None:
    cs, cm = corr(m, basket, dates), corr(m, market, dates)
    if cs is None or cm is None:
        return None
    half = len(dates) // 2
    parts = []
    for seg in (dates[:half], dates[half:]):
        # 반쪽 창은 겹침 요구치도 절반 — 안정성(부호 일치) 확인용.
        a, b = corr(m, basket, seg, half * 2 // 3), corr(m, market, seg, half * 2 // 3)
        parts.append(None if a is None or b is None else round(a - b, 3))
    stable = all(p is not None for p in parts) and (parts[0] >= 0) == (parts[1] >= 0)
    return {"sector_corr": round(cs, 3), "market_corr": round(cm, 3),
            "score": round(cs - cm, 3), "halves": parts, "stable": stable}


def verdict(sc: float, stable: bool) -> str:
    if sc >= TH_INCLUDE:
        return "편입 권고" if stable else "편입 쪽(불안정)"
    if sc <= TH_EXCLUDE:
        return "제외 권고" if stable else "제외 쪽(불안정)"
    return "보류(사업 축 판단 필요)"


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 대비
    ap = argparse.ArgumentParser(description="주도 섹터 동행성 판정")
    ap.add_argument("--rank", type=int, default=2, help="섹터 순위(config sectors.rank, 기본 ②반도체)")
    ap.add_argument("--window", type=int, default=120, help="상관 창(거래일)")
    ap.add_argument("--market-sample", type=int, default=400, help="시장 프록시 표본 수")
    ap.add_argument("--control-sample", type=int, default=60, help="음성 대조(reviewed_none) 표본 수")
    args = ap.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    sector = next((s for s in config["sectors"] if s["rank"] == args.rank), None)
    if sector is None:
        sys.exit(f"rank {args.rank} 섹터가 config에 없음")
    assign = config.get("assignments", {})
    members = {c: a for c, a in assign.items() if a.get("rank") == args.rank}
    high = {c: a for c, a in members.items() if a.get("confidence", "high") == "high"}
    ambiguous = {c: a for c, a in members.items() if a.get("confidence") in ("medium", "low")}
    reviewed_none = config.get("reviewed_none", {})
    none_codes = list(reviewed_none.keys() if isinstance(reviewed_none, dict) else
                      (x if isinstance(x, str) else x.get("code") for x in reviewed_none))

    print(f"섹터 {sector['label']} — 확실 {len(high)} · 아리까리 {len(ambiguous)} · 창 {args.window}일")

    high_maps = {c: m for c in high if (m := ret_map(c, args.window))}
    if len(high_maps) < 5:
        sys.exit("확실 멤버 시계열이 5개 미만 — 바스켓 구성 불가")
    dates = sorted(set.intersection(*[set(m) for m in high_maps.values()]))[-args.window:]

    # 시장 프록시: 캐시 전 종목에서 표본(섹터 멤버 제외) — 재현성 위해 시드 고정.
    all_codes = [p.stem for p in (ohlcv_matrix.SERIES_DIR).glob("*.json")]
    pool = [c for c in all_codes if c not in members]
    random.seed(42)
    market_maps = [m for c in random.sample(pool, min(args.market_sample, len(pool)))
                   if (m := ret_map(c, args.window))]
    market = basket_of(market_maps, dates)
    full_basket = basket_of(list(high_maps.values()), dates)

    # ── 검증 1: 양성 대조 (high, 자기제외 바스켓) ──
    pos = []
    for c, m in high_maps.items():
        others = [v for k, v in high_maps.items() if k != c]
        r = score(m, basket_of(others, dates), market, dates)
        if r:
            pos.append((high[c]["name"], r["score"]))
    pos_ok = sum(1 for _, s in pos if s > 0)

    # ── 검증 2: 음성 대조 (해당없음 확정 표본) ──
    random.seed(7)
    neg = []
    for c in random.sample(none_codes, min(args.control_sample, len(none_codes))):
        m = ret_map(c, args.window)
        if not m:
            continue
        r = score(m, full_basket, market, dates)
        if r:
            name = reviewed_none[c].get("name") if isinstance(reviewed_none, dict) and isinstance(reviewed_none.get(c), dict) else c
            neg.append((name or c, r["score"]))
    neg_ok = sum(1 for _, s in neg if s < TH_INCLUDE)

    print(f"[검증] 양성 대조: high {len(pos)}개 중 점수>0 = {pos_ok}개 ({pos_ok/len(pos)*100:.0f}%)")
    print(f"[검증] 음성 대조: 해당없음 {len(neg)}개 중 점수<{TH_INCLUDE} = {neg_ok}개 ({neg_ok/len(neg)*100:.0f}%)")

    # ── 본 판정: 아리까리 종목 ──
    rows = []
    for c, a in ambiguous.items():
        m = ret_map(c, args.window)
        r = score(m, full_basket, market, dates) if m else None
        if r is None:
            rows.append({"code": c, "name": a["name"], "confidence": a.get("confidence"),
                         "why": a.get("why"), "verdict": "데이터 부족"})
            continue
        rows.append({"code": c, "name": a["name"], "confidence": a.get("confidence"),
                     "why": a.get("why"), **r, "verdict": verdict(r["score"], r["stable"])})
    rows.sort(key=lambda x: x.get("score", -9), reverse=True)

    print(f"\n{'종목':<14} {'확신':<7} {'점수':>7} {'반쪽점수':>14} {'판정'}")
    for x in rows:
        if "score" not in x:
            print(f"{x['name']:<14} {x['confidence']:<7} {'—':>7} {'—':>14} {x['verdict']}")
            continue
        print(f"{x['name']:<14} {x['confidence']:<7} {x['score']:>+7.3f} {str(x['halves']):>14} {x['verdict']}")

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sector": {"rank": args.rank, "label": sector["label"]},
        "window_days": args.window,
        "thresholds": {"include": TH_INCLUDE, "exclude": TH_EXCLUDE},
        "validation": {
            "positive_control": {"n": len(pos), "score_gt0": pos_ok,
                                 "scores": sorted(pos, key=lambda x: -x[1])},
            "negative_control": {"n": len(neg), "score_lt_include": neg_ok,
                                 "scores": sorted(neg, key=lambda x: -x[1])},
        },
        "judgments": rows,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n저장: {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

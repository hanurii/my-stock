"""코스피 강세장 사이클 자동 분절 (결정적 규칙 — 재현 가능, 즉흥판단 아님).

^KS11 장기 일봉에서 ZigZag(20% 스윙)으로 저점·고점 교대 검출 →
저점→고점 상승률 ≥ BULL_MIN_GAIN(기본 35%)인 구간만 '강세장 사이클'로 채택.
산출: research/oneil-model-book/cycles/cycles_index.json + 사람이 읽는 목록.
KOSDAQ(^KQ11) 같은 구간 상승률은 참고로 병기.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.fetch import fetch_yahoo_chart  # noqa: E402

KST = timezone(timedelta(hours=9))
OUTDIR = ROOT / "research" / "oneil-model-book" / "cycles"
OUT = OUTDIR / "cycles_index.json"

SWING = 0.20          # ZigZag 반전 임계 (20% — 약세 구분)
BULL_MIN_GAIN = 0.35  # 저점→고점 ≥35% 만 '강세장 사이클'로 채택
START = "1996-01-01"


def ep(s):
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def series(sym):
    ch = fetch_yahoo_chart(sym, period1=ep(START),
                           period2=int(datetime.now(timezone.utc).timestamp()), interval="1d")
    if not ch:
        return [], []
    d = [datetime.fromtimestamp(t, KST).strftime("%Y-%m-%d") for t in ch["timestamps"]]
    return d, ch["closes"]


def zigzag(d, c):
    """20% 스윙 교대 극점 [(idx,'L'|'H')]. 마지막은 진행중(미확정) 극점."""
    n = len(c)
    if n < 2:
        return []
    piv = []
    hi_i = lo_i = 0
    trend = 0  # 0 미정, 1 상승(직전 저점 확정), -1 하락(직전 고점 확정)
    for i in range(1, n):
        if c[i] > c[hi_i]:
            hi_i = i
        if c[i] < c[lo_i]:
            lo_i = i
        if trend >= 0 and c[i] <= c[hi_i] * (1 - SWING):
            piv.append((hi_i, "H"))   # 고점 확정
            trend = -1
            lo_i = i                   # 이후 저점 추적 리셋
        elif trend <= 0 and c[i] >= c[lo_i] * (1 + SWING):
            piv.append((lo_i, "L"))   # 저점 확정
            trend = 1
            hi_i = i
    piv.append((hi_i, "H") if trend >= 0 else (lo_i, "L"))  # 진행중 극점
    # 동일 라벨 연속 정리(안전)
    out = []
    for p in piv:
        if out and out[-1][1] == p[1]:
            if (p[1] == "H" and c[p[0]] > c[out[-1][0]]) or \
               (p[1] == "L" and c[p[0]] < c[out[-1][0]]):
                out[-1] = p
        else:
            out.append(p)
    return out


def main():
    d, c = series("%5EKS11")
    if not c:
        print("KOSPI 시세 조회 실패", file=sys.stderr)
        return
    dq, cq = series("%5EKQ11")

    def kq_gain(a, b):
        ai = next((i for i, x in enumerate(dq) if x >= a), None)
        bi = next((i for i, x in enumerate(dq) if x >= b), None)
        if ai is None or bi is None or cq[ai] <= 0:
            return None
        return round((cq[bi] / cq[ai] - 1) * 100, 1)

    def kq_trough(a, b):
        """KOSDAQ가 a 직전 하락국면~b 사이 최저를 찍은 날 (앵커 보정용).
        탐색창: [a−240일, b]. 코스닥 시세 결손 시 None."""
        from datetime import datetime as _dt, timedelta as _td
        lo = (_dt.strptime(a, "%Y-%m-%d") - _td(days=240)).strftime("%Y-%m-%d")
        seg = [(dq[i], cq[i]) for i in range(len(dq)) if lo <= dq[i] <= b]
        if not seg:
            return None
        return min(seg, key=lambda x: x[1])[0]

    piv = zigzag(d, c)
    cycles = []
    for k in range(len(piv) - 1):
        i0, l0 = piv[k]
        i1, l1 = piv[k + 1]
        if l0 == "L" and l1 == "H":
            gain = c[i1] / c[i0] - 1
            if gain >= BULL_MIN_GAIN:
                ks_low, b = d[i0], d[i1]
                kq_low = kq_trough(ks_low, b)
                # 앵커 = 두 지수 저점 중 *더 이른* 날 (어느 시장 위너도 클립 안 되게)
                anchor = min([x for x in (ks_low, kq_low) if x]) if kq_low else ks_low
                cycles.append({
                    "cycle_id": "c" + anchor[:7],
                    "label": f"{anchor} 저점 → {b} 고점 "
                             f"(KOSPI +{gain*100:.0f}%, 앵커=KOSPI/KOSDAQ 중 이른쪽)",
                    "anchor": anchor,
                    "kospi_trough": ks_low, "kospi_trough_close": round(c[i0], 1),
                    "kosdaq_trough": kq_low,
                    "cycle_end": b, "end_close": round(c[i1], 1),
                    "kospi_gain_pct": round(gain * 100, 1),
                    "kosdaq_gain_pct": kq_gain(ks_low, b),
                    "ongoing": (k + 1 == len(piv) - 1 and piv[-1][1] == "H"
                                and i1 >= len(c) - 5),
                })

    OUTDIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "method": f"^KS11 일봉 ZigZag {int(SWING*100)}% 스윙, 저점→고점 ≥{int(BULL_MIN_GAIN*100)}% 채택",
        "params": {"swing": SWING, "bull_min_gain": BULL_MIN_GAIN, "start": START},
        "cycles": cycles,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"강세장 사이클 {len(cycles)}개 (규칙: 20% 스윙, +{int(BULL_MIN_GAIN*100)}%↑)")
    for i, x in enumerate(cycles, 1):
        og = " [진행중]" if x["ongoing"] else ""
        kqg = f"+{x['kosdaq_gain_pct']}%" if x['kosdaq_gain_pct'] is not None else "NA"
        print(f"{i:2d}. {x['cycle_id']:>10} | 앵커 {x['anchor']} → {x['cycle_end']} "
              f"| KOSPI+{x['kospi_gain_pct']}% KOSDAQ{kqg} "
              f"(KOSPI저점 {x['kospi_trough']} / KOSDAQ저점 {x['kosdaq_trough']}){og}")


if __name__ == "__main__":
    main()

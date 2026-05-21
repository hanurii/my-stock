"""v1.3 정교화 설계 — 케이프형(깊은+오래된 고점후 하락) 안에서
*이기는 케이프* vs *지는 케이프* 를 가르는 표식 탐색.

배경: 케이프형 무조건 제외=위너 학살(위너 55~59% 그 모양). 케이프형
승률 26%<비케이프 35% — 강자/약자 혼재. → 제외 아닌 *추가 통과조건*
설계. 케이프형 부분집합(위너+안오름, 2사이클)에서 후보 표식별
'케이프 위너율'이 베이스(26%) 대비 얼마나 오르는지·위너 보존율 측정.

후보 표식(모두 pivot 시점, 종가만 — _universe_prices엔 거래량 없음):
 T_STREAK≤k  진입 직전 연속 하락일 ≤ k (케이프=8일 → 자유낙하 배제)
 T_LOWAGE≥a  최근15일 최저가가 a거래일 이상 전 (= 신저점 갱신 멈춤)
 T_BOUNCE≥b  종가가 최근15일 최저 대비 +b%↑ (바닥서 반등)
 T_MA50UP    종가>50일선 AND 50일선 상승 (지지 사수+추세전환)
정직: 사후·생존자·종가만(거래량 표식 불가-명시)·단일창·방향만.
사용: python analyze_cape_refine.py
"""
import json
import sys
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
PAIRS = [("c2024-12", "c2024-12-ctrl500", "_universe_prices_5y.json"),
         ("c2020-03", "c2020-03-ctrl500", "_universe_prices.json")]


def rows(p):
    return [r for r in json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
            if not r.get("error") and r.get("pivot_date")]


def sma(c, i, w):
    return sum(c[i - w + 1:i + 1]) / w if i >= w - 1 else None


def feats(c, i0):
    """케이프형 여부 + 표식들. 부족하면 None."""
    if i0 < 60 or i0 >= len(c) or c[i0] <= 0:
        return None
    seg = c[i0 - 60:i0 + 1]
    hi = max(seg)
    hidx = max(range(i0 - 60, i0 + 1), key=lambda k: c[k])
    drop = c[i0] / hi - 1.0
    hi_age = i0 - hidx
    cape = (drop <= -0.12 and hi_age > 5)
    if not cape:
        return {"cape": False}
    # 연속 하락일
    streak = 0
    for k in range(i0, 0, -1):
        if c[k] < c[k - 1]:
            streak += 1
        else:
            break
    w15 = c[i0 - 15:i0 + 1]
    lo15 = min(w15)
    lo_idx = i0 - 15 + w15.index(lo15)
    low_age = i0 - lo_idx
    bounce = c[i0] / lo15 - 1.0 if lo15 > 0 else 0.0
    m50, m50p = sma(c, i0, 50), sma(c, i0 - 10, 50)
    ma50up = bool(m50 and m50p and c[i0] > m50 and m50 > m50p)
    fut = c[i0:min(i0 + 120, len(c))]
    gain = max(fut) / c[i0] - 1.0 if len(fut) > 5 else None
    return {"cape": True, "streak": streak, "low_age": low_age,
            "bounce": bounce, "ma50up": ma50up, "drop": drop, "gain": gain}


TESTS = [
    ("T_STREAK<=3 (자유낙하 배제)", lambda f: f["streak"] <= 3),
    ("T_STREAK<=5", lambda f: f["streak"] <= 5),
    ("T_LOWAGE>=3 (신저점 멈춤)", lambda f: f["low_age"] >= 3),
    ("T_BOUNCE>=3% (바닥반등)", lambda f: f["bounce"] >= 0.03),
    ("T_MA50UP (지지+전환)", lambda f: f["ma50up"]),
    ("복합 STREAK<=3 & MA50UP", lambda f: f["streak"] <= 3 and f["ma50up"]),
    ("복합 LOWAGE>=3 & BOUNCE>=3%",
     lambda f: f["low_age"] >= 3 and f["bounce"] >= 0.03),
]


def main():
    # 케이프형만 모음: (그룹, feats)
    capes = []
    for win, ctl, pf in PAIRS:
        U = json.loads((CY / win / pf).read_text(encoding="utf-8"))

        def collect(rws, grp):
            for r in rws:
                s = U.get(r["code"]) or {}
                d, c = s.get("d") or [], s.get("c") or []
                if r["pivot_date"] not in d:
                    continue
                f = feats(c, d.index(r["pivot_date"]))
                if f and f.get("cape") and f.get("gain") is not None:
                    capes.append((grp, f))
        collect(rows(win), "W")
        collect(rows(ctl), "L")
    nW = sum(1 for g, _ in capes if g == "W")
    nL = sum(1 for g, _ in capes if g == "L")
    base = nW / (nW + nL) * 100
    out = ["[v1.3 정교화] 케이프형 안에서 이기는/지는 케이프 가르기",
           f"케이프형 모집단: 위너 {nW} · 안오름 {nL} · "
           f"베이스 위너율 {base:.0f}% (이걸 넘겨야 표식 유효)",
           "표식 | 통과중 위너율 | 위너보존(통과위너/전체케이프위너) | 안오름배제%",
           "-" * 64]
    for name, fn in TESTS:
        pw = [f for g, f in capes if g == "W" and fn(f)]
        pl = [f for g, f in capes if g == "L" and fn(f)]
        wr = len(pw) / (len(pw) + len(pl)) * 100 if (pw or pl) else 0
        keep = len(pw) / nW * 100 if nW else 0
        rej = (1 - len(pl) / nL) * 100 if nL else 0
        mark = " ★" if (wr > base + 4 and keep >= 60) else ""
        out.append(f"{name:30s} | {wr:4.0f}% | {keep:4.0f}% | {rej:4.0f}%{mark}")
    out += ["-" * 64,
            f"해석: '통과중 위너율'이 베이스({base:.0f}%)보다 뚜렷이↑ &",
            "위너보존 ≥60% 인 표식이 정교화 후보(★). 그게 *이기는 케이프*",
            "표식. v1.3 정교화 = 케이프형이면 제외 대신 그 표식 요구.",
            "정직한 한계: 사후·생존자(상폐 제외)·종가만(거래량표식 불가)·",
            "단일 60/15창·120일성장창 임의·2사이클. 방향만, 절대수치 X."]
    fp = CY.parent / "_cape_refine.txt"
    fp.write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fp} (capeW={nW} capeL={nL} base={base:.0f}%)", file=sys.stderr)


if __name__ == "__main__":
    main()

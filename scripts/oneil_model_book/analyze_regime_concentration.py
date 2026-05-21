"""[#1] 소수테마 주도장 vs 광범위 강세장 판별 지표 정식화.

섹터 무리(보조 가점)는 cross-cycle 결과상 *시장구조 의존*:
 c2024-12 위너 섹터HHI 0.068 → 섹터무리 성립(순열 p=0.0000)  → 가점 ON
 c2020-03 위너 섹터HHI 0.037 → 섹터무리 미성립(p=0.0998)     → 가점 OFF
이 둘을 앵커로, "지금 장이 어느 쪽인가"를 가르는 지표를 정의·산출.

지표(주도 집중도) = 그 시점 RS≥80(상대강도 최강) 종목들의 induty_group3
HHI. 높음=주도주가 소수 섹터에 몰림(소수테마 주도장)→섹터무리 ON.
낮음=주도주가 전 섹터 분산(광범위 강세장)→섹터무리 OFF.

정직: ①앵커 2개뿐 → 임계는 *잠정*(원전/대규모 검증값 아님, 두 점
중간). ②model_book 위너 기반 = 사후 근사. *진짜 라이브* 판별은
유니버스 전 종목 RS+섹터 필요(유니버스 섹터 미보유 → 차기 과제).
③단일 사이클 표본·생존자. 방향(집중↑→섹터무리 유효)만 채택.
사용: python analyze_regime_concentration.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
# (사이클, 표시명, cross-cycle 순열검정 실측 결과)
CYCLES = [("c2024-12", "2024-25(반도체·AI)", "p=0.0000 성립"),
          ("c2020-03", "2020-21(코로나)", "p=0.0998 미성립")]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def hhi(labels):
    n = len(labels)
    if not n:
        return 0.0, 0.0
    c = Counter(labels)
    h = sum((v / n) ** 2 for v in c.values())
    return h, (1 / h if h else 0.0)


def sectors(cyc, rs_min=None):
    rows = json.loads((CY / cyc / "model_book.json").read_text(encoding="utf-8"))["rows"]
    out = []
    for r in rows:
        if r.get("error"):
            continue
        s = r.get("induty_group3")
        if s in (None, "", "None"):
            continue
        if rs_min is not None:
            v = num(r.get("rs_score"))
            if v is None or v < rs_min:
                continue
        out.append(str(s))
    return out


def main():
    rows = []
    for cyc, nm, xres in CYCLES:
        allh, alle = hhi(sectors(cyc))
        sub = sectors(cyc, rs_min=80)
        sh, se = hhi(sub)
        rows.append((cyc, nm, xres, allh, alle, sh, se, len(sub)))

    L = ["[#1] 소수테마 주도장 판별 지표 — 주도(RS≥80) 섹터 집중도",
         "지표 = 그 시점 RS≥80 종목의 induty_group3 HHI (↑=소수테마 주도)",
         "-" * 66,
         "사이클 | 위너전체 HHI(유효섹터) | RS≥80 HHI(유효·n) | cross-cycle"]
    for cyc, nm, xres, ah, ae, sh, se, sn in rows:
        L.append(f"{nm:18s} | {ah:.3f} ({ae:4.1f}) | "
                 f"{sh:.3f} ({se:4.1f}·n{sn}) | {xres}")
    on = next(r for r in rows if "성립" in r[2] and "미" not in r[2])
    off = next(r for r in rows if "미성립" in r[2])
    # 기대: 섹터무리 성립(ON) 사이클이 미성립(OFF)보다 더 집중(HHI↑)
    full_ok = on[3] > off[3]      # 위너 전체 HHI
    rs_ok = on[5] > off[5]        # RS≥80 주도주 HHI
    L += ["-" * 66,
          "기대 방향: 섹터무리 성립 사이클 HHI > 미성립 사이클 HHI",
          f"  위너전체 HHI: 성립 {on[3]:.3f} vs 미성립 {off[3]:.3f} "
          f"→ {'방향 일치(분리됨)' if full_ok else '불일치'}",
          f"  RS≥80 HHI : 성립 {on[5]:.3f} vs 미성립 {off[5]:.3f} "
          f"→ {'방향 일치' if rs_ok else '★불일치(역전) — 판별 실패'}",
          "",
          "결론(정직):",
          "- **위너 전체 섹터 HHI는 두 사이클을 올바른 방향으로 분리**",
          "  (집중 0.068→섹터무리 성립 / 분산 0.037→미성립). 단 이는",
          "  *사후* 지표 — 라이브선 위너를 모름.",
          "- **RS≥80 주도주 HHI(라이브 대용 후보)는 방향 역전 → 실패**.",
          "  원인 추정: c2020-03 RS≥80 n=35뿐 → HHI 표본 교란(소표본",
          "  일수록 HHI 기계적 상승). 단정 아님. → *이 대용치 폐기*.",
          "- ⇒ 검증된 라이브 트리거 *아직 없음*. 섹터무리 조건부 적용의",
          "  '소수테마 주도장' 판정은 미해결 과제로 정직 표기.",
          "",
          "다음(차기) — 라이브 판별 후보:",
          "- 섹터지수 수익 집중도(소수 섹터에 상승 쏠림 HHI; 유니버스",
          "  종목 섹터 불요·지수만 → 라이브 가능). 가장 유망.",
          "- 유니버스 전 종목 RS+섹터 동시 확보판(섹터 미보유=비용 큼).",
          "- 사이클 표본 확대(2015+)로 위너전체-HHI 임계 정식 보정.",
          "한계: 앵커 2·생존자·단일 사이클·사후. 방향성 결론만."]
    out = CY.parent / "_regime_concentration.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"saved: {out} (full_ok={full_ok} rs_ok={rs_ok} "
          f"on_full={on[3]:.3f} off_full={off[3]:.3f})", file=sys.stderr)


if __name__ == "__main__":
    main()

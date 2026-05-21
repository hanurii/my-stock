"""I축 20일 검정 — '외인+기관 20일 합산>0'이 핵심 변별축이 되나.

사용자 아이디어: 윈도우를 60→20일로 줄이고 외인+기관을 합산하면
변별력이 핵심축(L~7.78x)급으로 오르나? 진짜 20일 수급 데이터로 확정.
위너(c2024-12+c2020-03) vs 안오름(각 ctrl500). _flow20.json 사용.
결손은 제외(추정 없음). lift = P(통과|위너)/P(통과|안오름).
사용: python analyze_flow20.py
"""
import json
import sys
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
PAIRS = [("c2024-12", "c2024-12-ctrl500", "2024-25"),
         ("c2020-03", "c2020-03-ctrl500", "2020-21")]


def flow(dirn):
    return json.loads((CY / dirn / "_flow20.json").read_text(encoding="utf-8"))


GATES = [
    ("현행 I: 외인 OR 기관 60d>0",
     lambda v: ("f60" in v) and ((v["f60"] > 0) or (v["o60"] > 0))),
    ("(외인+기관) 60d 합산>0",
     lambda v: ("sum60" in v) and (v["sum60"] > 0)),
    ("외인 OR 기관 20d>0",
     lambda v: ("f20" in v) and ((v["f20"] > 0) or (v["o20"] > 0))),
    ("(외인+기관) 20d 합산>0  ★아이디어",
     lambda v: ("sum20" in v) and (v["sum20"] > 0)),
]


def main():
    out = ["[I축 20일 검정] 외인+기관 20일 합산이 핵심축 되나",
           "lift=위너통과율÷안오름통과율 · 결손 제외 · *L(7.78x) 기준 비교*",
           "참고: L 상대강도 7.78x(c2024)/2.19x(c2020) = 핵심축",
           "=" * 64]
    for win, ctl, nm in PAIRS:
        W, L = flow(win), flow(ctl)
        out.append(f"■ {nm}  (위너 {len(W)} · 안오름 {len(L)} 레코드)")
        for name, fn in GATES:
            wpass = sum(1 for v in W.values() if not v.get("err") and fn(v))
            wtot = sum(1 for v in W.values()
                       if not v.get("err") and _has(v, name))
            lpass = sum(1 for v in L.values() if not v.get("err") and fn(v))
            ltot = sum(1 for v in L.values()
                       if not v.get("err") and _has(v, name))
            wr = wpass / wtot if wtot else 0
            lr = lpass / ltot if ltot else 0
            lift = wr / lr if lr else None
            out.append(f"  {name:30s} 위너 {wr*100:3.0f}%({wpass}/{wtot}) "
                       f"안오름 {lr*100:3.0f}%({lpass}/{ltot}) "
                       f"lift {'n/a' if lift is None else f'{lift:.2f}x'}")
        out.append("-" * 64)
    out += ["판정: 20d 합산 lift 가 ~3x↑ 로 뛰면 핵심축 승격. 여전히",
            "1.1~1.5x 면 60d와 동급 '약한 보조'(윈도·합산 무관) = 사전",
            "예측대로 강세장엔 큰손 매수가 위너·안오름 공통이라 변별 약함.",
            "한계: 사후·생존자·naver깊이결손 제외·2사이클·금액 아닌 주식수",
            "기준(정규화 안 함). 방향만."]
    fp = CY.parent / "_flow20_test.txt"
    fp.write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fp}", file=sys.stderr)


def _has(v, gate_name):
    """게이트가 보는 필드가 그 레코드에 있나(분모 결정)."""
    if "60d" in gate_name:
        return "f60" in v or "sum60" in v
    return "f20" in v or "sum20" in v


if __name__ == "__main__":
    main()

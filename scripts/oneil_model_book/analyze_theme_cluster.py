"""테마 매핑 개선 — KSIC 대신 *동시등락 데이터 군집*으로 섹터무리 재측정.

문제: induty_group3(KSIC 3자리)는 한 투자테마를 여러 코드로 쪼개
섹터무리를 과소평가(예: 조선=311/291/281/412/649 분산). theme_manual
필드는 전부 빈값 → *라벨을 짓지 않고* 주가 동시등락으로 자동 군집.

방법(라벨 프리·환각 없음):
 - 사이클 창 공통 거래일서 각 종목 *주봉(5거래일) 로그수익률*.
 - 위너200+안오름500 전체 쌍 피어슨 상관. corr≥ρ 면 간선 → Union-Find
   연결요소 = '동시등락 클러스터'(= 데이터가 말하는 테마, 이름 없음).
 - 위너 vs 안오름 의 클러스터-멤버십 HHI·순열검정 → KSIC(0.068 vs
   0.025, p=0.0000) 대비 분리가 강해지면 테마매핑이 실질 개선.
 - 각 주요 위너 클러스터는 *구성으로만 묘사*(주 KSIC + 표본 3종목).

정직: ρ·주봉 다운샘플 민감·단일 사이클·생존자·탐색적. 클러스터 무명
(구성으로 기술). 절대수치 아닌 'KSIC 대비 방향'만.
사용: python analyze_theme_cluster.py [--rho 0.6]
"""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

CY = Path(__file__).resolve().parents[2] / "research" / "oneil-model-book" / "cycles"
U = json.loads((CY / "c2024-12" / "_universe_prices_5y.json").read_text(encoding="utf-8"))


def rows(p):
    return [r for r in json.loads((CY / p / "model_book.json").read_text(encoding="utf-8"))["rows"]
            if not r.get("error") and r.get("code") in U]


def hhi(labels):
    n = len(labels)
    if not n:
        return 0.0, 0.0
    c = Counter(labels)
    h = sum((v / n) ** 2 for v in c.values())
    return h, (1 / h if h else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rho", type=float, default=0.6)
    a = ap.parse_args()

    W = rows("c2024-12")
    Lo = rows("c2024-12-ctrl500")
    meta = {}                                   # code -> (grp, name, induty3)
    for r in W:
        meta[r["code"]] = ("위너", r.get("name", r["code"]), str(r.get("induty_group3")))
    for r in Lo:
        meta.setdefault(r["code"],
                        ("안오름", r.get("name", r["code"]), str(r.get("induty_group3"))))

    # 밀집 공통일(≥90% 종목 보유) → 주봉. 격자 전부 가진 종목만 사용.
    codes = [c for c in meta if U[c].get("d") and U[c].get("c")]
    freq = Counter()
    for c in codes:
        freq.update(U[c]["d"])
    thr = 0.9 * len(codes)
    days = sorted([d for d, n in freq.items() if n >= thr])[::5]   # 주봉
    if len(days) < 30:
        print(f"밀집 공통 주봉 부족 ({len(days)})", file=sys.stderr)
        return
    ret = {}
    dropped = 0
    for c in codes:
        m = dict(zip(U[c]["d"], U[c]["c"]))
        if any(d not in m or m[d] is None or m[d] <= 0 for d in days):
            dropped += 1
            continue
        px = [m[d] for d in days]
        r = [math.log(px[i + 1] / px[i]) for i in range(len(px) - 1)]
        mu = sum(r) / len(r)
        sd = (sum((x - mu) ** 2 for x in r) / len(r)) ** 0.5
        if sd == 0:
            continue
        ret[c] = [(x - mu) / sd for x in r]      # 표준화 (corr=평균곱)
    cl = list(ret)
    L = len(ret[cl[0]])

    # Union-Find: corr≥rho 연결
    par = {c: c for c in cl}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for i in range(len(cl)):
        ri = ret[cl[i]]
        for j in range(i + 1, len(cl)):
            corr = sum(ri[k] * ret[cl[j]][k] for k in range(L)) / L
            if corr >= a.rho:
                par[find(cl[i])] = find(cl[j])
    comp = {c: find(c) for c in cl}

    win_lab = [comp[r["code"]] for r in W if r["code"] in comp]
    lo_lab = [comp[r["code"]] for r in Lo if r["code"] in comp]
    hw, ew = hhi(win_lab)
    hc, ec = hhi(lo_lab)

    # 순열검정
    import random
    pool = list(win_lab) + list(lo_lab)
    nw = len(win_lab)
    obs = hw - hc
    random.seed(7)
    ge = 0
    N = 4000
    for _ in range(N):
        random.shuffle(pool)
        if hhi(pool[:nw])[0] - hhi(pool[nw:nw + len(lo_lab)])[0] >= obs:
            ge += 1
    p = ge / N

    out = [f"[테마매핑] 동시등락 군집 vs KSIC — 섹터무리 재측정 (ρ={a.rho})",
           f"밀집 주봉 {len(days)}구간·사용종목 {len(cl)}(커버부족 제외 "
           f"{dropped})·연결요소(클러스터) {len(set(comp.values()))}개",
           "",
           f"클러스터 멤버십 HHI: 위너 {hw:.3f}(유효 {ew:.1f}) · "
           f"안오름 {hc:.3f}(유효 {ec:.1f})",
           f"순열검정 N={N}: 위너−안오름 = {obs:+.3f}, p = {p:.4f} "
           f"({'유의' if p < 0.05 else '비유의'})",
           "KSIC(3자리) 기준선: 위너 0.068 / 안오름 0.025 / p=0.0000",
           "",
           "→ 동시등락 HHI 가 KSIC 보다 크고 p 도 유의면, 테마(동시등락)",
           "  군집이 위너 응집을 KSIC보다 더 잘 포착 = 테마매핑 실질 개선.",
           "  비슷/약하면 KSIC 로 충분(개선 효과 제한).",
           "",
           "상위 위너 클러스터 (구성으로만 기술 — 라벨 없음):"]
    by = defaultdict(list)
    for r in W:
        if r["code"] in comp:
            by[comp[r["code"]]].append(r)
    for root, rs in sorted(by.items(), key=lambda kv: -len(kv[1]))[:8]:
        if len(rs) < 2:
            continue
        ks = Counter(str(x.get("induty_group3")) for x in rs).most_common(3)
        nms = "·".join(x.get("name", x["code"]) for x in rs[:4])
        out.append(f"  위너 {len(rs):2d}종목 | 주KSIC {ks} | 예: {nms}")
    out += ["",
            "정직한 한계: ρ·주봉 다운샘플 민감·단일 사이클·생존자·탐색적·",
            "클러스터 무명(구성 기술). 절대수치 아닌 KSIC 대비 방향만.",
            "차기: ρ 민감도(0.5~0.8)·cross-cycle(c2020-03)·라이브 적용."]
    fp = CY.parent / f"_theme_cluster_rho{int(a.rho*100)}.txt"
    fp.write_text("\n".join(out), encoding="utf-8")
    print(f"saved: {fp} (winHHI={hw:.3f} ctlHHI={hc:.3f} p={p:.4f} "
          f"clusters={len(set(comp.values()))})", file=sys.stderr)


if __name__ == "__main__":
    main()

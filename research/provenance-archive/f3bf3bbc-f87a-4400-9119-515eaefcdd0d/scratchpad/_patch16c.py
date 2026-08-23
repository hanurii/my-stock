# -*- coding: utf-8 -*-
"""추첨 난수를 **(날짜, 팔)마다 독립**으로 바꾼다.

지금까지는 하나의 `rnd` 스트림을 모든 팔이 공유해서, **팔을 하나 추가하면 다른 팔의
추첨까지 바뀌었다.** 실측으로 C 의 95% 상한이 −0.0045 ↔ +0.0065 사이를 오가며
라벨이 "효과 있음(음수)" ↔ "판정불가"로 뒤집혔다.
→ `Random("seed|날짜|팔")` 로 고정하면 **팔을 더해도 기존 팔의 값이 안 변한다.**
"""
import pathlib

p = pathlib.Path("research/handoff/scripts/16-selection-edge.py")
t = p.read_text(encoding="utf-8")

# 팔별 독립 난수 헬퍼
old = """def make_blocks(rnd, n_pos):"""
new = """def draw_rng(D, arm):
    \"\"\"(날짜, 팔)마다 독립 난수 — 팔을 추가해도 기존 팔의 추첨이 안 바뀐다.\"\"\"
    return random.Random("%d|%s|%s" % (DRAW_SEED, D, arm))


def make_blocks(rnd, n_pos):"""
assert t.count(old) == 1
t = t.replace(old, new)

reps = [
    # C·B 풀
    ("""                rp = []
                for _ in range(N_REP):
                    pick = (rnd.sample(cd, k) if len(cd) >= k
                            else [cd[rnd.randrange(len(cd))] for _ in range(k)])
                    rp.append(st.mean([net(get(c, D, b1)["gain"]) for c in pick]))""",
     """                rp = []
                r0 = draw_rng(D, nm)
                for _ in range(N_REP):
                    pick = (r0.sample(cd, k) if len(cd) >= k
                            else [cd[r0.randrange(len(cd))] for _ in range(k)])
                    rp.append(st.mean([net(get(c, D, b1)["gain"]) for c in pick]))"""),
    # ATR 맞춤
    ("""                rp = []
                for _ in range(N_REP):
                    vv = []
                    for bd in our_bands:""",
     """                rp = []
                r0 = draw_rng(D, nm)
                for _ in range(N_REP):
                    vv = []
                    for bd in our_bands:"""),
    ("""                        vv.append(net(get(cd[rnd.randrange(len(cd))], D, b1)["gain"]))""",
     """                        vv.append(net(get(cd[r0.randrange(len(cd))], D, b1)["gain"]))"""),
    # A 팔
    ("""                reps = []
                for _ in range(N_REP):
                    pick = (rnd.sample(cand, k) if len(cand) >= k
                            else [cand[rnd.randrange(len(cand))] for _ in range(k)])""",
     """                reps = []
                r0 = draw_rng(D, ARMN[arm])
                for _ in range(N_REP):
                    pick = (r0.sample(cand, k) if len(cand) >= k
                            else [cand[r0.randrange(len(cand))] for _ in range(k)])"""),
    # 분포 표본
    ("""                    pk = (rnd.sample(cand, k) if len(cand) >= k else list(cand[:k]))""",
     """                    pk = (draw_rng(D, ARMN[arm] + "|dist").sample(cand, k)
                          if len(cand) >= k else list(cand[:k]))"""),
]
for a, b in reps:
    assert t.count(a) == 1, a[:60]
    t = t.replace(a, b)

t = t.replace("""    rnd = random.Random(DRAW_SEED)
    ARMS""", """    ARMS""")
p.write_text(t, encoding="utf-8")
print("patched")

# -*- coding: utf-8 -*-
"""149a 선행계산 — 🚨 «자료를 열지 않는다». 앞 구간에서 «이미 나온 수»만 쓴다.

  묻는 것 : 두뇌 세션이 §15 에 «미리» 적은 조건 1·2 를, 뒤 구간을 열기 «전»에 만족시킬 수 있나
  안 하는 것 : score() 를 import 하지 않는다 · 2012 이후 자료를 읽지 않는다 · N 을 늘리지 않는다
  출처 : data/148-result.json (A20 obs·z) · scripts/148-sieve.py:304 (se·천장) · 143-sieve.py:43-45 (창)
"""
import json, sys, os
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
R148 = json.load(open(os.path.join(HERE, "..", "data", "148-result.json"), encoding="utf-8"))

OBS   = R148["A20"]["obs"]          # 체 1등 − 그날 평균 (%p/날)
ZOBS  = R148["A20"]["z"]
THR148= R148["thr"]
SE    = 0.5795                      # 148-sieve.py:304 «실측» 표준편차
CEIL  = 9.207                       # 148-sieve.py:304 «완벽한 고르기» 천장
Z1S   = 1.645                       # 단측 95% (정규 근사 — 아래에서 «폭»으로 흔든다)

# ── 관문 ①  se 와 z 가 서로 맞나 (귀무 평균이 0 인가) ────────────────────────
MU = OBS - ZOBS * SE
print("## 관문 ① — 적어 둔 se 와 기록된 z 가 «서로» 맞나")
print("   obs %+.5f · z %.4f · se %.4f  →  함축 귀무평균 mu = %+.5f  (se 의 %.2f%%)"
      % (OBS, ZOBS, SE, MU, 100.0 * abs(MU) / SE))
if abs(MU) > 0.05 * SE:
    raise SystemExit("🚨 관문 ① 미통과 — se·z·obs 가 안 맞는다. 맞추지 말고 «왜»부터.")
print("   ✅ 통과 — 귀무 평균이 사실상 0. 아래 대수에서 se 는 «약분»되므로 이 값에 결과가 안 걸린다\n")

# ── 대수 ──────────────────────────────────────────────────────────────────────
#   효과의 단측 95% 하한   L   = sd·(z − 1.645)
#   뒤 구간 MDE(148 정의)  M   = z95 · sd/√R          (R = 뒤 날 수 / 앞 날 수)
#   조건 1 : M < L   ⇔   z95/√R < (z − 1.645)   ⇔   R > [ z95 / (z − 1.645) ]²
#   ★ sd 가 통째로 약분된다 → «필요 배수»는 앞 구간 z «하나»로 정해진다
def need_R(z95, z=ZOBS, disc=Z1S):
    d = z - disc
    return float("inf") if d <= 0 else (z95 / d) ** 2

print("## 대수 — 조건 1 은 «필요 배수 R» 하나로 줄어든다")
print("   조건 1 :  뒤 MDE < 앞 효과의 단측 95% 하한")
print("          ⇔  z95·sd/√R  <  sd·(z − 1.645)")
print("          ⇔  **R > [ z95 / (z − 1.645) ]²**      ← sd 가 «약분»된다")
print("   ⇒ 뒤 자료를 «한 줄도» 안 보고 정해진다. 앞 구간 z = %.4f 하나로.\n" % ZOBS)

# ── 민감도 : z95 를 «정규 근사»에 걸지 않는다 ──────────────────────────────────
print("## 민감도 — 단측 문턱 z95 를 흔들어도 결론이 안 바뀌나")
print("   | z95 | z − 1.645 | 필요 R(조건1) |")
print("   |---|---|---|")
for z95 in (1.55, 1.60, 1.645, 1.70, 1.75, 1.80, 1.8262):
    r = need_R(z95)
    print("   | %.4f | %.4f | %s |" % (z95, ZOBS - Z1S,
          "**∞ — 어떤 자료로도 불가**" if r == float("inf") else "**%.1f배**" % r))
print()

# ── 뒤 구간 «날 수»는 149a 가 잴 것 — 🚨 «점»이 아니라 «괄호»로 둔다 ────────────
#   348 일(자 A·+20)이 «앞 창 전체(12.75년)»의 날인지 «시험 반쪽(8.12년)»의 날인지
#   문서에서 갈라지지 않는다 → 두 읽기를 «둘 다» 계산하고 «나쁜 쪽»으로 판단하지 않는다.
FRONT_ALL_Y  = 12.75                            # 1999-04-01 ~ 2011-12-31
FRONT_TEST_Y = 8.12                             # 2003-11-19 ~ 2011-12-31
BACK_Y       = 14.67                            # 2012-01-01 ~ 2026-09-01
N_FRONT_DAYS = 348                              # 145-no-gate-sieve.md:79 (자 A·+20)
R_LO, R_HI   = BACK_Y / FRONT_ALL_Y, BACK_Y / FRONT_TEST_Y
R_EST        = R_HI                             # ★ 조건에 «유리한» 쪽을 쓴다
need = need_R(Z1S)
print("## 뒤 구간이 «실제로» 몇 배인가 — 🚨 «추정»이고 149a 가 «잴» 값이다")
print("   앞 날 수 %d개가 «전체 %.2f년»의 것인지 «시험 %.2f년»의 것인지 문서가 «안 가른다»"
      % (N_FRONT_DAYS, FRONT_ALL_Y, FRONT_TEST_Y))
print("   → **R ∈ [%.2f, %.2f]배**   (뒤 창 %.2f년 · 발생률이 같다는 가정)" % (R_LO, R_HI, BACK_Y))
print("   ★ 아래는 **괄호의 «유리한» 끝(%.2f배)**으로 판단한다 — 불리한 쪽을 골라 이기지 않는다" % R_EST)
print("   필요 %.1f배  vs  유리한 끝 %.2f배  →  **%.0f배 모자람**" % (need, R_EST, need / R_EST))
print("   ★ 뒤 구간 후보일 발생률이 앞의 **3배**여도 R=%.1f → 여전히 **%.0f배 모자람**"
      % (3 * R_EST, need / (3 * R_EST)))
print("   ⇒ 149a 가 «무엇을 재든» 조건 1 은 못 넘는다. 격차가 재는 값의 불확실성보다 **한 자리** 크다")
print("")

# ── 세 가지 «읽기» — 조건 1 은 「할인」을 넣느냐로 갈린다 ──────────────────────
print("## ★ 갈림 — 조건 1 의 답은 «승자의 저주 할인»을 넣느냐 «하나»로 갈린다")
rows = [("(가) 두뇌 세션이 «쓴» 그대로 — 하한과 견줌", need_R(Z1S)),
        ("(나) 할인 없이 «관측값»과 견줌",             (Z1S / ZOBS) ** 2),
        ("(다) 검출력 80%까지 요구",                   need_R(Z1S + 0.842)),
        ]
print("   | 읽기 | 필요 R | 추정 R=%.2f 로 |" % R_EST)
print("   |---|---|---|")
for nm, r in rows:
    print("   | %s | %.2f배 | %s |" % (nm, r, "✅ **통과**" if R_EST > r else "⛔ **미통과(%.0f배 모자람)**" % (r / R_EST)))
print("\n   🚨 (가)와 (나)의 답이 «반대»다. 그리고 두뇌 세션이 적은 것은 **(가)**다.\n")

# ── 조건 2 는 따로 — 둘이 «다른 것»을 묻는다 ──────────────────────────────────
mde_back = Z1S * SE / (R_EST ** 0.5)
print("## 조건 2 — 천장/MDE ≥ 2.0")
print("   뒤 MDE ≈ %.4f%%p/날 (단일물음 %.3f × se %.4f / √%.2f)" % (mde_back, Z1S, SE, R_EST))
print("   천장 %.3f  →  **%.2f배**  →  %s" % (CEIL, CEIL / mde_back,
      "✅ **통과**" if CEIL / mde_back >= 2.0 else "⛔ 미통과"))
print("   ★ 조건 2 는 「**큰** 효과를 볼 수 있나」 · 조건 1 은 「**이** 효과를 볼 수 있나」 — 답이 갈린다\n")

# ── 구조 ─────────────────────────────────────────────────────────────────────
print("## ★★ 구조 — 두뇌 세션이 든 «희망»과 «막힘»은 «같은 수»의 양면이다")
print("   「한 번만 물었다면 %.4f > 1.645 로 넘었다」 ← z 가 1.645 에 **가깝다**는 말" % ZOBS)
print("   「그래서 유보 자료로 확인할 수 없다」      ← R > [1.645/(z−1.645)]² 는 z 가 1.645 에")
print("                                                **가까울수록 «폭발»**한다 (%.1f배)" % need)
print("   ⇒ **설레게 하는 바로 그 수가, 확인을 불가능하게 하는 수다.**")

out = {"z_front": ZOBS, "obs": OBS, "se": SE, "mu_implied": MU,
       "need_R_written": need_R(Z1S), "need_R_noDiscount": (Z1S / ZOBS) ** 2,
       "need_R_power80": need_R(Z1S + 0.842), "R_lo": R_LO, "R_hi": R_HI, "R_est_favorable": R_EST,
       "cond2_ratio": CEIL / mde_back, "opened_back_data": False}
json.dump(out, open(os.path.join(HERE, "..", "data", "149a-precheck.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n⛔ 뒤 구간(2012~)을 «열지 않았다». score() 를 import 하지 «않았다». N 은 그대로다.")

# ── §8 «구성적» 쪽 — 두뇌 세션 요청. 🚨 그쪽 수 «둘»을 정정한다 ────────────────
print("")
print("## §8-① 민감도가 «둘» 있다 — 두뇌 세션의 31.5배는 «다른» 계산이다")
print("   | z95 | (i) 하한을 1.645 «고정» | (ii) z95 를 «양쪽 다» |")
print("   |---|---|---|")
for z95 in (1.55, 1.645, 1.75, 1.8262):
    a = need_R(z95)
    d = ZOBS - z95
    b = float("inf") if d <= 0 else (z95 / d) ** 2
    fm = lambda v: "∞" if v == float("inf") else "%.1f배" % v
    print("   | %.4f | %s | %s |" % (z95, fm(a), fm(b)))
print("   ⇒ 두뇌 세션 값은 (ii). **두 계산이 다르므로 「검산 일치」로 묶으면 안 된다**")
print("   ★ 그래도 결론 불변 — 최저 **31.5배** vs 있는 것 1.81배 = **17배 모자람**")

print("")
print("## §8-② 「z=3.00 이면 있다」 — 🚨 괄호의 «유리한» 끝에서만 참이다")
print("   | 앞 z | 필요 R | R=1.81(유리) | R=1.15(불리) |")
print("   |---|---|---|---|")
for z in (1.8262, 2.00, 2.50, 3.00, 3.18):
    r = (Z1S / (z - Z1S)) ** 2
    print("   | %.2f | %.2f배 | %s | %s |"
          % (z, r, "✅" if 1.81 > r else "⛔", "✅" if 1.15 > r else "⛔"))
ZB_HI, ZB_LO = Z1S + Z1S / (1.81 ** 0.5), Z1S + Z1S / (1.15 ** 0.5)
print("   유리한 끝 → 필요 z = **%.4f**   ·   불리한 끝 → 필요 z = **%.4f**" % (ZB_HI, ZB_LO))
print("   ⇒ 정직한 문장은 「z=3.00 이면 된다」가 아니라 **「z >= %.2f ~ %.2f 이어야 한다」**"
      % (ZB_HI, ZB_LO))

print("")
print("## §8-③ ★★ 그리고 우연이 아닌 것")
print("   148 이 «앞 구간»에 세운 max-T 문턱   = **%.4f**" % THR148)
print("   유보 자료가 «쓸 수 있게» 되는 z      = **%.2f ~ %.2f**" % (ZB_HI, ZB_LO))
print("   ⇒ **앞에서 세운 바로 그 문턱이, 뒷자료가 쓸모 있어지는 지점과 «거의 같다».**")
print("   ⇒ 문턱이 «두 번» 값어치를 한다 — 다중비교를 갚는 값이자, 유보 자료를 «쓸 수 있게» 하는 값")

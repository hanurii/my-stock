"""검출기·관문·매매값 중 「27.4년 백테스트」와 「사용자 결정」에 매인 것들이
그때와 같은지 검산한다.

왜 있나: 27.4년 백테스트(커밋 e8cd65ae, 「150 최종 확정」)가 그 값으로 돌았다.
값이 하나라도 바뀌면 그 27.4년은 이 스킬의 검증이 아니게 된다. 「같다」를
주장으로 남기지 않고 «출력값»으로 낸다.

기준 커밋이 «둘»이다 — 이 저장소의 수들은 서로 다른 결정 시점에 속한다.
검출기·관문 값은 e8cd65ae(백테스트가 돈 그 순간) 것이어야 하지만,
strategy_params.py 는 사용자가 바로 다음 날 41db459d(2026-09-02, 「익절
+20 에서 +30 으로」)로 «스스로» 바꿨다. e8cd65ae 하나로 strategy_params.py 를
재면 사용자의 그 결정 «자체»를 결함으로 찍는다. 그래서 대상마다 자기 기준
커밋을 따로 붙인다(각 표의 ref 칸).

그리고 기준이 «커밋»뿐인 것도 아니다. 미국 실전 파일 셋
(screen_trend_template_us.py · canslim_lib/us_matrix.py · us_seam.py)은
e8cd65ae 에 «존재하지 않았다» — 없는 커밋과는 견줄 수가 없다.
(셋 중 앞의 둘이 ⑤ 교차 검산의 대상이고, us_seam.py 는 얼릴 값이 없어
 제외한다 — 사유는 EXCLUDED_FILES 에 코드 확인과 함께 적혀 있다.) 그래서 그 파일들에는
물음을 바꾼다: 「커밋 X 이후 안 바뀌었나」가 아니라 **「27.4년 하네스가
«쓴 값»과 «같은가»」**다(⑤ 교차 검산). 하네스 쪽 값은 글자로 베껴 적지 않고
git show 로 «읽어» 견준다 — 베껴 적으면 같은 것을 가리키는 자가 둘이 되고
규약상 멈춰야 한다. 화면에도 「기준 커밋 없음 — 하네스 일치로 얼림」으로
따로 찍는다(조용히 섞으면 읽는 사람이 「커밋과 견줬다」로 오해한다).

■ 이 관문이 «실제로» 보는 범위 — 아래가 곧 코드의 표다.
  (넓게도 좁게도 안 쓰려고, 사람이 세는 대신 «표에서 나온 수»를 화면에 찍는다.)

  ① DICT_TARGETS — 검출기 넷(vcp·power_play·cheat·ipo_track)의 DEFAULT_PARAMS
     dict 를 키 하나하나 대조. 기준 e8cd65ae.
  ② CONST_TARGETS — 그 파일의 모듈최상위 대문자 상수 «전부»를 자동 수집해
     대조한다. 이름을 손으로 나열하지 않는다. 지금 다섯 파일이다 —
     strategy_params.py(기준 41db459d) · us_loader.py · minervini_filter.py ·
     liveness.py · ohlcv_matrix.py(넷 다 기준 e8cd65ae).
  ③④ SCALAR_TARGETS — trend_template.py 일곱 + screen_trend_template.py 둘을
     이름별로 대조. 기준 e8cd65ae.
  ⑤ 교차 검산 — 기준 커밋이 «없는» 새 미국 실전 파일의 값. 두 갈래다.
     · CROSS_TARGETS  — 하네스에 «짝이 있는» 이름을 그 짝과 견준다
       (screen_trend_template_us.RS_MIN ↔ 하네스 RS_MIN 등). 기준 쪽 값은
       git show 로 «읽는다».
     · DERIVED_TARGETS — 짝이 이름으로는 없지만 기준 커밋의 관문 상수에서
       «계산»되는 값(us_matrix.TRIM_BARS 는 trend_template 의 창+되돌아보기에서
       나오고, us_matrix.KEYS 는 us_loader 가 만드는 계열의 키다). 계산식이
       내는 수를 이 글에 적지 않는다 — 화면에 찍히는 수가 정본이다.
  ⑥ 상수 분류 검산 — ①②③④⑤ 표에 «한 번이라도» 나온 파일 전부에 대해
     「모듈최상위 대문자 상수가 빠짐없이 덮음 아니면 제외로 설명되는가」를
     검산한다. 미분류가 하나라도 남으면 그 파일에서 관문이 실패한다.
     대상 파일 목록을 손으로 적지 않는다 — _covered_file_basis() 가 ①②③④⑤
     표에서 끌어낸다. ⑥ 자신은 기준 커밋을 «안 읽는다» — 「지금 판에
     설명 안 된 상수가 있나」를 묻는 검산이라 그게 맞다. 화면에 찍히는 기준
     은 ①②③④⑤ 가 «값»을 견준 기준이라는 표시이고, 커밋 기준인지 「커밋
     없음 — 하네스 일치」인지를 파일마다 구분해 찍는다.
     검출기 넷은 지금 DEFAULT_PARAMS 하나뿐이라 미분류 0 이
     나오지만 목록에서 빠지지 않는다(표에 있으니 자동으로 들어온다).
  ⑦ 파일 분류 검산 — «뿌리 여럿»(ROOTS)의 전이 import 폐포를 각각 코드로
     떠서 합친 것이 모집단이다. 그 안의 파일 «전부»가 덮음 아니면
     제외(사유 필수)로 설명되는가를 검산한다. 미분류 파일이 하나라도 남으면
     관문이 실패한다. 폐포의 «수»를 이 글에 적지 않는다 — 적으면 그 수가
     코드와 갈라진다. 화면에 찍히는 수가 정본이다.
     왜 뿌리가 «여럿»인가: 폐포 «하나»(하네스)로 모집단을 만들면, 하네스가
     import 하지 «않는» 새 실전 파일은 모집단에 아예 안 들어와 관문에
     «보이지» 않는다. 실측으로 screen_trend_template_us.py 의 RS_MIN 을
     80에서 70으로 바꿔도 종료 0 이 났다(고치기 «전»). 관문이 지켜야 할 것은
     「하네스가 읽는 것」이 아니라 「27.4년의 수로 도는 실전 경로 전부」다.

■ 「열거하는 범위가 주장보다 좁다」를 막는 장치 다섯
  (이 파일이 여섯 번 고쳐졌고 여섯 번 다 같은 병이었다 —
   검출기만 봄 → 관문 상수 셋만 → 분류가 한 파일만 → 수집기가 비리터럴을
   조용히 버림 → 파일 «목록» 자체가 손 목록이고 잔여를 안 셈 →
   «뿌리»가 하나라 그 뿌리가 import 안 하는 실전 파일이 모집단 밖):

  (가) 수집은 «빠뜨리지» 않고, 따로 «모양을 센다». 두 걸음이다.
      첫째, _harvest_constants() 는 모듈 스코프에서 대문자 이름에 묶이는
      값을 «전부» 담는다 — 모듈 최상위뿐 아니라 if·try·for·while·with
      «안»의 대입도, 튜플 대입도, AugAssign 도 담는다. 한 이름에 대입이
      «여럿»이면 하나를 골라 보지 않고 «전부»를 이은 글자로 견준다
      (화면에 「다중/중첩 대입」으로 찍힌다). 그래서
      TT_LOW_MIN_PCT = 30.0 뒤에 += 5.0 을 두면 기준 커밋의 [값] 30.0 과
      달라져 「다름」이 난다 — 예전 판은 [값] 30.0 대 [값] 30.0 「같음」을
      찍고 종료 0 을 냈다. 모듈의 실제 값은 35.0 인데도.
      둘째, _uncollected_shapes() 가 «모양 자체»를 따로 센다. AugAssign·튜플
      대입·for 문의 대상·with as 대상은 0 이 아니면 관문을 실패시킨다.
      수집만으로 충분하지 않은 까닭: 수집은 「값이 다르다」만 말하고,
      「사람이 읽기 어려운 모양이 새로 들어왔다」는 그 자체로 고쳐야 할
      일이다. 두 겹이라 한 쪽이 새도 다른 쪽이 잡는다.
      이 검사가 «질 수 있는» 것을 심어서 확인했다(시험 d·e) — 항등식이
      아니다. 실제로 us_loader.py 의 SHARADAR(if/else 안에서 세 번 대입된다)을
      이 장치가 다섯째 고침의 첫 실행에서 찾아냈다.

  (나) 리터럴로 못 읽는 값은 «대입 오른쪽의 원시 글자»로 견준다.
      지금 판과 기준 커밋 판 «양쪽»에 ast.unparse 를 써서 뽑으므로 공백·따옴표
      차이로 오탐이 나지 않는다. 읽은 방식은 화면에 「값」/「글자」로 찍는다 —
      「글자로 견줌」이 섞여 있다는 걸 사람이 알아야 한다.
      예전 판은 ast.literal_eval 이 실패하면 그 이름을 «조용히 건너뛰어»
      덮음·제외·미분류 «세 곳 모두»에서 사라지게 했다. 미분류 관문이 이걸 못
      잡는 까닭은 하나다 — 미분류는 «셀 수 있는» 것만 센다.

  (다) 덮음 목록을 «손으로 또» 적지 않는다. _covered_names() 가
      DICT_TARGETS·CONST_TARGETS·SCALAR_TARGETS 라는 «실제 비교 표»에서
      덮음 집합을 끌어낸다. 표에 없는 이름은 자동으로 제외 아니면 미분류다.

  (라) «파일 목록»도 손으로 적지 않는다. _import_closure() 가 뿌리(ROOTS)
      마다 import 를 따라가며 저장소 내부 파일을 모으고, 그 폐포들을 합친다.
      손으로 적는 것은 «뿌리»뿐이다 — 「어디서부터 따라갈 것인가」이지
      「어느 파일이 들어 있나」가 아니다. from 패키지 import 모듈
      (ImportFrom 의 module 이 패키지이고 names 가 모듈인 꼴)과 상대 import
      (from .management import ...), 함수 «안»의 import(하네스 305행의
      import us_loader) 셋을 다 푼다 — 앞의 두 꼴을 못 풀면 폐포가 조용히
      작아지고, 그게 바로 이 파일이 걸린 그 병이다.

  (마) 덮음·제외·미분류의 «셈»이 실제로 깨질 수 있어야 한다.
      세 칸을 한 집합의 «분할»로 만들면 셋의 합은 항등식이 되어 「셈 안 맞음」
      관문이 «질 수가 없다». 그래서 제외 칸은 덮음 여부를 «빼지 않고» 센다 —
      한 이름(또는 한 파일)이 덮음과 제외에 «둘 다» 올라 있으면 합이 전체보다
      커져서 관문이 실패한다. 상수 층(⑥)과 파일 층(⑦) 둘 다 같은 방식이다.

■ 「제외」의 기준 넷과 «순서» — 기준을 한 번만 적고, 항목마다 꼬리표를 단다.
  (사유가 넷에 섞여 얹혀 있으면, 다음 상수가 왔을 때 어느 것을 대는지
   정한 곳이 없어 어느 쪽으로든 사후 정당화가 된다.)

  · 도달성 — 하네스가 이 코드경로를 안 부른다
  · 성격   — 판정 문턱이 아니라 목적지·시간대·표시·다른 시장 것이다
  · 출처조사 — 원전이 갈려 별도 조사 대상이다
  · 산출물종류 — 스킬이 아니라 연구용 하네스 파일이다

  순서 규칙: «도달성만으로는 제외하지 않는다» — 소비자가 하나뿐이라는 가정에
  기대는데, 그 가정은 미국 SEPA 스킬이 생기는 순간 깨진다. «성격»으로
  제외한다. 도달성은 «보조» 사유로만 적는다.
  그리고 망설여지면 덮음 쪽으로 기운다 — 덮음이 틀리면 헛경보, 제외가 틀리면
  놓침이라 비대칭이다.

■ 「이 범위 밖」 목록을 이 글에 «한 벌 더» 적지 않는다.
  EXCLUDED_FILES(파일 층)와 EXCLUDED_SCALARS(상수 층)에 기준 꼬리표와 함께
  적혀 있고 화면에도 찍힌다. 두 곳에 적으면 갈라지고, 갈라진 쪽이 바로
  「범위가 주장보다 좁다」의 발원지였다.

이 스크립트는 읽기만 한다 — 검출기·관문·매매 값을 고치지 않는다.

실행: python scripts/verify_frozen_params.py
같으면 종료 코드 0, 하나라도 다르면(또는 읽기 실패·미분류가 있으면) 1.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

# 저장소 뿌리 — 이 파일(scripts/verify_frozen_params.py) 위치에서 «파생»된다.
# 폐포를 뜰 때 모듈 이름을 파일로 푸는 기준 자리다. cwd 에 기대지 않는다:
# 다른 디렉터리에서 불러도 같은 모집단이 나와야 한다.
_REPO_ROOT = Path(__file__).resolve().parents[1]

# Windows 콘솔 기본 코드페이지(cp949 등)가 한글 출력을 깨뜨리는 걸 막는다
# (이 저장소의 다른 스크립트들도 같은 방식을 쓴다, 예: scripts/_calib_coil.py).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 상수를 «어떻게 읽었는가» 표식 — 화면에 그대로 찍는다.
READ_VALUE = "값"     # ast.literal_eval 로 읽은 실제 값
READ_SOURCE = "글자"  # 리터럴이 아니라 대입 오른쪽의 원시 글자(ast.unparse)

# ── ① 검출기 DEFAULT_PARAMS dict — 전부 27.4년 백테스트 원 커밋 기준 ──────
DICT_TARGETS = [
    ("scripts/canslim_lib/vcp.py", "DEFAULT_PARAMS", "e8cd65ae",
     "27.4년 백테스트 원 커밋(150 최종 확정)"),
    ("scripts/canslim_lib/power_play.py", "DEFAULT_PARAMS", "e8cd65ae",
     "27.4년 백테스트 원 커밋(150 최종 확정)"),
    ("scripts/canslim_lib/cheat.py", "DEFAULT_PARAMS", "e8cd65ae",
     "27.4년 백테스트 원 커밋(150 최종 확정)"),
    ("scripts/canslim_lib/ipo_track.py", "DEFAULT_PARAMS", "e8cd65ae",
     "27.4년 백테스트 원 커밋(150 최종 확정)"),
]

# ── ② 상수 이름을 손으로 나열하지 않는다. ────────────────────────────
# _harvest_constants() 가 모듈 최상위의 «모든 대문자 상수»를 스스로 찾는다.
#
# 🚨 2026-09-17 — strategy_params.py 를 이 목록에서 «뺐다».
#   이 검산기는 「미국 27.4년 백테스트가 돈 값에서 실전 도구가 안 벗어났나」를
#   본다. 그런데 strategy_params.py 는 «한국» 정본이다(읽는 곳 일곱이 전부 한국
#   도구 — autobuy 셋·make_order_sheet·screen_buy_recommendations·
#   track_buy_recommendations·이 파일. 미국 도구는 안 읽는다).
#   한국 파일을 미국 백테스트 값에 못 박아 두면, 한 시장의 근거로 다른 시장을
#   묶는 것이 된다 — 헌법 §0 이 금지하는 바로 그것이다.
#   실제로 그 못이 사고를 냈다: 2026-09-02 에 미국 154 판의 +30 이 한국 정본까지
#   따라 들어갔고, 한국 원장은 그동안 +20 으로 성과를 재고 있었다(두 값이 두 주
#   넘게 갈라져 있었다). 2026-09-17 사용자 결정으로 한국은 +20 으로 되돌렸다.
#   한국 값을 지키는 것은 이 검산기가 아니라 훅 guard_canon.py 의 몫이다.
CONST_TARGETS = [
    # ↓ 아래 넷은 다섯 번째 고침에서 «제외»가 아니라 «덮음»으로 올린 파일이다.
    #   폐포 안에 있고, 미국 27.4년 판정에 «드는 수»를 갖고 있다.
    #   왜 제외가 아닌가: 「하네스가 안 부른다」류의 «도달성» 사유는 소비자가
    #   하나뿐이라는 가정에 기대는데, 미국 SEPA 스킬이 생기면 그 가정이 깨진다.
    #   그리고 덮음이 틀리면 헛경보, 제외가 틀리면 놓침이다(비대칭).
    ("scripts/us_loader.py", "e8cd65ae",
     "미국 «유니버스를 정의»한다 — EXCHANGES(상장 거래소)·BASE_CATEGORIES/"
     "SEC_CATEGORIES/ADR_CATEGORIES(종목 범주)·SPAC_SIC(스팩 제외 SIC). "
     "하네스 305~308행이 us_loader.build_all(...) 로 «유니버스와 거래대금 "
     "시계열 자체»를 여기서 받는다(코드 확인). 하나라도 바뀌면 27.4년이 "
     "«다른 종목 집합» 위의 결과가 된다."),
    ("scripts/canslim_lib/minervini_filter.py", "e8cd65ae",
     "유동성 관문 — MIN_TURNOVER_EOK_DEFAULT=5.0 · TURNOVER_WINDOW_DAYS=50 · "
     "TURNOVER_MIN_DAYS=20 이 「살 수 있는 종목인가」를 가른다. "
     "도달성으로는 제외 대상이다(screen_trend_template.py:51 이 모듈을 "
     "import 하지만, 하네스는 그 파일에서 _compute_rs_for_all 하나만 "
     "가져가고 하네스 자신의 MIN_TURNOVER_EOK/TURNOVER_WINDOW 를 따로 쓴다 — "
     "코드 확인). 그러나 «성격»이 판정 문턱이고 앞으로의 미국 스킬이 이 "
     "경로를 쓸 것이므로 안전 쪽으로 덮음에 둔다."),
    ("scripts/canslim_lib/liveness.py", "e8cd65ae",
     "거래정지 판정 — HALT_ZERO_VOL_DAYS=5 가 「최근 며칠 거래량 0 이면 "
     "정지로 본다」를 정한다. 하네스 357행이 liveness.is_halted(t, asof=D) 를 "
     "days 없이 부르므로 이 기본값이 «그대로» 쓰인다(코드 확인) — 값이 바뀌면 "
     "27.4년의 유니버스가 달라진다."),
    ("scripts/canslim_lib/ohlcv_matrix.py", "e8cd65ae",
     "분할 보정 — REBASE_MIN_DEVIATION=0.02 · REBASE_RATIO_BOUNDS=(0.05, 20.0) "
     "이 「이 가격 점프를 분할로 볼 것인가」를 가른다(같은 파일 134·136행). "
     "하네스 39~41행이 이 모듈을 import 해 SERIES_DIR·FOREIGN_PATH 를 "
     "«실행 중에» 갈아끼우므로 구조적으로도 매여 있다."),
]

# ── ③④ trend_template.py + screen_trend_template.py — 「덮음」 목록. ──────
# 이름은 손으로 고르지만, 아래 EXCLUDED_SCALARS 와 짝지어 「이 파일의
# 모듈최상위 대문자 상수 «전부»가 덮음 아니면 제외 둘 중 하나」를 관문이
# 스스로 검산한다(_classify_scalars 참고). 사람이 또 빠뜨리면 「미분류」로
# 걸려 관문이 실패하지, 조용히 안 넘어간다.
SCALAR_TARGETS = [
    ("scripts/canslim_lib/trend_template.py", "TT_LOW_MIN_PCT", "e8cd65ae",
     "조건⑥ c6_pass 에 무조건(파라미터화 안 됨) 쓰인다 — 호출자가 못 바꾼다."),
    ("scripts/canslim_lib/trend_template.py", "TT_HIGH_MAX_PCT", "e8cd65ae",
     "조건⑦ c7_pass 에 무조건 쓰인다 — 호출자가 못 바꾼다."),
    ("scripts/canslim_lib/trend_template.py", "TT_SMA200_RISING_LOOKBACK_DAYS", "e8cd65ae",
     "조건③ c3_pass(sma200 > sma200_1m_ago) 계산에 무조건 쓰인다."),
    ("scripts/canslim_lib/trend_template.py", "SMA_WINDOW_50", "e8cd65ae",
     "sma50 을 만들고 조건④⑤가 그 값을 무조건 쓴다 — 호출자가 못 바꾼다."),
    ("scripts/canslim_lib/trend_template.py", "SMA_WINDOW_150", "e8cd65ae",
     "sma150 을 만들고 조건①②④가 그 값을 무조건 쓴다 — 호출자가 못 바꾼다."),
    ("scripts/canslim_lib/trend_template.py", "SMA_WINDOW_200", "e8cd65ae",
     "sma200 을 만들고 조건①②③④가 그 값을 무조건 쓴다 — 호출자가 못 바꾼다."),
    ("scripts/canslim_lib/trend_template.py", "WINDOW_52W", "e8cd65ae",
     "high_52w/low_52w 를 만들고 조건⑥⑦이 그 값을 무조건 쓴다 — 호출자가 못 바꾼다."),
    ("scripts/screen_trend_template.py", "MIN_RS_COMPARISON_POOL", "e8cd65ae",
     "_compute_rs_for_all(min_pool=이 값) 기본값 — 하네스가 min_pool 없이 "
     "부르므로(backtest_volatility_pilot_us.py:371) «호출자가 대체 안 하는» "
     "쪽. 표본이 모자라면 RS=None 이 되어 조건⑧이 자동 탈락한다."),
    ("scripts/screen_trend_template.py", "MIN_CLOSES_FOR_TT", "e8cd65ae",
     "«도달성»으로는 제외 대상이다 — 하네스는 이 파일에서 _compute_rs_for_all "
     "하나만 가져가고(backtest_volatility_pilot_us.py:51), 이 상수를 쓰는 "
     "_fetch_closes(88·93행)·_collect_one(140행)은 «그 함수가 부르지 않는다»"
     "(코드 확인). 그러나 «성격»이 「종가 개수가 이보다 적으면 아예 평가하지 "
     "않는다」는 평가 여부의 문턱이고, 앞으로의 미국 SEPA 스킬이 이 경로를 쓸 "
     "것이므로 안전 쪽으로 덮음에 둔다(덮음이 틀리면 헛경보, 제외가 틀리면 "
     "놓침). 값이 리터럴이 아니라 SMA_WINDOW_200 을 가리키는 «이름 참조»라 "
     "글자로 견준다 — 예전 판은 바로 이 때문에 이 이름을 수집 단계에서 "
     "조용히 버렸다."),
]

# ── ⑦ 파일 층 — 「어느 파일을 볼 것인가」도 손으로 적지 않는다. ──────────
# 이 관문이 지켜야 할 파일의 «모집단»은 「27.4년의 수로 도는 경로가 읽을 수
# 있는 것 전부」다. 뿌리 «하나»(하네스)의 폐포로는 그것을 못 덮는다 —
# 하네스가 import 하지 «않는» 실전 파일은 폐포 밖이라 관문에 «보이지» 않는다.
# 그래서 뿌리를 여럿 두고 각 뿌리의 전이 import 폐포를 «따로» 떠서 합친다.
# 폐포는 _import_closure() 가 코드로 뜬다. 손으로 적는 것은 «뿌리»뿐이고,
# 뿌리는 「어디서부터 따라갈 것인가」이지 「어느 파일이 들어 있나」가 아니다.
# 폐포의 «수»를 여기 적지 않는다 — 적는 순간 코드와 갈라진다.
ROOTS: list[tuple[str, str]] = [
    ("scripts/backtest_volatility_pilot_us.py",
     "27.4년 하네스 — 얼린 값이 «나온» 자리"),
    ("scripts/screen_trend_template_us.py",
     "미국 실전 1단계 — 얼린 값을 «쓰는» 자리(e8cd65ae 에 «없던» 파일)"),
    ("scripts/us_seam.py",
     "미국 실전 이음매 — 1단계가 읽는 뼈대·꼬리를 만드는 자리(e8cd65ae 에 «없던» 파일)"),
]

# 교차 검산(⑤)의 «기준 쪽». 27.4년이 돈 그 값이 정본이다.
FROZEN_HARNESS = ROOTS[0][0]
HARNESS_REF = "e8cd65ae"

# ── ⑤ 교차 검산 — 기준 커밋이 «없는» 파일의 값을 무엇과 견주나 ──────────
# 이 파일들은 e8cd65ae 에 존재하지 «않았다». 「그 커밋과 같은가」는 물을 수
# 없으므로 물음을 바꾼다 — 「27.4년 하네스가 «쓴 값»과 «같은가」.
# 기준 쪽 값을 여기에 «글자로 베껴 적지 않는다». 베껴 적으면 같은 것을
#    가리키는 자가 둘이 되고 규약상 멈춰야 한다. git show 로 «읽어» 견준다.
#
# (live_path, live_name, ref_path, ref_name, ref, 사유)
CROSS_TARGETS: list[tuple[str, str, str, str, str, str]] = [
    ("scripts/screen_trend_template_us.py", "RS_MIN",
     FROZEN_HARNESS, "RS_MIN", HARNESS_REF,
     "RS 합격선. 하네스가 evaluate_trend_template(..., rs_min=RS_MIN) 로 «자기 "
     "값을 명시로» 넘기므로(backtest_volatility_pilot_us.py:377) 27.4년은 이 "
     "수로 돌았다. 1단계가 다른 수를 쓰면 후보 집합 «자체»가 달라진다 — "
     "한국판 기본값 TT_RS_MIN_DEFAULT(70)로 흘러내리는 길이 실제로 있다."),
    ("scripts/screen_trend_template_us.py", "US_VARIANT",
     FROZEN_HARNESS, "US_VARIANT", HARNESS_REF,
     "유니버스 «판»(us_loader.load_tickers 의 variant). 27.4년이 «어느 종목 "
     "집합» 위의 결과인지를 정한다 — 바뀌면 같은 규칙이라도 다른 시장을 "
     "재는 것이 된다."),
]

# 짝이 «이름»으로는 없지만 기준 커밋의 관문 상수에서 «계산»되는 값.
# 계산기는 _REF_CALCS 에 등록한다(함수가 아래에 정의되므로 이름으로 가리킨다).
# 관계는 "==" 또는 ">=" 다 — 어느 쪽인지 화면에 찍는다.
# (live_path, live_name, ref, 관계, 계산기 이름, 사유)
DERIVED_TARGETS: list[tuple[str, str, str, str, str, str]] = [
    ("scripts/canslim_lib/us_matrix.py", "TRIM_BARS", HARNESS_REF, ">=",
     "needed_bars",
     "뼈대를 몇 봉으로 다듬나. 이 수가 모자라면 관문이 «조용히» 달라진다 — "
     "trend_template.py 의 _sma 는 needed = window + end_offset 보다 짧으면 "
     "None 을 돌려주고, 52주 수익률은 closes[-WINDOW_52W - 1] 을 읽으며, "
     "RS 는 win = min(n - 1, WINDOW_52W) 로 «단축 기준»이 된다"
     "(screen_trend_template.py:191). 값을 베껴 적지 않고 기준 커밋의 관문 "
     "상수에서 «계산»해 견준다. 관계가 «>=» 인 까닭: 봉이 더 많아도 모든 창이 "
     "끝에서 세므로 판정이 안 바뀐다(모자라면 바뀐다) — 비대칭이다."),
    ("scripts/canslim_lib/us_matrix.py", "KEYS", HARNESS_REF, "==",
     "series_keys",
     "뼈대가 실어 나르는 계열 «필드 이름»이다. trim_series 가 이 키만 남기므로 "
     "하나가 빠지면 그 자료가 조용히 사라진다 — volumes 가 빠지면 거래정지 "
     "판정(liveness)과 유동성 관문이 둘 다 달라진다. 기준은 e8cd65ae 판 "
     "us_loader 가 «만드는» 계열 dict 의 키다(코드로 뽑는다)."),
]

# 폐포 안의 모듈 이름을 저장소 파일로 풀 때 뒤지는 자리(하네스가 sys.path 에
# 넣는 자리와 같다 — backtest_volatility_pilot_us.py:38).
IMPORT_SEARCH_ROOTS = ("scripts", "scripts/canslim_lib", "")

# ── 폐포 안인데 «덮지 않는» 파일 — {path: (기준이름, 사유)} ──────────────
# 기준 이름 넷과 순서 규칙은 이 파일 맨 위 docstring 에 한 번 적혀 있다.
# 「도달성만으로는 제외하지 않는다 — 성격으로 제외하고 도달성은 보조로 적는다.」
# 사유는 전부 «코드를 직접 읽고» 적었다(짐작 금지).
# 여기에도 덮음 표에도 없는 파일은 ⑥ 에서 「미분류」로 걸려 관문이 실패한다.
EXCLUDED_FILES: dict[str, tuple[str, str]] = {
    FROZEN_HARNESS: (
        "산출물종류",
        "27.4년 하네스 «자신»이다. 이 관문이 지키는 것은 미국 SEPA 스킬이 쓸 "
        "값이고, 하네스는 스킬이 아니라 그 값을 «검증한 도구»다. 연구 각본은 "
        "앞으로도 고쳐지므로 얼리면 헛경보가 상시로 난다. "
        "(보조: 그래도 이 파일의 모듈최상위 대문자 상수 32개를 e8cd65ae 와 "
        "코드로 전수 대조했고 다른 것 0개다 — RS_MIN=80·TARGET_PCT=20.0·"
        "STOP_PCT=10.0 포함. 수동 확인이고 자동 검산 대상은 아니다.)"),
    "scripts/canslim_lib/criteria.py": (
        "출처조사",
        "RS 문턱(L_RS_MIN) 등 오닐 80·미너비니 70·대담 약 50 으로 «원전이 "
        "갈리는» 값이라 별도 조사 대상이다. 정본: "
        "research/handoff/scripts/204-param-provenance.py 의 Ⓑ류 항목."),
    "scripts/canslim_lib/__init__.py": (
        "성격",
        "모듈최상위 대문자 상수가 «0개»다(docstring 뿐 — 코드 확인). "
        "얼릴 값이 아예 없다."),
    "scripts/pathsink.py": (
        "성격",
        "상수가 NL = chr(10) «하나»뿐이다. 줄바꿈 문자이지 연구로 «고르는» "
        "수가 아니다. 쓰이는 곳 49·78·85·88행 전부 파일에 글자를 쓰는 자리다."),
    "scripts/canslim_lib/dart_cache.py": (
        "성격",
        "다섯 다 캐시 «경로»다(ROOT 는 파일 위치에서 파생, 나머지 넷은 그 "
        "밑의 디렉터리). 판정 문턱이 하나도 없다. "
        "(보조: 한국 DART 분기실적 캐시라 미국 경로가 안 읽는다.)"),
    "scripts/canslim_lib/fetch.py": (
        "성격",
        "열여섯 다 경로·HTTP 헤더·API URL·요청 간격·모듈 내부 상태다"
        "(_LAST_REQUEST_AT·_DART_EXHAUSTED 는 런 중에 «변하는» 값이지 설정이 "
        "아니다). 판정 문턱이 없다. EXCLUDE_PATTERN 은 한국 우선주·리츠·스팩 "
        "이름 정규식인데 미국 유니버스는 us_loader.SPAC_SIC 로 거른다"
        "(그 값은 ② 에서 얼린다)."),
    "scripts/canslim_lib/halt_reason.py": (
        "성격",
        "경로 둘과 «한국 DART 공시 제목» 정규식·키워드 다섯이다"
        "(_HALT_NOTICE 「주권매매거래정지」 등). 미국 티커에는 대응물이 없다. "
        "(보조: 하네스의 정지 판정은 liveness.is_halted 하나로 하고 이 모듈을 "
        "부르지 않는다 — liveness.py 에 halt_reason import 가 없다, 코드 확인. "
        "폐포에는 screen_trend_template.py:53 을 통해 들어왔다.)"),
    "scripts/canslim_lib/kis_api.py": (
        "성격",
        "한국투자증권 REST 접속 값이다 — BASE_REAL/BASE_VPS 주소, 토큰 캐시 "
        "경로, 호출 간격(_MIN_INTERVAL_SEC)·만료 여유(_TOKEN_LEEWAY_SEC). "
        "전부 «통신»을 정하지 «판정»을 정하지 않는다."),
    "scripts/canslim_lib/management.py": (
        "성격",
        "한국 DART 지배구조 «점수» 가중치 여덟과 등급 경계 둘이다"
        "(W_BUYBACK_* · TIER_EXCELLENT_MIN 등). 미국 백테스트의 진입·청산 "
        "판정식에 들어가지 않는다. "
        "(보조: classify_management 를 부르는 곳은 build_management_quality.py "
        "하나뿐이고, 폐포에는 halt_reason.py:194 의 「from .management import "
        "fetch_disclosure_list」 — «함수» 하나 — 를 통해 들어왔다.)"),
    "scripts/canslim_lib/pdata.py": (
        "성격",
        "한국 공공데이터포털 API 엔드포인트 셋과 캐시 경로·User-Agent 다. "
        "미국 자료는 Sharadar zip(us_loader)에서 온다."),
    "scripts/canslim_lib/pdata_series.py": (
        "성격",
        "둘 다 «한국 시장 구분»이다 — _MARKETS=(\"KOSPI\", \"KOSDAQ\")(코넥스 "
        "제외)와 _FOREIGN(코스닥 외국법인 9xxxxx 코드 정규식). 67행에서 한국 "
        "종목만 걸러내는 데 쓴다. "
        "(보조: 하네스 319~323행의 build_pdata_series 는 SERIES_SOURCE == "
        "\"pdata\" 일 때만 도는 한국 갈래이고, 미국은 317행 MARKET == \"us\" "
        "갈래로 _US_CACHE 를 쓴다 — 코드 확인.)"),
    "scripts/canslim_lib/pivot_backtest.py": (
        "성격",
        "PRICE_BUCKETS «하나»뿐인데, 이건 원화 가격대 «라벨»이다"
        "(2천·5천·1만·2만·5만원). price_bucket() 의 결과가 들어가는 곳은 "
        "하네스 497행의 결과 칸 하나와 544행 by_price 요약 둘뿐이고, 진입·"
        "청산 판정식에는 «안» 들어간다(코드 확인). 라벨이 바뀌어도 거래는 "
        "한 건도 안 달라진다."),
    "scripts/us_seam.py": (
        "성격",
        "모듈최상위 대문자 상수가 ROOT «하나»뿐이고 그것은 "
        "Path(__file__).resolve().parents[1] — 파일 위치에서 «파생되는» 값이다. "
        "게다가 이 파일 안에서 «쓰이는 곳이 0곳»이다(24행 정의뿐, grep 확인). "
        "얼릴 「고른 수」가 없다. 이 파일이 쓰는 TAIL_PATH·KEYS·to_timestamp 는 "
        "22행에서 canslim_lib.us_matrix 로부터 «가져다» 쓰는 것이고 정본은 "
        "us_matrix.py 이며 ⑤ 에서 얼린다. "
        "(보조: 그래도 ROOTS 에 «뿌리»로는 넣었다 — 이 파일이 새 모듈을 "
        "import 하면 그 모듈이 모집단에 들어와야 하기 때문이다.)"),
    "scripts/canslim_lib/pykrx_universe.py": (
        "성격",
        "한국 우선주·리츠·스팩 이름 정규식(EXCLUDE_PATTERN)과 pykrx 시장 ID "
        "매핑(_MARKET_ID_MAP = STK/KSQ)이다. 미국 유니버스는 us_loader 가 "
        "만든다(② 에서 얼린다)."),
}

# ── 「제외」 목록(상수 층) — 파일별 모듈최상위 대문자 상수인데 위 표들
# 어디에도 없는 것들. {path: {name: (기준이름, 사유)}} 형태다.
# 기준 이름 넷과 «순서 규칙»은 맨 위 docstring 에 한 번 적혀 있다 —
# 「도달성만으로는 제외하지 않는다. 성격으로 제외하고 도달성은 보조로 적는다.」
# 그 규칙을 지금 «완전히»는 못 지킨다: 아래 다섯은 도달성«만»으로 서 있다.
# 지우거나 몰래 성격으로 바꿔 적지 않고, 기준 꼬리표를 그대로 달아 두고
# main() 이 그 수를 화면에 «따로» 찍는다 — 미국 SEPA 스킬이 생기면 그 다섯이
# 곧 재검토 대상이라는 뜻이다(가정이 깨지는 자리를 숨기지 않는다).
# 관문 밖에 두는 «이유»는 코드를 직접 읽고 적는다(짐작 금지). 이 dict 에도
# 없으면 _classify_scalars() 가 「미분류」로 잡아 그 파일의 관문을 실패시킨다.
EXCLUDED_SCALARS: dict[str, dict[str, tuple[str, str]]] = {
    "scripts/canslim_lib/trend_template.py": {
        "TT_SMA200_RISING_PREFERRED_DAYS": (
            "성격",
            "조건③의 판정문(c3_pass)이 아니라 detail 문자열의 「5M 우수」 "
            "꼬리표에만 쓰인다 — 통과/탈락과 무관."),
        "TT_RS_MIN_DEFAULT": (
            "도달성",
            "27.4년 하네스(backtest_volatility_pilot_us.py:377)가 "
            "evaluate_trend_template(..., rs_min=RS_MIN) 로 «항상» 자기 값을 "
            "명시로 넘긴다 — 이 기본값은 호출자가 안 줬을 때만 쓰이는데 그런 "
            "일이 없으니 얼려봤자 지키는 게 없다. "
            "[재검토] 성격은 «판정 문턱»이라 순서 규칙대로면 덮음 후보다."),
        "GATE_MARGIN_REF": (
            "성격",
            "compute_gate_margin() 의 «화면 표시»용 기준선 이름이다 — 통과/"
            "탈락을 정하는 식이 아니라 「얼마나 모자랐나」를 사람에게 보여주는 "
            "값이다. (보조: backtest_volatility_pilot_us.py 는 이 함수를 아예 "
            "안 부른다 — grep 확인.)"),
        "GATE_MARGIN_LABEL": (
            "성격",
            "compute_gate_margin() 이 찍는 «라벨 글자»다 — 위와 같은 이유."),
    },
    "scripts/screen_trend_template_us.py": {
        "ROOT": (
            "성격",
            "Path(__file__).resolve().parents[1] — 이 파일 위치에서 «파생되는» "
            "저장소 뿌리다(사람이 고르는 수가 아니다). 쓰이는 곳 셋을 다 봤다 — "
            "53행 sys.path.insert, 82행 OUTPUT_PATH 조립, 397행 relative_to "
            "«표시»(grep 확인). 관문 판정식에 안 들어간다."),
        "OUTPUT_PATH": (
            "성격",
            "결과 저장 «목적지»다. 쓰이는 곳 넷을 다 봤다 — 392행 mkdir, 393행 "
            "임시파일 이름, 396행 replace, 397행 이름 출력. 이 파일에는 "
            "read_text 도 json.load 도 open( 도 «한 곳도 없어»(grep 확인) 쓴 것을 "
            "되읽어 판정에 쓰는 경로가 아예 없다."),
        "UTC": (
            "성격",
            "timezone.utc — 시간대다. 쓰이는 곳이 351행 generated_at 도장 "
            "«하나»뿐이다(grep 확인). 한국판 screen_trend_template.py 의 KST 와 "
            "같은 종류이고 같은 사유로 제외한다."),
    },
    "scripts/canslim_lib/us_matrix.py": {
        "ROOT": (
            "성격",
            "Path(__file__).resolve().parents[2] — 파일 위치에서 «파생되는» "
            "저장소 뿌리다. 쓰이는 곳은 15·20행의 캐시 경로 조립과 104행 "
            "sys.path.insert 뿐이다(grep 확인)."),
        "BASE_PATH": (
            "성격",
            "뼈대 캐시 파일의 «자리»다(.cache/us/base.json). 쓰이는 곳 셋을 다 "
            "봤다 — 53행 load_base 의 기본 경로, 71행 load_latest 의 «없을 때» "
            "갈래, 110행 build_base 의 기본 저장 자리. 어느 «파일»을 읽고 쓰나를 "
            "정할 뿐 판정 문턱이 아니다. "
            "(보조: 하네스에 이름이 «같은» 상수가 없다 — 견줄 짝이 없다. "
            "하네스는 _US_CACHE 를 실행 중에 채워 쓴다.)"),
        "TAIL_PATH": (
            "성격",
            "꼬리를 붙인 합본 캐시 파일의 «자리»다(.cache/us/tail.json). 쓰이는 "
            "곳은 71행 load_latest 의 존재 검사와 갈래뿐이다(grep 확인). 위와 "
            "같은 종류다. «어느 것을 읽을지 고르는 일»은 71행의 코드가 하지 이 "
            "상수가 하지 않는다."),
        "_BASE": (
            "성격",
            "런 중에 채워지는 «모듈 안 상태»다(38행 선언, 52~55행 load_base 가 "
            "채운다). 설정이 아니라 캐시 변수다 — fetch.py 의 _LAST_REQUEST_AT 를 "
            "같은 사유로 제외한 것과 같은 종류다."),
    },
    "scripts/screen_trend_template.py": {
        "NAVER_DAYS_BACK": (
            "도달성",
            "_fetch_closes() 전용(배치 행렬 조회 일수). 하네스가 이 파일에서 "
            "import 하는 건 _compute_rs_for_all 하나뿐이라(grep 확인) "
            "_fetch_closes 는 호출되지 않는다. "
            "[재검토] 순서 규칙상 재검토 대상 — 미국 스킬이 이 경로를 쓰면 깨진다."),
        "YAHOO_RANGE_FALLBACK": (
            "도달성",
            "_fetch_closes() 전용(야후 폴백 조회 범위). 위와 같은 이유로 "
            "하네스가 이 함수를 아예 안 부른다. [재검토] 순서 규칙상 재검토 대상."),
        "MAX_WORKERS": (
            "성격",
            "main() 의 ThreadPoolExecutor 병렬 «갈래 수»다 — 몇 갈래로 나눠 "
            "받든 받는 «값»은 안 바뀐다. 판정에 들어갈 수가 없는 종류의 수다. "
            "(보조: 하네스가 main() 을 안 부른다.)"),
        "GATE_NEAR_TOL": (
            "도달성",
            "하네스는 «자기 자신»의 GATE_NEAR_TOL_BT 를 따로 갖고 있다"
            "(backtest_volatility_pilot_us.py:208) — 이 파일의 GATE_NEAR_TOL 은 "
            "import 자체를 안 한다(구조적 독립). "
            "[재검토] 성격은 «관문 여유폭»이라 순서 규칙상 재검토 대상."),
        "GATE_NEAR_ENABLED": (
            "도달성",
            "하네스는 «자기 자신»의 GATE_NEAR_ALLOW(기본 빈 set, "
            "backtest_volatility_pilot_us.py:237)로 관문임박을 제어한다 — "
            "이 파일의 GATE_NEAR_ENABLED 는 import 하지 않는다. "
            "[재검토] 순서 규칙상 재검토 대상."),
        "ROOT": (
            "성격",
            "Path(__file__).resolve().parents[1] — 이 파일 위치에서 «파생되는» "
            "저장소 뿌리다(사람이 고르는 수가 아니다). 쓰이는 곳은 42행 "
            "sys.path.insert, 아래 세 출력 경로 조립, 703·710·754행의 "
            "상대경로 «표시»뿐 — 관문 판정식에 안 들어간다(코드 확인)."),
        "OUTPUT_PATH": (
            "성격",
            "결과 저장 «목적지»일 뿐이다. 쓰이는 곳 셋을 다 봤다 — run_full_scan "
            "701행(--out 없을 때 기본 저장 경로), main() 752·754행(argparse "
            "도움말 문구). 이 파일에는 read_text 도 json.load 도 «한 곳도 없어» "
            "쓴 것을 되읽어 판정에 쓰는 경로가 아예 없다(grep 확인)."),
        "HALTED_OUT_PATH": (
            "성격",
            "_save_halted_report() 338행 write_text 와 342행 이름 출력 전용 — "
            "거래정지 «내역을 적는» 곳이지 정지 «판정»을 하는 곳이 아니다"
            "(판정은 halt_reason 모듈). 되읽는 코드 없음."),
        "MINERVINI_OUT_PATH": (
            "성격",
            "_save_minervini_report() 377행 write_text 와 379행 이름 출력 전용 — "
            "제외 «내역을 적는» 곳이지 제외 «판정»을 하는 곳이 아니다"
            "(판정은 minervini_filter 모듈). 되읽는 코드 없음."),
        "KST": (
            "성격",
            "한국 시장 시간대(UTC+9) — 연구 결과로 «고르는» 수가 아니라 시장이 "
            "정하는 값이다. 쓰이는 곳은 야후 epoch 를 날짜 글자로 바꾸는 "
            "95·105·267행과 generated_at 도장 668·673행뿐이고, 미국판(Task 7)은 "
            "이 값을 물려받지 않고 자기 시장 시간대를 쓴다."),
    },
}

_MISSING = object()  # "값이 None/0/False" 와 "애초에 못 찾음" 을 구분하는 표식


def _dict_at(src: str, name: str) -> dict:
    """소스 문자열에서 최상위에 `name`으로 대입된 dict 리터럴을 읽는다.

    `Assign`(`NAME = {...}`, ipo_track.py)과 `AnnAssign`
    (`NAME: dict = {...}`, vcp/power_play/cheat.py) 둘 다 본다 — 이
    저장소의 네 검출기 파일이 두 형태를 섞어 쓴다. 못 찾으면 빈 dict를
    돌려준다(호출부가 이 빈 dict를 「읽기 실패」로 다뤄야 한다 — 이
    함수 자신은 실패와 "원래 비어 있음"을 구분하지 않는다).
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                tgt = getattr(t, "id", None) or getattr(t, "attr", None)
                if tgt == name:
                    return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign):
            if getattr(node.target, "id", None) == name and node.value:
                return ast.literal_eval(node.value)
    return {}


def _harvest_constants(src: str) -> dict[str, tuple[str, object]]:
    """모듈 스코프의 «대문자 이름 상수»를 모은다.

    돌려주는 것은 {이름: (읽은 방식, 견줄 것)}.
      · (READ_VALUE, 값)   — 모듈 최상위 단일 대입 하나뿐이고 literal_eval 로 읽힌 경우
      · (READ_SOURCE, 글자) — 리터럴이 아니거나, 대입이 «여럿»이거나,
        if/try/for/while/with «안»의 대입인 경우. 이때는 대입 하나만
        골라 보지 않고 «전부»를 이은 글자를 견준다 — 한 갈래만 보면
        다른 갈래가 바뀌어도 「같음」이 된다.

    이름을 손으로 나열하지 않는다 — 상수가 늘어도 이 함수는 안 고친다.
    함수·클래스 «안»의 이름은 안 본다(모듈 스코프만).

    못 읽는 값을 «버리지» 않는 까닭: 예전 판은 literal_eval 이 실패하면
    그 이름을 조용히 버렸다. 그러면 덮음에도, 제외에도, 미분류에도
    안 나타난다 — 미분류 관문은 «셀 수 있는» 것만 센다.
    """
    got: dict[str, list[tuple[str, str]]] = {}
    for name, shape, _collectible, value in _assigned_upper_names(src):
        # 값 노드가 있는 것은 «전부» 담는다 — 수집가능여부로 걸러내지
        # 않는다. 걸러내면 AugAssign 이 뒤에 붙은 이름이 「단일 리터럴」로
        # 남아 [값] 30.0 대 [값] 30.0 「같음」을 찍는다 — 모듈의 실제 값은
        # 35.0 인데도. «수집»과 «모양 세기»는 따로 둔다:
        # 여기는 다 담아 값이 «다르게» 보이게 하고,
        # _uncollected_shapes() 가 따로 «모양 자체»를 잡아 두 겹으로 막는다.
        if value is None:
            continue
        got.setdefault(name, []).append((shape, ast.unparse(value)))

    out: dict[str, tuple[str, object]] = {}
    for name, items in got.items():
        if len(items) == 1 and items[0][0] == _SHAPE_PLAIN:
            try:
                out[name] = (READ_VALUE, ast.literal_eval(items[0][1]))
            except Exception:
                out[name] = (READ_SOURCE, items[0][1])
        else:
            out[name] = (READ_SOURCE, "다중/중첩 대입: " + " | ".join(
                f"[{s}] {t}" for s, t in items))
    return out


_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_NEST_NODES = (ast.If, ast.Try, ast.For, ast.AsyncFor, ast.While,
               ast.With, ast.AsyncWith)
_SHAPE_PLAIN = "모듈최상위 단일이름"


def _sub_bodies(node) -> list:
    """if/try/for/while/with 같은 «감싸는» 노드 안의 문장들을 전부 모은다."""
    out: list = []
    for attr in ("body", "orelse", "finalbody"):
        out += list(getattr(node, attr, None) or [])
    for h in getattr(node, "handlers", None) or []:
        out += list(h.body)
    return out


def _target_names(target) -> list[str]:
    """대입 «대상» 안에 들어 있는 이름을 전부 꺼낸다(튜플·리스트·별표 포함)."""
    return [n.id for n in ast.walk(target) if isinstance(n, ast.Name)]


def _assigned_upper_names(src: str):
    """모듈 스코프에서 «대문자 이름을 묶는» 노드를 전부 훑는다.

    돌려주는 것은 [(이름, 모양, 수집가능여부, 값노드)].

    수집가능 = 대상이 «단일 Name» 이면서 Assign 또는 값 있는 AnnAssign.
    모듈 최상위든 if/try/for/while/with 안이든 다 담는다 — 단, 안에 있으면
    모양에 그 사실을 적어 _harvest_constants 가 «글자»로 견주게 한다.

    수집가능이 «False» 인 것 넷 — 이것들이 _uncollected_shapes 에서 관문을
    실패시킨다. 그래서 이 검사는 «질 수 있는» 검사다(항등식이 아니다):
      · AugAssign (X += 1)   — 모듈의 실제 값과 수집한 값이 어깼라진다.
        「못 읽었다」가 아니라 «잘못 읽었다»가 「같다」로 둔갑하는 길이라 제일 무겁다.
      · 튜플·리스트 대입 (A, B = 1, 2)
      · for 문의 대상 (for X in ...)
      · with ... as X 의 대상
    """
    found: list[tuple[str, str, bool, object]] = []

    def scan(body: list, nested: str) -> None:
        for node in body:
            if isinstance(node, _SCOPE_NODES):
                continue  # 함수·클래스 «안»의 이름은 모듈 상수가 아니다
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    simple = isinstance(t, ast.Name)
                    shape = _SHAPE_PLAIN if simple else type(t).__name__ + " 대입"
                    if nested:
                        shape = nested + " 안의 " + shape
                    for nm in _target_names(t):
                        if nm.isupper():
                            found.append((nm, shape, simple, node.value))
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                simple = isinstance(node.target, ast.Name)
                shape = _SHAPE_PLAIN if simple else "AnnAssign(복합)"
                if nested:
                    shape = nested + " 안의 " + shape
                for nm in _target_names(node.target):
                    if nm.isupper():
                        found.append((nm, shape, simple, node.value))
            elif isinstance(node, ast.AugAssign):
                shape = "AugAssign"
                if nested:
                    shape = nested + " 안의 AugAssign"
                for nm in _target_names(node.target):
                    if nm.isupper():
                        found.append((nm, shape, False, node.value))
            elif isinstance(node, _NEST_NODES):
                if isinstance(node, (ast.For, ast.AsyncFor)):
                    for nm in _target_names(node.target):
                        if nm.isupper():
                            found.append((nm, "for 문의 대상", False, None))
                if isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if item.optional_vars is not None:
                            for nm in _target_names(item.optional_vars):
                                if nm.isupper():
                                    found.append((nm, "with as 대상", False, None))
                scan(_sub_bodies(node), nested or type(node).__name__)

    scan(ast.parse(src).body, "")
    return found


def _uncollected_shapes(src: str) -> list[str]:
    """_harvest_constants() 가 «안 담는» 대문자 대입을 이름과 모양으로 돌려준다.

    0 이 아니면 main() 이 관문을 실패시킨다. 「지금 그런 모양이 없다」를
    「앞으로도 없다」로 바꾸는 장치다 — 새 모양이 들어오면 조용히 사라지는
    대신 «걸린다».

    이 검사가 «질 수 있다»는 것을 심어서 확인했다(시험 d·e):
    AugAssign · 튜플 대입 · for 대상 · with as 대상 을 심으면 종료 1 이 난다.
    """
    collected = set(_harvest_constants(src))
    bad: set[str] = set()
    for name, shape, collectible, _value in _assigned_upper_names(src):
        if (not collectible) or name not in collected:
            bad.add(f"{name} ({shape})")
    return sorted(bad)


def _resolve_module(mod: str) -> str | None:
    """점 찍힌 모듈 이름을 «저장소 안» 파일 경로로 푼다. 밖이면 None."""
    parts = mod.split(".")
    for base in IMPORT_SEARCH_ROOTS:
        head = [base] if base else []
        for rel in ("/".join(head + parts) + ".py",
                    "/".join(head + parts + ["__init__.py"])):
            if (_REPO_ROOT / rel).is_file():
                return rel
    return None


def _module_names_in(path: str) -> set[str]:
    """파일 하나가 «부르는» 모듈 이름을 전부 모은다.

    셋을 다 풀어야 폐포가 안 작아진다(넷째·다섯째 고침이 걸린 바로 그 자리):
      · import a.b            — Import
      · from pkg import mod   — ImportFrom 의 «패키지에서 모듈 꺼내기» 꼴.
                                module 만 보면 canslim_lib 만 잡히고
                                ohlcv_matrix 를 놓친다(하네스 39행).
      · from .management ...  — 상대 import(halt_reason.py:194)
    그리고 ast.walk 를 쓴다 — 함수 «안»의 import 도 본다(하네스 305행의
    import us_loader 가 미국 유니버스 전체를 끌고 들어온다).
    """
    tree = ast.parse((_REPO_ROOT / path).read_text(encoding="utf-8"))
    pkg = path.rsplit("/", 1)[0]
    pkg = pkg[len("scripts/"):].replace("/", ".") if pkg.startswith("scripts/") else ""
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                head = pkg.split(".") if pkg else []
                if node.level > 1:
                    head = head[:len(head) - (node.level - 1)]
                base = ".".join([x for x in head if x] + ([base] if base else []))
            if not base:
                continue
            out.add(base)
            for a in node.names:
                out.add(base + "." + a.name)
    return out


def _import_closure(entry: str) -> set[str]:
    """`entry` 부터 import 를 따라가며 «저장소 안» 파일을 전부 모은다.

    뿌리 «하나»의 폐포다. 관문의 모집단은 이것이 아니라 ROOTS 의 모든
    뿌리에 대한 폐포를 «합친» 것이다(_classify_files 참고) — 폐포 하나로
    모집단을 삼으면 그 뿌리가 import 하지 «않는» 파일이 관문에 안 보인다.
    수를 손으로 적지 않는 까닭: 적는 순간 코드와 갈라지고, 갈라진 쪽이
    바로 「범위가 주장보다 좁다」의 발원지였다.
    """
    seen = {entry}
    stack = [entry]
    while stack:
        for mod in sorted(_module_names_in(stack.pop())):
            got = _resolve_module(mod)
            if got and got not in seen:
                seen.add(got)
                stack.append(got)
    return seen


BASIS_COMMIT = "커밋"       # ①②③④ — 「그 커밋 이후 안 바뀌었나」
BASIS_HARNESS = "하네스일치"  # ⑤ — 그 커밋에 파일이 «없어서» 물을 수가 없다
BASIS_CONFLICT = "!충돌"


def _covered_file_basis() -> dict[str, tuple[str, str]]:
    """①②③④⑤ «실제 비교 표»에서 「덮는 파일 → (기준 종류, 기준 커밋)」을 끌어낸다.

    파일 목록을 손으로 또 적지 않는다. 기준 «종류»가 둘이라는 것이 요점이다 —
    새 실전 파일은 기준 커밋이 «없어서» 하네스와의 일치로 얼렸고, 그 사실이
    화면에 보여야 읽는 사람이 「커밋과 견줬다」로 오해하지 않는다.
    한 파일에 기준이 «둘» 붙으면 표가 어긋난 것이므로 그대로 두지 않고
    «!충돌» 로 표시해 관문이 실패하게 만든다(같은 것을 가리키는 수가 둘이면
    멈춘다).
    """
    seen: dict[str, set[tuple[str, str]]] = {}
    for path, _name, ref, _reason in DICT_TARGETS:
        seen.setdefault(path, set()).add((BASIS_COMMIT, ref))
    for path, ref, _reason in CONST_TARGETS:
        seen.setdefault(path, set()).add((BASIS_COMMIT, ref))
    for path, _name, ref, _reason in SCALAR_TARGETS:
        seen.setdefault(path, set()).add((BASIS_COMMIT, ref))
    for path, _name, _rp, _rn, ref, _reason in CROSS_TARGETS:
        seen.setdefault(path, set()).add((BASIS_HARNESS, ref))
    for path, _name, ref, _rel, _calc, _reason in DERIVED_TARGETS:
        seen.setdefault(path, set()).add((BASIS_HARNESS, ref))
    out: dict[str, tuple[str, str]] = {}
    for p, got in seen.items():
        if len(got) == 1:
            out[p] = sorted(got)[0]
        else:
            out[p] = (BASIS_CONFLICT,
                      ",".join(f"{k}:{r}" for k, r in sorted(got)))
    return out


def _basis_text(basis: tuple[str, str]) -> str:
    """기준을 사람이 읽는 한 줄로. «커밋»과 «커밋 없음»을 섞어 찍지 않는다."""
    kind, ref = basis
    if kind == BASIS_COMMIT:
        return f"①②③④ 값 대조 기준 «커밋» {ref}"
    if kind == BASIS_HARNESS:
        return (f"⑤ 교차 검산 · 기준 «커밋 없음» — 이 파일은 {ref} 에 존재하지 "
                f"않았다. 27.4년 하네스와의 «일치»로 얼렸다")
    return f"기준이 둘 이상이다 — 관문 «자신»의 결함: {ref}"


def _resolve_int(name: str, consts: dict) -> int | None:
    """수집한 상수 하나를 정수로 푼다. «다른 상수를 가리키는» 꼴이면 한 겹 따라간다.

    (screen_trend_template.py 의 MIN_CLOSES_FOR_TT = SMA_WINDOW_200 이 그 꼴이다.
     따라가지 않고 손으로 200 을 적으면 같은 것을 가리키는 자가 둘이 된다.)
    """
    entry = consts.get(name)
    if entry is None:
        return None
    kind, val = entry
    if kind == READ_VALUE and isinstance(val, int) and not isinstance(val, bool):
        return val
    if kind == READ_SOURCE and isinstance(val, str):
        other = consts.get(val.strip())
        if (other and other[0] == READ_VALUE and isinstance(other[1], int)
                and not isinstance(other[1], bool)):
            return other[1]
    return None


def _ref_needed_bars(ref: str) -> tuple[object, str, str | None]:
    """기준 커밋의 «관문 상수»에서 「몇 봉이 있어야 판정이 그대로인가」를 «계산»한다.

    돌려주는 것은 (필요한 최소 봉 수, 어떻게 나왔는지, 읽기 실패 사유).
    수를 베껴 적지 않는다 — ref 판 trend_template.py 와
    screen_trend_template.py 를 읽어 항을 «더하고 고른다».

    항의 출처(코드 확인):
      - trend_template.py 의 _sma: needed = window + end_offset
        -> SMA_WINDOW_200 + TT_SMA200_RISING_PREFERRED_DAYS (sma200_5m_ago)
        -> SMA_WINDOW_200 + TT_SMA200_RISING_LOOKBACK_DAYS  (sma200_1m_ago)
        -> SMA_WINDOW_150 · SMA_WINDOW_50
      - trend_template.py 의 52주 수익률: closes[-WINDOW_52W - 1] -> WINDOW_52W + 1
      - screen_trend_template.py 의 평가 최소 종가 수: MIN_CLOSES_FOR_TT
    """
    tt_src, err1 = _git_show(ref, "scripts/canslim_lib/trend_template.py")
    st_src, err2 = _git_show(ref, "scripts/screen_trend_template.py")
    err = err1 or err2
    try:
        consts = {**_harvest_constants(tt_src), **_harvest_constants(st_src)}
    except SyntaxError:
        return None, "기준 커밋의 관문 파일을 파싱 못 함", err or "파싱 실패"
    terms: dict[str, tuple] = {
        "sma200_5m_ago": ("SMA_WINDOW_200", "TT_SMA200_RISING_PREFERRED_DAYS"),
        "sma200_1m_ago": ("SMA_WINDOW_200", "TT_SMA200_RISING_LOOKBACK_DAYS"),
        "sma150": ("SMA_WINDOW_150",),
        "sma50": ("SMA_WINDOW_50",),
        "52주수익률": ("WINDOW_52W", 1),
        "평가최소종가수": ("MIN_CLOSES_FOR_TT",),
    }
    got: dict[str, int] = {}
    for label, parts in terms.items():
        acc = 0
        for part in parts:
            v = part if isinstance(part, int) else _resolve_int(part, consts)
            if v is None:
                return (None, f"{label}: 항 «{part}» 를 못 읽음",
                        err or f"{part} 를 못 읽음")
            acc += v
        got[label] = acc
    need = max(got.values())
    detail = " · ".join(f"{k}={v}" for k, v in
                        sorted(got.items(), key=lambda kv: -kv[1]))
    return need, f"max({detail}) = {need}", err


def _ref_series_keys(ref: str) -> tuple[object, str, str | None]:
    """기준 커밋의 us_loader 가 «만드는» 시세 계열의 키를 코드로 뽑는다.

    문자열만으로 된 dict 리터럴 중 "dates" 를 키로 가진 것을 찾는다.
    그런 것이 «한 가지»가 아니면(0가지이거나 두 가지 이상이면) 기준을 하나로
    못 좁힌 것이므로 실패로 돌려준다 — 무엇과 견줬는지가 흐려지면 조용한
    통과가 난다.
    """
    src, err = _git_show(ref, "scripts/us_loader.py")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None, "기준 커밋의 us_loader.py 를 파싱 못 함", err or "파싱 실패"
    hits = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Dict) and node.keys
                and all(isinstance(k, ast.Constant) and isinstance(k.value, str)
                        for k in node.keys)):
            keys = tuple(k.value for k in node.keys)
            if "dates" in keys:
                hits.append(keys)
    uniq = sorted(set(hits))
    if len(uniq) != 1:
        return (None,
                f"「dates」를 가진 문자열 키 dict 리터럴이 {len(uniq)}가지 — "
                "기준을 하나로 못 좁혔다",
                err or "기준을 하나로 못 좁힘")
    return uniq[0], f"us_loader.py 의 계열 초기화 dict 키 {len(uniq[0])}개", err


# DERIVED_TARGETS 의 「계산기 이름」을 실제 함수로 푼다. 표에 없는 이름이
# 적히면 main() 이 «관문 자신의 결함»으로 세고 실패시킨다.
_REF_CALCS = {
    "needed_bars": _ref_needed_bars,
    "series_keys": _ref_series_keys,
}


def _harness_twin_names(ref: str) -> tuple[list[tuple[str, str, str, str]], str | None]:
    """새 실전 파일의 상수 중 «하네스에 이름이 같은 짝»이 있는 것을 코드로 찾는다.

    「짝이 있는지」를 손으로 훑지 않는다 — 훑으면 다음 상수에서 또 빠뜨린다.
    돌려주는 것은 [(path, name, 분류, 견줌 글)] 과 읽기 실패 사유.
    분류는 「교차덮음」·「제외(기준)」·「미분류」 셋이다. 미분류는 ⑥ 이 이미
    관문을 실패시키므로 여기서는 세지 않고 «알리기»만 한다 —
    같은 것을 두 곳에서 세면 수가 둘이 된다.
    """
    src, err = _git_show(ref, FROZEN_HARNESS)
    try:
        harness = _harvest_constants(src)
    except SyntaxError:
        return [], err or "하네스 파싱 실패"
    cross = {(p, n) for (p, n, _rp, _rn, _r, _x) in CROSS_TARGETS}
    derived = {(p, n) for (p, n, _r, _rel, _c, _x) in DERIVED_TARGETS}
    out: list[tuple[str, str, str, str]] = []
    for path, basis in sorted(_covered_file_basis().items()):
        if basis[0] != BASIS_HARNESS:
            continue
        now = _harvest_constants(open(path, encoding="utf-8").read())
        for name in sorted(set(now) & set(harness)):
            if (path, name) in cross or (path, name) in derived:
                tag = "교차덮음"
            elif name in EXCLUDED_SCALARS.get(path, {}):
                tag = "제외(" + EXCLUDED_SCALARS[path][name][0] + ")"
            else:
                tag = "미분류"
            out.append((path, name, tag,
                        f"지금={_show(now[name])}  하네스={_show(harness[name])}"))
    return out, err


def _classify_files():
    """«뿌리 여럿»의 폐포 합집합 ∪ 덮음파일 을 덮음/제외/미분류로 가른다.

    돌려주는 것은 (뿌리별 폐포, 폐포 합집합, 모집단, 덮음, 제외, 미분류).
    뿌리별 폐포를 «따로» 돌려주는 까닭: 합집합만 찍으면 「어느 뿌리가 무엇을
    끌고 왔나」가 안 보이고, 뿌리가 조용히 빠져도 수가 그럴듯하게 남는다.

    제외 칸을 셀 때 «덮음 여부를 빼지 않는다» — 빼면 세 칸이 모집단의
    «분할»이 되어 「셈 안 맞음」 관문이 질 수가 없는 항등식이 된다.
    한 파일이 덮음과 제외에 둘 다 올라 있으면 합이 모집단보다 «커져서» 걸린다.
    """
    closures = {root: _import_closure(root) for root, _why in ROOTS}
    closure: set[str] = set()
    for one in closures.values():
        closure |= one
    covered = _covered_file_basis()
    # 덮음 표에 있는데 폐포 «밖»인 파일도 모집단에 넣는다 —
    # strategy_params.py 가 그렇다(하네스가 import 하지 않지만 스킬의 정본).
    universe = sorted(closure | set(covered))
    cov = [p for p in universe if p in covered]
    exc = [p for p in universe if p in EXCLUDED_FILES]
    unc = [p for p in universe if p not in covered and p not in EXCLUDED_FILES]
    return closures, closure, universe, cov, exc, unc


def _scalar_at(src: str, name: str):
    """소스 최상위에서 상수 하나를 (읽은 방식, 견줄 것) 로 읽는다.

    못 찾으면 `_MISSING` 을 돌려준다 — 상수의 «진짜 값»이 None/0/False 일 수도
    있어서 그것들과 "못 찾음"을 헷갈리면 안 된다. 수집 자체는
    _harvest_constants() 에 맡긴다(수집 규칙이 «한 곳»에만 있어야 이름이
    두 경로에서 서로 다르게 사라지지 않는다).
    """
    return _harvest_constants(src).get(name, _MISSING)


def _show(entry) -> str:
    """(읽은 방식, 견줄 것) 을 화면 글자로. 「글자로 견줌」을 사람이 알아야 한다."""
    if entry is _MISSING:
        return "(못 찾음)"
    kind, val = entry
    return f"[{kind}] {val!r}"


def _covered_names(path: str, all_names: list[str]) -> set[str]:
    """`path` 에서 «실제로 비교되는» 이름 집합을 «비교 표에서» 끌어낸다.

    덮음 목록을 손으로 한 벌 더 적지 않는 것이 요점이다 — 손으로 적으면
    표와 갈라지고, 갈라진 쪽이 「범위가 주장보다 좁다」의 발원지였다.
      · DICT_TARGETS  — 그 파일의 dict 이름(키 단위로 대조된다)
      · CONST_TARGETS — 그 파일은 «전부» 자동 수집해 대조하므로 전체가 덮음
      · SCALAR_TARGETS — 그 파일의 이름별 대조 항목
      · CROSS_TARGETS / DERIVED_TARGETS — ⑤ 교차 검산이 «하네스와» 견주는 항목.
        기준이 커밋이 아니라 하네스 일치일 뿐, 덮은 것은 덮은 것이다.
    """
    covered = {name for (p, name, _ref, _reason) in SCALAR_TARGETS if p == path}
    covered |= {name for (p, name, _ref, _reason) in DICT_TARGETS if p == path}
    covered |= {name for (p, name, _rp, _rn, _r, _x) in CROSS_TARGETS if p == path}
    covered |= {name for (p, name, _r, _rel, _c, _x) in DERIVED_TARGETS if p == path}
    if any(p == path for (p, _ref, _reason) in CONST_TARGETS):
        covered |= set(all_names)
    return covered


def _classify_scalars(path: str, src: str) -> tuple[list[str], list[str], list[str], list[str]]:
    """`path` 파일의 모듈최상위 대문자 상수 «전부»를 자동 수집해
    (전체, 덮음, 제외, 미분류) 네 이름 목록으로 가른다.

    특정 파일 이름에 매이지 않는다 — CLASSIFY_FILES 의 «어느» path 를 넣어도
    같은 방식으로 검산한다.

    「덮음」= _covered_names() 가 비교 표에서 끌어낸 것.
    「제외」= EXCLUDED_SCALARS[path] 에 이유가 적혀 있는 것.
    「미분류」= 둘 다 아닌 것 — 사람이 새 상수를 추가하고 어느 쪽에도 안
    넣으면 여기 걸려 그 파일의 관문이 실패한다.
    """
    harvested = _harvest_constants(src)
    all_names = sorted(harvested)
    covered = _covered_names(path, all_names)
    excluded = set(EXCLUDED_SCALARS.get(path, {}))
    # 제외 칸에서 «덮음 여부를 빼지 않는다». 빼면 세 칸이 all_names 의
    # «분할»이 되어 「덮음+제외+미분류 == 전체」가 항등식이 되고, 「셈 안 맞음」
    # 관문이 «질 수가 없는» 죽은 가지가 된다. 게다가 「and not in covered」는
    # 중복 등재된 이름을 «제외 칸에서 조용히 지워» 깨끗한 통과를 만들어 준다 —
    # 잡는 장치가 아니라 «삼키는» 장치였다. 이제 둘 다 세므로 합이 전체보다
    # 커져서 걸린다.
    covered_here = sorted(n for n in all_names if n in covered)
    excluded_here = sorted(n for n in all_names if n in excluded)
    unclassified = [n for n in all_names if n not in covered and n not in excluded]
    return all_names, covered_here, excluded_here, unclassified


def _git_show(ref: str, path: str) -> tuple[str, str | None]:
    """`git show ref:path` 결과와, 실패했으면 그 사유를 함께 돌려준다.

    실패해도 빈 문자열은 그대로 돌려준다 — 그러면 값-읽기 함수들이 빈/미상
    값을 내고, 그게 「같음」으로 둔갑하지 않도록 막는 일은 main() 의 몫이다.
    (git show 실패 시 old 가 비어 모든 키가 «다름»으로 찍히는 안전장치 자체는
    그대로 둔다 — 「다름 N개」가 조용한 통과보다 훨씬 낫다.) 다만 실패 사유는
    stderr 뿐 아니라 main() 이 «화면 출력 줄 자체»에도 찍어야 한다 — 그래야
    "진짜 값이 N개 다르다"와 "읽기가 실패해서 다르게 «보인다»"를 사람이 눈으로
    구분할 수 있다.
    """
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        err = result.stderr.strip() or "(사유 미상)"
        print(f"    [git show 실패] {ref}:{path}: {err}", file=sys.stderr)
        return result.stdout, err
    return result.stdout, None


def main() -> int:
    bad = 0           # 값이 달라진 항목 수
    read_fail = 0     # now·old 둘 다 못 읽은 대상 수 — 관문 자신의 결함
    unclassified = 0  # 덮음/제외 어디에도 없는 상수 수
    broken = 0        # 관문 «자신»의 결함 수(셈 안 맞음·못 담는 모양·기준 충돌)
    unclassified_files = 0  # 폐포 안인데 덮음·제외 어디에도 없는 파일 수
    by_source = []    # 「글자로 견준」 이름들 — 끝에 한 번 더 알린다
    reach_only = []   # «도달성»만으로 제외한 항목 — 실패는 아니고 재검토 알림

    covered_files = _covered_file_basis()  # ⑥ 가 돌 파일 목록(표에서 끌어냄)

    print("== ① 검출기 DEFAULT_PARAMS (기준: e8cd65ae, 27.4년 백테스트 원 커밋) ==")
    for path, name, ref, reason in DICT_TARGETS:
        now = _dict_at(open(path, encoding="utf-8").read(), name)
        old_src, err = _git_show(ref, path)
        old = _dict_at(old_src, name)
        keys = sorted(set(now) | set(old))
        fail_tag = f"  [git show 실패: {err}]" if err else ""

        if not keys:
            # now 와 old 가 «둘 다» 빈 dict. 값이 진짜로 같아서 빈 게 아니라
            # _dict_at 이 대상을 못 찾았을 때도 이 모양이 나온다. 이걸
            # "같음"으로 찍으면 관문이 아무것도 못 읽어도 항상 통과하는
            # «질 수 없는 관문»이 된다. 그래서 무조건 실패로 끝낸다.
            print(f"{path}  {name}  읽은 키 0개  "
                  f"[읽기 실패 — now={len(now)}개 old={len(old)}개]{fail_tag}")
            read_fail += 1
            continue

        diff = [k for k in keys if now.get(k) != old.get(k)]
        mark = "같음" if not diff else "다름"
        print(f"{path}  {name}  now={len(now)}개 old={len(old)}개 "
              f"합집합={len(keys)}개  {mark}{fail_tag}")
        for k in diff:
            print(f"    {k}: {ref}={old.get(k)!r}  지금={now.get(k)!r}")
            bad += 1

    print("\n== ② strategy_params.py 대문자 상수 자동 수집 "
          "(기준: 41db459d, 사용자 결정 2026-09-02) ==")
    for path, ref, reason in CONST_TARGETS:
        print(f"   기준 사유: {reason}")
        now = _harvest_constants(open(path, encoding="utf-8").read())
        old_src, err = _git_show(ref, path)
        old = _harvest_constants(old_src)
        keys = sorted(set(now) | set(old))
        fail_tag = f"  [git show 실패: {err}]" if err else ""

        if not keys:
            print(f"{path}  수집한 상수 0개  "
                  f"[읽기 실패 — now={len(now)}개 old={len(old)}개]{fail_tag}")
            read_fail += 1
            continue

        src_names = sorted(k for k in keys
                           if now.get(k, (None,))[0] == READ_SOURCE
                           or old.get(k, (None,))[0] == READ_SOURCE)
        by_source += [f"{path}:{n}" for n in src_names]
        diff = [k for k in keys if now.get(k, _MISSING) != old.get(k, _MISSING)]
        mark = "같음" if not diff else "다름"
        print(f"{path}  now={len(now)}개 old={len(old)}개 합집합={len(keys)}개 "
              f"(그중 글자로 견준 것 {len(src_names)}개)  {mark}{fail_tag}")
        for k in diff:
            print(f"    {k}: {ref}={_show(old.get(k, _MISSING))}  "
                  f"지금={_show(now.get(k, _MISSING))}")
            bad += 1

    print("\n== ③④ trend_template.py + screen_trend_template.py 관문 상수 "
          "(기준: e8cd65ae) ==")
    for path, name, ref, reason in SCALAR_TARGETS:
        now = _scalar_at(open(path, encoding="utf-8").read(), name)
        old_src, err = _git_show(ref, path)
        old = _scalar_at(old_src, name)
        fail_tag = f"  [git show 실패: {err}]" if err else ""

        if now is _MISSING and old is _MISSING:
            print(f"{path}  {name}  [읽기 실패 — now·old 둘 다 못 찾음]{fail_tag}")
            read_fail += 1
            continue

        for e in (now, old):
            if e is not _MISSING and e[0] == READ_SOURCE:
                by_source.append(f"{path}:{name}")
                break
        mark = "같음" if now == old else "다름"
        print(f"{path}  {name}  {ref}={_show(old)}  지금={_show(now)}  {mark}{fail_tag}")
        print(f"    (이유: {reason})")
        if now != old:
            bad += 1

    print("\n== ⑤ 교차 검산 — 기준 커밋이 «없는» 새 미국 실전 파일 ==")
    print(f"   이 파일들은 {HARNESS_REF} 에 «존재하지 않았다». 그래서 「그 커밋 이후")
    print("   안 바뀌었나」를 물을 수 «없다». 물음을 바꾼다 — 「27.4년 하네스가")
    print("   «쓴 값»과 «같은가」. 기준 쪽 값은 글자로 베껴 적지 않고 git show 로")
    print("   «읽어» 견준다(베껴 적으면 같은 것을 가리키는 자가 둘이 된다).")
    for live_path, live_name, ref_path, ref_name, ref, reason in CROSS_TARGETS:
        now = _scalar_at(open(live_path, encoding="utf-8").read(), live_name)
        old_src, err = _git_show(ref, ref_path)
        old = _scalar_at(old_src, ref_name)
        fail_tag = f"  [git show 실패: {err}]" if err else ""

        if now is _MISSING or old is _MISSING:
            print(f"{live_path}  {live_name}  [읽기 실패 — 지금={_show(now)} "
                  f"하네스={_show(old)}]{fail_tag}")
            read_fail += 1
            continue

        for e in (now, old):
            if e[0] == READ_SOURCE:
                by_source.append(f"{live_path}:{live_name}")
                break
        mark = "같음" if now == old else "다름"
        print(f"{live_path}  {live_name}  지금={_show(now)}  "
              f"기준 {ref_path}:{ref_name}@{ref}={_show(old)}  {mark}{fail_tag}")
        print(f"    (기준 «커밋 없음» — 하네스와의 일치로 얼렸다. 이유: {reason})")
        if now != old:
            bad += 1

    for live_path, live_name, ref, rel, calc_key, reason in DERIVED_TARGETS:
        calc = _REF_CALCS.get(calc_key)
        if calc is None or rel not in ("==", ">="):
            print(f"{live_path}  {live_name}  계산기 «{calc_key}» 또는 관계 "
                  f"«{rel}» 가 등록돼 있지 않다 — 관문 «자신»의 결함")
            broken += 1
            continue
        now = _scalar_at(open(live_path, encoding="utf-8").read(), live_name)
        ref_val, detail, err = calc(ref)
        fail_tag = f"  [git show 실패: {err}]" if err else ""

        if now is _MISSING or now[0] != READ_VALUE or ref_val is None:
            print(f"{live_path}  {live_name}  [읽기 실패 — 지금={_show(now)} "
                  f"기준={ref_val!r} ({detail})]{fail_tag}")
            read_fail += 1
            continue

        now_val = now[1]
        try:
            ok = (now_val == ref_val) if rel == "==" else (now_val >= ref_val)
        except TypeError:
            ok = False
            detail += " [견줄 수 없는 종류]"
        mark = "만족" if ok else "어긋남"
        print(f"{live_path}  {live_name}  지금={now_val!r}  "
              f"기준({ref} 에서 «계산»)={ref_val!r}  관계 «{rel}»  {mark}{fail_tag}")
        print(f"    (기준 «커밋 없음» — 하네스가 쓴 관문 상수에서 계산: {detail})")
        print(f"    (이유: {reason})")
        if not ok:
            bad += 1

    twins, twin_err = _harness_twin_names(HARNESS_REF)
    if twin_err:
        print(f"   [git show 실패: {twin_err}] — 짝 찾기가 «못» 돌았다")
        read_fail += 1
    print(f"   하네스와 이름이 «같은» 상수 {len(twins)}개 — 손으로 훑지 않고 "
          "코드로 찾는다(짝이 있는데 안 덮은 것이 드러나라고):")
    for path, name, tag, cmp_txt in twins:
        print(f"      {path}:{name}  [{tag}]  {cmp_txt}")
    if not twins:
        print("      (없음 — 새 실전 파일의 상수 중 하네스와 이름이 겹치는 것이 0개)")
    print("   («미분류»가 있으면 아래 ⑥ 이 그 파일에서 관문을 실패시킨다. "
          "여기서는 세지 않는다 — 같은 것을 두 곳에서 세면 수가 둘이 된다.)")

    print("\n== ⑥ 상수 분류 검산 (①②③④⑤ 표에 나온 파일마다 덮음/제외/미분류) ==")
    print("   대상 파일 목록은 손으로 적지 않는다 — 비교 표에서 끌어낸다.")
    for path in sorted(covered_files):
        basis = covered_files[path]
        # ⑥ 은 기준 커밋을 «안 읽는다» — 「지금 판에 설명 안 된 상수가
        # 있나」를 묻는 검산이라 그게 맞다. 그런데 예전 판은 「(기준 e8cd65ae)」만
        # 찍어서 «기준 커밋과 견줬다»로 읽혔다. 찍는 것을 지우는 대신
        # «무엇의 기준인지»를 같은 줄에 적는다. 그리고 기준 «종류»가 둘이므로
        # (커밋 / 커밋 없음-하네스 일치) 어느 쪽인지를 파일마다 구분해 찍는다 —
        # 조용히 섞으면 읽는 사람이 「커밋과 견줬다」로 오해한다.
        print(f"  -- {path}")
        print(f"     ({_basis_text(basis)} · ⑥ 자신은 지금 판만 읽는다) --")
        if basis[0] == BASIS_CONFLICT:
            print(f"   기준이 둘 이상이다 — 관문 «자신»의 결함: {basis[1]}")
            broken += 1
        now_src = open(path, encoding="utf-8").read()
        all_names, covered, excluded_here, unclassified_names = _classify_scalars(path, now_src)
        harvested = _harvest_constants(now_src)
        n_src = sum(1 for n in all_names if harvested[n][0] == READ_SOURCE)

        # (가) 안 담은 모양 세기 — 「지금 없다」를 「앞으로도 없다」로 바꿈다.
        missed = _uncollected_shapes(now_src)
        if missed:
            print(f"   수집기가 «안 담은» 대문자 대입 {len(missed)}개 — 관문 실패: {missed}")
            print("   (튜플 대입·if/try/for/while/with 안의 대입·AugAssign 은 담지 "
                  "않는다. AugAssign 은 «잘못 읽은» 값이 「같다」로 둔갑하는 길이라 "
                  "특히 위험하다. 모듈 최상위 단일 이름 대입으로 고쳐라.)")
            broken += 1

        print(f"   자동 수집한 모듈최상위 대문자 상수 {len(all_names)}개"
              f"(그중 글자로 읽은 것 {n_src}개): {all_names}")
        print(f"   덮음(①②③④⑤ 비교 표에서 끌어냄) {len(covered)}개: {covered}")
        print(f"   제외(EXCLUDED_SCALARS[path]) {len(excluded_here)}개:")
        for n in excluded_here:
            tag = EXCLUDED_SCALARS.get(path, {}).get(n)
            crit = tag[0] if isinstance(tag, tuple) else "(기준 미상)"
            print(f"      {n}  [기준 {crit}]")
            if crit == "도달성":
                reach_only.append(f"{path}:{n}")
        total = len(covered) + len(excluded_here) + len(unclassified_names)
        if total != len(all_names):
            print(f"   셈 안 맞음 {total} != {len(all_names)} — 관문 «자신»의 결함"
                  "(한 이름이 덮음과 제외에 둘 다 올라 있다)")
            broken += 1
        if unclassified_names:
            print(f"   미분류 {len(unclassified_names)}개 — 관문 실패: {unclassified_names}")
            print("   (새 상수를 추가했다면 SCALAR_TARGETS 나 EXCLUDED_SCALARS[path] 중 "
                  "하나에 기준 꼬리표와 이유를 달아 명시로 넣어야 통과한다)")
            unclassified += len(unclassified_names)
        elif total == len(all_names):
            print(f"   미분류 0개 — 덮음+제외+미분류 = {total} = 자동 수집 수")

    print("\n== ⑦ 파일 분류 검산 (뿌리 여럿의 전이 import 폐포 합집합) ==")
    closures, closure, universe, cov_f, exc_f, unc_f = _classify_files()
    print(f"   뿌리 {len(ROOTS)}개 — 각 뿌리의 폐포를 «따로» 떠서 합친다:")
    for root, why in ROOTS:
        print(f"      {root}  폐포 {len(closures[root])}개  — {why}")
    outside = sorted(set(universe) - closure)
    print(f"   폐포 합집합(저장소 안 파일) {len(closure)}개 · "
          f"덮음 표에만 있는 폐포 밖 파일 {len(outside)}개: {outside}")
    print(f"   모집단 = 폐포 합집합 ∪ 덮음파일 = {len(universe)}개")
    print(f"   덮음 {len(cov_f)}개: {cov_f}")
    print(f"   제외 {len(exc_f)}개:")
    for f_ in exc_f:
        crit = EXCLUDED_FILES[f_][0]
        print(f"      {f_}  [기준 {crit}]")
        if crit == "도달성":
            reach_only.append(f_)
    total_f = len(cov_f) + len(exc_f) + len(unc_f)
    if total_f != len(universe):
        print(f"   셈 안 맞음 {total_f} != {len(universe)} — 관문 «자신»의 결함"
              "(한 파일이 덮음과 제외에 둘 다 올라 있다)")
        broken += 1
    if unc_f:
        print(f"   미분류 파일 {len(unc_f)}개 — 관문 실패: {unc_f}")
        print("   (뿌리 중 어딘가에 새 파일이 붙었다. 판정에 드는 수가 있으면 "
              "CONST_TARGETS/SCALAR_TARGETS 에 넣어 얼리거나(기준 커밋이 있을 때) "
              "CROSS_TARGETS/DERIVED_TARGETS 에 넣어 하네스와 견주고, 아니면 "
              "EXCLUDED_FILES 에 기준 꼬리표와 «코드로 확인한» 사유를 적어라. "
              "도달성만으로는 제외하지 않는다 — 성격으로 제외한다.)")
        unclassified_files += len(unc_f)
    elif total_f == len(universe):
        print(f"   미분류 파일 0개 — 덮음+제외+미분류 = {total_f} = 모집단")

    print(f"\n다른 값 {bad}개")
    if by_source:
        print(f"글자로 견준 상수 {len(set(by_source))}개 — 값이 아니라 «대입 오른쪽 "
              f"글자»를 견줬다는 뜻이다: {sorted(set(by_source))}")
    if read_fail:
        print(f"읽기 실패 {read_fail}개 대상 — 관문이 검산을 «못» 했다는 뜻이지 "
              "「같다」는 뜻이 아니다")
    if unclassified:
        print(f"미분류 상수 {unclassified}개 — 덮음 파일 어딘가에 새 상수가 "
              "관문 밖에서 조용히 추가됐다는 뜻")
    if unclassified_files:
        print(f"미분류 파일 {unclassified_files}개 — 뿌리(ROOTS) 어딘가의 "
              "폐포에 새 파일이 관문 밖에서 조용히 붙었다는 뜻")
    if broken:
        print(f"관문 «자신»의 결함 {broken}건 — 셈이 안 맞거나, 수집기가 못 담는 "
              "모양이 생겼거나, 기준 커밋이 둘이다. 관문을 고쳐야 한다")
    if reach_only:
        # 「미국 SEPA 스킬이 생기면 그 가정이 깨진다」는 예언이었다. 예언은
        # 아무도 다시 안 본다 — 관문이 초록이면 «까닭»까지 아직 맞다고 읽힌다.
        # 그래서 예언을 «출력값»으로 바꾼다: 하네스 «말고» 다른 뿌리에서도
        # 그 파일에 닿는지를 폐포로 «계산»해 항목마다 찍는다.
        live_reach: set[str] = set()
        for root, _why in ROOTS[1:]:
            live_reach |= closures.get(root, set())
        broken_assumption = [x for x in sorted(reach_only)
                             if x.split(":")[0] in live_reach]
        print(f"\n[알림] «도달성»만으로 제외한 항목 {len(reach_only)}개 — 관문을 "
              "실패시키지는 않지만 순서 규칙상 «재검토 대상»이다. 도달성 사유는 "
              "「소비자가 하네스 하나뿐」이라는 가정에 기댄다. 그 가정이 «지금» "
              "성립하는지를 뿌리별 폐포로 계산해 항목마다 찍는다:")
        for x in sorted(reach_only):
            hit = "실전 뿌리에서도 닿음 — 가정이 «이미» 깨졌다" if x.split(":")[0] in live_reach \
                else "실전 뿌리에서는 안 닿음 — 가정이 아직 선다"
            print(f"   {x}  [{hit}]")
        if broken_assumption:
            print(f"   → {len(broken_assumption)}개는 「하네스만 소비자」가 «더 이상 "
                  "사실이 아니다». 값이 같아서 통과한 것이지 사유가 맞아서가 "
                  "아니다 — 다음 판에서 덮음으로 올릴지 정해야 한다.")

    return 1 if (bad or read_fail or unclassified or unclassified_files
                 or broken) else 0


if __name__ == "__main__":
    sys.exit(main())

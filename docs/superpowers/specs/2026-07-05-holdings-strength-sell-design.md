# SEPA 보유 종목 — 강세 매도(과열·절정) 신호 설계

날짜: 2026-07-05
상태: 설계 확정 대기 (사용자 리뷰 전)
기준 브랜치: `feat/sepa-strength-sell` (origin/master 기준)

## 목적

`/stocks/sepa` 「보유 종목 점검」 카드에 **강세 매도 신호** 트랙을 새로 얹는다.
마크 미너비니의 "강세에 팔아라(sell into strength)" — 여러 달 건강하게 오른 주가가
과열·절정(climax) 국면에 들어서면, 손절선에 닿기 전에 강세일 때 이익을 확정하라는 관점이다.

근거: 사용자가 정리한 『Think & Trade Like a Champion』 매도 챕터 요약(절정 분출·상승일 비율·
가속 상승·최대 상승일·소진성 갭·분산 정황·베이스 세기·PER 확대).

## 기존 구조와의 관계 (왜 세 번째 기둥인가)

master 기준으로 보유 카드는 이미 **세 시간대 중 둘**을 덮고 있다:

```
돌파 →→ [초기: 잘 따라가나?] →→ [중기: 무너지나?] →→ [말기: 과열됐나?]
         매집·MVP (있음)         약세 규칙 ①~⑥ (있음)    강세 매도 ← 이번 작업
         evaluate_accumulation    rule_* 6종              evaluate_climax (신규)
         evaluate_mvp             "손절/조기매도"          "강세에 판다"
         돌파 후 첫 15일 창        돌파 후 전 구간          최근 trailing 창
```

매집·MVP는 **초기 팔로우스루(사자마자 잘 가나)** 를 확인하는 강세 신호이고, 이번 트랙은
**말기 과열(너무 잘 올라 팔 때)** 를 감시한다. 둘은 중복이 아니라 강세 스펙트럼의 양 끝이다.

## 사용자 확정 사항

- **범위**: 가격·거래량만으로 계산되는 신호. **베이스 세기·PER 확대는 이번 제외**
  (각각 VCP처럼 자기 스펙+정답검증이 필요한 별도 슬라이스로 남김).
- **확장 게이트**: 피벗 × 1.05 = 이미 계산 중인 **`extension_pct ≥ 5`** 재사용. 새로 만들지 않음.
- **판정**: 2단계 단순. 확장 상태에서 신호 **1개라도** 발화하면 「🔥 강세 매도 검토」. 강도 등급 없음.
- **신호 세트**: 매집·MVP가 이미 보는 "상승일 세기·가격 상승률"과 중복을 피해,
  **네트-뉴 4종만** — 절정 분출 · 최대 상승일/변동폭 · 소진성 갭 · 분산 정황.
- **색**: 로즈·마젠타(과열). 매집(초록 ✓)·약세(빨강 ✗)와 시각적으로 구분.

## 전체 구조 (기존 3조각 위에 얹기)

```
public/data/sepa-holdings.json          ← 입력(불변)
scripts/screen_holdings_feedback.py     ← 변경 없음 (evaluate_holding이 strength 인라인 반환)
  └─ scripts/canslim_lib/sell_rules.py  ← evaluate_climax(신규) + evaluate_holding 배선
public/data/sepa-holdings-feedback.json ← strength 필드 추가되어 재생성
src/app/stocks/sepa/SepaHoldingsSection.tsx ← 배지 + 강세 매도 감시 패널
src/app/stocks/sepa/page.tsx            ← 용어 섹션에 4종 설명
tests/test_sell_rules.py                ← 강세 신호 + 게이트 단위테스트
```

## 판정 로직: `evaluate_climax(series, bi, pivot_price)`

`sell_rules.py`에 순수 함수로 추가(기존 `evaluate_accumulation`/`evaluate_mvp`와 동일 스타일).
`series`는 일봉 dict(dates/closes/highs/lows/volumes), `bi`는 돌파 인덱스, `pivot_price`는 피벗.

### 상수 (파일 상단)

```
EXT_GATE_PCT      = 5.0    # 확장 게이트: (현재/피벗 - 1)*100 ≥ 5
CLIMAX_25_MIN_W   = 5      # 절정 판정 창 하한(거래일)
CLIMAX_25_MAX_W   = 15     # +25% 판정 창 상한
CLIMAX_70_MAX_W   = 10     # +70% 판정 창 상한
CLIMAX_25_GAIN    = 0.25   # 5~15일 상승률 문턱
CLIMAX_70_GAIN    = 0.70   # 5~10일 상승률 문턱
BLOWOFF_RECENT    = 3      # 최대 상승일/변동폭이 "최근"으로 인정되는 거래일
GAP_RECENT        = 3      # 소진성 갭이 "최근"으로 인정되는 거래일
DISTRIB_WINDOW    = 10     # 분산 정황(반전·처닝) trailing 관찰 거래일
CHURN_MOVE_PCT    = 0.01   # 처닝: 종가 변화 절대값 < 1%
# HEAVY_VOL_MULT(=1.5), avg_volume() 은 기존 것 재사용
```

### 게이트

```
extension_pct = (current/pivot - 1)*100   # evaluate_holding이 이미 계산, 동일 값
extended = pivot is not None and extension_pct >= EXT_GATE_PCT
```

- `pivot is None` → `signal="na"`, `gate_detail="피벗 없음 — 판정 불가"`, `signals` 생략.
- `not extended` → `signal="not_extended"`, `gate_detail="확장 {ext:+.1f}% < 5%"`, `signals` 생략.
- `extended` → 아래 4종 계산 → `count`=발화 수 → `count≥1`면 `"sell_into_strength"`, else `"none"`.

### 신호 4종 (extended일 때만 계산)

각 신호는 `{"id","status","detail"}` 반환. `status ∈ fired | clear | pending`.

**S1. `climax_run` 절정 분출**
최근 종가 기준 trailing 상승률. `w`를 `CLIMAX_25_MIN_W..CLIMAX_25_MAX_W`로 돌며
`r_w = closes[-1]/closes[-1-w] - 1` 계산(바 부족한 `w`는 건너뜀).
- `w ≤ CLIMAX_70_MAX_W` 이고 `r_w ≥ 0.70` → **fired**(강력), detail `"최근 {w}일 +{r:.0%} — 폭발적 분출(70%+)"`.
- 아니면 `r_w ≥ 0.25` 인 `w`가 있으면 → **fired**, detail `"최근 {w}일 +{r:.0%} — 절정 구간(25%+)"`.
- 계산 가능한 `w`가 없으면(바 6개 미만) **pending**. 그 외 **clear**(`detail`에 최대 run 표기).

**S2. `blowoff_day` 최대 상승일/변동폭(막판)**
돌파 후 구간 `i ∈ [bi+1, n-1]`에서 일일 상승률 `g_i = closes[i]/closes[i-1]-1`,
일중폭 `rng_i = (highs[i]-lows[i])/closes[i]` 각각의 argmax를 구한다.
- 상승률 argmax **또는** 변동폭 argmax가 최근 `BLOWOFF_RECENT`(=3)거래일 안에 있으면 → **fired**
  (막판 최대 상승/최대 변동 = 상승 모멘텀 마지막 폭발). detail `"구간 최대 상승일 +{g:.0%}이 {k}일 전 출현"`.
- 돌파 후 거래일 < 5면 **pending**. 그 외 **clear**.

**S3. `exhaustion_gap` 소진성 갭**
최근 `GAP_RECENT`(=3)거래일 중 상승 갭(`lows[i] > highs[i-1]`, 완전 갭업)이 하나라도 있으면 → **fired**,
detail `"{k}일 전 상승 갭(전일 고가 위 출발)"`. 없으면 **clear**. 바 부족 시 **pending**.

**S4. `distribution` 분산 정황(청산)**
아래 셋 중 하나라도 있으면 → **fired**. detail에 발동한 유형·날짜 표기.
- (a) **대량 반전**: trailing `DISTRIB_WINDOW`일 내, 장중 신고가(`highs[i]>highs[i-1]`)인데 하락 마감
  (`closes[i]<closes[i-1]`) + `vols[i] ≥ 1.5×avg50`.
- (b) **처닝(과당매매)**: trailing 창 내, `vols[i] ≥ 1.5×avg50` 인데 `|closes[i]/closes[i-1]-1| < 0.01`
  (대량인데 가격 진전 없음 — 기관이 강세 이용해 매도).
- (c) **최대 거래량 하락일**: 돌파 후 전 구간 `[bi, n-1]`에서 거래량 최대인 날이 하락 마감이면
  (움직임 시작 이후 최대 거래량으로 하락).
- 셋 다 없으면 **clear**. 거래량 표본 부족 시 **pending**.

### 반환 (evaluate_holding에 배선)

`evaluate_holding` 반환 dict에 아래 `strength` 키 추가(기존 필드는 불변):

```json
"strength": {
  "signal": "sell_into_strength | none | not_extended | na",
  "extended": true,
  "gate_detail": "확장 +48.1% ≥ 5%",
  "count": 2,
  "signals": [
    { "id": "climax_run",     "status": "fired", "detail": "최근 8일 +38% — 절정 구간(25%+)" },
    { "id": "blowoff_day",    "status": "fired", "detail": "구간 최대 상승일 +14%이 1일 전 출현" },
    { "id": "exhaustion_gap", "status": "clear", "detail": "최근 갭 없음" },
    { "id": "distribution",   "status": "clear", "detail": "반전·처닝·최대량 하락 없음" }
  ]
}
```

- `not_extended`/`na`면 `signals`는 빈 배열, `count`=0.
- `extended`면 `signals`는 항상 4개(순서 고정).

## 화면: `SepaHoldingsSection.tsx` — 접기/펼치기로 단순화

정보량이 많아, 카드를 **네이티브 `<details>/<summary>`** 로 접는다(클라이언트 JS 없이 서버 렌더 유지).
접힘 = "오늘 손댈 일 있나"만, 펼침 = 상세. 강세 패널만이 아니라 **카드 전체를 이 구조로 재편**한다
(기존 매집·약세 패널도 상세 영역으로 이동 — 강세 트랙 추가로 밀도가 넘쳐서).

### 타입

```ts
interface StrengthSignal { id: string; status: "fired" | "clear" | "pending"; detail: string; }
interface Strength {
  signal: "sell_into_strength" | "none" | "not_extended" | "na";
  extended: boolean; gate_detail: string; count: number; signals: StrengthSignal[];
}
// HoldingFeedback에 strength?: Strength 추가
```

### 접힘 (`<summary>` — 항상 보임)

한 종목당 두 줄만:
- **1줄**: 종목명 + 코드 (좌) · 수익%(우, 초록/빨강)
- **2줄**: 행동 배지(좌) · `상세 ▾` 토글(우, 펼치면 `접기 ▴`)

행동 배지 = 필요할 때만 시선 끄는 것:
- 약세 신호 배지: `🔴 손절` / `🟠 조기 매도 · 위반 n건` / `🟢 정상 보유`(hold일 때도 표시해 "점검됨" 확인).
- `strength.signal === "sell_into_strength"`이면 로즈 배지 `🔥 강세 매도 검토` 추가
  (bg `rgba(245,169,206,0.14)`, fg `#f5a9ce`, border `rgba(245,169,206,0.34)`).
- **MVP·확장% 칩은 접힘에서 빼고 펼침으로** 이동(행동 아님, 보조 정보).

`<summary>`는 기본 디스클로저 삼각형 제거(`list-style:none`, `::-webkit-details-marker{display:none}`),
직접 그린 chevron을 `details[open]`에서 180° 회전. `:focus-visible` 링 제공(키보드 접근성).

접힘 2줄 사이에 **3트랙 점수판**(요약)도 넣는다: `매집 {n}/6`(창 미완이면 `D+{k}/15`) ·
`강세 발화 {count}/4`(미확장이면 `확장 전`, 문턱 근접 시 `(x%p)`) · `약세 위반 {n}`(관찰만 있으면 `관찰 {n}`).
숫자·색만으로 어떤 종목을 펼쳐볼지 판단되게 한다(매집=초록, 강세=로즈, 위반=빨강, 관찰=앰버, 대기·진행중=회색).

### 펼침 (`<details>` 본문)

순서: ① 보조 칩(`MVP`·`확장 ±x%`) → ② 매수·현재·손절선 줄 → ③ 매집 신호 패널(기존) →
④ 강세 매도 감시 패널(신규) → ⑤ 약세 규칙 ①~⑥(기존).

**전체 나열 + 충족 표시** — 세 패널 모두 항목을 **하나도 빠짐없이** 렌더하고, 만족/발화한 것만 마크한다
(요약 점수판과 달리 여기선 미충족·판정전 항목도 회색으로 남겨 대조되게 한다):
- 매집 6종(상승일 우세·양질 종가·연속상승7 + M·V·P): 충족 `✓`(초록) / 미충족 `○` / 판정전 `―`.
- 강세 매도 4종: 발화 `🔥`(로즈) / 미발화 `○` / 판정전 `―`.
- 약세 규칙 ①~⑥: 통과 `✓`(초록) / 위반 `✗`(빨강) / 관찰 `🟡`(앰버) / 판정전·해당없음 `―`.
- 각 패널 제목 우측에 **충족 집계**를 붙인다: 예) 매집 `충족 5/6`, 강세 `발화 2/4`,
  약세 `통과 4 · 위반 1 · 관찰 1`(0인 항목은 생략). 집계 색은 트랙 색을 따른다.

**강세 매도 감시 패널**(④, 매집 패널과 대칭):
- `sell_into_strength | none`(extended): 제목 `🔥 강세 매도 감시 · {gate_detail} · 발화 {count}/4`(로즈),
  2열 그리드 4종 — 마크 `🔥`(fired)/`○`(clear)/`―`(pending), 라벨 호버 툴팁.
- `not_extended`: 대기 박스 `확장 전 — 대기 · {gate_detail}`(문턱 근접 시 `(문턱까지 x%p)`).
- `na`: 대기 박스 `피벗 없음 — 판정 불가`(약세 트랙은 매수일 기준으로 계속 감시).

마크 색: fired=`#f5a9ce`, clear=`text-on-surface-variant/50`, pending=`/40`.

> **범위 메모**: 이 접기/펼치기 재편은 강세 트랙만이 아니라 카드 전체(매집·약세 포함)에 적용되므로,
> 기존 표시 로직을 `<summary>`(요약)/`<details>` 본문으로 나누는 리팩터가 포함된다.

## 용어 설명: 인라인 툴팁 (page.tsx 미변경)

매집·MVP가 이미 컴포넌트 내부 `Tip` + `ACC_META`/`MVP_META` 로 라벨 호버 툴팁을 제공한다.
강세 4종도 **동일 패턴**으로 `STRENGTH_META`(라벨·tip)를 두고 `Tip`으로 감싼다. `page.tsx`는 손대지 않는다.
tip 예: 절정 분출 = "확장 단계에서 최근 5~15일 +25%(또는 5~10일 +70%) 급등 — 강세에 이익 확정 검토".

## 테스트: `tests/test_sell_rules.py`

기존 `make_series` 헬퍼 재사용. 추가:
- 절정 분출: 10일 +30% → fired / +10% → clear / 8일 +75% → fired(강력).
- 최대 상승일: 최대 상승일이 마지막 3일 내 → fired / 오래된 위치 → clear.
- 소진성 갭: 최근 3일 내 갭업 → fired / 없음 → clear.
- 분산: (a)대량 반전 / (b)처닝 / (c)최대량 하락일 각각 fired.
- 게이트: `extension_pct < 5` → `not_extended`(signals 빈 배열) / `pivot=None` → `na`.
- extended인데 4종 모두 clear → `none`.

## 산출물 재생성

`python scripts/screen_holdings_feedback.py` 재실행 → `sepa-holdings-feedback.json`에 `strength` 필드 채워짐.
현재 실제 보유 4종은 모두 확장 <5%라 전부 `not_extended`로 나오는 것이 정상(회귀 확인용 기대값).

## 문서-로직 동기화

`sell_rules.py` 상단 docstring에 이 스펙 경로를 참조로 추가. 상수·문턱을 바꾸면 이 문서도 같은 라운드에 갱신.

## 범위 밖 (다음 슬라이스)

- **베이스 세기**(1~6번째 베이스 → 주기 초/후반): 베이스 열거 알고리즘 + 상승 시작점 판정 필요.
  기존 zigzag/피벗 machinery는 알려진 약점 있음(`vcp-book-examples-gaps`) → 자기 스펙+정답검증 필요.
- **PER 확대**(첫 베이스 피벗 시점 PER 대비 2배+): 첫 베이스 앵커가 필요해 베이스 세기에 종속 +
  보유 파이프라인에 펀더(DART) 의존 신설. 베이스 세기 이후 진행.

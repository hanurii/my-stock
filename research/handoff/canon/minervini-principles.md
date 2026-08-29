# 미너비니 원칙 — 수집본

**수집** 조사 세션 2026-08-29 · **수집만 했습니다. 검정·판정 없습니다.**
**용도** 100번 「미너비니 원칙 기반 수익률 검정」의 규칙 근거

---

## 🚨 이 문서를 읽는 법 — **출처 등급이 셋입니다**

```
[1차-본인]   미너비니 본인의 글·말 (X 트윗 · 인터뷰). **트윗 id 를 적어 두었으니 직접 여실 수 있습니다**
[1차-전사]   **사용자가 책 원문을 직접 옮겨 준 것** — 저장소 results/78 · 99 에 있습니다
[3차-해석]   제3자 정리글. **미너비니가 그렇게 말했다는 근거가 붙어 있지 않은 것**

🚨 확실치 않으면 전부 [3차-해석] 에 넣었습니다.
🚨 페이지를 «실제로 읽은 것»만 [읽음], 검색엔진 요약만 본 것은 [검색요약] 입니다.
   X(트위터)는 402 로 «전부» 못 읽었습니다 — 트윗 본문은 검색엔진이 실어 준 것입니다.
```

## 🚨 이미 철회된 오귀속 — **다시 줍지 마십시오**
([[minervini-progressive-exposure]] · 이전 조사에서 웹에 실제로 돌고 있음을 확인)
```
「손절 7~8%」= 오닐이지 미너비니 아님   ← 🚨 중립 검색어에서도 그냥 나옵니다
「Losers average losers」 = 폴 튜더 존스
「3연패 중단」 같은 고정 횟수 규칙 = 그의 것 아님
「¼→½→¾→풀」 4단 사다리 = 제3자 해석 (원 글이 스스로 밝힘)
「my own trading is the best market indicator」 = 그 문장 자체는 원문 없음 (원문은 아래 21번)
「위험 1~2%」 = 본인 트윗(1.25/2.5%)과 어긋남
「최근 10 거래」 = 본인 말은 「4 or 5」
「시장 폭 = 오닐 개념」이라는 귀속 = 철회됨
「분산일 세는 규칙」 = 사용자 확인 결과 원전에 없음
```

---

# ㉠ 종목 고르기

### 1. 트렌드 템플릿 8기준
① 인용 —
```
1. 현재가가 150일선·200일선 «위»
2. 150일선이 200일선 «위»
3. 200일선이 최소 1개월 «상승 중» (되도록 4~5개월)
4. 50일선이 150일선·200일선 «둘 다 위»
5. 현재가가 50일선 «위»
6. 현재가가 52주 «저가»보다 최소 **25% 위** (책 『Trade Like a Stock Market Wizard』는 **30%**)
7. 현재가가 52주 «고가»의 **25% 이내** (고가에 가까울수록 좋다)
8. **RS(상대강도) 순위 70 이상** (되도록 80~90 이상)
```
② 출처 — 여러 스크리너 사이트가 같은 여덟을 싣습니다 [검색요약]. **[3차-해석]이나 여덟 항목의 «내용»은 어긋나는 곳이 없었습니다.** 🚨 다만 **6번이 25%인지 30%인지 갈립니다** — 「책은 30%」라고 적은 곳이 있습니다.
③ 구현 가능? — **가능**. 전부 일봉에서 나옵니다. RS 는 우리 iRS 로 대응.
④ 이미 쟀나? — **쟀습니다.** 저장소의 `find-trend-template` 이 이 관문입니다. 미국 판 경로가 전부 이 관문 통과분입니다(91·93). **6번의 25 vs 30 은 안 갈라 봤습니다 — 미측정.**

### 2. 실적 조건
① 인용 —
```
분기 EPS 성장률 «전년 동기 대비» 최소 20~25%, 되도록 30~50%
매출 성장률 20% 이상 (일부는 15% 이상으로 적음)
이익률 «확대» 중
「Code 33」 = 이익·매출·이익률 «셋»이 «3분기» 연속 가속
```
② 출처 — [3차-해석] [검색요약]. 🚨 **숫자가 출처마다 다릅니다**(EPS 20 / 25 / 30, 매출 15 / 20 / 25). 본인 말로 확인한 건 **없습니다**.
③ 구현 가능? — **가능**. Sharadar 펀더멘털에 분기 EPS·매출·이익률이 있습니다.
④ 이미 쟀나? — **92번(us-fundamentals)·94번(roe-realized)에서 일부**. 「Code 33」(3분기 동시 가속)은 **미측정**.

### 3. 유동성·시가총액 하한
① 인용 — **못 찾았습니다.**
② 출처 — 없음. 🚨 「작은 회사가 크게 간다」는 취지의 서술은 널렸으나 **문턱 숫자가 없습니다.**
③ 구현 가능? — 가능하나 **문턱을 우리가 정해야 합니다** = 원전 밖.
④ 이미 쟀나? — 95번(marketcap)에서 시총 축을 봄. **원전 문턱은 없음.**

### 4. 주도 업종
① 인용 — **문턱 숫자 못 찾았습니다.** 「선도주를 산다」는 취지의 말만 있습니다.
④ 이미 쟀나? — **61번(selection-leaders)**이 우리가 만든 「주도업종」 정의이고, 91·93 의 사다리 ①②가 그것입니다. **원전 귀속 아님.**

---

# ㉡ 매수 시점

### 5. VCP (변동성 수축 패턴)
① 인용 —
```
수축 «2~4회», 가끔 5~6회. 각 수축은 앞선 것의 «대략 절반» 깊이
(예: −20% → −10% → −5%)
수축이 진행될수록 «거래량이 마른다». 돌파일에 거래량이 «터진다»
```
② 출처 — [3차-해석] 다수 [검색요약]. 저장소 메모리 [[vcp-best-practices]]에 「피벗 = 마지막 가장 타이트한 수축의 고점 · 20~30%씩 축소 · 풀백 거래량 40~60% · 돌파 140~150%+ · 최종수축 ATR≈1/3」이 이미 정리돼 있습니다.
③ 구현 가능? — **이미 구현돼 있습니다** (`find-vcp`).
④ 이미 쟀나? — **쟀습니다. 16번**: 검출기(VCP·3C·PP)의 몫은 **−0.44%p, 구간 −0.95~+0.03 = 판정불가**.

### 5b. 파워플레이 (Power Play / High Tight Flag) — ★ **사용자 가설이 «맞았습니다»**

**사용자 가설(2026-08-29)**: 「파워플레이 만족 시 펀더멘털을 보지 않는다고 미너비니가 한 걸로 기억한다」

#### ① 인용 — **1인칭 문장이 있습니다** [『Trade Like a Stock Market Wizard』]
> "**This is the only situation I will enter with a dearth of fundamentals.** With the power play, the stock is exhibiting so much strength that it's telling you that something is going on **regardless of what the current earnings and sales are showing you**."
>
> (파워플레이는 **내가 펀더멘털이 빈약한 채로 들어가는 «유일한» 경우**다. 파워플레이에서는 주가가 워낙 강해서, **지금 실적과 매출이 무엇을 보여 주든 상관없이** 무언가 일어나고 있다고 말해 주는 것이다.)

#### ② 출처 · 등급
```
등급   [1차-본인] — «1인칭»이고 책에서 옮긴 문장입니다.
       🚨 다만 저는 **책을 직접 못 읽었습니다.** 아래 두 곳이 «따로» 이 대목을 싣습니다.
독립   2곳 — 서로 다른 사람의 «독서 노트»이고 2014년 / 2019년으로 5년 떨어져 있습니다
       · whatheheckaboom.wordpress.com (2014-05-04) — **위 문장을 통째로** 인용
       · tradershall.wordpress.com (2019-07-15) — 요약형 "the only situation he enters
         with a dearth of fundamentals" (3인칭으로 바꿔 적음)
확인   ⛔ 『Trade Like a Stock Market Wizard』 PDF 링크가 검색에 나왔으나 **열지 않았습니다**
       → **몇 쪽인지는 확인 불가.** 사용자가 원문을 보실 때 쪽수를 달아 주시면 [1차-전사]로 굳습니다
```

#### ③ 파워플레이의 «정의» — 실적 조건이 **안 들어 있습니다**
```
상승     **100% 이상을 8주 «미만»**에, 대개 «잠잠하던 기간» 뒤에
횡보     **3~6주** 동안 좁은 범위. 조정폭 **최대 20~25%**
         (더 좋은 것은 **10% 이내**로 «아주» 조밀한 것, 또는 VCP 성격을 보이는 것)
거래량   돌파 «며칠 전»에 거래량이 크게 마른다
별칭     high tight flag (고가 밀집 깃대)
실적     **정의에 없습니다** — 위 인용이 그것을 «명시»합니다
```
독립 출처 3곳 이상이 100% / 8주 / 3~6주 / 20~25% 를 같은 값으로 냅니다.

**우리 검출기와 대조** — 우리는 「깃대 + 조밀한 횡보」로 보고 있습니다.
```
✅ 깃대            = 「100% / 8주 미만」에 대응
✅ 조밀한 횡보      = 「3~6주 · 최대 20~25%」에 대응
⚠️ **「대개 잠잠하던 기간 뒤에」가 우리 정의에 있는지 확인 필요** — 원전에 붙어 있는 조건입니다
⚠️ **「돌파 며칠 전 거래량이 마른다」**도 마찬가지
🚨 우리 검출기의 «숫자»(몇 주·몇 %)가 원전 값과 같은지는 **제가 코드를 안 봤습니다. 미확인.**
```

#### ④ 반대 방향 근거 — **본인 말로는 못 찾았습니다**
```
찾은 것은 [3차-해석]의 «단서»뿐입니다:
  「실적을 면제해도 Stage 2 자격·VCP 수준의 가격/거래량·시장 국면·위험관리는 그대로 필요하다」
  「실적이 나빠지는 회사의 VCP 는 기관 수급이 안 붙는다」
🚨 둘 다 «파워플레이»가 아니라 «VCP 일반»에 대한 글쓴이 서술이고, 미너비니 인용이 안 붙어 있습니다.
→ **「파워플레이도 실적을 본다」는 본인 문장은 «없습니다».**
```

#### 🚨🚨 그런데 — **103 의 결과와 이 인용은 «같은 것이 아닙니다»**
```
원전이 말한 것    "a dearth of fundamentals"        = 실적이 **빈약하다** (자료는 «있고» 나쁘다)
                  "regardless of current earnings and sales"  ← 실적을 «보고» 무시한다는 말

103 이 가른 것    실적 자료가 **없는** 회사를 버리느냐 마느냐  (자료 자체가 «없다»)
```
> ### **「나쁜 실적을 무시한다」와 「자료가 없는 회사를 산다」는 다른 말입니다.**
> ### 원전 인용은 **앞을 뒷받침하고 뒤는 «직접» 뒷받침하지 않습니다.**

두 가지가 겹치는 정도(자료 없는 회사 중 파워플레이 비중)는 **두뇌 세션이 지금 재고 있는 분포**로만 갈립니다. **제가 여기서 「우리 결과가 원전과 맞다」고 적지 않겠습니다.**

#### 이 인용이 «따로» 만들어 내는 검정거리 하나
원문이 **"the only situation"** 이라고 못 박았으므로, 뒤집으면 이렇게 됩니다:
```
파워플레이  → 실적 조건 **면제**
VCP · 3C    → 실적 조건 **적용**       ← 이것도 원전 주장이고, 아직 «안 쟀습니다»
```
④ 이미 쟀나? — **미측정.** 패턴별로 실적 조건을 갈라 건 판은 없습니다(103은 전체에 걸었습니다).

### 6. 피벗 · 돌파일 거래량
① 인용 — 피벗 = 「마지막 수축의 고점 = 저항선」. 돌파는 「강한 거래량」에.
② 출처 — [3차-해석]. 🚨 **「몇 배」인지 본인 말로는 못 찾았습니다.** 우리 정본의 1.5배는 우리가 정한 값입니다.
③ 구현 가능? — 가능.
④ 이미 쟀나? — **19번**: 「일봉 거래량으로 돌파일을 검정하는 것 자체가 구조적 룩어헤드」. 22번에서 갭업·거래량 재검정.

### 7. 갭업 추격
① 인용 — **못 찾았습니다.**
④ 이미 쟀나? — 우리 규약(`max(pivot, open)`)은 [[entry-execution-method]] = **사용자 실제 방식**이지 원전 아님.

---

# ㉢ 팔기

### 8. 손절
① 인용 —
```
「최대 손절 10%」 · 「평균 손실 5~6%」
근거 일화: "I went from having a 15% loss normalised everything to a 10% stop
            and my account would have been up 72% instead of being down."
```
② 출처 — elearnmarkets [읽음] + Ameet Rai X 정리 [검색요약] — **둘 다 같은 «다섯 값 묶음»이라 계보 1개**. [3차-해석].
🚨 **「7~8%」로 적은 출처가 여럿 있으나 그건 오닐입니다.**
③ 구현 가능? — 가능.
④ 이미 쟀나? — **많이 쟀습니다.** 12·12ii·14·24번(청산 격자) · 68번(손절폭) · 79번. **「평균 5~6%」가 «규칙»인지 «그의 실적 통계»인지는 미확정** — 이 둘은 백테스트에서 전혀 다른 것입니다.

### 9. 분할 익절 · 추격 손절 · 본전 손절
① 인용 —
```
「강세에 일부 판다」 — 대개 «위험의 2~3배»(2R~3R)에서
「이익이 어느 정도 나면 손절선을 «본전»으로 올린다」
「나머지는 이동평균이나 직전 저점으로 «추격»한다」
「본전선에 닿은 뒤에는 50일선을 추격 손절로 쓴다 — 종가가 그 아래면 판다」
```
② 출처 — [3차-해석] [검색요약]. 🚨 **본전 손절은 저장소가 이미 반증한 항목입니다**([[exit-rules-path-and-profit-protect]], 87번).
③ 구현 가능? — 가능.
④ 이미 쟀나? — **쟀습니다. 87번(breakeven-floor) · 23번(래칫 손절, 12칸 전부 채택 근거 없음) · 41·67번(추격) · 76번(청산×피라미딩).** 🚨 74~76번에서 **「증액 후 손절을 본전으로 올리는 것」이 −160.87%p** 였습니다.

### 10. 보유 기간 · 실적 발표
① 인용 — 「이익 쿠션이 두텁지 않으면 실적 발표 «전»에 정리한다」 [3차-해석·본인 시황 요약]. 정해진 «보유 일수» 규칙은 **못 찾았습니다.**
④ 이미 쟀나? — 7번(time-limit) · 80번(경로 3년 연장). **실적 발표 전 매도는 미측정** (저장소에 실적임박 표시는 있음: [[threshold-newcomer-caution]]).

---

# ㉣ 크기 · 개수

### 11. 거래당 위험
① 인용 — [1차-본인]
> "Regardless of position size I'm never risking more than **1.25% of my total equity on average.. 2.5% max**. … **A 25% position size requires a 5% stop.**"
② 출처 — X id **1383099725092691971** [1차-본인, 검색요약]
🚨 **어긋나는 값이 있습니다** — 「1~2%」를 적은 [3차] 출처가 셋 [읽음].
③ 구현 가능? — 가능.
④ 이미 쟀나? — 메모리 [[minervini-fidelity-2026-08]]에 **「위험 1.25%가 실제로는 1.73%」**. 77·99번.

### 12. 종목당 비중
① 인용 — 「최적 **20~25%**」. **『Momentum Masters』 인터뷰에서 「켈리 공식 / Optimal f 로 2:1 트레이더에게 25%가 최적」이라는 «자기 근거»로 말함.**
② 출처 — **계보 둘**:
```
계보 A  다섯 값 묶음(20~25% · 최대손절 10% · 평균손실 5~6% · 한 종목 50% 상한 · 1.25/2.5%)
        elearnmarkets [읽음] · Ameet Rai X [검색요약] → **하나로 셈**
계보 B  『Momentum Masters』(본인 인터뷰) — 켈리 근거로 «비중만» 말함 [1차-본인, 검색요약]
```
🚨 **비중을 아예 안 말하는 [3차] 출처가 넷** 있고 그중 하나는 「7% 손절이면 최대 약 18%」라는 **다른 산수**를 씁니다.
③④ — 우리 판은 **5칸 20%**(77·99번). 쟀습니다.

### 13. 동시보유 개수 — ⚠️ **확정 못 했습니다**
① 나온 값 전부:
```
10~12개 (대형 전문 16~20), 소액은 «최소» 4~8    elearnmarkets [읽음]
4~6개 집중, 대형이면 10~12                       [검색요약]
4~8, 큰 계좌 10~12                               [검색요약]
4~10                                             pictureperfectportfolios [읽음]
10~20 상시, 핵심 2~3개가 수익 대부분             [검색요약]
**7개**  ← 본인 트윗의 «실제 사례»                X id 1884707172040241617 [1차-본인]
```
🚨 **본인 사례 7개는 «Minervini Select Portfolio» = 그의 «상품»입니다. 개인 매매가 아닐 수 있습니다.**
③ 구현 가능? — 가능. ④ — 58·86번(슬롯 수)에서 쟀으나 **원전 문턱이 없어 우리가 정한 격자**였습니다.

### 14. 노출 사다리 (Progressive Exposure)
① 인용 — [1차-본인]
> "With Progressive Exposure, when your trading is going well you **press and get more aggressive** with position sizing and overall exposure. Conversely, when not doing well you **cut back**."
파일럿 크기: 「보통 **5%** 로 시작」 [『Momentum Masters』 요약, 검색요약]
② 출처 — X id **1293567014720745472** [1차-본인] + [1차-전사] results/78·99 (사용자 전사)
🚨 **「¼→½→¾→풀」 4단은 제3자 해석입니다.** 웹은 **「파일럿 → 되면 증액」 2단까지만** 말합니다.
🚨 **파일럿 5%** 는 정본의 「¼」과 «다른 값»입니다.
③ 구현 가능? — 가능. ④ — **많이 쟀습니다. 47·73·74·75·76·77·78·99번.** 78번 결론: 「조건부가 항상분할보다 낫다」는 **못 가림**.

### 15. 노출을 올리는 «방아쇠»
① 인용 — [1차-본인] **이것이 이 문서에서 가장 확실한 한 줄입니다**
> "You can look at all the indicators and indexes you want, but I have a very simple method to gauge the health of the market and determine if I should get aggressive; **are your last 4 or 5 stocks profitable on balance.** If no, then you have no business increasing your exposure."
② 출처 — X id **1331694910899179524** (2020-11) [1차-본인, 검색요약]
③ 구현 가능? — **가능**. 「최근 청산된 4~5건의 합산 손익 > 0」.
④ 이미 쟀나? — **99번**에서 `recent` 5건 vs 20건을 봄(다른 칸을 내는 비율 2.0%). 「타율이 아니라 합산 순익」이라는 점은 정본과 **일치**.

### 16. 연속 손실 뒤 규모 축소
① 인용 — 「잘 안 되면 줄인다」 [1차-본인, 14번과 같은 트윗]. **「몇 연패면」이라는 «숫자»는 없습니다** — 정본의 오귀속 목록도 그렇게 적고 있습니다.
④ 이미 쟀나? — 9번(loss-streak-pause). **원전 숫자 없음.**

---

# ㉤ 시장 국면

### 17. 무엇을 보고 「위험」이라 하는가 — **정성적이고 거시까지 섞습니다**
① 인용 — [1차-본인]
> "With rates rising, **breakouts faltering**, Powell talking hawkish, and a market that can't rally much… I'm already in mostly cash" (X id **1715466694364139917**)
> "…the Nasdaq closed lower −4.00% … **Volume was well above average** while this market has still not been able to bounce for any longer than one single session with distribu[tion]…" (X id **1899477808214048922**)
> "With many leaders extended and **fresh distribution in the major indexes**, odds favor near-term pressure and consolidation." (X id **2047366164595302679**)
② 🚨 **그는 "distribution" 이라는 «말»을 씁니다. 그러나 「며칠에 몇 회면 위험」이라는 «세는 규칙»은 못 찾았습니다.** (사용자 확인으로도 원전에 없음)
③ 구현 가능? — **부분만.** 「지수 하락률 + 평균 대비 거래량」은 가능. 「Powell」은 불가.
④ 이미 쟀나? — 50~53·59·60·97번(국면). 🚨 **97번이 쓴 이진 on/off 는 원전 귀속이 아닙니다.**

### 18. 현금 비중
① 인용 — [1차-본인] "I'm already in **mostly cash**" · [3차] 「조정이면 현금으로 간다」
🚨 **「몇 %까지」라는 숫자를 못 찾았습니다.**
④ — 54번(exposure-benchmark).

### 19. 현금에서 «돌아오는» 방아쇠 — ★ **이것이 우리 ⑥과 정면으로 닿습니다**
① 인용 — [1차-본인]
> "When I go to cash people always ask 'how long do we have to wait?' My answer: '**As long as it takes! Until setups proliferate and breakouts start working.**'"
② 출처 — X id **1418195374506917891** [1차-본인, 검색요약]
③ 🚨 **우리 ⑥과 «두 가지»가 다릅니다**
```
그의 말   「후보가 늘어난다」 AND 「돌파가 «먹히기» 시작한다」   ← «짝»
우리 ⑥    후보 수 > 최근 60일 중앙값                          ← 앞 절«만»
숫자      그는 «문턱을 안 붙였습니다»                          ← 우리 60일 중앙은 원전 밖
```
🚨 **그리고 15번(「최근 4~5건이 이익인가」)과 «합치면 안 됩니다».**
「돌파가 먹히는가」는 **시장의** 돌파라 현금에서도 보이고, 「내 최근 4~5건」은 현금에서는 **관측 불가**입니다. 합치면 **현금이면 영원히 못 나오는 구현**이 됩니다. **사다리의 «두 단»입니다.**
④ 이미 쟀나? — 97번이 ⑥을 씀. **「돌파가 먹히는가」 쪽은 미측정.**

### 20. 「기계적 모델」이 따로 있다
① 인용 — [1차-본인] "Our **long term mechanical model** has not yet triggered a sell signal…" (X id 1874139838313574883)
② 🚨 **그 모델의 «내용»은 비공개입니다. 못 찾았습니다.**

---

# ㉥ 그 밖

### 21. 공매도 — ⚠️ **저장소 메모리와 어긋납니다**
① 인용 — [1차-본인]
> "I am still **short the $SPY** from 12/9. My stop is at all-time highs on both the ETF and the cash index… Personally, I have no longs." (X id **1874139838313574883**)
② 🚨 저장소 메모리 [[short-interest-feasibility]]는 **「미너비니 미사용(99.99% 롱)」**이라 적고 있습니다.
**어느 쪽이 틀렸다고 안 적겠습니다** — 「개별주 공매도를 안 한다」와 「지수 ETF를 숏으로 헤지한다」는 **다른 말일 수 있습니다.** 갈라야 할 항목으로 남깁니다.
③ 구현 가능? — 가능하나 **우리 하네스는 롱 전용**입니다.
④ **미측정.**

### 22. 분산투자
① 인용 — [3차, 본인 취지 요약] 「업종·산업 분산은 시장 전체가 내릴 때 «거의 보호가 안 된다»」 · 「50개 잔포지션이 자산곡선을 희석하는 걸 원치 않는다」
④ — 17번(분산손실 −18.4%p) · 86번.

### 23. 연 수익률 목표
① — **못 찾았습니다.** 「연 몇 %를 목표한다」는 말을 못 봤습니다.

---

# 🚨 「책을 봐야 갈리는」 목록 — 사용자께 그대로 갑니다

**코드가 바뀌는 것**
1. **트렌드 템플릿 6번이 52주 저가 +25% 인가 +30% 인가** — 웹이 갈리고 「책은 30%」라 적은 곳이 있습니다.
2. **거래당 위험이 1.25%/2.5% 인가 1~2% 인가** — 본인 트윗은 앞, [3차] 셋은 뒤.
3. **동시보유 «기본»이 몇 개인가** — 웹은 4~20으로 흩어지고, 본인 사례 7개는 «상품»일 수 있습니다.
4. **파일럿이 ¼ 인가 5% 인가, 사다리가 몇 단인가** — 웹은 2단까지만 말합니다.
5. **실적 조건의 숫자** — EPS 20/25/30, 매출 15/20/25 로 갈립니다.

**방법이 바뀌는 것**
6. **분산일·후속매수일을 그가 «쓰는가».** 오닐 정의는 확실한데 **그가 쓴다는 본인 근거가 없습니다.**
7. **「setups proliferate」에 숫자가 붙는가** — 붙으면 우리 ⑥의 문턱이 원전에서 나오고, 안 붙으면 ⑥은 «우리가 만든 것»으로 남습니다.
8. **손절 「평균 5~6%」가 규칙인가 그의 실적 통계인가** — 백테스트에서 전혀 다릅니다.
9. **비중을 먼저 정하고 개수가 따라오는가** — [3차] 한 곳이 「비중은 위험예산의 «결과»」라고 «명시»합니다. 책이 같은 말을 하는지.
10. **공매도** — 개별주는 안 하고 지수 ETF만 숏인가.

---

# 출처
[1차-본인 · X — 전부 402 로 페이지는 못 읽음, 본문은 검색엔진 인용]
- [1331694910899179524 — 최근 4~5건이 이익인가](https://x.com/markminervini/status/1331694910899179524)
- [1418195374506917891 — setups proliferate / breakouts start working](https://x.com/markminervini/status/1418195374506917891)
- [1293567014720745472 — Progressive Exposure](https://x.com/markminervini/status/1293567014720745472)
- [1383099725092691971 — 1.25% / 2.5%, 25% 비중이면 5% 손절](https://x.com/markminervini/status/1383099725092691971)
- [1715466694364139917 — breakouts faltering, mostly cash](https://x.com/markminervini/status/1715466694364139917)
- [1899477808214048922 — 지수 −4.00%, 거래량 평균 이상, distribution](https://x.com/markminervini/status/1899477808214048922)
- [1874139838313574883 — SPY 숏, mechanical model](https://x.com/markminervini/status/1874139838313574883)
- [1884707172040241617 — Select Portfolio 7종목](https://x.com/markminervini/status/1884707172040241617)
- [1826989022041850163 — Timing / Turnover / Aggressive sizing / Cash](https://x.com/markminervini/status/1826989022041850163)

[1차-전사 · 사용자가 옮겨 준 책 원문]
- `results/78-source-quotes.md` · `results/99-source-faithful.md`

[3차-해석]
- [elearnmarkets — Think and Trade Like a Champion](https://www.elearnmarkets.com/school/units/think-and-trade-like-a-champion) [읽음]
- [financialtechwiz — Minervini Trading Strategy](https://www.financialtechwiz.com/post/mark-minervini-trading-strategy/) [읽음]
- [finermarketpoints — SEPA & VCP Guide](https://www.finermarketpoints.com/post/what-is-mark-minervini-s-trading-strategy-the-complete-sepa-vcp-guide) [읽음]
- [Picture Perfect Portfolios](https://pictureperfectportfolios.com/how-to-invest-like-mark-minervini-momentum-trading-champion/) [읽음]
- [Deepvue — Trend Template](https://deepvue.com/screener/minervini-trend-template/) [읽음]
- [paperswithbacktest — Mark Minervini](https://paperswithbacktest.com/wiki/mark-minervini) [읽음]
- [sobrief — Momentum Masters 요약](https://sobrief.com/books/momentum-masters) [검색요약 · 403]
- [X — Ameet Rai, Position Sizing Rules 정리](https://x.com/AmeetRai/status/1864744561668423792) [검색요약]

[파워플레이 — 책 인용을 싣는 «독서 노트» 두 곳, 5년 떨어져 있음]
- [whatheheckaboom — Book Review of Trade Like A Stock Market Wizard (2014-05-04)](https://whatheheckaboom.wordpress.com/2014/05/04/book-review-of-trade-like-a-stock-market-wizard-by-mark-minervini/) [읽음 — **1인칭 원문을 통째로** 인용]
- [tradershall — Trade Like A Stock Market Wizard Book Review and Notes (2019-07-15)](https://tradershall.wordpress.com/2019/07/15/mark-minervinis-trade-like-a-stock-market-wizard-book-review-and-notes/) [읽음 — 3인칭 요약형]
- [BrkoutGeek — Power Play Setup](https://brkoutgeek.substack.com/p/mark-minervinis-power-play-setup) [읽음 — 숫자 없음·실적 언급 없음]
- [Trading Engineered — The Powerplay Setup](https://tradingengineered.substack.com/p/the-powerplay-setup) [읽음 — 100%/2개월/2~3주·실적 언급 없음]

# 못 읽은 곳 (차단)
```
403 : TraderLion · ChartMill · Scribd · Stockopedia(Medium) · quantifiedstrategies
      · aistockselection · glasp · tradingliteracy · sobrief
402 : X(트위터) «전부»
⛔ 열지 않은 것 : 『Momentum Masters』 전문 PDF (무단 사본으로 보임)
```

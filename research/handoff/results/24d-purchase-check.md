# 24d — 결제 전 확인 (Sharadar)

- **공개 페이지 읽기만. 가입·결제·계정 생성 없음.** 자료는 한 건도 받지 않았다.
- 읽은 곳: `/subscribe` · `/prices` · `/docs/stocks` · `/docs/tickers` · `/docs/auth` ·
  `/docs/getting-started` · `/docs/faqs` · `/terms`
- **못 읽은 곳: `/docs/bulk`** — 본문이 **"Loading… Checking session…"**으로 **로그인을 요구한다.** 우회하지 않았다.

---

## ① 상품 — **`Prices` $9/월. 우리에게 필요한 표가 다 들어 있다.**

`https://sharadar.com/subscribe` 의 네 상품:

| 상품 | 월 | 포함 표 |
|---|---:|---|
| Fundamentals | $19 | descriptions · tickers · fundamentals · daily · **actions** · events · sp500 |
| **Prices** | **$9** | **descriptions · tickers · stocks · funds · metrics** |
| Investors | $19 | descriptions · tickers · insiders · holdings · … |
| Bundle | $29 | 전부 |

**→ `$9`가 단독 상품이 맞고, 번들을 살 필요가 없다.**

### 가격 표 `stocks` (`/docs/stocks`)

컬럼(원문 그대로): **`ticker` `date` `open` `high` `low` `close` `volume` `closeadj` `closeunadj` `lastupdated`**
> "End-of-day (EOD) Open, High, Low, Close and Volume (OHLCV) price data for **active and delisted** US public stocks"
> 시작 **"January 1998"** · **"Current count of 21,000 tickers"**

`/prices` 페이지:
> "**25,000+ tickers covering more than 10,000 active and 15,000 delisted securities**"
> "History back to **December 1998**"

### ★ 시점 유니버스 — **가능하다. `tickers` 표가 $9에 포함된다.**

두뇌 세션이 짚은 관건("그날 존재했는가를 가격 표만으로 알 수 있는가")의 답:

`tickers` 컬럼(원문): **`permaticker` `ticker` `name` `exchange` `isdelisted` `category` `firstpricedate` `lastpricedate`**
> "There is no default date window for the tickers table (**full universe including delisted**)"

**→ `firstpricedate ≤ D ≤ lastpricedate` 로 그날 상장 여부가 나온다. 별도 구매 불필요.**

### ★★ 그리고 이 표가 **제가 0단계에서 만든 오염을 고친다**

Tiingo `endDate`는 "상폐"와 "커버리지 중단"이 안 갈렸고, 표본의 12.5%가 **지금도 거래 중**이었다.
Sharadar는 **`isdelisted` 라벨을 직접 주고**, 티커 재사용 문제도 명시적으로 처리한다:

> "When a company is delisted and its ticker is later reused by a different company, **the active company keeps the ticker and the delisted company gets a number appended**. … we provide a **permaticker** … Sharadar's own unchanging and unique identifier"

**→ DCBO 같은 사례가 구조적으로 생기지 않는다.**

### 생존 편향 — 공급자 문구 원문

> "Yes, we have extensive delisted stock coverage and **estimate our data is 99% free of survivorship bias**. To our knowledge this is the most comprehensive dataset that is free of survivorship bias and readily available. We're continuously working on that last 1%…"

**공급자 주장이고 제가 실측하지 않았다.** 다만 **99%라고 스스로 한계를 적은 점**은 기록해 둔다.

### 개인 용도 — **우리 쓰임이 명시적으로 허용된다**

> "Does the Personal Use license cover trading my own account, research, or product development? **Yes.** Personal Use covers individuals using the data for their own purposes: **research, backtesting**, and automated trading of their own account with no external clients or money managed for others."

---

## ② API 키 — 가입·로그인 후 문서 페이지에서 받는다

> "You can get your **free API key by signing up**."
> "If you've already registered and are signed in, **your API key is listed below**." → `https://sharadar.com/docs/auth`

전달 방식:
> "?api_key=…" — 예: `https://api.sharadar.com/v1.0/data/fundamentals?api_key=…&ticker=AAPL`
> (가입 전에도 `test-api-key`로 **AAPL만** 조회 가능)

---

## ③ 접근 방식 — **벌크가 정본, REST는 보조**

> **"The easiest way to retrieve data is the bulk download method. This allows you to download entire tables in zipped CSV format with 5, 10 or full history depending on your preference and subscription permissions.** The downloads are pre-prepared and available at a single click or API call. We also provide a REST API which allows you to filter for the precise data you want to retrieve, **which is suitable in the event you want a limited amount of data**."

REST 사양(`/docs/getting-started`): 기준 URL `https://api.sharadar.com/v1.0/data/` ·
**기본 10,000행/요청**(`limit`로 조정) · `skip`으로 쪽 넘김 · `csv`/`json`.
**호출 한도(분/일)는 문서에 없다.**

**→ "한 번에 다 받아 로컬에 두고 구독 중 반복 실행"이라는 사용자 흐름은 벌크로 정확히 가능하다.**
우리 창(2020-01~2026-08, 약 1,670 거래일)은 **표 하나를 통째로 받아 자르는 편이 낫다.**

> ### 🚨 **여기가 유일한 미확인이고 결제 전에 알아야 한다**
> **"5, 10 or full history depending on … subscription permissions"** —
> **$9 `Prices` 상품이 "full history"를 받는지, 5년으로 잘리는지 확인하지 못했다.**
> `/docs/bulk` 본문이 **로그인 뒤에 있다.**
> **우리는 2020-01부터가 필요하다 = 6.6년이라, 5년으로 잘리면 모자란다.**
> ⚠️ 다만 **막히지는 않는다** — REST는 `from`/`to`로 임의 구간을 받을 수 있고
> (기본 창이 1년일 뿐 조정 가능), 10,000행씩 `skip`으로 넘기면 된다.
> **결제 직후 `/docs/bulk`에서 이 한 줄을 먼저 확인**하면 된다.

---

## ④ 잘못 사기 쉬운 지점

| # | 주의 | 근거 |
|---|---|---|
| 1 | **자동 결제가 기본이다** | "The credit card which you provide will **automatically and immediately be billed**" |
| 2 | **환불 없다** | "If you cancel your subscription you will no longer be billed but **no money already paid will be refunded**" |
| 3 | **해지는 기간 말에 적용** | "You may terminate your use … **at the end of the then-current subscription period**" |
| 4 | **해지하면 자료를 지워야 한다** | "**Within thirty (30) days of termination**, you will delete … all copies of the Services Data" (결과·요약통계 등 파생물은 유지 가능) |
| 5 | **개인 명의로만** | "Subscriptions … are individual and **may not be purchased or paid for as a shared institutional or corporate resource**" |
| 6 | **비슷한 이름 주의** | `Fundamentals $19`·`Investors $19`·`Bundle $29`는 **우리에게 불필요**하다. **`Prices $9`만** 고른다 |
| 7 | **`actions` 표는 $9에 없다** | 상폐 사유·티커 변경 이력은 `Fundamentals`/`Bundle` 쪽이다. **`permaticker`로 대체 가능해 필수는 아니다** |
| 8 | **자료 평가 공개 금지 조항** | "You may **not publish evaluations of this data** without permission" — 개인 연구는 무관하나 조항만 옮긴다 |

### 그리고 구현에서 반드시 지킬 것 하나

> **`open`·`high`·`low`·`volume`은 "split-adjusted"다.** 우리 한국 하네스는 **수정주가 룩어헤드를 피하려고
> 일부러 비수정 원본 거래대금**을 쓴다. Sharadar에서 같은 것을 하려면:
> > "**CloseUnadj is unadjusted and can be used to impute unadjusted Open, High, Low and Volume.**"
> **→ `closeunadj / close` 비율로 되돌려야 한다.** 이 단계를 빠뜨리면 **한국 쪽에서 제거한 룩어헤드가
> 미국 쪽에만 다시 들어가고, 대조가 무효가 된다.**

---

## `.env` 키 이름 제안

기존 관례가 `DART_API_KEY` · `KIS_APP_KEY` · `NAVER_CLIENT_ID` 형식이므로:

```
SHARADAR_API_KEY=여기에_키
```

`.gitignore` 4번 줄에 `.env`가 이미 등록돼 있어 **커밋되지 않는다.**
**키를 채팅에 붙여넣지 말고 `.env`에 직접 적는 방식이 맞다.**

---

## 확인하지 못한 것

1. **`Prices $9` 벌크의 history 깊이(5 / 10 / full)** — 로그인 뒤에 있다. **결제 직후 첫 확인 항목.**
2. **REST 호출 한도(분/일)** — 문서에 없다.
3. **"99% survivorship bias free"** — 공급자 주장이고 실측하지 않았다.
4. **`stocks` 표의 실제 행 수** — 받아 보기 전에는 모른다.
   (거칠게: 활동 티커 8,000~12,000 × 1,670 거래일 ≈ **1,300만~2,000만 행**)

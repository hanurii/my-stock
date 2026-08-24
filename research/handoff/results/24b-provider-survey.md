# 24b — 공급사 폭넓은 확인 (읽기·탐침만)

- 지시서: 두뇌 세션 26-08-24 «① 무료(또는 훨씬 싼) 공급사를 폭넓게»
- **가입·결제·계정 생성 없음. 대량 수집 없음.** 받은 것은 **공개 메타파일 1개**(Tiingo `supported_tickers.zip`)와
  **탐침 100회 미만**(Stooq 50 · Yahoo 50)뿐이다. **가격 자료를 디스크에 저장하지 않았다.**

---

## 🚨 먼저 — **제 0단계 수치 하나를 정정한다**

0단계에서 **"`endDate`가 창 안인 4,589건 = 상폐"**로 셌고, 그때 *"`endDate`는 상폐일이 아니라
가진 마지막 가격일"*이라고 단서를 달았다. **이번 Yahoo 탐침이 그 단서를 실측으로 확인했다.**

표본 40건 중 **5건은 지금도 거래되고 있다**(Yahoo 마지막 거래일이 전부 **2026-08-17**):

| 티커 | Tiingo `endDate` | Yahoo 행수 | Yahoo 마지막 |
|---|---|---:|---|
| DCBO | 2022-12-30 | 1,431 | **2026-08-17** |
| BTEK | 2024-08-15 | 1,477 | **2026-08-17** |
| PINC | 2025-11-25 | 46 | 2026-08-17 |
| STRD | 2026-05-28 | 300 | 2026-08-17 |
| UROY | 2026-07-27 | 1,332 | 2026-08-17 |

**→ 4,589건은 "상폐 수"가 아니라 상한이고, 표본에서 12.5%가 커버리지 중단이었다.**
**Tiingo 메타를 "상폐 정답지"로 쓰면 안 된다.** 검사 도구로는 여전히 쓸 수 있으나
**"사라진 종목"이 아니라 "Tiingo가 더는 안 주는 종목"으로 읽어야 한다.**

---

## ★ yfinance(Yahoo) — **실측으로 결격**

같은 표본 40 + **대조군 10**(살아 있고 2019 이전 시작). Stooq에서 오보를 잡은 그 장치를 그대로 썼다.

| | 결과 |
|---|---|
| 사라진 종목 40 | **HTTP 404 = 35건 · 응답 있음 5건** |
| **대조군 10** | **10 / 10 정상** → **탐침이 유효하다** |
| 응답 있던 5건 | **전부 현재도 거래 중**(위 표) — 상폐 시점 자료가 아니다 |

**→ 표본 40건 중 "상폐 시점에서 끝나는 시계열"은 0건이다.**
그리고 **응답 있던 5건은 더 나쁘다** — 없는 게 아니라 **지금 다른 값을 준다.**
**조용히 틀린 자료가 들어온다.**

---

## 공급사 표 — **①이 관문이다**

| 공급사 | **① 상폐** | ② 2020 이전 | ③ 전수 수집 | ④ 한도·비용 | ⑤ 약관 |
|---|---|---|---|---|---|
| **yfinance (Yahoo)** | ❌ **실측 35/40 404** | — | 무료 | 무료·비공식 | 확인 안 함 |
| **Stooq 벌크** | ❓ **확인 불가**(안티봇 PoW) | ❓ | ❓ | 무료 | ❓ |
| **Sharadar Prices** | ✅ **공급자 명시** "survivorship bias-free", 1998~ | ✅ | 벌크 표 | **$9/월** · 최소약정 없음 | **읽음** — 해지 후 30일 내 삭제, 파생물 유지 가능 |
| **Tiingo Power** | ⚠️ `endDate` 있음(위 정정 참조) | ✅ 1962~ | 109,753 심볼/월 | **$30/월** | **읽음** — 해지 시 즉시 삭제 |
| **EODHD** | ✅ **문서** "Delisted Data ✓"(무료 티어 제외) | ✅ "Ford Motors from Jun 1972" | 100,000 req/일 | **$19.99/월**(EOD All World) | 확인 안 함 |
| **Polygon → Massive** Starter | ❓ 문서에 없음 | ❌ **5년치뿐**(2020-01은 6.6년 전) | flat files | $29/월 | 확인 안 함 |
| 〃 Developer | ❓ | ✅ 10년 | flat files | **$79/월** | 확인 안 함 |
| **QuantConnect 무료** | ❓ 요금 페이지에 명시 없음 | ❓ | **클라우드 전용** | 무료. **로컬 내려받기는 QCC 토큰(유료)** | 확인 안 함 |
| **Norgate** | ✅ 상폐 자료 제공 | ✅ | 벌크 | 상폐 애드온 **$270/년 ≈ $22/월** · **최소 6·12개월 약정** | 확인 안 함 |
| **Alpha Vantage 무료** | ✅ 상폐 심볼 조회 제공 | ❓ | ❌ **25 req/일 → 12,876개에 515일** | 무료 | 확인 안 함 |
| **Finnhub 무료** | ❓ | ❓ | 60 req/분 | 무료 | 확인 안 함 |
| **Nasdaq Data Link 무료 테이블** | ❓ **확인 안 함** | ❓ | ❓ | 무료 | 확인 안 함 |
| **CRSP / WRDS** | ✅ 학계 표준 | ✅ | 벌크 | **기관 구독 필요** — 개인 접근 경로 확인 안 함 | 확인 안 함 |
| Kaggle·Zenodo 공개셋 | ❓ **확인 안 함** | ❓ | ❓ | 무료 | 라이선스 제각각 |

### 이 표에서 확실한 것만 추리면

- **무료 중 ①을 통과한 곳은 하나도 확인되지 않았다.**
  yfinance는 **실측으로 결격**, Stooq는 **확인 불가**, Alpha Vantage는 **④에서 결격**(515일),
  QuantConnect는 **로컬 사용이 유료**, 나머지 무료는 **확인 안 함**.
- **가장 싼 유료는 Sharadar $9/월**이고, **약관을 실제로 읽은 곳은 Sharadar와 Tiingo 둘뿐**이다.
- **EODHD $19.99는 상폐를 문서로 명시**하지만 **약관을 읽지 않았다.**
- **Polygon Starter($29)는 5년치라 기간이 모자란다** — 이 과제는 2020-01부터 필요하다.

---

## 확인하지 못한 것 — 이름을 적는다

1. **Nasdaq Data Link 무료 테이블 · Kaggle/Zenodo 공개셋 · CRSP/WRDS 개인 접근 조건** — **보지 않았다.**
2. **EODHD·Polygon·Norgate·QuantConnect의 약관** — 읽지 않았다.
   **Tiingo·Sharadar에서 나온 "해지 후 삭제" 조항이 이들에도 있는지 모른다.**
3. **Finnhub·SimFin의 상폐 정책** — 문서에서 못 찾았다.
4. **①을 표본 대조로 실측한 곳은 yfinance 하나뿐**이다. 나머지는 **가입이 필요해 탐침을 못 했다**(지시대로 가입 안 함).
5. **Tiingo `endDate`를 정답지로 쓴 것 자체가 오염돼 있다**(위 정정). **그래서 이번 실측의 "35/40 404"도
   엄밀히는 "Tiingo가 더는 안 주는 종목 중 87.5%를 Yahoo도 안 준다"**이다.
   ⚠️ **다만 결론 방향은 바뀌지 않는다** — 응답 있던 5건이 전부 현재 거래 중이라
   **상폐 시점에서 끝나는 시계열은 0건**이었다.

---

# 마무리 넷 (두뇌 세션 지시 — 더 넓히지 않음)

## 1. EODHD 약관 — **해지 후 삭제 조항이 여기에도 있다. 총액 역전 없음.**

> **"Upon termination or expiration of the subscription, the subscriber is required to delete all copies of the data in their possession within one (1) month."**
> (그리고 EODHD는 **삭제 확인을 요구할 권리**를 둔다.)

구독 중 저장:
> "EOD Historical Data Information may be stored on the subscriber's premises during the active subscription period."

재배포:
> "Selling, reselling, retransmitting, redistributing, displaying, or granting access to the Information or Services, whether in its original or repackaged form" — 비전문 사용자에게 **금지**

약정·환불:
> "Our subscription is monthly based and the User has no long-term obligations here. The User can cancel subscription anytime, **the minimum period of commitment is one month**."
> **"All subscription payments made to EOD Historical Data are final and non-refundable."**

**→ 읽은 세 곳(Tiingo·Sharadar·EODHD)이 전부 "해지 후 삭제"를 요구한다.**
**"$19.99를 한두 달만 쓰고 자료를 남긴다"는 성립하지 않는다.**
세 곳의 유예만 다르다: **Tiingo 즉시("promptly") · Sharadar 30일 · EODHD 1개월.**

## 2. Finnhub 무료 — **①을 볼 것도 없이 결격**

> 과거 일봉(`/stock/candle`)이 **유료 티어로 이동했고 무료 키에는 403을 반환한다.**
> 무료는 호출당 **1년치**만 준다(해상도 낮추면 더).

**→ ③(전수)·④(한도)에서 먼저 막힌다.** 상폐 정책은 확인하지 못했고 **확인할 필요가 없어졌다.**

## 3. Nasdaq Data Link 무료 테이블 — **2018년 3월에 멈춰 있다**

무료 `WIKI Prices`는 **1962~2018 미국 일봉이고 상폐 포함**이지만:
> **"Wiki Prices … only provides data going up to March 2018"** — 2018년에 폐기됨.
> 사유: "one of the main sources of that data is no longer available"

그리고 Nasdaq 자신이 이렇게 적는다:
> **"Free stock price data feeds are not available to replace Wiki Prices"** → 유료 EOD·SEP를 권한다.

**→ 우리 창은 2021-02-01부터다. ②에서 결격.**
⚠️ **공급자가 "무료 대체재는 없다"고 명시한 것은 이 조사 전체에 대한 방증이다.**

## 4. Kaggle·Zenodo 공개 데이터셋 — **출처를 확인하지 못했다**

| 후보 | 내용 | 판정 |
|---|---|---|
| Kaggle `Arandkei: Historical Delisted Assets Archive` | 상폐 종목 일봉 아카이브(2026-03 갱신)라고 소개됨 | **확인 불가** — 페이지가 스크립트로 렌더링돼 **라이선스·출처·종목 수·기간을 읽지 못했다.** 가입 없이는 API도 못 쓴다 |
| Zenodo `HF Data Library`(DOI 10.5281/zenodo.19501605) | 1분봉, **1,391 종목**, 2002~ | **③에서 결격** — 큐레이션된 부분집합이라 **유니버스 전수가 아니고 RS 백분위를 못 만든다** |
| Kaggle `Quandl WIKI Prices` | 위 3번과 같은 자료 | **②에서 결격**(2018) |

> 🚨 **그리고 두뇌 세션 규칙이 여기서 먼저 걸린다** — *"출처 불명 데이터셋은 쓰지 않는다."*
> **Arandkei는 출처를 확인하지 못했으므로, 라이선스가 어떻든 그 규칙에서 탈락한다.**
> **확인하려면 가입이 필요하고, 지시대로 가입하지 않았다.**

---

## 마무리 — 무료 쪽 결론

| 후보 | 막힌 곳 | 근거 |
|---|---|---|
| yfinance | **①** | **실측 35/40 HTTP 404**(대조군 10/10 정상) |
| Stooq | **확인 불가** | 안티봇 PoW |
| Alpha Vantage 무료 | **④** | 25 req/일 → 12,876개에 **515일** |
| Finnhub 무료 | **③④** | 과거 일봉이 유료(무료 키 403) |
| Nasdaq 무료 WIKI | **②** | **2018-03에서 멈춤** |
| QuantConnect 무료 | **③** | 클라우드 전용, 로컬은 유료 토큰 |
| Kaggle Arandkei | **출처** | 라이선스·출처 확인 불가 |
| Zenodo HF Data | **③** | 1,391 종목 부분집합 |

**무료 중 네 조건을 통과한 곳은 없다.**
**유료 최저가는 Sharadar $9/월**이고, **셋 다 해지하면 자료를 지워야 한다.**

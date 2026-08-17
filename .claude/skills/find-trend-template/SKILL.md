---
name: find-trend-template
description: >
  SEPA 종목 발굴의 첫 관문. Minervini 트렌드 템플레이트 8조건을 만족하는
  KOSPI+KOSDAQ 종목을 RS 80(SEPA 실전 기준)으로 추려 SEPA 전용 후보 파일
  (sepa-trend-candidates.json)에 저장한다. 공유 trend-template-candidates.json·
  make-hero·페이지 데이터는 일절 건드리지 않는다. 사용자가 "/find-trend-template",
  "SEPA 1단계", "추세 통과 종목 찾아줘", "트렌드 템플레이트로 SEPA 후보 추려줘"
  등을 요청할 때 사용.
---

# find-trend-template — SEPA 1단계: 추세 선별

SEPA(Specific Entry Point Analysis) 종목을 찾는 파이프라인의 **첫 단계**.
마크 미너비니의 **트렌드 템플레이트 8조건**을 만족하는 종목만 남겨, 이후
하위 스킬(베이스/VCP 분석 등)의 입력이 될 **SEPA 전용 후보 리스트**를 만든다.

이 스킬은 **얇은 빌딩블록**이다 — 스크리너 1단계만 실행하고, C 점수·코드33·
자동 commit 같은 일은 하지 않는다.

## 정의 원본 (트렌드 템플레이트 8조건)

`research/oneil-model-book/trend_template.md` 가 정의 원본. 요약:

1. 주가가 150일·200일 이평선 위
2. 150일 이평선이 200일 이평선 위
3. 200일 이평선이 최소 1개월(이상적으로 4~5개월) 상승 추세
4. 50일 이평선이 150일·200일 이평선 위
5. 주가가 50일 이평선 위
6. 주가가 52주 신저가보다 최소 30% 위
7. 주가가 52주 신고가의 25% 안 (가까울수록 좋음)
8. RS(상대강도) ≥ 합격선 — **이 스킬 기본 80** (SEPA 실전 기준)

## 불변 원칙

- **공유 파일 무접촉**: `public/data/trend-template-candidates.json` 을 절대
  덮어쓰지 않는다(make-hero·`/stocks/trend-template` 페이지가 RS 70으로 공유
  중인 파일). 반드시 `--out` 으로 SEPA 전용 파일에만 쓴다.
- **컷오프 금지(공유 산출물)**: 시총·거래대금·가격 컷오프를 추가하지 않는다
  ([screener-no-cutoff] 메모리 준수). **단 하나의 의도된 예외** — SEPA 전용
  실행은 `--minervini-filter` 로 **'미너비니가 사지 않는 주식'**(우선주·코스닥
  외국법인·저유동성 50일 평균 거래대금<5억)을 유니버스에서 제외한다
  (사용자 확정 2026-08-03, 7월 연쇄 손절 공통점 실측 근거). 플래그 없이는
  기존과 동일하므로 공유 trend-template/make-hero 는 무영향. 세부 근거:
  `docs/superpowers/specs/2026-08-03-minervini-non-buyable-filter.md`.
- **환각 금지**: 통과 종목 수·RS 등은 콘솔 출력 그대로 보고. 추측·요약 금지.

## 사전 조건

- **최신 데이터로 돌리려면 먼저 `update-data` 스킬 실행** — OHLCV 시세 행렬을
  최신 영업일까지 갱신한다(캐시 삭제 없음). 안 돌리면 행렬에 마지막으로 쌓인
  날짜 기준으로 선별됨.
- `.env` 의 `DATA_GO_KR_KEY` (공공데이터 일봉 — OHLCV 행렬 필수).
- OHLCV 행렬이 최초 1회 백필돼 있어야 함. 비어 있으면 첫 실행이 ~400영업일을
  채우느라 느림(`pwsh -File scripts/canslim_parallel.ps1` 한 번이면 채워짐).
  이후엔 행렬 캐시 hit 으로 빠름.
- 평가 부품: `scripts/canslim_lib/trend_template.py`.

## 실행 절차 (1줄)

```
python scripts/screen_trend_template.py --rs-min 80 --minervini-filter --ipo-track --out public/data/sepa-trend-candidates.json --save
```

- 산출: `public/data/sepa-trend-candidates.json`
- `--ipo-track`: 신규상장(상장 20~199거래일) 예외 트랙 — 200일 데이터가 없어 8조건
  평가가 불가능한 종목을 대체 7조건(상장 후 고저가·기준MA·iRS=전 종목 동일 창
  percentile·미너비니 필터)으로 별도 평가해 `ipo_candidates` 배열에 담는다.
  기존 candidates/failed_stocks 는 불변(플래그 없으면 산출 종전과 동일).
  파라미터 정본: `scripts/canslim_lib/ipo_track.py` DEFAULT_PARAMS.
  설계·근거: `docs/superpowers/specs/2026-08-08-ipo-exception-track-design.md`.
  `/stocks/sepa` 1단계 섹션에 "🐣 IPO 트랙" 요약이 뜬다.
  - 부산출(진단용): `public/data/sepa-halted-stocks.json` — 유니버스에서 빠진
    거래정지·제외 종목과 **정지 사유**(DART 공시 기준 `temporary` 일시적 기업행위 /
    `serious` 상장적격성 등 / `unknown` 불명). "이 종목이 왜 후보에 안 나오지?"를
    되짚는 용도이며 **제외 규칙 자체는 바꾸지 않는다**. DART가 죽어도 비차단.
  - 부산출(진단용): `public/data/sepa-minervini-excluded.json` — `--minervini-filter`
    가 걸러낸 '미너비니가 사지 않는 주식' 목록·사유(우선주/외국법인/저유동성).
    유니버스 단계 제외라 VCP·3C·파워플레이(트렌드/전수)·매수추천 전부에 전파된다.
  (구조는 기존 candidates JSON과 동일: `candidates[]`, `market_status`,
  `all_pass_count`, `rs_min` 등)
- 소요: ~1분 (행렬 캐시 hit 시), 첫 실행/캐시 비운 직후 ~3-5분.

### 옵션

- `--rs-min 70` : 정의서 기본선으로 완화(미너비니 책 기준). SEPA 실전은 80 권장.
- `--market KOSPI` / `--market KOSDAQ` : 한 시장만.
- `--asof YYYY-MM-DD` : 과거 시점 기준(룩어헤드 방지 백테스트용).
- `--minervini-filter` : '미너비니가 사지 않는 주식' 제외(SEPA 정규 실행은 항상 켬).
- `--min-turnover-eok 5` : 저유동성 기준(50일 평균 거래대금, 억원) 조정. 기본 5억
  (최초 10억 → 원장 소급 검증으로 하향: 5~10억 밴드가 최고 성과, 5억 미만은 +20% 0/98).

## 결과 확인

- 콘솔의 `✨ 8개 모두 통과: N종목` — 보통 RS 80 기준이면 정의서 70보다 종목 수
  적음. 강세장에서 수십~100여 종목.
- 산출 JSON 의 `market_status` 가 `Stage 2`(상승 추세장)인지 — 약세장이면
  통과 종목이 급감하는 게 정상.
- `candidates[].all_pass == true` 인 종목이 SEPA 다음 단계 입력. 추가로
  `gate_near == true`(관문 임박: 6~7/8 통과 + 실패가 **①⑤⑦뿐** + 근접 한도
  이내 — ① 150·200MA -10% · ⑤ 50MA -15% · ⑦ 52주고가 -35%, `GATE_NEAR_TOL`)인
  종목도 패턴 검출기(find-vcp·find-3c·find-power-play)까지 통과한다 — 이평선 바로 밑
  코일(한양이엔지 미스, 26-08-11)과 깊은 베이스 VCP(⑦만 미달: 메가터치 -32.3%
  08-07 · 네오오토 -34.1% 08-13→다음날 +20.2% 폭발)가 돌파 전날 걸러지는 구조적
  충돌 완화. ⑦ 한도 변천: 26-08-11 -40% 허용(40종목 유입) → 26-08-12 필수 환원
  → **26-08-17 -35% 재완화(사용자 결정, 네오오토 3번째 미스 계기)**. all_pass 가
  아닌 ⏳관문임박 표시이므로 미너비니 -25% 원칙은 본선(all_pass)에 유지된다.
  미달 사유는 `gate_near_reasons`(예: `"⑤ 50일선 -2.3%"`)로 산출돼 형제 검출기·
  매수추천까지 그대로 전파된다 — 페이지 ⏳관문임박 배지 옆(종목코드 줄)에 표시.
  IPO 트랙·자동매매 봇·보유 점검 피벗엔 미적용
  (봇 모집단은 관문 통과분 유지 — autobuy/watchlist.py 가 gate_near 제외).

## 다음 단계 (SEPA 파이프라인)

이 스킬(SEPA 1단계·관문) 통과 종목 = `sepa-trend-candidates.json` 은
**세 형제 패턴 검출 스킬의 공통 입력**이다(서로 독립, 순서 무관·병렬 가능):

- find-vcp        — 변동성 수축(VCP)             → sepa-vcp-candidates.json
- find-power-play — 파워 플레이(High Tight Flag)  → sepa-power-play-candidates.json
- find-3c         — 컵 완성 치트(Cup-Completion Cheat) → sepa-3c-candidates.json

트렌드 템플레이트는 **"추세가 살아있는 종목"** 만 남기는 관문이고, 실제 매수
시점은 이 패턴 분석에서 좁힌다.

> **find-*-history 는 정기 파이프라인 단계가 아니다.** 패턴 알고리즘을 과거
> 데이터로 회고·검증해 검출 로직을 더 견고히 다듬고 싶을 때만 필요에 따라
> 돌리는 도구다(매 실행마다 X).

## 안 하는 것

- C 점수·코드33 산출 — 그건 기존 `trend-template` 스킬(풀 파이프라인) 영역.
- 공유 `trend-template-candidates.json` 갱신 — 항상 `--out` 으로 분리.
- 자동 git commit/push — SEPA 단일 단계라 배포는 부모 `sepa` 스킬/사용자 판단.
- 자동 매매 신호 — 추세 관문일 뿐, 진입 결정은 다음 단계.

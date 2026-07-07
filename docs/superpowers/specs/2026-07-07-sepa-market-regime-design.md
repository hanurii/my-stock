# /stocks/sepa 시장 국면 차트 설계

날짜: 2026-07-07
상태: 설계 확정(사용자 승인) — 스펙 리뷰 대기
기준 브랜치: `feat/sepa-market-regime` (origin/master 451d6ba)

## 목적

봇·리포트가 쓰는 **등가중 지수(breadth)의 20일선 국면**을 사용자가 눈으로 확인할 수 있게 `/stocks/sepa` 페이지 최상단에 차트로 보여준다. "지금 상승추세(매매 ON)인지 하락추세(OFF)인지"를 한눈에. 이 지수는 공개 지수가 아니라 우리 캐시로 계산한 자작 지표라 볼 곳이 없어서 페이지에 만든다. [[sepa-nextday-breakout-findings]]

## 범위

- 등가중 지수 라인 + 20일 이동평균 라인 + **하락구간(지수<20MA) 빨강 음영** + 현재 상태 배지.
- 기간: 최근 약 12개월(캐시 범위 내).
- 범위 밖: 코스피/코스닥 실제 지수, 국면 완화 로직 변경, /sepa 파이프라인 자동 편입(추후).

## 사용자 확정 결정

- 위치: 페이지 **최상단 "시장 국면" 섹션**.
- 표시: 두 라인 + 상태 배지 **+ 하락구간 빨강 음영**.
- 기간: 최근 12개월.
- 국면 정의: **등가중 지수 > 20일 이동평균 = 상승추세**(봇·리포트와 동일 잣대).

## 구성 (3파일)

### ① 데이터 스크립트 — `scripts/build_market_regime.py` (신규)

- 캐시(`.cache/ohlcv/series`)로 등가중 지수 구성(전 종목 일평균 수익률 누적) + 20일 이동평균 + 국면(위/아래).
  등가중 구성 로직은 `autobuy.watchlist.build_ew_index` 재사용(전 종목 대상).
- 정규화: 첫 표시일 = 100 기준으로 재스케일(보기 편하게). 20MA·음영 판정은 스케일 무관.
- 출력 `public/data/market-regime.json`:
  ```json
  {"generated_at": "YYYY-MM-DD HH:MM",
   "current": {"date": "2026-07-07", "index": 95.2, "ma20": 98.4, "uptrend": false},
   "series": [{"date": "2025-07-08", "index": 100.0, "ma20": null, "up": null}, ...]}
  ```
  - `series`: 최근 ~250거래일(12개월). ma20 은 20일 미만이면 null. `up` = index>ma20 (ma20 null이면 null).
- 실행: `python -X utf8 scripts/build_market_regime.py`. 정션 금지 — 캐시는 주 작업트리 절대경로 참조.

### ② 차트 컴포넌트 — `src/app/stocks/sepa/MarketRegimeChart.tsx` (신규, "use client")

- 기존 `src/components/MiniChart.tsx` 의 recharts 다크테마 패턴 재사용(색·축 스타일).
- recharts `ComposedChart`(또는 LineChart): **등가중 지수 라인**(예 #95d3ba) + **20일선 라인**(예 #e0a458 점선).
- **하락구간 음영**: `series` 에서 `up===false` 인 연속 구간을 계산해 각 구간마다 `<ReferenceArea x1={시작날짜} x2={끝날짜} fill="빨강" fillOpacity={0.08} />`.
- 상단 **현재 상태 배지**: `current.uptrend` → 🟢 "상승추세 (매매 ON)" / 🔴 "하락추세 (매매 OFF)" + 현재 지수·20MA 값·기준일.
- props: `{ data: MarketRegime }`. 데이터 없거나 series<2 면 안내문("데이터 없음 — build_market_regime.py 실행").
- 음영 구간 계산은 순수 헬퍼 `downtrendSegments(series) -> [{x1,x2}]` 로 분리해 vitest.

### ③ 페이지 반영 — `src/app/stocks/sepa/page.tsx` (수정)

- 기존 `readJson<T>` 헬퍼로 `readJson<MarketRegime>("market-regime.json")`(없으면 null 허용 — 기존 exclusion 패턴처럼 try/catch).
- 페이지 최상단(첫 `<PatternSection>` 앞)에 `<section>` "시장 국면" + `<MarketRegimeChart data={regime} />`. regime null 이면 섹션 생략.

## 데이터 타입

```ts
type MarketRegime = {
  generated_at: string;
  current: { date: string; index: number; ma20: number | null; uptrend: boolean | null };
  series: { date: string; index: number; ma20: number | null; up: boolean | null }[];
};
```
`src/app/stocks/sepa/marketRegime.ts` 에 타입 + `downtrendSegments(series)` 순수 헬퍼.

## 테스트

- `downtrendSegments` 순수 헬퍼 vitest: 연속 하락구간 묶기(단일·복수·경계·전부상승·전부하락).
- 데이터 스크립트: 스모크(실행 → market-regime.json 생성, current.uptrend 가 최근 하락추세와 일치=false 확인).
- 페이지: `next build` 통과(서버 컴포넌트 + 클라이언트 차트 타입·SSR 무결).

## 데이터 흐름

`build_market_regime.py`(캐시 최신 후 수동) → `public/data/market-regime.json` → 빌드 타임 `page.tsx` fs.readFile → `<MarketRegimeChart>` 렌더. (SSG라 데이터 갱신은 재빌드=커밋 push 로 반영.)

## 배포

프로덕션(origin/master 자동배포)에 병합돼야 페이지에 뜬다. master 기준 브랜치에서 작업. [[make-hero-branch-vs-prod]]

## 한계

- 등가중 지수는 우리 캐시 기반 자작(현재 상장종목=생존편향). 실제 코스피/코스닥 아님(대형주 강세 국면과 갈릴 수 있음 — 페이지에 각주로 명시).
- SSG라 실시간 아님(마지막 빌드=캐시 시점 기준). /sepa 파이프라인 편입 전엔 수동 갱신.

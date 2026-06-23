---
name: make-hero
description: >
  매일 한 마디로 /stocks/hero-profile 페이지를 갱신하는 통합 자동화 스킬.
  두 레인으로 동작: (가격 레인=기본) 가격에서 파생되는 데이터만 빠르게 갱신하고
  펀더 캐시는 일절 안 건드림, (펀더 레인) DART 새 공시·주간 풀스캔 때만 펀더 재수집.
  마지막에 자동 git commit + push (Vercel 재배포 트리거). 사용자가 "/make-hero",
  "오늘 hero 갱신", "랭킹 갱신해줘", "가격만 갱신" 등을 요청할 때 사용.
---

# /make-hero — 매일 Hero Profile 갱신

매일 한 마디로 ranking 페이지·hero-profile 페이지가 최신 데이터로 새로 그려지도록
끝까지 자동화한다. **A·N·S·I 는 일상 갱신 안 함** (별도 트리거).

## 두 가지 레인 — 먼저 어느 레인인지 정한다

가격 갱신과 펀더(DART/Naver) 수집을 **분리**한다. 매일 가격만 보려고 돌릴 때
펀더 캐시를 통째로 날리고 전체 재수집하던 문제를 막기 위함.

| 레인 | 언제 | 무엇을 | 캐시 |
|------|------|--------|------|
| **가격 레인** (기본/매일) | "/make-hero", "오늘 hero 갱신", "랭킹 갱신", "가격만/빠르게" | OHLCV 행렬 + 트렌드1 + L + KIS 현재가 | `canslim_stocks`·DART·Naver **무접촉** (무효화·풀스캔 없음) |
| **펀더 레인** (명시 시) | "펀더 갱신", "공시 반영", "주간 풀스캔", 사업보고서 마감기 | 위 + C 메인 풀스캔 + 트렌드 C·code33 | DART 새 공시·신규상장 종목만 증분 무효화 |

- **기본은 가격 레인.** 사용자가 펀더를 명시하지 않으면 가격 레인(아래 "가격 레인 절차")만 돌린다.
- 펀더 레인은 사용자가 펀더/공시/풀스캔을 명시했을 때만 "펀더 레인 절차 (7단계)" 전체를 돈다.
- 두 레인 모두 **불변 원칙**과 **자동 commit 안전장치**(아래)를 따른다.

## 가격 레인 절차 (기본 — 빠른 일일 갱신)

```
pwsh -NoProfile -File scripts/refresh_price_only.ps1
```
- 내부 4단계(전부 캐시 삭제 0건): ①OHLCV 행렬 증분 +FDR 당일 보충 → ②트렌드 템플레이트 1단계 → ③L 점수(트렌드 RS lookup) → ④KIS 통합시세로 C 게이트 종목 현재가·신고가대비 정확화.
- KIS 키 없거나 장중이면 `-SkipKis` 로 ④ 생략(KRX 종가 유지).
- **펀더 풀스캔·DART 무효화를 호출하지 않음** → `canslim_stocks`/`dart_*`/`naver_annual` 캐시 무접촉. C 점수 필드는 직전 펀더 레인 값 그대로 유지되고 가격 필드만 갱신된다.
- 끝나면 **아래 7단계(자동 git commit + push)** 로 산출 4파일을 커밋. 커밋 메시지: `chore: 가격 정보 갱신 YYYY-MM-DD (FDR/KIS)`.
- 소요: ~5-10분 (대부분 FDR 보충 + 트렌드 수집).

아래 **불변 원칙·사전 조건**은 두 레인 공통이다.

## 불변 원칙

- **순서 엄수**: 1 → 2 → 3 → 4 → 5 → 6 → 7. 각 단계 실패 시 즉시 abort + 어디서 실패했는지 보고.
- **컷오프 보호**: 스크리너 컷오프(시총·거래대금) 절대 추가 금지 ([screener-no-cutoff] 메모리).
- **자동 commit 안전장치**: 시작 시 `git status` 확인 → 사용자 미커밋 변경 있으면 commit 보류 + 사용자에게 어떤 변경인지 보고. 작업 결과 파일만 명시적으로 staging.
- **환각 금지**: 결과 종목 수·점수는 콘솔 출력 그대로 보고. 추측·요약 금지.

## 사전 조건

- `.env` 의 `DART_API_KEY`(공시·펀더) + `DATA_GO_KR_KEY`(공공데이터 일봉, 행렬 필수) 설정
- `.env` 의 `KIS_APP_KEY`·`KIS_APP_SECRET` (외인소진율 + 6.5단계 통합시세; 없으면 외인 갱신·6.5 자동 skip)
- 어제 풀스캔 결과 `public/data/can-slim-candidates.json` 존재 (없으면 1단계가 신규 상장 = 전 종목으로 폴백 — 시간 늘어남)
- OHLCV 행렬 최초 1회 백필 필요: `pwsh -File scripts/canslim_parallel.ps1` 첫 실행이 ~400영업일을 채움(~5분). 이후엔 증분(영업일 1개)만.

## 펀더 레인 절차 (7단계) — 펀더/공시/주간 풀스캔 명시 시에만

> 가격 레인(기본)은 위 "가격 레인 절차"로 끝. 아래는 사용자가 펀더/공시/풀스캔을
> 명시했을 때만 돈다. 3·4·6.5·7단계는 가격 레인과 동일한 가격 산출을 포함한다.

### 1단계 — DART 새 공시 + 신규 상장 종목 식별 (증분)
```
python scripts/canslim_incremental_check.py
```
- DART list.json 으로 어제~오늘 정기보고서·잠정실적 공시 종목 추출
- 현재 universe ∖ 이전 candidates = 신규 상장 종목
- 합집합의 `.cache/canslim_stocks/<code>.json` 만 삭제
- **안전장치**: ①이전 `can-slim-candidates.json` 없으면 신규상장 무효화를 건너뜀(전체 캐시 wipe 방지, DART 공시 무효화만). ②무효화 대상이 universe 의 30%(또는 500종목)를 넘으면 삭제 안 하고 exit 2 로 중단 — 이때는 DART 조회/매핑 이상이므로 사용자에게 보고.
- **체크**: 콘솔의 "갱신 대상 K종목" 메시지 — 평일 보통 50~150개, 사업보고서 마감 시기엔 200+
- 소요: 5-15초

### 2단계 — C 메인 풀스캔 (배치 OHLCV 행렬 + 10워커 병렬)
```
pwsh -NoProfile -File scripts/canslim_parallel.ps1
```
- 내부 4단계 자동 실행:
  1. **OHLCV 행렬 + 외인 갱신** (`ohlcv_matrix.py --update --foreign`, 단일 프로세스)
     - 가격은 공공데이터포털(pdata) basDt 1회 호출로 전 종목 일봉을 받아 누적 행렬에 추가.
       종목별 Naver 일봉 루프 제거 → 매일 최신 1영업일만 fetch. **비수정주가라 일별 등락률로
       수정주가 복원**(액면분할 종목 가짜 추세 방지).
     - 외인소진율은 KIS `inquire-price`(hts_frgn_ehrt)로 미보유/만료(7일) 종목만 갱신.
  2. **연간 재무 prewarm** (`screen_canslim.py --prewarm-annual`, 단일 프로세스)
     - 연간 EPS/ROE(A기준)는 Naver(분할조정값)가 정확해 유지하되, 워커 병렬 시 Naver
       동시 호출이 스로틀링되므로 **워커 전에 단일 프로세스로 45일 캐시를 미리 데움**.
       정상일엔 캐시 hit 으로 수초, 최초/45일마다만 ~7분.
  3. **10워커 병렬 Pass 1** (`canslim_worker.ps1`, universe 슬라이스 분할, 캐시 TTL 72h)
     - 가격=행렬, 연간=prewarm 캐시, **분기 EPS/매출(C기준)=DART**(분기 YoY 는 Naver 와 일치
       검증됨). 캐시 미스 종목도 워커 안에선 Naver 호출 0 → 병렬 차단 위험 없음.
     - DART rate limit 은 워커당 자동 분할(800/N).
  4. **reduce 병합 + 저장** (`screen_canslim.py --reduce` → `can-slim-candidates.json`)
- 워커/창 수 조정: `-Workers 8`, 외인 갱신 생략: `-SkipForeign`.
- KIS 키 없으면 외인 갱신 자동 skip(기존 캐시 사용), DATA_GO_KR_KEY 없으면 행렬 갱신 실패 → abort.
- 소요: 정상일 ~3-5분 (행렬·연간·외인 캐시 hit + 병렬). 최초 1회만 행렬 백필(~5분)+연간 prewarm(~7분).

### 3단계 — 트렌드 1단계 (전 종목 일봉 = 배치 행렬)
```
python scripts/screen_trend_template.py --save
```
- 일봉은 2단계에서 갱신된 OHLCV 행렬을 읽음(종목별 Naver 호출 제거, Yahoo 폴백 유지).
- `trend-template-candidates.json` 갱신
- 소요: ~30초 (행렬 조회 + 병렬 12워커)

### 4단계 — L 점수 갱신 (트렌드 RS 차용)
```
python scripts/fetch_l_rs.py
```
- 3단계 결과의 RS 를 lookup만, 자체 호출 없음
- `can-slim-l-candidates.json` 갱신
- 소요: 즉시 (1초 미만)

### 5단계 — 트렌드 2단계 (C 점수)
```
python scripts/screen_trend_template_c_score.py
```
- 트렌드 통과 종목(~190) C 점수 — DART 캐시 hit
- `trend-template-c-scored.json` 갱신
- 소요: ~3분

### 6단계 — 트렌드 3단계 (코드 33)
```
python scripts/screen_trend_template_code33.py
```
- EPS·매출·순이익률 3분기 가속 판별
- `trend-template-code33.json` + 콘솔 표
- 소요: ~1분

### 6.5단계 — KIS 통합시세로 신고가·현재가 정확화
```
python scripts/refine_with_kis_nxt.py
```
- C 게이트 통과 ~210종목의 `current_price` + `pct_from_52w_high` 를 KIS 통합시세(KRX 정규장 + NXT 애프터) 로 갱신
- `can-slim-candidates.json` / `trend-template-candidates.json` / `trend-template-c-scored.json` 세 파일 동시 갱신
- KIS 키 (`.env` 의 `KIS_APP_KEY`·`KIS_APP_SECRET`) 없으면 자동 skip → KRX 종가 그대로 두고 메시지 출력
- 소요: ~30-60초 (병렬 4워커 + 글로벌 throttle, KIS rate limit 초당 ~8회 안전 마진)

### 7단계 — 자동 git commit + push
```
git status --short        # 사용자 미커밋 변경 있나 확인
git add public/data/can-slim-candidates.json public/data/can-slim-l-candidates.json \
        public/data/trend-template-candidates.json public/data/trend-template-c-scored.json \
        public/data/trend-template-code33.json
git commit -m "chore: daily hero refresh YYYY-MM-DD"
git push
```
- 6.5단계가 돌았으면 `can-slim-candidates.json` 의 `_kis_refined_at` 필드가 갱신돼 있음 — 커밋 메시지에 "(NXT 통합시세 반영)" 같이 명시해도 좋음
- 시작 시 `git status` 결과에 다른 변경이 있으면 **commit 보류 + 사용자에게 어떤 파일인지 보고**
- 데이터 파일만 명시적 staging (코드 변경 자동 포함 X)
- Vercel 이 자동 배포 트리거

총 소요: 평일 평균 **5-8분** (행렬 캐시 hit + 2단계 병렬). 행렬 최초 백필 날만 +5분.

## 결과 확인 (스킬 끝나면)

- `/stocks/canslim/ranking` 의 generated_at 이 오늘로 갱신
- `/stocks/hero-profile` 종목 수 변화
- 콘솔 마지막에 코드 33 통과 종목 표 표시

## 안전 / 검증

- **각 단계 실패 시 abort**: 다음 단계 진행 안 함. 단 2단계(C 메인) 실패 시 트렌드 파이프라인(3~6)은 그대로 진행 가능 — 트렌드는 메인 C 결과 의존 없음.
- **DART API 한도**: 분당 1000. 1단계 list.json ≤ 10회. 2단계 워커는 워커당 800/N 으로 자동 분할(합산 ≤ 800).
- **`stock_cache` TTL 72h**: 워커가 72h 캐시를 쓰므로 1단계 명시 무효화 종목 + 72h 만료분만 재fetch.
- **워커 내 Naver 호출 0**: 가격=행렬(공공데이터), 외인=KIS, 연간=prewarm 캐시, 분기=DART. 워커 병렬 구간에서 Naver 종목별 호출이 없어 차단 위험 제거. (연간만 Naver 인 이유: 액면분할 조정 EPS 정확도 — 단일 프로세스 prewarm 으로 동시성 회피.)
- **OHLCV 수정주가**: pdata 는 비수정주가라 일별 등락률(fltRt) 역체이닝으로 복원. pykrx 는 현재 KRX 엔드포인트와 불호환이라 미사용.
- **자동 commit 거부 케이스**: 사용자 미커밋 변경 / 충돌 / push 거부 (origin 새 커밋) → 사용자 보고 후 멈춤.

## 안 하는 것

- A·N·S·I 매일 갱신 (사업보고서 마감 시기 등 특정 시점만 명시 호출)
- GitHub Actions 등 백그라운드 스케줄러 (말 한 마디 트리거 방식만)
- 메인 candidates.json 의 부분 머지 (screen_canslim.py 가 풀스캔 후 통째 재작성하므로 머지 불필요)

---
name: update-data
description: >
  find-trend-template(및 가격 기반 스크리너)이 읽는 OHLCV 시세 행렬 캐시를 최신
  영업일까지 증분 갱신하는 선행 스킬. 기존 캐시를 절대 삭제하지 않고(append 성격),
  새 영업일만 공공데이터(pdata)에서 받고 당일 미공개분은 FDR로 보충한다. DART/Naver/
  canslim_stocks 펀더 캐시는 일절 건드리지 않는다. 사용자가 "/update-data",
  "캐시 최신화", "시세 데이터 갱신", "find-trend-template 전에 데이터 업데이트"
  등을 요청하거나, 최신 데이터로 스크리너를 돌리기 직전에 사용.
---

# update-data — OHLCV 시세 캐시 최신화

`find-trend-template` 같은 가격 기반 스크리너가 읽는 **OHLCV 시세 행렬**
(`.cache/ohlcv/series/<코드>.json`)을 최신 영업일까지 끌어올리는 **얇은 선행 스킬**.
스크리너 돌리기 직전에 한 번 실행하면 항상 최신 데이터 기준으로 선별된다.

## 불변 원칙 — 캐시 삭제 금지

- **기존 캐시를 지우지 않는다.** 이 명령은 디렉토리 wipe·종목 파일 삭제를 하지
  않는다. 새 영업일을 종목 시계열에 **추가(append)** 하고, 최신 400영업일
  롤링 윈도우로 다시 기록할 뿐이다.
- **펀더 캐시 무접촉**: DART/Naver/`canslim_stocks`/연간 재무 캐시는 이 명령의
  호출 경로에 **없다**. 구조적으로 못 건드린다.
- pdata 일자 캐시(`.cache/pdata/price_YYYYMMDD.json`)는 **새 날짜만 추가**
  fetch, 기존 날짜 파일은 보존.

## 사전 조건

- `.env` 의 `DATA_GO_KR_KEY` (공공데이터포털 일봉 — 필수).
- FinanceDataReader(FDR)는 선택. 없으면 당일 보충(`--fill-fdr`)만 자동 skip,
  pdata 분까지는 정상 갱신.

## 실행 절차 (명령 1줄)

```
python -X utf8 scripts/canslim_lib/ohlcv_matrix.py --update --window 400 --fill-fdr
```

- `-X utf8` : **필수.** Windows cp949 콘솔에서 이모지 로그 출력이 크래시하므로
  UTF-8 모드 강제. 빠뜨리면 `UnicodeEncodeError`로 즉시 실패한다.
- `--update` : pdata에서 **새 영업일만** fetch(보통 1일)해 종목별 시계열에 추가.
  이미 받은 날은 캐시 hit.
- `--fill-fdr` : pdata가 아직 못 준 당일/전일을 FDR(KRX 기반)로 보충. FDR
  close는 pdata 복원 close와 일치 검증됨.
  - **기준가 변경 자동 환산**: 액면분할·주식병합·감자가 나면 FDR은 과거를 새
    기준으로 바꿔 주지만 우리 캐시는 옛 기준에 머문다. 보충 시 겹치는 하루의
    종가를 대조해(정상이면 정확히 1.0) 어긋나면 과거 전체를 그 배수로 환산한
    뒤 붙인다. 환산이 일어나면 `🔧 기준가 변경 환산 N종목` 로그가 찍힌다.
    안 하면 "옛 기준 과거 + 새 기준 하루"가 되어 가짜 급등이 생기고
    200일선·52주 신고가·RS가 통째로 틀어진다(2026-07-31 금호전기 +360% 사고).
- `--window 400` : 최신 400영업일 유지(트렌드 템플레이트의 200일선·52주에 충분).
- 소요: ~10초~1분 (보통 새 영업일 1일치만 네트워크, 나머지 캐시 hit).

### 사후 복구 (이미 깨진 시계열)

```
python -X utf8 scripts/canslim_lib/ohlcv_matrix.py --repair-rebase          # 진단만
python -X utf8 scripts/canslim_lib/ohlcv_matrix.py --repair-rebase --apply  # 적용
```

마지막 날 등락이 가격제한폭(±30%)을 넘는 종목을 후보로 잡고, FDR 전일 종가와
대조해 **진짜 기준가 변경일 때만** 과거를 환산한다. 장기 정지 후 거래재개는
실제로 제한폭을 넘길 수 있어(예: -97% 붕괴) 후보라고 다 고치지 않는다.
기본은 진단만 — `--apply` 를 붙여야 파일을 건드린다.

## 결과 확인

- 콘솔의 `✅ ohlcv_matrix: N종목 시계열 저장 (S초)` — N이 전 종목 수(~2,600)인지.
- FDR 보충이 돌면 `📈 FDR 최근일 보충 ... appended_days` 로 추가된 영업일 표시.
- 갱신 후 대표 종목 마지막 날짜가 최신 영업일인지 의심되면
  `python scripts/canslim_lib/ohlcv_matrix.py` 없이 직접 확인하기보다
  바로 `find-trend-template` 결과의 `asof`로 확인.

## 다음 단계

갱신이 끝나면 곧바로 `find-trend-template`(SEPA 1단계)를 돌리면 최신 시세 기준으로
추세 통과 종목이 추려진다.

## 안 하는 것

- 외인소진율·DART·연간 재무 갱신 (트렌드 템플레이트 불필요. 필요 시 make-hero
  펀더 레인 별도).
- 산출 파일(`*-candidates.json`) 생성/갱신 — 그건 스크리너 스킬 몫.
- 자동 git commit — 캐시 갱신일 뿐 커밋할 산출물 없음.
- 캐시 삭제·무효화 — 절대 안 함(위 불변 원칙).

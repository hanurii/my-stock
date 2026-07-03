---
name: sepa
description: >
  SEPA 파이프라인 오케스트레이터(부모 스킬). update-data → find-trend-template
  → {find-vcp + find-power-play 동시} 를 정기 순서대로 전부 실행하고, 통합 요약
  후 결과 파일 3개(sepa-*-candidates.json)만 자동 commit+push 한다. 직접 계산은
  없음 — 하위 스킬을 Skill 도구로 호출하는 지휘 문서. 사용자가 "/sepa",
  "sepa 돌려줘", "세파 전체 실행", "SEPA 파이프라인", "오늘 세파 후보 갱신"
  등을 요청할 때 사용.
---

# sepa — SEPA 파이프라인 오케스트레이터

SEPA 종목 발굴 전체 파이프라인을 한 번에 돌리는 **부모 스킬**. 항상 처음부터
끝까지 전체 실행한다(중간 시작 없음 — 특정 단계만 필요하면 하위 스킬을 직접
호출).

## 불변 원칙

- **명령어 복사 금지**: 실행 명령의 원본은 각 하위 스킬 문서다. 이 스킬은
  하위 스킬을 **Skill 도구로 호출**해 그 지시를 따른다. 여기에 python 명령을
  베껴 적지 않는다(하위 스킬이 바뀌면 여기가 낡는다).
- **환각 금지**: 요약의 모든 숫자는 각 단계 콘솔 출력 그대로. 추측 금지.
- **실패 시 커밋 금지**: 어느 단계든 실패하면 즉시 중단하고 오류를 그대로
  보고한다. 반쯤 갱신된 결과가 배포되면 안 된다.

## 절차 (순서 고정)

1. **`update-data` 스킬 호출** — OHLCV 시세 캐시를 최신 영업일까지 갱신.
2. **`find-trend-template` 스킬 호출** — SEPA 1단계 추세 관문.
   - **통과 0종목이면 여기서 중단**하고 보고(약세장이면 정상). 3단계 이후·
     커밋 진행 안 함.
3. **`find-vcp` + `find-power-play` 스킬 호출 — 동시 실행.**
   - 두 스킬의 지시를 모두 로드한 뒤, 각 스크립트를 **백그라운드로 동시에**
     실행한다(Bash `run_in_background` 두 개, 둘 다 종료 알림 후 결과 취합).
     둘 다 `sepa-trend-candidates.json`을 읽기만 하고 서로 다른 파일에
     쓰므로 병렬 안전.
   - **한쪽만 실패해도 커밋 없이 중단·보고** — 두 결과 파일의 기준 시점이
     어긋난 채 배포되는 것을 막는다.
4. **통합 요약 보고** — 표 하나로:
   - 추세 통과 N종목 (market_status 포함)
   - VCP: breakout / actionable 종목과 피벗
   - 파워플레이: entry_ready 종목과 피벗
5. **자동 commit + push** — 커밋 대상은 아래 **3개 파일만**. 다른 변경 파일은
   절대 섞지 않는다(`git add` 에 경로 명시).
   - `public/data/sepa-trend-candidates.json`
   - `public/data/sepa-vcp-candidates.json`
   - `public/data/sepa-power-play-candidates.json`
   - 커밋 메시지: `chore(sepa): 파이프라인 결과 갱신 (YYYY-MM-DD)` —
     날짜는 실행일(오늘).
   - 현재 브랜치로 push. **브랜치가 master가 아니면 경고 한 줄**:
     "프로덕션(master 자동 배포)에는 반영되지 않음 — master 반영은 별도
     cherry-pick/머지 필요."

## 안 하는 것

- `find-vcp-history` / `find-power-play-history` — 정기 단계 아님(온디맨드
  검증 도구). 사용자가 따로 요청할 때만.
- 하위 스킬 옵션 튜닝(`--rs-min`, `--ticker`, `--universe all` 등) — 옵션이
  필요한 실행은 해당 하위 스킬을 직접 호출.
- 결과 파일 외 커밋(페이지 코드·캐시·스크립트 등 무접촉).
- `find-3c` — 스킬이 아직 없음. 스킬이 생기면 3단계 형제로 추가할 것.

# sepa 오케스트레이터 스킬 설계 (2026-07-03)

## 목적

`/sepa` 한 마디로 SEPA 종목 발굴 파이프라인 전체(데이터 갱신 → 추세 관문 →
패턴 탐지 → 요약 → 배포 커밋)를 정기 순서대로 실행하는 **부모 오케스트레이터
스킬**. `find-trend-template` 스킬 문서가 이미 "자동 commit은 부모 `sepa`
스킬/사용자 판단"이라고 예약해 둔 자리를 채운다.

## 형태

- 위치: `.claude/skills/sepa/SKILL.md` 파일 하나. **새 코드·스크립트 없음.**
- 방식: 실행 명령어를 복사하지 않고 **하위 스킬을 Skill 도구로 호출**해 그
  스킬의 지시를 따른다. 하위 스킬이 바뀌어도 sepa는 수정 불필요
  ([doc-logic-sync] 준수 — 명령 원본은 각 하위 스킬 한 곳뿐).

## 실행 순서 (항상 전체 실행, 중간 시작 옵션 없음 — 사용자 확정)

1. **update-data** — OHLCV 시세 캐시를 최신 영업일까지 증분 갱신.
2. **find-trend-template** — SEPA 1단계 추세 관문. **통과 0종목이면 여기서
   중단하고 보고**(약세장이면 정상). 이후 단계·커밋 진행 안 함.
3. **find-vcp + find-power-play + find-3c 동시 실행** — 모두
   `sepa-trend-candidates.json`을 읽기만 하고 서로 다른 파일에 쓰므로 병렬
   안전. 스크립트들을 백그라운드로 동시에 돌려 시간 절약. find-3c 스킬이
   현재 체크아웃에 없으면(구 브랜치) 건너뛰고 요약에 명시(실패 아님).
4. **통합 요약 보고** — 추세 통과 N종목 → VCP 살 자리(entry: breakout/
   actionable) M종목, 파워플레이 살 자리 K종목. 숫자는 콘솔 출력 그대로
   (환각 금지).
5. **자동 커밋 + 푸시 (사용자 확정: 항상)** — 커밋 대상은 결과 파일만:
   - `public/data/sepa-trend-candidates.json`
   - `public/data/sepa-vcp-candidates.json`
   - `public/data/sepa-power-play-candidates.json`
   - `public/data/sepa-3c-candidates.json` (find-3c 실행 시)
   - 다른 변경 파일은 절대 섞지 않는다([match-scope-to-target-page] 준수).
   - 현재 브랜치로 push. **브랜치가 master가 아니면 "프로덕션(master 자동
     배포)에는 반영되지 않음" 경고 한 줄 출력**([make-hero-branch-vs-prod]
     교훈).

## 실패 처리

- 어느 단계든 실패하면 **즉시 중단**, 콘솔 오류를 그대로 보고, **커밋하지
  않는다.** 반쯤 갱신된 결과가 배포되는 것을 방지.
- 3단계에서 한쪽 패턴 스크립트만 실패한 경우도 커밋 없이 중단·보고(두 결과
  파일의 기준 시점이 어긋난 채 배포되는 것 방지).

## 범위 제외

- `find-*-history`(vcp/power-play/3c) · `vcp-audit` — 정기 단계가 아닌
  온디맨드 검증 도구([sepa-pipeline-order]).
- (참고) find-3c는 master에 이미 병합돼 있어 3단계 형제로 포함. 이 feature
  브랜치에는 스킬 파일이 없어 merge 전까지는 건너뛰기로 동작.
- 하위 스킬 옵션 튜닝(`--rs-min`, `--ticker` 등) — 필요하면 하위 스킬을 직접
  호출.

## 트리거 예시

"/sepa", "sepa 돌려줘", "세파 전체 실행", "SEPA 파이프라인 돌려줘",
"오늘 세파 후보 갱신".

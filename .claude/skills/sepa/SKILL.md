---
name: sepa
description: >
  SEPA 파이프라인 오케스트레이터(부모 스킬). update-data → find-trend-template
  → {find-vcp·find-power-play·find-3c 형제 동시} 를 정기 순서대로 전부 실행하고,
  통합 요약 후 결과 파일(sepa-*-candidates.json)만 자동 commit+push 한다. 직접
  계산은 없음 — 하위 스킬을 Skill 도구로 호출하는 지휘 문서. 사용자가 "/sepa",
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
3. **패턴 검출기 동시 실행(백그라운드 병렬) — 네 갈래:**
   `find-vcp` · `find-power-play`(트렌드) · **`find-power-play` 전수** · `find-3c`.
   - 형제 스킬들의 지시를 모두 로드한 뒤, 각 스크립트를 **백그라운드로
     동시에** 실행한다(Bash `run_in_background`, 전부 종료 후 결과 취합).
     모두 `sepa-trend-candidates.json`/OHLCV 캐시를 읽기만 하고 서로 다른
     파일에 쓰므로 병렬 안전.
   - **전수 파워플레이**: `find-power-play` 스킬을 그 스킬 문서의
     `--universe all --rs-min 80` 옵션으로 **한 번 더** 실행 →
     `sepa-power-play-all-candidates.json`. `/stocks/sepa` 페이지의 '전수'
     섹션이 이 파일을 읽으므로 **정규 산출**이다(트렌드용
     `sepa-power-play-candidates.json`과 별개 파일).
   - `find-3c` 스킬이 현재 체크아웃에 없으면(구 브랜치) **건너뛰고 요약에
     그 사실을 명시**한다 — 실패로 취급하지 않는다.
   - **하나라도 실패하면 커밋 없이 중단·보고** — 결과 파일들의 기준 시점이
     어긋난 채 배포되는 것을 막는다.
4. **`check-holdings` 스킬 호출** — 보유 종목 매도규칙 점검. 형제 패턴 결과
   파일(피벗)을 읽으므로 반드시 형제 실행 뒤에 돈다.
   - `sepa-holdings.json`이 없거나 비면 실패가 아니라 **건너뜀**(빈 결과로
     정상 종료 — find-3c 부재 처리와 동일 정신).
5. **티어 추이 스냅샷 갱신 — `python scripts/snapshot_sepa.py`.** (오케스트레이터
   전용 마무리 스텝 — 하위 스킬 아님. 형제 패턴 파일을 한데 모아
   `sepa-tier-history.json`(최근 3일)에 그 asof 로 도장 찍는 파이프라인 접착제라
   부모가 소유한다.)
   - **반드시 3단계(형제 패턴)가 전부 끝난 뒤 실행** → 모든 후보 파일이
     갱신 완료된 상태라 스냅샷의 최신 날짜가 본문 상태와 **항상 일치**한다
     ('추이' 컬럼 마지막 점이 본문 티어와 어긋나지 않음: 본문 🔴 돌파면
     추이도 …🔴). 형제 안에서 병렬로 돌리지 않는 이유이기도 하다(경합 방지).
   - 후보 파일의 `status`를 **그대로 복사**(재분류 없음). find-3c 가 이번에
     건너뛰어졌어도 이 단계는 **항상 실행**한다 — 그래야 vcp·power-play 추이가
     낡지 않는다.
6. **국면 지수 갱신 — `python scripts/build_market_regime.py`.** (오케스트레이터
   전용 스텝 — 1단계에서 갱신된 캐시로 등가중 시장지수·20일선·국면을 계산해
   `public/data/market-regime.json` 을 생성한다. `/stocks/sepa` 최상단 국면차트가 읽는다.)
   - 후보 단계와 독립(캐시만 필요) — 1단계 이후면 가능하나 스냅샷과 함께 마무리로 돌린다.
   - **비차단**: 실패해도 파이프라인 실패로 보지 않고 오류 한 줄만 보고 후 넘어간다
     (그 경우 아래 커밋에서 `market-regime.json` 은 빼고 나머지만 커밋).
7. **통합 요약 보고** — 표 하나로:
   - 추세 통과 N종목 (market_status 포함)
   - VCP: breakout / actionable 종목과 피벗
   - 파워플레이(트렌드): entry_ready 종목과 피벗
   - 파워플레이(전수): entry_ready 종목과 피벗 (입력 종목 수 포함)
   - 3C: 진입 가능 종목과 피벗 (실행됐을 때만)
   - 보유 점검: 🔴 손절 N · 🟠 조기매도 N · 🟢 정상보유 N (check-holdings 콘솔 그대로)
8. **자동 commit + push** — 커밋 대상은 아래 **결과 파일만**. 다른 변경
   파일은 절대 섞지 않는다(`git add` 에 경로 명시).
   - `public/data/sepa-trend-candidates.json`
   - `public/data/sepa-vcp-candidates.json`
   - `public/data/sepa-power-play-candidates.json`
   - `public/data/sepa-power-play-all-candidates.json` (전수 — 페이지 '전수' 섹션)
   - `public/data/sepa-3c-candidates.json` (find-3c가 실행됐을 때만)
   - `public/data/sepa-holdings-feedback.json`
   - `public/data/sepa-tier-history.json` (5단계 스냅샷 결과 — 빠뜨리면 추이가
     갱신돼도 배포에 안 실려 낡은 채로 보인다)
   - `public/data/market-regime.json` (6단계 국면 지수 — /stocks/sepa 국면차트.
     6단계가 실패해 갱신 안 됐으면 제외)
   - 커밋 메시지: `chore(sepa): 파이프라인 결과 갱신 (YYYY-MM-DD)` —
     날짜는 실행일(오늘).
   - 현재 브랜치로 push. **브랜치가 master가 아니면 경고 한 줄**:
     "프로덕션(master 자동 배포)에는 반영되지 않음 — master 반영은 별도
     cherry-pick/머지 필요."
   - **master가 별도 워크트리(`../my-stock-master`)면** 그 워크트리에서 이
     커밋을 `git cherry-pick` 후 push 한다(메인 워크트리에서 `git checkout
     master` 는 워크트리 충돌로 불가). 캐시·전수는 메인 워크트리에서 생성한 뒤
     커밋만 옮긴다.

9. **캐시 백업(비차단) — `python scripts/backup_cache.py`.** 파이프라인 성공·
   커밋 완료 후 **마지막에** `.cache`(1단계에서 갱신된 OHLCV 포함) zip 스냅샷을
   로컬 `C:\Users\hanul\cache-backups`(7개) + 비공개 GitHub 릴리스
   `hanurii/my-stock-cache-backup`(7개)로 이중 백업한다. /sepa 를 돌리는 날마다
   (=컴퓨터가 켜져 캐시가 막 갱신된 시점) 자동 백업되므로 이게 **주 백업 트리거**다.
   - **비차단**: 백업 실패는 파이프라인 실패로 취급하지 않는다 — 결과는 이미
     커밋·배포됐다. 실패하면 오류 한 줄만 보고하고 넘어간다(정션 삭제 사고
     이후 신설된 복구 인프라 — 있으면 좋고 없어도 파이프라인엔 무해).
   - 펀더 캐시가 아직 비어 있어도 백업은 진행. 시계열 2000개 미만이면 스크립트가
     스스로 부분캐시로 보고 중단하니 별도 판단 불필요.

## 안 하는 것

- `find-*-history`(vcp/power-play/3c) · `vcp-audit` — 정기 단계 아님
  (온디맨드 검증 도구). 사용자가 따로 요청할 때만.
- 하위 스킬 옵션 튜닝(`--ticker`, VCP `--zigzag-pct`, 3C `--max-shelf-*` 등
  임계값 실험) — 정규 산출에 불필요한 옵션 실행은 해당 하위 스킬을 직접 호출.
  **예외: 전수 파워플레이 `--universe all --rs-min 80`은 페이지 '전수' 섹션용
  정규 스텝**이라 위 절차(3단계)에 포함한다.
- 결과 파일 외 커밋(페이지 코드·캐시·스크립트 등 무접촉).

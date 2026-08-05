# 수출 주도 종목 배지 (export-leader tags) — 설계

- 날짜: 2026-08-05
- 발단: 한국 수출 무역흑자 최대치 국면. 주도 수출 품목(반도체·무선통신기기·
  유선통신기기·석유제품·선박·가전제품·철강제품)에 속한 종목이 SEPA 후보에
  들어오면 한눈에 알아보고 싶다는 요청.
- 확정 결정(사용자 답변):
  1. **범위 = 밸류체인 포함** — 완제품 수출사뿐 아니라 장비·소재·부품사도
     포함하되 `direct`(직접) / `indirect`(간접·밸류체인)로 구분 표시.
  2. **품목 리스트 = 설정파일 직접 관리** — 관세청 API 자동화 없음. 무역
     흐름이 바뀌면 사용자가(또는 사용자가 시켜서) 설정 JSON을 수정.
  3. **분류 = 자동 + 오버라이드** — KRX 업종명·주요제품(Products) 텍스트
     키워드 매칭으로 1차 자동 분류, 예외는 오버라이드(강제 포함/제외)로 교정.
  4. **표시 = SEPA 페이지 배지만** — 후보 테이블·매수 추천 리스트에 표시.
     정렬·초수익 점수·보유 점검에는 일절 관여하지 않음(점수는 백테스트로
     검증된 조합이라 미검증 요인 혼입 금지).

## 아키텍처 (독립 태깅 스텝)

`snapshot_sepa.py` 와 같은 **오케스트레이터 전용 마무리 스텝** 패턴.
검출기(형제 스킬)는 무접촉 — 후보 파일을 읽기만 하고 태그 파일 하나만 쓴다.

```
export-leading-config.json ─┐
KRX 업종·주요제품(FDR, 캐시) ─┼→ tag_export_leaders.py → sepa-export-tags.json
후보 4파일 + 매수추천 (코드 수집) ─┘                          ↑ 페이지가 코드로 조인
```

## 구성요소

### 1. 설정파일 `public/data/export-leading-config.json`
```json
{
  "asof": "2026-08-05",
  "note": "수출 무역흑자 최대치 국면 주도 품목 — 사용자 관리",
  "categories": [
    {"key": "semiconductor", "label": "반도체", "keywords": ["반도체", "웨이퍼", "전자부품", ...]},
    {"key": "petroleum", "label": "석유제품", "keywords": ["석유 정제", ...]},
    ... 7품목
  ],
  "overrides": {
    "include": {"078930": {"category": "petroleum", "tier": "indirect", "reason": "GS칼텍스 지주"}},
    "exclude": {"094840": "통신장비 KSIC이나 실제는 지문인식", "028670": "해운=선박 이용자"}
  }
}
```
- 키워드는 KRX `Sector`(업종명)·`Products`(주요제품) 텍스트에 부분 일치.
- 키워드 매칭 = `direct` 후보, 오버라이드 include 는 `tier` 명시(직/간접).
- 장비·소재사가 업종명만으로 안 잡히면 include 오버라이드로 추가(예:
  뉴파워프라즈마 → semiconductor/indirect).

### 2. 태깅 스크립트 `scripts/tag_export_leaders.py`
- 입력: 후보 4파일(sepa-trend / vcp / power-play-all / 3c) + 매수추천에 등장하는
  전 종목코드 합집합.
- KRX 업종·주요제품: FDR `StockListing('KRX-DESC')` → `.cache/krx_desc.json` 에
  캐시(7일 TTL — 업종은 거의 안 변함). 네트워크 실패 시 캐시 사용, 캐시도
  없으면 이전 태그 파일 유지 후 경고(비차단).
- 산출 `public/data/sepa-export-tags.json`:
```json
{
  "asof": "2026-08-05",
  "config_asof": "2026-08-05",
  "tags": {
    "010950": {"name": "S-Oil", "category": "petroleum", "label": "석유제품",
               "tier": "direct", "basis": "업종: 석유 정제품 제조업"}
  }
}
```
- 분류 안 되는 종목은 tags 에 없음(추측 금지). 결정론적 — 같은 입력 → 같은 출력.

### 3. 페이지 배지 (`/stocks/sepa`)
- `sepa-export-tags.json` 을 fetch, 후보 테이블(트렌드·VCP·3C·파워플레이 전수)과
  매수 추천 리스트의 종목명 옆에 🚢 배지 + 품목명.
- `direct` = 진한 배지, `indirect` = 연한 배지(툴팁/괄호로 근거).
- 태그 파일 없거나 fetch 실패 → 배지 없이 기존 렌더 그대로(그레이스풀).

### 4. /sepa 오케스트레이터 통합
- 5단계(티어 스냅샷) 다음에 **비차단** 스텝으로 `python scripts/tag_export_leaders.py`.
- 커밋 목록에 `sepa-export-tags.json` 추가(실패 시 제외하고 나머지 커밋).
- 스킬 문서(`.claude/skills/sepa/SKILL.md`) 갱신 — 단계·커밋 목록.
  ([doc-logic-sync] 코드와 문서 같은 라운드 동기화.)

## 오류 처리
- FDR 실패 → 캐시 → 이전 산출 유지(비차단, 경고 1줄). 파이프라인 중단 없음.
- 설정파일 스키마 오류 → 명확한 에러 메시지 후 이전 산출 유지.
- 후보 파일 일부 부재(예: 3C 스킵) → 있는 파일만으로 진행.

## 테스트 (오늘 32종목 = 오라클)
`tests/test_export_tags.py` — 분류 함수 단위 테스트(고정 입력, 네트워크 없음):
- S-Oil(010950) → petroleum/direct (업종 "석유 정제품 제조업")
- 샘씨엔에스(252990)·타이거일렉(219130) → semiconductor (전자부품+반도체 제품 텍스트)
- 뉴파워프라즈마(144960) → semiconductor/indirect (오버라이드)
- GS(078930) → petroleum/indirect (오버라이드 include)
- 슈프리마에이치큐(094840) → 태그 없음 (오버라이드 exclude — KSIC 오탐 차단)
- 팬오션(028670) → 태그 없음 (오버라이드 exclude — 선박 이용자≠제조)
- 신한지주(055550) → 태그 없음 (키워드 불일치)

## 안 하는 것 (YAGNI)
- 관세청/무역통계 API 연동 · 수출액 실적 데이터 표시.
- 초수익 점수 반영(별도 백테스트 검증 전 금지) · 정렬 변경 · 보유 점검 표시.
- 전 종목 사전 태깅(후보 등장 종목만 — 파일 비대화 방지).

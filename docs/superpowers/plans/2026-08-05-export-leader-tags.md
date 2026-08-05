# 수출 주도 종목 배지 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SEPA 후보·매수추천에 등장한 종목이 수출 주도 품목(반도체 등 7품목)에 속하면 페이지에 🚢 배지로 표시한다.

**Architecture:** 오케스트레이터 전용 마무리 스텝 패턴(snapshot_sepa.py와 동일). 순수 분류 라이브러리(`scripts/canslim_lib/export_tags.py`) + CLI(`scripts/tag_export_leaders.py`)가 설정파일·KRX 업종 캐시로 `public/data/sepa-export-tags.json`을 산출하고, `/stocks/sepa` 서버 컴포넌트가 코드로 조인해 배지 렌더.

**Tech Stack:** Python 3 (stdlib + FinanceDataReader), pytest, Next.js App Router(서버 컴포넌트) + 기존 클라이언트 테이블 컴포넌트, vitest(기존 `*.test.ts` 패턴).

**Spec:** `docs/superpowers/specs/2026-08-05-export-leader-tags-design.md`

## Global Constraints

- 표시만 한다 — 정렬·초수익 점수·보유 점검 무접촉.
- 분류 실패/데이터 부재 시 추측 금지 — 태그 없음이 정답.
- 파이프라인 내 비차단 — 실패해도 /sepa 진행.
- 결정론 — 같은 입력이면 같은 출력(LLM·시간 의존 없음).
- 커밋은 오케스트레이터(부모)가 아닌 이 플랜 실행자가 태스크 단위로 수행.
- Windows 콘솔 실행은 항상 `python -X utf8`.

---

### Task 1: 분류 라이브러리 + 설정파일 (TDD)

**Files:**
- Create: `public/data/export-leading-config.json`
- Create: `scripts/canslim_lib/export_tags.py`
- Test: `tests/test_export_tags.py`

**Interfaces:**
- Produces: `load_config(path) -> dict`, `classify(code: str, sector: str|None, products: str|None, config: dict) -> dict|None`
  - 반환 태그: `{"category": str, "label": str, "tier": "direct"|"indirect", "basis": str}` 또는 `None`
  - 우선순위: exclude 오버라이드 > include 오버라이드 > 키워드 매칭(direct)

- [ ] **Step 1: 설정파일 작성** — `public/data/export-leading-config.json`:

```json
{
  "asof": "2026-08-05",
  "note": "수출 무역흑자 최대치 국면 주도 품목 — 사용자 직접 관리. 무역 흐름이 바뀌면 categories·overrides 수정.",
  "categories": [
    {"key": "semiconductor", "label": "반도체", "keywords": ["반도체", "웨이퍼", "포토마스크", "메모리"]},
    {"key": "wireless_comm", "label": "무선통신기기", "keywords": ["무선통신", "휴대폰", "스마트폰", "이동전화"]},
    {"key": "wired_comm", "label": "유선통신기기", "keywords": ["유선통신", "통신케이블", "광케이블"]},
    {"key": "petroleum", "label": "석유제품", "keywords": ["석유 정제", "정유", "윤활유"]},
    {"key": "ships", "label": "선박", "keywords": ["선박", "조선", "해양플랜트"]},
    {"key": "appliances", "label": "가전제품", "keywords": ["가전", "냉장고", "세탁기", "에어컨"]},
    {"key": "steel", "label": "철강제품", "keywords": ["철강", "제강", "제철", "강관", "냉연", "열연"]}
  ],
  "overrides": {
    "include": {
      "078930": {"category": "petroleum", "tier": "indirect", "reason": "GS칼텍스(석유제품 수출 대형사) 지주"},
      "144960": {"category": "semiconductor", "tier": "indirect", "reason": "반도체·디스플레이 플라즈마 장비"},
      "006340": {"category": "wired_comm", "tier": "indirect", "reason": "전력선 주력이나 통신케이블 병행"}
    },
    "exclude": {
      "094840": "KSIC 통신장비 코드이나 실제는 지문인식(바이오인식) 지주",
      "028670": "해상 운송업 — 선박을 이용하는 회사지 만드는 회사가 아님"
    }
  }
}
```

- [ ] **Step 2: 실패하는 테스트 작성** — `tests/test_export_tags.py` (오늘 32종목 오라클, 네트워크 없음):

```python
"""수출 주도 종목 분류 오라클 테스트 — 2026-08-05 SEPA 통과 32종목 기준."""
import json
from pathlib import Path

import pytest

from canslim_lib.export_tags import classify, load_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / "public" / "data" / "export-leading-config.json")


def tag(code, sector, products):
    return classify(code, sector, products, CONFIG)


def test_soil_petroleum_direct():
    t = tag("010950", "석유 정제품 제조업", None)
    assert t and t["category"] == "petroleum" and t["tier"] == "direct"
    assert "석유 정제" in t["basis"]


def test_samc_semiconductor_via_products():
    t = tag("252990", "전자부품 제조업", "반도체 검사용 세라믹 STF")
    assert t and t["category"] == "semiconductor" and t["tier"] == "direct"


def test_gs_holding_indirect_override():
    t = tag("078930", "기타 금융업", None)
    assert t and t["category"] == "petroleum" and t["tier"] == "indirect"
    assert "GS칼텍스" in t["basis"]


def test_newpower_semiconductor_indirect_override():
    t = tag("144960", "특수 목적용 기계 제조업", None)
    assert t and t["category"] == "semiconductor" and t["tier"] == "indirect"


def test_suprema_excluded_despite_ksic():
    assert tag("094840", "통신 및 방송 장비 제조업", None) is None


def test_panocean_excluded_shipping_user():
    assert tag("028670", "해상 운송업", "외항 화물 운송") is None


def test_shinhan_no_match():
    assert tag("055550", "기타 금융업", "금융지주회사") is None


def test_none_inputs_no_crash():
    assert tag("000000", None, None) is None


def test_config_schema():
    keys = {c["key"] for c in CONFIG["categories"]}
    assert len(keys) == 7 and "semiconductor" in keys
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `python -X utf8 -m pytest tests/test_export_tags.py -v`
Expected: FAIL — `ModuleNotFoundError: canslim_lib.export_tags` (기존 tests 는 conftest 로 scripts/ 경로 주입 — 없으면 `sys.path` 주입 방식을 기존 테스트 파일과 동일하게 맞춘다)

- [ ] **Step 4: 최소 구현** — `scripts/canslim_lib/export_tags.py`:

```python
"""수출 주도 품목 분류 — 설정 키워드 매칭 + 오버라이드.

우선순위: exclude > include > 키워드(direct). 매칭 실패 = None(추측 금지).
설정: public/data/export-leading-config.json (사용자 직접 관리).
"""
import json
from pathlib import Path


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _label(config, key):
    for c in config["categories"]:
        if c["key"] == key:
            return c["label"]
    return key


def classify(code, sector, products, config):
    ov = config.get("overrides", {})
    if code in ov.get("exclude", {}):
        return None
    inc = ov.get("include", {}).get(code)
    if inc:
        return {"category": inc["category"], "label": _label(config, inc["category"]),
                "tier": inc.get("tier", "indirect"), "basis": inc.get("reason", "오버라이드")}
    text = " ".join(x for x in (sector, products) if x)
    if not text:
        return None
    for cat in config["categories"]:
        for kw in cat["keywords"]:
            if kw in text:
                src = "업종" if sector and kw in sector else "주요제품"
                return {"category": cat["key"], "label": cat["label"],
                        "tier": "direct", "basis": f"{src}: …{kw}…"}
    return None
```

(basis 는 사람이 읽는 근거 문자열 — 정확 포맷은 구현 재량이나 테스트의 `in` 단언은 만족할 것)

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -X utf8 -m pytest tests/test_export_tags.py -v`
Expected: 9 passed

- [ ] **Step 6: Commit**

```bash
git add public/data/export-leading-config.json scripts/canslim_lib/export_tags.py tests/test_export_tags.py
git commit -m "feat(sepa): 수출 주도 품목 분류 라이브러리 + 설정파일"
```

### Task 2: 태깅 CLI 스크립트 + 실산출

**Files:**
- Create: `scripts/tag_export_leaders.py`
- Create(산출): `public/data/sepa-export-tags.json`
- Create(캐시): `.cache/krx_desc.json` (커밋 안 함)

**Interfaces:**
- Consumes: Task 1 의 `load_config`/`classify`.
- Produces: `sepa-export-tags.json` = `{"asof": "YYYY-MM-DD", "config_asof": str, "tags": {code: {name, category, label, tier, basis}}}` — 페이지(Task 3)가 이 스키마를 읽는다.

- [ ] **Step 1: CLI 작성** — `scripts/tag_export_leaders.py`:

```python
"""SEPA 후보 종목 수출 주도 품목 태깅 — /sepa 마무리 비차단 스텝.

입력: sepa-{trend,vcp,power-play-all,3c}-candidates.json + sepa-buy-recommendations.json
      + export-leading-config.json + KRX 업종·주요제품(FDR StockListing('KRX-DESC'), 7일 캐시)
출력: public/data/sepa-export-tags.json
실패 시: 이전 산출 유지(비차단) — exit 0 유지, 경고만 출력.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.export_tags import classify, load_config  # noqa: E402

DATA = ROOT / "public" / "data"
CACHE = ROOT / ".cache" / "krx_desc.json"
CACHE_TTL_DAYS = 7
CANDIDATE_FILES = [
    "sepa-trend-candidates.json", "sepa-vcp-candidates.json",
    "sepa-power-play-all-candidates.json", "sepa-3c-candidates.json",
    "sepa-buy-recommendations.json",
]


def collect_codes():
    codes, names, asof = {}, {}, None
    for fn in CANDIDATE_FILES:
        p = DATA / fn
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        asof = d.get("asof") or asof
        for c in d.get("candidates", []):
            if c.get("code"):
                codes[c["code"]] = True
                names[c["code"]] = c.get("name")
    return list(codes), names, asof


def load_krx_desc():
    if CACHE.exists() and time.time() - CACHE.stat().st_mtime < CACHE_TTL_DAYS * 86400:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing("KRX-DESC")
        m = {str(r["Code"]): {"sector": None if r["Sector"] != r["Sector"] else str(r["Sector"]),
                              "products": None if r["Products"] != r["Products"] else str(r["Products"]),
                              "industry": None if r["Industry"] != r["Industry"] else str(r["Industry"])}
             for _, r in df.iterrows()}
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        return m
    except Exception as e:
        if CACHE.exists():
            print(f"⚠️ KRX 최신 수집 실패({e}) — 캐시 사용")
            return json.loads(CACHE.read_text(encoding="utf-8"))
        raise


def main():
    config = load_config(DATA / "export-leading-config.json")
    codes, names, asof = collect_codes()
    try:
        krx = load_krx_desc()
    except Exception as e:
        print(f"⚠️ 업종 정보 없음({e}) — 이전 태그 파일 유지")
        return
    tags = {}
    for code in codes:
        info = krx.get(code, {})
        # KSIC 세부업종(industry)까지 합쳐 매칭 폭 확보 — sector 는 KOSDAQ 소속부명인 경우 있음
        sector_text = " ".join(x for x in (info.get("sector"), info.get("industry")) if x) or None
        t = classify(code, sector_text, info.get("products"), config)
        if t:
            tags[code] = {"name": names.get(code), **t}
    out = {"asof": asof, "config_asof": config.get("asof"), "tags": tags}
    (DATA / "sepa-export-tags.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    by_cat = {}
    for t in tags.values():
        by_cat[t["label"]] = by_cat.get(t["label"], 0) + 1
    print(f"💾 저장: sepa-export-tags.json — {len(tags)}종목 태깅 / 대상 {len(codes)}종목")
    for k, v in sorted(by_cat.items()):
        print(f"   {k}: {v}")


if __name__ == "__main__":
    main()
```

주의(FDR 데이터 실측 반영): `KRX-DESC` 의 `Sector` 컬럼은 KOSDAQ 에서 소속부명
("우량기업부" 등)이고 실제 업종명은 `Industry` 컬럼이다(2026-08-05 실측). 위처럼
sector+industry 를 합쳐 classify 의 `sector` 인자로 넘긴다.

- [ ] **Step 2: 실행·오늘 오라클 검증**

Run: `python -X utf8 scripts/tag_export_leaders.py`
Expected: 저장 로그 + 태그에 최소 010950(석유제품/direct)·078930(석유제품/indirect)·144960(반도체/indirect)·252990(반도체) 포함, 094840·028670 미포함. 검증:

```bash
python -X utf8 -c "import json; t=json.load(open('public/data/sepa-export-tags.json',encoding='utf-8'))['tags']; print({k:(v['label'],v['tier']) for k,v in t.items()}); assert '010950' in t and '078930' in t and '144960' in t and '094840' not in t and '028670' not in t"
```

타이거일렉(219130)이 Products 텍스트에 '반도체'가 없어 미태깅이면: 실제 Products 값을 확인하고, 반도체 검사용 PCB 가 맞으면 include 오버라이드에 추가(reason 명시) 후 재실행 — 추측으로 키워드를 넓히지 말 것.

- [ ] **Step 3: 전체 pytest 회귀**

Run: `python -X utf8 -m pytest tests/ -x -q`
Expected: 기존 테스트 전부 통과(신규 9 포함)

- [ ] **Step 4: Commit**

```bash
git add scripts/tag_export_leaders.py public/data/sepa-export-tags.json
git commit -m "feat(sepa): 수출 주도 태깅 스크립트 + 오늘 산출"
```

### Task 3: 페이지 배지 렌더 (프론트)

**Files:**
- Create: `src/app/stocks/sepa/ExportBadge.tsx`
- Modify: `src/app/stocks/sepa/page.tsx` (파일 read + prop 전달)
- Modify: `src/app/stocks/sepa/SepaPatternTable.tsx` (종목명 옆 배지)
- Modify: `src/app/stocks/sepa/BuyRecommendationSection.tsx` (종목명 옆 배지)
- Test: `src/app/stocks/sepa/exportTags.test.ts`

**Interfaces:**
- Consumes: `sepa-export-tags.json` 스키마(Task 2 Produces).
- Produces: `ExportBadge.tsx` 가 export — `export interface ExportTag { name?: string|null; category: string; label: string; tier: "direct"|"indirect"; basis: string }`, `export type ExportTagMap = Record<string, ExportTag>`, `export function ExportBadge({ tag }: { tag?: ExportTag })` (tag 없으면 null 반환).

- [ ] **Step 1: 배지 컴포넌트 + 타입** — `src/app/stocks/sepa/ExportBadge.tsx`:

```tsx
// 수출 주도 품목 배지 — 표시 전용(정렬·점수 무관여).
export interface ExportTag {
  name?: string | null;
  category: string;
  label: string;
  tier: "direct" | "indirect";
  basis: string;
}
export type ExportTagMap = Record<string, ExportTag>;

export interface ExportTagsFile {
  asof?: string;
  config_asof?: string;
  tags?: ExportTagMap;
}

export function ExportBadge({ tag }: { tag?: ExportTag }) {
  if (!tag) return null;
  const direct = tag.tier === "direct";
  return (
    <span
      title={`수출 주도 품목(${tag.label}${direct ? "" : " · 간접/밸류체인"}) — ${tag.basis}`}
      className={`inline-flex items-center gap-0.5 rounded px-1 py-px text-[10px] leading-none align-middle ${
        direct ? "text-sky-300 bg-sky-400/15" : "text-sky-300/60 bg-sky-400/10"
      }`}
    >
      🚢 {tag.label}
      {!direct && <span className="opacity-70">·간접</span>}
    </span>
  );
}
```

(색·클래스는 기존 파일들의 인라인 팔레트 관례에 맞춰 조정 가능 — 기존 컴포넌트가 tailwind 임의색 대신 hex 인라인 스타일을 쓰면 그 방식을 따른다)

- [ ] **Step 2: 조인 로직 테스트** — `src/app/stocks/sepa/exportTags.test.ts` (기존 `*.test.ts` 러너/스타일 그대로):

```ts
import { describe, expect, it } from "vitest";
import type { ExportTagsFile } from "./ExportBadge";

function tagFor(file: ExportTagsFile | null, code: string) {
  return file?.tags?.[code];
}

describe("export tags join", () => {
  const file: ExportTagsFile = {
    asof: "2026-08-05",
    tags: {
      "010950": { category: "petroleum", label: "석유제품", tier: "direct", basis: "업종: 석유 정제" },
      "078930": { category: "petroleum", label: "석유제품", tier: "indirect", basis: "GS칼텍스 지주" },
    },
  };
  it("태그 있는 코드만 매칭", () => {
    expect(tagFor(file, "010950")?.tier).toBe("direct");
    expect(tagFor(file, "055550")).toBeUndefined();
  });
  it("파일 없음(null) 그레이스풀", () => {
    expect(tagFor(null, "010950")).toBeUndefined();
  });
});
```

(기존 테스트가 vitest 가 아니면 — `sepaPatterns.test.ts` 상단 import 를 열어 실제 러너를 확인하고 동일하게 작성)

- [ ] **Step 3: 테스트 실행**

Run: `npm test -- exportTags` (기존 테스트 스크립트 관례 — package.json 의 test 스크립트 확인 후 동일 방식)
Expected: PASS

- [ ] **Step 4: page.tsx 연결**

`readJson` 병렬 로드에 추가하고 각 섹션에 전달:

```tsx
import { type ExportTagsFile, type ExportTagMap } from "./ExportBadge";
// SepaPage() 내:
const exportTagsFile = await readJson<ExportTagsFile>("sepa-export-tags.json");
const exportTags: ExportTagMap = exportTagsFile?.tags ?? {};
```

`PatternSection` props 에 `exportTags?: ExportTagMap` 추가 → `<SepaPatternTable rows=… columns=… trendByCode=… exportTags={exportTags} />`, `<BuyRecommendationSection … exportTags={exportTags} />`.

- [ ] **Step 5: 테이블·추천 리스트에 배지 삽입**

`SepaPatternTable.tsx`: `Props` 에 `exportTags?: Record<string, ExportTag>` 추가, 종목명 셀 렌더 지점에서:

```tsx
<ExportBadge tag={exportTags?.[row.code]} />
```

`BuyRecommendationSection.tsx`: 동일하게 props 추가 + 종목명 옆 `<ExportBadge tag={exportTags?.[rec.code]} />`.

- [ ] **Step 6: 타입·빌드 검증**

Run: `npx tsc --noEmit` (또는 프로젝트 관례 `npm run lint`) 후 `npm test`
Expected: 타입 에러 0, 전체 테스트 통과

- [ ] **Step 7: Commit**

```bash
git add src/app/stocks/sepa/ExportBadge.tsx src/app/stocks/sepa/exportTags.test.ts src/app/stocks/sepa/page.tsx src/app/stocks/sepa/SepaPatternTable.tsx src/app/stocks/sepa/BuyRecommendationSection.tsx
git commit -m "feat(sepa): /stocks/sepa 수출 주도 품목 배지 표시"
```

### Task 4: /sepa 오케스트레이터 문서 동기화

**Files:**
- Modify: `.claude/skills/sepa/SKILL.md`

**Interfaces:**
- Consumes: Task 2 CLI (`python scripts/tag_export_leaders.py`).

- [ ] **Step 1: SKILL.md 갱신** — 5단계(스냅샷) 항목 뒤에 비차단 스텝 추가:

```markdown
5.5 **수출 주도 태깅 — `python scripts/tag_export_leaders.py`.** (오케스트레이터
   전용 마무리 스텝 — 후보·추천 등장 종목을 수출 주도 품목(설정:
   `export-leading-config.json`, 사용자 관리)으로 분류해
   `sepa-export-tags.json` 산출. `/stocks/sepa` 배지가 읽는다.)
   - **비차단**: 실패해도 파이프라인 실패 아님 — 오류 한 줄 보고 후 진행
     (그 경우 커밋에서 `sepa-export-tags.json` 제외).
```

커밋 목록(9단계)에 한 줄 추가:

```markdown
   - `public/data/sepa-export-tags.json` (5.5단계 수출 주도 태그 — 실패 시 제외)
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/sepa/SKILL.md
git commit -m "docs(sepa): /sepa 파이프라인에 수출 주도 태깅 스텝 추가"
```

### Task 5: 통합 검증

**Files:** 없음(검증만)

- [ ] **Step 1: 전체 테스트**

Run: `python -X utf8 -m pytest tests/ -q && npm test`
Expected: 전부 통과

- [ ] **Step 2: 빌드 검증**

Run: `npm run build`
Expected: 빌드 성공 (`/stocks/sepa` 정적 생성 포함)

- [ ] **Step 3: 브랜치 push**

```bash
git push origin chore/sepa-2026-08-03
```

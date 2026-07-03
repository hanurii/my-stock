# SEPA 추이 컬럼 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/stocks/sepa` 각 패턴 테이블에 종목별 "최근 티어 추이" 컬럼(예: `🟢🔴`, 신규 진입 `🆕🔴`)을 추가한다.

**Architecture:** 파이프라인 마지막에 `snapshot_sepa.py`가 4개 패턴 후보를 트림해 `sepa-tier-history.json`(최근 3일)에 누적한다. 페이지는 이 히스토리를 읽어 날짜별로 기존 `classify`(레코드 단위)를 돌려 종목별 티어 시퀀스를 만들고, `SepaPatternTable`의 추이 컬럼에 렌더한다.

**Tech Stack:** Python(스냅샷) · Next.js 16/React/TypeScript(페이지) · vitest.

## Global Constraints

- 티어 규칙은 기존 `classify` 재사용(중복 금지). DRY 위해 `buildSection` 내부 로직을 `classifyCandidate(raw, config): Tier | null`로 추출해 공유.
- 티어→점: `breakout → 🔴`, `actionable → 🟢`, `watch → 🟡`, `null → 점 없음`. 신규(직전 날짜 티어 없음+오늘 있음) → 앞에 `🆕`.
- 히스토리 보관 = 최근 **3일**(오늘+2일). 스냅샷 레코드는 트림(화이트리스트 키만), 거대한 트렌드 파일 미포함.
- 대상 패턴 4종: `vcp · powerplayTrend · powerplayAll · threeC` (키는 `PATTERNS`와 동일).
- graceful: 히스토리/후보 파일 없거나 깨지면 추이 컬럼 생략·빈 배열(페이지·빌드 무영향).
- 작업 위치: `my-stock-master`(master, 완전한 node_modules). 검증 `npm run test`·`npx tsc --noEmit`·`npm run build`·`python`.
- UI 관례: 테마 토큰·`material-symbols-outlined`·한국어.

---

### Task 1: 스냅샷 스크립트 + 히스토리 부트스트랩

`snapshot_sepa.py`로 현재 4개 후보를 트림해 `sepa-tier-history.json`에 누적(최근 3일). git으로 6/30·7/1 부트스트랩.

**Files:**
- Create: `scripts/snapshot_sepa.py`
- Create(부트스트랩 산출): `public/data/sepa-tier-history.json`

**Interfaces:**
- Consumes: 없음(현재 `public/data`의 4개 후보 파일 읽음).
- Produces: `public/data/sepa-tier-history.json` — `{ "dates": string[], "byDate": { "<date>": { "vcp":[trim…], "powerplayTrend":[…], "powerplayAll":[…], "threeC":[…] } } }` (레코드 = 화이트리스트 키). 재사용 함수 `snapshot_from(data_dir: Path, hist_path: Path) -> None`, 상수 `HIST_PATH`.

- [ ] **Step 1: `snapshot_sepa.py` 작성**

Create `scripts/snapshot_sepa.py`:

```python
# scripts/snapshot_sepa.py
"""SEPA 티어 히스토리 스냅샷 — 파이프라인 마지막 스텝.

현재 public/data의 4개 패턴 후보 파일을 트림해 sepa-tier-history.json 에 그 asof 날짜로
추가하고, 최근 3일(오늘+2일)치만 유지한다. 페이지의 '추이' 컬럼 계산에 쓰인다.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
HIST_PATH = DATA / "sepa-tier-history.json"
MAX_DATES = 3

# 패턴키(페이지 PATTERNS와 동일) → 후보 파일명
PATTERN_FILES = {
    "vcp": "sepa-vcp-candidates.json",
    "powerplayTrend": "sepa-power-play-candidates.json",
    "powerplayAll": "sepa-power-play-all-candidates.json",
    "threeC": "sepa-3c-candidates.json",
}
# 분류·표시에 필요한 최소 키(존재하는 것만 보존)
KEEP_KEYS = [
    "code", "name", "market", "rs", "status", "pivot_price", "pct_to_pivot",
    "vcp_detected", "pattern_detected", "num_contractions",
    "flag_length_days", "flag_depth_pct",
]


def _trim(cand: dict) -> dict:
    return {k: cand[k] for k in KEEP_KEYS if k in cand}


def snapshot_from(data_dir: Path, hist_path: Path) -> None:
    asof = None
    by_pattern: dict[str, list] = {}
    for key, fname in PATTERN_FILES.items():
        p = data_dir / fname
        if not p.exists():
            by_pattern[key] = []
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            by_pattern[key] = []
            continue
        by_pattern[key] = [_trim(c) for c in d.get("candidates", [])]
        asof = asof or d.get("asof")
    if not asof:
        print("❌ asof 없음(후보 파일 부재) — 스냅샷 건너뜀")
        return

    hist = {"dates": [], "byDate": {}}
    if hist_path.exists():
        try:
            hist = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            hist = {"dates": [], "byDate": {}}
    hist.setdefault("dates", [])
    hist.setdefault("byDate", {})

    hist["byDate"][asof] = by_pattern
    dates = sorted(set(hist["byDate"].keys()))     # 오래된→최신
    dates = dates[-MAX_DATES:]                      # 최근 3일만
    hist["byDate"] = {d: hist["byDate"][d] for d in dates}
    hist["dates"] = dates

    hist_path.parent.mkdir(parents=True, exist_ok=True)
    hist_path.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {k: len(v) for k, v in by_pattern.items()}
    print(f"💾 스냅샷: {hist_path.relative_to(ROOT)} | {asof} 추가 | dates={dates} | {counts}")


def main() -> None:
    ap = argparse.ArgumentParser(description="SEPA 티어 히스토리 스냅샷")
    ap.add_argument("--data-dir", default=None, help="후보 파일 디렉토리(부트스트랩용, 기본 public/data)")
    args = ap.parse_args()
    data_dir = Path(args.data_dir) if args.data_dir else DATA
    snapshot_from(data_dir, HIST_PATH)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 부트스트랩 — 6/30 + 7/1 히스토리 생성**

6/30 후보 파일(git `108e471`)을 임시 폴더로 꺼내 6/30 스냅샷 → 그다음 현재(7/1) 스냅샷:

```bash
cd /c/Users/hanul/playground/my-stock-master
TMP=$(mktemp -d)
for f in sepa-vcp-candidates.json sepa-power-play-candidates.json sepa-power-play-all-candidates.json sepa-3c-candidates.json; do
  git show 108e471:public/data/$f > "$TMP/$f"
done
python -X utf8 scripts/snapshot_sepa.py --data-dir "$TMP"   # 6/30 추가
python -X utf8 scripts/snapshot_sepa.py                     # 7/1(현재) 추가
rm -rf "$TMP"
```

Expected: 두 번째 실행 로그가 `dates=['2026-06-30','2026-07-01']` 를 포함.

- [ ] **Step 3: 부트스트랩 검증**

Run:
```bash
cd /c/Users/hanul/playground/my-stock-master && python -X utf8 -c "import json; d=json.load(open('public/data/sepa-tier-history.json',encoding='utf-8')); print('dates',d['dates']); print('patterns',list(d['byDate'][d['dates'][-1]].keys())); print('vcp 7/1 recs',len(d['byDate']['2026-07-01']['vcp'])); print('sample',d['byDate']['2026-07-01']['vcp'][0])"
```
Expected: `dates ['2026-06-30', '2026-07-01']`, `patterns ['vcp','powerplayTrend','powerplayAll','threeC']`, vcp 레코드 수 >0, 샘플에 `code/name/status/pivot_price/pct_to_pivot/vcp_detected/num_contractions` 존재(트렌드 등 불필요 키 없음).

- [ ] **Step 4: 커밋**

```bash
git add scripts/snapshot_sepa.py public/data/sepa-tier-history.json
git commit -m "feat(sepa): 티어 히스토리 스냅샷 스크립트 + 6/30·7/1 부트스트랩"
```

---

### Task 2: `classifyCandidate` 추출 + 순수 `tierHistory.ts`

`buildSection` 내부 분류 로직을 `classifyCandidate`로 추출(DRY)하고, 히스토리에서 종목별 티어 추이 문자열을 계산하는 순수 모듈 + vitest.

**Files:**
- Modify: `src/app/stocks/sepa/sepaPatterns.ts` (`classifyCandidate` export + `buildSection` 재사용)
- Create: `src/app/stocks/sepa/tierHistory.ts`
- Test: `src/app/stocks/sepa/tierHistory.test.ts`

**Interfaces:**
- Consumes: `classify`, `PATTERNS`, types `Tier`/`RawCandidate`/`PatternConfig`, 신규 `classifyCandidate` (sepaPatterns.ts).
- Produces:
  - (sepaPatterns.ts) `function classifyCandidate(raw: RawCandidate, config: PatternConfig, watchPct?: number): Tier | null`
  - (tierHistory.ts) `type PatternKey = keyof typeof PATTERNS`
  - `interface TierHistory { dates: string[]; byDate: Record<string, Partial<Record<PatternKey, RawCandidate[]>>> }`
  - `function renderTrend(seq: (Tier | null)[]): string`
  - `function computeTrendByCode(history: TierHistory, patternKey: PatternKey, config: PatternConfig): Record<string, string>`

- [ ] **Step 1: `sepaPatterns.ts`에 `classifyCandidate` 추출**

`src/app/stocks/sepa/sepaPatterns.ts`에서 `buildSection`을 찾아, 루프 내 분류 로직을 헬퍼로 뽑는다. 먼저 `buildSection` 바로 위에 헬퍼를 추가:

```ts
// 레코드 1건 → 티어(숨김이면 null). buildSection·tierHistory 공유(DRY).
export function classifyCandidate(
  raw: RawCandidate,
  config: PatternConfig,
  watchPct: number = WATCH_PCT
): Tier | null {
  const detected = Boolean(raw[config.detectField]);
  const structureOk = config.structureOk(raw);
  return classify(
    {
      detected,
      status: String(raw.status ?? ""),
      pivot_price: num(raw.pivot_price),
      pct_to_pivot: num(raw.pct_to_pivot),
      structureOk,
    },
    watchPct
  );
}
```

그리고 `buildSection`의 루프를 이 헬퍼를 쓰도록 교체한다. 기존:

```ts
  for (const raw of candidates ?? []) {
    const detected = Boolean(raw[config.detectField]);
    const structureOk = config.structureOk(raw);
    const pivot_price = num(raw.pivot_price);
    const pct_to_pivot = num(raw.pct_to_pivot);
    const status = String(raw.status ?? "");
    const tier = classify({ detected, status, pivot_price, pct_to_pivot, structureOk }, watchPct);
    if (!tier) continue;
    rows.push({
      code: raw.code,
      name: raw.name,
      market: raw.market,
      current_price: raw.current_price,
      rs: raw.rs ?? null,
      status,
      pivot_price,
      pct_to_pivot,
      tier,
      raw,
    });
  }
```

교체:

```ts
  for (const raw of candidates ?? []) {
    const tier = classifyCandidate(raw, config, watchPct);
    if (!tier) continue;
    rows.push({
      code: raw.code,
      name: raw.name,
      market: raw.market,
      current_price: raw.current_price,
      rs: raw.rs ?? null,
      status: String(raw.status ?? ""),
      pivot_price: num(raw.pivot_price),
      pct_to_pivot: num(raw.pct_to_pivot),
      tier,
      raw,
    });
  }
```

- [ ] **Step 2: 리팩터 회귀 확인(기존 테스트 유지)**

Run: `cd /c/Users/hanul/playground/my-stock-master && npm run test`
Expected: 기존 29건 그대로 PASS(buildSection 동작 불변).

- [ ] **Step 3: 실패 테스트 작성 (`tierHistory.test.ts`)**

Create `src/app/stocks/sepa/tierHistory.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { renderTrend, computeTrendByCode, type TierHistory } from "./tierHistory";
import { PATTERNS, type RawCandidate } from "./sepaPatterns";

describe("renderTrend", () => {
  it("어제→오늘 티어 점", () => {
    expect(renderTrend(["actionable", "breakout"])).toBe("🟢🔴");
    expect(renderTrend(["actionable", "actionable"])).toBe("🟢🟢");
    expect(renderTrend(["actionable", "watch"])).toBe("🟢🟡");
  });
  it("신규(직전 없음+오늘 있음) → 🆕 접두", () => {
    expect(renderTrend([null, "breakout"])).toBe("🆕🔴");
    expect(renderTrend([null, null, "breakout"])).toBe("🆕🔴");
  });
  it("단일 날짜는 🆕 없음", () => {
    expect(renderTrend(["breakout"])).toBe("🔴");
  });
  it("3일치", () => {
    expect(renderTrend(["watch", "actionable", "breakout"])).toBe("🟡🟢🔴");
  });
  it("모두 없음 → 빈 문자열", () => {
    expect(renderTrend([null, null])).toBe("");
  });
});

describe("computeTrendByCode", () => {
  // 최소 필드만 갖춘 VCP 레코드
  const rec = (code: string, over: Partial<RawCandidate>): RawCandidate => ({
    code, name: code, market: "KOSPI", current_price: 1, rs: 90,
    status: "forming", pivot_price: 100, pct_to_pivot: 5,
    vcp_detected: true, num_contractions: 2, ...over,
  });
  const history: TierHistory = {
    dates: ["2026-06-30", "2026-07-01"],
    byDate: {
      "2026-06-30": {
        vcp: [
          rec("A", { status: "actionable", pct_to_pivot: 2 }),   // 어제 🟢
          rec("B", { status: "actionable", pct_to_pivot: 2 }),   // 어제 🟢
        ],
      },
      "2026-07-01": {
        vcp: [
          rec("A", { status: "breakout", pct_to_pivot: -5 }),    // 오늘 🔴
          rec("B", { status: "forming", pct_to_pivot: 6 }),      // 오늘 🟡
          rec("C", { status: "breakout", pct_to_pivot: -3 }),    // 오늘 🔴 (신규)
        ],
      },
    },
  };
  it("종목별 추이 문자열 (신규 🆕 포함)", () => {
    const t = computeTrendByCode(history, "vcp", PATTERNS.vcp);
    expect(t["A"]).toBe("🟢🔴");   // 진입임박 → 돌파
    expect(t["B"]).toBe("🟢🟡");   // 진입임박 → 예의주시
    expect(t["C"]).toBe("🆕🔴");   // 어제 없음 → 오늘 돌파
  });
});
```

- [ ] **Step 4: 실패 확인**

Run: `cd /c/Users/hanul/playground/my-stock-master && npm run test`
Expected: FAIL — `Cannot find module './tierHistory'`.

- [ ] **Step 5: `tierHistory.ts` 구현**

Create `src/app/stocks/sepa/tierHistory.ts`:

```ts
// SEPA 티어 추이 계산 (순수). 히스토리 스냅샷 → 종목별 최근 티어 시퀀스 문자열.
import {
  classifyCandidate,
  PATTERNS,
  type PatternConfig,
  type RawCandidate,
  type Tier,
} from "./sepaPatterns";

export type PatternKey = keyof typeof PATTERNS;

export interface TierHistory {
  dates: string[];
  byDate: Record<string, Partial<Record<PatternKey, RawCandidate[]>>>;
}

const TIER_DOT: Record<Tier, string> = {
  breakout: "🔴",
  actionable: "🟢",
  watch: "🟡",
};

// 티어 시퀀스(오래된→최신) → 표시 문자열. null(숨김/미노출)은 점 생략.
// 신규(직전 날짜 null + 최신 non-null, 직전 날짜가 존재할 때) → 앞에 🆕.
export function renderTrend(seq: (Tier | null)[]): string {
  const dots = seq
    .filter((t): t is Tier => t != null)
    .map((t) => TIER_DOT[t])
    .join("");
  const last = seq[seq.length - 1];
  const prev = seq.length >= 2 ? seq[seq.length - 2] : undefined;
  const isNew = last != null && prev === null;
  return (isNew ? "🆕" : "") + dots;
}

export function computeTrendByCode(
  history: TierHistory,
  patternKey: PatternKey,
  config: PatternConfig
): Record<string, string> {
  const dates = history.dates ?? [];
  const tierPerDate: Record<string, Record<string, Tier | null>> = {};
  const allCodes = new Set<string>();
  for (const d of dates) {
    const recs = history.byDate?.[d]?.[patternKey] ?? [];
    const m: Record<string, Tier | null> = {};
    for (const raw of recs) {
      m[raw.code] = classifyCandidate(raw, config);
      allCodes.add(raw.code);
    }
    tierPerDate[d] = m;
  }
  const out: Record<string, string> = {};
  for (const code of allCodes) {
    const seq = dates.map((d) => tierPerDate[d]?.[code] ?? null);
    out[code] = renderTrend(seq);
  }
  return out;
}
```

- [ ] **Step 6: 통과 확인**

Run: `cd /c/Users/hanul/playground/my-stock-master && npm run test`
Expected: 전부 PASS(renderTrend·computeTrendByCode 신규 + 기존 29건).

- [ ] **Step 7: 타입·린트**

Run: `cd /c/Users/hanul/playground/my-stock-master && npx tsc --noEmit && npx eslint src/app/stocks/sepa/tierHistory.ts src/app/stocks/sepa/sepaPatterns.ts`
Expected: 에러 없음.

- [ ] **Step 8: 커밋**

```bash
git add src/app/stocks/sepa/sepaPatterns.ts src/app/stocks/sepa/tierHistory.ts src/app/stocks/sepa/tierHistory.test.ts
git commit -m "feat(sepa): classifyCandidate 추출 + 티어 추이 계산 모듈 + vitest"
```

---

### Task 3: 추이 컬럼(테이블) + 페이지 연결

`SepaPatternTable`에 추이 컬럼을 추가하고, `page.tsx`가 히스토리를 로드해 패턴별 추이를 계산·전달한다.

**Files:**
- Modify: `src/app/stocks/sepa/SepaPatternTable.tsx` (선택적 `trendByCode` prop + "추이" 컬럼)
- Modify: `src/app/stocks/sepa/page.tsx` (히스토리 로드·계산·전달, PatternSection prop)
- Modify: `.claude/skills/find-3c/SKILL.md` (스냅샷 스텝 안내 1줄)

**Interfaces:**
- Consumes (Task 2): `computeTrendByCode`, `type TierHistory` (tierHistory.ts), `PATTERNS`.
- Produces: 추이 컬럼이 있는 `SepaPatternTable`; 히스토리를 읽어 전달하는 `page.tsx`.

- [ ] **Step 1: `SepaPatternTable`에 추이 컬럼 추가**

`src/app/stocks/sepa/SepaPatternTable.tsx`의 `Props`에 `trendByCode?` 추가:

```tsx
interface Props {
  rows: ClassifiedRow[];
  columns: PatternColumn[];
  trendByCode?: Record<string, string>;
}
```

컴포넌트 시그니처를 `export function SepaPatternTable({ rows, columns, trendByCode }: Props) {` 로 바꾼다.

헤더에서 "피벗대비" `SortHeader` 다음 줄에 추이 헤더를 추가:

```tsx
            <SortHeader k="from_pivot" label="피벗대비" activeSortKey={sortKey} sortDesc={sortDesc} onToggle={toggleSort} />
            {trendByCode && (
              <th className="px-2 py-2 text-center text-[11px] font-medium text-on-surface-variant/80" title="최근 티어 추이(오래된→최신). 🆕=오늘 신규">
                추이
              </th>
            )}
```

바디에서 "피벗대비" `<td>` (pivotColor 스타일 td) 다음에 추이 셀을 추가:

```tsx
                <td className="px-2 py-2 text-right" style={{ color: pivotColor(r.pct_to_pivot) }}>
                  {/* 표시 부호 반전 ... 기존 주석 유지 */}
                  {fmtPct(r.pct_to_pivot === null ? null : -r.pct_to_pivot, 1)}
                </td>
                {trendByCode && (
                  <td className="px-2 py-2 text-center whitespace-nowrap tracking-wide">
                    {trendByCode[r.code] || "—"}
                  </td>
                )}
```

- [ ] **Step 2: `page.tsx` — 히스토리 로드·계산·전달**

`src/app/stocks/sepa/page.tsx` 상단 import에 추가(기존 sepaPatterns import 아래):

```tsx
import { computeTrendByCode, type TierHistory } from "./tierHistory";
```

`SepaPage` 함수에서 기존 `Promise.all([...])` 로드 블록 다음에 히스토리 로드·계산을 추가한다. 기존:

```tsx
  const [trend, vcp, ppTrend, ppAll, threeC] = await Promise.all([
    readJson<TrendData>("sepa-trend-candidates.json"),
    readJson<CandidateFile>(PATTERNS.vcp.file),
    readJson<CandidateFile>(PATTERNS.powerplayTrend.file),
    readJson<CandidateFile>(PATTERNS.powerplayAll.file),
    readJson<CandidateFile>(PATTERNS.threeC.file),
  ]);
```

바로 다음에 삽입:

```tsx
  const history = await readJson<TierHistory>("sepa-tier-history.json");
  const trends = history
    ? {
        vcp: computeTrendByCode(history, "vcp", PATTERNS.vcp),
        powerplayTrend: computeTrendByCode(history, "powerplayTrend", PATTERNS.powerplayTrend),
        powerplayAll: computeTrendByCode(history, "powerplayAll", PATTERNS.powerplayAll),
        threeC: computeTrendByCode(history, "threeC", PATTERNS.threeC),
      }
    : null;
```

`PatternSection` 헬퍼에 `trendByCode` prop을 추가한다. 기존:

```tsx
function PatternSection({
  config,
  data,
}: {
  config: PatternConfig;
  data: CandidateFile | null;
}) {
```

교체:

```tsx
function PatternSection({
  config,
  data,
  trendByCode,
}: {
  config: PatternConfig;
  data: CandidateFile | null;
  trendByCode?: Record<string, string>;
}) {
```

그리고 그 안의 `<SepaPatternTable rows={rows} columns={config.columns} />` 를 교체:

```tsx
      <SepaPatternTable rows={rows} columns={config.columns} trendByCode={trendByCode} />
```

마지막으로 4개 `<PatternSection .../>` 호출에 `trendByCode`를 전달:

```tsx
      <PatternSection config={PATTERNS.vcp} data={vcp} trendByCode={trends?.vcp} />
      <PatternSection config={PATTERNS.powerplayTrend} data={ppTrend} trendByCode={trends?.powerplayTrend} />
      <PatternSection config={PATTERNS.powerplayAll} data={ppAll} trendByCode={trends?.powerplayAll} />
      <PatternSection config={PATTERNS.threeC} data={threeC} trendByCode={trends?.threeC} />
```

- [ ] **Step 3: find-3c 스킬에 스냅샷 스텝 1줄 안내**

`.claude/skills/find-3c/SKILL.md`의 실행 절차 끝(또는 "다음 단계" 부근)에 한 줄 추가:

```markdown
- SEPA 파이프라인 마지막에 `python scripts/snapshot_sepa.py` 를 실행해 티어 추이 스냅샷(`sepa-tier-history.json`, 최근 3일)을 갱신한다 — `/stocks/sepa` 페이지의 '추이' 컬럼용.
```

(파일에 해당 섹션이 없으면 문서 맨 끝에 `## 다음 단계` 로 추가.)

- [ ] **Step 4: 빌드·린트·테스트**

Run: `cd /c/Users/hanul/playground/my-stock-master && npx tsc --noEmit && npx eslint src/app/stocks/sepa/SepaPatternTable.tsx src/app/stocks/sepa/page.tsx && npm run test && npm run build`
Expected: 타입·린트 에러 없음, vitest PASS, `next build` 성공(`/stocks/sepa` 정적 라우트).

- [ ] **Step 5: 수동 시각 확인**

Run: `cd /c/Users/hanul/playground/my-stock-master && npm run dev` → `http://localhost:3000/stocks/sepa`
Expected: VCP 테이블에 "추이" 컬럼. 타이거일렉 `🟢🔴`, 아이비김영 `🆕🔴`, 삼성전기 `🟢🟢`, 나이스정보통신·비엠티 `🟢🟡`. 파워플레이·3C 테이블에도 추이 컬럼 표시.

- [ ] **Step 6: 커밋**

```bash
git add src/app/stocks/sepa/SepaPatternTable.tsx src/app/stocks/sepa/page.tsx .claude/skills/find-3c/SKILL.md
git commit -m "feat(sepa): 패턴 테이블 추이 컬럼 + 히스토리 연결 + 스냅샷 스텝 안내"
```

---

## Self-Review

**Spec coverage:**
- §2 추이 컬럼만·점 매핑·🆕·classify 재사용·3일·4패턴 → Task 2(renderTrend/classifyCandidate)·Task 3(컬럼)·Task 1(3일) ✓
- §4 히스토리 파일·트림·스냅샷 스텝·부트스트랩 → Task 1 ✓
- §5 tierHistory 로직(classifyCandidate 헬퍼·renderTrend·computeTrendByCode) → Task 2 ✓
- §6 컴포넌트·page·PatternSection·스킬 문서 → Task 3 ✓
- §7 graceful(히스토리 없음→컬럼 생략, 파일 일부 없음→빈 배열) → Task 1(빈 배열)·Task 3(trends null→trendByCode undefined→컬럼 생략) ✓
- §8 테스트(renderTrend·computeTrendByCode·스냅샷 스모크·tsc/build) → Task 1 Step 3·Task 2·Task 3 Step 4 ✓

**Placeholder scan:** 코드 스텝 모두 완전한 코드. Task 3(컴포넌트/page)은 vitest 없음(프로젝트 React 테스트 환경 부재, 로직은 Task 2에서 검증 — 명시적 의도). 스냅샷 스텝 안내 문구는 실제 명령.

**Type consistency:** `classifyCandidate(raw, config, watchPct?)`가 Task 2 정의·`buildSection`/`computeTrendByCode` 사용에서 일치. `TierHistory{dates,byDate}`·`PatternKey`·`renderTrend`·`computeTrendByCode` 시그니처가 Task 2 정의·Task 3(page) 사용에서 동일. 히스토리 `byDate` 안쪽 키(vcp/powerplayTrend/powerplayAll/threeC)가 Task 1 스냅샷·Task 2 조회·Task 3 계산에서 동일. `trendByCode?: Record<string,string>`가 Task 3 SepaPatternTable·PatternSection·page에서 일관.

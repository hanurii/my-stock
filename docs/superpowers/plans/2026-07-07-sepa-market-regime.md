# /stocks/sepa 시장 국면 차트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 등가중 지수·20일선·하락구간 음영·현재 상태를 `/stocks/sepa` 최상단에 차트로 보여줘 국면을 눈으로 확인하게 한다.

**Architecture:** Python 스크립트가 등가중 지수(전 종목 일평균수익 누적)+20일선+국면을 `public/data/market-regime.json` 으로 생성 → 서버 컴포넌트 page.tsx 가 빌드타임에 읽어 클라이언트 recharts 차트에 전달. 음영 구간 계산은 순수 헬퍼로 분리해 테스트.

**Tech Stack:** Next.js App Router(서버+클라이언트 컴포넌트) · recharts ^3.8.0 · Tailwind · vitest · Python(canslim_lib·autobuy 재사용)

## Global Constraints

- 작업 위치: 워크트리 `C:\Users\hanul\playground\my-stock-regime`, 브랜치 `feat/sepa-market-regime`(origin/master 451d6ba). **master 기준**(프로덕션 자동배포).
- 국면 정의: **등가중 지수 > 20일 이동평균 = 상승추세**(봇·리포트와 동일). 등가중 구성은 `autobuy.watchlist.build_ew_index` 재사용.
- 기간: 최근 250거래일(~12개월). 첫 표시일=100 정규화(index·ma20 동일 배율, 국면 판정은 스케일 무관).
- **정션 금지**: 캐시는 주 작업트리 `C:\Users\hanul\playground\my-stock` 절대경로 참조.
- 차트 다크테마: 기존 `src/components/MiniChart.tsx` 색·축 스타일 준수(지수 라인 #95d3ba, 축 tick #909097, axis #2e3447).
- 각주 필수: "전 종목 등가중 지수(자작·시장 폭). 코스피 아님."
- 페이지 데이터 로드는 기존 `readJson<T>(filename)` 헬퍼 재사용(없으면 null 반환 — 이미 try/catch 내장).

## 파일 구조

- `scripts/build_market_regime.py` (신규) — 데이터 생성.
- `public/data/market-regime.json` (신규 산출).
- `src/app/stocks/sepa/marketRegime.ts` (신규) — 타입 + `downtrendSegments` 순수 헬퍼.
- `src/app/stocks/sepa/marketRegime.test.ts` (신규) — 헬퍼 vitest.
- `src/app/stocks/sepa/MarketRegimeChart.tsx` (신규, "use client") — recharts 차트.
- `src/app/stocks/sepa/page.tsx` (수정) — 최상단 섹션 반영.

---

### Task 1: 데이터 스크립트 `build_market_regime.py`

**Files:**
- Create: `scripts/build_market_regime.py`
- 산출: `public/data/market-regime.json`

**Interfaces:**
- Consumes: `autobuy.watchlist.build_ew_index(get_series, codes) -> list[float]`(sorted(union dates) 축 정렬), `canslim_lib.ohlcv_matrix.get_series`.
- Produces: `market-regime.json` = `{generated_at, current:{date,index,ma20,uptrend}, series:[{date,index,ma20,up}]}`.

- [ ] **Step 1: Implement** — `scripts/build_market_regime.py`:
```python
"""등가중 시장 국면 지수 → public/data/market-regime.json.
전 종목 일평균수익 누적 등가중 지수 + 20일선 + 국면(위/아래). 봇·리포트와 동일 잣대.
실행: python -X utf8 scripts/build_market_regime.py. 정션 금지 — 캐시는 주 작업트리 절대경로."""
from __future__ import annotations
import json, sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MAIN = Path(r"C:\Users\hanul\playground\my-stock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib import ohlcv_matrix  # noqa: E402
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
from autobuy.watchlist import build_ew_index  # noqa: E402

WINDOW = 250
MA = 20


def build():
    codes = [p.stem for p in (MAIN / ".cache" / "ohlcv" / "series").glob("*.json")]
    idx = build_ew_index(ohlcv_matrix.get_series, codes)
    all_dates = sorted({d for c in codes for d in (ohlcv_matrix.get_series(c) or {}).get("dates", [])})
    n = min(len(idx), len(all_dates))
    idx, all_dates = idx[:n], all_dates[:n]
    ma20 = [None] * n
    for i in range(n):
        if i >= MA - 1:
            ma20[i] = sum(idx[i - MA + 1:i + 1]) / MA
    start = max(0, n - WINDOW)
    base = idx[start] or 1.0
    series = []
    for i in range(start, n):
        v = idx[i] / base * 100
        m = (ma20[i] / base * 100) if ma20[i] is not None else None
        up = (v > m) if m is not None else None
        series.append({"date": all_dates[i], "index": round(v, 2),
                       "ma20": (round(m, 2) if m is not None else None), "up": up})
    last = series[-1]
    out = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "current": {"date": last["date"], "index": last["index"], "ma20": last["ma20"], "uptrend": last["up"]},
           "series": series}
    outp = ROOT / "public" / "data" / "market-regime.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"저장 {outp} · {len(series)}일 · 현재 {last['date']} 지수 {last['index']} "
          f"20MA {last['ma20']} → {'상승추세' if last['up'] else '하락추세'}")


if __name__ == "__main__":
    build()
```

- [ ] **Step 2: 스모크 실행**

Run: `python -X utf8 scripts/build_market_regime.py`
Expected: `저장 ...market-regime.json · 250일 · 현재 2026-07-07 ... → 하락추세`
(최근 6·7월은 등가중 하락추세이므로 **현재=하락추세(uptrend:false)** 여야 정상. 상승추세로 나오면 로직 오류 — 조사.)

- [ ] **Step 3: JSON 형태 확인**

Run: `python -X utf8 -c "import json;d=json.load(open('public/data/market-regime.json',encoding='utf-8'));print(d['current']);print('series',len(d['series']),d['series'][0],d['series'][-1])"`
Expected: current 에 uptrend:false, series 250개, 각 원소에 date/index/ma20/up. 첫 원소 index≈100.

- [ ] **Step 4: Commit**
```bash
git add scripts/build_market_regime.py public/data/market-regime.json
git commit -m "feat(sepa-regime): build_market_regime.py — 등가중 국면 지수 데이터 생성"
```

---

### Task 2: 타입 + `downtrendSegments` 순수 헬퍼 (TDD)

**Files:**
- Create: `src/app/stocks/sepa/marketRegime.ts`
- Test: `src/app/stocks/sepa/marketRegime.test.ts`

**Interfaces:**
- Produces: `type MarketRegime`, `type RegimePoint`, `downtrendSegments(series: RegimePoint[]) -> {x1:string; x2:string}[]` (up===false 연속 구간을 첫날~끝날로 묶음).

- [ ] **Step 1: Write failing tests** — `src/app/stocks/sepa/marketRegime.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { downtrendSegments, type RegimePoint } from "./marketRegime";

const pt = (date: string, up: boolean | null): RegimePoint => ({ date, index: 100, ma20: 100, up });

describe("downtrendSegments", () => {
  it("단일 하락구간을 묶는다", () => {
    const s = [pt("d0", true), pt("d1", false), pt("d2", false), pt("d3", true)];
    expect(downtrendSegments(s)).toEqual([{ x1: "d1", x2: "d2" }]);
  });
  it("복수 하락구간을 각각 묶는다", () => {
    const s = [pt("d0", false), pt("d1", true), pt("d2", false)];
    expect(downtrendSegments(s)).toEqual([{ x1: "d0", x2: "d0" }, { x1: "d2", x2: "d2" }]);
  });
  it("끝까지 하락이면 마지막 구간을 닫는다", () => {
    const s = [pt("d0", true), pt("d1", false), pt("d2", false)];
    expect(downtrendSegments(s)).toEqual([{ x1: "d1", x2: "d2" }]);
  });
  it("전부 상승이면 빈 배열", () => {
    expect(downtrendSegments([pt("d0", true), pt("d1", true)])).toEqual([]);
  });
  it("up===null 은 하락으로 치지 않는다", () => {
    const s = [pt("d0", null), pt("d1", false)];
    expect(downtrendSegments(s)).toEqual([{ x1: "d1", x2: "d1" }]);
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `npx vitest run src/app/stocks/sepa/marketRegime.test.ts`
Expected: FAIL — cannot resolve `./marketRegime`.

- [ ] **Step 3: Implement** — `src/app/stocks/sepa/marketRegime.ts`:
```ts
export type RegimePoint = { date: string; index: number; ma20: number | null; up: boolean | null };

export type MarketRegime = {
  generated_at: string;
  current: { date: string; index: number; ma20: number | null; uptrend: boolean | null };
  series: RegimePoint[];
};

/** series 에서 하락구간(up===false)이 연속된 구간을 [{x1,x2}] 로 묶는다(음영용). */
export function downtrendSegments(series: RegimePoint[]): { x1: string; x2: string }[] {
  const segs: { x1: string; x2: string }[] = [];
  let start: string | null = null;
  let prev: string | null = null;
  for (const p of series) {
    if (p.up === false) {
      if (start === null) start = p.date;
      prev = p.date;
    } else if (start !== null && prev !== null) {
      segs.push({ x1: start, x2: prev });
      start = null;
      prev = null;
    }
  }
  if (start !== null && prev !== null) segs.push({ x1: start, x2: prev });
  return segs;
}
```

- [ ] **Step 4: Run tests to pass**

Run: `npx vitest run src/app/stocks/sepa/marketRegime.test.ts`
Expected: 5 passed.

- [ ] **Step 5: Commit**
```bash
git add src/app/stocks/sepa/marketRegime.ts src/app/stocks/sepa/marketRegime.test.ts
git commit -m "feat(sepa-regime): MarketRegime 타입 + downtrendSegments 헬퍼(TDD)"
```

---

### Task 3: 차트 컴포넌트 + 페이지 반영

**Files:**
- Create: `src/app/stocks/sepa/MarketRegimeChart.tsx`
- Modify: `src/app/stocks/sepa/page.tsx`

**Interfaces:**
- Consumes: `marketRegime.ts`(MarketRegime·downtrendSegments), recharts, `readJson<T>` (page 내 기존 헬퍼).
- Produces: `<MarketRegimeChart data={MarketRegime} />`; page 최상단 "시장 국면" 섹션.

- [ ] **Step 1: Implement chart** — `src/app/stocks/sepa/MarketRegimeChart.tsx`:
```tsx
"use client";

import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import { type MarketRegime, downtrendSegments } from "./marketRegime";

export function MarketRegimeChart({ data }: { data: MarketRegime }) {
  if (!data || data.series.length < 2) {
    return (
      <p className="text-[11px] text-on-surface-variant/70">
        국면 데이터 없음 — build_market_regime.py 실행 필요
      </p>
    );
  }
  const segs = downtrendSegments(data.series);
  const up = data.current.uptrend;
  const tickInterval = Math.max(1, Math.floor(data.series.length / 8));
  return (
    <div>
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span
          className="text-[11px] font-medium px-2 py-0.5 rounded"
          style={{
            backgroundColor: up ? "rgba(16,185,129,0.18)" : "rgba(255,180,171,0.18)",
            color: up ? "#10b981" : "#ffb4ab",
          }}
        >
          {up ? "🟢 상승추세 (매매 ON)" : "🔴 하락추세 (매매 OFF)"}
        </span>
        <span className="text-[11px] text-on-surface-variant/70">
          {data.current.date} · 지수 {data.current.index} / 20일선 {data.current.ma20 ?? "—"}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data.series} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
          {segs.map((s, i) => (
            <ReferenceArea key={i} x1={s.x1} x2={s.x2} fill="#ff5449" fillOpacity={0.08} ifOverflow="extendDomain" />
          ))}
          <XAxis
            dataKey="date"
            tick={{ fill: "#909097", fontSize: 10 }}
            axisLine={{ stroke: "#2e3447" }}
            tickLine={false}
            interval={tickInterval}
          />
          <YAxis
            tick={{ fill: "#909097", fontSize: 10 }}
            axisLine={{ stroke: "#2e3447" }}
            tickLine={false}
            domain={["auto", "auto"]}
            width={40}
          />
          <Tooltip contentStyle={{ background: "#1a1f2e", border: "1px solid #2e3447", fontSize: 11 }} />
          <Line type="monotone" dataKey="index" stroke="#95d3ba" dot={false} strokeWidth={1.5} name="등가중지수" />
          <Line type="monotone" dataKey="ma20" stroke="#e0a458" dot={false} strokeWidth={1} strokeDasharray="4 3" name="20일선" />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="text-[10px] text-on-surface-variant/60 mt-1">
        ※ 전 종목 등가중 지수(자작·시장 폭 지표). 코스피 아님 — 대형주 강세 국면과 갈릴 수 있음.
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Wire into page** — `src/app/stocks/sepa/page.tsx` 수정:

(a) 상단 import 추가(기존 import 들 근처):
```tsx
import { MarketRegimeChart } from "./MarketRegimeChart";
import { type MarketRegime } from "./marketRegime";
```
(b) 데이터 로드부(다른 `readJson` 호출들 근처)에 추가:
```tsx
const regime = await readJson<MarketRegime>("market-regime.json");
```
(c) 반환 JSX 에서 **가장 첫 자식**(기존 "1단계 트렌드 템플릿" `<section>` 바로 앞)에 삽입 — 기존 카드 스타일 준수:
```tsx
{regime && (
  <section className="bg-surface-container-low rounded-xl ghost-border p-4">
    <h3 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
      <span className="material-symbols-outlined text-base text-primary">insights</span>
      시장 국면 — 등가중 지수 20일선
    </h3>
    <MarketRegimeChart data={regime} />
  </section>
)}
```
(page.tsx 를 읽어 반환 블록의 최상단 위치를 정확히 확인 후 삽입할 것. 래핑 엘리먼트가 fragment/`<div>` 든 그 첫 자식이 되게.)

- [ ] **Step 3: 타입·린트·빌드 검증**

Run: `npx tsc --noEmit` (또는 `npm run lint` 존재 시 병행)
Expected: 타입 에러 없음.

Run: `npm run build` (Next 프로덕션 빌드)
Expected: `/stocks/sepa` 포함 빌드 성공(서버 컴포넌트가 market-regime.json 읽고 클라이언트 차트 SSR 통과). 에러 시 수정.

- [ ] **Step 4: 전체 테스트 재확인**

Run: `npx vitest run src/app/stocks/sepa/`
Expected: 기존 테스트 + marketRegime 5개 전부 pass.

- [ ] **Step 5: Commit**
```bash
git add src/app/stocks/sepa/MarketRegimeChart.tsx src/app/stocks/sepa/page.tsx
git commit -m "feat(sepa-regime): MarketRegimeChart + /stocks/sepa 최상단 국면 섹션"
```

---

## Self-Review

**1. Spec coverage**
- 데이터 스크립트(등가중+20MA+국면, 250일, 100정규화, build_ew_index 재사용) → Task1. ✅
- 하락구간 음영(downtrendSegments + ReferenceArea) → Task2(헬퍼)+Task3(렌더). ✅
- 두 라인 + 상태 배지 + 각주 → Task3. ✅
- 페이지 최상단 섹션·readJson 재사용·null시 생략 → Task3. ✅
- 국면 정의 동일 잣대·정션 금지·다크테마 → Global Constraints + 각 태스크. ✅
- 테스트(헬퍼 vitest·스크립트 스모크·next build) → Task2/1/3. ✅

**2. Placeholder scan** — 세 파일 전부 완전한 코드. JSON 은 Task1 실행 산출. page 삽입은 정확한 위치를 읽어 확인(코드 제공).

**3. Type consistency**
- `MarketRegime`·`RegimePoint` Task2 정의 ↔ Task3(props)·page(readJson<MarketRegime>) 동일. ✅
- `downtrendSegments(series)->{x1,x2}[]` Task2 ↔ Task3(segs.map). ✅
- JSON 키(current.uptrend·series[].up/index/ma20/date) Task1 산출 ↔ Task2 타입 ↔ Task3 소비 일치. ✅
- recharts `ReferenceArea`·`ComposedChart` 사용(빌드에서 import 해상도 확인; 미해상 시 LineChart+동일 프리미티브로 대체).

> 통합 위험(빌드서 확인): recharts v3 SSR·ReferenceArea x축 매칭(dataKey="date" 문자열 x1/x2 일치), page 삽입 위치.

---

## Execution Handoff

순서: Task1(데이터, 스모크로 현재=하락추세 확인) → Task2(헬퍼 TDD) → Task3(차트+페이지, next build). Task3 의 빌드 통과가 최종 산출.

import fs from "fs/promises";
import path from "path";
import { TrendTemplateTable, type TrendTemplateRow } from "./TrendTemplateTable";

interface MarketStatus {
  passed: boolean;
  value: string;
  detail: string;
  kospi_close: number | null;
}

interface TrendCandidate {
  code: string;
  name: string;
  market: string;
  market_cap_eok: number;
  current_price: number;
  rs: number | null;
  return_window_pct: number | null;
  passed_count: number;
  all_pass: boolean;
  extras: {
    sma50: number | null;
    sma150: number | null;
    sma200: number | null;
    high_52w: number | null;
    low_52w: number | null;
    sma200_rising_5m_preferred: boolean | null;
  };
}

interface TrendData {
  generated_at: string;
  asof: string;
  scanned_count: number;
  evaluated_count: number;
  all_pass_count: number;
  rs_universe_n: number;
  rs_min: number;
  market_status: MarketStatus;
  candidates: TrendCandidate[];
}

interface CScoredCandidate {
  code: string;
  c_score: number | null;
  c_score_tier: string | null;
  c_gate_pass: boolean;
  c_detailed: {
    yoy_pct: number | null;
    sales_yoy_pct: number | null;
    eps_accel_3q: boolean;
    sales_accel_3q: boolean;
    never_sell: boolean;
    eps_accel_quality: string | null;
    latest_quarter: string | null;
  };
}

interface CScoredData {
  generated_at: string;
  asof: string;
  evaluated_count: number;
  c_gate_pass_count: number;
  tier_distribution: Record<string, number>;
  candidates: CScoredCandidate[];
}

interface Code33Candidate {
  code: string;
  code33_pass: boolean;
  listed_shares: number | null;
  latest_net_margin_pct: number | null;
  net_margin_accel_3q: boolean;
}

interface Code33Data {
  generated_at: string;
  asof: string;
  input_count: number;
  eligible_count: number;
  code33_pass_count: number;
  passes: Code33Candidate[];
  all_evaluated: Code33Candidate[];
}

async function readJson<T>(filename: string): Promise<T | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", filename);
    return JSON.parse(await fs.readFile(filePath, "utf-8")) as T;
  } catch {
    return null;
  }
}

export default async function TrendTemplatePage() {
  const [trend, cscored, code33] = await Promise.all([
    readJson<TrendData>("trend-template-candidates.json"),
    readJson<CScoredData>("trend-template-c-scored.json"),
    readJson<Code33Data>("trend-template-code33.json"),
  ]);

  if (!trend) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            트렌드 템플레이트
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">
            데이터가 아직 생성되지 않았습니다. <code className="text-xs">/trend-template</code> 스킬을 한 번 돌려주세요.
          </p>
        </header>
      </div>
    );
  }

  const cMap = new Map<string, CScoredCandidate>();
  if (cscored) {
    for (const c of cscored.candidates) cMap.set(c.code, c);
  }
  const code33Map = new Map<string, Code33Candidate>();
  const code33EvalSet = new Set<string>();
  if (code33) {
    for (const c of code33.all_evaluated) {
      code33Map.set(c.code, c);
      code33EvalSet.add(c.code);
    }
  }

  // 트렌드 8조건 통과 종목만 (191)
  const passed = trend.candidates.filter((c) => c.all_pass);

  const rows: TrendTemplateRow[] = passed.map((t) => {
    const c = cMap.get(t.code);
    const e = code33Map.get(t.code);
    const high = t.extras?.high_52w;
    const pctFromHigh =
      high && high > 0 ? (t.current_price - high) / high * 100 : null;
    return {
      code: t.code,
      name: t.name,
      market: t.market,
      market_cap_eok: t.market_cap_eok,
      current_price: t.current_price,
      rs: t.rs,
      return_window_pct: t.return_window_pct,
      sma200_rising_5m: t.extras?.sma200_rising_5m_preferred ?? false,
      high_52w: high ?? null,
      pct_from_52w_high: pctFromHigh,
      c_score: c?.c_score ?? null,
      c_score_tier: c?.c_score_tier ?? null,
      c_gate_pass: c?.c_gate_pass ?? false,
      eps_yoy_pct: c?.c_detailed?.yoy_pct ?? null,
      sales_yoy_pct: c?.c_detailed?.sales_yoy_pct ?? null,
      eps_accel_3q: c?.c_detailed?.eps_accel_3q ?? false,
      sales_accel_3q: c?.c_detailed?.sales_accel_3q ?? false,
      never_sell: c?.c_detailed?.never_sell ?? false,
      eps_accel_quality: c?.c_detailed?.eps_accel_quality ?? null,
      latest_quarter: c?.c_detailed?.latest_quarter ?? null,
      evaluated_for_code33: code33EvalSet.has(t.code),
      code33_pass: e?.code33_pass ?? false,
      net_margin_pct: e?.latest_net_margin_pct ?? null,
      net_margin_accel_3q: e?.net_margin_accel_3q ?? false,
      listed_shares: e?.listed_shares ?? null,
    };
  });

  const code33Count = rows.filter((r) => r.code33_pass).length;
  const gateCount = rows.filter((r) => r.c_gate_pass).length;
  const cEvaluated = rows.filter((r) => r.c_score !== null).length;

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          트렌드 템플레이트
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          Minervini 트렌드 템플레이트 8조건 통과 → CAN SLIM C 원칙 점수 부여 → 코드 33 (EPS·매출·순이익률 3분기 단조 가속) 까지 한눈에.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          1단계 정의:{" "}
          <code className="text-xs">research/oneil-model-book/trend_template.md</code>
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          기준일: {trend.asof} · 평가 {trend.evaluated_count.toLocaleString()}종목 · 트렌드 통과{" "}
          {rows.length}종목 · RS 모집단 {trend.rs_universe_n.toLocaleString()}
        </p>
      </header>

      {/* 시장 추세 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">show_chart</span>
          KOSPI 추세 (참고)
          <span
            className="text-[11px] font-medium px-2 py-0.5 rounded ml-1"
            style={{
              backgroundColor: trend.market_status.passed
                ? "rgba(16,185,129,0.18)"
                : "rgba(255,180,171,0.18)",
              color: trend.market_status.passed ? "#10b981" : "#ffb4ab",
            }}
          >
            {trend.market_status.value}
          </span>
        </h3>
        <p className="text-[11px] text-on-surface-variant/70 leading-relaxed">
          {trend.market_status.detail}
        </p>
      </section>

      {/* 단계별 요약 카드 */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-surface-container-low rounded-lg p-4 ghost-border">
          <p className="text-[11px] text-on-surface-variant/70 mb-1 flex items-center gap-1">
            <span className="material-symbols-outlined text-sm">filter_1</span> 트렌드 8조건 통과
          </p>
          <p className="text-2xl font-serif font-bold text-on-surface">
            {rows.length}
            <span className="text-xs text-on-surface-variant/50 ml-1.5">/ {trend.evaluated_count.toLocaleString()}</span>
          </p>
          <p className="text-[10px] text-on-surface-variant/50 mt-0.5">추세·신고가 근접·RS≥70</p>
        </div>
        <div className="bg-surface-container-low rounded-lg p-4 ghost-border">
          <p className="text-[11px] text-on-surface-variant/70 mb-1 flex items-center gap-1">
            <span className="material-symbols-outlined text-sm">filter_2</span> C 게이트 통과
          </p>
          <p className="text-2xl font-serif font-bold" style={{ color: "#34d399" }}>
            {gateCount}
            <span className="text-xs text-on-surface-variant/50 ml-1.5">/ {cEvaluated}</span>
          </p>
          <p className="text-[10px] text-on-surface-variant/50 mt-0.5">EPS YoY≥25% AND 매출 동반 AND 가속</p>
        </div>
        <div className="bg-surface-container-low rounded-lg p-4 ghost-border">
          <p className="text-[11px] text-on-surface-variant/70 mb-1 flex items-center gap-1">
            <span className="material-symbols-outlined text-sm">filter_3</span> 코드 33 통과 (황금 후보)
          </p>
          <p className="text-2xl font-serif font-bold" style={{ color: "#e9c176" }}>
            {code33Count}
            <span className="text-xs text-on-surface-variant/50 ml-1.5">/ {code33?.eligible_count ?? "?"}</span>
          </p>
          <p className="text-[10px] text-on-surface-variant/50 mt-0.5">EPS·매출·순이익률 모두 3분기 단조 가속</p>
        </div>
      </section>

      {/* 컬럼·배지 설명 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 text-xs space-y-2">
        <h3 className="text-sm font-serif font-bold text-on-surface flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-base text-primary">help_outline</span>
          용어·배지
        </h3>
        <p className="text-on-surface-variant">
          <strong className="text-on-surface">RS</strong>: 전 종목(2,569) 대비 252거래일 수익률 백분위 (1~99). 트렌드 8 통과 기준 ≥ 70.
        </p>
        <p className="text-on-surface-variant">
          <strong className="text-on-surface">C 점수</strong>: 분기 EPS YoY·가속·매출 3축 종합 (0~100+). 등급 배지(🅐🅑🅒🅓) 와 게이트 통과 여부 별도.
        </p>
        <p className="text-on-surface-variant">
          <strong className="text-on-surface">EPS / 매출 / 순이익률 YoY</strong>: 최신 분기 vs 전년 동기. 단조 3분기 가속(✓) 표시.
        </p>
        <p style={{ color: "#e9c176" }}>
          <strong>★ 코드 33</strong>: EPS·매출·순이익률 셋 다 3분기 단조 가속 — 추세 + 펀더멘털 + 수익성 가속 모두 만족하는 황금 후보.
        </p>
        <p className="text-emerald-300">
          <strong>⛔ 절대 매도 금지</strong>: EPS+매출 둘 다 3분기 가속 (O&apos;Neil 책 기준 #4).
        </p>
        <p style={{ color: "#a8b5d0" }}>
          <strong>★ 5M↑</strong>: 200일선이 5개월(약 110거래일) 전보다 위 — Minervini 권장 우수 조건.
        </p>
        <p className="text-on-surface-variant/70 mt-2 pt-2 border-t border-outline-variant/15">
          <span className="material-symbols-outlined text-[13px] align-middle mr-0.5">info</span>
          C 게이트 통과 종목은 <strong className="text-on-surface-variant">KIS 통합시세 (KRX 정규장 + NXT 애프터 종가)</strong> 기준이고, 그 외 종목은 KRX 정규장 종가 기준입니다.
        </p>
      </section>

      {/* 메인 표 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">table_view</span>
          트렌드 8조건 통과 — {rows.length}종목
        </h3>
        <TrendTemplateTable rows={rows} />
      </section>
    </div>
  );
}

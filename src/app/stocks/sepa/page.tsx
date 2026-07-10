import fs from "fs/promises";
import path from "path";
import { SepaPatternTable } from "./SepaPatternTable";
import { PositionSizeCalculator } from "./PositionSizeCalculator";
import { PATTERNS, buildSection, type PatternConfig, type RawCandidate } from "./sepaPatterns";
import { computeTrendByCode, type TierHistory } from "./tierHistory";
import { MarketRegimeChart } from "./MarketRegimeChart";
import { type MarketRegime } from "./marketRegime";
import { BuyRecommendationSection, type BuyRecFile } from "./BuyRecommendationSection";

interface MarketStatus {
  passed: boolean;
  value: string;
  detail: string;
}
interface TrendData {
  asof: string;
  evaluated_count: number;
  all_pass_count: number;
  market_status: MarketStatus;
}
interface CandidateFile {
  asof?: string;
  candidates?: RawCandidate[];
}
interface ExclusionFile {
  exclusions?: { code: string; name?: string; reason?: string }[];
}

async function readJson<T>(filename: string): Promise<T | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", filename);
    return JSON.parse(await fs.readFile(filePath, "utf-8")) as T;
  } catch {
    return null;
  }
}

function PatternSection({
  config,
  data,
  trendByCode,
  excludeCodes,
}: {
  config: PatternConfig;
  data: CandidateFile | null;
  trendByCode?: Record<string, string>;
  excludeCodes: ReadonlySet<string>;
}) {
  if (!data) {
    return (
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">pattern</span>
          {config.label}
        </h3>
        <p className="text-sm text-on-surface-variant/60 bg-surface-container-low rounded-xl ghost-border p-4">
          데이터가 아직 생성되지 않았습니다. (산출 파일 <code className="text-xs">{config.file}</code> 없음)
        </p>
      </section>
    );
  }
  const { rows, counts } = buildSection(data.candidates ?? [], config, undefined, excludeCodes);
  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">pattern</span>
        {config.label}
        <span className="text-xs font-normal text-on-surface-variant/60 ml-1">
          🔴 {counts.breakout} · 🟢 {counts.actionable} · 🟡 {counts.watch}
        </span>
      </h3>
      <SepaPatternTable rows={rows} columns={config.columns} trendByCode={trendByCode} />
    </section>
  );
}

export default async function SepaPage() {
  const [trend, vcp, ppTrend, ppAll, threeC] = await Promise.all([
    readJson<TrendData>("sepa-trend-candidates.json"),
    readJson<CandidateFile>(PATTERNS.vcp.file),
    readJson<CandidateFile>(PATTERNS.powerplayTrend.file),
    readJson<CandidateFile>(PATTERNS.powerplayAll.file),
    readJson<CandidateFile>(PATTERNS.threeC.file),
  ]);

  const exclusionFile = await readJson<ExclusionFile>("sepa-exclusions.json");
  // 상장폐지 예정 등 수동 제외 종목(전 패턴 공통 필터).
  const excludeCodes = new Set((exclusionFile?.exclusions ?? []).map((e) => e.code));

  const regime = await readJson<MarketRegime>("market-regime.json");
  const buyRecs = await readJson<BuyRecFile>("sepa-buy-recommendations.json");

  const history = await readJson<TierHistory>("sepa-tier-history.json");
  const trends = history
    ? {
        vcp: computeTrendByCode(history, "vcp", PATTERNS.vcp),
        powerplayTrend: computeTrendByCode(history, "powerplayTrend", PATTERNS.powerplayTrend),
        powerplayAll: computeTrendByCode(history, "powerplayAll", PATTERNS.powerplayAll),
        threeC: computeTrendByCode(history, "threeC", PATTERNS.threeC),
      }
    : null;

  if (!trend) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">SEPA 셋업</h2>
          <p className="text-sm text-on-surface-variant mt-2">
            데이터가 아직 생성되지 않았습니다. <code className="text-xs">find-trend-template</code> 스킬을 먼저 돌려주세요.
          </p>
        </header>
      </div>
    );
  }

  const asofs = Array.from(
    new Set([trend.asof, vcp?.asof, ppTrend?.asof, ppAll?.asof, threeC?.asof].filter(Boolean))
  );

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">SEPA 셋업</h2>
        <p className="text-base text-on-surface-variant mt-2">
          미너비니 SEPA — 트렌드 템플릿 1단계 통과 종목에 대해 VCP·파워 플레이 등 패턴의 돌파·진입임박·예의주시를 한눈에.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          기준일: {asofs.join(" · ")} · 트렌드 통과 {trend.all_pass_count.toLocaleString()}종목 / 평가{" "}
          {trend.evaluated_count.toLocaleString()}
        </p>
      </header>

      {regime && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-4">
          <h3 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
            <span className="material-symbols-outlined text-base text-primary">insights</span>
            등가중 지수 · 20일선 (시장 폭)
          </h3>
          <MarketRegimeChart data={regime} />
        </section>
      )}

      {/* 1단계 트렌드 요약 + KOSPI 추세 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">filter_1</span>
          1단계 트렌드 템플릿 통과 — {trend.all_pass_count.toLocaleString()}종목
          <span
            className="text-[11px] font-medium px-2 py-0.5 rounded ml-1"
            style={{
              backgroundColor: trend.market_status.passed ? "rgba(16,185,129,0.18)" : "rgba(255,180,171,0.18)",
              color: trend.market_status.passed ? "#10b981" : "#ffb4ab",
            }}
          >
            KOSPI {trend.market_status.value}
          </span>
        </h3>
        <p className="text-[11px] text-on-surface-variant/70 leading-relaxed">{trend.market_status.detail}</p>
      </section>

      <BuyRecommendationSection data={buyRecs} />

      <PatternSection config={PATTERNS.vcp} data={vcp} trendByCode={trends?.vcp} excludeCodes={excludeCodes} />
      <PatternSection config={PATTERNS.powerplayTrend} data={ppTrend} trendByCode={trends?.powerplayTrend} excludeCodes={excludeCodes} />
      <PatternSection config={PATTERNS.powerplayAll} data={ppAll} trendByCode={trends?.powerplayAll} excludeCodes={excludeCodes} />
      <PatternSection config={PATTERNS.threeC} data={threeC} trendByCode={trends?.threeC} excludeCodes={excludeCodes} />

      {/* 포지션 크기 계산기 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 space-y-3">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">calculate</span>
          포지션 크기 계산기 (미너비니 기준)
        </h3>
        <ul className="text-xs text-on-surface-variant/80 space-y-0.5 list-disc list-inside">
          <li>한 매매 위험은 총 자본의 1.25~2.50%, 최대 손절 10%, 손실 평균 5~6% 이내.</li>
          <li>한 종목 비중 50% 초과 금지 · 최고 종목엔 총포지션의 20~25%.</li>
          <li>최대 종목 수 10~12개.</li>
        </ul>
        <PositionSizeCalculator />
      </section>

      {/* 용어·배지 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 text-xs space-y-4">
        <h3 className="text-sm font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">help_outline</span>
          상태·지표
        </h3>

        {/* 그룹 1: 상태 배지 */}
        <div>
          <p className="text-[11px] font-bold text-on-surface-variant/60 mb-1.5">
            🚦 상태 배지 <span className="font-normal text-on-surface-variant/50">· 승격 순서: 예의주시 → 진입임박 → 돌파</span>
          </p>
          <ul className="space-y-1 text-on-surface-variant">
            <li><strong style={{ color: "#ffb4ab" }}>🔴 돌파</strong> — 패턴 확정 + 당일 피벗 첫 돌파(거래량 터짐). 지금 뚫는 중.</li>
            <li><strong style={{ color: "#34d399" }}>🟢 진입임박</strong> — 패턴 확정 + 피벗 코앞(~5%)·거래량 마름 = <strong className="text-on-surface">돌파 초읽기</strong>(매수 준비 구간).</li>
            <li><strong style={{ color: "#e9c176" }}>🟡 예의주시</strong> — 형성 중이거나 피벗 12% 이내로 접근 중. 관심종목, 바로 매수는 아님.</li>
          </ul>
        </div>

        {/* 그룹 2: 주요 지표 */}
        <div className="border-t border-outline-variant/10 pt-3">
          <p className="text-[11px] font-bold text-on-surface-variant/60 mb-1.5">📊 주요 지표</p>
          <dl className="space-y-1.5 text-on-surface-variant">
            <div className="flex gap-2"><dt className="font-semibold text-on-surface w-20 shrink-0">피벗</dt><dd className="flex-1">최소저항선(돌파 기준가).</dd></div>
            <div className="flex gap-2"><dt className="font-semibold text-on-surface w-20 shrink-0">피벗대비</dt><dd className="flex-1">(현재가−피벗)/피벗 · 음수=아래, 양수=위 · <strong className="text-on-surface">0에 가까울수록 진입 적기</strong>.</dd></div>
            <div className="flex gap-2">
              <dt className="font-semibold text-on-surface w-20 shrink-0">코일</dt>
              <dd className="flex-1">
                돌파 직전 좁고 조용하게 응축되는 최종 수축 구간.
                <span className="block text-on-surface-variant/80 mt-0.5">├ <strong className="text-on-surface/90">코일길이</strong> : 그 구간 일수 — 짧을수록 좋음(통상 3~5일)</span>
                <span className="block text-on-surface-variant/80">└ <strong className="text-on-surface/90">코일마름</strong> : 코일 거래량 ÷ 50일 평균 — 낮을수록 좋음(검출 ≤0.95)</span>
              </dd>
            </div>
            <div className="flex gap-2"><dt className="font-semibold text-on-surface w-20 shrink-0">타이트</dt><dd className="flex-1">최근 ~10일 일중 변동폭((고−저)/종가) 평균(%) — 작을수록 변동성 압축.</dd></div>
            <div className="flex gap-2"><dt className="font-semibold text-on-surface w-20 shrink-0">베이스깊이</dt><dd className="flex-1">고점 대비 최대 조정폭(%) — 통상 15~30%.</dd></div>
          </dl>
        </div>

        {/* 그룹 3: 패턴별 확정 기준 */}
        <div className="border-t border-outline-variant/10 pt-3">
          <p className="text-[11px] font-bold text-on-surface-variant/60 mb-1.5">
            🎯 패턴별 확정 기준 <span className="font-normal text-on-surface-variant/50">· 모두 충족해야 🔴/🟢, 하나라도 미달이면 🟡·숨김</span>
          </p>
          <ul className="space-y-1 text-on-surface-variant">
            <li><strong className="text-on-surface">VCP</strong> — 수축 2~6회 · 갈수록 얕아짐(순 수렴) · 최종 타이트 코일(종가 변동폭 ≤12% <em>그리고</em> 거래량 ≤50일평균×0.95)</li>
            <li><strong className="text-on-surface">파워 플레이</strong> — 깃대 14주(≤70일) 내 <strong>+90%↑</strong> 급등 · 깃발 8~30일 · 깃발 깊이 ≤20%</li>
            <li><strong className="text-on-surface">3C</strong>(컵 완성 치트) — 컵 깊이 12~50% · 컵 길이 ≥17일 · 선반 2~25일·깊이 ≤12%·위치 25~90% · 거래량 마름</li>
          </ul>
        </div>

        <p className="text-on-surface-variant/55 pt-2 border-t border-outline-variant/15">
          각 섹션은 해당 패턴을 충족(돌파·진입임박)하거나 근접한(예의주시) 종목만 노출하며, 실패·원거리 종목은 숨깁니다. 데이터는 읽기 전용.
        </p>
      </section>
    </div>
  );
}

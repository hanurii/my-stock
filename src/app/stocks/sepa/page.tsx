import fs from "fs/promises";
import path from "path";
import { SepaPatternTable } from "./SepaPatternTable";
import { PATTERNS, buildSection, type PatternConfig, type RawCandidate } from "./sepaPatterns";

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
}: {
  config: PatternConfig;
  data: CandidateFile | null;
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
  const { rows, counts } = buildSection(data.candidates ?? [], config);
  return (
    <section>
      <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">pattern</span>
        {config.label}
        <span className="text-xs font-normal text-on-surface-variant/60 ml-1">
          🔴 {counts.breakout} · 🟢 {counts.actionable} · 🟡 {counts.watch}
        </span>
      </h3>
      <SepaPatternTable rows={rows} columns={config.columns} />
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

      <PatternSection config={PATTERNS.vcp} data={vcp} />
      <PatternSection config={PATTERNS.powerplayTrend} data={ppTrend} />
      <PatternSection config={PATTERNS.powerplayAll} data={ppAll} />
      <PatternSection config={PATTERNS.threeC} data={threeC} />

      {/* 용어·배지 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 text-xs space-y-2">
        <h3 className="text-sm font-serif font-bold text-on-surface flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-base text-primary">help_outline</span>
          상태·지표
        </h3>
        <p className="text-on-surface-variant">
          <strong style={{ color: "#ffb4ab" }}>🔴 돌파</strong>: 패턴 확정 + 당일 피벗 첫돌파(거래량 터짐) ·{" "}
          <strong style={{ color: "#34d399" }}>🟢 진입임박</strong>: 패턴 확정 + 피벗 코앞(약 5% 이내)·거래량 마름 ·{" "}
          <strong style={{ color: "#e9c176" }}>🟡 예의주시</strong>: 형성 중 + 피벗 12% 이내(아직 매수엔 이름).
        </p>
        <p className="text-on-surface-variant/80 bg-surface-container/30 rounded-lg px-3 py-2 leading-relaxed">
          <strong className="text-on-surface">진입임박 vs 예의주시</strong> — 둘 다 &ldquo;피벗 아래&rdquo;지만 <strong>무르익은 정도</strong>가 다릅니다.{" "}
          <strong style={{ color: "#34d399" }}>🟢 진입임박</strong>은 패턴이 <em>확정</em>됐고 피벗 바로 아래(약 5% 이내)에서 거래량까지 말라 <strong className="text-on-surface">돌파 초읽기</strong> 상태 — 지금이 매수 준비 구간이고, 피벗을 뚫으면 바로 진입합니다.{" "}
          <strong style={{ color: "#e9c176" }}>🟡 예의주시</strong>는 아직 이른 단계로, ① 패턴이 떴어도 베이스가 더 만들어지는 중(형성)이거나 ② 아직 미확정이지만 피벗 12% 이내로 다가오는 중 — <strong className="text-on-surface">관심종목에 담아 지켜볼 후보</strong>(바로 매수 아님).{" "}
          한 종목은 보통 <strong style={{ color: "#e9c176" }}>예의주시</strong> → (무르익으면) <strong style={{ color: "#34d399" }}>진입임박</strong> → <strong style={{ color: "#ffb4ab" }}>돌파</strong> 순으로 승격됩니다.
        </p>
        <p className="text-on-surface-variant">
          <strong className="text-on-surface">피벗</strong>: 최소저항선(돌파 기준가). <strong className="text-on-surface">피벗대비</strong>: (현재가−피벗)/피벗 — 음수=피벗 아래(미달), 양수=피벗 위(돌파). 0에 가까울수록 진입 적기.
        </p>
        <p className="text-on-surface-variant">
          <strong className="text-on-surface">코일</strong>: 돌파 직전 주가가 좁고 조용하게 응축되는 마지막 구간(폭발 직전 최종 타이트 수축).{" "}
          <strong className="text-on-surface">코일길이</strong>: 그 구간이 며칠짜리인지(거래일) — 짧을수록(미너비니 통상 3~5일) 응축이 잘 된 셋업.{" "}
          <strong className="text-on-surface">코일마름</strong>: 코일 평균 거래량 ÷ 50일 평균 거래량 — 1보다 작을수록 거래량 고갈(예: 0.3=평소의 30%), 검출기는 0.95 이하만 코일로 인정. 낮을수록 좋은 신호.
        </p>
        <p className="text-on-surface-variant">
          <strong className="text-on-surface">타이트</strong>: 최근 약 10거래일 일중 변동폭((고−저)/종가) 평균(%) — 작을수록 가격이 조밀하게 붙어 움직임(변동성 압축). <strong className="text-on-surface">베이스깊이</strong>: 베이스가 고점 대비 가장 깊게 조정된 폭(%) — 미너비니 통상 15~30%.
        </p>
        <p className="text-on-surface-variant">
          <strong className="text-on-surface">VCP</strong>(변동성 수축): 수축 횟수 + 위 코일·타이트 지표. <strong className="text-on-surface">파워 플레이</strong>(하이 타이트 플래그): 깃대 상승률·일수 + 깃발 깊이.
        </p>
        <p className="text-on-surface-variant/60 mt-1 pt-2 border-t border-outline-variant/15">
          각 섹션은 그 패턴을 만족(돌파·진입임박)하거나 곧 만족할(예의주시) 종목만 노출하며, 실패·원거리 종목은 숨깁니다. 데이터는 읽기 전용(별도 파이프라인이 생성).
        </p>
      </section>
    </div>
  );
}

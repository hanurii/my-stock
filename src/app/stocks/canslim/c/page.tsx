import fs from "fs/promises";
import path from "path";
import { CanslimTable, type CanslimCandidate } from "../CanslimTable";
import { EPS_ACCEL_QUALITY_META } from "../lib/epsAccel";
import { passesCGate, USER_C_THRESHOLD } from "../lib/cFilter";

interface MarketStatus {
  kospi_trend_verdict: string;
  passed: boolean;
  value: string;
  detail: string;
  kospi_close: number | null;
}

interface CanslimData {
  generated_at: string;
  scanned_count: number;
  evaluated_count: number;
  market_status: MarketStatus;
  candidates: CanslimCandidate[];
}

async function getData(): Promise<CanslimData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export default async function CanslimCPage() {
  const data = await getData();

  if (!data || data.candidates.length === 0) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            CAN SLIM 발굴 — C: 현재 분기 EPS
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">데이터가 아직 생성되지 않았습니다.</p>
        </header>
      </div>
    );
  }

  // 평가된 universe 내 시총 순위 부여
  const rankByCode = new Map<string, number>();
  [...data.candidates]
    .sort((a, b) => b.market_cap_eok - a.market_cap_eok)
    .forEach((c, idx) => rankByCode.set(c.code, idx + 1));

  const main = data.candidates.filter((c) => passesCGate(c.criteria.C));

  const tierCounts = (() => {
    const counts: Record<string, number> = { 강력: 0, 좋음: 0, 중립: 0, 약함: 0 };
    for (const c of main) {
      const t = c.c_score_tier ?? (c.c_score !== undefined ? (c.c_score >= 80 ? "강력" : c.c_score >= 70 ? "좋음" : c.c_score >= 50 ? "중립" : "약함") : null);
      if (t) counts[t]++;
    }
    return counts;
  })();
  const hasScores = main.some((c) => c.c_score !== undefined);

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — C: 현재 분기 EPS
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 첫 글자 &lsquo;C&rsquo; — 분기 주당순이익이 전년 동기 대비 얼마나 크게 늘었는가.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          노출 조건: 분기 EPS YoY <strong className="text-on-surface-variant">+{USER_C_THRESHOLD}% 이상</strong> AND <strong className="text-on-surface-variant">매출 동반</strong>(분기 매출 +25% OR 3분기 매출 가속) AND EPS 가속 중.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일: {data.generated_at} · 평가 {data.evaluated_count.toLocaleString()}종목 · 노출 {main.length}종목
        </p>
      </header>

      {/* C 점수 4축 안내 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-1 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">scoreboard</span>
          C 점수 — 4축 100점 만점
          <span className="text-[11px] text-on-surface-variant/60 font-normal ml-1">
            · 필터 통과 종목 사이의 우선순위
          </span>
        </h3>
        <p className="text-[11px] text-on-surface-variant/60 mb-3">
          오닐 책 무게중심을 반영해 EPS 자체 평가에 74점을 할당. 매출 검증과 경영진이 나머지 26점.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          {[
            { axis: "① 분기 EPS YoY 폭", max: 39, hint: "+25% 부터 시작, +100%↑ 만점" },
            { axis: "② EPS 가속 폭", max: 35, hint: "▲14 · ▲▲26 · 🔥31 + 3분기 +4" },
            { axis: "③ 매출 가속", max: 19, hint: "+25% 10 / 3분기 +6 / ⛔ +3" },
            { axis: "④ 경영진 품질", max: 7, hint: "워치리스트 우수 7 · 전문 4" },
          ].map((a) => (
            <div key={a.axis} className="bg-surface-container/50 rounded-lg p-2.5">
              <p className="text-on-surface-variant/60 mb-0.5">{a.axis}</p>
              <p className="text-on-surface font-medium">{a.max}점 만점</p>
              <p className="text-[10px] text-on-surface-variant/50 mt-0.5">{a.hint}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
          {[
            { tier: "🅐 강력", range: "80+", color: "#10b981" },
            { tier: "🅑 좋음", range: "70~79", color: "#34d399" },
            { tier: "🅒 중립", range: "50~69", color: "#e9c176" },
            { tier: "🅓 약함", range: "<50", color: "#ffb4ab" },
          ].map((t) => (
            <span key={t.tier} className="inline-flex items-center gap-1.5 px-2 py-1 rounded" style={{ backgroundColor: `${t.color}20`, color: t.color }}>
              <span className="font-bold">{t.tier}</span>
              <span className="opacity-80">{t.range}</span>
            </span>
          ))}
        </div>
      </section>

      {/* EPS 가속도 단계 (O'Neil 책 기준 #3 — 가장 중요한 원칙 정량화) */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4">
        <h3 className="text-sm font-serif font-bold text-on-surface mb-1 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">bolt</span>
          EPS 가속도 단계
          <span className="text-[11px] text-on-surface-variant/60 font-normal ml-1">
            · O&apos;Neil 책 기준 #3 — &quot;직전 분기 대비 가속 폭이 가장 중요&quot;
          </span>
        </h3>
        <p className="text-[11px] text-on-surface-variant/60 mb-3">
          가속 폭 Δ = (이번 분기 EPS YoY %) − (직전 분기 EPS YoY %). YoY 는 절댓값 분모 공식이라 적자→흑자 턴어라운드도 같은 척도로 mild/strong/explosive 중 하나에 분류된다.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
          {(["mild", "strong", "explosive"] as const).map((q) => {
            const meta = EPS_ACCEL_QUALITY_META[q];
            const ranges: Record<string, string> = {
              mild: "0 < Δ ≤ 25%p",
              strong: "25 < Δ ≤ 100%p",
              explosive: "Δ > 100%p",
            };
            return (
              <div
                key={q}
                className="rounded-lg p-2.5 flex flex-col gap-0.5"
                style={{ backgroundColor: meta.bg }}
              >
                <p className={`flex items-center gap-1 ${meta.weight}`} style={{ color: meta.color }}>
                  <span>{meta.icon}</span>
                  <span>{meta.label}</span>
                </p>
                <p className="text-on-surface-variant/70 text-[11px]">{ranges[q]}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* 필터 설명 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-4 text-xs space-y-2">
        <h3 className="text-sm font-serif font-bold text-on-surface flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-base text-primary">filter_alt</span>
          필터 설명
        </h3>
        <p className="text-on-surface-variant"><strong className="text-on-surface">매출 +25% 이상</strong>: 이번 분기 매출 YoY ≥ 25% 종목 (이미 페이지 노출 조건의 일부, 토글로 좁히기 가능).</p>
        <p className="text-on-surface-variant"><strong className="text-on-surface">매출 3분기 가속</strong>: 최근 3분기 매출 YoY 성장률이 단조 증가 (이미 페이지 노출 조건의 일부).</p>
        <p className="text-on-surface-variant"><strong className="text-on-surface">EPS 가속 중</strong>: 가속 폭이 mild(0~25%p) / strong(25~100%p) / explosive(100%p+) 중 하나인 종목 (O&apos;Neil 책 기준 #3 가장 중요).</p>
        <p className="text-on-surface-variant"><strong className="text-on-surface">12M EPS 신고점</strong>: 최근 12개월 4개 분기 EPS가 그 이전 모든 분기의 신고점에 근접·돌파.</p>
        <p className="text-emerald-300"><strong>⛔ 절대 매도 금지</strong>: 매출+EPS 모두 최근 3분기 가속 — O&apos;Neil 책 기준 #4 (배지로 자동 부여, 필터 X).</p>
      </section>

      {/* 메인 테이블 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">trending_up</span>
          분기 EPS YoY +{USER_C_THRESHOLD}% 이상 ({main.length}종목)
        </h3>
        {hasScores && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
            {([
              { key: "강력", color: "#10b981", mark: "🅐" },
              { key: "좋음", color: "#34d399", mark: "🅑" },
              { key: "중립", color: "#e9c176", mark: "🅒" },
              { key: "약함", color: "#ffb4ab", mark: "🅓" },
            ] as const).map((t) => (
              <div key={t.key} className="bg-surface-container-low rounded-lg p-3 ghost-border">
                <p className="text-[11px] text-on-surface-variant/70 mb-1">
                  <span style={{ color: t.color }}>{t.mark}</span> {t.key}
                </p>
                <p className="text-xl font-serif font-bold" style={{ color: t.color }}>
                  {tierCounts[t.key]}
                  <span className="text-xs text-on-surface-variant/50 ml-1">종목</span>
                </p>
              </div>
            ))}
          </div>
        )}
        <CanslimTable
          candidates={main.map((c) => ({ ...c, market_cap_rank: rankByCode.get(c.code) }))}
        />
      </section>

      {/* C 원칙 학습 섹션 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">menu_book</span>
          &lsquo;C&rsquo; 원칙 — 7가지 핵심 (William O&apos;Neil)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            { title: "1. 비교 기준", body: "반드시 전년 동기 대비. 직전 분기 비교는 계절성 왜곡. 4분기는 작년 4분기와 비교." },
            { title: "2. 최소 매수 컷오프", body: "절대 하한 +18~20% (이하는 매수 금지). 권장 +25~30%. 대세 상승기엔 +40~500%, 최고 종목 +100~500%." },
            { title: "3. 가속화 (가장 중요)", body: "증가율 절대 폭보다 직전 분기 대비 더 커지는가가 핵심. 15%→40~50% 가속이면 어닝 서프라이즈. 12개월 매분기 EPS 신고점에 근접하면 최고." },
            { title: "4. 매출액 동반", body: "EPS 폭증해도 매출 +25%↑ 또는 3분기 연속 가속해야 의미. 매출+순이익 모두 가속 중이면 특별 관리." },
            { title: "5. 미래 실적·컨센", body: "향후 1~2분기 예상치를 1년 전 같은 분기와 비교. 애널리스트 예상치 상향 횟수, 컨센 상회 빈도 확인." },
            { title: "6. 경고·위험", body: "강세장 막바지엔 +100%여도 천정 가능. 2분기 연속 EPS 감소는 심각. 증가율 2/3 둔화(100%→30%)도 심각. 증자 희석 이력 필수 확인." },
            { title: "7. 동종업계 검증", body: "같은 업종에서 눈길 끄는 기업이 단 하나도 없으면 투자 판단 자체가 틀렸을 가능성." },
          ].map((c) => (
            <div key={c.title} className="bg-surface-container/50 rounded-lg p-3">
              <p className="font-medium text-on-surface mb-1">{c.title}</p>
              <p className="text-on-surface-variant leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

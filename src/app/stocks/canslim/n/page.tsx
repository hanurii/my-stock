import fs from "fs/promises";
import path from "path";
import { NewHighsTable, type NCandidate } from "../NewHighsTable";

interface NData {
  generated_at: string;
  input_track: string;
  c_input_total: number;
  scored_count: number;
  unscored_count: number;
  scoring_version: string;
  score_axes: {
    competitive_advantage_max: number;
    revenue_contribution_max: number;
    sector_impact_max: number;
  };
  tier_cutoffs: { A: number; B: number; C: number; D: number };
  tier_counts: Record<string, number>;
  candidates: NCandidate[];
}

async function getNData(): Promise<NData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-n-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

const TIER_COLORS: Record<string, string> = {
  A: "#10b981",
  B: "#34d399",
  C: "#e9c176",
  D: "#ffb4ab",
};

const TIER_LABELS: Record<string, string> = {
  A: "🅐 강력 신제품",
  B: "🅑 검증 신제품",
  C: "🅒 부분 신제품",
  D: "🅓 약함",
};

export default async function CanslimNPage() {
  const data = await getNData();

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — N: 신제품
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 세 번째 글자 &lsquo;N&rsquo; — 최고 수익률 종목의 95%가 신제품·신경영·신고가 중 하나 충족. 본 페이지는 <strong className="text-on-surface-variant">신제품 단일 축</strong>으로 집중 평가.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          입력 모집단: <strong className="text-on-surface-variant">C 게이트 통과 종목 전체</strong> · 제외 컷오프 없음 ·
          점수 체계 <strong className="text-on-surface-variant">30점 만점</strong> (경쟁 우위 15 + 매출 기여 10 + 섹터 임팩트 5).
        </p>
        {data && (
          <p className="text-xs text-on-surface-variant/50 mt-1">
            생성일 {data.generated_at} · C 입력 {data.c_input_total}종목 · 채점 <strong className="text-on-surface-variant">{data.scored_count}</strong>
            {data.unscored_count > 0 && <> · 미조사 {data.unscored_count}</>}
          </p>
        )}
      </header>

      {/* 점수 체계 안내 */}
      {data && (
        <section className="bg-surface-container-low rounded-xl ghost-border p-4">
          <h3 className="text-sm font-serif font-bold text-on-surface mb-1 flex items-center gap-2">
            <span className="material-symbols-outlined text-base text-primary">scoreboard</span>
            N 점수 — 3축 30점 만점
            <span className="text-[11px] text-on-surface-variant/60 font-normal ml-1">
              · 신제품 단일 축에 집중
            </span>
          </h3>
          <p className="text-[11px] text-on-surface-variant/60 mb-3">
            해자(moat) 가 신제품의 수명을 결정. 경쟁 우위에 최대 가중치 15점, 실현된 매출 10점, 섹터 환경 5점.
          </p>
          <div className="grid grid-cols-3 gap-2 text-xs">
            {[
              { axis: "① 경쟁 우위", max: 15, hint: "독점 15 · 우위 11 · 대등 7 · 추격 4 · me-too 0" },
              { axis: "② 매출 기여", max: 10, hint: "≥30% 10 · 15~30% 7 · 5~15% 5 · <5% YoY+100% 2" },
              { axis: "③ 섹터 임팩트", max: 5, hint: "주도 섹터 5 · 성장 4 · 안정 3 · 사양 1" },
            ].map((a) => (
              <div key={a.axis} className="bg-surface-container/50 rounded-lg p-2.5">
                <p className="text-on-surface-variant/60 mb-0.5">{a.axis}</p>
                <p className="text-on-surface font-medium">{a.max}점 만점</p>
                <p className="text-[10px] text-on-surface-variant/50 mt-0.5 leading-relaxed">{a.hint}</p>
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
            {(["A", "B", "C", "D"] as const).map((t) => {
              const ranges: Record<string, string> = { A: "24+", B: "18~23", C: "10~17", D: "<10" };
              return (
                <span
                  key={t}
                  className="inline-flex items-center gap-1.5 px-2 py-1 rounded"
                  style={{ backgroundColor: `${TIER_COLORS[t]}20`, color: TIER_COLORS[t] }}
                >
                  <span className="font-bold">{TIER_LABELS[t]}</span>
                  <span className="opacity-80">{ranges[t]}</span>
                </span>
              );
            })}
          </div>
        </section>
      )}

      {/* 등급별 카운트 */}
      {data && (
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {(["A", "B", "C", "D"] as const).map((t) => (
            <div key={t} className="bg-surface-container-low rounded-lg p-3 ghost-border">
              <p className="text-[11px] text-on-surface-variant/70 mb-1" style={{ color: TIER_COLORS[t] }}>
                {TIER_LABELS[t]}
              </p>
              <p className="text-xl font-serif font-bold" style={{ color: TIER_COLORS[t] }}>
                {data.tier_counts[t] ?? 0}
                <span className="text-xs text-on-surface-variant/50 ml-1">종목</span>
              </p>
            </div>
          ))}
        </section>
      )}

      {/* N 본문 */}
      <section>
        {data ? (
          <>
            <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">trending_up</span>
              C 통과 종목 N 점수 ({data.candidates.length})
            </h3>
            <NewHighsTable candidates={data.candidates} />
          </>
        ) : (
          <div className="bg-surface-container-low rounded-xl ghost-border p-6 text-center text-sm text-on-surface-variant/70">
            N 데이터가 아직 생성되지 않았습니다.
            <br />
            <span className="text-[11px] text-on-surface-variant/50 mt-1 block">
              <code className="px-1.5 py-0.5 bg-surface-container/50 rounded">python scripts/build_n_v2.py</code>{" "}
              실행 후 종목별 N 점수가 채점됩니다.
            </span>
          </div>
        )}
      </section>

      {/* N 원칙 학습 섹션 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">menu_book</span>
          &lsquo;N&rsquo; 원칙 — 신제품 평가의 핵심
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            {
              title: "1. 95% 공통 — 신제품·신경영·신고가",
              body: "오닐 책: 최고 수익률 종목의 95%가 신제품·신경영·신고가 중 하나 이상을 충족. 본 페이지는 신제품 한 축에 집중 (신고가는 L, 신경영은 신호 잡음비 문제로 제외).",
            },
            {
              title: "2. 신제품의 기준 — 까다롭게",
              body: "단순 신제품이 아닌 '살아가는 방식을 혁신적으로 변화시키는 제품'. 한창때 수백만 일자리·생활수준 향상에 기여하는 종류.",
            },
            {
              title: "3. 경쟁 우위 (15점) — 해자가 수명을 결정",
              body: "글로벌·한국 독점 15점 / 명확한 우위 11점 / 대등 7점 / 추격 4점 / me-too 0점. 출처 URL 없으면 0점이 원칙.",
            },
            {
              title: "4. 현재 매출 기여 (10점) — 기대가 아닌 실증",
              body: "전사 매출 ≥30% 10점 / 15~30% 7점 / 5~15% 5점 / <5% 이지만 YoY +100% 2점. 사업보고서·IR 의 세그먼트별 매출이 기준.",
            },
            {
              title: "5. 섹터·시장 임팩트 (5점)",
              body: "주도 섹터 핵심 5점 / 성장 섹터 보조 4점 / 안정 섹터 차별 3점 / 사양 섹터 1점. 섹터 CAGR·산업 리포트 인용.",
            },
            {
              title: "6. 대역설 (Great Paradox)",
              body: "주가가 너무 비싸 보이는 종목이 더 오르고, 싸 보이는 종목이 더 떨어진다. 직관과 반대 — 강한 신제품은 이미 시장이 인식하고 있다.",
            },
            {
              title: "7. 매수 시점 — 분기점(pivot) 돌파",
              body: "강세장에서 모양을 만들고 치솟기 시작하는 시점. 탄탄한 모양 + 거래량 동반 + 신고가 근접/돌파. 5~10% 이상 상승 후 추격 매수 금지.",
            },
            {
              title: "8. N 점수만으로 매수 X",
              body: "N 은 신제품 강도만 평가. 매수는 C(분기실적) · A(연간실적) · S(수급) · L(상대강도) · M(시장추세) · I(기관수급) 와 함께.",
            },
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

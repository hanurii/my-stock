import fs from "fs/promises";
import path from "path";
import { LeaderTable, type LCandidate } from "../LeaderTable";

interface LData {
  generated_at: string;
  schema_version: string;
  c_input_count: number;
  l_evaluated_count: number;
  data_missing_count: number;
  universe: {
    type: string;
    actual_size: number;
    return_period: string;
    scoring: string;
  };
  candidates: LCandidate[];
}

async function getData(): Promise<LData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-l-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export default async function CanslimLPage() {
  const data = await getData();

  if (!data || data.candidates.length === 0) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            CAN SLIM 발굴 — L: 주도주 (Leader)
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">데이터가 아직 생성되지 않았습니다.</p>
        </header>
      </div>
    );
  }

  const { universe } = data;

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — L: 주도주 (Leader)
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 다섯 번째 글자 &lsquo;L&rsquo; — 시장 대비 상대 강도를 1~99 점수로 정량화한다.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          입력 모집단: <strong className="text-on-surface-variant">C 통과 종목</strong> 한정 ·{" "}
          척도: <strong className="text-on-surface-variant">RS 1~99 (컷오프 없음 — RS 가 곧 L 점수)</strong>
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일 {data.generated_at} · C 입력 {data.c_input_count}종목 · L 평가{" "}
          <strong className="text-on-surface-variant">{data.l_evaluated_count}개</strong>
          {data.data_missing_count > 0 && <> · 데이터 없음 {data.data_missing_count}개</>}
        </p>
      </header>

      {/* 평가 기준 */}
      <section className="bg-surface-container-low/50 rounded-xl ghost-border p-5">
        <h3 className="text-sm font-medium text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base">tune</span>
          평가 기준
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-xs text-on-surface-variant/80">
          <div>
            <p className="text-on-surface-variant mb-1">RS 점수 산출</p>
            <ul className="space-y-1 list-disc list-inside">
              <li>비교 모집단: <strong>{universe.type}</strong> ({universe.actual_size}개 유효)</li>
              <li>계산: {universe.return_period}</li>
              <li>모집단 내 백분위(1~99) → L 점수 (99 = 상위 1%)</li>
              <li>컷오프 없음 — 평가 가능한 모든 종목을 점수와 함께 노출</li>
            </ul>
          </div>
          <div>
            <p className="text-on-surface-variant mb-1">등급 라벨 (O&apos;Neil 책 기준, 점수에 영향 없음)</p>
            <ul className="space-y-1 list-disc list-inside">
              <li><strong>RS 95~99</strong>: 최강 주도주 — 매수 우선 검토</li>
              <li><strong>RS 90~94</strong>: 강한 주도주 — 매수 가능</li>
              <li><strong>RS 80~89</strong>: 주도주 — 책의 매수 권장선</li>
              <li><strong>RS 70~79</strong>: 회색지대 — 매수 보류</li>
              <li><strong>RS 40~69</strong>: 소외주 동조 — 절대 매수 금지</li>
              <li><strong>RS &lt; 40</strong>: 소외주 — 매수 금지</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 메인 테이블 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">military_tech</span>
          L 점수 순 정렬 ({data.l_evaluated_count}개 평가
          {data.data_missing_count > 0 && <> + {data.data_missing_count}개 데이터 없음</>})
        </h3>
        <LeaderTable candidates={data.candidates} />
      </section>

      {/* 매수 시점 안내 */}
      <section className="rounded-xl ghost-border p-4 bg-amber-400/[0.04]">
        <h4 className="text-sm font-medium text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-amber-300 text-base">warning</span>
          L 점수가 높아도 매수 시점은 별도 — 진입 3대 조건 (O&apos;Neil 책 기준)
        </h4>
        <ul className="space-y-1.5 text-xs text-on-surface-variant/80 list-disc list-inside leading-relaxed">
          <li>
            <strong>모양 형성 확인</strong> — 적절한 기간 동안 확실한 차트 모양(베이스)을 만들어냈는지 확인 후 매수.
          </li>
          <li>
            <strong>분기점(pivot) 매수</strong> — 정확한 매수 지점에서만 진입. 최초 매수 지점에서 <strong>+5~10% 이상 상승한 다음에는 매수 금지</strong> (추격 매수 회피).
          </li>
          <li>
            <strong>-8% 손절</strong> — 매수가 대비 -8% 하락한 종목은 즉시 매도. CAN SLIM 공통 손절선이지만 L에서 특히 강조.
          </li>
        </ul>
      </section>

      {/* L 원칙 학습 섹션 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">menu_book</span>
          &lsquo;L&rsquo; 원칙 — 6가지 핵심 (William O&apos;Neil)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            {
              title: "1. 주도주 선택 — 업종 내 최고 2~3개만",
              body: "주도주가 아니면 매수하지 마라. 업종 내 최고 종목 2~3개 중에서만 골라라. O'Neil: “정말 애가 탈 정도로 싸게 보이는 주식이라 해도 소외주는 투자 수익을 가져다 주는 경우가 거의 없다.”",
            },
            {
              title: "2. RS 점수 정의 — 52주 백분위",
              body: "지난 52주 주가 상승률을 시장 전체 종목과 비교한 백분위 점수(1~99점). RS 99 = 상위 1%, RS 50 = 시장의 절반은 이 종목보다 우수하고 나머지 절반은 부진하다는 뜻.",
            },
            {
              title: "3. RS 등급 라벨 — 책 기준 매수 권장 구간",
              body: "RS 80+ = 책의 매수 권장선. RS 70 미만은 시장 수익률 뛰어남 아님. RS 40~69 는 소외주 동조 절대 매수 금지. 우리 시스템은 컷오프 없이 점수만 표시 — 사용자가 등급 라벨과 함께 직접 판단.",
            },
            {
              title: "4. L 점수 활용 — 100점 만점 척도",
              body: "v3 부터 RS 가 곧 L 점수. 1~99 연속 척도라 다른 페이지 점수와 동일선상 비교 가능. RS 50 종목도 페이지에 노출되나, 매수 후보로는 RS 80+ 만 검토.",
            },
            {
              title: "5. 매수 시점 — 모양 + 분기점 + 추격 금지",
              body: "(1) 적절한 기간 동안 확실한 차트 모양 형성 (2) 정확한 분기점(pivot)에서 매수. 최초 매수 지점에서 5~10% 이상 상승한 다음에는 매수 금지 — 추격 매수의 우를 막고, 매물 출회로 조정 시 보유 물량을 지키기 위함.",
            },
            {
              title: "6. -8% 손절",
              body: "O'Neil: “매수 가격보다 8% 떨어진 소외주가 있다면 당장 팔아버려라. 그렇게 하지 않으면 치명적인 상처를 입을 수 있다.” CAN SLIM 공통 손절선이지만 L 원칙에서 특히 강조.",
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

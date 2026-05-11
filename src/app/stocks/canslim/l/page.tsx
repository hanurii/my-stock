import fs from "fs/promises";
import path from "path";
import { LeaderTable, type LCandidate } from "../LeaderTable";

interface LData {
  generated_at: string;
  s_input_count: number;
  l_passed_count: number;
  excluded_count: number;
  universe: {
    type: string;
    actual_size: number;
    rs_cutoff: number;
    return_period: string;
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
          윌리엄 오닐의 다섯 번째 글자 &lsquo;L&rsquo; — 상대적 주가 강도(RS) 점수로 시장 주도주만 골라낸다.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          입력 모집단: <strong className="text-on-surface-variant">S 통과 종목</strong> 한정.{" "}
          노출 컷오프: <strong className="text-on-surface-variant">RS ≥ {universe.rs_cutoff}</strong>.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일 {data.generated_at} · S 입력 {data.s_input_count}종목 · L 통과 <strong className="text-on-surface-variant">{data.l_passed_count}개</strong>
          {data.excluded_count > 0 && <> · 제외 {data.excluded_count}개</>}
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
              <li>모집단 내 백분위(1~99) → RS 점수 (99 = 상위 1%)</li>
            </ul>
          </div>
          <div>
            <p className="text-on-surface-variant mb-1">매수 판정 (O&apos;Neil 원전)</p>
            <ul className="space-y-1 list-disc list-inside">
              <li><strong>RS ≥ 80</strong>: 매수 가능 (사용자 컷오프)</li>
              <li><strong>RS 70~79</strong>: 회색지대 — 매수 기준 미달</li>
              <li><strong>RS 40~60</strong>: 소외주 동조 — 절대 매수 금지</li>
              <li><strong>RS &lt; 70</strong>: 시장 수익률 뛰어난 주식 아님</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 메인 테이블 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">military_tech</span>
          L 통과 종목 ({data.l_passed_count})
        </h3>
        <LeaderTable candidates={data.candidates} />
      </section>

      {/* 매수 시점 안내 */}
      <section className="rounded-xl ghost-border p-4 bg-amber-400/[0.04]">
        <h4 className="text-sm font-medium text-on-surface mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-amber-300 text-base">warning</span>
          RS 80+ 매수 진입 시 주의 (O&apos;Neil 원전)
        </h4>
        <ul className="space-y-1.5 text-xs text-on-surface-variant/80 list-disc list-inside leading-relaxed">
          <li>
            <strong>모양 형성 확인</strong> — 적절한 기간 동안 확실한 차트 모양(베이스)을 만들어냈는지 확인 후 매수.
          </li>
          <li>
            <strong>분기점(pivot) 매수</strong> — 정확한 매수 지점에서만 진입. 최초 매수 지점에서 <strong>+5~10% 이상 상승한 다음에는 매수 금지</strong> (추격 매수 회피).
          </li>
          <li>
            <strong>소외주 -8% 손절</strong> — 매수가 대비 -8% 하락한 종목은 즉시 매도. CAN SLIM 공통 손절선이지만 L에서 특히 강조.
          </li>
        </ul>
      </section>

      {/* 참고 — O'Neil 원전 */}
      <section className="text-xs text-on-surface-variant/60 leading-relaxed">
        <p className="mb-1">
          <strong className="text-on-surface-variant/80">O&apos;Neil 원전 인용</strong> —
          &ldquo;업종 내 최고 종목 2~3개 중에서 매수하라&rdquo;,
          &ldquo;주도주가 아니면 매수하지 마라&rdquo;,
          &ldquo;상대적 주가 강도가 80점 이상인 주식을 매수해라&rdquo;,
          &ldquo;정말 애가 탈 정도로 싸게 보이는 주식이라 해도 소외주는 투자 수익을 가져다 주는 경우가 거의 없다&rdquo;.
        </p>
      </section>
    </div>
  );
}

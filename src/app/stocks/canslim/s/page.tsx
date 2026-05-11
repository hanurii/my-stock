import fs from "fs/promises";
import path from "path";
import { SupplyDemandTable, ExcludedSection, type SCandidate } from "../SupplyDemandTable";

interface SData {
  generated_at: string;
  n_input_count: number;
  s_passed_count: number;
  excluded_count: number;
  cutoffs: {
    debt_ratio_threshold: number | null;
    debt_reduction_threshold_pp: number | null;
    split_exclude_count: number;
  };
  candidates: SCandidate[];
  excluded: Array<{ code: string; name: string; reasons: string[] }>;
}

async function getData(): Promise<SData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-s-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export default async function CanslimSPage() {
  const data = await getData();

  if (!data || data.candidates.length === 0) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            CAN SLIM 발굴 — S: 수요와 공급
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">데이터가 아직 생성되지 않았습니다.</p>
        </header>
      </div>
    );
  }

  const { debt_ratio_threshold, debt_reduction_threshold_pp } = data.cutoffs;

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — S: 수요와 공급
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 네 번째 글자 &lsquo;S&rsquo; — 발행주식수·자사주매입·경영진 지분·부채비율·주식분할로 수요와 공급 구조 점검.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          입력 모집단: <strong className="text-on-surface-variant">N 통과 종목</strong> 한정.{" "}
          노출 제외: <strong className="text-on-surface-variant">최근 5년 주식분할 3회 이상</strong>
          {debt_ratio_threshold !== null && (
            <> · <strong className="text-on-surface-variant">부채비율 &gt; {debt_ratio_threshold}%</strong></>
          )}
          .
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일 {data.generated_at} · N 입력 {data.n_input_count}종목 · S 통과 <strong className="text-on-surface-variant">{data.s_passed_count}개</strong> · 제외 {data.excluded_count}개
        </p>
      </header>

      {/* 컷오프 TBD 안내 */}
      {(debt_ratio_threshold === null || debt_reduction_threshold_pp === null) && (
        <section className="rounded-xl ghost-border p-4 bg-amber-400/5">
          <div className="flex items-start gap-2 text-xs text-on-surface-variant/80">
            <span className="material-symbols-outlined text-amber-400 text-base">info</span>
            <div className="space-y-1">
              <p className="text-on-surface-variant">컷오프 확정 대기 (TBD)</p>
              {debt_ratio_threshold === null && (
                <p>• 부채비율 과도 컷오프: 미설정 — N 통과 종목 분포 분석 후 결정 예정 (현재는 raw 값만 표시).</p>
              )}
              {debt_reduction_threshold_pp === null && (
                <p>• &ldquo;부채 크게 감소&rdquo; 라벨 기준: 미설정 — 분포 분석 후 결정 예정 (현재 라벨 비활성).</p>
              )}
            </div>
          </div>
        </section>
      )}

      {/* 평가 기준 */}
      <section className="bg-surface-container-low/50 rounded-xl ghost-border p-5">
        <h3 className="text-sm font-medium text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base">tune</span>
          평가 기준
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-xs text-on-surface-variant/80">
          <div>
            <p className="text-on-surface-variant mb-1">정보 표시 (raw 값)</p>
            <ul className="space-y-1 list-disc list-inside">
              <li>유통물량 / 전체 주식수 비율 (대주주 5%룰 합산 차감으로 추계)</li>
              <li>최고 경영진 보유 % (5%룰 대량보유 보고자 합산)</li>
              <li>부채비율 (총부채/자기자본, 현재 + 추세)</li>
              <li>최근 3년 자사주 매입 결정 공시 수</li>
            </ul>
          </div>
          <div>
            <p className="text-on-surface-variant mb-1">라벨 (가점, 통과 영향 X)</p>
            <ul className="space-y-1 list-disc list-inside">
              <li><strong>자사주 매우 큰 매입</strong>: 자사주 보유율 10%↑</li>
              <li><strong>연간 부채 크게 감소</strong>: 최근 2~3년 연간 부채비율 20%p↑ 감소</li>
              <li><strong>분기 부채 크게 감소</strong>: 최근 5분기 분기 부채비율 20%p↑ 감소</li>
              <li><strong>주식 분할 주의</strong>: 최근 5년 분할 1~2회 (천장 신호 가능성)</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 메인 테이블 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">trending_up</span>
          S 통과 종목 ({data.s_passed_count})
        </h3>
        <SupplyDemandTable candidates={data.candidates} />
      </section>

      {/* 제외 종목 */}
      <ExcludedSection excluded={data.excluded} />

      {/* 참고 — O'Neil 원전 */}
      <section className="text-xs text-on-surface-variant/60 leading-relaxed">
        <p className="mb-1">
          <strong className="text-on-surface-variant/80">O&apos;Neil 원전 인용</strong> — &ldquo;자사주 10%만 매수해도 무척 큰 것이다&rdquo;,
          &ldquo;두세 차례의 주식 분할은 천장을 쳤다는 징후&rdquo; (분할 다음해 본격 상승 18%),
          &ldquo;부채비율 낮을수록 더 안전하고 더 나은 기업&rdquo;,
          &ldquo;경영진이 많은 주식을 보유한 기업은 자기 회사 주식에 애착을 가지고 있다는 반증&rdquo;.
        </p>
      </section>
    </div>
  );
}

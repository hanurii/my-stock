import fs from "fs/promises";
import path from "path";
import { NewHighsTable, type NCandidate } from "../NewHighsTable";

interface NData {
  generated_at: string;
  input_track: string;
  a_input_total: number;
  n_count: number;
  data_sources: {
    price: string;
    commentary: string;
  };
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

export default async function CanslimNPage() {
  const data = await getNData();

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — N: 신제품·신경영·신고가
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 세 번째 글자 &lsquo;N&rsquo; — 최고 수익률 종목의 95%가 신제품·신경영·신고가 중 하나를 충족.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          입력 모집단: <strong className="text-on-surface-variant">A 충족도 점수 ≥ 80 (정통)</strong> 종목 한정 ·
          신고가 달성 정도는 자동 계산(Yahoo 1년 일봉), 신제품·신경영은 한국 언론사 검색·확인된 사실만 코멘트.
        </p>
        {data && (
          <p className="text-xs text-on-surface-variant/50 mt-1">
            생성일 {data.generated_at} · A 입력 {data.a_input_total}종목 · N 후보 <strong className="text-on-surface-variant">{data.n_count}개</strong>
          </p>
        )}
      </header>

      {/* N 본문 */}
      <section>
        {data ? (
          <NewHighsTable candidates={data.candidates} />
        ) : (
          <div className="bg-surface-container-low rounded-xl ghost-border p-6 text-center text-sm text-on-surface-variant/70">
            N 데이터가 아직 생성되지 않았습니다.
            <br />
            <span className="text-[11px] text-on-surface-variant/50 mt-1 block">
              <code className="px-1.5 py-0.5 bg-surface-container/50 rounded">python scripts/fetch_n_prices.py</code> 실행 후 종목별 카탈리스트 코멘트 작성 필요.
            </span>
          </div>
        )}
      </section>

      {/* N 원칙 학습 섹션 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">menu_book</span>
          &lsquo;N&rsquo; 원칙 — 7가지 핵심 (William O&apos;Neil)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            { title: "1. N 의 3대 키워드 (95% 공통)", body: "최고 수익률 종목의 95%가 신제품·신경영·신고가 중 하나 이상을 충족. 셋 모두 보면 더 강력." },
            { title: "2. 신제품의 기준", body: "단순 신제품이 아닌, 살아가는 방식을 혁신적으로 변화시키는 제품. 한창때 수백만 일자리·생활수준 향상에 기여." },
            { title: "3. 신경영·산업환경", body: "경영 혁신, 산업환경 결정적 개선 수혜 기업, 새 서비스 개발 기업도 포함." },
            { title: "4. 대역설 (Great Paradox)", body: "주가가 너무 비싸 보이는 종목이 더 오르고, 싸 보이는 종목이 더 떨어진다. 직관과 반대." },
            { title: "5. 역발상 매매 심리", body: "대중이 '비싸 보인다' 할 때 매수, '매력적'이라 느낄 때 매도. 군중 반대 시점." },
            { title: "6. 정확한 매수 시점 (피벗)", body: "강세장에서 모양을 만들고 치솟기 시작하는 시점. 탄탄한 모양 + 거래량 동반 + 신고가 근접/돌파." },
            { title: "7. 매수 금지 신호", body: "모양 형성 후 5~10% 이상 상승 시 매수 금지(추격 매수→손절매 위험). 단순 신고가 추격 금지." },
          ].map((c) => (
            <div key={c.title} className="bg-surface-container/50 rounded-lg p-3">
              <p className="font-medium text-on-surface mb-1">{c.title}</p>
              <p className="text-on-surface-variant leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {data && (
        <section className="text-[11px] text-on-surface-variant/50 space-y-0.5">
          <p>· 가격 데이터: {data.data_sources.price}</p>
          <p>· 코멘트 출처: {data.data_sources.commentary}</p>
        </section>
      )}
    </div>
  );
}

import fs from "fs";
import path from "path";
import { ETFFinder } from "@/components/ETFFinder";

interface TopHolding {
  code?: string;
  name: string;
  weight_pct: number;
}

interface ETF {
  code: string;
  name: string;
  manager: string;
  geography: string;
  tracking_index: string | null;
  listed_date: string | null;
  expense_ratio_pct: number | null;
  aum_krw: number | null;
  trading_volume_30d_krw: number | null;
  ytd_return_pct: number | null;
  top_holdings: TopHolding[];
  metrics_updated_at: string | null;
  notes?: string;
}

interface Sector {
  key: string;
  label: string;
  aliases: string[];
  description: string;
  etf_codes: string[];
}

interface ETFData {
  updated_at: string;
  data_status: {
    metadata_verified: boolean;
    metrics_last_refreshed: string | null;
    refresh_command: string;
    note: string;
  };
  sectors: Sector[];
  etfs: Record<string, ETF>;
}

function getETFData(): ETFData | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "etf-data.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as ETFData;
  } catch {
    return null;
  }
}

export const dynamic = "force-static";
export const revalidate = false;

export default function ETFFinderPage() {
  const data = getETFData();

  if (!data) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-3xl font-serif text-primary mb-4">데이터 없음</h2>
        <p className="text-on-surface-variant">
          ETF 데이터 파일이 없습니다.
        </p>
      </div>
    );
  }

  const totalETFs = Object.keys(data.etfs).length;
  const sectorsWithETFs = data.sectors.filter((s) => s.etf_codes.length > 0).length;

  return (
    <div className="space-y-12">
      {/* Header */}
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          ETF Finder
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          핫섹터 ETF 파인더
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          섹터를 선택하면 관련 ETF를 추천 + 운용보수·펀드 규모·거래대금 기반 점수
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1.5">
          기준일: {data.updated_at} · 등록 ETF {totalETFs}개 · ETF 매핑 섹터 {sectorsWithETFs}개
        </p>
        {!data.data_status.metrics_last_refreshed && (
          <div className="mt-4 rounded-xl p-4" style={{ backgroundColor: "#d4b48315" }}>
            <p className="text-sm" style={{ color: "#d4b483" }}>
              <span className="material-symbols-outlined text-base align-middle mr-1">info</span>
              운용보수·펀드 규모 등 수치 데이터 미갱신 상태입니다. 갱신 명령:
              <code className="text-xs bg-surface-container/40 px-2 py-0.5 rounded ml-2">
                {data.data_status.refresh_command}
              </code>
            </p>
            <p className="text-xs text-on-surface-variant/60 mt-1">
              {data.data_status.note}
            </p>
          </div>
        )}
      </section>

      <ETFFinder sectors={data.sectors} etfs={data.etfs} />

      {/* 평가 기준 설명 */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <h3 className="text-lg font-serif text-on-surface mb-4">평가 기준 설명</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="bg-surface-container/40 rounded-lg p-4">
            <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-1.5">
              ① 운용보수 (낮을수록 좋음)
            </p>
            <p className="text-on-surface-variant leading-relaxed">
              연 0.05~0.15% = 우수 / 0.15~0.4% = 보통 / 0.4%+ = 부담. 장기 보유 시 복리로 누적되어 큰 차이.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-4">
            <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-1.5">
              ② 펀드 규모 (클수록 안정)
            </p>
            <p className="text-on-surface-variant leading-relaxed">
              해당 ETF에 모인 전체 자금. 1조원 이상 = 우수 / 1,000~5,000억 = 보통 / 100억 미만 = 상장폐지 위험. 규모가 작으면 매수·매도 시 호가 격차도 큼.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-4">
            <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-1.5">
              ③ 거래대금 (클수록 유동성)
            </p>
            <p className="text-on-surface-variant leading-relaxed">
              일 평균 10억원 이상 = 우수. 거래대금이 적으면 매수·매도 시 호가 슬리피지 발생.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-4">
            <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-1.5">
              ④ 상장기간 (길수록 검증)
            </p>
            <p className="text-on-surface-variant leading-relaxed">
              5년 이상 = 시장 사이클 검증 / 1년 미만 = 신생 ETF 주의. 상장 직후 ETF는 운용 안정성 미검증.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-4">
            <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-1.5">
              ⑤ 종목 분산 (집중도 ↓ = 좋음)
            </p>
            <p className="text-on-surface-variant leading-relaxed">
              상위 3종목 비중 합이 50% 이하 = 분산 양호. 한 종목 30%+ 차지하면 사실상 그 종목 베팅.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-4">
            <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-1.5">
              ⑥ 추적 지수 (테마 일관성)
            </p>
            <p className="text-on-surface-variant leading-relaxed">
              FnGuide / WISE / KRX 등 정식 지수 추종이 안정적. "테마/액티브" 표시는 운용사 재량 비중.
            </p>
          </div>
          <div className="bg-surface-container/40 rounded-lg p-4 md:col-span-2">
            <p className="text-xs uppercase tracking-wider text-on-surface-variant/50 mb-1.5">
              참고: 올해 수익률 (= YTD, Year-To-Date)
            </p>
            <p className="text-on-surface-variant leading-relaxed">
              올해 1월 1일 대비 현재 등락률. 점수에는 반영하지 않음 (좋은 ETF인지와 별개) — 단지 현재 모멘텀 참고용.
              <span className="text-on-surface-variant/60 text-xs">
                {" "}예) +50% = 올해 50% 상승 / -10% = 올해 10% 하락.
              </span>
            </p>
          </div>
        </div>
      </section>

      {/* 데이터 갱신 가이드 */}
      <section className="bg-surface-container-low rounded-xl p-6 sm:p-8 ghost-border">
        <h3 className="text-lg font-serif text-on-surface mb-4">데이터 갱신 + ETF 추가 방법</h3>
        <div className="space-y-3 text-sm text-on-surface-variant">
          <div>
            <p className="font-medium text-on-surface mb-1">1. ETF 추가</p>
            <p className="leading-relaxed">
              <code className="bg-surface-container/40 px-2 py-0.5 rounded text-xs">
                public/data/etf-data.json
              </code>{" "}
              파일에서 <code className="bg-surface-container/40 px-1 py-0.5 rounded text-xs">sectors[].etf_codes</code>에 ETF 종목코드 추가, <code className="bg-surface-container/40 px-1 py-0.5 rounded text-xs">etfs</code> 객체에 ETF 메타데이터 입력.
            </p>
          </div>
          <div>
            <p className="font-medium text-on-surface mb-1">2. 수치 데이터 갱신</p>
            <p className="leading-relaxed">
              아직 자동 갱신 스크립트 미구현. 수동으로 Naver 모바일 API 또는 ETF CHECK에서 조회 후 JSON 직접 편집.
              <br />
              <span className="text-xs text-on-surface-variant/60">
                참고: m.stock.naver.com/api · etfcheck.co.kr
              </span>
            </p>
          </div>
          <div>
            <p className="font-medium text-on-surface mb-1">3. 새 섹터 추가</p>
            <p className="leading-relaxed">
              <code className="bg-surface-container/40 px-1 py-0.5 rounded text-xs">sectors</code> 배열에 새 객체 추가 (key, label, aliases, description, etf_codes).
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

import fs from "fs/promises";
import path from "path";
import Link from "next/link";
import { InstitutionalTable, type ICandidate } from "../InstitutionalTable";

interface IData {
  generated_at: string;
  l_input_count: number;
  passed_count: number;
  excluded_count: number;
  candidates: ICandidate[];
}

async function getData(): Promise<IData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "can-slim-i-candidates.json");
    return JSON.parse(await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

export default async function CanslimIPage() {
  const data = await getData();

  if (!data || data.candidates.length === 0) {
    return (
      <div className="space-y-10">
        <header>
          <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
            CAN SLIM 발굴 — I: 기관 투자가의 뒷받침
          </h2>
          <p className="text-sm text-on-surface-variant mt-2">데이터가 아직 생성되지 않았습니다.</p>
        </header>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-on-surface">
          CAN SLIM 발굴 — I: 기관 투자가의 뒷받침
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          윌리엄 오닐의 여섯 번째 글자 &lsquo;I&rsquo; — 기관 투자가의 양·추세·질 3축으로 매수 적격성 판단.
        </p>
        <p className="text-xs text-on-surface-variant/60 mt-1.5">
          입력 모집단: <strong className="text-on-surface-variant">L 통과 종목</strong> 한정.{" "}
          데이터 소스: <strong className="text-on-surface-variant">DART 5%룰</strong> · <strong className="text-on-surface-variant">네이버 일별 기관 매매</strong>.
          미달 종목은 <strong className="text-on-surface-variant">회색 음영 + 사유</strong>로 표시.
        </p>
        <p className="text-xs text-on-surface-variant/50 mt-1">
          생성일 {data.generated_at} · L 입력 {data.l_input_count}종목 · 통과{" "}
          <strong className="text-on-surface-variant">{data.passed_count}개</strong> · 회색 처리 {data.excluded_count}개
        </p>
        <div className="mt-3">
          <Link
            href="/stocks/canslim/i/managers"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg ghost-border text-xs text-on-surface-variant hover:bg-surface-container/50 transition-all"
          >
            <span className="material-symbols-outlined text-base">groups</span>
            운용사 관점으로 보기 →
          </Link>
        </div>
      </header>

      {/* 평가 기준 */}
      <section className="bg-surface-container-low/50 rounded-xl ghost-border p-5">
        <h3 className="text-sm font-medium text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base">tune</span>
          평가 기준 — 4 게이트 + 4 경고
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 text-xs text-on-surface-variant/80">
          <div>
            <p className="text-on-surface-variant mb-1">노출 게이트 (해당 시 회색 처리)</p>
            <ul className="space-y-1 list-disc list-inside">
              <li><strong>G1 기관 매매 두 분기 연속 이탈</strong>: 직전 60일 음수 + 그 전 60일도 음수</li>
              <li><strong>G2 5%룰 지분 1년 감소 + 신규 시그널 0</strong>: -2.0%p 이상 감소 AND 신규/추가매수/재등장 모두 0건</li>
              <li><strong>G3 5%룰 이탈 다수</strong>: 1년 내 5%→미만 이탈 보고자 ≥ 2건</li>
              <li><strong>G4 기관 뒷받침 완전 부재</strong>: 5%+ 기관 0 + 60일 매매 ≤ 0 + 신규 시그널 0</li>
            </ul>
          </div>
          <div>
            <p className="text-on-surface-variant mb-1">경고 시그널 (통과해도 표시)</p>
            <ul className="space-y-1 list-disc list-inside">
              <li><strong>C1 신규 시그널 0건</strong>: 책 기준 — 신규 편입이 가장 중요</li>
              <li><strong>C2 직전 분기 큰 하락</strong>: 매수→매도 전환 또는 -50%↑ 가속</li>
              <li><strong>C3 분기 추세 악화</strong>: 직전 분기 대비 -10% 이상</li>
              <li><strong>C4 5%룰 기관 부재 + 60일 이탈</strong></li>
            </ul>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-on-surface/5 text-[11px] text-on-surface-variant/70 space-y-1">
          <p className="text-on-surface-variant">신규 시그널 3 카테고리</p>
          <ul className="grid grid-cols-1 sm:grid-cols-3 gap-x-3 gap-y-0.5 list-disc list-inside">
            <li><strong>🆕 strict 신규</strong>: 1년 내 첫 등장</li>
            <li><strong>➕ 추가매수</strong>: 최근 90일 비중 증가</li>
            <li><strong>🔄 재등장</strong>: 6개월 공백 후 재진입</li>
          </ul>
        </div>
      </section>

      {/* 메인 테이블 */}
      <section>
        <h3 className="text-lg font-serif font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">groups</span>
          L 통과 종목 — 기관 뒷받침 ({data.candidates.length})
        </h3>
        <p className="text-[11px] text-on-surface-variant/60 mb-3">
          행 클릭 시 보고자별 시계열 · 1년 이탈 · 기관 매매 상세 펼쳐짐. 5%+ 기관 컬럼의 괄호는 (한국/글로벌/연기금) 분해 수치.
        </p>
        <InstitutionalTable candidates={data.candidates} />
      </section>

      {/* I 원칙 학습 섹션 */}
      <section className="bg-surface-container-low rounded-xl ghost-border p-5 space-y-4">
        <h3 className="text-lg font-serif font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">menu_book</span>
          &lsquo;I&rsquo; 원칙 — 6가지 핵심 (William O&apos;Neil)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            {
              title: "1. 정의 — 기관 투자가의 뒷받침",
              body:
                "기관이 일정 수준 보유하면 '뒷받침' 한다고 표현. 최고의 주식이라 해서 반드시 대다수 기관이 보유할 필요는 없으나, 적어도 여러 기관이 보유해야 한다.",
            },
            {
              title: "2. 점검 항목 — 양·추세·질 3축",
              body:
                "(a) 얼마나 많은 기관이 보유 중인가, (b) 최근 몇 분기 동안 보유 기관 수가 꾸준히 늘었는가·특히 지난 분기에 크게 늘었는가, (c) 가장 뛰어난 노련한 매니저(최소 1~2명) 보유 종목인가.",
            },
            {
              title: "3. 기관의 질 — 펀드 등급",
              body:
                "12개월·3년 수익률로 평가. 상위 5% = a+, b+ 이상 우수. 핵심 매니저 이탈 시 운용 성과가 확 달라질 수 있으니 매니저 변동도 추적. (한국 보정: fundguide 분기/연간 Top 10 상대평가 a+/a/a- 3등급)",
            },
            {
              title: "4. 신규 편입이 훨씬 중요",
              body:
                "가장 최근 분기에 비중 있게 신규 편입된 종목은 기존 보유보다 훨씬 눈여겨봐야 한다. 펀드가 포트폴리오를 새로 구성하기 시작하면 비중을 늘려갈 가능성이 높고, 신규 편입은 가까운 매각 가능성이 작다. 책 기준 공시 시점은 분기/반기 종료 후 약 6주.",
            },
            {
              title: "5. 매수 판단 — AND 조건",
              body:
                "(1) 평균 이상 성과의 기관 가운데 적어도 몇 곳이 매수 + (2) 최근 몇 분기 보유 기관 수가 늘어남. 양만 많고 질이 낮으면 매수 X. 결국 '현명한 판단·고급 정보 기반 매수'와 '실수로 잘못 매수한 주식'을 구분하는 것이 CAN SLIM 의 역할.",
            },
            {
              title: "6. 시장 감각 — 우수 뮤추얼 펀드 연구",
              body:
                "운용 성과가 뛰어난 뮤추얼 펀드 보고서를 읽고 투자 철학·매수 종목을 학습. 그게 시장이 어떻게 움직이는지 자체적으로 느끼는 방법.",
            },
          ].map((c) => (
            <div key={c.title} className="bg-surface-container/50 rounded-lg p-3">
              <p className="font-medium text-on-surface mb-1">{c.title}</p>
              <p className="text-on-surface-variant leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
        <div className="text-[10px] text-on-surface-variant/50 pt-2 border-t border-on-surface/5">
          한국 보정: 미국 13F 같은 펀드별 전수 공시 불가능. DART 5%룰(대량보유보고) + 네이버 일별 기관 매매 + 국민연금 분기 공시 하이브리드로 양·추세·질 측정. 5% 미만 보유 + 시총 100조+ 메가캡은 시그널 약화 한계 인지.
        </div>
      </section>
    </div>
  );
}

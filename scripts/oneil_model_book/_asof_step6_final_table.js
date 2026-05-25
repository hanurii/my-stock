// Step 6: 5축 (C·A·N·S·L) 합산 → 최종 top 20 표 산출
// N 점수는 2025-11-25 시점 한국 언론/증권사 자료 기준 (Step 5 산출)

const fs = require('fs');
const path = require('path');

const ROOT = 'C:/Users/hanul/playground/my-stock';

const top20Data = require(path.join(ROOT, 'research/oneil-model-book/_asof_2025-11-25_top20.json'));

// Step 5 — 20종 점-시점 N 점수 (2025-11-25 이전 한국 언론·증권사 자료 기준)
// 채점 룰: IMPL_canslim_n_page.md 그대로 (경쟁우위 15 + 매출기여 10 + 섹터임팩트 5)
const N_SCORES = {
  '089970': { name:'브이엠',         total:27, tier:'A', product:'반도체 식각장비 (국내 유일)', comp:15, rev:7, sec:5,
    rationale:'국내 유일 식각 장비. 25.11.06 SK하이닉스 76.5억 수주(매출 10.89%). 4Q25 매출 504억 예상 — 3년만의 분기 500억+.' },
  '356860': { name:'티엘비',         total:30, tier:'A', product:'DDR5/SOCAMM PCB',           comp:15, rev:10, sec:5,
    rationale:'DDR5 7200Mbps+ 신제품 ASP 사이클. 25년 매출 2,584억(+43.6%) 영업익 259억(+673%). DDR5 59% / SSD 36%.' },
  '458870': { name:'씨어스테크놀로지',  total:30, tier:'A', product:'씽크(thynC) AI 환자 모니터링', comp:15, rev:10, sec:5,
    rationale:'AI 입원환자 모니터링 사실상 국내 독점. 누적 6000병상. 3Q 매출 +1500% 흑전, thynC가 142억(매출 핵심).' },
  '322000': { name:'HD현대에너지솔루션', total:25, tier:'A', product:'N타입 고효율 태양광 모듈',     comp:11, rev:10, sec:4,
    rationale:'국내 태양광 모듈 1위, N타입 전환. 25년 매출 4,927억(+17%) 영업익 412억(+1,077%). 미국 1,619억(+257%, 4Q 비중 44%).' },
  '009150': { name:'삼성전기',         total:30, tier:'A', product:'AI MLCC·FC-BGA',           comp:15, rev:10, sec:5,
    rationale:'FC-BGA 수요 생산능력 50%+ 초과, 공급 부족. 25년 매출 11.3조 역대 최대. FC-BGA 1.1조(+28.3%), 기판 내 비중 50%+.' },
  '016610': { name:'DB증권',           total:17, tier:'C', product:'PIB(PB+IB) 사업모델',          comp:7,  rev:5,  sec:5,
    rationale:'PB·IB 연계 PIB 모델. 3Q 누적 매출 +39.2%, 영업익 +92.5%. 자기매매·자산운용·저축은행 다축. 단 신제품 카탈리스트는 약함.' },
  '009155': { name:'삼성전기우',        total:30, tier:'A', product:'AI MLCC·FC-BGA (우선주)',    comp:15, rev:10, sec:5,
    rationale:'보통주(009150)와 동일 펀더멘털.' },
  '278470': { name:'에이피알',          total:30, tier:'A', product:'메디큐브 K뷰티',             comp:15, rev:10, sec:5,
    rationale:'美 울타뷰티 입점 3개월 만에 +30% 성장. K뷰티 글로벌 톱티어. 3Q 매출 3,859억(+122%), 美 비중 39% 분기 1,500억+. 25년 1조 매출 확정적.' },
  '037460': { name:'삼지전자',          total:16, tier:'C', product:'오픈랜 O-RU + 전자부품 유통',  comp:7,  rev:5,  sec:4,
    rationale:'24.11 오픈랜 K-OTIC 국제인증. 단 매출 84~85%가 전자부품 유통이라 통신 신제품 매출 기여 미미. 25년 매출 4.29조 영업익 1,624억.' },
  '098120': { name:'마이크로컨텍솔',     total:23, tier:'B', product:'반도체 번인·테스트 소켓',     comp:11, rev:7,  sec:5,
    rationale:'번인 소켓 삼성·SK하이닉스·마이크론 납품. 25년 상반기 매출 +61.9% 영업익 +147%. HBM 공급부족 25년 지속 → 직접 수혜.' },
  '007660': { name:'이수페타시스',       total:30, tier:'A', product:'AI 가속기용 초고다층 MLB',    comp:15, rev:10, sec:5,
    rationale:'초고다층 MLB 글로벌 빅테크 러브콜 폭주. 25년 매출 1조·영업익 2,000억 기대. 월 신규수주 800억 (캐파 650억으로 공급부족).' },
  '019180': { name:'티에이치엔',        total:10, tier:'C', product:'자동차 와이어링하네스',        comp:4,  rev:5,  sec:1,
    rationale:'현대차/기아 메인 공급. 1Q25 매출 +19.2%이나 영업익 -55.5% 수익성 압박. 신제품 카탈리스트 약함, 사이클 의존.' },
  '000880': { name:'한화',             total:26, tier:'A', product:'방산·우주 지주 (3사 통합)',   comp:11, rev:10, sec:5,
    rationale:'방산 3사 모두 호조 — 에어로 +20%, 시스템 +10.7%, 오션 +19.9%. 25년 연결 매출 +34.4% 영업익 +71.6%. K방산 + 우주.' },
  '033500': { name:'동성화인텍',         total:26, tier:'A', product:'LNG/ULEC 보냉재',           comp:11, rev:10, sec:5,
    rationale:'HD현대중공업 3,216억 + 삼호 893억 수주. 3.6년 수주잔고. 25년 매출 6,700~7,493억(+12.6~25%). LNG 슈퍼사이클.' },
  '425420': { name:'티에프이',          total:27, tier:'A', product:'2.5D/3D 패키지 테스트 소켓',  comp:15, rev:7,  sec:5,
    rationale:'25.3Q 북미 ASIC 신규 진입, CPO 열관리 수주. 25년 매출 +51.8% 영업익 +334%, OPM 20%. 4Q 매출 362억(+75%).' },
  '318160': { name:'셀바이오휴먼텍',     total:18, tier:'B', product:'고부가 마스크팩 시트 + ODM', comp:7,  rev:7,  sec:4,
    rationale:'마스크팩 시트 소재 + 화장품 OEM/ODM 사업 확장. 25년 매출 510억(+79.6%) 영업익 93억(+132.5%) 창립 최대.' },
  '071970': { name:'HD현대마린엔진',    total:23, tier:'B', product:'대형 선박엔진',              comp:11, rev:7,  sec:5,
    rationale:'HD현대 계열 + 11.14 케이조선 645.9억 수주(매출 20.5%). 25년 상반기 매출 +24.4% 영업익 +81.8%. 25년 수주 매출 54% 비중.' },
  '187870': { name:'디바이스',          total:22, tier:'B', product:'OLED Mask 세정장비',         comp:11, rev:7,  sec:4,
    rationale:'IT용 OLED Mask 세정기 시장 점유율 90%+. 25년 3Q 누적 매출 +172.2% 흑전. 삼성전자 반도체 웨이퍼 세정 297억 수주.' },
  '241770': { name:'메카로',            total:23, tier:'B', product:'반도체 CVD/ALD Heater·Source', comp:11, rev:7, sec:5,
    rationale:'CVD/ALD Heater block + Chemical Source 삼성·SK 90%+ 점유율. 24년 매출 +50.5% 영업익 +272.9%. 전공정 슈퍼사이클 직접 수혜.' },
  '327260': { name:'RF머트리얼즈',      total:23, tier:'B', product:'엔비디아 광증폭기 + 5G/방산 패키지', comp:11, rev:7, sec:5,
    rationale:'엔비디아 AI 서버 광증폭기 패키지 공급 + GaN heat sink 세계 최초. 5G HTCC + 군수. 3Q 매출 146억(+89%), 25년 580억 → 26년 792억.' },
};

// 5축 합산 + 재정렬
const final = top20Data.top20.map(r => {
  const nMeta = N_SCORES[r.code];
  const nScore = nMeta?.total || 0;
  return {
    ...r,
    n_score: nScore,
    n_tier: nMeta?.tier || '?',
    n_product: nMeta?.product || '',
    n_rationale: nMeta?.rationale || '',
    n_comp: nMeta?.comp,
    n_rev: nMeta?.rev,
    n_sec: nMeta?.sec,
    total_5axis: r.total_4axis + nScore,
  };
});
final.sort((a, b) => b.total_5axis - a.total_5axis);

// Markdown 표
let md = `# 2025-11-25 시점 CAN SLIM Ranking top 20 (점-시점 재구성)

> **목적**: 사용자의 백테스트 — "6개월 전 상위에 있던 종목은 무엇이었고, 그 시점 신고가 대비 가격은 얼마였나?" 사후 3개월 후 결과 평가는 사용자가 HTS에서 직접 수행.
>
> **데이터 기준**: 모든 4축(C·A·S·L)은 2025-11-25 시점 점-시점 재계산. N은 11/25 이전 한국 언론/증권사 자료만 사용해 직접 채점. S는 오늘 기준값 (부채·주주가치 안정 지표).

## 5축 합산 점수 top 20

| 순위 | 코드 | 종목명 | 시장 | 시총(억) | C/100 | A/50 | N/30 | S/60 | L/99 | **합산** | 신고가대비 | 1Y |
|---:|:-:|:-|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
`;

for (let i = 0; i < final.length; i++) {
  const r = final[i];
  md += `| ${i + 1} | ${r.code} | ${r.name} | ${r.market} | ${r.market_cap_eok.toLocaleString()} | ${r.c_score.toFixed(0)} | ${r.a_score} | ${r.n_score} | ${r.s_score} | ${r.l_score} | **${r.total_5axis.toFixed(0)}** | ${r.pct_from_52w_high}% | ${r.return_1y_pct}% |\n`;
}

md += `\n## N 점수 상세 (2025-11-25 시점 사실 기준)\n\n`;
md += `| 코드 | 종목 | N점수 | 핵심제품 | 채점 근거 |\n|:-:|:-|:-:|:-|:-|\n`;
for (const r of final) {
  md += `| ${r.code} | ${r.name} | ${r.n_score} (${r.n_comp}+${r.n_rev}+${r.n_sec}) | ${r.n_product} | ${r.n_rationale} |\n`;
}

md += `\n## 데이터 메타\n\n`;
md += `- **점-시점 안전**: 가격·시총·L·신고가대비 = 2025-11-25 일봉 캐시 (\`_universe_prices_5y.json\`); C·A 분기 데이터 ≤ '202509', 연간 ≤ '202412'; N = 11/25 이전 한국 언론·증권사 리포트만\n`;
md += `- **C 게이트 통과 모집단**: 181종 (이 중 4축 상위 20을 우선 추출, 5축 재정렬)\n`;
md += `- **S 점수 한계**: \`can-slim-s-candidates.json\` 오늘값 사용 (부채·주주가치 안정 지표). 점-시점 C 게이트만 통과하고 오늘의 ranking S 산출 대상에 없는 종목은 S=0으로 잡힘 (실제 점수보다 보수적)\n`;
md += `- **시총 한계**: 점-시점 종가 × 현재 주식수 (분할·증자 미반영). 일부 오차 가능\n`;
md += `- **N 점수**: 본인 직접 채점 (메모리 [[doc-logic-sync]] 기반 IMPL_canslim_n_page.md 룰 그대로 — 경쟁우위 15 + 매출기여 10 + 섹터임팩트 5)\n`;
md += `- **사후 3개월 평가**: 미산정. 사용자가 HTS에서 차트 분석 직접 수행 예정\n`;

const outMd = path.join(ROOT, 'out', 'ranking_asof_2025-11-25.md');
fs.mkdirSync(path.dirname(outMd), { recursive: true });
fs.writeFileSync(outMd, md);

// CSV
let csv = '순위,코드,종목명,시장,시총(억),C,A,N,S,L,5축합산,신고가대비(%),1Y수익률(%),신고가(원),점-시점종가,N핵심제품,N채점근거\n';
for (let i = 0; i < final.length; i++) {
  const r = final[i];
  const escape = (s) => `"${(s || '').replace(/"/g, '""')}"`;
  csv += `${i + 1},${r.code},${escape(r.name)},${r.market},${r.market_cap_eok},${r.c_score.toFixed(0)},${r.a_score},${r.n_score},${r.s_score},${r.l_score},${r.total_5axis.toFixed(0)},${r.pct_from_52w_high},${r.return_1y_pct},${r.high_52w},${r.close_asof},${escape(r.n_product)},${escape(r.n_rationale)}\n`;
}
const outCsv = path.join(ROOT, 'out', 'ranking_asof_2025-11-25.csv');
fs.writeFileSync(outCsv, csv);

console.log(`Markdown: ${outMd}`);
console.log(`CSV:      ${outCsv}`);
console.log(`\n5축 합산 top 20 (재정렬):`);
console.log('순  code   name              시총(억)   C   A   N   S   L  합산  신고대비');
console.log('─'.repeat(95));
for (let i = 0; i < final.length; i++) {
  const r = final[i];
  console.log(
    `${(i + 1).toString().padStart(2)} ${r.code} ${(r.name||'').padEnd(18)} ${(r.market_cap_eok||0).toLocaleString().padStart(9)} ${r.c_score.toFixed(0).padStart(3)} ${r.a_score.toString().padStart(3)} ${r.n_score.toString().padStart(3)} ${r.s_score.toString().padStart(3)} ${r.l_score.toString().padStart(3)} ${r.total_5axis.toFixed(0).padStart(5)} ${(r.pct_from_52w_high+'%').padStart(8)}`,
  );
}

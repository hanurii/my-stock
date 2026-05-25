// 21~40위 5축 합산 표 산출 (Top 20 와 동일 방법론)

const fs = require('fs');
const path = require('path');
const ROOT = 'C:/Users/hanul/playground/my-stock';

const data = require(path.join(ROOT, 'research/oneil-model-book/_asof_2025-11-25_top20.json'));
const rows21_40 = data.all_rows.slice(20, 40);

// 점-시점 N 점수 (2025-11-25 이전 한국 언론·증권사 자료 기준)
const N = {
  '100840': { n:23, t:'B', p:'AI 데이터센터용 공랭식 열교환기',
    r:'데이터센터용 소형 가스터빈 수요 증가 → 공랭식 열교환기 수요 ↑. 25년 매출 +106% 영업익 +400%, 분기 1,500억대.' },
  '259630': { n:22, t:'B', p:'각형/파우치 셀 조립 자동화 장비',
    r:'GM 등 23 글로벌 + LG에너지·SK온 45 배터리 메이커 공급. 3Q 누적 매출 1,708억(+155% YoY). 30년 1조 매출 목표.' },
  '108380': { n:18, t:'B', p:'조선·방산·철도·자동차 다각 전자',
    r:'압력센서·수중로봇·전자기판 다각화. 1Q 매출 +34.5% 영업익 +140%, 2Q 매출 563억(+13%) 영업익 +89%.' },
  '402340': { n:19, t:'B', p:'SK하이닉스 지분(반도체 지주)',
    r:'25년 매출 1.41조, 영업익 8.8조(SK하이닉스 지분법 +117.5%) 사상최대. 11번가·티맵·SK하이닉스 포트폴리오 지주.' },
  '052400': { n:25, t:'A', p:'지역화폐 결제 (12조 규모)',
    r:'지역화폐 결제 9조 → 12조 확대. 25년 매출 3,088억(+31%) 영업익 885억(+166%, +881% 폭증).' },
  '200670': { n:15, t:'C', p:'필러·톡신·관절염',
    r:'필러·톡신·휴톡스 다각화. 25년 3Q 누적 매출 -0.3% 영업익 -5.3% — 본업 정체. 필러 수출 +46% 보조.' },
  '060250': { n:20, t:'B', p:'전자결제 (거래액 51.5조)',
    r:'전자결제 거래대금 51.5조 — 50조 시대 진입. 25년 매출 1.23조(+12%) 영업익 547억(+25%).' },
  '003230': { n:30, t:'A', p:'불닭볶음면 (글로벌)',
    r:'매출 2조 돌파·영업익 5,000억+ 사상최대. 1Q 매출 7,144억(+35%), 미국 +37%·중국 +36%·유럽 +215% 폭증.' },
  '085620': { n:14, t:'C', p:'생명보험 (건강보험 성장)',
    r:'건강보험 성장. 1Q 순익 +115%, 매출 2.80조(+159.5%) 영업익 +73.8%. 신제품 카탈리스트 약함.' },
  '267260': { n:30, t:'A', p:'미국 765kV 초고압 변압기',
    r:'AI 데이터센터 전력망 + 미국 765kV 초고압. 변압기 30개월 대기, 11조 수주잔고. 3Q 전력기기 5,878억(+87.7%).' },
  '285130': { n:14, t:'C', p:'합성수지·신약 다각',
    r:'25년 매출 2.37조(+36.2%), 영업손실 축소, 순익 흑전. 신제품 카탈리스트 약함 — 종속사 실적 개선 위주.' },
  '950140': { n:23, t:'B', p:'미국 K뷰티 ODM',
    r:'아마존·월마트·울타뷰티 미국 ODM. 25년 상반기 매출 +1.6% 영업익 +34.3%. 코스메카코리아 지분 50%로 확대.' },
  '218410': { n:23, t:'B', p:'GaN 트랜지스터 (통신+방산)',
    r:'GaN 전력증폭기 매출 비중 75%. 3Q 누적 매출 +53.5% 영업익 흑전. 4Q 매출 556억(+44% YoY) 예상.' },
  '181710': { n:17, t:'C', p:'페이코·게임·클라우드',
    r:'3Q 매출 6,256억(+2.8%), 결제 +15.5%, 클라우드 +12%. 영업익 276억 흑전. GPU 사업 신규 확장.' },
  '080010': { n:8,  t:'D', p:'전시·B2B·철강 유통',
    r:'매출 구성 전시 68.6% / 철강 19.8% / B2B 8.4%. 신제품 카탈리스트 미확인. 데이터 부족.' },
  '033530': { n:17, t:'C', p:'자동차 배기시스템 + 수소차 분리판',
    r:'현대차/기아 1차 밴더. 3Q 매출 4,688억(+6.6%) 영업익 247억(+79.3%). 수소차 분리판·SBW 신사업 진출.' },
  '101490': { n:27, t:'A', p:'EUV 블랭크마스크·펠리클',
    r:'EUV 펠리클 90% 투과율 글로벌 2호 양산 임박. 용인 EUV 전용센터 25.10 완공. 3Q 누적 매출 +37.7% 영업익 +45.5%.' },
  '214450': { n:22, t:'B', p:'리쥬란 스킨부스터',
    r:'리쥬란 국내 1위 + 미국·유럽 매출 본격화. 3Q 매출 1,354억(+51.8%) 영업익 619억(+77%, OPM 45.7%). 단 의료기기 내수 -6%, 피크아웃 우려.' },
  '267270': { n:17, t:'C', p:'굴착기·신흥국',
    r:'중동·아프리카 +68%, 중남미 +46% 신흥국 강세. 4Q 매출 9,360억(+18.6%). 단 1Q는 -7.4% 변동성.' },
  '099410': { n:18, t:'B', p:'조선 의장 배관 (LNG)',
    r:'조선 배관 본업. LNG선 수요 증가 수혜. 1H25 매출 +29.5% 영업익 +71.3%.' },
};

const final = rows21_40.map(r => {
  const nm = N[r.code];
  return {
    ...r,
    n_score: nm?.n || 0,
    n_tier: nm?.t || '?',
    n_product: nm?.p || '',
    n_rationale: nm?.r || '',
    total_5axis: r.total_4axis + (nm?.n || 0),
  };
});
final.sort((a, b) => b.total_5axis - a.total_5axis);

// Markdown
let md = `# 2025-11-25 시점 CAN SLIM Ranking 21~40 (점-시점 재구성)

> Top 20 와 동일 방법론. 4축(C·A·S·L) 점-시점 + N 11/25 이전 자료 기준 직접 채점.

## 5축 합산 (21~40위 재정렬)

| 잠정순위 | 코드 | 종목명 | 시장 | 시총(억) | C/100 | A/50 | N/30 | S/60 | L/99 | **합산** | 신고가대비 | 1Y |
|---:|:-:|:-|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
`;

for (let i = 0; i < final.length; i++) {
  const r = final[i];
  md += `| ${i + 21} | ${r.code} | ${r.name} | ${r.market} | ${(r.market_cap_eok||0).toLocaleString()} | ${r.c_score.toFixed(0)} | ${r.a_score} | ${r.n_score} | ${r.s_score} | ${r.l_score} | **${r.total_5axis.toFixed(0)}** | ${r.pct_from_52w_high}% | ${r.return_1y_pct}% |\n`;
}

md += `\n## N 점수 상세\n\n| 코드 | 종목 | N | 핵심제품 | 채점 근거 |\n|:-:|:-|:-:|:-|:-|\n`;
for (const r of final) {
  md += `| ${r.code} | ${r.name} | ${r.n_score} | ${r.n_product} | ${r.n_rationale} |\n`;
}

const outMd = path.join(ROOT, 'out', 'ranking_asof_2025-11-25_rank21-40.md');
fs.writeFileSync(outMd, md);

// CSV
let csv = '잠정순위,코드,종목명,시장,시총(억),C,A,N,S,L,5축합산,신고가대비(%),1Y수익률(%),신고가(원),점-시점종가,N핵심제품,N채점근거\n';
for (let i = 0; i < final.length; i++) {
  const r = final[i];
  const e = (s) => `"${(s || '').replace(/"/g, '""')}"`;
  csv += `${i + 21},${r.code},${e(r.name)},${r.market},${r.market_cap_eok},${r.c_score.toFixed(0)},${r.a_score},${r.n_score},${r.s_score},${r.l_score},${r.total_5axis.toFixed(0)},${r.pct_from_52w_high},${r.return_1y_pct},${r.high_52w},${r.close_asof},${e(r.n_product)},${e(r.n_rationale)}\n`;
}
fs.writeFileSync(path.join(ROOT, 'out', 'ranking_asof_2025-11-25_rank21-40.csv'), csv);

console.log(`Markdown: ${outMd}`);
console.log(`\n21~40위 5축 합산 (재정렬):`);
console.log('순  code   name              시총(억)   C   A   N   S   L  합산  신고대비');
console.log('─'.repeat(95));
for (let i = 0; i < final.length; i++) {
  const r = final[i];
  console.log(
    `${(i + 21).toString().padStart(2)} ${r.code} ${(r.name||'').padEnd(18)} ${(r.market_cap_eok||0).toLocaleString().padStart(9)} ${r.c_score.toFixed(0).padStart(3)} ${r.a_score.toString().padStart(3)} ${r.n_score.toString().padStart(3)} ${r.s_score.toString().padStart(3)} ${r.l_score.toString().padStart(3)} ${r.total_5axis.toFixed(0).padStart(5)} ${(r.pct_from_52w_high+'%').padStart(8)}`,
  );
}

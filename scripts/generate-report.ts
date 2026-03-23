import fs from "fs";
import path from "path";

const prevPath = path.join(process.cwd(), "public/data/2026-03-23.json");
const prev = JSON.parse(fs.readFileSync(prevPath, "utf-8"));

function shiftTs(ts: {날짜: string; 종가: number}[], newDate: string, newValue: number) {
  return [...ts.slice(1), { 날짜: newDate, 종가: newValue }];
}

// 3/23(월) 검증된 데이터 (출처: Seoul Economic Daily, Yahoo Finance, CNBC, Bloomberg)
const report = {
  meta: {
    date: "2026-03-24",
    weekday: "화",
    generated_at: "2026-03-24 08:30:00",
  },

  briefing: `## 오늘의 거시경제 브리핑

**3/23(월) "블랙 먼데이"** — 코스피가 -6.49%(5,405.75), 코스닥이 -5.56%(1,096.89) 폭락했다. 중동 전쟁 격화, 유가 급등, 원화 약세가 겹치며 매도 사이드카가 발동됐다. 3/20(5,781) 대비 이틀간 -6.5% 하락이다.

반면 뉴욕 증시는 반등했다. 트럼프 대통령이 이란 공습 중단을 선언하고 "생산적 대화"를 했다고 밝히면서 다우 +1.38%(+631pt), 나스닥 +1.38%, S&P500 +1.15%로 마감했다. WTI 유가는 $91.4로 -6.9% 급락했다.

원/달러 환율은 1,517.3원으로 17년래 최약세를 기록했다. 외국인 투자자 이탈과 수입물가 부담이 동시에 커지고 있다. 미 2년물 국채 수익률이 6월 이후 처음으로 4%를 돌파했다 — 유가발 인플레 우려로 금리 인하 기대가 후퇴하고 있다.

금 가격이 장중 $4,250 이하까지 급락(2026년 최저)했다가 $4,427로 부분 회복했다. 전통적 안전자산이 작동하지 않는 비정상적 상황이다.

**핵심 관전 포인트**: 한국 시장이 미국 반등 효과를 얼마나 반영할지. 이란 휴전 지속 여부가 유가와 글로벌 심리의 방향을 결정한다.`,

  scenario: {
    "코드": "D",
    "시나리오": "중동 리스크 + 고유가 + 원화 약세 복합 충격",
    "해석": "한국은 블랙먼데이 후폭풍, 미국은 이란 협상 기대 반등. 괴리 존재.",
    "대응": "신규 매수 자제. 이란 협상 결과 확인 후 판단. 환율 안정 시 우량주 분할 매수 검토.",
  },

  indicators: {
    korea: [
      {
        name: "코스피",
        value: 5405.75,
        change: -6.49,
        weekly_change: -6.49,
        trend: "▼▼ 블랙먼데이 급락",
        comment: "매도 사이드카 발동. 3/20 5,781 → 3/23 5,406 (-6.5%). 중동 리스크+고유가+원화약세 삼중고.",
        timeseries: shiftTs(prev.indicators.korea[0].timeseries, "03/23", 5405.75),
      },
      {
        name: "코스닥",
        value: 1096.89,
        change: -5.56,
        weekly_change: -5.56,
        trend: "▼▼ 급락",
        comment: "소형주 급락. 투자 심리 극도로 위축.",
        timeseries: shiftTs(prev.indicators.korea[1].timeseries, "03/23", 1096.89),
      },
    ],
    us: [
      {
        name: "나스닥",
        value: 21946.76,
        change: 1.38,
        weekly_change: 1.38,
        trend: "▲ 반등",
        comment: "트럼프 이란 공습 중단 발표로 기술주 반등",
        timeseries: shiftTs(prev.indicators.us[0].timeseries, "03/23", 21946.76),
      },
      {
        name: "다우존스",
        value: 46208.47,
        change: 1.38,
        weekly_change: 1.38,
        trend: "▲ 반등",
        comment: "이란 협상 기대감에 +631pt 상승",
        timeseries: shiftTs(prev.indicators.us[1].timeseries, "03/23", 46208.47),
      },
      {
        name: "S&P500",
        value: 6581.00,
        change: 1.15,
        weekly_change: 1.15,
        trend: "▲ 반등",
        comment: "전 섹터 안도 랠리. 에너지주는 유가 하락에 약세.",
        timeseries: shiftTs(prev.indicators.us[2].timeseries, "03/23", 6581.00),
      },
    ],
    fx: [
      {
        name: "원/달러",
        value: 1517.3,
        change: 1.11,
        weekly_change: 1.11,
        trend: "▲ 원화 약세 심화",
        comment: "17년래 최약세. 외국인 이탈 + 수입물가 부담 가중.",
        timeseries: shiftTs(prev.indicators.fx[0].timeseries, "03/23", 1517.3),
      },
      {
        name: "달러인덱스",
        value: 99.10,
        change: -0.47,
        weekly_change: -0.47,
        trend: "▼ 약세",
        comment: "이란 긴장 완화로 달러 약세 전환",
        timeseries: shiftTs(prev.indicators.fx[1].timeseries, "03/23", 99.10),
      },
      {
        name: "엔/달러",
        value: 150.35,
        change: -0.3,
        weekly_change: -0.3,
        trend: "▬ 횡보",
        comment: "엔화 소폭 강세",
        timeseries: shiftTs(prev.indicators.fx[2].timeseries, "03/23", 150.35),
      },
    ],
    bonds: [
      {
        name: "미국채10년",
        value: 4.39,
        change: 0,
        weekly_change: 0,
        trend: "▬ 고수준 유지",
        comment: "4.39%대 유지. 유가발 인플레 우려로 하락 제한.",
        timeseries: shiftTs(prev.indicators.bonds[0].timeseries, "03/23", 4.39),
      },
      {
        name: "미국채2년",
        value: 3.97,
        change: 0.77,
        weekly_change: 0.77,
        trend: "▲ 급등",
        comment: "6월 이후 첫 4% 돌파. 유가발 인플레로 금리 인하 기대 후퇴.",
        timeseries: shiftTs(prev.indicators.bonds[1].timeseries, "03/23", 3.97),
      },
    ],
    commodities: [
      {
        name: "WTI유가",
        value: 91.40,
        change: -6.9,
        weekly_change: -6.9,
        trend: "▼▼ 급락",
        comment: "이란 협상 기대감에 $98→$91 급락. 전쟁 프리미엄 축소.",
        timeseries: shiftTs(prev.indicators.commodities[0].timeseries, "03/23", 91.40),
      },
      {
        name: "두바이유",
        value: 134,
        change: 0,
        weekly_change: 0,
        trend: "▬ 데이터 미갱신",
        comment: "WTI 대비 높은 프리미엄 유지. 호르무즈 해협 리스크 반영.",
        timeseries: shiftTs(prev.indicators.commodities[1].timeseries, "03/23", 134),
      },
      {
        name: "VIX",
        value: 26.78,
        change: 0,
        weekly_change: 0,
        trend: "▬ 고수준 유지",
        comment: "변동성 여전히 높음. 20 이하로 내려와야 정상화.",
        timeseries: shiftTs(prev.indicators.commodities[2].timeseries, "03/23", 26.78),
      },
      {
        name: "금",
        value: 4427,
        change: -0.05,
        weekly_change: -0.05,
        trend: "▼ 장중 급락 후 부분 회복",
        comment: "장중 $4,250 이하(2026년 최저) 터치 후 $4,427 회복. 안전자산 역할 의문.",
        timeseries: shiftTs(prev.indicators.commodities[3].timeseries, "03/23", 4427),
      },
      {
        name: "비트코인",
        value: 70600,
        change: 5.0,
        weekly_change: 5.0,
        trend: "▲ 반등",
        comment: "트럼프 이란 협상 발표 후 약 5% 반등.",
        timeseries: shiftTs(prev.indicators.commodities[4].timeseries, "03/23", 70600),
      },
    ],
  },

  spread: {
    "10년물": 4.39,
    "3개월물": 3.73,
    "금리차": 0.66,
    "상태": "정상",
  },

  causal_chain: `**이란 리스크 → 유가 급등 → 한국 블랙먼데이 체인**
\`\`\`
중동 전쟁 격화 (이란)
  → 유가 급등 (WTI $98 수준까지 상승)
  → 한국 수입물가 부담 + 원화 약세 (1,517원)
  → 외국인 매도 가속
  → 코스피 -6.49% 블랙먼데이
\`\`\`

**트럼프 이란 협상 → 미국 반등 체인**
\`\`\`
트럼프, 이란 공습 중단 + "생산적 대화" 발표
  → WTI 유가 $98 → $91 (-6.9%)
  → 인플레이션 재점화 우려 완화
  → 다우 +631pt (+1.38%), 나스닥 +1.38%
  → 한국 시장 3/24 갭업 출발 기대
\`\`\``,

  investment_direction: `**1) 반드시 알고 있어야 하는 사실**

- 코스피가 **5,405.75**로 전일 대비 **-6.49% 폭락**했다(블랙먼데이). 매도 사이드카 발동.
- 트럼프가 이란 공습 **중단**을 선언하고 협상에 나섰다. 미국 증시는 반등.
- WTI 유가가 **$91.4**로 -6.9% 급락했다. 이란 협상 기대감.
- 원/달러 환율이 **1,517.3원**으로 **17년래 최약세**. 수입물가·외국인 이탈 이중 압박.
- 미 2년물 국채 수익률이 **4% 돌파**(6월 이후 최초). 금리 인하 기대 후퇴.
- VIX **26.78**로 높은 변동성 지속. 감정적 매매 경계.
- 금이 장중 **$4,250**(2026년 최저)까지 급락 후 반등. 안전자산 역할 의문.

**2) 유리한 항목과 불리한 항목**

| 구분 | 항목 |
|------|------|
| 🟢 유리 | 수출주 (원화 약세 수혜), 미국 반등 효과로 갭업 기대 |
| 🟡 관망 | 저평가 우량주 (블랙먼데이로 가격 하락했으나 추세 미확인) |
| 🔴 불리 | 해외 자산 신규 매수 (환율 1,517원), 레버리지 (VIX 26+) |

**3) 이번 주 지켜봐야 할 주제**

**이란 협상 진행 상황**
- 왜 중요한가: 협상 성공 → 유가 추가 하락 → 인플레 완화 → 증시 반등. 협상 결렬 → 유가 재급등 → 추가 하락.
- 어떻게 대응할까: 협상 결과 나올 때까지 관망. 확정 시 분할 매수 검토.

**코스피 5,400선 지지 여부**
- 왜 중요한가: 블랙먼데이 후 미국 반등 효과 반영 시 기술적 반등 가능. 5,400 이탈 시 추가 하락 우려.
- 어떻게 대응할까: 워치리스트 B등급 이상 종목 중 목표가 근접 종목 모니터링.

**원/달러 환율 안정화**
- 왜 중요한가: 1,517원은 17년래 최약세. 환율 안정 → 외국인 매도 완화 → 코스피 반등 동력.
- 어떻게 대응할까: 정부 개입 여부, 1,500원 이하 안착 여부 확인.`,

  news: [
    { 제목: "\"블랙 먼데이\" — 코스피 -6.49% 폭락, 코스닥 -5.56% 급락, 매도 사이드카 발동", 링크: "https://en.sedaily.com/finance/2026/03/23/kospi-plunges-over-6-percent-as-soaring-oil-won-and-rate", 출처: "서울경제", 날짜: "2026-03-23" },
    { 제목: "트럼프, 이란 공습 중단 선언 — \"생산적 대화\" 진행. 미 증시 급반등", 링크: "https://finance.yahoo.com/news/live/stock-market-today-dow-sp-500-nasdaq-futures-soar-as-trump-postpones-iran-strike-citing-very-good-talks-230122467.html", 출처: "Yahoo Finance", 날짜: "2026-03-23" },
    { 제목: "WTI 유가 $91.4로 -6.9% 급락 — 이란 협상 기대감", 링크: "https://www.cnbc.com/2026/03/23/oil-prices-trump-iran-strait-of-hormuz-wti-crude-middle-east-lng-gas.html", 출처: "CNBC", 날짜: "2026-03-23" },
    { 제목: "원/달러 1,517원 — 17년래 최약세 기록", 링크: "https://www.koreaherald.com/article/10700238", 출처: "Korea Herald", 날짜: "2026-03-23" },
    { 제목: "미 2년물 국채 수익률 4% 돌파 — 6월 이후 첫. 금리 인하 기대 후퇴", 링크: "https://www.bloomberg.com/news/articles/2026-03-23/us-two-year-bond-yield-climbs-to-4-for-first-time-since-june", 출처: "Bloomberg", 날짜: "2026-03-23" },
    { 제목: "금값 장중 $4,250 급락(2026년 최저) 후 $4,427 회복", 링크: "https://finance.yahoo.com/personal-finance/investing/article/gold-price-today-monday-march-23-gold-briefly-falls-below-4300-its-lowest-price-of-2026-104957419.html", 출처: "Yahoo Finance", 날짜: "2026-03-23" },
    { 제목: "다우 +631pt 반등, S&P500 +1.15% — 이란 휴전 기대", 링크: "https://finance.yahoo.com/news/live/stock-market-today-dow-sp-500-nasdaq-futures-soar-as-trump-postpones-iran-strike-citing-very-good-talks-230122467.html", 출처: "Yahoo Finance", 날짜: "2026-03-23" },
    { 제목: "비트코인 $70,600 — 트럼프 발표 후 약 5% 반등", 링크: "https://fortune.com/article/price-of-bitcoin-03-23-2026/", 출처: "Fortune", 날짜: "2026-03-23" },
  ],

  cpi_gdp: prev.cpi_gdp,

  divergence: `### ⚠️ 괴리 감지

> 🇺🇸 **미국 괴리**: 나스닥이 반등했으나 GDP 0.7%(저성장) + WTI $91(고유가) 조합은 스태그플레이션 우려를 유지시킨다. 이란 협상 실패 시 재차 급락 가능.

> 🇰🇷 **한국 급락 괴리**: 코스피 5,406은 3/20(5,781) 대비 -6.5%. 미국은 반등했는데 한국만 폭락한 것은 원화 약세(1,517원)와 외국인 매도가 추가 변수로 작용한 것. 미국 반등 효과 반영 시 기술적 반등 여지 있으나, 환율 불안 지속 시 제한적.`,

  asset_recommendation: prev.asset_recommendation,

  historical: prev.historical.map((h: Record<string, unknown>) => {
    if (h.name === "코스피") return { ...h, current: 5405.75, percentile: 84.9, judgment: "🟡 고점에서 조정 — 블랙먼데이 -6.5%" };
    if (h.name === "나스닥") return { ...h, current: 21946.76 };
    if (h.name === "원/달러") return { ...h, current: 1517.3, percentile: 92.1, judgment: "🔴 원화 극약세 — 17년래 최저, 수입물가 부담 극심" };
    if (h.name === "WTI유가") return { ...h, current: 91.40, percentile: 71.5, judgment: "🔴 유가 높음 — 인플레이션 압력" };
    if (h.name === "금") return { ...h, current: 4427, percentile: 82.4, judgment: "🟡 금 고점에서 급락 중 — 장중 2026년 최저 터치" };
    if (h.name === "VIX") return { ...h, current: 26.78, judgment: "🔴 높은 변동성 — 불안심리 확산, 급등락 주의" };
    if (h.name === "미국채10년") return { ...h, current: 4.39, judgment: "🔴 금리 높음 — 주식 밸류에이션 압박" };
    if (h.name === "달러인덱스") return { ...h, current: 99.10 };
    return h;
  }),

  longterm_charts: prev.longterm_charts,
};

const outPath = path.join(process.cwd(), "public/data/2026-03-24.json");
fs.writeFileSync(outPath, JSON.stringify(report, null, 2), "utf-8");
console.log(`Report generated: ${outPath}`);
console.log(`Size: ${fs.statSync(outPath).size} bytes`);

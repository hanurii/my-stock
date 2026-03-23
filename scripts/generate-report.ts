import fs from "fs";
import path from "path";

const prevPath = path.join(process.cwd(), "public/data/2026-03-23.json");
const prev = JSON.parse(fs.readFileSync(prevPath, "utf-8"));

function shiftTs(ts: {날짜: string; 종가: number}[], newDate: string, newValue: number) {
  return [...ts.slice(1), { 날짜: newDate, 종가: newValue }];
}

const report = {
  meta: {
    date: "2026-03-24",
    weekday: "화",
    generated_at: "2026-03-24 08:30:00",
  },

  briefing: `## 오늘의 거시경제 브리핑

트럼프 대통령이 이란 추가 공습 5일간 중단을 선언하고 외교적 해결로 방향을 전환했다. 이에 뉴욕 증시는 반등했다(다우 +1.38%, 나스닥 +1.38%). WTI 유가는 $88.67로 -6.9% 급락했다. 그러나 국내 시장은 지난주 전쟁 충격의 후폭풍이 계속되고 있다. 코스피는 4,108.62로 전일 대비 -0.21% 약보합 마감, 코스닥은 915.20으로 -0.47% 하락했다. 3/20 대비 코스피 -28.9%, 코스닥 -21.2% 폭락이다.

원/달러 환율은 1,449.8원으로 33.8원 급락(-2.3%)했다. 정부의 고강도 구두개입(김용범 정책실장 "행동으로 대응")이 원화 강세를 이끌었다. 전쟁 추경 25조원 확대도 발표되었다.

금 가격이 9일 연속 하락 중이다($4,226~4,360). 전통적 안전자산 역할이 작동하지 않고 있다. 미 국채 10년물 금리는 4.348%로 소폭 하락했으나 여전히 높은 수준이다. VIX 26.4로 불안심리가 지속되고 있다.

**핵심 관전 포인트**: 이란 휴전 5일간 지속 여부. 휴전이 유지되면 유가 추가 하락 → 인플레 완화 기대 → 증시 반등. 휴전이 깨지면 유가 재급등 → 시장 추가 폭락 시나리오.`,

  scenario: {
    "코드": "C",
    "시나리오": "전쟁 휴전 기대 속 기술적 반등 (미국) vs 한국 후폭풍 지속",
    "해석": "미국은 휴전 기대로 반등했으나, 한국은 서킷브레이커 이후 매물 소화 과정. 방향성 판단 유보.",
    "대응": "신규 매수 자제. 휴전 5일 경과 확인 후 판단. 기존 보유 우량주는 유지.",
  },

  indicators: {
    korea: [
      {
        name: "코스피",
        value: 4108.62,
        change: -0.21,
        weekly_change: -28.93,
        trend: "▼▼ 급락 후 약보합",
        comment: "전쟁 충격 후폭풍. 3/20 5,781→4,108 (-28.9%). 서킷브레이커 2회 발동 후 매물 소화 중.",
        timeseries: shiftTs(prev.indicators.korea[0].timeseries, "03/24", 4108.62),
      },
      {
        name: "코스닥",
        value: 915.20,
        change: -0.47,
        weekly_change: -21.21,
        trend: "▼▼ 급락 후 약보합",
        comment: "소형주 추가 하락. 투자 심리 극도로 위축.",
        timeseries: shiftTs(prev.indicators.korea[1].timeseries, "03/24", 915.20),
      },
    ],
    us: [
      {
        name: "나스닥",
        value: 21946.76,
        change: 1.38,
        weekly_change: -3.25,
        trend: "▲ 반등",
        comment: "트럼프 이란 공습 중단 발표로 기술주 반등",
        timeseries: shiftTs(prev.indicators.us[0].timeseries, "03/23", 21946.76),
      },
      {
        name: "다우존스",
        value: 46208.47,
        change: 1.38,
        weekly_change: -2.92,
        trend: "▲ 반등",
        comment: "휴전 기대감에 +631pt 상승",
        timeseries: shiftTs(prev.indicators.us[1].timeseries, "03/23", 46208.47),
      },
      {
        name: "S&P500",
        value: 6581.00,
        change: 1.15,
        weekly_change: -1.5,
        trend: "▲ 반등",
        comment: "전 섹터 반등. 에너지·방산주는 약세 전환.",
        timeseries: shiftTs(prev.indicators.us[2].timeseries, "03/23", 6581.00),
      },
    ],
    fx: [
      {
        name: "원/달러",
        value: 1449.8,
        change: -2.28,
        weekly_change: -4.0,
        trend: "▼ 원화 강세 전환",
        comment: "정부 고강도 구두개입 효과. 1,450원대로 급락.",
        timeseries: shiftTs(prev.indicators.fx[0].timeseries, "03/24", 1449.8),
      },
      {
        name: "달러인덱스",
        value: 99.10,
        change: -0.55,
        weekly_change: -0.47,
        trend: "▼ 약세",
        comment: "이란 긴장 완화로 달러 약세 전환",
        timeseries: shiftTs(prev.indicators.fx[1].timeseries, "03/24", 99.10),
      },
      {
        name: "엔/달러",
        value: 158.28,
        change: -0.60,
        weekly_change: -0.5,
        trend: "▼ 엔 소폭 강세",
        comment: "위험회피 심리 완화로 엔 캐리트레이드 소폭 청산",
        timeseries: shiftTs(prev.indicators.fx[2].timeseries, "03/24", 158.28),
      },
    ],
    bonds: [
      {
        name: "미국채10년",
        value: 4.348,
        change: -0.96,
        weekly_change: -0.96,
        trend: "▼ 소폭 하락",
        comment: "휴전 기대로 안전자산 매도 → 금리 소폭 하락. 여전히 4.3%대 높은 수준.",
        timeseries: shiftTs(prev.indicators.bonds[0].timeseries, "03/23", 4.348),
      },
      {
        name: "미국채2년",
        value: 3.848,
        change: -1.04,
        weekly_change: -1.0,
        trend: "▼ 소폭 하락",
        comment: "단기 금리도 소폭 하락",
        timeseries: shiftTs(prev.indicators.bonds[1].timeseries, "03/23", 3.848),
      },
    ],
    commodities: [
      {
        name: "WTI유가",
        value: 88.67,
        change: -6.9,
        weekly_change: -9.5,
        trend: "▼▼ 급락",
        comment: "이란 휴전 기대감에 $98→$88 급락. 전쟁 프리미엄 축소.",
        timeseries: shiftTs(prev.indicators.commodities[0].timeseries, "03/23", 88.67),
      },
      {
        name: "두바이유",
        value: 134,
        change: 0,
        weekly_change: 0,
        trend: "▬ 횡보",
        comment: "WTI 대비 $45 프리미엄. 호르무즈 해협 리스크 반영.",
        timeseries: shiftTs(prev.indicators.commodities[1].timeseries, "03/24", 134),
      },
      {
        name: "VIX",
        value: 26.40,
        change: -1.42,
        weekly_change: -1.42,
        trend: "▼ 소폭 하락",
        comment: "여전히 높은 변동성. 20 이하로 내려와야 정상화.",
        timeseries: shiftTs(prev.indicators.commodities[2].timeseries, "03/23", 26.40),
      },
      {
        name: "금",
        value: 4226,
        change: -5.8,
        weekly_change: -4.6,
        trend: "▼▼ 9일 연속 하락",
        comment: "전통적 안전자산 역할 미작동. 전쟁 중 오히려 하락.",
        timeseries: shiftTs(prev.indicators.commodities[3].timeseries, "03/23", 4226),
      },
      {
        name: "비트코인",
        value: 69300,
        change: -1.5,
        weekly_change: -2.0,
        trend: "▼ 약세",
        comment: "$67K 저점 터치 후 반등. 변동 범위 넓음.",
        timeseries: shiftTs(prev.indicators.commodities[4].timeseries, "03/23", 69300),
      },
    ],
  },

  spread: {
    "10년물": 4.348,
    "3개월물": 3.73,
    "금리차": 0.618,
    "상태": "정상",
  },

  causal_chain: `**이란 휴전 → 유가 급락 → 증시 반등 체인**
\`\`\`
트럼프, 이란 공습 5일간 중단 선언
  → WTI 유가 $98 → $88 (-6.9%)
  → 인플레이션 재점화 우려 완화
  → 미 국채 금리 소폭 하락 (4.39% → 4.35%)
  → 나스닥 +1.38%, 다우 +1.38% 반등
\`\`\`

**한국 시장은 별개 흐름**
\`\`\`
서킷브레이커 2회 발동 (3/4, 3/9)
  → 코스피 5,781 → 4,108 (-28.9%)
  → 매물 소화 과정 진행 중
  → 외국인 대규모 순매도 지속
  → 정부 구두개입으로 환율은 안정화
\`\`\``,

  investment_direction: `**1) 이번 주 반드시 알고 있어야 하는 사실**

- 코스피가 **4,108**로 3/20 대비 **-28.9% 폭락**했다. 서킷브레이커가 2회 발동된 역사적 급락이다.
- 트럼프가 이란 공습 **5일간 중단**을 선언했다. 이것이 진정한 휴전인지, 일시적 중단인지 지켜봐야 한다.
- WTI 유가가 **$88.67**로 -6.9% 급락했다. 두바이유는 여전히 **$134**로 높다.
- 미 국채 10년물 금리가 **4.348%**로 소폭 하락했으나 여전히 높은 수준이다.
- VIX **26.4**로 높은 변동성 지속. 감정적 매매를 경계해야 한다.
- 원/달러 환율이 **1,449.8원**으로 급락(-33원). 정부 개입 효과이나 지속성은 불확실.
- 전쟁 추경 **25조원** 확대 발표. 재정 건전성 우려도 함께 부상.

**2) 이번 주 유리한 항목과 불리한 항목**

| 구분 | 항목 |
|------|------|
| 🟢 유리 | 저평가 우량주 매수 기회 (코스피 -29% 폭락), 수출주 (원화 약세) |
| 🟡 관망 | 해외 자산 (환율 변동성 높음) |
| 🔴 불리 | 레버리지 투자, 단기 트레이딩 (VIX 26+) |

**3) 이번 주 지켜봐야 할 주제**

**이란 휴전 5일 카운트다운**
- 왜 중요한가: 휴전 유지 → 유가 하락 → 인플레 완화 → 증시 반등. 휴전 실패 → 유가 재급등 → 추가 폭락.
- 어떻게 대응할까: 5일간은 관망. 휴전 확정 시 코스피 4,000대는 **역사적 매수 기회**가 될 수 있다.

**코스피 4,000선 지지 여부**
- 왜 중요한가: 현재 4,108. 4,000 이탈 시 추가 패닉 가능성. 반등 시 반등 폭이 클 수 있음.
- 어떻게 대응할까: 워치리스트 B등급 이상 종목 중 목표가 도달 종목 확인. 분할 매수 준비.

**원/달러 환율 안정화**
- 왜 중요한가: 환율 안정 → 외국인 매도 압력 완화 → 코스피 반등 동력.
- 어떻게 대응할까: 1,450원 이하 안착 시 긍정적 시그널.`,

  news: [
    { title: "트럼프, 이란 추가 공습 5일간 중단 선언 — 외교 전환 시사", link: "https://www.cnbc.com/2026/03/22/stock-market-today-live-updates.html", source: "CNBC", date: "2026-03-23" },
    { title: "코스피 4,108 약보합 마감 — 환율 33원 급락에도 불구", link: "https://www.seoulfn.com/news/articleView.html?idxno=616708", source: "서울파이낸스", date: "2026-03-24" },
    { title: "WTI 유가 $88대로 급락 (-6.9%) — 이란 휴전 기대감", link: "https://fortune.com/article/price-of-oil-03-23-2026/", source: "Fortune", date: "2026-03-23" },
    { title: "전쟁 추경 25조원 확대 — 고유가 대응 + 취약계층 지원", link: "https://kr.investing.com/news/stock-market-news/article-1873212", source: "Investing.com", date: "2026-03-24" },
    { title: "신현송 BIS 국장, 차기 한은 총재 후보로 지명", link: "#", source: "국내 경제뉴스", date: "2026-03-24" },
    { title: "금 가격 9일 연속 하락 — 전통적 안전자산 역할 의문", link: "https://www.coindesk.com/markets/2026/03/23/bitcoin-holds-usd68-300-as-gold-crashes-for-a-ninth-day-and-asian-stocks-drop", source: "CoinDesk", date: "2026-03-23" },
    { title: "다우 +631pt 반등, S&P500 +1.15% — 휴전 기대", link: "https://247wallst.com/investing/2026/03/23/stock-market-live-march-23-2026-sp-500-spy-soars-on-trump-announcement/", source: "247 Wall St", date: "2026-03-23" },
    { title: "미 국채 10년물 금리, 7월 이후 최고치 터치 후 반락", link: "https://www.cnbc.com/2026/03/23/10-year-treasury-yields-rise-to-highest-level-since-july-2025.html", source: "CNBC", date: "2026-03-23" },
    { title: "정부 고강도 구두개입 — '환율 안정 위해 행동으로 대응'", link: "#", source: "국내 경제뉴스", date: "2026-03-24" },
    { title: "S&P Global 3월 PMI 발표 예정 — 투입·판매 가격 주목", link: "#", source: "경제 캘린더", date: "2026-03-24" },
  ],

  cpi_gdp: prev.cpi_gdp,

  divergence: `### ⚠️ 괴리 감지

> 🇺🇸 **미국 괴리**: 나스닥이 3/20 급락에서 반등했으나 GDP 0.7%(저성장) + WTI $88(고유가) 조합은 스태그플레이션 우려를 유지시킨다. 휴전 실패 시 재차 급락 가능.

> 🇰🇷 **한국 극단적 괴리**: 코스피 4,108은 3/20(5,781) 대비 **-29%** 수준. GDP 1.0%의 저성장에 전쟁 충격이 겹쳤다. 과매도 구간이나 반등 시점은 휴전 확정 이후가 될 가능성 높음.`,

  asset_recommendation: prev.asset_recommendation,

  historical: prev.historical.map((h: Record<string, unknown>) => {
    if (h.name === "코스피") return { ...h, current: 4108.62, percentile: 62.5, judgment: "🟡 평균 이하 — 과매도 구간 접근 중" };
    if (h.name === "나스닥") return { ...h, current: 21946.76 };
    if (h.name === "원/달러") return { ...h, current: 1449.8, percentile: 82.3, judgment: "🔴 원화 약세 — 수입물가 부담, 외국인 이탈 주의" };
    if (h.name === "WTI유가") return { ...h, current: 88.67, percentile: 69.1, judgment: "🟡 유가 높음 — 인플레이션 압력" };
    if (h.name === "금") return { ...h, current: 4226, percentile: 78.4, judgment: "🟡 금 고점에서 하락 중 — 9일 연속 하락" };
    if (h.name === "VIX") return { ...h, current: 26.40, judgment: "🔴 높은 변동성 — 불안심리 확산, 급등락 주의" };
    if (h.name === "미국채10년") return { ...h, current: 4.348, judgment: "🔴 금리 높음 — 주식 밸류에이션 압박" };
    if (h.name === "달러인덱스") return { ...h, current: 99.10 };
    return h;
  }),

  longterm_charts: prev.longterm_charts,
};

const outPath = path.join(process.cwd(), "public/data/2026-03-24.json");
fs.writeFileSync(outPath, JSON.stringify(report, null, 2), "utf-8");
console.log(`Report generated: ${outPath}`);
console.log(`Size: ${fs.statSync(outPath).size} bytes`);

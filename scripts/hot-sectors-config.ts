// 핫 섹터/테마 페이지용 정적 설정.
//
// - GLOBAL_SECTOR_ETFS: 글로벌 GICS 11개 SPDR 섹터 ETF
// - KOREA_SECTOR_SEEDS: 한국 핫섹터 후보 + 대표 종목 코드 (시총가중 집계 대상)
// - KOREA_THEME_SEEDS: 한국 테마 + 대표 종목 + 뉴스 키워드
// - SECTOR_ETFS / THEME_ETFS: 사용자가 매수 가능한 한국 ETF 매핑 (코드는 fetch 시 Naver 호출로 검증)
// - LINKAGE_PAIRS: 글로벌 → 한국 연동 페어
// - SCORE_THRESHOLDS: 분류 임계값

export interface ETFCandidate {
  code: string;
  name: string;
  note?: string;
}

export interface SectorSeed {
  wics_name: string;          // UI/조회 키
  gics_mapped: string;        // 글로벌 비교용 라벨
  stock_codes: string[];      // 시총가중 집계 대상
  news_keywords: string[];    // 뉴스 멘션 카운트용
}

export interface ThemeSeed {
  name: string;
  stock_codes: string[];
  news_keywords: string[];
}

// ── 글로벌 GICS 섹터 ETF (S&P 500 SPDR) ──
export const GLOBAL_SECTOR_ETFS = [
  { ticker: "XLK", gics_name: "Information Technology", gics_name_kr: "정보기술" },
  { ticker: "XLF", gics_name: "Financials", gics_name_kr: "금융" },
  { ticker: "XLV", gics_name: "Health Care", gics_name_kr: "헬스케어" },
  { ticker: "XLE", gics_name: "Energy", gics_name_kr: "에너지" },
  { ticker: "XLI", gics_name: "Industrials", gics_name_kr: "산업재" },
  { ticker: "XLY", gics_name: "Consumer Discretionary", gics_name_kr: "임의소비재" },
  { ticker: "XLP", gics_name: "Consumer Staples", gics_name_kr: "필수소비재" },
  { ticker: "XLU", gics_name: "Utilities", gics_name_kr: "유틸리티" },
  { ticker: "XLRE", gics_name: "Real Estate", gics_name_kr: "부동산" },
  { ticker: "XLC", gics_name: "Communication Services", gics_name_kr: "통신서비스" },
  { ticker: "XLB", gics_name: "Materials", gics_name_kr: "소재" },
] as const;

// ── 한국 핫섹터 후보 (대표 종목 시총가중 집계) ──
// 메모 2026-04 기준 9개 핫 섹터 + 추가 후보
export const KOREA_SECTOR_SEEDS: SectorSeed[] = [
  {
    wics_name: "반도체",
    gics_mapped: "Semiconductors & Semi Equipment",
    stock_codes: ["005930", "000660", "042700", "240810", "036930"],
    news_keywords: ["반도체", "메모리", "삼성전자", "SK하이닉스", "파운드리"],
  },
  {
    wics_name: "2차전지",
    gics_mapped: "Electrical Equipment / Batteries",
    stock_codes: ["373220", "006400", "247540", "086520", "066970"],
    news_keywords: ["2차전지", "이차전지", "배터리", "전기차", "양극재", "음극재", "LG에너지솔루션", "삼성SDI"],
  },
  {
    wics_name: "방산",
    gics_mapped: "Aerospace & Defense",
    stock_codes: ["047810", "012450", "272210", "064350"],
    news_keywords: ["방산", "K방산", "K-방산", "한화에어로스페이스", "한국항공우주", "현대로템"],
  },
  {
    wics_name: "조선",
    gics_mapped: "Marine / Shipbuilding",
    stock_codes: ["329180", "010140", "009540", "042660"],
    news_keywords: ["조선", "LNG선", "한화오션", "HD현대중공업", "삼성중공업", "수주"],
  },
  {
    wics_name: "전력/원전",
    gics_mapped: "Utilities / Heavy Equipment",
    stock_codes: ["015760", "034020", "052690", "267260"],
    news_keywords: ["원전", "원자력", "SMR", "두산에너빌리티", "한국전력", "송배전", "변압기"],
  },
  {
    wics_name: "바이오",
    gics_mapped: "Biotechnology",
    stock_codes: ["068270", "207940", "196170", "326030"],
    news_keywords: ["바이오", "셀트리온", "삼성바이오로직스", "신약", "임상", "FDA"],
  },
  {
    wics_name: "반도체기판",
    gics_mapped: "Electronic Components",
    stock_codes: ["009150", "008060", "006405"],
    news_keywords: ["기판", "FCBGA", "삼성전기", "대덕전자"],
  },
  {
    wics_name: "로봇",
    gics_mapped: "Industrial Robotics",
    stock_codes: ["108860", "278470", "094820", "036030"],
    news_keywords: ["로봇", "휴머노이드", "자동화", "협동로봇", "두산로보틱스", "레인보우로보틱스"],
  },
  {
    wics_name: "AI/소프트웨어",
    gics_mapped: "Software & Services",
    stock_codes: ["035420", "035720", "377300", "053800"],
    news_keywords: ["AI", "인공지능", "네이버", "카카오", "생성형 AI", "챗GPT", "LLM"],
  },
  {
    wics_name: "에너지",
    gics_mapped: "Energy",
    stock_codes: ["096770", "010950", "267250"],
    news_keywords: ["에너지", "정유", "유가", "WTI", "SK이노베이션", "S-Oil", "OPEC"],
  },
  {
    wics_name: "자동차",
    gics_mapped: "Automobiles",
    stock_codes: ["005380", "000270", "012330"],
    news_keywords: ["현대차", "기아", "자동차", "현대모비스", "전기차"],
  },
  {
    wics_name: "철강",
    gics_mapped: "Steel & Metals",
    stock_codes: ["005490", "004020", "103140"],
    news_keywords: ["철강", "POSCO", "포스코", "현대제철", "고로"],
  },
];

// ── 한국 테마 (메모 9 섹터 + 5 테마 시드) ──
export const KOREA_THEME_SEEDS: ThemeSeed[] = [
  {
    name: "HBM",
    stock_codes: ["000660", "042700", "005930", "240810"],
    news_keywords: ["HBM", "고대역폭메모리", "HBM3", "HBM4"],
  },
  {
    name: "휴머노이드/로봇",
    stock_codes: ["108860", "278470", "094820", "036030"],
    news_keywords: ["휴머노이드", "로봇", "테슬라 옵티머스"],
  },
  {
    name: "K-방산",
    stock_codes: ["047810", "012450", "272210", "064350"],
    news_keywords: ["K방산", "K-방산", "수출", "방산"],
  },
  {
    name: "K-원전",
    stock_codes: ["052690", "267260", "034020", "015760"],
    news_keywords: ["원전", "SMR", "원자력", "두산에너빌리티"],
  },
  {
    name: "조선 슈퍼사이클",
    stock_codes: ["329180", "010140", "009540", "042660"],
    news_keywords: ["조선", "LNG선", "수주", "한화오션", "HD현대"],
  },
  {
    name: "전력 인프라",
    stock_codes: ["015760", "034020", "108670", "100090"],
    news_keywords: ["전력", "변압기", "송배전", "데이터센터 전력"],
  },
  {
    name: "AI 반도체",
    stock_codes: ["000660", "042700", "240810", "036930", "005930"],
    news_keywords: ["AI 반도체", "엔비디아", "GPU", "HBM"],
  },
  {
    name: "바이오 신약",
    stock_codes: ["068270", "207940", "196170", "302440"],
    news_keywords: ["임상", "FDA", "신약", "바이오시밀러"],
  },
  {
    name: "VC/IPO 회복",
    stock_codes: ["030200", "035420", "035720"],
    news_keywords: ["IPO", "벤처캐피탈", "VC", "공모주"],
  },
  {
    name: "2차전지",
    stock_codes: ["373220", "006400", "247540", "086520", "066970"],
    news_keywords: ["2차전지", "전기차", "배터리", "양극재"],
  },
  {
    name: "반도체 기판",
    stock_codes: ["009150", "008060"],
    news_keywords: ["반도체 기판", "FCBGA", "MLB"],
  },
  {
    name: "AI 소프트웨어",
    stock_codes: ["035420", "035720", "377300", "053800"],
    news_keywords: ["생성형 AI", "LLM", "엔비디아", "AI 모델"],
  },
];

// ── 한국 핫섹터/테마 매수 가능 ETF (코드는 fetch-hot-sectors가 Naver로 실재 여부 검증) ──
// 구현 시 Naver integration API로 각 코드 호출 → 실패 시 "검증 실패" 라벨로 표시
export const SECTOR_ETFS: Record<string, ETFCandidate[]> = {
  "반도체": [
    { code: "091160", name: "KODEX 반도체" },
    { code: "139260", name: "TIGER 200 IT" },
    { code: "469150", name: "ACE AI반도체포커스" },
  ],
  "2차전지": [
    { code: "305540", name: "TIGER 2차전지테마" },
    { code: "364980", name: "TIGER KRX2차전지K-뉴딜" },
  ],
  "방산": [
    { code: "449450", name: "PLUS K방산" },
  ],
  "조선": [
    { code: "466920", name: "SOL 조선TOP3플러스" },
  ],
  "전력/원전": [
    { code: "455090", name: "TIGER 원자력테마" },
  ],
  "바이오": [
    { code: "244580", name: "KODEX 바이오" },
    { code: "143860", name: "TIGER 헬스케어" },
  ],
  "반도체기판": [],
  "로봇": [
    { code: "445290", name: "KODEX K-로봇액티브" },
  ],
  "AI/소프트웨어": [
    { code: "314250", name: "KODEX 미국나스닥100TR", note: "참고: 미국 IT" },
  ],
  "에너지": [],
  "자동차": [
    { code: "139260", name: "TIGER 200 IT" },
  ],
  "철강": [],
};

export const THEME_ETFS: Record<string, ETFCandidate[]> = {
  "HBM": [
    { code: "469150", name: "ACE AI반도체포커스" },
    { code: "091160", name: "KODEX 반도체" },
  ],
  "휴머노이드/로봇": [
    { code: "445290", name: "KODEX K-로봇액티브" },
  ],
  "K-방산": [
    { code: "449450", name: "PLUS K방산" },
  ],
  "K-원전": [
    { code: "455090", name: "TIGER 원자력테마" },
  ],
  "조선 슈퍼사이클": [
    { code: "466920", name: "SOL 조선TOP3플러스" },
  ],
  "전력 인프라": [],
  "AI 반도체": [
    { code: "469150", name: "ACE AI반도체포커스" },
    { code: "091160", name: "KODEX 반도체" },
  ],
  "바이오 신약": [
    { code: "244580", name: "KODEX 바이오" },
  ],
  "VC/IPO 회복": [],
  "2차전지": [
    { code: "305540", name: "TIGER 2차전지테마" },
  ],
  "반도체 기판": [],
  "AI 소프트웨어": [],
};

// ── 글로벌 → 한국 연동 페어 ──
export const LINKAGE_PAIRS = [
  { global_ticker: "SOXX", kr_sector: "반도체", global_name_kr: "필라델피아 반도체 (SOXX)" },
  { global_ticker: "XBI", kr_sector: "바이오", global_name_kr: "美 바이오 (XBI)" },
  { global_ticker: "ITA", kr_sector: "방산", global_name_kr: "美 방산 (ITA)" },
  { global_ticker: "URA", kr_sector: "전력/원전", global_name_kr: "글로벌 우라늄 (URA)" },
];

// ── 분류 임계값 ──
export const SCORE_THRESHOLDS = {
  REAL_HOT: 70,
  REAL_HOT_THEME: 75,
  EMERGING_SHORT_MOMENTUM: 75,
  IN_PROGRESS_MIN: 50,
  COOLING_6M: 15,
  FAKE_SHORT_SPIKE_PCT: 5,
  FAKE_60D_FLAT_PCT: 2,
  FAKE_VOLUME_5D_RATIO: 3,
  FAKE_VOLUME_20D_RATIO: 1.3,
  FAKE_NEWS_SURGE_PCT: 200,
  FAKE_NEWS_DECOUPLE_PRICE_PCT: 5,
  VOLUME_SUSTAIN_HIGH: 1.3,
};

"""신규 6개 N commentary 를 can-slim-n-candidates.json 에 머지.

5개 종목 (subagent 조사 결과) + 1개 (미래에셋증권우 = 미래에셋증권 복사).
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

N_DATA = Path("C:/Users/hanul/playground/my-stock/public/data/can-slim-n-candidates.json")

NEW_COMMENTS = {
    "003230": {
        "summary": "美·유럽 채널 침투 + 2분기 호실적 + 김정수 부회장 글로벌 전담 체제",
        "new_product": "까르보불닭 납작당면 출시(2025-07), 밀양 2공장 가동(2025-06), 中 자싱 신공장 착공(2027 완공)",
        "new_management": "김정수 부회장이 지주사 대표 사임 → 불닭 글로벌 판로 확대에 전담",
        "new_high_reason": "2Q25 매출 5,531억(+30% YoY)·영업익 1,201억(+34% YoY) + 美 월마트 입점률 90%·코스트코 50% 돌파 + 유럽 +200%대 + 식품 최초 9.7억달러 수출탑 → 8/28 장중 1,642,000원 신고가",
        "sources": [
            {"title": "삼양식품 2분기 영업익 1201억… 전년비 34% 증가", "url": "https://www.moneys.co.kr/article/2025081815043338053"},
            {"title": "[특징주] '불닭볶음면' 인기에...삼양식품, 52주 신고가 경신", "url": "https://www.youthdaily.co.kr/news/article.html?no=194185"},
            {"title": "까르보불닭 납작당면 출시", "url": "https://www.news1.kr/industry/distribution/5839900"},
            {"title": "삼양식품 밀양 2공장 본격 가동", "url": "https://www.newsis.com/view/NISX20250610_0003208092"},
            {"title": "삼양라운드스퀘어 김정수 대표 사임…전문경영인 체제로 전환", "url": "https://www.thinkfood.co.kr/news/articleView.html?idxno=102546"},
            {"title": "삼양식품, 中 자싱 첫 해외공장 (2000억, 2027 완공)", "url": "http://news.bizwatch.co.kr/article/consumer/2024/12/19/0049"},
            {"title": "삼양식품, 업계 최초 '9억불 수출탑'", "url": "https://www.moneys.co.kr/article/2025120409105988212"},
            {"title": "유럽 매출 215% 폭증... 분기 최대 실적", "url": "https://www.insight.co.kr/news/553996"},
        ],
        "researched_at": "2026-05-15",
    },
    "016360": {
        "summary": "1Q 어닝 서프라이즈(순익 4,509억, 컨센 +15.6%) + IBKR 외국인통합계좌 출시",
        "new_product": "IBKR 외국인통합계좌 5월 정식 오픈 (외국인이 자국 증권사에서 한국 주식 직접 거래), 적립식 증여·자녀자산관리 서비스",
        "new_management": None,
        "new_high_reason": "5/4 IBKR 베타 개시 뉴스에 +29% 폭등, 5/6 신고가 149,500원. 5/12 1Q 실적 영업익 6,095억(+82% YoY)·순익 4,509억(+81.5%) 어닝 서프라이즈. 하나/키움 목표가 175,000~180,000원 상향",
        "sources": [
            {"title": "삼성증권은 정말 서양 주식개미를 몰고 왔을까", "url": "https://news.bizwatch.co.kr/article/market/2026/05/07/0038"},
            {"title": "삼성증권, 1분기 순이익 4500억 돌파…역대 최대", "url": "https://biz.heraldcorp.com/article/10735444"},
            {"title": "삼성증권, IBKR과 외국인통합계좌 정식 오픈", "url": "https://www.dt.co.kr/article/12061979"},
            {"title": "삼성증권, 적립식 증여·자녀자산관리 서비스 출시", "url": "https://www.newspim.com/news/view/20260511001238"},
            {"title": "[리포트] 삼성증권 목표가 175,000원 - 하나증권", "url": "https://news.nate.com/view/20260512n05046"},
            {"title": "[리포트] 삼성증권 목표가 180,000원 - 키움증권", "url": "https://news.nate.com/view/20260512n04966"},
        ],
        "researched_at": "2026-05-15",
    },
    "006800": {
        "summary": "국내 증권사 최초 '분기 영업익 1조' 돌파 + 6,354억 역대 최대 주주환원",
        "new_product": "홍콩 '주식+디지털자산 통합 MTS' 6월 오픈(한국 증권사 최초), AI 추천검색 MTS 기능, 해외주식 양도세 신고대행",
        "new_management": None,
        "new_high_reason": "1Q 영업익 1조3,750억(+297%)·순익 1조19억(+288%) 한국 증권사 최초 분기 1조 돌파. 스페이스X 등 평가이익 8,040억 반영. AUM 600조→776조 머니무브. 2/24 결의 6,354억 역대 최대 주주환원(자사주 소각+배당, 환원성향 40%) → 5/6 신고가 83,800원",
        "sources": [
            {"title": "미래에셋증권, 업계 첫 분기 순익 1조 돌파", "url": "https://www.hankyung.com/article/2026051217841"},
            {"title": "분기 순이익 '1조원' 돌파…'로빈후드'보다 성적 높다", "url": "https://www.news1.kr/finance/general-stock/6163738"},
            {"title": "미래에셋증권, 6354억 역대 최대 주주환원안 결의", "url": "https://www.fnnews.com/news/202602241953168171"},
            {"title": "홍콩 '주식·디지털자산 통합 MTS' 6월 오픈", "url": "https://www.news1.kr/finance/general-stock/6137642"},
            {"title": "미래에셋, MTS에 'AI추천검색' 담았다", "url": "https://m.sedaily.com/article/14073972"},
            {"title": "해외주식 양도소득세 신고대행 접수 시작", "url": "https://www.mt.co.kr/stock/2026/04/08/2026040810562955967"},
        ],
        "researched_at": "2026-05-15",
    },
    "068270": {
        "summary": "짐펜트라 美 처방 폭증 + 4Q 사상 최대 실적 + 1.7조 자사주 소각, 이후 美 공장 일회성 비용·약가 인하 우려로 -21% 조정",
        "new_product": "짐펜트라(IBD, 1Q 매출 +294%·美 처방 +185%), 옴리클로(일본 졸레어 바이오시밀러 퍼스트), 스테키마(일본 IV 추가 승인), ADC 4종 美 임상 1상(CT-P70 FDA 패스트트랙)",
        "new_management": "2026-03 주총에서 서진석 단독 대표 추대 공식화, 김형기 대표 퇴임. 2026 JPM 헬스케어 단독 데뷔, 2세 경영·신약 기업 전환 본격화",
        "new_high_reason": "신고가 트리거: 4Q25 영업익 4,722억(+140% YoY, 컨센 +19%), 연간 영업익 1.17조 사상 최대 + 1.7조 자사주 소각(발행주식 4%, 단일 역대 최대) + 짐펜트라 美 가속화 기대. 이후 -21% 조정: 일라이 릴리 인수 美 공장 가동 초기 일회성 비용으로 1Q OPM 28.1%로 둔화 + 구제품 약가 인하 + CPI 쇼크",
        "sources": [
            {"title": "셀트리온, 매출 4조1625억·영업익 1조1685억 사상 최대", "url": "https://www.ezyeconomy.com/news/articleView.html?idxno=231950"},
            {"title": "증권가 목표치 줄상향", "url": "https://biz.heraldcorp.com/article/10647859"},
            {"title": "짐펜트라, 美 1분기 처방량 185%↑", "url": "https://www.newspim.com/news/view/20260508000160"},
            {"title": "셀트리온, 1.7조 자사주 소각…역대 최대 주주환원", "url": "https://biz.heraldcorp.com/article/10707204"},
            {"title": "일본서 옴리클로·아이덴젤트 품목허가 승인", "url": "https://www.kpanews.co.kr/news/articleView.html?idxno=531815"},
            {"title": "日서 스테키마 IV 제형 추가 승인", "url": "https://biz.heraldcorp.com/article/10721827"},
            {"title": "서진석 단독 데뷔, '하반기 ADC 1상 결과 공개' [JPM2026]", "url": "https://www.sedaily.com/NewsView/2K7ASGBK21"},
            {"title": "셀트리온, 1Q 매출 1.1조·영업익 3219억 분기 최대", "url": "https://pharm.edaily.co.kr/news/read?newsId=03742486645446296"},
            {"title": "셀트리온, 20만원도 깨졌다…바이오 개미 분통", "url": "https://www.wowtv.co.kr/NewsCenter/News/Read?articleId=A202604100426"},
        ],
        "researched_at": "2026-05-15",
    },
    # ── KOSDAQ 신규 발굴 7종목 (2026-05-15) ──
    "080220": {
        "summary": "LPDDR4X 품귀 + 1Q 영업익 +1,714% 폭증으로 신고가 행진",
        "new_product": "LPDDR5x 기반 AI 엣지·AIoT 메모리 솔루션 개발 가속, 퀄컴·미디어텍 5G IoT 칩셋 인증 보유한 국내 유일 메모리 팹리스",
        "new_management": None,
        "new_high_reason": "1Q26 매출 1,805억(+273% YoY)·영업익 671억(+1,714% YoY)·OPM 37% 분기 사상 최대. 글로벌 메모리사 LPDDR4X 감산과 대미 관세 선수요로 품귀, 가격 협상력 확보. D램 가격 2Q +43~48% 추가 상승 전망(트렌드포스), 온디바이스 AI·피지컬 AI 수혜 겹쳐 5/14 +20% 급등",
        "sources": [
            {"title": "[특징주] 제주반도체, 1분기 영업익 1714% 폭증에 장중 20%대 급등 — LPDDR4X 반사이익", "url": "https://www.widedaily.com/news/articleView.html?idxno=294024"},
            {"title": "'슈퍼사이클' 올라탄 제주반도체 매출 3배 이상 껑충", "url": "https://www.fnnews.com/news/202605141430527218"},
            {"title": "제주반도체, 온디바이스 AI·5G IoT 수요 기대에 16.32% 급등 52주 신고가", "url": "https://www.topstarnews.net/news/articleView.html?idxno=15924900"},
            {"title": "[투자 핫플레이스] 국내 유일 LPDDR5 기반 5G IoT 솔루션 보유", "url": "https://www.mt.co.kr/stock/2025/12/26/2025122612367019567"},
            {"title": "[종목이슈] 제주반도체, 온디바이스 AI 'LPDDR' 숨은 진주", "url": "https://www.inews24.com/view/1655131"},
        ],
        "researched_at": "2026-05-15",
    },
    "356860": {
        "summary": "DDR5 + SOCAMM2 글로벌 메모리 2사 퀄 통과로 1년 +467% 신고가",
        "new_product": "SOCAMM2 기판 글로벌 메모리 3사 중 2사 퀄 통과(2026-03), 4Q26 매출 본격화. LPDDR6 SOCAMM PCB도 1사 요청받아 개발 착수(2026-04)",
        "new_management": "1,200억 주주배정 유상증자(발행가 5.79만원)로 베트남 2공장 증설, 생산능력 2만→4만㎡ 2배 확대",
        "new_high_reason": "교보증권 추정 1Q26 매출 747억(+41% YoY)·영업익 95억(+408% YoY) — AI 서버 DDR5/eSSD 호황 본격 반영. SOCAMM2 2사 퀄 통과로 2026 매출 511억(+964%) 신성장축 확보, 메리츠가 목표가·실적 상향 → AI 데이터센터 모멘텀 지속",
        "sources": [
            {"title": "티엘비, AI용 SOCAMM2 기판 메모리 2곳 퀄 통과", "url": "https://www.thelec.kr/news/articleView.html?idxno=52980"},
            {"title": "티엘비, 1200억 유상증자로 베트남 신공장…생산능력 2배", "url": "https://www.thelec.kr/news/articleView.html?idxno=54933"},
            {"title": "티엘비, LPDDR6 적용 SOCAMM 모듈용 기판 개발", "url": "https://www.thelec.kr/news/articleView.html?idxno=55794"},
            {"title": "티엘비, 기판 수요 강세에 기록적 성장세…목표주가↑", "url": "https://www.newsprime.co.kr/news/article/?no=730139"},
            {"title": "[특징주] 티엘비, CXL 기반 메모리 제품 본격 양산화", "url": "https://v.daum.net/v/20251019162502608"},
        ],
        "researched_at": "2026-05-15",
    },
    "095340": {
        "summary": "HBM 3사 공급 시작 + 1Q26 영업익 +237%로 신고가 견인",
        "new_product": "HBM 테스트 소켓 1Q26 첫 납품(삼성 — 소켓+번인테스터 턴키, SK하이닉스 — 소켓), 유리기판·NPU·AI ASIC 소켓으로 라인업 확장. 빅테크 AI칩 테스트 점유율 50% 목표",
        "new_management": "2024-10 SKC가 ISC 인수 → SK엔펄스·앱솔릭스와 시너지로 반도체 소재 분기 최대 매출. SKC 신임 대표 김종우 2026-03 선임",
        "new_high_reason": "1Q26 매출 683억(+115%)·영업익 236억(+237%, OPM 35%) 어닝 서프라이즈. HBM 3사(삼성·SK하이닉스·마이크론) 테스트 솔루션 공급 본격화 임박. AI GPU·ASIC 소켓 +191% YoY·메모리 +159% YoY·데이터센터 매출 542억(+221%, 전사 79.4%) → 4/9 신고가 271,000원",
        "sources": [
            {"title": "ISC, 1분기 영업익 236억원…전년比 237% 증가", "url": "https://zdnet.co.kr/view/?no=20260427100925"},
            {"title": "ISC, HBM 3사 테스트 솔루션 공급 착수···빅테크 AI칩 점유율 50% 목표", "url": "https://www.sisajournal-e.com/news/articleView.html?idxno=419017"},
            {"title": "ISC, HBM 테스트 소켓 개발…내년 1분기 양산", "url": "https://www.hankyung.com/article/2024122350061"},
            {"title": "ISC, 유리기판 테스트 소켓 양산 테스트 완료...HBM·NPU 매출 다각화", "url": "https://www.newspim.com/news/view/20250108000278"},
            {"title": "[2026 주총] SKC, 김종우 신임 대표이사 선임", "url": "https://www.financialpost.co.kr/news/articleView.html?idxno=253174"},
        ],
        "researched_at": "2026-05-15",
    },
    "082920": {
        "summary": "美 군용 드론·미사일 배터리 脫중국 공급망 한국 전환 + 1Q 호실적 + 캐나다 이노바 인수",
        "new_product": "천무 무기체계용 초소형 앰플전지·신관용 중형 앰플전지 양산 본격화. 자폭형 드론용 Li-CFx/MnO2 전지로 라인업 확장, 2026 하반기 양산 공급 예정",
        "new_management": "2025-10 캐나다 Innova Power Solutions 100% 인수(약 336억) 완료 — 북미 고온전지 사업 본격 확장",
        "new_high_reason": "1Q26 매출 683억(+26.6%)·영업익 203억(+34.5%) 컨센 상회, 고온전지 +95.5%·앰플열전지 +22.6%. 美 전쟁부 방한 비공개 회의로 미군 드론·미사일용 특수전지 脫중국 공급망 재편 수혜 부각 + 5/13 신한투자 목표가 6.5만→7.0만원 상향 → 5/11 신고가 64,100원",
        "sources": [
            {"title": "비츠로셀, 성장주 가치 확산에 주목…목표가↑ - 신한", "url": "https://www.g-enews.com/article/Securities/2026/05/20260513083058763444093b5d4e_1"},
            {"title": "[N2 특징주] 비츠로셀 장중 상한가…美 군용 드론 배터리 협력 기대", "url": "https://www.news2day.co.kr/article/20260318500106"},
            {"title": "미군, 드론·미사일 배터리도 '脫중국'… 韓 중소기업으로 공급망 이동", "url": "https://www.thepublic.kr/news/articleView.html?idxno=297877"},
            {"title": "비츠로셀, 방위사업청과 166억 리튬전지 공급 계약", "url": "https://www.newswire.co.kr/newsRead.php?no=1016356"},
            {"title": "비츠로셀, 캐나다 이노바 인수 완료…고온전지 시장 지배력 강화", "url": "https://news.mtn.co.kr/news-detail/2025100214430786495"},
        ],
        "researched_at": "2026-05-15",
    },
    "368770": {
        "summary": "광섬유 자이로 IMU·항법 강자, K방산 + AI 데이터센터 동시 수혜",
        "new_product": "Viavi Solutions(美) 48.9억 IMU 공급(2026-01, AI 인프라·데이터센터·항공우주). 한화에어로스페이스 IM3 발사관용 광센서 조립체 45.6억 장기계약(2026-01~2029-11). 안티재밍 GNSS 융합 통합항법 확대",
        "new_management": "2026-05-12 임시주총서 정관 변경·주식매수선택권(스톡옵션) 부여 안건 부의 — 임원 인센티브 정비",
        "new_high_reason": "2025 연결 매출 +32%·영업익 +40%·순익 +30% 역대 실적, 3분기 단독 매출 2배·영업익 4배 급증. 수출 비중 50% 균형, Viavi(AI 인프라)·Inertial Labs·한화에어로 글로벌 수주 누적, K방산 + AI 데이터센터 광반도체 이중 테마 → 4/17 신고가 26,500원",
        "sources": [
            {"title": "파이버프로, 48억 관성측정장치 미국 수출계약", "url": "https://www.edaily.co.kr/News/Read?newsId=02955286645319688&mediaCodeNo=257"},
            {"title": "파이버프로, 한화에어로스페이스 45.5억 공급계약", "url": "https://www.digitaltoday.co.kr/news/articleView.html?idxno=623836"},
            {"title": "파이버프로, 한화에어로 46억 광센서 조립체 공급계약", "url": "https://www.edaily.co.kr/News/Read?newsId=03617846645321656&mediaCodeNo=257"},
            {"title": "K방산 항법 강자 파이버프로, 3분기 매출 2배 급증", "url": "https://www.hankyung.com/article/202511144675i"},
            {"title": "[특징주] 파이버프로, 69.8억 관성측정장치 공급계약", "url": "https://www.widedaily.com/news/articleView.html?idxno=250435"},
        ],
        "researched_at": "2026-05-15",
    },
    "043260": {
        "summary": "에이디에스테크 인수로 광트랜시버·CPO 밸류체인 진입, 엔비디아·브로드컴 양대 고객 확보",
        "new_product": "자회사 에이디에스테크가 국내 유일 광트랜시버·CPO(Co-Packaged Optics) 정렬 장비 양산, 엔비디아 자회사 멜라녹스에 공급 중. 2026-04 브로드컴과 CPO 칩 테스터 장비 계약 체결, 3분기 양산 발주 기대",
        "new_management": "2021년 취임한 박성재 부회장이 M&A 주도로 콘덴서 → AI 인프라 기업 전환. 송광열 ADS테크 대표가 성호전자 공동대표로 합류",
        "new_high_reason": "2025-12 에이디에스테크 2,800억(87.5%) 인수 공시 후 이틀 연속 상한가 → 2026-02 거래 종결로 연결 편입 → 메리츠·미래에셋 'CPO 밸류체인 핵심' 리포트 + 엔비디아 GTC 2025 CPO 차세대 솔루션 부각 + ADS테크 매출 2023 95억 → 2024 635억(6배), 2026E 매출 903억·영업익 433억 전망 → 4/14 신고가 53,200원",
        "sources": [
            {"title": "성호전자, 에이디에스테크 87.5% 지분 2800억 인수", "url": "https://www.edaily.co.kr/News/Read?newsId=04286966642396552&mediaCodeNo=257"},
            {"title": "성호전자, 엔비디아 협력업체 품었다", "url": "https://www.hankyung.com/article/2025120809061"},
            {"title": "성호전자, 엔비디아 생태계 진입…메리츠證 'CPO 밸류체인 핵심'", "url": "https://www.sedaily.com/article/20010647"},
            {"title": "엔비디아·브로드컴 양산 현실화…미래證, 성호전자 CPO 기술 조명", "url": "https://www.sedaily.com/article/20018406"},
            {"title": "성호전자 ADS테크, 엔비디아 이어 브로드컴과 계약", "url": "https://www.mt.co.kr/stock/2026/04/23/2026042314292289900"},
        ],
        "researched_at": "2026-05-15",
    },
    "036170": {
        "summary": "사명변경 + SMI 인수 + 마이크론 퀄통과 3박자 반도체 소부장 전환주",
        "new_product": "자회사 에스엠아이(SMI)가 차세대 반도체 증착·플라즈마 에칭 공정용 광온도센서(OTS)를 국내 최초 국산화 — 기존 제품 대비 수명 4~6배(1.5→6개월) 연장",
        "new_management": "2025-03 사명을 '클라우드에어' → '에이치엠넥스' 변경. 2025-05 반도체 증착장비 전문 SMI 지분 91.15% 인수 — LED → 반도체 소부장 사업 전환",
        "new_high_reason": "2026-01-08 자회사 SMI 광온도센서가 마이크론 싱가포르 퀄테스트 최종 통과 → 이틀 연속 상한가. 2026 마이크론 월 사용량 10%+, 2027 50~60% 수주 확대 전망. SK하이닉스·삼성전자·TSMC·CXMT 확장 기대 + 용인 반도체 클러스터 입주 → 5/8 신고가 8,770원",
        "sources": [
            {"title": "에이치엠넥스 자회사 광온도센서, 마이크론 품질테스트 통과", "url": "https://www.hankyung.com/article/2026010885996"},
            {"title": "에이치엠넥스 子 SMI, 반도체 핵심부품 광온도센서 국산화…마이크론 퀄 통과", "url": "https://www.edaily.co.kr/News/Read?newsId=02978246645315752&mediaCodeNo=257"},
            {"title": "[특징주] 에이치엠넥스, 마이크론 퀄 테스트 통과에 이틀째 상한가", "url": "https://www.ajunews.com/view/20260109094850788"},
            {"title": "광온도센서로 마이크론 뚫은 에이치엠넥스…다음 관문은 삼성·SK", "url": "https://www.leadeconomy.co.kr/news/articleView.html?idxno=7048"},
        ],
        "researched_at": "2026-05-15",
    },
    "267250": {
        "summary": "1Q 영업익 2.83조(+120%) 지주사 전환 후 분기 최대 + 자회사 조선·전력·정유 트리플 호조 + 자사주 10.5% 소각 검토",
        "new_product": "HD현대일렉트릭 美 앨라배마 제2 변압기 공장 기공(2700억, 765kV 초고압, 2027 준공), 텍사스 200MWh ESS 착공, HD현대로보틱스 2026 하반기 IPO 추진",
        "new_management": "권오갑 명예회장 사임, 정기선 회장·조영철 부회장 공동대표 체제(2026 첫 정기주총). 정기선 회장 '기술 초격차·디지털 전환' 그룹 전략 제시",
        "new_high_reason": "1Q 영업익 2.83조(YoY +120%) 지주사 전환 후 최대. 조선(HD한국조선해양 OPM 16.7%)·전력·건설기계·정유 트리플 호조. 자사주 10.5% 소각 검토(5/13 컨콜) + 배당 900→1,300원. 흥국증권 NAV 재평가로 목표가 37만→40만원 상향 → 4/30 신고가 310,500원",
        "sources": [
            {"title": "HD현대, 1분기 영업익 2조8348억…YoY +120.4%", "url": "https://www.hankyung.com/article/2026051338376"},
            {"title": "1Q 영업익 2.8조 깜짝 실적...조선·정유·전력 트리플 호조", "url": "https://www.newspim.com/news/view/20260513001275"},
            {"title": "[컨콜] HD현대 '자사주 소각 검토'", "url": "https://www.newspim.com/news/view/20260513001122"},
            {"title": "HD현대, 자회사 고른 성장에 재평가…목표가 40만원-흥국", "url": "https://v.daum.net/v/20260514081115749"},
            {"title": "HD현대일렉트릭, 美 제2 변압기 공장 착공", "url": "https://www.g-enews.com/article/Global-Biz/2026/04/2026042809252874130c8c1c064d_1"},
            {"title": "정기선 회장 체제 첫 주총 HD현대 경영 전략", "url": "https://www.getnews.co.kr/news/articleView.html?idxno=866656"},
            {"title": "[자사주 정책 대전환] HD현대, 자사주 활용 5년 공백 깨나", "url": "https://www.bloter.net/news/articleView.html?idxno=640987"},
        ],
        "researched_at": "2026-05-15",
    },
}


def main() -> None:
    n = json.loads(N_DATA.read_text(encoding="utf-8"))
    candidates = n["candidates"]

    # 미래에셋증권우(006805) 는 보통주(006800) commentary 복사
    pref_comment = dict(NEW_COMMENTS["006800"])
    pref_comment["summary"] = "[보통주 미래에셋증권(006800) 데이터 동기화] " + pref_comment["summary"]
    NEW_COMMENTS["006805"] = pref_comment

    # 빈 스켈레톤(summary=None) 도 "코멘트 없음"으로 간주, NEW_COMMENTS 종목은 항상 덮어쓰기
    updated = 0
    for c in candidates:
        if c["code"] in NEW_COMMENTS:
            c["n_commentary"] = NEW_COMMENTS[c["code"]]
            updated += 1
            print(f"  ✓ {c['code']} {c['name']} commentary 적용")

    n["generated_at"] = "2026-05-15"
    N_DATA.write_text(json.dumps(n, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(1 for c in candidates if c.get("n_commentary"))
    print(f"\n총 {len(candidates)}개 중 commentary 보유: {total}개 (이번 추가: {updated}개)")


if __name__ == "__main__":
    main()

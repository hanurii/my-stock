import { Collapsible } from "@/components/Collapsible";
import { getGradeColor } from "@/lib/scoring";

// ── 공통 테이블 ──

function CriteriaTable({ title, icon, maxScore, rows }: {
  title: string;
  icon: string;
  maxScore: number;
  rows: { item: string; max: number; criteria: string }[];
}) {
  return (
    <div className="bg-surface-container-low rounded-xl p-5 ghost-border">
      <div className="flex items-center gap-2 mb-4">
        <span className="material-symbols-outlined text-primary text-lg">{icon}</span>
        <h4 className="text-base font-serif text-on-surface">{title}</h4>
        <span className="text-xs text-on-surface-variant ml-auto">만점 {maxScore}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
              <th className="text-left px-3 pb-2 font-normal">항목</th>
              <th className="text-left px-3 pb-2 font-normal">만점</th>
              <th className="text-left px-3 pb-2 font-normal">기준</th>
            </tr>
          </thead>
          <tbody className="text-on-surface-variant">
            {rows.map((row) => (
              <tr key={row.item} className="border-t border-surface-container-highest/30">
                <td className="px-3 py-2 text-on-surface">{row.item}</td>
                <td className="px-3 py-2 font-mono">{row.max}</td>
                <td className="px-3 py-2">{row.criteria}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function GradeScale() {
  return (
    <div className="bg-surface-container-low rounded-xl p-5 ghost-border">
      <h4 className="text-base font-serif text-on-surface mb-3">등급 기준</h4>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {([
          { grade: "A", range: "80점 초과", label: "강력 매수" },
          { grade: "B", range: "70~80점", label: "매수 검토" },
          { grade: "C", range: "50~69점", label: "워치리스트" },
          { grade: "D", range: "50점 미만", label: "투자 부적합" },
        ] as const).map(({ grade, range, label }) => {
          const color = getGradeColor(grade);
          return (
            <div key={grade} className="flex items-center gap-3 bg-surface-container/30 rounded-lg p-3">
              <span className="text-xl font-serif font-bold" style={{ color }}>{grade}</span>
              <div>
                <p className="text-sm font-mono text-on-surface">{range}</p>
                <p className="text-xs text-on-surface-variant">{label}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 국내 배당주 채점 기준 ──

export function DomesticScoringCriteria() {
  return (
    <Collapsible title="채점 기준표">
      <div className="space-y-6">
        <CriteriaTable
          title="저평가/이익창출력" icon="analytics" maxScore={35}
          rows={[
            { item: "PER", max: 20, criteria: "<5배: 20 · <8배: 15 · <10배: 10 · ≥10배: 5 · 적자: 0" },
            { item: "PBR", max: 5, criteria: "<0.3배: 5 · <0.6배: 4 · <1.0배: 3 · ≥1.0배: 0" },
            { item: "이익 지속가능성", max: 5, criteria: "지속가능: 5 · 불안정: 0" },
            { item: "중복상장 여부", max: 5, criteria: "단독상장: 5 · 중복상장: 0" },
          ]}
        />
        <CriteriaTable
          title="주주환원 의지" icon="volunteer_activism" maxScore={40}
          rows={[
            { item: "배당수익률", max: 10, criteria: ">7%: 10 · >5%: 7 · >3%: 5 · ≤3%: 2" },
            { item: "분기배당", max: 5, criteria: "실시: 5 · 미실시: 0" },
            { item: "배당 연속 인상", max: 5, criteria: "10년+: 5 · 5년+: 4 · 3년+: 3 · 미달/들쑥날쑥: 0" },
            { item: "자사주 소각", max: 7, criteria: "5년 연속: 7 · 3년 연속: 5 · 1년: 3 · 안 함: 0" },
            { item: "소각 비율", max: 8, criteria: ">2%: 8 · >1.5%: 5 · >0.5%: 3 · ≤0.5%: 0" },
            { item: "자사주 보유", max: 5, criteria: "없음(0%): 5 · <2%: 4 · <5%: 2 · ≥5%: 0" },
          ]}
        />
        <CriteriaTable
          title="미래성장/경쟁력" icon="trending_up" maxScore={25}
          rows={[
            { item: "미래 성장 잠재력", max: 10, criteria: "매우 높다: 10 · 높다: 7 · 보통: 5 · 낮다: 3" },
            { item: "기업 경영", max: 10, criteria: "우수한 경영자: 10 · 전문경영자: 5 · 저조: 0" },
            { item: "세계적 브랜드", max: 5, criteria: "있다: 5 · 없다: 0" },
          ]}
        />
        <GradeScale />
      </div>
    </Collapsible>
  );
}

// ── 해외 배당주 채점 기준 ──

export function OverseasScoringCriteria() {
  return (
    <Collapsible title="채점 기준표 — 해외">
      <div className="space-y-6">
        <CriteriaTable
          title="저평가/이익창출력" icon="analytics" maxScore={30}
          rows={[
            { item: "PER", max: 20, criteria: "<8배: 20 · <12배: 15 · <18배: 10 · ≥18배: 5 · 적자: 0" },
            { item: "PBR", max: 5, criteria: "<0.8배: 5 · <1.5배: 4 · <3.0배: 3 · ≥3.0배: 0" },
            { item: "이익 지속가능성", max: 5, criteria: "지속가능: 5 · 불안정: 0" },
          ]}
        />
        <CriteriaTable
          title="주주환원 의지" icon="volunteer_activism" maxScore={45}
          rows={[
            { item: "배당수익률", max: 10, criteria: ">7%: 10 · >5%: 7 · >3%: 5 · ≤3%: 2" },
            { item: "배당 연속 인상", max: 10, criteria: "50년+(King): 10 · 25년+(Aristocrat): 8 · 10년+: 6 · 5년+: 4 · 3년+: 2 · 미달: 0" },
            { item: "Payout Ratio", max: 5, criteria: "<60%: 5 · <80%: 3 · ≥80%/적자: 0" },
            { item: "자사주 소각", max: 7, criteria: "5년 연속: 7 · 3년 연속: 5 · 1년: 3 · 안 함: 0" },
            { item: "소각 비율", max: 8, criteria: ">2%: 8 · >1.5%: 5 · >0.5%: 3 · ≤0.5%: 0" },
            { item: "배당 삭감 이력", max: 5, criteria: "5년 내 없음: 5 · 삭감 후 복원: 2 · 삭감/중단: 0" },
          ]}
        />
        <CriteriaTable
          title="미래성장/경쟁력" icon="trending_up" maxScore={25}
          rows={[
            { item: "미래 성장 잠재력", max: 10, criteria: "매우 높다: 10 · 높다: 7 · 보통: 5 · 낮다: 3" },
            { item: "기업 경영", max: 10, criteria: "우수한 경영 실적: 10 · 보통: 5 · 저조: 0" },
            { item: "세계적 브랜드", max: 5, criteria: "있다: 5 · 없다: 0" },
          ]}
        />
        <GradeScale />
      </div>
    </Collapsible>
  );
}

// ── 성장주 채점 기준 ──

export function GrowthScoringCriteria() {
  return (
    <Collapsible title="채점 기준표">
      <div className="space-y-6">
        <CriteriaTable
          title="성장성" icon="trending_up" maxScore={35}
          rows={[
            { item: "매출 성장률 (3Y CAGR)", max: 8, criteria: ">20%: 8 · >12%: 6 · >5%: 3 · ≤5%: 1" },
            { item: "영업이익 성장률 (3Y CAGR)", max: 8, criteria: ">25%: 8 · >15%: 6 · >5%: 3 · ≤5%: 1" },
            { item: "최근 분기 YoY 영업이익", max: 7, criteria: ">30%: 7 · >15%: 5 · >0%: 3 · ≤0%: 0" },
            { item: "성장 가속도", max: 5, criteria: "분기 > 3Y×2 (강한 가속): 5 · 분기 > 3Y (가속 중): 3 · 둔화·정체: 0" },
            { item: "R&D·설비투자/매출", max: 7, criteria: ">10%: 7 · >5%: 5 · >2%: 3 · ≤2%: 1" },
          ]}
        />
        <div className="bg-surface-container-low rounded-xl p-4 ghost-border">
          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-on-surface-variant text-base mt-0.5">info</span>
            <div className="text-xs text-on-surface-variant leading-relaxed space-y-1">
              <p className="font-serif text-sm text-on-surface">성장 가속도 해석</p>
              <p>최근 분기 YoY 영업이익 성장률이 3년 평균(CAGR)을 넘는지 비교합니다. 3년간 고성장한 종목일수록 최근 분기가 그 평균을 넘기 어렵기 때문에, 대부분의 종목은 &lsquo;둔화·정체&rsquo;에 해당합니다. &lsquo;가속 중&rsquo; 이상이 나오는 종목은 지금 순풍이 불고 있다는 시그널이므로 희소한 가점 항목입니다.</p>
              <p>영업이익 3Y CAGR이 마이너스(역성장)인 종목은 성장주의 핵심 전제가 깨진 상태이므로, D등급(투자 부적합)으로 제한됩니다.</p>
            </div>
          </div>
        </div>
        <CriteriaTable
          title="합리적 밸류에이션" icon="query_stats" maxScore={30}
          rows={[
            { item: "PEG", max: 10, criteria: "<0.5: 10 · <1.0: 8 · <1.5: 5 · <2.0: 2 · ≥2.0: 0 · 적자: −5" },
            { item: "PSR", max: 10, criteria: "<0.5: 10 · <1: 8 · <3: 6 · <5: 3 · <10: 1 · ≥10: 0" },
            { item: "PER", max: 5, criteria: "<15: 5 · <25: 3 · <40: 1 · ≥40: 0 · 적자: −5" },
            { item: "흑자 지속성", max: 5, criteria: "흑자 지속: 5 · 전환 임박: 3 · 적자 지속: −5" },
          ]}
        />
        <div className="bg-surface-container-low rounded-xl p-4 ghost-border">
          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-on-surface-variant text-base mt-0.5">info</span>
            <div className="text-xs text-on-surface-variant leading-relaxed space-y-2">
              <p className="font-serif text-sm text-on-surface">밸류에이션 지표 해석</p>
              <p><strong className="text-on-surface">PEG</strong> = PER &divide; <strong>순이익(EPS)</strong> 성장률. 성장 속도 대비 주가가 싼지 비싼지를 판단합니다. 1.0 미만이면 성장 대비 저평가, 1.0 이상이면 고평가입니다. 순이익 성장률이 음수이면 분모가 음수가 되어 산출 불가(null)로 처리됩니다.</p>
              <p><strong className="text-on-surface">PSR</strong> = 시가총액 &divide; 매출액. 아직 이익이 적은 성장 초기 기업의 가치를 매출 규모로 가늠합니다. 낮을수록 매출 대비 주가가 저렴합니다.</p>
              <p><strong className="text-on-surface">PER</strong> = 주가 &divide; 주당순이익. 현재 이익 대비 주가 수준을 나타냅니다. 성장주는 PER이 높은 편이므로 PEG와 함께 봐야 합니다.</p>
              <p><strong className="text-on-surface">PEG 산출 불가 vs 역성장 등급 상한</strong> — PEG는 <em>순이익(EPS)</em> 성장률 기준이고, 역성장 등급 상한은 <em>영업이익</em> 3Y CAGR 기준입니다. 영업이익은 본업 수익력, 순이익은 영업외비용·일회성 손실까지 포함하므로 결과가 다를 수 있습니다. 영업이익이 성장 중이면 PEG가 산출 불가여도 역성장 등급 상한은 적용되지 않습니다.</p>
            </div>
          </div>
        </div>
        <CriteriaTable
          title="경쟁력/저평가 시그널" icon="shield" maxScore={35}
          rows={[
            { item: "부채비율", max: 6, criteria: "<50%: 6 · <100%: 4 · <200%: 2 · ≥200%: 0" },
            { item: "영업이익률", max: 5, criteria: ">15%: 5 · >8%: 4 · >3%: 2 · ≤3%: 0" },
            { item: "영업이익률 개선", max: 5, criteria: "+5%p 이상: 5 · +2%p 이상: 3 · 소폭 개선: 1 · 악화: 0" },
            { item: "글로벌 확장성", max: 3, criteria: "해외매출 >30%: 3 · >10%: 2 · ≤10%: 0" },
            { item: "종합 경쟁력", max: 8, criteria: "주관적 보수 평가 0~8 (뚜렷한 우위 7+, 보통 4~6, 불명확 ~3)" },
            { item: "시가총액", max: 4, criteria: "<3천억(소형): 4 · <7천억: 3 · <2조: 2 · <10조: 1 · ≥10조: 0" },
            { item: "외국인 보유비중", max: 4, criteria: "<5%: 4 · <10%: 3 · <20%: 2 · <30%: 1 · ≥30%: 0" },
          ]}
        />
        <CriteriaTable
          title="주주환원 보정" icon="volunteer_activism" maxScore={5}
          rows={[
            { item: "자사주 소각", max: 3, criteria: "3년+: +3 · 2년: +2 · 1년: +1 · 없음: 0" },
            { item: "배당 연속성", max: 2, criteria: "4년+: +2 · 2~3년: +1 · 불규칙/없음: 0" },
            { item: "지분 희석 (감점)", max: 0, criteria: "1건당 −5점 (상한 없음)" },
          ]}
        />
        <div className="bg-surface-container-low rounded-xl p-4 ghost-border">
          <div className="flex items-start gap-2">
            <span className="material-symbols-outlined text-on-surface-variant text-base mt-0.5">info</span>
            <p className="text-xs text-on-surface-variant leading-relaxed">
              주주환원 데이터는 DART OpenAPI 기반 최근 5년 이력입니다.
              나쁜 희석(감점 대상): 전환권행사, 신주인수권행사, 유상증자(제3자배정), 주식매수선택권행사, 상환권행사.
              합리적 희석(감점 제외): 유상증자(일반공모/주주우선공모/주주배정), 무상증자, 주식분할 등.
              데이터 미확보 종목은 보정 없이 기존 점수를 유지합니다.
              희석 등급 상한: 10건+ → D 고정 · 5~9건 → C 이하 · 3~4건 → B 이하.
            </p>
          </div>
        </div>
        <div className="bg-surface-container-low rounded-xl p-5 ghost-border">
          <h4 className="text-base font-serif text-on-surface mb-3">금리 환경 감점</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wider text-on-surface-variant/50">
                  <th className="text-left px-3 pb-2 font-normal">기준금리</th>
                  <th className="text-left px-3 pb-2 font-normal">감점</th>
                  <th className="text-left px-3 pb-2 font-normal">환경</th>
                </tr>
              </thead>
              <tbody className="text-on-surface-variant">
                {[
                  { rate: "≤1.5%", penalty: "0", label: "초저금리 — 성장주 최적 환경" },
                  { rate: "≤2.0%", penalty: "−3", label: "저금리" },
                  { rate: "≤2.5%", penalty: "−5", label: "보통" },
                  { rate: "≤3.0%", penalty: "−10", label: "고금리 — 성장주 주의" },
                  { rate: "≤3.5%", penalty: "−13", label: "고금리 — 성장주 위험" },
                  { rate: ">3.5%", penalty: "−15", label: "초고금리 — 극도로 불리" },
                ].map((row) => (
                  <tr key={row.rate} className="border-t border-surface-container-highest/30">
                    <td className="px-3 py-2 font-mono text-on-surface">{row.rate}</td>
                    <td className="px-3 py-2 font-mono text-error">{row.penalty}</td>
                    <td className="px-3 py-2">{row.label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <GradeScale />
      </div>
    </Collapsible>
  );
}

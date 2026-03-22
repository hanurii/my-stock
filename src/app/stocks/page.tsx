export default function StocksPage() {
  return (
    <div className="py-20">
      <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">Undervalued Stocks</p>
      <h2 className="text-4xl font-serif font-bold text-on-surface tracking-tight mb-4">저평가 가치주</h2>
      <p className="text-sm text-on-surface-variant mb-8">재무지표 기반 자동 스크리닝</p>
      <div className="bg-surface-container-low rounded-xl p-8 ghost-border">
        <div className="flex items-center gap-3 text-primary-dim/60">
          <span className="material-symbols-outlined">construction</span>
          <span className="text-sm">섹션 4(재무지표 계산기) 완성 후 오픈 예정</span>
        </div>
      </div>
    </div>
  );
}

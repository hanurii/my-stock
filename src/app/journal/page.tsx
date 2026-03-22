export default function JournalPage() {
  return (
    <div className="py-20">
      <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">Trading Journal</p>
      <h2 className="text-4xl font-serif font-bold text-on-surface tracking-tight mb-4">매매일지</h2>
      <p className="text-sm text-on-surface-variant mb-8">주식 매매 기록 · 수익률 · AI 매매 평가</p>
      <div className="bg-surface-container-low rounded-xl p-8 ghost-border">
        <div className="flex items-center gap-3 text-primary-dim/60">
          <span className="material-symbols-outlined">construction</span>
          <span className="text-sm">준비 중</span>
        </div>
      </div>
    </div>
  );
}

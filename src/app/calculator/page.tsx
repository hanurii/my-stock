export default function CalculatorPage() {
  return (
    <div className="py-20">
      <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">Financial Calculator</p>
      <h2 className="text-4xl font-serif font-bold text-on-surface tracking-tight mb-4">재무지표 계산기</h2>
      <p className="text-sm text-on-surface-variant mb-8">DART 공시 데이터 기반 EPS · PER · PBR 계산</p>
      <div className="bg-surface-container-low rounded-xl p-8 ghost-border">
        <div className="flex items-center gap-3 text-primary-dim/60">
          <span className="material-symbols-outlined">construction</span>
          <span className="text-sm">DART API 키 발급 후 개발 예정</span>
        </div>
      </div>
    </div>
  );
}

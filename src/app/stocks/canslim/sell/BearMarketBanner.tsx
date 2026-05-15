// 약세장 모드 마커 — 현재 강세장 가정. 약세장 도래 시 페이지별 분기 로직 활성화 필요.
// TODO: 약세장 모드 진입 시 -3% 손절 / +15% 익절 분기 로직 추가.

export function BearMarketBanner() {
  return (
    <div className="flex items-center gap-2 rounded-lg ghost-border bg-surface-container/30 px-3 py-2 text-[11px] text-on-surface-variant/70">
      <span className="material-symbols-outlined text-sm text-on-surface-variant/50">
        construction
      </span>
      <span>
        <strong className="text-on-surface-variant/80">약세장 모드 구현 필요</strong> — 장 진입 시 활성. 약세장에서는 책 기준 손절 -3% / 익절 +15%로 더 타이트하게.
      </span>
    </div>
  );
}

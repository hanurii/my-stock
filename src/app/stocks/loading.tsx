export default function StocksLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* 헤더 스켈레톤 */}
      <div className="space-y-3">
        <div className="h-6 w-48 bg-surface-container-high rounded" />
        <div className="h-4 w-96 max-w-full bg-surface-container rounded" />
      </div>

      {/* 카드 스켈레톤 */}
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-surface-container-low rounded-xl ghost-border p-6 space-y-4">
          <div className="flex items-center gap-4">
            <div className="h-8 w-8 bg-surface-container-high rounded" />
            <div className="space-y-2 flex-1">
              <div className="h-5 w-32 bg-surface-container-high rounded" />
              <div className="h-3 w-20 bg-surface-container rounded" />
            </div>
            <div className="h-10 w-16 bg-surface-container-high rounded-lg" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="h-12 bg-surface-container rounded-lg" />
            <div className="h-12 bg-surface-container rounded-lg" />
            <div className="h-12 bg-surface-container rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}

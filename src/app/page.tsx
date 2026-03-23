import { getReportData, getReportDates } from "@/lib/data";
import { ReportView } from "@/components/ReportView";
import Link from "next/link";

export default function Home() {
  const dates = getReportDates();
  const report = getReportData();

  if (!report) {
    return (
      <div className="text-center py-32">
        <h1 className="text-3xl font-serif text-primary mb-4">데이터 없음</h1>
        <p className="text-on-surface-variant text-base">
          리포트 데이터가 아직 생성되지 않았습니다.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-12">
      {/* 날짜별 리포트 목록 */}
      {dates.length > 1 && (
        <section className="bg-surface-container-low rounded-xl p-4 sm:p-6 ghost-border overflow-hidden">
          <h3 className="text-base font-serif text-on-surface mb-4 tracking-tight">
            지난 리포트
          </h3>
          <div className="flex flex-wrap gap-2">
            {dates.map((date, i) => (
              <Link
                key={date}
                href={i === 0 ? "/" : `/report/${date}`}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                  i === 0
                    ? "gold-shimmer text-on-primary font-bold"
                    : "bg-surface-container-high text-on-surface-variant hover:text-primary hover:bg-surface-container-highest"
                }`}
              >
                {date}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* 최신 리포트 */}
      <ReportView report={report} />
    </div>
  );
}

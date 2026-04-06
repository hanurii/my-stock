import { getReportData, getReportDates } from "@/lib/data";
import { ReportView } from "@/components/ReportView";
import { DateNav } from "@/components/DateNav";
import Link from "next/link";

export const dynamicParams = false;

export function generateStaticParams() {
  const dates = getReportDates();
  return dates.map((date) => ({ date }));
}

export default async function ReportPage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const report = getReportData(date);
  const dates = getReportDates();

  if (!report) {
    return (
      <div className="text-center py-32">
        <h1 className="text-3xl font-serif text-primary mb-4">
          {date} 리포트 없음
        </h1>
        <Link href="/" className="text-primary-dim hover:text-primary transition-colors">
          ← 최신 리포트로 돌아가기
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-12">
      {/* 네비게이션 */}
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="flex items-center gap-2 text-primary-dim hover:text-primary transition-colors text-sm shrink-0"
        >
          <span className="material-symbols-outlined text-base">arrow_back</span>
          최신 리포트
        </Link>

        <DateNav dates={dates} activeDate={date} fadeFrom="surface" />
      </div>

      <ReportView report={report} />
    </div>
  );
}

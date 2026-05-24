import fs from "fs";
import path from "path";
import { MarkdownText } from "@/components/MarkdownText";

interface MusingSection {
  heading: string;
  body: string;
}

interface Musing {
  id: string;
  date: string;
  title: string;
  summary: string;
  tags: string[];
  sections: MusingSection[];
}

interface MusingsData {
  updated_at: string;
  musings: Musing[];
}

function getMusingsData(): MusingsData | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "musings.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as MusingsData;
  } catch {
    return null;
  }
}

export default function MusingsPage() {
  const data = getMusingsData();

  if (!data || data.musings.length === 0) {
    return (
      <div className="space-y-14">
        <section>
          <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
            Musings
          </p>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
            고민 한 스푼
          </h2>
          <p className="text-base text-on-surface-variant mt-2">
            거시경제·시장 흐름·매매 전략에 대한 생각 기록
          </p>
        </section>
        <div className="bg-surface-container-low rounded-xl p-10 ghost-border text-center">
          <span className="material-symbols-outlined text-primary-dim/30 text-4xl mb-4 block">
            psychology
          </span>
          <p className="text-lg text-on-surface-variant">아직 기록된 고민이 없습니다</p>
          <p className="text-sm text-on-surface-variant/50 mt-2">
            대화로 정리한 내용이 이 페이지에 누적됩니다
          </p>
        </div>
      </div>
    );
  }

  const { musings } = data;
  const sorted = [...musings].sort((a, b) => b.date.localeCompare(a.date));

  return (
    <div className="space-y-14">
      <section>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary-dim/60 mb-2">
          Musings
        </p>
        <h2 className="text-3xl sm:text-4xl font-serif font-bold text-on-surface tracking-tight">
          고민 한 스푼
        </h2>
        <p className="text-base text-on-surface-variant mt-2">
          거시경제·시장 흐름·매매 전략에 대한 생각 기록 · 총 {musings.length}건
        </p>
      </section>

      <div className="space-y-10">
        {sorted.map((m) => (
          <article
            key={m.id}
            className="bg-surface-container-low rounded-xl ghost-border overflow-hidden"
          >
            <header className="p-6 sm:p-8 pb-4 border-b border-outline-variant/10">
              <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2 mb-3">
                <h3 className="text-2xl font-serif text-on-surface tracking-tight leading-snug">
                  {m.title}
                </h3>
                <p className="text-sm font-mono text-primary-dim/70 shrink-0">
                  {m.date}
                </p>
              </div>
              <p className="text-sm text-on-surface-variant leading-relaxed mb-4">
                <MarkdownText>{m.summary}</MarkdownText>
              </p>
              <div className="flex flex-wrap gap-2">
                {m.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[11px] px-2.5 py-1 rounded-full bg-primary/10 text-primary/80 tracking-wide"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </header>

            <div className="p-6 sm:p-8 space-y-7">
              {m.sections.map((s, i) => (
                <div key={i}>
                  <h4 className="text-base font-serif text-primary mb-2.5 tracking-tight">
                    {s.heading}
                  </h4>
                  <div className="text-sm text-on-surface-variant leading-relaxed whitespace-pre-line">
                    <MarkdownText>{s.body}</MarkdownText>
                  </div>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

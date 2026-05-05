import { getHotSectorsData } from "@/lib/hot-sectors.server";
import { HotSectorsView } from "@/components/HotSectorsView";

export const dynamic = "force-static";

export default function HotSectorsPage() {
  const data = getHotSectorsData();

  if (!data) {
    return (
      <div className="space-y-8">
        <header>
          <h1 className="text-3xl sm:text-4xl font-serif text-primary tracking-tight">
            핫 섹터 / 핫 테마
          </h1>
          <p className="text-sm text-on-surface-variant mt-2">
            5D~6M 추세 + 3주체 매집 + 거래대금 + 뉴스
          </p>
        </header>
        <section className="glass-card rounded-xl ghost-border p-6 text-on-surface-variant">
          데이터가 아직 수집되지 않았습니다. <code>scripts/fetch-hot-sectors.ts</code>를 실행해 주세요.
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-8 sm:space-y-10">
      {/* Header */}
      <header>
        <h1 className="text-3xl sm:text-4xl font-serif text-primary tracking-tight">
          핫 섹터 / 핫 테마
        </h1>
        <p className="text-sm text-on-surface-variant mt-2">
          5D~6M 추세 + 외인·기관·개인 3주체 매집 + 거래대금 + 뉴스 — 모두 보고 직접 판단
        </p>
        <p className="text-[11px] text-on-surface-variant/70 mt-1">
          데이터 출처: {data.meta.source} · 갱신: {data.meta.last_updated} (KST)
          {data.meta.failed_count > 0 ? ` · 실패 ${data.meta.failed_count}종목` : ""}
        </p>
      </header>

      <HotSectorsView data={data} />

      {/* Footer */}
      <footer className="text-[11px] text-on-surface-variant/70 leading-relaxed border-t border-outline-variant/15 pt-4">
        ⚠️ 본 데이터는 시드 종목군에 한한 핫 섹터/테마 추정으로 한국 시장 전체를 대표하지 않을 수 있습니다.
        Naver Finance + Yahoo Finance에서 제공하는 가격·수급·뉴스 데이터를 기반으로 산출된 학습 목적의 참고 자료입니다.
        🔥 진짜 핫이라도 매수 후 분기별 점검 필수.
      </footer>
    </div>
  );
}

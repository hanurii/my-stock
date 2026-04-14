"use client";

import { useState } from "react";
import { BioView } from "./BioView";
import { BigPharmaView } from "./BigPharmaView";

interface BioPageTabsProps {
  pipelines: unknown[];
  briefings: Record<string, unknown>;
  bigpharmaDeals: unknown[];
}

export function BioPageTabs({ pipelines, briefings, bigpharmaDeals }: BioPageTabsProps) {
  const [tab, setTab] = useState<"pipeline" | "bigpharma">("pipeline");

  return (
    <div>
      <div className="flex gap-1 mb-6 bg-surface-container-low rounded-lg p-1">
        <button
          onClick={() => setTab("pipeline")}
          className={`flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-all ${
            tab === "pipeline" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container"
          }`}
        >
          <span className="material-symbols-outlined text-base align-middle mr-1">biotech</span>
          임상 파이프라인 ({pipelines.length})
        </button>
        <button
          onClick={() => setTab("bigpharma")}
          className={`flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-all ${
            tab === "bigpharma" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container"
          }`}
        >
          <span className="material-symbols-outlined text-base align-middle mr-1">handshake</span>
          빅파마가 주목한 기업 ({bigpharmaDeals.length})
        </button>
      </div>

      {tab === "pipeline" ? (
        <BioView pipelines={pipelines as never[]} briefings={briefings as never} />
      ) : (
        <BigPharmaView deals={bigpharmaDeals as never[]} />
      )}
    </div>
  );
}

"use client";

interface Tab {
  id: string;
  label: string;
}

export function HotSectorTabBar({
  tabs,
  active,
  onChange,
}: {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex gap-1 sm:gap-2 overflow-x-auto border-b border-outline-variant/15 -mx-4 sm:-mx-6 px-4 sm:px-6">
      {tabs.map((tab) => {
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`shrink-0 px-3 sm:px-4 py-2.5 text-sm font-medium border-b-2 transition-all ${
              isActive
                ? "border-primary text-primary"
                : "border-transparent text-on-surface-variant hover:text-on-surface"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

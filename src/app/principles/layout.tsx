import { PrinciplesTabs } from "./PrinciplesTabs";

export default function PrinciplesLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-8">
      <PrinciplesTabs />
      {children}
    </div>
  );
}

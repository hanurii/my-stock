import { CanslimNav } from "./CanslimNav";

export default function CanslimLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-6">
      <CanslimNav />
      {children}
    </div>
  );
}

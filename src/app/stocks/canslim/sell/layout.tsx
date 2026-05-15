import { SellNav } from "./SellNav";

export default function SellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <SellNav />
      {children}
    </div>
  );
}

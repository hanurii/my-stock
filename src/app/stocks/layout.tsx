import fs from "fs";
import path from "path";
import { StocksTabs } from "./StocksTabs";

function getBerkshireIsNew(): boolean {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "berkshire-13f.json");
    const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
    return raw.is_new === true;
  } catch {
    return false;
  }
}

export default function StocksLayout({ children }: { children: React.ReactNode }) {
  const berkshireIsNew = getBerkshireIsNew();

  return (
    <div className="space-y-8">
      <StocksTabs berkshireIsNew={berkshireIsNew} />
      {children}
    </div>
  );
}

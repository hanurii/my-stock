import fs from "fs/promises";
import path from "path";
import { StocksTabs } from "./StocksTabs";

async function getBerkshireIsNew(): Promise<boolean> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "berkshire-13f.json");
    const raw = JSON.parse(await fs.readFile(filePath, "utf-8"));
    return raw.is_new === true;
  } catch {
    return false;
  }
}

export default async function StocksLayout({ children }: { children: React.ReactNode }) {
  const berkshireIsNew = await getBerkshireIsNew();

  return (
    <div className="space-y-8">
      <StocksTabs berkshireIsNew={berkshireIsNew} />
      {children}
    </div>
  );
}

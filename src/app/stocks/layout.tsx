import fs from "fs/promises";
import path from "path";
import { StocksTabs } from "./StocksTabs";

async function getBerkshireIsNew(): Promise<boolean> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "berkshire-13f.json");
    const raw = JSON.parse(await fs.readFile(filePath, "utf-8"));
    if (raw.is_new !== true) return false;

    // new_label_until(오늘 + 14일) 만료 체크 (KST 기준 YYYY-MM-DD)
    const todayKst = new Date(Date.now() + 9 * 3600_000).toISOString().split("T")[0];
    if (typeof raw.new_label_until === "string" && raw.new_label_until < todayKst) {
      return false;
    }
    return true;
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

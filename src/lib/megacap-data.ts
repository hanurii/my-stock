import fs from "fs/promises";
import path from "path";
import type { MegacapMonitorData, MegacapFXData } from "./megacap";

export async function getMegacapData(): Promise<MegacapMonitorData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "megacap-monitor.json");
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw) as MegacapMonitorData;
  } catch {
    return null;
  }
}

export async function getMegacapFXData(): Promise<MegacapFXData | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "data", "megacap-fx.json");
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw) as MegacapFXData;
  } catch {
    return null;
  }
}

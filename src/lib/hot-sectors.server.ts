import "server-only";
import fs from "fs";
import path from "path";
import type { HotSectorsData } from "./hot-sectors";

const FILE_PATH = path.join(process.cwd(), "public", "data", "hot-sectors.json");

export function getHotSectorsData(): HotSectorsData | null {
  try {
    const raw = fs.readFileSync(FILE_PATH, "utf-8");
    return JSON.parse(raw) as HotSectorsData;
  } catch {
    return null;
  }
}

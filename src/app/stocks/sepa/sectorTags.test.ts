import { describe, it, expect } from "vitest";
import type { SectorTagsFile } from "./SectorBadge";

// 페이지 조인 로직과 동일: 태그 파일(null 가능)에서 코드로 태그 조회.
function tagFor(file: SectorTagsFile | null, code: string) {
  return file?.tags?.[code];
}

describe("leading sector tags join", () => {
  const file: SectorTagsFile = {
    asof: "2026-08-08",
    tags: {
      "000660": { name: "SK하이닉스", rank: 1, label: "HBM & 반도체 후공정", short: "HBM후공정", confidence: "high" },
      "007660": { name: "이수페타시스", rank: 2, label: "반도체", short: "반도체", confidence: "low" },
    },
    unclassified: [{ code: "477850", name: "마키나락스" }],
  };
  it("태그 있는 코드만 매칭", () => {
    expect(tagFor(file, "000660")?.rank).toBe(1);
    expect(tagFor(file, "007660")?.confidence).toBe("low");
    expect(tagFor(file, "055550")).toBeUndefined();
  });
  it("파일 없음(null) 그레이스풀", () => {
    expect(tagFor(null, "000660")).toBeUndefined();
  });
  it("tags 필드 없음 그레이스풀", () => {
    expect(tagFor({ asof: "2026-08-08" }, "000660")).toBeUndefined();
  });
});

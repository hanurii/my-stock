import { describe, it, expect } from "vitest";
import type { ExportTagsFile } from "./ExportBadge";

// 페이지 조인 로직과 동일: 태그 파일(null 가능)에서 코드로 태그 조회.
function tagFor(file: ExportTagsFile | null, code: string) {
  return file?.tags?.[code];
}

describe("export tags join", () => {
  const file: ExportTagsFile = {
    asof: "2026-08-05",
    tags: {
      "010950": { category: "petroleum", label: "석유제품", tier: "direct", basis: "업종: 석유 정제" },
      "078930": { category: "petroleum", label: "석유제품", tier: "indirect", basis: "GS칼텍스 지주" },
    },
  };
  it("태그 있는 코드만 매칭", () => {
    expect(tagFor(file, "010950")?.tier).toBe("direct");
    expect(tagFor(file, "078930")?.tier).toBe("indirect");
    expect(tagFor(file, "055550")).toBeUndefined();
  });
  it("파일 없음(null) 그레이스풀", () => {
    expect(tagFor(null, "010950")).toBeUndefined();
  });
  it("tags 필드 없음 그레이스풀", () => {
    expect(tagFor({ asof: "2026-08-05" }, "010950")).toBeUndefined();
  });
});

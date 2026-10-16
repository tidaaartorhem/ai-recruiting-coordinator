import { describe, expect, it } from "vitest";
import {
  educationTier,
  experiencePoints,
  extractYears,
  fixMojibake,
  normalize,
  scoreSubset,
  skillHit,
  toContractShape,
} from "./scoring";
import vectors from "../../data/test-vectors.json";

describe("fixMojibake", () => {
  it("repairs double-encoded UTF-8", () => {
    expect(fixMojibake("NaÃ¯ve Bayes")).toBe("Naïve Bayes");
  });
  it("leaves clean text alone", () => {
    expect(fixMojibake("Senior Java Developer")).toBe("Senior Java Developer");
  });
  it("leaves unrecoverable text alone", () => {
    expect(fixMojibake("")).toBe("");
  });
});

describe("normalize", () => {
  it("collapses whitespace", () => {
    expect(normalize("  a\n\n  b\t c ")).toBe("a b c");
  });
});

describe("skillHit", () => {
  it("rejects javascript as a java hit", () => {
    expect(skillHit("javascript developer, typescript too", "java")).toBe(false);
  });
  it("matches aliases and sentence-final punctuation", () => {
    expect(skillHit("core java, spring boot, rest apis", "rest api")).toBe(true);
    expect(skillHit("core java, spring boot, rest apis", "spring")).toBe(true);
  });
});

describe("extractYears", () => {
  it("reads years-of-experience phrases", () => {
    expect(extractYears("5 years of experience in Java")).toBe(5);
  });
  it("reads the skill-matrix month rows (max, not sum)", () => {
    expect(extractYears("Python- Exprience - 24 months. SQL- Exprience - 12 months")).toBe(2);
  });
  it("ignores template noise like 80 years", () => {
    expect(extractYears("80 years' experience summary")).toBe(0);
  });
  it("takes the max credible claim", () => {
    expect(extractYears("2 years of experience. Exprience - 60 months in testing.")).toBe(5);
  });
});

describe("experiencePoints", () => {
  it("follows the disclosed bands", () => {
    expect([experiencePoints(9), experiencePoints(6), experiencePoints(3)]).toEqual([20, 16, 12]);
    expect([experiencePoints(1), experiencePoints(0.5), experiencePoints(0)]).toEqual([8, 4, 0]);
  });
});

describe("educationTier", () => {
  it("ranks doctorate above masters above bachelors above diploma", () => {
    expect(educationTier("PhD in Computer Science").tier).toBe("doctorate");
    expect(educationTier("M.Sc. Data Science").tier).toBe("masters");
    expect(educationTier("B.Tech Computer Science").tier).toBe("bachelors");
    expect(educationTier("Diploma in testing").tier).toBe("diploma");
    expect(educationTier("10 years building things").tier).toBe("none");
  });
});

describe("shared contract parity (test-vectors.json)", () => {
  it("has at least 4 vectors", () => {
    expect(vectors.vectors.length).toBeGreaterThanOrEqual(4);
  });
  for (const v of vectors.vectors as Array<{ id: string; text: string; expected: object }>) {
    it(`vector ${v.id} matches the contract exactly`, () => {
      expect(toContractShape(scoreSubset(v.text))).toEqual(v.expected);
    });
  }
  it("is deterministic", () => {
    const t = "Senior Java developer, 6 years of experience. Spring Boot, Docker. B.Tech.";
    expect(scoreSubset(t)).toEqual(scoreSubset(t));
  });
});

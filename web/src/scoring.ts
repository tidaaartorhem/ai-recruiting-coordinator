/**
 * scoring.ts — in-browser mirror of the Python match engine's disclosed
 * subset (used by the Paste-a-Resume tab).
 *
 * Shared contract (identical rules to src/recruiting/):
 *   required-skill coverage: matched / 6 required skills x 35
 *   years of experience:     >=8 -> 20, >=5 -> 16, >=3 -> 12, >=1 -> 8, >0 -> 4
 *   education tier:          doctorate 20, masters 14, bachelors 9, diploma 4
 *
 * TF-IDF is intentionally excluded: it needs the full corpus document
 * frequencies, which live in the Python pipeline only. The paste tab says so.
 */

export const REQUIRED_SKILLS = [
  "java",
  "spring",
  "rest api",
  "sql",
  "docker",
  "microservices",
];

const SKILL_ALIASES: Record<string, string[]> = {
  spring: ["spring boot", "springboot", "spring mvc", "spring framework"],
  "rest api": ["restful", "rest api", "rest apis", "rest services", "web services"],
  sql: ["sql", "mysql", "postgresql", "postgres", "sqlserver", "sql server", "oracle db"],
  docker: ["docker", "containerization", "containers"],
  microservices: ["microservices", "micro services", "micro-service"],
  java: ["java", "j2ee", "core java"],
};

/** Repair UTF-8 mojibake ("NaÃ¯ve" -> "Naïve"): the inverse of decoding
 *  UTF-8 bytes as Latin-1. Mirrors Python's text.encode('latin-1').decode('utf-8'). */
export function fixMojibake(text: string): string {
  if (!text || !text.includes("Ã")) return text;
  try {
    const bytes = new Uint8Array(
      [...text].map((ch) => {
        const code = ch.charCodeAt(0);
        if (code > 255) throw new Error("non-latin1");
        return code;
      }),
    );
    const fixed = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    if (fixed.includes("Ã") || fixed.includes("�")) return text;
    return fixed;
  } catch {
    return text;
  }
}

export function normalize(text: string): string {
  if (!text) return "";
  return fixMojibake(text).split(/\s+/).join(" ").trim();
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function skillHit(textLower: string, canonical: string): boolean {
  const terms = [canonical, ...(SKILL_ALIASES[canonical] ?? [])];
  return terms.some((t) => new RegExp(`\\b${escapeRegExp(t)}\\b`).test(textLower));
}

const YEARS_RE = /\b(\d{1,2})\s*(?:\+|plus)?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp\.?|experiance)\b/gi;
const MONTHS_RE = /\bexp[e]?rience\s*[-–:]\s*(\d{1,3})\s*months?\b/gi;
const LESS_THAN_YEAR_RE = /less\s+than\s+1\s*year/i;
const MAX_SANE_YEARS = 40;

export function extractYears(rawText: string): number {
  const text = fixMojibake(rawText);
  const candidates: number[] = [];
  for (const m of text.matchAll(YEARS_RE)) {
    const y = parseInt(m[1], 10);
    if (y > 0 && y <= MAX_SANE_YEARS) candidates.push(y);
  }
  let maxMonths = 0;
  for (const m of text.matchAll(MONTHS_RE)) {
    const months = parseInt(m[1], 10);
    if (months > 0 && months <= 600) maxMonths = Math.max(maxMonths, months);
  }
  if (maxMonths > 0) candidates.push(Math.round((maxMonths / 12) * 10) / 10);
  if (LESS_THAN_YEAR_RE.test(text)) candidates.push(0.5);
  if (candidates.length === 0) return 0;
  return Math.round(Math.max(...candidates) * 10) / 10;
}

export function experiencePoints(years: number): number {
  if (years >= 8) return 20;
  if (years >= 5) return 16;
  if (years >= 3) return 12;
  if (years >= 1) return 8;
  if (years > 0) return 4;
  return 0;
}

const EDUCATION_TIERS: Array<[string, number, string[]]> = [
  ["doctorate", 20, ["phd", "ph.d", "doctorate", "doctoral"]],
  ["masters", 14, ["m.s.", "m.sc", "msc", "m.tech", "mtech", "m.e.", "mba", "master", "post graduate", "postgraduate"]],
  ["bachelors", 9, ["b.tech", "btech", "b.e.", "b.sc", "bsc", "bachelor", "b.com", "b.a.", "undergraduate", "graduation"]],
  ["diploma", 4, ["diploma", "certificate", "certification"]],
];

export function educationTier(rawText: string): { tier: string; points: number } {
  const text = normalize(rawText).toLowerCase();
  for (const [tier, points, keywords] of EDUCATION_TIERS) {
    if (keywords.some((kw) => text.includes(kw))) return { tier, points };
  }
  return { tier: "none", points: 0 };
}

export interface SubsetScore {
  matchedRequired: string[];
  skillPoints: number;
  years: number;
  experiencePoints: number;
  educationTier: string;
  educationPoints: number;
  subsetScore: number;
}

/** The disclosed subset of the full 100-point score (excludes TF-IDF). */
export function scoreSubset(rawText: string): SubsetScore {
  const textLower = normalize(rawText).toLowerCase();
  const matchedRequired = REQUIRED_SKILLS.filter((s) => skillHit(textLower, s));
  const skillPoints =
    Math.round((matchedRequired.length / REQUIRED_SKILLS.length) * 35 * 10) / 10;
  const years = extractYears(rawText);
  const expPoints = experiencePoints(years);
  const edu = educationTier(rawText);
  return {
    matchedRequired,
    skillPoints,
    years,
    experiencePoints: expPoints,
    educationTier: edu.tier,
    educationPoints: edu.points,
    subsetScore: Math.round((skillPoints + expPoints + edu.points) * 10) / 10,
  };
}

/** Map a SubsetScore to the exact key names of the shared contract
 *  (data/test-vectors.json), which uses the Python pipeline's snake_case. */
export function toContractShape(s: SubsetScore): Record<string, unknown> {
  return {
    matched_required: s.matchedRequired,
    skill_points: s.skillPoints,
    years: s.years,
    experience_points: s.experiencePoints,
    education_tier: s.educationTier,
    education_points: s.educationPoints,
    subset_score: s.subsetScore,
  };
}

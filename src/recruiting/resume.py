"""Resume loading and feature extraction.

Features extracted per resume (all deterministic, regex/keyword based):
  - required/nice-to-have skill hits (whole-word, case-insensitive)
  - years of experience (regex claims, sanity-capped)
  - education tier (keyword tiers)
"""

from __future__ import annotations

import csv
import re

from .normalize import fix_mojibake, normalize

# ---------------------------------------------------------------------------
# Experience extraction
# ---------------------------------------------------------------------------

# "5 years of experience", "3+ years experience", "2 yrs exp"
_YEARS_RE = re.compile(
    r"(?i)\b(\d{1,2})\s*(?:\+|plus)?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp\.?|experiance)\b"
)
# Skill-matrix rows like "Python- Exprience - 24 months"
_MONTHS_RE = re.compile(r"(?i)\bexp[e]?rience\s*[-–:]\s*(\d{1,3})\s*months?\b")
_LESS_THAN_YEAR_RE = re.compile(r"(?i)less\s+than\s+1\s*year")

# Claims above this are treated as corpus noise ("80 years' experience"
# appears in the dataset as a template artifact, not a human career).
_MAX_SANE_YEARS = 40


def extract_years_experience(raw_text: str) -> float:
    """Best-estimate total years of experience from a resume.

    Strategy: collect every sane year claim, sum every month-matrix row into
    years, map "less than 1 year" to 0.5, and take the maximum — a candidate's
    total experience is the largest single credible claim, not a sum of
    per-skill rows (which would double-count overlapping jobs).
    """
    text = fix_mojibake(raw_text)
    candidates: list[float] = []

    for m in _YEARS_RE.finditer(text):
        years = int(m.group(1))
        if 0 < years <= _MAX_SANE_YEARS:
            candidates.append(float(years))

    months_total = 0
    for m in _MONTHS_RE.finditer(text):
        months = int(m.group(1))
        if 0 < months <= 600:
            # Max, not sum: per-skill rows overlap in calendar time, so adding
            # them double-counts the same working years.
            months_total = max(months_total, months)
    if months_total:
        candidates.append(round(months_total / 12.0, 1))

    if _LESS_THAN_YEAR_RE.search(text):
        candidates.append(0.5)

    if not candidates:
        return 0.0
    return round(max(candidates), 1)


# ---------------------------------------------------------------------------
# Education tiers
# ---------------------------------------------------------------------------

# Ordered high → low; first match wins. Keywords are checked as substrings on
# normalized (lowercased) text, which is why "msc"/"m.s." variants matter.
_EDUCATION_TIERS: list[tuple[str, int, list[str]]] = [
    ("doctorate", 20, ["phd", "ph.d", "doctorate", "doctoral"]),
    ("masters", 14, ["m.s.", "m.sc", "msc", "m.tech", "mtech", "m.e.", "mba", "master", "post graduate", "postgraduate"]),
    ("bachelors", 9, ["b.tech", "btech", "b.e.", "b.sc", "bsc", "bachelor", "b.com", "b.a.", "undergraduate", "graduation"]),
    ("diploma", 4, ["diploma", "certificate", "certification"]),
]


def extract_education_tier(raw_text: str) -> tuple[str, int]:
    """Return (tier_name, tier_points). Points follow the disclosed weights."""
    text = normalize(raw_text).lower()
    for tier_name, points, keywords in _EDUCATION_TIERS:
        for kw in keywords:
            if kw in text:
                return tier_name, points
    return "none", 0


# ---------------------------------------------------------------------------
# Skill matching
# ---------------------------------------------------------------------------

_SKILL_ALIASES: dict[str, list[str]] = {
    # canonical skill -> extra spellings accepted as a hit
    "spring": ["spring boot", "springboot", "spring mvc", "spring framework"],
    "rest api": ["restful", "rest api", "rest apis", "rest services", "web services"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "sqlserver", "sql server", "oracle db"],
    "docker": ["docker", "containerization", "containers"],
    "microservices": ["microservices", "micro services", "micro-service"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services", "ec2", "s3"],
    "kafka": ["kafka"],
    "junit": ["junit", "testng", "unit testing"],
    "ci/cd": ["ci/cd", "ci cd", "jenkins", "continuous integration", "github actions", "gitlab ci"],
    "git": ["git", "github", "gitlab", "version control"],
    "maven": ["maven", "gradle"],
    "hibernate": ["hibernate", "jpa"],
    "java": ["java", "j2ee", "core java"],
    "python": ["python"],
    "react": ["react", "react.js", "reactjs"],
}


def skill_hit(text_lower: str, canonical: str) -> bool:
    """True if the canonical skill or any accepted alias appears as a
    whole word/phrase in the lowercased resume text. Plain \\b word
    boundaries: they match before punctuation and at string ends, while
    still rejecting "java" inside "javascript"."""
    terms = [canonical] + _SKILL_ALIASES.get(canonical, [])
    for term in terms:
        if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
            return True
    return False


def extract_skill_hits(raw_text: str, skills: list[str]) -> dict[str, bool]:
    """Map each requested skill to a boolean hit on the resume."""
    text_lower = normalize(raw_text).lower()
    return {skill: skill_hit(text_lower, skill) for skill in skills}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_resumes(csv_path: str) -> list[dict]:
    """Load the bundled resume corpus. Returns dicts with id, category,
    raw text, and normalized text."""
    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        for i, row in enumerate(csv.DictReader(f)):
            raw = row.get("Resume", "") or ""
            rows.append(
                {
                    "id": f"R{i+1:04d}",
                    "category": (row.get("Category", "") or "").strip(),
                    "raw": raw,
                    "text": normalize(raw),
                }
            )
    return rows

"""Deterministic match engine with disclosed weights.

score_candidate(text) -> 0..100, pure function of the resume text.

The four signals and their weights (published in README and in every
score payload under `weights_disclosure`):

| Signal                | Weight | Rule                                            |
|-----------------------|--------|-------------------------------------------------|
| Required-skill coverage | 35   | matched required skills / total required, ×35   |
| TF-IDF cosine vs spec | 25     | cosine similarity of resume vector to the job   |
|                       |        | spec vector, ×25                                |
| Years of experience   | 20     | >=8 → 20; >=5 → 16; >=3 → 12; >=1 → 8; >0 → 4  |
| Education tier        | 20     | doctorate → 20; masters → 14; bachelors → 9;    |
|                       |        | diploma → 4; none → 0                           |

No LLM, no embeddings, no randomness. The in-browser TypeScript mirror in
web/src/scoring.ts implements the skill-coverage, experience, and education
rules (a disclosed subset); TF-IDF is Python-only because it needs the full
corpus document frequencies, which are shipped in public/data/tfidf.json.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .normalize import normalize
from .resume import extract_education_tier, extract_skill_hits, extract_years_experience

# ---------------------------------------------------------------------------
# The job spec — the single fixed hiring scenario for this replay.
# ---------------------------------------------------------------------------

JOB_SPEC = {
    "title": "Senior Backend Engineer (Java)",
    "company_context": "B2B SaaS, Toronto (hybrid)",
    "required_skills": ["java", "spring", "rest api", "sql", "docker", "microservices"],
    "nice_to_have": ["kubernetes", "aws", "kafka", "junit", "ci/cd", "git", "maven", "hibernate"],
    "spec_text": (
        "Senior Backend Engineer for a B2B SaaS platform in Toronto. "
        "Build and scale Java microservices with Spring Boot, design REST APIs, "
        "and own data persistence with SQL databases. Containerize services with "
        "Docker and ship through CI/CD. We value strong testing discipline with "
        "JUnit, cloud experience on AWS, event-driven design with Kafka, "
        "Kubernetes operations, and solid Git workflows with Maven builds."
    ),
}

WEIGHTS = {
    "required_skill_coverage": 35,
    "tfidf_cosine": 25,
    "years_experience": 20,
    "education_tier": 20,
}


def experience_points(years: float) -> int:
    if years >= 8:
        return 20
    if years >= 5:
        return 16
    if years >= 3:
        return 12
    if years >= 1:
        return 8
    if years > 0:
        return 4
    return 0


# ---------------------------------------------------------------------------
# Hand-rolled TF-IDF (standard library only; corpus IDF is deterministic)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z][a-z0-9+#.\-]*")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(normalize(text).lower())


class TfidfIndex:
    """Corpus TF-IDF with cosine similarity to a query (the job spec)."""

    def __init__(self, documents: list[str]):
        self.n_docs = len(documents)
        df: Counter[str] = Counter()
        self.doc_vectors: list[dict[str, float]] = []
        for doc in documents:
            counts = Counter(tokenize(doc))
            self.doc_vectors.append(dict(counts))
            for term in counts:
                df[term] += 1
        # Smoothed IDF so no term gets a zero or negative weight.
        self.idf = {t: math.log((self.n_docs + 1) / (f + 1)) + 1.0 for t, f in df.items()}

    def vector(self, counts: Counter[str]) -> dict[str, float]:
        total = sum(counts.values()) or 1
        return {t: (c / total) * self.idf.get(t, 1.0) for t, c in counts.items()}

    @staticmethod
    def cosine(a: dict[str, float], b: dict[str, float]) -> float:
        dot = sum(a[t] * b.get(t, 0.0) for t in a)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def similarity(self, doc_index: int, query_text: str) -> float:
        doc_vec = self.vector(Counter(self.doc_vectors[doc_index]))
        q_vec = self.vector(Counter(tokenize(query_text)))
        return self.cosine(doc_vec, q_vec)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_candidate(
    raw_text: str,
    tfidf: TfidfIndex,
    doc_index: int,
    spec: dict = JOB_SPEC,
) -> dict:
    """Score one resume. Returns the full breakdown (every sub-score disclosed)."""
    required = spec["required_skills"]
    hits = extract_skill_hits(raw_text, required + spec["nice_to_have"])
    matched_required = sum(1 for s in required if hits[s])
    skill_points = round(matched_required / len(required) * WEIGHTS["required_skill_coverage"], 1)

    cosine = tfidf.similarity(doc_index, spec["spec_text"])
    tfidf_points = round(cosine * WEIGHTS["tfidf_cosine"], 1)

    years = extract_years_experience(raw_text)
    exp_points = experience_points(years)

    tier_name, tier_points = extract_education_tier(raw_text)

    total = round(skill_points + tfidf_points + exp_points + tier_points, 1)

    return {
        "score": total,
        "breakdown": {
            "required_skill_coverage": skill_points,
            "required_skills_matched": [s for s in required if hits[s]],
            "required_skills_total": len(required),
            "tfidf_cosine": round(cosine, 4),
            "tfidf_points": tfidf_points,
            "years_experience": years,
            "experience_points": exp_points,
            "education_tier": tier_name,
            "education_points": tier_points,
        },
        "nice_to_have_matched": [s for s in spec["nice_to_have"] if hits[s]],
        "weights_disclosure": WEIGHTS,
    }

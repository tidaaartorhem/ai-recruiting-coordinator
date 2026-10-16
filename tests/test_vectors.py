"""Shared-contract parity: the Python pipeline must reproduce every value in
data/test-vectors.json, the same file the in-browser TypeScript mirror is
tested against (web/src/scoring.test.ts)."""

import json
from pathlib import Path

from recruiting.matching import WEIGHTS, experience_points
from recruiting.resume import extract_education_tier, extract_skill_hits, extract_years_experience

VECTORS = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "test-vectors.json").read_text()
)


def subset_score(text: str) -> dict:
    required = VECTORS["required_skills"]
    hits = extract_skill_hits(text, required)
    matched = [s for s in required if hits[s]]
    skill_points = round(len(matched) / len(required) * WEIGHTS["required_skill_coverage"], 1)
    years = extract_years_experience(text)
    exp_points = experience_points(years)
    tier_name, tier_points = extract_education_tier(text)
    return {
        "matched_required": matched,
        "skill_points": skill_points,
        "years": years,
        "experience_points": exp_points,
        "education_tier": tier_name,
        "education_points": tier_points,
        "subset_score": round(skill_points + exp_points + tier_points, 1),
    }


def test_all_vectors_match_contract():
    assert len(VECTORS["vectors"]) >= 4
    for v in VECTORS["vectors"]:
        got = subset_score(v["text"])
        assert got == v["expected"], f"vector {v['id']} mismatch: {got} != {v['expected']}"


def test_contract_weights_disclosed():
    assert VECTORS["weights"]["required_skill_coverage"] == 35
    assert VECTORS["weights"]["years_experience"] == 20
    assert VECTORS["weights"]["education_tier"] == 20

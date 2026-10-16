import math

from recruiting.matching import (
    JOB_SPEC,
    WEIGHTS,
    TfidfIndex,
    experience_points,
    score_candidate,
)

DOCS = [
    "Java Spring Boot microservices REST APIs SQL Docker",
    "Python machine learning data science pandas",
    "Manual testing QA selenium test cases",
]


def test_experience_points_bands():
    assert experience_points(9) == 20
    assert experience_points(6) == 16
    assert experience_points(3) == 12
    assert experience_points(1) == 8
    assert experience_points(0.5) == 4
    assert experience_points(0) == 0


def test_weights_sum_to_100():
    assert sum(WEIGHTS.values()) == 100


def test_tfidf_similarity_prefers_matching_doc():
    idx = TfidfIndex(DOCS)
    sims = [idx.similarity(i, "Java Spring microservices") for i in range(3)]
    assert sims[0] > sims[1] and sims[0] > sims[2]
    assert all(0.0 <= s <= 1.0 + 1e-9 for s in sims)


def test_score_candidate_breakdown_discloses_everything():
    idx = TfidfIndex(DOCS + [JOB_SPEC["spec_text"]])
    text = (
        "Senior Java developer, 6 years of experience. Spring Boot microservices, "
        "REST APIs, SQL, Docker. B.Tech."
    )
    out = score_candidate(text, idx, 3)
    bd = out["breakdown"]
    assert out["score"] == round(
        bd["required_skill_coverage"] + bd["tfidf_points"]
        + bd["experience_points"] + bd["education_points"], 1,
    )
    assert bd["required_skills_matched"] == ["java", "spring", "rest api", "sql", "docker", "microservices"]
    assert bd["years_experience"] == 6.0
    assert bd["education_tier"] == "bachelors"
    assert out["weights_disclosure"] == WEIGHTS


def test_score_candidate_deterministic():
    idx = TfidfIndex(DOCS)
    a = score_candidate("Java 3 years of experience. Docker, SQL.", idx, 0)
    b = score_candidate("Java 3 years of experience. Docker, SQL.", idx, 0)
    assert a == b

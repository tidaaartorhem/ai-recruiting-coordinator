from recruiting.resume import (
    extract_education_tier,
    extract_skill_hits,
    extract_years_experience,
    load_resumes,
)

DATA = "/home/hatch/workspace/github-repos/ai-recruiting-coordinator/data/resumes_raw.csv"


def test_load_resumes_count():
    rows = load_resumes(DATA)
    assert len(rows) == 962
    assert rows[0]["id"] == "R0001"
    assert set(rows[0]) >= {"id", "category", "raw", "text"}


def test_load_resumes_normalizes_mojibake():
    rows = load_resumes(DATA)
    assert not any("Ã" in r["text"] for r in rows)


def test_years_from_years_phrase():
    assert extract_years_experience("5 years of experience in Java") == 5.0


def test_years_from_months_matrix():
    assert extract_years_experience("Python- Exprience - 24 months") == 2.0


def test_years_ignores_noise_claims():
    # "80 years' experience" is a template artifact in the corpus, not a career.
    assert extract_years_experience("80 years' experience summary") == 0.0


def test_years_takes_max_claim():
    text = "2 years of experience. Exprience - 60 months in testing."
    assert extract_years_experience(text) == 5.0


def test_education_tiers():
    assert extract_education_tier("PhD in Computer Science")[0] == "doctorate"
    assert extract_education_tier("M.Sc. Data Science")[0] == "masters"
    assert extract_education_tier("B.Tech Computer Science")[0] == "bachelors"
    assert extract_education_tier("Diploma in testing")[0] == "diploma"
    assert extract_education_tier("10 years building things")[0] == "none"


def test_skill_hit_whole_word():
    # "JavaScript" must not count as a "java" hit.
    hits = extract_skill_hits("JavaScript developer, TypeScript too", ["java"])
    assert hits == {"java": False}
    hits = extract_skill_hits("Core Java, Spring Boot, REST APIs", ["java", "spring", "rest api"])
    assert hits == {"java": True, "spring": True, "rest api": True}

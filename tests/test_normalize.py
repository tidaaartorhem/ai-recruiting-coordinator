from recruiting.normalize import fix_mojibake, normalize


def test_fix_mojibake_repairs_double_encoded_utf8():
    assert fix_mojibake("NaÃ¯ve Bayes") == "Naïve Bayes"


def test_fix_mojibake_leaves_clean_text_alone():
    assert fix_mojibake("Senior Java Developer") == "Senior Java Developer"


def test_fix_mojibake_empty():
    assert fix_mojibake("") == ""


def test_normalize_collapses_whitespace():
    assert normalize("  a\n\n  b\t c ") == "a b c"

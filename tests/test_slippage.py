from recruiting.slippage import bucket, score_slippage


def test_fresh_candidate_is_low():
    out = score_slippage(2, 10, 0, True)
    assert out["risk"] == 0 and out["bucket"] == "low"


def test_stale_candidate_scores():
    out = score_slippage(21, 10, 0, True)
    assert out["components"]["staleness"] == 30  # capped
    assert out["bucket"] in ("watch", "high", "critical")


def test_feedback_debt_and_unscheduled_stack():
    out = score_slippage(3, 10, 2, False)
    assert out["components"]["feedback_debt"] == 20
    assert out["components"]["unscheduled"] == 20
    assert len(out["drivers"]) == 2


def test_buckets():
    assert bucket(10) == "low"
    assert bucket(30) == "watch"
    assert bucket(60) == "high"
    assert bucket(90) == "critical"


def test_max_score_bounded():
    out = score_slippage(365, 365, 99, False)
    assert out["risk"] == 100

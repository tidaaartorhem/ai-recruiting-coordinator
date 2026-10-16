"""Slippage risk scorer: who is silently going stale, and why.

score_slippage(...) -> 0..100 (higher = worse). Deterministic, disclosed:

| Driver              | Rule                                                  | Cap |
|---------------------|-------------------------------------------------------|-----|
| Candidate staleness | +3 per day since last touch beyond 7 stale-free days  | 30  |
| Loop drag           | +2 per day of time-to-loop beyond 14 days             | 20  |
| Feedback debt       | +10 per overdue feedback item on the candidate's loop | 30  |
| Unscheduled loop    | +20 if the candidate has no future rounds scheduled   | 20  |

Buckets: 0–24 low · 25–49 watch · 50–74 high · 75+ critical.
"""


def bucket(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "watch"
    return "low"


def score_slippage(
    days_since_touch: int,
    time_to_loop_days: int,
    overdue_feedback: int,
    has_future_rounds: bool,
) -> dict:
    stale_points = min(30, max(0, 3 * (days_since_touch - 7)))
    drag_points = min(20, max(0, 2 * (time_to_loop_days - 14)))
    debt_points = min(30, 10 * max(0, overdue_feedback))
    unscheduled_points = 0 if has_future_rounds else 20
    total = stale_points + drag_points + debt_points + unscheduled_points
    drivers = []
    if stale_points:
        drivers.append(
            f"stale: last touch {days_since_touch}d ago (+{stale_points})"
        )
    if drag_points:
        drivers.append(
            f"loop drag: {time_to_loop_days}d to close the loop (+{drag_points})"
        )
    if debt_points:
        drivers.append(
            f"feedback debt: {overdue_feedback} overdue (+{debt_points})"
        )
    if unscheduled_points:
        drivers.append("no future rounds scheduled (+20)")
    return {
        "risk": total,
        "bucket": bucket(total),
        "drivers": drivers,
        "components": {
            "staleness": stale_points,
            "loop_drag": drag_points,
            "feedback_debt": debt_points,
            "unscheduled": unscheduled_points,
        },
    }

from datetime import date, datetime

from recruiting import scheduler as sched_mod
from recruiting.scenario import TODAY, seeded_interview_records


def _shortlist(n=4):
    return [
        {"id": f"R{i+1:04d}", "rank": i + 1, "score": 90 - i}
        for i in range(n)
    ]


def test_schedule_respects_panelist_availability_windows():
    shortlist = _shortlist(2)
    payload = sched_mod.schedule_loops(shortlist, [])
    from recruiting.scenario import PANEL

    for plan in payload["candidates"]:
        for r in plan["rounds"]:
            if r["status"] != "scheduled":
                continue
            day = date.fromisoformat(r["date"])
            wins = PANEL[r["panelist"]]["availability"].get(day.weekday(), [])
            start_min = int(r["start"][11:13]) * 60 + int(r["start"][14:16])
            assert any(ws * 60 <= start_min for ws, _ in wins), r


def test_no_panelist_double_booking_and_max_two_per_day():
    shortlist = _shortlist(6)
    payload = sched_mod.schedule_loops(shortlist, [])
    seen: dict[tuple[str, str, str], int] = {}
    for plan in payload["candidates"]:
        for r in plan["rounds"]:
            if r["status"] != "scheduled":
                continue
            s, e = r["start"], r["end"]
            for plan2 in payload["candidates"]:
                for r2 in plan2["rounds"]:
                    if r2["status"] != "scheduled" or r2 is r:
                        continue
                    if r2["panelist"] == r["panelist"]:
                        assert e <= r2["start"] or s >= r2["end"], (r, r2)
            key = (r["panelist"], r["date"])
            seen[key] = seen.get(key, 0) + 1
    assert all(v <= 2 for v in seen.values())


def test_rounds_run_in_order_after_previous():
    shortlist = _shortlist(3)
    payload = sched_mod.schedule_loops(shortlist, [])
    for plan in payload["candidates"]:
        dates = [r["date"] for r in plan["rounds"] if r.get("date")]
        assert dates == sorted(dates)
        assert len(set(dates)) == len(dates)  # prevention guard: no same-day stacks


def test_double_booking_detector_flags_seeded_stack():
    shortlist = _shortlist(6)
    completed = seeded_interview_records(shortlist)
    payload = sched_mod.schedule_loops(shortlist, completed)
    plan = next(p for p in payload["candidates"] if p["candidate_id"] == "R0006")
    assert len(plan["double_booking_flags"]) == 1
    flag = plan["double_booking_flags"][0]
    assert set(flag["rounds"]) == {"Recruiter Screen", "Technical Deep-Dive"}


def test_bottleneck_identifies_constrained_panelist():
    shortlist = _shortlist(4)
    payload = sched_mod.schedule_loops(shortlist, [])
    b = payload["bottleneck"]
    # Mei Chen has the fewest weekly window hours (3 days x 5h).
    assert b["structural"] == "Mei Chen"
    assert b["structural_weekly_hours"] == 15
    assert b["load_leader"] in [r["panelist"] for r in
                                sched_mod.ROUNDS]
    for plan in payload["candidates"]:
        assert plan["time_to_loop_days"] > 0

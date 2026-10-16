from recruiting import feedback as fb
from recruiting.scenario import TODAY, seeded_interview_records


def _shortlist(n=8):
    return [{"id": f"R{i+1:04d}", "rank": i + 1, "score": 90 - i} for i in range(n)]


def _items():
    return fb.evaluate_feedback(seeded_interview_records(_shortlist()))


def test_sla_statuses_cover_all_seeded_states():
    statuses = {i["status"] for i in _items()}
    assert {"submitted_on_time", "overdue", "due_soon"} <= statuses


def test_overdue_hours_positive_and_ranked():
    queue = fb.build_nudge_queue(_items())
    overdue = [q for q in queue if q["status"] == "overdue"]
    assert overdue
    hours = [q["hours_overdue"] for q in overdue]
    assert hours == sorted(hours, reverse=True)
    assert all(h > 0 for h in hours)


def test_every_nudge_has_one_action_and_human_gate():
    for q in fb.build_nudge_queue(_items()):
        assert q["recommended_action"].startswith(("Send feedback nudge", "Pre-emptive ping"))
        assert q["human_gate"] is True


def test_due_soon_item_is_rank4_deep_dive():
    item = next(
        i for i in _items()
        if i["candidate_id"] == "R0005" and i["round"] == "Technical Deep-Dive"
    )
    assert item["status"] == "due_soon"
    assert 0 < item["hours_remaining"] <= 6


def test_debrief_ready_candidate_gets_suggestion_behind_gate():
    from recruiting import scheduler as sched_mod
    from recruiting.pipeline import _panel_bookings_from_schedule

    shortlist = _shortlist()
    completed = seeded_interview_records(shortlist)
    schedule = sched_mod.schedule_loops(shortlist, completed)
    items = fb.evaluate_feedback(completed)
    bookings = _panel_bookings_from_schedule(schedule)
    debrief = fb.debrief_readiness(items, schedule, bookings)
    ready = [d for d in debrief if not d.get("blocked")]
    # Rank 1 has all completed feedback in and every round slotted.
    r1 = next(d for d in debrief if d["candidate_rank"] == 1)
    assert not r1.get("blocked") and r1["human_gate"] is True
    assert r1["suggested_debrief"] > schedule["candidates"][0]["rounds"][-1]["end"]
    # Rank 2 is blocked on missing feedback.
    r2 = next(d for d in debrief if d["candidate_rank"] == 2)
    assert r2["blocked"] and r2["blockers"]


def test_summary_counts():
    s = fb.summarize(_items())
    assert s["total_interviews"] == len(_items())
    assert s["overdue_count"] == sum(1 for i in _items() if i["status"] == "overdue")
    assert s["worst_overdue"]["hours_overdue"] > 0

"""Feedback SLA engine: the chase queue recruiters actually need.

Rules (disclosed):
  - Every completed interview starts a feedback SLA clock of 24h at its end.
  - Status at review time (fixed TODAY 09:00):
      submitted_on_time / submitted_late / overdue / due_soon (<6h left) / pending
  - The nudge queue ranks overdue items by overdue hours (desc), then
    due-soon items by hours remaining (asc). Each entry carries exactly ONE
    recommended action and is human-gated: nudges are staged locally, never
    sent automatically.
  - Debrief readiness: a candidate is ready when every completed interview
    has feedback submitted AND every round is completed or scheduled. The
    desk then auto-suggests a debrief slot (next weekday 15:00 Toronto,
    hiring manager + recruiter free) — suggestion only, behind the human gate.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from .scenario import DUE_SOON_HOURS, FEEDBACK_SLA_HOURS, ROUNDS, TODAY_START

REVIEW_TIME = TODAY_START  # 2026-10-16 09:00, fixed for the replay


def evaluate_feedback(records: list[dict]) -> list[dict]:
    """Attach SLA status to each seeded interview record."""
    items = []
    for rec in records:
        end = datetime.fromisoformat(rec["end"])
        deadline = end + timedelta(hours=FEEDBACK_SLA_HOURS)
        submitted = rec["feedback_submitted_at"]
        item = dict(rec)
        item["sla_deadline"] = deadline.isoformat()
        if submitted:
            sub = datetime.fromisoformat(submitted)
            item["status"] = (
                "submitted_on_time" if sub <= deadline else "submitted_late"
            )
            item["hours_overdue"] = 0.0
        elif REVIEW_TIME > deadline:
            item["status"] = "overdue"
            item["hours_overdue"] = round(
                (REVIEW_TIME - deadline).total_seconds() / 3600, 1
            )
        else:
            remaining = (deadline - REVIEW_TIME).total_seconds() / 3600
            item["status"] = "due_soon" if remaining <= DUE_SOON_HOURS else "pending"
            item["hours_overdue"] = 0.0
            item["hours_remaining"] = round(remaining, 1)
        items.append(item)
    return items


def build_nudge_queue(items: list[dict]) -> list[dict]:
    """Ranked chase list with one recommended action per item (human-gated)."""
    actionable = [i for i in items if i["status"] in ("overdue", "due_soon")]
    actionable.sort(
        key=lambda i: (
            0 if i["status"] == "overdue" else 1,
            -i.get("hours_overdue", 0),
            i.get("hours_remaining", 0),
        )
    )
    queue = []
    for i in actionable:
        if i["status"] == "overdue":
            action = (
                "Send feedback nudge to {panelist}: {round} feedback for "
                "candidate {cid} (rank #{rank}) is {h}h past the 24h SLA. "
                "Ask for the hire/no-hire call plus 2 supporting signals."
            ).format(
                panelist=i["panelist"], round=i["round"],
                cid=i["candidate_id"], rank=i["candidate_rank"],
                h=i["hours_overdue"],
            )
        else:
            action = (
                "Pre-emptive ping to {panelist}: {round} feedback for candidate "
                "{cid} (rank #{rank}) is due in {h}h. A 3-line template is "
                "attached so it takes under two minutes."
            ).format(
                panelist=i["panelist"], round=i["round"],
                cid=i["candidate_id"], rank=i["candidate_rank"],
                h=i["hours_remaining"],
            )
        queue.append(
            {
                "candidate_id": i["candidate_id"],
                "candidate_rank": i["candidate_rank"],
                "round": i["round"],
                "panelist": i["panelist"],
                "status": i["status"],
                "hours_overdue": i.get("hours_overdue", 0.0),
                "hours_remaining": i.get("hours_remaining"),
                "sla_deadline": i["sla_deadline"],
                "recommended_action": action,
                "human_gate": True,
                "gate_note": "Nudges are staged in this desk only. Nothing is "
                "sent until a human approves each item.",
            }
        )
    return queue


def _next_weekday_15h(after: datetime, bookings: dict[str, list]) -> datetime:
    """Next weekday 15:00 with Daniel Okafor (hiring manager) and Priya Nair
    (recruiter) both free for one hour."""
    day = after.date() + timedelta(days=1)
    while True:
        if day.weekday() < 5:
            slot_start = datetime.combine(day, time(15, 0))
            slot_end = slot_start + timedelta(hours=1)
            free = True
            for name in ("Daniel Okafor", "Priya Nair"):
                for d, s, e in bookings.get(name, []):
                    bstart = datetime.combine(d, time(s // 60, s % 60))
                    bend = datetime.combine(d, time(e // 60, e % 60))
                    if not (slot_end <= bstart or slot_start >= bend):
                        free = False
                        break
                if not free:
                    break
            if free:
                return slot_start
        day += timedelta(days=1)


def debrief_readiness(
    items: list[dict], schedule: dict, panel_bookings: dict[str, list]
) -> list[dict]:
    """Candidates whose loop can go to debrief: all completed interviews have
    feedback, and every round is completed or scheduled."""
    by_cand: dict[str, list[dict]] = {}
    for i in items:
        by_cand.setdefault(i["candidate_id"], []).append(i)

    ready = []
    for plan in schedule["candidates"]:
        cid = plan["candidate_id"]
        rounds = plan["rounds"]
        all_slotted = all(r["status"] in ("completed", "scheduled") for r in rounds)
        feedback_ok = all(
            i["status"] in ("submitted_on_time", "submitted_late")
            for i in by_cand.get(cid, [])
        )
        missing = [
            i["round"]
            for i in by_cand.get(cid, [])
            if i["status"] not in ("submitted_on_time", "submitted_late")
        ]
        unscheduled = [r["round"] for r in rounds if r["status"] not in ("completed", "scheduled")]
        if all_slotted and feedback_ok and not missing and not unscheduled:
            last = max(
                datetime.fromisoformat(r["end"]) for r in rounds if r.get("end")
            )
            suggestion = _next_weekday_15h(last, panel_bookings)
            ready.append(
                {
                    "candidate_id": cid,
                    "candidate_rank": plan["rank"],
                    "suggested_debrief": suggestion.isoformat(),
                    "human_gate": True,
                    "gate_note": "Debrief is proposed, not booked. A human "
                    "confirms the slot and the invite list.",
                }
            )
        else:
            blockers = [f"feedback missing: {m}" for m in missing] + [
                f"round not slotted: {u}" for u in unscheduled
            ]
            if blockers:
                ready.append(
                    {
                        "candidate_id": cid,
                        "candidate_rank": plan["rank"],
                        "blocked": True,
                        "blockers": blockers,
                    }
                )
    return ready


def summarize(items: list[dict]) -> dict:
    from collections import Counter

    counts = Counter(i["status"] for i in items)
    overdue = [i for i in items if i["status"] == "overdue"]
    worst = max(overdue, key=lambda i: i["hours_overdue"]) if overdue else None
    return {
        "total_interviews": len(items),
        "by_status": dict(counts),
        "overdue_count": len(overdue),
        "worst_overdue": (
            {
                "candidate_id": worst["candidate_id"],
                "round": worst["round"],
                "panelist": worst["panelist"],
                "hours_overdue": worst["hours_overdue"],
            }
            if worst
            else None
        ),
    }

"""The fixed replay scenario, disclosed in full.

Everything a recruiter would normally type into an ATS is seeded here as a
*fixed, declared* replay so the coordination layer can be exercised against
the real resume corpus:

- TODAY is fixed at 2026-10-16. All timestamps are relative to it.
- One interviewer panel (6 people) with explicit weekly availability windows.
- Five loop rounds in fixed order.
- Per-candidate "last touch" timestamps (recruiter's last contact with the
  candidate) spread 1–21 days before today, by seeded offset.
- Seeded completed interviews in the past 7 days with feedback submitted /
  overdue / still-within-SLA states, by seeded offset.

None of this is presented as live data; the README and the UI both label it
a seeded replay scenario. The resume scores it all hangs off are 100% real.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

TODAY = date(2026, 10, 16)
TODAY_START = datetime(2026, 10, 16, 9, 0)

# ---------------------------------------------------------------------------
# Panel: name -> {role, availability: {weekday(0=Mon): [(start,end), ...]}}
# Times are local (Toronto) 30-minute-slot interview windows.
# ---------------------------------------------------------------------------

PANEL = {
    "Priya Nair": {
        "role": "Recruiter",
        "availability": {0: [(9, 17)], 1: [(9, 17)], 2: [(9, 17)], 3: [(9, 17)], 4: [(9, 17)]},
    },
    "Daniel Okafor": {
        "role": "Hiring Manager",
        "availability": {1: [(10, 16)], 2: [(10, 16)], 3: [(10, 16)]},
    },
    "Mei Chen": {
        "role": "Staff Engineer · System Design",
        "availability": {0: [(10, 15)], 2: [(10, 15)], 4: [(10, 15)]},
    },
    "Tomás Rivera": {
        "role": "Senior Engineer · Technical Deep-Dive",
        "availability": {1: [(11, 17)], 2: [(11, 17)], 3: [(11, 17)], 4: [(11, 17)]},
    },
    "Sarah Kim": {
        "role": "Engineering Manager · Values & Culture",
        "availability": {0: [(9, 14)], 1: [(9, 14)], 2: [(9, 14)], 3: [(9, 14)]},
    },
    "Vikram Rao": {
        "role": "QA Lead · Testing Round",
        "availability": {2: [(10, 16)], 3: [(10, 16)], 4: [(10, 16)]},
    },
}

ROUNDS = [
    {"name": "Recruiter Screen", "panelist": "Priya Nair", "minutes": 15},
    {"name": "Technical Deep-Dive", "panelist": "Tomás Rivera", "minutes": 60},
    {"name": "System Design", "panelist": "Mei Chen", "minutes": 60},
    {"name": "Hiring Manager", "panelist": "Daniel Okafor", "minutes": 45},
    {"name": "Values & Culture", "panelist": "Sarah Kim", "minutes": 30},
]

# Recruiter screen is already done for the whole shortlist (seeded as
# completed 3–9 days before TODAY, offsets below by candidate rank).
SCREEN_DONE_OFFSETS = [9, 8, 7, 7, 6, 6, 5, 5, 4, 4, 3, 3]

# Days since the recruiter last touched the candidate, by shortlist rank.
# Deliberately spread so the slippage board shows the full risk spectrum.
LAST_TOUCH_OFFSETS = [2, 9, 5, 14, 3, 21, 7, 4, 12, 6, 1, 18]

# Seeded *completed* interviews in the replay window (past 7 days) with
# feedback outcomes. end_offset: days before TODAY the interview ended.
# feedback_offset: days before TODAY feedback was submitted (None = never).
SEEDED_INTERVIEWS = [
    # (candidate_rank0, round_name, end_offset_days, end_hour, feedback_offset_days)
    (0, "Recruiter Screen", 9, 10, 9),     # submitted same day
    (0, "Technical Deep-Dive", 4, 14, 3),  # submitted next day, within SLA
    (1, "Recruiter Screen", 8, 11, None),  # never submitted -> overdue
    (1, "Technical Deep-Dive", 3, 11, None),  # never submitted -> overdue
    (2, "Recruiter Screen", 7, 9, 6),      # submitted, within SLA
    (3, "Recruiter Screen", 7, 15, None),  # overdue
    (4, "Recruiter Screen", 6, 10, 5),    # submitted
    # Ends Oct 15 14:00 -> SLA deadline Oct 16 14:00, 5h left at review time:
    # the one "due soon" item in the replay.
    (4, "Technical Deep-Dive", 1, 14, None),  # due soon (5h remaining)
    (5, "Recruiter Screen", 6, 14, None),  # overdue
    # Deliberate same-day stack in the replay: screen at 14:00 and deep-dive
    # at 16:00 on the same day. The scheduler's double-booking detector must
    # flag this as a candidate-fatigue risk.
    (5, "Technical Deep-Dive", 6, 16, None),  # same day as screen -> flagged
    (6, "Recruiter Screen", 5, 10, 4),    # submitted
    (7, "Recruiter Screen", 5, 11, None),  # overdue
    (8, "Recruiter Screen", 4, 9, 3),     # submitted
]

FEEDBACK_SLA_HOURS = 24
# A feedback item is "due soon" when the SLA clock has less than this left.
DUE_SOON_HOURS = 6
# A candidate goes stale when the recruiter hasn't touched them this long.
STALE_DAYS = 7


def seeded_interview_records(shortlist: list[dict]) -> list[dict]:
    """Expand SEEDED_INTERVIEWS into concrete records with timestamps."""
    records = []
    for rank, round_name, end_off, end_hour, fb_off in SEEDED_INTERVIEWS:
        if rank >= len(shortlist):
            continue
        cand = shortlist[rank]
        rnd = next(r for r in ROUNDS if r["name"] == round_name)
        end = datetime.combine(TODAY - timedelta(days=end_off), time(end_hour, 0))
        start = end - timedelta(minutes=rnd["minutes"])
        records.append(
            {
                "candidate_id": cand["id"],
                "candidate_rank": rank + 1,
                "round": round_name,
                "panelist": rnd["panelist"],
                "start": start.isoformat(),
                "end": end.isoformat(),
                "feedback_submitted_at": (
                    datetime.combine(TODAY - timedelta(days=fb_off), time(12, 0)).isoformat()
                    if fb_off is not None
                    else None
                ),
            }
        )
    return records


def scenario_disclosure() -> dict:
    return {
        "today": TODAY.isoformat(),
        "job_spec": "Senior Backend Engineer (Java), B2B SaaS, Toronto (hybrid)",
        "feedback_sla_hours": FEEDBACK_SLA_HOURS,
        "stale_days": STALE_DAYS,
        "note": "Seeded fixed replay scenario. Panel availability, touch "
        "timestamps, and interview/feedback history are seeded and disclosed; "
        "resume scores come from the real corpus.",
    }

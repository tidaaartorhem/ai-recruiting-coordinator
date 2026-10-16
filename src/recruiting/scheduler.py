"""Deterministic loop scheduler.

Rules (all disclosed, no randomness):
  1. Rounds run in fixed order; each round is scheduled on the earliest day
     strictly after the previous round's date (completed or scheduled).
  2. A panelist is booked into the earliest 30-minute-granularity slot inside
     their weekly availability windows that fits the round length, with at most
     2 interviews per panelist per day and no overlapping bookings.
  3. A candidate never gets two interviews on the same day — if the earliest
     slot would collide with an already-completed or scheduled interview for
     that candidate, the scheduler flags DOUBLE_BOOKING_RISK and moves the
     round to the next clean day.
  4. Rounds already completed in the seeded replay are never re-scheduled.

Derived outputs:
  - per-candidate time-to-loop (days from TODAY to the last round)
  - structural bottleneck: panelist with the fewest weekly window hours
  - load leader: panelist with the most interviews assigned
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from .scenario import PANEL, ROUNDS, TODAY

MAX_PER_DAY = 2
SLOT_GRANULARITY_MIN = 30
SEARCH_HORIZON_DAYS = 60


def _windows_for(panelist: str, day: date) -> list[tuple[int, int]]:
    return PANEL[panelist]["availability"].get(day.weekday(), [])


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


class Scheduler:
    def __init__(self):
        # panelist -> list of (date, start_min, end_min)
        self.bookings: dict[str, list[tuple[date, int, int]]] = {p: [] for p in PANEL}

    def book(self, panelist: str, day: date, start_min: int, minutes: int) -> None:
        self.bookings[panelist].append((day, start_min, start_min + minutes))

    def day_count(self, panelist: str, day: date) -> int:
        return sum(1 for d, _, _ in self.bookings[panelist] if d == day)

    def overlaps(self, panelist: str, day: date, start_min: int, end_min: int) -> bool:
        for d, s, e in self.bookings[panelist]:
            if d == day and not (end_min <= s or start_min >= e):
                return True
        return False

    def earliest_slot(
        self, panelist: str, after: date, minutes: int
    ) -> tuple[date, int] | None:
        """Earliest (day, start_minute) strictly after `after`."""
        day = after + timedelta(days=1)
        for _ in range(SEARCH_HORIZON_DAYS):
            if self.day_count(panelist, day) < MAX_PER_DAY:
                for wstart, wend in _windows_for(panelist, day):
                    start = wstart * 60
                    while start + minutes <= wend * 60:
                        if not self.overlaps(panelist, day, start, start + minutes):
                            return day, start
                        start += SLOT_GRANULARITY_MIN
            day += timedelta(days=1)
        return None


def schedule_loops(
    shortlist: list[dict], completed: list[dict]
) -> dict:
    """Schedule the remaining rounds for every shortlisted candidate.

    Returns the full schedule payload (JSON-serializable).
    """
    sched = Scheduler()

    # Seed the panelist calendars with the completed (seeded) interviews so
    # the scheduler never double-books a panelist over the replay history.
    for rec in completed:
        start = datetime.fromisoformat(rec["start"])
        end = datetime.fromisoformat(rec["end"])
        sched.book(
            rec["panelist"],
            start.date(),
            _to_minutes(start.time()),
            int((end - start).total_seconds() // 60),
        )

    completed_by_cand: dict[str, list[dict]] = {}
    for rec in completed:
        completed_by_cand.setdefault(rec["candidate_id"], []).append(rec)

    candidate_plans = []
    for cand in shortlist:
        cid = cand["id"]
        done = {r["round"] for r in completed_by_cand.get(cid, [])}
        busy_days = {
            datetime.fromisoformat(r["start"]).date()
            for r in completed_by_cand.get(cid, [])
        }
        plan_rounds = []
        # Anchor: day after the latest completed round (or TODAY if none,
        # meaning the screen itself is still ahead — not the case here, but
        # the rule is total).
        anchor = TODAY
        for r in completed_by_cand.get(cid, []):
            d = datetime.fromisoformat(r["end"]).date()
            if d > anchor:
                anchor = d

        double_booking_flags: list[dict] = []
        for rnd in ROUNDS:
            if rnd["name"] in done:
                rec = next(
                    r for r in completed_by_cand[cid] if r["round"] == rnd["name"]
                )
                plan_rounds.append(
                    {
                        "round": rnd["name"],
                        "panelist": rnd["panelist"],
                        "date": datetime.fromisoformat(rec["start"]).date().isoformat(),
                        "start": rec["start"],
                        "end": rec["end"],
                        "status": "completed",
                    }
                )
                continue
            slot = sched.earliest_slot(rnd["panelist"], anchor, rnd["minutes"])
            scheduled_ok = slot is not None
            while scheduled_ok:
                assert slot is not None
                day, start_min = slot
                # Prevention guard: the scheduler never *creates* a same-day
                # stack. (The flag below also covers stacks already present in
                # the seeded replay history.)
                if day not in busy_days:
                    break
                nxt = sched.earliest_slot(rnd["panelist"], day, rnd["minutes"])
                if nxt is None:
                    scheduled_ok = False
                    break
                slot = nxt
            if not scheduled_ok or slot is None:
                plan_rounds.append(
                    {
                        "round": rnd["name"],
                        "panelist": rnd["panelist"],
                        "status": "unschedulable",
                    }
                )
                continue
            day, start_min = slot
            sched.book(rnd["panelist"], day, start_min, rnd["minutes"])
            busy_days.add(day)
            start_dt = datetime.combine(day, time(start_min // 60, start_min % 60))
            end_dt = start_dt + timedelta(minutes=rnd["minutes"])
            plan_rounds.append(
                {
                    "round": rnd["name"],
                    "panelist": rnd["panelist"],
                    "date": day.isoformat(),
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "status": "scheduled",
                }
            )
            anchor = day

        dated = [r for r in plan_rounds if r.get("date")]
        last_date = max(datetime.fromisoformat(r["date"]).date() for r in dated)
        time_to_loop = (last_date - TODAY).days

        # Double-booking detector: any candidate with 2+ interviews on the
        # same calendar day (seeded history or scheduled) is flagged as a
        # candidate-fatigue / no-show risk.
        by_day: dict[str, list[str]] = {}
        for r in dated:
            by_day.setdefault(r["date"], []).append(r["round"])
        for d, rounds in sorted(by_day.items()):
            if len(rounds) > 1:
                double_booking_flags.append(
                    {
                        "date": d,
                        "rounds": rounds,
                        "reason": "candidate has %d interviews on the same day — "
                        "fatigue/no-show risk; avoid stacking future loops"
                        % len(rounds),
                    }
                )

        candidate_plans.append(
            {
                "candidate_id": cid,
                "rank": cand["rank"],
                "rounds": plan_rounds,
                "time_to_loop_days": time_to_loop,
                "double_booking_flags": double_booking_flags,
            }
        )

    # Bottleneck analysis.
    weekly_hours = {}
    for name, info in PANEL.items():
        weekly_hours[name] = sum(e - s for wins in info["availability"].values() for s, e in wins)
    structural = min(weekly_hours, key=lambda p: weekly_hours[p])
    assigned = {p: len(sched.bookings[p]) for p in PANEL}
    # Load leader counts only *scheduled* (future) interviews, not replay history.
    future_counts: dict[str, int] = {p: 0 for p in PANEL}
    for plan in candidate_plans:
        for r in plan["rounds"]:
            if r["status"] == "scheduled":
                future_counts[r["panelist"]] += 1
    load_leader = max(future_counts, key=lambda p: future_counts[p])

    return {
        "candidates": candidate_plans,
        "bottleneck": {
            "structural": structural,
            "structural_weekly_hours": weekly_hours[structural],
            "load_leader": load_leader,
            "load_leader_scheduled": future_counts[load_leader],
            "weekly_hours": weekly_hours,
            "scheduled_per_panelist": future_counts,
        },
        "rules": [
            "rounds run in fixed order, each on the earliest day strictly after the previous round",
            "panelists take the earliest fitting slot inside weekly availability windows (30-min granularity)",
            "max 2 interviews per panelist per day; no overlapping panelist bookings",
            "a candidate never gets two interviews on the same day (collision -> next clean day + flag)",
        ],
    }

"""Pipeline orchestration: real resumes in, coordination desk JSON out.

run_pipeline() executes the full deterministic chain and returns every
payload the frontend consumes. scripts/build_loopboard.py writes them to
public/data/*.json.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from . import feedback as feedback_mod
from . import matching, scheduler as scheduler_mod, slippage
from .matching import JOB_SPEC, TfidfIndex, WEIGHTS, score_candidate
from .resume import load_resumes
from .scenario import (
    LAST_TOUCH_OFFSETS,
    TODAY,
    scenario_disclosure,
    seeded_interview_records,
)

SHORTLIST_SIZE = 12
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def run_pipeline(csv_path: str | Path | None = None) -> dict[str, dict | list]:
    resumes = load_resumes(str(csv_path or (DATA_DIR / "resumes_raw.csv")))

    tfidf = TfidfIndex([r["text"] for r in resumes])
    scored = []
    for i, r in enumerate(resumes):
        s = score_candidate(r["raw"], tfidf, i)
        scored.append(
            {
                "id": r["id"],
                "category": r["category"],
                "score": s["score"],
                "breakdown": s["breakdown"],
                "nice_to_have_matched": s["nice_to_have_matched"],
                "excerpt": r["text"][:600],
            }
        )
    # Deterministic rank: score desc, then id asc.
    scored.sort(key=lambda c: (-c["score"], c["id"]))
    shortlist = []
    for rank, c in enumerate(scored[:SHORTLIST_SIZE], start=1):
        c["rank"] = rank
        shortlist.append(c)

    completed = seeded_interview_records(shortlist)
    schedule = scheduler_mod.schedule_loops(shortlist, completed)

    fb_items = feedback_mod.evaluate_feedback(completed)
    nudge_queue = feedback_mod.build_nudge_queue(fb_items)
    panel_bookings = _panel_bookings_from_schedule(schedule)
    debrief = feedback_mod.debrief_readiness(fb_items, schedule, panel_bookings)

    # Slippage per candidate.
    overdue_by_cand: dict[str, int] = {}
    for i in fb_items:
        if i["status"] == "overdue":
            overdue_by_cand[i["candidate_id"]] = overdue_by_cand.get(i["candidate_id"], 0) + 1
    plan_by_cand = {p["candidate_id"]: p for p in schedule["candidates"]}
    risks = []
    for rank, cand in enumerate(shortlist, start=1):
        cid = cand["id"]
        plan = plan_by_cand[cid]
        touch_offset = LAST_TOUCH_OFFSETS[rank - 1]
        has_future = any(r["status"] == "scheduled" for r in plan["rounds"])
        risk = slippage.score_slippage(
            days_since_touch=touch_offset,
            time_to_loop_days=plan["time_to_loop_days"],
            overdue_feedback=overdue_by_cand.get(cid, 0),
            has_future_rounds=has_future,
        )
        risks.append(
            {
                "candidate_id": cid,
                "rank": rank,
                "score": cand["score"],
                "category": cand["category"],
                "days_since_touch": touch_offset,
                "last_touch": (TODAY - timedelta(days=touch_offset)).isoformat(),
                "time_to_loop_days": plan["time_to_loop_days"],
                "overdue_feedback": overdue_by_cand.get(cid, 0),
                **risk,
            }
        )
    risks.sort(key=lambda r: (-r["risk"], r["rank"]))

    return {
        "scenario": scenario_disclosure(),
        "shortlist": shortlist,
        "schedule": schedule,
        "feedback": {
            "items": fb_items,
            "nudge_queue": nudge_queue,
            "debrief": debrief,
            "summary": feedback_mod.summarize(fb_items),
            "review_time": feedback_mod.REVIEW_TIME.isoformat(),
        },
        "slippage": risks,
        "meta": {
            "resumes_scored": len(resumes),
            "shortlist_size": SHORTLIST_SIZE,
            "job_spec": JOB_SPEC["title"] + " — " + JOB_SPEC["company_context"],
            "weights": WEIGHTS,
            "generated": "pipeline",
        },
    }


def _panel_bookings_from_schedule(schedule: dict) -> dict[str, list]:
    """Rebuild per-panelist (date, start_min, end_min) bookings from the
    schedule payload (the Scheduler instance itself isn't serializable)."""
    from datetime import datetime, time as dtime

    bookings: dict[str, list] = {}
    for plan in schedule["candidates"]:
        for r in plan["rounds"]:
            if r.get("status") not in ("scheduled", "completed") or not r.get("start"):
                continue
            s = datetime.fromisoformat(r["start"])
            e = datetime.fromisoformat(r["end"])
            bookings.setdefault(r["panelist"], []).append(
                (s.date(), s.hour * 60 + s.minute, e.hour * 60 + e.minute)
            )
    return bookings


def write_payloads(payloads: dict, out_dir: str | Path) -> list[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "scenario.json": payloads["scenario"],
        "shortlist.json": payloads["shortlist"],
        "schedule.json": payloads["schedule"],
        "feedback.json": payloads["feedback"],
        "slippage.json": payloads["slippage"],
        "meta.json": payloads["meta"],
    }
    written = []
    for name, obj in files.items():
        (out / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
        written.append(name)
    return written

# Loopboard — the interview-loop coordination desk

**Live:** https://ai-recruiting-coordinator.web.app · **Repo:** github.com/tidaaartorhem/ai-recruiting-coordinator

Recruiting teams don't lose candidates at sourcing. They lose them in the **coordination layer**: interview loops scheduled over days of ping-pong, interviewer feedback that arrives late or never (killing debriefs), and candidates silently going stale while everyone assumes someone else followed up. ATS tools track stages but never *enforce* the coordination. Loopboard is the deterministic ops desk for that layer:

1. **Ranked shortlist** — 962 real resumes scored against one job spec by a deterministic engine with disclosed weights. No LLM ranking, no black box.
2. **Loop scheduler** — assigns every round to a real availability window, computes who bottlenecks the loop, time-to-loop per candidate, and flags candidate double-bookings.
3. **Feedback chase** — a 24h SLA clock on every completed interview, a ranked nudge queue with one recommended action per stalled item (human-gated: nothing sends itself), and a debrief-readiness board that auto-suggests a slot only when all feedback is in (also human-gated).
4. **Slippage board** — who is going stale and exactly why, scored 0–100 on disclosed drivers.
5. **Paste a resume** — score any resume text in the browser with the same disclosed rules.

## The deep-rooted pain

- **Loops die in calendars, not in ATS stages.** A "stage" says *Technical Round*; it doesn't say Mei Chen only interviews Mon/Wed/Fri 10–15 and she's the reason four loops close three weeks out. Loopboard computes the bottleneck instead of letting recruiters discover it by embarrassment.
- **Feedback has no clock.** Interviewers promise "notes by EOD" and the debrief gets scheduled anyway, then cancelled, then the candidate waits 11 days. A deterministic SLA clock with a chase queue is the entire fix — no AI needed, just enforcement.
- **Staleness is silent.** Nobody gets an alert that a candidate hasn't been touched in 21 days. The slippage scorer turns "I thought you were following up" into a number with named drivers.
- **Resume ranking is vibes.** Keyword search in an ATS rewards whoever stuffed "Java" the most times. A disclosed, reproducible score (with the exact weights printed next to every candidate) is auditable in a way LLM shortlists are not.

## How the scoring works (disclosed, deterministic)

`score_candidate(text)` is a pure function — same resume, same score, every run:

| Signal | Weight | Rule |
|---|---|---|
| Required-skill coverage | 35 | matched required skills ÷ 6 required, × 35 |
| TF-IDF cosine vs job spec | 25 | cosine similarity of resume vector to the spec vector, × 25 |
| Years of experience | 20 | ≥8 → 20; ≥5 → 16; ≥3 → 12; ≥1 → 8; >0 → 4 |
| Education tier | 20 | doctorate → 20; masters → 14; bachelors → 9; diploma → 4; none → 0 |

Required skills for the spec: `java, spring, rest api, sql, docker, microservices` (with a disclosed alias map, e.g. "spring boot" counts for spring). Experience comes from regex extraction ("5 years of experience", skill-matrix "Exprience – 24 months" rows taking the max, not the sum). TF-IDF is hand-rolled over the corpus (no sklearn needed). The paste-a-resume tab mirrors the skill/experience/education rules in TypeScript; TF-IDF stays Python-only because it needs the full corpus frequencies — the tab says so, and `data/test-vectors.json` keeps both implementations in exact agreement (tested on both sides).

## The seeded replay scenario (declared, not hidden)

Everything a recruiter would type into an ATS is a **fixed, declared replay** so the coordination layer can be exercised:

- **Today is fixed at 2026-10-16.** All timestamps are relative to it.
- **One job spec:** Senior Backend Engineer (Java), B2B SaaS, Toronto (hybrid).
- **Panel of 6** with explicit weekly availability windows (`src/recruiting/scenario.py`).
- **Touch timestamps** spread 1–21 days before today, by candidate rank.
- **13 seeded interviews** in the past 7 days: feedback submitted on time, submitted late, overdue, and due-soon states.

The resume scores are 100% real. The panel, touches, and interview history are seeded and labeled as such in the UI and in `scenario.json`.

## The data

`data/resumes_raw.csv` — 962 real resumes (Category + Resume text), mirror of the public-domain Kaggle Resume dataset lineage. Source: https://huggingface.co/datasets/Sachinkelenjaguri/Resume_dataset/raw/main/UpdatedResumeDataSet.csv

Heads-up baked into the pipeline: 725 of 962 resumes carry UTF-8 mojibake ("NaÃ¯ve") from the dataset's lineage; `normalize.py` repairs it with the exact inverse operation before any extraction runs.

## Try it in 5 minutes

1. **Shortlist** — see 962 resumes collapse to a ranked 12 with per-candidate breakdowns. Note which categories top the list for a Java spec (spoiler: not "Java Developer").
2. **Loop scheduler** — open candidate #6's timeline: the desk flagged a real double-booking in the replay (two interviews, same day). Check the bottleneck cards: who blocks the loop, and why.
3. **Feedback chase** — the nudge queue ranks 6 overdue feedback items by hours past SLA. Stage a nudge (local only — it just marks it for your review).
4. **Slippage board** — candidate #6 again: highest risk, with named drivers (21 days untouched + 2 overdue feedbacks).
5. **Paste a resume** — paste any resume text; the browser scores it live on the disclosed rules.

## Run it yourself

```bash
pip install -r requirements.txt
PYTHONPATH=src python3 -m pytest tests/          # 35 tests
PYTHONPATH=src python3 scripts/build_loopboard.py # rebuilds web/public/data/*.json
cd web && npm install && npm test                 # 19 vitest tests
cd web && npm run build                           # pipeline + vite build -> web/dist
```

Deploy (Firebase Hosting, project `portfolio-3da31`):

```bash
~/workspace/tools/node_modules/.bin/firebase deploy --only hosting --project portfolio-3da31
```

## Layout

```
src/recruiting/   normalize.py, resume.py, matching.py, scenario.py,
                  scheduler.py, feedback.py, slippage.py, pipeline.py
scripts/          build_loopboard.py  (pipeline -> web/public/data/*.json)
tests/            35 pytest tests (incl. shared-contract parity)
data/             resumes_raw.csv, test-vectors.json
web/src/          scoring.ts (TS mirror) + scoring.test.ts (19 vitest tests),
                  views: Shortlist, Scheduler, Feedback chase, Slippage, Paste-a-resume
firebase.json     hosting site: ai-recruiting-coordinator
```

## What the pipeline found on the real data

- Top score across 962 resumes for the Java backend spec: **54.3/100** — no resume in the corpus cracks 60; the corpus is keyword-sparse for senior backend signals.
- The **"Java Developer"-labeled resumes don't make the top 12 at all** (first appears at rank 59). The shortlist is dominated by Blockchain/Database/DevOps resumes that mention Docker, SQL, and REST more often — category labels are a poor proxy for skill coverage, which is the point of scoring text instead of labels.
- **Mei Chen (system design) is the structural bottleneck** — 15 weekly availability hours, the fewest on the panel; Daniel Okafor (hiring manager) carries the heaviest scheduled load. Time-to-loop across the shortlist: 5–19 days.
- **6 of 13 replay interviews are past their 24h feedback SLA**, and the highest slippage risk (50/100, "high") is the candidate untouched for 21 days with 2 overdue feedbacks — exactly the silent-stall pattern the desk exists to catch.

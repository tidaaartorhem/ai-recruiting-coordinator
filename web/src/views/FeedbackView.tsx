import { useState } from "react";
import type { FeedbackPayload } from "../types";

const STATUS_CLASS: Record<string, string> = {
  submitted_on_time: "badge ok",
  submitted_late: "badge warn",
  overdue: "badge bad",
  due_soon: "badge warn",
  pending: "badge neutral",
};

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-CA", {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export default function FeedbackView({ feedback }: { feedback: FeedbackPayload }) {
  const [staged, setStaged] = useState<Set<string>>(new Set());
  const [proposed, setProposed] = useState<Set<string>>(new Set());
  const s = feedback.summary;

  const stage = (key: string) =>
    setStaged((prev) => new Set(prev).add(key));
  const propose = (key: string) =>
    setProposed((prev) => new Set(prev).add(key));

  const ready = feedback.debrief.filter((d) => !d.blocked);
  const blocked = feedback.debrief.filter((d) => d.blocked);

  return (
    <div>
      <div className="grid3">
        <div className="card">
          <h3>Feedback SLA</h3>
          <div style={{ fontSize: 20, fontWeight: 700 }}>24 hours</div>
          <div className="hint">Clock starts when each interview ends. Review time: {fmt(feedback.review_time)}.</div>
        </div>
        <div className="card">
          <h3>Overdue right now</h3>
          <div style={{ fontSize: 20, fontWeight: 700, color: s.overdue_count ? "var(--bad)" : "var(--ok)" }}>
            {s.overdue_count} of {s.total_interviews}
          </div>
          <div className="hint">
            {s.worst_overdue
              ? `Worst: ${s.worst_overdue.panelist}, ${s.worst_overdue.round} (${s.worst_overdue.candidate_id}) — ${s.worst_overdue.hours_overdue}h overdue.`
              : "Nothing overdue."}
          </div>
        </div>
        <div className="card">
          <h3>Debrief readiness</h3>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{ready.length} ready · {blocked.length} blocked</div>
          <div className="hint">Ready = every completed interview has feedback and every round is slotted.</div>
        </div>
      </div>

      <div className="card">
        <h2>Chase queue — one action per stalled item</h2>
        <p className="hint">Ranked by overdue hours. Every nudge is human-gated: staging it here only marks it for your review — nothing is sent automatically.</p>
        <table className="data">
          <thead>
            <tr><th>Candidate</th><th>Round</th><th>Panelist</th><th>Status</th><th>Recommended action</th><th></th></tr>
          </thead>
          <tbody>
            {feedback.nudge_queue.map((n) => {
              const key = `${n.candidate_id}-${n.round}`;
              const isStaged = staged.has(key);
              return (
                <tr key={key}>
                  <td><strong>#{n.candidate_rank}</strong> <span className="mono">{n.candidate_id}</span></td>
                  <td>{n.round}</td>
                  <td>{n.panelist}</td>
                  <td>
                    <span className={STATUS_CLASS[n.status] || "badge neutral"}>
                      {n.status.replace(/_/g, " ")}
                      {n.status === "overdue" ? ` · ${n.hours_overdue}h` : ""}
                      {n.status === "due_soon" ? ` · ${n.hours_remaining}h left` : ""}
                    </span>
                  </td>
                  <td style={{ maxWidth: 380 }}>{n.recommended_action}</td>
                  <td>
                    <button className="btn" disabled={isStaged} onClick={() => stage(key)}>
                      {isStaged ? "Staged ✓" : "Stage nudge"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {feedback.nudge_queue.length === 0 && <p className="hint">Queue clear — no overdue or due-soon feedback.</p>}
      </div>

      <div className="grid2">
        <div className="card">
          <h2>Debrief-ready</h2>
          <p className="hint">Suggested slot: next weekday 15:00 with the hiring manager and recruiter free. Proposed, never booked.</p>
          {ready.map((d) => {
            const isProposed = proposed.has(d.candidate_id);
            return (
              <div key={d.candidate_id} style={{ padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
                <div><strong>#{d.candidate_rank}</strong> <span className="mono">{d.candidate_id}</span></div>
                <div className="hint" style={{ margin: "2px 0 8px" }}>Suggested: {fmt(d.suggested_debrief)}</div>
                <button className="btn primary" disabled={isProposed} onClick={() => propose(d.candidate_id)}>
                  {isProposed ? "Proposed ✓" : "Propose debrief"}
                </button>
              </div>
            );
          })}
          {ready.length === 0 && <p className="hint">No candidate is debrief-ready yet.</p>}
        </div>
        <div className="card">
          <h2>Blocked</h2>
          <p className="hint">Exactly what stands between each candidate and a debrief.</p>
          {blocked.map((d) => (
            <div key={d.candidate_id} style={{ padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
              <div><strong>#{d.candidate_rank}</strong> <span className="mono">{d.candidate_id}</span></div>
              <ul style={{ margin: "4px 0", paddingLeft: 18, color: "var(--ink-soft)", fontSize: 13 }}>
                {d.blockers!.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>All interviews</h2>
        <table className="data">
          <thead><tr><th>Candidate</th><th>Round</th><th>Panelist</th><th>Ended</th><th>SLA deadline</th><th>Feedback</th><th>Status</th></tr></thead>
          <tbody>
            {feedback.items.map((it, i) => (
              <tr key={i}>
                <td><strong>#{it.candidate_rank}</strong> <span className="mono">{it.candidate_id}</span></td>
                <td>{it.round}</td>
                <td>{it.panelist}</td>
                <td>{fmt(it.end)}</td>
                <td>{fmt(it.sla_deadline)}</td>
                <td>{fmt(it.feedback_submitted_at)}</td>
                <td><span className={STATUS_CLASS[it.status]}>{it.status.replace(/_/g, " ")}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

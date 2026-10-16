import type { SchedulePayload, ShortlistCandidate } from "../types";

function fmtDateTime(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-CA", {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

const STATUS_BADGE: Record<string, string> = {
  scheduled: "badge",
  completed: "badge ok",
  unschedulable: "badge bad",
};

export default function SchedulerView({ schedule, shortlist }: {
  schedule: SchedulePayload;
  shortlist: ShortlistCandidate[];
}) {
  const b = schedule.bottleneck;
  const idToCategory = Object.fromEntries(shortlist.map((c) => [c.id, c.category]));
  const times = schedule.candidates.map((p) => p.time_to_loop_days);

  return (
    <div>
      <div className="grid3">
        <div className="card">
          <h3>Structural bottleneck</h3>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{b.structural}</div>
          <div className="hint">Fewest weekly availability hours: {b.structural_weekly_hours}h. Every loop that needs this panelist waits on their calendar.</div>
        </div>
        <div className="card">
          <h3>Load leader</h3>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{b.load_leader}</div>
          <div className="hint">{b.load_leader_scheduled} upcoming interviews assigned — the most of any panelist.</div>
        </div>
        <div className="card">
          <h3>Time-to-loop</h3>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{Math.min(...times)}–{Math.max(...times)} days</div>
          <div className="hint">From today to each candidate's final round. Panelist load per week shown below.</div>
        </div>
      </div>

      <div className="card">
        <h2>Scheduling rules (deterministic)</h2>
        <ul style={{ margin: "4px 0", paddingLeft: 20, color: "var(--ink-soft)" }}>
          {schedule.rules.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
        <table className="data" style={{ marginTop: 12 }}>
          <thead><tr><th>Panelist</th><th>Weekly window hours</th><th>Upcoming interviews</th></tr></thead>
          <tbody>
            {Object.keys(b.weekly_hours).map((p) => (
              <tr key={p}>
                <td><strong>{p}</strong></td>
                <td>{b.weekly_hours[p]}h</td>
                <td>{b.scheduled_per_panelist[p]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {schedule.candidates.map((plan) => (
        <div className="card" key={plan.candidate_id}>
          <h2>
            #{plan.rank} · <span className="mono">{plan.candidate_id}</span>{" "}
            <span className="badge neutral">{idToCategory[plan.candidate_id]}</span>{" "}
            <span className="badge violet">loop closes in {plan.time_to_loop_days}d</span>
          </h2>
          <div className="timeline">
            {plan.rounds.map((r, i) => (
              <div className={`tstep ${r.status}`} key={i}>
                <div>
                  <div><strong>{r.round}</strong> — {r.panelist} <span className={STATUS_BADGE[r.status]}>{r.status}</span></div>
                  <div className="when">{fmtDateTime(r.start)}{r.end ? ` → ${fmtDateTime(r.end)}` : ""}</div>
                </div>
              </div>
            ))}
          </div>
          {plan.double_booking_flags.map((f, i) => (
            <div className="flag" key={i}>
              <strong>Double-booking risk · {f.date}:</strong> {f.rounds.join(" + ")} — {f.reason}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

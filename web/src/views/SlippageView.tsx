import type { SlippageRisk } from "../types";

const BUCKET_CLASS: Record<string, string> = {
  low: "badge ok",
  watch: "badge warn",
  high: "badge bad",
  critical: "badge bad",
};

export default function SlippageView({ risks }: { risks: SlippageRisk[] }) {
  const counts = risks.reduce<Record<string, number>>((acc, r) => {
    acc[r.bucket] = (acc[r.bucket] || 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <div className="card">
        <h2>Slippage risk board</h2>
        <p className="hint">
          Who is silently going stale, and why. Score 0–100: staleness (3/day past 7 stale-free days, cap 30) +
          loop drag (2/day past 14 days to close, cap 20) + feedback debt (10 per overdue item, cap 30) +
          unscheduled loop (+20). Buckets: 0–24 low · 25–49 watch · 50–74 high · 75+ critical.
        </p>
        <div className="badges">
          {(["critical", "high", "watch", "low"] as const).map((b) => (
            <span key={b} className={BUCKET_CLASS[b]}>{b}: {counts[b] || 0}</span>
          ))}
        </div>
      </div>

      {risks.map((r) => (
        <div className="card" key={r.candidate_id}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <h2 style={{ margin: 0 }}>
              #{r.rank} · <span className="mono">{r.candidate_id}</span>{" "}
              <span className="badge neutral">{r.category}</span>
            </h2>
            <span className={BUCKET_CLASS[r.bucket]} style={{ fontSize: 13 }}>
              {r.bucket} · {r.risk}/100
            </span>
          </div>
          <div className="kv" style={{ marginTop: 10 }}>
            <dt>Last touch</dt><dd>{r.last_touch} ({r.days_since_touch}d ago)</dd>
            <dt>Loop closes in</dt><dd>{r.time_to_loop_days} days</dd>
            <dt>Overdue feedback</dt><dd>{r.overdue_feedback}</dd>
            <dt>Match score</dt><dd>{r.score.toFixed(1)} / 100</dd>
          </div>
          {r.drivers.length > 0 ? (
            <ul style={{ margin: "10px 0 0", paddingLeft: 18, color: "var(--ink-soft)" }}>
              {r.drivers.map((d, i) => <li key={i}>{d}</li>)}
            </ul>
          ) : (
            <p className="hint" style={{ margin: "10px 0 0" }}>No risk drivers — this candidate is moving cleanly.</p>
          )}
        </div>
      ))}
    </div>
  );
}

import { useState } from "react";
import type { ShortlistCandidate } from "../types";

function ScoreBar({ score }: { score: number }) {
  return (
    <span className="scorebar">
      <span className="track">
        <span className="fill" style={{ width: `${score}%` }} />
      </span>
      <span className="num">{score.toFixed(1)}</span>
    </span>
  );
}

function Row({ c }: { c: ShortlistCandidate }) {
  const [open, setOpen] = useState(false);
  const b = c.breakdown;
  return (
    <>
      <tr onClick={() => setOpen(!open)} style={{ cursor: "pointer" }}>
        <td><strong>#{c.rank}</strong></td>
        <td className="mono">{c.id}</td>
        <td>{c.category}</td>
        <td><ScoreBar score={c.score} /></td>
        <td>{b.years_experience} yrs</td>
        <td>{b.education_tier}</td>
        <td style={{ color: "var(--ink-faint)" }}>{open ? "▾" : "▸"}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={7} style={{ background: "#fbfcfe" }}>
            <div className="breakdown">
              <div className="cell">
                <div className="k">Skill coverage · 35</div>
                <div className="v">{b.required_skill_coverage}</div>
                <div className="d">{b.required_skills_matched.join(", ") || "none"} ({b.required_skills_matched.length}/{b.required_skills_total})</div>
              </div>
              <div className="cell">
                <div className="k">TF-IDF cosine · 25</div>
                <div className="v">{b.tfidf_points}</div>
                <div className="d">cosine {b.tfidf_cosine} vs job spec</div>
              </div>
              <div className="cell">
                <div className="k">Experience · 20</div>
                <div className="v">{b.experience_points}</div>
                <div className="d">{b.years_experience} years extracted</div>
              </div>
              <div className="cell">
                <div className="k">Education · 20</div>
                <div className="v">{b.education_points}</div>
                <div className="d">tier: {b.education_tier}</div>
              </div>
            </div>
            {c.nice_to_have_matched.length > 0 && (
              <div style={{ marginTop: 8, fontSize: 12.5, color: "var(--ink-soft)" }}>
                Nice-to-have also present: {c.nice_to_have_matched.join(", ")}
              </div>
            )}
            <div style={{ marginTop: 8, fontSize: 12.5, color: "var(--ink-faint)" }}>
              Excerpt: “{c.excerpt}…”
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function Shortlist({ candidates, meta }: {
  candidates: ShortlistCandidate[];
  meta: { resumes_scored: number; job_spec: string; weights: Record<string, number> };
}) {
  const w = meta.weights;
  return (
    <div>
      <div className="card">
        <h2>Ranked shortlist</h2>
        <p className="hint">
          {meta.resumes_scored} real resumes scored against <strong>{meta.job_spec}</strong>.
          Click a row for the full score breakdown. Weights: skill coverage {w.required_skill_coverage} ·
          TF-IDF cosine {w.tfidf_cosine} · experience {w.years_experience} · education {w.education_tier}.
        </p>
        <table className="data">
          <thead>
            <tr>
              <th>Rank</th><th>ID</th><th>Category</th><th>Score / 100</th>
              <th>Experience</th><th>Education</th><th></th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => <Row key={c.id} c={c} />)}
          </tbody>
        </table>
      </div>
    </div>
  );
}

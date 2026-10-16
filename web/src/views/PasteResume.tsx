import { useMemo, useState } from "react";
import { REQUIRED_SKILLS, scoreSubset } from "../scoring";

const SAMPLE = `Senior Java Developer with 6 years of experience building Spring Boot microservices and REST APIs. SQL databases, Docker containers. B.Tech in Computer Science.`;

export default function PasteResume() {
  const [text, setText] = useState(SAMPLE);
  const result = useMemo(() => (text.trim() ? scoreSubset(text) : null), [text]);

  return (
    <div>
      <div className="card">
        <h2>Paste a resume — score it in your browser</h2>
        <p className="hint">
          Runs the disclosed subset of the match rules locally in TypeScript: required-skill coverage (35),
          years of experience (20), education tier (20). TF-IDF vs the job spec (25) needs the full 962-resume
          corpus, so it only runs in the Python pipeline — the score below is out of 75, not 100, and says so.
          Nothing you paste leaves this page.
        </p>
        <textarea
          className="paste"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste resume text here…"
        />
        {result && (
          <div style={{ marginTop: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span className="scorebar" style={{ minWidth: 200 }}>
                <span className="track"><span className="fill" style={{ width: `${(result.subsetScore / 75) * 100}%` }} /></span>
                <span className="num">{result.subsetScore.toFixed(1)} / 75</span>
              </span>
            </div>
            <div className="breakdown" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
              <div className="cell">
                <div className="k">Skill coverage · 35</div>
                <div className="v">{result.skillPoints}</div>
                <div className="d">
                  {REQUIRED_SKILLS.map((s) => (
                    <span key={s} className={result.matchedRequired.includes(s) ? "badge ok" : "badge neutral"}
                      style={{ marginRight: 4, marginBottom: 4 }}>
                      {result.matchedRequired.includes(s) ? "✓ " : "✗ "}{s}
                    </span>
                  ))}
                </div>
              </div>
              <div className="cell">
                <div className="k">Experience · 20</div>
                <div className="v">{result.experiencePoints}</div>
                <div className="d">{result.years} years extracted</div>
              </div>
              <div className="cell">
                <div className="k">Education · 20</div>
                <div className="v">{result.educationPoints}</div>
                <div className="d">tier: {result.educationTier}</div>
              </div>
            </div>
            <div className="disclosure">
              <b>Shared contract.</b> These are the exact rules the Python pipeline applies
              (verified by <span className="mono">data/test-vectors.json</span>, tested on both sides).
              The full score adds TF-IDF cosine vs the job spec × 25, computed over the corpus.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

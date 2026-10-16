import { useState } from "react";
import "./styles.css";
import { useDeskData } from "./data";
import Shortlist from "./views/Shortlist";
import SchedulerView from "./views/SchedulerView";
import FeedbackView from "./views/FeedbackView";
import SlippageView from "./views/SlippageView";
import PasteResume from "./views/PasteResume";

type Tab = "shortlist" | "scheduler" | "feedback" | "slippage" | "paste";

export default function App() {
  const { data, error } = useDeskData();
  const [tab, setTab] = useState<Tab>("shortlist");

  if (error) return <div className="app"><div className="error">Failed to load desk data: {error}</div></div>;
  if (!data) return <div className="app"><div className="loading">Loading the coordination desk…</div></div>;

  const tabs: Array<{ id: Tab; label: string; count?: number }> = [
    { id: "shortlist", label: "Shortlist", count: data.shortlist.length },
    { id: "scheduler", label: "Loop scheduler", count: data.shortlist.length },
    { id: "feedback", label: "Feedback chase", count: data.feedback.nudge_queue.length },
    { id: "slippage", label: "Slippage board", count: data.slippage.filter((r) => r.bucket !== "low").length },
    { id: "paste", label: "Paste a resume" },
  ];

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1><span className="mark">LB</span>Loopboard</h1>
          <p className="sub">
            The interview-loop coordination desk. Ranked shortlist from real resume text,
            deterministic loop scheduling across interviewer availability, a feedback-SLA
            chase queue with human-gated nudges, and a slippage risk board.
          </p>
          <div className="badges">
            <span className="badge neutral">Seeded replay · {data.scenario.today}</span>
            <span className="badge neutral">{data.meta.job_spec}</span>
            <span className="badge ok">{data.meta.resumes_scored} real resumes scored</span>
          </div>
        </div>
      </header>

      <nav className="tabs">
        {tabs.map((t) => (
          <button key={t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>
            {t.label}
            {t.count !== undefined && <span className="count">{t.count}</span>}
          </button>
        ))}
      </nav>

      {tab === "shortlist" && <Shortlist candidates={data.shortlist} meta={data.meta} />}
      {tab === "scheduler" && <SchedulerView schedule={data.schedule} shortlist={data.shortlist} />}
      {tab === "feedback" && <FeedbackView feedback={data.feedback} />}
      {tab === "slippage" && <SlippageView risks={data.slippage} />}
      {tab === "paste" && <PasteResume />}

      <div className="card">
        <h2>How this desk works — and what is seeded</h2>
        <div className="hint" style={{ marginBottom: 0 }}>
          {data.scenario.note} The resume scores are 100% real: 962 resumes from the public-domain
          Kaggle Resume dataset lineage, scored by a deterministic engine (skill coverage 35, TF-IDF cosine 25,
          experience 20, education 20 — weights disclosed in every payload). Panel availability, touch timestamps,
          and interview/feedback history are the fixed seeded replay above. No AI generates any fact on this page.
        </div>
      </div>

      <footer className="footer">
        Loopboard · deterministic recruiting operations ·{" "}
        <a href="https://github.com/tidaaartorhem/ai-recruiting-coordinator">github.com/tidaaartorhem/ai-recruiting-coordinator</a>
      </footer>
    </div>
  );
}

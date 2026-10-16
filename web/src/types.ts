export interface ScoreBreakdown {
  required_skill_coverage: number;
  required_skills_matched: string[];
  required_skills_total: number;
  tfidf_cosine: number;
  tfidf_points: number;
  years_experience: number;
  experience_points: number;
  education_tier: string;
  education_points: number;
}

export interface ShortlistCandidate {
  id: string;
  rank: number;
  category: string;
  score: number;
  breakdown: ScoreBreakdown;
  nice_to_have_matched: string[];
  excerpt: string;
}

export interface PlanRound {
  round: string;
  panelist: string;
  date?: string;
  start?: string;
  end?: string;
  status: "scheduled" | "completed" | "unschedulable";
}

export interface CandidatePlan {
  candidate_id: string;
  rank: number;
  rounds: PlanRound[];
  time_to_loop_days: number;
  double_booking_flags: Array<{ date: string; rounds: string[]; reason: string }>;
}

export interface SchedulePayload {
  candidates: CandidatePlan[];
  bottleneck: {
    structural: string;
    structural_weekly_hours: number;
    load_leader: string;
    load_leader_scheduled: number;
    weekly_hours: Record<string, number>;
    scheduled_per_panelist: Record<string, number>;
  };
  rules: string[];
}

export interface FeedbackItem {
  candidate_id: string;
  candidate_rank: number;
  round: string;
  panelist: string;
  start: string;
  end: string;
  feedback_submitted_at: string | null;
  sla_deadline: string;
  status: "submitted_on_time" | "submitted_late" | "overdue" | "due_soon" | "pending";
  hours_overdue: number;
  hours_remaining?: number;
}

export interface NudgeItem {
  candidate_id: string;
  candidate_rank: number;
  round: string;
  panelist: string;
  status: string;
  hours_overdue: number;
  hours_remaining?: number;
  sla_deadline: string;
  recommended_action: string;
  human_gate: boolean;
  gate_note: string;
}

export interface DebriefEntry {
  candidate_id: string;
  candidate_rank: number;
  suggested_debrief?: string;
  human_gate?: boolean;
  gate_note?: string;
  blocked?: boolean;
  blockers?: string[];
}

export interface FeedbackPayload {
  items: FeedbackItem[];
  nudge_queue: NudgeItem[];
  debrief: DebriefEntry[];
  summary: {
    total_interviews: number;
    by_status: Record<string, number>;
    overdue_count: number;
    worst_overdue: {
      candidate_id: string;
      round: string;
      panelist: string;
      hours_overdue: number;
    } | null;
  };
  review_time: string;
}

export interface SlippageRisk {
  candidate_id: string;
  rank: number;
  score: number;
  category: string;
  days_since_touch: number;
  last_touch: string;
  time_to_loop_days: number;
  overdue_feedback: number;
  risk: number;
  bucket: "low" | "watch" | "high" | "critical";
  drivers: string[];
  components: Record<string, number>;
}

export interface ScenarioPayload {
  today: string;
  job_spec: string;
  feedback_sla_hours: number;
  stale_days: number;
  note: string;
}

export interface MetaPayload {
  resumes_scored: number;
  shortlist_size: number;
  job_spec: string;
  weights: Record<string, number>;
  generated: string;
}

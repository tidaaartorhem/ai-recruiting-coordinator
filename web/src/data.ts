import { useEffect, useState } from "react";
import type {
  FeedbackPayload,
  MetaPayload,
  ScenarioPayload,
  SchedulePayload,
  ShortlistCandidate,
  SlippageRisk,
} from "./types";

export interface DeskData {
  scenario: ScenarioPayload;
  shortlist: ShortlistCandidate[];
  schedule: SchedulePayload;
  feedback: FeedbackPayload;
  slippage: SlippageRisk[];
  meta: MetaPayload;
}

async function get<T>(name: string): Promise<T> {
  const res = await fetch(`data/${name}.json`);
  if (!res.ok) throw new Error(`failed to load data/${name}.json`);
  return res.json() as Promise<T>;
}

export function useDeskData() {
  const [data, setData] = useState<DeskData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [scenario, shortlist, schedule, feedback, slippage, meta] =
          await Promise.all([
            get<ScenarioPayload>("scenario"),
            get<ShortlistCandidate[]>("shortlist"),
            get<SchedulePayload>("schedule"),
            get<FeedbackPayload>("feedback"),
            get<SlippageRisk[]>("slippage"),
            get<MetaPayload>("meta"),
          ]);
        setData({ scenario, shortlist, schedule, feedback, slippage, meta });
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, []);

  return { data, error };
}

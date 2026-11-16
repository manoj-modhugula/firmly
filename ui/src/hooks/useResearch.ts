import { useCallback, useEffect, useRef, useState } from 'react';
import { observeResearch, type ResearchFailure } from '../lib/researchObserver';
export type { ResearchFailure } from '../lib/researchObserver';
import { addEvent } from '../lib/progress';
import type { Job, ResearchEvent } from '../lib/types';
export function useResearch(
  jobId: string | null,
  onComplete: (report: string, company?: string) => void,
  onFailed: (message: string, kind: ResearchFailure) => void,
  onSnapshot?: (job: Job) => void,
) {
  const [events, setEvents] = useState<ResearchEvent[]>([]);
  const [completed, setCompleted] = useState<string[]>([]);
  const [reconnecting, setReconnecting] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const callbacks = useRef({ onComplete, onFailed, onSnapshot });
  callbacks.current = { onComplete, onFailed, onSnapshot };
  const reconnect = useCallback(() => setAttempt((value) => value + 1), []);
  useEffect(() => {
    setEvents([]);
    setCompleted([]);
    setReconnecting(false);
    if (!jobId) return;
    return observeResearch(jobId, {
      onSnapshot: (job) => {
        callbacks.current.onSnapshot?.(job);
        if (job.completed_steps) setCompleted(job.completed_steps);
      },
      onEvent: (event) => {
        setEvents((previous) => addEvent(previous, event));
        if (event.type === 'progress' && event.step) {
          setCompleted((previous) =>
            Array.from(new Set([...previous, ...(event.completed_steps || []), event.step!])),
          );
        }
      },
      onComplete: (report, company) => callbacks.current.onComplete(report, company),
      onFailed: (message, kind) => callbacks.current.onFailed(message, kind),
      onReconnecting: setReconnecting,
    });
  }, [jobId, attempt]);
  return { events, completed, reconnecting, reconnect };
}

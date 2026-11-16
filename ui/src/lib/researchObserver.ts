import { ApiError, getJob } from './api';
import type { Job, ResearchEvent } from './types';

export type ResearchFailure = 'failed' | 'unavailable' | 'connection';
type Stream = Pick<EventSource, 'onopen' | 'onmessage' | 'onerror' | 'close'>;
type Listeners = {
  onSnapshot: (job: Job) => void;
  onEvent: (event: ResearchEvent) => void;
  onComplete: (report: string, company?: string) => void;
  onFailed: (message: string, kind: ResearchFailure) => void;
  onReconnecting: (reconnecting: boolean) => void;
};
const defaults = {
  open: (url: string): Stream => new EventSource(url),
  read: getJob,
  pollEvery: 5000,
};
function isResearchEvent(value: unknown): value is ResearchEvent {
  if (!value || typeof value !== 'object' || !('type' in value) || typeof value.type !== 'string')
    return false;
  const event = value as Record<string, unknown>;
  for (const field of ['step', 'category', 'report', 'company', 'error', 'message', 'query']) {
    if (event[field] !== undefined && typeof event[field] !== 'string') return false;
  }
  return (
    event.completed_steps === undefined ||
    (Array.isArray(event.completed_steps) &&
      event.completed_steps.every((step) => typeof step === 'string'))
  );
}
export function observeResearch(jobId: string, listeners: Listeners, dependencies = defaults) {
  let disposed = false;
  let finished = false;
  let checking = false;
  let failures = 0;
  const controller = new AbortController();
  const source = dependencies.open(`/api/research/${encodeURIComponent(jobId)}/stream`);
  const finish = (
    report?: string,
    error?: string,
    kind: ResearchFailure = 'failed',
    company?: string,
  ) => {
    if (finished || disposed) return;
    finished = true;
    source.close();
    controller.abort();
    if (timer) clearInterval(timer);
    if (report) listeners.onComplete(report, company);
    else listeners.onFailed(error || 'The report could not be completed.', kind);
  };
  const check = async () => {
    if (checking || disposed || finished) return;
    checking = true;
    try {
      const job = await dependencies.read(jobId, controller.signal);
      if (disposed || finished) return;
      failures = 0;
      listeners.onReconnecting(false);
      listeners.onSnapshot(job);
      if (job.status === 'completed') finish(job.report, undefined, 'failed', job.company);
      else if (job.status === 'failed') finish(undefined, job.error);
    } catch (error) {
      if (disposed || finished) return;
      listeners.onReconnecting(true);
      failures++;
      if (error instanceof ApiError && error.status === 404)
        finish(
          undefined,
          'This report is unavailable or expired. You can start new research.',
          'unavailable',
        );
      else if (failures >= 3)
        finish(
          undefined,
          'We could not confirm the research status. Reconnect to check the existing run.',
          'connection',
        );
    } finally {
      checking = false;
    }
  };
  source.onopen = () => {
    if (!disposed && !finished) listeners.onReconnecting(false);
  };
  source.onmessage = (message) => {
    if (disposed || finished) return;
    let value: unknown;
    try {
      value = JSON.parse(message.data);
    } catch {
      return;
    }
    if (!isResearchEvent(value)) return;
    const event = value;
    if (event.type === 'complete') {
      finish(event.report, undefined, 'failed', event.company);
      return;
    }
    if (event.type === 'error') {
      finish(undefined, event.error);
      return;
    }
    listeners.onEvent(event);
  };
  source.onerror = () => {
    if (!finished && !disposed) {
      listeners.onReconnecting(true);
      void check();
    }
  };
  const timer = setInterval(check, dependencies.pollEvery);
  void check();
  return () => {
    disposed = true;
    controller.abort();
    source.close();
    controller.abort();
    if (timer) clearInterval(timer);
  };
}

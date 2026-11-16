import { Check, LoaderCircle, Minus } from 'lucide-react';
import { CATEGORIES, STAGES, researchStage } from '../lib/progress';
import type { ResearchEvent } from '../lib/types';
export function Progress({
  company,
  events,
  completed,
  reconnecting,
}: {
  company: string;
  events: ResearchEvent[];
  completed: string[];
  reconnecting: boolean;
}) {
  const current = researchStage(completed);
  return (
    <main className="a-center progress-page" id="main-content">
      <div className="f-kicker">Researching {company}</div>
      <h1>Preparing your briefing</h1>
      <p className="a-sub">
        Gathering the business context, developments, and sources for your next conversation.
      </p>
      <div className="progress-current" role="status" aria-live="polite">
        <LoaderCircle size={17} className="spin" />
        {reconnecting
          ? 'Reconnecting to your research…'
          : current?.[1] || 'Researching four perspectives'}
      </div>
      {reconnecting && (
        <div className="connection-notice" role="status">
          The connection was interrupted. We are checking the existing run; no new research has been
          started.
        </div>
      )}
      <div className="research-tracks">
        {CATEGORIES.map((category) => {
          const done = completed.includes(category.node);
          const activity = events.some((event) => event.category === category.id);
          const started = activity || completed.includes('company_context');
          const Icon = done ? Check : started ? LoaderCircle : Minus;
          return (
            <div className="research-track" key={category.id}>
              <div className="track-heading">
                <h2>{category.title}</h2>
                <span className="a-status">
                  <Icon size={15} className={!done && started ? 'spin' : ''} />
                  {done ? 'Done' : started ? 'Researching' : 'Waiting'}
                </span>
              </div>
              <p>{category.description}</p>
            </div>
          );
        })}
      </div>
      <details className="progress-stages">
        <summary>View research stages</summary>
        <ol className="pipeline-list" aria-label="Research stages">
          {STAGES.filter(([id]) => id !== 'company_context').map(([id, title]) => (
            <li
              key={id}
              className={completed.includes(id) ? 'done' : current?.[0] === id ? 'active' : ''}
            >
              {completed.includes(id) ? <Check size={14} /> : <span className="stage-dot" />}
              {title}
            </li>
          ))}
        </ol>
      </details>
      <p className="progress-footnote">
        Keep this page open. Completion time depends on the connected services.
      </p>
    </main>
  );
}

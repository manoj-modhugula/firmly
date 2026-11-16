import { CloudOff, FileSearch, Settings2 } from 'lucide-react';
type Props = {
  kind: 'configuration' | 'failed' | 'unavailable' | 'connection';
  message: string;
  company: string;
  onPrimary: () => void;
  onBack: () => void;
  onSample: () => void;
  onRetrySubmission: () => void;
  busy: boolean;
  pendingSubmission: boolean;
};
export function Notice({
  kind,
  message,
  company,
  onPrimary,
  onBack,
  onSample,
  onRetrySubmission,
  busy,
  pendingSubmission,
}: Props) {
  const Icon =
    kind === 'configuration' ? Settings2 : kind === 'unavailable' ? FileSearch : CloudOff;
  const title =
    kind === 'configuration'
      ? 'Connect research services'
      : kind === 'failed'
        ? 'Research interrupted'
        : kind === 'connection'
          ? 'Check your research connection'
          : 'Report unavailable';
  return (
    <main className="a-center notice-page" id="main-content">
      <div className="a-icon">
        <Icon size={24} />
      </div>
      <h1>{title}</h1>
      <p className="a-sub" role="status">
        {message}
      </p>
      {company && (
        <p className="notice-context">
          Company <strong>{company}</strong>
        </p>
      )}
      <div className="a-actions">
        <button className="f-black" disabled={busy} onClick={onPrimary}>
          {busy
            ? 'Checking…'
            : kind === 'configuration'
              ? 'Open research settings'
              : kind === 'unavailable'
                ? 'Start new research'
                : kind === 'connection'
                  ? 'Reconnect to existing research'
                  : 'Try again'}
        </button>
        {kind === 'connection' && pendingSubmission ? (
          <button className="f-plain" disabled={busy} onClick={onRetrySubmission}>
            Retry the same request
          </button>
        ) : (
          <button className="f-plain" onClick={onSample}>
            Explore sample report
          </button>
        )}
      </div>
      {kind === 'connection' && pendingSubmission && (
        <p className="recovery-hint">
          Retrying uses the same request ID to prevent duplicate research.
        </p>
      )}
      <button className="f-demo-link notice-back" onClick={onBack}>
        {company ? 'Edit company details' : 'Back to home'}
      </button>
    </main>
  );
}

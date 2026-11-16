import { useEffect, useState } from 'react';
import { Check, ExternalLink } from 'lucide-react';
import { getModels } from '../lib/api';
import { connectionErrors } from '../lib/navigation';
import { AUTOMATIC_MODEL_ID, MODEL_KEY_URL, SEARCH_KEY_URL } from '../lib/connections';
import type { Config, Settings as ResearchSettings } from '../lib/types';

type Props = {
  value: ResearchSettings;
  config: Config | null;
  onSave: (settings: ResearchSettings) => void;
  onBack: () => void;
  continueCompany?: string;
  saving: boolean;
};
export function Settings({ value, config, onSave, onBack, continueCompany, saving }: Props) {
  const [draft, setDraft] = useState(value);
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [modelError, setModelError] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const errors = connectionErrors(draft, config);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    getModels(controller.signal)
      .then((data) => {
        if (active) setModels(data.models);
      })
      .catch(() => {
        if (active)
          setModelError('The model list is unavailable. Automatic selection is still available.');
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);
  const update = (field: keyof ResearchSettings, value: string) =>
    setDraft((settings) => ({ ...settings, [field]: value }));
  const available = models.filter(
    (model) => model.id.endsWith(':free') && model.id !== AUTOMATIC_MODEL_ID,
  );
  const personal = draft.connection === 'personal';
  const managedReady = !!(config?.direct_model_ready || config?.model_gateway_ready);
  const showConnection = managedReady || !personal;
  return (
    <main id="main-content" className="a-center a-settings">
      <h1>Research settings</h1>
      <p className="a-sub">
        Connect your services for live research. The sample works without keys.
      </p>
      <form
        className="a-panel settings-panel"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          setSubmitted(true);
          if (errors.accessKey || errors.searchKey) {
            requestAnimationFrame(() =>
              document.querySelector<HTMLInputElement>('[aria-invalid="true"]')?.focus(),
            );
            return;
          }
          onSave({
            ...draft,
            accessKey: draft.accessKey.trim(),
            searchKey: draft.searchKey.trim(),
          });
        }}
      >
        <div className="a-setting">
          <div className={showConnection ? 'a-two' : 'model-choice'}>
            {showConnection && (
              <label>
                Connection
                <select
                  value={draft.connection}
                  onChange={(event) => update('connection', event.target.value)}
                >
                  <option value="personal">Keys for this tab</option>
                  <option value="managed">Installation defaults</option>
                </select>
              </label>
            )}
            {personal ? (
              <label>
                Model
                <select
                  value={draft.model}
                  onChange={(event) => update('model', event.target.value)}
                >
                  <option value={AUTOMATIC_MODEL_ID}>Automatic · Free</option>
                  {!available.some((model) => model.id === draft.model) &&
                    draft.model !== AUTOMATIC_MODEL_ID && (
                      <option value={draft.model}>Custom model</option>
                    )}
                  {available.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <div className="server-config">
                {managedReady && <Check size={16} />}{' '}
                {managedReady ? 'Configured on this installation' : 'Model connection needed'}
              </div>
            )}
          </div>
          {personal && (
            <p className="field-hint">Free access is subject to availability and usage limits.</p>
          )}
          {!personal && submitted && errors.accessKey && (
            <p className="field-error" role="alert">
              {errors.accessKey}
            </p>
          )}
          {modelError && <p role="status">{modelError}</p>}
        </div>
        {personal && (
          <div className="a-setting">
            <label>
              <span className="key-label">
                Model access key
                <a className="service-link" href={MODEL_KEY_URL} target="_blank" rel="noreferrer">
                  Get a key
                  <ExternalLink size={13} />
                </a>
              </span>
              <input
                aria-label="Model access key"
                aria-invalid={submitted && !!errors.accessKey}
                aria-describedby="model-key-feedback"
                type="password"
                autoComplete="off"
                value={draft.accessKey}
                maxLength={500}
                onChange={(event) => update('accessKey', event.target.value)}
                placeholder={
                  config?.model_gateway_ready
                    ? 'Ready on this installation · optional override'
                    : 'Enter your model access key'
                }
              />
            </label>
            {submitted && errors.accessKey && (
              <p id="model-key-feedback" className="field-error" role="alert">
                {errors.accessKey}
              </p>
            )}
          </div>
        )}
        <div className="a-setting">
          <label>
            <span className="key-label">
              Web research key
              <a className="service-link" href={SEARCH_KEY_URL} target="_blank" rel="noreferrer">
                Get a key
                <ExternalLink size={13} />
              </a>
            </span>
            <input
              aria-label="Web research key"
              aria-invalid={submitted && !!errors.searchKey}
              aria-describedby="search-key-feedback"
              type="password"
              autoComplete="off"
              value={draft.searchKey}
              maxLength={500}
              onChange={(event) => update('searchKey', event.target.value)}
              placeholder={
                config?.search_ready
                  ? 'Ready on this installation · optional override'
                  : 'Enter your web research key'
              }
            />
          </label>
          {submitted && errors.searchKey && (
            <p id="search-key-feedback" className="field-error" role="alert">
              {errors.searchKey}
            </p>
          )}
          <p>
            Keys clear on reload. When research starts, they are sent to Firmly’s server and the
            connected services.
          </p>
        </div>
        <p className="connection-verification">
          Not verified. Credentials are checked when research starts.
        </p>
        <div className="a-actions">
          <button className="f-black" disabled={saving}>
            {saving
              ? 'Starting…'
              : continueCompany
                ? `Continue researching ${continueCompany}`
                : 'Apply settings'}
          </button>
          <button type="button" className="f-plain" disabled={saving} onClick={onBack}>
            Cancel
          </button>
        </div>
      </form>
    </main>
  );
}

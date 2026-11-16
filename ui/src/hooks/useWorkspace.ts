import { AUTOMATIC_MODEL_ID } from '../lib/connections';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useResearch, type ResearchFailure } from './useResearch';
import { useSettingsNavigation } from './useSettingsNavigation';
import { useNavigation } from './useNavigation';
import { ApiError, createResearch, getConfig, getJob } from '../lib/api';
import {
  readPendingSubmission,
  rememberSubmission,
  type PendingSubmission,
} from '../lib/submission';
import { HOME, connectionErrors } from '../lib/navigation';
import { SAMPLE_COMPANY, SAMPLE_REPORT } from '../lib/sample';
import {
  EMPTY_COMPANY,
  type Company,
  type Config,
  type Job,
  type Page,
  type Section,
  type Settings as SettingsType,
} from '../lib/types';
type SavedReport = { content: string; company: string };
export function useWorkspace() {
  const { route, navigate: go } = useNavigation();
  const routeRef = useRef(route);
  routeRef.current = route;
  const pendingCompany = useRef(false);
  const pendingSubmission = useRef<PendingSubmission | null>(readPendingSubmission());
  const [company, setCompany] = useState<Company>(
    pendingSubmission.current?.company || EMPTY_COMPANY,
  );
  const [settings, setSettings] = useState<SettingsType>({
    searchKey: '',
    accessKey: '',
    model: AUTOMATIC_MODEL_ID,
    connection: 'personal',
  });
  const [config, setConfig] = useState<Config | null>(null);
  const [jobId, setJobId] = useState<string | null>(route.job);
  const jobRef = useRef(jobId);
  jobRef.current = jobId;
  const [jobStatus, setJobStatus] = useState<
    'idle' | 'running' | 'completed' | 'failed' | 'unknown'
  >(route.job ? 'running' : 'idle');
  const [reports, setReports] = useState<Record<string, SavedReport>>({});
  const [starting, setStarting] = useState(false);
  const startLock = useRef(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [focusRequest, setFocusRequest] = useState(0);
  const busy = !!jobId && (jobStatus === 'running' || jobStatus === 'unknown');
  const { rememberReturn, closeSettings } = useSettingsNavigation(
    route,
    go,
    jobStatus === 'completed',
  );
  const navigate = useCallback(
    (page: Page, replace = false) => {
      const current = routeRef.current;
      if (page === 'settings' && current.page !== 'settings') rememberReturn(current);
      const next =
        page === 'home'
          ? HOME
          : page === 'progress'
            ? { ...HOME, page, job: jobRef.current }
            : { ...current, page, scroll: 0 };
      go(next, replace);
    },
    [go, rememberReturn],
  );
  const onComplete = useCallback(
    (content: string, name?: string) => {
      const id = jobRef.current;
      if (!id) return;
      pendingSubmission.current = null;
      rememberSubmission(null);
      setJobStatus('completed');
      setError('');
      setReports((previous) => ({
        ...previous,
        [id]: { content, company: name || previous[id]?.company || company.company },
      }));
      const current = routeRef.current;
      if ((current.page === 'progress' || current.page === 'connection') && current.job === id)
        go({ ...current, page: 'report', scroll: 0 }, true);
    },
    [go, company.company],
  );
  const onFailed = useCallback(
    (message: string, kind: ResearchFailure) => {
      setJobStatus(kind === 'connection' ? 'unknown' : 'failed');
      setError(
        pendingSubmission.current
          ? 'We could not confirm an accepted request. Reconnect or retry the same request safely.'
          : message,
      );
      const current = routeRef.current;
      const page = pendingSubmission.current ? 'connection' : kind;
      if (
        !current.sample &&
        current.job === jobRef.current &&
        (current.page === 'progress' || current.page === 'connection' || current.page === 'report')
      )
        go({ ...current, page, scroll: 0 }, true);
    },
    [go],
  );
  const onSnapshot = useCallback((job: Job) => {
    const id = jobRef.current;
    if (!id) return;
    setCompany((previous) =>
      previous.company === job.company ? previous : { ...previous, company: job.company },
    );
    setReports((previous) => {
      const content = job.report || previous[id]?.content || '';
      if (previous[id]?.content === content && previous[id]?.company === job.company)
        return previous;
      return { ...previous, [id]: { content, company: job.company } };
    });
  }, []);
  const research = useResearch(jobId, onComplete, onFailed, onSnapshot);
  useEffect(() => {
    if (route.page !== 'progress' || route.job !== jobId) return;
    if (jobStatus === 'completed') go({ ...route, page: 'report' }, true);
    else if (jobStatus === 'failed')
      go({ ...route, page: pendingSubmission.current ? 'connection' : 'failed' }, true);
  }, [route, jobId, jobStatus, go]);
  useEffect(() => {
    const controller = new AbortController();
    getConfig(controller.signal)
      .then(setConfig)
      .catch(() => {
        // Unknown installation defaults are rechecked before every submission.
        if (!controller.signal.aborted) setConfig(null);
      });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (route.job && route.job !== jobRef.current) {
      setJobId(route.job);
      setJobStatus('running');
    }
  }, [route.job]);
  useEffect(() => {
    const caption =
      route.page === 'home'
        ? 'Know more. Be sure.'
        : route.page === 'report'
          ? `${route.sample ? SAMPLE_COMPANY.company : reports[route.job || '']?.company || company.company}: Report`
          : route.page === 'settings'
            ? 'Research settings'
            : route.page === 'progress'
              ? 'Research in progress'
              : 'Research';
    document.title = `Firmly: ${caption}`;
  }, [route, company.company, reports]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(''), 5000);
    return () => clearTimeout(timer);
  }, [toast]);
  const focusCompany = () => {
    setError('');
    navigate('home');
    setFocusRequest((value) => value + 1);
  };
  const newResearch = () => {
    if (busy) {
      navigate('progress');
      return;
    }
    pendingCompany.current = false;
    setCompany(EMPTY_COMPANY);
    focusCompany();
  };
  const openSample = (section: Section = 'briefing') => {
    pendingCompany.current = false;
    go({ ...HOME, page: 'report', sample: true, section });
  };
  const start = async (value = settings) => {
    if (startLock.current) return;
    if (busy && !pendingSubmission.current) {
      research.reconnect();
      navigate('progress');
      return;
    }
    if (
      pendingSubmission.current &&
      JSON.stringify(company) !== JSON.stringify(pendingSubmission.current.company)
    ) {
      setError(
        `Resolve the existing request for ${pendingSubmission.current.company.company} before starting a different research run.`,
      );
      navigate('connection');
      return;
    }
    const details = pendingSubmission.current?.company || company;
    if (!details.company.trim()) {
      setError('Enter a company name, then select Research.');
      focusCompany();
      return;
    }
    startLock.current = true;
    setStarting(true);
    setError('');
    let sent = false;
    try {
      const fresh = await getConfig();
      setConfig(fresh);
      const missing = connectionErrors(value, fresh);
      if (missing.accessKey || missing.searchKey) {
        pendingCompany.current = true;
        setError(
          'Connect your model and web research services to continue. Your company details are preserved.',
        );
        navigate('configuration');
        return;
      }
      const submission = pendingSubmission.current || {
        id: crypto.randomUUID(),
        company: { ...details },
      };
      pendingSubmission.current = submission;
      rememberSubmission(submission);
      sent = true;
      const result = await createResearch(submission.company, value, submission.id);
      pendingSubmission.current = null;
      rememberSubmission(null);
      pendingCompany.current = false;
      setReports((previous) => ({
        ...previous,
        [result.job_id]: { content: '', company: details.company },
      }));
      setJobId(result.job_id);
      setJobStatus('running');
      research.reconnect();
      go({ ...HOME, page: 'progress', job: result.job_id });
    } catch (err) {
      const uncertain =
        sent && (!(err instanceof ApiError) || err.status === 408 || err.status === 409);
      if (uncertain) {
        setError(
          'We could not confirm whether the request was accepted. Check the existing request or retry it safely.',
        );
        go({ ...HOME, page: 'connection', job: pendingSubmission.current?.id || null });
      } else {
        if (sent) {
          pendingSubmission.current = null;
          rememberSubmission(null);
        }
        setError(err instanceof Error ? err.message : 'Could not connect. Please try again.');
        navigate(err instanceof ApiError && err.status === 409 ? 'configuration' : 'failed');
      }
    } finally {
      startLock.current = false;
      setStarting(false);
    }
  };
  const reconnect = async () => {
    const pending = pendingSubmission.current;
    if (pending) {
      if (startLock.current) return;
      startLock.current = true;
      setStarting(true);
      try {
        const job = await getJob(pending.id);
        setReports((previous) => ({
          ...previous,
          [pending.id]: { content: job.report || '', company: job.company },
        }));
        setJobId(pending.id);
        setJobStatus(
          job.status === 'completed' ? 'completed' : job.status === 'failed' ? 'failed' : 'running',
        );
        pendingSubmission.current = null;
        rememberSubmission(null);
        research.reconnect();
        go({ ...HOME, job: pending.id, page: job.status === 'completed' ? 'report' : 'progress' });
      } catch (err) {
        setError(
          err instanceof ApiError && err.status === 404
            ? 'No accepted request was found yet. Retry this request to check again without creating a duplicate.'
            : 'The connection is still unavailable. Your request has not been restarted.',
        );
      } finally {
        startLock.current = false;
        setStarting(false);
      }
    } else if (jobId) {
      setJobStatus('running');
      research.reconnect();
      navigate('progress');
    } else {
      focusCompany();
    }
  };
  const saveSettings = (value: SettingsType) => {
    setSettings(value);
    if (pendingCompany.current) {
      void start(value);
      return;
    }
    setToast('Settings configured. Credentials will be verified when research starts.');
    closeSettings();
  };
  const page = route.page;
  const saved = route.sample
    ? { content: SAMPLE_REPORT, company: SAMPLE_COMPANY.company }
    : reports[route.job || ''];
  const showReady =
    jobStatus === 'completed' &&
    jobId &&
    reports[jobId]?.content &&
    !(page === 'report' && route.job === jobId);
  const openSettings = () => {
    navigate('settings');
    history.replaceState({ ...history.state, settingsFromApp: true }, '', location.href);
  };
  return {
    page,
    route,
    go,
    company,
    setCompany,
    settings,
    config,
    jobId,
    reports,
    jobStatus,
    busy,
    starting,
    error,
    toast,
    focusRequest,
    continueCompany: pendingCompany.current ? company.company : undefined,
    hasPendingSubmission: !!pendingSubmission.current,
    research,
    navigate,
    focusCompany,
    newResearch,
    openSample,
    closeSettings,
    start,
    reconnect,
    saveSettings,
    showReady,
    openSettings,
    saved,
  };
}

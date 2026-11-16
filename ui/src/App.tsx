import { lazy, Suspense } from 'react';
import { Header, Footer } from './components/Shell';
import { Home } from './components/Home';
import { Settings } from './components/Settings';
import { Progress } from './components/Progress';
import { Notice } from './components/Notice';
import { useWorkspace } from './hooks/useWorkspace';
import type { Page } from './lib/types';
import { HOME } from './lib/navigation';
const Report = lazy(() =>
  import('./components/Report').then((module) => ({ default: module.Report })),
);
export default function App() {
  const {
    page,
    route,
    go,
    company,
    setCompany,
    settings,
    config,
    jobId,
    reports,
    busy,
    starting,
    error,
    toast,
    focusRequest,
    continueCompany,
    hasPendingSubmission,
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
  } = useWorkspace();
  return (
    <div id="firmly-direction" className={page === 'home' ? 'f-homepage' : ''}>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className="f-site">
        <Header
          page={page}
          onNavigate={(next) => (next === 'settings' ? openSettings() : navigate(next))}
          busy={busy}
          onStart={focusCompany}
          onNew={newResearch}
        />
        {showReady && (
          <div className="report-ready" role="status">
            <span>{reports[jobId!].company || 'Your company'} report is ready.</span>
            <button
              className="f-demo-link"
              onClick={() => go({ ...HOME, page: 'report', job: jobId })}
            >
              Open report →
            </button>
          </div>
        )}
        {page === 'home' && (
          <Home
            company={company}
            setCompany={setCompany}
            onSubmit={() => void start()}
            onSample={openSample}
            starting={starting}
            error={error}
            focusRequest={focusRequest}
            onStart={focusCompany}
          />
        )}
        {page === 'settings' && (
          <Settings
            value={settings}
            config={config}
            onBack={closeSettings}
            onSave={saveSettings}
            continueCompany={continueCompany}
            saving={starting}
          />
        )}
        {page === 'progress' && (
          <Progress
            company={reports[jobId || '']?.company || company.company || 'your company'}
            events={research.events}
            completed={research.completed}
            reconnecting={research.reconnecting}
          />
        )}
        {page === 'report' &&
          (saved?.content ? (
            <Suspense
              fallback={
                <main className="a-center" id="main-content" role="status">
                  Opening your report…
                </main>
              }
            >
              <Report
                key={route.sample ? 'sample' : route.job}
                report={saved.content}
                company={saved.company || company.company || 'Company'}
                sample={route.sample}
                section={route.section}
                onSectionChange={(section) => go({ ...route, section, scroll: 0 }, true)}
                restoreScroll={route.scroll}
              />
            </Suspense>
          ) : (
            <main className="a-center" id="main-content" role="status">
              Retrieving your report…
            </main>
          ))}
        {(['configuration', 'failed', 'unavailable', 'connection'] as Page[]).includes(page) && (
          <Notice
            kind={page as 'configuration' | 'failed' | 'unavailable' | 'connection'}
            message={
              error || 'This report is no longer available. You can begin another research run.'
            }
            company={company.company}
            busy={starting}
            pendingSubmission={hasPendingSubmission}
            onPrimary={
              page === 'configuration'
                ? openSettings
                : page === 'connection'
                  ? () => void reconnect()
                  : page === 'unavailable'
                    ? newResearch
                    : () => void start()
            }
            onRetrySubmission={() => void start()}
            onBack={focusCompany}
            onSample={() => openSample()}
          />
        )}
        <Footer />
      </div>
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </div>
  );
}

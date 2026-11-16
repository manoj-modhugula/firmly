import React from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource/geist/latin-400.css';
import '@fontsource/geist/latin-500.css';
import App from './App';
import './styles.css';
class ErrorBoundary extends React.Component<React.PropsWithChildren, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <main className="fatal-fallback">
          <h1>Let’s try that again.</h1>
          <p>The page couldn’t be displayed. Reload to return to Firmly.</p>
          <button onClick={() => location.reload()}>Reload page</button>
        </main>
      );
    return this.props.children;
  }
}
// An open tab can retain a previous deployment's lazy report URL. Refresh once,
// preserving the job/sample URL; the normal fallback handles persistent failures.
window.addEventListener('vite:preloadError', (event) => {
  try {
    const now = Date.now();
    const last = Number(sessionStorage.getItem('firmly:asset-reload') || 0);
    if (now - last < 60_000) return;
    sessionStorage.setItem('firmly:asset-reload', String(now));
    event.preventDefault();
    location.reload();
  } catch {
    /* Restricted storage: keep the manual reload fallback. */
  }
});
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);

import { ArrowUpRight, Menu } from 'lucide-react';
import type { Page } from '../lib/types';
export function Header({
  page,
  onNavigate,
  busy,
  onStart,
  onNew,
}: {
  page: Page;
  onNavigate: (page: Page) => void;
  busy: boolean;
  onStart: () => void;
  onNew: () => void;
}) {
  return (
    <header className="f-header">
      <a
        className="f-logo"
        href="#"
        onClick={(e) => {
          e.preventDefault();
          onNavigate('home');
        }}
        aria-label="Firmly home"
      >
        <span className="brand-mark" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        Firmly
      </a>
      <nav className="f-nav" aria-label="Main navigation">
        {page === 'home' ? (
          <>
            <a className="hp-navlink" href="#overview">
              Overview
            </a>
            <a className="hp-navlink" href="#how-it-works">
              How it works
            </a>
          </>
        ) : null}
        {page !== 'settings' && (
          <button className="f-plain" onClick={() => onNavigate('settings')}>
            Research settings
          </button>
        )}
        {page === 'home' ? (
          <button onClick={onStart} className="hp-start">
            Start research <ArrowUpRight size={16} />
          </button>
        ) : (
          page !== 'progress' && (
            <button className="f-black" onClick={onNew}>
              {busy ? 'View progress' : 'New research'}
              <ArrowUpRight size={16} />
            </button>
          )
        )}
        <details className="mobile-menu">
          <summary aria-label="Open navigation">
            <Menu size={20} />
          </summary>
          <div>
            <button
              onClick={(event) => {
                event.currentTarget.closest('details')?.removeAttribute('open');
                onNavigate('settings');
              }}
            >
              Research settings
            </button>
            <button
              onClick={(event) => {
                event.currentTarget.closest('details')?.removeAttribute('open');
                onNavigate(busy ? 'progress' : 'home');
              }}
            >
              {busy ? 'View progress' : 'Research home'}
            </button>
          </div>
        </details>
      </nav>
    </header>
  );
}
export function Footer() {
  return (
    <footer className="f-foot">
      <span>Firmly</span>
      <span>A clearer view of the companies that matter.</span>
    </footer>
  );
}

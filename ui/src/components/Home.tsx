import { HomePreview } from './home/HomePreview';
import { HomeSections } from './home/HomeSections';
import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Sparkles, X } from 'lucide-react';
import type { Company, Section } from '../lib/types';
export function Home({
  company,
  setCompany,
  onSubmit,
  onSample,
  starting,
  error,
  focusRequest,
  onStart,
}: {
  company: Company;
  setCompany: (company: Company) => void;
  onSubmit: () => void;
  onSample: (section?: Section) => void;
  starting: boolean;
  error: string;
  focusRequest: number;
  onStart: () => void;
}) {
  const root = useRef<HTMLElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const entry = useRef<HTMLFormElement>(null);
  const [showHint, setShowHint] = useState(false);
  useEffect(() => {
    if (!focusRequest) return;
    setShowHint(true);
    const frame = requestAnimationFrame(() => {
      input.current?.focus({ preventScroll: true });
      input.current?.scrollIntoView({
        block: 'center',
        behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [focusRequest]);
  useEffect(() => {
    if (!showHint) return;
    const dismissOutside = (event: PointerEvent) => {
      if (!entry.current?.contains(event.target as Node)) setShowHint(false);
    };
    const dismissEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setShowHint(false);
    };
    document.addEventListener('pointerdown', dismissOutside);
    document.addEventListener('keydown', dismissEscape);
    return () => {
      document.removeEventListener('pointerdown', dismissOutside);
      document.removeEventListener('keydown', dismissEscape);
    };
  }, [showHint]);
  useEffect(() => {
    if (
      matchMedia('(prefers-reduced-motion: reduce)').matches ||
      !('IntersectionObserver' in window)
    )
      return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries)
          if (e.isIntersecting) {
            e.target.classList.remove('hp-pending');
            observer.unobserve(e.target);
          }
      },
      { threshold: 0.12, rootMargin: '0px 0px -24px 0px' },
    );
    root.current
      ?.querySelectorAll('.hp-perspectives > div,.hp-process > h2,.hp-step,.hp-close > *')
      .forEach((el) => {
        if (el.getBoundingClientRect().top < innerHeight) return;
        el.classList.add('hp-reveal', 'hp-pending');
        observer.observe(el);
      });
    return () => observer.disconnect();
  }, []);
  return (
    <main ref={root} id="main-content">
      <div className="f-hero" id="research">
        <div>
          <div className="f-kicker">Company research, in perspective.</div>
          <h1>
            Know the company.
            <br />
            <span className="f-gradient">See the full picture.</span>
          </h1>
          <p className="f-description">
            Understand the business, the latest moves, and what to ask before your next
            conversation.
          </p>
          <form
            ref={entry}
            className="f-search"
            onSubmit={(e) => {
              e.preventDefault();
              setShowHint(false);
              onSubmit();
            }}
          >
            {showHint && (
              <div className="research-start-hint" id="research-start-hint" role="status">
                <span className="research-hint-icon" aria-hidden="true">
                  <Sparkles size={16} />
                </span>
                <span>Start with a company name.</span>
                <button
                  type="button"
                  className="research-hint-close"
                  aria-label="Dismiss research tip"
                  onClick={() => setShowHint(false)}
                >
                  <X size={15} />
                </button>
              </div>
            )}
            <input
              ref={input}
              aria-describedby={showHint ? 'research-start-hint' : undefined}
              aria-label="Company name"
              placeholder="Company name or website"
              value={company.company}
              maxLength={180}
              required
              onChange={(e) => {
                setShowHint(false);
                setCompany({ ...company, company: e.target.value });
              }}
            />
            <button className="f-black" disabled={starting}>
              {starting ? 'Starting…' : 'Research'}
              <ArrowUpRight size={17} />
            </button>
          </form>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <details className="a-details">
            <summary>Add company details</summary>
            <div className="a-fields">
              <label>
                Website
                <input
                  autoComplete="url"
                  placeholder="company.com"
                  value={company.company_url}
                  maxLength={500}
                  onChange={(e) => setCompany({ ...company, company_url: e.target.value })}
                />
              </label>
              <label>
                Industry
                <input
                  placeholder="Optional"
                  maxLength={180}
                  value={company.industry}
                  onChange={(e) => setCompany({ ...company, industry: e.target.value })}
                />
              </label>
              <label>
                Headquarters
                <input
                  placeholder="City, country"
                  maxLength={180}
                  value={company.hq_location}
                  onChange={(e) => setCompany({ ...company, hq_location: e.target.value })}
                />
              </label>
            </div>
          </details>
        </div>
        <HomePreview onSample={onSample} />
      </div>
      <HomeSections onStart={onStart} />
    </main>
  );
}

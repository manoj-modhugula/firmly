import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArrowLeft, ArrowRight, ArrowUpRight, Download, LoaderCircle } from 'lucide-react';
import { parseReport, safeURL } from '../lib/report';
import { SAMPLE_PERIOD } from '../lib/sample';
import { exportPDF } from '../lib/api';
import type { Section } from '../lib/types';

export function Report({
  report,
  company,
  sample,
  section,
  onSectionChange,
  restoreScroll,
}: {
  report: string;
  company: string;
  sample: boolean;
  section: Section;
  onSectionChange: (section: Section) => void;
  restoreScroll: number;
}) {
  const parsed = useMemo(() => parseReport(report), [report]);
  const tab: Section = parsed.sections[section]
    ? section
    : parsed.sections.briefing
      ? 'briefing'
      : parsed.fallback && !sample
        ? 'full'
        : 'company';
  const setTab = onSectionChange;
  const nav = useRef<HTMLElement>(null);
  const [overflow, setOverflow] = useState({ left: false, right: false });
  const initialScroll = useRef(restoreScroll);
  useLayoutEffect(() => {
    const frame = requestAnimationFrame(() =>
      scrollTo({ top: initialScroll.current, behavior: 'instant' }),
    );
    return () => cancelAnimationFrame(frame);
  }, []);
  useEffect(() => {
    const element = nav.current;
    if (!element) return;
    const update = () =>
      setOverflow({
        left: element.scrollLeft > 2,
        right: element.scrollLeft + element.clientWidth < element.scrollWidth - 2,
      });
    const observer = new ResizeObserver(update);
    observer.observe(element);
    element.addEventListener('scroll', update, { passive: true });
    update();
    return () => {
      observer.disconnect();
      element.removeEventListener('scroll', update);
    };
  }, []);
  useEffect(() => {
    const element = nav.current;
    const active = element?.querySelector<HTMLElement>('[aria-pressed="true"]');
    if (element && active) {
      const start = active.offsetLeft - element.offsetLeft;
      if (start < element.scrollLeft) element.scrollLeft = start;
      else if (start + active.offsetWidth > element.scrollLeft + element.clientWidth)
        element.scrollLeft = start + active.offsetWidth - element.clientWidth;
    }
  }, [tab]);
  const [exporting, setExporting] = useState(false);
  const [pdfError, setPDFError] = useState('');
  const [downloaded, setDownloaded] = useState(false);
  const tabs: [Section, string][] = [
    ...(parsed.sections.briefing ? [['briefing', 'Briefing'] as [Section, string]] : []),
    ...(parsed.fallback ? [['full', 'Full report'] as [Section, string]] : []),
    ['company', 'Company'],
    ['industry', 'Industry'],
    ['financial', 'Financial'],
    ['news', 'News'],
    ['references', 'References'],
  ];
  const download = async () => {
    if (exporting) return;
    setExporting(true);
    setPDFError('');
    setDownloaded(false);
    try {
      await exportPDF(report, company, sample);
      setDownloaded(true);
    } catch {
      setPDFError('The PDF couldn’t be created. Your report is still available.');
    } finally {
      setExporting(false);
    }
  };
  const content = parsed.sections[tab];
  return (
    <main className="a-page" id="main-content">
      <div className="a-reporthead">
        <div className="f-company">
          <span className="f-avatar">{company.slice(0, 1).toLowerCase()}</span>
          <div>
            <h1>{company}</h1>
            <p className="a-date">
              {sample ? `Saved example · As of ${SAMPLE_PERIOD}` : 'Company research'}
            </p>
          </div>
        </div>
        <button className="f-black" disabled={exporting} onClick={download}>
          {exporting ? <LoaderCircle size={16} className="spin" /> : <Download size={16} />}{' '}
          {exporting ? 'Preparing PDF…' : 'Export PDF'}
        </button>
      </div>
      {downloaded && (
        <p className="export-success" role="status">
          Download started.
        </p>
      )}
      {pdfError && (
        <div className="a-notice" role="alert">
          <span>{pdfError}</span>
          <button onClick={download}>Try export again →</button>
        </div>
      )}
      <div className="a-reportgrid">
        <article className="a-panel report-panel">
          <div className="report-navigation">
            <nav ref={nav} className="a-tabs" aria-label="Report sections">
              {tabs.map(([id, title]) => (
                <button key={id} aria-pressed={tab === id} onClick={() => setTab(id)}>
                  {title}
                </button>
              ))}
            </nav>
            {(overflow.left || overflow.right) && (
              <div className="section-controls">
                <span>More sections</span>
                <button
                  aria-label="Scroll to earlier report sections"
                  disabled={!overflow.left}
                  onClick={() => nav.current?.scrollBy({ left: -180, behavior: 'smooth' })}
                >
                  <ArrowLeft size={16} />
                </button>
                <button
                  aria-label="Scroll to later report sections"
                  disabled={!overflow.right}
                  onClick={() => nav.current?.scrollBy({ left: 180, behavior: 'smooth' })}
                >
                  <ArrowRight size={16} />
                </button>
              </div>
            )}
          </div>
          <div className="a-content" aria-label={`${tab} report section`}>
            {content ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                skipHtml
                urlTransform={(url) => safeURL(url) || (url.startsWith('#') ? url : '')}
                components={{
                  img: ({ alt }) => (alt ? <span>{alt}</span> : null),
                  a: ({ href, children }) => {
                    const index = parsed.references.findIndex(
                      (ref) => ref.url === safeURL(href || ''),
                    );
                    const compact = tab !== 'references' && tab !== 'full' && index >= 0;
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noreferrer"
                        className={compact ? 'report-citation' : undefined}
                        title={compact ? parsed.references[index].title : undefined}
                        aria-label={
                          compact
                            ? `Source ${index + 1}: ${parsed.references[index].title}`
                            : undefined
                        }
                      >
                        {compact ? `[${index + 1}]` : children}
                      </a>
                    );
                  },
                  table: ({ children }) => (
                    <div className="table-scroll">
                      <table>{children}</table>
                    </div>
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
            ) : (
              <>
                <h2>{tabs.find(([id]) => id === tab)?.[1]}</h2>
                <p>
                  This report does not include a separate {tab} section.
                  {parsed.fallback
                    ? ' The full report preserves the available material.'
                    : ' No information has been inferred to fill the gap.'}
                </p>
              </>
            )}
          </div>
        </article>
        <aside className="a-rail" aria-label="Report sources">
          <div className="a-panel source-panel">
            <div className="source-heading">
              <h2>Sources</h2>
              <span>{parsed.references.length}</span>
            </div>
            <ol className="source-list">
              {parsed.references.slice(0, 5).map((ref, index) => {
                const [title, ...details] = ref.title.split(' · ');
                return (
                  <li className="a-ref" key={ref.url}>
                    <span className="source-number" aria-hidden="true">
                      {index + 1}
                    </span>
                    <div>
                      <a href={ref.url} target="_blank" rel="noreferrer">
                        {title}
                        <ArrowUpRight size={13} />
                      </a>
                      <p>
                        {new URL(ref.url).hostname.replace(/^www\./, '')}
                        {details.length ? ` · ${details.join(' · ')}` : ''}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
            {!parsed.references.length && (
              <p>No source links were supplied in the references section.</p>
            )}
            {parsed.references.length > 0 && tab !== 'references' && (
              <button className="f-demo-link source-all" onClick={() => setTab('references')}>
                View {parsed.references.length > 5 ? 'all ' : ''}references{' '}
                <ArrowUpRight size={14} />
              </button>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}

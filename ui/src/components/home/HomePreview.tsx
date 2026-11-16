import { ArrowUpRight, Layers2, PanelRight } from 'lucide-react';
import type { Section } from '../../lib/types';
export function HomePreview({ onSample }: { onSample: (section?: Section) => void }) {
  return (
    <div className="f-stage" aria-label="Cursor example report preview">
      <div className="f-product">
        <div className="f-productbar">
          <span className="f-windowdots" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>Company research</span>
          <PanelRight size={15} />
        </div>
        <div className="f-productbody">
          <div className="f-company">
            <span className="f-avatar">c</span>
            <div>
              <h3>Cursor</h3>
              <p className="f-small">AI developer tools · November 2025 example</p>
            </div>
          </div>
          <nav className="f-mini-tabs" aria-label="Example report sections">
            {(['briefing', 'company', 'industry', 'financial', 'news'] as Section[]).map(
              (section) => (
                <button key={section} onClick={() => onSample(section)}>
                  {section[0].toUpperCase() + section.slice(1)}
                </button>
              ),
            )}
          </nav>
          <div className="f-mini-label">BEFORE THE CONVERSATION</div>
          <p className="f-mini-lead">Can faster coding mean faster delivery?</p>
          <div className="f-mini-insight">
            <Layers2 size={16} />
            <span>Coding agents, Composer, and enterprise controls.</span>
          </div>
          <div className="hp-previewref">
            <p>Go beyond the company summary</p>
            <span>How do you measure useful agent output?</span>
          </div>
        </div>
        <div className="f-mini-footer">
          <button className="f-demo-link" onClick={() => onSample()}>
            Explore sample report <ArrowUpRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

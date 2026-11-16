import { ArrowUpRight, Building2, Layers2, ChartNoAxesCombined, Newspaper } from 'lucide-react';
import { CATEGORIES } from '../../lib/progress';
const icons = [Building2, Layers2, ChartNoAxesCombined, Newspaper];
export function HomeSections({ onStart }: { onStart: () => void }) {
  return (
    <>
      <section className="hp-section hp-perspectives" id="overview">
        <div>
          <div className="f-kicker">The details, connected</div>
          <h2>
            Four perspectives.
            <br />
            <span className="f-gradient">One clearer picture.</span>
          </h2>
          <p className="hp-intro">
            Understand what a company does, where it operates, and what is changing around it.
          </p>
        </div>
        <div className="hp-four">
          {CATEGORIES.map((category, i) => {
            const Icon = icons[i];
            return (
              <div key={category.id}>
                <div className="hp-icon">
                  <Icon size={23} />
                </div>
                <h3>
                  The{' '}
                  {category.id === 'financial'
                    ? 'financial context'
                    : category.id === 'news'
                      ? 'latest moves'
                      : category.id}
                </h3>
                <p>{category.description}</p>
              </div>
            );
          })}
        </div>
      </section>
      <section className="hp-section hp-process" id="how-it-works">
        <div className="f-kicker">From question to context</div>
        <h2>A simple path through the details.</h2>
        <div className="hp-steps">
          {[
            [
              'Start with a company',
              'Add its name and any context that helps identify the right business.',
            ],
            [
              'Follow the research',
              'See the research stages as sources are gathered and the report takes shape.',
            ],
            [
              'Prepare for the conversation',
              'Read what matters, check the sources, and leave with informed questions.',
            ],
          ].map(([title, description], i) => (
            <div className="hp-step" key={title}>
              <span>0{i + 1}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="hp-section hp-close">
        <div>
          <h2>
            Start with a name.
            <br />
            <span className="f-gradient">Leave with perspective.</span>
          </h2>
          <p>A clearer view before your next conversation.</p>
        </div>
        <button onClick={onStart} className="hp-start">
          Research a company <ArrowUpRight size={16} />
        </button>
      </section>
    </>
  );
}

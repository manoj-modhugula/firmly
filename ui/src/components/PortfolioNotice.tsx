import { FileSearch } from 'lucide-react';

export function PortfolioNotice({
  onSample,
  onBack,
}: {
  onSample: () => void;
  onBack: () => void;
}) {
  return (
    <main className="a-center notice-page" id="main-content">
      <div className="a-icon">
        <FileSearch size={24} />
      </div>
      <h1>Explore Firmly</h1>
      <p className="a-sub" role="status">
        Live research isn’t connected yet. Explore the Cursor report to see the research, sources,
        and briefing.
      </p>
      <div className="a-actions">
        <button className="f-black" onClick={onSample}>
          Explore sample report
        </button>
        <button className="f-plain" onClick={onBack}>
          Back to home
        </button>
      </div>
    </main>
  );
}

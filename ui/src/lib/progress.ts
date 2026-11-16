import type { ResearchEvent } from './types';
export const CATEGORIES = [
  {
    id: 'company',
    node: 'company_track',
    title: 'Company',
    description: 'Products, leadership, customers, and business model.',
  },
  {
    id: 'industry',
    node: 'market_track',
    title: 'Industry',
    description: 'Market context, competitors, and challenges.',
  },
  {
    id: 'financial',
    node: 'financial_track',
    title: 'Financial',
    description: 'Funding, investment, and available financial context.',
  },
  {
    id: 'news',
    node: 'news_track',
    title: 'News',
    description: 'Announcements, partnerships, and recent developments.',
  },
];
export const STAGES = [
  ['company_context', 'Getting oriented'],
  ['gather_stage', 'Collecting research'],
  ['selection_stage', 'Selecting sources'],
  ['reading_stage', 'Reading source material'],
  ['writing_stage', 'Writing sections'],
  ['assembly_stage', 'Preparing your report'],
] as const;
export function addEvent(events: ResearchEvent[], event: ResearchEvent) {
  // Keep the useful recent events bounded; streamed token fragments are not UI rows.
  if (['query_generating', 'report_chunk'].includes(event.type)) return events;
  return [...events, event].slice(-80);
}

export function researchStage(completed: string[]) {
  if (!completed.includes('company_context')) return STAGES[0];
  if (!CATEGORIES.every((category) => completed.includes(category.node))) return undefined;
  return STAGES.find(([id]) => !completed.includes(id));
}

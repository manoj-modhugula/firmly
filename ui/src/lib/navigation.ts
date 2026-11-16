import type { Page, Section } from './types';
const PAGES: Page[] = [
  'home',
  'settings',
  'progress',
  'report',
  'configuration',
  'failed',
  'unavailable',
  'connection',
];
export const SECTIONS: Section[] = [
  'briefing',
  'company',
  'industry',
  'financial',
  'news',
  'references',
  'full',
];
export type Route = {
  page: Page;
  job: string | null;
  sample: boolean;
  section: Section;
  scroll: number;
};
export function readRoute(search: string): Route {
  const params = new URLSearchParams(search);
  const job = params.get('job');
  const sample = params.has('sample');
  const view = params.get('view') as Page;
  const section = params.get('section') as Section;
  return {
    page: PAGES.includes(view) ? view : sample ? 'report' : job ? 'progress' : 'home',
    job,
    sample,
    section: SECTIONS.includes(section) ? section : 'briefing',
    scroll: 0,
  };
}
export function routeURL(route: Route) {
  const params = new URLSearchParams();
  if (route.job) params.set('job', route.job);
  if (route.sample) params.set('sample', '1');
  const defaultPage = route.sample ? 'report' : route.job ? 'progress' : 'home';
  if (route.page !== defaultPage) params.set('view', route.page);
  if (route.section !== 'briefing' && (route.sample || route.job))
    params.set('section', route.section);
  return '/' + (params.size ? '?' + params : '');
}
export function connectionErrors(
  settings: import('./types').Settings,
  config: import('./types').Config | null,
) {
  return {
    accessKey:
      settings.connection === 'managed'
        ? !(config?.model_gateway_ready || config?.direct_model_ready)
          ? 'This installation has no model connection. Use keys for this tab.'
          : ''
        : !settings.accessKey.trim() && !config?.model_gateway_ready
          ? 'Enter a model access key.'
          : '',
    searchKey:
      !settings.searchKey.trim() && !config?.search_ready ? 'Enter a web research key.' : '',
  };
}

export const HOME: Route = {
  page: 'home',
  job: null,
  sample: false,
  section: 'briefing',
  scroll: 0,
};

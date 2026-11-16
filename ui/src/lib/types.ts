export type Page =
  | 'home'
  | 'settings'
  | 'progress'
  | 'report'
  | 'configuration'
  | 'failed'
  | 'unavailable'
  | 'connection';
export type Section =
  | 'briefing'
  | 'company'
  | 'industry'
  | 'financial'
  | 'news'
  | 'references'
  | 'full';
export type Company = {
  company: string;
  company_url: string;
  industry: string;
  hq_location: string;
};
export type Settings = {
  searchKey: string;
  accessKey: string;
  model: string;
  connection: 'personal' | 'managed';
};
export type Config = {
  search_ready: boolean;
  model_gateway_ready: boolean;
  direct_model_ready: boolean;
  default_model: string;
  storage_ready: boolean;
};
export type ResearchEvent = {
  type: string;
  step?: string;
  category?: string;
  report?: string;
  company?: string;
  error?: string;
  message?: string;
  query?: string;
  query_number?: number;
  completed_steps?: string[];
  total_documents?: number;
  count?: number;
};
export type Job = {
  status: string;
  company: string;
  report?: string;
  error?: string;
  current_step?: string;
  completed_steps?: string[];
};
export const EMPTY_COMPANY: Company = {
  company: '',
  company_url: '',
  industry: '',
  hq_location: '',
};

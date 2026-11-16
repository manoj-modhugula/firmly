import type { Company } from './types';
export type PendingSubmission = { id: string; company: Company };
const KEY = 'firmly:pending-submission';
export function readPendingSubmission(): PendingSubmission | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(KEY) || 'null');
    if (!value || typeof value.id !== 'string' || !/^[-a-f0-9]{36}$/i.test(value.id)) return null;
    if (
      !value.company ||
      !['company', 'company_url', 'industry', 'hq_location'].every(
        (key) => typeof value.company[key] === 'string',
      )
    )
      return null;
    return {
      id: value.id,
      company: {
        company: value.company.company,
        company_url: value.company.company_url,
        industry: value.company.industry,
        hq_location: value.company.hq_location,
      },
    };
  } catch {
    return null;
  }
}
export function rememberSubmission(value: PendingSubmission | null) {
  try {
    if (!value) {
      sessionStorage.removeItem(KEY);
      return;
    }
    // Explicit allowlist: credentials and settings never enter session storage.
    const { company, company_url, industry, hq_location } = value.company;
    sessionStorage.setItem(
      KEY,
      JSON.stringify({ id: value.id, company: { company, company_url, industry, hq_location } }),
    );
  } catch {
    /* Recovery still works in memory if storage is unavailable. */
  }
}

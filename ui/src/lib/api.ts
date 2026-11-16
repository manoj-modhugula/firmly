import type { Company, Config, Job, Settings } from './types';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function checked(response: Response) {
  if (response.ok) return response;
  let message = 'The request could not be completed. Please try again.';
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') message = body.detail;
    else if (response.status === 422) message = 'Check the company details and try again.';
  } catch {
    /* A non-JSON error response uses the safe fallback. */
  }
  throw new ApiError(response.status, message);
}

async function request<T>(
  url: string,
  options: RequestInit,
  timeout: number,
  read: (response: Response) => Promise<T>,
): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const abort = () => controller.abort();
  options.signal?.addEventListener('abort', abort, { once: true });
  if (options.signal?.aborted) abort();
  const timer = setTimeout(() => {
    timedOut = true;
    abort();
  }, timeout);
  try {
    return await read(await checked(await fetch(url, { ...options, signal: controller.signal })));
  } catch (error) {
    if (timedOut)
      throw new ApiError(
        408,
        'The connection timed out. Please check your connection and try again.',
      );
    throw error;
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', abort);
  }
}

export function requestJSON<T>(
  url: string,
  options: RequestInit = {},
  timeout = 12_000,
): Promise<T> {
  return request(url, options, timeout, (response) => response.json());
}
export const getConfig = (signal?: AbortSignal) => requestJSON<Config>('/api/config', { signal });
export const getJob = (id: string, signal?: AbortSignal) =>
  requestJSON<Job>(`/api/research/${encodeURIComponent(id)}`, { signal });
export const getModels = (signal?: AbortSignal) =>
  requestJSON<{ models: { id: string; name: string }[] }>('/api/models', { signal });
export function createResearch(
  company: Company,
  settings: Settings,
  requestId: string,
): Promise<{ job_id: string }> {
  return requestJSON(
    '/api/research',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...company,
        request_id: requestId,
        search_key: settings.searchKey.trim() || undefined,
        model_key:
          settings.connection === 'personal' ? settings.accessKey.trim() || undefined : undefined,
        model: settings.connection === 'personal' ? settings.model : undefined,
      }),
    },
    20_000,
  );
}
export async function exportPDF(report: string, company: string) {
  const blob = await request(
    '/api/generate-pdf',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_content: report, company_name: company }),
    },
    30_000,
    (response) => response.blob(),
  );
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${company.replace(/[^a-z0-9-]/gi, '-').slice(0, 80) || 'company'}-research.pdf`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

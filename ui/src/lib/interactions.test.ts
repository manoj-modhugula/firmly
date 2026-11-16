import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readRoute, routeURL, connectionErrors } from './navigation';
import { ApiError, requestJSON, createResearch } from './api';
import type { Settings, Config } from './types';
const settings: Settings = {
  searchKey: '',
  accessKey: '',
  model: 'automatic',
  connection: 'personal',
};
const config: Config = {
  search_ready: false,
  model_gateway_ready: false,
  direct_model_ready: false,
  default_model: 'automatic',
  storage_ready: false,
};
test('history URLs preserve selected report section through settings without credentials', () => {
  const report = {
    page: 'report' as const,
    job: null,
    sample: true,
    section: 'financial' as const,
    scroll: 0,
  };
  assert.deepEqual(readRoute(new URL(routeURL(report), 'https://example.org').search), report);
  assert.equal(
    readRoute(new URL(routeURL({ ...report, page: 'settings' }), 'https://example.org').search)
      .section,
    'financial',
  );
  assert.equal(readRoute('?view=unexpected&section=unexpected').page, 'home');
  assert.equal(readRoute('?view=connection&job=existing').job, 'existing');
});
test('missing connections show individual errors and support installation defaults', () => {
  assert.ok(connectionErrors(settings, config).accessKey);
  assert.ok(connectionErrors(settings, config).searchKey);
  assert.ok(connectionErrors({ ...settings, accessKey: '  ' }, config).accessKey);
  assert.deepEqual(connectionErrors({ ...settings, accessKey: 'key', searchKey: 'key' }, config), {
    accessKey: '',
    searchKey: '',
  });
  assert.deepEqual(
    connectionErrors(
      { ...settings, connection: 'managed' },
      { ...config, direct_model_ready: true, search_ready: true },
    ),
    { accessKey: '', searchKey: '' },
  );
});
test('stalled requests abort with a recoverable timeout', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (_url, options) =>
    new Promise((_resolve, reject) =>
      options?.signal?.addEventListener('abort', () => reject(new Error('aborted'))),
    );
  try {
    await assert.rejects(
      requestJSON('/test', {}, 10),
      (error: unknown) => error instanceof ApiError && error.status === 408,
    );
  } finally {
    globalThis.fetch = original;
  }
});
test('retry submission retains request identity and only sends credentials in POST body', async () => {
  const original = globalThis.fetch;
  const calls: { url: string; body: Record<string, unknown> }[] = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), body: JSON.parse(String(options?.body)) });
    return new Response(JSON.stringify({ job_id: 'same' }), { status: 202 });
  };
  try {
    for (let i = 0; i < 2; i++)
      await createResearch(
        { company: 'Example', company_url: '', industry: '', hq_location: '' },
        { ...settings, accessKey: ' secret-model ', searchKey: ' secret-search ' },
        'same-request',
      );
    assert.equal(calls[0].body.request_id, calls[1].body.request_id);
    assert.equal(calls[0].body.model_key, 'secret-model');
    assert.equal(calls[0].url, '/api/research');
  } finally {
    globalThis.fetch = original;
  }
});

test('pending submission recovery excludes credentials from stored metadata', async () => {
  const { rememberSubmission, readPendingSubmission } = await import('./submission');
  const saved = new Map<string, string>();
  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => saved.get(key) || null,
      setItem: (key: string, value: string) => saved.set(key, value),
      removeItem: (key: string) => saved.delete(key),
    },
  });
  try {
    rememberSubmission({
      id: '12345678-1234-4234-8234-123456789abc',
      company: {
        company: 'Example',
        company_url: '',
        industry: '',
        hq_location: '',
        model_key: 'must-not-store',
      } as never,
    });
    assert.equal(readPendingSubmission()?.company.company, 'Example');
    assert.ok(![...saved.values()].join('').includes('must-not-store'));
    rememberSubmission(null);
    assert.equal(readPendingSubmission(), null);
  } finally {
    Reflect.deleteProperty(globalThis, 'sessionStorage');
  }
});

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { setImmediate as flush } from 'node:timers/promises';
import { ApiError, requestJSON } from './api';
import { observeResearch } from './researchObserver';
import type { Job, ResearchEvent } from './types';

class TestStream {
  onopen: EventSource['onopen'] = null;
  onerror: EventSource['onerror'] = null;
  onmessage: EventSource['onmessage'] = null;
  closed = false;
  close() {
    this.closed = true;
  }
  message(value: unknown) {
    this.onmessage?.call(
      this as unknown as EventSource,
      new MessageEvent('message', { data: JSON.stringify(value) }),
    );
  }
  error() {
    this.onerror?.call(this as unknown as EventSource, new Event('error'));
  }
}
function harness(read: (id: string, signal?: AbortSignal) => Promise<Job>, pollEvery = 5000) {
  const stream = new TestStream();
  const complete: string[] = [];
  const failures: string[] = [];
  const events: ResearchEvent[] = [];
  const snapshots: Job[] = [];
  const dispose = observeResearch(
    'existing',
    {
      onComplete: (report) => complete.push(report),
      onFailed: (_message, kind) => failures.push(kind),
      onEvent: (event) => events.push(event),
      onSnapshot: (job) => snapshots.push(job),
      onReconnecting: () => {},
    },
    { open: () => stream, read, pollEvery },
  );
  return { stream, complete, failures, events, snapshots, dispose };
}

test('completion closes the stream and ignores duplicate terminal events and late GET responses', async (t) => {
  let resolve!: (job: Job) => void;
  const h = harness(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  t.after(h.dispose);
  h.stream.message({ type: 'complete', report: '# Complete', company: 'Test' });
  h.stream.message({ type: 'complete', report: '# Duplicate' });
  resolve({ status: 'completed', company: 'Test', report: '# Late' });
  await flush();
  assert.deepEqual(h.complete, ['# Complete']);
  assert.equal(h.stream.closed, true);
  assert.deepEqual(h.snapshots, []);
});

test('disposal aborts in-flight status requests and prevents callbacks after unmount', async () => {
  let signal: AbortSignal | undefined;
  let resolve!: (job: Job) => void;
  const h = harness((_id, requestSignal) => {
    signal = requestSignal;
    return new Promise((done) => {
      resolve = done;
    });
  });
  h.dispose();
  assert.equal(signal?.aborted, true);
  assert.equal(h.stream.closed, true);
  resolve({ status: 'completed', company: 'Test', report: '# Late' });
  h.stream.message({ type: 'error', error: 'Late failure' });
  await flush();
  assert.deepEqual(h.complete, []);
  assert.deepEqual(h.failures, []);
});

test('malformed event payloads are ignored while valid progress remains available', async (t) => {
  const h = harness(async () => ({ status: 'processing', company: 'Test' }));
  t.after(h.dispose);
  for (const value of [
    null,
    {},
    [],
    { type: 3 },
    { type: 'complete', report: 42 },
    { type: 'progress', completed_steps: [null] },
  ])
    h.stream.message(value);
  h.stream.message({ type: 'progress', step: 'company_track' });
  await flush();
  assert.equal(h.events.length, 1);
  assert.equal(h.events[0].step, 'company_track');
  assert.deepEqual(h.failures, []);
});

test('overlapping stream errors do not start concurrent status requests', async (t) => {
  let calls = 0;
  const h = harness(async () => {
    calls++;
    return new Promise(() => {});
  });
  t.after(h.dispose);
  h.stream.error();
  h.stream.error();
  await flush();
  assert.equal(calls, 1);
});

test('missing jobs produce unavailable recovery and stop observing', async (t) => {
  const h = harness(async () => {
    throw new ApiError(404, 'Missing');
  });
  t.after(h.dispose);
  await flush();
  assert.deepEqual(h.failures, ['unavailable']);
  assert.equal(h.stream.closed, true);
});

test('three failed checks produce connection recovery without submitting new research', async (t) => {
  let calls = 0;
  const h = harness(async () => {
    calls++;
    throw new ApiError(503, 'Unavailable');
  }, 2);
  t.after(h.dispose);
  await new Promise<void>((resolve, reject) => {
    const deadline = setTimeout(() => {
      clearInterval(check);
      reject(new Error('Recovery did not finish'));
    }, 200);
    const check = setInterval(() => {
      if (h.failures.length) {
        clearInterval(check);
        clearTimeout(deadline);
        resolve();
      }
    }, 2);
  });
  assert.equal(calls, 3);
  assert.deepEqual(h.failures, ['connection']);
  assert.equal(h.stream.closed, true);
});

test('caller cancellation reaches fetch without being mislabeled as a timeout', async () => {
  const original = globalThis.fetch;
  const controller = new AbortController();
  globalThis.fetch = async (_url, options) =>
    new Promise((_resolve, reject) =>
      options?.signal?.addEventListener('abort', () =>
        reject(new DOMException('Cancelled', 'AbortError')),
      ),
    );
  try {
    const result = requestJSON('/test', { signal: controller.signal });
    controller.abort();
    await assert.rejects(
      result,
      (error) => error instanceof DOMException && error.name === 'AbortError',
    );
  } finally {
    globalThis.fetch = original;
  }
});

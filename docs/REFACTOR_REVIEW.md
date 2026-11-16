# Code review and validation — November 16, 2026

This record covers code organization, resource management, and regression checks.

## Completed

| Area | Changes |
| --- | --- |
| Readability | Formatted TypeScript, JSX, CSS, Python, and test sources; removed unused imports and variables. |
| Frontend boundaries | Separated screen composition, workspace coordination, settings return navigation, and the stream observer; extracted homepage sections. |
| Styling | Removed 187 superseded declarations and unused notice/proof styles; split styles into five files while preserving cascade order. |
| API boundaries | Separated composition, schemas, routes, middleware, model catalog, and job execution. |
| Job state | Added typed records, centralized publication, context-local store binding, bounded history, and safe event metadata. |
| Requests | Enforced body limits incrementally, including chunked bodies; retained request identity and capacity checks. |
| Lifecycle | Added request cancellation, stream disposal, task cancellation, owned HTTP pools, and database shutdown. |
| Parallel work | Capped actual extraction requests across categories; cancel sibling briefing tasks when one fails. |
| Errors | Removed empty catches, validated stream payloads, suppressed late callbacks, cleared recovered errors, and handled missing persisted content. |
| Sources | Preserved meaningful query parameters during URL normalization and curation. |
| Persistence | Added upserts, UTC timestamps, bounded socket/operation timeouts, and safe completion ordering. |
| Diagnostics | Replaced eager formatted logging with parameterized calls where applicable; moved detailed reference logging to debug. |
| Dead code | Removed a no-op progress helper, unused reference parser, empty PDF constructor, duplicated track wrappers, and unsupported editor entry points. |
| Publication | Ignored local QA output and mock ZIP archives; added architecture and validation documentation. |
| Checks | Added Prettier, ESLint, TypeScript unused checks, Ruff, targeted regression tests. |

## Verification

- 37 backend tests pass, including a complete run through the real pipeline stages with mocked external model/search boundaries.
- 22 frontend tests pass, including stream disposal, late responses, duplicate completion, malformed events, overlapping polls, connection recovery, and caller cancellation.
- A clean `npm ci` install, Python formatting/lint, frontend formatting/lint/type checks, and the production build pass.
- Python dependency consistency check passes. The npm audit reports zero vulnerabilities, including development dependencies.
- Browser checks cover submission through settings, field errors, progress, reload recovery on the same job, completion while settings remain open, report opening, PDF export, failed jobs, missing jobs, and reconnection without a new submission.
- Homepage, report, and settings comparisons at 1280px and 390px found no differences in the recorded computed layout/typography/color/border styles. Additional narrow checks at 320px and wide report checks at 1440px fit without page-wide horizontal overflow.

## Size and local parsing measurements

The production CSS decreased from 42.64KB to approximately 38.20KB before compression; gzip decreased from 8.27KB to approximately 7.59KB. The homepage JavaScript increased from 61.57KB to approximately 62.29KB gzipped after adding cancellation and recovery validation.

A local Node benchmark after warmup ran 200 parses per input. The 6,799-character saved report had a 1.174ms median and 1.494ms p95. A synthetic 67,990-character input had a 12.372ms median and 13.122ms p95. These measure parsing on this machine, not browser rendering, Core Web Vitals, or provider research latency.

## Remaining verification

Broad exception handlers at external-service and optional-persistence boundaries provide safe errors and recoverable fallbacks.

Live model/search quality, credential acceptance, provider latency, and quota behavior still require configured service keys. Real MongoDB persistence remains unverified. Docker execution could not be tested because the local daemon is not running. A full accessibility audit and production load test remain separate release checks.

The single-worker, in-memory active-job architecture remains appropriate for a controlled demo. It requires additional infrastructure for durable jobs or horizontal scaling.

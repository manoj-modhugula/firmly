# Architecture

Firmly serves a React interface and a FastAPI research API from one origin. The supported server entry point is `application:app`.

## Interface

- `App.tsx` composes screens and shared navigation.
- `hooks/useWorkspace.ts` coordinates the active company, research submission, and report state.
- `hooks/useSettingsNavigation.ts` preserves the route and report section when opening settings.
- `hooks/useNavigation.ts` owns browser history and scroll restoration.
- `hooks/useResearch.ts` adapts the research observer to React state.
- `lib/researchObserver.ts` owns the event stream, status polling, reconnection, and disposal.
- `lib/api.ts` owns HTTP error handling, deadlines, caller cancellation, and PDF downloads.
- `lib/report.ts` parses Markdown sections and safe source links.
- `components/home/` contains the homepage preview and supporting sections.
- `styles.css` imports the layout, component, report, screen, and interaction styles in cascade order. Keep that order when editing styles.

Credentials stay in tab memory. Pending-submission recovery stores only an ID and allowlisted company details in session storage. A reload reconnects through the existing job URL.

## API

- `firmly_api/app.py` composes the application and manages service startup and shutdown.
- `firmly_api/schemas.py` validates incoming payloads.
- `firmly_api/middleware.py` bounds streamed request bodies and applies local request limits.
- `firmly_api/research.py` exposes submission, status, report, event-stream, PDF, and health routes.
- `firmly_api/service.py` owns job acceptance, idempotent retries, task execution, deadlines, and optional persistence.
- `firmly_api/catalog.py` caches model choices and coalesces concurrent refreshes.

## Research engine

The pipeline grounds the company, runs four research tracks, gathers and selects sources, enriches documents, generates section briefings, and assembles the report.

`firmly_engine/jobs.py` owns typed job records, bounded replay history, and event publication. A context-local store keeps stage events associated with the executing service. Progress history retains allowlisted metadata rather than source bodies or credentials.

`firmly_engine/resources.py` owns per-run HTTP pools. Search and extraction share a web client. Model calls share owned transports. Resources are released on success, failure, and cancellation. Extraction is capped at three simultaneous requests per run; briefing generation is capped at two. Structured briefing tasks cancel their siblings on failure.

## Persistence and deployment

Run one ASGI worker. Job state, replay history, local quotas, and retry identity are process-local. Active jobs do not survive restart. Optional MongoDB persistence stores completed reports with bounded connection timeouts, upserts, and UTC timestamps. Missing persisted report content produces a recoverable failure.

The Dockerfile builds the interface and copies both Python packages into the runtime image. Public owner-funded research requires access control and shared quotas. Horizontal scaling requires durable jobs and shared coordination before adding workers.
